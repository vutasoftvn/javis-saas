"""seed automation_definitions catalog (additive data)

Revision ID: v13_028_automation_catalog_seed
Revises: v13_027_agent_governance
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

from app.core.snowflake import generate_snowflake_id

revision: str = "v13_028_automation_catalog_seed"
down_revision: Union[str, Sequence[str], None] = "v13_027_agent_governance"
branch_labels = None
depends_on = None

_SEED_ROWS = [
    {
        "automation_key": "system.telegram_notification",
        "name": "Telegram Notification",
        "domain": "system",
        "risk_level": "low",
        "approval_mode": "none",
    },
    {
        "automation_key": "sales.followup_email",
        "name": "Sales Follow-up Email",
        "domain": "sales",
        "risk_level": "medium",
        "approval_mode": "required",
    },
]


def upgrade() -> None:
    conn = op.get_bind()
    for row in _SEED_ROWS:
        conn.execute(
            sa.text(
                "INSERT INTO automation_definitions "
                "(id, automation_key, name, domain, provider, enabled, risk_level, approval_mode) "
                "VALUES (:id, :automation_key, :name, :domain, 'n8n', true, :risk_level, :approval_mode) "
                "ON CONFLICT (automation_key) DO NOTHING"
            ),
            {"id": generate_snowflake_id(), **row},
        )


def downgrade() -> None:
    conn = op.get_bind()
    keys = [row["automation_key"] for row in _SEED_ROWS]
    conn.execute(
        sa.text("DELETE FROM automation_definitions WHERE automation_key IN :keys").bindparams(
            sa.bindparam("keys", expanding=True)
        ),
        {"keys": keys},
    )
