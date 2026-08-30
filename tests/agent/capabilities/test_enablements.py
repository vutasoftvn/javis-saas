from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
import pytest

from agent.capabilities.enablements import (
    CapabilityEnablement,
    InMemoryEnablementStore,
    assert_enabled_for_invocation,
)
from agent.capabilities.gateway import CapabilityGateway, GatewayExecutionRequest
from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.capability import CapabilityRisk, CapabilitySpec
from agent.runs.repository import InMemoryRunRepository


@pytest.fixture
def test_registry():
    registry = CapabilityRegistry()
    spec = CapabilitySpec(
        id="operations.task.create_draft",
        description="Draft an internal task",
        input_schema={"type": "object", "properties": {"title": {"type": "string"}}},
        risk=CapabilityRisk.MEDIUM,
        metadata={"action_class": "B"},
    )
    handler = AsyncMock(return_value={"id": "task-123", "status": "draft"})
    registry.register(spec, handler)
    return registry


@pytest.mark.asyncio
async def test_enablement_store_matrix(test_registry):
    store = InMemoryEnablementStore()
    repo = InMemoryRunRepository()
    gateway = CapabilityGateway(registry=test_registry, repository=repo, enablement_store=store)

    # 1. Register enablement for ws-a, skill_hash='abc', action_class='B'
    enb = CapabilityEnablement(
        id="enb-1",
        workspace_id="ws-a",
        capability_id="operations.task.create_draft",
        skill_id="operations.task-manager",
        skill_hash="abc",
        action_class="B",
        status="ENABLED",
    )
    await store.save_enablement(enb)

    # 2. Matching request succeeds
    req_match = GatewayExecutionRequest(
        run_id="run-1",
        capability_id="operations.task.create_draft",
        input_payload={"title": "Review metrics"},
        workspace_id="ws-a",
        principal="user-founder",
        context={"workspace_id": "ws-a", "skill_hash": "abc", "action_class": "B"},
    )
    res_match = await gateway.execute(req_match)
    assert res_match.status == "completed"
    assert res_match.output_payload["id"] == "task-123"

    # 3. Wrong workspace -> denied
    req_wrong_ws = GatewayExecutionRequest(
        run_id="run-2",
        capability_id="operations.task.create_draft",
        input_payload={"title": "Review metrics"},
        workspace_id="ws-b",
        principal="user-founder",
        context={"workspace_id": "ws-b", "skill_hash": "abc", "action_class": "B"},
    )
    res_wrong_ws = await gateway.execute(req_wrong_ws)
    assert res_wrong_ws.status == "denied"
    assert "No enablement record found" in res_wrong_ws.error_message

    # 4. Wrong skill_hash -> denied
    req_wrong_hash = GatewayExecutionRequest(
        run_id="run-3",
        capability_id="operations.task.create_draft",
        input_payload={"title": "Review metrics"},
        workspace_id="ws-a",
        principal="user-founder",
        context={"workspace_id": "ws-a", "skill_hash": "changed", "action_class": "B"},
    )
    res_wrong_hash = await gateway.execute(req_wrong_hash)
    assert res_wrong_hash.status == "denied"
    assert "No enablement record found" in res_wrong_hash.error_message

    # 5. Wrong action_class -> denied
    req_wrong_action = GatewayExecutionRequest(
        run_id="run-4",
        capability_id="operations.task.create_draft",
        input_payload={"title": "Review metrics"},
        workspace_id="ws-a",
        principal="user-founder",
        context={"workspace_id": "ws-a", "skill_hash": "abc", "action_class": "X"},
    )
    res_wrong_action = await gateway.execute(req_wrong_action)
    assert res_wrong_action.status == "denied"
    assert "No enablement record found" in res_wrong_action.error_message


@pytest.mark.asyncio
async def test_expired_and_revoked_enablement_fails_closed(test_registry):
    store = InMemoryEnablementStore()
    repo = InMemoryRunRepository()
    gateway = CapabilityGateway(registry=test_registry, repository=repo, enablement_store=store)

    # 1. Expired enablement
    expired_enb = CapabilityEnablement(
        id="enb-expired",
        workspace_id="ws-a",
        capability_id="operations.task.create_draft",
        skill_id="operations.task-manager",
        skill_hash="abc",
        action_class="B",
        status="ENABLED",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    await store.save_enablement(expired_enb)

    req_expired = GatewayExecutionRequest(
        run_id="run-expired",
        capability_id="operations.task.create_draft",
        input_payload={"title": "Review metrics"},
        workspace_id="ws-a",
        principal="user-founder",
        context={"workspace_id": "ws-a", "skill_hash": "abc", "action_class": "B"},
    )
    res_expired = await gateway.execute(req_expired)
    assert res_expired.status == "denied"
    assert "not active" in res_expired.error_message

    # Verify audit event emitted and NO tool started / completed event
    events = await repo.list_events("run-expired")
    event_types = [e.event_type for e in events]
    assert "capability.enablement_denied" in event_types
    assert "tool.started" not in event_types
    assert "tool.completed" not in event_types

    # 2. Revoked enablement
    revoked_enb = CapabilityEnablement(
        id="enb-revoked",
        workspace_id="ws-a",
        capability_id="operations.task.create_draft",
        skill_id="operations.task-manager",
        skill_hash="xyz",
        action_class="B",
        status="REVOKED",
    )
    await store.save_enablement(revoked_enb)

    req_revoked = GatewayExecutionRequest(
        run_id="run-revoked",
        capability_id="operations.task.create_draft",
        input_payload={"title": "Review metrics"},
        workspace_id="ws-a",
        principal="user-founder",
        context={"workspace_id": "ws-a", "skill_hash": "xyz", "action_class": "B"},
    )
    res_revoked = await gateway.execute(req_revoked)
    assert res_revoked.status == "denied"
    assert "not active" in res_revoked.error_message


@pytest.mark.asyncio
async def test_read_and_artifact_actions_pass_without_explicit_enablement(test_registry):
    store = InMemoryEnablementStore()
    repo = InMemoryRunRepository()
    gateway = CapabilityGateway(registry=test_registry, repository=repo, enablement_store=store)

    # Register read capability
    read_spec = CapabilitySpec(
        id="analytics.metric_contract.get",
        description="Get metric contract",
        input_schema={"type": "object", "properties": {}},
        risk=CapabilityRisk.LOW,
        metadata={"action_class": "R"},
    )
    read_handler = AsyncMock(return_value={"contracts": []})
    test_registry.register(read_spec, read_handler)

    req_read = GatewayExecutionRequest(
        run_id="run-read",
        capability_id="analytics.metric_contract.get",
        input_payload={},
        workspace_id="ws-a",
        principal="user-founder",
        context={"workspace_id": "ws-a", "action_class": "R"},
    )
    res_read = await gateway.execute(req_read)
    assert res_read.status == "completed"
    assert res_read.output_payload == {"contracts": []}
