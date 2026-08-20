from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_workspace_member
from app.db.models import WorkspaceMember
from app.db.session import get_db
from app.workforce.agents.delegation.models import DelegationJob
from app.workforce.agents.delegation.task_board import (
    AssignmentConflict,
    TaskBoardAccessDenied,
    TaskBoardService,
    DelegationDisabled,
)

router = APIRouter()


def _scoped_job(db: Session, workspace_id: int, job_id: int) -> DelegationJob:
    job = db.query(DelegationJob).filter(
        DelegationJob.id == job_id,
        DelegationJob.workspace_id == workspace_id,
    ).one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Delegation job not found")
    return job


def _serialize(job: DelegationJob) -> dict[str, Any]:
    return {
        "id": str(job.id),
        "run_step_id": str(job.run_step_id),
        "attempt_no": job.attempt_no,
        "provider_kind": job.provider_kind,
        "provider_name": job.provider_name,
        "profile_id": job.profile_id,
        "runtime_name": job.runtime_name,
        "status": job.status,
        "result": job.result_jsonb,
        "error_code": job.error_code,
        "error_message": job.error_message,
        "available_at": job.available_at.isoformat() if job.available_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.get("/{job_id}")
def get_delegation_job(
    job_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return _serialize(_scoped_job(db, member.workspace_id, job_id))


@router.post("/{job_id}/cancel")
def cancel_delegation_job(
    job_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    job = _scoped_job(db, member.workspace_id, job_id)
    try:
        cancelled = TaskBoardService.cancel_step(
            db,
            member.workspace_id,
            job.run_step_id,
        )
    except TaskBoardAccessDenied as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _serialize(cancelled)


@router.post("/{job_id}/retry", status_code=status.HTTP_201_CREATED)
def retry_delegation_job(
    job_id: int,
    member: WorkspaceMember = Depends(get_current_workspace_member),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _scoped_job(db, member.workspace_id, job_id)
    try:
        retry = TaskBoardService.retry_job(db, member.workspace_id, job_id)
    except TaskBoardAccessDenied as exc:
        raise HTTPException(status_code=404, detail="Delegation job not found") from exc
    except AssignmentConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DelegationDisabled as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return _serialize(retry)
