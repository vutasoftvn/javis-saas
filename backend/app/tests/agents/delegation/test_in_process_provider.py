import pytest

from app.workforce.agents.delegation.types import (
    DelegationRequest,
    DelegationStatus,
)
from app.workforce.agents.runtime.adapters.mock import MockRuntime
from app.workforce.agents.runtime.errors import AgentRuntimeError
from app.workforce.agents.runtime.manager import AgentRuntimeManager


def _request(runtime_name: str = "mock") -> DelegationRequest:
    return DelegationRequest(
        workspace_id=1,
        outcome_run_id=2,
        run_step_id=3,
        root_agent_run_id=4,
        parent_agent_run_id=4,
        profile_id="marketing",
        provider_name="in_process",
        runtime_name=runtime_name,
        task="Analyze the funnel",
        permission_profile="read_only",
        context={"user_id": 5, "structured_output": {"leads": 12}},
    )


@pytest.mark.asyncio
async def test_in_process_provider_runs_once_and_exposes_terminal_poll_result():
    from app.workforce.agents.delegation.providers.in_process import (
        InProcessSubagentProvider,
    )

    manager = AgentRuntimeManager()
    manager.register(MockRuntime())
    provider = InProcessSubagentProvider(manager)

    handle = await provider.delegate(_request(), "delegate:3:1")
    result = await provider.poll(handle)

    assert handle.provider_name == "in_process"
    assert result.status == DelegationStatus.SUCCEEDED
    assert result.structured_result == {"leads": 12}
    assert "Analyze the funnel" in (result.output_text or "")


@pytest.mark.asyncio
async def test_in_process_provider_never_falls_back_for_explicit_runtime():
    from app.workforce.agents.delegation.providers.in_process import (
        InProcessSubagentProvider,
    )

    manager = AgentRuntimeManager()
    manager.register(MockRuntime())
    provider = InProcessSubagentProvider(manager)

    with pytest.raises(AgentRuntimeError) as error:
        await provider.delegate(_request("missing"), "delegate:3:1")

    assert error.value.code == "AGENT_RUNTIME_UNAVAILABLE"
