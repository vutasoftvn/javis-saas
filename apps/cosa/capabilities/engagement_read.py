from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from agent_core.contracts.capability import CapabilitySpec
from agent_core.governance.contracts import ApprovalPolicy, CapabilityRisk

from apps.cosa.capabilities.client import CompanyServiceClient

logger = logging.getLogger("cosa.capabilities.engagement_read")

__all__ = ["ENGAGEMENT_THREAD_READ_SPEC", "create_engagement_thread_read_handler"]

ENGAGEMENT_THREAD_READ_SPEC = CapabilitySpec(
    id="engagement.thread.read",
    description="Đọc context tối thiểu hoá của một conversation thread (status, SLA, message metadata, "
    "internal note, assignment, labels) cho Customer Support Copilot. KHÔNG billing/subscription.",
    risk=CapabilityRisk.LOW,
    approval_policy=ApprovalPolicy.NEVER,
    idempotency_semantics="payload_deterministic",
    input_schema={
        "type": "object",
        "required": ["thread_id"],
        "properties": {"thread_id": {"type": "string"}, "message_limit": {"type": "integer", "default": 30}},
    },
    output_schema={"type": "object", "properties": {"thread": {"type": "object"}, "messages": {"type": "array"}}},
)


def create_engagement_thread_read_handler(
    company_client: CompanyServiceClient,
) -> Callable[[dict[str, Any], Any], Coroutine[Any, Any, dict[str, Any]]]:
    async def handle(args: dict[str, Any], ctx: Any) -> dict[str, Any]:
        workspace_id = _resolve_workspace_id(args, ctx)
        thread_id = args.get("thread_id")
        if not thread_id:
            raise ValueError("engagement.thread.read: thiếu thread_id")
        headers = {"X-Workspace-Id": str(workspace_id)}
        res = await company_client.get(
            f"/commercial/engagement/threads/{thread_id}/context", headers=headers
        )
        return res or {"thread": None, "messages": []}

    return handle


def _resolve_workspace_id(args: dict[str, Any], ctx: Any) -> str:
    wid = ctx.get("workspace_id") if isinstance(ctx, dict) else getattr(ctx, "workspace_id", None)
    if not wid and "workspace_id" in args:
        wid = str(args["workspace_id"])
    if not wid:
        raise ValueError("engagement.thread.read: thiếu workspace_id")
    return str(wid)
