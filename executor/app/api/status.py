from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from app.models.execution import StatusResponse
import app.services.execution_service as svc

router = APIRouter()

_404 = {status.HTTP_404_NOT_FOUND: {"description": "Execution record not found"}}


@router.get(
    "/status/{execution_id}",
    response_model=StatusResponse,
    summary="Poll execution status",
    description="""
Poll this endpoint after receiving a `202` from an async webhook.

Terminal states: `COMPLETED` or `FAILED`. Stop polling when either is reached.

| Status | Meaning |
|---|---|
| `RECEIVED` | Execution record created, background task not yet started |
| `PROCESSING` | Background task is actively running |
| `COMPLETED` | Finished successfully — `result` field is populated |
| `FAILED` | Errored or timed out — `error_message` field is populated |
""",
    responses=_404,
)
async def get_status(execution_id: UUID) -> StatusResponse:
    return await svc.get_execution(execution_id)
