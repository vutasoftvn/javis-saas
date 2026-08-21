import os
from integrations.llm_providers._openai_compatible import OpenAICompatibleClient


class ApiAIVnClient(OpenAICompatibleClient):
    """Client for ApiAI.vn (OpenAI-compatible Vietnamese specialized LLM provider)."""

    def __init__(self, model: str = "apiai-fast"):
        super().__init__(
            base_url=os.environ.get("APIAIVN_BASE_URL", "https://api.apiai.vn/v1"),
            api_key=os.environ.get("APIAIVN_API_KEY", ""),
            model=model,
        )
        self.provider_name = "apiai_vn"
        self.model = model
