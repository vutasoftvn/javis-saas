"""seed desktop_local_transport feature flag default

Revision ID: v13_037_desktop_local_transport
Revises: v13_036_agentic_control_plane
Create Date: 2026-08-15 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from core.snowflake import generate_snowflake_id


revision: str = "v13_037_desktop_local_transport"
down_revision: Union[str, Sequence[str], None] = "v13_036_agentic_control_plane"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    exists = bind.execute(
        sa.text("SELECT 1 FROM feature_flags WHERE workspace_id IS NULL AND key = 'desktop_local_transport'")
    ).first()
    if exists is None:
        bind.execute(
            sa.text(
                "INSERT INTO feature_flags "
                "(id, workspace_id, key, enabled, description, created_at, updated_at) "
                "VALUES (:id, NULL, 'desktop_local_transport', true, 'Enable local LiveKit transport when available', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"id": generate_snowflake_id()},
        )
    else:
        bind.execute(
            sa.text("UPDATE feature_flags SET enabled = true, updated_at = CURRENT_TIMESTAMP WHERE workspace_id IS NULL AND key = 'desktop_local_transport'")
        )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM feature_flags WHERE workspace_id IS NULL AND key = 'desktop_local_transport'"))
