from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_workspace_member
from app.core.feature_flags import FLAG_AGENT_MEMORY_V12_3, is_enabled
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.workforce.memory.health import check_sidecar_health
from app.workforce.memory.service import get_gateway

router = APIRouter()

# MEM-0 scope (spec §209): plumbing + health check.
# MEM-1 (spec §148, Claude Code PoC only) adds the single task-context recall
# endpoint below - no general recall/search/candidates/promote endpoints yet,
# those come online in later MEM phases once real behavior exists behind them.


@router.get("/status")
def get_memory_status(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    return {"enabled": is_enabled(db, FLAG_AGENT_MEMORY_V12_3, workspace_id)}


@router.get("/health")
async def get_memory_health():
    """Live sidecar health (spec §180) - not workspace-scoped, this reflects
    process-level reachability, same as /api/v1/realtime/health."""
    health = await check_sidecar_health()
    return {
        "status": health.status,
        "latency_ms": health.latency_ms,
        "backend": health.backend,
        "last_error": health.last_error,
    }


@router.get("/task-context/{job_id}")
async def get_task_context(
    job_id: str,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    """MEM-1 Claude Code PoC recall (spec §148) - "Tiếp tục implementation ...
    hôm qua" resume flow. Returns null (never raises) when memory is
    disabled or the sidecar has nothing for this job - callers should treat
    that as "no prior context available", not an error."""
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    gateway = get_gateway(db, workspace_id)
    context = await gateway.get_task_context(job_id)
    return {"job_id": job_id, "context": context}
