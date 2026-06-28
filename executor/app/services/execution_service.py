from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import status

from app.core.errors import NotFoundError
from app.db.database import get_connection
from app.models.execution import ExecutionStatus, StatusResponse


def _to_status_response(row: asyncpg.Record) -> StatusResponse:
    result = None
    if row["response_body"]:
        try:
            result = json.loads(row["response_body"])
        except json.JSONDecodeError:
            result = {"raw": row["response_body"]}
    return StatusResponse(
        id=str(row["id"]),
        task_id=str(row["task_id"]),
        attempt_id=str(row["attempt_id"]),
        status=ExecutionStatus(row["status"]),
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        duration_ms=row["duration_ms"],
        result=result,
        error_message=row["error_message"],
    )


async def create_execution(
    task_id: UUID,
    attempt_id: UUID,
    webhook_url: str,
    payload: dict[str, Any],
) -> UUID:
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO executions (task_id, attempt_id, webhook_url, payload)
            VALUES ($1, $2, $3, $4::jsonb)
            ON CONFLICT (attempt_id) DO NOTHING
            RETURNING id
            """,
            task_id, attempt_id, webhook_url, json.dumps(payload),
        )
        if row:
            return row["id"]
        # duplicate attempt_id from a scheduler retry — return the existing execution id
        return await conn.fetchval("SELECT id FROM executions WHERE attempt_id = $1", attempt_id)


async def mark_processing(execution_id: UUID) -> None:
    async with get_connection() as conn:
        await conn.execute(
            "UPDATE executions SET status = 'PROCESSING', updated_at = NOW() WHERE id = $1",
            execution_id,
        )


async def complete(execution_id: UUID, result: dict[str, Any], duration_ms: int) -> None:
    async with get_connection() as conn:
        await conn.execute(
            """
            UPDATE executions
            SET status = 'COMPLETED', http_status = $4, completed_at = NOW(),
                response_body = $2, duration_ms = $3, updated_at = NOW()
            WHERE id = $1
            """,
            execution_id, json.dumps(result), duration_ms, status.HTTP_200_OK,
        )


async def fail(execution_id: UUID, error: str, duration_ms: int) -> None:
    async with get_connection() as conn:
        await conn.execute(
            """
            UPDATE executions
            SET status = 'FAILED', completed_at = NOW(),
                error_message = $2, duration_ms = $3, updated_at = NOW()
            WHERE id = $1
            """,
            execution_id, error, duration_ms,
        )


async def get_execution(execution_id: UUID) -> StatusResponse:
    async with get_connection() as conn:
        row = await conn.fetchrow("SELECT * FROM executions WHERE id = $1", execution_id)
    if not row:
        raise NotFoundError(f"execution {execution_id} not found")
    return _to_status_response(row)
