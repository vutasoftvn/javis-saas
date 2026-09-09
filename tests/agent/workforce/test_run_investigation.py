from __future__ import annotations

import pytest
from agent.runs.models import (
    RunCheckpointRecord,
    RunEventRecord,
    RunRecord,
    RunToolCallRecord,
    WorkforceRunAttribution,
)
from agent.runs.repository import InMemoryRunRepository
from agent.workforce.investigation import get_scoped_run_investigation


@pytest.mark.asyncio
async def test_investigation_reads_governance_ledger_not_sse() -> None:
    repo = InMemoryRunRepository()
    await repo.create_run(
        RunRecord(
            run_id="run_1",
            workspace_id="ws_a",
            principal="system:workforce",
            root_executable_id="cosa.agents.operations",
            workforce_attribution=WorkforceRunAttribution(
                agent_instance_id="emp_1",
                assignment_id="as_1",
                work_package_id="wp_1",
                work_attempt_id="wa_1",
            ),
        )
    )
    await repo.save_checkpoint(
        RunCheckpointRecord(
            checkpoint_ref="ckpt_1", run_id="run_1", sequence_no=1, step_name="plan"
        )
    )
    await repo.save_tool_call(
        RunToolCallRecord(
            tool_call_id="call_1",
            run_id="run_1",
            checkpoint_ref="ckpt_1",
            capability_id="operations.task.read",
            payload_hash="h",
            status="pending",
        )
    )
    await repo.append_event(
        RunEventRecord(event_id="evt_1", run_id="run_1", event_type="run.started")
    )

    inv = await get_scoped_run_investigation(repo, "run_1", "ws_a")
    assert inv is not None
    assert inv.workforce_attribution["work_attempt_id"] == "wa_1"
    assert inv.checkpoints[0]["checkpoint_ref"] == "ckpt_1"
    assert inv.tool_calls[0]["tool_call_id"] == "call_1"
    assert inv.approvals[0]["tool_call_id"] == "call_1"
    assert inv.approvals[0]["checkpoint_ref"] == "ckpt_1"
    assert any(e["event_type"] == "run.started" for e in inv.run_events)


@pytest.mark.asyncio
async def test_investigation_is_tenant_scoped() -> None:
    repo = InMemoryRunRepository()
    await repo.create_run(
        RunRecord(
            run_id="run_x",
            workspace_id="ws_a",
            principal="p",
            root_executable_id="cosa.agents.operations",
        )
    )
    assert await get_scoped_run_investigation(repo, "run_x", "ws_OTHER") is None
    assert await get_scoped_run_investigation(repo, "nope", "ws_a") is None
