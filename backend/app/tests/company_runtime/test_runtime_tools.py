from unittest.mock import MagicMock
import pytest

from app.core.snowflake import generate_snowflake_id
from app.modules.company_runtime.tools import (
    runtime_get_status,
    runtime_get_dag,
    runtime_get_blockers,
    runtime_get_needs_you,
    runtime_create_handoff,
    work_review,
    work_rework,
    runtime_classify_intent,
)
from app.modules.company_runtime.models import Blocker, NeedsYouItem, WorkReview
from app.modules.tasks.models import Task
from app.modules.outcomes.models import Outcome


def test_runtime_tools_execution():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    outcome_id = generate_snowflake_id()
    task_id = generate_snowflake_id()

    # 1. runtime_get_status
    db.query.return_value.filter.return_value.all.return_value = []
    db.query.return_value.filter.return_value.count.return_value = 0
    status = runtime_get_status(db, ws_id)
    assert "total_tasks" in status

    # 2. runtime_classify_intent
    intent = runtime_classify_intent(db, ws_id, "Tôi muốn duyệt chi phí phần mềm")
    assert intent["intent"] == "APPROVAL"

    # 3. runtime_get_blockers
    db.query.return_value.filter.return_value.all.return_value = [
        Blocker(id=generate_snowflake_id(), workspace_id=ws_id, blocker_type="LEGAL_UNCERTAINTY", description="GDPR review", status="OPEN")
    ]
    blockers = runtime_get_blockers(db, ws_id)
    assert blockers["total"] == 1

    # 4. runtime_get_needs_you
    db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
        NeedsYouItem(id=generate_snowflake_id(), workspace_id=ws_id, source_type="blocker", source_id=1, priority="P0", reason="Needs decision", status="OPEN")
    ]
    needs = runtime_get_needs_you(db, ws_id)
    assert needs["total"] == 1

    # 5. work_review (ACCEPTED)
    outcome = Outcome(id=outcome_id, workspace_id=ws_id, task_id=task_id, title="Test", desired_result="Done", status="running")
    task = Task(id=task_id, workspace_id=ws_id, title="Test Task", status="in_progress")
    db.query.return_value.filter.return_value.first.side_effect = [outcome, task]

    review_res = work_review(db, ws_id, outcome_id=outcome_id, result="ACCEPTED", feedback="Approved")
    assert review_res["ok"] is True
    assert review_res["result"] == "ACCEPTED"
