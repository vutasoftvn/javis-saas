from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional
from google.adk.workflow._function_node import FunctionNode

from agentos.core.context import AgentContext
from agentos.core.executor import Executor
from agentos.core.model_provider import ModelProvider
from agentos.core.models import TaskContext
from agentos.core.planner import Planner
from agentos.core.policy import PolicyEngine
from agentos.core.trace import TraceRecorder
from agentos.tools.registry import ToolRegistry


def build_execution_node(
    model_provider: Optional[ModelProvider] = None,
    tool_registry: Optional[ToolRegistry] = None,
    policy_engine: Optional[PolicyEngine] = None,
) -> FunctionNode:
    async def execution_fn(ctx: Any) -> dict[str, Any]:
        specialists = ctx.state.get("delegated_specialists", [])
        goal = ctx.state.get("goal", "")
        workspace_id = ctx.state.get("workspace_id", "default_ws")
        mission_id = ctx.state.get("mission_id", "mission_default")

        # Custom executor factory if supplied in state or default
        custom_runner = ctx.state.get("specialist_runner")

        async def run_specialist(spec_info: dict[str, Any]) -> tuple[str, str, int]:
            domain = spec_info.get("domain", "general")
            agent_key = spec_info.get("agent_key", f"{domain}_specialist")

            if custom_runner is not None:
                output, tools_made = await custom_runner(domain, goal, workspace_id)
                return domain, output, tools_made

            if model_provider is not None and tool_registry is not None:
                trace = TraceRecorder(run_id=f"{mission_id}_{domain}")
                executor = Executor(
                    model_provider=model_provider,
                    tool_registry=tool_registry,
                    planner=Planner(),
                    trace=trace,
                    policy_engine=policy_engine or PolicyEngine(),
                    requester=agent_key,
                )
                task = TaskContext(
                    goal=f"Analyze {domain} aspect for: {goal}",
                    agent_key=agent_key,
                    workspace_id=workspace_id,
                )
                context = AgentContext(task=task, system_policy="Analyze and produce structured findings.")
                output, tools_made = await executor.run(context)
                return domain, output, tools_made

            # Fallback stub specialist analysis
            return domain, f"{domain.capitalize()} specialist report on: {goal}", 0

        # Execute all specialists concurrently in parallel
        results = await asyncio.gather(*(run_specialist(s) for s in specialists))

        specialist_reports: dict[str, Any] = {}
        total_tools_made = 0
        for domain, output, tools_made in results:
            specialist_reports[domain] = {"findings": output, "status": "completed"}
            total_tools_made += tools_made

        ctx.state["specialist_reports"] = specialist_reports
        ctx.state["tool_calls_made"] = total_tools_made
        ctx.state["execution_status"] = "completed"

        return {
            "specialist_reports_count": len(specialist_reports),
            "tool_calls_made": total_tools_made,
        }

    return FunctionNode(func=execution_fn, name="execution_node")
