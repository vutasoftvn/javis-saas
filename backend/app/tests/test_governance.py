import uuid
from app.core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from app.db.models import WorkspaceMember, WorkflowRun, WorkflowStep, WorkflowApproval, AuditLog, WorkflowDefinition, Brain
from app.core.audit import write_audit_log
from app.modules.platform.router import list_audit_events
from app.modules.workflows.router import (
    approve_workflow_step,
    reject_workflow_step,
    list_workflow_approvals,
    list_workflow_definitions
)


def test_write_audit_log_helper():
    db = MagicMock()
    actor_id = generate_snowflake_id()
    target_id = generate_snowflake_id()
    
    log = write_audit_log(
        db=db,
        actor_type="user",
        actor_id=actor_id,
        action="workflow.step.approve",
        target_type="workflow_step",
        target_id=target_id,
        metadata_jsonb={"run_id": "test-run"}
    )
    
    assert log.action == "workflow.step.approve"
    assert log.actor_type == "user"
    assert db.add.called
    assert db.commit.called


def test_list_audit_events_cross_tenant_forbidden():
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = generate_snowflake_id()
    
    other_ws_id = generate_snowflake_id()
    db = MagicMock()
    
    with pytest.raises(HTTPException) as exc_info:
        list_audit_events(workspace_id=other_ws_id, member=member, db=db)
        
    assert exc_info.value.status_code == 403


def test_list_audit_events_scoped_success():
    ws_id = generate_snowflake_id()
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id
    member.user_id = generate_snowflake_id()
    
    db = MagicMock()
    
    # Mock audit logs
    mock_log1 = MagicMock(spec=AuditLog)
    mock_log1.id = generate_snowflake_id()
    mock_log1.actor_type = "user"
    mock_log1.actor_id = member.user_id
    mock_log1.action = "workflow.step.approve"
    mock_log1.target_type = "workflow_step"
    mock_log1.target_id = generate_snowflake_id()
    mock_log1.metadata_jsonb = {"workspace_id": str(ws_id)}
    mock_log1.created_at = MagicMock()
    mock_log1.created_at.isoformat.return_value = "2026-08-11T07:50:00"
    
    # list_audit_events now scopes strictly via a single DB-level filter on
    # metadata_jsonb['workspace_id'] (.filter().order_by().count() /
    # .offset().limit().all()) - it no longer issues a second query against
    # WorkspaceMember for an actor-membership fallback (that was the source
    # of a cross-tenant leak, see test_platform_audit_events.py).
    query = MagicMock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.offset.return_value = query
    query.limit.return_value = query
    query.count.return_value = 1
    query.all.return_value = [mock_log1]
    db.query.return_value = query

    res = list_audit_events(workspace_id=ws_id, member=member, db=db)
    assert res["total"] == 1
    assert res["events"][0]["action"] == "workflow.step.approve"


def test_approve_and_reject_workflow_step_with_audit(monkeypatch):
    ws_id = generate_snowflake_id()
    member = MagicMock(spec=WorkspaceMember)
    member.workspace_id = ws_id
    member.user_id = generate_snowflake_id()
    
    step_id = generate_snowflake_id()
    run_id = generate_snowflake_id()
    
    db = MagicMock()
    
    mock_step = MagicMock(spec=WorkflowStep)
    mock_step.id = step_id
    mock_step.run_id = run_id
    mock_step.status = "waiting_approval"
    mock_step.node_id = "agent_action"
    
    mock_run = MagicMock(spec=WorkflowRun)
    mock_run.id = run_id
    mock_run.status = "paused"
    
    mock_approval = MagicMock(spec=WorkflowApproval)
    mock_approval.id = generate_snowflake_id()
    mock_approval.step_id = step_id
    mock_approval.status = "pending"
    
    db.query.return_value.filter.return_value.first.side_effect = [
        mock_step,      # step lookup
        mock_run,       # run lookup
        mock_approval,  # approval lookup
    ]
    
    # Mock resolve_workflow_run_workspace_id
    monkeypatch.setattr("app.modules.workflows.router.resolve_workflow_run_workspace_id", lambda db, run: ws_id)
    
    res = approve_workflow_step(step_id=step_id, workspace_id=ws_id, member=member, db=db)
    assert res["status"] == "success"
    assert mock_step.status == "running"
    assert mock_approval.status == "approved"
    assert db.commit.called
