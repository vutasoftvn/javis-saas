"""create blockers and needs_you_items tables

Revision ID: v13_009_blockers
Revises: v13_008_dag
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "v13_009_blockers"
down_revision: Union[str, Sequence[str], None] = "v13_008_dag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "blockers",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
        sa.Column("task_id", sa.BigInteger(), sa.ForeignKey("tasks.id"), nullable=True, index=True),
        sa.Column("outcome_id", sa.BigInteger(), sa.ForeignKey("outcomes.id"), nullable=True, index=True),
        sa.Column("cycle_id", sa.BigInteger(), sa.ForeignKey("twelve_week_cycles.id"), nullable=True, index=True),
        sa.Column("weekly_mission_id", sa.BigInteger(), sa.ForeignKey("weekly_commitments.id"), nullable=True, index=True),
        sa.Column("blocker_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("requested_capability", sa.String(100), nullable=True),
        sa.Column("assigned_function", sa.String(50), nullable=True, index=True),
        sa.Column("status", sa.String(50), server_default="OPEN", nullable=False),
        sa.Column("resolution_artifact_id", sa.BigInteger(), sa.ForeignKey("artifacts.id"), nullable=True),
        sa.Column("escalated_to", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )

    op.create_table(
        "needs_you_items",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
        sa.Column("cycle_id", sa.BigInteger(), sa.ForeignKey("twelve_week_cycles.id"), nullable=True, index=True),
        sa.Column("source_type", sa.String(50), nullable=False, index=True),
        sa.Column("source_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("priority", sa.String(20), server_default="P1", nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("requested_action", sa.String(255), nullable=True),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(50), server_default="OPEN", nullable=False),
        sa.Column("snooze_until", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("needs_you_items")
    op.drop_table("blockers")
