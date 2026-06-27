from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import httpx
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from fastapi import status

from app.core.config import get_settings
from app.models.task import TaskResponse, TaskStatus
from app.services import task_service

log = structlog.get_logger()

_scheduler: Optional[AsyncIOScheduler] = None
_client: Optional[httpx.AsyncClient] = None


def get_scheduler() -> AsyncIOScheduler:
    if _scheduler is None:
        raise RuntimeError("job runner not started — call start() in lifespan first")
    return _scheduler


def _get_client() -> httpx.AsyncClient:
    if _client is None:
        raise RuntimeError("job runner not started — call start() in lifespan first")
    return _client


async def start() -> None:
    global _scheduler, _client
    settings = get_settings()
    _client = httpx.AsyncClient(timeout=settings.WEBHOOK_TIMEOUT_SECONDS)
    _scheduler = AsyncIOScheduler()
    _scheduler.start()
    await task_service.recover_running_tasks()
    await _reload_pending()
    log.info("job_runner.started")


async def stop() -> None:
    global _scheduler, _client
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
    if _client:
        await _client.aclose()
    _client = None
    log.info("job_runner.stopped")


def schedule_task(task_id: UUID, execution_time: datetime) -> None:
    settings = get_settings()
    get_scheduler().add_job(
        fire_webhook,
        trigger=DateTrigger(run_date=execution_time),
        args=[task_id],
        id=str(task_id),
        replace_existing=True,
        misfire_grace_time=settings.MISFIRE_GRACE_TIME_SECONDS,
    )
    log.info("task.scheduled", task_id=str(task_id), run_at=execution_time.isoformat())


def _schedule_retry(task_id: UUID, retry_count: int) -> None:
    settings = get_settings()
    # delay doubles each attempt: 60s → 120s → 240s…
    delay_s = settings.RETRY_BASE_DELAY_SECONDS * (2 ** (retry_count - 1))
    run_at = datetime.now(timezone.utc) + timedelta(seconds=delay_s)
    get_scheduler().add_job(
        fire_webhook,
        trigger=DateTrigger(run_date=run_at),
        args=[task_id],
        id=f"{task_id}_retry_{retry_count}",
        replace_existing=True,
        misfire_grace_time=settings.MISFIRE_GRACE_TIME_SECONDS,
    )
    log.info("task.retry_scheduled", task_id=str(task_id), retry=retry_count, delay_s=delay_s)


def _schedule_poll(task_id: UUID, check_url: str, attempt_id: UUID, poll_count: int) -> None:
    settings = get_settings()
    run_at = datetime.now(timezone.utc) + timedelta(seconds=settings.POLL_INTERVAL_SECONDS)
    get_scheduler().add_job(
        _poll_execution,
        trigger=DateTrigger(run_date=run_at),
        args=[task_id, check_url, attempt_id, poll_count],
        id=f"{task_id}_poll_{poll_count}",
        replace_existing=True,
    )
    log.info("task.poll_scheduled", task_id=str(task_id), poll_count=poll_count)


def cancel_job(task_id: UUID) -> None:
    try:
        get_scheduler().remove_job(str(task_id))
        log.info("task.job_cancelled", task_id=str(task_id))
    except Exception:
        pass  # job already fired or was never in the scheduler


async def _reload_pending() -> None:
    count = 0
    for task_status in (TaskStatus.CREATED, TaskStatus.PENDING):
        tasks = await task_service.list_tasks(status=task_status, limit=1000)
        for task in tasks:
            schedule_task(UUID(task.id), task.execution_time)
            count += 1
    # RETRYING tasks lost their delay on restart — fire immediately so they're not stuck
    for task in await task_service.list_tasks(status=TaskStatus.RETRYING, limit=1000):
        schedule_task(UUID(task.id), datetime.now(timezone.utc))
        count += 1
    log.info("job_runner.pending_reloaded", count=count)


async def fire_webhook(task_id: UUID) -> None:
    task = await task_service.get_task(task_id)
    if not task:
        log.warning("webhook.task_not_found", task_id=str(task_id))
        return

    # race-condition guard: task may have been cancelled or finished between scheduling and now
    if task.status in (TaskStatus.CANCELLED, TaskStatus.SUCCESS, TaskStatus.FAILED):
        log.info("webhook.skip", task_id=str(task_id), status=task.status)
        return

    attempt_number = task.retry_count + 1
    attempt_id = await task_service.create_attempt(task_id, attempt_number)
    await task_service.mark_running(task_id)

    start = time.perf_counter()
    try:
        resp = await _get_client().post(
            task.webhook_url,
            json={"task_id": str(task_id), "attempt_id": str(attempt_id), "payload": task.payload},
        )
        duration_ms = int((time.perf_counter() - start) * 1000)

        if resp.status_code == status.HTTP_202_ACCEPTED:
            check_url = resp.json().get("check_url")
            if not check_url:
                log.error("webhook.missing_check_url", task_id=str(task_id))
                await _handle_failure(task_id, attempt_id, "202 response missing check_url", duration_ms, task)
                return
            _schedule_poll(task_id, check_url, attempt_id, poll_count=0)
            log.info("webhook.async_queued", task_id=str(task_id), check_url=check_url)

        elif resp.is_success:
            await task_service.complete_attempt(attempt_id, resp.status_code, resp.text, duration_ms)
            await task_service.mark_success(task_id)
            log.info("webhook.success", task_id=str(task_id), http_status=resp.status_code, duration_ms=duration_ms)

        else:
            log.warning("webhook.non_2xx", task_id=str(task_id), http_status=resp.status_code)
            await _handle_failure(task_id, attempt_id, f"HTTP {resp.status_code}", duration_ms, task)

    except Exception:
        duration_ms = int((time.perf_counter() - start) * 1000)
        log.error("webhook.error", task_id=str(task_id), exc_info=True)
        await _handle_failure(task_id, attempt_id, "connection error or timeout", duration_ms, task)


async def _poll_execution(task_id: UUID, check_url: str, attempt_id: UUID, poll_count: int) -> None:
    settings = get_settings()

    if poll_count >= settings.POLL_MAX_ATTEMPTS:
        log.warning("webhook.poll_timeout", task_id=str(task_id), polls=poll_count)
        task = await task_service.get_task(task_id)
        await _handle_failure(task_id, attempt_id, "async execution timed out", 0, task)
        return

    try:
        resp = await _get_client().get(check_url)
        data = resp.json()
        exec_status = data.get("status")

        if exec_status == "COMPLETED":
            duration_ms = data.get("duration_ms") or 0
            await task_service.complete_attempt(attempt_id, status.HTTP_200_OK, resp.text, duration_ms)
            await task_service.mark_success(task_id)
            log.info("webhook.poll_completed", task_id=str(task_id), polls=poll_count + 1)

        elif exec_status == "FAILED":
            error = data.get("error_message") or "executor reported failure"
            task = await task_service.get_task(task_id)
            log.warning("webhook.poll_failed", task_id=str(task_id))
            await _handle_failure(task_id, attempt_id, error, 0, task)

        else:
            # RECEIVED or PROCESSING — keep polling
            _schedule_poll(task_id, check_url, attempt_id, poll_count + 1)

    except Exception:
        log.error("webhook.poll_error", task_id=str(task_id), poll_count=poll_count, exc_info=True)
        # transient error polling the executor — retry the poll itself
        _schedule_poll(task_id, check_url, attempt_id, poll_count + 1)


async def _handle_failure(
    task_id: UUID,
    attempt_id: UUID,
    error: str,
    duration_ms: int,
    task: Optional[TaskResponse],
) -> None:
    await task_service.fail_attempt(attempt_id, error, duration_ms)
    if task and task.retry_count < task.max_retries:
        new_count = await task_service.increment_retry_count(task_id)
        await task_service.mark_retrying(task_id)
        _schedule_retry(task_id, new_count)
        log.info("task.will_retry", task_id=str(task_id), retry=new_count, max=task.max_retries)
    else:
        await task_service.mark_failed(task_id)
        log.warning("task.permanently_failed", task_id=str(task_id))
