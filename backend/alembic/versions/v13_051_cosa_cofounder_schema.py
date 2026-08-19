"""Add COSA Co-Founder Architecture Schema (F4 Spec).

Adds category and is_default_active to agent_definitions.
Creates founder_decisions (Founder Decision Queue & Evidence Integration).
Creates agent_aliases (Soft Migration & Backward Compatibility Layer).

Revision ID: v13_051_cosa_cofounder_schema
Revises: v13_050_pending_schema_sync
Create Date: 2026-08-19 08:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "v13_051_cosa_cofounder_schema"
down_revision: Union[str, Sequence[str], None] = "5a2db44a5acd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Update agent_definitions table
    if "agent_definitions" in tables:
        columns = [c["name"] for c in inspector.get_columns("agent_definitions")]
        if "category" not in columns:
            op.add_column(
                "agent_definitions",
                sa.Column("category", sa.String(length=50), nullable=False, server_default="DOMAIN"),
            )
            op.create_index("ix_agent_definitions_category", "agent_definitions", ["category"])
        
        if "is_default_active" not in columns:
            op.add_column(
                "agent_definitions",
                sa.Column("is_default_active", sa.Boolean(), nullable=False, server_default="false"),
            )

    # 2. Create founder_decisions table
    if "founder_decisions" not in tables:
        op.create_table(
            "founder_decisions",
            sa.Column("id", sa.BigInteger(), nullable=False, primary_key=True),
            sa.Column("workspace_id", sa.BigInteger(), nullable=True),
            sa.Column("project_id", sa.BigInteger(), nullable=True),
            sa.Column("domain", sa.String(length=50), nullable=False, server_default="CROSS_DOMAIN"),
            sa.Column("question", sa.Text(), nullable=False),
            sa.Column("context_summary", sa.Text(), nullable=True),
            sa.Column("options_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
            sa.Column("ai_recommendation_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
            sa.Column("evidence_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
            sa.Column("risk_analysis_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
            sa.Column("decision_made", sa.Text(), nullable=True),
            sa.Column("founder_notes", sa.Text(), nullable=True),
            sa.Column("decided_by_user_id", sa.BigInteger(), nullable=True),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_founder_decisions_workspace_id", "founder_decisions", ["workspace_id"])
        op.create_index("ix_founder_decisions_project_id", "founder_decisions", ["project_id"])
        op.create_index("ix_founder_decisions_domain", "founder_decisions", ["domain"])
        op.create_index("ix_founder_decisions_status", "founder_decisions", ["status"])
        op.create_index("ix_founder_decisions_created_at", "founder_decisions", ["created_at"])

    # 3. Create agent_aliases table
    if "agent_aliases" not in tables:
        op.create_table(
            "agent_aliases",
            sa.Column("id", sa.BigInteger(), nullable=False, primary_key=True),
            sa.Column("workspace_id", sa.BigInteger(), nullable=True),
            sa.Column("alias_key", sa.String(length=100), nullable=False),
            sa.Column("target_type", sa.String(length=50), nullable=False),
            sa.Column("target_key", sa.String(length=100), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
            sa.Column("notes", sa.String(length=255), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("workspace_id", "alias_key", name="uq_agent_alias_ws_key"),
        )
        op.create_index("ix_agent_aliases_alias_key", "agent_aliases", ["alias_key"])
        op.create_index("ix_agent_aliases_workspace_id", "agent_aliases", ["workspace_id"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "agent_aliases" in tables:
        op.drop_table("agent_aliases")

    if "founder_decisions" in tables:
        op.drop_table("founder_decisions")

    if "agent_definitions" in tables:
        columns = [c["name"] for c in inspector.get_columns("agent_definitions")]
        if "is_default_active" in columns:
            op.drop_column("agent_definitions", "is_default_active")
        if "category" in columns:
            op.drop_index("ix_agent_definitions_category", table_name="agent_definitions")
            op.drop_column("agent_definitions", "category")
