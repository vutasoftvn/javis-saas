"""Add COSA Hybrid Data Architecture Platform Outbox and Inbox tables (Phase 2).

Creates platform_outbox for transactional event sync to Supabase Central.
Creates platform_inbox for receiving and processing events from Supabase Central.

Revision ID: v13_053_hybrid_platform_outbox
Revises: v13_052_hybrid_platform_baseline
Create Date: 2026-08-19 08:34:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "v13_053_hybrid_platform_outbox"
down_revision: Union[str, Sequence[str], None] = "v13_052_hybrid_platform_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create platform_outbox
    if "platform_outbox" not in tables:
        op.create_table(
            "platform_outbox",
            sa.Column("id", sa.BigInteger(), nullable=False, primary_key=True),
            sa.Column("event_id", sa.String(length=36), nullable=False),
            sa.Column("event_type", sa.String(length=100), nullable=False),
            sa.Column("aggregate_type", sa.String(length=50), nullable=False),
            sa.Column("aggregate_id", sa.String(length=36), nullable=False),
            sa.Column("company_id", sa.String(length=36), nullable=False),
            sa.Column("classification", sa.String(length=50), nullable=False, server_default="PLATFORM_REQUIRED"),
            sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_retries", sa.Integer(), nullable=False, server_default="10"),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("next_retry_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("sent_at", sa.DateTime(), nullable=True),
            sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_platform_outbox_event_id", "platform_outbox", ["event_id"], unique=True)
        op.create_index("ix_platform_outbox_status", "platform_outbox", ["status"])
        op.create_index("ix_platform_outbox_status_next_retry", "platform_outbox", ["status", "next_retry_at"])
        op.create_index("ix_platform_outbox_company_status", "platform_outbox", ["company_id", "status"])

    # 2. Create platform_inbox
    if "platform_inbox" not in tables:
        op.create_table(
            "platform_inbox",
            sa.Column("id", sa.BigInteger(), nullable=False, primary_key=True),
            sa.Column("event_id", sa.String(length=36), nullable=False),
            sa.Column("event_type", sa.String(length=100), nullable=False),
            sa.Column("company_id", sa.String(length=36), nullable=False),
            sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("received_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("processed_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_platform_inbox_event_id", "platform_inbox", ["event_id"], unique=True)
        op.create_index("ix_platform_inbox_status", "platform_inbox", ["status"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "platform_inbox" in tables:
        op.drop_table("platform_inbox")

    if "platform_outbox" in tables:
        op.drop_table("platform_outbox")
