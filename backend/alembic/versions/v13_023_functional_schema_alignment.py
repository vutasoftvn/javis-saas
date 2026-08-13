"""align persistent schema with functional metadata

Revision ID: v13_023_schema_align
Revises: v13_022_chat_tool_access

The previous stage-orchestration migration intentionally created the tables and
their composite lookup indexes first.  The ORM subsequently gained the
single-column tenant and relation indexes used by scoped APIs.  This migration
adds those non-destructive indexes and makes metric metadata persistable.

The realtime migrations created both a unique constraint and a unique index for
the same column.  PostgreSQL only needs the named unique index, so remove the
redundant constraints while retaining uniqueness throughout the upgrade.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "v13_023_schema_align"
down_revision = "v13_022_chat_tool_access"
branch_labels = None
depends_on = None


_INDEXES = (
    ("ix_capability_definitions_brain_id", "capability_definitions", ["brain_id"]),
    ("ix_capability_definitions_capability_key", "capability_definitions", ["capability_key"]),
    ("ix_capability_definitions_workspace_id", "capability_definitions", ["workspace_id"]),
    ("ix_mvp_stages_brain_id", "mvp_stages", ["brain_id"]),
    ("ix_mvp_stages_project_id", "mvp_stages", ["project_id"]),
    ("ix_mvp_stages_workspace_id", "mvp_stages", ["workspace_id"]),
    ("ix_projects_active_stage_id", "projects", ["active_stage_id"]),
    ("ix_stage_assignments_assessment_id", "stage_assignments", ["assessment_id"]),
    ("ix_stage_assignments_brain_id", "stage_assignments", ["brain_id"]),
    ("ix_stage_assignments_mvp_stage_id", "stage_assignments", ["mvp_stage_id"]),
    ("ix_stage_assignments_workspace_id", "stage_assignments", ["workspace_id"]),
    ("ix_stage_revisions_brain_id", "stage_revisions", ["brain_id"]),
    ("ix_stage_revisions_mvp_stage_id", "stage_revisions", ["mvp_stage_id"]),
    ("ix_stage_revisions_workspace_id", "stage_revisions", ["workspace_id"]),
    ("ix_stage_service_assessments_brain_id", "stage_service_assessments", ["brain_id"]),
    ("ix_stage_service_assessments_capability_id", "stage_service_assessments", ["capability_id"]),
    ("ix_stage_service_assessments_mvp_stage_id", "stage_service_assessments", ["mvp_stage_id"]),
    ("ix_stage_service_assessments_workspace_id", "stage_service_assessments", ["workspace_id"]),
    ("ix_strategy_audit_events_mvp_stage_id", "strategy_audit_events", ["mvp_stage_id"]),
    ("ix_strategy_audit_events_project_id", "strategy_audit_events", ["project_id"]),
    ("ix_strategy_audit_events_workspace_id", "strategy_audit_events", ["workspace_id"]),
    ("ix_workspace_agents_brain_id", "workspace_agents", ["brain_id"]),
    ("ix_workspace_agents_workspace_id", "workspace_agents", ["workspace_id"]),
    ("ix_workspace_template_versions_template_id", "workspace_template_versions", ["template_id"]),
    ("ix_workspace_template_versions_workspace_id", "workspace_template_versions", ["workspace_id"]),
    ("ix_workspace_templates_brain_id", "workspace_templates", ["brain_id"]),
    ("ix_workspace_templates_workspace_id", "workspace_templates", ["workspace_id"]),
)


def upgrade() -> None:
    op.add_column("metrics", sa.Column("metric_type", sa.String(50), nullable=True))
    op.add_column("metrics", sa.Column("evidence_refs", postgresql.JSONB(), nullable=True))

    for name, table_name, columns in _INDEXES:
        op.create_index(name, table_name, columns)

    op.drop_constraint("realtime_sessions_room_name_key", "realtime_sessions", type_="unique")
    op.drop_constraint("voice_usage_records_session_id_key", "voice_usage_records", type_="unique")


def downgrade() -> None:
    # Recreate the redundant constraints only to make downgrade structurally
    # reversible; the named unique indexes continue enforcing the invariant.
    op.create_unique_constraint("voice_usage_records_session_id_key", "voice_usage_records", ["session_id"])
    op.create_unique_constraint("realtime_sessions_room_name_key", "realtime_sessions", ["room_name"])

    for name, table_name, _columns in reversed(_INDEXES):
        op.drop_index(name, table_name=table_name)

    op.drop_column("metrics", "evidence_refs")
    op.drop_column("metrics", "metric_type")
