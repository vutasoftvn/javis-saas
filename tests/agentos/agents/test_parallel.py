import asyncio

import pytest

from agentos.agents.parallel import ParallelFanOut
from agentos.core.models import AgentResult, AgentRunStatus, TaskContext


class _SlowEchoAgent:
    def __init__(self, tag: str, delay: float = 0.0) -> None:
        self._tag = tag
        self._delay = delay

    async def run(self, task: TaskContext) -> AgentResult:
        if self._delay:
            await asyncio.sleep(self._delay)
        return AgentResult(run_id="r", status=AgentRunStatus.COMPLETED, output=self._tag)


@pytest.mark.asyncio
async def test_parallel_fan_out_collects_all_results_in_order():
    fan_out = ParallelFanOut([_SlowEchoAgent("market"), _SlowEchoAgent("competitor"), _SlowEchoAgent("customer")])
    task = TaskContext(goal="research", agent_key="fanout", workspace_id="ws1")

    results = await fan_out.run(task)

    assert [r.output for r in results] == ["market", "competitor", "customer"]


@pytest.mark.asyncio
async def test_parallel_fan_out_runs_concurrently_not_sequentially():
    fan_out = ParallelFanOut([_SlowEchoAgent("a", delay=0.05), _SlowEchoAgent("b", delay=0.05)])
    task = TaskContext(goal="research", agent_key="fanout", workspace_id="ws1")

    loop = asyncio.get_event_loop()
    start = loop.time()
    await fan_out.run(task)
    elapsed = loop.time() - start

    assert elapsed < 0.09  # would be >= 0.1 if the two agents ran sequentially
