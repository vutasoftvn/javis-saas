from datetime import datetime
from typing import Optional, Any
from sqlalchemy.orm import Session

from app.modules.outcomes.models import Outcome
from app.modules.tasks.models import Task
from app.modules.company_runtime.models import WorkReview, Blocker, NeedsYouItem
from app.modules.company_runtime.state_service import TaskStateService


class ReviewService:
    """Handles review decisions, rework loop gating, and escalation routing."""

    VALID_RESULTS = {"ACCEPTED", "REWORK_REQUIRED", "ESCALATED"}
    DEFAULT_MAX_REWORK = 3

    @classmethod
    def create_review(
        cls,
        db: Session,
        workspace_id: int,
        outcome_id: int,
        reviewer_type: str,
        result: str,
        reviewer_id: Optional[int] = None,
        feedback: Optional[str] = None,
        evidence_refs: Optional[Any] = None,
        max_rework_count: int = DEFAULT_MAX_REWORK,
    ) -> WorkReview:
        if result not in cls.VALID_RESULTS:
            raise ValueError(f"Invalid review result '{result}'. Must be one of {cls.VALID_RESULTS}")

        outcome = (
            db.query(Outcome)
            .filter(Outcome.id == outcome_id, Outcome.workspace_id == workspace_id)
            .first()
        )
        if not outcome:
            raise ValueError(f"Outcome {outcome_id} not found in workspace {workspace_id}")

        evidence_payload = (
            {"items": evidence_refs} if isinstance(evidence_refs, list) else evidence_refs
        )

        review = WorkReview(
            workspace_id=workspace_id,
            outcome_id=outcome_id,
            reviewer_type=reviewer_type,
            reviewer_id=reviewer_id,
            result=result,
            feedback=feedback,
            evidence_refs=evidence_payload,
            created_at=datetime.utcnow(),
        )
        db.add(review)

        task = None
        if outcome.task_id:
            task = (
                db.query(Task)
                .filter(Task.id == outcome.task_id, Task.workspace_id == workspace_id)
                .first()
            )

        if result == "ACCEPTED":
            outcome.status = "completed"
            outcome.updated_at = datetime.utcnow()
            db.add(outcome)
            db.commit()
            if task:
                TaskStateService.transition(
                    db=db,
                    task=task,
                    target_status="done",
                    actor_id=reviewer_id,
                    reason=f"Review accepted: {feedback or ''}",
                )

        elif result == "REWORK_REQUIRED":
            if (outcome.rework_count or 0) >= max_rework_count:
                raise ValueError(
                    f"Max rework count ({max_rework_count}) exceeded for Outcome {outcome_id}. Must escalate to founder/expert."
                )

            outcome.rework_count = (outcome.rework_count or 0) + 1
            outcome.status = "running"
            outcome.updated_at = datetime.utcnow()
            db.add(outcome)
            db.commit()
            if task:
                TaskStateService.transition(
                    db=db,
                    task=task,
                    target_status="in_progress",
                    actor_id=reviewer_id,
                    reason=f"Rework required (Attempt {outcome.rework_count}): {feedback or ''}",
                )

        elif result == "ESCALATED":
            outcome.status = "waiting_approval"
            outcome.updated_at = datetime.utcnow()
            db.add(outcome)
            db.commit()
            if task:
                TaskStateService.transition(
                    db=db,
                    task=task,
                    target_status="waiting_approval",
                    actor_id=reviewer_id,
                    reason=f"Review escalated: {feedback or ''}",
                )

            # Auto-create NeedsYouItem for founder attention
            needs_item = NeedsYouItem(
                workspace_id=workspace_id,
                cycle_id=outcome.cycle_id,
                source_type="review",
                source_id=review.id,
                priority="P0",
                reason=f"Outcome review escalated: {feedback or outcome.title}",
                requested_action=f"Review outcome '{outcome.title}' exception",
                created_at=datetime.utcnow(),
            )
            db.add(needs_item)
            db.commit()

        db.commit()
        db.refresh(review)
        return review
