from __future__ import annotations

from agentos.core.agent import Agent
from agentos.core.models import AgentResult, AgentRunStatus, TaskContext


class SequentialPipeline:
    """Sequential multi-agent flow (blueprint §9.2): each agent's output
    becomes the next agent's goal. Stops at the first non-COMPLETED
    result — a broken link in the chain should not silently continue.
    """

    def __init__(self, agents: list[Agent]) -> None:
        self._agents = agents

    async def run(self, initial_task: TaskContext) -> list[AgentResult]:
        results: list[AgentResult] = []
        current_task = initial_task
        for agent in self._agents:
            result = await agent.run(current_task)
            results.append(result)
            if result.status != AgentRunStatus.COMPLETED:
                break
            current_task = current_task.model_copy(update={"goal": result.output or current_task.goal})
        return results
