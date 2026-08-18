import asyncio
import base64
import json

import httpx
import pytest

from app.integrations.channels.email.gmail_client import (
    MAX_BODY_CHARS,
    GmailClient,
    GmailError,
    parse_message,
)


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")


def _raw_message(*, body_parts, subject="Báo giá tháng 8", message_id="m1"):
    return {
        "id": message_id,
        "threadId": "t1",
        "snippet": "tóm lược ngắn",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "From", "value": "Khách hàng <khach@example.com>"},
                {"name": "Subject", "value": subject},
                {"name": "Date", "value": "Mon, 10 Aug 2026 09:00:00 +0700"},
            ],
            "parts": body_parts,
        },
    }


def test_parse_message_reads_headers_and_plain_text_body():
    message = parse_message(
        _raw_message(
            body_parts=[
                {"mimeType": "text/plain", "body": {"data": _b64("Nội dung thư")}},
            ]
        )
    )

    assert message.sender == "Khách hàng <khach@example.com>"
    assert message.subject == "Báo giá tháng 8"
    assert message.body == "Nội dung thư"


def test_parse_message_prefers_plain_text_over_html():
    """Thư marketing luôn có cả hai phần; nhét HTML vào prompt là đốt token cho thẻ <div>."""
    message = parse_message(
        _raw_message(
            body_parts=[
                {"mimeType": "text/html", "body": {"data": _b64("<p>Bản HTML</p>")}},
                {"mimeType": "text/plain", "body": {"data": _b64("Bản chữ thường")}},
            ]
        )
    )

    assert message.body == "Bản chữ thường"


def test_parse_message_falls_back_to_html_when_there_is_no_plain_text():
    message = parse_message(
        _raw_message(
            body_parts=[
                {"mimeType": "text/html", "body": {"data": _b64("<p>Chỉ có HTML</p>")}},
            ]
        )
    )

    assert "Chỉ có HTML" in message.body


def test_parse_message_digs_into_nested_multipart():
    """Thư có đính kèm là multipart/mixed bọc ngoài multipart/alternative - đọc nông một
    tầng thì thân thư ra rỗng."""
    message = parse_message(
        _raw_message(
            body_parts=[
                {
                    "mimeType": "multipart/alternative",
                    "parts": [
                        {"mimeType": "text/plain", "body": {"data": _b64("Thư có đính kèm")}},
                    ],
                },
                {"mimeType": "application/pdf", "body": {"attachmentId": "a1"}},
            ]
        )
    )

    assert message.body == "Thư có đính kèm"


def test_parse_message_truncates_a_huge_body():
    message = parse_message(
        _raw_message(
            body_parts=[
                {"mimeType": "text/plain", "body": {"data": _b64("x" * (MAX_BODY_CHARS + 500))}},
            ]
        )
    )

    assert len(message.body) < MAX_BODY_CHARS + 100
    assert message.body.endswith("[đã cắt bớt]")


def test_list_messages_fetches_full_content_for_each_hit():
    """messages.list chỉ trả id - thiếu bước messages.get thì model chỉ có id để tóm tắt."""
    seen_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        if request.url.path.endswith("/messages"):
            return httpx.Response(200, json={"messages": [{"id": "m1"}, {"id": "m2"}]})
        return httpx.Response(
            200,
            json=_raw_message(
                body_parts=[{"mimeType": "text/plain", "body": {"data": _b64("Xin chào")}}],
                message_id=request.url.path.rsplit("/", 1)[-1],
            ),
        )

    client = GmailClient("token", transport=httpx.MockTransport(handler))
    messages = asyncio.run(client.list_messages(max_results=2))

    assert [m.id for m in messages] == ["m1", "m2"]
    assert all(m.body == "Xin chào" for m in messages)
    assert sum(1 for path in seen_paths if path.endswith(("/m1", "/m2"))) == 2


def test_expired_token_says_to_reconnect():
    """401 nghĩa là người dùng phải đi kết nối lại - nói "Gmail trả lỗi 401" thì họ chịu."""
    transport = httpx.MockTransport(lambda request: httpx.Response(401, json={}))
    client = GmailClient("token", transport=transport)

    with pytest.raises(GmailError) as exc:
        asyncio.run(client.list_messages())

    assert "kết nối lại" in str(exc.value)


def test_create_draft_sends_a_valid_rfc822_message():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={"id": "draft-1"})

    client = GmailClient("token", transport=httpx.MockTransport(handler))
    draft = asyncio.run(
        client.create_draft(to="sep@example.com", subject="Chào", body="Nội dung")
    )

    assert draft["id"] == "draft-1"
    raw = base64.urlsafe_b64decode(captured["message"]["raw"]).decode("utf-8")
    assert "To: sep@example.com" in raw
    assert "Nội dung" in raw
