# backend/app/workforce/agents/orchestration/adk/nodes/create_mission_node.py
"""FunctionNode đầu tiên trong AdkCofounderWorkflow — tạo Outcome/OutcomeRun/
AgentRun ở trạng thái draft/queued/created, y hệt nhánh không-resume của
chief_of_staff.py::orchestrate (giữ nguyên hành vi: mission ở "draft" cho tới
khi risk-gate (Task 12) xác nhận auto_start)."""
from datetime import datetime, timezone
from typing import Any

from agent_runtime.sessions.models import AgentRun
from google.adk.workflow._function_node import FunctionNode

from app.core.snowflake import generate_snowflake_id
from app.db.session import SessionLocal
from app.founder_os.outcomes.models import Outcome, OutcomeRun
from app.workforce.agents.governance.budget import MissionBudget


async def create_mission_fn(ctx: Any) -> dict[str, Any]:
    goal = ctx.state["goal"]
    workspace_id = ctx.state["workspace_id"]
    user_id = ctx.state["user_id"]
    company_id = ctx.state.get("company_id") or workspace_id
    active_domains = ctx.state.get("requested_domains") or ctx.state.get("domains") or []
    intent = ctx.state.get("intent")
    budget_raw = ctx.state.get("mission_budget")
    if isinstance(budget_raw, dict):
        budget_dict = budget_raw
    elif isinstance(budget_raw, MissionBudget):
        budget_dict = budget_raw.model_dump()
    else:
        budget_dict = MissionBudget().model_dump()

    db = SessionLocal()
    try:
        existing_mission_id = ctx.state.get("existing_mission_id")
        if existing_mission_id:
            mission_run = db.query(AgentRun).filter(AgentRun.id == existing_mission_id).one()
            outcome_run = db.query(OutcomeRun).filter(OutcomeRun.id == mission_run.outcome_run_id).one()
            outcome = db.query(Outcome).filter(Outcome.id == outcome_run.outcome_id).one()
            mission_id = mission_run.id
            outcome_id = outcome.id
            outcome_run_id = outcome_run.id
        else:
            mission_id = generate_snowflake_id()
            outcome = Outcome(
                id=generate_snowflake_id(), workspace_id=workspace_id, function="strategy",
                title=f"Mission: {goal[:200]}", desired_result=goal, requested_by=user_id,
                status="draft", created_at=datetime.now(timezone.utc),
            )
            db.add(outcome)

            outcome_run = OutcomeRun(
                id=generate_snowflake_id(), outcome_id=outcome.id, agent_run_id=None,
                status="queued", verification_status="UNKNOWN",
                started_at=datetime.now(timezone.utc), created_at=datetime.now(timezone.utc),
            )
            db.add(outcome_run)
            db.flush()

            mission_run = AgentRun(
                id=mission_id, workspace_id=workspace_id, company_id=company_id, user_id=user_id,
                outcome_run_id=outcome_run.id, agent_key="chief_of_staff", runtime="adk",
                status="created", permission_profile="chief_of_staff_suggest",
                budget_jsonb=budget_dict,
                metadata_jsonb={
                    "goal": goal, "domains": active_domains,
                    "intent": intent.value if intent is not None and hasattr(intent, "value") else intent,
                },
                started_at=datetime.now(timezone.utc),
            )
            db.add(mission_run)
            db.flush()
            outcome_run.agent_run_id = mission_id
            db.commit()

            outcome_id, outcome_run_id = outcome.id, outcome_run.id
    finally:
        db.close()


    ctx.state["mission_id"] = mission_id
    ctx.state["outcome_id"] = outcome_id
    ctx.state["outcome_run_id"] = outcome_run_id
    ctx.state["active_domains"] = active_domains
    return {"mission_id": mission_id}


def build_create_mission_node() -> FunctionNode:
    return FunctionNode(func=create_mission_fn, name="create_mission_node")
