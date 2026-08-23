from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, NamedTuple, Protocol, runtime_checkable

from agent_core.workflows.models import StepOutcome, StepStatus

__all__ = [
    "WorkflowStep",
    "DeterministicStep",
    "AgentRunnerProtocol",
    "AgentStep",
    "ParallelBranch",
    "ParallelStep",
    "CompensatingStep",
    "RetryStep",
]


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


@runtime_checkable
class AgentRunnerProtocol(Protocol):
    """Protocol trừu tượng cho Agent Runner trong WorkflowStep."""
    async def run(self, task: Any) -> Any:
        ...


class AgentStep:
    """An agent-reasoning step (blueprint §45: agent workflow can be
    probabilistic). Reads `goal_key` from state as the agent's goal and
    writes the agent's output to `output_key`.
    """

    def __init__(
        self,
        name: str,
        agent: Any,
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
        # Hỗ trợ cả TaskContext object hoặc dict task
        class SimpleTaskContext:
            def __init__(self, goal: str, agent_key: str, workspace_id: str):
                self.goal = goal
                self.agent_key = agent_key
                self.workspace_id = workspace_id

        task = SimpleTaskContext(
            goal=state.get(self._goal_key, ""),
            agent_key=self._agent_key,
            workspace_id=state.get(self._workspace_key, ""),
        )
        result = await self._agent.run(task)
        status_val = getattr(result, "status", None)
        status_str = str(getattr(status_val, "value", status_val) or "").upper()
        if status_str not in ("COMPLETED", "SUCCESS"):
            err = getattr(result, "error", None) or "agent step did not complete"
            return StepOutcome(status=StepStatus.FAILED, error=err)
        return StepOutcome(status=StepStatus.COMPLETED, updates={self._output_key: getattr(result, "output", result)})


class ParallelBranch(NamedTuple):
    """Một nhánh fan-out của ParallelStep."""
    name: str
    agent: Any
    goal_key: str
    agent_key: str


class ParallelStep:
    """Bước chạy song song (Parallel pattern): chạy đồng thời agent của từng
    nhánh, merge kết quả vào state[output_key] dạng {branch_name: output}.
    Chỉ FAILED khi tất cả các nhánh đều fail.
    """

    def __init__(
        self,
        name: str,
        branches: list[ParallelBranch],
        *,
        output_key: str,
        workspace_key: str = "workspace_id",
    ) -> None:
        if not branches:
            raise ValueError("ParallelStep requires at least one branch")
        self.name = name
        self._branches = branches
        self._output_key = output_key
        self._workspace_key = workspace_key

    async def run(self, state: dict[str, Any]) -> StepOutcome:
        class SimpleTaskContext:
            def __init__(self, goal: str, agent_key: str, workspace_id: str):
                self.goal = goal
                self.agent_key = agent_key
                self.workspace_id = workspace_id

        async def run_branch(branch: ParallelBranch):
            task = SimpleTaskContext(
                goal=state.get(branch.goal_key, ""),
                agent_key=branch.agent_key,
                workspace_id=state.get(self._workspace_key, ""),
            )
            return branch.name, await branch.agent.run(task)

        results = await asyncio.gather(*(run_branch(branch) for branch in self._branches))

        outputs: dict[str, Any] = {}
        failures: list[str] = []
        for branch_name, result in results:
            status_val = getattr(result, "status", None)
            status_str = str(getattr(status_val, "value", status_val) or "").upper()
            if status_str in ("COMPLETED", "SUCCESS"):
                outputs[branch_name] = getattr(result, "output", result)
            else:
                failures.append(branch_name)

        if not outputs:
            return StepOutcome(
                status=StepStatus.FAILED,
                error=f"all parallel branches failed: {', '.join(failures)}",
            )
        return StepOutcome(status=StepStatus.COMPLETED, updates={self._output_key: outputs})


class CompensatingStep:
    """Bọc một step với hành động compensate chạy khi có step *sau đó*
    trong cùng workflow bị fail.
    """

    def __init__(self, step: WorkflowStep, *, compensate: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
        self.name = step.name
        self._step = step
        self.compensate = compensate

    async def run(self, state: dict[str, Any]) -> StepOutcome:
        return await self._step.run(state)


class RetryStep:
    """Retry step con tối đa `max_attempts` lần khi trả về FAILED."""

    def __init__(self, step: WorkflowStep, *, max_attempts: int = 3) -> None:
        from agent_core.workflows.approval_step import ApprovalGateStep

        if isinstance(step, ApprovalGateStep):
            raise TypeError("RetryStep cannot wrap an ApprovalGateStep")
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self.name = step.name
        self._step = step
        self._max_attempts = max_attempts
        self.attempts_made = 0

    async def run(self, state: dict[str, Any]) -> StepOutcome:
        outcome: StepOutcome | None = None
        for attempt in range(1, self._max_attempts + 1):
            self.attempts_made = attempt
            outcome = await self._step.run(state)
            if outcome.status != StepStatus.FAILED:
                return outcome
        assert outcome is not None
        return outcome
