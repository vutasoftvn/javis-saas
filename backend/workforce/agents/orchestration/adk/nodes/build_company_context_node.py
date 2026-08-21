# backend/app/workforce/agents/orchestration/adk/nodes/build_company_context_node.py
"""FunctionNode tất định gọi lại nguyên vẹn build_agent_context/
CofounderContextAssembler.assemble (không đổi nội bộ 2 hàm này)."""
import json
from typing import Any

from google.adk.workflow._function_node import FunctionNode

from db.session import SessionLocal
from workforce.agents.context.assembler import CofounderContextAssembler
from workforce.agents.context.builder import build_agent_context
from workforce.routing.deterministic import Intent


async def build_company_context_fn(ctx: Any) -> dict[str, Any]:
    workspace_id = ctx.state["workspace_id"]
    company_id = ctx.state.get("company_id")
    user_id = ctx.state.get("user_id")
    active_domains = ctx.state.get("active_domains") or ctx.state.get("requested_domains") or ctx.state.get("domains") or []
    intent = ctx.state.get("intent")
    raw_intent = intent if isinstance(intent, Intent) else (Intent(intent) if intent else Intent.FOUNDER_COMMAND)

    db = SessionLocal()
    try:
        agent_ctx = build_agent_context(
            db=db, workspace_id=workspace_id, company_id=company_id,
            agent_key="chief_of_staff", user_id=user_id,
        )
        cofounder_context = CofounderContextAssembler.assemble(
            db=db, workspace_id=workspace_id, intent=raw_intent,
            business_signal_domains=tuple(active_domains) if active_domains else None,
        )
    finally:
        db.close()

    agent_context_dict = (
        agent_ctx.model_dump(mode="json") if hasattr(agent_ctx, "model_dump")
        else json.loads(json.dumps(agent_ctx, default=str))
    )
    cofounder_json = json.loads(json.dumps(cofounder_context, default=str))
    ctx.state["agent_context"] = agent_context_dict
    ctx.state["cofounder_context"] = cofounder_json
    ctx.state["company_context"] = cofounder_json
    return {"agent_context": agent_context_dict, "cofounder_context": cofounder_json}


def build_company_context_node() -> FunctionNode:
    return FunctionNode(func=build_company_context_fn, name="build_company_context_node")
