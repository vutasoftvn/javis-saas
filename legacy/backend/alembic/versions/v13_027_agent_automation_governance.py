"""agent runtime governance + automation runtime tables (additive)

Revision ID: v13_027_agent_governance
Revises: v13_026_reference_ids
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "v13_027_agent_governance"
down_revision: Union[str, Sequence[str], None] = "v13_026_reference_ids"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # agent_runs
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("conversation_id", sa.BigInteger(), nullable=True),
        sa.Column("parent_run_id", sa.BigInteger(), nullable=True),
        sa.Column("agent_key", sa.String(length=100), nullable=False),
        sa.Column("runtime", sa.String(length=50), nullable=False, server_default="mock"),
        sa.Column("runtime_version", sa.String(length=50), nullable=True),
        sa.Column("runtime_session_id", sa.String(length=255), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="completed"),
        sa.Column("permission_profile", sa.String(length=50), nullable=False, server_default="read_only"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_runs_workspace_id"), "agent_runs", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_agent_runs_company_id"), "agent_runs", ["company_id"], unique=False)
    op.create_index(op.f("ix_agent_runs_user_id"), "agent_runs", ["user_id"], unique=False)
    op.create_index(op.f("ix_agent_runs_conversation_id"), "agent_runs", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_agent_runs_parent_run_id"), "agent_runs", ["parent_run_id"], unique=False)
    op.create_index(op.f("ix_agent_runs_agent_key"), "agent_runs", ["agent_key"], unique=False)

    # agent_events
    op.create_table(
        "agent_events",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("agent_key", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("payload_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("runtime_event_id", sa.String(length=255), nullable=True),
        sa.Column("parent_event_id", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_events_run_id"), "agent_events", ["run_id"], unique=False)

    # agent_tool_calls
    op.create_table(
        "agent_tool_calls",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("agent_key", sa.String(length=100), nullable=False),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="low"),
        sa.Column("input_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("output_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="success"),
        sa.Column("approval_id", sa.BigInteger(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_tool_calls_run_id"), "agent_tool_calls", ["run_id"], unique=False)
    op.create_index(op.f("ix_agent_tool_calls_approval_id"), "agent_tool_calls", ["approval_id"], unique=False)

    # agent_approvals
    op.create_table(
        "agent_approvals",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=True),
        sa.Column("requested_by_agent", sa.String(length=100), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=True),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("input_preview_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.BigInteger(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("execution_result_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["agent_runs.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_approvals_workspace_id"), "agent_approvals", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_agent_approvals_company_id"), "agent_approvals", ["company_id"], unique=False)
    op.create_index(op.f("ix_agent_approvals_run_id"), "agent_approvals", ["run_id"], unique=False)

    # automation_definitions
    op.create_table(
        "automation_definitions",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("automation_key", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=50), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="n8n"),
        sa.Column("provider_workflow_ref", sa.String(length=255), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="low"),
        sa.Column("approval_mode", sa.String(length=50), nullable=False, server_default="none"),
        sa.Column("input_schema_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("output_schema_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("automation_key", name="uq_automation_definitions_key"),
    )
    op.create_index(op.f("ix_automation_definitions_automation_key"), "automation_definitions", ["automation_key"], unique=True)

    # automation_runs
    op.create_table(
        "automation_runs",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("workspace_id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=True),
        sa.Column("automation_key", sa.String(length=100), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="n8n"),
        sa.Column("provider_execution_id", sa.String(length=255), nullable=True),
        sa.Column("agent_run_id", sa.BigInteger(), nullable=True),
        sa.Column("approval_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="running"),
        sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="low"),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("payload_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_automation_runs_idempotency_key"),
    )
    op.create_index(op.f("ix_automation_runs_workspace_id"), "automation_runs", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_automation_runs_company_id"), "automation_runs", ["company_id"], unique=False)
    op.create_index(op.f("ix_automation_runs_automation_key"), "automation_runs", ["automation_key"], unique=False)
    op.create_index(op.f("ix_automation_runs_provider_execution_id"), "automation_runs", ["provider_execution_id"], unique=False)
    op.create_index(op.f("ix_automation_runs_agent_run_id"), "automation_runs", ["agent_run_id"], unique=False)
    op.create_index(op.f("ix_automation_runs_approval_id"), "automation_runs", ["approval_id"], unique=False)

    # automation_callbacks
    op.create_table(
        "automation_callbacks",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("provider_execution_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("signature", sa.String(length=255), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("payload_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["run_id"], ["automation_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_automation_callbacks_run_id"), "automation_callbacks", ["run_id"], unique=False)


def downgrade() -> None:
    op.drop_table("automation_callbacks")
    op.drop_table("automation_runs")
    op.drop_table("automation_definitions")
    op.drop_table("agent_approvals")
    op.drop_table("agent_tool_calls")
    op.drop_table("agent_events")
    op.drop_table("agent_runs")
