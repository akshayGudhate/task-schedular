"""Scheduler API endpoint tests.

Service layer (task_service, job_runner) is mocked so no DB or APScheduler needed.
The `client` fixture comes from conftest.py.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.core.errors import InvalidTransitionError, NotFoundError
from app.models.task import RecurrenceType, TaskStatus
from tests.conftest import make_detail, make_task

_FUTURE = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()


# ── POST /tasks ────────────────────────────────────────────────────────────────


class TestCreateTask:
    async def test_returns_201_with_created_status(self, client):
        task = make_task()
        with (
            patch(
                "app.services.task_service.create_task",
                new_callable=AsyncMock,
                return_value=task,
            ),
            patch("app.services.job_runner.schedule_task"),
        ):
            resp = await client.post(
                "/tasks",
                json={
                    "name": "Send Welcome Email",
                    "execution_time": _FUTURE,
                    "webhook_url": "http://executor:8090/send-welcome",
                },
            )
        assert resp.status_code == 201
        assert resp.json()["status"] == "CREATED"

    async def test_schedule_task_is_called(self, client):
        task = make_task()
        with (
            patch(
                "app.services.task_service.create_task",
                new_callable=AsyncMock,
                return_value=task,
            ),
            patch("app.services.job_runner.schedule_task") as mock_schedule,
        ):
            await client.post(
                "/tasks",
                json={
                    "name": "Test",
                    "execution_time": _FUTURE,
                    "webhook_url": "http://executor:8090/send-welcome",
                },
            )
        mock_schedule.assert_called_once()

    async def test_past_execution_time_returns_422(self, client):
        past = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
        resp = await client.post(
            "/tasks",
            json={
                "name": "Test",
                "execution_time": past,
                "webhook_url": "http://example.com/hook",
            },
        )
        assert resp.status_code == 422

    async def test_invalid_webhook_url_returns_422(self, client):
        resp = await client.post(
            "/tasks",
            json={
                "name": "Test",
                "execution_time": _FUTURE,
                "webhook_url": "not-a-url",
            },
        )
        assert resp.status_code == 422

    async def test_empty_name_returns_422(self, client):
        resp = await client.post(
            "/tasks",
            json={
                "name": "   ",
                "execution_time": _FUTURE,
                "webhook_url": "http://example.com/hook",
            },
        )
        assert resp.status_code == 422

    async def test_missing_required_fields_returns_422(self, client):
        resp = await client.post("/tasks", json={"name": "Test"})
        assert resp.status_code == 422


# ── GET /tasks ─────────────────────────────────────────────────────────────────


class TestListTasks:
    async def test_returns_200_with_list(self, client):
        tasks = [make_task(), make_task()]
        with patch(
            "app.services.task_service.list_tasks",
            new_callable=AsyncMock,
            return_value=tasks,
        ):
            resp = await client.get("/tasks")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_empty_list_returns_200(self, client):
        with patch(
            "app.services.task_service.list_tasks",
            new_callable=AsyncMock,
            return_value=[],
        ):
            resp = await client.get("/tasks")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_status_filter_is_passed_to_service(self, client):
        with patch(
            "app.services.task_service.list_tasks",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock:
            await client.get("/tasks?status=SUCCESS")
        mock.assert_awaited_once_with(status=TaskStatus.SUCCESS, limit=50, offset=0)

    async def test_pagination_params_are_passed_to_service(self, client):
        with patch(
            "app.services.task_service.list_tasks",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock:
            await client.get("/tasks?limit=10&offset=20")
        mock.assert_awaited_once_with(status=None, limit=10, offset=20)

    async def test_invalid_status_value_returns_422(self, client):
        resp = await client.get("/tasks?status=BOGUS")
        assert resp.status_code == 422

    async def test_limit_above_max_returns_422(self, client):
        resp = await client.get("/tasks?limit=201")
        assert resp.status_code == 422


# ── GET /tasks/{task_id} ───────────────────────────────────────────────────────


class TestGetTask:
    async def test_returns_200_with_attempts_array(self, client):
        task_id = str(uuid.uuid4())
        detail = make_detail(id=task_id)
        with patch(
            "app.services.task_service.get_task_with_attempts",
            new_callable=AsyncMock,
            return_value=detail,
        ):
            resp = await client.get(f"/tasks/{task_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == task_id
        assert "attempts" in body
        assert isinstance(body["attempts"], list)

    async def test_unknown_id_returns_404(self, client):
        with patch(
            "app.services.task_service.get_task_with_attempts",
            new_callable=AsyncMock,
            side_effect=NotFoundError("task not found"),
        ):
            resp = await client.get(f"/tasks/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_invalid_uuid_returns_422(self, client):
        resp = await client.get("/tasks/not-a-uuid")
        assert resp.status_code == 422


# ── PATCH /tasks/{task_id}/cancel ─────────────────────────────────────────────


class TestCancelTask:
    async def test_cancels_created_task_and_returns_200(self, client):
        task_id = str(uuid.uuid4())
        cancelled = make_task(id=task_id, status=TaskStatus.CANCELLED)
        with (
            patch(
                "app.services.task_service.cancel_task",
                new_callable=AsyncMock,
                return_value=cancelled,
            ),
            patch("app.services.job_runner.cancel_job"),
        ):
            resp = await client.patch(f"/tasks/{task_id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "CANCELLED"

    async def test_cancel_job_is_called(self, client):
        task_id = str(uuid.uuid4())
        cancelled = make_task(id=task_id, status=TaskStatus.CANCELLED)
        with (
            patch(
                "app.services.task_service.cancel_task",
                new_callable=AsyncMock,
                return_value=cancelled,
            ),
            patch("app.services.job_runner.cancel_job") as mock_cancel,
        ):
            await client.patch(f"/tasks/{task_id}/cancel")
        mock_cancel.assert_called_once_with(uuid.UUID(task_id))

    async def test_cancel_unknown_task_returns_404(self, client):
        with (
            patch(
                "app.services.task_service.cancel_task",
                new_callable=AsyncMock,
                side_effect=NotFoundError("not found"),
            ),
            patch("app.services.job_runner.cancel_job"),
        ):
            resp = await client.patch(f"/tasks/{uuid.uuid4()}/cancel")
        assert resp.status_code == 404

    async def test_cancel_running_task_returns_409(self, client):
        with (
            patch(
                "app.services.task_service.cancel_task",
                new_callable=AsyncMock,
                side_effect=InvalidTransitionError("cannot cancel RUNNING"),
            ),
            patch("app.services.job_runner.cancel_job"),
        ):
            resp = await client.patch(f"/tasks/{uuid.uuid4()}/cancel")
        assert resp.status_code == 409

    async def test_cancel_success_task_returns_409(self, client):
        with (
            patch(
                "app.services.task_service.cancel_task",
                new_callable=AsyncMock,
                side_effect=InvalidTransitionError("cannot cancel SUCCESS"),
            ),
            patch("app.services.job_runner.cancel_job"),
        ):
            resp = await client.patch(f"/tasks/{uuid.uuid4()}/cancel")
        assert resp.status_code == 409


# ── GET /health ────────────────────────────────────────────────────────────────


class TestHealth:
    async def test_health_returns_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
