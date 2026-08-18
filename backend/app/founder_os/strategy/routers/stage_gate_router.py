from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.platform.auth.models import WorkspaceMember
from app.founder_os.strategy.schemas.stage_gate_schemas import (
    StageGateAuditRequest,
    StageGateAuditResponse,
    PrematureScalingAlertResponse,
    ApplyStageTransitionRequest,
)
from app.founder_os.strategy.services.stage_gate_service import StageGateService

router = APIRouter(prefix="/stage-gate", tags=["Stage Gate Auditing & Anti-Premature Scaling"])


@router.post("/audit", response_model=StageGateAuditResponse)
def audit_stage_readiness(
    payload: StageGateAuditRequest,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    """Thực hiện phiên thẩm định chuyển giai đoạn (Stage Gate Audit)."""
    return StageGateService.evaluate_stage_readiness(
        db, member.workspace_id, payload.project_id, payload.target_stage
    )


@router.get("/history/{project_id}", response_model=List[StageGateAuditResponse])
def get_audit_history(
    project_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    """Lấy lịch sử các phiên thẩm định Stage Gate của dự án."""
    return StageGateService.get_audit_history(
        db, member.workspace_id, project_id
    )


@router.get("/guardrails/{project_id}", response_model=List[PrematureScalingAlertResponse])
def check_guardrails(
    project_id: int,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    """Quét và lấy danh sách cảnh báo Anti-Premature Scaling."""
    return StageGateService.check_anti_premature_guardrails(
        db, member.workspace_id, project_id
    )


@router.post("/apply-transition/{audit_id}")
def apply_stage_transition(
    audit_id: int,
    payload: Optional[ApplyStageTransitionRequest] = None,
    db: Session = Depends(get_db),
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    """Áp dụng nâng cấp giai đoạn chính thức sau khi thẩm định thành công."""
    if member.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Chỉ Admin/Founder mới có quyền duyệt chuyển Stage",
        )
    project = StageGateService.apply_stage_advancement(
        db, member.workspace_id, audit_id, payload.rationale if payload else None
    )
    return {
        "status": "success",
        "project_id": str(project.id),
        "new_stage": project.project_stage,
        "message": f"Dự án đã được nâng cấp chính thức lên {project.project_stage}.",
    }
