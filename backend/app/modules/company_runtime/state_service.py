from datetime import datetime
from typing import Optional, Set, Dict
from sqlalchemy.orm import Session

from app.modules.tasks.models import Task
from app.core.audit import write_audit_log


class TaskStateService:
    """Guards task state transitions and emits audit logs."""

    VALID_STATUSES: Set[str] = {
        "todo",
        "in_progress",
        "waiting_approval",
        "blocked",
        "done",
        "cancelled",
    }

    LEGAL_TRANSITIONS: Dict[str, Set[str]] = {
        "todo": {"in_progress", "blocked", "cancelled"},
        "in_progress": {"waiting_approval", "blocked", "done", "cancelled", "todo"},
        "waiting_approval": {"in_progress", "done", "blocked", "cancelled"},
        "blocked": {"todo", "in_progress", "cancelled"},
        "done": {"in_progress"},
        "cancelled": {"todo"},
    }

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        if from_status == to_status:
            return True
        return to_status in cls.LEGAL_TRANSITIONS.get(from_status, set())

    @classmethod
    def transition(
        cls,
        db: Session,
        task: Task,
        target_status: str,
        actor_id: Optional[int] = None,
        actor_type: str = "user",
        reason: Optional[str] = None,
    ) -> Task:
        if target_status not in cls.VALID_STATUSES:
            raise ValueError(f"Invalid target status '{target_status}'. Valid statuses: {cls.VALID_STATUSES}")

        if task.status == target_status:
            return task

        if not cls.can_transition(task.status, target_status):
            raise ValueError(
                f"Illegal state transition from '{task.status}' to '{target_status}' for Task {task.id}"
            )

        old_status = task.status
        task.status = target_status
        task.updated_at = datetime.utcnow()
        db.add(task)
        db.commit()
        db.refresh(task)

        # Audit log entry with workspace metadata
        write_audit_log(
            db=db,
            actor_type=actor_type,
            actor_id=actor_id or 0,
            action="task.status.transition",
            target_type="task",
            target_id=task.id,
            metadata_jsonb={
                "workspace_id": str(task.workspace_id),
                "from_status": old_status,
                "to_status": target_status,
                "reason": reason or "",
            },
        )

        # Trigger downstream dependency re-evaluation
        try:
            from app.modules.company_runtime.dependency_service import DependencyService
            DependencyService.reevaluate_downstream(db, task.id)
        except Exception:
            pass

        return task
