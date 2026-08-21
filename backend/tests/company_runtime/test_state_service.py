from unittest.mock import MagicMock
import pytest

from core.snowflake import generate_snowflake_id
from founder_os.tasks.models import Task
from platform_core.license.state_service import TaskStateService


def test_task_state_transitions_legal():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    task = Task(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        title="Implement OAuth",
        status="todo",
    )

    # todo -> in_progress
    updated = TaskStateService.transition(db, task, "in_progress", actor_id=1, reason="Starting work")
    assert updated.status == "in_progress"
    assert db.commit.called

    # in_progress -> waiting_approval
    updated = TaskStateService.transition(db, task, "waiting_approval", actor_id=1, reason="Needs review")
    assert updated.status == "waiting_approval"

    # waiting_approval -> done
    updated = TaskStateService.transition(db, task, "done", actor_id=1, reason="Approved")
    assert updated.status == "done"

    # done -> in_progress (reopen / rework)
    updated = TaskStateService.transition(db, task, "in_progress", actor_id=1, reason="Rework required")
    assert updated.status == "in_progress"


def test_task_state_transition_illegal_raises():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    task = Task(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        title="Direct jump task",
        status="todo",
    )

    # todo -> done directly is illegal without going through in_progress/review
    with pytest.raises(ValueError, match="Illegal state transition"):
        TaskStateService.transition(db, task, "done", actor_id=1)


def test_task_state_transition_invalid_status_raises():
    db = MagicMock()
    task = Task(
        id=generate_snowflake_id(),
        workspace_id=generate_snowflake_id(),
        title="Bogus status",
        status="todo",
    )

    with pytest.raises(ValueError, match="Invalid target status"):
        TaskStateService.transition(db, task, "non_existent_status")
