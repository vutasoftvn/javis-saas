from unittest.mock import AsyncMock, MagicMock

import pytest
from agent.executive_board.models import ExecutiveAnalysisOutcome

from apps.cosa.worker.executive_board_handler import (
    ExecutiveBoardPayloadError,
    execute_executive_deliberation_framed_task,
)
from tests.agent.executive_board.advisor_support import build_pin


def camel_pin(role_key: str) -> dict:
    """Đúng shape Company phát trong `selectedRoles` của outbox event."""
    pin = build_pin(role_key)
    return {
        "roleKey": role_key,
        "deployment": {
            "projectAgentDeploymentId": pin.deployment.project_agent_deployment_id,
            "profileKey": pin.deployment.profile_key,
            "specId": pin.deployment.spec_id,
            "specVersion": pin.deployment.spec_version,
            "specHash": pin.deployment.spec_hash,
        },
        "overlay": {
            "roleKey": role_key,
            "overlaySpecId": pin.overlay.overlay_spec_id,
            "overlaySpecVersion": pin.overlay.overlay_spec_version,
            "overlaySpecHash": pin.overlay.overlay_spec_hash,
            "skillPins": [
                {"skillId": s.skill_id, "version": s.version, "definitionHash": s.definition_hash}
                for s in pin.overlay.skill_pins
            ],
        },
    }


def make_payload(**overrides) -> dict:
    payload = {
        "workspace_id": "ws-1",
        "project_id": "proj-1",
        "deliberation_id": "delib-1",
        "frame_version": 1,
        "question": "Should we increase subscription pricing?",
        "selected_roles": [camel_pin("cfo")],
        "evidence_refs": [],
    }
    payload.update(overrides)
    return payload


def make_plane(runner) -> MagicMock:
    plane = MagicMock()
    plane.executive_board_client = MagicMock()
    plane.executive_board_client.submit_analysis_callback = AsyncMock(return_value={"success": True})

    async def authority(**kwargs):
        # Company trả đúng pin đã persist trong frame.
        return {"rolePin": camel_pin(kwargs["role_key"])}

    plane.executive_board_client.get_deliberation_authority = AsyncMock(side_effect=authority)
    plane.executive_board_runner = runner
    return plane


@pytest.mark.asyncio
async def test_executive_board_handler_success_passes_exact_pins_to_runner():
    runner = MagicMock()
    runner.run = AsyncMock(
        return_value=ExecutiveAnalysisOutcome(
            kind="executive.analysis.completed.v1",
            deliberation_id="delib-1",
            frame_version=1,
            role_key="cfo",
            descriptor={"conclusion": "Financial viability is sound.", "confidence": "HIGH"},
        )
    )
    plane = make_plane(runner)

    res = await execute_executive_deliberation_framed_task(plane, None, make_payload())

    assert res["status"] == "completed"
    assert res["results"] == [{"role_key": "cfo", "outcome": "executive.analysis.completed.v1"}]
    request = runner.run.await_args.args[0]
    assert request.execution_pin == build_pin("cfo")
    assert request.project_id == "proj-1"
    assert request.peer_drafts is None
    kwargs = plane.executive_board_client.submit_analysis_callback.call_args.kwargs
    assert kwargs["workspace_id"] == "ws-1"
    assert kwargs["project_id"] == "proj-1"
    assert kwargs["deliberation_id"] == "delib-1"
    assert kwargs["payload"]["kind"] == "executive.analysis.completed.v1"


@pytest.mark.asyncio
async def test_failed_runner_outcome_still_carries_pin_hashes_in_callback():
    runner = MagicMock()
    runner.run = AsyncMock(side_effect=RuntimeError("boom"))
    plane = make_plane(runner)

    res = await execute_executive_deliberation_framed_task(plane, None, make_payload())

    assert res["results"][0]["outcome"] == "executive.analysis.failed.v1"
    body = plane.executive_board_client.submit_analysis_callback.call_args.kwargs["payload"]
    pin = build_pin("cfo")
    assert body["kind"] == "executive.analysis.failed.v1"
    # Encore từ chối `null` cho field optional: callback không được mang key None.
    assert "descriptor" not in body
    assert all(v is not None for v in body.values())
    assert body["deployment_pin_hash"] == pin.deployment.identity_hash()
    assert body["overlay_pin_hash"] == pin.overlay.identity_hash()


@pytest.mark.asyncio
async def test_authority_denied_blocks_the_run_and_reports_a_failed_outcome_with_pin_hashes():
    from apps.cosa.company.executive_board_client import ExecutiveBoardAuthorityError

    runner = MagicMock()
    runner.run = AsyncMock()
    plane = make_plane(runner)
    plane.executive_board_client.get_deliberation_authority = AsyncMock(
        side_effect=ExecutiveBoardAuthorityError("paused deployment", status_code=412)
    )

    res = await execute_executive_deliberation_framed_task(plane, None, make_payload())

    runner.run.assert_not_awaited()
    body = plane.executive_board_client.submit_analysis_callback.call_args.kwargs["payload"]
    assert res["results"][0]["outcome"] == "executive.analysis.failed.v1"
    assert "AUTHORITY_DENIED" in body["error_detail"]
    assert body["overlay_pin_hash"] == build_pin("cfo").overlay.identity_hash()


@pytest.mark.asyncio
async def test_authority_pin_drift_blocks_the_run():
    runner = MagicMock()
    runner.run = AsyncMock()
    plane = make_plane(runner)
    drifted = camel_pin("cfo")
    drifted["deployment"]["specHash"] = "0" * 64
    plane.executive_board_client.get_deliberation_authority = AsyncMock(
        return_value={"rolePin": drifted}
    )

    await execute_executive_deliberation_framed_task(plane, None, make_payload())

    runner.run.assert_not_awaited()
    body = plane.executive_board_client.submit_analysis_callback.call_args.kwargs["payload"]
    assert "PIN_DRIFT" in body["error_detail"]


@pytest.mark.asyncio
@pytest.mark.parametrize("mutate", ["no_deployment", "no_overlay_hash", "no_skills", "role_mismatch"])
async def test_malformed_pin_payload_fails_without_running_or_defaulting(mutate):
    raw = camel_pin("cfo")
    if mutate == "no_deployment":
        del raw["deployment"]
    elif mutate == "no_overlay_hash":
        del raw["overlay"]["overlaySpecHash"]
    elif mutate == "no_skills":
        raw["overlay"]["skillPins"] = []
    else:
        raw["overlay"]["roleKey"] = "cmo"
    runner = MagicMock()
    runner.run = AsyncMock()
    plane = make_plane(runner)

    with pytest.raises(ExecutiveBoardPayloadError):
        await execute_executive_deliberation_framed_task(
            plane, None, make_payload(selected_roles=[raw])
        )
    runner.run.assert_not_awaited()
    plane.executive_board_client.submit_analysis_callback.assert_not_awaited()


@pytest.mark.asyncio
async def test_payload_requires_workspace_project_and_deliberation():
    plane = make_plane(MagicMock())
    with pytest.raises(ValueError, match="Missing required fields"):
        await execute_executive_deliberation_framed_task(
            plane, None, make_payload(project_id=None)
        )
