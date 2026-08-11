from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.modules.outcomes import service
from app.modules.outcomes.models import RunStep, Artifact

router = APIRouter()


class OutcomeCreate(BaseModel):
    title: str
    desired_result: str
    project_id: Optional[int] = None
    acceptance_criteria: Optional[Dict[str, Any]] = None


class ArtifactCreate(BaseModel):
    title: str
    type: str  # document, spreadsheet, code, research_bundle, media, external_action_receipt, dashboard_snapshot
    outcome_id: Optional[int] = None
    run_id: Optional[int] = None
    local_uri: Optional[str] = None
    object_storage_uri: Optional[str] = None
    content_hash: Optional[str] = None


@router.post("/outcomes", status_code=status.HTTP_201_CREATED)
def create_new_outcome(
    data: OutcomeCreate,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    outcome = service.create_outcome(
        db=db,
        workspace_id=workspace_id,
        user_id=member.user_id,
        title=data.title,
        desired_result=data.desired_result,
        project_id=data.project_id,
        acceptance_criteria=data.acceptance_criteria,
    )
    return {
        "id": str(outcome.id),
        "title": outcome.title,
        "desired_result": outcome.desired_result,
        "status": outcome.status,
        "created_at": outcome.created_at.isoformat(),
    }


@router.get("/outcomes")
def list_workspace_outcomes(
    workspace_id: int,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = 50,
    offset: int = 0,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    l = int(limit) if isinstance(limit, (int, str)) and str(limit).isdigit() else 50
    o = int(offset) if isinstance(offset, (int, str)) and str(offset).isdigit() else 0

    outcomes = service.list_outcomes(
        db=db,
        workspace_id=workspace_id,
        status=status_filter,
        limit=l,
        offset=o,
    )
    return {
        "total": len(outcomes),
        "outcomes": [
            {
                "id": str(o.id),
                "title": o.title,
                "desired_result": o.desired_result,
                "project_id": str(o.project_id) if o.project_id else None,
                "status": o.status,
                "created_at": o.created_at.isoformat(),
            }
            for o in outcomes
        ],
    }


@router.get("/outcomes/{outcome_id}")
def get_outcome_details(
    outcome_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    outcome = service.get_outcome(db=db, outcome_id=outcome_id, workspace_id=workspace_id)
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")

    return {
        "id": str(outcome.id),
        "title": outcome.title,
        "desired_result": outcome.desired_result,
        "acceptance_criteria": outcome.acceptance_criteria,
        "project_id": str(outcome.project_id) if outcome.project_id else None,
        "status": outcome.status,
        "created_at": outcome.created_at.isoformat(),
    }


@router.post("/outcomes/{outcome_id}/runs", status_code=status.HTTP_201_CREATED)
def trigger_outcome_run(
    outcome_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    try:
        run = service.create_outcome_run(
            db=db,
            outcome_id=outcome_id,
            workspace_id=workspace_id,
            user_id=member.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {
        "id": str(run.id),
        "outcome_id": str(run.outcome_id),
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "created_at": run.created_at.isoformat(),
    }


@router.get("/runs/{run_id}")
def get_outcome_run_details(
    run_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    run = service.get_run(db=db, run_id=run_id, workspace_id=workspace_id)
    if not run:
        raise HTTPException(status_code=404, detail="Outcome run not found")

    steps = db.query(RunStep).filter(RunStep.run_id == run_id).order_by(RunStep.created_at.asc()).all()
    artifacts = db.query(Artifact).filter(Artifact.run_id == run_id).all()

    return {
        "id": str(run.id),
        "outcome_id": str(run.outcome_id),
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "created_at": run.created_at.isoformat(),
        "steps": [
            {
                "id": str(s.id),
                "type": s.type,
                "status": s.status,
                "risk_level": s.risk_level,
                "expected_output": s.expected_output,
            }
            for s in steps
        ],
        "artifacts": [
            {
                "id": str(a.id),
                "title": a.title,
                "type": a.type,
                "status": a.status,
            }
            for a in artifacts
        ],
    }


@router.get("/runs/{run_id}/events")
def list_outcome_run_events(
    run_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    events = service.list_run_events(db=db, run_id=run_id, workspace_id=workspace_id)
    return {
        "total": len(events),
        "events": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "payload": e.payload_jsonb,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
    }


@router.post("/artifacts", status_code=status.HTTP_201_CREATED)
def create_new_artifact(
    data: ArtifactCreate,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    artifact = service.create_artifact(
        db=db,
        workspace_id=workspace_id,
        user_id=member.user_id,
        type=data.type,
        title=data.title,
        outcome_id=data.outcome_id,
        run_id=data.run_id,
        local_uri=data.local_uri,
        object_storage_uri=data.object_storage_uri,
        content_hash=data.content_hash,
    )
    return {
        "id": str(artifact.id),
        "title": artifact.title,
        "type": artifact.type,
        "status": artifact.status,
        "created_at": artifact.created_at.isoformat(),
    }


@router.get("/artifacts/{artifact_id}")
def get_artifact_details(
    artifact_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    artifact = service.get_artifact(db=db, artifact_id=artifact_id, workspace_id=workspace_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return {
        "id": str(artifact.id),
        "outcome_id": str(artifact.outcome_id) if artifact.outcome_id else None,
        "run_id": str(artifact.run_id) if artifact.run_id else None,
        "type": artifact.type,
        "title": artifact.title,
        "local_uri": artifact.local_uri,
        "object_storage_uri": artifact.object_storage_uri,
        "status": artifact.status,
        "created_at": artifact.created_at.isoformat(),
    }


@router.get("/artifacts")
def list_workspace_artifacts(
    workspace_id: int,
    type_filter: Optional[str] = Query(None, alias="type"),
    limit: int = 50,
    offset: int = 0,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    l = int(limit) if isinstance(limit, (int, str)) and str(limit).isdigit() else 50
    o = int(offset) if isinstance(offset, (int, str)) and str(offset).isdigit() else 0

    artifacts = service.list_artifacts(
        db=db,
        workspace_id=workspace_id,
        type=type_filter,
        limit=l,
        offset=o,
    )
    return {
        "total": len(artifacts),
        "artifacts": [
            {
                "id": str(a.id),
                "title": a.title,
                "type": a.type,
                "outcome_id": str(a.outcome_id) if a.outcome_id else None,
                "run_id": str(a.run_id) if a.run_id else None,
                "status": a.status,
                "created_at": a.created_at.isoformat(),
            }
            for a in artifacts
        ],
    }
