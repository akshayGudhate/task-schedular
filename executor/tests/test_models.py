"""Executor model tests — pure unit, no DB or HTTP."""

import uuid

import pytest
from pydantic import ValidationError

from app.models.execution import ExecutionRequest, ExecutionStatus, WebhookResponse


# ── ExecutionRequest ───────────────────────────────────────────────────────────


def test_valid_execution_request():
    req = ExecutionRequest(
        task_id=uuid.uuid4(),
        attempt_id=uuid.uuid4(),
        payload={"key": "value"},
    )
    assert req.payload == {"key": "value"}


def test_payload_defaults_to_empty_dict():
    req = ExecutionRequest(task_id=uuid.uuid4(), attempt_id=uuid.uuid4())
    assert req.payload == {}


def test_task_id_must_be_uuid():
    with pytest.raises(ValidationError):
        ExecutionRequest(task_id="not-a-uuid", attempt_id=uuid.uuid4())


def test_attempt_id_must_be_uuid():
    with pytest.raises(ValidationError):
        ExecutionRequest(task_id=uuid.uuid4(), attempt_id="not-a-uuid")


# ── ExecutionStatus ────────────────────────────────────────────────────────────


def test_execution_status_values():
    assert ExecutionStatus.RECEIVED == "RECEIVED"
    assert ExecutionStatus.PROCESSING == "PROCESSING"
    assert ExecutionStatus.COMPLETED == "COMPLETED"
    assert ExecutionStatus.FAILED == "FAILED"


# ── WebhookResponse ────────────────────────────────────────────────────────────


def test_sync_response_has_no_check_url():
    r = WebhookResponse(
        execution_id=str(uuid.uuid4()), status="COMPLETED", result={"ok": True}
    )
    assert r.check_url is None


def test_async_response_has_check_url_and_no_result():
    exec_id = str(uuid.uuid4())
    r = WebhookResponse(
        execution_id=exec_id,
        status="QUEUED",
        check_url=f"http://executor:8090/status/{exec_id}",
    )
    assert r.result is None
    assert exec_id in r.check_url
