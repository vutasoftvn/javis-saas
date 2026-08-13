"""enable V13.2 Sales CRM feature flags defaults

Revision ID: v13_016_sales_crm_flag_defaults
Revises: v13_015_sales_crm_flags
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "v13_016_sales_crm_flag_defaults"
down_revision: Union[str, Sequence[str], None] = "v13_015_sales_crm_flags"
branch_labels = None
depends_on = None

P0_FLAGS = (
    "sales_crm_core_v13_2",
    "account_contact_v13_2",
    "lead_management_v13_2",
    "opportunity_management_v13_2",
    "customer_core_v13_2",
    "marketing_sales_handoff_v13_2",
    "sales_finance_handoff_v13_2",
    "sales_legal_handoff_v13_2",
    "sales_tech_handoff_v13_2",
)


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE feature_flags SET enabled = true, updated_at = CURRENT_TIMESTAMP "
            "WHERE workspace_id IS NULL AND key IN :keys "
            "AND description = 'COSA V13.2 Revenue OS default'"
        ).bindparams(sa.bindparam("keys", expanding=True)),
        {"keys": P0_FLAGS},
    )


def downgrade() -> None:
    pass
