"""COSA Automation MVP (Task 5) — the worker `automation_run` handler."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from agent.contracts.run import RunStatus
from agent.runs.repository import InMemoryRunRepository

from apps.cosa.worker.handlers import execute_automation_run_task


class RecordingGateway:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def execute(self, request):
        rec = {
            "capability_id": getattr(request, "capability_id", None),
            "run_id": getattr(request, "run_id", None),
            "tool_call_id": getattr(request, "tool_call_id", None) or "call_x",
        }
        self.calls.append(rec)
        return SimpleNamespace(tool_call_id=rec["tool_call_id"], status="completed")


def _plane(gateway: RecordingGateway | None = None):
    return SimpleNamespace(
        run_repository=InMemoryRunRepository(),
        gateway=gateway or RecordingGateway(),
        stream_event_repository=None,
    )


_STREAM = SimpleNamespace()  # never touched: stream_event_repository is None


def _payload(key: str = "operating.weekly-review", **over) -> dict:
    base = {
        "task_type": "automation_run",
        "run_id": f"run_auto_{key.replace('.', '_')}",
        "invocation_id": "inv-1",
        "workspace_id": "ws-1",
        "automation_key": key,
        "revision": 1,
        "revision_hash": "r" * 64,
        "trigger_kind": "manual",
        "trigger_identity": "req-1",
        "correlation_id": "corr-1",
        "agent_profile": "operations",
        "configuration": {"projectId": "p1"},
    }
    base.update(over)
    return base


@pytest.mark.asyncio
async def test_weekly_review_run_completes_with_pinned_manifest_and_evidence():
    plane = _plane()
    payload = _payload("operating.weekly-review")
    await execute_automation_run_task(plane, _STREAM, payload)

    run = await plane.run_repository.get_run(payload["run_id"])
    assert run.status == RunStatus.COMPLETED
    assert run.root_executable_kind == "workflow"

    manifest = await plane.run_repository.get_automation_manifest(payload["run_id"])
    assert manifest is not None
    assert manifest["manifest_json"]["automation_key"] == "operating.weekly-review"

    events = [e.event_type for e in await plane.run_repository.list_events(payload["run_id"])]
    assert "run.started" in events and "run.completed" in events

    ck = await plane.run_repository.get_latest_checkpoint(payload["run_id"])
    assert set(("digest_markdown", "source_refs")).issubset(ck.serialized_state["evidence"].keys())
    # every gateway call was an allow-listed read capability
    allowed = set(manifest["manifest_json"]["capability_allowlist"])
    for call in plane.gateway.calls:
        assert call["capability_id"] in allowed


@pytest.mark.asyncio
async def test_commercial_outbound_returns_a_draft_and_never_delivers():
    plane = _plane()
    payload = _payload("commercial.outbound-draft", configuration={"audienceRef": "a1"})
    await execute_automation_run_task(plane, _STREAM, payload)

    ck = await plane.run_repository.get_latest_checkpoint(payload["run_id"])
    evidence = ck.serialized_state["evidence"]
    assert evidence["draft_artifact"]["status"] == "draft"
    # no capability id even hints at a send/deliver
    for call in plane.gateway.calls:
        assert "send" not in call["capability_id"] and "deliver" not in call["capability_id"]


@pytest.mark.asyncio
async def test_unknown_blueprint_key_fails_without_a_run():
    plane = _plane()
    payload = _payload("operating.not-a-blueprint")
    with pytest.raises(KeyError):
        await execute_automation_run_task(plane, _STREAM, payload)
    assert await plane.run_repository.get_automation_manifest(payload["run_id"]) is None


@pytest.mark.asyncio
async def test_restart_reloads_the_persisted_manifest_not_a_mutated_spec():
    plane = _plane()
    payload = _payload("operations.task-follow-up")
    await execute_automation_run_task(plane, _STREAM, payload)
    first = await plane.run_repository.get_automation_manifest(payload["run_id"])

    # A second dispatch of the same run (worker restart) must not create a
    # different manifest; save_automation_manifest is insert-once.
    await execute_automation_run_task(plane, _STREAM, payload)
    second = await plane.run_repository.get_automation_manifest(payload["run_id"])
    assert first["manifest_hash"] == second["manifest_hash"]
    run = await plane.run_repository.get_run(payload["run_id"])
    assert run.status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_local_only_blueprint_blocks_without_a_local_node():
    # None of the shipped blueprints are local_only, so simulate by forcing the
    # manifest metadata path: a blueprint whose runtime_requirement is local_only
    # is BLOCKED, never cloud-fallen-back. We assert the guard via the payload
    # flag on a run whose metadata we monkeypatch.
    import agent.workflows.automation_blueprints as bp

    key = "strategy.initiative-health"
    orig = bp.get_blueprint_metadata

    def _meta(k):
        m = orig(k)
        if k == key:
            m["runtime_requirement"] = "local_only"
        return m

    bp.get_blueprint_metadata = _meta
    try:
        plane = _plane()
        payload = _payload(key, local_runtime_available=False)
        await execute_automation_run_task(plane, _STREAM, payload)
        run = await plane.run_repository.get_run(payload["run_id"])
        assert run.status == RunStatus.FAILED
        events = [e.event_type for e in await plane.run_repository.list_events(payload["run_id"])]
        assert "run.blocked" in events
    finally:
        bp.get_blueprint_metadata = orig
