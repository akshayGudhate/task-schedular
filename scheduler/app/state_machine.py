from __future__ import annotations

from app.core.errors import InvalidTransitionError
from app.models.task import TaskStatus

# re-export for convenience
__all__ = ["guard", "InvalidTransitionError", "ALLOWED_TRANSITIONS"]

# allowed transitions
ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.CREATED:   {TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.PENDING:   {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.RUNNING:   {TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.RETRYING},
    TaskStatus.RETRYING:  {TaskStatus.RUNNING},   # only way out is the retry job firing
    TaskStatus.SUCCESS:   set(),
    TaskStatus.FAILED:    set(),
    TaskStatus.CANCELLED: set(),
}

# guard
def guard(current: TaskStatus, next_status: TaskStatus) -> None:
    # the repository calls this before any update — no service can bypass it
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if next_status not in allowed:
        raise InvalidTransitionError(
            f"task cannot move from {current.value} → {next_status.value} "
            f"(allowed from {current.value}: {[s.value for s in allowed] or 'none — terminal state'})"
        )
