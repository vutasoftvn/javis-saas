from __future__ import annotations

import os

from agentos.core.adapters.anthropic_provider import AnthropicModelProvider
from agentos.core.adapters.deepseek_harness_provider import DeepSeekHarnessModelProvider
from agentos.core.adapters.openai_compatible_provider import OpenAICompatibleModelProvider
from agentos.core.model_provider import ModelProvider

_SUPPORTED_PROVIDERS = ("deepseek", "openai", "openrouter", "anthropic")


class UnknownModelProviderError(ValueError):
    def __init__(self, provider: str) -> None:
        super().__init__(f"Unknown LLM provider '{provider}'. Supported: {', '.join(_SUPPORTED_PROVIDERS)}")


def build_model_provider(provider: str | None = None) -> ModelProvider:
    """Multi-provider LLM Gateway factory (agentos-native, no dependency on
    the frozen `legacy/backend` — see ADR-012 "Newly-tracked capability
    families": LLM Chat Gateway). `provider` defaults to
    `CHAT_DEFAULT_PROVIDER` (matching the env var name already used by
    `docker-compose.yml`'s `brain-api`/`agent-worker`), falling back to
    `deepseek`. Each provider reads its own API key/base URL from the same
    env var names `docker-compose.yml` already declares, so no new
    configuration is required to switch providers.
    """
    provider = (provider or os.getenv("CHAT_DEFAULT_PROVIDER") or "deepseek").lower()

    if provider == "deepseek":
        return DeepSeekHarnessModelProvider(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            model_name=os.getenv("DEEPSEEK_DEFAULT_MODEL", "deepseek-chat"),
        )
    if provider == "openai":
        return OpenAICompatibleModelProvider(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini"),
        )
    if provider == "openrouter":
        return OpenAICompatibleModelProvider(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            model=os.getenv("OPENROUTER_DEFAULT_MODEL", "deepseek/deepseek-chat"),
        )
    if provider == "anthropic":
        return AnthropicModelProvider(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            model=os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-5"),
        )

    raise UnknownModelProviderError(provider)
