"""Create agent_proposals table."""

from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "v13_035_agent_proposals"
down_revision = "v13_034_execution_skills"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_proposals",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
        sa.Column("company_id", sa.BigInteger(), nullable=True, index=True),
        sa.Column("run_id", sa.BigInteger(), sa.ForeignKey("agent_runs.id"), nullable=True, index=True),
        sa.Column("proposal_type", sa.String(length=50), nullable=False),
        sa.Column("created_by_agent", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("payload_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("reviewed_by", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("applied_resource_id", sa.String(length=100), nullable=True),
    )
    now = datetime.now(timezone.utc)
    feature_flags = sa.table(
        "feature_flags",
        sa.column("id", sa.BigInteger),
        sa.column("workspace_id", sa.BigInteger),
        sa.column("key", sa.String),
        sa.column("enabled", sa.Boolean),
        sa.column("description", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    from app.core.snowflake import generate_snowflake_id
    op.bulk_insert(
        feature_flags,
        [
            {
                "id": generate_snowflake_id(),
                "workspace_id": None,
                "key": "agent_runtime_tools",
                "enabled": False,
                "description": "Enables multi-turn ReAct tool execution loop in DeepSeek Harness Agent Runtime.",
                "created_at": now,
                "updated_at": now,
            },
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM feature_flags WHERE workspace_id IS NULL AND key = 'agent_runtime_tools'"
        )
    )
    op.drop_table("agent_proposals")

