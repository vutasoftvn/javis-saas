from __future__ import annotations

from typing import Any
from google.adk.workflow._function_node import FunctionNode
from agentos.core.policy import ToolRiskLevel


def classify_domains_risk(domains: list[str]) -> ToolRiskLevel:
    # Deterministic risk classification mapping
    high_risk_domains = {"legal", "finance_transfer", "production_deploy", "admin"}
    medium_risk_domains = {"sales_outreach", "finance", "strategy"}

    for d in domains:
        if d in high_risk_domains:
            return ToolRiskLevel.HIGH
    for d in domains:
        if d in medium_risk_domains:
            return ToolRiskLevel.MEDIUM
    return ToolRiskLevel.LOW


async def risk_classification_fn(ctx: Any) -> dict[str, Any]:
    active_domains: list[str] = ctx.state.get("active_domains", [])
    risk_level = ctx.state.get("risk_level")
    if isinstance(risk_level, str):
        try:
            risk_level = ToolRiskLevel(risk_level)
        except ValueError:
            risk_level = classify_domains_risk(active_domains)
    elif not isinstance(risk_level, ToolRiskLevel):
        risk_level = classify_domains_risk(active_domains)

    ctx.state["risk_level"] = risk_level.value
    # LOW and MEDIUM auto_start; HIGH and CRITICAL need confirmation
    if risk_level in (ToolRiskLevel.LOW, ToolRiskLevel.MEDIUM):
        ctx.route = "auto_start"
    else:
        ctx.route = "needs_confirmation"

    return {"risk_level": risk_level.value, "route": ctx.route}


def build_risk_classification_node() -> FunctionNode:
    return FunctionNode(func=risk_classification_fn, name="risk_classification_node")
