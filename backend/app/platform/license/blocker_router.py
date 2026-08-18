from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.core.function_router import route_function
from app.platform.license.models import Blocker, NeedsYouItem
from app.founder_os.tasks.models import Task
from app.platform.license.state_service import TaskStateService


class BlockerRouter:
    """Classifies, routes, and escalates blockers across the 5 AI Functions or Founder queue."""

    @classmethod
    def route_blocker_function(cls, description: str, blocker_type: str) -> Optional[str]:
        # Direct type mapping first
        if blocker_type in {"FINANCE_EXCEPTION", "MISSING_DOCUMENT", "PRICING_NEEDED", "DISCOUNT_APPROVAL", "PAYMENT_ISSUE"}:
            return "FINANCE"
        if blocker_type in {"LEGAL_UNCERTAINTY", "LEGAL_REVIEW"}:
            return "LEGAL"
        if blocker_type in {"TECHNICAL_BLOCK", "TECHNICAL_QUESTION", "PRODUCT_GAP"}:
            return "TECH"
        if blocker_type in {"FOUNDER_DECISION", "HUMAN_INPUT"}:
            return None  # Direct founder escalation

        # Fall back to deterministic function routing from description
        routed = route_function(description)
        return routed

    @classmethod
    def create_blocker(
        cls,
        db: Session,
        workspace_id: int,
        blocker_type: str,
        description: str,
        task_id: Optional[int] = None,
        outcome_id: Optional[int] = None,
        cycle_id: Optional[int] = None,
        weekly_mission_id: Optional[int] = None,
        requested_capability: Optional[str] = None,
        assigned_function: Optional[str] = None,
    ) -> Blocker:
        if not assigned_function:
            assigned_function = cls.route_blocker_function(description, blocker_type)

        is_founder_level = assigned_function is None or blocker_type in {
            "FOUNDER_DECISION",
            "HUMAN_INPUT",
        }
        status = "ESCALATED" if is_founder_level else "ROUTED"

        blocker = Blocker(
            workspace_id=workspace_id,
            task_id=task_id,
            outcome_id=outcome_id,
            cycle_id=cycle_id,
            weekly_mission_id=weekly_mission_id,
            blocker_type=blocker_type,
            description=description,
            requested_capability=requested_capability,
            assigned_function=assigned_function,
            status=status,
            created_at=datetime.utcnow(),
        )
        db.add(blocker)
        db.commit()
        db.refresh(blocker)

        # Mark associated task as blocked
        if task_id:
            task = (
                db.query(Task)
                .filter(Task.id == task_id, Task.workspace_id == workspace_id)
                .first()
            )
            if task and task.status != "blocked":
                TaskStateService.transition(
                    db=db,
                    task=task,
                    target_status="blocked",
                    reason=f"Blocked by {blocker_type}: {description}",
                )

        # If founder action required, add to Needs You queue
        if is_founder_level or status == "ESCALATED":
            needs_item = NeedsYouItem(
                workspace_id=workspace_id,
                cycle_id=cycle_id,
                source_type="blocker",
                source_id=blocker.id,
                priority="P0" if blocker_type == "FOUNDER_DECISION" else "P1",
                reason=f"Blocker requires founder decision: {description}",
                requested_action=f"Resolve {blocker_type} for task {task_id or 'operation'}",
                created_at=datetime.utcnow(),
            )
            db.add(needs_item)
            db.commit()

        return blocker

    @classmethod
    def resolve_blocker(
        cls,
        db: Session,
        workspace_id: int,
        blocker_id: int,
        resolution_artifact_id: Optional[int] = None,
    ) -> Blocker:
        blocker = (
            db.query(Blocker)
            .filter(Blocker.id == blocker_id, Blocker.workspace_id == workspace_id)
            .first()
        )
        if not blocker:
            raise ValueError(f"Blocker {blocker_id} not found in workspace {workspace_id}")

        blocker.status = "RESOLVED"
        blocker.resolution_artifact_id = resolution_artifact_id
        blocker.resolved_at = datetime.utcnow()
        db.add(blocker)

        # Resolve associated NeedsYou item
        needs_item = (
            db.query(NeedsYouItem)
            .filter(
                NeedsYouItem.workspace_id == workspace_id,
                NeedsYouItem.source_type == "blocker",
                NeedsYouItem.source_id == blocker.id,
                NeedsYouItem.status != "RESOLVED",
            )
            .first()
        )
        if needs_item:
            needs_item.status = "RESOLVED"
            needs_item.resolved_at = datetime.utcnow()
            db.add(needs_item)

        # Re-evaluate task state if it was blocked
        if blocker.task_id:
            task = (
                db.query(Task)
                .filter(Task.id == blocker.task_id, Task.workspace_id == workspace_id)
                .first()
            )
            if task and task.status == "blocked":
                # Check if other active blockers exist for this task
                active_blockers = (
                    db.query(Blocker)
                    .filter(
                        Blocker.task_id == task.id,
                        Blocker.id != blocker.id,
                        Blocker.status.in_(["OPEN", "ROUTED", "RESOLVING", "ESCALATED"]),
                    )
                    .count()
                )
                if active_blockers == 0:
                    TaskStateService.transition(
                        db=db,
                        task=task,
                        target_status="todo",
                        reason=f"Blocker {blocker.id} resolved",
                    )

        db.commit()
        db.refresh(blocker)
        return blocker
