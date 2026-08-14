from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_current_workspace_member
from app.core.snowflake import generate_snowflake_id
from app.core.tool_registry import ToolSpec
from app.agents.governance.models import AgentRun, AgentApproval
from app.agents.governance.policy_engine import (
    PolicyEngine,
    PolicyAction,
    PermissionLevel,
)
from app.agents.governance.approval_service import ApprovalService
from app.modules.sales.sales_tools import create_activity


def test_policy_engine_l0_read_enforcement():
    read_tool = ToolSpec(
        namespace="sales",
        name="get_pipeline_summary",
        callable=lambda: None,
        permission_level="read_only",
        risk_level="low",
        allowed_agent_keys=["sales_specialist"],
    )
    write_tool = ToolSpec(
        namespace="sales",
        name="create_activity",
        callable=lambda: None,
        permission_level="scoped_write",
        risk_level="low",
        allowed_agent_keys=["sales_specialist"],
    )

    # 1. Read tool under L0 is ALLOWED
    dec1 = PolicyEngine.evaluate(
        agent_key="sales_specialist",
        tool_spec=read_tool,
        permission_profile="L0_READ",
    )
    assert dec1.action == PolicyAction.ALLOW

    # 2. Write tool under L0 is DENIED
    dec2 = PolicyEngine.evaluate(
        agent_key="sales_specialist",
        tool_spec=write_tool,
        permission_profile="L0_READ",
    )
    assert dec2.action == PolicyAction.DENY


def test_policy_engine_l1_suggest_requires_approval_for_write():
    write_tool = ToolSpec(
        namespace="sales",
        name="create_activity",
        callable=lambda: None,
        permission_level="scoped_write",
        risk_level="low",
        allowed_agent_keys=["sales_specialist"],
    )

    decision = PolicyEngine.evaluate(
        agent_key="sales_specialist",
        tool_spec=write_tool,
        permission_profile="L1_SUGGEST",
    )
    assert decision.action == PolicyAction.REQUIRE_APPROVAL
    assert decision.requires_approval is True


def test_policy_engine_l2_and_l3_execution():
    low_risk_write = ToolSpec(
        namespace="sales",
        name="create_activity",
        callable=lambda: None,
        permission_level="scoped_write",
        risk_level="low",
        allowed_agent_keys=["sales_specialist"],
    )
    critical_write = ToolSpec(
        namespace="finance",
        name="execute_transfer",
        callable=lambda: None,
        permission_level="admin_write",
        risk_level="critical",
        allowed_agent_keys=["finance_specialist"],
    )

    # L2 allows low-risk scoped write
    dec_l2 = PolicyEngine.evaluate(
        agent_key="sales_specialist",
        tool_spec=low_risk_write,
        permission_profile="L2_DRAFT",
    )
    assert dec_l2.action == PolicyAction.ALLOW

    # L3 allows low-risk write
    dec_l3 = PolicyEngine.evaluate(
        agent_key="sales_specialist",
        tool_spec=low_risk_write,
        permission_profile="L3_EXECUTE",
    )
    assert dec_l3.action == PolicyAction.ALLOW

    # Critical risk ALWAYS mandates approval under L3
    dec_crit = PolicyEngine.evaluate(
        agent_key="finance_specialist",
        tool_spec=critical_write,
        permission_profile="L3_EXECUTE",
    )
    assert dec_crit.action == PolicyAction.REQUIRE_APPROVAL


def test_policy_engine_agent_key_whitelist():
    tool = ToolSpec(
        namespace="sales",
        name="get_pipeline_summary",
        callable=lambda: None,
        permission_level="read_only",
        risk_level="low",
        allowed_agent_keys=["sales_specialist"],
    )

    # Unlisted agent key is DENIED
    dec = PolicyEngine.evaluate(
        agent_key="marketing_specialist",
        tool_spec=tool,
        permission_profile="L0_READ",
    )
    assert dec.action == PolicyAction.DENY


def test_approval_service_lifecycle():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    appr_id = generate_snowflake_id()

    approval = AgentApproval(
        id=appr_id,
        workspace_id=ws_id,
        requested_by_agent="sales_specialist",
        action_type="create_activity",
        tool_name="sales.create_activity",
        risk_level="low",
        status="pending",
    )

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = approval

    # Test approve
    approved = ApprovalService.approve(
        db=db,
        workspace_id=ws_id,
        approval_id=appr_id,
        reviewed_by=user_id,
    )
    assert approved.status == "approved"
    assert approved.reviewed_by == user_id


def test_approvals_rest_endpoints(client: TestClient):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    appr_id = generate_snowflake_id()

    member = MagicMock()
    member.workspace_id = ws_id
    member.user_id = user_id

    app.dependency_overrides[get_current_workspace_member] = lambda: member

    approval = AgentApproval(
        id=appr_id,
        workspace_id=ws_id,
        requested_by_agent="sales_specialist",
        action_type="create_activity",
        tool_name="sales.create_activity",
        risk_level="low",
        status="pending",
    )

    try:
        from app.db.session import get_db
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [approval]
        mock_db.query.return_value.filter.return_value.first.return_value = approval
        app.dependency_overrides[get_db] = lambda: mock_db

        # GET /api/v1/agents/approvals
        res = client.get("/api/v1/agents/approvals")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["id"] == str(appr_id)

        # POST /api/v1/agents/approvals/{id}/approve
        res_approve = client.post(f"/api/v1/agents/approvals/{appr_id}/approve")
        assert res_approve.status_code == 200
        assert res_approve.json()["status"] == "approved"

    finally:
        app.dependency_overrides.pop(get_current_workspace_member, None)


def test_sales_create_activity_tool():
    ws_id = generate_snowflake_id()
    db = MagicMock()

    res = create_activity(
        db=db,
        workspace_id=ws_id,
        entity_type="lead",
        entity_id=12345,
        activity_type="CALL",
        summary="Spoke with VP of Engineering regarding requirements",
        outcome="Scheduled follow-up demo for Tuesday",
        next_action="Send calendar invite",
    )

    assert res["status"] == "success"
    assert res["entity_type"] == "lead"
    assert res["entity_id"] == 12345
    assert res["activity_type"] == "CALL"
    assert "activity_id" in res
