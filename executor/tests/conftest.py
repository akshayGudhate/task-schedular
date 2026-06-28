import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# must be set before app modules are imported
os.environ.setdefault(
    "EXECUTOR_DB_URL", "postgresql://test:test@localhost/test_executor"
)

from app.models.execution import ExecutionStatus, StatusResponse  # noqa: E402


def make_status_response(**kwargs) -> StatusResponse:
    now = datetime.now(timezone.utc)
    return StatusResponse(
        **{
            "id": str(uuid.uuid4()),
            "task_id": str(uuid.uuid4()),
            "attempt_id": str(uuid.uuid4()),
            "status": ExecutionStatus.COMPLETED,
            "started_at": now,
            "completed_at": now,
            "duration_ms": 12,
            "result": {"done": True},
            "error_message": None,
            **kwargs,
        }
    )


@pytest.fixture
async def client():
    with (
        patch("app.main.create_pool", new_callable=AsyncMock),
        patch("app.main.close_pool", new_callable=AsyncMock),
    ):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c
