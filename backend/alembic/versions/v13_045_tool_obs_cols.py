"""Add resource_type, resource_id, capability, source_version, content_hash, provenance_jsonb, plan_id, step_id to agent_tool_calls.

Revision ID: v13_045_tool_obs_cols
Revises: v13_044_approval_action_cols
Create Date: 2026-08-15 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "v13_045_tool_obs_cols"
down_revision: Union[str, Sequence[str], None] = "v13_044_approval_action_cols"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("agent_tool_calls")]

    if "plan_id" not in columns:
        op.add_column("agent_tool_calls", sa.Column("plan_id", sa.BigInteger(), nullable=True))
        op.create_index("ix_agent_tool_calls_plan_id", "agent_tool_calls", ["plan_id"])

    if "step_id" not in columns:
        op.add_column("agent_tool_calls", sa.Column("step_id", sa.BigInteger(), nullable=True))
        op.create_index("ix_agent_tool_calls_step_id", "agent_tool_calls", ["step_id"])

    if "resource_type" not in columns:
        op.add_column("agent_tool_calls", sa.Column("resource_type", sa.String(100), nullable=True))

    if "resource_id" not in columns:
        op.add_column("agent_tool_calls", sa.Column("resource_id", sa.String(255), nullable=True))

    if "capability" not in columns:
        op.add_column("agent_tool_calls", sa.Column("capability", sa.String(150), nullable=True))
        op.create_index("ix_agent_tool_calls_capability", "agent_tool_calls", ["capability"])

    if "source_version" not in columns:
        op.add_column("agent_tool_calls", sa.Column("source_version", sa.String(50), nullable=True))

    if "content_hash" not in columns:
        op.add_column("agent_tool_calls", sa.Column("content_hash", sa.String(128), nullable=True))

    if "provenance_jsonb" not in columns:
        op.add_column("agent_tool_calls", sa.Column("provenance_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_index("ix_agent_tool_calls_capability", table_name="agent_tool_calls")
    op.drop_index("ix_agent_tool_calls_step_id", table_name="agent_tool_calls")
    op.drop_index("ix_agent_tool_calls_plan_id", table_name="agent_tool_calls")
    op.drop_column("agent_tool_calls", "provenance_jsonb")
    op.drop_column("agent_tool_calls", "content_hash")
    op.drop_column("agent_tool_calls", "source_version")
    op.drop_column("agent_tool_calls", "capability")
    op.drop_column("agent_tool_calls", "resource_id")
    op.drop_column("agent_tool_calls", "resource_type")
    op.drop_column("agent_tool_calls", "step_id")
    op.drop_column("agent_tool_calls", "plan_id")
