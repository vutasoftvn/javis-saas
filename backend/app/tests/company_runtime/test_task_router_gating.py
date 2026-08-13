"""Regression tests for the state-machine gate on PUT /tasks/{id}.

The V13.1 plan requires status changes to route through TaskStateService only
when the flag is on AND the task carries a Work Contract (a linked Outcome).
Routing every status change through the guard unconditionally silently breaks
the plain Kanban board: tasks_view.dart has todo / in_progress / done columns
with free drag-and-drop, but `todo -> done` is not a legal transition, so the
ordinary "drag a card straight to Done" gesture would start failing with an
HTTP 400 even with every V13.1 flag off.
"""
from unittest.mock import MagicMock, patch

from app.core.snowflake import generate_snowflake_id
from app.modules.tasks.models import Task
from app.modules.tasks.router import _uses_state_machine


def _task(status: str = "todo") -> Task:
    return Task(
        id=generate_snowflake_id(),
        workspace_id=generate_snowflake_id(),
        title="Kanban card",
        status=status,
    )


def test_flag_off_bypasses_state_machine():
    task = _task()
    with patch("app.core.feature_flags.is_enabled", return_value=False):
        assert _uses_state_machine(MagicMock(), task, task.workspace_id) is False


def test_flag_on_without_linked_outcome_bypasses_state_machine():
    """A task with no Work Contract keeps pre-V13.1 behaviour even with the
    flag on - the contract is what makes the work state-machine governed."""
    task = _task()
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with patch("app.core.feature_flags.is_enabled", return_value=True):
        assert _uses_state_machine(db, task, task.workspace_id) is False


def test_flag_on_with_linked_outcome_uses_state_machine():
    task = _task()
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = (generate_snowflake_id(),)

    with patch("app.core.feature_flags.is_enabled", return_value=True):
        assert _uses_state_machine(db, task, task.workspace_id) is True


def test_kanban_shortcut_is_illegal_only_under_the_state_machine():
    """Documents why the gate matters: todo -> done is exactly the transition
    the Kanban board allows and the state machine rejects."""
    from app.modules.company_runtime.state_service import TaskStateService

    assert TaskStateService.can_transition("todo", "done") is False
    assert TaskStateService.can_transition("todo", "in_progress") is True
