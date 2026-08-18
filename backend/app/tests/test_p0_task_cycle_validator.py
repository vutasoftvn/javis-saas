"""Pytest suite for Phase P0: Task Dependency Cycle Validation."""

import pytest
from unittest.mock import MagicMock
from app.founder_os.tasks.cycle_validator import validate_no_dependency_cycle, DependencyCycleError
from app.founder_os.tasks.models import TaskDependency


def test_self_dependency_rejected():
    """A task cannot depend on itself."""
    mock_db = MagicMock()
    with pytest.raises(DependencyCycleError, match="Self-dependency detected"):
        validate_no_dependency_cycle(mock_db, task_id=101, depends_on_task_id=101)


def test_direct_cycle_rejected():
    """A -> B -> A must be rejected."""
    mock_db = MagicMock()
    # Existing: Task 102 depends on Task 101 (101 -> 102)
    mock_dep = MagicMock(spec=TaskDependency)
    mock_dep.task_id = 102
    mock_dep.depends_on_task_id = 101
    mock_db.query.return_value.all.return_value = [mock_dep]

    # Trying to add: Task 101 depends on Task 102
    with pytest.raises(DependencyCycleError, match="Dependency cycle detected"):
        validate_no_dependency_cycle(mock_db, task_id=101, depends_on_task_id=102)


def test_indirect_cycle_rejected():
    """A -> B -> C -> A must be rejected."""
    mock_db = MagicMock()
    # Existing: 101 -> 102 and 102 -> 103
    dep1 = MagicMock(spec=TaskDependency)
    dep1.task_id = 102
    dep1.depends_on_task_id = 101

    dep2 = MagicMock(spec=TaskDependency)
    dep2.task_id = 103
    dep2.depends_on_task_id = 102

    mock_db.query.return_value.all.return_value = [dep1, dep2]

    # Trying to add: Task 101 depends on Task 103
    with pytest.raises(DependencyCycleError, match="Dependency cycle detected"):
        validate_no_dependency_cycle(mock_db, task_id=101, depends_on_task_id=103)


def test_valid_dag_allowed():
    """Valid tree/DAG dependencies must be accepted."""
    mock_db = MagicMock()
    # Existing: 101 -> 102
    dep1 = MagicMock(spec=TaskDependency)
    dep1.task_id = 102
    dep1.depends_on_task_id = 101

    mock_db.query.return_value.all.return_value = [dep1]

    # Adding: Task 103 depends on Task 102 (101 -> 102 -> 103) is valid!
    validate_no_dependency_cycle(mock_db, task_id=103, depends_on_task_id=102)
