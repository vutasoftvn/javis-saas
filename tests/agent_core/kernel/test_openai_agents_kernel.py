from __future__ import annotations

import pytest

from agent_core.contracts.run import RunRequest, RunStatus
from agent_core.contracts.spec import AgentSpec
from agent_core.kernel.openai_agents_kernel import OpenAIAgentsKernel
from agent_core.runs.repository import InMemoryRunRepository


@pytest.mark.asyncio
async def test_kernel_end_to_end_execution_and_event_logging():
    repo = InMemoryRunRepository()
    kernel = OpenAIAgentsKernel(repository=repo)

    spec = AgentSpec(
        id="general_assistant",
        instructions="You are a helpful assistant.",
    )
    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "Hello world"},
    )

    result = await kernel.run(request, spec)

    assert result.status == RunStatus.COMPLETED
    assert "Processed: Hello world" in str(result.final_output)

    # Verify event ledger
    events = await repo.list_events(result.run_id)
    event_types = [e.event_type for e in events]
    assert "run.started" in event_types
    assert "message.delta" in event_types
    assert "run.completed" in event_types


@pytest.mark.asyncio
async def test_kernel_approval_pause_and_resume():
    repo = InMemoryRunRepository()

    def mock_executor(tool_name, args):
        return {"payout_id": "po_999", "status": "sent"}

    kernel = OpenAIAgentsKernel(
        repository=repo,
        capability_executor=mock_executor,
    )

    spec = AgentSpec(id="finance_agent", instructions="Handle payouts.")
    request = RunRequest(
        principal="finance_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "Transfer $1,000 to vendor_1"},
    )

    # 1. Chạy lần đầu -> phát hiện transfer -> pause WAITING_APPROVAL
    result = await kernel.run(request, spec)
    assert result.status == RunStatus.WAITING_APPROVAL
    assert len(result.interruptions_waits) == 1

    wait = result.interruptions_waits[0]
    ckpt_ref = wait.checkpoint_ref
    appr_id = wait.related_ref

    # Verify approval record created in repository
    appr_record = await repo.get_approval(appr_id)
    assert appr_record is not None
    assert appr_record.status == "pending"

    # 2. Decide approval
    await repo.decide_approval(appr_id, reviewer="founder_1", approved=True)

    # 3. Resume với checkpoint_ref
    resumed = await kernel.resume(
        run_id=result.run_id,
        checkpoint_ref=ckpt_ref,
        updates={"approved": True},
    )

    assert resumed.status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_kernel_cancellation():
    repo = InMemoryRunRepository()
    kernel = OpenAIAgentsKernel(repository=repo)

    spec = AgentSpec(id="long_agent")
    request = RunRequest(
        principal="test_user",
        root_executable_ref=spec.to_pinned_identity(),
        input={"prompt": "Start task"},
    )

    # Tạo run record trước
    res = await kernel.run(request, spec)
    assert res.status == RunStatus.COMPLETED

    # Test cancel
    cancelled = await kernel.cancel(res.run_id, reason="User cancelled")
    assert cancelled is True

    run_rec = await repo.get_run(res.run_id)
    assert run_rec.status == RunStatus.CANCELLED
