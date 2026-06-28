from __future__ import annotations

from app.models.task import TaskStatus

ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.CREATED:   {TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.PENDING:   {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.RUNNING:   {TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.RETRYING},
    TaskStatus.RETRYING:  {TaskStatus.RUNNING},  # only the scheduled retry job can move this forward — no cancel once committed to retry
    TaskStatus.SUCCESS:   set(),
    TaskStatus.FAILED:    set(),
    TaskStatus.CANCELLED: set(),
}
