from __future__ import annotations

from typing import Any, Optional
from google.adk.workflow._function_node import FunctionNode

from agentos.core.approval import ApprovalService, ApprovalStatus


def build_approval_gate_node(approval_service: Optional[ApprovalService] = None) -> FunctionNode:
    service = approval_service or ApprovalService()

    async def approval_gate_fn(ctx: Any) -> dict[str, Any]:
        mission_id = ctx.state.get("mission_id")
        action = ctx.state.get("action", "adk_mission_execution")
        subject = ctx.state.get("goal", "Mission goal")
        requester = ctx.state.get("requester", "adk_orchestrator")

        existing_id = ctx.state.get("pending_approval_id")
        if existing_id:
            try:
                approval = service.get(existing_id)
                if approval.status == ApprovalStatus.APPROVED:
                    ctx.state["approval_status"] = "APPROVED"
                    ctx.route = "approved"
                    return {"status": "APPROVED"}
                elif approval.status == ApprovalStatus.DENIED:
                    ctx.state["approval_status"] = "DENIED"
                    ctx.route = "denied"
                    return {"status": "DENIED", "reason": approval.reason}
                else:
                    ctx.route = "pending"
                    return {"status": "PENDING"}
            except Exception:
                pass

        approval = service.request_approval(
            action=action,
            subject=subject,
            requester=requester,
            run_id=mission_id,
            correlation_id=ctx.state.get("correlation_id"),
        )
        ctx.state["pending_approval_id"] = approval.id
        ctx.state["approval_status"] = "PENDING"
        ctx.route = "pending"
        return {"status": "PENDING", "approval_id": approval.id}

    return FunctionNode(func=approval_gate_fn, name="approval_gate_node")
