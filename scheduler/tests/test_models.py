"""TaskCreate validator tests — pure unit, no DB or HTTP."""

from datetime import datetime, timedelta, timezone

import pytest  # pyright: ignore[reportMissingImports]
from pydantic import ValidationError

from app.models.task import RecurrenceType, TaskCreate

_FUTURE = datetime.now(timezone.utc) + timedelta(hours=1)
_VALID = {
    "name": "Test",
    "execution_time": _FUTURE,
    "webhook_url": "http://example.com/hook",
}


# ── name ──────────────────────────────────────────────────────────────────────


def test_valid_task_creates_with_defaults():
    t = TaskCreate(**_VALID)
    assert t.name == "Test"
    assert t.recurrence == RecurrenceType.NONE
    assert t.max_retries == 3
    assert t.cron_expression is None


def test_name_is_stripped():
    t = TaskCreate(**{**_VALID, "name": "  hello  "})
    assert t.name == "hello"


def test_empty_name_rejected():
    with pytest.raises(ValidationError, match="name cannot be empty"):
        TaskCreate(**{**_VALID, "name": "   "})


# ── webhook_url ────────────────────────────────────────────────────────────────


def test_https_url_accepted():
    t = TaskCreate(**{**_VALID, "webhook_url": "https://secure.example.com/hook"})
    assert t.webhook_url.startswith("https://")


def test_non_http_url_rejected():
    with pytest.raises(ValidationError):
        TaskCreate(**{**_VALID, "webhook_url": "ftp://example.com/hook"})


def test_bare_string_url_rejected():
    with pytest.raises(ValidationError):
        TaskCreate(**{**_VALID, "webhook_url": "not-a-url"})


# ── execution_time ─────────────────────────────────────────────────────────────


def test_past_time_rejected():
    past = datetime.now(timezone.utc) - timedelta(seconds=1)
    with pytest.raises(ValidationError, match="future"):
        TaskCreate(**{**_VALID, "execution_time": past})


def test_future_time_accepted():
    future = datetime.now(timezone.utc) + timedelta(days=1)
    t = TaskCreate(**{**_VALID, "execution_time": future})
    assert t.execution_time == future


# ── max_retries ────────────────────────────────────────────────────────────────


def test_max_retries_zero_allowed():
    t = TaskCreate(**{**_VALID, "max_retries": 0})
    assert t.max_retries == 0


def test_negative_max_retries_rejected():
    with pytest.raises(ValidationError):
        TaskCreate(**{**_VALID, "max_retries": -1})


# ── recurrence / cron_expression ──────────────────────────────────────────────


def test_custom_cron_requires_expression():
    with pytest.raises(ValidationError, match="cron_expression"):
        TaskCreate(**{**_VALID, "recurrence": RecurrenceType.CUSTOM_CRON})


def test_cron_expression_forbidden_for_daily():
    with pytest.raises(ValidationError):
        TaskCreate(
            **{
                **_VALID,
                "recurrence": RecurrenceType.DAILY,
                "cron_expression": "*/5 * * * *",
            }
        )


def test_cron_expression_forbidden_for_none():
    with pytest.raises(ValidationError):
        TaskCreate(**{**_VALID, "cron_expression": "*/5 * * * *"})


def test_custom_cron_with_expression_accepted():
    t = TaskCreate(
        **{
            **_VALID,
            "recurrence": RecurrenceType.CUSTOM_CRON,
            "cron_expression": "*/30 * * * *",
        }
    )
    assert t.cron_expression == "*/30 * * * *"
