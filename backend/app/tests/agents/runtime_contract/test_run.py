import pytest
from app.agents.runtime.base import AgentRuntime
from app.agents.runtime.types import AgentRunRequest, AgentRunResult
from app.tests.agents.runtime_contract.conftest import skip_without_dsh_live


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "runtime_fixture",
    ["mock_runtime", pytest.param("dsh_runtime", marks=skip_without_dsh_live)],
)
async def test_runtime_contract_run_success(runtime_fixture, request, sample_request: AgentRunRequest):
    runtime: AgentRuntime = request.getfixturevalue(runtime_fixture)
    
    result: AgentRunResult = await runtime.run(sample_request)

    assert result is not None
    assert isinstance(result.run_id, str)
    assert len(result.run_id) > 0
    assert result.runtime == runtime.runtime_name
    assert result.agent_key == sample_request.agent_key
    assert result.status == "completed"
    assert result.output_text is not None


@pytest.mark.asyncio
async def test_mock_runtime_with_tools(mock_runtime, sample_request: AgentRunRequest):
    sample_request.context["simulate_tools"] = True
    result = await mock_runtime.run(sample_request)

    assert result.status == "completed"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["tool"] == "mock_read_data"


@pytest.mark.asyncio
async def test_mock_runtime_resume(mock_runtime, sample_request: AgentRunRequest):
    session_id = "test_session_123"
    result = await mock_runtime.resume(session_id, sample_request)

    assert result.status == "completed"
    assert result.runtime_session_id == session_id
