"""Tests for Shared Work Orchestrator Service and Policy Engine."""

import pytest
from unittest.mock import MagicMock, patch

from workforce.agents.orchestrator.command import CommandCategory, OrchestratorRequest
from workforce.agents.orchestrator.service import WorkOrchestratorService, PolicyEngine
from core.snowflake import generate_snowflake_id


def test_policy_engine_gates_high_risk_plan_commands():
    req = OrchestratorRequest(
        category=CommandCategory.PLAN_CYCLE_COMMAND,
        action="activate_cycle",
        payload={"duration_weeks": 13, "title": "Q3 Execution"},
    )
    policy = PolicyEngine.evaluate(req)
    assert policy.allowed is True
    assert policy.requires_approval is True
    assert policy.risk_level == "high"


def test_policy_engine_allows_low_risk_inquiry():
    req = OrchestratorRequest(
        category=CommandCategory.INQUIRY,
        action="get_status",
    )
    policy = PolicyEngine.evaluate(req)
    assert policy.allowed is True
    assert policy.requires_approval is False
    assert policy.risk_level == "low"


def test_orchestrator_creates_proposal_for_high_risk_action():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = MagicMock()

    with patch("workforce.agents.orchestrator.service.AgentProposalService.create_proposal") as mock_create:
        mock_proposal = MagicMock()
        mock_proposal.id = 123456789
        mock_proposal.status = "pending"
        mock_create.return_value = mock_proposal

        req = OrchestratorRequest(
            category=CommandCategory.PLAN_CYCLE_COMMAND,
            action="activate_cycle",
            payload={"duration_weeks": 13, "title": "Q3 Cycle"},
        )
        resp = WorkOrchestratorService.handle_command(
            db=db,
            workspace_id=ws_id,
            user_id=user_id,
            request=req,
        )

        assert resp.status == "proposal_created"
        assert resp.proposal_id == "123456789"
        mock_create.assert_called_once()


def test_orchestrator_answers_progress_snapshot_inquiry():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = MagicMock()

    mock_snapshot = {"cycle": {"duration_weeks": 13, "current_week": 2, "overall_progress": 25.0}}
    with patch("workforce.agents.orchestrator.service.ProgressSnapshotService.generate_snapshot", return_value=mock_snapshot):
        req = OrchestratorRequest(
            category=CommandCategory.REPORT_REQUEST,
            action="get_progress_snapshot",
        )
        resp = WorkOrchestratorService.handle_command(
            db=db,
            workspace_id=ws_id,
            user_id=user_id,
            request=req,
        )

        assert resp.status == "answered"
        assert resp.result == mock_snapshot


def test_orchestrator_activate_cycle_creates_an_applicable_proposal():
    """Bug đã tái hiện trực tiếp trước khi sửa: payload cũ {"action":..., "category":...}
    bị ProposalCommand's allowlist strict từ chối với ValidationError chưa bắt. Test này
    chạy qua AgentProposalService.create_proposal THẬT (không mock) để đảm bảo payload
    sinh ra khớp đúng shape ProposalCommand chờ đợi."""
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = MagicMock()
    db.refresh.side_effect = lambda proposal: None

    req = OrchestratorRequest(
        category=CommandCategory.PLAN_CYCLE_COMMAND,
        action="activate_cycle",
        payload={"title": "PMF validation cycle", "desired_week_count": 6},
    )
    resp = WorkOrchestratorService.handle_command(
        db=db, workspace_id=ws_id, user_id=user_id, request=req,
    )

    assert resp.status == "proposal_created"
    created_proposal = db.add.call_args.args[0]
    assert created_proposal.payload_jsonb["command"]["command_type"] == "project_cycle.setup"
    assert created_proposal.payload_jsonb["command"]["arguments"]["desired_week_count"] == 6


def test_orchestrator_rejects_unsupported_high_risk_action_cleanly():
    """Action không có trong bảng ánh xạ phải trả về 'rejected' sạch, không crash 500."""
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = MagicMock()

    req = OrchestratorRequest(
        category=CommandCategory.PLAN_CYCLE_COMMAND,
        action="an_action_with_no_mapped_command_type",
        payload={},
    )
    resp = WorkOrchestratorService.handle_command(
        db=db, workspace_id=ws_id, user_id=user_id, request=req,
    )

    assert resp.status == "rejected"
    assert "an_action_with_no_mapped_command_type" in resp.message
    db.add.assert_not_called()

