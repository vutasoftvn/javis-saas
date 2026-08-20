import logging

from app.workforce.agents.delegation.provider import DelegationProvider

logger = logging.getLogger(__name__)


class DelegationProviderUnknown(RuntimeError):
    """Raised when governed routing names an unregistered provider."""


class DelegationProviderManager:
    """Fail-closed registry for delegation provider adapters."""

    def __init__(self) -> None:
        self._providers: dict[str, DelegationProvider] = {}
        self._is_started = False

    def register(self, provider: DelegationProvider) -> None:
        self._providers[provider.provider_name] = provider
        logger.info(
            "[DelegationProviderManager] Registered provider: '%s'",
            provider.provider_name,
        )

    async def start(self) -> None:
        if "in_process" not in self._providers:
            from app.workforce.agents.delegation.providers.in_process import (
                InProcessSubagentProvider,
            )

            self.register(InProcessSubagentProvider())
        self._is_started = True

    async def stop(self) -> None:
        self._is_started = False

    def get(self, provider_name: str) -> DelegationProvider:
        try:
            return self._providers[provider_name]
        except KeyError as exc:
            raise DelegationProviderUnknown(
                f"Delegation provider '{provider_name}' is not registered. "
                f"Available providers: {list(self._providers.keys())}"
            ) from exc

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())


delegation_provider_manager = DelegationProviderManager()
