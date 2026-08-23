from __future__ import annotations

import httpx
import pytest

from agentos.core.adapters.openai_compatible_provider import (
    OpenAICompatibleModelProvider,
    OpenAICompatibleProviderUnavailableError,
)

_RealAsyncClient = httpx.AsyncClient


@pytest.mark.asyncio
async def test_generate_raises_when_api_key_missing():
    provider = OpenAICompatibleModelProvider(api_key=None, base_url="https://example.test/v1", model="m")

    with pytest.raises(OpenAICompatibleProviderUnavailableError, match="m"):
        await provider.generate(system_prompt="sys", messages=[{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_generate_returns_text_for_plain_response(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(200, json={"choices": [{"message": {"content": "hello there"}}]})

    monkeypatch.setattr(
        httpx, "AsyncClient", lambda *a, **kw: _RealAsyncClient(*a, transport=httpx.MockTransport(handler), **kw)
    )
    provider = OpenAICompatibleModelProvider(api_key="test-key", base_url="https://example.test/v1", model="m")

    response = await provider.generate(system_prompt="sys", messages=[{"role": "user", "content": "hi"}])

    assert response.text == "hello there"
    assert response.tool_call is None
    assert response.model == "m"
    assert response.usage is None


@pytest.mark.asyncio
async def test_generate_parses_real_token_usage_when_present(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "hello there"}}],
                "usage": {"prompt_tokens": 42, "completion_tokens": 7, "total_tokens": 49},
            },
        )

    monkeypatch.setattr(
        httpx, "AsyncClient", lambda *a, **kw: _RealAsyncClient(*a, transport=httpx.MockTransport(handler), **kw)
    )
    provider = OpenAICompatibleModelProvider(api_key="test-key", base_url="https://example.test/v1", model="m")

    response = await provider.generate(system_prompt="sys", messages=[{"role": "user", "content": "hi"}])

    assert response.usage.input_tokens == 42
    assert response.usage.output_tokens == 7


@pytest.mark.asyncio
async def test_generate_parses_tool_call_convention(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"tool_call": {"name": "task_create", "arguments": {"title": "Ship it"}}}'
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(
        httpx, "AsyncClient", lambda *a, **kw: _RealAsyncClient(*a, transport=httpx.MockTransport(handler), **kw)
    )
    provider = OpenAICompatibleModelProvider(api_key="test-key", base_url="https://example.test/v1", model="m")

    response = await provider.generate(system_prompt="sys", messages=[{"role": "user", "content": "hi"}])

    assert response.text is None
    assert response.tool_call.tool_name == "task_create"
    assert response.tool_call.arguments == {"title": "Ship it"}


@pytest.mark.asyncio
async def test_generate_stringifies_tool_result_messages(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr(
        httpx, "AsyncClient", lambda *a, **kw: _RealAsyncClient(*a, transport=httpx.MockTransport(handler), **kw)
    )
    provider = OpenAICompatibleModelProvider(api_key="test-key", base_url="https://example.test/v1", model="m")

    await provider.generate(
        system_prompt="sys", messages=[{"role": "tool", "content": {"echoed": "hi"}}]
    )

    tool_message = captured["body"]["messages"][-1]
    assert tool_message["role"] == "tool"
    assert isinstance(tool_message["content"], str)
