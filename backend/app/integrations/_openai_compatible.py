"""Client dùng chung cho các provider theo chuẩn OpenAI /chat/completions (OpenAI,
OpenRouter). deepseek_client.py KHÔNG kế thừa từ đây - nó đã hoạt động đúng và có test
riêng (test_deepseek_client.py), tách để không đụng vào code đang chạy."""

import json
from typing import Any, AsyncIterator

import httpx

from app.modules.chat.ai_router import AIEvent, ChatTurn, ToolCall


def turn_to_payload(turn: ChatTurn) -> dict:
    """Một ChatTurn -> một message theo đúng hình dạng OpenAI mong đợi.

    Lượt tool phải giữ nguyên tool_call_id và lượt assistant phải giữ nguyên tool_calls:
    provider đối chiếu id giữa hai lượt đó, thiếu là cả hội thoại bị từ chối 400.
    """
    if turn.role == "tool":
        return {
            "role": "tool",
            "tool_call_id": turn.tool_call_id,
            "content": turn.content,
        }

    message: dict[str, Any] = {"role": turn.role, "content": turn.content}
    if turn.tool_calls:
        message["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": call.arguments},
            }
            for call in turn.tool_calls
        ]
    return message


class _ToolCallAccumulator:
    """Tool call về theo từng mảnh giống hệt text: tên ở mảnh đầu, arguments nhỏ giọt qua
    nhiều chunk. Phải gom theo ``index`` rồi mới parse - đọc từng mảnh là JSON luôn dở dang."""

    def __init__(self):
        self._by_index: dict[int, dict] = {}

    def add(self, chunk: dict) -> None:
        index = chunk.get("index", 0)
        current = self._by_index.setdefault(index, {"id": "", "name": "", "arguments": ""})
        if chunk.get("id"):
            current["id"] = chunk["id"]
        function = chunk.get("function") or {}
        if function.get("name"):
            current["name"] = function["name"]
        if function.get("arguments"):
            current["arguments"] += function["arguments"]

    def finish(self) -> list[ToolCall]:
        return [
            ToolCall(
                id=item["id"] or f"call_{index}",
                name=item["name"],
                arguments=item["arguments"] or "{}",
            )
            for index, item in sorted(self._by_index.items())
            if item["name"]
        ]


class OpenAICompatibleClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._transport = transport

    async def stream_chat(
        self, turns: list[ChatTurn], tools: list[dict[str, Any]] | None = None
    ) -> AsyncIterator[AIEvent]:
        if not self._api_key:
            yield AIEvent(kind="failed", error_code="provider_not_configured")
            return

        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {
            "model": self._model,
            "messages": [turn_to_payload(turn) for turn in turns],
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        accumulator = _ToolCallAccumulator()
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
                            break
                        try:
                            data = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        choices = data.get("choices") or []
                        if choices:
                            delta = choices[0].get("delta") or {}
                            content = delta.get("content")
                            if content:
                                yield AIEvent(kind="delta", content=content)
                            for chunk in delta.get("tool_calls") or []:
                                accumulator.add(chunk)
                            if choices[0].get("finish_reason"):
                                usage = data.get("usage") or {}
                                for call in accumulator.finish():
                                    yield AIEvent(kind="tool_call", tool_call=call)
                                accumulator = _ToolCallAccumulator()
                                yield AIEvent(
                                    kind="completed",
                                    input_tokens=usage.get("prompt_tokens"),
                                    output_tokens=usage.get("completion_tokens"),
                                )
        except httpx.HTTPError:
            yield AIEvent(kind="failed", error_code="provider_unavailable")
