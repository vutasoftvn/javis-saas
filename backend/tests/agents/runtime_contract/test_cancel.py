import asyncio
import pytest
from workforce.agents.runtime.types import AgentRunRequest


@pytest.mark.asyncio
async def test_runtime_cancel(mock_runtime, sample_request: AgentRunRequest):
    sample_request.context["sleep_seconds"] = 1.0

    # Start run in background
    run_task = asyncio.create_task(mock_runtime.run(sample_request))
    await asyncio.sleep(0.05)

    # Get active run id from mock runtime's active tasks
    active_run_ids = list(mock_runtime._active_tasks.keys())
    assert len(active_run_ids) == 1
    run_id = active_run_ids[0]

    # Trigger cancel
    await mock_runtime.cancel(run_id)
    result = await run_task

    assert result.status == "cancelled"
