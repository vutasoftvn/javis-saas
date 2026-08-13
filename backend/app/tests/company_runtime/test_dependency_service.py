from unittest.mock import MagicMock
import pytest

from app.core.snowflake import generate_snowflake_id
from app.modules.tasks.models import Task, TaskDependency
from app.modules.company_runtime.dependency_service import DependencyService


def test_dependency_cycle_detection():
    # Linear: 1 -> 2 -> 3
    assert DependencyService.detect_cycles([(2, 1), (3, 2)]) is False

    # Cycle: 1 -> 2 -> 3 -> 1
    assert DependencyService.detect_cycles([(2, 1), (3, 2), (1, 3)]) is True

    # Diamond DAG: 1 -> 2, 1 -> 3, 2 -> 4, 3 -> 4
    assert DependencyService.detect_cycles([(2, 1), (3, 1), (4, 2), (4, 3)]) is False


def test_add_dependency_and_self_dependency_rejected():
    db = MagicMock()
    task_id = generate_snowflake_id()

    # Self-dependency error
    with pytest.raises(ValueError, match="cannot depend on itself"):
        DependencyService.add_dependency(db, task_id, task_id)


def test_get_ready_tasks_evaluation():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    t1_id, t2_id, t3_id = generate_snowflake_id(), generate_snowflake_id(), generate_snowflake_id()

    t1 = Task(id=t1_id, workspace_id=ws_id, title="Legal Terms", status="done")
    t2 = Task(id=t2_id, workspace_id=ws_id, title="Tech Landing", status="in_progress")
    t3 = Task(id=t3_id, workspace_id=ws_id, title="Marketing Launch", status="todo")

    # t3 depends on t1 (done) and t2 (in_progress)
    dep1 = TaskDependency(task_id=t3_id, depends_on_task_id=t1_id, status="SATISFIED")
    dep2 = TaskDependency(task_id=t3_id, depends_on_task_id=t2_id, status="PENDING")

    db.query.return_value.filter.return_value.all.side_effect = [
        [t3],          # list tasks
        [dep1, dep2],  # deps for t3
    ]
    db.query.return_value.filter.return_value.first.side_effect = [t1, t2]

    ready = DependencyService.get_ready_tasks(db, ws_id)
    # Since t2 is still in_progress, t3 is not ready yet
    assert len(ready) == 0
