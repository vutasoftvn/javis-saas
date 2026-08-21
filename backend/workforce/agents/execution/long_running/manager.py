import logging

from workforce.agents.execution.long_running.base import LongRunningWorkProvider

logger = logging.getLogger(__name__)


class LongRunningProviderUnknown(RuntimeError):
    pass


class LongRunningWorkProviderManager:
    """Fail-closed registry for long-running work implementations."""

    def __init__(self) -> None:
        self._providers: dict[str, LongRunningWorkProvider] = {}

    def register(self, provider: LongRunningWorkProvider) -> None:
        self._providers[provider.provider_name] = provider
        logger.info(
            "[LongRunningWorkProviderManager] Registered provider: '%s'",
            provider.provider_name,
        )

    def get(self, provider_name: str) -> LongRunningWorkProvider:
        try:
            return self._providers[provider_name]
        except KeyError as exc:
            raise LongRunningProviderUnknown(
                f"Long-running provider '{provider_name}' is not registered. "
                f"Available providers: {list(self._providers.keys())}"
            ) from exc

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())


long_running_provider_manager = LongRunningWorkProviderManager()
