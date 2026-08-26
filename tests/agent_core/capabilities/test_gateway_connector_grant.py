from __future__ import annotations

import pytest

from agent_core.contracts.capability import CapabilitySpec
from agent_core.governance.contracts import CapabilityRisk
from agent_core.capabilities.gateway import CapabilityGateway, GatewayExecutionRequest
from agent_core.capabilities.grants import ConnectorGrant
from agent_core.capabilities.registry import CapabilityRegistry
from agent_core.runs.repository import InMemoryRunRepository


def _mcp_read_spec() -> CapabilitySpec:
    return CapabilitySpec(
        id="mcp.sandbox_read.list_items",
        risk=CapabilityRisk.MEDIUM,
        connector_requirements={"connector_id": "sandbox-read"},
    )


@pytest.fixture
def gateway_with_grant(monkeypatch):
    registry = CapabilityRegistry()
    repo = InMemoryRunRepository()
    call_counts = {"n": 0}

    def handler(payload, ctx):
        call_counts["n"] += 1
        return {"items": []}

    registry.register(_mcp_read_spec(), handler)

    state = {"grant": ConnectorGrant(
        grant_id="grant_1", tenant_id="ws_a", principal="user_a",
        connector_id="sandbox-read", allowed_actions=("mcp.sandbox_read.*",), is_revoked=False,
    )}

    async def resolver(connector_id, req):
        return state["grant"]

    gateway = CapabilityGateway(registry=registry, repository=repo, connector_grant_resolver=resolver)
    return gateway, repo, call_counts, state


@pytest.mark.asyncio
async def test_execute_denied_when_connector_grant_revoked(gateway_with_grant):
    gateway, repo, call_counts, state = gateway_with_grant
    state["grant"] = state["grant"].model_copy(update={"is_revoked": True})

    req = GatewayExecutionRequest(
        run_id="run_1", capability_id="mcp.sandbox_read.list_items",
        input_payload={}, workspace_id="ws_a", principal="user_a",
    )
    res = await gateway.execute(req)

    assert res.status == "denied"
    assert call_counts["n"] == 0


@pytest.mark.asyncio
async def test_execute_allowed_when_connector_grant_valid(gateway_with_grant):
    gateway, repo, call_counts, state = gateway_with_grant

    req = GatewayExecutionRequest(
        run_id="run_2", capability_id="mcp.sandbox_read.list_items",
        input_payload={}, workspace_id="ws_a", principal="user_a",
    )
    res = await gateway.execute(req)

    assert res.status == "completed"
    assert call_counts["n"] == 1


@pytest.mark.asyncio
async def test_resume_after_approval_rechecks_grant_and_denies_if_revoked_meanwhile():
    """Capability HIGH risk + connector_requirements -> lần gọi 1 waiting_approval,
    approve, nhưng grant bị revoke TRƯỚC lần gọi 2 (resume) -> resume phải denied,
    không thực thi handler. Đây là bằng chứng trực tiếp cho yêu cầu re-check tại
    thời điểm side effect, không chỉ tại dispatch ban đầu."""
    registry = CapabilityRegistry()
    repo = InMemoryRunRepository()
    call_counts = {"n": 0}

    def handler(payload, ctx):
        call_counts["n"] += 1
        return {"ok": True}

    spec = CapabilitySpec(
        id="mcp.sandbox_write.dangerous_action",
        risk=CapabilityRisk.HIGH,
        connector_requirements={"connector_id": "sandbox-write"},
    )
    registry.register(spec, handler)

    state = {"grant": ConnectorGrant(
        grant_id="grant_2", tenant_id="ws_a", principal="user_a",
        connector_id="sandbox-write", allowed_actions=("*",), is_revoked=False,
    )}

    async def resolver(connector_id, req):
        return state["grant"]

    gateway = CapabilityGateway(registry=registry, repository=repo, connector_grant_resolver=resolver)

    req = GatewayExecutionRequest(
        run_id="run_3", capability_id="mcp.sandbox_write.dangerous_action",
        input_payload={}, workspace_id="ws_a", principal="user_a",
        tool_call_id="call_resume_1", checkpoint_ref="ckpt_resume_1",
    )

    res1 = await gateway.execute(req)
    assert res1.status == "waiting_approval"

    await repo.decide_approval(res1.wait_descriptor.related_ref, reviewer="founder_1", approved=True)

    # Grant bị revoke SAU khi approve, TRƯỚC khi resume
    state["grant"] = state["grant"].model_copy(update={"is_revoked": True})

    res2 = await gateway.execute(req)
    assert res2.status == "denied"
    assert call_counts["n"] == 0
