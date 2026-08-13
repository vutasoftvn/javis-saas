from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.modules.company_runtime.intent_classifier import WorkIntentClassifier
from app.modules.company_runtime.decomposition_service import DecompositionService
from app.modules.company_runtime.dependency_service import DependencyService
from app.modules.company_runtime.blocker_router import BlockerRouter
from app.modules.company_runtime.needs_you_service import NeedsYouService
from app.modules.company_runtime.checkpoint_service import CheckpointService
from app.modules.company_runtime.handoff_service import HandoffService
from app.modules.tasks.models import Task, TaskDependency
from app.modules.company_runtime.models import Blocker, NeedsYouItem


class CompanyRuntimeManager:
    """Central thin coordinator for Company Runtime operations without introducing a second execution engine."""

    @classmethod
    def classify_intent(cls, text: str) -> Dict[str, Any]:
        return WorkIntentClassifier.classify(text)

    @classmethod
    def decompose_mission(
        cls,
        db: Session,
        workspace_id: int,
        weekly_commitment_id: int,
        user_id: int,
    ) -> Dict[str, Any]:
        return DecompositionService.decompose_weekly_mission(
            db=db,
            workspace_id=workspace_id,
            weekly_commitment_id=weekly_commitment_id,
            user_id=user_id,
        )

    @classmethod
    def get_runtime_status(cls, db: Session, workspace_id: int) -> Dict[str, Any]:
        tasks = db.query(Task).filter(Task.workspace_id == workspace_id).all()
        status_counts: Dict[str, int] = {}
        for t in tasks:
            status_counts[t.status] = status_counts.get(t.status, 0) + 1

        active_blockers = (
            db.query(Blocker)
            .filter(Blocker.workspace_id == workspace_id, Blocker.status.in_(["OPEN", "ROUTED", "ESCALATED"]))
            .count()
        )

        needs_you_items = (
            db.query(NeedsYouItem)
            .filter(NeedsYouItem.workspace_id == workspace_id, NeedsYouItem.status == "OPEN")
            .count()
        )

        ready_tasks = DependencyService.get_ready_tasks(db=db, workspace_id=workspace_id)

        return {
            "total_tasks": len(tasks),
            "status_breakdown": status_counts,
            "ready_tasks_count": len(ready_tasks),
            "active_blockers_count": active_blockers,
            "needs_you_count": needs_you_items,
        }

    @classmethod
    def get_dag(cls, db: Session, workspace_id: int) -> Dict[str, Any]:
        tasks = db.query(Task).filter(Task.workspace_id == workspace_id).all()
        task_map = {t.id: t for t in tasks}
        deps = (
            db.query(TaskDependency)
            .filter(TaskDependency.task_id.in_(task_map.keys()))
            .all()
            if task_map
            else []
        )

        nodes = [
            {
                "id": str(t.id),
                "title": t.title,
                "function": t.function,
                "status": t.status,
                "execution_mode": t.execution_mode,
            }
            for t in tasks
        ]

        edges = [
            {
                "source": str(d.depends_on_task_id),
                "target": str(d.task_id),
                "dependency_type": d.dependency_type,
                "status": d.status,
            }
            for d in deps
        ]

        return {"nodes": nodes, "edges": edges}

    @classmethod
    def checkpoint(cls, db: Session, workspace_id: int, reason: str = "MANUAL") -> Dict[str, Any]:
        ckpt = CheckpointService.checkpoint(db=db, workspace_id=workspace_id, reason=reason)
        return {
            "checkpoint_id": str(ckpt.id),
            "sequence": ckpt.sequence,
            "reason": ckpt.checkpoint_reason,
            "created_at": ckpt.created_at.isoformat(),
        }

    @classmethod
    def resume(cls, db: Session, workspace_id: int) -> Dict[str, Any]:
        return CheckpointService.resume(db=db, workspace_id=workspace_id)
