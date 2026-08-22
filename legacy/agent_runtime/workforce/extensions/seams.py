from typing import Protocol, Any, runtime_checkable
from pydantic import BaseModel, Field

class ProviderHealth(BaseModel):
    status: str
    message: str | None = None

class DiscoveredCapability(BaseModel):
    capability_id: str
    name: str
    description: str | None = None
    input_schema: dict | None = None
    output_schema: dict | None = None
    endpoint_config: dict = Field(default_factory=dict)

class ProviderResult(BaseModel):
    status: str
    result: Any | None = None

@runtime_checkable
class ConnectorProvider(Protocol):
    async def health(self, scope: Any) -> ProviderHealth:
        ...

    async def discover(self, scope: Any, config: dict) -> tuple[DiscoveredCapability, ...]:
        ...

    async def invoke(self, scope: Any, capability: DiscoveredCapability, arguments: dict) -> ProviderResult:
        ...

@runtime_checkable
class ModelProvider(Protocol):
    async def health(self, scope: Any) -> ProviderHealth:
        ...

@runtime_checkable
class ToolBackend(Protocol):
    async def health(self, scope: Any) -> ProviderHealth:
        ...

@runtime_checkable
class ExecutorProvider(Protocol):
    async def health(self, scope: Any) -> ProviderHealth:
        ...

    async def start(self, scope: Any, config: dict, input_data: dict) -> ProviderResult:
        ...

    async def stream(self, scope: Any, run_id: str):
        ...

    async def cancel(self, scope: Any, run_id: str) -> bool:
        ...

    async def ingest_artifacts(self, scope: Any, run_id: str) -> list:
        ...

@runtime_checkable
class SandboxProvider(Protocol):
    async def health(self, scope: Any) -> ProviderHealth:
        ...

@runtime_checkable
class KnowledgeProvider(Protocol):
    async def health(self, scope: Any) -> ProviderHealth:
        ...

@runtime_checkable
class EventStore(Protocol):
    async def health(self, scope: Any) -> ProviderHealth:
        ...

@runtime_checkable
class RuntimeAdapter(Protocol):
    async def health(self, scope: Any) -> ProviderHealth:
        ...

    async def start(self, scope: Any, config: dict, input_data: dict) -> ProviderResult:
        ...

    async def stream(self, scope: Any, run_id: str):
        ...

    async def cancel(self, scope: Any, run_id: str) -> bool:
        ...

    async def ingest_artifacts(self, scope: Any, run_id: str) -> list:
        ...
