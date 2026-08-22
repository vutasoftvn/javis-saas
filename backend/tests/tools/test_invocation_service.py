import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from cosa_core.tools.invocation.service import ToolInvocationService, invoke_tool_via_spec
from cosa_core.tools.invocation.contracts import ToolInvocationRequest
from cosa_core.tools.registry import ToolSpec
from cosa_core.runtime.execution_scope import ExecutionScope

def sample_tool(workspace_id: int):
    return {"workspace": workspace_id}

@pytest.fixture
def dummy_scope():
    return ExecutionScope(
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

@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

@pytest.mark.asyncio
async def test_tool_invocation_service_e2e(dummy_scope, mock_db):
    spec = ToolSpec(namespace="test", name="tool", callable=sample_tool)

    # We must patch get_tool_by_flat_name in the service's imported location
    import cosa_core.tools.registry as tr_mod
    original_get_tool = tr_mod.get_tool_by_flat_name
    tr_mod.get_tool_by_flat_name = MagicMock(return_value=spec)
    
    req = ToolInvocationRequest(
        scope=dummy_scope,
        tool_flat_name="test_tool",
        arguments={},
        source="chat"
    )
    
    service = ToolInvocationService()
    
    # Mock kernel to always allow
    service.policy_gate.kernel = MagicMock()

    from cosa_core.governance.kernel import GovernanceDecision
    from cosa_core.governance.policy_engine import PolicyAction
    service.policy_gate.kernel.evaluate_and_audit_tool_call.return_value = GovernanceDecision(
        allowed=True,
        action=PolicyAction.ALLOW,
        reason="allowed",
        tool_spec=spec,
        sanitized_args={}
    )
    
    result = await service.invoke(mock_db, req)
    
    assert result.status == "success"
    assert result.output == {"workspace": 1}
    tr_mod.get_tool_by_flat_name = original_get_tool

@pytest.mark.asyncio
async def test_invoke_tool_via_spec(mock_db):
    spec = ToolSpec(namespace="test", name="tool", callable=sample_tool)

    import cosa_core.tools.registry as tr_mod
    original_get_tool = tr_mod.get_tool_by_flat_name
    tr_mod.get_tool_by_flat_name = MagicMock(return_value=spec)

    # We need to mock service inside invoke_tool_via_spec if we want to isolate,
    # or just let it run e2e. Let's run e2e.
    # We must mock GovernanceKernel.evaluate_and_audit_tool_call inside policy_gate

    # Actually, we can just replace the ToolInvocationService's policy_gate in invoke_tool_via_spec,
    # or mock kernel globally.

    import cosa_core.tools.invocation.policy_gate as pg
    original_kernel = pg.GovernanceKernel
    pg.GovernanceKernel = MagicMock()
    mock_instance = pg.GovernanceKernel.return_value

    from cosa_core.governance.kernel import GovernanceDecision
    from cosa_core.governance.policy_engine import PolicyAction
    mock_instance.evaluate_and_audit_tool_call.return_value = GovernanceDecision(
        allowed=True,
        action=PolicyAction.ALLOW,
        reason="allowed",
        tool_spec=spec,
        sanitized_args={}
    )
    
    # Invoke legacy
    result = await invoke_tool_via_spec(
        spec=spec,
        db=mock_db,
        workspace_id=1,
        user_id=42,
        arguments={}
    )
    
    assert result == {"workspace": 1}
    
    # Restore
    pg.GovernanceKernel = original_kernel
    tr_mod.get_tool_by_flat_name = original_get_tool
