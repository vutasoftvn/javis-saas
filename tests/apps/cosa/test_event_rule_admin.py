"""Task 4.5: admin create/enable EventTriggerRule, gated by can_enable_trigger."""
from types import SimpleNamespace

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from agent.evals.promotion import PromotionEvidence
from agent.evals.promotion_repository import InMemoryPromotionEvidenceRepository
from agent.governance.contracts import PinnedSpecIdentity as GovPinned
from apps.cosa.api.app import create_cosa_app
from apps.cosa.events.rule_store import InMemoryTriggerRuleStore

pytestmark = pytest.mark.asyncio

FP = {"cosa.agent": "hash_A"}


class _FP:
    async def current(self, rule):
        return dict(FP)


@pytest_asyncio.fixture
async def client():
    evidence_store = InMemoryPromotionEvidenceRepository()
    deps = SimpleNamespace(
        rule_store=InMemoryTriggerRuleStore(),
        evidence_store=evidence_store,
        fingerprint_provider=_FP(),
        trigger_policy=SimpleNamespace(policy_version="p1"),
    )
    plane = SimpleNamespace(event_intake_deps=deps)
    app = create_cosa_app(plane=plane)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        c._evidence_store = evidence_store  # type: ignore[attr-defined]
        yield c


async def _create(client, *, mode="artifact_only", evidence_ref=None, ws="ws_1"):
    r = await client.post("/agent/events/rules", json={
        "workspaceId": ws,
        "eventType": "operations.task.created.v1",
        "agentSpec": {"id": "cosa.agent", "version": "1.0.0", "definitionHash": "hash_A"},
        "mode": mode,
        "maxRunsPerAggregatePerDay": 1,
        "requiredCapabilities": [],
        "evalEvidenceRef": evidence_ref,
    })
    assert r.status_code == 201
    return r.json()["ruleId"]


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
    r = await client.post(f"/agent/events/rules/{rid}/enable", json={"workspaceId": "ws_1"})
    assert r.status_code == 200 and r.json()["status"] == "enabled"


async def test_enable_write_rule_without_evidence_denied(client):
    rid = await _create(client, mode="write", evidence_ref=None)
    r = await client.post(f"/agent/events/rules/{rid}/enable", json={"workspaceId": "ws_1"})
    assert r.status_code == 422
    assert r.json()["detail"]["reason"] == "no_eval_evidence"


async def test_enable_write_rule_with_valid_evidence_pending_then_approved(client):
    ev = await client._evidence_store.create(_evidence(boundary="write"))
    rid = await _create(client, mode="write", evidence_ref=ev.evidence_id)
    r1 = await client.post(f"/agent/events/rules/{rid}/enable", json={"workspaceId": "ws_1"})
    assert r1.status_code == 200 and r1.json()["status"] == "pending_human_approval"
    r2 = await client.post(f"/agent/events/rules/{rid}/enable",
                           json={"workspaceId": "ws_1", "approvedBy": "op_1"})
    assert r2.status_code == 200 and r2.json()["status"] == "enabled"


async def test_enable_proposal_rule_with_stale_evidence_denied(client):
    ev = await client._evidence_store.create(_evidence(fps={"cosa.agent": "hash_OLD"}, boundary="proposal"))
    rid = await _create(client, mode="proposal", evidence_ref=ev.evidence_id)
    r = await client.post(f"/agent/events/rules/{rid}/enable", json={"workspaceId": "ws_1"})
    assert r.status_code == 422 and r.json()["detail"]["reason"] == "stale_evidence"


async def test_enable_rejected_cross_workspace(client):
    rid = await _create(client, ws="ws_1")
    r = await client.post(f"/agent/events/rules/{rid}/enable", json={"workspaceId": "ws_2"})
    assert r.status_code == 404


async def test_create_and_list_engagement_write_rule(client):
    r = await client.post("/agent/events/rules", json={
        "workspaceId": "ws_eng_1",
        "eventType": "engagement.message.received.v1",
        "agentSpec": {
            "id": "cosa.agents.customer_support_autopilot",
            "version": "1.0.0",
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

    list_res = await client.get("/agent/events/rules?workspaceId=ws_eng_1")
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert any(i["ruleId"] == rule_id and i["eventType"] == "engagement.message.received.v1" and i["mode"] == "write" for i in items)
