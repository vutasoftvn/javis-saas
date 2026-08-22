# backend/app/workforce/agents/orchestration/adk/nodes/approval_gate_node.py
"""Luôn chạy sau QualityGateNode bất kể PASS/FAIL — giống chief_of_staff.py hiện
tại vẫn tạo Approval/Proposal cho action_plan dù quality gate có fail hay không;
chỉ final_status (ExecutionNode) mới bị ảnh hưởng bởi gate."""
from typing import Any

from google.adk.workflow._function_node import FunctionNode

from db.session import SessionLocal
from workforce.agents.orchestration.synthesis_helpers import (
    create_approvals_and_proposals_for_action_plan,
    derive_priorities_and_actions,
)


async def approval_gate_fn(ctx: Any) -> dict[str, Any]:
    workspace_id = ctx.state["workspace_id"]
    mission_id = ctx.state["mission_id"]
    specialist_reports: dict[str, Any] = ctx.state.get("specialist_reports", {})
    sales_data = specialist_reports.get("sales", {})
    fin_data = specialist_reports.get("finance", {})

    priorities, action_plan = derive_priorities_and_actions(sales_data, fin_data)
    db = SessionLocal()
    try:
        required_approvals, created_proposals = create_approvals_and_proposals_for_action_plan(
            db, workspace_id=workspace_id, run_id=mission_id, action_plan=action_plan,
        )
    finally:
        db.close()

    ctx.state["priorities"] = priorities
    ctx.state["action_plan"] = action_plan
    ctx.state["required_approvals"] = required_approvals
    ctx.state["created_proposals"] = created_proposals
    return {"priorities": priorities, "action_plan": action_plan}


def build_approval_gate_node() -> FunctionNode:
    return FunctionNode(func=approval_gate_fn, name="approval_gate_node")
