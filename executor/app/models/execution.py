from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    RECEIVED   = "RECEIVED"    # webhook received, queued for processing
    PROCESSING = "PROCESSING"  # actively running
    COMPLETED  = "COMPLETED"   # finished successfully
    FAILED     = "FAILED"      # errored out or timed out


class ExecutionRequest(BaseModel):
    task_id:    UUID
    attempt_id: UUID
    payload:    dict = Field(default_factory=dict)


class WebhookResponse(BaseModel):
    execution_id: str
    status:       str
    result:       Optional[dict] = None   # populated on sync 200
    check_url:    Optional[str]  = None   # populated on async 202


class StatusResponse(BaseModel):
    id:            str
    task_id:       str
    attempt_id:    str
    status:        ExecutionStatus
    started_at:    datetime
    completed_at:  Optional[datetime]
    duration_ms:   Optional[int]
    result:        Optional[dict]   # parsed from response_body
    error_message: Optional[str]
