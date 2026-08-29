from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from agent.contracts.capability import CapabilitySpec
from agent.governance.contracts import ApprovalPolicy, CapabilityRisk

logger = logging.getLogger("cosa.capabilities.engagement_message_draft")

__all__ = ["ENGAGEMENT_MESSAGE_DRAFT_SPEC", "create_engagement_message_draft_handler"]

ENGAGEMENT_MESSAGE_DRAFT_SPEC = CapabilitySpec(
    id="engagement.message.draft",
    description="Tạo artifact bản nháp trả lời khách hàng kèm evidence_refs và rationale. "
    "HOÀN TOÀN KHÔNG gửi tin, không side-effect bên ngoài.",
    risk=CapabilityRisk.LOW,
    approval_policy=ApprovalPolicy.NEVER,
    idempotency_semantics="payload_deterministic",
    input_schema={
        "type": "object",
        "required": ["thread_id", "draft_body", "evidence_refs"],
        "properties": {
            "thread_id": {"type": "string", "description": "ID của thread cần phản hồi"},
            "draft_body": {"type": "string", "description": "Nội dung bản nháp tin nhắn phản hồi"},
            "evidence_refs": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "description": "Các trích dẫn căn cứ xác thực từ knowledge/thread",
            },
            "rationale": {
                "type": "string",
                "description": "Lý do / tóm tắt giải thích cho bản nháp",
            },
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "artifact_kind": {"type": "string"},
            "thread_id": {"type": "string"},
            "draft_body": {"type": "string"},
            "evidence_refs": {"type": "array"},
            "rationale": {"type": "string"},
            "delivery": {"type": "string"},
        },
    },
)


def create_engagement_message_draft_handler() -> Callable[
    [dict[str, Any], Any], Coroutine[Any, Any, dict[str, Any]]
]:
    """Tạo handler tạo draft artifact an toàn (no network / no side effect)."""

    async def handle(args: dict[str, Any], ctx: Any) -> dict[str, Any]:
        thread_id = args.get("thread_id")
        if not thread_id:
            raise ValueError("engagement.message.draft: thiếu thread_id")

        draft_body = args.get("draft_body")
        if not draft_body or not str(draft_body).strip():
            raise ValueError("engagement.message.draft: draft_body không được rỗng")

        evidence_refs = args.get("evidence_refs")
        if not evidence_refs or not isinstance(evidence_refs, list) or len(evidence_refs) == 0:
            raise ValueError(
                "engagement.message.draft: evidence_refs phải có ít nhất 1 trích dẫn căn cứ"
            )

        rationale = args.get("rationale", "")

        return {
            "artifact_kind": "message_draft",
            "thread_id": str(thread_id),
            "draft_body": str(draft_body).strip(),
            "evidence_refs": [str(ref) for ref in evidence_refs],
            "rationale": str(rationale),
            "delivery": "none",
        }

    return handle
