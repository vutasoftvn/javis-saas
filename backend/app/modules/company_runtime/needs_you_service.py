from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.modules.company_runtime.models import NeedsYouItem, Blocker, WorkReview
from app.modules.tasks.models import Task


class NeedsYouService:
    """Read-composition service for the founder's unified 'Needs You' queue."""

    @classmethod
    def list_items(
        cls,
        db: Session,
        workspace_id: int,
        include_snoozed: bool = False,
    ) -> List[Dict[str, Any]]:
        now = datetime.utcnow()
        filters = [
            NeedsYouItem.workspace_id == workspace_id,
            NeedsYouItem.status != "RESOLVED",
            NeedsYouItem.status != "CANCELLED",
        ]

        if not include_snoozed:
            filters.append(
                (NeedsYouItem.snooze_until.is_(None)) | (NeedsYouItem.snooze_until <= now)
            )

        items = (
            db.query(NeedsYouItem)
            .filter(*filters)
            .order_by(NeedsYouItem.priority.asc(), NeedsYouItem.created_at.desc())
            .all()
        )

        results = []
        for item in items:
            results.append({
                "id": str(item.id),
                "workspace_id": str(item.workspace_id),
                "cycle_id": str(item.cycle_id) if item.cycle_id else None,
                "source_type": item.source_type,
                "source_id": str(item.source_id),
                "priority": item.priority,
                "reason": item.reason,
                "requested_action": item.requested_action,
                "due_at": item.due_at.isoformat() if item.due_at else None,
                "status": item.status,
                "snooze_until": item.snooze_until.isoformat() if item.snooze_until else None,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            })
        return results

    @classmethod
    def resolve_item(
        cls,
        db: Session,
        workspace_id: int,
        item_id: int,
    ) -> NeedsYouItem:
        item = (
            db.query(NeedsYouItem)
            .filter(NeedsYouItem.id == item_id, NeedsYouItem.workspace_id == workspace_id)
            .first()
        )
        if not item:
            raise ValueError(f"NeedsYou item {item_id} not found in workspace {workspace_id}")

        item.status = "RESOLVED"
        item.resolved_at = datetime.utcnow()
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @classmethod
    def snooze_item(
        cls,
        db: Session,
        workspace_id: int,
        item_id: int,
        until: datetime,
    ) -> NeedsYouItem:
        item = (
            db.query(NeedsYouItem)
            .filter(NeedsYouItem.id == item_id, NeedsYouItem.workspace_id == workspace_id)
            .first()
        )
        if not item:
            raise ValueError(f"NeedsYou item {item_id} not found in workspace {workspace_id}")

        item.status = "SNOOZED"
        item.snooze_until = until
        db.add(item)
        db.commit()
        db.refresh(item)
        return item
