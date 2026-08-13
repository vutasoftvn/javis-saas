from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.modules.company_runtime.models import Handoff, WorkReview, Blocker
from app.modules.tasks.models import Task, TaskDependency
from app.modules.outcomes.models import Outcome, Artifact


class HandoffService:
    """Structured Handoff service for inter-function collaboration and Work Inspector data aggregation."""

    VALID_HANDOFF_TYPES = {
        "REQUEST_INPUT",
        "TRANSFER_ARTIFACT",
        "ASK_REVIEW",
        "ASK_DECISION",
        "REPORT_BLOCKER",
        "HANDOFF_TO_NEXT_FUNCTION",
    }

    VALID_FUNCTIONS = {"LEGAL", "MARKETING", "SALES", "TECH", "FINANCE"}

    @classmethod
    def create_handoff(
        cls,
        db: Session,
        workspace_id: int,
        from_function: str,
        to_function: str,
        handoff_type: str,
        requested_action: str,
        source_task_id: Optional[int] = None,
        target_task_id: Optional[int] = None,
        cycle_id: Optional[int] = None,
        weekly_mission_id: Optional[int] = None,
        artifact_refs: Optional[Any] = None,
        decision_refs: Optional[Any] = None,
        due_at: Optional[datetime] = None,
        idempotency_key: Optional[str] = None,
    ) -> Handoff:
        from_fn = from_function.upper()
        to_fn = to_function.upper()
        if from_fn not in cls.VALID_FUNCTIONS or to_fn not in cls.VALID_FUNCTIONS:
            raise ValueError(
                f"Invalid functions '{from_function}' -> '{to_function}'. Valid functions: {cls.VALID_FUNCTIONS}"
            )

        if handoff_type not in cls.VALID_HANDOFF_TYPES:
            raise ValueError(
                f"Invalid handoff_type '{handoff_type}'. Valid types: {cls.VALID_HANDOFF_TYPES}"
            )

        if idempotency_key:
            existing = db.query(Handoff).filter(
                Handoff.workspace_id == workspace_id,
                Handoff.idempotency_key == idempotency_key,
            ).first()
            if existing:
                return existing

        handoff = Handoff(
            workspace_id=workspace_id,
            cycle_id=cycle_id,
            weekly_mission_id=weekly_mission_id,
            from_function=from_fn,
            to_function=to_fn,
            source_task_id=source_task_id,
            target_task_id=target_task_id,
            handoff_type=handoff_type,
            requested_action=requested_action,
            artifact_refs={"items": artifact_refs} if isinstance(artifact_refs, list) else artifact_refs,
            decision_refs={"items": decision_refs} if isinstance(decision_refs, list) else decision_refs,
            due_at=due_at,
            idempotency_key=idempotency_key,
            status="PENDING",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(handoff)
        db.commit()
        db.refresh(handoff)
        return handoff

    @classmethod
    def list_handoffs(
        cls,
        db: Session,
        workspace_id: int,
        from_function: Optional[str] = None,
        to_function: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Handoff]:
        query = db.query(Handoff).filter(Handoff.workspace_id == workspace_id)
        if from_function:
            query = query.filter(Handoff.from_function == from_function.upper())
        if to_function:
            query = query.filter(Handoff.to_function == to_function.upper())
        if status:
            query = query.filter(Handoff.status == status.upper())
        return query.order_by(Handoff.created_at.desc()).all()

    @classmethod
    def accept_handoff(cls, db: Session, workspace_id: int, handoff_id: int) -> Handoff:
        handoff = (
            db.query(Handoff)
            .filter(Handoff.id == handoff_id, Handoff.workspace_id == workspace_id)
            .first()
        )
        if not handoff:
            raise ValueError(f"Handoff {handoff_id} not found in workspace {workspace_id}")
        if handoff.status != "PENDING":
            raise ValueError(f"Invalid handoff status transition: {handoff.status} -> ACCEPTED")
        handoff.status = "ACCEPTED"
        handoff.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(handoff)
        return handoff

    @classmethod
    def complete_handoff(cls, db: Session, workspace_id: int, handoff_id: int) -> Handoff:
        handoff = (
            db.query(Handoff)
            .filter(Handoff.id == handoff_id, Handoff.workspace_id == workspace_id)
            .first()
        )
        if not handoff:
            raise ValueError(f"Handoff {handoff_id} not found in workspace {workspace_id}")
        if handoff.status != "ACCEPTED":
            raise ValueError(f"Invalid handoff status transition: {handoff.status} -> COMPLETED")
        handoff.status = "COMPLETED"
        handoff.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(handoff)
        return handoff

    @classmethod
    def get_work_inspector(
        cls,
        db: Session,
        workspace_id: int,
        task_id: int,
    ) -> Dict[str, Any]:
        """Aggregate transparent operational view across Task, Outcome, Dependencies, Reviews, Handoffs, Blockers, Artifacts."""
        task = (
            db.query(Task)
            .filter(Task.id == task_id, Task.workspace_id == workspace_id)
            .first()
        )
        if not task:
            raise ValueError(f"Task {task_id} not found in workspace {workspace_id}")

        outcome = (
            db.query(Outcome)
            .filter(
                Outcome.workspace_id == workspace_id,
                (Outcome.task_id == task_id) | (Outcome.id == task.initiative_id),
            )
            .first()
        )

        # Dependencies
        upstream_deps = db.query(TaskDependency).filter(TaskDependency.task_id == task.id).all()
        downstream_deps = db.query(TaskDependency).filter(TaskDependency.depends_on_task_id == task.id).all()

        # Reviews
        reviews = []
        if outcome:
            reviews = (
                db.query(WorkReview)
                .filter(WorkReview.outcome_id == outcome.id, WorkReview.workspace_id == workspace_id)
                .order_by(WorkReview.created_at.asc())
                .all()
            )

        # Handoffs
        handoffs = (
            db.query(Handoff)
            .filter(
                Handoff.workspace_id == workspace_id,
                (Handoff.source_task_id == task.id) | (Handoff.target_task_id == task.id),
            )
            .order_by(Handoff.created_at.asc())
            .all()
        )

        # Blockers
        blockers = (
            db.query(Blocker)
            .filter(
                Blocker.workspace_id == workspace_id,
                (Blocker.task_id == task.id) | (outcome and Blocker.outcome_id == outcome.id),
            )
            .order_by(Blocker.created_at.asc())
            .all()
        )

        # Artifacts
        artifacts = (
            db.query(Artifact)
            .filter(
                Artifact.workspace_id == workspace_id,
                (outcome and Artifact.outcome_id == outcome.id),
            )
            .order_by(Artifact.created_at.asc())
            .all()
        )

        return {
            "task": {
                "id": str(task.id),
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
                "function": task.function,
                "execution_mode": task.execution_mode,
                "due_at": task.due_at.isoformat() if task.due_at else None,
                "created_at": task.created_at.isoformat(),
            },
            "outcome": {
                "id": str(outcome.id),
                "title": outcome.title,
                "desired_result": outcome.desired_result,
                "status": outcome.status,
                "acceptance_criteria": outcome.acceptance_criteria,
                "required_artifacts": outcome.required_artifacts,
                "review_type": outcome.review_type,
                "rework_count": outcome.rework_count,
            }
            if outcome
            else None,
            "dependencies": {
                "upstream": [
                    {
                        "task_id": str(d.depends_on_task_id),
                        "dependency_type": d.dependency_type,
                        "status": d.status,
                    }
                    for d in upstream_deps
                ],
                "downstream": [
                    {
                        "task_id": str(d.task_id),
                        "dependency_type": d.dependency_type,
                        "status": d.status,
                    }
                    for d in downstream_deps
                ],
            },
            "reviews": [
                {
                    "id": str(r.id),
                    "reviewer_type": r.reviewer_type,
                    "result": r.result,
                    "feedback": r.feedback,
                    "evidence_refs": r.evidence_refs,
                    "created_at": r.created_at.isoformat(),
                }
                for r in reviews
            ],
            "handoffs": [
                {
                    "id": str(h.id),
                    "from_function": h.from_function,
                    "to_function": h.to_function,
                    "handoff_type": h.handoff_type,
                    "requested_action": h.requested_action,
                    "status": h.status,
                    "created_at": h.created_at.isoformat(),
                }
                for h in handoffs
            ],
            "blockers": [
                {
                    "id": str(b.id),
                    "blocker_type": b.blocker_type,
                    "description": b.description,
                    "assigned_function": b.assigned_function,
                    "status": b.status,
                    "created_at": b.created_at.isoformat(),
                }
                for b in blockers
            ],
            "artifacts": [
                {
                    "id": str(a.id),
                    "title": a.title,
                    "type": a.type,
                    "status": a.status,
                    "local_uri": a.local_uri,
                    "created_at": a.created_at.isoformat(),
                }
                for a in artifacts
            ],
        }
