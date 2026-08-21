from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import BigInteger, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base_class import Base
from core.snowflake import generate_snowflake_id


class Device(Base):
    """Mô hình Device - Thiết bị thực thi Client/Desktop Node trong mạng lưới (§58–74, §80–95)."""
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    platform: Mapped[str] = mapped_column(String(50))  # macos, windows, linux, ios, android
    capabilities: Mapped[Optional[list]] = mapped_column(JSONB, default=["claude_code", "git", "filesystem"])
    allowed_projects: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    trust_level: Mapped[str] = mapped_column(String(50), default="standard")  # standard, elevated, admin
    status: Mapped[str] = mapped_column(String(50), default="offline")  # online, offline, busy
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DeviceCredential(Base):
    """Mô hình DeviceCredential - Chứng chỉ đăng ký thiết bị an toàn.

    Chỉ lưu SHA-256 hash của enrollment token, không bao giờ lưu token gốc -
    token gốc chỉ được trả về MỘT LẦN trong response của POST /devices/enroll.
    Nếu DB bị lộ, kẻ tấn công không lấy được token dùng được để giả làm worker.
    """
    __tablename__ = "device_credentials"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DeveloperJob(Base):
    """Mô hình DeveloperJob - Tác vụ lập trình định tuyến đến Device worker (§83)."""
    __tablename__ = "developer_jobs"
    __table_args__ = (
        UniqueConstraint('workspace_id', 'idempotency_key', name='uix_developer_job_workspace_idempotency_key'),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), index=True)
    outcome_id: Mapped[Optional[int]] = mapped_column(ForeignKey("outcomes.id"), nullable=True, index=True)
    agent_run_id: Mapped[Optional[int]] = mapped_column(ForeignKey("agent_runs.id"), nullable=True, index=True)
    run_step_id: Mapped[Optional[int]] = mapped_column(ForeignKey("run_steps.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    executor_kind: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    required_capabilities: Mapped[Optional[list]] = mapped_column(JSONB, default=["claude_code", "git"])
    assigned_device_id: Mapped[Optional[int]] = mapped_column(ForeignKey("devices.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="QUEUED")  # QUEUED, WAITING_FOR_DEVICE, CLAIMED, RUNNING, WAITING_APPROVAL, SUCCEEDED, FAILED, CANCELLED
    worktree_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    diff_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    test_results: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    request_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    result_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    cancel_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # Voice-triggered job dispatch (mCOSA V12.2 §70/§90.11): a retried/reconnected
    # voice command must not create a second job. NULL for HTTP-created jobs,
    # which have no such retry concern.
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class JobLease(Base):
    """Mô hình JobLease - Khóa độc quyền tạm thời cho Worker khi nhận job."""
    __tablename__ = "job_leases"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    job_id: Mapped[int] = mapped_column(ForeignKey("developer_jobs.id"), index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    worker_id: Mapped[str] = mapped_column(String(100))
    lease_token_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    lease_until: Mapped[datetime] = mapped_column(DateTime)
    renewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
