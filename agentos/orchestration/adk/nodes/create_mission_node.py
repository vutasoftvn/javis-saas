from __future__ import annotations

import uuid
from typing import Any
from google.adk.workflow._function_node import FunctionNode


async def create_mission_fn(ctx: Any) -> dict[str, Any]:
    goal = ctx.state.get("goal", "")
    workspace_id = ctx.state.get("workspace_id", "default_ws")
    user_id = ctx.state.get("user_id")
    company_id = ctx.state.get("company_id") or workspace_id
    active_domains = ctx.state.get("requested_domains") or ctx.state.get("domains") or ["strategy", "sales", "finance"]

    mission_id = ctx.state.get("existing_mission_id") or str(uuid.uuid4())
    ctx.state["mission_id"] = mission_id
    ctx.state["workspace_id"] = workspace_id
    ctx.state["company_id"] = company_id
    ctx.state["user_id"] = user_id
    ctx.state["goal"] = goal
    ctx.state["active_domains"] = active_domains
    ctx.state["status"] = "created"

    return {"mission_id": mission_id, "active_domains": active_domains}


def build_create_mission_node() -> FunctionNode:
    return FunctionNode(func=create_mission_fn, name="create_mission_node")
