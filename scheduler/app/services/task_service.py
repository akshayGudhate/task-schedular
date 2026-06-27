from __future__ import annotations

import json
from typing import Optional
from uuid import UUID

import asyncpg

from app.core.errors import NotFoundError
from app.db.database import get_connection
from app.models.task import (
    AttemptStatus,
    TaskAttemptResponse,
    TaskCreate,
    TaskDetailResponse,
    TaskResponse,
    TaskStatus,
)
from app.state_machine import guard


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
