from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, NamedTuple, Protocol, runtime_checkable

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


class ParallelBranch(NamedTuple):
    """Một nhánh fan-out của ParallelStep: chạy `agent` (với vai trò
    `agent_key`) trên state[goal_key], gắn nhãn `name` cho output khi merge.
    """

    name: str
    agent: Agent
    goal_key: str
    agent_key: str


class ParallelStep:
    """Bước chạy song song (blueprint §9.2 Parallel pattern, ví dụ: Market
    Research / Competitor Research / Customer Research -> Synthesizer):
    chạy đồng thời agent của từng nhánh, merge kết quả vào
    state[output_key] dạng {branch_name: output} để bước sau
    (DeterministicStep/AgentStep) tổng hợp. Cùng hành vi với ParallelFanOut
    (agentos/agents/parallel.py) nhưng ở cấp workflow step — "không thoát
    sớm khi 1 nhánh fail": bước này chỉ FAILED khi tất cả nhánh đều fail.
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
        async def run_branch(branch: ParallelBranch):
            task = TaskContext(
                goal=state[branch.goal_key],
                agent_key=branch.agent_key,
                workspace_id=state[self._workspace_key],
            )
            return branch.name, await branch.agent.run(task)

        results = await asyncio.gather(*(run_branch(branch) for branch in self._branches))

        outputs: dict[str, Any] = {}
        failures: list[str] = []
        for branch_name, result in results:
            if result.status == AgentRunStatus.COMPLETED:
                outputs[branch_name] = result.output
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
    trong cùng workflow bị fail (gap analysis Giai đoạn 3.3 — "compensation
    step: rollback khi 1 bước sau bị reject/fail"). WorkflowEngine gọi
    `compensate(state)` cho mọi CompensatingStep đã hoàn thành, theo thứ tự
    ngược, đúng 1 lần khi workflow chuyển sang FAILED — best-effort: lỗi
    compensate được gom vào workflow.state["_compensation_errors"] thay vì
    raise, để 1 rollback lỗi không chặn các rollback khác chạy tiếp.
    """

    def __init__(self, step: WorkflowStep, *, compensate: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
        self.name = step.name
        self._step = step
        self.compensate = compensate

    async def run(self, state: dict[str, Any]) -> StepOutcome:
        return await self._step.run(state)


class RetryStep:
    """Retry step con tối đa `max_attempts` lần khi nó trả về FAILED, trước
    khi chịu thua (blueprint §81: lỗi transient/business-conflict xứng đáng
    được retry, không nên abort ngay — "không retry mù": chỉ chạy lại đúng
    step đã fail, không bao giờ retry một outcome WAITING_APPROVAL hay
    COMPLETED).

    Cố tình KHÔNG cho bọc ApprovalGateStep: WorkflowEngine.resume() nhận
    diện step đang pause bằng `isinstance(step, ApprovalGateStep)`, và
    quyết định approval (denied vs pending) là quyết định governance, không
    phải lỗi có thể retry — retry nó sẽ âm thầm request lại approval thay vì
    hiện rõ việc bị từ chối.
    """

    def __init__(self, step: WorkflowStep, *, max_attempts: int = 3) -> None:
        from agentos.workflows.approval_step import ApprovalGateStep

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
