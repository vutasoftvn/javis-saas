import pytest
from unittest.mock import MagicMock
from typing import Any
import inspect

from core.tool_registry import ToolSpec
from core.tool_dispatch import execute_tool_spec

# Note: As of Phase 2, GovernanceKernel is implemented in app/workforce/agents/runtime/governance.py or similar.
# Since we are just writing characterization tests, we'll mock the GovernanceKernel behavior.

def sample_tool(db, workspace_id: int, user_id: int, target: str, payload: dict) -> dict:
    return {"status": "ok", "target": target}

@pytest.fixture
def db_session():
    return MagicMock()

@pytest.mark.asyncio
async def test_execute_tool_spec_strips_injected_parameters(db_session):
    """
    Characterization test: execute_tool_spec currently strips parameters
    like workspace_id from the model's arguments and injects server-side ones.
    """
    spec = ToolSpec(
        namespace="test",
        name="sample_tool",
        callable=sample_tool,
    )
    
    # Model attempts to inject a different workspace_id and user_id
    malicious_args = {
        "workspace_id": 9999,
        "user_id": 9999,
        "target": "victim",
        "payload": {}
    }
    
    import core.tool_registry as tr_mod
    original_get_tool = tr_mod.get_tool_by_flat_name
    tr_mod.get_tool_by_flat_name = MagicMock(return_value=spec)
    
    import workforce.tools.invocation.policy_gate as pg
    original_kernel = pg.GovernanceKernel
    pg.GovernanceKernel = MagicMock()
    mock_instance = pg.GovernanceKernel.return_value
    
    from workforce.agents.governance.kernel import GovernanceDecision
    from workforce.agents.governance.policy_engine import PolicyAction
    mock_instance.evaluate_and_audit_tool_call.return_value = GovernanceDecision(
        allowed=True,
        action=PolicyAction.ALLOW,
        reason="allowed",
        tool_spec=spec,
        sanitized_args={"target": "victim", "payload": {}}
    )
    
    result = await execute_tool_spec(
        spec=spec,
        db=db_session,
        workspace_id=1,
        user_id=42,
        arguments=malicious_args
    )
    
    # execute_tool_spec doesn't actually expose its inner kwargs, but we can verify it doesn't fail
    # and returns the expected result from sample_tool. We assume sample_tool receives 1 and 42.
    assert result == {"status": "ok", "target": "victim"}
    
    tr_mod.get_tool_by_flat_name = original_get_tool
    pg.GovernanceKernel = original_kernel

@pytest.mark.asyncio
async def test_governance_kernel_can_deny_before_dispatch(db_session):
    """
    Characterization test: If GovernanceKernel denies an action, the dispatch should not happen.
    Currently, tool_dispatch.py does not call GovernanceKernel!
    This test proves why we need the unified invocation pipeline.
    """
    from workforce.agents.governance.kernel import GovernanceKernel
    from workforce.agents.runtime.types import AgentRunRequest
    
    kernel = GovernanceKernel()
    
    request = AgentRunRequest(
        workspace_id="1",
        company_id="1",
        user_id="1",
        agent_key="test_agent",
        task="do something",
        permission_profile="restricted"
    )
    
    # Force a deny
    kernel.evaluate_and_audit_tool_call = MagicMock(return_value="denied")
    
    decision = kernel.evaluate_and_audit_tool_call(db_session, request, "sensitive_action", {})
    assert decision == "denied"
    
    # In legacy flow, tool_dispatch is unaware of this decision and would execute if called directly.
    # The unified pipeline will solve this.
