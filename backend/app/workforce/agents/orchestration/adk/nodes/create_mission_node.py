# backend/app/workforce/agents/orchestration/adk/nodes/create_mission_node.py
"""FunctionNode tạo Outcome + OutcomeRun + AgentRun (nếu chưa có sẵn từ caller)
— giữ đúng schema canonical, KHÔNG tạo bảng mới (Quyết định 1)."""
from datetime import datetime, timezone
from typing import Any

from google.adk.workflow._function_node import FunctionNode

from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.founder_os.outcomes.models import Outcome, OutcomeRun


async def create_mission_fn(ctx: Any) -> dict[str, Any]:
    db = ctx.state["db"]
    workspace_id = ctx.state["workspace_id"]
    user_id = ctx.state.get("user_id")
    company_id = ctx.state.get("company_id")
    goal = ctx.state["goal"]
    domains = ctx.state.get("domains", ["sales", "finance"])
    intent = ctx.state.get("intent")
    context = ctx.state.get("context")

    outcome = ctx.state.get("outcome")
    outcome_run = ctx.state.get("outcome_run")
    mission_run = ctx.state.get("mission_run")

    if outcome is None:
        outcome = Outcome(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            function="strategy",
            title=f"Co-Founder Mission: {goal[:60]}",
            desired_result=goal,
            requested_by=user_id,
            status="running",
        )
        db.add(outcome)
        db.flush()
        ctx.state["outcome"] = outcome

    if outcome_run is None:
        outcome_run = OutcomeRun(
            id=generate_snowflake_id(),
            outcome_id=outcome.id,
            status="running",
            verification_status="UNKNOWN",
        )
        db.add(outcome_run)
        db.flush()
        ctx.state["outcome_run"] = outcome_run

    if mission_run is None:
        mission_id = generate_snowflake_id()
        mission_run = AgentRun(
            id=mission_id,
            workspace_id=workspace_id,
            company_id=company_id,
            user_id=user_id,
            outcome_run_id=outcome_run.id,
            agent_key="chief_of_staff",
            runtime="adk",
            status="running",
            metadata_jsonb={
                "goal": goal,
                "domains": domains,
                "context": context,
                "intent": getattr(intent, "value", intent) if intent else None,
            },
            started_at=datetime.now(timezone.utc),
        )
        db.add(mission_run)
        db.flush()
        outcome_run.agent_run_id = mission_id
        db.commit()
        ctx.state["mission_run"] = mission_run

    return {"mission_run_id": mission_run.id, "outcome_id": outcome.id, "outcome_run_id": outcome_run.id}


def build_create_mission_node() -> FunctionNode:
    return FunctionNode(func=create_mission_fn, name="create_mission_node")
