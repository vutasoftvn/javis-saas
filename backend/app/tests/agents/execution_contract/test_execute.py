import pytest
from app.workforce.agents.execution.adapters.mock import MockExecutor
from app.workforce.agents.execution.types import SandboxPolicy


@pytest.mark.asyncio
async def test_mock_execute_success(mock_executor: MockExecutor, sample_policy: SandboxPolicy):
    sandbox_id = await mock_executor.create_workspace(sample_policy)
    res = await mock_executor.execute(sandbox_id, "python -c 'print(1+1)'", timeout_seconds=10)

    assert res.status == "completed"
    assert res.exit_code == 0
    assert "Executed:" in (res.stdout_excerpt or "")


@pytest.mark.asyncio
async def test_mock_execute_failure(mock_executor: MockExecutor, sample_policy: SandboxPolicy):
    sandbox_id = await mock_executor.create_workspace(sample_policy)
    res = await mock_executor.execute(sandbox_id, "exit 1", timeout_seconds=10)

    assert res.status == "failed"
    assert res.exit_code == 1
    assert "Mock command error" in (res.stderr_excerpt or "")
