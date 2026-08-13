from datetime import datetime
from typing import Iterable, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.platform.models import FeatureFlag
from app.core.snowflake import generate_snowflake_id

# Predefined V12 Feature Flag Keys
FLAG_PROJECT_CLASSIFIER_V12 = "project_classifier_v12"
FLAG_CYCLE_13WEEK_V12 = "cycle_13week_v12"
FLAG_MILESTONES_GATES_V12 = "milestones_gates_v12"
FLAG_METHODOLOGY_ROUTER_V12 = "methodology_router_v12"
FLAG_ASSISTED_TERRA_V12 = "assisted_terra_v12"
FLAG_WEEKLY_MISSIONS_V12 = "weekly_missions_v12"
FLAG_PORTFOLIO_V12 = "portfolio_v12"
FLAG_SHARED_PESTEL_V12 = "shared_pestel_v12"
FLAG_PORTFOLIO_SWOT_TOWS_V12 = "portfolio_swot_tows_v12"
FLAG_CAPACITY_PLANNER_V12 = "capacity_planner_v12"
FLAG_FOUNDER_ATTENTION_V12 = "founder_attention_v12"
FLAG_PORTFOLIO_CYCLE_V12 = "portfolio_cycle_v12"
FLAG_NEXT_BEST_ACTION_V12 = "next_best_action_v12"
FLAG_LIVING_PESTEL_V12 = "living_pestel_v12"

# mCOSA V12.2 - Hybrid LiveKit Local/Cloud realtime voice
FLAG_DESKTOP_LOCAL_TRANSPORT_V12_2 = "desktop_livekit_local_v12_2"

# mCOSA V12.3 - Hierarchical Agent Memory (MEM-0, ADR-MEM-001/002)
FLAG_AGENT_MEMORY_V12_3 = "agent_memory_v12_3"

# mCOSA V13 — Focused Company Cycle OS.
# Keep these keys centralized so routers, realtime tools and Flutter navigation
# all resolve the same workspace-scoped feature policy.
FLAG_LEGAL_FUNCTION_V13 = "legal_function_v13"
FLAG_MARKETING_FUNCTION_V13 = "marketing_function_v13"
FLAG_SALES_FUNCTION_V13 = "sales_function_v13"
FLAG_TECH_FUNCTION_V13 = "tech_function_v13"
FLAG_FINANCE_FUNCTION_V13 = "finance_function_v13"
FLAG_LEARNING_V13 = "learning_v13"
FLAG_CEO_BRIEF_V13 = "ceo_brief_v13"
FLAG_ADVANCED_ORG_CHART_V13 = "advanced_org_chart_v13"

# mCOSA V13.1 — Company Runtime
FLAG_COMPANY_RUNTIME_V13_1 = "company_runtime_v13_1"
FLAG_WORKITEM_STATE_MACHINE_V13_1 = "workitem_state_machine_v13_1"
FLAG_WORK_CONTRACT_V13_1 = "work_contract_v13_1"
FLAG_REVIEW_REWORK_V13_1 = "review_rework_v13_1"
FLAG_DEPENDENCY_DAG_V13_1 = "dependency_dag_v13_1"
FLAG_STRUCTURED_BLOCKER_V13_1 = "structured_blocker_v13_1"
FLAG_NEEDS_YOU_QUEUE_V13_1 = "needs_you_queue_v13_1"
FLAG_STRUCTURED_HANDOFF_V13_1 = "structured_handoff_v13_1"
FLAG_WORK_INSPECTOR_V13_1 = "work_inspector_v13_1"
FLAG_RUNTIME_CHECKPOINT_V13_1 = "runtime_checkpoint_v13_1"
FLAG_WORK_INTENT_CLASSIFIER_V13_1 = "work_intent_classifier_v13_1"
FLAG_QUICK_TASK_V13_1 = "quick_task_v13_1"
FLAG_COMPANY_WORK_V13_1 = "company_work_v13_1"

# V13.1 P1 Reserved Flags (default disabled)
FLAG_EXECUTOR_RESOLVER_V13_1 = "executor_resolver_v13_1"
FLAG_EPHEMERAL_SPECIALIST_V13_1 = "ephemeral_specialist_v13_1"
FLAG_CYCLE_GRANTS_V13_1 = "cycle_grants_v13_1"
FLAG_ROLE_ATTRIBUTION_V13_1 = "role_attribution_v13_1"
FLAG_AGENT_EXPERIENCE_V13_1 = "agent_experience_v13_1"
FLAG_FUNCTION_SKILLS_V13_1 = "function_skills_v13_1"

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


def is_enabled(db: Session, key: str, workspace_id: Optional[int] = None) -> bool:
    """Check if a feature flag is enabled.
    
    1. If workspace_id is provided, check for a workspace-specific override.
    2. Fall back to global flag (workspace_id IS NULL).
    3. Return False if no flag is found.
    """
    if workspace_id is not None:
        ws_flag = (
            db.query(FeatureFlag)
            .filter(FeatureFlag.workspace_id == workspace_id, FeatureFlag.key == key)
            .first()
        )
        if ws_flag is not None:
            return bool(ws_flag.enabled)

    global_flag = (
        db.query(FeatureFlag)
        .filter(FeatureFlag.workspace_id.is_(None), FeatureFlag.key == key)
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
    for flag in flags:
        if flag.workspace_id is None:
            effective.setdefault(flag.key, bool(flag.enabled))
        elif flag.workspace_id == workspace_id:
            effective[flag.key] = bool(flag.enabled)
    return effective
