"""State machine tests — pure unit, no DB or HTTP."""

from app.models.task import TaskStatus
from app.state_machine import ALLOWED_TRANSITIONS


def test_every_status_has_an_entry():
    assert set(ALLOWED_TRANSITIONS.keys()) == set(TaskStatus)


def test_terminal_states_have_no_outgoing_transitions():
    for status in (TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.CANCELLED):
        assert ALLOWED_TRANSITIONS[status] == set(), f"{status} must be terminal"


def test_cancel_allowed_from_created_and_pending_only():
    can_cancel = {
        s
        for s, targets in ALLOWED_TRANSITIONS.items()
        if TaskStatus.CANCELLED in targets
    }
    assert can_cancel == {TaskStatus.CREATED, TaskStatus.PENDING}


def test_running_reaches_all_terminal_outcomes():
    from_running = ALLOWED_TRANSITIONS[TaskStatus.RUNNING]
    assert TaskStatus.SUCCESS in from_running
    assert TaskStatus.FAILED in from_running
    assert TaskStatus.RETRYING in from_running


def test_retrying_can_only_move_to_running():
    assert ALLOWED_TRANSITIONS[TaskStatus.RETRYING] == {TaskStatus.RUNNING}


def test_created_moves_to_pending_before_running():
    assert TaskStatus.PENDING in ALLOWED_TRANSITIONS[TaskStatus.CREATED]
    assert TaskStatus.RUNNING in ALLOWED_TRANSITIONS[TaskStatus.CREATED]


def test_no_backwards_transitions():
    # once a task moves forward in its lifecycle it cannot return to CREATED or PENDING
    for status in (
        TaskStatus.RUNNING,
        TaskStatus.RETRYING,
        TaskStatus.SUCCESS,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    ):
        assert TaskStatus.CREATED not in ALLOWED_TRANSITIONS[status]
        assert TaskStatus.PENDING not in ALLOWED_TRANSITIONS[status]
