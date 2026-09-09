from __future__ import annotations

from types import SimpleNamespace

import pytest
from agent.runs.repository import InMemoryRunRepository

import apps.cosa.worker.work_package_run as wpr
from apps.cosa.worker.work_package_run import (
    WorkPackagePayloadError,
    execute_work_package_task,
)


def _payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "run_id": "run_wf_1",
        "workspace_id": "ws_a",
        "agent_instance_id": "emp_1",
        "assignment_id": "as_1",
        "work_package_id": "wp_1",
        "work_attempt_id": "wa_1",
        "agent_profile": "operations",
        "user_prompt": "do the work",
    }
    base.update(overrides)
    return base


@pytest.fixture
def plane_and_stream(monkeypatch):
    repo = InMemoryRunRepository()
    plane = SimpleNamespace(repository=repo)
    stream = SimpleNamespace()

    async def _fake_inner(_plane, _stream, _payload):
        # Kernel path bị thay bằng no-op — test này kiểm chứng hợp đồng của
        # wrapper (validate + attribution), không phải kernel.
        return None

    monkeypatch.setattr(wpr, "_execute_run_task_inner", _fake_inner, raising=False)
    # Patch the symbol as imported lazily inside execute_work_package_task.
    import apps.cosa.worker.handlers as handlers_mod

    monkeypatch.setattr(handlers_mod, "_execute_run_task_inner", _fake_inner, raising=False)
    return plane, stream, repo


@pytest.mark.asyncio
async def test_rejects_payload_missing_any_workforce_id(plane_and_stream) -> None:
    plane, stream, _ = plane_and_stream
    for key in ("agent_instance_id", "assignment_id", "work_package_id", "work_attempt_id"):
        bad = _payload()
        bad.pop(key)
        with pytest.raises(WorkPackagePayloadError):
            await execute_work_package_task(plane, stream, bad)


@pytest.mark.asyncio
async def test_rejects_assignment_not_matching_signed_snapshot(plane_and_stream) -> None:
    plane, stream, _ = plane_and_stream
    with pytest.raises(WorkPackagePayloadError):
        await execute_work_package_task(plane, stream, _payload(signed_assignment_id="as_OTHER"))


@pytest.mark.asyncio
async def test_run_keeps_exact_employee_package_attempt_attribution(plane_and_stream) -> None:
    plane, stream, repo = plane_and_stream
    await execute_work_package_task(plane, stream, _payload())
    run = await repo.get_run("run_wf_1")
    assert run is not None
    assert run.workforce_attribution.agent_instance_id == "emp_1"
    assert run.workforce_attribution.work_package_id == "wp_1"
    assert run.workforce_attribution.work_attempt_id == "wa_1"


@pytest.mark.asyncio
async def test_attribution_survives_a_kernel_recreated_run_record(
    plane_and_stream, monkeypatch
) -> None:
    plane, stream, repo = plane_and_stream

    async def _inner_that_recreates(_plane, _stream, payload):
        from agent.runs.models import RunRecord

        # Simulate kernel overwriting the run row without attribution.
        await repo.create_run(
            RunRecord(
                run_id=payload["run_id"],
                workspace_id="ws_a",
                principal="system:workforce",
                root_executable_id="cosa.agents.operations",
            )
        )

    import apps.cosa.worker.handlers as handlers_mod

    monkeypatch.setattr(
        handlers_mod, "_execute_run_task_inner", _inner_that_recreates, raising=False
    )

    await execute_work_package_task(plane, stream, _payload())
    run = await repo.get_run("run_wf_1")
    assert run.workforce_attribution is not None
    assert run.workforce_attribution.work_attempt_id == "wa_1"
