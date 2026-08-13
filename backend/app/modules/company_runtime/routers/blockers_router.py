from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.modules.company_runtime.models import Blocker
from app.modules.company_runtime.blocker_router import BlockerRouter

router = APIRouter()


class BlockerCreateRequest(BaseModel):
    blocker_type: str
    description: str
    task_id: Optional[int] = None
    outcome_id: Optional[int] = None
    cycle_id: Optional[int] = None
    weekly_mission_id: Optional[int] = None
    requested_capability: Optional[str] = None
    assigned_function: Optional[str] = None


class BlockerResolveRequest(BaseModel):
    resolution_artifact_id: Optional[int] = None


@router.get("/blockers")
def list_blockers(
    workspace_id: int,
    status_filter: Optional[str] = Query(None, alias="status"),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    query = db.query(Blocker).filter(Blocker.workspace_id == workspace_id)
    if status_filter:
        query = query.filter(Blocker.status == status_filter.upper())

    blockers = query.order_by(Blocker.created_at.desc()).all()
    return {
        "total": len(blockers),
        "blockers": [
            {
                "id": str(b.id),
                "task_id": str(b.task_id) if b.task_id else None,
                "outcome_id": str(b.outcome_id) if b.outcome_id else None,
                "blocker_type": b.blocker_type,
                "description": b.description,
                "assigned_function": b.assigned_function,
                "status": b.status,
                "created_at": b.created_at.isoformat(),
                "resolved_at": b.resolved_at.isoformat() if b.resolved_at else None,
            }
            for b in blockers
        ],
    }


@router.post("/blockers", status_code=status.HTTP_201_CREATED)
def create_blocker_endpoint(
    data: BlockerCreateRequest,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    blocker = BlockerRouter.create_blocker(
        db=db,
        workspace_id=workspace_id,
        blocker_type=data.blocker_type,
        description=data.description,
        task_id=data.task_id,
        outcome_id=data.outcome_id,
        cycle_id=data.cycle_id,
        weekly_mission_id=data.weekly_mission_id,
        requested_capability=data.requested_capability,
        assigned_function=data.assigned_function,
    )

    return {
        "id": str(blocker.id),
        "blocker_type": blocker.blocker_type,
        "description": blocker.description,
        "assigned_function": blocker.assigned_function,
        "status": blocker.status,
        "created_at": blocker.created_at.isoformat(),
    }


@router.post("/blockers/{blocker_id}/resolve")
def resolve_blocker_endpoint(
    blocker_id: int,
    workspace_id: int,
    data: Optional[BlockerResolveRequest] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    try:
        resolved = BlockerRouter.resolve_blocker(
            db=db,
            workspace_id=workspace_id,
            blocker_id=blocker_id,
            resolution_artifact_id=data.resolution_artifact_id if data else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "id": str(resolved.id),
        "status": resolved.status,
        "resolved_at": resolved.resolved_at.isoformat() if resolved.resolved_at else None,
    }
