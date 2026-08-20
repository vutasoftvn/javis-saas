"""Skill Registry Versioning (G1 §61-62 / G3 Phase 1C): add `is_system` to
distinguish platform-shipped skills from workspace-authored ones. No new
status values require a migration - `status` was already an unconstrained
String(30) column, so `experimental`/`archived`/`blocked` are purely an
application-level addition to the set of strings written there.

Revision ID: v13_056_skill_registry_v
Revises: v13_055_canon_capability
Create Date: 2026-08-20 10:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "v13_056_skill_registry_v"
down_revision: Union[str, Sequence[str], None] = "v13_055_canon_capability"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = {c["name"] for c in inspector.get_columns("global_skill_registry")}

    if "is_system" not in existing_columns:
        with op.batch_alter_table("global_skill_registry") as batch_op:
            batch_op.add_column(
                sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.false())
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = {c["name"] for c in inspector.get_columns("global_skill_registry")}

    if "is_system" in existing_columns:
        with op.batch_alter_table("global_skill_registry") as batch_op:
            batch_op.drop_column("is_system")
