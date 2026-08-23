import pytest

from agentos.agents.agent_registry import AgentRegistry
from agentos.agents.parallel import ParallelFanOut
from agentos.agents.supervisor import SupervisorAgent
from agentos.core.model_provider import ModelResponse, StubModelProvider
from agentos.core.models import AgentRunStatus, TaskContext
from agentos.core.runtime import AgentRuntime
from agentos.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_supervisor_delegates_to_a_real_agent_runtime_specialist():
    sales_provider = StubModelProvider([ModelResponse(text="Lead qualified: high intent.")])
    sales_runtime = AgentRuntime(sales_provider, ToolRegistry())

    finance_provider = StubModelProvider([ModelResponse(text="Invoice reviewed: approved.")])
    finance_runtime = AgentRuntime(finance_provider, ToolRegistry())

    registry = AgentRegistry()
    registry.register(
        "sales_specialist", sales_runtime, domain="sales", intents=["qualify lead", "sales outreach"]
    )
    registry.register("finance_specialist", finance_runtime, domain="finance", intents=["review invoice"])
    supervisor = SupervisorAgent(registry)

    task = TaskContext(goal="qualify this inbound lead", agent_key="supervisor", workspace_id="ws1")
    result = await supervisor.run(task)

    assert result.status == AgentRunStatus.COMPLETED
    assert result.output == "Lead qualified: high intent."


@pytest.mark.asyncio
async def test_parallel_fan_out_runs_multiple_real_agent_runtimes():
    market_runtime = AgentRuntime(StubModelProvider([ModelResponse(text="market: growing")]), ToolRegistry())
    competitor_runtime = AgentRuntime(
        StubModelProvider([ModelResponse(text="competitor: 3 major players")]), ToolRegistry()
    )

    fan_out = ParallelFanOut([market_runtime, competitor_runtime])
    task = TaskContext(goal="research the market", agent_key="fanout", workspace_id="ws1")

    results = await fan_out.run(task)

    assert [r.output for r in results] == ["market: growing", "competitor: 3 major players"]
    assert all(r.status == AgentRunStatus.COMPLETED for r in results)
