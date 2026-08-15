"""Add capability, resource_type, resource_id, simulation_result_jsonb, idempotency_key, and is_strong_approval columns to agent_approvals.

Revision ID: v13_044_approval_action_cols
Revises: v13_043_capability_grants
Create Date: 2026-08-15 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "v13_044_approval_action_cols"
down_revision: Union[str, Sequence[str], None] = "v13_043_capability_grants"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("agent_approvals")]

    if "capability" not in columns:
        op.add_column("agent_approvals", sa.Column("capability", sa.String(150), nullable=True))
        op.create_index("ix_agent_approvals_capability", "agent_approvals", ["capability"])

    if "resource_type" not in columns:
        op.add_column("agent_approvals", sa.Column("resource_type", sa.String(100), nullable=True))

    if "resource_id" not in columns:
        op.add_column("agent_approvals", sa.Column("resource_id", sa.String(255), nullable=True))

    if "simulation_result_jsonb" not in columns:
        op.add_column("agent_approvals", sa.Column("simulation_result_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    if "idempotency_key" not in columns:
        op.add_column("agent_approvals", sa.Column("idempotency_key", sa.String(255), nullable=True))
        op.create_index("ix_agent_approvals_idempotency_key", "agent_approvals", ["idempotency_key"])

    if "is_strong_approval" not in columns:
        op.add_column("agent_approvals", sa.Column("is_strong_approval", sa.Boolean(), server_default=sa.text("false"), nullable=False))


def downgrade() -> None:
    op.drop_index("ix_agent_approvals_idempotency_key", table_name="agent_approvals")
    op.drop_index("ix_agent_approvals_capability", table_name="agent_approvals")
    op.drop_column("agent_approvals", "is_strong_approval")
    op.drop_column("agent_approvals", "idempotency_key")
    op.drop_column("agent_approvals", "simulation_result_jsonb")
    op.drop_column("agent_approvals", "resource_id")
    op.drop_column("agent_approvals", "resource_type")
    op.drop_column("agent_approvals", "capability")
