"""Dependency Cycle Validator for Tasks (§b2 §6.2, §P0.5).

Ensures that task dependencies form a Directed Acyclic Graph (DAG)
and strictly rejects cyclic relationships (e.g. A -> B -> A).
"""

from typing import List, Set, Dict
from sqlalchemy.orm import Session
from business_core.tasks.models import TaskDependency


class DependencyCycleError(ValueError):
    """Raised when adding a task dependency would create a cycle."""
    pass


def validate_no_dependency_cycle(
    db: Session,
    task_id: int,
    depends_on_task_id: int,
) -> None:
    """Validate that adding `task_id depends on depends_on_task_id` does not create a cycle.

    Self-dependencies (task_id == depends_on_task_id) are rejected immediately.
    """
    if task_id == depends_on_task_id:
        raise DependencyCycleError(f"Self-dependency detected: Task {task_id} cannot depend on itself.")

    # Load all existing dependencies
    deps: List[TaskDependency] = db.query(TaskDependency).all()

    # Build adjacency list: target -> list of sources (or child -> parents)
    # If task_id depends on depends_on_task_id, there is a directed edge: depends_on_task_id -> task_id
    adj: Dict[int, List[int]] = {}
    for d in deps:
        adj.setdefault(d.depends_on_task_id, []).append(d.task_id)

    # Add candidate edge
    adj.setdefault(depends_on_task_id, []).append(task_id)

    # Run DFS from task_id to see if we can reach depends_on_task_id
    visited: Set[int] = set()
    stack: Set[int] = set()

    def has_cycle(node: int) -> bool:
        visited.add(node)
        stack.add(node)

        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                if has_cycle(neighbor):
                    return True
            elif neighbor in stack:
                return True

        stack.remove(node)
        return False

    for node in list(adj.keys()):
        if node not in visited:
            if has_cycle(node):
                raise DependencyCycleError(
                    f"Dependency cycle detected when linking Task {task_id} to depend on Task {depends_on_task_id}."
                )
