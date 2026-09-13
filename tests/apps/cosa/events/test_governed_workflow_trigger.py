"""Task 11 (plan 2026-09-13-founder-configurable-agent-skill-workflow) —
router intake for `operations.workflow_run.requested.v1`: exactly one
scheduler task per governed workflow run, coalesced on a deterministic
run_id, with truthful ignored/rejected outcomes for a malformed or
cross-workspace trigger."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest

from apps.cosa.events.router import (
    GOVERNED_WORKFLOW_RUN_REQUESTED_EVENT,
    Unauthenticated,
    handle_event,
)

SECRET = "test-secret"


def _raw(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _sig(payload: dict) -> str:
    return hmac.new(SECRET.encode("utf-8"), _raw(payload), hashlib.sha256).hexdigest()


def _trigger_payload(**over) -> dict:
    base = {
        "workspace_id": "ws_1",
        "project_id": "proj_1",
        "workflow_binding_id": "binding_1",
        "workflow_asset_id": "wf_governed_1",
        "workflow_version": "1.0.0",
        "workflow_definition_hash": "h" * 64,
        "project_agent_deployment_id": "dep_1",
        "idempotency_key": "idem_1",
        "correlation_id": "corr_1",
    }
    base.update(over)
    return base


def _env(payload: dict, *, event_type: str = GOVERNED_WORKFLOW_RUN_REQUESTED_EVENT) -> dict:
    return {
        "eventId": uuid.uuid4().hex,
        "eventType": event_type,
        "schemaVersion": 1,
        "occurredAt": "2026-09-13T10:00:00.000Z",
        "workspaceId": "ws_1",
        "aggregateType": "project_workflow_binding",
        "aggregateId": payload.get("workflow_binding_id", "binding_1"),
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
        self.dispatches: list[dict[str, Any]] = []

    async def schedule_platform_task(
        self,
        *,
        target_spec_id: str,
        task_type: str,
        input_payload: dict[str, Any],
        coalescing_key: str | None = None,
    ) -> str:
        tid = f"task_{uuid.uuid4().hex[:8]}"
        self.dispatches.append(
            {
                "task_id": tid,
                "target_spec_id": target_spec_id,
                "task_type": task_type,
                "input_payload": dict(input_payload),
                "coalescing_key": coalescing_key,
            }
        )
        return tid


@dataclass
class Deps:
    local_auth: InMemoryLocalAuth = field(default_factory=InMemoryLocalAuth)
    inbox_store: InMemoryInboxStore = field(default_factory=InMemoryInboxStore)
    execution_plane: StubExecutionPlane = field(default_factory=StubExecutionPlane)
    db: DummyDb = field(default_factory=DummyDb)
    caller_workspace_id: str | None = None


@pytest.mark.asyncio
async def test_valid_signed_trigger_schedules_exactly_one_governed_workflow_task() -> None:
    deps = Deps()
    env = _env(_trigger_payload())
    res = await handle_event(deps, _raw(env), _sig(env))
    assert res.outcome == "accepted"
    assert len(deps.execution_plane.dispatches) == 1
    dispatch = deps.execution_plane.dispatches[0]
    assert dispatch["task_type"] == "governed_workflow_run"
    assert dispatch["input_payload"]["workspace_id"] == "ws_1"
    assert dispatch["input_payload"]["project_id"] == "proj_1"
    assert dispatch["input_payload"]["run_id"]


@pytest.mark.asyncio
async def test_duplicate_signed_event_is_deduped_by_inbox() -> None:
    deps = Deps()
    env = _env(_trigger_payload())
    raw, sig = _raw(env), _sig(env)
    assert (await handle_event(deps, raw, sig)).outcome == "accepted"
    assert (await handle_event(deps, raw, sig)).outcome == "duplicate"
    assert len(deps.execution_plane.dispatches) == 1


@pytest.mark.asyncio
async def test_retried_event_with_same_idempotency_key_coalesces_on_the_same_run() -> None:
    """A different eventId (Company at-least-once retry) but the SAME
    idempotency_key must resolve to the exact same run_id/coalescing_key —
    the scheduler (not this test) is what actually collapses these into one
    task, but the router must feed it a deterministic key to do so."""
    deps = Deps()
    payload = _trigger_payload()
    env1 = _env(payload)
    env2 = _env(payload)  # fresh eventId, identical payload/idempotency_key
    res1 = await handle_event(deps, _raw(env1), _sig(env1))
    res2 = await handle_event(deps, _raw(env2), _sig(env2))
    assert res1.outcome == "accepted"
    assert res2.outcome == "accepted"
    assert len(deps.execution_plane.dispatches) == 2
    run_ids = {d["input_payload"]["run_id"] for d in deps.execution_plane.dispatches}
    coalescing_keys = {d["coalescing_key"] for d in deps.execution_plane.dispatches}
    assert len(run_ids) == 1
    assert len(coalescing_keys) == 1


@pytest.mark.asyncio
async def test_unsigned_event_is_rejected_before_scheduling() -> None:
    deps = Deps()
    env = _env(_trigger_payload())
    with pytest.raises(Unauthenticated):
        await handle_event(deps, _raw(env), "deadbeef")
    assert deps.execution_plane.dispatches == []


@pytest.mark.asyncio
async def test_forbidden_key_in_payload_is_quarantined() -> None:
    deps = Deps()
    env = _env(_trigger_payload(prompt="leak me"))
    res = await handle_event(deps, _raw(env), _sig(env))
    assert res.outcome == "rejected"
    assert "prompt" in (res.reason or "")
    assert deps.execution_plane.dispatches == []


@pytest.mark.asyncio
async def test_missing_field_is_quarantined() -> None:
    deps = Deps()
    payload = _trigger_payload()
    del payload["workflow_definition_hash"]
    env = _env(payload)
    res = await handle_event(deps, _raw(env), _sig(env))
    assert res.outcome == "rejected"
    assert "workflow_definition_hash" in (res.reason or "")
    assert deps.execution_plane.dispatches == []


@pytest.mark.asyncio
async def test_cross_workspace_payload_is_rejected() -> None:
    deps = Deps()
    env = _env(_trigger_payload(workspace_id="ws_other"))
    res = await handle_event(deps, _raw(env), _sig(env))
    assert res.outcome == "rejected"
    assert "workspace" in (res.reason or "")
    assert deps.execution_plane.dispatches == []
