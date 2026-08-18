"""Factory tạo ChatProvider theo tên provider + model. Nguồn sự thật duy nhất về provider
nào tồn tại - AIRouter và worker không tự new() client, luôn đi qua build_provider() để
không có chỗ nào quên đăng ký provider mới."""

from app.integrations.llm_providers.anthropic_client import AnthropicClient
from app.integrations.llm_providers.apiai_vn_client import ApiAIVnClient
from app.integrations.llm_providers.deepseek_client import DeepSeekClient
from app.integrations.llm_providers.gemini_client import GeminiClient
from app.integrations.llm_providers.openai_client import OpenAIClient
from app.integrations.llm_providers.openrouter_client import OpenRouterClient
from app.workforce.chat.ai_router import ChatProvider

_BUILDERS = {
    "deepseek": DeepSeekClient,
    "openai": OpenAIClient,
    "openrouter": OpenRouterClient,
    "anthropic": AnthropicClient,
    "gemini": GeminiClient,
    "apiai_vn": ApiAIVnClient,
}


# Provider có thể lấy khoá từ workspace_secrets chứ không chỉ từ biến môi trường. Truyền
# workspace_id ở mọi chỗ biết được nó, để một workspace không bao giờ tiêu khoá (và hoá
# đơn) của workspace khác - chỉ khi thật sự không có ngữ cảnh mới để None.
_WORKSPACE_SCOPED = {"openrouter"}


def build_provider(provider: str, model: str, workspace_id: int | None = None) -> ChatProvider:
    builder = _BUILDERS.get(provider)
    if builder is None:
        raise ValueError(f"Unknown provider: {provider}")
    if provider in _WORKSPACE_SCOPED:
        return builder(model=model, workspace_id=workspace_id)
    return builder(model=model)
