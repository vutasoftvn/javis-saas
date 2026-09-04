from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest

from apps.cosa.events.router import handle_event

SECRET = "test-secret"


def _raw(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _sig(payload: dict) -> str:
    return hmac.new(SECRET.encode("utf-8"), _raw(payload), hashlib.sha256).hexdigest()


def _env(event_type: str, payload: dict, *, aggregate_type: str, aggregate_id: str) -> dict:
    return {
        "eventId": str(uuid.uuid4()),
        "eventType": event_type,
        "schemaVersion": 1,
        "occurredAt": "2026-09-04T10:00:00.000Z",
        "workspaceId": "ws_1",
        "aggregateType": aggregate_type,
        "aggregateId": aggregate_id,
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
        self.records: dict[tuple[str, str, str], dict] = {}

    async def record(self, conn: Any, **kw: Any) -> str:
        key = (kw["workspace_id"], kw["event_id"], kw["consumer_name"])
        if key in self.records:
            return "duplicate"
        self.records[key] = dict(kw)
        return "recorded"

    async def set_outcome(
        self, conn: Any, ws: str, eid: str, consumer: str, outcome: str, task_id: str | None = None
    ) -> None:
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
        self.platform_tasks: list[dict] = []

    async def schedule_platform_task(
        self, *, target_spec_id: str, task_type: str, input_payload: dict, coalescing_key=None
    ) -> str:
        tid = f"task_{uuid.uuid4().hex[:8]}"
        self.platform_tasks.append(
            {
                "task_id": tid,
                "target_spec_id": target_spec_id,
                "task_type": task_type,
                "input_payload": input_payload,
                "coalescing_key": coalescing_key,
            }
        )
        return tid

    async def schedule_reference_task(self, rule: Any, env: Any) -> str:  # pragma: no cover
        raise AssertionError("self-trigger events must not fall through to trigger_policy")


class ExplodingTriggerPolicy:
    async def resolve(self, **kw: Any):  # pragma: no cover
        raise AssertionError("trigger_policy.resolve must not be called for self-trigger events")


@dataclass
class Deps:
    local_auth: InMemoryLocalAuth = field(default_factory=InMemoryLocalAuth)
    inbox_store: InMemoryInboxStore = field(default_factory=InMemoryInboxStore)
    execution_plane: StubExecutionPlane = field(default_factory=StubExecutionPlane)
    trigger_policy: ExplodingTriggerPolicy = field(default_factory=ExplodingTriggerPolicy)
    db: DummyDb = field(default_factory=DummyDb)
    caller_workspace_id: str | None = None


@pytest.mark.asyncio
async def test_weekly_goal_set_schedules_goal_decomposition_task():
    deps = Deps()
    payload = {
        "workspaceId": "ws_1",
        "projectId": "proj_1",
        "weeklyPlanId": "wp_1",
        "focus": "Close 3 customer interviews",
        "origin": "chat",
        "originRef": "conv_9",
    }
    env = _env(
        "operating.weekly_goal.set.v1", payload, aggregate_type="weekly_plan", aggregate_id="wp_1"
    )
    raw = _raw(env)
    res = await handle_event(deps, raw, _sig(env))

    assert res.outcome == "accepted"
    assert len(deps.execution_plane.platform_tasks) == 1
    t = deps.execution_plane.platform_tasks[0]
    assert t["task_type"] == "goal_decomposition"
    assert t["target_spec_id"] == "cosa.agents.operations"
    assert t["input_payload"]["project_id"] == "proj_1"
    assert t["input_payload"]["weekly_plan_id"] == "wp_1"
    assert t["input_payload"]["goal_text"] == "Close 3 customer interviews"
    assert t["input_payload"]["origin"] == "chat"
    assert t["input_payload"]["origin_ref"] == "conv_9"


@pytest.mark.asyncio
async def test_execution_plan_accepted_schedules_workspace_task_sweep():
    deps = Deps()
    payload = {"workspaceId": "ws_1", "projectId": "proj_1", "planId": "pl_1", "taskIds": ["t1", "t2"]}
    env = _env(
        "operating.execution_plan.accepted.v1",
        payload,
        aggregate_type="execution_plan",
        aggregate_id="pl_1",
    )
    res = await handle_event(deps, _raw(env), _sig(env))
    assert res.outcome == "accepted"
    assert deps.execution_plane.platform_tasks[0]["task_type"] == "workspace_task_sweep"
    assert deps.execution_plane.platform_tasks[0]["input_payload"]["workspace_id"] == "ws_1"


@pytest.mark.asyncio
async def test_duplicate_event_is_not_scheduled_twice():
    deps = Deps()
    payload = {"workspaceId": "ws_1", "projectId": "p", "weeklyPlanId": "wp", "focus": "x"}
    env = _env(
        "operating.weekly_goal.set.v1", payload, aggregate_type="weekly_plan", aggregate_id="wp"
    )
    raw, sig = _raw(env), _sig(env)
    await handle_event(deps, raw, sig)
    res2 = await handle_event(deps, raw, sig)
    assert res2.outcome == "duplicate"
    assert len(deps.execution_plane.platform_tasks) == 1
