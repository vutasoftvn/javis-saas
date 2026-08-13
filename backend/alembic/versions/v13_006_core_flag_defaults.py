"""correct V13 core global defaults while preserving workspace overrides

Revision ID: v13_006_defaults
Revises: v13_005_finance
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "v13_006_defaults"
down_revision: Union[str, Sequence[str], None] = "v13_005_finance"
branch_labels = None
depends_on = None

CORE_FLAGS = (
    "legal_function_v13", "marketing_function_v13", "sales_function_v13",
    "tech_function_v13", "finance_function_v13", "learning_v13", "ceo_brief_v13",
)


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE feature_flags SET enabled = true, updated_at = CURRENT_TIMESTAMP "
            "WHERE workspace_id IS NULL AND key IN :keys "
            "AND description = 'mCOSA V13 focused-company-cycle default'"
        ).bindparams(sa.bindparam("keys", expanding=True)),
        {"keys": CORE_FLAGS},
    )


def downgrade() -> None:
    pass
