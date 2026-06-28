from __future__ import annotations

# two webhook patterns: sync (200 — done by the time we respond) and async (202 — scheduler must poll check_url)
import asyncio
import time
from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, BackgroundTasks, Request, status

from app.models.execution import ExecutionRequest, WebhookResponse
import app.services.execution_service as svc

router = APIRouter()
log = structlog.get_logger()

_404 = {status.HTTP_404_NOT_FOUND: {"description": "Execution record not found"}}


async def _run_async(execution_id: UUID, delay: float, result: dict[str, Any]) -> None:
    # runs in a FastAPI BackgroundTask so the 202 response is sent before processing starts
    start = time.perf_counter()
    try:
        await svc.mark_processing(execution_id)
        await asyncio.sleep(delay)
        duration_ms = int((time.perf_counter() - start) * 1000)
        await svc.complete(execution_id, result, duration_ms)
        log.info("execution.completed", execution_id=str(execution_id))
    except Exception:
        duration_ms = int((time.perf_counter() - start) * 1000)
        await svc.fail(
            execution_id, "unexpected error during async processing", duration_ms
        )
        log.error("execution.failed", execution_id=str(execution_id), exc_info=True)


@router.post(
    "/send-welcome",
    response_model=WebhookResponse,
    summary="Send welcome email",
    description="""
**Sync — returns 200 immediately.**

Simulates sending a welcome email to a new user. Execution is recorded in the DB and
`status` is `COMPLETED` by the time the response is returned.

**Expected payload fields:**
- `email` — recipient address (falls back to `"unknown"`)
- `template` — template name (falls back to `"welcome"`)
""",
)
async def send_welcome(body: ExecutionRequest, request: Request) -> WebhookResponse:
    start = time.perf_counter()
    exec_id = await svc.create_execution(
        body.task_id,
        body.attempt_id,
        str(request.url),
        body.payload,
    )
    await svc.mark_processing(exec_id)
    result = {
        "email_sent": True,
        "recipient": body.payload.get("email", "unknown"),
        "template": body.payload.get("template", "welcome"),
    }
    duration_ms = int((time.perf_counter() - start) * 1000)
    await svc.complete(exec_id, result, duration_ms)
    log.info("webhook.send_welcome", execution_id=str(exec_id))
    return WebhookResponse(execution_id=str(exec_id), status="COMPLETED", result=result)


@router.post(
    "/security-alert",
    response_model=WebhookResponse,
    summary="Trigger security alert",
    description="""
**Sync — returns 200 immediately.**

Simulates dispatching a security alert to Slack and email. Execution is recorded and
`status` is `COMPLETED` by the time the response is returned.

**Expected payload fields:**
- `severity` — `"low"`, `"medium"`, or `"high"` (falls back to `"medium"`)
""",
)
async def security_alert(body: ExecutionRequest, request: Request) -> WebhookResponse:
    start = time.perf_counter()
    exec_id = await svc.create_execution(
        body.task_id,
        body.attempt_id,
        str(request.url),
        body.payload,
    )
    await svc.mark_processing(exec_id)
    result = {
        "alert_sent": True,
        "severity": body.payload.get("severity", "medium"),
        "notified_channels": ["slack", "email"],
    }
    duration_ms = int((time.perf_counter() - start) * 1000)
    await svc.complete(exec_id, result, duration_ms)
    log.info("webhook.security_alert", execution_id=str(exec_id))
    return WebhookResponse(execution_id=str(exec_id), status="COMPLETED", result=result)


@router.post(
    "/notify-admin",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=WebhookResponse,
    summary="Notify admin on new signup",
    description="""
**Async — returns 202 immediately, processes in background (~3 s).**

Simulates notifying the admin dashboard when a new user signs up.
The response includes a `check_url` — poll it with `GET /status/{execution_id}` until
`status` is `COMPLETED` or `FAILED`.

**Expected payload fields:**
- `user` — username or email of the new signup (falls back to `"unknown"`)
""",
)
async def notify_admin(
    body: ExecutionRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> WebhookResponse:
    exec_id = await svc.create_execution(
        body.task_id,
        body.attempt_id,
        str(request.url),
        body.payload,
    )
    result = {
        "notification_sent": True,
        "channel": "admin_dashboard",
        "user": body.payload.get("user", "unknown"),
    }
    background_tasks.add_task(_run_async, exec_id, 3.0, result)
    check_url = f"{request.base_url}status/{exec_id}"
    log.info("webhook.notify_admin.queued", execution_id=str(exec_id))
    return WebhookResponse(
        execution_id=str(exec_id), status="QUEUED", check_url=check_url
    )


@router.post(
    "/daily-report",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=WebhookResponse,
    summary="Trigger daily summary report",
    description="""
**Async — returns 202 immediately, processes in background (~5 s).**

Simulates generating the daily summary report. The response includes a `check_url` —
poll it with `GET /status/{execution_id}` until `status` is `COMPLETED` or `FAILED`.

No special payload fields required.
""",
)
async def daily_report(
    body: ExecutionRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> WebhookResponse:
    exec_id = await svc.create_execution(
        body.task_id,
        body.attempt_id,
        str(request.url),
        body.payload,
    )
    result = {
        "report_generated": True,
        "report_id": str(exec_id),
        "total_rows": 1234,
    }
    background_tasks.add_task(_run_async, exec_id, 5.0, result)
    check_url = f"{request.base_url}status/{exec_id}"
    log.info("webhook.daily_report.queued", execution_id=str(exec_id))
    return WebhookResponse(
        execution_id=str(exec_id), status="QUEUED", check_url=check_url
    )
