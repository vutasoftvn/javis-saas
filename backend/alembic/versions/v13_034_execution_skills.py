"""COSA OpenSandbox Custom & Third-Party Skill Runtime Feature Flag."""

from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa

from app.core.snowflake import generate_snowflake_id


revision = "v13_034_execution_skills"
down_revision = "v13_033_execution_coding"
branch_labels = None
depends_on = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def upgrade() -> None:
    now = utc_now()
    feature_flags = sa.table(
        "feature_flags",
        sa.column("id", sa.BigInteger),
        sa.column("workspace_id", sa.BigInteger),
        sa.column("key", sa.String),
        sa.column("enabled", sa.Boolean),
        sa.column("description", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    op.bulk_insert(
        feature_flags,
        [
            {
                "id": generate_snowflake_id(),
                "workspace_id": None,
                "key": "agent_execution_skills",
                "enabled": False,
                "description": "Enables isolated third-party skill execution in ephemeral sandboxes.",
                "created_at": now,
                "updated_at": now,
            },
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM feature_flags WHERE workspace_id IS NULL AND key = 'agent_execution_skills'"
        )
    )
