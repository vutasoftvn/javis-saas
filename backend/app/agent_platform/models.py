from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    String, Boolean, DateTime, ForeignKey, BigInteger, Text, Integer, Float, Numeric, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.db.snowflake_model import SnowflakeIDMixin
from app.core.snowflake import generate_snowflake_id


class AgentDefinition(Base, SnowflakeIDMixin):
    """Định nghĩa Agent trong hệ thống COSA (Registry)."""
    __tablename__ = "agent_definitions"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    key: Mapped[str] = mapped_column(String(100), index=True)  # vd: 'founder', 'sales', 'finance'
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agent_type: Mapped[str] = mapped_column(String(50), default="specialist")  # 'general', 'specialist', 'workflow', 'orchestrator'
    default_model_profile: Mapped[str] = mapped_column(String(100), default="reasoning")  # 'fast', 'reasoning', 'chat', 'local'
    system_prompt_key: Mapped[str] = mapped_column(String(255), default="default.system")
    risk_level: Mapped[int] = mapped_column(Integer, default=1)  # 0..4
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("workspace_id", "key", name="uq_agent_definitions_ws_key"),
    )


class ToolDefinition(Base, SnowflakeIDMixin):
    """Định nghĩa Tool tập trung trong Tool Registry."""
    __tablename__ = "tool_definitions"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    key: Mapped[str] = mapped_column(String(150), index=True)  # vd: 'crm.search', 'email.send', 'github.issue'
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transport: Mapped[str] = mapped_column(String(50), default="local")  # 'local', 'mcp', 'a2a', 'n8n', 'sandbox', 'api'
    risk_level: Mapped[int] = mapped_column(Integer, default=0)  # R0..R4
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    input_schema: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    output_schema: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    config_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)  # Server URLs, webhook IDs, sandbox profiles
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("workspace_id", "key", name="uq_tool_definitions_ws_key"),
    )


class AgentToolPermission(Base, SnowflakeIDMixin):
    """Ma trận phân quyền Agent <-> Tool."""
    __tablename__ = "agent_tool_permissions"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agent_definitions.id"), index=True)
    tool_id: Mapped[int] = mapped_column(ForeignKey("tool_definitions.id"), index=True)
    allow_execute: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("workspace_id", "agent_id", "tool_id", name="uq_agent_tool_perm_ws"),
    )


class PlatformPromptTemplate(Base, SnowflakeIDMixin):
    """Prompt template có versioning và khả năng rollback / restore default."""
    __tablename__ = "platform_prompt_templates"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    key: Mapped[str] = mapped_column(String(255), index=True)  # vd: 'founder.system', 'router.intent'
    default_content: Mapped[str] = mapped_column(Text)
    current_content: Mapped[str] = mapped_column(Text)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    updated_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("workspace_id", "key", name="uq_platform_prompt_ws_key"),
    )


class PlatformPromptVersion(Base, SnowflakeIDMixin):
    """Lịch sử sửa đổi prompt."""
    __tablename__ = "platform_prompt_versions"

    template_id: Mapped[int] = mapped_column(ForeignKey("platform_prompt_templates.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    change_note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PlatformSecretRef(Base, SnowflakeIDMixin):
    """Tham chiếu Secret an toàn (Secret Broker), không để lộ API key vào LLM."""
    __tablename__ = "platform_secret_refs"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    provider: Mapped[str] = mapped_column(String(100))  # 'resend', 'github', 'openai', 'gemini'
    key_name: Mapped[str] = mapped_column(String(255))
    external_ref: Mapped[str] = mapped_column(Text)  # Vault key / encrypted payload ref
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentRun(Base, SnowflakeIDMixin):
    """Theo dõi lần chạy (Execution Run) của Agent/Workflow phục vụ Observability."""
    __tablename__ = "platform_agent_runs"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    trace_id: Mapped[str] = mapped_column(String(100), index=True)
    session_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    agent_key: Mapped[str] = mapped_column(String(100), index=True)
    workflow_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="running")  # 'running', 'completed', 'failed', 'paused_for_approval'
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    estimated_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.0)
    meta_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AgentStep(Base, SnowflakeIDMixin):
    """Từng bước thực thi (Step Span) trong một Agent Run."""
    __tablename__ = "platform_agent_steps"

    run_id: Mapped[int] = mapped_column(ForeignKey("platform_agent_runs.id"), index=True)
    parent_step_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    step_type: Mapped[str] = mapped_column(String(50))  # 'router', 'agent', 'model', 'tool', 'mcp', 'a2a', 'approval', 'sandbox'
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="success")  # 'success', 'failed', 'pending'
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    metadata_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
