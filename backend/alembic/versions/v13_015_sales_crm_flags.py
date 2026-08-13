"""seed V13.2 Sales CRM feature flags

Revision ID: v13_015_sales_crm_flags
Revises: v13_014_sales_crm_core
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "v13_015_sales_crm_flags"
down_revision: Union[str, Sequence[str], None] = "v13_014_sales_crm_core"
branch_labels = None
depends_on = None

V13_2_P0_FLAGS = (
    ("sales_crm_core_v13_2", "COSA V13.2 Revenue OS default"),
    ("account_contact_v13_2", "COSA V13.2 Revenue OS default"),
    ("lead_management_v13_2", "COSA V13.2 Revenue OS default"),
    ("opportunity_management_v13_2", "COSA V13.2 Revenue OS default"),
    ("customer_core_v13_2", "COSA V13.2 Revenue OS default"),
    ("marketing_sales_handoff_v13_2", "COSA V13.2 Revenue OS default"),
    ("sales_finance_handoff_v13_2", "COSA V13.2 Revenue OS default"),
    ("sales_legal_handoff_v13_2", "COSA V13.2 Revenue OS default"),
    ("sales_tech_handoff_v13_2", "COSA V13.2 Revenue OS default"),
)


def upgrade() -> None:
    for key, desc in V13_2_P0_FLAGS:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO feature_flags (id, key, enabled, workspace_id, description, created_at, updated_at) "
                "VALUES (CAST(floor(random() * 9000000000000000000 + 1000000000000000000) AS BIGINT), :key, false, NULL, :desc, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) "
                "ON CONFLICT (key) WHERE workspace_id IS NULL DO NOTHING"
            ),
            {"key": key, "desc": desc},
        )


def downgrade() -> None:
    pass
