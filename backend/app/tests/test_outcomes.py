from datetime import datetime
from app.core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from app.db.models import WorkspaceMember
from app.founder_os.outcomes import service
from app.founder_os.outcomes.models import Outcome, OutcomeRun, RunStep, RunEvent, Artifact
from app.founder_os.outcomes.router import (
    create_new_outcome,
    list_workspace_outcomes,
    trigger_outcome_run,
    get_outcome_run_details,
    list_outcome_run_events,
    create_new_artifact,
    list_workspace_artifacts,
    OutcomeCreate,
    ArtifactCreate,
)


def test_outcome_creation_and_lifecycle():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id
    member.user_id = user_id
    
    db = MagicMock()
    
    data = OutcomeCreate(
        title="Chiến dịch Q3 Brand Launch",
        desired_result="Hoàn thành bộ tài liệu ra mắt và landing page",
        acceptance_criteria={"min_pages": 3, "reviewed_by_legal": True}
    )
    
    res = create_new_outcome(data=data, workspace_id=ws_id, member=member, db=db)
    assert res["title"] == "Chiến dịch Q3 Brand Launch"
    assert res["status"] == "draft"
    assert db.add.called
    assert db.commit.called


def test_trigger_outcome_run_lifecycle(monkeypatch):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    outcome_id = generate_snowflake_id()
    
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id
    member.user_id = user_id
    
    db = MagicMock()
    
    mock_outcome = MagicMock(spec=Outcome)
    mock_outcome.id = outcome_id
    mock_outcome.workspace_id = ws_id
    mock_outcome.title = "Báo cáo phân tích đối thủ"
    mock_outcome.desired_result = "Tài liệu so sánh tính năng"
    
    db.query.return_value.filter.return_value.first.return_value = mock_outcome
    
    res = trigger_outcome_run(outcome_id=outcome_id, workspace_id=ws_id, member=member, db=db)
    
    assert res["status"] == "running"
    assert res["outcome_id"] == str(outcome_id)
    assert mock_outcome.status == "running"
    assert db.add.called
    assert db.commit.called


def test_cross_tenant_isolation_forbidden():
    ws_id_a = generate_snowflake_id()
    ws_id_b = generate_snowflake_id()
    
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id_a
    
    db = MagicMock()
    
    data = OutcomeCreate(
        title="Unauthorized Outcome",
        desired_result="Should fail"
    )
    
    # Try creating outcome in workspace B with member of workspace A
    with pytest.raises(HTTPException) as exc_info:
        create_new_outcome(data=data, workspace_id=ws_id_b, member=member, db=db)
        
    assert exc_info.value.status_code == 403


def test_artifact_creation_and_listing():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id
    member.user_id = user_id
    
    db = MagicMock()
    
    data = ArtifactCreate(
        title="Sơ đồ kiến trúc V10",
        type="document",
        local_uri="/storage/docs/v10.pdf"
    )
    
    res = create_new_artifact(data=data, workspace_id=ws_id, member=member, db=db)
    assert res["title"] == "Sơ đồ kiến trúc V10"
    assert res["type"] == "document"
    assert res["status"] == "draft"
    assert db.add.called


def test_create_outcome_run_publishes_run_events_to_mission_control_bus(monkeypatch):
    """P0.3: RunEvent used to be a DB-only insert, invisible to any live subscriber watching
    mission_control_bus (SSE / Mission Inspector / Hologram Hub) - only AgentEventRecord events
    from chief_of_staff.py reached that bus. Every RunEvent created by create_outcome_run must
    now also be published live via mission_control_bus.emit_event with matching run_id/
    workspace_id/event_type/payload."""
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    outcome_id = generate_snowflake_id()

    db = MagicMock()

    mock_outcome = MagicMock(spec=Outcome)
    mock_outcome.id = outcome_id
    mock_outcome.workspace_id = ws_id
    mock_outcome.title = "Kế hoạch ra mắt sản phẩm"
    mock_outcome.desired_result = "Tài liệu kế hoạch chi tiết"
    db.query.return_value.filter.return_value.first.return_value = mock_outcome

    from app.workforce.agents.orchestration.mission_control_bus import mission_control_bus

    emitted_calls = []
    mock_emit = MagicMock(side_effect=lambda **kwargs: emitted_calls.append(kwargs))
    monkeypatch.setattr(mission_control_bus, "emit_event", mock_emit)

    run = service.create_outcome_run(
        db=db, outcome_id=outcome_id, workspace_id=ws_id, user_id=user_id
    )

    # 3 RunEvent rows are created in create_outcome_run: run.created, step.completed,
    # artifact.created - each one must have a matching live emit_event call.
    assert mock_emit.call_count == 3
    event_types = [call["event_type"] for call in emitted_calls]
    assert event_types == ["run.created", "step.completed", "artifact.created"]

    for call in emitted_calls:
        assert call["run_id"] == str(run.id)
        assert call["workspace_id"] == str(ws_id)
        assert isinstance(call["data"], dict)

    assert emitted_calls[0]["data"]["outcome_id"] == str(outcome_id)
    assert emitted_calls[2]["data"]["title"].startswith("Báo cáo kết quả")

    persisted_events = [
        call.args[0]
        for call in db.add.call_args_list
        if call.args and isinstance(call.args[0], RunEvent)
    ]
    assert [event.sequence for event in persisted_events] == [1, 2, 3]
    assert len({event.event_key for event in persisted_events}) == 3
