"""Create agent_goals, agent_plans, agent_plan_steps, agent_business_memories tables."""

from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "v13_036_agentic_control_plane"
down_revision = "v13_035_agent_proposals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. agent_goals table
    op.create_table(
        "agent_goals",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
        sa.Column("company_id", sa.BigInteger(), nullable=True, index=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("goal_type", sa.String(length=50), nullable=False, server_default="business_goal"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_metric_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 2. agent_plans table
    op.create_table(
        "agent_plans",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("goal_id", sa.BigInteger(), sa.ForeignKey("agent_goals.id"), nullable=False, index=True),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
        sa.Column("company_id", sa.BigInteger(), nullable=True, index=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 3. agent_plan_steps table
    op.create_table(
        "agent_plan_steps",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("plan_id", sa.BigInteger(), sa.ForeignKey("agent_plans.id"), nullable=False, index=True),
        sa.Column("sequence_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=100), nullable=False, server_default="founder"),
        sa.Column("capability", sa.String(length=100), nullable=False, server_default="reasoning"),
        sa.Column("tool_id", sa.String(length=100), nullable=True),
        sa.Column("policy_level", sa.String(length=50), nullable=False, server_default="L0_READ"),
        sa.Column("input_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expected_output_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("output_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("dependencies_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("approval_id", sa.BigInteger(), nullable=True, index=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 4. agent_business_memories table
    op.create_table(
        "agent_business_memories",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
        sa.Column("company_id", sa.BigInteger(), nullable=True, index=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("memory_type", sa.String(length=50), nullable=False),
        sa.Column("domain", sa.String(length=50), nullable=False, server_default="general"),
        sa.Column("key", sa.String(length=255), nullable=False, index=True),
        sa.Column("value_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provenance_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("agent_business_memories")
    op.drop_table("agent_plan_steps")
    op.drop_table("agent_plans")
    op.drop_table("agent_goals")
