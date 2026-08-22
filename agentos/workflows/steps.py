from __future__ import annotations

from typing import Any, Awaitable, Callable, Protocol, runtime_checkable

from agentos.core.agent import Agent
from agentos.core.models import AgentRunStatus, TaskContext
from agentos.workflows.models import StepOutcome, StepStatus


@runtime_checkable
class WorkflowStep(Protocol):
    name: str

    async def run(self, state: dict[str, Any]) -> StepOutcome:
        ...


class DeterministicStep:
    """A plain deterministic business step (blueprint §45: business
    workflow logic must not be replaced by an LLM). `fn` receives the
    current workflow state and returns a dict of updates to merge in.
    """

    def __init__(self, name: str, fn: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]) -> None:
        self.name = name
        self._fn = fn

    async def run(self, state: dict[str, Any]) -> StepOutcome:
        updates = await self._fn(state)
        return StepOutcome(status=StepStatus.COMPLETED, updates=updates)


class AgentStep:
    """An agent-reasoning step (blueprint §45: agent workflow can be
    probabilistic). Reads `goal_key` from state as the agent's goal and
    writes the agent's output to `output_key`.
    """

    def __init__(
        self,
        name: str,
        agent: Agent,
        *,
        goal_key: str,
        output_key: str,
        agent_key: str,
        workspace_key: str = "workspace_id",
    ) -> None:
        self.name = name
        self._agent = agent
        self._goal_key = goal_key
        self._output_key = output_key
        self._agent_key = agent_key
        self._workspace_key = workspace_key

    async def run(self, state: dict[str, Any]) -> StepOutcome:
        task = TaskContext(
            goal=state[self._goal_key],
            agent_key=self._agent_key,
            workspace_id=state[self._workspace_key],
        )
        result = await self._agent.run(task)
        if result.status != AgentRunStatus.COMPLETED:
            return StepOutcome(status=StepStatus.FAILED, error=result.error or "agent step did not complete")
        return StepOutcome(status=StepStatus.COMPLETED, updates={self._output_key: result.output})
