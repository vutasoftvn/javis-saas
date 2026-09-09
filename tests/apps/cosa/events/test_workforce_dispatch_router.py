"""Router wiring cho signed work-package dispatch + deterministic outcome
analysis dispatch (Task 3/4/4A)."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import pytest
from agent.workforce.outcome_analysis import OUTCOME_ANALYSIS_SKILL_ID
from agent.workforce.repository import InMemoryWorkforceRepository

from apps.cosa.events.router import handle_event
from apps.cosa.worker.outcome_analysis_run import (
    OutcomeAnalysisPayloadError,
    validate_outcome_analysis_payload,
)

SECRET = "test-secret"


def _raw(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _sig(payload: dict) -> str:
    return hmac.new(SECRET.encode("utf-8"), _raw(payload), hashlib.sha256).hexdigest()


def _env(event_type: str, payload: dict) -> dict:
    return {
        "eventId": uuid.uuid4().hex,
        "eventType": event_type,
        "schemaVersion": 1,
        "occurredAt": "2026-09-09T10:00:00.000Z",
        "workspaceId": "ws_1",
        "aggregateType": "work_package",
        "aggregateId": "wp_1",
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
        self.platform_tasks: list[dict] = []

    async def schedule_platform_task(
        self, *, target_spec_id, task_type, input_payload, coalescing_key=None
    ):
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


@dataclass
class Deps:
    local_auth: InMemoryLocalAuth = field(default_factory=InMemoryLocalAuth)
    inbox_store: InMemoryInboxStore = field(default_factory=InMemoryInboxStore)
    execution_plane: StubExecutionPlane = field(default_factory=StubExecutionPlane)
    db: DummyDb = field(default_factory=DummyDb)
    caller_workspace_id: str | None = None
    workforce_repository: Any = None


def _wp_payload(**over):
    base = {
        "workspaceId": "ws_1",
        "workPackageId": "wp_1",
        "workAttemptId": "wa_1",
        "agentInstanceId": "emp_1",
        "assignmentId": "as_1",
        "effectivePriority": "P1",
        "expectedCapabilityRefs": ["operations.task.read"],
        "correlationId": "corr_1",
    }
    base.update(over)
    return base


@pytest.mark.asyncio
async def test_signed_work_package_queued_schedules_one_work_package_task() -> None:
    deps = Deps()
    env = _env("operating.work_package.queued.v1", _wp_payload())
    raw = _raw(env)
    res = await handle_event(deps, raw, _sig(env))
    assert res.outcome == "accepted"
    assert len(deps.execution_plane.platform_tasks) == 1
    task = deps.execution_plane.platform_tasks[0]
    assert task["task_type"] == "work_package"
    assert task["input_payload"]["work_attempt_id"] == "wa_1"
    assert task["input_payload"]["agent_instance_id"] == "emp_1"
    assert task["coalescing_key"] == "wp:ws_1:wa_1"

    # Duplicate signed event -> inbox dedup -> no second task.
    res2 = await handle_event(deps, raw, _sig(env))
    assert res2.outcome == "duplicate"
    assert len(deps.execution_plane.platform_tasks) == 1


@pytest.mark.asyncio
async def test_work_package_dispatch_with_bad_attribution_is_rejected() -> None:
    deps = Deps()
    bad = _wp_payload()
    del bad["agentInstanceId"]
    env = _env("operating.work_package.queued.v1", bad)
    res = await handle_event(deps, _raw(env), _sig(env))
    assert res.outcome == "rejected"
    assert res.reason == "missing_workforce_attribution"
    assert deps.execution_plane.platform_tasks == []


@pytest.mark.asyncio
async def test_task_result_submitted_schedules_outcome_analysis_when_bound() -> None:
    repo = InMemoryWorkforceRepository()
    emp, asg = uuid4(), uuid4()
    await repo.upsert_outcome_analysis_binding(
        "ws_1",
        "TASK_OUTCOME",
        emp,
        asg,
        "AUTO_ALL_TASKS",
        OUTCOME_ANALYSIS_SKILL_ID,
        "1.0.0",
        "sha256:s",
        "founder_1",
    )
    deps = Deps(workforce_repository=repo)
    env = _env(
        "operating.task.result_submitted.v1",
        {
            "workspaceId": "ws_1",
            "taskResultId": "tr_1",
            "contractId": "c_1",
            "requestId": "req_1",
        },
    )
    res = await handle_event(deps, _raw(env), _sig(env))
    assert res.outcome == "accepted"
    task = deps.execution_plane.platform_tasks[0]
    assert task["task_type"] == "outcome_analysis"
    assert task["target_spec_id"] == OUTCOME_ANALYSIS_SKILL_ID
    assert task["input_payload"]["agent_instance_id"] == str(emp)


@pytest.mark.asyncio
async def test_task_result_submitted_blocked_when_no_binding() -> None:
    deps = Deps(workforce_repository=InMemoryWorkforceRepository())
    env = _env(
        "operating.task.result_submitted.v1",
        {"workspaceId": "ws_1", "taskResultId": "tr_1", "contractId": "c_1"},
    )
    res = await handle_event(deps, _raw(env), _sig(env))
    assert res.outcome == "blocked_configuration"
    assert deps.execution_plane.platform_tasks == []


@pytest.mark.asyncio
async def test_manual_policy_does_not_schedule() -> None:
    repo = InMemoryWorkforceRepository()
    await repo.upsert_outcome_analysis_binding(
        "ws_1",
        "TASK_OUTCOME",
        uuid4(),
        uuid4(),
        "MANUAL",
        OUTCOME_ANALYSIS_SKILL_ID,
        "1.0.0",
        "sha256:s",
        "founder_1",
    )
    deps = Deps(workforce_repository=repo)
    env = _env(
        "operating.task.result_submitted.v1",
        {"workspaceId": "ws_1", "taskResultId": "tr_1", "contractId": "c_1"},
    )
    res = await handle_event(deps, _raw(env), _sig(env))
    assert res.outcome == "ignored_manual"
    assert deps.execution_plane.platform_tasks == []


def test_outcome_analysis_payload_rejects_forbidden_capabilities() -> None:
    good = {
        "request_id": "r",
        "task_result_id": "tr",
        "contract_id": "c",
        "workspace_id": "ws",
        "run_id": "run",
        "agent_instance_id": "emp",
        "assignment_id": "as",
        "skill_id": OUTCOME_ANALYSIS_SKILL_ID,
        "skill_version": "1.0.0",
        "definition_hash": "sha256:s",
    }
    assert validate_outcome_analysis_payload(good)

    with pytest.raises(OutcomeAnalysisPayloadError):
        validate_outcome_analysis_payload({**good, "capability_refs": ["operations.task.advance"]})
    with pytest.raises(OutcomeAnalysisPayloadError):
        validate_outcome_analysis_payload(
            {**good, "capability_refs": ["operations.kr.actual.write"]}
        )
    with pytest.raises(OutcomeAnalysisPayloadError):
        bad = dict(good)
        del bad["request_id"]
        validate_outcome_analysis_payload(bad)
