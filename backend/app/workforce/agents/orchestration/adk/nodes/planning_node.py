# backend/app/workforce/agents/orchestration/adk/nodes/planning_node.py
"""Chỉ chạy trên route "auto_start" (RiskClassificationNode, Task 12) — mission
ở route "needs_confirmation" KHÔNG đi qua node này, giữ nguyên ở trạng thái draft
cho tới khi seam resume_mission()/confirm_mission() (Task 25) được gọi."""
from datetime import datetime, timezone
from typing import Any

from agent_runtime.sessions.models import AgentRun
from google.adk.workflow._function_node import FunctionNode

from app.db.session import SessionLocal
from app.founder_os.outcomes.models import Outcome, OutcomeRun
from app.workforce.agents.governance.states import validate_run_transition
from app.workforce.agents.orchestration.specialist_registry import DEFAULT_ORCHESTRATION_DOMAINS


async def planning_fn(ctx: Any) -> dict[str, Any]:
    active_domains = ctx.state.get("active_domains") or list(DEFAULT_ORCHESTRATION_DOMAINS)

    db = SessionLocal()
    try:
        outcome = db.query(Outcome).filter(Outcome.id == ctx.state["outcome_id"]).one()
        outcome_run = db.query(OutcomeRun).filter(OutcomeRun.id == ctx.state["outcome_run_id"]).one()
        mission_run = db.query(AgentRun).filter(AgentRun.id == ctx.state["mission_id"]).one()

        outcome.status = "planning"
        outcome_run.status = "running"
        mission_run.status = validate_run_transition(mission_run.status, "running")
        db.commit()
    finally:
        db.close()

    ctx.state["active_domains"] = active_domains
    return {"active_domains": active_domains}


def build_planning_node() -> FunctionNode:
    return FunctionNode(func=planning_fn, name="planning_node")
