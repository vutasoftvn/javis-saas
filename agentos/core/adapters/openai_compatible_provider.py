from __future__ import annotations

import httpx

from agentos.core.adapters._tool_call_parsing import parse_tool_call
from agentos.core.model_provider import ModelResponse


class OpenAICompatibleProviderUnavailableError(RuntimeError):
    """Raised when an OpenAI-compatible provider is called without an API key."""


class OpenAICompatibleModelProvider:
    """`ModelProvider` for any OpenAI-Chat-Completions-compatible HTTP API
    (OpenAI, OpenRouter, DeepSeek's plain REST endpoint, and other
    OpenAI-compatible gateways). Self-contained — calls the provider's HTTP
    API directly with `httpx`, unlike `legacy/backend/integrations/llm_providers/`'s
    equivalents which import `workforce.chat.ai_router` types and therefore
    require the frozen `legacy/backend` package graph to even import (see
    ADR-012). This adapter exists so `agentos/` can reach these providers
    without depending on `legacy/backend` at all.
    """

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        model: str,
        extra_headers: dict[str, str] | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._extra_headers = extra_headers or {}
        self._timeout = timeout

    async def generate(self, *, system_prompt: str, messages: list[dict]) -> ModelResponse:
        if not self._api_key:
            raise OpenAICompatibleProviderUnavailableError(
                f"No API key configured for model '{self._model}' at {self._base_url}"
            )

        payload_messages = [{"role": "system", "content": system_prompt}]
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", message)
            if role == "tool":
                # Executor appends raw tool results as {"role": "tool", "content": <dict>};
                # OpenAI-compatible APIs expect message content to be a string.
                content = content if isinstance(content, str) else str(content)
            payload_messages.append({"role": role, "content": content})

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            **self._extra_headers,
        }
        body = {"model": self._model, "messages": payload_messages}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(f"{self._base_url}/chat/completions", headers=headers, json=body)
            response.raise_for_status()
            data = response.json()

        text = data["choices"][0]["message"]["content"] or ""
        tool_call = parse_tool_call(text)
        if tool_call is not None:
            return ModelResponse(tool_call=tool_call)
        return ModelResponse(text=text)
