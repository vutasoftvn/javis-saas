from __future__ import annotations

from unittest.mock import AsyncMock
import pytest

from agent.capabilities.enablements import CapabilityEnablement, InMemoryEnablementStore
from agent.capabilities.gateway import CapabilityGateway, GatewayExecutionRequest
from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.capability import CapabilityRisk, CapabilitySpec
from agent.runs.repository import InMemoryRunRepository

pytestmark = pytest.mark.integration


@pytest.fixture
def setup_gateway():
    registry = CapabilityRegistry()
    repo = InMemoryRunRepository()
    store = InMemoryEnablementStore()
    gateway = CapabilityGateway(registry=registry, repository=repo, enablement_store=store)

    # 1. B action: operations.task.create_draft
    spec_b = CapabilitySpec(
        id="operations.task.create_draft",
        description="Draft task",
        input_schema={"type": "object", "properties": {"title": {"type": "string"}}},
        risk=CapabilityRisk.MEDIUM,
        metadata={"action_class": "B"},
    )
    handler_b = AsyncMock(return_value={"id": "task-001", "status": "draft"})
    registry.register(spec_b, handler_b)

    # 2. A action: commercial.campaign_asset.write
    spec_a = CapabilitySpec(
        id="commercial.campaign_asset.write",
        description="Write campaign asset",
        input_schema={"type": "object", "properties": {"asset_name": {"type": "string"}}},
        risk=CapabilityRisk.LOW,
        metadata={"action_class": "A"},
    )
    handler_a = AsyncMock(return_value={"asset_id": "asset-001", "status": "saved"})
    registry.register(spec_a, handler_a)

    # 3. M action: finance.payout.execute (Human owned)
    spec_m = CapabilitySpec(
        id="finance.payout.execute",
        description="Execute payout",
        input_schema={"type": "object", "properties": {"amount": {"type": "number"}}},
        risk=CapabilityRisk.CRITICAL,
        metadata={"action_class": "M"},
    )
    handler_m = AsyncMock(return_value={"payout_id": "payout-001"})
    registry.register(spec_m, handler_m)

    return {
        "gateway": gateway,
        "store": store,
        "repo": repo,
        "handlers": {"b": handler_b, "a": handler_a, "m": handler_m},
    }


@pytest.mark.asyncio
async def test_growth_scale_action_matrix_execution(setup_gateway):
    gateway: CapabilityGateway = setup_gateway["gateway"]
    store: InMemoryEnablementStore = setup_gateway["store"]

    # 1. B action without enablement is DENIED
    req_b_no_enb = GatewayExecutionRequest(
        run_id="run-b1",
        capability_id="operations.task.create_draft",
        input_payload={"title": "Draft 1"},
        workspace_id="ws-c",
        principal="user-founder",
        context={"workspace_id": "ws-c", "skill_hash": "hash_ops", "action_class": "B"},
    )
    res_b_no = await gateway.execute(req_b_no_enb)
    assert res_b_no.status == "denied"
    assert "No enablement record found" in res_b_no.error_message

    # 2. B action WITH valid enablement SUCCEEDS
    await store.save_enablement(
        CapabilityEnablement(
            id="enb-b1",
            workspace_id="ws-c",
            capability_id="operations.task.create_draft",
            skill_id="operations.weekly-review",
            skill_hash="hash_ops",
            action_class="B",
            status="ENABLED",
        )
    )
    res_b_ok = await gateway.execute(req_b_no_enb)
    assert res_b_ok.status == "completed"
    assert res_b_ok.output_payload["id"] == "task-001"

    # 3. A action (Artifact) succeeds under standard tenancy without explicit enablement
    req_a = GatewayExecutionRequest(
        run_id="run-a1",
        capability_id="commercial.campaign_asset.write",
        input_payload={"asset_name": "Asset 1"},
        workspace_id="ws-c",
        principal="user-founder",
        context={"workspace_id": "ws-c", "action_class": "A"},
    )
    res_a = await gateway.execute(req_a)
    assert res_a.status == "completed"
    assert res_a.output_payload["status"] == "saved"

    # 4. M action (Money) is DENIED if no active M enablement is registered
    req_m = GatewayExecutionRequest(
        run_id="run-m1",
        capability_id="finance.payout.execute",
        input_payload={"amount": 1000},
        workspace_id="ws-c",
        principal="user-founder",
        context={"workspace_id": "ws-c", "skill_hash": "hash_fin", "action_class": "M"},
    )
    res_m = await gateway.execute(req_m)
    assert res_m.status == "denied"
    assert "No enablement record found" in res_m.error_message
