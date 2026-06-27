from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel


# attempt status
class AttemptStatus(str, Enum):
    RUNNING = "RUNNING"  # http request is in-flight
    SUCCESS = "SUCCESS"  # got a clean response
    FAILED  = "FAILED"   # non-2xx, timeout, or connection error


# task attempt model
class TaskAttempt(BaseModel):
    id:             str
    task_id:        str
    attempt_number: int       # incremented with each retry
    started_at:     datetime
    completed_at:   Optional[datetime]  # null while the request is in-flight
    http_status:    Optional[int]       # null if we never got a response
    response_body:  Optional[str]       # enough to debug
    duration_ms:    Optional[int]       # time from request start to response received
    status:         AttemptStatus
    error_message:  Optional[str]       # not on http errors

    # needed for ORM hydration
    model_config = {"from_attributes": True}
