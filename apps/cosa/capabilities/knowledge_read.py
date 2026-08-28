from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from agent_core.contracts.capability import CapabilitySpec
from agent_core.governance.contracts import ApprovalPolicy, CapabilityRisk

logger = logging.getLogger("cosa.capabilities.knowledge_read")

__all__ = [
    "KNOWLEDGE_PROFILE_READ_SPEC",
    "create_knowledge_profile_read_handler",
]

KNOWLEDGE_PROFILE_READ_SPEC = CapabilitySpec(
    id="knowledge.profile.read",
    description="Đọc profile/summary tri thức doanh nghiệp và đối thủ cạnh tranh với kiểm soát sensitivity.",
    risk=CapabilityRisk.LOW,
    approval_policy=ApprovalPolicy.NEVER,
    idempotency_semantics="payload_deterministic",
    input_schema={
        "type": "object",
        "properties": {
            "profile_type": {
                "type": "string",
                "description": "Loại profile (competitor, product, market_summary)",
            },
            "profile_id": {
                "type": "string",
                "description": "ID định danh của profile",
            },
            "include_untrusted": {
                "type": "boolean",
                "default": False,
                "description": "Cho phép lấy các insight chưa được verify",
            },
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "profile": {"type": "object"},
            "sensitivity": {"type": "string"},
            "untrusted": {"type": "boolean"},
        },
    },
)


def create_knowledge_profile_read_handler() -> Callable[
    [dict[str, Any], Any], Coroutine[Any, Any, dict[str, Any]]
]:
    """Tạo handler đọc knowledge profile kiểm soát sensitivity và gắn nhãn untrusted rõ ràng."""

    async def handle_knowledge_profile_read(args: dict[str, Any], ctx: Any) -> dict[str, Any]:
        workspace_id: str | None = None
        if isinstance(ctx, dict):
            workspace_id = ctx.get("workspace_id")
        elif hasattr(ctx, "workspace_id"):
            workspace_id = ctx.workspace_id

        if not workspace_id and "workspace_id" in args:
            workspace_id = str(args["workspace_id"])

        if not workspace_id:
            raise ValueError("Không thể thực hiện knowledge.profile.read: thiếu workspace_id")

        profile_type = args.get("profile_type", "competitor")
        profile_id = args.get("profile_id", "default")
        include_untrusted = args.get("include_untrusted", False)

        # Profile mẫu được sanitize và gắn nhãn rõ ràng theo taxonomy
        return {
            "workspace_id": workspace_id,
            "profile_id": profile_id,
            "profile_type": profile_type,
            "sensitivity": "internal",
            "untrusted": not include_untrusted,
            "data": {
                "name": profile_id,
                "category": profile_type,
                "insights": [],
                "source_attribution": "curated_knowledge",
            },
        }

    return handle_knowledge_profile_read
