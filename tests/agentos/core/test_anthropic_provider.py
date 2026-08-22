from __future__ import annotations

import httpx
import pytest

from agentos.core.adapters.anthropic_provider import (
    AnthropicModelProvider,
    AnthropicProviderUnavailableError,
)

_RealAsyncClient = httpx.AsyncClient


@pytest.mark.asyncio
async def test_generate_raises_when_api_key_missing():
    provider = AnthropicModelProvider(api_key=None)

    with pytest.raises(AnthropicProviderUnavailableError, match="ANTHROPIC_API_KEY"):
        await provider.generate(system_prompt="sys", messages=[{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_generate_returns_text_for_plain_response(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-api-key"] == "test-key"
        return httpx.Response(200, json={"content": [{"type": "text", "text": "hello there"}]})

    monkeypatch.setattr(
        httpx, "AsyncClient", lambda *a, **kw: _RealAsyncClient(*a, transport=httpx.MockTransport(handler), **kw)
    )
    provider = AnthropicModelProvider(api_key="test-key")

    response = await provider.generate(system_prompt="sys", messages=[{"role": "user", "content": "hi"}])

    assert response.text == "hello there"
    assert response.tool_call is None


@pytest.mark.asyncio
async def test_generate_parses_tool_call_convention(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "content": [
                    {
                        "type": "text",
                        "text": '{"tool_call": {"name": "task_create", "arguments": {"title": "Ship it"}}}',
                    }
                ]
            },
        )

    monkeypatch.setattr(
        httpx, "AsyncClient", lambda *a, **kw: _RealAsyncClient(*a, transport=httpx.MockTransport(handler), **kw)
    )
    provider = AnthropicModelProvider(api_key="test-key")

    response = await provider.generate(system_prompt="sys", messages=[{"role": "user", "content": "hi"}])

    assert response.tool_call.tool_name == "task_create"
