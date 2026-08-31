"""Task 4.5: admin create/enable EventTriggerRule, gated by can_enable_trigger."""
import logging
from types import SimpleNamespace

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from agent.evals.promotion import PromotionEvidence
from agent.evals.promotion_repository import InMemoryPromotionEvidenceRepository
from agent.governance.contracts import PinnedSpecIdentity as GovPinned
from apps.cosa.api.app import create_cosa_app
from apps.cosa.events.rule_store import InMemoryTriggerRuleStore
from tests.apps.cosa.auth_test_helpers import override_authenticated_identity

pytestmark = pytest.mark.asyncio

FP = {"cosa.agent": "hash_A"}


class _FP:
    async def current(self, rule):
        return dict(FP)


async def _make_client(*, workspace_id="ws_1", role_id="founder", platform_user_id="operator-user", authenticated=True):
    evidence_store = InMemoryPromotionEvidenceRepository()
    deps = SimpleNamespace(
        rule_store=InMemoryTriggerRuleStore(),
        evidence_store=evidence_store,
        fingerprint_provider=_FP(),
        trigger_policy=SimpleNamespace(policy_version="p1"),
    )
    plane = SimpleNamespace(event_intake_deps=deps)
    app = create_cosa_app(plane=plane)
    if authenticated:
        override_authenticated_identity(
            app,
            workspace_id=workspace_id,
            role_id=role_id,
            platform_user_id=platform_user_id,
        )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        c._evidence_store = evidence_store  # type: ignore[attr-defined]
        c._app = app  # type: ignore[attr-defined]
        yield c


@pytest_asyncio.fixture
async def client():
    async for c in _make_client():
        yield c


@pytest_asyncio.fixture
async def operator_client():
    async for c in _make_client():
        yield c


@pytest_asyncio.fixture
async def member_client():
    async for c in _make_client(role_id="member"):
        yield c


@pytest_asyncio.fixture
async def unsecured_client():
    async for c in _make_client(authenticated=False):
        yield c


def valid_rule_payload(*, mode="artifact_only", evidence_ref=None):
    return {
        "eventType": "operations.task.created.v1",
        "agentSpec": {"id": "cosa.agent", "version": "1.0.0", "definitionHash": "hash_A"},
        "mode": mode,
        "maxRunsPerAggregatePerDay": 1,
        "requiredCapabilities": [],
        "evalEvidenceRef": evidence_ref,
    }


async def _create(client, *, mode="artifact_only", evidence_ref=None, ws="ws_1"):
    r = await client.post("/agent/events/rules", json=valid_rule_payload(mode=mode, evidence_ref=evidence_ref))
    assert r.status_code == 201
    return r.json()["ruleId"]


@pytest_asyncio.fixture
async def write_rule_id(operator_client):
    ev = await operator_client._evidence_store.create(_evidence(boundary="write"))
    return await _create(operator_client, mode="write", evidence_ref=ev.evidence_id)


async def test_rule_routes_reject_missing_identity(unsecured_client):
    response = await unsecured_client.post("/agent/events/rules", json=valid_rule_payload())
    assert response.status_code == 401


async def test_member_cannot_create_or_enable_rule(member_client):
    assert (await member_client.post("/agent/events/rules", json=valid_rule_payload())).status_code == 403
    override_authenticated_identity(member_client._app, role_id="founder")  # type: ignore[attr-defined]
    created = await member_client.post("/agent/events/rules", json=valid_rule_payload())
    assert created.status_code == 201

    override_authenticated_identity(member_client._app, role_id="member")  # type: ignore[attr-defined]
    enabled = await member_client.post(f"/agent/events/rules/{created.json()['ruleId']}/enable", json={})
    assert enabled.status_code == 403


async def test_list_uses_identity_workspace_not_query(operator_client):
    response = await operator_client.get("/agent/events/rules", params={"workspaceId": "other"})
    assert response.status_code == 404


async def test_write_approval_actor_is_derived(operator_client, write_rule_id):
    response = await operator_client.post(f"/agent/events/rules/{write_rule_id}/enable", json={})
    assert response.json()["approvedBy"] == "operator-user"


def _evidence(*, passed=True, fps=None, boundary="write"):
    return PromotionEvidence(
        target_ref=GovPinned(spec_kind="agent", spec_id="cosa.agent",
                             spec_version="1.0.0", definition_hash="hash_A"),
        required_eval_run_ids=["run_1"], observed_fingerprints=dict(fps or FP),
        policy_version="p1", policy_checks_passed=passed,
        check_details={"action_boundary": boundary, "event_schema_version": 1},
    )


async def test_create_rule_is_always_disabled(client):
    rid = await _create(client)
    r = await client.get("/agent/events/rules", params={"workspaceId": "ws_1"})
    item = next(i for i in r.json()["items"] if i["ruleId"] == rid)
    assert item["enabled"] is False


async def test_enable_artifact_only_rule_succeeds(client):
    rid = await _create(client, mode="artifact_only")
    r = await client.post(f"/agent/events/rules/{rid}/enable", json={})
    assert r.status_code == 200 and r.json()["status"] == "enabled"


async def test_enable_write_rule_without_evidence_denied(client):
    rid = await _create(client, mode="write", evidence_ref=None)
    r = await client.post(f"/agent/events/rules/{rid}/enable", json={})
    assert r.status_code == 422
    assert r.json()["detail"]["reason"] == "no_eval_evidence"


async def test_enable_write_rule_with_valid_evidence_uses_authenticated_approver(client):
    ev = await client._evidence_store.create(_evidence(boundary="write"))
    rid = await _create(client, mode="write", evidence_ref=ev.evidence_id)
    r = await client.post(f"/agent/events/rules/{rid}/enable", json={})
    assert r.status_code == 200 and r.json() == {"status": "enabled", "approvedBy": "operator-user"}


async def test_enable_write_rule_with_approval_emits_audit_log(client, caplog):
    """Finding 5 (final review, human decision) — self-approval (same
    identity creates and enables a write-mode rule) has no genuine two-actor
    approval gate and won't get one (would lock out solo-founder
    workspaces). Instead, a structured application-log audit record must be
    emitted whenever a write-mode rule's human-approval gate is satisfied."""
    ev = await client._evidence_store.create(_evidence(boundary="write"))
    rid = await _create(client, mode="write", evidence_ref=ev.evidence_id)

    with caplog.at_level(logging.INFO, logger="apps.cosa.api.event_rule_routes"):
        r = await client.post(f"/agent/events/rules/{rid}/enable", json={})

    assert r.status_code == 200
    audit_records = [
        rec
        for rec in caplog.records
        if rec.message == "event trigger rule enabled with human approval"
    ]
    assert len(audit_records) == 1
    rec = audit_records[0]
    assert rec.rule_id == rid
    assert rec.workspace_id == "ws_1"
    assert rec.operator_id == "operator-user"
    assert rec.mode == "write"


async def test_enable_artifact_only_rule_does_not_emit_approval_audit_log(client, caplog):
    """Audit log is scoped to the human-approval gate only — artifact_only
    rules (no approval required) must not emit the same record."""
    rid = await _create(client, mode="artifact_only")

    with caplog.at_level(logging.INFO, logger="apps.cosa.api.event_rule_routes"):
        r = await client.post(f"/agent/events/rules/{rid}/enable", json={})

    assert r.status_code == 200
    assert not [
        rec
        for rec in caplog.records
        if rec.message == "event trigger rule enabled with human approval"
    ]


async def test_enable_proposal_rule_with_stale_evidence_denied(client):
    ev = await client._evidence_store.create(_evidence(fps={"cosa.agent": "hash_OLD"}, boundary="proposal"))
    rid = await _create(client, mode="proposal", evidence_ref=ev.evidence_id)
    r = await client.post(f"/agent/events/rules/{rid}/enable", json={})
    assert r.status_code == 422 and r.json()["detail"]["reason"] == "stale_evidence"


async def test_enable_rejected_cross_workspace(client):
    rid = await _create(client, ws="ws_1")
    override_authenticated_identity(client._app, workspace_id="ws_2")  # type: ignore[attr-defined]
    r = await client.post(f"/agent/events/rules/{rid}/enable", json={})
    assert r.status_code == 404


async def test_create_and_list_engagement_write_rule(client):
    r = await client.post("/agent/events/rules", json={
        "eventType": "engagement.message.received.v1",
        "agentSpec": {
            "id": "cosa.agents.customer_support_autopilot",
            "version": "1.1.0",
            "definitionHash": "hash_ap_1",
        },
        "mode": "write",
        "maxRunsPerAggregatePerDay": 10,
        "requiredCapabilities": ["engagement.message.send", "engagement.assignment.write"],
        "aggregateFilter": {"inbox_id": "inbox_vip_1", "intent": "faq"},
    })
    assert r.status_code == 201
    rule_id = r.json()["ruleId"]
    assert r.json()["enabled"] is False

    list_res = await client.get("/agent/events/rules")
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert any(i["ruleId"] == rule_id and i["eventType"] == "engagement.message.received.v1" and i["mode"] == "write" for i in items)
