import os
import httpx

from integrations.llm_providers._openai_compatible import OpenAICompatibleClient


class DeepSeekClient(OpenAICompatibleClient):
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        # Nếu không có DEEPSEEK_API_KEY riêng, tự động dùng OPENROUTER_API_KEY làm fallback
        dp_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        or_key = os.environ.get("OPENROUTER_API_KEY", "").strip()

        if api_key is not None:
            resolved_key = api_key
            resolved_base_url = base_url or os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            resolved_model = model or os.environ.get("DEEPSEEK_DEFAULT_MODEL", "deepseek-chat")
        elif dp_key:
            resolved_key = dp_key
            resolved_base_url = base_url or os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            resolved_model = model or os.environ.get("DEEPSEEK_DEFAULT_MODEL", "deepseek-chat")
        elif or_key:
            resolved_key = or_key
            resolved_base_url = base_url or os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
            resolved_model = "deepseek/deepseek-chat" if (model in (None, "deepseek-chat")) else model
        else:
            resolved_key = ""
            resolved_base_url = base_url or "https://api.deepseek.com"
            resolved_model = model or "deepseek-chat"

        super().__init__(
            api_key=resolved_key,
            base_url=resolved_base_url,
            model=resolved_model,
            transport=transport,
        )
        self._api_key = resolved_key
        self._base_url = resolved_base_url
        self._model = resolved_model

