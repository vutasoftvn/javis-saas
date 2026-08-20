"""
COSA Multi-LLM Model Gateway Router
Điều phối thông minh giữa các Model Provider theo Capability Policy (Structure.md Mục 30).
"""
import logging
from typing import Dict, Optional
from agent.models.base import ModelCallPayload, ModelCapabilityPolicy, ModelProviderInterface, ModelResponse
from agent.models.providers import AnthropicProvider, DeepSeekProvider, OpenAIProvider

logger = logging.getLogger(__name__)


class ModelGateway:
    """Gateway định tuyến LLM có hỗ trợ tự động chuyển đổi Fallback"""

    def __init__(
        self,
        deepseek_provider: Optional[DeepSeekProvider] = None,
        anthropic_provider: Optional[AnthropicProvider] = None,
        openai_provider: Optional[OpenAIProvider] = None
    ):
        self.deepseek = deepseek_provider or DeepSeekProvider()
        self.anthropic = anthropic_provider or AnthropicProvider()
        self.openai = openai_provider or OpenAIProvider()

    async def generate(self, payload: ModelCallPayload) -> ModelResponse:
        """Định tuyến gọi Model Provider phù hợp nhất với Capability Policy"""
        primary_provider = self._select_primary_provider(payload.policy)
        try:
            return await primary_provider.generate(payload)
        except Exception as e:
            logger.warning(f"Primary provider failed: {e}. Switching to OpenAI fallback.")
            return await self.openai.generate(payload)

    def _select_primary_provider(self, policy: ModelCapabilityPolicy) -> ModelProviderInterface:
        if policy == ModelCapabilityPolicy.REASONING:
            return self.deepseek
        elif policy == ModelCapabilityPolicy.FAST:
            return self.anthropic
        elif policy == ModelCapabilityPolicy.CODING:
            return self.anthropic
        else:
            return self.openai


# Singleton instance
model_gateway = ModelGateway()
