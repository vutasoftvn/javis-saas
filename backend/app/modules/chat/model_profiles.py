"""Model Logical Profiles (mCOSA V12 Architecture §56).

Maps logical roles (STRATEGIC_ANALYZER, CONVERSATION_ROUTER, DEVELOPER_WORKER)
to (provider, model) pairs without hardcoding provider names in domain modules.
"""

import logging
import os
from typing import Tuple, Dict, Any

from app.modules.chat.model_registry import (
    is_known,
    is_provider_configured,
    DEFAULT_PROVIDER,
    DEFAULT_MODEL,
    _first_configured,
)
from app.modules.chat.providers import build_provider
from app.modules.chat.ai_router import ChatProvider

logger = logging.getLogger(__name__)

PROFILE_STRATEGIC_ANALYZER = "STRATEGIC_ANALYZER"
PROFILE_CONVERSATION_ROUTER = "CONVERSATION_ROUTER"
PROFILE_DEVELOPER_WORKER = "DEVELOPER_WORKER"

ALL_PROFILES = [
    PROFILE_STRATEGIC_ANALYZER,
    PROFILE_CONVERSATION_ROUTER,
    PROFILE_DEVELOPER_WORKER,
]

_DEFAULT_PROFILES = {
    PROFILE_STRATEGIC_ANALYZER: ("openai", "gpt-4o"),
    PROFILE_CONVERSATION_ROUTER: ("deepseek", "deepseek-chat"),
    PROFILE_DEVELOPER_WORKER: ("anthropic", "claude-3-5-sonnet-latest"),
}

_ENV_PROFILE_PREFIX = {
    PROFILE_STRATEGIC_ANALYZER: "STRATEGIC_ANALYZER",
    PROFILE_CONVERSATION_ROUTER: "CONVERSATION_ROUTER",
    PROFILE_DEVELOPER_WORKER: "DEVELOPER_WORKER",
}


def resolve_profile(profile_name: str) -> Tuple[str, str]:
    """Resolve a logical profile to an active (provider, model) tuple.
    
    Reads from environment overrides, validates availability, and gracefully
    falls back to the first configured provider or default provider.
    """
    normalized_profile = profile_name.upper().strip()
    env_prefix = _ENV_PROFILE_PREFIX.get(normalized_profile)

    if env_prefix:
        env_provider = os.environ.get(f"{env_prefix}_PROVIDER", "").strip()
        env_model = os.environ.get(f"{env_prefix}_MODEL", "").strip()
        if env_provider and env_model and is_known(env_provider, env_model):
            if is_provider_configured(env_provider):
                return env_provider, env_model
            logger.warning(
                "Configured profile %s (%s/%s) lacks API credentials",
                normalized_profile, env_provider, env_model
            )

    default_pair = _DEFAULT_PROFILES.get(normalized_profile)
    if default_pair:
        prov, mdl = default_pair
        if is_provider_configured(prov):
            return prov, mdl

    first_avail = _first_configured()
    if first_avail:
        return first_avail

    return DEFAULT_PROVIDER, DEFAULT_MODEL


def build_profile_provider(profile_name: str) -> ChatProvider:
    """Instantiate a ChatProvider for a logical profile."""
    provider, model = resolve_profile(profile_name)
    return build_provider(provider, model)


def list_profile_mappings() -> Dict[str, Dict[str, Any]]:
    """Return all logical profiles with their currently resolved provider and model."""
    result = {}
    for prof in ALL_PROFILES:
        prov, mdl = resolve_profile(prof)
        result[prof] = {
            "profile": prof,
            "provider": prov,
            "model": mdl,
            "configured": is_provider_configured(prov),
        }
    return result
