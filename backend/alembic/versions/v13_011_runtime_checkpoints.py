"""create runtime_checkpoints table

Revision ID: v13_011_checkpoints
Revises: v13_010_handoffs
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "v13_011_checkpoints"
down_revision: Union[str, Sequence[str], None] = "v13_010_handoffs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runtime_checkpoints",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
        sa.Column("cycle_id", sa.BigInteger(), sa.ForeignKey("twelve_week_cycles.id"), nullable=True, index=True),
        sa.Column("weekly_mission_id", sa.BigInteger(), sa.ForeignKey("weekly_commitments.id"), nullable=True, index=True),
        sa.Column("sequence", sa.Integer(), server_default="1", nullable=False),
        sa.Column("work_item_states", postgresql.JSONB(), nullable=True),
        sa.Column("dependency_state", postgresql.JSONB(), nullable=True),
        sa.Column("pending_approvals", postgresql.JSONB(), nullable=True),
        sa.Column("pending_needs_you", postgresql.JSONB(), nullable=True),
        sa.Column("active_executors", postgresql.JSONB(), nullable=True),
        sa.Column("checkpoint_reason", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade() -> None:
    op.drop_table("runtime_checkpoints")
