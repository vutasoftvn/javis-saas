from datetime import datetime
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.core.feature_flags import FLAG_FINANCE_FUNCTION_V13, require_flag
from app.db.models import WorkspaceMember
from app.modules.company_runtime.models import Handoff
from app.modules.company_runtime.handoff_service import HandoffService

router = APIRouter()


def _require_target_function_access(db: Session, workspace_id: int, handoff_id: int) -> None:
    handoff = db.query(Handoff).filter(
        Handoff.id == handoff_id,
        Handoff.workspace_id == workspace_id,
    ).first()
    if handoff is None:
        raise HTTPException(status_code=404, detail="Handoff not found")
    if handoff.to_function == "FINANCE":
        require_flag(db, FLAG_FINANCE_FUNCTION_V13, workspace_id)


class HandoffCreateRequest(BaseModel):
    from_function: str
    to_function: str
    handoff_type: str
    requested_action: str
    source_task_id: Optional[int] = None
    target_task_id: Optional[int] = None
    cycle_id: Optional[int] = None
    weekly_mission_id: Optional[int] = None
    artifact_refs: Optional[Any] = None
    decision_refs: Optional[Any] = None
    due_at: Optional[datetime] = None


@router.post("/handoffs", status_code=status.HTTP_201_CREATED)
def create_handoff_endpoint(
    data: HandoffCreateRequest,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")
    _require_target_function_access(db, workspace_id, handoff_id)

    try:
        handoff = HandoffService.create_handoff(
            db=db,
            workspace_id=workspace_id,
            from_function=data.from_function,
            to_function=data.to_function,
            handoff_type=data.handoff_type,
            requested_action=data.requested_action,
            source_task_id=data.source_task_id,
            target_task_id=data.target_task_id,
            cycle_id=data.cycle_id,
            weekly_mission_id=data.weekly_mission_id,
            artifact_refs=data.artifact_refs,
            decision_refs=data.decision_refs,
            due_at=data.due_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "id": str(handoff.id),
        "from_function": handoff.from_function,
        "to_function": handoff.to_function,
        "handoff_type": handoff.handoff_type,
        "status": handoff.status,
        "created_at": handoff.created_at.isoformat(),
    }


@router.get("/handoffs")
def list_handoffs_endpoint(
    workspace_id: int,
    from_function: Optional[str] = Query(None),
    to_function: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    handoffs = HandoffService.list_handoffs(
        db=db,
        workspace_id=workspace_id,
        from_function=from_function,
        to_function=to_function,
        status=status_filter,
    )
    return {
        "total": len(handoffs),
        "handoffs": [
            {
                "id": str(h.id),
                "from_function": h.from_function,
                "to_function": h.to_function,
                "handoff_type": h.handoff_type,
                "requested_action": h.requested_action,
                "source_task_id": str(h.source_task_id) if h.source_task_id else None,
                "target_task_id": str(h.target_task_id) if h.target_task_id else None,
                "status": h.status,
                "created_at": h.created_at.isoformat(),
            }
            for h in handoffs
        ],
    }


@router.post("/handoffs/{handoff_id}/accept")
def accept_handoff_endpoint(
    handoff_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")
    _require_target_function_access(db, workspace_id, handoff_id)

    try:
        handoff = HandoffService.accept_handoff(db=db, workspace_id=workspace_id, handoff_id=handoff_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"id": str(handoff.id), "status": handoff.status}


@router.post("/handoffs/{handoff_id}/complete")
def complete_handoff_endpoint(
    handoff_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    try:
        handoff = HandoffService.complete_handoff(db=db, workspace_id=workspace_id, handoff_id=handoff_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"id": str(handoff.id), "status": handoff.status}


@router.get("/tasks/{task_id}/inspector")
def get_task_inspector(
    task_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    try:
        inspector_data = HandoffService.get_work_inspector(
            db=db, workspace_id=workspace_id, task_id=task_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return inspector_data
