import pytest
from app.workforce.agents.execution.adapters.mock import MockExecutor
from app.workforce.agents.execution.types import SandboxPolicy


@pytest.mark.asyncio
async def test_mock_command_timeout(mock_executor: MockExecutor, sample_policy: SandboxPolicy):
    sandbox_id = await mock_executor.create_workspace(sample_policy)
    res = await mock_executor.execute(sandbox_id, "sleep_forever", timeout_seconds=1)
    
    assert res.status == "timeout"
    assert res.exit_code == -1
