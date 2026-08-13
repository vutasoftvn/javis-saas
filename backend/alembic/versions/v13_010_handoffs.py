"""create handoffs table

Revision ID: v13_010_handoffs
Revises: v13_009_blockers
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "v13_010_handoffs"
down_revision: Union[str, Sequence[str], None] = "v13_009_blockers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "handoffs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
        sa.Column("cycle_id", sa.BigInteger(), sa.ForeignKey("twelve_week_cycles.id"), nullable=True, index=True),
        sa.Column("weekly_mission_id", sa.BigInteger(), sa.ForeignKey("weekly_commitments.id"), nullable=True, index=True),
        sa.Column("from_function", sa.String(50), nullable=False, index=True),
        sa.Column("to_function", sa.String(50), nullable=False, index=True),
        sa.Column("source_task_id", sa.BigInteger(), sa.ForeignKey("tasks.id"), nullable=True, index=True),
        sa.Column("target_task_id", sa.BigInteger(), sa.ForeignKey("tasks.id"), nullable=True, index=True),
        sa.Column("handoff_type", sa.String(50), nullable=False),
        sa.Column("requested_action", sa.Text(), nullable=False),
        sa.Column("artifact_refs", postgresql.JSONB(), nullable=True),
        sa.Column("decision_refs", postgresql.JSONB(), nullable=True),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(50), server_default="PENDING", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade() -> None:
    op.drop_table("handoffs")
