from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

from agentos.core.adapters.contracts import AgentRuntimeAdapter
from agentos.core.approval import ApprovalService
from agentos.core.context import AgentContext
from agentos.core.context_builder import ContextBuilder
from agentos.core.executor import Executor, ToolApprovalRequiredError, ToolPermissionDeniedError
from agentos.core.model_provider import ModelProvider
from agentos.core.models import TaskContext
from agentos.core.planner import Planner
from agentos.core.policy import PermissionLevel, PolicyEngine
from agentos.core.trace import TraceRecorder
from agentos.profiles.registry import AgentProfileRegistry
from agentos.skills.registry import SkillRegistry
from agentos.tools.registry import ToolRegistry


class AdkOrchestrator:
    """Production Multi-Agent Orchestrator implementing `AgentRuntimeAdapter` (contracts.py).
    
    Orchestrates complex missions by delegating sub-tasks to specialized domain agents
    (e.g., Sales, Finance, Strategy, Marketing) that run concurrently in parallel waves.
    
    Guarantees:
    - Parallel execution: Specialists execute concurrently via `asyncio.gather()`.
    - Strict governance: Every side effect is evaluated by `PolicyEngine.evaluate_access()`.
    - No direct side effects: Orchestrator only coordinates; specialists execute tools.
    - Zero legacy imports.
    """

    def __init__(
        self,
        model_provider: ModelProvider,
        tool_registry: ToolRegistry,
        *,
        policy_engine: Optional[PolicyEngine] = None,
        approval_service: Optional[ApprovalService] = None,
        profile_registry: Optional[AgentProfileRegistry] = None,
        skill_registry: Optional[SkillRegistry] = None,
        context_builder: Optional[ContextBuilder] = None,
        default_domains: Optional[list[str]] = None,
    ) -> None:
        self._model_provider = model_provider
        self._tool_registry = tool_registry
        self._policy_engine = policy_engine or PolicyEngine()
        self._approval_service = approval_service or ApprovalService()
        self._profile_registry = profile_registry
        self._skill_registry = skill_registry
        self._context_builder = context_builder or ContextBuilder(tool_registry)
        self._default_domains = default_domains or ["strategy", "sales", "finance"]

    def _resolve_domains_for_task(self, context: AgentContext) -> list[str]:
        # Check if requested domains are specified in metadata
        meta = getattr(context.task, "metadata", {}) or {}
        requested = meta.get("requested_domains") or meta.get("domains")
        if requested and isinstance(requested, list):
            return requested

        goal_lower = context.task.goal.lower()
        active = []
        if any(w in goal_lower for w in ["sale", "revenue", "deal", "pipeline", "customer", "lead"]):
            active.append("sales")
        if any(w in goal_lower for w in ["finance", "cost", "budget", "invoice", "payment", "margin"]):
            active.append("finance")
        if any(w in goal_lower for w in ["strategy", "market", "competitor", "plan", "growth"]):
            active.append("strategy")
        if any(w in goal_lower for w in ["marketing", "campaign", "social", "content"]):
            active.append("marketing")

        return active or self._default_domains

    async def _run_specialist(
        self,
        domain: str,
        parent_context: AgentContext,
    ) -> tuple[str, str, int]:
        agent_key = f"{domain}_specialist"
        role = parent_context.role or parent_context.task.role or "user"
        perm_level = parent_context.agent_permission_level or parent_context.task.agent_permission_level or PermissionLevel.L1_SUGGEST
        meta = parent_context.task.metadata or {}

        task = TaskContext(
            goal=f"Analyze and provide expert domain recommendations for: {parent_context.task.goal}",
            agent_key=agent_key,
            workspace_id=parent_context.task.workspace_id,
            company_id=parent_context.task.company_id,
            user_id=parent_context.task.user_id,
            role=role,
            agent_permission_level=perm_level,
            correlation_id=parent_context.correlation_id,
            metadata={"domain": domain, "parent_goal": parent_context.task.goal},
        )

        specialist_context = await self._context_builder.build(task)
        trace = TraceRecorder(
            run_id=f"{meta.get('run_id', 'mission')}_{domain}",
            correlation_id=parent_context.correlation_id,
            workspace_id=parent_context.task.workspace_id,
            company_id=parent_context.task.company_id,
        )

        executor = Executor(
            model_provider=self._model_provider,
            tool_registry=self._tool_registry,
            planner=Planner(),
            trace=trace,
            policy_engine=self._policy_engine,
            approval_service=self._approval_service,
            requester=agent_key,
        )

        output, tool_calls_made = await executor.run(specialist_context)
        return domain, output, tool_calls_made

    async def run(self, context: AgentContext) -> tuple[str, int]:
        domains = self._resolve_domains_for_task(context)

        # Run specialists concurrently in parallel
        specialist_tasks = [self._run_specialist(domain, context) for domain in domains]
        results = await asyncio.gather(*specialist_tasks)

        total_tool_calls = sum(r[2] for r in results)
        reports = {domain: output for domain, output, _ in results}

        # Synthesis phase
        report_sections = [f"### {domain.upper()} SPECIALIST FINDINGS:\n{output}" for domain, output in reports.items()]
        combined_reports = "\n\n".join(report_sections)

        synthesis_prompt = (
            f"You are the Co-founder synthesizing specialist domain analyses for mission: '{context.task.goal}'.\n\n"
            f"Specialist Findings:\n{combined_reports}\n\n"
            f"Synthesize these findings into an executive decision and concrete next actions."
        )

        resp = await self._model_provider.generate(
            system_prompt="You are a Chief of Staff AI synthesizing multiple specialist reports into unified strategy.",
            messages=[{"role": "user", "content": synthesis_prompt}],
        )

        synthesis_output = resp.text or combined_reports
        final_output = f"{synthesis_output}\n\n---\n**Specialist Contributions ({len(domains)} active domains)**:\n{combined_reports}"

        return final_output, total_tool_calls
