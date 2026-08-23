from __future__ import annotations

from typing import Protocol, runtime_checkable

from agentos.core.models import AgentResult, TaskContext


@runtime_checkable
class Agent(Protocol):
    async def run(self, task: TaskContext) -> AgentResult:
        ...
