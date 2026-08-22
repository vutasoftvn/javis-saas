"""DSPy LM Factory resolving COSA Model Policy into configured dspy.LM instances."""

import os
from typing import Any, Dict, Optional

from workforce.agents.reliability.model_profiles import ModelProfileRegistry
from workforce.ai.model_policy.gateway_lm import GatewayLM

try:
    import dspy
except ImportError:
    dspy = None


class DSPyLMFactory:
    """Factory to build dspy.LM objects according to COSA Model Policies via ModelProfileRegistry."""

    @staticmethod
    def get_lm(
        model_policy: Optional[str] = None,
        override_model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2000,
        **kwargs: Any
    ) -> Any:
        """Resolve policy via ModelProfileRegistry and return configured dspy.LM."""
        if dspy is None:
            raise RuntimeError("DSPy 3.3.0 is not installed or available.")

        policy = (model_policy or "fast_reasoning").lower()

        # Check environment configuration / provider routing
        api_key = (
            os.getenv("APIAI_API_KEY")
            or os.getenv("DEEPSEEK_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        if not api_key or api_key.startswith("dummy") or api_key == "your_deepseek_api_key_here":
            return None
        api_base = os.getenv("APIAI_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL") or None

        # Model selection based on ModelProfileRegistry
        if override_model:
            model_name = override_model
        elif "deep_reasoning" in policy or "reasoning" in policy:
            profile = ModelProfileRegistry.get_profile("reasoning")
            model_name = f"{profile.primary_provider}/{profile.primary_model}"
        elif "creative" in policy or "fast" in policy:
            profile = ModelProfileRegistry.get_profile("chat_fast")
            model_name = f"{profile.primary_provider}/{profile.primary_model}"
        else:
            profile = ModelProfileRegistry.get_profile("extraction")
            model_name = f"{profile.primary_provider}/{profile.primary_model}"

        lm_kwargs: Dict[str, Any] = {
            "model": model_name,
            "api_key": api_key,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }
        if api_base:
            lm_kwargs["api_base"] = api_base

        return GatewayLM(**lm_kwargs)
