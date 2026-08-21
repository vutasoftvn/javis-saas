import asyncio

from integrations.llm_providers.deepseek_client import DeepSeekClient
from workforce.chat.ai_router import ChatTurn


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


def test_deepseek_client_supports_standard_tool_calling():
    async def handler(request):
        assert request.url.path == "/chat/completions"
        payload = __import__("json").loads(request.content)
        assert "tools" in payload
        assert payload["tools"][0]["function"]["name"] == "strategy_list_projects"
        return __import__("httpx").Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=(
                b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_123","function":{"name":"strategy_list_projects","arguments":"{}"}}]}}]}\n\n'
                b'data: {"choices":[{"delta":{},"finish_reason":"tool_calls"}],"usage":{"prompt_tokens":10,"completion_tokens":5}}\n\n'
                b"data: [DONE]\n\n"
            ),
        )

    client = DeepSeekClient(
        api_key="test-key",
        transport=__import__("httpx").MockTransport(handler),
    )

    tools = [{"type": "function", "function": {"name": "strategy_list_projects", "parameters": {}}}]

    async def collect_events():
        return [
            event
            async for event in client.stream_chat([ChatTurn(role="user", content="Dự án")], tools=tools)
        ]

    events = asyncio.run(collect_events())

    assert [event.kind for event in events] == ["tool_call", "completed"]
    assert events[0].tool_call.name == "strategy_list_projects"
    assert events[0].tool_call.arguments == "{}"


def test_deepseek_client_cleanses_raw_special_tokens_and_extracts_inline_tool_call():
    """Xử lý lỗi rò rỉ token đặc biệt và tự parse inline function call nếu model stream vào content."""
    async def handler(request):
        return __import__("httpx").Response(
            200,
            headers={"content-type": "text/event-stream"},
            content=(
                b'data: {"choices":[{"delta":{"content":"< | place__holder__no__568 | >\xe0\xb8\x97\xe0\xb8\x94\xe0\xb8\xaa\xe0\xb8\xad\xe0\xb8\x9a\xe9\x82\xa3\xe9\xba\xbc \xd9\x81\xd8\xb1\xdb\x8c\xd9\xbe\xdb\x8c\xd8\xb3function< | tool__sep | >strategy_list_projects json {}"}}]}\n\n'
                b'data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"prompt_tokens":12,"completion_tokens":8}}\n\n'
                b"data: [DONE]\n\n"
            ),
        )

    client = DeepSeekClient(
        api_key="test-key",
        transport=__import__("httpx").MockTransport(handler),
    )

    tools = [{"type": "function", "function": {"name": "strategy_list_projects", "parameters": {}}}]

    async def collect_events():
        return [
            event
            async for event in client.stream_chat([ChatTurn(role="user", content="Dự án")], tools=tools)
        ]

    events = asyncio.run(collect_events())

    # Không có delta rác nào lọt qua, và tool_call được parse thành công
    assert [event.kind for event in events] == ["tool_call", "completed"]
    assert events[0].tool_call.name == "strategy_list_projects"
    assert events[0].tool_call.arguments == "{}"

