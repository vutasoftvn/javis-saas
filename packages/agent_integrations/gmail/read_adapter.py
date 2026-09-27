"""Adapter đọc Gmail (plan hub vận hành đợt 2 B3) — gọi thẳng Gmail REST API bằng httpx.

Vì sao KHÔNG đi qua khung MCP (`apps/cosa/capabilities/mcp_connectors.py`, manifest G-6) như
plan ghi: khung đó lấy credential là MỘT token chung cho cả server qua `auth_env`, chưa có
secret theo từng workspace. Yêu cầu cốt lõi của B3 là "agent chỉ dùng token đã cấp qua grant
connector của founder", nên adapter nhận `access_token` do caller truyền vào — caller
(`apps/cosa/capabilities/email_digest_read.py`) resolve token từ `secret_ref` của grant
connector `email-read`. Adapter không đọc env, không cache token, không log token.

Chỉ đọc metadata: `messages.list` (`q=is:unread`) rồi `messages.get` với `format=metadata` +
`metadataHeaders=Subject,From,Date` cho từng id. Không bao giờ xin full body.

Phân loại lỗi (B5/Task 6 map sang trạng thái lịch):
- 401/403 (hoặc token rỗng) → `GmailReauthRequiredError` (`code="email_reauth_required"`):
  token hết hạn/không đủ quyền, founder cần kết nối lại → `blocked_reauth`.
- 429/5xx/lỗi mạng/timeout → `GmailRetryableError` (`retryable=True`).
- 4xx khác → `GmailApiError` (không thử lại, không phải lỗi token).
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from typing import Any, Protocol

import httpx

__all__ = [
    "GMAIL_API_BASE_URL",
    "MAX_RESULTS_LIMIT",
    "SNIPPET_MAX_LENGTH",
    "EmailReadAdapter",
    "EmailSummary",
    "GmailApiError",
    "GmailReadAdapter",
    "GmailReauthRequiredError",
    "GmailRetryableError",
]

GMAIL_API_BASE_URL = "https://gmail.googleapis.com/gmail/v1"
SNIPPET_MAX_LENGTH = 300
MAX_RESULTS_LIMIT = 50
_METADATA_HEADERS = ("Subject", "From", "Date")
# Giới hạn số request messages.get chạy song song — tránh tự gây 429 khi max_results lớn.
_GET_CONCURRENCY = 5


class GmailApiError(Exception):
    """Lỗi gọi Gmail không thuộc hai loại dưới (vd. 400/404). Message không chứa token."""

    code = "email_provider_error"
    retryable = False

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(f"{self.code}: {message}")
        self.status_code = status_code


class GmailReauthRequiredError(GmailApiError):
    """Token hết hạn/bị thu hồi/không đủ quyền — founder cần kết nối lại email.

    Tên ổn định để lịch nền (B5) map sang `blocked_reauth` (kiểm `isinstance` qua
    `GatewayExecutionResult.failure`, hoặc tiền tố `email_reauth_required:` trong message).
    """

    code = "email_reauth_required"


class GmailRetryableError(GmailApiError):
    """429 / 5xx / lỗi mạng — thử lại sau được."""

    code = "email_provider_unavailable"
    retryable = True


@dataclass(frozen=True)
class EmailSummary:
    id: str
    thread_id: str
    subject: str
    sender: str
    date: str
    snippet: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


class EmailReadAdapter(Protocol):
    async def list_unread(
        self, access_token: str, *, max_results: int = 20
    ) -> list[EmailSummary]: ...


class GmailReadAdapter:
    """Implementation `EmailReadAdapter` cho Gmail. `transport` để test tiêm
    `httpx.MockTransport` — test không gọi mạng thật."""

    def __init__(
        self,
        *,
        base_url: str = GMAIL_API_BASE_URL,
        timeout: float = 15.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._transport = transport

    async def list_unread(self, access_token: str, *, max_results: int = 20) -> list[EmailSummary]:
        if not isinstance(max_results, int) or not 1 <= max_results <= MAX_RESULTS_LIMIT:
            raise ValueError(f"max_results phải trong khoảng 1..{MAX_RESULTS_LIMIT}")
        if not access_token:
            raise GmailReauthRequiredError("chưa có access token — founder cần kết nối lại email")

        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=self._timeout,
            transport=self._transport,
        ) as client:
            listing = await self._get_json(
                client,
                "/users/me/messages",
                params={"q": "is:unread", "maxResults": max_results},
            )
            ids = [
                str(item["id"])
                for item in (listing.get("messages") or [])
                if isinstance(item, dict) and item.get("id")
            ][:max_results]
            if not ids:
                return []

            semaphore = asyncio.Semaphore(_GET_CONCURRENCY)

            async def fetch(msg_id: str) -> EmailSummary:
                async with semaphore:
                    data = await self._get_json(
                        client,
                        f"/users/me/messages/{msg_id}",
                        params=[
                            ("format", "metadata"),
                            *(("metadataHeaders", h) for h in _METADATA_HEADERS),
                        ],
                    )
                return _to_summary(msg_id, data)

            return list(await asyncio.gather(*(fetch(i) for i in ids)))

    async def _get_json(self, client: httpx.AsyncClient, path: str, *, params: Any) -> dict:
        try:
            res = await client.get(path, params=params)
        except httpx.HTTPError as err:
            # Không đưa str(err) vào message: có thể chứa URL/headers.
            raise GmailRetryableError(f"không kết nối được Gmail ({type(err).__name__})") from None
        status = res.status_code
        if status in (401, 403):
            raise GmailReauthRequiredError(
                "token hết hạn hoặc không đủ quyền — founder cần kết nối lại email",
                status_code=status,
            )
        if status == 429 or status >= 500:
            raise GmailRetryableError(
                f"Gmail tạm thời không phục vụ (HTTP {status})", status_code=status
            )
        if status >= 400:
            raise GmailApiError(f"Gmail từ chối yêu cầu (HTTP {status})", status_code=status)
        try:
            data = res.json()
        except ValueError:
            raise GmailApiError("Gmail trả phản hồi không phải JSON", status_code=status) from None
        return data if isinstance(data, dict) else {}


def _to_summary(msg_id: str, data: dict) -> EmailSummary:
    raw_headers = (data.get("payload") or {}).get("headers") or []
    headers: dict[str, str] = {}
    for h in raw_headers:
        if isinstance(h, dict) and isinstance(h.get("name"), str):
            headers.setdefault(h["name"].lower(), str(h.get("value") or ""))
    return EmailSummary(
        id=str(data.get("id") or msg_id),
        thread_id=str(data.get("threadId") or ""),
        subject=headers.get("subject", ""),
        sender=headers.get("from", ""),
        date=headers.get("date", ""),
        snippet=str(data.get("snippet") or "")[:SNIPPET_MAX_LENGTH],
    )
