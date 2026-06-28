"""Executor API endpoint tests.

execution_service is mocked so no DB needed.
Background tasks (_run_async) are also mocked to avoid real async delays in tests.
The `client` fixture comes from conftest.py.
"""

import uuid
from unittest.mock import AsyncMock, patch
from app.core.errors import NotFoundError
from app.models.execution import ExecutionStatus
from tests.conftest import make_status_response

_TASK_ID = str(uuid.uuid4())
_ATTEMPT_ID = str(uuid.uuid4())
_BASE_BODY = {"task_id": _TASK_ID, "attempt_id": _ATTEMPT_ID, "payload": {}}


# ── POST /send-welcome (sync 200) ──────────────────────────────────────────────


class TestSendWelcome:
    async def test_returns_200_with_completed_status(self, client):
        exec_id = uuid.uuid4()
        with (
            patch(
                "app.services.execution_service.create_execution",
                new_callable=AsyncMock,
                return_value=exec_id,
            ),
            patch(
                "app.services.execution_service.mark_processing", new_callable=AsyncMock
            ),
            patch("app.services.execution_service.complete", new_callable=AsyncMock),
        ):
            resp = await client.post("/send-welcome", json=_BASE_BODY)
        assert resp.status_code == 200
        assert resp.json()["status"] == "COMPLETED"

    async def test_payload_email_appears_in_result(self, client):
        exec_id = uuid.uuid4()
        body = {
            **_BASE_BODY,
            "payload": {"email": "user@example.com", "template": "welcome"},
        }
        with (
            patch(
                "app.services.execution_service.create_execution",
                new_callable=AsyncMock,
                return_value=exec_id,
            ),
            patch(
                "app.services.execution_service.mark_processing", new_callable=AsyncMock
            ),
            patch("app.services.execution_service.complete", new_callable=AsyncMock),
        ):
            resp = await client.post("/send-welcome", json=body)
        assert resp.json()["result"]["recipient"] == "user@example.com"
        assert resp.json()["result"]["template"] == "welcome"

    async def test_missing_email_falls_back_to_unknown(self, client):
        exec_id = uuid.uuid4()
        with (
            patch(
                "app.services.execution_service.create_execution",
                new_callable=AsyncMock,
                return_value=exec_id,
            ),
            patch(
                "app.services.execution_service.mark_processing", new_callable=AsyncMock
            ),
            patch("app.services.execution_service.complete", new_callable=AsyncMock),
        ):
            resp = await client.post("/send-welcome", json=_BASE_BODY)
        assert resp.json()["result"]["recipient"] == "unknown"


# ── POST /security-alert (sync 200) ───────────────────────────────────────────


class TestSecurityAlert:
    async def test_returns_200_with_completed_status(self, client):
        exec_id = uuid.uuid4()
        with (
            patch(
                "app.services.execution_service.create_execution",
                new_callable=AsyncMock,
                return_value=exec_id,
            ),
            patch(
                "app.services.execution_service.mark_processing", new_callable=AsyncMock
            ),
            patch("app.services.execution_service.complete", new_callable=AsyncMock),
        ):
            resp = await client.post("/security-alert", json=_BASE_BODY)
        assert resp.status_code == 200
        assert resp.json()["result"]["alert_sent"] is True

    async def test_severity_in_payload_appears_in_result(self, client):
        exec_id = uuid.uuid4()
        body = {**_BASE_BODY, "payload": {"severity": "high"}}
        with (
            patch(
                "app.services.execution_service.create_execution",
                new_callable=AsyncMock,
                return_value=exec_id,
            ),
            patch(
                "app.services.execution_service.mark_processing", new_callable=AsyncMock
            ),
            patch("app.services.execution_service.complete", new_callable=AsyncMock),
        ):
            resp = await client.post("/security-alert", json=body)
        assert resp.json()["result"]["severity"] == "high"

    async def test_notified_channels_in_result(self, client):
        exec_id = uuid.uuid4()
        with (
            patch(
                "app.services.execution_service.create_execution",
                new_callable=AsyncMock,
                return_value=exec_id,
            ),
            patch(
                "app.services.execution_service.mark_processing", new_callable=AsyncMock
            ),
            patch("app.services.execution_service.complete", new_callable=AsyncMock),
        ):
            resp = await client.post("/security-alert", json=_BASE_BODY)
        channels = resp.json()["result"]["notified_channels"]
        assert "slack" in channels
        assert "email" in channels


# ── POST /notify-admin (async 202) ────────────────────────────────────────────


class TestNotifyAdmin:
    async def test_returns_202_with_queued_status(self, client):
        exec_id = uuid.uuid4()
        with (
            patch(
                "app.services.execution_service.create_execution",
                new_callable=AsyncMock,
                return_value=exec_id,
            ),
            patch("app.api.webhooks._run_async", new_callable=AsyncMock),
        ):
            resp = await client.post("/notify-admin", json=_BASE_BODY)
        assert resp.status_code == 202
        assert resp.json()["status"] == "QUEUED"

    async def test_check_url_contains_execution_id(self, client):
        exec_id = uuid.uuid4()
        with (
            patch(
                "app.services.execution_service.create_execution",
                new_callable=AsyncMock,
                return_value=exec_id,
            ),
            patch("app.api.webhooks._run_async", new_callable=AsyncMock),
        ):
            resp = await client.post("/notify-admin", json=_BASE_BODY)
        assert str(exec_id) in resp.json()["check_url"]

    async def test_result_is_null_in_202_response(self, client):
        exec_id = uuid.uuid4()
        with (
            patch(
                "app.services.execution_service.create_execution",
                new_callable=AsyncMock,
                return_value=exec_id,
            ),
            patch("app.api.webhooks._run_async", new_callable=AsyncMock),
        ):
            resp = await client.post("/notify-admin", json=_BASE_BODY)
        assert resp.json()["result"] is None


# ── POST /daily-report (async 202) ────────────────────────────────────────────


class TestDailyReport:
    async def test_returns_202_with_queued_status(self, client):
        exec_id = uuid.uuid4()
        with (
            patch(
                "app.services.execution_service.create_execution",
                new_callable=AsyncMock,
                return_value=exec_id,
            ),
            patch("app.api.webhooks._run_async", new_callable=AsyncMock),
        ):
            resp = await client.post("/daily-report", json=_BASE_BODY)
        assert resp.status_code == 202
        assert resp.json()["status"] == "QUEUED"

    async def test_check_url_contains_execution_id(self, client):
        exec_id = uuid.uuid4()
        with (
            patch(
                "app.services.execution_service.create_execution",
                new_callable=AsyncMock,
                return_value=exec_id,
            ),
            patch("app.api.webhooks._run_async", new_callable=AsyncMock),
        ):
            resp = await client.post("/daily-report", json=_BASE_BODY)
        assert str(exec_id) in resp.json()["check_url"]


# ── GET /status/{execution_id} ─────────────────────────────────────────────────


class TestStatus:
    async def test_returns_completed_status(self, client):
        exec_id = uuid.uuid4()
        sr = make_status_response(id=str(exec_id), status=ExecutionStatus.COMPLETED)
        with patch(
            "app.services.execution_service.get_execution",
            new_callable=AsyncMock,
            return_value=sr,
        ):
            resp = await client.get(f"/status/{exec_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "COMPLETED"

    async def test_returns_processing_status(self, client):
        exec_id = uuid.uuid4()
        sr = make_status_response(
            id=str(exec_id),
            status=ExecutionStatus.PROCESSING,
            completed_at=None,
            duration_ms=None,
            result=None,
        )
        with patch(
            "app.services.execution_service.get_execution",
            new_callable=AsyncMock,
            return_value=sr,
        ):
            resp = await client.get(f"/status/{exec_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "PROCESSING"

    async def test_unknown_id_returns_404(self, client):
        with patch(
            "app.services.execution_service.get_execution",
            new_callable=AsyncMock,
            side_effect=NotFoundError("execution not found"),
        ):
            resp = await client.get(f"/status/{uuid.uuid4()}")
        assert resp.status_code == 404

    async def test_invalid_uuid_returns_422(self, client):
        resp = await client.get("/status/not-a-uuid")
        assert resp.status_code == 422


# ── GET /health ────────────────────────────────────────────────────────────────


class TestHealth:
    async def test_health_returns_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
