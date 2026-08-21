"""Client cho Gemini generateContent API (SSE qua ?alt=sse, role "model" thay vì
"assistant", system là field systemInstruction riêng, usageMetadata là cumulative nên
chỉ lấy giá trị cuối cùng thay vì phát completed nhiều lần)."""

import json
import os
from typing import AsyncIterator

import httpx

from workforce.chat.ai_router import AIEvent, ChatTurn


class GeminiClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        self._base_url = base_url or os.environ.get(
            "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"
        )
        self._model = model or os.environ.get("GEMINI_DEFAULT_MODEL", "gemini-1.5-flash")
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

        system_parts = [turn.content for turn in turns if turn.role == "system"]
        contents = [
            {
                "role": "model" if turn.role == "assistant" else "user",
                "parts": [{"text": turn.content}],
            }
            for turn in turns
            if turn.role != "system"
        ]
        payload: dict = {"contents": contents}
        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_parts)}]}

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                transport=self._transport,
                timeout=60.0,
            ) as client:
                async with client.stream(
                    "POST",
                    f"/models/{self._model}:streamGenerateContent",
                    params={"alt": "sse", "key": self._api_key},
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        yield AIEvent(kind="failed", error_code=f"provider_http_{response.status_code}")
                        return

                    last_usage: dict = {}
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        try:
                            data = json.loads(line[6:])
                        except json.JSONDecodeError:
                            continue

                        candidates = data.get("candidates") or []
                        if candidates:
                            parts = (candidates[0].get("content") or {}).get("parts") or []
                            text = "".join(part.get("text", "") for part in parts)
                            if text:
                                yield AIEvent(kind="delta", content=text)
                        usage = data.get("usageMetadata")
                        if usage:
                            last_usage = usage

                    yield AIEvent(
                        kind="completed",
                        input_tokens=last_usage.get("promptTokenCount"),
                        output_tokens=last_usage.get("candidatesTokenCount"),
                    )
        except httpx.HTTPError:
            yield AIEvent(kind="failed", error_code="provider_unavailable")
