from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    String, Boolean, DateTime, ForeignKey, BigInteger, Text, Integer, Float, Numeric, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base_class import Base
from db.snowflake_model import SnowflakeIDMixin
from core.snowflake import generate_snowflake_id


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
    category: Mapped[str] = mapped_column(String(50), default="DOMAIN", index=True)  # 'ORCHESTRATOR', 'DOMAIN', 'OPTIONAL_DOMAIN', 'LEGACY'
    # Quyết định 4.3b (COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md) - nối bản ghi DB
    # (identity/risk-level/status) với runtime composition (skills/tools/workflows)
    # của AgentProfile in-memory, KHÔNG bắt AgentProfile phải chuyển xuống DB.
    profile_slug: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    is_default_active: Mapped[bool] = mapped_column(Boolean, default=False)
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
        {"schema": "agent_runtime"},
    )


class AgentHierarchy(Base, SnowflakeIDMixin):
    """Sơ đồ tổ chức (Org Chart) & quan hệ cấp bậc giữa các Agent và Human Leads."""
    __tablename__ = "agent_hierarchies"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    parent_agent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("agent_runtime.agent_definitions.id"), index=True, nullable=True)
    child_agent_id: Mapped[int] = mapped_column(ForeignKey("agent_runtime.agent_definitions.id"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(50), default="REPORTS_TO")  # 'MANAGES', 'REPORTS_TO', 'COLLABORATES'
    meta_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("workspace_id", "parent_agent_id", "child_agent_id", name="uq_agent_hierarchy_ws_nodes"),
        {"schema": "agent_runtime"},
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
        {"schema": "agent_runtime"},
    )


class PlatformToolVersion(Base, SnowflakeIDMixin):
    """Lịch sử sửa đổi Tool Definition (Skill Versioning)."""
    __tablename__ = "platform_tool_versions"
    __table_args__ = {"schema": "agent_runtime"}

    tool_id: Mapped[int] = mapped_column(ForeignKey("agent_runtime.tool_definitions.id"), index=True)
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
    agent_id: Mapped[int] = mapped_column(ForeignKey("agent_runtime.agent_definitions.id"), index=True)
    tool_id: Mapped[int] = mapped_column(ForeignKey("agent_runtime.tool_definitions.id"), index=True)
    allow_execute: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("workspace_id", "agent_id", "tool_id", name="uq_agent_tool_perm_ws"),
        {"schema": "agent_runtime"},
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
        {"schema": "agent_runtime"},
    )


class ApprovalRequest(Base, SnowflakeIDMixin):
    """Phiếu yêu cầu phê duyệt trong Human Approval Inbox."""
    __tablename__ = "approval_requests"
    __table_args__ = {"schema": "agent_runtime"}

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
    __table_args__ = {"schema": "agent_runtime"}

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    agent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("agent_runtime.agent_definitions.id"), index=True, nullable=True)
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
    __table_args__ = {"schema": "agent_runtime"}

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
        {"schema": "agent_runtime"},
    )


class PlatformPromptVersion(Base, SnowflakeIDMixin):
    """Lịch sử sửa đổi prompt."""
    __tablename__ = "platform_prompt_versions"
    __table_args__ = {"schema": "agent_runtime"}

    template_id: Mapped[int] = mapped_column(ForeignKey("agent_runtime.platform_prompt_templates.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    change_note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PlatformSecretRef(Base, SnowflakeIDMixin):
    """Tham chiếu Secret an toàn (Secret Broker), không để lộ API key vào LLM."""
    __tablename__ = "platform_secret_refs"
    __table_args__ = {"schema": "agent_runtime"}

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    provider: Mapped[str] = mapped_column(String(100))  # 'resend', 'github', 'openai', 'gemini'
    key_name: Mapped[str] = mapped_column(String(255))
    external_ref: Mapped[str] = mapped_column(Text)  # Vault key / encrypted payload ref
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LegacyPlatformAgentRun(Base, SnowflakeIDMixin):
    """Theo dõi lần chạy (Execution Run) của Agent/Workflow phục vụ Observability & Audit.

    Đổi tên từ `AgentRun` (G3 §2, §9.6a): tránh nhầm với model AgentRun canonical
    ở app.workforce.agents.governance.models (table agent_runs), model đó mới là
    nơi orchestrator thật (ChiefOfStaffOrchestrator) ghi dữ liệu. Bảng
    platform_agent_runs này vẫn đang được dùng thật bởi dispatcher/admin_api/
    governance.exception_engine/automation.heartbeat_monitor — chưa đủ điều kiện
    xóa hẳn, việc hợp nhất về 1 bảng duy nhất là phạm vi Phase 1B.
    """
    __tablename__ = "platform_agent_runs"
    __table_args__ = {"schema": "agent_runtime"}

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    trace_id: Mapped[str] = mapped_column(String(100), index=True)
    session_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    task_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    agent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("agent_runtime.agent_definitions.id"), index=True, nullable=True)
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
    __table_args__ = {"schema": "agent_runtime"}

    run_id: Mapped[int] = mapped_column(ForeignKey("agent_runtime.platform_agent_runs.id"), index=True)
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
    agent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("agent_runtime.agent_definitions.id"), index=True, nullable=True)
    agent_key: Mapped[str] = mapped_column(String(100), index=True)
    status: Mapped[str] = mapped_column(String(50), default="HEALTHY")  # 'HEALTHY', 'DEGRADED', 'STALLED', 'OFFLINE'
    active_runs_count: Mapped[int] = mapped_column(Integer, default=0)
    last_heartbeat_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    metadata_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("workspace_id", "agent_key", name="uq_agent_heartbeat_ws_key"),
        {"schema": "agent_runtime"},
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
        {"schema": "agent_runtime"},
    )


class RoutineExecution(Base, SnowflakeIDMixin):
    """Lịch sử thực thi các lần chạy Routine tự động."""
    __tablename__ = "routine_executions"
    __table_args__ = {"schema": "agent_runtime"}

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    routine_id: Mapped[int] = mapped_column(ForeignKey("agent_runtime.agent_routines.id"), index=True)
    task_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    run_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="SUCCESS")  # 'SUCCESS', 'FAILED', 'RUNNING'
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_summary_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WorkProduct(Base, SnowflakeIDMixin):
    """Sản phẩm bàn giao văn bản hóa có cấu trúc của Agent (Work Product Contract)."""
    __tablename__ = "work_products"
    __table_args__ = {"schema": "agent_runtime"}

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
    __table_args__ = {"schema": "agent_runtime"}

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    work_product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("agent_runtime.work_products.id"), index=True, nullable=True)
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


class EscalationRecord(Base, SnowflakeIDMixin):
    """
    Hồ sơ leo thang ngoại lệ trong AI Workforce (Phase 6 — Exception Escalation Engine).

    Lưu toàn bộ vòng đời của một exception từ lúc phát hiện đến khi được resolve.
    """
    __tablename__ = "escalation_records"
    __table_args__ = {"schema": "agent_runtime"}

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    exception_type: Mapped[str] = mapped_column(String(50), index=True)
    # AGENT_STALL | BUDGET_OVERFLOW | CONSECUTIVE_ERROR | STAGE_MISMATCH

    tier: Mapped[str] = mapped_column(String(50), index=True)
    # AUTO_RETRY | LEAD_NOTIFY | FOUNDER_GATE

    agent_key: Mapped[str] = mapped_column(String(100), index=True)
    run_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    stage_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # Stage context khi exception xảy ra, ví dụ: 'S0', 'S2'

    details_jsonb: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)
    # Chi tiết exception: cost, error_count, timeout_minutes, deemphasized_domains...

    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True)
    # OPEN | RESOLVED | DISMISSED

    resolution_action: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # retry | reassign | force_approve | dismiss | increase_budget | block_permanently

    resolution_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FounderDecision(Base, SnowflakeIDMixin):
    """
    Hồ sơ quyết định chiến lược của Founder (Founder Decision Object & Queue).

    Phục vụ hàng đợi ra quyết định của Founder (Waiting for You), liên kết trực tiếp
    với Evidence Engine (F1/F3) và hỗ trợ Co-Founder phản biện (Challenge Mode).
    """
    __tablename__ = "founder_decisions"
    __table_args__ = {"schema": "agent_runtime"}

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    project_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    domain: Mapped[str] = mapped_column(String(50), default="CROSS_DOMAIN", index=True)  # SALES, MARKETING, FINANCE, LEGAL, TECH, CROSS_DOMAIN
    question: Mapped[str] = mapped_column(Text)
    context_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    options_jsonb: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list)
    ai_recommendation_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    evidence_ids: Mapped[List[str]] = mapped_column(JSONB, default=list)  # Liên kết Evidence IDs từ F1/F3
    risk_analysis_jsonb: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", index=True)  # PENDING, DECIDED, DISMISSED, DEFERRED
    decision_made: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    founder_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_by_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentAlias(Base, SnowflakeIDMixin):
    """
    Ánh xạ bí danh (Agent Alias / Soft Migration Layer).
    
    Hỗ trợ tương thích ngược khi gọi các agent keys cũ, tự động điều hướng sang
    COSA Co-Founder, Domain Agents, Specialists hoặc Shared Capabilities.
    """
    __tablename__ = "agent_aliases"

    workspace_id: Mapped[Optional[int]] = mapped_column(BigInteger, index=True, nullable=True)
    alias_key: Mapped[str] = mapped_column(String(100), index=True)  # vd: 'founder_agent', 'research_agent', 'seo_agent'
    target_type: Mapped[str] = mapped_column(String(50))  # 'ORCHESTRATOR', 'DOMAIN', 'SPECIALIST', 'CAPABILITY', 'TOOL'
    target_key: Mapped[str] = mapped_column(String(100))  # vd: 'cosa', 'investigate', 'marketing.seo'
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("workspace_id", "alias_key", name="uq_agent_alias_ws_key"),
        {"schema": "agent_runtime"},
    )

