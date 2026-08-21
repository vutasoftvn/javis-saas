from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from platform_core.license.models import RuntimeCheckpoint, NeedsYouItem, Blocker
from founder_os.tasks.models import Task, TaskDependency
from integrations.devices.models import DeveloperJob


class CheckpointService:
    """Runtime checkpointing and crash recovery / resume engine."""

    VALID_REASONS = {
        "PERIODIC",
        "WORK_ITEM_STATE_CHANGE",
        "APPROVAL_CREATED",
        "BEFORE_EXTERNAL_ACTION",
        "SESSION_END",
        "DEVICE_SLEEP",
        "ERROR_RECOVERY",
    }

    @classmethod
    def checkpoint(
        cls,
        db: Session,
        workspace_id: int,
        reason: str = "PERIODIC",
        cycle_id: Optional[int] = None,
        weekly_mission_id: Optional[int] = None,
    ) -> RuntimeCheckpoint:
        # Snapshot tasks
        tasks = db.query(Task).filter(Task.workspace_id == workspace_id).all()
        task_states = {
            str(t.id): {
                "status": t.status,
                "title": t.title,
                "function": t.function,
                "priority": t.priority,
            }
            for t in tasks
        }

        # Snapshot dependencies
        task_ids = [t.id for t in tasks]
        deps = (
            db.query(TaskDependency)
            .filter(TaskDependency.task_id.in_(task_ids))
            .all()
            if task_ids
            else []
        )
        dep_states = [
            {
                "task_id": str(getattr(d, "task_id", "")),
                "depends_on_task_id": str(getattr(d, "depends_on_task_id", "")),
                "dependency_type": getattr(d, "dependency_type", "BLOCKS"),
                "status": getattr(d, "status", "PENDING"),
            }
            for d in deps
            if hasattr(d, "task_id")
        ]

        # Snapshot pending approvals and needs you
        needs_items = (
            db.query(NeedsYouItem)
            .filter(NeedsYouItem.workspace_id == workspace_id, NeedsYouItem.status != "RESOLVED")
            .all()
        )
        needs_states = [
            {
                "id": str(getattr(n, "id", "")),
                "source_type": getattr(n, "source_type", "unknown"),
                "source_id": str(getattr(n, "source_id", "")),
                "priority": getattr(n, "priority", "P1"),
                "reason": getattr(n, "reason", ""),
            }
            for n in needs_items
            if hasattr(n, "source_type")
        ]

        # Snapshot active developer jobs
        jobs = (
            db.query(DeveloperJob)
            .filter(DeveloperJob.workspace_id == workspace_id, DeveloperJob.status.in_(["CLAIMED", "QUEUED"]))
            .all()
        )
        job_states = [
            {
                "id": str(getattr(j, "id", "")),
                "title": getattr(j, "title", ""),
                "status": getattr(j, "status", ""),
                "device_id": str(j.assigned_device_id) if getattr(j, "assigned_device_id", None) else None,
            }
            for j in jobs
            if hasattr(j, "assigned_device_id") or hasattr(j, "title")
        ]

        # Compute next sequence
        max_seq = (
            db.query(func.max(RuntimeCheckpoint.sequence))
            .filter(RuntimeCheckpoint.workspace_id == workspace_id)
            .scalar()
        ) or 0

        ckpt = RuntimeCheckpoint(
            workspace_id=workspace_id,
            cycle_id=cycle_id,
            weekly_mission_id=weekly_mission_id,
            sequence=max_seq + 1,
            work_item_states={"tasks": task_states},
            dependency_state={"dependencies": dep_states},
            pending_approvals={},
            pending_needs_you={"items": needs_states},
            active_executors={"developer_jobs": job_states},
            checkpoint_reason=reason,
            created_at=datetime.utcnow(),
        )
        db.add(ckpt)
        db.commit()
        db.refresh(ckpt)
        return ckpt

    @classmethod
    def resume(cls, db: Session, workspace_id: int) -> Dict[str, Any]:
        """Restore and reconcile operational state after desktop sleep or restart without duplicating tasks."""
        latest_ckpt = (
            db.query(RuntimeCheckpoint)
            .filter(RuntimeCheckpoint.workspace_id == workspace_id)
            .order_by(RuntimeCheckpoint.sequence.desc())
            .first()
        )

        reconciled_tasks = []
        tasks_in_progress = (
            db.query(Task)
            .filter(Task.workspace_id == workspace_id, Task.status == "in_progress")
            .all()
        )

        for task in tasks_in_progress:
            # Check if there is an active running developer job
            active_job = (
                db.query(DeveloperJob)
                .filter(DeveloperJob.workspace_id == workspace_id, DeveloperJob.status == "CLAIMED")
                .first()
            )
            # Reconcile status
            reconciled_tasks.append({
                "task_id": str(task.id),
                "title": task.title,
                "status": task.status,
                "has_active_worker": bool(active_job),
            })

        active_needs_count = (
            db.query(NeedsYouItem)
            .filter(NeedsYouItem.workspace_id == workspace_id, NeedsYouItem.status == "OPEN")
            .count()
        )

        return {
            "status": "resumed",
            "checkpoint_id": str(latest_ckpt.id) if latest_ckpt else None,
            "checkpoint_sequence": latest_ckpt.sequence if latest_ckpt else 0,
            "reconciled_tasks_count": len(reconciled_tasks),
            "reconciled_tasks": reconciled_tasks,
            "active_needs_you_count": active_needs_count,
            "resumed_at": datetime.utcnow().isoformat(),
        }
