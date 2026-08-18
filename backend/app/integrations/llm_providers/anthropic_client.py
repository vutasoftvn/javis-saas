"""Client cho Anthropic Messages API (giao thức SSE khác hẳn OpenAI-compatible: có
event: message_start/content_block_delta/message_delta riêng, và "system" là field
top-level chứ không phải role trong messages)."""

import json
import os
from typing import AsyncIterator

import httpx

from app.workforce.chat.ai_router import AIEvent, ChatTurn

ANTHROPIC_VERSION = "2023-06-01"


class AnthropicClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._api_key = api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY", "")
        self._base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        self._model = model or os.environ.get("ANTHROPIC_DEFAULT_MODEL", "claude-3-5-sonnet-latest")
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
        messages = [
            {"role": turn.role, "content": turn.content} for turn in turns if turn.role != "system"
        ]
        headers = {"x-api-key": self._api_key, "anthropic-version": ANTHROPIC_VERSION}
        payload: dict = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": messages,
            "stream": True,
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)

        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                transport=self._transport,
                timeout=60.0,
            ) as client:
                async with client.stream(
                    "POST", "/v1/messages", headers=headers, json=payload
                ) as response:
                    if response.status_code != 200:
                        yield AIEvent(kind="failed", error_code=f"provider_http_{response.status_code}")
                        return

                    event_name: str | None = None
                    input_tokens: int | None = None
                    async for line in response.aiter_lines():
                        if line.startswith("event: "):
                            event_name = line[7:].strip()
                            continue
                        if not line.startswith("data: "):
                            continue
                        try:
                            data = json.loads(line[6:])
                        except json.JSONDecodeError:
                            continue

                        if event_name == "message_start":
                            input_tokens = ((data.get("message") or {}).get("usage") or {}).get(
                                "input_tokens"
                            )
                        elif event_name == "content_block_delta":
                            delta = data.get("delta") or {}
                            if delta.get("type") == "text_delta" and delta.get("text"):
                                yield AIEvent(kind="delta", content=delta["text"])
                        elif event_name == "message_delta":
                            usage = data.get("usage") or {}
                            yield AIEvent(
                                kind="completed",
                                input_tokens=input_tokens,
                                output_tokens=usage.get("output_tokens"),
                            )
                        elif event_name == "error":
                            error = data.get("error") or {}
                            yield AIEvent(kind="failed", error_code=error.get("type") or "provider_error")
                            return
        except httpx.HTTPError:
            yield AIEvent(kind="failed", error_code="provider_unavailable")
