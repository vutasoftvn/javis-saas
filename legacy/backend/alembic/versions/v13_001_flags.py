"""seed focused V13 feature-flag defaults without changing existing overrides

Revision ID: v13_001_flags
Revises: cce0693a148d
Create Date: 2026-08-13 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from core.snowflake import generate_snowflake_id


revision: str = "v13_001_flags"
down_revision: Union[str, Sequence[str], None] = "cce0693a148d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_ENABLED_DEFAULTS = (
    "legal_function_v13",
    "marketing_function_v13",
    "sales_function_v13",
    "tech_function_v13",
    "finance_function_v13",
    "learning_v13",
    "ceo_brief_v13",
)

_DISABLED_DEFAULTS = (
    "advanced_org_chart_v13",
    "portfolio_v12",
    "capacity_planner_v12",
    "founder_attention_v12",
    "portfolio_cycle_v12",
    "portfolio_swot_tows_v12",
)


def _insert_absent(bind, key: str, enabled: bool) -> None:
    exists = bind.execute(
        sa.text("SELECT 1 FROM feature_flags WHERE workspace_id IS NULL AND key = :key"),
        {"key": key},
    ).first()
    if exists is None:
        bind.execute(
            sa.text(
                "INSERT INTO feature_flags "
                "(id, workspace_id, key, enabled, description, created_at, updated_at) "
                "VALUES (:id, NULL, :key, :enabled, :description, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"id": generate_snowflake_id(), "key": key, "enabled": enabled, "description": "mCOSA V13 focused-company-cycle default"},
        )


def upgrade() -> None:
    """Add absent global defaults; preserve every existing flag row exactly."""
    bind = op.get_bind()
    for key in _ENABLED_DEFAULTS:
        _insert_absent(bind, key, True)
    for key in _DISABLED_DEFAULTS:
        _insert_absent(bind, key, False)


def downgrade() -> None:
    """Do not delete flags: configuration is intentionally non-destructive."""
