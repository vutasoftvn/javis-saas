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
    """Định nghĩa Agent trong hệ thống COSA Control Plane (Registry)."""
    __tablename__ = "agent_definitions"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    key: Mapped[str] = mapped_column(String(100), index=True)  # vd: 'founder_copilot', 'cfo_agent', 'tech_lead_agent'
    name: Mapped[str] = mapped_column(String(255))
    role_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # vd: 'Chief Financial Officer'
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # vd: 'Finance', 'Engineering'
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agent_type: Mapped[str] = mapped_column(String(50), default="specialist")  # 'general', 'specialist', 'workflow', 'orchestrator'
    default_model_profile: Mapped[str] = mapped_column(String(100), default="reasoning")  # 'fast', 'reasoning', 'coding', 'chat', 'local'
    system_prompt_key: Mapped[str] = mapped_column(String(255), default="default.system")
    risk_level: Mapped[int] = mapped_column(Integer, default=1)  # 0..4 (R0: Auto -> R4: Critical Founder Only)
    status: Mapped[str] = mapped_column(String(50), default="idle")  # 'idle', 'busy', 'paused', 'error', 'offline'
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    capabilities_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    model_config_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("workspace_id", "key", name="uq_agent_definitions_ws_key"),
    )


class AgentHierarchy(Base, SnowflakeIDMixin):
    """Sơ đồ tổ chức (Org Chart) & quan hệ cấp bậc giữa các Agent và Human Leads."""
    __tablename__ = "agent_hierarchies"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    parent_agent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("agent_definitions.id"), index=True, nullable=True)
    child_agent_id: Mapped[int] = mapped_column(ForeignKey("agent_definitions.id"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(50), default="REPORTS_TO")  # 'MANAGES', 'REPORTS_TO', 'COLLABORATES'
    meta_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("workspace_id", "parent_agent_id", "child_agent_id", name="uq_agent_hierarchy_ws_nodes"),
    )


class ToolDefinition(Base, SnowflakeIDMixin):
    """Định nghĩa Tool tập trung trong Tool Registry (Skill Layer)."""
    __tablename__ = "tool_definitions"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    key: Mapped[str] = mapped_column(String(150), index=True)  # vd: 'crm.search', 'email.send', 'github.issue'
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transport: Mapped[str] = mapped_column(String(50), default="local")  # 'local', 'mcp', 'a2a', 'n8n', 'sandbox', 'api'
    risk_level: Mapped[int] = mapped_column(Integer, default=0)  # R0..R4
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    input_schema: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    output_schema: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    config_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)  # Server URLs, webhook IDs, sandbox profiles
    default_config_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("workspace_id", "key", name="uq_tool_definitions_ws_key"),
    )


class PlatformToolVersion(Base, SnowflakeIDMixin):
    """Lịch sử sửa đổi Tool Definition (Skill Versioning)."""
    __tablename__ = "platform_tool_versions"

    tool_id: Mapped[int] = mapped_column(ForeignKey("tool_definitions.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    input_schema: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    output_schema: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    config_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    change_note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)



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


class UnifiedPermission(Base, SnowflakeIDMixin):
    """Permission Engine hợp nhất cho cả Human User và AI Agent (Principal-based)."""
    __tablename__ = "unified_permissions"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    principal_type: Mapped[str] = mapped_column(String(20), index=True)  # 'USER' hoặc 'AGENT'
    principal_id: Mapped[int] = mapped_column(BigInteger, index=True)  # User ID hoặc Agent ID
    resource_type: Mapped[str] = mapped_column(String(50), index=True)  # 'TOOL', 'DATA', 'MODULE', 'BUDGET'
    resource_key: Mapped[str] = mapped_column(String(150), index=True)  # vd: 'crm.update', 'finance.read', '*'
    action: Mapped[str] = mapped_column(String(50), default="EXECUTE")  # 'READ', 'WRITE', 'EXECUTE', 'APPROVE', 'ADMIN'
    is_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("workspace_id", "principal_type", "principal_id", "resource_type", "resource_key", "action", name="uq_unified_perm"),
    )


class ApprovalRequest(Base, SnowflakeIDMixin):
    """Phiếu yêu cầu phê duyệt trong Human Approval Inbox."""
    __tablename__ = "approval_requests"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    task_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    run_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    requester_agent_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    requester_agent_key: Mapped[str] = mapped_column(String(100), index=True)
    action_type: Mapped[str] = mapped_column(String(50))  # 'TOOL_EXEC', 'PAYMENT', 'DATA_MUTATE', 'PUBLISH'
    risk_level: Mapped[str] = mapped_column(String(20), default="HIGH")  # 'HIGH', 'CRITICAL'
    required_role: Mapped[str] = mapped_column(String(50), default="FOUNDER")  # 'LEAD', 'FOUNDER'
    status: Mapped[str] = mapped_column(String(50), default="PENDING")  # 'PENDING', 'APPROVED', 'REJECTED', 'CANCELLED'
    tool_key: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    payload_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approver_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    approver_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentBudget(Base, SnowflakeIDMixin):
    """Ngân sách chi tiêu Token & USD cho Agent và Department."""
    __tablename__ = "agent_budgets"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    agent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("agent_definitions.id"), index=True, nullable=True)
    agent_key: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    cycle_type: Mapped[str] = mapped_column(String(50), default="12_WEEK_YEAR")  # 'DAILY', 'MONTHLY', '12_WEEK_YEAR'
    limit_usd: Mapped[float] = mapped_column(Float, default=100.0)
    spent_usd: Mapped[float] = mapped_column(Float, default=0.0)
    soft_limit_percent: Mapped[float] = mapped_column(Float, default=0.8)  # Cảnh báo ở 80%
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    period_start: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CostLedger(Base, SnowflakeIDMixin):
    """Sổ cái tài chính bất biến (Immutable Cost Ledger) ghi nhận chi phí từng lần chạy."""
    __tablename__ = "cost_ledger_entries"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    run_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    task_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    agent_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    agent_key: Mapped[str] = mapped_column(String(100), index=True)
    provider: Mapped[str] = mapped_column(String(50))  # 'claude', 'gemini', 'deepseek', 'http'
    model_name: Mapped[str] = mapped_column(String(100))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    cost_vnd: Mapped[float] = mapped_column(Float, default=0.0)  # Quy đổi VND (tỷ giá 25,400)
    billing_cycle: Mapped[str] = mapped_column(String(50), default="12WY_Q3")
    meta_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


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
    """Theo dõi lần chạy (Execution Run) của Agent/Workflow phục vụ Observability & Audit."""
    __tablename__ = "platform_agent_runs"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    trace_id: Mapped[str] = mapped_column(String(100), index=True)
    session_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    task_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    agent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("agent_definitions.id"), index=True, nullable=True)
    agent_key: Mapped[str] = mapped_column(String(100), index=True)
    workflow_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    runtime_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 'claude', 'gemini', 'deepseek', 'http'
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="running")  # 'queued', 'running', 'completed', 'failed', 'paused_for_approval'
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=0)
    estimated_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.0)
    prompt_snapshot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
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


class AgentHeartbeat(Base, SnowflakeIDMixin):
    """Giám sát nhịp tim và trạng thái liveness của Agent."""
    __tablename__ = "agent_heartbeats"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    agent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("agent_definitions.id"), index=True, nullable=True)
    agent_key: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(50), default="HEALTHY")  # 'HEALTHY', 'DEGRADED', 'STALLED', 'OFFLINE'
    active_runs_count: Mapped[int] = mapped_column(Integer, default=0)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    metadata_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("workspace_id", "agent_key", name="uq_agent_heartbeat_ws_key"),
    )


class AgentRoutine(Base, SnowflakeIDMixin):
    """Quy trình tự động hóa tuần hoàn gắn liền với chu kỳ 12-Week Year."""
    __tablename__ = "agent_routines"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    key: Mapped[str] = mapped_column(String(100), index=True)  # vd: 'monday_tactics_dispatch', 'friday_scoreboard_wrapup'
    name: Mapped[str] = mapped_column(String(255))
    routine_type: Mapped[str] = mapped_column(String(50), default="WEEKLY_TACTICS")  # 'WEEKLY_TACTICS', 'FRIDAY_SCOREBOARD', 'DAILY_STANDUP', 'WEEK_13_REVIEW'
    cron_expression: Mapped[str] = mapped_column(String(100), default="0 8 * * 1")
    target_agent_key: Mapped[str] = mapped_column(String(100), default="founder_copilot")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    payload_template_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("workspace_id", "key", name="uq_agent_routines_ws_key"),
    )


class RoutineExecution(Base, SnowflakeIDMixin):
    """Lịch sử thực thi các lần chạy Routine tự động."""
    __tablename__ = "routine_executions"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    routine_id: Mapped[int] = mapped_column(ForeignKey("agent_routines.id"), index=True)
    task_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    run_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="SUCCESS")  # 'SUCCESS', 'FAILED', 'RUNNING'
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_summary_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WorkProduct(Base, SnowflakeIDMixin):
    """Sản phẩm bàn giao văn bản hóa có cấu trúc của Agent (Work Product Contract)."""
    __tablename__ = "work_products"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    task_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    run_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    agent_key: Mapped[str] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(255))
    product_type: Mapped[str] = mapped_column(String(50), default="DOCUMENT")  # 'DOCUMENT', 'CODE_DIFF', 'DECISION_RECORD', 'FINANCIAL_REPORT', 'TACTIC_DELIVERABLE'
    status: Mapped[str] = mapped_column(String(50), default="DRAFT")  # 'DRAFT', 'REVIEWED', 'ACCEPTED', 'REVISION_REQUESTED', 'REJECTED'
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_markdown: Mapped[str] = mapped_column(Text)
    artifacts_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    metadata_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    reviewed_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DecisionRecord(Base, SnowflakeIDMixin):
    """Hồ sơ lưu trữ quyết định kiến trúc / chiến lược (Architecture/Action Decision Record)."""
    __tablename__ = "decision_records"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    work_product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("work_products.id"), index=True, nullable=True)
    task_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="PROPOSED")  # 'PROPOSED', 'ACCEPTED', 'SUPERSEDED', 'REJECTED'
    context_summary: Mapped[str] = mapped_column(Text)
    decision_content: Mapped[str] = mapped_column(Text)
    consequences: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    alternatives_considered: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author_agent_key: Mapped[str] = mapped_column(String(100), default="founder_copilot")
    approved_by_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


