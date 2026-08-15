"""Add company_id, plan_id, step_id, actor_type, actor_id, tool_id, status columns to agent_events and make run_id nullable.

Revision ID: v13_040_agent_events_columns
Revises: v13_039_cycle_proj_dur
Create Date: 2026-08-15 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "v13_040_agent_events_columns"
down_revision: Union[str, Sequence[str], None] = "v13_039_cycle_proj_dur"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("agent_events")]

    op.alter_column("agent_events", "run_id", existing_type=sa.BigInteger(), nullable=True)

    if "company_id" not in columns:
        op.add_column("agent_events", sa.Column("company_id", sa.BigInteger(), nullable=True))
        op.create_index(op.f("ix_agent_events_company_id"), "agent_events", ["company_id"], unique=False)

    if "plan_id" not in columns:
        op.add_column("agent_events", sa.Column("plan_id", sa.BigInteger(), nullable=True))
        op.create_index(op.f("ix_agent_events_plan_id"), "agent_events", ["plan_id"], unique=False)

    if "step_id" not in columns:
        op.add_column("agent_events", sa.Column("step_id", sa.BigInteger(), nullable=True))
        op.create_index(op.f("ix_agent_events_step_id"), "agent_events", ["step_id"], unique=False)

    if "actor_type" not in columns:
        op.add_column("agent_events", sa.Column("actor_type", sa.String(length=50), nullable=True))

    if "actor_id" not in columns:
        op.add_column("agent_events", sa.Column("actor_id", sa.String(length=255), nullable=True))

    if "tool_id" not in columns:
        op.add_column("agent_events", sa.Column("tool_id", sa.String(length=100), nullable=True))

    if "status" not in columns:
        op.add_column("agent_events", sa.Column("status", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_events", "status")
    op.drop_column("agent_events", "tool_id")
    op.drop_column("agent_events", "actor_id")
    op.drop_column("agent_events", "actor_type")
    op.drop_index(op.f("ix_agent_events_step_id"), table_name="agent_events")
    op.drop_column("agent_events", "step_id")
    op.drop_index(op.f("ix_agent_events_plan_id"), table_name="agent_events")
    op.drop_column("agent_events", "plan_id")
    op.drop_index(op.f("ix_agent_events_company_id"), table_name="agent_events")
    op.drop_column("agent_events", "company_id")
    op.alter_column("agent_events", "run_id", existing_type=sa.BigInteger(), nullable=False)
