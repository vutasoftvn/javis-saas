"""
OpenAI / OpenRouter Fallback Provider
"""
import time
from typing import Any, Dict
from agent.models.base import ModelCallPayload, ModelCapabilityPolicy, ModelProviderInterface, ModelResponse


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
