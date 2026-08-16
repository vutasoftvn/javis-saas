from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.core.snowflake import generate_snowflake_id
from app.db.models import (
    WorkspaceMember,
    Brain,
    Project,
    Initiative,
)
from app.modules.strategy.project_classifier_service import ProjectClassifierService
from app.modules.strategy.methodology_router import MethodologyRouterService
from app.modules.strategy.assisted_analyzer import AssistedAnalyzerService
from app.core.feature_flags import (
    require_flag,
    FLAG_PROJECT_CLASSIFIER_V12,
    FLAG_METHODOLOGY_ROUTER_V12,
    FLAG_ASSISTED_TERRA_V12,
)

# Re-export schemas for backward compatibility with tests & external callers
from app.modules.strategy.schemas import (
    ObjectiveCreate,
    CanvasCreate,
    CanvasUpdate,
    RevisionCreate,
    ApproveRevisionBody,
    RequestChangesBody,
    CoreValueIn,
    FoundationSave,
    PromptTemplateUpdate,
    AiAnalysisRequest,
    AnalysisExportRequest,
    AnalysisImportRequest,
    ProjectCreate,
    ProjectUpdate,
    ProjectClassifyRequest,
    MethodologyRouteRequest,
    InitiativeCreate,
    InitiativeUpdate,
)

# Re-export route handlers from domain sub-routers
from app.modules.strategy.routers.canvas_router import (
    router as canvas_router,
    list_bsc_scorecards,
    list_strategic_objectives,
    create_strategic_objective,
    list_canvases,
    create_canvas,
    get_canvas_detail,
    update_canvas,
    delete_canvas,
    create_revision,
    get_revision_detail,
    submit_revision_for_review,
    approve_revision,
    request_changes_on_revision,
    save_foundation,
)
from app.modules.strategy.routers.analysis_router import (
    router as analysis_router,
    create_decision,
    list_decisions,
    _serialize_decision,
)
from app.modules.strategy.routers.project_orchestration_router import router as project_orchestration_router
from app.modules.strategy.routers.template_router import router as template_router

router = APIRouter()

# Include modular domain sub-routers
router.include_router(canvas_router)
router.include_router(analysis_router)
router.include_router(project_orchestration_router)
router.include_router(template_router)


def _serialize_project(project: Project) -> dict:
    return {
        "id": str(project.id),
        "title": getattr(project, 'title', getattr(project, 'name', '')),
        "description": getattr(project, 'description', None),
        "phase": getattr(project, 'phase', None),
        "status": getattr(project, 'status', 'active'),
        "start_date": project.start_date.isoformat() if getattr(project, 'start_date', None) else None,
        "end_date": project.end_date.isoformat() if getattr(project, 'end_date', None) else None,
        "created_at": project.created_at.isoformat() if getattr(project, 'created_at', None) else None,
    }


def _serialize_initiative(initiative: Initiative) -> dict:
    return {
        "id": str(initiative.id),
        "project_id": str(initiative.project_id) if initiative.project_id else None,
        "title": initiative.title,
        "status": initiative.status,
        "owner_id": str(initiative.owner_id) if initiative.owner_id else None,
        "created_at": initiative.created_at.isoformat() if initiative.created_at else None,
    }


@router.get("/projects")
def list_projects(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    projects = db.query(Project).filter(Project.workspace_id == workspace_id).all()
    return {"projects": [_serialize_project(p) for p in projects]}


@router.post("/projects")
def create_project(
    workspace_id: int,
    data: ProjectCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    brain = db.query(Brain).filter(Brain.workspace_id == workspace_id).first()
    title_val = data.title or data.name or "Untitled Project"
    kwargs = {
        "workspace_id": workspace_id,
        "brain_id": brain.id if brain else generate_snowflake_id(),
        "title": title_val,
        "status": data.status or "active",
    }
    if getattr(data, "phase", None) is not None:
        kwargs["phase"] = data.phase
    if getattr(data, "description", None) is not None:
        kwargs["description"] = data.description
    if getattr(data, "start_date", None) is not None:
        kwargs["start_date"] = data.start_date
    if getattr(data, "end_date", None) is not None:
        kwargs["end_date"] = data.end_date
    project = Project(**kwargs)
    db.add(project)
    db.commit()
    db.refresh(project)
    return _serialize_project(project)


# ==========================================
# mCOSA V12 Single Project Journey & Initiatives Endpoints
# ==========================================

@router.post("/projects/{project_id}/classify")
def classify_project_endpoint(
    project_id: int,
    workspace_id: int,
    data: Optional[ProjectClassifyRequest] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_PROJECT_CLASSIFIER_V12, workspace_id)
    service = ProjectClassifierService(db=db, workspace_id=workspace_id, user_id=member.user_id)
    return service.classify_project(
        project_id=project_id,
        title_override=data.title_override if data else None,
        description_override=data.description_override if data else None,
    )


@router.get("/projects/{project_id}/methodology")
def get_methodology_plan_endpoint(
    project_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_METHODOLOGY_ROUTER_V12, workspace_id)
    service = MethodologyRouterService(db=db, workspace_id=workspace_id, user_id=member.user_id)
    plan = service.get_plan(project_id=project_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Methodology plan not found")
    return plan


@router.post("/projects/{project_id}/methodology")
def route_methodology_endpoint(
    project_id: int,
    workspace_id: int,
    data: Optional[MethodologyRouteRequest] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_METHODOLOGY_ROUTER_V12, workspace_id)
    service = MethodologyRouterService(db=db, workspace_id=workspace_id, user_id=member.user_id)
    return service.route_methodology(
        project_id=project_id,
        custom_methodologies=data.custom_methodologies if data else None,
        custom_rules=data.custom_rules if data else None,
        rationale_override=data.rationale_override if data else None,
    )


@router.post("/analysis/export")
def export_analysis_prompt_endpoint(
    workspace_id: int,
    data: Optional[AnalysisExportRequest] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_ASSISTED_TERRA_V12, workspace_id)
    service = AssistedAnalyzerService(db=db, workspace_id=workspace_id, user_id=member.user_id)
    return service.export_analysis_prompt(
        project_id=data.project_id if data else None,
        canvas_id=data.canvas_id if data else None,
    )


@router.post("/analysis/import")
def import_analysis_result_endpoint(
    workspace_id: int,
    data: AnalysisImportRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    require_flag(db, FLAG_ASSISTED_TERRA_V12, workspace_id)
    service = AssistedAnalyzerService(db=db, workspace_id=workspace_id, user_id=member.user_id)
    return service.import_analysis_result(
        raw_input=data.raw_input,
        project_id=data.project_id,
        canvas_id=data.canvas_id,
    )


@router.get("/initiatives")
def list_initiatives(
    workspace_id: int,
    project_id: Optional[int] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    query = db.query(Initiative).filter(Initiative.workspace_id == workspace_id)
    if project_id:
        query = query.filter(Initiative.project_id == project_id)
    initiatives = query.order_by(Initiative.created_at.desc()).all()
    return {"initiatives": [_serialize_initiative(i) for i in initiatives]}


@router.post("/initiatives")
def create_initiative(
    workspace_id: int,
    data: InitiativeCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    brain = db.query(Brain).filter(Brain.workspace_id == workspace_id).first()
    initiative = Initiative(
        workspace_id=workspace_id,
        brain_id=brain.id if brain else generate_snowflake_id(),
        project_id=data.project_id,
        title=data.title,
        status=data.status or "active",
        owner_id=data.owner_id or member.user_id,
    )
    db.add(initiative)
    db.commit()
    db.refresh(initiative)
    return _serialize_initiative(initiative)


@router.put("/initiatives/{initiative_id}")
def update_initiative(
    initiative_id: int,
    workspace_id: int,
    data: InitiativeUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    initiative = db.query(Initiative).filter(Initiative.id == initiative_id, Initiative.workspace_id == workspace_id).first()
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")

    if data.title is not None:
        initiative.title = data.title
    if data.status is not None:
        initiative.status = data.status
    if data.owner_id is not None:
        initiative.owner_id = data.owner_id

    db.commit()
    db.refresh(initiative)
    return _serialize_initiative(initiative)


@router.delete("/initiatives/{initiative_id}")
def delete_initiative(
    initiative_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    initiative = db.query(Initiative).filter(Initiative.id == initiative_id, Initiative.workspace_id == workspace_id).first()
    if not initiative:
        raise HTTPException(status_code=404, detail="Initiative not found")

    db.delete(initiative)
    db.commit()
    return {"status": "deleted", "id": str(initiative_id)}
