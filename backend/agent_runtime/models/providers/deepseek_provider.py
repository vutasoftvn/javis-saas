"""
DeepSeek Model Provider Adapter (Reasoning R1 & General V3)
Hỗ trợ cả DeepSeek Cloud API và Local vLLM/Ollama endpoints (Structure.md Mục 30).
"""
import time
from typing import Any, Dict
from agent_runtime.models.base import ModelCallPayload, ModelCapabilityPolicy, ModelProviderInterface, ModelResponse


class DeepSeekProvider(ModelProviderInterface):
    """Hiện thực Adapter cho DeepSeek Models"""

    def __init__(self, api_key: str = "mock-deepseek-key", base_url: str = "https://api.deepseek.com"):
        self.api_key = api_key
        self.base_url = base_url

    async def generate(self, payload: ModelCallPayload) -> ModelResponse:
        start_time = time.time()
        # Xác định model cụ thể dựa theo policy
        model_name = "deepseek-reasoner" if payload.policy == ModelCapabilityPolicy.REASONING else "deepseek-chat"

        # Mock reasoning response logic
        last_msg = payload.messages[-1].get("content", "") if payload.messages else ""
        content = f"[DeepSeek {model_name}] Phân tích chiến lược: Đã xử lý yêu cầu '{last_msg[:50]}...'"
        
        duration_ms = int((time.time() - start_time) * 1000)
        return ModelResponse(
            content=content,
            tool_calls=[],
            model_name=model_name,
            provider="deepseek",
            usage={"prompt_tokens": 150, "completion_tokens": 80},
            duration_ms=duration_ms
        )
