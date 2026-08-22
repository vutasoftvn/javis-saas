from datetime import datetime
from typing import Iterable, Optional

from fastapi import HTTPException, status
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, Session, mapped_column

from cosa_core.db.base import Base
from cosa_core.snowflake import generate_snowflake_id


class FeatureFlag(Base):
    __tablename__ = "feature_flags"
    __table_args__ = (
        UniqueConstraint('workspace_id', 'key', name='uix_feature_flag_workspace_key'),
        Index('uix_feature_flags_global_key', 'key', unique=True, postgresql_where=text('workspace_id IS NULL')),
        {"schema": "core"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False, default=generate_snowflake_id)
    workspace_id: Mapped[Optional[int]] = mapped_column(ForeignKey("core.workspaces.id"), nullable=True, index=True)
    key: Mapped[str] = mapped_column(String(100), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Canonical functional capability keys.  The historical constant names remain
# temporarily so downstream imports do not break during the rollout; their
# *values* are versionless and all persistence goes through the registry below.
FLAG_PROJECT_CLASSIFIER_V12 = "project_classification"
FLAG_CYCLE_13WEEK_V12 = "twelve_week_planning"
FLAG_MILESTONES_GATES_V12 = "milestone_gates"
FLAG_METHODOLOGY_ROUTER_V12 = "methodology_planning"
FLAG_ASSISTED_TERRA_V12 = "assisted_strategy_analysis"
FLAG_WEEKLY_MISSIONS_V12 = "weekly_missions"
FLAG_PORTFOLIO_V12 = "portfolio_intelligence"
FLAG_SHARED_PESTEL_V12 = "shared_pestel"
FLAG_PORTFOLIO_SWOT_TOWS_V12 = "portfolio_swot_tows"
FLAG_CAPACITY_PLANNER_V12 = "capacity_planning"
FLAG_FOUNDER_ATTENTION_V12 = "founder_attention"
FLAG_PORTFOLIO_CYCLE_V12 = "portfolio_cycles"
FLAG_NEXT_BEST_ACTION_V12 = "next_best_action"
FLAG_LIVING_PESTEL_V12 = "living_pestel"
FLAG_DESKTOP_LOCAL_TRANSPORT_V12_2 = "desktop_local_transport"
FLAG_AGENT_MEMORY_V12_3 = "agent_memory"
FLAG_LEGAL_FUNCTION_V13 = "legal_operations"
FLAG_MARKETING_FUNCTION_V13 = "marketing_operations"
FLAG_SALES_FUNCTION_V13 = "sales_operations"
FLAG_TECH_FUNCTION_V13 = "technology_operations"
FLAG_FINANCE_FUNCTION_V13 = "finance_operations"
FLAG_LEARNING_V13 = "organizational_learning"
FLAG_CEO_BRIEF_V13 = "executive_brief"
FLAG_ADVANCED_ORG_CHART_V13 = "organization_chart"

# mCOSA V13.1 — Company Runtime
FLAG_COMPANY_RUNTIME_V13_1 = "company_runtime"
FLAG_WORKITEM_STATE_MACHINE_V13_1 = "work_management_state_machine"
FLAG_WORK_CONTRACT_V13_1 = "work_contract"
FLAG_REVIEW_REWORK_V13_1 = "review_rework"
FLAG_DEPENDENCY_DAG_V13_1 = "dependency_management"
FLAG_STRUCTURED_BLOCKER_V13_1 = "structured_blockers"
FLAG_NEEDS_YOU_QUEUE_V13_1 = "needs_you_queue"
FLAG_STRUCTURED_HANDOFF_V13_1 = "structured_handoffs"
FLAG_WORK_INSPECTOR_V13_1 = "work_inspector"
FLAG_RUNTIME_CHECKPOINT_V13_1 = "runtime_checkpoints"
FLAG_WORK_INTENT_CLASSIFIER_V13_1 = "work_intent_classification"
FLAG_QUICK_TASK_V13_1 = "quick_tasks"
FLAG_COMPANY_WORK_V13_1 = "company_work"

# V13.1 P1 Reserved Flags (default disabled)
FLAG_EXECUTOR_RESOLVER_V13_1 = "executor_resolution"
FLAG_EPHEMERAL_SPECIALIST_V13_1 = "ephemeral_specialists"
FLAG_CYCLE_GRANTS_V13_1 = "cycle_grants"
FLAG_ROLE_ATTRIBUTION_V13_1 = "role_attribution"
FLAG_AGENT_EXPERIENCE_V13_1 = "agent_experience"
FLAG_FUNCTION_SKILLS_V13_1 = "functional_skills"

# mCOSA V13.2 — Revenue & Sales Operating System
FLAG_SALES_CRM_CORE_V13_2 = "sales_crm"
FLAG_ACCOUNT_CONTACT_V13_2 = "account_contact_management"
FLAG_LEAD_MANAGEMENT_V13_2 = "lead_management"
FLAG_OPPORTUNITY_MANAGEMENT_V13_2 = "opportunity_management"
FLAG_CUSTOMER_CORE_V13_2 = "customer_management"
FLAG_MARKETING_SALES_HANDOFF_V13_2 = "marketing_sales_handoff"
FLAG_SALES_FINANCE_HANDOFF_V13_2 = "sales_finance_handoff"
FLAG_SALES_LEGAL_HANDOFF_V13_2 = "sales_legal_handoff"
FLAG_SALES_TECH_HANDOFF_V13_2 = "sales_technology_handoff"
FLAG_CONVERSATION_GATE_V13_2 = "conversation_gate"
FLAG_STRATEGY_MODULE_V13_2 = "strategy_module"

# Agent Runtime Flags
FLAG_AGENT_RUNTIME = "agent_runtime"
FLAG_AGENT_RUNTIME_DEEPSEEK = "agent_runtime_deepseek"
FLAG_AGENT_RUNTIME_TOOLS = "agent_runtime_tools"
FLAG_AGENT_EXECUTION = "agent_execution"
FLAG_AGENT_EXECUTION_SANDBOX = "agent_execution_sandbox"
FLAG_AGENT_EXECUTION_BROWSER = "agent_execution_browser"
FLAG_AGENT_EXECUTION_CODING = "agent_execution_coding"
FLAG_AGENT_EXECUTION_SKILLS = "agent_execution_skills"
FLAG_AGENT_DELEGATION = "agent_delegation"

FLAG_AGENT_DELEGATION_CHIEF_OF_STAFF = "agent_delegation_chief_of_staff"
FLAG_AGENT_DELEGATION_DEVICE_EXECUTORS = "agent_delegation_device_executors"
FLAG_AGENT_DELEGATION_N8N = "agent_delegation_n8n"
FLAG_AGENT_DELEGATION_SANDBOX = "agent_delegation_sandbox"

V13_2_P0_FLAGS = frozenset({
    FLAG_SALES_CRM_CORE_V13_2,
    FLAG_ACCOUNT_CONTACT_V13_2,
    FLAG_LEAD_MANAGEMENT_V13_2,
    FLAG_OPPORTUNITY_MANAGEMENT_V13_2,
    FLAG_CUSTOMER_CORE_V13_2,
    FLAG_MARKETING_SALES_HANDOFF_V13_2,
    FLAG_SALES_FINANCE_HANDOFF_V13_2,
    FLAG_SALES_LEGAL_HANDOFF_V13_2,
    FLAG_SALES_TECH_HANDOFF_V13_2,
})

V13_FEATURE_FLAGS = {
    FLAG_LEGAL_FUNCTION_V13,
    FLAG_MARKETING_FUNCTION_V13,
    FLAG_SALES_FUNCTION_V13,
    FLAG_TECH_FUNCTION_V13,
    FLAG_FINANCE_FUNCTION_V13,
    FLAG_LEARNING_V13,
    FLAG_CEO_BRIEF_V13,
    FLAG_ADVANCED_ORG_CHART_V13,
}

V13_DEFAULT_DISABLED_FEATURE_FLAGS = frozenset({FLAG_ADVANCED_ORG_CHART_V13})
V13_DEFAULT_ENABLED_FEATURE_FLAGS = frozenset(V13_FEATURE_FLAGS - V13_DEFAULT_DISABLED_FEATURE_FLAGS)

# mCOSA V13.1 Feature Flag Sets
V13_1_P0_FLAGS = frozenset({
    FLAG_COMPANY_RUNTIME_V13_1,
    FLAG_WORKITEM_STATE_MACHINE_V13_1,
    FLAG_WORK_CONTRACT_V13_1,
    FLAG_REVIEW_REWORK_V13_1,
    FLAG_DEPENDENCY_DAG_V13_1,
    FLAG_STRUCTURED_BLOCKER_V13_1,
    FLAG_NEEDS_YOU_QUEUE_V13_1,
    FLAG_STRUCTURED_HANDOFF_V13_1,
    FLAG_WORK_INSPECTOR_V13_1,
    FLAG_RUNTIME_CHECKPOINT_V13_1,
    FLAG_WORK_INTENT_CLASSIFIER_V13_1,
    FLAG_QUICK_TASK_V13_1,
    FLAG_COMPANY_WORK_V13_1,
})

V13_1_P1_FLAGS = frozenset({
    FLAG_EXECUTOR_RESOLVER_V13_1,
    FLAG_EPHEMERAL_SPECIALIST_V13_1,
    FLAG_CYCLE_GRANTS_V13_1,
    FLAG_ROLE_ATTRIBUTION_V13_1,
    FLAG_AGENT_EXPERIENCE_V13_1,
    FLAG_FUNCTION_SKILLS_V13_1,
})

V13_1_FEATURE_FLAGS = frozenset(V13_1_P0_FLAGS | V13_1_P1_FLAGS)

# ``legacy -> canonical``.  Keep this data-only compatibility layer at the
# persistence boundary; routers and tools receive canonical values from their
# constants above.  It can be deleted after old workspace overrides expire.
LEGACY_FLAG_ALIASES = {
    "project_classifier_v12": FLAG_PROJECT_CLASSIFIER_V12,
    "cycle_13week_v12": FLAG_CYCLE_13WEEK_V12,
    "milestones_gates_v12": FLAG_MILESTONES_GATES_V12,
    "methodology_router_v12": FLAG_METHODOLOGY_ROUTER_V12,
    "assisted_terra_v12": FLAG_ASSISTED_TERRA_V12,
    "weekly_missions_v12": FLAG_WEEKLY_MISSIONS_V12,
    "portfolio_v12": FLAG_PORTFOLIO_V12,
    "shared_pestel_v12": FLAG_SHARED_PESTEL_V12,
    "portfolio_swot_tows_v12": FLAG_PORTFOLIO_SWOT_TOWS_V12,
    "capacity_planner_v12": FLAG_CAPACITY_PLANNER_V12,
    "founder_attention_v12": FLAG_FOUNDER_ATTENTION_V12,
    "portfolio_cycle_v12": FLAG_PORTFOLIO_CYCLE_V12,
    "next_best_action_v12": FLAG_NEXT_BEST_ACTION_V12,
    "living_pestel_v12": FLAG_LIVING_PESTEL_V12,
    "desktop_livekit_local_v12_2": FLAG_DESKTOP_LOCAL_TRANSPORT_V12_2,
    "agent_memory_v12_3": FLAG_AGENT_MEMORY_V12_3,
    "legal_function_v13": FLAG_LEGAL_FUNCTION_V13,
    "marketing_function_v13": FLAG_MARKETING_FUNCTION_V13,
    "sales_function_v13": FLAG_SALES_FUNCTION_V13,
    "tech_function_v13": FLAG_TECH_FUNCTION_V13,
    "finance_function_v13": FLAG_FINANCE_FUNCTION_V13,
    "learning_v13": FLAG_LEARNING_V13,
    "ceo_brief_v13": FLAG_CEO_BRIEF_V13,
    "advanced_org_chart_v13": FLAG_ADVANCED_ORG_CHART_V13,
    "company_runtime_v13_1": FLAG_COMPANY_RUNTIME_V13_1,
    "workitem_state_machine_v13_1": FLAG_WORKITEM_STATE_MACHINE_V13_1,
    "work_contract_v13_1": FLAG_WORK_CONTRACT_V13_1,
    "review_rework_v13_1": FLAG_REVIEW_REWORK_V13_1,
    "dependency_dag_v13_1": FLAG_DEPENDENCY_DAG_V13_1,
    "structured_blocker_v13_1": FLAG_STRUCTURED_BLOCKER_V13_1,
    "needs_you_queue_v13_1": FLAG_NEEDS_YOU_QUEUE_V13_1,
    "structured_handoff_v13_1": FLAG_STRUCTURED_HANDOFF_V13_1,
    "work_inspector_v13_1": FLAG_WORK_INSPECTOR_V13_1,
    "runtime_checkpoint_v13_1": FLAG_RUNTIME_CHECKPOINT_V13_1,
    "work_intent_classifier_v13_1": FLAG_WORK_INTENT_CLASSIFIER_V13_1,
    "quick_task_v13_1": FLAG_QUICK_TASK_V13_1,
    "company_work_v13_1": FLAG_COMPANY_WORK_V13_1,
    "sales_crm_core_v13_2": FLAG_SALES_CRM_CORE_V13_2,
    "account_contact_v13_2": FLAG_ACCOUNT_CONTACT_V13_2,
    "lead_management_v13_2": FLAG_LEAD_MANAGEMENT_V13_2,
    "opportunity_management_v13_2": FLAG_OPPORTUNITY_MANAGEMENT_V13_2,
    "customer_core_v13_2": FLAG_CUSTOMER_CORE_V13_2,
    "marketing_sales_handoff_v13_2": FLAG_MARKETING_SALES_HANDOFF_V13_2,
    "sales_finance_handoff_v13_2": FLAG_SALES_FINANCE_HANDOFF_V13_2,
    "sales_legal_handoff_v13_2": FLAG_SALES_LEGAL_HANDOFF_V13_2,
    "sales_tech_handoff_v13_2": FLAG_SALES_TECH_HANDOFF_V13_2,
}


def canonical_flag_key(key: str) -> str:
    """Return the stable functional key for a persisted or requested key."""
    return LEGACY_FLAG_ALIASES.get(key, key)


def _candidate_keys(key: str) -> tuple[str, ...]:
    canonical = canonical_flag_key(key)
    legacy = tuple(alias for alias, target in LEGACY_FLAG_ALIASES.items() if target == canonical)
    return (canonical, *legacy)

# Mọi flag đang khoá một tool AI, kèm mặc định mong muốn.
#
# is_enabled() trả False khi không tìm thấy row, nên một flag chỉ được khai báo mà không
# ai seed = tool tương ứng biến mất khỏi cả voice lẫn chat mà không có lỗi nào để lần ra.
# Đúng chuyện đã xảy ra với next_best_action_v12: prompt dặn model "LUÔN gọi
# get_next_best_actions" trong khi tool đó chưa bao giờ được gắn.
#
# Đây là nguồn sự thật để test_feature_flags đối chiếu với tool_registry và với migration.
# Thêm tool có flag mới thì thêm một dòng ở đây VÀ seed trong migration.
TOOL_FLAG_DEFAULTS = {
    FLAG_CEO_BRIEF_V13: True,
    FLAG_NEXT_BEST_ACTION_V12: True,
    FLAG_WEEKLY_MISSIONS_V12: True,
    FLAG_TECH_FUNCTION_V13: True,
    FLAG_FINANCE_FUNCTION_V13: True,
    FLAG_SALES_FUNCTION_V13: True,
    FLAG_LEGAL_FUNCTION_V13: True,
    FLAG_MARKETING_FUNCTION_V13: True,
    FLAG_SALES_CRM_CORE_V13_2: True,
    FLAG_STRATEGY_MODULE_V13_2: True,
    # Tắt có chủ đích: chưa có UI portfolio đi kèm (xem v13_001_flags).
    FLAG_PORTFOLIO_V12: False,
    FLAG_COMPANY_RUNTIME_V13_1: True,
    FLAG_DEPENDENCY_DAG_V13_1: True,
    FLAG_STRUCTURED_BLOCKER_V13_1: True,
    FLAG_NEEDS_YOU_QUEUE_V13_1: True,
    FLAG_STRUCTURED_HANDOFF_V13_1: True,
    FLAG_REVIEW_REWORK_V13_1: True,
    FLAG_WORK_INSPECTOR_V13_1: True,
    FLAG_RUNTIME_CHECKPOINT_V13_1: True,
    FLAG_WORK_INTENT_CLASSIFIER_V13_1: True,
    FLAG_AGENT_RUNTIME_TOOLS: False,
    FLAG_AGENT_EXECUTION: False,
    FLAG_AGENT_EXECUTION_BROWSER: False,
    FLAG_AGENT_EXECUTION_CODING: False,
    FLAG_AGENT_EXECUTION_SKILLS: False,
}


def is_enabled(db: Session, key: str, workspace_id: Optional[int] = None) -> bool:
    """Check if a feature flag is enabled.

    1. If workspace_id is provided, check for a workspace-specific override.
    2. Fall back to global flag (workspace_id IS NULL).
    3. Return False if no flag is found.
    """
    candidates = _candidate_keys(key)
    if workspace_id is not None:
        for candidate in candidates:
            ws_flag = (
                db.query(FeatureFlag)
                .filter(FeatureFlag.workspace_id == workspace_id, FeatureFlag.key == candidate)
                .first()
            )
            if ws_flag is not None:
                return bool(ws_flag.enabled)

    for candidate in candidates:
        global_flag = (
            db.query(FeatureFlag)
            .filter(FeatureFlag.workspace_id.is_(None), FeatureFlag.key == candidate)
            .first()
        )
        if global_flag is not None:
            return bool(global_flag.enabled)

    return False


def require_flag(db: Session, key: str, workspace_id: Optional[int] = None) -> None:
    """Raise 403 unless the given feature flag is enabled for this workspace."""
    if not is_enabled(db, key, workspace_id=workspace_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Feature '{key}' is not enabled for this workspace",
        )


def set_feature_flag(
    db: Session,
    key: str,
    enabled: bool,
    workspace_id: Optional[int] = None,
    description: Optional[str] = None,
) -> FeatureFlag:
    """Set or create a feature flag (global or workspace-scoped)."""
    key = canonical_flag_key(key)
    query = db.query(FeatureFlag).filter(FeatureFlag.key == key)
    if workspace_id is not None:
        flag = query.filter(FeatureFlag.workspace_id == workspace_id).first()
    else:
        flag = query.filter(FeatureFlag.workspace_id.is_(None)).first()

    now = datetime.utcnow()
    if flag is not None:
        flag.enabled = enabled
        flag.updated_at = now
        if description is not None:
            flag.description = description
    else:
        flag = FeatureFlag(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            key=key,
            enabled=enabled,
            description=description,
            created_at=now,
            updated_at=now,
        )
        db.add(flag)

    db.commit()
    db.refresh(flag)
    return flag


def list_feature_flags(
    db: Session, workspace_id: Optional[int] = None
) -> list[FeatureFlag]:
    """List feature flags. If workspace_id is given, returns both global and workspace flags."""
    if workspace_id is not None:
        return (
            db.query(FeatureFlag)
            .filter(
                (FeatureFlag.workspace_id == workspace_id)
                | (FeatureFlag.workspace_id.is_(None))
            )
            .all()
        )
    return db.query(FeatureFlag).filter(FeatureFlag.workspace_id.is_(None)).all()


def effective_feature_flags(
    flags: Iterable[FeatureFlag], workspace_id: int
) -> dict[str, bool]:
    """Collapse global and workspace rows into the values visible to a workspace."""
    effective: dict[str, bool] = {}
    # Preserve global-versus-workspace precedence and, within each scope, give
    # the canonical row priority over its legacy fallback.
    ordered = sorted(
        flags,
        key=lambda flag: (
            0 if flag.workspace_id is None else 1,
            1 if flag.key == canonical_flag_key(flag.key) else 0,
        ),
    )
    for flag in ordered:
        if flag.workspace_id is None or flag.workspace_id == workspace_id:
            effective[canonical_flag_key(flag.key)] = bool(flag.enabled)
    return effective
