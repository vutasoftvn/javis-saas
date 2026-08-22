# backend/agentos/core/context_builder.py
from __future__ import annotations

import logging
from typing import Any
from agentos.core.context import AgentContext
from agentos.core.models import TaskContext
from agentos.memory.retriever import MemoryRetriever
from agentos.skills.instruction_loader import SkillInstructionLoader
from agentos.skills.router import SkillRouter
from agentos.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

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
        knowledge_retriever: Any | None = None,
        conversation_history_provider: Any | None = None,
    ) -> None:
        self._tool_registry = tool_registry
        self._system_policy = system_policy
        self._memory_retriever = memory_retriever
        self._skill_router = skill_router
        self._skill_instruction_loader = skill_instruction_loader
        self._knowledge_retriever = knowledge_retriever
        self._conversation_history_provider = conversation_history_provider

    async def build(
        self,
        task: TaskContext,
        *,
        conversation_messages: list[dict[str, Any]] | None = None,
    ) -> AgentContext:
        memory_snippets = await self._memory_retriever.retrieve(task) if self._memory_retriever else []

        knowledge_snippets: list[str] = []
        if self._knowledge_retriever is not None:
            try:
                knowledge_snippets = await self._knowledge_retriever.retrieve(task)
            except Exception as exc:
                logger.warning(
                    "Knowledge retrieval failed or Phase 7 not fully ready: %s. Continuing with empty snippets.",
                    exc,
                )
                knowledge_snippets = []
        else:
            logger.info("Knowledge retriever is not configured (Phase 7). Returning empty snippets.")

        history: list[dict[str, Any]] = []
        if conversation_messages is not None:
            history = conversation_messages
        elif task.metadata and ("conversation_messages" in task.metadata or "history" in task.metadata):
            history = task.metadata.get("conversation_messages") or task.metadata.get("history") or []
        elif self._conversation_history_provider is not None:
            conv_id = task.metadata.get("conversation_id")
            if conv_id:
                history = await self._conversation_history_provider.get_recent_messages(
                    conversation_id=conv_id,
                    workspace_id=task.workspace_id,
                    limit=task.metadata.get("history_limit", 10),
                )


        tool_names = self._tool_registry.names()
        if task.metadata and "allowed_tools" in task.metadata:
            allowed_set = set(task.metadata["allowed_tools"])
            tool_names = [t for t in tool_names if t in allowed_set]

        sys_policy = self._system_policy
        if task.metadata and task.metadata.get("mission"):
            sys_policy = f"{sys_policy}\nAgent Mission: {task.metadata['mission']}"

        return AgentContext(
            task=task,
            system_policy=sys_policy,
            tool_names=tool_names,
            memory_snippets=memory_snippets,
            knowledge_snippets=knowledge_snippets,
            conversation_messages=history,
            skill_instructions=self._select_skill_instructions(task),
            role=task.role,
            agent_permission_level=task.agent_permission_level,
            company_id=task.company_id,
            workspace_id=task.workspace_id,
            user_id=task.user_id,
            workforce_member_id=task.workforce_member_id,
            correlation_id=task.correlation_id,
        )

    def _select_skill_instructions(self, task: TaskContext) -> list[str]:
        if self._skill_router is None or self._skill_instruction_loader is None:
            return []
        allowed_skills = task.metadata.get("allowed_skills") if task.metadata else None
        try:
            selected = self._skill_router.select(
                task.goal,
                role=task.role,
                agent_permission_level=task.agent_permission_level,
                allowed_skills=allowed_skills,
            )
        except TypeError:
            try:
                selected = self._skill_router.select(
                    task.goal,
                    role=task.role,
                    agent_permission_level=task.agent_permission_level,
                )
            except TypeError:
                selected = self._skill_router.select(task.goal)

        if selected is None:
            return []
        return [self._skill_instruction_loader.load(selected.metadata.id)]
