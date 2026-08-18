from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.db.models import (
    WorkspaceMember,
    StrategyCanvas,
    StrategyRevision,
    StrategyFoundation,
    CoreValue,
    BscScorecard,
    StrategicObjective,
)
from app.founder_os.strategy.strategy_canvas_service import StrategyCanvasService
from app.founder_os.strategy.foundation_ai_service import generate_foundation_suggestion
from app.founder_os.strategy.schemas.canvas_schemas import (
    ObjectiveCreate,
    CanvasCreate,
    CanvasUpdate,
    RevisionCreate,
    ApproveRevisionBody,
    RequestChangesBody,
    FoundationSave,
)

router = APIRouter()

VALID_PERSPECTIVES = {"financial", "customer_market", "internal_process", "learning_growth"}


def _service(workspace_id: int, member: WorkspaceMember, db: Session) -> StrategyCanvasService:
    return StrategyCanvasService(db=db, user_id=member.user_id, workspace_id=workspace_id, role=member.role)


def _serialize_canvas(canvas: StrategyCanvas) -> dict:
    return {
        "id": str(canvas.id),
        "name": canvas.name,
        "description": canvas.description,
        "status": canvas.status,
        "created_at": canvas.created_at,
    }


def _serialize_revision(revision: StrategyRevision) -> dict:
    return {
        "id": str(revision.id),
        "canvas_id": str(revision.canvas_id),
        "revision_no": revision.revision_no,
        "status": revision.status,
        "parent_revision_id": str(revision.parent_revision_id) if revision.parent_revision_id else None,
        "approved_by": str(revision.approved_by) if revision.approved_by else None,
        "approved_at": revision.approved_at,
        "created_at": revision.created_at,
    }


def _serialize_core_value(value: CoreValue) -> dict:
    return {
        "slot_no": value.slot_no,
        "title": value.title,
        "description": value.description,
        "decision_rule": value.decision_rule,
    }


@router.get("/scorecards")
def list_bsc_scorecards(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    scorecards = db.query(BscScorecard).filter(BscScorecard.workspace_id == workspace_id).all()
    return {"scorecards": [{"id": str(s.id), "status": s.status} for s in scorecards]}


@router.get("/objectives")
def list_strategic_objectives(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    objectives = db.query(StrategicObjective).filter(StrategicObjective.workspace_id == workspace_id).all()
    return {"objectives": [{"id": str(o.id), "perspective": o.perspective, "statement": o.statement} for o in objectives]}


@router.post("/objectives")
def create_strategic_objective(
    workspace_id: int,
    data: ObjectiveCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    scorecard = db.query(BscScorecard).filter(
        BscScorecard.id == data.scorecard_id,
        BscScorecard.workspace_id == workspace_id
    ).first()
    if not scorecard:
        raise HTTPException(status_code=404, detail="Scorecard not found for this workspace")

    if data.perspective not in VALID_PERSPECTIVES:
        raise HTTPException(
            status_code=422,
            detail=f"perspective must be one of {sorted(VALID_PERSPECTIVES)}"
        )

    new_obj = StrategicObjective(
        workspace_id=workspace_id,
        scorecard_id=data.scorecard_id,
        perspective=data.perspective,
        statement=data.statement,
        owner_id=data.owner_id
    )
    db.add(new_obj)
    db.commit()
    db.refresh(new_obj)
    return {"id": str(new_obj.id), "statement": new_obj.statement}


@router.get("/canvases")
def list_canvases(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    svc = _service(workspace_id, member, db)
    canvases = svc.list_canvases()
    return {"canvases": [_serialize_canvas(c) for c in canvases]}


@router.post("/canvases")
def create_canvas(
    workspace_id: int,
    data: CanvasCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    svc = _service(workspace_id, member, db)
    canvas = svc.create_canvas(name=data.name, description=data.description)
    return _serialize_canvas(canvas)


@router.post("/canvases/{canvas_id}/generate-ai-foundation")
async def generate_ai_foundation(
    canvas_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    svc = _service(workspace_id, member, db)
    canvas = svc.get_canvas(canvas_id)
    foundation = await generate_foundation_suggestion(db, workspace_id, canvas.name, canvas.description)
    return {"foundation": foundation}


@router.get("/canvases/{canvas_id}")
def get_canvas_detail(
    canvas_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    svc = _service(workspace_id, member, db)
    canvas = svc.get_canvas(canvas_id)
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")
    revisions = svc.list_revisions(canvas_id)
    active_rev = svc.get_active_revision(canvas_id)
    return {
        "canvas": _serialize_canvas(canvas),
        "active_revision": _serialize_revision(active_rev) if active_rev else None,
        "revisions": [_serialize_revision(r) for r in revisions],
    }


@router.put("/canvases/{canvas_id}")
def update_canvas(
    canvas_id: int,
    workspace_id: int,
    data: CanvasUpdate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    svc = _service(workspace_id, member, db)
    canvas = svc.update_canvas(canvas_id, name=data.name, description=data.description)
    if not canvas:
        raise HTTPException(status_code=404, detail="Canvas not found")
    return _serialize_canvas(canvas)


@router.delete("/canvases/{canvas_id}")
def delete_canvas(
    canvas_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    svc = _service(workspace_id, member, db)
    svc.delete_canvas(canvas_id)
    return {"status": "deleted", "id": str(canvas_id)}


@router.post("/canvases/{canvas_id}/revisions")
def create_revision(
    canvas_id: int,
    workspace_id: int,
    data: Optional[RevisionCreate] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    svc = _service(workspace_id, member, db)
    base_revision_id = int(data.base_revision_id) if data and data.base_revision_id else None
    rev = svc.create_revision(canvas_id, base_revision_id=base_revision_id)
    return _serialize_revision(rev)


@router.get("/revisions/{revision_id}")
def get_revision_detail(
    revision_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    svc = _service(workspace_id, member, db)
    rev = svc.get_revision(revision_id)
    if not rev:
        raise HTTPException(status_code=404, detail="Revision not found")
    foundation, values = svc.get_foundation(revision_id)
    return {
        **_serialize_revision(rev),
        "foundation": {
            "vision": foundation.vision if foundation else None,
            "mission": foundation.mission if foundation else None,
            "values": [_serialize_core_value(v) for v in values],
        },
    }


@router.post("/revisions/{revision_id}/submit-review")
def submit_revision_for_review(
    revision_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    svc = _service(workspace_id, member, db)
    rev = svc.submit_review(revision_id)
    return _serialize_revision(rev)


@router.post("/revisions/{revision_id}/approve")
def approve_revision(
    revision_id: int,
    workspace_id: int,
    data: Optional[ApproveRevisionBody] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    svc = _service(workspace_id, member, db)
    rev = svc.approve_revision(revision_id, note=data.note if data else None)
    return _serialize_revision(rev)


@router.post("/revisions/{revision_id}/request-changes")
def request_changes_on_revision(
    revision_id: int,
    workspace_id: int,
    data: RequestChangesBody,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    svc = _service(workspace_id, member, db)
    rev = svc.request_changes(revision_id, reason=data.reason)
    return _serialize_revision(rev)


@router.put("/revisions/{revision_id}/foundation")
def save_foundation(
    revision_id: int,
    workspace_id: int,
    data: FoundationSave,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    svc = _service(workspace_id, member, db)
    foundation, core_values = svc.save_foundation(
        revision_id=revision_id,
        vision=data.vision,
        mission=data.mission,
        values=[v.model_dump() for v in data.values],
    )
    return {
        "revision_id": str(revision_id),
        "vision": foundation.vision,
        "mission": foundation.mission,
        "values": [_serialize_core_value(v) for v in core_values],
    }
