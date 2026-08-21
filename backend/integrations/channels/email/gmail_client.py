"""Đọc/soạn Gmail qua REST API v1.

Chỉ dùng httpx như mọi client khác trong thư mục này, không kéo thêm google-api-python-client:
ta cần đúng 5 lời gọi, còn thư viện đó kéo theo cả gRPC lẫn một tầng auth riêng.
"""

import base64
import logging
from dataclasses import dataclass
from email.message import EmailMessage

import httpx

logger = logging.getLogger(__name__)

API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

# Trần cắt nội dung mỗi thư trước khi đưa vào prompt. Một thư quảng cáo HTML có thể dài
# hàng chục nghìn ký tự; 3 thư như thế là thổi bay context window và tốn tiền vô ích.
MAX_BODY_CHARS = 4000


class GmailError(RuntimeError):
    """Lỗi gọi Gmail đủ rõ để hiển thị lại cho người dùng."""


@dataclass(frozen=True)
class GmailMessage:
    id: str
    thread_id: str
    sender: str
    subject: str
    date: str
    snippet: str
    body: str

    def as_prompt_dict(self) -> dict:
        return {
            "id": self.id,
            "from": self.sender,
            "subject": self.subject,
            "date": self.date,
            "body": self.body or self.snippet,
        }


def _decode_part(data: str) -> str:
    try:
        return base64.urlsafe_b64decode(data.encode("ascii")).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _extract_body(payload: dict) -> str:
    """Lấy phần text/plain; chỉ khi không có mới rơi về text/html.

    Gmail trả về cây MIME nhiều tầng (multipart/alternative lồng multipart/mixed), nên phải
    duyệt đệ quy chứ không thể đọc mỗi payload['body'].
    """
    if not payload:
        return ""

    mime = payload.get("mimeType", "")
    body_data = (payload.get("body") or {}).get("data")
    if body_data and mime == "text/plain":
        return _decode_part(body_data)

    html_fallback = ""
    for part in payload.get("parts") or []:
        found = _extract_body(part)
        if found:
            if part.get("mimeType") == "text/html" and not html_fallback:
                html_fallback = found
                continue
            return found

    if html_fallback:
        return html_fallback
    if body_data:
        return _decode_part(body_data)
    return ""


def _header(headers: list, name: str) -> str:
    for item in headers or []:
        if item.get("name", "").lower() == name.lower():
            return item.get("value", "")
    return ""


def parse_message(raw: dict) -> GmailMessage:
    payload = raw.get("payload") or {}
    headers = payload.get("headers") or []
    body = _extract_body(payload).strip()
    if len(body) > MAX_BODY_CHARS:
        body = body[:MAX_BODY_CHARS] + "\n...[đã cắt bớt]"
    return GmailMessage(
        id=raw.get("id", ""),
        thread_id=raw.get("threadId", ""),
        sender=_header(headers, "From"),
        subject=_header(headers, "Subject") or "(không có tiêu đề)",
        date=_header(headers, "Date"),
        snippet=raw.get("snippet", ""),
        body=body,
    )


class GmailClient:
    """Một access token = một hòm thư. Token do google_oauth_service làm mới trước khi tạo."""

    def __init__(self, access_token: str, transport: httpx.AsyncBaseTransport | None = None):
        self._access_token = access_token
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=API_BASE,
            headers={"Authorization": f"Bearer {self._access_token}"},
            transport=self._transport,
            timeout=30.0,
        )

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        async with self._client() as client:
            response = await client.request(method, path, **kwargs)
        if response.status_code == 401:
            raise GmailError("Kết nối Gmail hết hiệu lực, hãy kết nối lại.")
        if response.status_code == 403:
            raise GmailError("Tài khoản Gmail chưa cấp đủ quyền cho thao tác này.")
        if response.status_code >= 400:
            logger.warning("Gmail %s %s -> %s", method, path, response.status_code)
            raise GmailError(f"Gmail trả lỗi {response.status_code}")
        return response.json() if response.content else {}

    async def list_messages(self, query: str = "", max_results: int = 5) -> list[GmailMessage]:
        """Danh sách thư kèm nội dung. ``query`` dùng cú pháp tìm kiếm của Gmail.

        messages.list chỉ trả về id, nên phải gọi tiếp messages.get cho từng thư - đó là lý
        do max_results bị chặn nhỏ ở tầng tool.
        """
        listing = await self._request(
            "GET",
            "/messages",
            params={"maxResults": max_results, "q": query or "in:inbox"},
        )
        messages = []
        for stub in listing.get("messages") or []:
            raw = await self._request(
                "GET", f"/messages/{stub['id']}", params={"format": "full"}
            )
            messages.append(parse_message(raw))
        return messages

    async def get_message(self, message_id: str) -> GmailMessage:
        raw = await self._request("GET", f"/messages/{message_id}", params={"format": "full"})
        return parse_message(raw)

    async def create_draft(self, to: str, subject: str, body: str) -> dict:
        message = EmailMessage()
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        return await self._request(
            "POST", "/drafts", json={"message": {"raw": encoded}}
        )

    async def send_draft(self, draft_id: str) -> dict:
        """Gửi một bản nháp đã tạo sẵn.

        Tách khỏi create_draft có chủ đích: thư chỉ rời hòm thư ở đúng một chỗ này, và chỗ
        này chỉ được gọi sau khi người dùng bấm duyệt (xem email_approval_service).
        """
        return await self._request("POST", "/drafts/send", json={"id": draft_id})
