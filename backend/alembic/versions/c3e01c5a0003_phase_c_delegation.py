"""add durable Phase C delegation coordination

Revision ID: c3e01c5a0003
Revises: b2e01c5a0002
Create Date: 2026-08-20 20:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c3e01c5a0003"
down_revision: Union[str, Sequence[str], None] = "b2e01c5a0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "run_steps",
        sa.Column("assigned_agent_profile_id", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "run_steps",
        sa.Column("assigned_runtime", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "run_steps",
        sa.Column("delegated_run_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "run_steps",
        sa.Column(
            "result_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_run_steps_assigned_agent_profile_id",
        "run_steps",
        ["assigned_agent_profile_id"],
    )
    op.create_index(
        "ix_run_steps_delegated_run_id",
        "run_steps",
        ["delegated_run_id"],
    )
    op.create_foreign_key(
        "fk_run_steps_delegated_run_id",
        "run_steps",
        "agent_runs",
        ["delegated_run_id"],
        ["id"],
    )
    op.execute(
        "UPDATE run_steps SET risk_level = 'R' || substring(risk_level from 2) "
        "WHERE risk_level IN ('L0','L1','L2','L3','L4')"
    )
    op.alter_column(
        "run_steps",
        "risk_level",
        existing_type=sa.String(length=20),
        server_default="R0",
        existing_nullable=True,
    )

    # Task 2 backfills and enforces NOT NULL after every writer uses the
    # concurrency-safe event allocator. Unique constraints remain safe while
    # legacy writers temporarily emit NULL.
    op.add_column("run_events", sa.Column("sequence", sa.Integer(), nullable=True))
    op.add_column(
        "run_events",
        sa.Column("event_key", sa.String(length=255), nullable=True),
    )
    op.create_unique_constraint(
        "uq_run_events_run_sequence", "run_events", ["run_id", "sequence"]
    )
    op.create_unique_constraint(
        "uq_run_events_run_event_key", "run_events", ["run_id", "event_key"]
    )

    op.add_column(
        "developer_jobs",
        sa.Column("agent_run_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "developer_jobs",
        sa.Column("run_step_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "developer_jobs",
        sa.Column("executor_kind", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "developer_jobs",
        sa.Column(
            "request_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "developer_jobs",
        sa.Column(
            "result_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "developer_jobs",
        sa.Column("cancel_requested_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_developer_jobs_agent_run_id", "developer_jobs", ["agent_run_id"]
    )
    op.create_index(
        "ix_developer_jobs_run_step_id", "developer_jobs", ["run_step_id"]
    )
    op.create_index(
        "ix_developer_jobs_executor_kind", "developer_jobs", ["executor_kind"]
    )
    op.create_foreign_key(
        "fk_developer_jobs_agent_run_id",
        "developer_jobs",
        "agent_runs",
        ["agent_run_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_developer_jobs_run_step_id",
        "developer_jobs",
        "run_steps",
        ["run_step_id"],
        ["id"],
    )

    op.add_column(
        "job_leases",
        sa.Column("lease_token_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "job_leases",
        sa.Column("renewed_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_job_leases_lease_token_hash",
        "job_leases",
        ["lease_token_hash"],
    )

    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM agent_runs AS child
            LEFT JOIN agent_runs AS parent ON parent.id = child.parent_run_id
            WHERE child.parent_run_id IS NOT NULL
              AND (parent.id IS NULL OR parent.workspace_id <> child.workspace_id)
          ) THEN
            RAISE EXCEPTION
              'Cannot add agent_runs parent FK: orphan or cross-workspace parent chain exists';
          END IF;
        END
        $$;
        """
    )
    op.create_foreign_key(
        "fk_agent_runs_parent_run_id",
        "agent_runs",
        "agent_runs",
        ["parent_run_id"],
        ["id"],
    )

    op.create_table(
        "delegation_jobs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column(
            "workspace_id",
            sa.BigInteger(),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "run_step_id",
            sa.BigInteger(),
            sa.ForeignKey("run_steps.id"),
            nullable=False,
        ),
        sa.Column(
            "root_agent_run_id",
            sa.BigInteger(),
            sa.ForeignKey("agent_runs.id"),
            nullable=False,
        ),
        sa.Column(
            "parent_agent_run_id",
            sa.BigInteger(),
            sa.ForeignKey("agent_runs.id"),
            nullable=False,
        ),
        sa.Column(
            "child_agent_run_id",
            sa.BigInteger(),
            sa.ForeignKey("agent_runs.id"),
            nullable=True,
        ),
        sa.Column("attempt_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("provider_kind", sa.String(length=50), nullable=False),
        sa.Column("provider_name", sa.String(length=100), nullable=False),
        sa.Column("profile_id", sa.String(length=100), nullable=False),
        sa.Column("runtime_name", sa.String(length=100), nullable=True),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="queued",
        ),
        sa.Column(
            "provider_handle_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column(
            "available_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column("next_poll_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("claimed_by", sa.String(length=100), nullable=True),
        sa.Column("lease_token", sa.String(length=64), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "reserved_cost_usd",
            sa.Numeric(12, 6),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "reserved_tool_calls", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "reserved_steps", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "result_jsonb",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.UniqueConstraint(
            "run_step_id",
            "attempt_no",
            name="uq_delegation_job_step_attempt",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "idempotency_key",
            name="uq_delegation_job_workspace_idempotency",
        ),
    )
    op.create_index(
        "ix_delegation_jobs_workspace_id",
        "delegation_jobs",
        ["workspace_id"],
    )
    op.create_index(
        "ix_delegation_jobs_run_step_id",
        "delegation_jobs",
        ["run_step_id"],
    )
    op.create_index(
        "ix_delegation_jobs_root_agent_run_id",
        "delegation_jobs",
        ["root_agent_run_id"],
    )
    op.create_index(
        "ix_delegation_jobs_parent_agent_run_id",
        "delegation_jobs",
        ["parent_agent_run_id"],
    )
    op.create_index(
        "ix_delegation_jobs_child_agent_run_id",
        "delegation_jobs",
        ["child_agent_run_id"],
    )
    op.create_index(
        "ix_delegation_jobs_provider_name",
        "delegation_jobs",
        ["provider_name"],
    )
    op.create_index(
        "ix_delegation_jobs_status",
        "delegation_jobs",
        ["status"],
    )
    op.create_index(
        "ix_delegation_jobs_available_at",
        "delegation_jobs",
        ["available_at"],
    )
    op.create_index(
        "ix_delegation_jobs_next_poll_at",
        "delegation_jobs",
        ["next_poll_at"],
    )
    op.create_index(
        "ix_delegation_jobs_lease_expires_at",
        "delegation_jobs",
        ["lease_expires_at"],
    )
    op.create_index(
        "ix_delegation_jobs_status_available",
        "delegation_jobs",
        ["status", "available_at"],
    )
    op.create_index(
        "ix_delegation_jobs_status_next_poll",
        "delegation_jobs",
        ["status", "next_poll_at"],
    )


def downgrade() -> None:
    op.drop_table("delegation_jobs")

    op.drop_constraint(
        "fk_agent_runs_parent_run_id", "agent_runs", type_="foreignkey"
    )

    op.drop_index("ix_job_leases_lease_token_hash", table_name="job_leases")
    op.drop_column("job_leases", "renewed_at")
    op.drop_column("job_leases", "lease_token_hash")

    op.drop_constraint(
        "fk_developer_jobs_run_step_id", "developer_jobs", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_developer_jobs_agent_run_id", "developer_jobs", type_="foreignkey"
    )
    op.drop_index("ix_developer_jobs_executor_kind", table_name="developer_jobs")
    op.drop_index("ix_developer_jobs_run_step_id", table_name="developer_jobs")
    op.drop_index("ix_developer_jobs_agent_run_id", table_name="developer_jobs")
    op.drop_column("developer_jobs", "cancel_requested_at")
    op.drop_column("developer_jobs", "result_jsonb")
    op.drop_column("developer_jobs", "request_jsonb")
    op.drop_column("developer_jobs", "executor_kind")
    op.drop_column("developer_jobs", "run_step_id")
    op.drop_column("developer_jobs", "agent_run_id")

    op.drop_constraint(
        "uq_run_events_run_event_key", "run_events", type_="unique"
    )
    op.drop_constraint(
        "uq_run_events_run_sequence", "run_events", type_="unique"
    )
    op.drop_column("run_events", "event_key")
    op.drop_column("run_events", "sequence")

    op.drop_constraint(
        "fk_run_steps_delegated_run_id", "run_steps", type_="foreignkey"
    )
    op.drop_index("ix_run_steps_delegated_run_id", table_name="run_steps")
    op.drop_index(
        "ix_run_steps_assigned_agent_profile_id", table_name="run_steps"
    )
    op.drop_column("run_steps", "result_jsonb")
    op.drop_column("run_steps", "delegated_run_id")
    op.drop_column("run_steps", "assigned_runtime")
    op.drop_column("run_steps", "assigned_agent_profile_id")
    op.execute(
        "UPDATE run_steps SET risk_level = 'L' || substring(risk_level from 2) "
        "WHERE risk_level IN ('R0','R1','R2','R3','R4')"
    )
    op.alter_column(
        "run_steps",
        "risk_level",
        existing_type=sa.String(length=20),
        server_default=None,
        existing_nullable=True,
    )
