import pytest
from workforce.agents.execution.adapters.mock import MockExecutor
from workforce.agents.execution.errors import ExecutionRuntimeError
from workforce.agents.execution.types import SandboxPolicy


@pytest.mark.asyncio
async def test_mock_provider_unavailable_raises_runtime_error(mock_executor: MockExecutor, sample_policy: SandboxPolicy):
    mock_executor.set_available(False)
    
    with pytest.raises(ExecutionRuntimeError) as exc_info:
        await mock_executor.create_workspace(sample_policy)
    
    assert exc_info.value.code == "EXEC_PROVIDER_UNAVAILABLE"
