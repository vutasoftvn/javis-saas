import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth import get_current_workspace_member, get_current_device
from app.db.models import WorkspaceMember, Device
from app.modules.agent_memory.claude_code_capture import capture_developer_job_completion
from app.modules.devices import service

router = APIRouter()


class DeviceEnrollRequest(BaseModel):
    name: str
    platform: str  # macos, windows, linux
    capabilities: Optional[List[str]] = None
    trust_level: Optional[str] = "standard"


class DeviceHeartbeatRequest(BaseModel):
    status: Optional[str] = "online"


class JobClaimRequest(BaseModel):
    worker_id: str
    lease_duration_minutes: Optional[int] = 15


class DeveloperJobCreate(BaseModel):
    title: str
    outcome_id: Optional[int] = None
    required_capabilities: Optional[List[str]] = None


class JobSubmitResultsRequest(BaseModel):
    status: str = "SUCCEEDED"  # SUCCEEDED, FAILED, WAITING_APPROVAL
    diff_summary: Optional[str] = None
    test_results: Optional[Dict[str, Any]] = None
    worktree_path: Optional[str] = None


@router.post("/devices/enroll", status_code=status.HTTP_201_CREATED)
def enroll_new_device(
    data: DeviceEnrollRequest,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    device, raw_token = service.enroll_device(
        db=db,
        workspace_id=workspace_id,
        user_id=member.user_id,
        name=data.name,
        platform=data.platform,
        capabilities=data.capabilities,
        trust_level=data.trust_level or "standard",
    )
    return {
        "device_id": str(device.id),
        "name": device.name,
        "platform": device.platform,
        "capabilities": device.capabilities,
        "trust_level": device.trust_level,
        # Shown ONLY here, ONLY once - the DB stores nothing but a hash of
        # this value (DeviceCredential.token_hash). Losing it means
        # re-enrolling the device; there is no recovery endpoint by design.
        "enrollment_token": raw_token,
        "created_at": device.created_at.isoformat(),
    }


@router.get("/devices")
def list_workspace_devices(
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    devices = service.list_devices(db=db, workspace_id=workspace_id)
    return {
        "total": len(devices),
        "devices": [
            {
                "id": str(d.id),
                "name": d.name,
                "platform": d.platform,
                "capabilities": d.capabilities,
                "trust_level": d.trust_level,
                "status": d.status,
                "last_seen": d.last_seen.isoformat() if d.last_seen else None,
                "created_at": d.created_at.isoformat(),
            }
            for d in devices
        ],
    }


@router.post("/devices/{device_id}/heartbeat")
def device_heartbeat(
    device_id: int,
    workspace_id: int,
    data: Optional[DeviceHeartbeatRequest] = None,
    caller_device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    # Worker-facing endpoint: authenticated by the device's own enrollment
    # token (get_current_device), NOT a user's JWT - a device may only ever
    # heartbeat as itself.
    if caller_device.id != device_id or caller_device.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this device")

    device = service.heartbeat_device(
        db=db,
        device_id=device_id,
        workspace_id=workspace_id,
        status=data.status if data and data.status else "online",
    )
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return {
        "status": "ok",
        "device_id": str(device.id),
        "device_status": device.status,
        "last_seen": device.last_seen.isoformat() if device.last_seen else None,
    }


@router.post("/devices/jobs", status_code=status.HTTP_201_CREATED)
def create_job(
    data: DeveloperJobCreate,
    workspace_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    if member.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this workspace")

    job = service.create_developer_job(
        db=db,
        workspace_id=workspace_id,
        user_id=member.user_id,
        title=data.title,
        outcome_id=data.outcome_id,
        required_capabilities=data.required_capabilities,
    )
    return {
        "id": str(job.id),
        "title": job.title,
        "status": job.status,
        "required_capabilities": job.required_capabilities,
        "created_at": job.created_at.isoformat(),
    }


@router.get("/devices/jobs")
def list_jobs(
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

    jobs = service.list_developer_jobs(
        db=db,
        workspace_id=workspace_id,
        status=status_filter,
        limit=l,
        offset=o,
    )
    return {
        "total": len(jobs),
        "jobs": [
            {
                "id": str(j.id),
                "title": j.title,
                "status": j.status,
                "assigned_device_id": str(j.assigned_device_id) if j.assigned_device_id else None,
                "diff_summary": j.diff_summary,
                "created_at": j.created_at.isoformat(),
            }
            for j in jobs
        ],
    }


@router.post("/devices/{device_id}/jobs/{job_id}/claim")
def claim_job_endpoint(
    device_id: int,
    job_id: int,
    workspace_id: int,
    data: JobClaimRequest,
    caller_device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    # Worker-facing endpoint: a device may only claim jobs as itself, within
    # its own workspace - see device_heartbeat's comment above.
    if caller_device.id != device_id or caller_device.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this device")

    try:
        job, lease = service.claim_job(
            db=db,
            device_id=device_id,
            job_id=job_id,
            workspace_id=workspace_id,
            worker_id=data.worker_id,
            lease_duration_minutes=data.lease_duration_minutes or 15,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status": "claimed",
        "job_id": str(job.id),
        "device_id": str(device_id),
        "lease_id": str(lease.id),
        "lease_until": lease.lease_until.isoformat(),
    }


@router.post("/devices/jobs/{job_id}/submit-results")
def submit_job_results_endpoint(
    job_id: int,
    workspace_id: int,
    data: JobSubmitResultsRequest,
    caller_device: Device = Depends(get_current_device),
    db: Session = Depends(get_db),
):
    # Worker-facing endpoint: a device may only submit results for a job it
    # actually claimed (enforced in service.submit_job_results) and within
    # its own workspace.
    if caller_device.workspace_id != workspace_id:
        raise HTTPException(status_code=403, detail="Access forbidden to this device")

    try:
        job = service.submit_job_results(
            db=db,
            job_id=job_id,
            workspace_id=workspace_id,
            device_id=caller_device.id,
            status=data.status,
            diff_summary=data.diff_summary,
            test_results=data.test_results,
            worktree_path=data.worktree_path,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # MEM-1 Claude Code PoC (spec §148-149, ADR-MEM-001) - best-effort
    # capture, never allowed to affect this response (capture_developer_job_completion
    # never raises on its own). asyncio.run() is safe here because this is a
    # sync FastAPI path function, executed in Starlette's threadpool with no
    # event loop already running on this thread.
    asyncio.run(capture_developer_job_completion(db, workspace_id, job))

    return {
        "status": "updated",
        "job_id": str(job.id),
        "job_status": job.status,
        "diff_summary": job.diff_summary,
    }
