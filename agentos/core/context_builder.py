# backend/agentos/core/context_builder.py
from __future__ import annotations

from agentos.core.context import AgentContext
from agentos.core.models import TaskContext
from agentos.memory.retriever import MemoryRetriever
from agentos.skills.instruction_loader import SkillInstructionLoader
from agentos.skills.router import SkillRouter
from agentos.tools.registry import ToolRegistry

DEFAULT_SYSTEM_POLICY = (
    "You are an AI Agent OS agent. Use only the tools listed. "
    "Never fabricate tool results."
)


class ContextBuilder:
    def __init__(
        self,
        tool_registry: ToolRegistry,
        system_policy: str = DEFAULT_SYSTEM_POLICY,
        memory_retriever: MemoryRetriever | None = None,
        skill_router: SkillRouter | None = None,
        skill_instruction_loader: SkillInstructionLoader | None = None,
    ) -> None:
        self._tool_registry = tool_registry
        self._system_policy = system_policy
        self._memory_retriever = memory_retriever
        self._skill_router = skill_router
        self._skill_instruction_loader = skill_instruction_loader

    async def build(self, task: TaskContext) -> AgentContext:
        memory_snippets = await self._memory_retriever.retrieve(task) if self._memory_retriever else []
        return AgentContext(
            task=task,
            system_policy=self._system_policy,
            tool_names=self._tool_registry.names(),
            memory_snippets=memory_snippets,
            skill_instructions=self._select_skill_instructions(task),
        )

    def _select_skill_instructions(self, task: TaskContext) -> list[str]:
        if self._skill_router is None or self._skill_instruction_loader is None:
            return []
        selected = self._skill_router.select(task.goal)
        if selected is None:
            return []
        return [self._skill_instruction_loader.load(selected.metadata.id)]
