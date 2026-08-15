from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.execution.manager import execution_provider_manager
from app.agents.execution.models import ExecutionJob, ExecutionStep
from app.agents.execution.types import ExecutionHealth, ExecutionStatus
from app.core.auth import get_current_workspace_member
from app.core.feature_flags import FLAG_AGENT_EXECUTION, is_enabled
from app.core.tenancy import get_execution_job_scoped
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.integrations.s3_client import generate_presigned_download_url, put_object
from app.modules.outcomes.models import Artifact

router = APIRouter()


class JobCreateRequest(BaseModel):
    agent_key: str = "generic"
    policy_name: str = "safe_analysis"
    commands: List[str] = Field(default_factory=list)
    input_files: Dict[str, str] = Field(default_factory=dict)  # rel_path -> text/base64
    agent_run_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


def _require_execution_flag(db: Session, workspace_id: int) -> None:
    if not is_enabled(db, FLAG_AGENT_EXECUTION, workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Execution runtime is disabled for this workspace",
        )


def _serialize_job(job: ExecutionJob) -> Dict[str, Any]:
    return {
        "id": str(job.id),
        "id_str": str(job.id),
        "workspace_id": str(job.workspace_id),
        "brain_id": str(job.brain_id) if job.brain_id else None,
        "user_id": str(job.user_id),
        "agent_run_id": str(job.agent_run_id) if job.agent_run_id else None,
        "agent_key": job.agent_key,
        "provider": job.provider,
        "sandbox_id": job.sandbox_id,
        "status": job.status,
        "retry_count": job.retry_count,
        "idempotency_key": job.idempotency_key,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "destroyed_at": job.destroyed_at.isoformat() if job.destroyed_at else None,
        "error_code": job.error_code,
        "error_message": job.error_message,
        "metadata": job.metadata_jsonb or {},
    }


def _serialize_step(step: ExecutionStep) -> Dict[str, Any]:
    return {
        "id": str(step.id),
        "id_str": str(step.id),
        "job_id": str(step.job_id),
        "sequence": step.sequence,
        "step_type": step.step_type,
        "command": step.command,
        "status": step.status,
        "exit_code": step.exit_code,
        "started_at": step.started_at.isoformat() if step.started_at else None,
        "completed_at": step.completed_at.isoformat() if step.completed_at else None,
        "stdout_excerpt": step.stdout_excerpt,
        "stderr_excerpt": step.stderr_excerpt,
    }


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
def create_job(
    request: JobCreateRequest,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _require_execution_flag(db, member.workspace_id)

    # Idempotency check if key provided
    if request.idempotency_key:
        existing = (
            db.query(ExecutionJob)
            .filter(
                ExecutionJob.workspace_id == member.workspace_id,
                ExecutionJob.idempotency_key == request.idempotency_key,
            )
            .first()
        )
        if existing:
            return _serialize_job(existing)

    agent_run_id_int = int(request.agent_run_id) if request.agent_run_id and request.agent_run_id.isdigit() else None

    meta = {
        "policy_name": request.policy_name,
        "commands": request.commands,
        "input_files": request.input_files,
        **(request.metadata or {}),
    }

    job = ExecutionJob(
        workspace_id=member.workspace_id,
        user_id=member.user_id,
        agent_key=request.agent_key,
        agent_run_id=agent_run_id_int,
        status=ExecutionStatus.QUEUED.value,
        idempotency_key=request.idempotency_key,
        metadata_jsonb=meta,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return _serialize_job(job)


@router.get("/jobs")
def list_jobs(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _require_execution_flag(db, member.workspace_id)

    query = db.query(ExecutionJob).filter(ExecutionJob.workspace_id == member.workspace_id)
    if status_filter:
        query = query.filter(ExecutionJob.status == status_filter)

    total = query.count()
    jobs = query.order_by(ExecutionJob.id.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_serialize_job(j) for j in jobs],
    }


@router.get("/jobs/{job_id}")
def get_job(
    job_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _require_execution_flag(db, member.workspace_id)
    job = get_execution_job_scoped(db, job_id, member.workspace_id)

    steps = (
        db.query(ExecutionStep)
        .filter(ExecutionStep.job_id == job.id)
        .order_by(ExecutionStep.sequence.asc())
        .all()
    )

    data = _serialize_job(job)
    data["steps"] = [_serialize_step(s) for s in steps]
    return data


@router.post("/jobs/{job_id}/files")
async def upload_job_file(
    job_id: int,
    file: UploadFile = File(...),
    destination_path: Optional[str] = Query(None),
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _require_execution_flag(db, member.workspace_id)
    job = get_execution_job_scoped(db, job_id, member.workspace_id)

    content = await file.read()
    filename = destination_path or file.filename or "input.dat"
    storage_key = f"workspaces/{member.workspace_id}/execution/{job.id}/inputs/{filename}"

    put_object(storage_key, content, file.content_type or "application/octet-stream")

    # Update job metadata input files
    meta = job.metadata_jsonb or {}
    inputs = meta.get("input_files", {})
    inputs[filename] = storage_key
    meta["input_files"] = inputs
    job.metadata_jsonb = meta
    db.commit()

    return {
        "status": "success",
        "job_id": str(job.id),
        "filename": filename,
        "storage_key": storage_key,
        "size_bytes": len(content),
    }


@router.get("/jobs/{job_id}/artifacts")
def get_job_artifacts(
    job_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _require_execution_flag(db, member.workspace_id)
    job = get_execution_job_scoped(db, job_id, member.workspace_id)

    artifacts = (
        db.query(Artifact)
        .filter(
            Artifact.execution_job_id == job.id,
            Artifact.workspace_id == member.workspace_id,
        )
        .all()
    )

    items = []
    for art in artifacts:
        download_url = None
        if art.object_storage_uri:
            try:
                download_url = generate_presigned_download_url(art.object_storage_uri)
            except Exception:
                download_url = None

        items.append(
            {
                "id": str(art.id),
                "id_str": str(art.id),
                "type": art.type,
                "title": art.title,
                "object_storage_uri": art.object_storage_uri,
                "content_hash": art.content_hash,
                "status": art.status,
                "download_url": download_url,
                "created_at": art.created_at.isoformat() if art.created_at else None,
            }
        )

    return {"job_id": str(job.id), "artifacts": items}


@router.delete("/jobs/{job_id}")
def cancel_job(
    job_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _require_execution_flag(db, member.workspace_id)
    job = get_execution_job_scoped(db, job_id, member.workspace_id)

    if job.status in [ExecutionStatus.COMPLETED.value, ExecutionStatus.FAILED.value, ExecutionStatus.DESTROYED.value]:
        return _serialize_job(job)

    job.status = ExecutionStatus.CANCELLED.value
    db.commit()
    return _serialize_job(job)


@router.get("/health")
async def get_execution_health(
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
):
    _require_execution_flag(db, member.workspace_id)
    provider = execution_provider_manager.get()
    health_info: ExecutionHealth = await provider.health()
    return health_info.model_dump()
