from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlparse

import pytest
from httpx import ASGITransport, AsyncClient

from apps.cosa.api.app import create_cosa_app
from apps.cosa.composition.agent_plane import CosaAgentPlane, build_cosa_agent_plane
from apps.cosa.events.router import Unauthenticated, handle_event
from apps.cosa.events.trigger_policy import EventTriggerRule, PinnedSpecIdentity

SECRET = "test-secret"
CONSUMER = "agentos.event_intake"


def _raw(payload: dict) -> bytes:
    # Phải khớp byte-exact với cách httpx serialize body khi gọi `json=payload`
    # (ensure_ascii=False, separators không space) để chữ ký HMAC verify được.
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _sig(payload: dict, secret: str = SECRET) -> dict[str, str]:
    sig = hmac.new(secret.encode("utf-8"), _raw(payload), hashlib.sha256).hexdigest()
    return {"X-COSA-Local-Signature": sig}


def _env(
    workspace_id: str = "ws_1",
    event_type: str = "operations.task.created.v1",
    aggregate_id: str = "t_1",
    correlation_id: str = "corr_1",
) -> dict:
    return {
        "eventId": str(uuid.uuid4()),
        "eventType": event_type,
        "schemaVersion": 1,
        "occurredAt": "2026-08-28T10:00:00.000Z",
        "workspaceId": workspace_id,
        "aggregateType": "task",
        "aggregateId": aggregate_id,
        "correlationId": correlation_id,
        "actor": {"kind": "system", "id": "relay"},
        "producer": {"service": "company.operations", "version": "1.0.0"},
        "classification": "internal",
        "payload": {
            "taskId": aggregate_id,
            "workspaceId": workspace_id,
            "title": "Test Task",
            "status": "todo",
        },
    }


class InMemoryTriggerRuleStore:
    def __init__(self, rules: Optional[List[EventTriggerRule]] = None) -> None:
        self.rules: Dict[tuple[str, str], EventTriggerRule] = {}
        for r in rules or []:
            self.rules[(r.workspace_id, r.event_type)] = r

    async def find(self, workspace_id: str, event_type: str, aggregate: dict) -> Optional[EventTriggerRule]:
        return self.rules.get((workspace_id, event_type))


class InMemoryRunCounter:
    def __init__(self) -> None:
        self.counts: Dict[tuple[str, str, str], int] = {}

    async def today(self, workspace_id: str, rule_id: str, aggregate_id: str) -> int:
        return self.counts.get((workspace_id, rule_id, aggregate_id), 0)

    def increment(self, workspace_id: str, rule_id: str, aggregate_id: str) -> None:
        key = (workspace_id, rule_id, aggregate_id)
        self.counts[key] = self.counts.get(key, 0) + 1


class InMemoryCapabilityChecker:
    def __init__(self, available: Optional[set[tuple[str, str]]] = None) -> None:
        self.available = available or set()

    def has(self, workspace_id: str, capability: str) -> bool:
        return (workspace_id, capability) in self.available


class InMemoryLocalAuth:
    """Mirror `LocalServiceAuth`: ký/verify trên đúng bytes body."""

    def __init__(self, secret: str = SECRET) -> None:
        self.secret = secret

    def sign(self, raw_body: bytes) -> str:
        return hmac.new(self.secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    def verify(self, signature: str, raw_body: bytes) -> bool:
        if not signature or not self.secret:
            return False
        return hmac.compare_digest(signature, self.sign(raw_body))


class InMemoryInboxStore:
    def __init__(self) -> None:
        self.records: Dict[tuple[str, str, str], dict] = {}

    async def record(
        self,
        conn: Any,
        *,
        workspace_id: str,
        event_id: str,
        consumer_name: str,
        event_type: str,
        correlation_id: str,
        outcome: str,
        scheduled_task_id: Optional[str] = None,
        aggregate_type: Optional[str] = None,
        aggregate_id: Optional[str] = None,
    ) -> Literal["recorded", "duplicate"]:
        key = (workspace_id, event_id, consumer_name)
        if key in self.records:
            return "duplicate"
        self.records[key] = {
            "workspace_id": workspace_id,
            "event_id": event_id,
            "consumer_name": consumer_name,
            "event_type": event_type,
            "correlation_id": correlation_id,
            "outcome": outcome,
            "scheduled_task_id": scheduled_task_id,
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
        }
        return "recorded"

    async def set_outcome(
        self,
        conn: Any,
        workspace_id: str,
        event_id: str,
        consumer_name: str,
        outcome: str,
        scheduled_task_id: Optional[str] = None,
    ) -> None:
        key = (workspace_id, event_id, consumer_name)
        if key in self.records:
            self.records[key]["outcome"] = outcome
            if scheduled_task_id:
                self.records[key]["scheduled_task_id"] = scheduled_task_id


class StubExecutionPlaneClient:
    def __init__(self) -> None:
        self.scheduled: List[dict] = []

    async def schedule_reference_task(self, rule: EventTriggerRule, envelope: Any) -> str:
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        self.scheduled.append({
            "task_id": task_id,
            "workspace_id": envelope.workspaceId,
            "event_id": envelope.eventId,
            "correlation_id": envelope.correlationId,
            "agent_spec": {
                "id": rule.agent_spec.id,
                "version": rule.agent_spec.version,
                "definition_hash": rule.agent_spec.definition_hash,
            },
            "aggregate_ref": {"type": envelope.aggregateType, "id": envelope.aggregateId},
            "mode": rule.mode,
        })
        return task_id


class DummyDb:
    class DummyTx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    def begin(self):
        return self.DummyTx()


@dataclass
class IntakeTestDeps:
    local_auth: InMemoryLocalAuth = field(default_factory=InMemoryLocalAuth)
    inbox_store: InMemoryInboxStore = field(default_factory=InMemoryInboxStore)
    rule_store: InMemoryTriggerRuleStore = field(default_factory=InMemoryTriggerRuleStore)
    run_counter: InMemoryRunCounter = field(default_factory=InMemoryRunCounter)
    capability_checker: InMemoryCapabilityChecker = field(default_factory=InMemoryCapabilityChecker)
    execution_plane: StubExecutionPlaneClient = field(default_factory=StubExecutionPlaneClient)
    db: DummyDb = field(default_factory=DummyDb)
    caller_workspace_id: Optional[str] = None

    @property
    def trigger_policy(self):
        from apps.cosa.events.trigger_policy import TriggerPolicyService
        return TriggerPolicyService(
            store=self.rule_store,
            capabilities=self.capability_checker,
            run_counter=self.run_counter,
        )


@pytest.fixture
def default_rule() -> EventTriggerRule:
    return EventTriggerRule(
        rule_id="rule_1",
        workspace_id="ws_1",
        event_type="operations.task.created.v1",
        agent_spec=PinnedSpecIdentity(
            id="cosa.operations.task_responder",
            version="1.0.0",
            definition_hash="hash123",
        ),
        mode="proposal",
        max_runs_per_aggregate_per_day=5,
        required_capabilities=("operations.task.read",),
        aggregate_filter=None,
        owner="operator",
        enabled=True,
    )


@pytest.fixture
def test_deps(default_rule: EventTriggerRule) -> IntakeTestDeps:
    deps = IntakeTestDeps()
    deps.rule_store.rules[("ws_1", "operations.task.created.v1")] = default_rule
    deps.capability_checker.available.add(("ws_1", "operations.task.read"))
    return deps


@pytest.fixture
def intake_client(test_deps: IntakeTestDeps):
    app = create_cosa_app()
    app.state.plane = type("DummyPlane", (), {"event_intake_deps": test_deps})()
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_accepted_event_schedules_reference_task(intake_client: AsyncClient, test_deps: IntakeTestDeps):
    env = _env()
    r = await intake_client.post("/agent/internal/events", json=env, headers=_sig(env))
    assert r.status_code == 200
    data = r.json()
    assert data["outcome"] == "accepted"
    assert data["scheduledTaskId"]
    assert len(test_deps.execution_plane.scheduled) == 1
    scheduled = test_deps.execution_plane.scheduled[0]
    assert scheduled["workspace_id"] == "ws_1"
    assert scheduled["event_id"] == env["eventId"]
    # Reference-only: no title or status in task payload
    assert "title" not in scheduled
    assert "status" not in scheduled


@pytest.mark.asyncio
async def test_duplicate_event_returns_duplicate_without_second_task(
    intake_client: AsyncClient, test_deps: IntakeTestDeps
):
    env = _env()
    first = await intake_client.post("/agent/internal/events", json=env, headers=_sig(env))
    second = await intake_client.post("/agent/internal/events", json=env, headers=_sig(env))
    assert first.status_code == 200 and first.json()["outcome"] == "accepted"
    assert second.status_code == 200 and second.json()["outcome"] == "duplicate"
    assert len(test_deps.execution_plane.scheduled) == 1


@pytest.mark.asyncio
async def test_invalid_local_signature_returns_401(intake_client: AsyncClient):
    env = _env()
    r = await intake_client.post(
        "/agent/internal/events", json=env, headers={"X-COSA-Local-Signature": "bad-signature"}
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_cross_workspace_envelope_returns_403(
    intake_client: AsyncClient, test_deps: IntakeTestDeps
):
    test_deps.caller_workspace_id = "ws_1"
    env = _env(workspace_id="ws_2")
    r = await intake_client.post("/agent/internal/events", json=env, headers=_sig(env))
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_disabled_rule_returns_ignored(
    intake_client: AsyncClient, test_deps: TestEventIntakeDeps, default_rule: EventTriggerRule
):
    disabled = EventTriggerRule(
        rule_id=default_rule.rule_id,
        workspace_id=default_rule.workspace_id,
        event_type=default_rule.event_type,
        agent_spec=default_rule.agent_spec,
        mode=default_rule.mode,
        max_runs_per_aggregate_per_day=default_rule.max_runs_per_aggregate_per_day,
        required_capabilities=default_rule.required_capabilities,
        aggregate_filter=default_rule.aggregate_filter,
        owner=default_rule.owner,
        enabled=False,
    )
    test_deps.rule_store.rules[("ws_1", "operations.task.created.v1")] = disabled
    env = _env()
    r = await intake_client.post("/agent/internal/events", json=env, headers=_sig(env))
    assert r.status_code == 200
    assert r.json()["outcome"] == "ignored_rule_disabled"
    assert len(test_deps.execution_plane.scheduled) == 0


@pytest.mark.asyncio
async def test_no_rule_returns_ignored(intake_client: AsyncClient):
    env = _env(event_type="operations.task.overdue.v1")
    r = await intake_client.post("/agent/internal/events", json=env, headers=_sig(env))
    assert r.status_code == 200
    assert r.json()["outcome"] == "ignored_rule_disabled"


@pytest.mark.asyncio
async def test_rate_limited_aggregate_returns_policy_denied(
    intake_client: AsyncClient, test_deps: IntakeTestDeps
):
    test_deps.run_counter.counts[("ws_1", "rule_1", "t_rl")] = 5  # reached max
    env = _env(aggregate_id="t_rl")
    r = await intake_client.post("/agent/internal/events", json=env, headers=_sig(env))
    assert r.status_code == 200
    assert r.json()["outcome"] == "policy_denied"
    assert r.json()["reason"] == "rate_limited"


@pytest.mark.asyncio
async def test_rule_missing_capability_returns_policy_denied(
    intake_client: AsyncClient, test_deps: IntakeTestDeps
):
    test_deps.capability_checker.available.clear()  # no capabilities
    env = _env()
    r = await intake_client.post("/agent/internal/events", json=env, headers=_sig(env))
    assert r.status_code == 200
    assert r.json()["outcome"] == "policy_denied"
    assert r.json()["reason"].startswith("missing_capability:")


@pytest.mark.asyncio
async def test_invalid_envelope_returns_400(intake_client: AsyncClient):
    bad = _env()
    del bad["correlationId"]
    r = await intake_client.post("/agent/internal/events", json=bad, headers=_sig(bad))
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_worker_crash_after_inbox_before_schedule_recovers_without_duplicate(
    intake_client: AsyncClient, test_deps: IntakeTestDeps
):
    env = _env()
    # Simulate first intake crashed right after inbox recording
    await test_deps.inbox_store.record(
        None,
        workspace_id=env["workspaceId"],
        event_id=env["eventId"],
        consumer_name=CONSUMER,
        event_type=env["eventType"],
        correlation_id=env["correlationId"],
        outcome="pending",
    )
    # Relay retries POST
    r = await intake_client.post("/agent/internal/events", json=env, headers=_sig(env))
    assert r.status_code == 200
    assert r.json()["outcome"] in ("accepted", "duplicate")


@pytest.mark.asyncio
async def test_handle_event_verifies_over_raw_bytes(test_deps: IntakeTestDeps):
    envelope = _env()
    # unicode trong payload — chữ ký ký trên bytes UTF-8, phải verify khớp
    envelope["payload"]["note"] = "Xin chào — cần hỗ trợ ngay"
    raw = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
    sig = test_deps.local_auth.sign(raw)
    result = await handle_event(test_deps, raw, sig)
    assert result.outcome in {"accepted", "duplicate"}


@pytest.mark.asyncio
async def test_handle_event_rejects_wrong_signature(test_deps: IntakeTestDeps):
    raw = json.dumps(_env(), ensure_ascii=False).encode("utf-8")
    with pytest.raises(Unauthenticated):
        await handle_event(test_deps, raw, "not-a-valid-signature")


@pytest.mark.asyncio
async def test_handle_event_rejects_non_json_body(test_deps: IntakeTestDeps):
    raw = b"not-json-at-all"
    sig = test_deps.local_auth.sign(raw)
    with pytest.raises(ValueError, match="not valid JSON"):
        await handle_event(test_deps, raw, sig)


def test_intake_target_must_be_local_not_remote_platform_url(monkeypatch):
    monkeypatch.setenv("COSA_EXECUTION_PLANE_URL", "https://platform.cosa.example.com")
    monkeypatch.setenv("COSA_PLATFORM_CONTROL_PLANE_URL", "https://platform.cosa.example.com")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("AGENT_DATABASE_URL", "postgresql://user:pass@127.0.0.1:5433/db")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    with pytest.raises(RuntimeError, match="execution plane URL"):
        build_cosa_agent_plane()
