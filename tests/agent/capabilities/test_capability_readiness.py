"""Tests for Capability Readiness Checking & Gateway Integration (Phase 4).

Theo Hermes/LangGraph Integration Plan §3, Phase 4:
- Test 1: Readiness CONNECTOR_OFFLINE + Governance ALLOW -> Proceed with warning (governance decides).
- Test 2: Readiness READY + Governance DENY -> Blocked by governance, proving Readiness != Authorization.
- Test 3: Readiness MISSING_CREDENTIAL -> Blocked by gateway readiness check.
"""

from __future__ import annotations

import pytest

from agent.contracts.capability import (
    CapabilityReadiness,
    CapabilityReadinessReason,
    CapabilitySpec,
)
from agent.governance.contracts import CapabilityRisk, PolicyDecision, PolicyOutcome
from agent.capabilities.gateway import (
    CapabilityGateway,
    GatewayExecutionRequest,
)
from agent.capabilities.readiness import RegistryCapabilityReadinessChecker
from agent.capabilities.registry import CapabilityRegistry
from agent.runs.repository import InMemoryRunRepository


@pytest.fixture
def test_registry():
    reg = CapabilityRegistry()
    
    # Capability 1: Operations Task Read
    reg.register(
        CapabilitySpec(
            id="operations.task.read",
            description="Read task details",
            risk=CapabilityRisk.LOW,
            input_schema={"type": "object", "properties": {"task_id": {"type": "string"}}},
            connector_requirements={"connector_id": "operations_service"},
        ),
        handler=lambda payload, ctx: {"status": "success", "data": {"task_id": payload.get("task_id"), "title": "Done"}},
    )

    # Capability 2: Finance Invoice Send
    reg.register(
        CapabilitySpec(
            id="finance.invoice.send",
            description="Send invoice to customer",
            risk=CapabilityRisk.LOW,
            input_schema={"type": "object", "properties": {"invoice_id": {"type": "string"}}},
            connector_requirements={"connector_id": "quickbooks_connector"},
        ),
        handler=lambda payload, ctx: {"status": "success", "sent": True},
    )

    return reg


@pytest.mark.asyncio
async def test_readiness_connector_offline_with_governance_allow(test_registry, caplog):
    """Test 1: CONNECTOR_OFFLINE + ALLOW -> Proceed with warning, not blocked."""
    checker = RegistryCapabilityReadinessChecker(
        test_registry,
        connector_health_override={"quickbooks_connector": CapabilityReadinessReason.CONNECTOR_OFFLINE},
    )
    
    # Governance evaluator returns ALLOW
    def mock_policy(capability_id, payload, context):
        return PolicyDecision(outcome=PolicyOutcome.ALLOW, reason="Policy allows task")

    gateway = CapabilityGateway(
        registry=test_registry,
        repository=InMemoryRunRepository(),
        policy_evaluator=mock_policy,
        readiness_checker=checker,
    )

    req = GatewayExecutionRequest(
        run_id="run_test_offline",
        capability_id="finance.invoice.send",
        input_payload={"invoice_id": "inv_1001"},
        workspace_id="ws_ready",
    )

    res = await gateway.execute(req)
    # Governance allows -> execution completes despite connector offline warning
    assert res.status == "completed"
    assert res.output_payload == {"status": "success", "sent": True}
    assert "is offline. Proceeding with warning" in caplog.text


@pytest.mark.asyncio
async def test_readiness_ready_with_governance_deny(test_registry):
    """Test 2: READY + DENY -> Blocked by governance, proving Readiness != Authorization."""
    checker = RegistryCapabilityReadinessChecker(
        test_registry,
        connector_health_override={"operations.task.read": CapabilityReadinessReason.READY},
    )

    # Governance evaluator returns DENY
    def mock_policy(capability_id, payload, context):
        return PolicyDecision(outcome=PolicyOutcome.DENY, reason="Tenant suspended")

    gateway = CapabilityGateway(
        registry=test_registry,
        repository=InMemoryRunRepository(),
        policy_evaluator=mock_policy,
        readiness_checker=checker,
    )

    req = GatewayExecutionRequest(
        run_id="run_test_deny",
        capability_id="operations.task.read",
        input_payload={"task_id": "task_99"},
        workspace_id="ws_ready",
    )

    res = await gateway.execute(req)
    assert res.status == "denied"
    assert "denied by policy" in (res.error_message or "").lower()


@pytest.mark.asyncio
async def test_readiness_missing_credential_blocks_execution(test_registry):
    """Test 3: MISSING_CREDENTIAL -> Explicitly blocked by readiness check before policy."""
    checker = RegistryCapabilityReadinessChecker(
        test_registry,
        connector_health_override={"finance.invoice.send": CapabilityReadinessReason.MISSING_CREDENTIAL},
    )

    gateway = CapabilityGateway(
        registry=test_registry,
        repository=InMemoryRunRepository(),
        policy_evaluator=lambda c, p, ctx: PolicyDecision(outcome=PolicyOutcome.ALLOW),
        readiness_checker=checker,
    )

    req = GatewayExecutionRequest(
        run_id="run_test_missing_cred",
        capability_id="finance.invoice.send",
        input_payload={"invoice_id": "inv_2002"},
        workspace_id="ws_ready",
    )

    res = await gateway.execute(req)
    assert res.status == "failed"
    assert "missing credential" in (res.error_message or "").lower()


@pytest.mark.asyncio
async def test_readiness_probes_company_client_health(test_registry):
    """Test company_client health probe detects offline service."""
    from unittest.mock import AsyncMock

    mock_client = AsyncMock()
    mock_client.health_check = AsyncMock(return_value=False)

    reg = CapabilityRegistry()
    reg.register(
        CapabilitySpec(
            id="company.employee.list",
            description="List employees",
            risk=CapabilityRisk.LOW,
            input_schema={"type": "object"},
            connector_requirements={"connector_id": "operations"},
        ),
        handler=lambda p, ctx: {"status": "ok"},
    )

    checker = RegistryCapabilityReadinessChecker(reg, company_client=mock_client)
    res = await checker.check("company.employee.list")
    assert res.ready is False
    assert res.reason_code == CapabilityReadinessReason.CONNECTOR_OFFLINE

