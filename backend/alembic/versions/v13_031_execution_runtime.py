"""COSA OpenSandbox Execution Runtime schema, presets, and feature flags."""

import json
from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from app.core.snowflake import generate_snowflake_id


revision = "v13_031_execution_runtime"
down_revision = "v13_030_worker_heartbeat"
branch_labels = None
depends_on = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def upgrade() -> None:
    # 1. Create sandbox_policies table
    op.create_table(
        "sandbox_policies",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), index=True, nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False, index=True),
        sa.Column("agent_type", sa.String(length=50), server_default="generic", nullable=False),
        sa.Column("network_policy_jsonb", JSONB(), nullable=True),
        sa.Column("filesystem_policy_jsonb", JSONB(), nullable=True),
        sa.Column("command_policy_jsonb", JSONB(), nullable=True),
        sa.Column("credential_policy_jsonb", JSONB(), nullable=True),
        sa.Column("resource_limit_jsonb", JSONB(), nullable=True),
        sa.Column("timeout_seconds", sa.Integer(), server_default="300", nullable=False),
        sa.Column("approval_policy", sa.String(length=50), server_default="auto", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 2. Create execution_jobs table
    op.create_table(
        "execution_jobs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), index=True, nullable=False),
        sa.Column("brain_id", sa.BigInteger(), nullable=True, index=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), index=True, nullable=False),
        sa.Column("agent_run_id", sa.BigInteger(), sa.ForeignKey("agent_runs.id"), nullable=True, index=True),
        sa.Column("agent_key", sa.String(length=100), nullable=False, index=True),
        sa.Column("provider", sa.String(length=50), server_default="mock", nullable=False),
        sa.Column("sandbox_id", sa.String(length=255), nullable=True),
        sa.Column("policy_id", sa.BigInteger(), sa.ForeignKey("sandbox_policies.id"), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="queued", nullable=False, index=True),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("destroyed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_jsonb", JSONB(), nullable=True),
        sa.UniqueConstraint("workspace_id", "idempotency_key", name="uq_execution_jobs_ws_idempotency"),
    )

    # 3. Create execution_steps table
    op.create_table(
        "execution_steps",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("job_id", sa.BigInteger(), sa.ForeignKey("execution_jobs.id"), index=True, nullable=False),
        sa.Column("sequence", sa.Integer(), server_default="1", nullable=False),
        sa.Column("step_type", sa.String(length=50), server_default="command", nullable=False),
        sa.Column("command", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="completed", nullable=False),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stdout_excerpt", sa.Text(), nullable=True),
        sa.Column("stderr_excerpt", sa.Text(), nullable=True),
    )

    # 4. Add execution_job_id to artifacts table
    op.add_column(
        "artifacts",
        sa.Column("execution_job_id", sa.BigInteger(), sa.ForeignKey("execution_jobs.id"), nullable=True),
    )
    op.create_index("ix_artifacts_execution_job_id", "artifacts", ["execution_job_id"])

    # 5. Seed 5 global preset policies (§48)
    presets = [
        {
            "name": "safe_analysis",
            "agent_type": "analyst",
            "network_policy_jsonb": {"default": "deny", "allow": []},
            "filesystem_policy_jsonb": {"read": ["/input", "/workspace"], "write": ["/output", "/tmp", "/workspace"]},
            "command_policy_jsonb": {"allow": ["python", "python3", "pip"]},
            "credential_policy_jsonb": {"allow": []},
            "resource_limit_jsonb": {"image": "python:3.11-slim", "cpu": 1.0, "memory_mb": 1024, "disk_mb": 1024, "max_artifact_bytes": 52428800, "max_artifact_count": 20},
            "timeout_seconds": 300,
            "approval_policy": "auto",
        },
        {
            "name": "research",
            "agent_type": "researcher",
            "network_policy_jsonb": {"default": "deny", "allow": ["api.openai.com", "api.deepseek.com", "openrouter.ai"]},
            "filesystem_policy_jsonb": {"read": ["/input", "/workspace"], "write": ["/output", "/tmp", "/workspace"]},
            "command_policy_jsonb": {"allow": ["python", "python3", "curl"]},
            "credential_policy_jsonb": {"allow": []},
            "resource_limit_jsonb": {"image": "python:3.11-slim", "cpu": 1.0, "memory_mb": 1024, "disk_mb": 1024, "max_artifact_bytes": 52428800, "max_artifact_count": 30},
            "timeout_seconds": 300,
            "approval_policy": "auto",
        },
        {
            "name": "marketing",
            "agent_type": "marketer",
            "network_policy_jsonb": {"default": "deny", "allow": []},
            "filesystem_policy_jsonb": {"read": ["/input", "/workspace"], "write": ["/output", "/tmp", "/workspace"]},
            "command_policy_jsonb": {"allow": ["python", "python3"]},
            "credential_policy_jsonb": {"allow": []},
            "resource_limit_jsonb": {"image": "python:3.11-slim", "cpu": 1.0, "memory_mb": 1024, "disk_mb": 1024, "max_artifact_bytes": 52428800, "max_artifact_count": 20},
            "timeout_seconds": 300,
            "approval_policy": "auto",
        },
        {
            "name": "finance",
            "agent_type": "finance",
            "network_policy_jsonb": {"default": "deny", "allow": []},
            "filesystem_policy_jsonb": {"read": ["/input", "/workspace"], "write": ["/output", "/tmp", "/workspace"]},
            "command_policy_jsonb": {"allow": ["python", "python3"]},
            "credential_policy_jsonb": {"allow": []},
            "resource_limit_jsonb": {"image": "python:3.11-slim", "cpu": 1.0, "memory_mb": 1024, "disk_mb": 1024, "max_artifact_bytes": 52428800, "max_artifact_count": 20},
            "timeout_seconds": 300,
            "approval_policy": "auto",
        },
        {
            "name": "coding",
            "agent_type": "developer",
            "network_policy_jsonb": {"default": "deny", "allow": ["github.com", "pypi.org", "files.pythonhosted.org"]},
            "filesystem_policy_jsonb": {"read": ["/input", "/workspace"], "write": ["/output", "/tmp", "/workspace"]},
            "command_policy_jsonb": {"allow": ["python", "python3", "pytest", "git", "pip"]},
            "credential_policy_jsonb": {"allow": []},
            "resource_limit_jsonb": {"image": "python:3.11-slim", "cpu": 2.0, "memory_mb": 2048, "disk_mb": 2048, "max_artifact_bytes": 104857600, "max_artifact_count": 50},
            "timeout_seconds": 600,
            "approval_policy": "auto",
        },
    ]

    bind = op.get_bind()
    now = utc_now()
    for p in presets:
        bind.execute(
            sa.text(
                "INSERT INTO sandbox_policies "
                "(id, workspace_id, name, agent_type, network_policy_jsonb, filesystem_policy_jsonb, "
                "command_policy_jsonb, credential_policy_jsonb, resource_limit_jsonb, timeout_seconds, "
                "approval_policy, created_at, updated_at) "
                "VALUES (:id, NULL, :name, :agent_type, :net, :fs, :cmd, :cred, :res, :timeout, :approval, :now, :now)"
            ),
            {
                "id": generate_snowflake_id(),
                "name": p["name"],
                "agent_type": p["agent_type"],
                "net": json.dumps(p["network_policy_jsonb"]),
                "fs": json.dumps(p["filesystem_policy_jsonb"]),
                "cmd": json.dumps(p["command_policy_jsonb"]),
                "cred": json.dumps(p["credential_policy_jsonb"]),
                "res": json.dumps(p["resource_limit_jsonb"]),
                "timeout": p["timeout_seconds"],
                "approval": p["approval_policy"],
                "now": now,
            },
        )

    # 6. Seed Feature Flags
    flags = [
        ("agent_execution", False, "Enable AI agent execution runtime and sandbox jobs"),
        ("agent_execution_sandbox", False, "Enable OpenSandbox execution provider in worker"),
    ]
    for key, enabled, desc in flags:
        bind.execute(
            sa.text(
                "INSERT INTO feature_flags (id, workspace_id, key, enabled, description, created_at, updated_at) "
                "VALUES (:id, NULL, :key, :enabled, :desc, :now, :now) "
                "ON CONFLICT DO NOTHING"
            ),
            {
                "id": generate_snowflake_id(),
                "key": key,
                "enabled": enabled,
                "desc": desc,
                "now": now,
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM feature_flags WHERE key IN ('agent_execution', 'agent_execution_sandbox')"))
    op.drop_index("ix_artifacts_execution_job_id", table_name="artifacts")
    op.drop_column("artifacts", "execution_job_id")
    op.drop_table("execution_steps")
    op.drop_table("execution_jobs")
    op.drop_table("sandbox_policies")
