from unittest.mock import MagicMock
import pytest

from app.core.snowflake import generate_snowflake_id
from app.founder_os.outcomes.models import Outcome
from app.founder_os.tasks.models import Task
from app.platform.license.review_service import ReviewService


def test_review_accepted_flow():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    task_id = generate_snowflake_id()
    outcome_id = generate_snowflake_id()

    task = Task(id=task_id, workspace_id=ws_id, title="Implement Feature", status="in_progress")
    outcome = Outcome(id=outcome_id, workspace_id=ws_id, task_id=task_id, title="Feature Outcome", desired_result="Done", status="running", rework_count=0)

    db.query.return_value.filter.return_value.first.side_effect = [outcome, task]

    review = ReviewService.create_review(
        db=db,
        workspace_id=ws_id,
        outcome_id=outcome_id,
        reviewer_type="COSA_REVIEW",
        result="ACCEPTED",
        feedback="High quality output",
    )

    assert review.result == "ACCEPTED"
    assert outcome.status == "completed"
    assert task.status == "done"


def test_review_rework_loop_and_cap():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    task_id = generate_snowflake_id()
    outcome_id = generate_snowflake_id()

    task = Task(id=task_id, workspace_id=ws_id, title="Draft Copy", status="waiting_approval")
    outcome = Outcome(id=outcome_id, workspace_id=ws_id, task_id=task_id, title="Copy Outcome", desired_result="Done", status="planning", rework_count=1)

    db.query.return_value.filter.return_value.first.side_effect = [outcome, task]

    # Rework 2 (rework_count becomes 2)
    review = ReviewService.create_review(
        db=db,
        workspace_id=ws_id,
        outcome_id=outcome_id,
        reviewer_type="FOUNDER_REVIEW",
        result="REWORK_REQUIRED",
        feedback="CTA does not match ICP",
        max_rework_count=3,
    )

    assert review.result == "REWORK_REQUIRED"
    assert outcome.rework_count == 2
    assert task.status == "in_progress"

    # Now attempt when rework_count == 3 (hits max_rework_count cap)
    outcome.rework_count = 3
    db.query.return_value.filter.return_value.first.side_effect = [outcome, task]

    with pytest.raises(ValueError, match="Max rework count .* exceeded"):
        ReviewService.create_review(
            db=db,
            workspace_id=ws_id,
            outcome_id=outcome_id,
            reviewer_type="FOUNDER_REVIEW",
            result="REWORK_REQUIRED",
            feedback="Still needs changes",
            max_rework_count=3,
        )
