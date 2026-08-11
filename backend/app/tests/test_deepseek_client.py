import asyncio

from app.integrations.deepseek_client import DeepSeekClient
from app.modules.chat.ai_router import ChatTurn


def test_deepseek_client_normalizes_streaming_deltas_and_usage():
    async def handler(request):
        assert request.url.path == "/chat/completions"
        return __import__("httpx").Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=(
                b'data: {"choices":[{"delta":{"content":"Xin "}}]}\n\n'
                b'data: {"choices":[{"delta":{"content":"chao"}}]}\n\n'
                b'data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":3,"completion_tokens":2}}\n\n'
                b"data: [DONE]\n\n"
            ),
        )

    client = DeepSeekClient(
        api_key="test-key",
        transport=__import__("httpx").MockTransport(handler),
    )

    async def collect_events():
        return [
            event
            async for event in client.stream_chat([ChatTurn(role="user", content="Hi")])
        ]

    events = asyncio.run(collect_events())

    assert [event.kind for event in events] == ["delta", "delta", "completed"]
    assert [event.content for event in events[:2]] == ["Xin ", "chao"]
    assert events[-1].input_tokens == 3
    assert events[-1].output_tokens == 2


def test_deepseek_client_reports_missing_credential_without_request():
    client = DeepSeekClient(api_key="")

    async def collect_events():
        return [
            event
            async for event in client.stream_chat([ChatTurn(role="user", content="Hi")])
        ]

    events = asyncio.run(collect_events())

    assert len(events) == 1
    assert events[0].kind == "failed"
    assert events[0].error_code == "provider_not_configured"
