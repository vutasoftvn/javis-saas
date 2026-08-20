"""seed Phase C rollout flags disabled by default

Revision ID: c6e01c5a0006
Revises: c5e01c5a0005
Create Date: 2026-08-20 21:15:00.000000
"""

from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.snowflake import generate_snowflake_id


revision: str = "c6e01c5a0006"
down_revision: Union[str, Sequence[str], None] = "c5e01c5a0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DESCRIPTION = "Phase C durable delegation rollout gate (disabled by default)."
_FLAGS = (
    "agent_delegation",
    "agent_delegation_chief_of_staff",
    "agent_delegation_device_executors",
    "agent_delegation_n8n",
    "agent_delegation_sandbox",
)


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(timezone.utc)
    for key in _FLAGS:
        exists = bind.execute(
            sa.text(
                "SELECT 1 FROM feature_flags "
                "WHERE workspace_id IS NULL AND key = :key"
            ),
            {"key": key},
        ).scalar()
        if exists is None:
            bind.execute(
                sa.text(
                    "INSERT INTO feature_flags "
                    "(id, workspace_id, key, enabled, description, created_at, updated_at) "
                    "VALUES (:id, NULL, :key, false, :description, :now, :now)"
                ),
                {
                    "id": generate_snowflake_id(),
                    "key": key,
                    "description": _DESCRIPTION,
                    "now": now,
                },
            )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM feature_flags "
            "WHERE workspace_id IS NULL AND description = :description"
        ).bindparams(description=_DESCRIPTION)
    )
