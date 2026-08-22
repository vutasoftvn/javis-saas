"""project stage orchestration

Revision ID: v13_021_project_stage_orchestration
Revises: v13_020_widen_snowflake_ids
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "v13_021_stage_orchestration"
down_revision = "v13_020_widen_snowflake_ids"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("active_stage_id", sa.BigInteger(), nullable=True))
    # mvp_stage_id, not stage_id: weekly_plans/milestones/gate_decisions already use
    # stage_id as a foreign key to the unrelated cycle_stages table.
    op.add_column("okr_cycles", sa.Column("mvp_stage_id", sa.BigInteger(), nullable=True))
    op.add_column("twelve_week_cycles", sa.Column("mvp_stage_id", sa.BigInteger(), nullable=True))
    op.add_column("gate_decisions", sa.Column("mvp_stage_id", sa.BigInteger(), nullable=True))

    op.create_table(
        "mvp_stages",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("brain_id", sa.BigInteger(), sa.ForeignKey("brains.id"), nullable=False),
        sa.Column("project_id", sa.BigInteger(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("scope_jsonb", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("exit_criteria_jsonb", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(24), nullable=False, server_default="DRAFT"),
        sa.Column("template_snapshot_jsonb", postgresql.JSONB(), nullable=True),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("project_id", "sequence_no", name="uq_mvp_stage_project_sequence"),
    )
    op.create_index("ix_mvp_stage_workspace_project_status", "mvp_stages", ["workspace_id", "project_id", "status"])
    op.create_index("uq_mvp_stage_one_active", "mvp_stages", ["project_id"], unique=True, postgresql_where=sa.text("status = 'ACTIVE'"))

    # Now that mvp_stages exists, wire up the deferred foreign keys.
    op.create_foreign_key("fk_project_active_stage", "projects", "mvp_stages", ["active_stage_id"], ["id"])
    op.create_foreign_key("fk_okr_cycle_mvp_stage", "okr_cycles", "mvp_stages", ["mvp_stage_id"], ["id"])
    op.create_foreign_key("fk_twelve_week_cycle_mvp_stage", "twelve_week_cycles", "mvp_stages", ["mvp_stage_id"], ["id"])
    op.create_foreign_key("fk_gate_decision_mvp_stage", "gate_decisions", "mvp_stages", ["mvp_stage_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_okr_cycle_mvp_stage_id", "okr_cycles", ["mvp_stage_id"])
    op.create_index("ix_twelve_week_cycle_mvp_stage_id", "twelve_week_cycles", ["mvp_stage_id"])
    op.create_index("ix_gate_decision_mvp_stage_id", "gate_decisions", ["mvp_stage_id"])

    op.create_table(
        "workspace_templates",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("brain_id", sa.BigInteger(), sa.ForeignKey("brains.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source_key", sa.String(100), nullable=False),
        sa.Column("active_version_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("workspace_id", "source_key", name="uq_workspace_template_source"),
    )
    op.create_table(
        "workspace_template_versions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("template_id", sa.BigInteger(), sa.ForeignKey("workspace_templates.id"), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("config_jsonb", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("source_seed_key", sa.String(100)),
        sa.Column("playbook_document_id", sa.BigInteger(), sa.ForeignKey("vault_documents.id"), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("template_id", "version_no", name="uq_workspace_template_version"),
    )
    op.create_table(
        "capability_definitions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("brain_id", sa.BigInteger(), sa.ForeignKey("brains.id"), nullable=False),
        sa.Column("capability_key", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("expected_deliverables_jsonb", postgresql.JSONB(), nullable=True),
        sa.Column("evidence_requirements_jsonb", postgresql.JSONB(), nullable=True),
        sa.Column("supported_execution_modes_jsonb", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("risk_level", sa.String(24), nullable=False, server_default="LOW"),
        sa.Column("professional_review_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "workspace_agents",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("brain_id", sa.BigInteger(), sa.ForeignKey("brains.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("capability_keys_jsonb", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "stage_revisions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("brain_id", sa.BigInteger(), sa.ForeignKey("brains.id"), nullable=False),
        sa.Column("mvp_stage_id", sa.BigInteger(), sa.ForeignKey("mvp_stages.id"), nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("change_type", sa.String(24), nullable=False, server_default="MINOR"),
        sa.Column("before_snapshot_jsonb", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("after_snapshot_jsonb", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("impact_preview_jsonb", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(24), nullable=False, server_default="PREVIEWED"),
        sa.Column("created_by", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("applied_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("mvp_stage_id", "revision_no", name="uq_stage_revision_stage_no"),
    )
    op.create_index("ix_stage_revision_workspace_stage", "stage_revisions", ["workspace_id", "mvp_stage_id"])
    op.create_table(
        "stage_service_assessments",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("brain_id", sa.BigInteger(), sa.ForeignKey("brains.id"), nullable=False),
        sa.Column("mvp_stage_id", sa.BigInteger(), sa.ForeignKey("mvp_stages.id"), nullable=False),
        sa.Column("capability_id", sa.BigInteger(), sa.ForeignKey("capability_definitions.id"), nullable=False),
        sa.Column("disposition", sa.String(24), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.String(24), nullable=False, server_default="LOW"),
        sa.Column("expected_output", sa.Text(), nullable=True),
        sa.Column("execution_mode", sa.String(24), nullable=False, server_default="MANUAL"),
        sa.Column("professional_review_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(24), nullable=False, server_default="DRAFT"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_stage_assessment_workspace_stage", "stage_service_assessments", ["workspace_id", "mvp_stage_id"])
    op.create_table(
        "stage_assignments",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("brain_id", sa.BigInteger(), sa.ForeignKey("brains.id"), nullable=False),
        sa.Column("mvp_stage_id", sa.BigInteger(), sa.ForeignKey("mvp_stages.id"), nullable=False),
        sa.Column("assessment_id", sa.BigInteger(), sa.ForeignKey("stage_service_assessments.id"), nullable=False),
        sa.Column("agent_id", sa.BigInteger(), sa.ForeignKey("workspace_agents.id"), nullable=True),
        sa.Column("weekly_commitment_id", sa.BigInteger(), sa.ForeignKey("weekly_commitments.id"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("execution_mode", sa.String(24), nullable=False, server_default="MANUAL"),
        sa.Column("status", sa.String(24), nullable=False, server_default="DRAFT"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_stage_assignment_workspace_stage", "stage_assignments", ["workspace_id", "mvp_stage_id"])
    op.create_table(
        "strategy_audit_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("project_id", sa.BigInteger(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("mvp_stage_id", sa.BigInteger(), sa.ForeignKey("mvp_stages.id"), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("actor_type", sa.String(24), nullable=False),
        sa.Column("actor_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("payload_jsonb", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_strategy_audit_workspace_project", "strategy_audit_events", ["workspace_id", "project_id"])


def downgrade() -> None:
    op.drop_table("strategy_audit_events")
    op.drop_table("stage_assignments")
    op.drop_table("stage_service_assessments")
    op.drop_table("stage_revisions")
    op.drop_table("workspace_agents")
    op.drop_table("capability_definitions")
    op.drop_table("workspace_template_versions")
    op.drop_table("workspace_templates")

    op.drop_constraint("fk_gate_decision_mvp_stage", "gate_decisions", type_="foreignkey")
    op.drop_constraint("fk_twelve_week_cycle_mvp_stage", "twelve_week_cycles", type_="foreignkey")
    op.drop_constraint("fk_okr_cycle_mvp_stage", "okr_cycles", type_="foreignkey")
    op.drop_constraint("fk_project_active_stage", "projects", type_="foreignkey")

    op.drop_index("uq_mvp_stage_one_active", table_name="mvp_stages")
    op.drop_index("ix_mvp_stage_workspace_project_status", table_name="mvp_stages")
    op.drop_table("mvp_stages")

    op.drop_column("gate_decisions", "mvp_stage_id")
    op.drop_column("twelve_week_cycles", "mvp_stage_id")
    op.drop_column("okr_cycles", "mvp_stage_id")
    op.drop_column("projects", "active_stage_id")
    op.drop_column("projects", "description")
