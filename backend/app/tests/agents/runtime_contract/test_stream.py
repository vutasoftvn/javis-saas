import pytest
from app.agents.runtime.types import AgentEvent, AgentRunRequest


@pytest.mark.asyncio
async def test_mock_runtime_stream(mock_runtime, sample_request: AgentRunRequest):
    events: list[AgentEvent] = []
    async for event in mock_runtime.stream(sample_request):
        events.append(event)

    assert len(events) >= 3
    event_types = [e.event_type for e in events]
    assert "run_started" in event_types
    assert "thought" in event_types
    assert "run_completed" in event_types


@pytest.mark.asyncio
async def test_dsh_runtime_stream(dsh_runtime, sample_request: AgentRunRequest):
    events: list[AgentEvent] = []
    async for event in dsh_runtime.stream(sample_request):
        events.append(event)

    assert len(events) >= 2
    event_types = [e.event_type for e in events]
    assert "run_started" in event_types
