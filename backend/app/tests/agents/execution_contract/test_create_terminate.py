import pytest
from app.workforce.agents.execution.adapters.mock import MockExecutor
from app.workforce.agents.execution.types import SandboxPolicy


@pytest.mark.asyncio
async def test_mock_create_and_terminate(mock_executor: MockExecutor, sample_policy: SandboxPolicy):
    sandbox_id = await mock_executor.create_workspace(sample_policy, metadata={"job_id": 123})
    assert sandbox_id.startswith("mock-sbx-")
    assert sandbox_id in mock_executor._sandboxes

    await mock_executor.terminate(sandbox_id)
    assert sandbox_id not in mock_executor._sandboxes
