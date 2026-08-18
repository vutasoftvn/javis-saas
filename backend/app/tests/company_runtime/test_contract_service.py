from unittest.mock import MagicMock
import pytest

from app.core.snowflake import generate_snowflake_id
from app.founder_os.outcomes.models import Outcome
from app.platform.license.contract_service import WorkContractService


def test_set_work_contract_and_kr_links():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    task_id = generate_snowflake_id()
    reviewer_id = generate_snowflake_id()
    kr_id_1 = generate_snowflake_id()
    kr_id_2 = generate_snowflake_id()

    outcome = Outcome(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        title="Beta Waitlist Landing",
        desired_result="Public waitlist page live",
        status="planning",
    )

    updated = WorkContractService.set_work_contract(
        db=db,
        outcome=outcome,
        task_id=task_id,
        required_artifacts=["Landing URL", "Copy Doc", "Screenshot"],
        reviewer_id=reviewer_id,
        review_type="COSA_REVIEW",
        validation_rules=["Responsive test pass", "Analytics event fires"],
        linked_kr_ids=[kr_id_1, kr_id_2],
    )

    assert updated.task_id == task_id
    assert updated.reviewer_id == reviewer_id
    assert updated.review_type == "COSA_REVIEW"
    assert updated.required_artifacts == {"items": ["Landing URL", "Copy Doc", "Screenshot"]}
    assert updated.validation_rules == {"rules": ["Responsive test pass", "Analytics event fires"]}
    assert db.commit.called
