from __future__ import annotations

from typing import Any, Optional
from google.adk.workflow._function_node import FunctionNode

from agentos.core.context_builder import ContextBuilder
from agentos.core.models import TaskContext
from agentos.tools.registry import ToolRegistry


def build_company_context_node(
    context_builder: Optional[ContextBuilder] = None,
    tool_registry: Optional[ToolRegistry] = None,
) -> FunctionNode:
    builder = context_builder or ContextBuilder(tool_registry or ToolRegistry())

    async def build_company_context_fn(ctx: Any) -> dict[str, Any]:
        task = ctx.state.get("task")
        if not isinstance(task, TaskContext):
            task = TaskContext(
                goal=ctx.state.get("goal", ""),
                agent_key=ctx.state.get("agent_key", "chief_of_staff"),
                workspace_id=ctx.state.get("workspace_id", "default_ws"),
                company_id=ctx.state.get("company_id"),
                user_id=ctx.state.get("user_id"),
                role=ctx.state.get("role", "founder"),
            )

        agent_context = await builder.build(task)
        ctx.state["agent_context"] = agent_context
        ctx.state["memory_snippets"] = agent_context.memory_snippets
        ctx.state["knowledge_snippets"] = agent_context.knowledge_snippets
        ctx.state["knowledge_citations"] = [
            c.model_dump() for c in getattr(agent_context, "knowledge_citations", [])
        ]
        ctx.state["skill_instructions"] = agent_context.skill_instructions

        return {
            "memory_snippets_count": len(agent_context.memory_snippets),
            "knowledge_snippets_count": len(agent_context.knowledge_snippets),
        }

    return FunctionNode(func=build_company_context_fn, name="build_company_context_node")
