import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session

from cosa_core.tools.invocation.policy_gate import PolicyGate
from cosa_core.tools.invocation.contracts import ToolInvocationRequest, ToolInvocationResult
from cosa_core.tools.registry import ToolSpec
from cosa_core.runtime.execution_scope import ExecutionScope
from cosa_core.governance.kernel import GovernanceDecision
from cosa_core.governance.policy_engine import PolicyAction

def sample_tool():
    pass

@pytest.fixture
def dummy_request():
    scope = ExecutionScope(
        workspace_id=1,
        company_id=1,
        principal_user_id=1,
        principal_member_id=1,
        principal_role="owner",
        operating_unit_id=None,
        offering_id=None,
        initiative_id=None,
        profile_id=None,
        session_id=None,
        grants=()
    )
    return ToolInvocationRequest(
        scope=scope,
        tool_flat_name="test_tool",
        arguments={},
        source="chat"
    )

@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

def test_policy_gate_allow(dummy_request, mock_db):
    gate = PolicyGate()
    
    spec = ToolSpec(namespace="test", name="tool", callable=sample_tool)
    
    # Mock kernel
    gate.kernel = MagicMock()
    gate.kernel.evaluate_and_audit_tool_call.return_value = GovernanceDecision(
        allowed=True,
        action=PolicyAction.ALLOW,
        reason="allowed",
        tool_spec=spec,
        sanitized_args={}
    )
    
    # Spy backend
    spy = MagicMock(return_value="executed")
    
    result = gate.execute_if_allowed(mock_db, dummy_request, spy)
    
    assert result == "executed"
    spy.assert_called_once()

def test_policy_gate_deny(dummy_request, mock_db):
    gate = PolicyGate()
    
    spec = ToolSpec(namespace="test", name="tool", callable=sample_tool)
    
    gate.kernel = MagicMock()
    gate.kernel.evaluate_and_audit_tool_call.return_value = GovernanceDecision(
        allowed=False,
        action=PolicyAction.DENY,
        reason="denied",
        tool_spec=spec,
        sanitized_args={}
    )
    
    spy = MagicMock()
    
    result = gate.execute_if_allowed(mock_db, dummy_request, spy)
    
    assert isinstance(result, ToolInvocationResult)
    assert result.status == "denied"
    spy.assert_not_called()

def test_policy_gate_require_approval(dummy_request, mock_db):
    gate = PolicyGate()
    
    spec = ToolSpec(namespace="test", name="tool", callable=sample_tool)
    
    mock_approval = MagicMock()
    mock_approval.id = 42
    
    gate.kernel = MagicMock()
    gate.kernel.evaluate_and_audit_tool_call.return_value = GovernanceDecision(
        allowed=False,
        action=PolicyAction.REQUIRE_APPROVAL,
        reason="approval required",
        tool_spec=spec,
        approval=mock_approval,
        sanitized_args={}
    )
    
    spy = MagicMock()
    
    result = gate.execute_if_allowed(mock_db, dummy_request, spy)
    
    assert isinstance(result, ToolInvocationResult)
    assert result.status == "approval_required"
    assert result.approval_id == "42"
    spy.assert_not_called()
