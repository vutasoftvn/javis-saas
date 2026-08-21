from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from core.snowflake import generate_snowflake_id
from integrations.realtime import tools


def test_get_ceo_brief_delegates_to_hub_summary_data():
    db = MagicMock()
    ws_id = generate_snowflake_id()

    with patch("integrations.realtime.tools.get_hub_summary_data") as mock_summary:
        mock_summary.return_value = {"status": "active"}
        result = tools.get_ceo_brief(db, ws_id)

    mock_summary.assert_called_once_with(db=db, workspace_id=ws_id)
    assert result == {"status": "active"}


def test_get_next_best_actions_flag_disabled_returns_empty_without_raising():
    """Unlike the HTTP route (which 400s via require_flag), a disabled flag
    here must degrade gracefully - the voice agent needs to say "not enabled
    for this workspace" mid-conversation, not raise an HTTPException."""
    db = MagicMock()
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    with patch("integrations.realtime.tools.is_enabled", return_value=False):
        result = tools.get_next_best_actions(db, ws_id, user_id)

    assert result == {"enabled": False, "next_actions": []}


def test_get_next_best_actions_flag_enabled_scopes_by_workspace_and_user():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    with patch("integrations.realtime.tools.is_enabled", return_value=True), patch(
        "integrations.realtime.tools.NextBestActionService"
    ) as mock_service_cls:
        mock_service = MagicMock()
        mock_service.get_top_next_actions.return_value = [{"title": "Ship MVP"}]
        mock_service_cls.return_value = mock_service

        result = tools.get_next_best_actions(db, ws_id, user_id, limit=3)

    mock_service_cls.assert_called_once_with(db, ws_id, user_id)
    mock_service.get_top_next_actions.assert_called_once_with(limit=3)
    assert result == {"enabled": True, "next_actions": [{"title": "Ship MVP"}]}


def test_get_project_status_found_returns_compact_status():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    project_id = generate_snowflake_id()
    fake_project = MagicMock(
        title="mVault",
        status="active",
        phase="BUILD",
        current_gate="GATE_2",
        project_type="PRODUCT",
        strategic_priority="P0",
    )

    with patch("integrations.realtime.tools.get_project_scoped", return_value=fake_project) as mock_scoped:
        result = tools.get_project_status(db, ws_id, project_id)

    mock_scoped.assert_called_once_with(db, project_id, ws_id)
    assert result == {
        "found": True,
        "title": "mVault",
        "status": "active",
        "phase": "BUILD",
        "current_gate": "GATE_2",
        "project_type": "PRODUCT",
        "strategic_priority": "P0",
    }


def test_get_project_status_cross_tenant_returns_not_found_without_raising():
    """A project from another workspace (or a nonexistent id) must not raise
    mid-turn - the voice agent needs to say "couldn't find that project"."""
    db = MagicMock()
    ws_id = generate_snowflake_id()
    project_id = generate_snowflake_id()

    with patch(
        "integrations.realtime.tools.get_project_scoped",
        side_effect=HTTPException(status_code=404, detail="Project not found"),
    ):
        result = tools.get_project_status(db, ws_id, project_id)

    assert result == {"found": False}


def test_get_portfolio_status_flag_disabled_returns_empty_without_raising():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    portfolio_id = generate_snowflake_id()

    with patch("integrations.realtime.tools.is_enabled", return_value=False):
        result = tools.get_portfolio_status(db, ws_id, user_id, portfolio_id)

    assert result == {"enabled": False}


def test_get_portfolio_status_flag_enabled_scopes_by_workspace():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    portfolio_id = generate_snowflake_id()

    with patch("integrations.realtime.tools.is_enabled", return_value=True), patch(
        "integrations.realtime.tools.PortfolioService"
    ) as mock_service_cls:
        mock_service = MagicMock()
        mock_service.get_portfolio.return_value = {"id": str(portfolio_id), "name": "Core"}
        mock_service_cls.return_value = mock_service

        result = tools.get_portfolio_status(db, ws_id, user_id, portfolio_id)

    mock_service_cls.assert_called_once_with(db, ws_id, user_id)
    mock_service.get_portfolio.assert_called_once_with(portfolio_id)
    assert result == {"enabled": True, "found": True, "portfolio": {"id": str(portfolio_id), "name": "Core"}}


def test_get_portfolio_status_not_found_returns_found_false_without_raising():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    portfolio_id = generate_snowflake_id()

    with patch("integrations.realtime.tools.is_enabled", return_value=True), patch(
        "integrations.realtime.tools.PortfolioService"
    ) as mock_service_cls:
        mock_service = MagicMock()
        mock_service.get_portfolio.side_effect = HTTPException(status_code=404, detail="Portfolio not found")
        mock_service_cls.return_value = mock_service

        result = tools.get_portfolio_status(db, ws_id, user_id, portfolio_id)

    assert result == {"enabled": True, "found": False}


def test_get_developer_job_status_found_returns_compact_status():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    job_id = generate_snowflake_id()
    fake_job = MagicMock(title="Implement X", status="RUNNING", diff_summary=None, test_results=None)
    db.query.return_value.filter.return_value.first.return_value = fake_job

    result = tools.get_developer_job_status(db, ws_id, job_id)

    assert result == {
        "found": True,
        "title": "Implement X",
        "status": "RUNNING",
        "diff_summary": None,
        "test_results": None,
    }


def test_get_developer_job_status_cross_tenant_returns_not_found():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    job_id = generate_snowflake_id()
    db.query.return_value.filter.return_value.first.return_value = None

    result = tools.get_developer_job_status(db, ws_id, job_id)

    assert result == {"found": False}


def test_request_developer_job_delegates_to_devices_service_with_idempotency_key():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    fake_job = MagicMock(id=999, status="QUEUED")

    with patch("integrations.realtime.tools.create_developer_job", return_value=fake_job) as mock_create:
        result = tools.request_developer_job(
            db, ws_id, user_id, "Implement Portfolio Impact Matrix", voice_command_id="call_abc123"
        )

    mock_create.assert_called_once_with(
        db, ws_id, user_id, "Implement Portfolio Impact Matrix", idempotency_key="call_abc123"
    )
    assert result == {"job_id": "999", "status": "QUEUED"}


def test_get_pending_approvals_delegates_to_workflow_approvals():
    db = MagicMock()
    ws_id = generate_snowflake_id()

    with patch("integrations.realtime.tools.list_workflow_approvals") as mock_list:
        mock_list.return_value = {"total": 1, "approvals": [{"id": "1"}]}
        result = tools.get_pending_approvals(db, ws_id, limit=3)

    mock_list.assert_called_once_with(
        workspace_id=ws_id, status_filter="pending", limit=3, offset=0, member=None, db=db
    )
    assert result == {"total": 1, "approvals": [{"id": "1"}]}


def test_approve_action_delegates_to_approve_workflow_step():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    step_id = generate_snowflake_id()

    with patch("integrations.realtime.tools.approve_workflow_step") as mock_approve:
        mock_approve.return_value = {"status": "success", "message": "Step approved and resumed"}
        result = tools.approve_action(db, ws_id, user_id, step_id)

    _, kwargs = mock_approve.call_args
    assert kwargs["step_id"] == step_id
    assert kwargs["workspace_id"] == ws_id
    assert kwargs["member"].user_id == user_id
    assert kwargs["db"] == db
    assert result == {"status": "success", "message": "Step approved and resumed"}


def test_approve_action_degrades_gracefully_instead_of_raising():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    step_id = generate_snowflake_id()

    with patch(
        "integrations.realtime.tools.approve_workflow_step",
        side_effect=HTTPException(status_code=400, detail="Step is not waiting for approval"),
    ):
        result = tools.approve_action(db, ws_id, user_id, step_id)

    assert result == {"ok": False, "error": "Step is not waiting for approval"}


def test_reject_action_delegates_to_reject_workflow_step():
    db = MagicMock()
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    step_id = generate_snowflake_id()

    with patch("integrations.realtime.tools.reject_workflow_step") as mock_reject:
        mock_reject.return_value = {"status": "success", "message": "Step rejected and workflow cancelled"}
        result = tools.reject_action(db, ws_id, user_id, step_id)

    _, kwargs = mock_reject.call_args
    assert kwargs["step_id"] == step_id
    assert kwargs["member"].user_id == user_id
    assert result == {"status": "success", "message": "Step rejected and workflow cancelled"}
