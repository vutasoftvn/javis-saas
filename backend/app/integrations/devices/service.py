from datetime import datetime, timedelta
import hashlib
import secrets
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.integrations.devices.models import Device, DeviceCredential, DeveloperJob, JobLease
from app.founder_os.outcomes.models import Outcome
from app.core.audit import write_audit_log
from app.core.events import publish_event


def hash_device_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def hash_lease_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def enroll_device(
    db: Session,
    workspace_id: int,
    user_id: int,
    name: str,
    platform: str,
    capabilities: Optional[List[str]] = None,
    trust_level: str = "standard",
) -> Tuple[Device, str]:
    """Đăng ký thiết bị mới, trả về (device, raw_token).

    raw_token chỉ tồn tại trong bộ nhớ ở lần gọi này - DB chỉ lưu hash của nó
    (xem DeviceCredential.token_hash). Caller (router) phải trả raw_token cho
    client ngay trong response này vì sẽ không thể lấy lại được sau đó.
    """
    device = Device(
        workspace_id=workspace_id,
        name=name,
        platform=platform,
        capabilities=capabilities or ["claude_code", "git", "filesystem"],
        trust_level=trust_level,
        status="online",
        last_seen=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    raw_token = f"mcosa_dev_{secrets.token_urlsafe(32)}"
    cred = DeviceCredential(
        device_id=device.id,
        token_hash=hash_device_token(raw_token),
        is_revoked=False,
        expires_at=datetime.utcnow() + timedelta(days=365),
        created_at=datetime.utcnow(),
    )
    db.add(cred)
    db.commit()

    write_audit_log(
        db=db,
        actor_type="user",
        actor_id=user_id,
        action="device.enroll",
        target_type="device",
        target_id=device.id,
        metadata_jsonb={"workspace_id": str(workspace_id), "name": name, "platform": platform}
    )

    publish_event(
        event_type="device.enrolled",
        workspace_id=workspace_id,
        actor_id=user_id,
        payload={"device_id": str(device.id), "name": device.name, "platform": device.platform}
    )

    return device, raw_token


def resolve_device_from_token(db: Session, raw_token: str) -> Optional[Device]:
    """Xác thực một enrollment token (Bearer header của Local Worker Plane)
    và trả về Device tương ứng, hoặc None nếu token sai/đã thu hồi/hết hạn.
    Đây là cơ chế xác thực RIÊNG cho worker, độc lập với JWT của user (§113's
    two-plane split) - dùng bởi core/auth.py::get_current_device.
    """
    token_hash = hash_device_token(raw_token)
    cred = db.query(DeviceCredential).filter(
        DeviceCredential.token_hash == token_hash,
        DeviceCredential.is_revoked == False,  # noqa: E712
    ).first()
    if not cred:
        return None
    if cred.expires_at and cred.expires_at < datetime.utcnow():
        return None
    return db.query(Device).filter(Device.id == cred.device_id).first()


def list_devices(
    db: Session,
    workspace_id: int,
) -> List[Device]:
    return db.query(Device).filter(Device.workspace_id == workspace_id).order_by(Device.created_at.desc()).all()


def heartbeat_device(
    db: Session,
    device_id: int,
    workspace_id: int,
    status: str = "online",
) -> Optional[Device]:
    device = db.query(Device).filter(
        Device.id == device_id,
        Device.workspace_id == workspace_id
    ).first()
    if not device:
        return None

    device.last_seen = datetime.utcnow()
    device.status = status
    db.commit()
    return device


def create_developer_job(
    db: Session,
    workspace_id: int,
    user_id: int,
    title: str,
    outcome_id: Optional[int] = None,
    required_capabilities: Optional[List[str]] = None,
    idempotency_key: Optional[str] = None,
) -> DeveloperJob:
    """Create a DeveloperJob. When `idempotency_key` is given (voice-triggered
    dispatch - mCOSA V12.2 §70/§90.11) and a job already exists for this
    workspace+key, that existing job is returned unchanged instead of
    creating a duplicate - a retried/reconnected voice command must not
    spawn a second Claude Code job."""
    if idempotency_key is not None:
        existing = (
            db.query(DeveloperJob)
            .filter(
                DeveloperJob.workspace_id == workspace_id,
                DeveloperJob.idempotency_key == idempotency_key,
            )
            .first()
        )
        if existing is not None:
            return existing

    if outcome_id is not None:
        outcome = db.query(Outcome).filter(
            Outcome.id == outcome_id,
            Outcome.workspace_id == workspace_id,
        ).first()
        if outcome is None:
            raise ValueError("Outcome not found or access denied")
        outcome.function = "TECH"

    job = DeveloperJob(
        workspace_id=workspace_id,
        outcome_id=outcome_id,
        title=title,
        required_capabilities=required_capabilities or ["claude_code", "git"],
        status="QUEUED",
        idempotency_key=idempotency_key,
        created_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    write_audit_log(
        db=db,
        actor_type="user",
        actor_id=user_id,
        action="developer_job.create",
        target_type="developer_job",
        target_id=job.id,
        metadata_jsonb={"workspace_id": str(workspace_id), "title": title}
    )

    publish_event(
        event_type="job.created",
        workspace_id=workspace_id,
        actor_id=user_id,
        payload={"job_id": str(job.id), "title": job.title, "status": job.status}
    )

    return job


def list_developer_jobs(
    db: Session,
    workspace_id: int,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[DeveloperJob]:
    query = db.query(DeveloperJob).filter(DeveloperJob.workspace_id == workspace_id)
    if status:
        query = query.filter(DeveloperJob.status == status)
    return query.order_by(DeveloperJob.created_at.desc()).offset(offset).limit(limit).all()


def claim_job(
    db: Session,
    device_id: int,
    job_id: int,
    workspace_id: int,
    worker_id: str,
    lease_duration_minutes: int = 15,
) -> Tuple[DeveloperJob, JobLease]:
    job = (
        db.query(DeveloperJob)
        .filter(
            DeveloperJob.id == job_id,
            DeveloperJob.workspace_id == workspace_id,
        )
        .with_for_update()
        .first()
    )
    if not job:
        raise ValueError("Developer job not found")

    if job.status not in ("QUEUED", "WAITING_FOR_DEVICE"):
        raise ValueError(f"Job is not available for claiming (current status: {job.status})")

    device = (
        db.query(Device)
        .filter(
            Device.id == device_id,
            Device.workspace_id == workspace_id,
        )
        .first()
    )
    if device is None:
        raise PermissionError("Device does not belong to this workspace")
    if device.status not in ("online", "busy"):
        raise PermissionError("Device is not online")
    required = set(job.required_capabilities or [])
    available = set(device.capabilities or [])
    if not required.issubset(available):
        raise PermissionError(
            f"Device capabilities do not satisfy job requirements: {sorted(required - available)}"
        )
    request = job.request_jsonb or {}
    project_id = request.get("project_id")
    if device.allowed_projects and (
        project_id is None or str(project_id) not in {str(value) for value in device.allowed_projects}
    ):
        raise PermissionError("Device is not allowed to execute this project")
    trust_rank = {"standard": 0, "elevated": 1, "admin": 2}
    required_trust = str(request.get("required_trust_level", "standard"))
    if trust_rank.get(device.trust_level, -1) < trust_rank.get(required_trust, 99):
        raise PermissionError(
            f"Device trust level '{device.trust_level}' is below '{required_trust}'"
        )
    active_lease = (
        db.query(JobLease)
        .filter(
            JobLease.job_id == job.id,
            JobLease.lease_until > datetime.utcnow(),
        )
        .first()
    )
    if active_lease is not None:
        raise ValueError("Job already has an active lease")

    job.status = "CLAIMED"
    job.assigned_device_id = device_id
    raw_lease_token = secrets.token_urlsafe(32)
    lease = JobLease(
        job_id=job.id,
        device_id=device_id,
        worker_id=worker_id,
        lease_token_hash=hash_lease_token(raw_lease_token),
        lease_until=datetime.utcnow() + timedelta(minutes=lease_duration_minutes),
        created_at=datetime.utcnow(),
    )
    db.add(lease)
    db.commit()
    db.refresh(job)
    db.refresh(lease)
    # Transient, returned once to the authenticated device; never persisted.
    lease.lease_token = raw_lease_token

    publish_event(
        event_type="job.claimed",
        workspace_id=workspace_id,
        payload={"job_id": str(job.id), "device_id": str(device_id), "worker_id": worker_id}
    )

    return job, lease


def renew_job_lease(
    db: Session,
    job_id: int,
    workspace_id: int,
    device_id: int,
    lease_token: str,
    lease_duration_minutes: int = 15,
) -> JobLease:
    job = db.query(DeveloperJob).filter(
        DeveloperJob.id == job_id,
        DeveloperJob.workspace_id == workspace_id,
        DeveloperJob.assigned_device_id == device_id,
    ).first()
    if job is None:
        raise PermissionError("Job is not assigned to this device")
    now = datetime.utcnow()
    lease = (
        db.query(JobLease)
        .filter(
            JobLease.job_id == job_id,
            JobLease.device_id == device_id,
            JobLease.lease_token_hash == hash_lease_token(lease_token),
            JobLease.lease_until > now,
        )
        .with_for_update()
        .first()
    )
    if lease is None:
        raise PermissionError("Active job lease is missing, expired, or invalid")
    lease.renewed_at = now
    lease.lease_until = now + timedelta(minutes=lease_duration_minutes)
    db.commit()
    db.refresh(lease)
    lease.lease_token = lease_token
    return lease


def submit_job_results(
    db: Session,
    job_id: int,
    workspace_id: int,
    device_id: int,
    lease_token: Optional[str] = None,
    status: str = "SUCCEEDED",
    diff_summary: Optional[str] = None,
    test_results: Optional[Dict[str, Any]] = None,
    worktree_path: Optional[str] = None,
) -> DeveloperJob:
    job = db.query(DeveloperJob).filter(
        DeveloperJob.id == job_id,
        DeveloperJob.workspace_id == workspace_id
    ).first()
    if not job:
        raise ValueError("Developer job not found")

    if job.assigned_device_id != device_id:
        # A device may only report results for a job it actually claimed -
        # without this, any enrolled device in the workspace could overwrite
        # another device's job (fabricate a diff/test result it never ran).
        raise PermissionError("Job is not assigned to this device")

    now = datetime.utcnow()
    lease = (
        db.query(JobLease)
        .filter(
            JobLease.job_id == job.id,
            JobLease.device_id == device_id,
            JobLease.lease_token_hash == hash_lease_token(lease_token or ""),
            JobLease.lease_until > now,
        )
        .with_for_update()
        .first()
    )
    if lease is None:
        raise PermissionError("Active job lease is missing, expired, or invalid")
    if job.status not in ("CLAIMED", "RUNNING", "WAITING_APPROVAL"):
        raise ValueError(f"Job cannot accept results from status {job.status}")
    if status not in ("SUCCEEDED", "FAILED", "WAITING_APPROVAL", "CANCELLED"):
        raise ValueError(f"Unsupported DeveloperJob result status {status}")

    job.status = status
    if diff_summary is not None:
        job.diff_summary = diff_summary
    if test_results is not None:
        job.test_results = test_results
    if worktree_path is not None:
        job.worktree_path = worktree_path
    job.result_jsonb = {
        "diff_summary": diff_summary,
        "test_results": test_results,
        "worktree_path": worktree_path,
    }
        
    db.commit()
    db.refresh(job)

    publish_event(
        event_type="job.completed",
        workspace_id=workspace_id,
        payload={"job_id": str(job.id), "status": job.status, "diff_summary": diff_summary}
    )

    return job


def request_job_cancel(
    db: Session,
    job_id: int,
    workspace_id: int,
) -> DeveloperJob:
    job = (
        db.query(DeveloperJob)
        .filter(
            DeveloperJob.id == job_id,
            DeveloperJob.workspace_id == workspace_id,
        )
        .with_for_update()
        .first()
    )
    if job is None:
        raise ValueError("Developer job not found")
    if job.status in ("SUCCEEDED", "FAILED", "CANCELLED"):
        return job
    job.cancel_requested_at = datetime.utcnow()
    if job.status in ("QUEUED", "WAITING_FOR_DEVICE"):
        job.status = "CANCELLED"
    db.commit()
    db.refresh(job)
    return job


def get_developer_job(
    db: Session,
    job_id: int,
    workspace_id: int,
) -> Optional[DeveloperJob]:
    return db.query(DeveloperJob).filter(
        DeveloperJob.id == job_id,
        DeveloperJob.workspace_id == workspace_id
    ).first()


def resolve_developer_job_approval(
    db: Session,
    job_id: int,
    workspace_id: int,
    decision: str,
    feedback: Optional[str] = None,
) -> DeveloperJob:
    job = get_developer_job(db=db, job_id=job_id, workspace_id=workspace_id)
    if not job:
        raise ValueError("Developer job not found")

    job.status = "SUCCEEDED" if decision.upper() == "APPROVED" else "FAILED"
    job.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(job)

    publish_event(
        event_type="job.approval_resolved",
        workspace_id=workspace_id,
        payload={"job_id": str(job.id), "status": job.status, "decision": decision, "feedback": feedback}
    )
    return job
