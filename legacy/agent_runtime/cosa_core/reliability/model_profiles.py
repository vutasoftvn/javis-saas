from typing import Dict, Optional
from pydantic import BaseModel, Field


class ModelProfile(BaseModel):
    name: str
    description: str
    primary_provider: str
    primary_model: str
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
    timeout_seconds: float = 30.0
    cost_per_1k_input: float = 0.00014  # USD
    cost_per_1k_output: float = 0.00028 # USD


class ModelProfileRegistry:
    """Manages system-wide AI Model Profiles decoupling business code from hardcoded model names."""

    _PROFILES: Dict[str, ModelProfile] = {
        "chat_fast": ModelProfile(
            name="chat_fast",
            description="Ultra-low latency model for conversational chitchat and quick summaries.",
            primary_provider="deepseek",
            primary_model="deepseek-chat",
            fallback_provider="anthropic",
            fallback_model="claude-3-5-haiku-20241022",
            timeout_seconds=15.0,
            cost_per_1k_input=0.00014,
            cost_per_1k_output=0.00028,
        ),
        "reasoning": ModelProfile(
            name="reasoning",
            description="High-capacity reasoning model for strategic synthesis, complex analysis, and coding.",
            primary_provider="deepseek",
            primary_model="deepseek-reasoner",
            fallback_provider="anthropic",
            fallback_model="claude-3-7-sonnet-20250219",
            timeout_seconds=60.0,
            cost_per_1k_input=0.00055,
            cost_per_1k_output=0.00219,
        ),
        "extraction": ModelProfile(
            name="extraction",
            description="Strict JSON/Schema extraction model for parser and tool bridge conversions.",
            primary_provider="deepseek",
            primary_model="deepseek-chat",
            fallback_provider="openai",
            fallback_model="gpt-4o-mini",
            timeout_seconds=20.0,
            cost_per_1k_input=0.00014,
            cost_per_1k_output=0.00028,
        ),
        "local_embedding": ModelProfile(
            name="local_embedding",
            description="Local vector embedding for private knowledge retrieval via pgvector.",
            primary_provider="local",
            primary_model="bge-m3",
            fallback_provider=None,
            fallback_model=None,
            timeout_seconds=5.0,
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0,
        ),
    }

    @classmethod
    def get_profile(cls, name: str) -> ModelProfile:
        return cls._PROFILES.get(name) or cls._PROFILES["chat_fast"]

    @classmethod
    def register_profile(cls, profile: ModelProfile) -> None:
        cls._PROFILES[profile.name] = profile

    @classmethod
    def list_profiles(cls) -> list[ModelProfile]:
        return list(cls._PROFILES.values())
