import pytest
from app.workforce.agents.runtime.errors import AgentErrorCode, AgentRuntimeError
from app.workforce.agents.runtime.types import AgentRunRequest


@pytest.mark.asyncio
async def test_mock_runtime_crash_isolation(mock_runtime, sample_request: AgentRunRequest):
    mock_runtime.set_healthy(False)

    health = await mock_runtime.health()
    assert health.status == "unavailable"

    with pytest.raises(AgentRuntimeError) as exc_info:
        await mock_runtime.run(sample_request)

    assert exc_info.value.code == AgentErrorCode.AGENT_RUNTIME_UNAVAILABLE


@pytest.mark.asyncio
async def test_dsh_runtime_missing_api_key(sample_request: AgentRunRequest):
    from app.workforce.agents.runtime.adapters.deepseek_harness import DeepSeekHarnessAdapter

    adapter = DeepSeekHarnessAdapter(api_key=None)
    health = await adapter.health()
    assert health.status == "unavailable"

    with pytest.raises(AgentRuntimeError) as exc_info:
        await adapter.run(sample_request)

    assert exc_info.value.code == AgentErrorCode.AGENT_RUNTIME_UNAVAILABLE
