import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# must be set before app modules are imported so get_settings() (lru_cached) reads them
os.environ.setdefault(
    "SCHEDULER_DB_URL", "postgresql://test:test@localhost/test_scheduler"
)
os.environ.setdefault("EXECUTOR_BASE_URL", "http://executor:8090")

from app.models.task import (
    RecurrenceType,
    TaskDetailResponse,
    TaskResponse,
    TaskStatus,
)  # noqa: E402


def make_task(**kwargs) -> TaskResponse:
    now = datetime.now(timezone.utc)
    return TaskResponse(
        **{
            "id": str(uuid.uuid4()),
            "name": "Test Task",
            "execution_time": now + timedelta(hours=1),
            "webhook_url": "http://executor:8090/send-welcome",
            "payload": {},
            "recurrence": RecurrenceType.NONE,
            "cron_expression": None,
            "status": TaskStatus.CREATED,
            "max_retries": 3,
            "retry_count": 0,
            "parent_task_id": None,
            "created_at": now,
            "updated_at": now,
            **kwargs,
        }
    )


def make_detail(**kwargs) -> TaskDetailResponse:
    return TaskDetailResponse(**make_task(**kwargs).model_dump(), attempts=[])


@pytest.fixture
async def client():
    # patch lifespan dependencies so no real DB or APScheduler is needed
    with (
        patch("app.main.create_pool", new_callable=AsyncMock),
        patch("app.main.close_pool", new_callable=AsyncMock),
        patch("app.main.seed", new_callable=AsyncMock),
        patch("app.services.job_runner.start", new_callable=AsyncMock),
        patch("app.services.job_runner.stop", new_callable=AsyncMock),
    ):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c
