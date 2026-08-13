from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.modules.chat.ai_router import AIEvent, ChatTurn
from app.modules.strategy.ai_prompt_utils import consume_ai_stream

_MODULE = "app.modules.strategy.ai_prompt_utils"


class _SequencedProvider:
    """Replays one AIEvent sequence per call to stream_chat, in order."""

    def __init__(self, sequences):
        self._sequences = list(sequences)

    async def stream_chat(self, turns, tools=None):
        sequence = self._sequences.pop(0)
        for event in sequence:
            yield event


@pytest.mark.asyncio
async def test_succeeds_immediately_without_retry_on_first_try():
    provider = _SequencedProvider([[AIEvent(kind="delta", content="hello"), AIEvent(kind="completed")]])

    result = await consume_ai_stream(provider, [ChatTurn(role="user", content="hi")])

    assert result == "hello"


@pytest.mark.asyncio
async def test_retries_a_429_and_succeeds_on_the_next_attempt():
    provider = _SequencedProvider([
        [AIEvent(kind="failed", error_code="provider_http_429")],
        [AIEvent(kind="delta", content="ok now"), AIEvent(kind="completed")],
    ])

    with patch(f"{_MODULE}.asyncio.sleep", return_value=None):
        result = await consume_ai_stream(provider, [ChatTurn(role="user", content="hi")], max_retries=2)

    assert result == "ok now"


@pytest.mark.asyncio
async def test_raises_a_friendly_message_after_exhausting_429_retries():
    provider = _SequencedProvider([
        [AIEvent(kind="failed", error_code="provider_http_429")],
        [AIEvent(kind="failed", error_code="provider_http_429")],
        [AIEvent(kind="failed", error_code="provider_http_429")],
    ])

    with patch(f"{_MODULE}.asyncio.sleep", return_value=None):
        with pytest.raises(HTTPException) as exc_info:
            await consume_ai_stream(provider, [ChatTurn(role="user", content="hi")], max_retries=2)

    assert exc_info.value.status_code == 502
    assert "provider_http_429" not in exc_info.value.detail
    assert "giới hạn tốc độ" in exc_info.value.detail


@pytest.mark.asyncio
async def test_non_retryable_error_fails_immediately_without_sleeping():
    provider = _SequencedProvider([[AIEvent(kind="failed", error_code="provider_http_400")]])

    with patch(f"{_MODULE}.asyncio.sleep", return_value=None) as mock_sleep:
        with pytest.raises(HTTPException) as exc_info:
            await consume_ai_stream(provider, [ChatTurn(role="user", content="hi")], max_retries=2)

    assert exc_info.value.status_code == 502
    assert not mock_sleep.called
