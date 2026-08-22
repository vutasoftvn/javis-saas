# backend/app/workforce/agents/orchestration/runtime_session_models.py
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base_class import Base
from db.snowflake_model import SnowflakeIDMixin


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RuntimeSession(SnowflakeIDMixin, Base):
    """Nối các loại runtime session (ADK/DeepSeek/Sandbox/Human) dưới 1 Mission.

    AgentRun.runtime_session_id (String đơn) quá chật khi 1 mission có nhiều
    runtime session cùng lúc (vd ADK workflow session + DeepSeek Harness session
    của 1 specialist con) — bảng này KHÔNG thay AgentRun/AgentEventRecord, chỉ là
    bảng ánh xạ session-level bổ sung.
    """

    __tablename__ = "runtime_sessions"

    workspace_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("core.workspaces.id"), nullable=False, index=True)
    mission_run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("agent_runtime.agent_runs.id"), nullable=False, index=True)
    agent_run_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("agent_runtime.agent_runs.id"), nullable=True, index=True)

    runtime_type: Mapped[str] = mapped_column(String(30), nullable=False)  # ADK | DEEPSEEK_HARNESS | OPENSANDBOX | HUMAN
    external_session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    parent_session_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("agent_runtime.runtime_sessions.id", use_alter=True), nullable=True, index=True
    )

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active", server_default="active")
    checkpoint_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    metadata_jsonb: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_runtime_sessions_mission_status", "mission_run_id", "status"),
        {"schema": "agent_runtime"},
    )
