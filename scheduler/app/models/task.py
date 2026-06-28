from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class TaskStatus(str, Enum):
    CREATED = "CREATED"  # just landed in the db, waiting for its scheduled time
    PENDING = "PENDING"  # picked up by the scheduler, about to fire
    RUNNING = "RUNNING"  # webhook is in-flight (or being polled for async tasks)
    RETRYING = "RETRYING"  # failed but has retries left — sitting out the backoff delay
    SUCCESS = "SUCCESS"  # got a clean 2xx, we're done
    FAILED = "FAILED"  # exhausted all retries, giving up
    CANCELLED = "CANCELLED"  # user killed it before it ever ran


class RecurrenceType(str, Enum):
    NONE = "NONE"  # one-shot, fire and forget
    HOURLY = "HOURLY"  # reschedule every hour after success
    DAILY = "DAILY"  # reschedule every day after success
    CUSTOM_CRON = (
        "CUSTOM_CRON"  # uses cron_expression — next run computed via CronTrigger
    )


class AttemptStatus(str, Enum):
    RUNNING = "RUNNING"  # http request is in-flight
    SUCCESS = "SUCCESS"  # got a clean 2xx response
    FAILED = "FAILED"  # non-2xx, timeout, or connection error


class TaskCreate(BaseModel):
    name: str
    execution_time: datetime
    webhook_url: str
    payload: dict[str, Any] = Field(default_factory=dict)
    recurrence: RecurrenceType = RecurrenceType.NONE
    cron_expression: Optional[str] = None
    max_retries: int = Field(default=3, ge=0)

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()

    @field_validator("webhook_url")
    @classmethod
    def must_be_http(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("must start with http:// or https://")
        return v

    @field_validator("execution_time")
    @classmethod
    def must_be_future(cls, v: datetime) -> datetime:
        now = datetime.now(tz=v.tzinfo or timezone.utc)
        if v <= now:
            raise ValueError("must be a future datetime")
        return v

    @model_validator(mode="after")
    def validate_cron(self) -> TaskCreate:
        if self.recurrence == RecurrenceType.CUSTOM_CRON and not self.cron_expression:
            raise ValueError("cron_expression required when recurrence is CUSTOM_CRON")
        if self.recurrence != RecurrenceType.CUSTOM_CRON and self.cron_expression:
            raise ValueError(
                "cron_expression only allowed when recurrence is CUSTOM_CRON"
            )
        return self


class TaskAttemptResponse(BaseModel):
    id: str
    attempt_number: int
    started_at: datetime
    completed_at: Optional[datetime]
    http_status: Optional[int]
    response_body: Optional[str]
    duration_ms: Optional[int]
    status: AttemptStatus
    error_message: Optional[str]


class TaskResponse(BaseModel):
    id: str
    name: str
    execution_time: datetime
    webhook_url: str
    payload: dict
    recurrence: RecurrenceType
    cron_expression: Optional[str]
    status: TaskStatus
    max_retries: int
    retry_count: int
    parent_task_id: Optional[str]
    created_at: datetime
    updated_at: datetime


class TaskDetailResponse(TaskResponse):
    attempts: list[TaskAttemptResponse] = []
