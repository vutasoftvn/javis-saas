import pytest
from typing import Any
from workforce.extensions.seams import RuntimeAdapter, ExecutorProvider, ProviderHealth, ProviderResult

class FakeRuntimeAdapter:
    async def health(self, scope: Any) -> ProviderHealth:
        return ProviderHealth(status="ok")
        
    async def start(self, scope: Any, config: dict, input_data: dict) -> ProviderResult:
        return ProviderResult(status="started", result="run_123")
        
    async def stream(self, scope: Any, run_id: str):
        yield {"event": "test"}
        
    async def cancel(self, scope: Any, run_id: str) -> bool:
        return True
        
    async def ingest_artifacts(self, scope: Any, run_id: str) -> list:
        return ["artifact_1"]

class FakeExecutorProvider:
    async def health(self, scope: Any) -> ProviderHealth:
        return ProviderHealth(status="ok")
        
    async def start(self, scope: Any, config: dict, input_data: dict) -> ProviderResult:
        return ProviderResult(status="started", result="exec_123")
        
    async def stream(self, scope: Any, run_id: str):
        yield {"event": "test"}
        
    async def cancel(self, scope: Any, run_id: str) -> bool:
        return True
        
    async def ingest_artifacts(self, scope: Any, run_id: str) -> list:
        return ["artifact_1"]

@pytest.mark.asyncio
async def test_runtime_adapter_contract():
    adapter = FakeRuntimeAdapter()
    assert isinstance(adapter, RuntimeAdapter)
    
    health = await adapter.health(None)
    assert health.status == "ok"
    
    result = await adapter.start(None, {}, {})
    assert result.status == "started"

@pytest.mark.asyncio
async def test_executor_provider_contract():
    provider = FakeExecutorProvider()
    assert isinstance(provider, ExecutorProvider)
    
    cancel_result = await provider.cancel(None, "exec_123")
    assert cancel_result is True
