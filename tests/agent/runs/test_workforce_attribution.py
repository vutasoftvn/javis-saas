from __future__ import annotations

import pytest
from agent.runs.models import RunRecord, WorkforceRunAttribution
from agent.runs.repository import InMemoryRunRepository


@pytest.mark.asyncio
async def test_run_record_round_trips_workforce_attribution() -> None:
    repo = InMemoryRunRepository()
    attribution = WorkforceRunAttribution(
        agent_instance_id="emp_1",
        assignment_id="as_1",
        work_package_id="wp_1",
        work_attempt_id="wa_1",
    )
    await repo.create_run(
        RunRecord(
            run_id="run_wf_1",
            workspace_id="ws_a",
            principal="system:workforce",
            root_executable_id="cosa.agents.operations",
            workforce_attribution=attribution,
        )
    )
    fetched = await repo.get_run("run_wf_1")
    assert fetched is not None
    assert fetched.workforce_attribution == attribution


@pytest.mark.asyncio
async def test_non_workforce_run_has_null_attribution() -> None:
    repo = InMemoryRunRepository()
    await repo.create_run(
        RunRecord(
            run_id="run_plain",
            workspace_id="ws_a",
            principal="user:1",
            root_executable_id="cosa.agents.operations",
        )
    )
    fetched = await repo.get_run("run_plain")
    assert fetched is not None
    assert fetched.workforce_attribution is None


@pytest.mark.asyncio
async def test_attach_workforce_attribution_is_immutable_addendum() -> None:
    repo = InMemoryRunRepository()
    await repo.create_run(
        RunRecord(
            run_id="run_wf_2",
            workspace_id="ws_a",
            principal="system:workforce",
            root_executable_id="cosa.agents.operations",
        )
    )
    attribution = WorkforceRunAttribution(
        agent_instance_id="emp_2",
        assignment_id="as_2",
        work_package_id="wp_2",
        work_attempt_id="wa_2",
    )
    updated = await repo.attach_workforce_attribution("run_wf_2", attribution)
    assert updated is not None
    assert updated.workforce_attribution == attribution
    assert (await repo.get_run("run_wf_2")).workforce_attribution == attribution

    # attach on an unknown run returns None (no ghost rows).
    assert await repo.attach_workforce_attribution("nope", attribution) is None


@pytest.mark.asyncio
async def test_reassignment_does_not_transfer_approval_between_attempts() -> None:
    """Approval bind vào run_id + tool_call_id + checkpoint_ref. Attempt mới =
    run_id mới, nên approval của attempt cũ KHÔNG chuyển sang (spec §13.7)."""
    repo = InMemoryRunRepository()
    old_attr = WorkforceRunAttribution(
        agent_instance_id="emp_1",
        assignment_id="as_1",
        work_package_id="wp_1",
        work_attempt_id="wa_1",
    )
    new_attr = WorkforceRunAttribution(
        agent_instance_id="emp_2",
        assignment_id="as_2",
        work_package_id="wp_1",
        work_attempt_id="wa_2",
    )
    await repo.create_run(
        RunRecord(
            run_id="run_old",
            workspace_id="ws_a",
            principal="system:workforce",
            root_executable_id="cosa.agents.operations",
            workforce_attribution=old_attr,
        )
    )
    from agent.runs.models import RunApprovalRecord

    await repo.create_approval(
        RunApprovalRecord(
            approval_id="appr_1",
            run_id="run_old",
            tool_call_id="call_1",
            checkpoint_ref="ckpt_1",
        )
    )
    await repo.create_run(
        RunRecord(
            run_id="run_new",
            workspace_id="ws_a",
            principal="system:workforce",
            root_executable_id="cosa.agents.operations",
            workforce_attribution=new_attr,
        )
    )

    appr = await repo.get_approval("appr_1")
    assert appr is not None and appr.run_id == "run_old"
    # Approval vẫn trỏ đúng run/tool_call/checkpoint của attempt cũ.
    by_call = await repo.get_approval_by_tool_call("call_1")
    assert by_call is not None and by_call.run_id == "run_old"
    # Attempt mới chưa có approval nào cho tool_call của riêng nó.
    assert await repo.get_approval_by_tool_call("call_2") is None
    assert (await repo.get_run("run_new")).workforce_attribution.work_attempt_id == "wa_2"
