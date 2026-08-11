"""mcosa v12 model profile overrides table + flag gating sprint6-10

Revision ID: v12_011_flags2
Revises: v12_010_flags
Create Date: 2026-08-11 21:00:00.000000

Creates `model_profile_overrides` (workspace-scoped admin override for the
STRATEGIC_ANALYZER/CONVERSATION_ROUTER/DEVELOPER_WORKER logical model profiles,
backing PUT /api/v1/strategy/model-profiles/{id} which was previously a no-op).

Seeds the Sprint 6-10 feature flags (portfolio_v12, shared_pestel_v12,
portfolio_swot_tows_v12, capacity_planner_v12, founder_attention_v12,
portfolio_cycle_v12, next_best_action_v12, living_pestel_v12) as globally
enabled by default. These flags were defined in feature_flags.py but never
seeded or checked via require_flag() in their routers; portfolio_router.py,
next_action_router.py and living_pestel_router.py now gate their endpoints
with require_flag() (mirroring the Sprint 1-3 pattern), so without a seeded
default every workspace would 403 on endpoints that were previously live
unconditionally.
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'v12_011_flags2'
down_revision: Union[str, Sequence[str], None] = 'v12_010_flags'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FLAGS = [
    "portfolio_v12",
    "shared_pestel_v12",
    "portfolio_swot_tows_v12",
    "capacity_planner_v12",
    "founder_attention_v12",
    "portfolio_cycle_v12",
    "next_best_action_v12",
    "living_pestel_v12",
]


def upgrade() -> None:
    op.create_table(
        'model_profile_overrides',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('workspace_id', sa.Uuid(), nullable=False),
        sa.Column('profile_key', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'profile_key', name='uix_model_profile_override_ws_key'),
    )
    op.create_index(
        op.f('ix_model_profile_overrides_workspace_id'),
        'model_profile_overrides', ['workspace_id'], unique=False,
    )

    feature_flags = sa.table(
        "feature_flags",
        sa.column("id", sa.Uuid()),
        sa.column("workspace_id", sa.Uuid()),
        sa.column("key", sa.String()),
        sa.column("enabled", sa.Boolean()),
        sa.column("description", sa.Text()),
    )
    op.bulk_insert(
        feature_flags,
        [
            {
                "id": uuid.uuid4(),
                "workspace_id": None,
                "key": key,
                "enabled": True,
                "description": "Enabled by default; endpoints were already live unconditionally before require_flag() gating was added.",
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
    op.drop_index(op.f('ix_model_profile_overrides_workspace_id'), table_name='model_profile_overrides')
    op.drop_table('model_profile_overrides')
