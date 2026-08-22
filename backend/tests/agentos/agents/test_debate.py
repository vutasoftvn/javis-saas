import pytest

from agentos.agents.debate import DebateLoop
from agentos.core.models import AgentResult, AgentRunStatus, TaskContext


class _ScriptedAgent:
    def __init__(self, outputs: list[str]) -> None:
        self._outputs = list(outputs)

    async def run(self, task: TaskContext) -> AgentResult:
        output = self._outputs.pop(0)
        return AgentResult(run_id="r", status=AgentRunStatus.COMPLETED, output=output)


@pytest.mark.asyncio
async def test_debate_loop_stops_immediately_when_critic_approves():
    generator = _ScriptedAgent(["draft v1"])
    critic = _ScriptedAgent(["approved"])
    loop = DebateLoop(generator, critic)
    task = TaskContext(goal="write a tagline", agent_key="debate", workspace_id="ws1")

    generator_result, critic_result = await loop.run(task)

    assert generator_result.output == "draft v1"
    assert critic_result.output == "approved"


@pytest.mark.asyncio
async def test_debate_loop_revises_once_then_stops_at_max_rounds():
    generator = _ScriptedAgent(["draft v1", "draft v2"])
    critic = _ScriptedAgent(["needs more punch", "still not great"])
    loop = DebateLoop(generator, critic, max_rounds=2)
    task = TaskContext(goal="write a tagline", agent_key="debate", workspace_id="ws1")

    generator_result, critic_result = await loop.run(task)

    assert generator_result.output == "draft v2"
    assert critic_result.output == "still not great"


@pytest.mark.asyncio
async def test_debate_loop_respects_max_rounds_of_one():
    generator = _ScriptedAgent(["draft v1"])
    critic = _ScriptedAgent(["needs work"])
    loop = DebateLoop(generator, critic, max_rounds=1)
    task = TaskContext(goal="write a tagline", agent_key="debate", workspace_id="ws1")

    generator_result, critic_result = await loop.run(task)

    assert generator_result.output == "draft v1"
    assert critic_result.output == "needs work"
