import os

import httpx

from app.integrations._openai_compatible import OpenAICompatibleClient


class OpenAIClient(OpenAICompatibleClient):
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        super().__init__(
            api_key=api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", ""),
            base_url=base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=model or os.environ.get("OPENAI_DEFAULT_MODEL", "gpt-4o-mini"),
            transport=transport,
        )
