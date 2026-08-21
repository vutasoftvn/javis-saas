# backend/app/workforce/agents/orchestration/mission_resume_models.py
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from db.base_class import Base
from db.snowflake_model import SnowflakeIDMixin


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MissionResumeJob(SnowflakeIDMixin, Base):
    """Đảm bảo đúng 1 worker resume AdkCofounderWorkflow cho mỗi checkpoint khi
    nhiều specialist RunStep hoàn tất gần nhau — thay cho cơ chế advisory-lock +
    materialized-event trong chief_of_staff.py::resume_after_delegation (xem
    Quyết định 1, mục "Exactly-once resume").

    checkpoint_key xác định CHÍNH XÁC điểm pause nào đang được resume (vd
    "specialist_join:<run_step_id>") — UNIQUE(mission_run_id, checkpoint_key)
    là cơ chế chặn 2 worker cùng resume 1 checkpoint, KHÔNG chặn resume các
    checkpoint khác nhau của cùng 1 mission (đúng ngữ nghĩa, vì 1 mission có
    thể có nhiều specialist hoàn tất ở các thời điểm khác nhau).
    """

    __tablename__ = "mission_resume_jobs"

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workspaces.id"), nullable=False, index=True)
    mission_run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("agent_runtime.agent_runs.id"), nullable=False, index=True)
    workflow_session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    checkpoint_key: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(String(100), nullable=False)

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="queued", server_default="queued")
    claimed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    __table_args__ = (
        UniqueConstraint("mission_run_id", "checkpoint_key", name="uq_mission_resume_job_mission_checkpoint"),
        Index("ix_mission_resume_jobs_status_created", "status", "created_at"),
        {"schema": "agent_runtime"},
    )
