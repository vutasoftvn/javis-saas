from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any

from app.db.session import engine, get_db
from app.core.worker_health import get_worker_health
from app.core.auth import get_current_workspace_member
from app.db.models import (
    WorkspaceMember,
    AuditLog,
    Task,
    AIRun,
    MCPConnection,
)
from app.platform.core.hub_service import get_hub_summary_data

router = APIRouter()

@router.get("/{workspace_id}/hub-summary")
def get_hub_summary(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    if member.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: member does not belong to this workspace"
        )

    return get_hub_summary_data(db=db, workspace_id=workspace_id)

@router.get("/{workspace_id}/audit-events")
def list_audit_events(
    workspace_id: int,
    action: Optional[str] = None,
    actor_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    if member.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: member does not belong to this workspace"
        )

    l = int(limit) if isinstance(limit, (int, str)) and str(limit).isdigit() else 50
    o = int(offset) if isinstance(offset, (int, str)) and str(offset).isdigit() else 0

    # Filter at the DB level on metadata_jsonb['workspace_id'] (a real JSONB
    # column) instead of loading the entire audit_logs table into memory and
    # filtering in Python. Matching is strictly on workspace_id - a previous
    # "OR actor is also a member of this workspace" fallback was removed
    # because it leaked audit entries an actor generated in a *different*
    # workspace into this workspace's audit view whenever that actor happened
    # to belong to both. Every AuditLog writer now reliably tags
    # workspace_id (write_audit_log, VaultRepository, StrategyCanvasService),
    # so the fallback is no longer needed to catch untagged rows.
    query = db.query(AuditLog).filter(
        AuditLog.metadata_jsonb["workspace_id"].astext == str(workspace_id)
    )
    if action:
        query = query.filter(AuditLog.action == action)
    if actor_type:
        query = query.filter(AuditLog.actor_type == actor_type)

    query = query.order_by(AuditLog.created_at.desc())
    total = query.count()
    paged = query.offset(o).limit(l).all()

    return {
        "total": total,
        "events": [
            {
                "id": str(e.id),
                "actor_type": e.actor_type,
                "actor_id": str(e.actor_id),
                "action": e.action,
                "target_type": e.target_type,
                "target_id": str(e.target_id),
                "metadata": e.metadata_jsonb,
                "created_at": e.created_at.isoformat()
            } for e in paged
        ]
    }

@router.get("/{workspace_id}/diagnostics")
def get_diagnostics(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    if member.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: member does not belong to this workspace"
        )
    if member.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    workers_healthy, _ = get_worker_health(engine)

    failed_connectors = db.query(func.count(MCPConnection.id)).filter(
        MCPConnection.workspace_id == workspace_id,
        MCPConnection.status == "error"
    ).scalar() or 0

    ai_runs_count = db.query(func.count(AIRun.id)).filter(
        AIRun.workspace_id == workspace_id
    ).scalar() or 0

    tasks_count = db.query(func.count(Task.id)).filter(
        Task.workspace_id == workspace_id
    ).scalar() or 0

    return {
        "status": "ok",
        "workers": "healthy" if workers_healthy else "degraded",
        "connectors": "healthy" if failed_connectors == 0 else "degraded",
        "usage": {
            "ai_runs": ai_runs_count,
            "tasks": tasks_count
        }
    }


@router.post("/{workspace_id}/quick-actions/execute")
def run_quick_action(
    workspace_id: int,
    payload: Dict[str, Any],
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db)
):
    """Execute a typed quick action with structured prompt, tool execution and telemetry."""
    if member.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: member does not belong to this workspace"
        )

    action_key = payload.get("action_key") or "daily_brief"
    from app.workforce.agents.capabilities.quick_action_service import execute_quick_action
    result = execute_quick_action(
        db=db,
        workspace_id=workspace_id,
        action_key=action_key,
        user_id=member.user_id
    )
    return result.dict()

