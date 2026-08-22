from __future__ import annotations

import asyncio

from agentos.core.agent import Agent
from agentos.core.models import AgentResult, TaskContext


class ParallelFanOut:
    """Parallel multi-agent flow (blueprint §9.2): run several agents
    concurrently against the same task and collect every result — no
    early exit on failure, since the whole point of fan-out is that one
    branch's failure shouldn't block the others from completing.
    """

    def __init__(self, agents: list[Agent]) -> None:
        self._agents = agents

    async def run(self, task: TaskContext) -> list[AgentResult]:
        return list(await asyncio.gather(*(agent.run(task) for agent in self._agents)))
