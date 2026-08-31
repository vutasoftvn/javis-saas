from __future__ import annotations

import pytest
from agent.capabilities.gateway import GatewayExecutionRequest
from agent.capabilities.gateway_internals import TenancyVerifier
from agent.contracts.capability import CapabilitySpec
from agent.contracts.errors import TenancyUnresolvedError
from agent.governance.contracts import CapabilityRisk


@pytest.fixture
def tenancy_verifier():
    return TenancyVerifier()


@pytest.mark.asyncio
async def test_tenancy_verifier_high_risk_requires_workspace(tenancy_verifier):
    """HIGH-risk capability without workspace raises TenancyUnresolvedError."""
    spec = CapabilitySpec(
        id="test.high_risk",
        version="1.0.0",
        risk=CapabilityRisk.HIGH,
    )
    req = GatewayExecutionRequest(
        run_id="run_1",
        capability_id="test.high_risk",
        input_payload={},
        workspace_id=None,
        principal="user_1",
    )

    with pytest.raises(TenancyUnresolvedError):
        await tenancy_verifier.verify(spec, req)


@pytest.mark.asyncio
async def test_tenancy_verifier_high_risk_requires_principal(tenancy_verifier):
    """HIGH-risk capability without principal raises TenancyUnresolvedError."""
    spec = CapabilitySpec(
        id="test.high_risk",
        version="1.0.0",
        risk=CapabilityRisk.HIGH,
    )
    req = GatewayExecutionRequest(
        run_id="run_1",
        capability_id="test.high_risk",
        input_payload={},
        workspace_id="ws_1",
        principal=None,
    )

    with pytest.raises(TenancyUnresolvedError):
        await tenancy_verifier.verify(spec, req)


@pytest.mark.asyncio
async def test_tenancy_verifier_rejects_default_workspace(tenancy_verifier):
    """Tenancy check rejects 'default' or 'default_workspace' sentinel values."""
    spec = CapabilitySpec(
        id="test.high_risk",
        version="1.0.0",
        risk=CapabilityRisk.HIGH,
    )
    req = GatewayExecutionRequest(
        run_id="run_1",
        capability_id="test.high_risk",
        input_payload={},
        workspace_id="default_workspace",
        principal="user_1",
    )

    with pytest.raises(TenancyUnresolvedError):
        await tenancy_verifier.verify(spec, req)


@pytest.mark.asyncio
async def test_tenancy_verifier_low_risk_no_workspace_required(tenancy_verifier):
    """LOW-risk capability does not require workspace."""
    spec = CapabilitySpec(
        id="test.low_risk",
        version="1.0.0",
        risk=CapabilityRisk.LOW,
    )
    req = GatewayExecutionRequest(
        run_id="run_1",
        capability_id="test.low_risk",
        input_payload={},
        workspace_id=None,
    )

    ws, principal = await tenancy_verifier.verify(spec, req)
    assert ws == ""
    # GatewayExecutionRequest defaults `principal` to "system" khi không truyền
    # (không phải None) — LOW-risk không cần tenancy nên giá trị mặc định này
    # được trả nguyên vẹn, không bị verifier ép về rỗng.
    assert principal == "system"


@pytest.mark.asyncio
async def test_tenancy_verifier_fallback_from_context_dict(tenancy_verifier):
    """Tenancy verifier falls back to context dict for workspace/principal."""
    spec = CapabilitySpec(
        id="test.high_risk",
        version="1.0.0",
        risk=CapabilityRisk.HIGH,
    )
    req = GatewayExecutionRequest(
        run_id="run_1",
        capability_id="test.high_risk",
        input_payload={},
        context={"workspace_id": "ws_from_ctx", "principal": "user_from_ctx"},
    )

    ws, principal = await tenancy_verifier.verify(spec, req)
    assert ws == "ws_from_ctx"
    assert principal == "user_from_ctx"


@pytest.mark.asyncio
async def test_tenancy_verifier_explicit_req_overrides_context(tenancy_verifier):
    """Explicit workspace/principal in request overrides context."""
    spec = CapabilitySpec(
        id="test.high_risk",
        version="1.0.0",
        risk=CapabilityRisk.HIGH,
    )
    req = GatewayExecutionRequest(
        run_id="run_1",
        capability_id="test.high_risk",
        input_payload={},
        workspace_id="ws_req",
        principal="user_req",
        context={"workspace_id": "ws_ctx", "principal": "user_ctx"},
    )

    ws, principal = await tenancy_verifier.verify(spec, req)
    assert ws == "ws_req"
    assert principal == "user_req"
