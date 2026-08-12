from datetime import datetime
from typing import Optional

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
