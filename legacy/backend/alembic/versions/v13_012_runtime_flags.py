"""seed V13.1 feature flags as disabled defaults

Revision ID: v13_012_runtime_flags
Revises: v13_011_checkpoints
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from core.snowflake import generate_snowflake_id

revision: str = "v13_012_runtime_flags"
down_revision: Union[str, Sequence[str], None] = "v13_011_checkpoints"
branch_labels = None
depends_on = None

V13_1_FLAGS = (
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
    "executor_resolver_v13_1",
    "ephemeral_specialist_v13_1",
    "cycle_grants_v13_1",
    "role_attribution_v13_1",
    "agent_experience_v13_1",
    "function_skills_v13_1",
)


def _insert_absent(bind, key: str, enabled: bool) -> None:
    exists = bind.execute(
        sa.text("SELECT 1 FROM feature_flags WHERE workspace_id IS NULL AND key = :key"),
        {"key": key},
    ).first()
    if exists is None:
        bind.execute(
            sa.text(
                "INSERT INTO feature_flags "
                "(id, workspace_id, key, enabled, description, created_at, updated_at) "
                "VALUES (:id, NULL, :key, :enabled, :description, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"id": generate_snowflake_id(), "key": key, "enabled": enabled, "description": "mCOSA V13.1 Company Runtime default"},
        )


def upgrade() -> None:
    bind = op.get_bind()
    for key in V13_1_FLAGS:
        _insert_absent(bind, key, False)


def downgrade() -> None:
    pass
