import pytest

from agentos.core.approval import ApprovalService
from agentos.core.models import AgentResult, AgentRunStatus, TaskContext
from agentos.core.policy import PermissionClass, PolicyEngine
from agentos.workflows.approval_step import ApprovalGateStep
from agentos.workflows.models import StepOutcome, StepStatus
from agentos.workflows.steps import (
    AgentStep,
    CompensatingStep,
    DeterministicStep,
    ParallelBranch,
    ParallelStep,
    RetryStep,
    WorkflowStep,
)


class _EchoAgent:
    async def run(self, task: TaskContext) -> AgentResult:
        return AgentResult(run_id="r", status=AgentRunStatus.COMPLETED, output=f"researched: {task.goal}")


class _FailingAgent:
    async def run(self, task: TaskContext) -> AgentResult:
        return AgentResult(run_id="r", status=AgentRunStatus.FAILED, error="model unavailable")


class _LabeledAgent:
    def __init__(self, label: str, *, fail: bool = False) -> None:
        self._label = label
        self._fail = fail

    async def run(self, task: TaskContext) -> AgentResult:
        if self._fail:
            return AgentResult(run_id="r", status=AgentRunStatus.FAILED, error=f"{self._label} failed")
        return AgentResult(run_id="r", status=AgentRunStatus.COMPLETED, output=f"{self._label}: {task.goal}")


async def _write_record(state: dict) -> dict:
    return {"record_id": "rec-123"}


def test_deterministic_step_satisfies_protocol():
    assert isinstance(DeterministicStep("write", _write_record), WorkflowStep)


def test_agent_step_satisfies_protocol():
    step = AgentStep("research", _EchoAgent(), goal_key="goal", output_key="research", agent_key="researcher")
    assert isinstance(step, WorkflowStep)


@pytest.mark.asyncio
async def test_deterministic_step_merges_returned_updates():
    step = DeterministicStep("write", _write_record)

    outcome = await step.run({})

    assert outcome.status == StepStatus.COMPLETED
    assert outcome.updates == {"record_id": "rec-123"}


@pytest.mark.asyncio
async def test_agent_step_writes_output_to_output_key():
    step = AgentStep("research", _EchoAgent(), goal_key="goal", output_key="research_notes", agent_key="researcher")
    state = {"goal": "market size for widgets", "workspace_id": "ws1"}

    outcome = await step.run(state)

    assert outcome.status == StepStatus.COMPLETED
    assert outcome.updates == {"research_notes": "researched: market size for widgets"}


@pytest.mark.asyncio
async def test_agent_step_fails_when_agent_does_not_complete():
    step = AgentStep("research", _FailingAgent(), goal_key="goal", output_key="research_notes", agent_key="researcher")
    state = {"goal": "market size for widgets", "workspace_id": "ws1"}

    outcome = await step.run(state)

    assert outcome.status == StepStatus.FAILED
    assert outcome.error == "model unavailable"


@pytest.mark.asyncio
async def test_parallel_step_merges_every_branch_output():
    step = ParallelStep(
        "research-fanout",
        [
            ParallelBranch("market", _LabeledAgent("market"), "goal", "market_agent"),
            ParallelBranch("competitor", _LabeledAgent("competitor"), "goal", "competitor_agent"),
        ],
        output_key="research",
    )
    state = {"goal": "widgets", "workspace_id": "ws1"}

    outcome = await step.run(state)

    assert outcome.status == StepStatus.COMPLETED
    assert outcome.updates == {
        "research": {"market": "market: widgets", "competitor": "competitor: widgets"}
    }


@pytest.mark.asyncio
async def test_parallel_step_keeps_successful_branches_when_one_fails():
    step = ParallelStep(
        "research-fanout",
        [
            ParallelBranch("market", _LabeledAgent("market"), "goal", "market_agent"),
            ParallelBranch("competitor", _LabeledAgent("competitor", fail=True), "goal", "competitor_agent"),
        ],
        output_key="research",
    )
    state = {"goal": "widgets", "workspace_id": "ws1"}

    outcome = await step.run(state)

    assert outcome.status == StepStatus.COMPLETED
    assert outcome.updates == {"research": {"market": "market: widgets"}}


@pytest.mark.asyncio
async def test_parallel_step_fails_only_when_every_branch_fails():
    step = ParallelStep(
        "research-fanout",
        [
            ParallelBranch("market", _LabeledAgent("market", fail=True), "goal", "market_agent"),
            ParallelBranch("competitor", _LabeledAgent("competitor", fail=True), "goal", "competitor_agent"),
        ],
        output_key="research",
    )
    state = {"goal": "widgets", "workspace_id": "ws1"}

    outcome = await step.run(state)

    assert outcome.status == StepStatus.FAILED
    assert "market" in outcome.error and "competitor" in outcome.error


def test_parallel_step_rejects_empty_branches():
    with pytest.raises(ValueError):
        ParallelStep("empty", [], output_key="research")


@pytest.mark.asyncio
async def test_retry_step_returns_first_success_without_extra_attempts():
    calls = 0

    async def _flaky(state: dict) -> dict:
        nonlocal calls
        calls += 1
        return {"ok": True}

    step = RetryStep(DeterministicStep("flaky", _flaky), max_attempts=3)

    outcome = await step.run({})

    assert outcome.status == StepStatus.COMPLETED
    assert calls == 1
    assert step.attempts_made == 1


@pytest.mark.asyncio
async def test_retry_step_retries_until_success_within_max_attempts():
    calls = 0

    async def _flaky(state: dict) -> dict:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise RuntimeError("transient")
        return {"ok": True}

    class _FlakyStep:
        name = "flaky"

        async def run(self, state):
            try:
                updates = await _flaky(state)
            except RuntimeError as exc:
                return StepOutcome(status=StepStatus.FAILED, error=str(exc))
            return StepOutcome(status=StepStatus.COMPLETED, updates=updates)

    step = RetryStep(_FlakyStep(), max_attempts=3)

    outcome = await step.run({})

    assert outcome.status == StepStatus.COMPLETED
    assert calls == 3
    assert step.attempts_made == 3


@pytest.mark.asyncio
async def test_retry_step_gives_up_after_max_attempts():
    class _AlwaysFailsStep:
        name = "nope"

        async def run(self, state):
            return StepOutcome(status=StepStatus.FAILED, error="still broken")

    step = RetryStep(_AlwaysFailsStep(), max_attempts=2)

    outcome = await step.run({})

    assert outcome.status == StepStatus.FAILED
    assert outcome.error == "still broken"
    assert step.attempts_made == 2


def test_retry_step_rejects_wrapping_an_approval_gate_step():
    gate = ApprovalGateStep(
        "gate",
        policy_engine=PolicyEngine(),
        approval_service=ApprovalService(),
        permission=PermissionClass.SEND_MESSAGE,
        action="send",
        subject_key="x",
        requester="agent",
    )
    with pytest.raises(TypeError):
        RetryStep(gate)


@pytest.mark.asyncio
async def test_compensating_step_runs_the_wrapped_step_and_satisfies_protocol():
    compensated = []

    async def _compensate(state: dict) -> None:
        compensated.append(state.get("record_id"))

    step = CompensatingStep(DeterministicStep("write", _write_record), compensate=_compensate)
    assert isinstance(step, WorkflowStep)

    outcome = await step.run({})

    assert outcome.status == StepStatus.COMPLETED
    assert outcome.updates == {"record_id": "rec-123"}
    assert compensated == []  # compensate is only invoked by WorkflowEngine, not by run()
