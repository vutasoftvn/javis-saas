from datetime import datetime
import uuid
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from app.db.models import WorkspaceMember
from app.modules.outcomes.models import Outcome, OutcomeRun, RunStep, RunEvent, Artifact
from app.modules.outcomes.router import (
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
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
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
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    outcome_id = uuid.uuid4()
    
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
    ws_id_a = uuid.uuid4()
    ws_id_b = uuid.uuid4()
    
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
    ws_id = uuid.uuid4()
    user_id = uuid.uuid4()
    
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
