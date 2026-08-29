from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from agent_core.contracts.capability import CapabilitySpec
from agent_core.governance.contracts import ApprovalPolicy, CapabilityRisk
from apps.cosa.capabilities.client import CompanyServiceClient

logger = logging.getLogger("cosa.capabilities.engagement_assignment_write")

__all__ = ["ENGAGEMENT_ASSIGNMENT_WRITE_SPEC", "create_engagement_assignment_write_handler"]

ENGAGEMENT_ASSIGNMENT_WRITE_SPEC = CapabilitySpec(
    id="engagement.assignment.write",
    description="Thay đổi phân phối / gắn nhãn / bàn giao nhân viên (handoff) cho engagement thread. "
    "Mặc định yêu cầu approval (hoặc allow theo rule scope).",
    risk=CapabilityRisk.MEDIUM,
    approval_policy=ApprovalPolicy.CONDITIONAL,
    idempotency_semantics="idempotency_key",
    input_schema={
        "type": "object",
        "required": ["thread_id", "op"],
        "properties": {
            "thread_id": {"type": "string", "description": "ID của thread cần thao tác"},
            "op": {
                "type": "string",
                "enum": ["route_team", "route_member", "apply_label", "handoff_human"],
                "description": "Thao tác thực hiện",
            },
            "team_id": {"type": "string", "description": "ID của Team nếu op=route_team"},
            "member_id": {"type": "string", "description": "ID của Member nếu op=route_member"},
            "label_key": {"type": "string", "description": "Key của Label nếu op=apply_label"},
            "reason": {"type": "string", "description": "Lý do thay đổi phân phối / bàn giao"},
        },
    },
    output_schema={
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "op": {"type": "string"},
            "thread_id": {"type": "string"},
        },
    },
)


def create_engagement_assignment_write_handler(
    company_client: CompanyServiceClient,
) -> Callable[[dict[str, Any], Any], Coroutine[Any, Any, dict[str, Any]]]:
    """Tạo handler ghi nhận phân phối / handoff qua Company service."""

    async def handle(args: dict[str, Any], ctx: Any) -> dict[str, Any]:
        thread_id = args.get("thread_id")
        if not thread_id:
            raise ValueError("engagement.assignment.write: thiếu thread_id")

        op = args.get("op")
        if op not in ("route_team", "route_member", "apply_label", "handoff_human"):
            raise ValueError(f"engagement.assignment.write: op không hợp lệ: {op}")

        workspace_id = (
            getattr(ctx, "workspace_id", None)
            if not isinstance(ctx, dict)
            else ctx.get("workspace_id")
        )
        if not workspace_id or str(workspace_id).strip() in ("", "default", "default_workspace"):
            raise ValueError("engagement.assignment.write: workspace_id bắt buộc và không được là default")

        headers = {"X-Workspace-Id": str(workspace_id)}
        reason = args.get("reason") or f"autopilot_{op}"

        if op == "route_team":
            team_id = args.get("team_id")
            await company_client.post(
                f"/commercial/engagement/threads/{thread_id}/assign",
                json={"teamId": team_id, "reason": reason},
                headers=headers,
            )
        elif op == "route_member":
            member_id = args.get("member_id")
            await company_client.post(
                f"/commercial/engagement/threads/{thread_id}/assign",
                json={"memberId": member_id, "reason": reason},
                headers=headers,
            )
        elif op == "apply_label":
            label_key = args.get("label_key")
            await company_client.post(
                f"/commercial/engagement/threads/{thread_id}/labels",
                json={"labelKey": label_key},
                headers=headers,
            )
        elif op == "handoff_human":
            await company_client.post(
                f"/commercial/engagement/threads/{thread_id}/assign",
                json={"activeMode": "team_queue", "reason": reason},
                headers=headers,
            )

        return {
            "status": "success",
            "op": op,
            "thread_id": str(thread_id),
        }

    return handle
