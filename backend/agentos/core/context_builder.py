from __future__ import annotations

from agentos.core.context import AgentContext
from agentos.core.models import TaskContext
from agentos.tools.registry import ToolRegistry

DEFAULT_SYSTEM_POLICY = (
    "You are an AI Agent OS agent. Use only the tools listed. "
    "Never fabricate tool results."
)


class ContextBuilder:
    def __init__(self, tool_registry: ToolRegistry, system_policy: str = DEFAULT_SYSTEM_POLICY) -> None:
        self._tool_registry = tool_registry
        self._system_policy = system_policy

    def build(self, task: TaskContext) -> AgentContext:
        return AgentContext(
            task=task,
            system_policy=self._system_policy,
            tool_names=self._tool_registry.names(),
        )
