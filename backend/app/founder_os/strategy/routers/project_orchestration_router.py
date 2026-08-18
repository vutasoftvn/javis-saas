from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.core.authz import authorize
from app.db.models import Brain, WorkspaceMember
from app.founder_os.strategy.models import MvpStage, StageRevision, StageServiceAssessment
from app.founder_os.strategy.project_orchestration_service import ProjectOrchestrationService
from app.founder_os.strategy.routing_service import RoutingService
from app.founder_os.strategy.schemas.project_orchestration_schemas import (
    ApplyStageRevisionRequest,
    GenerateRoadmapRequest,
    RoadmapDraft,
    ServiceAssessmentConfirmRequest,
    StagePlanDraft,
    StageRevisionChange,
    Week13ConfirmRequest,
)

router = APIRouter()


def _service(workspace_id: int, member: WorkspaceMember, db: Session) -> ProjectOrchestrationService:
    brain = db.query(Brain).filter(Brain.workspace_id == workspace_id).first()
    if not brain:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace brain not found")
    return ProjectOrchestrationService(db, workspace_id, brain.id, member.user_id, member.role)


def _routing_service(workspace_id: int, member: WorkspaceMember, db: Session) -> RoutingService:
    brain = db.query(Brain).filter(Brain.workspace_id == workspace_id).first()
    if not brain:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace brain not found")
    return RoutingService(db, workspace_id, brain.id, member.user_id)


def _serialize_assessment(a: StageServiceAssessment) -> dict:
    return {
        "id": str(a.id),
        "capability_id": str(a.capability_id),
        "disposition": a.disposition,
        "reason": a.reason,
        "risk_level": a.risk_level,
        "expected_output": a.expected_output,
        "execution_mode": a.execution_mode,
        "professional_review_required": a.professional_review_required,
        "is_available": a.is_available,
        "status": a.status,
    }


def _serialize_stage(s: MvpStage) -> dict:
    scope = s.scope_jsonb or {}
    exit_criteria = s.exit_criteria_jsonb or {}
    return {
        "id": str(s.id),
        "sequence_no": s.sequence_no,
        "title": s.title,
        "hypothesis": s.hypothesis,
        "scope": scope.get("items", []),
        "non_goals": scope.get("non_goals", []),
        "exit_criteria": exit_criteria.get("items", []),
        "status": s.status,
    }


def _serialize_revision(r: StageRevision) -> dict:
    return {
        "id": str(r.id),
        "revision_no": r.revision_no,
        "change_type": r.change_type,
        "before": r.before_snapshot_jsonb,
        "after": r.after_snapshot_jsonb,
        "impact_preview": r.impact_preview_jsonb,
        "status": r.status,
    }


@router.get("/projects/{project_id}/stages")
def list_project_stages(project_id: int, workspace_id: int,
                        member: WorkspaceMember = Depends(get_current_workspace_member),
                        db: Session = Depends(get_db)):
    stages = _service(workspace_id, member, db).list_stages(project_id)
    return {"stages": [_serialize_stage(s) for s in stages]}


@router.get("/projects/{project_id}/mvp-roadmap")
def get_mvp_roadmap(project_id: int, workspace_id: int,
                    member: WorkspaceMember = Depends(get_current_workspace_member),
                    db: Session = Depends(get_db)):
    stages = _service(workspace_id, member, db).list_stages(project_id)
    return {"stages": [_serialize_stage(s) for s in stages]}


@router.post("/projects/{project_id}/mvp-roadmap:generate")
def generate_mvp_roadmap(project_id: int, workspace_id: int,
                          data: Optional[GenerateRoadmapRequest] = None,
                          member: WorkspaceMember = Depends(get_current_workspace_member),
                          db: Session = Depends(get_db)):
    authorize(member, "project.update")
    instruction = data.instruction if data else None
    draft = _service(workspace_id, member, db).generate_roadmap(project_id, instruction=instruction)
    return draft.model_dump()


@router.put("/projects/{project_id}/mvp-roadmap")
def save_mvp_roadmap_draft(project_id: int, workspace_id: int, data: RoadmapDraft,
                            member: WorkspaceMember = Depends(get_current_workspace_member),
                            db: Session = Depends(get_db)):
    authorize(member, "project.update")
    stages = _service(workspace_id, member, db).save_roadmap_draft(project_id, data)
    return {"stages": [_serialize_stage(s) for s in stages]}


@router.post("/projects/{project_id}/mvp-roadmap:confirm")
def confirm_mvp_roadmap(project_id: int, workspace_id: int,
                         member: WorkspaceMember = Depends(get_current_workspace_member),
                         db: Session = Depends(get_db)):
    authorize(member, "project.update")
    stages = _service(workspace_id, member, db).confirm_roadmap(project_id)
    return {"stages": [_serialize_stage(s) for s in stages]}


@router.post("/projects/{project_id}/stages/{stage_id}:plan")
def plan_mvp_stage(project_id: int, stage_id: int, workspace_id: int,
                    member: WorkspaceMember = Depends(get_current_workspace_member),
                    db: Session = Depends(get_db)):
    authorize(member, "project.update")
    draft = _routing_service(workspace_id, member, db).plan_stage(stage_id)
    return draft.model_dump()


@router.post("/projects/{project_id}/stages/{stage_id}:activate")
def activate_mvp_stage(project_id: int, stage_id: int, workspace_id: int, data: StagePlanDraft,
                        member: WorkspaceMember = Depends(get_current_workspace_member),
                        db: Session = Depends(get_db)):
    authorize(member, "project.update")
    result = _service(workspace_id, member, db).activate_stage(project_id, stage_id, data)
    return {
        "stage": _serialize_stage(result["stage"]),
        "okr_cycle_id": str(result["okr_cycle"].id),
        "weekly_plan_count": len(result["weekly_plans"]),
    }


@router.post("/projects/{project_id}/stages/{stage_id}/service-assessment:generate")
def generate_stage_service_assessment(project_id: int, stage_id: int, workspace_id: int,
                                       member: WorkspaceMember = Depends(get_current_workspace_member),
                                       db: Session = Depends(get_db)):
    assessments = _routing_service(workspace_id, member, db).generate_assessment(stage_id)
    return {"assessments": [_serialize_assessment(a) for a in assessments]}


@router.post("/projects/{project_id}/stages/{stage_id}/service-assessment:confirm")
def confirm_stage_service_assessment(project_id: int, stage_id: int, workspace_id: int,
                                      data: ServiceAssessmentConfirmRequest,
                                      member: WorkspaceMember = Depends(get_current_workspace_member),
                                      db: Session = Depends(get_db)):
    assessments = _routing_service(workspace_id, member, db).confirm_assessment(stage_id, data.decisions)
    return {"assessments": [_serialize_assessment(a) for a in assessments]}


@router.post("/stages/{stage_id}:preview-revision")
def preview_stage_revision(stage_id: int, workspace_id: int, data: StageRevisionChange,
                            member: WorkspaceMember = Depends(get_current_workspace_member),
                            db: Session = Depends(get_db)):
    revision = _service(workspace_id, member, db).preview_stage_revision(stage_id, data)
    return _serialize_revision(revision)


@router.post("/stages/{stage_id}:apply-revision")
def apply_stage_revision(stage_id: int, workspace_id: int, data: ApplyStageRevisionRequest,
                          member: WorkspaceMember = Depends(get_current_workspace_member),
                          db: Session = Depends(get_db)):
    stage = _service(workspace_id, member, db).apply_stage_revision(stage_id, int(data.revision_id))
    return _serialize_stage(stage)


@router.post("/stages/{stage_id}/week-13:generate")
def generate_week13(stage_id: int, workspace_id: int,
                     member: WorkspaceMember = Depends(get_current_workspace_member),
                     db: Session = Depends(get_db)):
    return _service(workspace_id, member, db).generate_week13(stage_id)


@router.post("/stages/{stage_id}/week-13:confirm")
def confirm_week13(stage_id: int, workspace_id: int, data: Week13ConfirmRequest,
                    member: WorkspaceMember = Depends(get_current_workspace_member),
                    db: Session = Depends(get_db)):
    result = _service(workspace_id, member, db).confirm_week13(stage_id, data.decision, data.rationale)
    return {
        "stage": _serialize_stage(result["stage"]),
        "gate_decision": result["gate_decision"],
    }
