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


def test_runtime_dispatch_cycle_command_calls_the_orchestrator(monkeypatch):
    from app.modules.company_runtime import tools as company_runtime_tools
    from app.agents.orchestrator.command import CommandCategory, OrchestratorResponse

    captured = {}

    class _FakeOrchestrator:
        @staticmethod
        def handle_command(db, workspace_id, user_id, request):
            captured["request"] = request
            return OrchestratorResponse(
                command_id="cmd-1",
                status="proposal_created",
                category=request.category,
                action=request.action,
                proposal_id="999",
                message="Đã tạo đề xuất chờ duyệt.",
            )

    monkeypatch.setattr(company_runtime_tools, "WorkOrchestratorService", _FakeOrchestrator)

    db = MagicMock()
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    result = company_runtime_tools.runtime_dispatch_cycle_command(
        db, ws_id, user_id, duration_weeks=6, project_hint="mID",
    )

    assert result["status"] == "proposal_created"
    assert result["proposal_id"] == "999"
    assert captured["request"].category == CommandCategory.PLAN_CYCLE_COMMAND
    assert captured["request"].action == "activate_cycle"
    assert captured["request"].payload["desired_week_count"] == 6
    assert captured["request"].payload["title"] == "mID"

