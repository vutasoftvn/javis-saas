"""migrate feature configuration to functional capability keys

Revision ID: v13_024_functional_flags
Revises: v13_023_schema_align

Historical rows remain readable through the application compatibility registry.
This migration copies their effective values forward without overwriting an
operator-created canonical row, at both global and workspace scope.
"""

from alembic import op
import sqlalchemy as sa

from app.core.feature_flags import LEGACY_FLAG_ALIASES
from app.core.snowflake import generate_snowflake_id


revision = "v13_024_functional_flags"
down_revision = "v13_023_schema_align"
branch_labels = None
depends_on = None


# Keep every AI tool's operational default explicit in migration history. These
# are versionless functional keys; a missing row would silently hide a tool.
_TOOL_DEFAULTS = {
    "executive_brief": True,
    "next_best_action": True,
    "weekly_missions": True,
    "technology_operations": True,
    "finance_operations": True,
    "portfolio_intelligence": False,
    "company_runtime": True,
    "dependency_management": True,
    "structured_blockers": True,
    "needs_you_queue": True,
    "structured_handoffs": True,
    "review_rework": True,
    "work_inspector": True,
    "runtime_checkpoints": True,
    "work_intent_classification": True,
}


def _canonical_exists(bind, workspace_id, key: str) -> bool:
    return bind.execute(
        sa.text(
            "SELECT 1 FROM feature_flags "
            "WHERE workspace_id IS NOT DISTINCT FROM :workspace_id AND key = :key"
        ),
        {"workspace_id": workspace_id, "key": key},
    ).first() is not None


def upgrade() -> None:
    bind = op.get_bind()
    for legacy_key, canonical_key in LEGACY_FLAG_ALIASES.items():
        rows = bind.execute(
            sa.text(
                "SELECT workspace_id, enabled, description, created_at, updated_at "
                "FROM feature_flags WHERE key = :key"
            ),
            {"key": legacy_key},
        ).mappings()
        for row in rows:
            if _canonical_exists(bind, row["workspace_id"], canonical_key):
                continue
            bind.execute(
                sa.text(
                    "INSERT INTO feature_flags "
                    "(id, workspace_id, key, enabled, description, created_at, updated_at) "
                    "VALUES (:id, :workspace_id, :key, :enabled, :description, :created_at, :updated_at)"
                ),
                {"id": generate_snowflake_id(), "key": canonical_key, **dict(row)},
            )

    for key, enabled in _TOOL_DEFAULTS.items():
        if not _canonical_exists(bind, None, key):
            bind.execute(
                sa.text(
                    "INSERT INTO feature_flags "
                    "(id, workspace_id, key, enabled, description, created_at, updated_at) "
                    "VALUES (:id, NULL, :key, :enabled, :description, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {
                    "id": generate_snowflake_id(),
                    "key": key,
                    "enabled": enabled,
                    "description": "Functional capability default",
                },
            )


def downgrade() -> None:
    # Capability configuration is operator state. Do not remove copied rows.
    pass
