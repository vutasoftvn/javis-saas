"""Create report_automation_flows and report_delivery_history tables.

Revision ID: v13_038_report_automation_tables
Revises: v13_037_desktop_local_transport
Create Date: 2026-08-15 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "v13_038_report_automation_tables"
down_revision: Union[str, Sequence[str], None] = "v13_037_desktop_local_transport"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "report_automation_flows",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("trigger_type", sa.String(length=50), nullable=False, server_default="cron"),
        sa.Column("schedule_cron", sa.String(length=100), nullable=True),
        sa.Column("timezone", sa.String(length=50), nullable=False, server_default="Asia/Ho_Chi_Minh"),
        sa.Column("scope", sa.String(length=50), nullable=False, server_default="cycle"),
        sa.Column("channels", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "report_delivery_history",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("flow_id", sa.BigInteger(), sa.ForeignKey("report_automation_flows.id"), nullable=False, index=True),
        sa.Column("workspace_id", sa.BigInteger(), sa.ForeignKey("workspaces.id"), nullable=False, index=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="delivered"),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("payload_snapshot_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("report_delivery_history")
    op.drop_table("report_automation_flows")
