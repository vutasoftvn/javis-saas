from collections import defaultdict
from datetime import datetime
from typing import List, Optional, Set, Dict
from sqlalchemy.orm import Session

from founder_os.tasks.models import Task, TaskDependency


class DependencyService:
    """Dependency DAG engine with cycle detection and downstream re-evaluation."""

    VALID_DEPENDENCY_TYPES = {
        "BLOCKS",
        "REQUIRES_OUTPUT",
        "REQUIRES_APPROVAL",
        "REQUIRES_DECISION",
        "REQUIRES_DOCUMENT",
    }

    @staticmethod
    def detect_cycles(edges: List[tuple[int, int]]) -> bool:
        """Check for cycles in a list of (task_id, depends_on_task_id) pairs using DFS."""
        adj: Dict[int, List[int]] = defaultdict(list)
        nodes: Set[int] = set()
        for u, v in edges:
            adj[v].append(u)  # v (upstream) -> u (downstream)
            nodes.add(u)
            nodes.add(v)

        visited: Dict[int, int] = {}  # 0: unvisited, 1: visiting, 2: visited

        def dfs(node: int) -> bool:
            visited[node] = 1
            for neighbor in adj.get(node, []):
                state = visited.get(neighbor, 0)
                if state == 1:
                    return True  # Cycle found
                if state == 0:
                    if dfs(neighbor):
                        return True
            visited[node] = 2
            return False

        for node in nodes:
            if visited.get(node, 0) == 0:
                if dfs(node):
                    return True
        return False

    @classmethod
    def add_dependency(
        cls,
        db: Session,
        task_id: int,
        depends_on_task_id: int,
        dependency_type: str = "BLOCKS",
    ) -> TaskDependency:
        if task_id == depends_on_task_id:
            raise ValueError("A task cannot depend on itself")

        if dependency_type not in cls.VALID_DEPENDENCY_TYPES:
            raise ValueError(
                f"Invalid dependency_type '{dependency_type}'. Must be one of {cls.VALID_DEPENDENCY_TYPES}"
            )

        # Check existing dependencies for cycle detection
        existing_deps = db.query(TaskDependency).all()
        edges = [(dep.task_id, dep.depends_on_task_id) for dep in existing_deps]
        edges.append((task_id, depends_on_task_id))

        if cls.detect_cycles(edges):
            raise ValueError(
                f"Circular dependency detected between Task {task_id} and Task {depends_on_task_id}"
            )

        # Check if already exists
        existing = (
            db.query(TaskDependency)
            .filter(
                TaskDependency.task_id == task_id,
                TaskDependency.depends_on_task_id == depends_on_task_id,
            )
            .first()
        )
        if existing:
            existing.dependency_type = dependency_type
            db.commit()
            db.refresh(existing)
            return existing

        dep = TaskDependency(
            task_id=task_id,
            depends_on_task_id=depends_on_task_id,
            dependency_type=dependency_type,
            status="PENDING",
            created_at=datetime.utcnow(),
        )
        db.add(dep)
        db.commit()
        db.refresh(dep)
        return dep

    @classmethod
    def get_ready_tasks(cls, db: Session, workspace_id: int) -> List[Task]:
        """Return tasks that have all upstream dependencies satisfied (done/completed)."""
        tasks = (
            db.query(Task)
            .filter(
                Task.workspace_id == workspace_id,
                Task.status.in_(["todo", "blocked"]),
            )
            .all()
        )

        ready_tasks: List[Task] = []
        for task in tasks:
            deps = db.query(TaskDependency).filter(TaskDependency.task_id == task.id).all()
            if not deps:
                ready_tasks.append(task)
                continue

            all_satisfied = True
            for dep in deps:
                upstream = db.query(Task).filter(Task.id == dep.depends_on_task_id).first()
                if not upstream or upstream.status != "done":
                    all_satisfied = False
                    break

            if all_satisfied:
                ready_tasks.append(task)

        return ready_tasks

    @classmethod
    def reevaluate_downstream(cls, db: Session, upstream_task_id: int) -> List[Task]:
        """Re-evaluates downstream tasks when an upstream task status changes."""
        deps = (
            db.query(TaskDependency)
            .filter(TaskDependency.depends_on_task_id == upstream_task_id)
            .all()
        )
        upstream_task = db.query(Task).filter(Task.id == upstream_task_id).first()
        is_done = upstream_task and upstream_task.status == "done"

        affected_tasks: List[Task] = []
        for dep in deps:
            if is_done:
                dep.status = "SATISFIED"
            else:
                dep.status = "PENDING"
            db.add(dep)

            downstream = db.query(Task).filter(Task.id == dep.task_id).first()
            if downstream:
                affected_tasks.append(downstream)

        db.commit()
        return affected_tasks
