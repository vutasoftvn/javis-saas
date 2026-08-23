from __future__ import annotations

from typing import Any
from google.adk.workflow._function_node import FunctionNode


async def planning_fn(ctx: Any) -> dict[str, Any]:
    active_domains = ctx.state.get("active_domains") or ["strategy", "sales", "finance"]
    ctx.state["status"] = "planning"
    ctx.state["active_domains"] = active_domains
    return {"active_domains": active_domains, "status": "planning"}


def build_planning_node() -> FunctionNode:
    return FunctionNode(func=planning_fn, name="planning_node")
