from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.models.task import TaskCreate, TaskDetailResponse, TaskResponse, TaskStatus
import app.services.task_service as svc

router = APIRouter()

_404 = {status.HTTP_404_NOT_FOUND: {"description": "Task not found"}}
_409 = {status.HTTP_409_CONFLICT:  {"description": "Transition not allowed by the state machine"}}
_422 = {status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation error — invalid field value"}}


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=TaskResponse,
    summary="Create a task",
    description="""
Schedule a new task for webhook execution.

- `execution_time` must be a future UTC datetime
- `webhook_url` must start with `http://` or `https://`
- `recurrence: CUSTOM_CRON` requires a valid `cron_expression`
- `max_retries` defaults to 3; set to 0 to disable retries
""",
    responses=_422,
)
async def create_task(body: TaskCreate) -> TaskResponse:
    return await svc.create_task(body)


@router.get(
    "",
    response_model=list[TaskResponse],
    summary="List tasks",
    description="Returns all tasks ordered by creation time (newest first). Filter by `status` and paginate with `limit` / `offset`.",
)
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    limit:  int = Query(50, ge=1, le=200, description="Max results to return"),
    offset: int = Query(0,  ge=0,         description="Number of results to skip"),
) -> list[TaskResponse]:
    return await svc.list_tasks(status=status, limit=limit, offset=offset)


@router.get(
    "/{task_id}",
    response_model=TaskDetailResponse,
    summary="Get task with attempt history",
    description="Returns the task plus every attempt recorded — use this to inspect retry history and HTTP responses.",
    responses=_404,
)
async def get_task(task_id: UUID) -> TaskDetailResponse:
    return await svc.get_task_with_attempts(task_id)


@router.patch(
    "/{task_id}/cancel",
    response_model=TaskResponse,
    summary="Cancel a task",
    description="Moves the task to `CANCELLED`. Only allowed from `CREATED` or `PENDING` — returns 409 if the task is already running, done, or failed.",
    responses={**_404, **_409},
)
async def cancel_task(task_id: UUID) -> TaskResponse:
    return await svc.cancel_task(task_id)
