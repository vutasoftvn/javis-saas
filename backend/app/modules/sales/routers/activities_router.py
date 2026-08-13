from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_workspace_member
from app.core.feature_flags import FLAG_SALES_CRM_CORE_V13_2, FLAG_SALES_FUNCTION_V13, require_flag
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.modules.sales.models import SalesActivity
from app.modules.sales.domain.activities import ActivityService

router = APIRouter()


class ActivityCreate(BaseModel):
    entity_type: str
    entity_id: int
    activity_type: str
    summary: str
    channel: Optional[str] = None
    direction: Optional[str] = None
    outcome: Optional[str] = None
    next_action: Optional[str] = None
    artifact_refs: Optional[Dict[str, Any]] = None


def _guard(workspace_id: int, member: WorkspaceMember, db: Session) -> None:
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    require_flag(db, FLAG_SALES_FUNCTION_V13, workspace_id)
    require_flag(db, FLAG_SALES_CRM_CORE_V13_2, workspace_id)


def _serialize_activity(act: SalesActivity):
    return {
        "id": str(act.id),
        "workspace_id": str(act.workspace_id),
        "entity_type": act.entity_type,
        "entity_id": str(act.entity_id),
        "activity_type": act.activity_type,
        "channel": act.channel,
        "direction": act.direction,
        "summary": act.summary,
        "outcome": act.outcome,
        "next_action": act.next_action,
        "actor_id": str(act.actor_id) if act.actor_id else None,
        "occurred_at": act.occurred_at.isoformat() if act.occurred_at else None,
        "artifact_refs": act.artifact_refs,
    }


@router.post("/activities", status_code=201)
def create_activity(
    data: ActivityCreate,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db)
    act = ActivityService.create_activity(
        db=db,
        workspace_id=workspace_id,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        activity_type=data.activity_type,
        summary=data.summary,
        channel=data.channel,
        direction=data.direction,
        outcome=data.outcome,
        next_action=data.next_action,
        actor_id=member.user_id,
        artifact_refs=data.artifact_refs,
    )
    return _serialize_activity(act)


@router.get("/activities")
def list_activities(
    workspace_id: int,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _guard(workspace_id, member, db)
    activities = ActivityService.list_activities(
        db, workspace_id, entity_type=entity_type, entity_id=entity_id, limit=limit, offset=offset
    )
    return {"activities": [_serialize_activity(a) for a in activities]}
