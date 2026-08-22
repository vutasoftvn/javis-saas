import pytest

from agentos.core.models import AgentResult, AgentRunStatus, TaskContext
from agentos.workflows.models import StepStatus
from agentos.workflows.steps import AgentStep, DeterministicStep, WorkflowStep


class _EchoAgent:
    async def run(self, task: TaskContext) -> AgentResult:
        return AgentResult(run_id="r", status=AgentRunStatus.COMPLETED, output=f"researched: {task.goal}")


class _FailingAgent:
    async def run(self, task: TaskContext) -> AgentResult:
        return AgentResult(run_id="r", status=AgentRunStatus.FAILED, error="model unavailable")


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
