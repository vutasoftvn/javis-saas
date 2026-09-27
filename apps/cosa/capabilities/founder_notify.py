"""Capability `founder.notify.send` (ADR-FOUNDER-CHANNEL-001, plan hub vận hành đợt 2 B2).

Gửi thông báo vào kênh nhận ĐÃ XÁC MINH của chính founder sở hữu run (T2-self). Schema tool
KHÔNG có tham số người nhận: không `chat_id`, `recipient`, `channel_id` hay member id nào.
Company (`POST /identity/founder-notifications/send`) tự tra kênh theo danh tính trong
delegation của run và từ chối (`invalid_argument`) mọi field ngoài `content`/`channelKind`.

Bậc T2 (`access_matrix`): chat run buộc founder duyệt từng lần; lịch nền chỉ được uỷ quyền
trước qua snapshot của lịch (B5). Lỗi company giữ nguyên `CompanyServiceError` — message mang
mã máy-đọc-được (`founder_channel_unavailable:`, `founder_channel_ambiguous:`,
`founder_owner_not_authorized:`, `founder_channel_delivery_failed:`) để B5 phân loại.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk

from apps.cosa.capabilities.client import CompanyServiceClient
from apps.cosa.capabilities.startup_os_onboard import context_workspace_id

__all__ = ["FOUNDER_NOTIFY_SEND_SPEC", "create_founder_notify_send_handler"]

MAX_CONTENT_LENGTH = 4000
_CHANNEL_KINDS = ("telegram",)
_ALLOWED_ARGS = frozenset({"content", "channel_kind"})
_PATH = "/identity/founder-notifications/send"

FOUNDER_NOTIFY_SEND_SPEC = CapabilitySpec(
    id="founder.notify.send",
    description=(
        "Send a notification to the founder's OWN verified notification channel (e.g. their "
        "Telegram group). You cannot choose a recipient: the destination is always the channel "
        "the founder configured and verified. Founder must approve in chat before it runs. "
        "Keep content concise; never include secrets or tokens."
    ),
    # Cùng risk/approval với capability T2 hiện có (okr.key_result.create).
    risk=CapabilityRisk.MEDIUM,
    approval_policy=ApprovalPolicy.POLICY_DRIVEN,
    input_schema={
        "type": "object",
        "required": ["content"],
        "additionalProperties": False,
        "properties": {
            "content": {"type": "string", "minLength": 1, "maxLength": MAX_CONTENT_LENGTH},
            "channel_kind": {"type": "string", "enum": list(_CHANNEL_KINDS)},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "delivered": {"type": "boolean"},
            "channel_kind": {"type": "string"},
            "channel_label": {"type": "string"},
        },
    },
)


def create_founder_notify_send_handler(
    client: CompanyServiceClient,
) -> Callable[[dict[str, Any], Any], Coroutine[Any, Any, dict[str, Any]]]:
    async def handler(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
        # Không lặng lẽ bỏ qua tham số lạ (vd. model tự thêm chat_id): từ chối rõ ràng.
        unknown = sorted(set(payload) - _ALLOWED_ARGS)
        if unknown:
            raise ValueError(
                f"founder.notify.send: tham số không được phép: {', '.join(unknown)} "
                "(người nhận luôn là kênh đã xác minh của founder)"
            )
        content = payload.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("founder.notify.send: content không được rỗng")
        content = content.strip()
        if len(content) > MAX_CONTENT_LENGTH:
            raise ValueError(f"founder.notify.send: content dài quá {MAX_CONTENT_LENGTH} ký tự")
        channel_kind = payload.get("channel_kind")
        if channel_kind is not None and channel_kind not in _CHANNEL_KINDS:
            raise ValueError("founder.notify.send: channel_kind không được hỗ trợ")

        headers = {"X-Workspace-Id": context_workspace_id(context, FOUNDER_NOTIFY_SEND_SPEC.id)}
        # Body chỉ có content/channelKind — không bao giờ thêm field người nhận.
        body: dict[str, Any] = {"content": content}
        if channel_kind is not None:
            body["channelKind"] = channel_kind
        res = await client.post(_PATH, json=body, headers=headers)
        return {
            "delivered": bool(res.get("delivered")),
            "channel_kind": res.get("channelKind"),
            "channel_label": res.get("channelLabel"),
        }

    return handler
