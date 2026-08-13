from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.modules.sales.models import SalesActivity


class ActivityService:
    @staticmethod
    def create_activity(
        db: Session,
        workspace_id: int,
        entity_type: str,
        entity_id: int,
        activity_type: str,
        summary: str,
        channel: Optional[str] = None,
        direction: Optional[str] = None,
        outcome: Optional[str] = None,
        next_action: Optional[str] = None,
        actor_id: Optional[int] = None,
        occurred_at: Optional[datetime] = None,
        artifact_refs: Optional[Dict[str, Any]] = None,
    ) -> SalesActivity:
        activity = SalesActivity(
            workspace_id=workspace_id,
            entity_type=entity_type.lower(),
            entity_id=entity_id,
            activity_type=activity_type.upper(),
            channel=channel,
            direction=direction,
            summary=summary,
            outcome=outcome,
            next_action=next_action,
            actor_id=actor_id,
            occurred_at=occurred_at or datetime.utcnow(),
            artifact_refs=artifact_refs,
        )
        db.add(activity)
        db.commit()
        db.refresh(activity)
        return activity

    @staticmethod
    def record_status_change(
        db: Session,
        workspace_id: int,
        entity_type: str,
        entity_id: int,
        old_status: str,
        new_status: str,
        reason: Optional[str] = None,
        actor_id: Optional[int] = None,
    ) -> SalesActivity:
        summary = f"Status changed from {old_status} to {new_status}"
        if reason:
            summary += f": {reason}"
        return ActivityService.create_activity(
            db=db,
            workspace_id=workspace_id,
            entity_type=entity_type,
            entity_id=entity_id,
            activity_type="STATUS_CHANGE",
            summary=summary,
            actor_id=actor_id,
        )

    @staticmethod
    def list_activities(
        db: Session,
        workspace_id: int,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[SalesActivity]:
        query = db.query(SalesActivity).filter(SalesActivity.workspace_id == workspace_id)
        if entity_type:
            query = query.filter(SalesActivity.entity_type == entity_type.lower())
        if entity_id:
            query = query.filter(SalesActivity.entity_id == entity_id)
        return query.order_by(SalesActivity.occurred_at.desc()).offset(offset).limit(limit).all()
