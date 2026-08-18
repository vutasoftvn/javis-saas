import pytest
from app.workforce.chat.model_profiles import (
    resolve_profile,
    build_profile_provider,
    list_profile_mappings,
    PROFILE_STRATEGIC_ANALYZER,
    PROFILE_CONVERSATION_ROUTER,
    PROFILE_DEVELOPER_WORKER,
)
from app.workforce.chat.model_registry import _PROVIDER_KEY_ENV


def _forget_every_provider_key(monkeypatch):
    for provider, key_env in _PROVIDER_KEY_ENV.items():
        monkeypatch.delenv(key_env, raising=False)
        monkeypatch.delenv(f"PROVIDER_CONFIGURED_{provider.upper()}", raising=False)


def test_resolve_profile_with_environment_override(monkeypatch):
    _forget_every_provider_key(monkeypatch)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek-test")
    monkeypatch.setenv("CONVERSATION_ROUTER_PROVIDER", "deepseek")
    monkeypatch.setenv("CONVERSATION_ROUTER_MODEL", "deepseek-chat")

    prov, model = resolve_profile(PROFILE_CONVERSATION_ROUTER)
    assert prov == "deepseek"
    assert model == "deepseek-chat"


def test_resolve_profile_fallback_when_default_not_configured(monkeypatch):
    _forget_every_provider_key(monkeypatch)
    # Only openrouter is configured
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

    prov, model = resolve_profile(PROFILE_STRATEGIC_ANALYZER)
    # Should fall back to first configured provider
    assert prov == "openrouter"


def test_list_profile_mappings():
    mappings = list_profile_mappings()
    assert PROFILE_STRATEGIC_ANALYZER in mappings
    assert PROFILE_CONVERSATION_ROUTER in mappings
    assert PROFILE_DEVELOPER_WORKER in mappings
    assert "provider" in mappings[PROFILE_STRATEGIC_ANALYZER]
    assert "model" in mappings[PROFILE_STRATEGIC_ANALYZER]
