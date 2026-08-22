import pytest

from agentos.agents.sequential import SequentialPipeline
from agentos.core.models import AgentResult, AgentRunStatus, TaskContext


class _EchoAgent:
    def __init__(self, prefix: str) -> None:
        self._prefix = prefix

    async def run(self, task: TaskContext) -> AgentResult:
        return AgentResult(run_id="r", status=AgentRunStatus.COMPLETED, output=f"{self._prefix}:{task.goal}")


class _FailingAgent:
    async def run(self, task: TaskContext) -> AgentResult:
        return AgentResult(run_id="r", status=AgentRunStatus.FAILED, error="boom")


@pytest.mark.asyncio
async def test_sequential_pipeline_feeds_output_forward():
    pipeline = SequentialPipeline([_EchoAgent("plan"), _EchoAgent("execute")])
    task = TaskContext(goal="ship the feature", agent_key="pipeline", workspace_id="ws1")

    results = await pipeline.run(task)

    assert [r.output for r in results] == ["plan:ship the feature", "execute:plan:ship the feature"]


@pytest.mark.asyncio
async def test_sequential_pipeline_stops_on_first_failure():
    pipeline = SequentialPipeline([_EchoAgent("plan"), _FailingAgent(), _EchoAgent("never runs")])
    task = TaskContext(goal="ship the feature", agent_key="pipeline", workspace_id="ws1")

    results = await pipeline.run(task)

    assert len(results) == 2
    assert results[-1].status == AgentRunStatus.FAILED
