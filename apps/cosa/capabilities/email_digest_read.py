"""Capability `email.digest.read` (plan hub vận hành đợt 2 B3) — T0, đọc email chưa đọc rút gọn.

Luồng credential (quyết định controller, lệch plan "adapter Gmail qua MCP manifest G-6"):
khung MCP hiện có (`mcp_connectors.py`) dùng MỘT token chung cho cả server qua `auth_env`, không
đáp ứng "agent chỉ dùng token đã cấp qua grant connector của founder". Nên:

1. Spec khai báo `connector_requirements={"connector_id": "email-read"}` — cùng cơ chế các tool
   MCP (`mcp_tool_to_capability_spec`): CapabilityGateway re-verify grant connector `email-read`
   của workspace/conversation ở MỌI lần execute (Bước 8.5, qua `ConnectorGrantHttpClient`); không
   có grant ⇒ gateway DENY trước khi tới handler.
2. Handler lấy ĐÚNG grant gateway vừa verify qua `agent.capabilities.connector_grant_context`
   (gateway set cho đúng 1 tool call) — không gọi control-plane assert lần hai. Không có grant
   (vd. gateway không cấu hình resolver) ⇒ `EmailNotConnectedError`, không trả rỗng im lặng.
3. `grant.metadata["secret_ref"]` → `resolve_connector_secret` (resolver tiêm được; dev đọc env
   `COSA_CONNECTOR_SECRET_<REF>`) → access token OAuth.
4. `GmailReadAdapter` gọi thẳng Gmail REST API, chỉ metadata (subject/from/date/snippet ≤300).

Lỗi adapter giữ nguyên kiểu: `GmailReauthRequiredError` (`email_reauth_required:`) cho 401/403 —
B5 map sang `blocked_reauth`; `GmailRetryableError` cho 429/5xx.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from agent.capabilities.connector_grant_context import get_current_connector_grant
from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk
from agent_integrations.gmail import (
    MAX_RESULTS_LIMIT,
    EmailReadAdapter,
    GmailReadAdapter,
)

from apps.cosa.capabilities.connector_secret import (
    ConnectorSecretUnresolvableError,
    resolve_connector_secret,
)

__all__ = [
    "EMAIL_CONNECTOR_KEY",
    "EMAIL_DIGEST_READ_SPEC",
    "EmailNotConnectedError",
    "create_email_digest_read_handler",
]

EMAIL_CONNECTOR_KEY = "email-read"
DEFAULT_MAX_RESULTS = 20
_ALLOWED_ARGS = frozenset({"max_results"})

EMAIL_DIGEST_READ_SPEC = CapabilitySpec(
    id="email.digest.read",
    description=(
        "List the founder's UNREAD emails from their connected mailbox as short summaries "
        "(subject, sender, date, snippet) — never the full body. Use it to prepare an email "
        "digest. Requires the founder to have connected email in the Tools tab; if it reports "
        "the mailbox is not connected or needs reconnecting, tell the founder to (re)connect it."
    ),
    # Cùng risk/approval với capability đọc hiện có (business.read): T0, không cần duyệt.
    risk=CapabilityRisk.LOW,
    approval_policy=ApprovalPolicy.NEVER,
    connector_requirements={"connector_id": EMAIL_CONNECTOR_KEY},
    input_schema={
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS_LIMIT},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "emails": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "thread_id": {"type": "string"},
                        "subject": {"type": "string"},
                        "sender": {"type": "string"},
                        "date": {"type": "string"},
                        "snippet": {"type": "string"},
                    },
                },
            },
            "count": {"type": "integer"},
        },
    },
    metadata={"risk_class": "READ", "data_category": "PERSONAL", "scope": "mail:read"},
)


class EmailNotConnectedError(RuntimeError):
    """Workspace/phiên chưa có grant connector `email-read` dùng được."""

    code = "email_not_connected"

    def __init__(self) -> None:
        super().__init__(
            f"{self.code}: chưa kết nối email — founder cần kết nối hộp thư ở tab Công cụ "
            "và cấp quyền cho phiên này"
        )


def create_email_digest_read_handler(
    adapter: EmailReadAdapter | None = None,
) -> Callable[[dict[str, Any], Any], Coroutine[Any, Any, dict[str, Any]]]:
    reader: EmailReadAdapter = adapter or GmailReadAdapter()

    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        unknown = sorted(set(payload) - _ALLOWED_ARGS)
        if unknown:
            raise ValueError(f"email.digest.read: tham số không được phép: {', '.join(unknown)}")
        max_results = payload.get("max_results", DEFAULT_MAX_RESULTS)
        if (
            isinstance(max_results, bool)
            or not isinstance(max_results, int)
            or not 1 <= max_results <= MAX_RESULTS_LIMIT
        ):
            raise ValueError(f"email.digest.read: max_results phải trong 1..{MAX_RESULTS_LIMIT}")

        grant = get_current_connector_grant()
        if grant is None or grant.connector_id != EMAIL_CONNECTOR_KEY or grant.is_revoked:
            raise EmailNotConnectedError()
        secret_ref = str((grant.metadata or {}).get("secret_ref") or "")
        if not secret_ref:
            raise ConnectorSecretUnresolvableError(EMAIL_CONNECTOR_KEY)

        access_token = await resolve_connector_secret(secret_ref, connector_key=EMAIL_CONNECTOR_KEY)
        emails = await reader.list_unread(access_token, max_results=max_results)
        return {"emails": [e.to_dict() for e in emails], "count": len(emails)}

    return handler
