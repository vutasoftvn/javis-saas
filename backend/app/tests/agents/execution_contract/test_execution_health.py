import pytest
from app.agents.execution.adapters.mock import MockExecutor
from app.agents.execution.adapters.opensandbox import OpenSandboxExecutor


@pytest.mark.asyncio
async def test_mock_health(mock_executor: MockExecutor):
    health = await mock_executor.health()
    assert health.provider == "mock"
    assert health.available is True


@pytest.mark.asyncio
async def test_opensandbox_health_structure():
    sbx_exec = OpenSandboxExecutor(domain="http://127.0.0.1:8080")
    health = await sbx_exec.health()
    assert health.provider == "opensandbox"
