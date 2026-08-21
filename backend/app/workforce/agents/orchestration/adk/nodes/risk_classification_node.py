# backend/app/workforce/agents/orchestration/adk/nodes/risk_classification_node.py
"""FunctionNode tất định — risk-tier R0-R4 KHÔNG để LLM tự quyết (đúng cách
chief_of_staff.py hiện không để LLM tự quyết action-plan, xem Quyết định 1)."""
from typing import Any

from google.adk.workflow._function_node import FunctionNode

from app.workforce.agents.orchestration.specialist_registry import (
    AUTO_START_MAX_RISK,
    RISK_ORDER,
    classify_mission_risk,
)


async def risk_classification_fn(ctx: Any) -> dict[str, str]:
    active_domains: list[str] = ctx.state.get("active_domains", [])
    risk_level = classify_mission_risk(active_domains)
    ctx.state["risk_level"] = risk_level
    ctx.route = (
        "auto_start"
        if RISK_ORDER.index(risk_level) <= RISK_ORDER.index(AUTO_START_MAX_RISK)
        else "needs_confirmation"
    )
    return {"risk_level": risk_level}


def build_risk_classification_node() -> FunctionNode:
    return FunctionNode(func=risk_classification_fn, name="risk_classification_node")
