import pytest

from agentos.core.agent import Agent
from agentos.core.context import AgentContext
from agentos.core.models import AgentResult, AgentRunStatus, TaskContext


class _FakeAgent:
    async def run(self, task: TaskContext) -> AgentResult:
        return AgentResult(run_id="r1", status=AgentRunStatus.COMPLETED, output="ok")


def test_fake_agent_satisfies_protocol():
    assert isinstance(_FakeAgent(), Agent)


@pytest.mark.asyncio
async def test_fake_agent_run_returns_result():
    task = TaskContext(goal="hi", agent_key="fake", workspace_id="ws1")
    result = await _FakeAgent().run(task)
    assert result.status == AgentRunStatus.COMPLETED


def test_agent_context_holds_task_and_policy():
    task = TaskContext(goal="hi", agent_key="fake", workspace_id="ws1")
    context = AgentContext(task=task, system_policy="be nice", tool_names=["echo"])
    assert context.task == task
    assert context.tool_names == ["echo"]
    assert context.memory_snippets == []
