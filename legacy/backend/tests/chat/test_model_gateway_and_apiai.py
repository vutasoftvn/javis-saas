import pytest
from workforce.chat.model_profiles import (
    ModelGateway,
    PROFILE_CHAT_FAST,
    PROFILE_BUSINESS_DEEP,
    PROFILE_STRUCTURED_EXTRACT,
    resolve_profile,
)
from workforce.chat.providers import build_provider
from workforce.chat.model_registry import MODELS, is_known
from integrations.llm_providers.apiai_vn_client import ApiAIVnClient


def test_model_gateway_profile_resolution():
    # 1. Check all profiles resolve to valid tuples
    for prof in (PROFILE_CHAT_FAST, PROFILE_BUSINESS_DEEP, PROFILE_STRUCTURED_EXTRACT):
        prov, mdl = ModelGateway.resolve(prof)
        assert isinstance(prov, str)
        assert isinstance(mdl, str)
        assert len(prov) > 0
        assert len(mdl) > 0


def test_apiai_vn_client_integration():
    client = ApiAIVnClient(model="apiai-fast")
    assert client.provider_name == "apiai_vn"
    assert client.model == "apiai-fast"

    # Provider factory test
    built = build_provider("apiai_vn", "apiai-fast")
    assert isinstance(built, ApiAIVnClient)

    # Registry check
    assert is_known("apiai_vn", "apiai-fast") is True
    assert is_known("apiai_vn", "apiai-pro") is True
