"""Factory tạo ChatProvider theo tên provider + model. Nguồn sự thật duy nhất về provider
nào tồn tại - AIRouter và worker không tự new() client, luôn đi qua build_provider() để
không có chỗ nào quên đăng ký provider mới."""

from app.integrations.anthropic_client import AnthropicClient
from app.integrations.deepseek_client import DeepSeekClient
from app.integrations.gemini_client import GeminiClient
from app.integrations.openai_client import OpenAIClient
from app.integrations.openrouter_client import OpenRouterClient
from app.modules.chat.ai_router import ChatProvider

_BUILDERS = {
    "deepseek": DeepSeekClient,
    "openai": OpenAIClient,
    "openrouter": OpenRouterClient,
    "anthropic": AnthropicClient,
    "gemini": GeminiClient,
}


def build_provider(provider: str, model: str) -> ChatProvider:
    builder = _BUILDERS.get(provider)
    if builder is None:
        raise ValueError(f"Unknown provider: {provider}")
    return builder(model=model)
