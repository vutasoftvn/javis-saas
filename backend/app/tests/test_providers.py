import asyncio

import httpx
import pytest

from app.integrations.llm_providers.anthropic_client import AnthropicClient
from app.integrations.llm_providers.gemini_client import GeminiClient
from app.integrations.llm_providers.openai_client import OpenAIClient
from app.integrations.llm_providers.openrouter_client import OpenRouterClient
from app.workforce.chat.ai_router import ChatTurn
from app.workforce.chat.providers import build_provider


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


def test_openrouter_falls_back_to_the_key_the_workspace_saved_in_the_app(monkeypatch):
    """Người dùng nhập khoá OpenRouter ngay trong app (lưu mã hoá ở workspace_secrets) và
    is_provider_configured đã tính khoá đó là "đã cấu hình". Nếu chỗ gọi model thật chỉ đọc
    biến môi trường thì UI báo xanh còn mọi lượt gọi chết ở provider_not_configured, và AI
    chỉ sống chừng nào container còn giữ khoá trong env - dựng lại container là mất."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    seen = {}

    def _fake_lookup(workspace_id=None):
        seen["workspace_id"] = workspace_id
        return "key-from-workspace-secret"

    monkeypatch.setattr(
        "app.integrations.llm_providers.openrouter_service.get_openrouter_api_key", _fake_lookup
    )

    async def handler(request):
        assert request.headers["authorization"] == "Bearer key-from-workspace-secret"
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=b'data: {"choices":[{"delta":{"content":"ok"}}]}\n\ndata: [DONE]\n\n',
        )

    client = OpenRouterClient(
        model="deepseek/deepseek-chat",
        workspace_id=4242,
        transport=httpx.MockTransport(handler),
    )
    events = _collect(client)

    assert seen["workspace_id"] == 4242
    assert [e.kind for e in events] == ["delta"]


def test_build_provider_passes_the_workspace_down_to_openrouter(monkeypatch):
    """Khoá là của một workspace cụ thể: dùng nhầm khoá workspace khác là tính hoá đơn AI
    sang tenant khác."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    seen = {}

    monkeypatch.setattr(
        "app.integrations.llm_providers.openrouter_service.get_openrouter_api_key",
        lambda workspace_id=None: seen.setdefault("workspace_id", workspace_id) or "k",
    )

    build_provider("openrouter", "deepseek/deepseek-chat", 777)

    assert seen["workspace_id"] == 777
