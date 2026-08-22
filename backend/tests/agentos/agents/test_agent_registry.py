import pytest

from agentos.agents.agent_registry import AgentNotFoundError, AgentRegistry
from agentos.core.models import AgentResult, AgentRunStatus, TaskContext


class _FakeAgent:
    async def run(self, task: TaskContext) -> AgentResult:
        return AgentResult(run_id="r1", status=AgentRunStatus.COMPLETED, output="ok")


def test_register_and_get():
    registry = AgentRegistry()
    agent = _FakeAgent()
    registry.register("sales_specialist", agent, domain="sales", intents=["qualify lead"])

    record = registry.get("sales_specialist")

    assert record.agent is agent
    assert record.domain == "sales"
    assert record.intents == ["qualify lead"]


def test_get_missing_agent_raises():
    registry = AgentRegistry()
    with pytest.raises(AgentNotFoundError):
        registry.get("missing")


def test_list_filters_by_domain():
    registry = AgentRegistry()
    registry.register("sales_specialist", _FakeAgent(), domain="sales", intents=["qualify lead"])
    registry.register("finance_specialist", _FakeAgent(), domain="finance", intents=["review invoice"])

    sales_only = registry.list(domain="sales")

    assert [r.agent_key for r in sales_only] == ["sales_specialist"]
