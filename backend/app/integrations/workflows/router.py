from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.core.tenancy import resolve_workflow_run_workspace_id
from app.core.audit import write_audit_log
from app.db.models import WorkspaceMember, WorkflowDefinition, WorkflowVersion, WorkflowRun, WorkflowStep, WorkflowApproval, Brain

router = APIRouter()

class WorkflowDefinitionCreate(BaseModel):
    brain_id: int
    slug: str

class WorkflowVersionCreate(BaseModel):
    graph_jsonb: dict

class WorkflowRunCreate(BaseModel):
    input_jsonb: Optional[Dict[str, Any]] = None

@router.get("/definitions")
def list_workflow_definitions(
    workspace_id: int,
    brain_id: Optional[int] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    query = db.query(WorkflowDefinition).join(Brain)
    query = query.filter(Brain.workspace_id == workspace_id)
    if brain_id:
        query = query.filter(WorkflowDefinition.brain_id == brain_id)
    
    definitions = query.all()
    return {
        "definitions": [
            {
                "id": str(d.id),
                "brain_id": str(d.brain_id),
                "slug": d.slug,
                "current_version_id": str(d.current_version_id) if d.current_version_id else None,
                "created_at": d.created_at.isoformat()
            } for d in definitions
        ]
    }

@router.post("/definitions", status_code=status.HTTP_201_CREATED)
def create_workflow_definition(
    workspace_id: int,
    data: WorkflowDefinitionCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    brain = db.query(Brain).filter(Brain.id == data.brain_id, Brain.workspace_id == workspace_id).first()
    if not brain:
        raise HTTPException(status_code=404, detail="Brain not found or access denied")
        
    definition = WorkflowDefinition(brain_id=data.brain_id, slug=data.slug)
    db.add(definition)
    db.commit()
    db.refresh(definition)

    write_audit_log(
        db=db,
        actor_type="user",
        actor_id=member.user_id,
        action="workflow.definition.create",
        target_type="workflow_definition",
        target_id=definition.id,
        metadata_jsonb={"workspace_id": str(workspace_id), "slug": data.slug}
    )
    
    return {
        "id": str(definition.id),
        "brain_id": str(definition.brain_id),
        "slug": definition.slug,
        "created_at": definition.created_at.isoformat()
    }

@router.post("/definitions/{definition_id}/versions", status_code=status.HTTP_201_CREATED)
def create_workflow_version(
    workspace_id: int,
    definition_id: int,
    data: WorkflowVersionCreate,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    definition = db.query(WorkflowDefinition).join(Brain).filter(
        WorkflowDefinition.id == definition_id,
        Brain.workspace_id == workspace_id
    ).first()
    if not definition:
        raise HTTPException(status_code=404, detail="Definition not found")
        
    last_version = db.query(WorkflowVersion).filter(WorkflowVersion.definition_id == definition_id).order_by(WorkflowVersion.version_no.desc()).first()
    next_no = last_version.version_no + 1 if last_version else 1
    
    version = WorkflowVersion(
        definition_id=definition_id,
        graph_jsonb=data.graph_jsonb,
        version_no=next_no
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    
    # Update current version
    definition.current_version_id = version.id
    db.commit()
    
    return {
        "id": str(version.id),
        "version_no": version.version_no,
        "created_at": version.created_at.isoformat()
    }

@router.post("/definitions/{definition_id}/run", status_code=status.HTTP_201_CREATED)
def trigger_workflow_run(
    definition_id: int,
    workspace_id: int,
    data: Optional[WorkflowRunCreate] = None,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    definition = db.query(WorkflowDefinition).join(Brain).filter(
        WorkflowDefinition.id == definition_id,
        Brain.workspace_id == workspace_id
    ).first()
    if not definition:
        raise HTTPException(status_code=404, detail="Workflow definition not found")

    if not definition.current_version_id:
        raise HTTPException(status_code=400, detail="Workflow definition has no versions")

    run = WorkflowRun(
        version_id=definition.current_version_id,
        status="running",
        trigger="manual",
        input_jsonb=data.input_jsonb if data else {}
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    # Initial start step
    step = WorkflowStep(
        run_id=run.id,
        node_id="start",
        status="completed",
        attempt=1,
        output_jsonb={"result": "Workflow initialized"}
    )
    db.add(step)
    db.commit()

    write_audit_log(
        db=db,
        actor_type="user",
        actor_id=member.user_id,
        action="workflow.run.start",
        target_type="workflow_run",
        target_id=run.id,
        metadata_jsonb={"workspace_id": str(workspace_id), "definition_id": str(definition_id), "slug": definition.slug}
    )

    return {
        "id": str(run.id),
        "version_id": str(run.version_id),
        "status": run.status,
        "trigger": run.trigger,
        "created_at": run.created_at.isoformat()
    }

@router.get("/runs")
def list_workflow_runs(
    workspace_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    brain_ids = [b.id for b in db.query(Brain.id).filter(Brain.workspace_id == workspace_id).all()]
    
    query = db.query(WorkflowRun).join(
        WorkflowVersion, WorkflowRun.version_id == WorkflowVersion.id
    ).join(
        WorkflowDefinition, WorkflowVersion.definition_id == WorkflowDefinition.id
    ).filter(
        WorkflowDefinition.brain_id.in_(brain_ids) if brain_ids else False
    ).order_by(WorkflowRun.created_at.desc())

    total = query.count() if brain_ids else 0
    runs = query.offset(offset).limit(limit).all() if brain_ids else []

    return {
        "total": total,
        "runs": [
            {
                "id": str(r.id),
                "version_id": str(r.version_id),
                "status": r.status,
                "trigger": r.trigger,
                "created_at": r.created_at.isoformat()
            } for r in runs
        ]
    }

@router.get("/runs/{run_id}")
def get_workflow_run(
    run_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run or resolve_workflow_run_workspace_id(db, run) != workspace_id:
        raise HTTPException(status_code=404, detail="Run not found")

    steps = db.query(WorkflowStep).filter(WorkflowStep.run_id == run_id).order_by(WorkflowStep.created_at.asc()).all()
    
    return {
        "run": {
            "id": str(run.id),
            "status": run.status,
            "trigger": run.trigger
        },
        "steps": [
            {
                "id": str(s.id),
                "node_id": s.node_id,
                "status": s.status,
                "attempt": s.attempt,
                "output_jsonb": s.output_jsonb,
                "created_at": s.created_at.isoformat()
            }
            for s in steps
        ]
    }

@router.post("/runs/{run_id}/resume")
def resume_workflow_run(
    run_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
    if not run or resolve_workflow_run_workspace_id(db, run) != workspace_id:
        raise HTTPException(status_code=404, detail="Run not found")
        
    if run.status != "paused":
        raise HTTPException(status_code=400, detail="Run is not paused")
        
    run.status = "running"
    db.commit()

    write_audit_log(
        db=db,
        actor_type="user",
        actor_id=member.user_id,
        action="workflow.run.resume",
        target_type="workflow_run",
        target_id=run.id,
        metadata_jsonb={"workspace_id": str(workspace_id)}
    )

    return {"status": "success", "message": "Run resumed"}

# ====================================================
# Approvals & Human-in-the-loop Governance
# ====================================================

@router.get("/approvals")
def list_workflow_approvals(
    workspace_id: int,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    # Scoped the same way list_workflow_runs derives workspace ownership: join
    # through to WorkflowDefinition.brain_id BEFORE paginating. Filtering after
    # offset/limit (as this endpoint previously did) silently drops this
    # workspace's own approvals once enough other tenants' rows sort ahead of
    # them - a real governance bug, not just a style issue.
    brain_ids = [b.id for b in db.query(Brain.id).filter(Brain.workspace_id == workspace_id).all()]

    query = db.query(
        WorkflowApproval, WorkflowStep
    ).join(
        WorkflowStep, WorkflowApproval.step_id == WorkflowStep.id
    ).join(
        WorkflowRun, WorkflowStep.run_id == WorkflowRun.id
    ).join(
        WorkflowVersion, WorkflowRun.version_id == WorkflowVersion.id
    ).join(
        WorkflowDefinition, WorkflowVersion.definition_id == WorkflowDefinition.id
    ).filter(
        WorkflowDefinition.brain_id.in_(brain_ids) if brain_ids else False
    )

    if status_filter:
        query = query.filter(WorkflowApproval.status == status_filter)

    query = query.order_by(WorkflowApproval.created_at.desc())

    total = query.count() if brain_ids else 0
    results = query.offset(offset).limit(limit).all() if brain_ids else []

    return {
        "total": total,
        "approvals": [
            {
                "id": str(approval.id),
                "step_id": str(approval.step_id),
                "run_id": str(step.run_id),
                "node_id": step.node_id,
                "status": approval.status,
                "snapshot_payload": approval.snapshot_payload_jsonb,
                "reviewed_by": str(approval.reviewed_by) if approval.reviewed_by else None,
                "reviewed_at": approval.reviewed_at.isoformat() if approval.reviewed_at else None,
                "created_at": approval.created_at.isoformat()
            } for approval, step in results
        ]
    }

@router.post("/steps/{step_id}/approve")
def approve_workflow_step(
    step_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    step = db.query(WorkflowStep).filter(WorkflowStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    run = db.query(WorkflowRun).filter(WorkflowRun.id == step.run_id).first()
    if not run or resolve_workflow_run_workspace_id(db, run) != workspace_id:
        raise HTTPException(status_code=404, detail="Step not found")

    if step.status != "waiting_approval":
        raise HTTPException(status_code=400, detail="Step is not waiting for approval")
        
    step.status = "running"
    run.status = "running"
    
    approval = db.query(WorkflowApproval).filter(
        WorkflowApproval.step_id == step.id,
        WorkflowApproval.status == "pending"
    ).first()
    if approval:
        approval.status = "approved"
        approval.reviewed_by = member.user_id
        approval.reviewed_at = datetime.utcnow()
        
    db.commit()

    write_audit_log(
        db=db,
        actor_type="user",
        actor_id=member.user_id,
        action="workflow.step.approve",
        target_type="workflow_step",
        target_id=step.id,
        metadata_jsonb={
            "workspace_id": str(workspace_id),
            "run_id": str(run.id),
            "node_id": step.node_id,
            "approval_id": str(approval.id) if approval else None
        }
    )
    
    return {"status": "success", "message": "Step approved and resumed"}

@router.post("/steps/{step_id}/reject")
def reject_workflow_step(
    step_id: int,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    step = db.query(WorkflowStep).filter(WorkflowStep.id == step_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    run = db.query(WorkflowRun).filter(WorkflowRun.id == step.run_id).first()
    if not run or resolve_workflow_run_workspace_id(db, run) != workspace_id:
        raise HTTPException(status_code=404, detail="Step not found")

    if step.status != "waiting_approval":
        raise HTTPException(status_code=400, detail="Step is not waiting for approval")
        
    step.status = "rejected"
    run.status = "cancelled"
    
    approval = db.query(WorkflowApproval).filter(
        WorkflowApproval.step_id == step.id,
        WorkflowApproval.status == "pending"
    ).first()
    if approval:
        approval.status = "rejected"
        approval.reviewed_by = member.user_id
        approval.reviewed_at = datetime.utcnow()
        
    db.commit()

    write_audit_log(
        db=db,
        actor_type="user",
        actor_id=member.user_id,
        action="workflow.step.reject",
        target_type="workflow_step",
        target_id=step.id,
        metadata_jsonb={
            "workspace_id": str(workspace_id),
            "run_id": str(run.id),
            "node_id": step.node_id,
            "approval_id": str(approval.id) if approval else None
        }
    )
    
    return {"status": "success", "message": "Step rejected and workflow cancelled"}


# ====================================================
# Automation & n8n Callback Webhooks
# ====================================================
from fastapi import Request, Header
from app.integrations.workflows.n8n_gateway_service import handle_n8n_callback

@router.post("/public/automations/callback/{run_id}")
async def receive_automation_callback(
    run_id: str,
    request: Request,
    x_cosa_signature: Optional[str] = Header(None, alias="X-COSA-Signature"),
    db: Session = Depends(get_db),
):
    """Tiếp nhận webhook callback từ n8n khi workflow hoàn thành."""
    raw_body = await request.body()
    payload = await request.json()

    try:
        rid = int(run_id)
        res = handle_n8n_callback(
            db=db,
            run_id=rid,
            payload=payload,
            raw_body_bytes=raw_body,
            signature_header=x_cosa_signature or "",
        )
        return res
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
