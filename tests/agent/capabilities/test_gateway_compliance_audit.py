from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from agent.capabilities.gateway import CapabilityGateway, GatewayExecutionRequest
from agent.capabilities.registry import CapabilityRegistry
from agent.contracts.capability import CapabilitySpec
from agent.contracts.wait import WaitKind
from agent.governance.contracts import CapabilityRisk
from agent.runs.repository import InMemoryRunRepository
from apps.cosa.compliance.contracts import ComplianceSnapshot


@pytest.mark.asyncio
async def test_gateway_emits_complete_compliance_decision_event() -> None:
    registry = CapabilityRegistry()
    repo = InMemoryRunRepository()

    spec = CapabilitySpec(
        id="finance.invoice.get",
        version="1.0.0",
        risk=CapabilityRisk.LOW,
        input_schema={
            "type": "object",
            "required": ["invoice_id"],
            "properties": {"invoice_id": {"type": "string"}},
        },
    )

    def handler(payload, ctx):
        return {"invoice_id": payload["invoice_id"], "amount": 100}

    registry.register(spec, handler)
    gateway = CapabilityGateway(registry=registry, repository=repo)

    approved_snapshot = ComplianceSnapshot(
        workspace_id="ws_100",
        deployment_id="dep_100",
        assessment_id="ass_100",
        mode="ADVISORY_ONLY",
        status="APPROVED_FOR_USE",
        allowed_capabilities=frozenset(["finance.invoice.get"]),
        provider_profile_version="v3",
        data_profile_version="v1",
        provider_key="deepseek",
        model_key="deepseek-chat",
        purpose_id="advisory",
        retention_policy_id="retain-30d",
        snapshot_hash="sha256:approved_snap_123",
        policy_snapshot_hash="sha256:policy_snap_456",
        evidence_hashes=["sha256:evidence-a"],
        rule_version_ids=["134-2025-v1"],
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    # Context contains sensitive elements that MUST NOT leak into audit event
    context = {
        "workspace_id": "ws_100",
        "compliance_snapshot": approved_snapshot,
        "Authorization": "Bearer secret-token-should-not-leak",
        "company_delegation": "super-secret-delegation-token",
        "customer_email": "customer@example.com",
        "delegation_jti": "jti-uuid-777",
    }

    req = GatewayExecutionRequest(
        run_id="run_100",
        capability_id="finance.invoice.get",
        input_payload={"invoice_id": "inv_1"},
        workspace_id="ws_100",
        context=context,
    )

    res = await gateway.execute(req)
    assert res.status == "completed"

    # Verify event stored in run repository
    events = await repo.list_events("run_100")
    compliance_events = [e for e in events if e.event_type == "compliance.decision"]
    assert len(compliance_events) == 1
    event = compliance_events[0]

    # Required contract assertions (Task 9 Step 1):
    assert event.payload["snapshot_hash"] == approved_snapshot.snapshot_hash
    assert event.payload["evidence_hashes"] == ["sha256:evidence-a"]
    assert "Bearer " not in json.dumps(event.model_dump(mode="json"))
    assert "customer@example.com" not in json.dumps(event.model_dump(mode="json"))

    # Verify other required fields in Decision Event interface:
    assert event.payload["run_id"] == "run_100"
    assert event.payload["workspace_id"] == "ws_100"
    assert event.payload["deployment_id"] == "dep_100"
    assert event.payload["capability_id"] == "finance.invoice.get"
    assert event.payload["decision"] == "ALLOW"
    assert event.payload["rule_version_ids"] == ["134-2025-v1"]
    assert event.payload["delegation_jti"] == "jti-uuid-777"
    assert "timestamp" in event.payload


@pytest.mark.asyncio
async def test_gateway_denies_suspended_deployment_on_resume() -> None:
    registry = CapabilityRegistry()
    repo = InMemoryRunRepository()

    spec = CapabilitySpec(
        id="finance.invoice.get",
        version="1.0.0",
        risk=CapabilityRisk.LOW,
        input_schema={
            "type": "object",
            "required": ["invoice_id"],
            "properties": {"invoice_id": {"type": "string"}},
        },
    )

    call_count = 0

    def handler(payload, ctx):
        nonlocal call_count
        call_count += 1
        return {"invoice_id": payload["invoice_id"]}

    registry.register(spec, handler)
    gateway = CapabilityGateway(registry=registry, repository=repo)

    # Snapshot marked SUSPENDED
    suspended_snapshot = {
        "workspace_id": "ws_100",
        "deployment_id": "dep_100",
        "status": "SUSPENDED",
        "snapshot_hash": "sha256:old_snap_hash",
        "policy_snapshot_hash": "sha256:old_pol_hash",
        "evidence_hashes": [],
        "rule_version_ids": [],
    }

    req = GatewayExecutionRequest(
        run_id="run_200",
        capability_id="finance.invoice.get",
        input_payload={"invoice_id": "inv_1"},
        workspace_id="ws_100",
        context={"workspace_id": "ws_100", "compliance_snapshot": suspended_snapshot},
    )

    res = await gateway.execute(req)
    assert res.status == "denied"
    assert "suspended" in (res.error_message or "").lower()
    assert call_count == 0  # Handler was never called

    events = await repo.list_events("run_200")
    compliance_events = [e for e in events if e.event_type == "compliance.decision"]
    assert len(compliance_events) == 1
    assert compliance_events[0].payload["decision"] == "DENY"
    assert compliance_events[0].payload["reason_code"] == "DEPLOYMENT_SUSPENDED"


@pytest.mark.asyncio
async def test_gateway_handles_missing_snapshot_evidence_lists() -> None:
    """Regression (Task 8): snapshot dict thiếu hẳn `evidence_hashes`/
    `rule_version_ids` (không phải `[]`, mà KHÔNG có key) trước đây khiến
    `list(snap.get(...))` nhận `None` và raise TypeError khi build
    compliance.decision event — dù request lẽ ra phải ALLOW bình thường.
    """
    registry = CapabilityRegistry()
    repo = InMemoryRunRepository()

    spec = CapabilitySpec(
        id="finance.invoice.get",
        version="1.0.0",
        risk=CapabilityRisk.LOW,
        input_schema={
            "type": "object",
            "required": ["invoice_id"],
            "properties": {"invoice_id": {"type": "string"}},
        },
    )

    def handler(payload, ctx):
        return {"invoice_id": payload["invoice_id"]}

    registry.register(spec, handler)
    gateway = CapabilityGateway(registry=registry, repository=repo)

    # Snapshot dict KHÔNG có key evidence_hashes/rule_version_ids.
    minimal_snapshot = {
        "workspace_id": "ws_100",
        "deployment_id": "dep_100",
        "status": "APPROVED_FOR_USE",
        "snapshot_hash": "sha256:minimal_snap_hash",
        "policy_snapshot_hash": "sha256:minimal_pol_hash",
    }

    req = GatewayExecutionRequest(
        run_id="run_300",
        capability_id="finance.invoice.get",
        input_payload={"invoice_id": "inv_1"},
        workspace_id="ws_100",
        context={"workspace_id": "ws_100", "compliance_snapshot": minimal_snapshot},
    )

    res = await gateway.execute(req)
    assert res.status == "completed"

    events = await repo.list_events("run_300")
    compliance_events = [e for e in events if e.event_type == "compliance.decision"]
    assert len(compliance_events) == 1
    assert compliance_events[0].payload["evidence_hashes"] == []
    assert compliance_events[0].payload["rule_version_ids"] == []
