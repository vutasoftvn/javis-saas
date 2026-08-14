import pytest
from app.agents.runtime.types import AgentRunRequest


@pytest.mark.asyncio
async def test_runtime_trace_collection(mock_runtime, sample_request: AgentRunRequest):
    result = await mock_runtime.run(sample_request)
    assert result.status == "completed"

    trace = await mock_runtime.get_trace(result.run_id)
    assert len(trace) >= 3

    event_types = [ev.event_type for ev in trace]
    assert "run_started" in event_types
    assert "thought" in event_types
    assert "run_completed" in event_types
    assert all(ev.run_id == result.run_id for ev in trace)
