import pytest
from app.workforce.extensions.capability_bridge import CapabilityBridge
from app.workforce.agents.runtime.execution_scope import ExecutionScope
from app.workforce.extensions.seams import DiscoveredCapability

class DenyKernel:
    async def evaluate_and_audit_tool_call(self, scope, capability, arguments):
        class Result:
            status = "denied"
        return Result()

class RequireApprovalKernel:
    async def evaluate_and_audit_tool_call(self, scope, capability, arguments):
        class Result:
            status = "approval_required"
        return Result()

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
        grants=()
    )

@pytest.fixture
def capability():
    return DiscoveredCapability(capability_id="com.cosa.mcp.github:search", name="search")

@pytest.mark.asyncio
async def test_denied_mcp_call_never_invokes_provider(scope, capability):
    from unittest.mock import AsyncMock
    provider = AsyncMock()
    kernel = DenyKernel()
    bridge = CapabilityBridge()
    result = await bridge.invoke(scope, capability, {"query": "x"}, kernel, provider)
    assert result.status == "denied"
    provider.invoke.assert_not_awaited()

@pytest.mark.asyncio
async def test_approval_required_mcp_call_never_invokes_provider(scope, capability):
    from unittest.mock import AsyncMock
    provider = AsyncMock()
    kernel = RequireApprovalKernel()
    bridge = CapabilityBridge()
    result = await bridge.invoke(scope, capability, {"query": "x"}, kernel, provider)
    assert result.status == "approval_required"
    provider.invoke.assert_not_awaited()
