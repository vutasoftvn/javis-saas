import pytest
import os
from unittest.mock import patch

from app.workforce.chat.model_registry import (
    list_models,
    get_model,
    is_known,
    is_provider_configured,
    is_selectable,
    _FALLBACK_PROVIDER,
    _FALLBACK_MODEL,
)
from app.workforce.chat.providers import build_provider
from app.integrations.llm_providers.kira_ai_client import KiraAIClient


def test_kira_ai_models_registered():
    models = list_models()
    kira_models = [m for m in models if m.provider == "kira_ai"]
    assert len(kira_models) >= 8

    # Default model deepseek-v4-pro-free exists
    default_m = get_model("kira_ai", "deepseek-v4-pro-free")
    assert default_m is not None
    assert default_m.label == "DeepSeek V4 Pro Free (Kira AI)"
    assert default_m.supports_tools is True

    # Fallback constants
    assert _FALLBACK_PROVIDER == "kira_ai"
    assert _FALLBACK_MODEL == "deepseek-v4-pro-free"


def test_kira_ai_provider_configured_env():
    with patch.dict(os.environ, {"KIRAAI_API_KEY": "sk-kira-test-key-123"}, clear=False):
        assert is_provider_configured("kira_ai") is True
        assert is_selectable("kira_ai", "deepseek-v4-pro-free") is True


def test_kira_ai_build_provider():
    with patch.dict(os.environ, {
        "KIRAAI_API_KEY": "sk-kira-test-key-123",
        "KIRAAI_BASE_URL": "https://api.kiraai.vn/v1"
    }, clear=False):
        client = build_provider("kira_ai", "deepseek-v4-pro-free")
        assert isinstance(client, KiraAIClient)
        assert client.model == "deepseek-v4-pro-free"
        assert client.base_url == "https://api.kiraai.vn/v1"
        assert client.api_key == "sk-kira-test-key-123"
