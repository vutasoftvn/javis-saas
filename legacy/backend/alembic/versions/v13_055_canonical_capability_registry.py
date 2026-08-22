"""Extend capability_definitions into the canonical Capability Registry (G1 §4 / G3 Phase 1B).

Widens workspace_id/brain_id to nullable (platform-global capability rows
from the runtime registry / business packs have neither), and adds the
columns needed to also cover what `workforce/agents/capabilities/registry.py`
(runtime authorization) and `business/packs/schemas.py` (business-pack
content catalog) used to hold in two separate, disconnected places.

No data is deleted or renamed — this is additive plus a nullability
relaxation, safe to run before the seed-migration script that populates the
new rows (a separate, non-schema step, per G2 §25 "data backfill riêng").

Revision ID: v13_055_canonical_capability_registry
Revises: v13_054_local_entitlement
Create Date: 2026-08-19 19:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "v13_055_canon_capability"
down_revision: Union[str, Sequence[str], None] = "v13_054_local_entitlement"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_NEW_COLUMNS = (
    ("description", sa.Text(), True, None),
    ("domain", sa.String(length=50), False, "CROSS_DOMAIN"),
    ("owner_agent_key", sa.String(length=100), True, None),
    ("status", sa.String(length=20), False, "ACTIVE"),
    ("source", sa.String(length=30), False, "founder_os_seed"),
    ("source_pack_key", sa.String(length=100), True, None),
    ("requires_approval", sa.Boolean(), False, "false"),
    ("content_jsonb", postgresql.JSONB(astext_type=sa.Text()), True, None),
    ("metadata_jsonb", postgresql.JSONB(astext_type=sa.Text()), True, None),
    ("updated_at", sa.DateTime(), True, None),
)


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = {c["name"] for c in inspector.get_columns("capability_definitions")}

    with op.batch_alter_table("capability_definitions") as batch_op:
        # Platform-global rows (runtime registry / business packs) have no
        # single owning workspace/brain.
        batch_op.alter_column("workspace_id", existing_type=sa.BigInteger(), nullable=True)
        batch_op.alter_column("brain_id", existing_type=sa.BigInteger(), nullable=True)
        batch_op.alter_column("capability_key", existing_type=sa.String(length=150), type_=sa.String(length=150))

        for name, col_type, nullable, server_default in _NEW_COLUMNS:
            if name in existing_columns:
                continue
            batch_op.add_column(
                sa.Column(name, col_type, nullable=nullable, server_default=server_default)
            )

    op.execute("UPDATE capability_definitions SET updated_at = created_at WHERE updated_at IS NULL")

    if "ix_capability_definitions_domain" not in [ix["name"] for ix in inspector.get_indexes("capability_definitions")]:
        op.create_index("ix_capability_definitions_domain", "capability_definitions", ["domain"])
    if "ix_capability_definitions_owner_agent_key" not in [ix["name"] for ix in inspector.get_indexes("capability_definitions")]:
        op.create_index("ix_capability_definitions_owner_agent_key", "capability_definitions", ["owner_agent_key"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_indexes = {ix["name"] for ix in inspector.get_indexes("capability_definitions")}

    if "ix_capability_definitions_owner_agent_key" in existing_indexes:
        op.drop_index("ix_capability_definitions_owner_agent_key", table_name="capability_definitions")
    if "ix_capability_definitions_domain" in existing_indexes:
        op.drop_index("ix_capability_definitions_domain", table_name="capability_definitions")

    with op.batch_alter_table("capability_definitions") as batch_op:
        for name, _col_type, _nullable, _default in reversed(_NEW_COLUMNS):
            batch_op.drop_column(name)
        batch_op.alter_column("capability_key", existing_type=sa.String(length=150), type_=sa.String(length=100))
        # Not reverting workspace_id/brain_id back to NOT NULL — any
        # platform-global row inserted after upgrade() would violate that
        # constraint, and this migration doesn't know which rows to delete.
