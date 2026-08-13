from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.modules.company_runtime.runtime_manager import CompanyRuntimeManager

router = APIRouter()


class ClassifyIntentRequest(BaseModel):
    text: str


class DecomposeMissionRequest(BaseModel):
    weekly_commitment_id: int


class CheckpointRequest(BaseModel):
    reason: Optional[str] = "MANUAL"


@router.post("/runtime/classify-intent")
def classify_intent_endpoint(
    data: ClassifyIntentRequest,
):
    result = CompanyRuntimeManager.classify_intent(data.text)
    return result


@router.post("/runtime/decompose", status_code=status.HTTP_201_CREATED)
def decompose_mission_endpoint(
    data: DecomposeMissionRequest,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    try:
        result = CompanyRuntimeManager.decompose_mission(
            db=db,
            workspace_id=workspace_id,
            weekly_commitment_id=data.weekly_commitment_id,
            user_id=member.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return result


@router.get("/runtime/status")
def get_runtime_status_endpoint(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    return CompanyRuntimeManager.get_runtime_status(db=db, workspace_id=workspace_id)


@router.get("/runtime/dag")
def get_dag_endpoint(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    return CompanyRuntimeManager.get_dag(db=db, workspace_id=workspace_id)


@router.post("/runtime/checkpoint")
def create_checkpoint_endpoint(
    workspace_id: int,
    data: Optional[CheckpointRequest] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    reason = data.reason if data and data.reason else "MANUAL"
    return CompanyRuntimeManager.checkpoint(db=db, workspace_id=workspace_id, reason=reason)


@router.post("/runtime/resume")
def resume_runtime_endpoint(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    return CompanyRuntimeManager.resume(db=db, workspace_id=workspace_id)
