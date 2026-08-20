from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.tool_registry import ToolSpec
from app.workforce.agents.governance.kernel import GovernanceDecision
from app.workforce.agents.governance.policy_engine import PolicyAction
from app.workforce.agents.runtime.execution_scope import ExecutionScope
from app.workforce.extensions.capability_bridge import CapabilityBridge
from app.workforce.extensions.seams import DiscoveredCapability, ProviderResult
from app.workforce.tools.invocation.contracts import ToolInvocationRequest

@pytest.fixture
def scope():
    return ExecutionScope(
        workspace_id=101,
        company_id=101,
        principal_user_id=1,
        principal_member_id=1,
        principal_role="owner",
        operating_unit_id=None,
        offering_id=None,
        initiative_id=None,
        profile_id=None,
        session_id=None,
        grants=(),
    )

@pytest.fixture
def capability():
    return DiscoveredCapability(
        capability_id="com.cosa.mcp.github:search",
        name="search",
        input_schema={"type": "object"},
        endpoint_config={"endpoint": "https://mcp.test/rpc"},
    )


@pytest.fixture
def tool_spec():
    return ToolSpec(
        namespace="com_cosa_mcp_github",
        name="search",
        callable=lambda: None,
        execution_backend="connector",
        backend_id="com.cosa.mcp.github",
    )


@pytest.fixture
def invocation_request(scope):
    return ToolInvocationRequest(
        scope=scope,
        tool_flat_name="com_cosa_mcp_github_search",
        arguments={"query": "Ada"},
        source="test",
    )

@pytest.mark.asyncio
async def test_denied_connector_never_invokes_provider(
    invocation_request, capability, tool_spec
):
    decision = GovernanceDecision(
        allowed=False,
        action=PolicyAction.DENY,
        reason="not authorized",
        tool_spec=tool_spec,
        sanitized_args=invocation_request.arguments,
    )
    provider = AsyncMock()

    with patch(
        "app.workforce.extensions.capability_bridge.GovernanceKernel.evaluate_and_audit_tool_call",
        return_value=decision,
    ) as evaluate:
        result = await CapabilityBridge().invoke(
            MagicMock(),
            invocation_request.scope,
            invocation_request,
            None,
            capability,
            provider,
        )

    assert result == {"status": "blocked", "error": "not authorized"}
    evaluate.assert_called_once()
    provider.invoke.assert_not_awaited()


@pytest.mark.asyncio
async def test_approval_required_connector_never_invokes_provider(
    invocation_request, capability, tool_spec
):
    approval = MagicMock(id=4321)
    decision = GovernanceDecision(
        allowed=False,
        action=PolicyAction.REQUIRE_APPROVAL,
        reason="operator approval required",
        tool_spec=tool_spec,
        approval=approval,
        sanitized_args=invocation_request.arguments,
    )
    provider = AsyncMock()

    result = await CapabilityBridge().invoke(
        MagicMock(),
        invocation_request.scope,
        invocation_request,
        None,
        capability,
        provider,
        decision,
    )

    assert result == {
        "status": "awaiting_approval",
        "approval_id": "4321",
        "tool_name": tool_spec.qualified_name,
        "message": "operator approval required",
    }
    provider.invoke.assert_not_awaited()


@pytest.mark.asyncio
async def test_allowed_connector_reuses_decision_and_passes_full_capability(
    invocation_request, capability, tool_spec
):
    decision = GovernanceDecision(
        allowed=True,
        action=PolicyAction.ALLOW,
        reason="allowed",
        tool_spec=tool_spec,
        sanitized_args={"query": "sanitized"},
    )
    provider = AsyncMock()
    provider.invoke.return_value = ProviderResult(
        status="success", result={"matches": ["Ada"]}
    )

    with patch(
        "app.workforce.extensions.capability_bridge.GovernanceKernel.evaluate_and_audit_tool_call"
    ) as evaluate:
        result = await CapabilityBridge().invoke(
            MagicMock(),
            invocation_request.scope,
            invocation_request,
            99,
            capability,
            provider,
            decision,
        )

    assert result == ProviderResult(status="success", result={"matches": ["Ada"]})
    evaluate.assert_not_called()
    provider.invoke.assert_awaited_once_with(
        invocation_request.scope, capability, {"query": "sanitized"}
    )
