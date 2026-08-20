from abc import ABC, abstractmethod

from app.workforce.agents.delegation.types import (
    DelegationHandle,
    DelegationRequest,
    DelegationResult,
    ProviderHealth,
)


class DelegationProvider(ABC):
    """Provider-neutral contract for asynchronous delegated work."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Stable routing name persisted on DelegationJob."""
        ...

    @abstractmethod
    async def delegate(
        self,
        request: DelegationRequest,
        idempotency_key: str,
    ) -> DelegationHandle:
        """Start or recover one idempotent delegation attempt."""
        ...

    @abstractmethod
    async def poll(self, handle: DelegationHandle) -> DelegationResult:
        """Read current provider state without creating a new attempt."""
        ...

    @abstractmethod
    async def cancel(self, handle: DelegationHandle) -> bool:
        """Request cancellation and report whether it was accepted."""
        ...

    @abstractmethod
    async def health(self) -> ProviderHealth:
        """Report whether this provider can accept work."""
        ...
