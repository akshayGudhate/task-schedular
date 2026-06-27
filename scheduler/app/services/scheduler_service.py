from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

from app.core.config import get_settings
from app.models.task import TaskStatus

log = structlog.get_logger()

_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    if _scheduler is None:
        raise RuntimeError("scheduler engine not started — call start() in lifespan first")
    return _scheduler


async def start() -> None:
    global _scheduler
    _scheduler = AsyncIOScheduler()
    _scheduler.start()
    await _reload_pending()
    log.info("scheduler.engine.started")


async def stop() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
    log.info("scheduler.engine.stopped")


def schedule_task(task_id: UUID, execution_time: datetime) -> None:
    from app.services.webhook_service import fire_webhook  # deferred — avoids circular import when webhook_service imports scheduler_service for retry scheduling
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


def schedule_retry(task_id: UUID, retry_count: int) -> None:
    from app.services.webhook_service import fire_webhook
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
    log.info("task.retry_scheduled",
             task_id=str(task_id), retry=retry_count, delay_s=delay_s, run_at=run_at.isoformat())


def schedule_poll(task_id: UUID, check_url: str, attempt_id: UUID, poll_count: int) -> None:
    from app.services.webhook_service import poll_execution
    settings = get_settings()
    run_at = datetime.now(timezone.utc) + timedelta(seconds=settings.POLL_INTERVAL_SECONDS)
    get_scheduler().add_job(
        poll_execution,
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
    from app.services.task_service import list_tasks
    count = 0

    for status in (TaskStatus.CREATED, TaskStatus.PENDING):
        tasks = await list_tasks(status=status, limit=1000)
        for task in tasks:
            schedule_task(UUID(task.id), task.execution_time)
            count += 1

    # RETRYING tasks lost their delay on restart — fire immediately so they're not stuck
    for task in await list_tasks(status=TaskStatus.RETRYING, limit=1000):
        schedule_task(UUID(task.id), datetime.now(timezone.utc))
        count += 1

    log.info("scheduler.pending_reloaded", count=count)
