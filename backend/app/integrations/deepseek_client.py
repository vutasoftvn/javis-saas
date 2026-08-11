import json
import os
from typing import AsyncIterator

import httpx

from app.modules.chat.ai_router import AIEvent, ChatTurn


class DeepSeekClient:
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
            self._api_key = api_key
            self._base_url = base_url or os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            self._model = model or os.environ.get("DEEPSEEK_DEFAULT_MODEL", "deepseek-chat")
        elif dp_key:
            self._api_key = dp_key
            self._base_url = base_url or os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            self._model = model or os.environ.get("DEEPSEEK_DEFAULT_MODEL", "deepseek-chat")
        elif or_key:
            self._api_key = or_key
            self._base_url = base_url or os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
            self._model = "deepseek/deepseek-chat" if (model in (None, "deepseek-chat")) else model
        else:
            self._api_key = ""
            self._base_url = base_url or "https://api.deepseek.com"
            self._model = model or "deepseek-chat"

        self._transport = transport

    async def stream_chat(
        self, turns: list[ChatTurn], tools: list | None = None
    ) -> AsyncIterator[AIEvent]:
    # tools: các provider này chưa nối tool-calling. Nhận rồi bỏ qua để AIRouter chỉ có
    # MỘT chữ ký duy nhất; chat_execution_service tự lọc tool theo supports_tools của
    # model nên nhánh này không bị gọi kèm tool trong thực tế.
        if not self._api_key:
            yield AIEvent(kind="failed", error_code="provider_not_configured")
            return

        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {
            "model": self._model,
            "messages": [{"role": turn.role, "content": turn.content} for turn in turns],
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                transport=self._transport,
                timeout=60.0,
            ) as client:
                async with client.stream(
                    "POST", "/chat/completions", headers=headers, json=payload
                ) as response:
                    if response.status_code != 200:
                        yield AIEvent(kind="failed", error_code=f"provider_http_{response.status_code}")
                        return
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        raw = line[6:]
                        if raw == "[DONE]":
                            return
                        try:
                            data = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        choices = data.get("choices") or []
                        if choices:
                            content = (choices[0].get("delta") or {}).get("content")
                            if content:
                                yield AIEvent(kind="delta", content=content)
                            if choices[0].get("finish_reason"):
                                usage = data.get("usage") or {}
                                yield AIEvent(
                                    kind="completed",
                                    input_tokens=usage.get("prompt_tokens"),
                                    output_tokens=usage.get("completion_tokens"),
                                )
        except httpx.HTTPError:
            yield AIEvent(kind="failed", error_code="provider_unavailable")
