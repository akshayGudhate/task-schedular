from __future__ import annotations

import json
from typing import Optional
from uuid import UUID

import asyncpg
import structlog

from app.core.errors import InvalidTransitionError, NotFoundError
from app.db.database import get_connection
from app.models.task import (
    AttemptStatus,
    TaskAttemptResponse,
    TaskCreate,
    TaskDetailResponse,
    TaskResponse,
    TaskStatus,
)
from app.state_machine import ALLOWED_TRANSITIONS

log = structlog.get_logger()


def _to_task_response(row: asyncpg.Record) -> TaskResponse:
    payload = row["payload"]
    if isinstance(payload, str):
        payload = json.loads(payload)
    return TaskResponse(
        id=str(row["id"]),
        name=row["name"],
        execution_time=row["execution_time"],
        webhook_url=row["webhook_url"],
        payload=payload,
        recurrence=row["recurrence"],
        cron_expression=row["cron_expression"],
        status=row["status"],
        max_retries=row["max_retries"],
        retry_count=row["retry_count"],
        parent_task_id=str(row["parent_task_id"]) if row["parent_task_id"] else None,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _to_attempt_response(row: asyncpg.Record) -> TaskAttemptResponse:
    return TaskAttemptResponse(
        id=str(row["id"]),
        attempt_number=row["attempt_number"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        http_status=row["http_status"],
        response_body=row["response_body"],
        duration_ms=row["duration_ms"],
        status=AttemptStatus(row["status"]),
        error_message=row["error_message"],
    )


async def create_task(data: TaskCreate) -> TaskResponse:
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO tasks (name, execution_time, webhook_url, payload, recurrence, cron_expression, max_retries)
            VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7)
            RETURNING *
            """,
            data.name,
            data.execution_time,
            data.webhook_url,
            json.dumps(data.payload),
            data.recurrence.value,
            data.cron_expression,
            data.max_retries,
        )
    return _to_task_response(row)


async def list_tasks(
    status: Optional[TaskStatus] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[TaskResponse]:
    async with get_connection() as conn:
        if status:
            rows = await conn.fetch(
                "SELECT * FROM tasks WHERE status = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3",
                status.value, limit, offset,
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT $1 OFFSET $2",
                limit, offset,
            )
    return [_to_task_response(r) for r in rows]


async def get_task_with_attempts(task_id: UUID) -> TaskDetailResponse:
    async with get_connection() as conn:
        task_row = await conn.fetchrow("SELECT * FROM tasks WHERE id = $1", task_id)
        if not task_row:
            raise NotFoundError(f"task {task_id} not found")
        attempt_rows = await conn.fetch(
            "SELECT * FROM task_attempts WHERE task_id = $1 ORDER BY attempt_number",
            task_id,
        )
    return TaskDetailResponse(
        **_to_task_response(task_row).model_dump(),
        attempts=[_to_attempt_response(r) for r in attempt_rows],
    )


async def cancel_task(task_id: UUID) -> TaskResponse:
    async with get_connection() as conn:
        row = await conn.fetchrow("SELECT status FROM tasks WHERE id = $1", task_id)
        if not row:
            raise NotFoundError(f"task {task_id} not found")

        guard(TaskStatus(row["status"]), TaskStatus.CANCELLED)

        updated = await conn.fetchrow(
            "UPDATE tasks SET status = 'CANCELLED', updated_at = NOW() WHERE id = $1 RETURNING *",
            task_id,
        )
    return _to_task_response(updated)


async def get_task(task_id: UUID) -> Optional[TaskResponse]:
    async with get_connection() as conn:
        row = await conn.fetchrow("SELECT * FROM tasks WHERE id = $1", task_id)
    return _to_task_response(row) if row else None


async def recover_running_tasks() -> int:
    async with get_connection() as conn:
        # close attempt records left open by the previous process
        await conn.execute(
            """
            UPDATE task_attempts
            SET status = 'FAILED'::attempt_status, error_message = 'interrupted by service restart',
                completed_at = NOW(), duration_ms = 0
            WHERE status = 'RUNNING'::attempt_status
            """
        )
        rows = await conn.fetch(
            """
            UPDATE tasks SET
                retry_count = CASE WHEN retry_count < max_retries THEN retry_count + 1 ELSE retry_count END,
                status      = CASE WHEN retry_count < max_retries THEN 'RETRYING'::task_status ELSE 'FAILED'::task_status END,
                updated_at  = NOW()
            WHERE status = 'RUNNING'
            RETURNING id, status
            """
        )
    for row in rows:
        log.warning("task.recovered", task_id=str(row["id"]), new_status=row["status"])
    return len(rows)


async def _transition(task_id: UUID, next_status: TaskStatus) -> None:
    # compute valid predecessors from the state machine — UPDATE checks them atomically, no separate SELECT needed
    valid_from = [s.value for s, allowed in ALLOWED_TRANSITIONS.items() if next_status in allowed]
    async with get_connection() as conn:
        row = await conn.fetchrow(
            "UPDATE tasks SET status = $2, updated_at = NOW() WHERE id = $1 AND status = ANY($3::text[]) RETURNING id",
            task_id, next_status.value, valid_from,
        )
        if row:
            return
        # error path only — distinguish not-found from invalid transition
        current = await conn.fetchrow("SELECT status FROM tasks WHERE id = $1", task_id)
    if not current:
        raise NotFoundError(f"task {task_id} not found")
    raise InvalidTransitionError(
        f"task cannot move from {current['status']} → {next_status.value} "
        f"(valid predecessors: {valid_from or 'none — terminal state'})"
    )


async def mark_running(task_id: UUID) -> None:
    await _transition(task_id, TaskStatus.RUNNING)


async def mark_success(task_id: UUID) -> None:
    await _transition(task_id, TaskStatus.SUCCESS)


async def mark_failed(task_id: UUID) -> None:
    await _transition(task_id, TaskStatus.FAILED)


async def mark_retrying(task_id: UUID) -> None:
    await _transition(task_id, TaskStatus.RETRYING)


async def increment_retry_count(task_id: UUID) -> int:
    # atomic — returns the new count so the caller can compute the next delay
    async with get_connection() as conn:
        row = await conn.fetchrow(
            "UPDATE tasks SET retry_count = retry_count + 1, updated_at = NOW() WHERE id = $1 RETURNING retry_count",
            task_id,
        )
    return row["retry_count"]


async def create_attempt(task_id: UUID, attempt_number: int) -> UUID:
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO task_attempts (task_id, attempt_number, started_at, status)
            VALUES ($1, $2, NOW(), 'RUNNING')
            RETURNING id
            """,
            task_id, attempt_number,
        )
    return row["id"]


async def complete_attempt(
    attempt_id: UUID, http_status: int, response_body: str, duration_ms: int,
) -> None:
    async with get_connection() as conn:
        await conn.execute(
            """
            UPDATE task_attempts
            SET status = 'SUCCESS', http_status = $2, response_body = $3,
                duration_ms = $4, completed_at = NOW()
            WHERE id = $1
            """,
            attempt_id, http_status, response_body, duration_ms,
        )


async def fail_attempt(attempt_id: UUID, error_message: str, duration_ms: int) -> None:
    async with get_connection() as conn:
        await conn.execute(
            """
            UPDATE task_attempts
            SET status = 'FAILED', error_message = $2, duration_ms = $3, completed_at = NOW()
            WHERE id = $1
            """,
            attempt_id, error_message, duration_ms,
        )
