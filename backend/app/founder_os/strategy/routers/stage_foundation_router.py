from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.platform.auth.models import WorkspaceMember
from app.founder_os.strategy.models import Project
from app.founder_os.strategy.schemas.stage_schemas import (
    ProjectStageEnum,
    StagePolicySpec,
    StageContextResponse,
    ProjectStageUpdateRequest,
    StageSummaryResponse,
)
from app.founder_os.strategy.services.management_policy_engine import ManagementPolicyEngine
from app.founder_os.strategy.services.stage_resolver_service import StageResolverService

router = APIRouter(prefix="/stage", tags=["COSA Stage Operating Architecture"])


@router.get("/context", response_model=StageContextResponse)
def get_stage_context(
    project_id: Optional[int] = Query(None, description="Project ID cụ thể (để trống sẽ fallback về Project P0 active)"),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    """Lấy toàn diện Ngữ cảnh vận hành Stage (Company Identity + Project Stage + Policy)."""
    resolver = StageResolverService(db=db, workspace_id=member.workspace_id, user_id=member.user_id)
    return resolver.resolve_context(project_id=project_id)


@router.get("/policy/{stage}", response_model=StagePolicySpec)
def get_stage_policy(
    stage: str,
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    """Lấy quy chuẩn chính sách chi tiết của một Stage cụ thể (S0 đến S6)."""
    return ManagementPolicyEngine.get_policy(stage)


@router.get("/list-stages", response_model=List[StageSummaryResponse])
def list_all_stages(
    member: WorkspaceMember = Depends(get_current_workspace_member),
):
    """Lấy danh sách tóm tắt cả 7 Stage chuẩn của COSA Lifecycle."""
    return ManagementPolicyEngine.list_stage_summaries()


@router.patch("/project/{project_id}", response_model=StageContextResponse)
def update_project_stage_info(
    project_id: int,
    payload: ProjectStageUpdateRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    """Cập nhật Stage, Mục tiêu và Rào cản rủi ro (Constraints) của một Project."""
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.workspace_id == member.workspace_id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found in current workspace"
        )

    if payload.project_stage is not None:
        if project.project_stage != payload.project_stage.value:
            project.project_stage = payload.project_stage.value
            project.stage_started_at = datetime.utcnow()

    if payload.stage_goal is not None:
        project.stage_goal = payload.stage_goal

    if payload.critical_constraints is not None:
        project.critical_constraints = payload.critical_constraints

    if payload.exit_criteria is not None:
        project.exit_criteria_jsonb = payload.exit_criteria

    if payload.stage_metadata is not None:
        merged_meta = dict(project.stage_metadata or {})
        merged_meta.update(payload.stage_metadata)
        project.stage_metadata = merged_meta

    db.commit()
    db.refresh(project)

    resolver = StageResolverService(db=db, workspace_id=member.workspace_id, user_id=member.user_id)
    return resolver.resolve_context(project_id=project.id)
