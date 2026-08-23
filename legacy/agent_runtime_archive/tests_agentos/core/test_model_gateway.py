from __future__ import annotations

import pytest

from agentos.core.adapters.anthropic_provider import AnthropicModelProvider
from agentos.core.adapters.deepseek_harness_provider import DeepSeekHarnessModelProvider
from agentos.core.adapters.model_gateway import build_model_provider
from agentos.core.adapters.openai_compatible_provider import OpenAICompatibleModelProvider
from agentos.core.model_provider import ModelProvider


def test_defaults_to_deepseek_when_unset(monkeypatch):
    monkeypatch.delenv("CHAT_DEFAULT_PROVIDER", raising=False)
    assert isinstance(build_model_provider(), DeepSeekHarnessModelProvider)


def test_reads_chat_default_provider_env(monkeypatch):
    monkeypatch.setenv("CHAT_DEFAULT_PROVIDER", "openai")
    assert isinstance(build_model_provider(), OpenAICompatibleModelProvider)


@pytest.mark.parametrize(
    "name,expected_cls",
    [
        ("deepseek", DeepSeekHarnessModelProvider),
        ("openai", OpenAICompatibleModelProvider),
        ("openrouter", OpenAICompatibleModelProvider),
        ("anthropic", AnthropicModelProvider),
    ],
)
def test_explicit_provider_selection(name, expected_cls):
    provider = build_model_provider(name)
    assert isinstance(provider, expected_cls)
    assert isinstance(provider, ModelProvider)


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="unknown-provider"):
        build_model_provider("unknown-provider")
