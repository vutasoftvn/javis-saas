"""COSA Automation MVP (Task 4) — router intake for
`automation.invocation.requested.v1` and control-plane dispatch fencing."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest

from apps.cosa.events.router import Unauthenticated, handle_event

SECRET = "test-secret"


def _raw(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _sig(payload: dict) -> str:
    return hmac.new(SECRET.encode("utf-8"), _raw(payload), hashlib.sha256).hexdigest()


def _dispatch_payload(**over) -> dict:
    base = {
        "schema_version": 1,
        "invocation_id": "inv_1",
        "workspace_id": "ws_1",
        "automation_key": "operating.weekly-review",
        "revision": 1,
        "revision_hash": "a" * 64,
        "trigger_kind": "manual",
        "trigger_identity": "req-1",
        "correlation_id": "corr_1",
        "requested_at": "2026-09-10T10:00:00.000Z",
    }
    base.update(over)
    return base


def _env(payload: dict, *, event_type: str = "automation.invocation.requested.v1") -> dict:
    return {
        "eventId": uuid.uuid4().hex,
        "eventType": event_type,
        "schemaVersion": 1,
        "occurredAt": "2026-09-10T10:00:00.000Z",
        "workspaceId": "ws_1",
        "aggregateType": "automation_invocation",
        "aggregateId": payload.get("invocation_id", "inv_1"),
        "correlationId": "corr_1",
        "actor": {"kind": "user", "id": "u1"},
        "producer": {"service": "company.operations", "version": "1.0.0"},
        "classification": "internal",
        "payload": payload,
    }


class InMemoryLocalAuth:
    def verify(self, signature: str, raw_body: bytes) -> bool:
        return hmac.compare_digest(
            signature, hmac.new(SECRET.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        )


class InMemoryInboxStore:
    def __init__(self) -> None:
        self.records: dict[tuple, dict] = {}

    async def record(self, conn, **kw):
        key = (kw["workspace_id"], kw["event_id"], kw["consumer_name"])
        if key in self.records:
            return "duplicate"
        self.records[key] = dict(kw)
        return "recorded"

    async def set_outcome(self, conn, ws, eid, consumer, outcome, task_id=None):
        key = (ws, eid, consumer)
        if key in self.records:
            self.records[key]["outcome"] = outcome
            self.records[key]["scheduled_task_id"] = task_id


class DummyDb:
    class _Tx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

    def begin(self):
        return self._Tx()


class StubExecutionPlane:
    def __init__(self) -> None:
        self.automation_dispatches: list[Any] = []

    async def schedule_automation_dispatch(self, env: Any) -> str:
        tid = f"task_{uuid.uuid4().hex[:8]}"
        self.automation_dispatches.append({"task_id": tid, "payload": dict(env.payload)})
        return tid


@dataclass
class Deps:
    local_auth: InMemoryLocalAuth = field(default_factory=InMemoryLocalAuth)
    inbox_store: InMemoryInboxStore = field(default_factory=InMemoryInboxStore)
    execution_plane: StubExecutionPlane = field(default_factory=StubExecutionPlane)
    db: DummyDb = field(default_factory=DummyDb)
    caller_workspace_id: str | None = None


@pytest.mark.asyncio
async def test_valid_signed_automation_event_schedules_one_dispatch() -> None:
    deps = Deps()
    env = _env(_dispatch_payload())
    res = await handle_event(deps, _raw(env), _sig(env))
    assert res.outcome == "accepted"
    assert len(deps.execution_plane.automation_dispatches) == 1
    assert deps.execution_plane.automation_dispatches[0]["payload"]["invocation_id"] == "inv_1"


@pytest.mark.asyncio
async def test_duplicate_signed_event_is_deduped_by_inbox() -> None:
    deps = Deps()
    env = _env(_dispatch_payload())
    raw, sig = _raw(env), _sig(env)
    assert (await handle_event(deps, raw, sig)).outcome == "accepted"
    assert (await handle_event(deps, raw, sig)).outcome == "duplicate"
    assert len(deps.execution_plane.automation_dispatches) == 1


@pytest.mark.asyncio
async def test_unsigned_event_is_rejected_before_scheduling() -> None:
    deps = Deps()
    env = _env(_dispatch_payload())
    with pytest.raises(Unauthenticated):
        await handle_event(deps, _raw(env), "deadbeef")
    assert deps.execution_plane.automation_dispatches == []


@pytest.mark.asyncio
async def test_forbidden_key_in_payload_is_quarantined() -> None:
    deps = Deps()
    env = _env(_dispatch_payload(prompt="leak me"))
    res = await handle_event(deps, _raw(env), _sig(env))
    assert res.outcome == "rejected"
    assert "prompt" in (res.reason or "")
    assert deps.execution_plane.automation_dispatches == []


@pytest.mark.asyncio
async def test_missing_field_is_quarantined() -> None:
    deps = Deps()
    payload = _dispatch_payload()
    del payload["revision_hash"]
    env = _env(payload)
    res = await handle_event(deps, _raw(env), _sig(env))
    assert res.outcome == "rejected"
    assert "revision_hash" in (res.reason or "")


@pytest.mark.asyncio
async def test_cross_workspace_payload_is_rejected() -> None:
    deps = Deps()
    env = _env(_dispatch_payload(workspace_id="ws_other"))
    res = await handle_event(deps, _raw(env), _sig(env))
    assert res.outcome == "rejected"
    assert "workspace" in (res.reason or "")
