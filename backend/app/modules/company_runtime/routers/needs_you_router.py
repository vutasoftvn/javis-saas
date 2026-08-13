from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.modules.company_runtime.needs_you_service import NeedsYouService

router = APIRouter()


class SnoozeRequest(BaseModel):
    until: datetime


@router.get("/needs-you")
def list_needs_you(
    workspace_id: int,
    include_snoozed: bool = Query(False),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    items = NeedsYouService.list_items(
        db=db,
        workspace_id=workspace_id,
        include_snoozed=include_snoozed,
    )
    return {"total": len(items), "items": items}


@router.post("/needs-you/{item_id}/resolve")
def resolve_needs_you_endpoint(
    item_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    try:
        resolved = NeedsYouService.resolve_item(db=db, workspace_id=workspace_id, item_id=item_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "id": str(resolved.id),
        "status": resolved.status,
        "resolved_at": resolved.resolved_at.isoformat() if resolved.resolved_at else None,
    }


@router.post("/needs-you/{item_id}/snooze")
def snooze_needs_you_endpoint(
    item_id: int,
    data: SnoozeRequest,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    try:
        snoozed = NeedsYouService.snooze_item(
            db=db, workspace_id=workspace_id, item_id=item_id, until=data.until
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "id": str(snoozed.id),
        "status": snoozed.status,
        "snooze_until": snoozed.snooze_until.isoformat() if snoozed.snooze_until else None,
    }
