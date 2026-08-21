# backend/app/workforce/agents/orchestration/adk/nodes/governance_gate_node.py
"""FunctionNode tất định bọc BudgetTracker/StuckDetector — dùng lại tại nhiều
điểm trong graph, giống closure check_governance() trong chief_of_staff.py hiện
tại (KHÔNG đổi nội bộ BudgetTracker/StuckDetector, chỉ gọi lại nguyên vẹn)."""
from typing import Any

from agent_runtime.sessions.models import AgentRun
from google.adk.workflow._function_node import FunctionNode

from db.session import SessionLocal
from workforce.agents.governance.budget import BudgetTracker, MissionBudget
from workforce.agents.governance.stuck_detector import StuckDetector


async def governance_gate_fn(ctx: Any) -> dict[str, Any]:
    mission_id = ctx.state["mission_id"]
    budget_raw = ctx.state.get("mission_budget")
    if isinstance(budget_raw, dict):
        budget = MissionBudget(**budget_raw)
    elif isinstance(budget_raw, MissionBudget):
        budget = budget_raw
    else:
        budget = None

    current_step = ctx.state.get("current_step", 0)

    db = SessionLocal()
    try:
        mission_run = db.query(AgentRun).filter(AgentRun.id == mission_id).one()
        budget_result = BudgetTracker.check(db=db, agent_run=mission_run, budget=budget, current_step=current_step)
        if budget_result.is_exceeded:
            ctx.state["governance_block_reason"] = budget_result.message
            ctx.route = "blocked"
            return {"blocked": True, "reason_code": budget_result.reason_code}

        stuck_result = StuckDetector.analyze_run(db=db, run_id=mission_run.id)
        if stuck_result.is_stuck and stuck_result.suggested_action == "ABORT_RUN":
            ctx.state["governance_block_reason"] = f"Stuck loop detected: {stuck_result.detail}"
            ctx.route = "blocked"
            return {"blocked": True, "reason_code": "STUCK_LOOP"}
    finally:
        db.close()

    ctx.route = "continue"
    return {"blocked": False}


def build_governance_gate_node(name: str = "governance_gate_node") -> FunctionNode:
    return FunctionNode(func=governance_gate_fn, name=name)
