# backend/app/workforce/agents/orchestration/adk/nodes/build_company_context_node.py
"""FunctionNode tất định gọi lại nguyên vẹn build_agent_context/
CofounderContextAssembler.assemble (không đổi nội bộ 2 hàm này)."""
from typing import Any

from google.adk.workflow._function_node import FunctionNode

from app.db.session import SessionLocal
from app.workforce.agents.context.assembler import CofounderContextAssembler
from app.workforce.agents.context.builder import build_agent_context
from app.workforce.routing.deterministic import Intent


async def build_company_context_fn(ctx: Any) -> dict[str, Any]:
    workspace_id = ctx.state["workspace_id"]
    company_id = ctx.state.get("company_id")
    user_id = ctx.state["user_id"]
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

    agent_context_dict = agent_ctx.model_dump()
    ctx.state["agent_context"] = agent_context_dict
    ctx.state["cofounder_context"] = cofounder_context
    ctx.state["company_context"] = cofounder_context
    return {"agent_context": agent_context_dict, "cofounder_context": cofounder_context}



def build_company_context_node() -> FunctionNode:
    return FunctionNode(func=build_company_context_fn, name="build_company_context_node")
