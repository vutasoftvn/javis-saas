"""
Anthropic Claude & OpenAI Model Provider Adapters
"""
import time
from typing import Any, Dict
from agent_runtime.models.base import ModelCallPayload, ModelCapabilityPolicy, ModelProviderInterface, ModelResponse


class AnthropicProvider(ModelProviderInterface):
    """Hiện thực Adapter cho Anthropic Claude Models (Sonnet, Haiku)"""

    def __init__(self, api_key: str = "mock-anthropic-key"):
        self.api_key = api_key

    async def generate(self, payload: ModelCallPayload) -> ModelResponse:
        start_time = time.time()
        if payload.policy == ModelCapabilityPolicy.FAST:
            model_name = "claude-3-5-haiku-20241022"
        elif payload.policy == ModelCapabilityPolicy.CODING:
            model_name = "claude-3-7-sonnet-20250219"
        else:
            model_name = "claude-3-7-sonnet-20250219"

        last_msg = payload.messages[-1].get("content", "") if payload.messages else ""
        content = f"[Anthropic {model_name}] Phản hồi cho: '{last_msg[:50]}...'"

        duration_ms = int((time.time() - start_time) * 1000)
        return ModelResponse(
            content=content,
            tool_calls=[],
            model_name=model_name,
            provider="anthropic",
            usage={"prompt_tokens": 120, "completion_tokens": 60},
            duration_ms=duration_ms
        )


class OpenAIProvider(ModelProviderInterface):
    """Hiện thực Fallback Adapter cho OpenAI / OpenRouter Models"""

    def __init__(self, api_key: str = "mock-openai-key"):
        self.api_key = api_key

    async def generate(self, payload: ModelCallPayload) -> ModelResponse:
        start_time = time.time()
        model_name = "gpt-4o-mini" if payload.policy == ModelCapabilityPolicy.FAST else "gpt-4o"
        last_msg = payload.messages[-1].get("content", "") if payload.messages else ""
        content = f"[OpenAI {model_name}] Phản hồi cho: '{last_msg[:50]}...'"

        duration_ms = int((time.time() - start_time) * 1000)
        return ModelResponse(
            content=content,
            tool_calls=[],
            model_name=model_name,
            provider="openai",
            usage={"prompt_tokens": 110, "completion_tokens": 50},
            duration_ms=duration_ms
        )
