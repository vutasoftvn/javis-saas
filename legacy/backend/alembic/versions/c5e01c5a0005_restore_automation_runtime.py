"""restore automation runtime tables still owned by production models

Revision ID: c5e01c5a0005
Revises: c4e01c5a0004
Create Date: 2026-08-20 20:45:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c5e01c5a0005"
down_revision: Union[str, Sequence[str], None] = "c4e01c5a0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "automation_definitions",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("automation_key", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("domain", sa.String(50), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False, server_default="n8n"),
        sa.Column("provider_workflow_ref", sa.String(255), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="low"),
        sa.Column("approval_mode", sa.String(50), nullable=False, server_default="none"),
        sa.Column("input_schema_jsonb", postgresql.JSONB(), nullable=True),
        sa.Column("output_schema_jsonb", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("automation_key", name="uq_automation_definitions_key"),
    )
    op.create_index("ix_automation_definitions_automation_key", "automation_definitions", ["automation_key"], unique=False)
    op.create_index("ix_automation_definitions_id", "automation_definitions", ["id"], unique=False)

    op.create_table(
        "automation_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=True),
        sa.Column("automation_key", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False, server_default="n8n"),
        sa.Column("provider_execution_id", sa.String(255), nullable=True),
        sa.Column("agent_run_id", sa.BigInteger(), nullable=True),
        sa.Column("approval_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="running"),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="low"),
        sa.Column("idempotency_key", sa.String(255), nullable=True),
        sa.Column("payload_jsonb", postgresql.JSONB(), nullable=True),
        sa.Column("result_jsonb", postgresql.JSONB(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "idempotency_key", name="uq_automation_runs_workspace_idempotency"),
    )
    for column in ("workspace_id", "company_id", "automation_key", "provider_execution_id", "agent_run_id", "approval_id"):
        op.create_index(f"ix_automation_runs_{column}", "automation_runs", [column], unique=False)
    op.create_index("ix_automation_runs_id", "automation_runs", ["id"], unique=False)

    op.create_table(
        "automation_callbacks",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("provider_execution_id", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("signature", sa.String(255), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("payload_jsonb", postgresql.JSONB(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["run_id"], ["automation_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "signature", name="uq_automation_callbacks_run_signature"),
    )
    op.create_index("ix_automation_callbacks_run_id", "automation_callbacks", ["run_id"], unique=False)
    op.create_index("ix_automation_callbacks_id", "automation_callbacks", ["id"], unique=False)
    # Phase-C's first schema revision omitted the index declared by SnowflakeIDMixin.
    op.create_index("ix_delegation_jobs_id", "delegation_jobs", ["id"], unique=False)


def downgrade() -> None:
    # Tolerate databases that briefly ran the initial restoration revision before
    # the missing Snowflake index was folded into it.
    op.execute("DROP INDEX IF EXISTS ix_delegation_jobs_id")
    op.drop_table("automation_callbacks")
    op.drop_table("automation_runs")
    op.drop_table("automation_definitions")
