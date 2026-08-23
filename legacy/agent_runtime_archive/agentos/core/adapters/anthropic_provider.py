from __future__ import annotations

import httpx

from agentos.core.adapters._tool_call_parsing import parse_tool_call
from agentos.core.model_provider import ModelResponse, TokenUsage

_DEFAULT_BASE_URL = "https://api.anthropic.com"
_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProviderUnavailableError(RuntimeError):
    """Raised when the Anthropic provider is called without an API key."""


class AnthropicModelProvider:
    """`ModelProvider` for the Anthropic Messages API. Self-contained (calls
    the HTTP API directly) rather than importing
    `legacy/backend/integrations/llm_providers/anthropic_client.py`, which
    depends on `workforce.chat.ai_router` and therefore the frozen
    `legacy/backend` package graph (see ADR-012).
    """

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str = "claude-sonnet-5",
        base_url: str = _DEFAULT_BASE_URL,
        max_tokens: int = 4096,
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._max_tokens = max_tokens
        self._timeout = timeout

    async def generate(self, *, system_prompt: str, messages: list[dict]) -> ModelResponse:
        if not self._api_key:
            raise AnthropicProviderUnavailableError("ANTHROPIC_API_KEY is not configured")

        payload_messages = []
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", message)
            if role == "tool":
                role = "user"
                content = content if isinstance(content, str) else str(content)
            elif role == "assistant" and "tool_call" in message:
                content = str(message["tool_call"])
            payload_messages.append({"role": role, "content": content})

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }
        body = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "system": system_prompt,
            "messages": payload_messages,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(f"{self._base_url}/v1/messages", headers=headers, json=body)
            response.raise_for_status()
            data = response.json()

        text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
        usage_raw = data.get("usage")
        usage = (
            TokenUsage(
                input_tokens=usage_raw.get("input_tokens", 0),
                output_tokens=usage_raw.get("output_tokens", 0),
            )
            if usage_raw
            else None
        )
        tool_call = parse_tool_call(text)
        if tool_call is not None:
            return ModelResponse(tool_call=tool_call, model=self._model, usage=usage)
        return ModelResponse(text=text, model=self._model, usage=usage)
