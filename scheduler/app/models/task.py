from __future__ import annotations  # keeps Optional[] working on python 3.9 locally

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


# task status
class TaskStatus(str, Enum):
    CREATED   = "CREATED"   # just landed in the db, waiting for its scheduled time
    PENDING   = "PENDING"   # picked up by the scheduler, about to fire
    RUNNING   = "RUNNING"   # webhook is in-flight (or being polled for async tasks)
    RETRYING  = "RETRYING"  # failed but has retries left — sitting out the backoff delay
    SUCCESS   = "SUCCESS"   # got a clean 2xx, we're done
    FAILED    = "FAILED"    # exhausted all retries, giving up
    CANCELLED = "CANCELLED" # user killed it before it ever ran


# recurrence type
class RecurrenceType(str, Enum):
    NONE        = "NONE"        # one-shot, fire and forget
    HOURLY      = "HOURLY"      # reschedule every hour after success
    DAILY       = "DAILY"       # reschedule every day after success
    CUSTOM_CRON = "CUSTOM_CRON" # uses cron_expression — next run computed via CronTrigger


# task model
class Task(BaseModel):
    id:              str
    name:            str
    execution_time:  datetime
    webhook_url:     str
    payload:         dict           # passed as JSON body when the webhook fires
    recurrence:      RecurrenceType
    cron_expression: Optional[str]  # only set when recurrence is CUSTOM_CRON
    status:          TaskStatus
    max_retries:     int
    retry_count:     int            # incremented on each failed attempt, reset if task clones for next run
    parent_task_id:  Optional[str]  # set on recurring child tasks so you can trace the chain
    created_at:      datetime
    updated_at:      datetime

    # needed for ORM hydration
    model_config = {"from_attributes": True}
