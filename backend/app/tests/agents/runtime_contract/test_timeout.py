import pytest
from app.workforce.agents.runtime.errors import AgentErrorCode, AgentRuntimeError
from app.workforce.agents.runtime.types import AgentRunRequest


@pytest.mark.asyncio
async def test_runtime_timeout(mock_runtime, sample_request: AgentRunRequest):
    sample_request.timeout_seconds = 0.05
    sample_request.context["sleep_seconds"] = 1.0

    with pytest.raises(AgentRuntimeError) as exc_info:
        await mock_runtime.run(sample_request)

    assert exc_info.value.code == AgentErrorCode.AGENT_RUNTIME_TIMEOUT
    assert exc_info.value.retryable is True
