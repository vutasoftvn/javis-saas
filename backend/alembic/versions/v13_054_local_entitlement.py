"""Add local_entitlement_snapshots table for persisted offline entitlement caching (G2 P0.3).

Before this table existed, EntitlementManager only cached the current signed
entitlement snapshot in a process-memory dict — every process restart lost
any paid entitlement and silently fell back to the Free tier default, even
with a still-valid license cached moments earlier. Local now persists the
current (and historical) snapshot(s) so a restart can reload and re-verify
before falling back to anything.

Revision ID: v13_054_local_entitlement
Revises: v13_053_hybrid_platform_outbox
Create Date: 2026-08-19 18:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "v13_054_local_entitlement"
down_revision: Union[str, Sequence[str], None] = "v13_053_hybrid_platform_outbox"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "local_entitlement_snapshots" not in tables:
        op.create_table(
            "local_entitlement_snapshots",
            sa.Column("id", sa.BigInteger(), nullable=False, primary_key=True),
            sa.Column("company_id", sa.String(length=36), nullable=False),
            sa.Column("plan", sa.String(length=50), nullable=False),
            sa.Column("payload_jsonb", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
            sa.Column("signature", sa.Text(), nullable=False),
            sa.Column("signature_alg", sa.String(length=30), nullable=False, server_default="HMAC_SHA256"),
            sa.Column("key_id", sa.String(length=50), nullable=True),
            sa.Column("issued_at", sa.DateTime(), nullable=False),
            sa.Column("valid_until", sa.DateTime(), nullable=False),
            sa.Column("grace_period_days", sa.Integer(), nullable=False, server_default="7"),
            sa.Column("received_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("verified_at", sa.DateTime(), nullable=True),
            sa.Column("verification_status", sa.String(length=30), nullable=False, server_default="UNVERIFIED"),
            sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        op.create_index(
            "ix_local_entitlement_snapshots_company_current",
            "local_entitlement_snapshots",
            ["company_id", "is_current"],
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "local_entitlement_snapshots" in tables:
        op.drop_table("local_entitlement_snapshots")
