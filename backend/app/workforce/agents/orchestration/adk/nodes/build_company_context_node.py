# backend/app/workforce/agents/orchestration/adk/nodes/build_company_context_node.py
"""FunctionNode dựng company context qua CofounderContextAssembler — dùng lại
nguyên vẹn assembler hiện có (CofounderContextAssembler.assemble_scoped)."""
from typing import Any

from google.adk.workflow._function_node import FunctionNode

from app.workforce.agents.context import CofounderContextAssembler
from app.workforce.routing.deterministic import Intent


async def build_company_context_fn(ctx: Any) -> dict[str, Any]:
    db = ctx.state["db"]
    workspace_id = ctx.state["workspace_id"]
    domains = ctx.state.get("domains", ["sales", "finance"])
    raw_intent = ctx.state.get("intent")
    intent = raw_intent if isinstance(raw_intent, Intent) else (Intent(raw_intent) if raw_intent else Intent.FOUNDER_COMMAND)

    bundle = CofounderContextAssembler.assemble(
        db=db,
        workspace_id=workspace_id,
        intent=intent,
        business_signal_domains=tuple(domains) if domains else None,
    )
    ctx.state["company_context"] = bundle
    return {"company_context": bundle}



def build_company_context_node() -> FunctionNode:
    return FunctionNode(func=build_company_context_fn, name="build_company_context_node")
