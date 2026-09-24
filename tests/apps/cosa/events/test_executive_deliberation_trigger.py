"""Router intake cho `executive.deliberation.framed.v1`: một frame version = một task,
mang nguyên pin deployment + overlay Company đã persist tới worker handler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from agent.executive_board.models import ExecutiveAnalysisOutcome

from apps.cosa.events.router import EXECUTIVE_DELIBERATION_FRAMED_EVENT, handle_event
from apps.cosa.worker.executive_board_handler import execute_executive_deliberation_framed_task
from tests.agent.executive_board.advisor_support import build_pin
from tests.agent.executive_board.test_handler import camel_pin
from tests.apps.cosa.events.test_governed_workflow_trigger import Deps, _env, _raw, _sig


def _framed_env(**payload_over) -> dict:
    payload = {
        "deliberationId": "delib_1",
        "frameVersion": 1,
        "question": "Có nên tăng giá?",
        "selectedRoles": [camel_pin("cfo"), camel_pin("cmo")],
        "evidenceSources": [
            {"sourceRef": "project://proj_1/doc", "sourceHash": "h1", "classification": "internal"}
        ],
    }
    payload.update(payload_over)
    env = _env(payload, event_type=EXECUTIVE_DELIBERATION_FRAMED_EVENT)
    env["projectId"] = "proj_1"
    env["aggregateType"] = "deliberation"
    env["aggregateId"] = "delib_1"
    return env


@pytest.mark.asyncio
async def test_framed_event_schedules_one_project_scoped_task_with_pins():
    deps = Deps()
    env = _framed_env()

    res = await handle_event(deps, _raw(env), _sig(env))

    assert res.outcome == "accepted"
    (dispatch,) = deps.execution_plane.dispatches
    assert dispatch["task_type"] == "executive_deliberation_framed"
    assert dispatch["coalescing_key"] == "exec_delib:ws_1:delib_1:1"
    assert dispatch["target_spec_id"] == build_pin("cfo").overlay.overlay_spec_id
    body = dispatch["input_payload"]
    assert body["workspace_id"] == "ws_1"
    assert body["project_id"] == "proj_1"
    assert body["evidence_refs"][0]["source_ref"] == "project://proj_1/doc"

    # Payload router tạo ra được handler parse ra đúng pin (không default, không mất trường).
    runner = MagicMock()
    runner.run = AsyncMock(
        side_effect=lambda req: ExecutiveAnalysisOutcome(
            kind="executive.analysis.completed.v1",
            deliberation_id=req.deliberation_id,
            frame_version=req.frame_version,
            role_key=req.role_key,
            descriptor={"conclusion": "ok"},
        )
    )
    plane = MagicMock()
    plane.executive_board_runner = runner
    plane.executive_board_client.submit_analysis_callback = AsyncMock(return_value={})
    plane.executive_board_client.get_deliberation_authority = AsyncMock(
        side_effect=lambda **kw: {"rolePin": camel_pin(kw["role_key"])}
    )

    await execute_executive_deliberation_framed_task(plane, None, body)

    requests = [c.args[0] for c in runner.run.await_args_list]
    assert [r.execution_pin for r in requests] == [build_pin("cfo"), build_pin("cmo")]
    assert all(r.project_id == "proj_1" for r in requests)


@pytest.mark.asyncio
async def test_duplicate_framed_event_is_deduped():
    deps = Deps()
    env = _framed_env()
    raw, sig = _raw(env), _sig(env)
    assert (await handle_event(deps, raw, sig)).outcome == "accepted"
    assert (await handle_event(deps, raw, sig)).outcome == "duplicate"
    assert len(deps.execution_plane.dispatches) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutation",
    [
        {"selectedRoles": []},
        {"question": ""},
        {"selectedRoles": [{"roleKey": "cfo"}]},
    ],
)
async def test_malformed_framed_event_is_rejected_without_scheduling(mutation):
    deps = Deps()
    env = _framed_env(**mutation)
    res = await handle_event(deps, _raw(env), _sig(env))
    assert res.outcome == "rejected"
    assert deps.execution_plane.dispatches == []


@pytest.mark.asyncio
async def test_framed_event_without_project_id_is_rejected():
    deps = Deps()
    env = _framed_env()
    del env["projectId"]
    res = await handle_event(deps, _raw(env), _sig(env))
    assert res.outcome == "rejected"
    assert "projectId" in (res.reason or "")
