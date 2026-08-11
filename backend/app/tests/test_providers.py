import asyncio

import httpx
import pytest

from app.integrations.anthropic_client import AnthropicClient
from app.integrations.gemini_client import GeminiClient
from app.integrations.openai_client import OpenAIClient
from app.integrations.openrouter_client import OpenRouterClient
from app.modules.chat.ai_router import ChatTurn
from app.modules.chat.providers import build_provider


def _collect(client):
    async def run():
        return [event async for event in client.stream_chat([ChatTurn(role="user", content="Hi")])]

    return asyncio.run(run())


def test_openai_client_normalizes_streaming_deltas_and_usage():
    async def handler(request):
        assert request.url.path == "/v1/chat/completions"
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=(
                b'data: {"choices":[{"delta":{"content":"Hi "}}]}\n\n'
                b'data: {"choices":[{"delta":{"content":"there"}}]}\n\n'
                b'data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":3,"completion_tokens":2}}\n\n'
                b"data: [DONE]\n\n"
            ),
        )

    client = OpenAIClient(api_key="test-key", transport=httpx.MockTransport(handler))
    events = _collect(client)

    assert [e.kind for e in events] == ["delta", "delta", "completed"]
    assert events[-1].input_tokens == 3
    assert events[-1].output_tokens == 2


def test_openai_client_reports_missing_credential_without_request():
    events = _collect(OpenAIClient(api_key=""))
    assert [e.kind for e in events] == ["failed"]
    assert events[0].error_code == "provider_not_configured"


def test_openrouter_client_normalizes_streaming_deltas():
    async def handler(request):
        assert request.url.path == "/api/v1/chat/completions"
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=(
                b'data: {"choices":[{"delta":{"content":"Xin"}}]}\n\n'
                b'data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":1,"completion_tokens":1}}\n\n'
                b"data: [DONE]\n\n"
            ),
        )

    client = OpenRouterClient(api_key="test-key", transport=httpx.MockTransport(handler))
    events = _collect(client)

    assert [e.kind for e in events] == ["delta", "completed"]


def test_anthropic_client_normalizes_sse_events_and_usage():
    async def handler(request):
        assert request.url.path == "/v1/messages"
        assert request.headers["x-api-key"] == "test-key"
        body = (
            b'event: message_start\n'
            b'data: {"type":"message_start","message":{"usage":{"input_tokens":7}}}\n\n'
            b'event: content_block_delta\n'
            b'data: {"delta":{"type":"text_delta","text":"Xin "}}\n\n'
            b'event: content_block_delta\n'
            b'data: {"delta":{"type":"text_delta","text":"chao"}}\n\n'
            b'event: message_delta\n'
            b'data: {"delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":4}}\n\n'
            b'event: message_stop\n'
            b'data: {}\n\n'
        )
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body)

    client = AnthropicClient(api_key="test-key", transport=httpx.MockTransport(handler))
    events = _collect(client)

    assert [e.kind for e in events] == ["delta", "delta", "completed"]
    assert [e.content for e in events[:2]] == ["Xin ", "chao"]
    assert events[-1].input_tokens == 7
    assert events[-1].output_tokens == 4


def test_anthropic_client_reports_missing_credential_without_request():
    events = _collect(AnthropicClient(api_key=""))
    assert [e.kind for e in events] == ["failed"]
    assert events[0].error_code == "provider_not_configured"


def test_gemini_client_normalizes_sse_chunks_and_final_usage():
    async def handler(request):
        assert request.url.path.endswith(":streamGenerateContent")
        assert request.url.params["key"] == "test-key"
        body = (
            b'data: {"candidates":[{"content":{"parts":[{"text":"Xin "}]}}]}\n\n'
            b'data: {"candidates":[{"content":{"parts":[{"text":"chao"}]}}],'
            b'"usageMetadata":{"promptTokenCount":5,"candidatesTokenCount":2}}\n\n'
        )
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body)

    client = GeminiClient(api_key="test-key", transport=httpx.MockTransport(handler))
    events = _collect(client)

    assert [e.kind for e in events] == ["delta", "delta", "completed"]
    assert events[-1].input_tokens == 5
    assert events[-1].output_tokens == 2


def test_gemini_client_reports_missing_credential_without_request():
    events = _collect(GeminiClient(api_key=""))
    assert [e.kind for e in events] == ["failed"]
    assert events[0].error_code == "provider_not_configured"


def test_build_provider_rejects_unknown_provider():
    with pytest.raises(ValueError):
        build_provider("does-not-exist", "some-model")


def test_build_provider_returns_configured_client_for_each_known_provider():
    for provider in ("deepseek", "openai", "openrouter", "anthropic", "gemini"):
        client = build_provider(provider, "some-model")
        assert hasattr(client, "stream_chat")
