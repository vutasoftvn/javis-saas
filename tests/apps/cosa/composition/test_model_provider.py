from __future__ import annotations

import pytest


def test_build_deepseek_model_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    from apps.cosa.composition.model_provider import build_deepseek_model

    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
        build_deepseek_model()


def test_build_deepseek_model_returns_litellm_model_with_env_config(monkeypatch):
    pytest.importorskip("agents")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-123")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://custom.deepseek.example")
    monkeypatch.setenv("DEEPSEEK_DEFAULT_MODEL", "deepseek-reasoner")
    from agents.extensions.models.litellm_model import LitellmModel
    from apps.cosa.composition.model_provider import build_deepseek_model

    model = build_deepseek_model()

    assert isinstance(model, LitellmModel)


def test_build_deepseek_model_defaults_base_url_and_model(monkeypatch):
    pytest.importorskip("agents")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-123")
    monkeypatch.delenv("DEEPSEEK_BASE_URL", raising=False)
    monkeypatch.delenv("DEEPSEEK_DEFAULT_MODEL", raising=False)
    from agents.extensions.models.litellm_model import LitellmModel
    from apps.cosa.composition.model_provider import build_deepseek_model

    model = build_deepseek_model()

    assert isinstance(model, LitellmModel)
