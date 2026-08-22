"""Add retry_count, max_retries, and fallback_used columns to agent_plan_steps.

Revision ID: v13_042_step_retry_cols
Revises: v13_041_agent_run_status_default
Create Date: 2026-08-15 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "v13_042_step_retry_cols"
down_revision: Union[str, Sequence[str], None] = "v13_041_agent_run_status_default"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("agent_plan_steps")]

    if "retry_count" not in columns:
        op.add_column("agent_plan_steps", sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False))

    if "max_retries" not in columns:
        op.add_column("agent_plan_steps", sa.Column("max_retries", sa.Integer(), server_default="3", nullable=False))

    if "fallback_used" not in columns:
        op.add_column("agent_plan_steps", sa.Column("fallback_used", sa.Boolean(), server_default=sa.text("false"), nullable=False))


def downgrade() -> None:
    op.drop_column("agent_plan_steps", "fallback_used")
    op.drop_column("agent_plan_steps", "max_retries")
    op.drop_column("agent_plan_steps", "retry_count")
