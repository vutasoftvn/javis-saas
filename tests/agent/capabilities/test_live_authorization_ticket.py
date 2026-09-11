from __future__ import annotations

import pytest

from agent.capabilities.gateway import (
    CapabilityGateway,
    GatewayExecutionRequest,
)
from agent.capabilities.outbound_headers import get_outbound_headers
from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.capability import CapabilitySpec
from agent.contracts.wait import WaitKind
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk
from agent.runs.repository import InMemoryRunRepository
from apps.cosa.authorization.live_authorizer import (
    LiveAuthorizationAuthorizer,
    LiveAuthorizationResult,
)


class FakeLiveAuthorizer(LiveAuthorizationAuthorizer):
    def __init__(self, grants_status: dict[str, str] | None = None) -> None:
        super().__init__(company_client=None)
        self.grants_status = grants_status or {}
        self.calls: list[dict] = []

    async def authorize(self, req: GatewayExecutionRequest, spec: CapabilitySpec) -> LiveAuthorizationResult:
        self.calls.append({"req": req, "spec": spec})
        grant_id = req.context.get("agent_capability_grant_id")
        status = self.grants_status.get(grant_id, "ACTIVE")
        if status == "REVOKED":
            return LiveAuthorizationResult(
                allowed=False,
                error_message="AGENT_CAPABILITY_GRANT_REVOKED: grant has been revoked by founder",
            )
        return LiveAuthorizationResult(
            allowed=True,
            ticket_id="tkt_test_12345",
            epoch=1,
            expires_at="2026-09-11T12:00:00Z",
        )


@pytest.mark.asyncio
async def test_revoked_grant_after_dispatch_cannot_obtain_ticket():
    registry = CapabilityRegistry()
    repo = InMemoryRunRepository()

    write_spec = CapabilitySpec(
        id="finance.transaction.record",
        version="1.0.0",
        risk=CapabilityRisk.LOW,
        approval_policy=ApprovalPolicy.NEVER,
        metadata={"risk_class": "FINANCIAL"},
        input_schema={
            "type": "object",
            "required": ["amount"],
            "properties": {"amount": {"type": "number"}},
        },
    )

    executed = False

    def write_handler(payload, ctx):
        nonlocal executed
        executed = True
        return {"recorded": True}

    registry.register(write_spec, write_handler)

    authorizer = FakeLiveAuthorizer(grants_status={"grant-77": "ACTIVE"})
    gateway = CapabilityGateway(
        registry=registry,
        repository=repo,
        live_authorizer=authorizer,
    )

    req = GatewayExecutionRequest(
        run_id="run-7",
        capability_id="finance.transaction.record",
        input_payload={"amount": 500},
        workspace_id="ws-1",
        context={
            "workspace_id": "ws-1",
            "agent_workforce_member_id": "99",
            "agent_capability_grant_id": "grant-77",
        },
    )

    # Revoke grant before execution
    authorizer.grants_status["grant-77"] = "REVOKED"

    result = await gateway.execute(req)
    assert result.status == "denied"
    assert "AGENT_CAPABILITY_GRANT_REVOKED" in (result.error_message or "")
    assert not executed


@pytest.mark.asyncio
async def test_revocation_blocks_resuming_after_approval():
    registry = CapabilityRegistry()
    repo = InMemoryRunRepository()

    write_spec = CapabilitySpec(
        id="finance.payout.execute",
        version="1.0.0",
        risk=CapabilityRisk.HIGH,
        metadata={"risk_class": "FINANCIAL"},
        input_schema={"type": "object"},
    )

    def write_handler(payload, ctx):
        return {"paid": True}

    registry.register(write_spec, write_handler)

    authorizer = FakeLiveAuthorizer(grants_status={"grant-payout": "ACTIVE"})
    gateway = CapabilityGateway(
        registry=registry,
        repository=repo,
        live_authorizer=authorizer,
    )

    req = GatewayExecutionRequest(
        run_id="run-payout",
        capability_id="finance.payout.execute",
        input_payload={},
        workspace_id="ws-1",
        context={
            "workspace_id": "ws-1",
            "agent_workforce_member_id": "99",
            "agent_capability_grant_id": "grant-payout",
        },
    )

    # 1. Step 8 -> waiting_approval
    res1 = await gateway.execute(req)
    assert res1.status == "waiting_approval"
    assert res1.wait_descriptor is not None

    # 2. Reviewer approves
    appr_id = res1.wait_descriptor.related_ref
    await repo.decide_approval(appr_id, reviewer="founder_1", approved=True)

    # 3. Founder revokes grant BEFORE resume
    authorizer.grants_status["grant-payout"] = "REVOKED"

    # 4. Resume execution -> denied at Step 8.8
    res2 = await gateway.execute(req)
    assert res2.status == "denied"
    assert "AGENT_CAPABILITY_GRANT_REVOKED" in (res2.error_message or "")


@pytest.mark.asyncio
async def test_active_grant_obtains_ticket_and_attaches_to_context_and_outbound():
    registry = CapabilityRegistry()
    repo = InMemoryRunRepository()

    write_spec = CapabilitySpec(
        id="finance.transaction.record",
        version="1.0.0",
        risk=CapabilityRisk.LOW,
        approval_policy=ApprovalPolicy.NEVER,
        metadata={"risk_class": "FINANCIAL"},
        input_schema={"type": "object"},
    )

    observed_ticket_in_ctx = None
    observed_ticket_in_headers = None

    def write_handler(payload, ctx):
        nonlocal observed_ticket_in_ctx, observed_ticket_in_headers
        observed_ticket_in_ctx = ctx.get("authorization_ticket_id")
        observed_ticket_in_headers = get_outbound_headers().get("X-Cosa-Authorization-Ticket")
        return {"success": True}

    registry.register(write_spec, write_handler)

    authorizer = FakeLiveAuthorizer(grants_status={"grant-88": "ACTIVE"})
    gateway = CapabilityGateway(
        registry=registry,
        repository=repo,
        live_authorizer=authorizer,
    )

    req = GatewayExecutionRequest(
        run_id="run-8",
        capability_id="finance.transaction.record",
        input_payload={},
        workspace_id="ws-1",
        context={
            "workspace_id": "ws-1",
            "agent_workforce_member_id": "99",
            "agent_capability_grant_id": "grant-88",
        },
    )

    result = await gateway.execute(req)
    assert result.status == "completed"
    assert observed_ticket_in_ctx == "tkt_test_12345"
    assert observed_ticket_in_headers == "tkt_test_12345"


@pytest.mark.asyncio
async def test_read_capability_skips_live_ticket():
    registry = CapabilityRegistry()
    repo = InMemoryRunRepository()

    read_spec = CapabilitySpec(
        id="operations.task.list",
        version="1.0.0",
        risk=CapabilityRisk.LOW,
        metadata={"risk_class": "READ"},
        input_schema={"type": "object"},
    )

    def read_handler(payload, ctx):
        return {"tasks": []}

    registry.register(read_spec, read_handler)

    authorizer = FakeLiveAuthorizer()
    gateway = CapabilityGateway(
        registry=registry,
        repository=repo,
        live_authorizer=authorizer,
    )

    req = GatewayExecutionRequest(
        run_id="run-9",
        capability_id="operations.task.list",
        input_payload={},
        workspace_id="ws-1",
        context={
            "workspace_id": "ws-1",
            "agent_workforce_member_id": "99",
        },
    )

    result = await gateway.execute(req)
    assert result.status == "completed"
    assert len(authorizer.calls) == 0
