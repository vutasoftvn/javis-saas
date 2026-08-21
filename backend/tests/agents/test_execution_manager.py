import pytest

from workforce.agents.execution.errors import ExecutionErrorCode, ExecutionRuntimeError
from workforce.agents.execution.manager import ExecutionProviderManager


@pytest.mark.asyncio
async def test_execution_manager_registers_and_gets_mock():
    mgr = ExecutionProviderManager()
    await mgr.start()

    provider = mgr.get("mock")
    assert provider.provider_name == "mock"


def test_execution_manager_raises_on_unknown_provider():
    mgr = ExecutionProviderManager()

    with pytest.raises(ExecutionRuntimeError) as exc_info:
        mgr.get("unknown_provider_xyz")

    assert exc_info.value.code == ExecutionErrorCode.EXEC_PROVIDER_UNKNOWN
    assert "unknown_provider_xyz" in exc_info.value.message
