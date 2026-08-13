"""seed V13.2 Sales CRM feature flags

Revision ID: v13_015_sales_crm_flags
Revises: v13_014_sales_crm_core
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

from app.core.snowflake import generate_snowflake_id

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
    # v13_001/v13_012 seeded global flags (workspace_id IS NULL) via a plain
    # non-unique index (ix_feature_flags_key) - fine for their SELECT-then-INSERT
    # pattern, but this migration's ON CONFLICT needs an actual partial unique
    # index to target, or Postgres rejects it with "no unique or exclusion
    # constraint matching the ON CONFLICT specification".
    op.create_index(
        "uix_feature_flags_global_key",
        "feature_flags",
        ["key"],
        unique=True,
        postgresql_where=sa.text("workspace_id IS NULL"),
    )
    for key, desc in V13_2_P0_FLAGS:
        op.get_bind().execute(
            sa.text(
                "INSERT INTO feature_flags (id, key, enabled, workspace_id, description, created_at, updated_at) "
                "VALUES (:id, :key, false, NULL, :desc, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) "
                "ON CONFLICT (key) WHERE workspace_id IS NULL DO NOTHING"
            ),
            {"id": generate_snowflake_id(), "key": key, "desc": desc},
        )


def downgrade() -> None:
    op.drop_index("uix_feature_flags_global_key", table_name="feature_flags")
