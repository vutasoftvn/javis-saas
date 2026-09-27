"""GmailReadAdapter (plan hub vận hành đợt 2 B3) — chỉ transport giả, KHÔNG gọi mạng thật."""

from __future__ import annotations

import httpx
import pytest
from agent_integrations.gmail import (
    GMAIL_API_BASE_URL,
    EmailSummary,
    GmailApiError,
    GmailReadAdapter,
    GmailReauthRequiredError,
    GmailRetryableError,
)

TOKEN = "ya29.test-access-token"


def _message(msg_id: str, *, subject: str, sender: str, snippet: str) -> dict:
    return {
        "id": msg_id,
        "threadId": f"t-{msg_id}",
        "snippet": snippet,
        "payload": {
            "headers": [
                {"name": "Subject", "value": subject},
                {"name": "From", "value": sender},
                {"name": "Date", "value": "Sun, 27 Sep 2026 08:00:00 +0700"},
            ]
        },
    }


class _Recorder:
    def __init__(self, handler) -> None:
        self.requests: list[httpx.Request] = []
        self._handler = handler

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._handler(request)


def _adapter(recorder: _Recorder) -> GmailReadAdapter:
    return GmailReadAdapter(transport=httpx.MockTransport(recorder))


@pytest.mark.asyncio
async def test_list_unread_returns_metadata_summaries_without_body() -> None:
    long_snippet = "x" * 400

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/users/me/messages"):
            return httpx.Response(200, json={"messages": [{"id": "m1"}, {"id": "m2"}]})
        if path.endswith("/users/me/messages/m1"):
            return httpx.Response(
                200,
                json=_message("m1", subject="Hoá đơn", sender="a@x.vn", snippet="Xin chào"),
            )
        if path.endswith("/users/me/messages/m2"):
            return httpx.Response(
                200, json=_message("m2", subject="Họp", sender="b@y.vn", snippet=long_snippet)
            )
        return httpx.Response(404)

    rec = _Recorder(handler)
    emails = await _adapter(rec).list_unread(TOKEN, max_results=5)

    assert [e.id for e in emails] == ["m1", "m2"]
    first = emails[0]
    assert isinstance(first, EmailSummary)
    assert first.thread_id == "t-m1"
    assert first.subject == "Hoá đơn"
    assert first.sender == "a@x.vn"
    assert first.date == "Sun, 27 Sep 2026 08:00:00 +0700"
    assert first.snippet == "Xin chào"
    assert len(emails[1].snippet) == 300
    # Shape trả ra đúng 6 field, không có body/payload.
    assert set(first.to_dict()) == {"id", "thread_id", "subject", "sender", "date", "snippet"}

    list_req = rec.requests[0]
    assert str(list_req.url).startswith(f"{GMAIL_API_BASE_URL}/users/me/messages?")
    assert list_req.url.params["q"] == "is:unread"
    assert list_req.url.params["maxResults"] == "5"
    for req in rec.requests:
        assert req.headers["Authorization"] == f"Bearer {TOKEN}"
    for get_req in rec.requests[1:]:
        # Chỉ metadata — không bao giờ xin full body.
        assert get_req.url.params["format"] == "metadata"
        assert get_req.url.params.get_list("metadataHeaders") == ["Subject", "From", "Date"]


@pytest.mark.asyncio
async def test_list_unread_empty_inbox_returns_empty_list() -> None:
    rec = _Recorder(lambda request: httpx.Response(200, json={"resultSizeEstimate": 0}))
    assert await _adapter(rec).list_unread(TOKEN) == []
    assert rec.requests[0].url.params["maxResults"] == "20"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403])
async def test_invalid_token_raises_reauth_required(status: int) -> None:
    rec = _Recorder(lambda request: httpx.Response(status, json={"error": {"code": status}}))
    with pytest.raises(GmailReauthRequiredError) as exc_info:
        await _adapter(rec).list_unread(TOKEN)
    err = exc_info.value
    assert err.code == "email_reauth_required"
    assert err.status_code == status
    assert str(err).startswith("email_reauth_required:")
    assert TOKEN not in str(err)
    assert not err.retryable


@pytest.mark.asyncio
async def test_rate_limit_raises_retryable_error() -> None:
    rec = _Recorder(lambda request: httpx.Response(429, json={"error": {"code": 429}}))
    with pytest.raises(GmailRetryableError) as exc_info:
        await _adapter(rec).list_unread(TOKEN)
    assert exc_info.value.retryable
    assert exc_info.value.status_code == 429
    assert exc_info.value.code == "email_provider_unavailable"


@pytest.mark.asyncio
async def test_server_error_on_message_get_is_retryable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/users/me/messages"):
            return httpx.Response(200, json={"messages": [{"id": "m1"}]})
        return httpx.Response(503)

    with pytest.raises(GmailRetryableError):
        await _adapter(_Recorder(handler)).list_unread(TOKEN)


@pytest.mark.asyncio
async def test_network_error_is_retryable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    with pytest.raises(GmailRetryableError):
        await _adapter(_Recorder(handler)).list_unread(TOKEN)


@pytest.mark.asyncio
async def test_other_client_error_is_not_retryable_nor_reauth() -> None:
    rec = _Recorder(lambda request: httpx.Response(400, json={"error": {"code": 400}}))
    with pytest.raises(GmailApiError) as exc_info:
        await _adapter(rec).list_unread(TOKEN)
    assert not isinstance(exc_info.value, GmailReauthRequiredError | GmailRetryableError)
    assert not exc_info.value.retryable


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [0, 51, -1])
async def test_max_results_out_of_range_rejected(bad: int) -> None:
    rec = _Recorder(lambda request: httpx.Response(200, json={}))
    with pytest.raises(ValueError):
        await _adapter(rec).list_unread(TOKEN, max_results=bad)
    assert rec.requests == []


@pytest.mark.asyncio
async def test_empty_token_raises_reauth_without_network() -> None:
    rec = _Recorder(lambda request: httpx.Response(200, json={}))
    with pytest.raises(GmailReauthRequiredError):
        await _adapter(rec).list_unread("")
    assert rec.requests == []
