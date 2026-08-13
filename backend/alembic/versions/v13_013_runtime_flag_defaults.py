"""enable V13.1 P0 core feature flags defaults

Revision ID: v13_013_flag_defaults
Revises: v13_012_runtime_flags
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "v13_013_flag_defaults"
down_revision: Union[str, Sequence[str], None] = "v13_012_runtime_flags"
branch_labels = None
depends_on = None

P0_FLAGS = (
    "company_runtime_v13_1",
    "workitem_state_machine_v13_1",
    "work_contract_v13_1",
    "review_rework_v13_1",
    "dependency_dag_v13_1",
    "structured_blocker_v13_1",
    "needs_you_queue_v13_1",
    "structured_handoff_v13_1",
    "work_inspector_v13_1",
    "runtime_checkpoint_v13_1",
    "work_intent_classifier_v13_1",
    "quick_task_v13_1",
    "company_work_v13_1",
)


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            "UPDATE feature_flags SET enabled = true, updated_at = CURRENT_TIMESTAMP "
            "WHERE workspace_id IS NULL AND key IN :keys "
            "AND description = 'mCOSA V13.1 Company Runtime default'"
        ).bindparams(sa.bindparam("keys", expanding=True)),
        {"keys": P0_FLAGS},
    )


def downgrade() -> None:
    pass
