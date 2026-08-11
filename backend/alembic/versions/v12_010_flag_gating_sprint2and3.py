"""mcosa v12 sprint 2 and 3 feature flag gating defaults

Revision ID: v12_010_flags
Revises: v12_009_sprint10
Create Date: 2026-08-11 20:10:00.000000

Seeds the Sprint 1-3 feature flags (project_classifier_v12, cycle_13week_v12,
milestones_gates_v12, methodology_router_v12, assisted_terra_v12,
weekly_missions_v12) as globally enabled by default. These flags now gate their
respective /api/v1/strategy endpoints (see router.py and execution_router.py
`require_flag` calls); without a seeded default the endpoints would 403 for
every workspace since is_enabled() returns False when no row exists.
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'v12_010_flags'
down_revision: Union[str, Sequence[str], None] = 'v12_009_sprint10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FLAGS = [
    "project_classifier_v12",
    "cycle_13week_v12",
    "milestones_gates_v12",
    "methodology_router_v12",
    "assisted_terra_v12",
    "weekly_missions_v12",
]


def upgrade() -> None:
    feature_flags = sa.table(
        "feature_flags",
        sa.column("id", sa.Uuid()),
        sa.column("workspace_id", sa.Uuid()),
        sa.column("key", sa.String()),
        sa.column("enabled", sa.Boolean()),
        sa.column("description", sa.Text()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    # created_at/updated_at are left out so the column server_default (now())
    # defined on the feature_flags table applies.
    op.bulk_insert(
        feature_flags,
        [
            {
                "id": uuid.uuid4(),
                "workspace_id": None,
                "key": key,
                "enabled": True,
                "description": "Enabled by default at Sprint 2/3 rollout (backend gating added retroactively).",
            }
            for key in FLAGS
        ],
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM feature_flags WHERE workspace_id IS NULL AND key = ANY(:keys)"),
        {"keys": FLAGS},
    )
