from abc import ABC, abstractmethod

from workforce.agents.execution.long_running.types import (
    CancelResult,
    WorkContext,
    WorkHandle,
    WorkProviderCapabilities,
    WorkProviderHealth,
    WorkRequest,
    WorkStatus,
)


class LongRunningWorkProvider(ABC):
    """Provider-neutral contract for externally durable asynchronous work."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    async def start(
        self,
        context: WorkContext,
        request: WorkRequest,
        idempotency_key: str,
    ) -> WorkHandle:
        ...

    @abstractmethod
    async def poll(self, context: WorkContext, handle: WorkHandle) -> WorkStatus:
        ...

    @abstractmethod
    async def cancel(self, context: WorkContext, handle: WorkHandle) -> CancelResult:
        ...

    @abstractmethod
    async def health(self) -> WorkProviderHealth:
        ...

    @abstractmethod
    async def capabilities(self) -> WorkProviderCapabilities:
        ...
