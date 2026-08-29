from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk

from apps.cosa.capabilities.client import CompanyServiceClient, CompanyServiceError

logger = logging.getLogger("cosa.capabilities.engagement_message_send")

__all__ = ["ENGAGEMENT_MESSAGE_SEND_SPEC", "create_engagement_message_send_handler"]

ENGAGEMENT_MESSAGE_SEND_SPEC = CapabilitySpec(
    id="engagement.message.send",
    description="Gửi tin nhắn công khai tới khách hàng trong thread (P0 sendPublicMessage). "
    "MẶC ĐỊNH BẮT BUỘC APPROVAL trừ khi khớp template pre-authorize chính xác. "
    "Delivery thật do P0 relay và ownership check đảm bảo.",
    risk=CapabilityRisk.HIGH,
    approval_policy=ApprovalPolicy.ALWAYS,
    idempotency_semantics="idempotency_key",
    input_schema={
        "type": "object",
        "required": ["thread_id", "body", "idempotency_key"],
        "properties": {
            "thread_id": {"type": "string", "description": "ID của thread cần gửi tin nhắn"},
            "body": {"type": "string", "description": "Nội dung tin nhắn cần gửi"},
            "idempotency_key": {"type": "string", "description": "Khóa chống trùng lặp"},
            "template_ref": {
                "type": "string",
                "description": "Mã tham chiếu template FAQ (nếu có)",
            },
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "message_id": {"type": "string"},
            "delivery_state": {"type": "string"},
        },
    },
)


def create_engagement_message_send_handler(
    company_client: CompanyServiceClient,
) -> Callable[[dict[str, Any], Any], Coroutine[Any, Any, dict[str, Any]]]:
    """Tạo handler gửi tin nhắn qua Company service (P0 API)."""

    async def handle(args: dict[str, Any], ctx: Any) -> dict[str, Any]:
        thread_id = args.get("thread_id")
        if not thread_id:
            raise ValueError("engagement.message.send: thiếu thread_id")

        body = args.get("body")
        if not body or not str(body).strip():
            raise ValueError("engagement.message.send: body không được rỗng")

        idempotency_key = args.get("idempotency_key")
        if not idempotency_key:
            raise ValueError("engagement.message.send: thiếu idempotency_key")

        workspace_id = (
            getattr(ctx, "workspace_id", None)
            if not isinstance(ctx, dict)
            else ctx.get("workspace_id")
        )
        if not workspace_id or str(workspace_id).strip() in ("", "default", "default_workspace"):
            raise ValueError(
                "engagement.message.send: workspace_id bắt buộc và không được là default"
            )

        headers = {"X-Workspace-Id": str(workspace_id)}

        payload = {
            "body": str(body).strip(),
            "idempotencyKey": str(idempotency_key),
            "templateRef": args.get("template_ref"),
        }

        try:
            res = await company_client.post(
                f"/commercial/engagement/threads/{thread_id}/messages",
                json=payload,
                headers=headers,
            )
            message_id = str(res.get("messageId") or res.get("id") or "")
            delivery_state = str(res.get("deliveryState") or "queued")
            return {
                "message_id": message_id,
                "delivery_state": delivery_state,
            }
        except CompanyServiceError as exc:
            if exc.status_code == 409:
                logger.warning(
                    "engagement.message.send 409 conflict / takeover on thread %s: %s",
                    thread_id,
                    exc,
                )
                return {
                    "message_id": "",
                    "delivery_state": "cancelled",
                    "reason": "conflict_or_taken_over",
                }
            raise

    return handle
