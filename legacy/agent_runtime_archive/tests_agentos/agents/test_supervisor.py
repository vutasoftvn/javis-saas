import pytest

from agentos.agents.agent_registry import AgentRegistry
from agentos.agents.supervisor import SupervisorAgent, score_agent
from agentos.core.agent import Agent
from agentos.core.models import AgentResult, AgentRunStatus, TaskContext


class _FakeAgent:
    def __init__(self, tag: str) -> None:
        self._tag = tag

    async def run(self, task: TaskContext) -> AgentResult:
        return AgentResult(run_id="r1", status=AgentRunStatus.COMPLETED, output=f"handled by {self._tag}")


def test_score_agent_rewards_matching_intents():
    assert score_agent("qualify this lead", ["qualify lead", "score lead"]) > score_agent(
        "qualify this lead", ["review invoice"]
    )


def test_supervisor_satisfies_agent_protocol():
    assert isinstance(SupervisorAgent(AgentRegistry()), Agent)


@pytest.mark.asyncio
async def test_supervisor_delegates_to_highest_scoring_specialist():
    registry = AgentRegistry()
    registry.register(
        "sales_specialist", _FakeAgent("sales"), domain="sales", intents=["qualify lead", "sales outreach"]
    )
    registry.register("finance_specialist", _FakeAgent("finance"), domain="finance", intents=["review invoice"])
    supervisor = SupervisorAgent(registry)
    task = TaskContext(goal="qualify this new lead", agent_key="supervisor", workspace_id="ws1")

    result = await supervisor.run(task)

    assert result.status == AgentRunStatus.COMPLETED
    assert result.output == "handled by sales"


@pytest.mark.asyncio
async def test_supervisor_respects_domain_scope():
    registry = AgentRegistry()
    registry.register("sales_specialist", _FakeAgent("sales"), domain="sales", intents=["qualify lead"])
    registry.register("finance_specialist", _FakeAgent("finance"), domain="finance", intents=["qualify lead"])
    supervisor = SupervisorAgent(registry, domain="finance")
    task = TaskContext(goal="qualify this lead", agent_key="supervisor", workspace_id="ws1")

    result = await supervisor.run(task)

    assert result.output == "handled by finance"


@pytest.mark.asyncio
async def test_supervisor_returns_failed_result_when_no_specialist_matches():
    registry = AgentRegistry()
    registry.register("sales_specialist", _FakeAgent("sales"), domain="sales", intents=["qualify lead"])
    supervisor = SupervisorAgent(registry)
    task = TaskContext(goal="completely unrelated task", agent_key="supervisor", workspace_id="ws1")

    result = await supervisor.run(task)

    assert result.status == AgentRunStatus.FAILED
    assert result.error is not None
