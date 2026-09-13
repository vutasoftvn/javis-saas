from __future__ import annotations

import pytest

from agent.workflows.models import StepOutcome, StepStatus
from agent.workflows.retry_step import RetryWorkflowStep


class FailingHandler:
    def __init__(self, fail_times: int) -> None:
        self.fail_times = fail_times
        self.calls = 0

    async def __call__(self, state: dict) -> StepOutcome:
        self.calls += 1
        if self.calls <= self.fail_times:
            return StepOutcome(status=StepStatus.FAILED, error="transient error")
        return StepOutcome(status=StepStatus.COMPLETED, updates={"success": True})


@pytest.mark.asyncio
async def test_retry_stops_at_declared_limit():
    failing_handler = FailingHandler(fail_times=5)
    step = RetryWorkflowStep(failing_handler, max_attempts=2, initial_backoff=0.01)
    outcome = await step.run({})
    assert outcome.status == StepStatus.FAILED
    assert failing_handler.calls == 2


@pytest.mark.asyncio
async def test_retry_succeeds_before_limit():
    failing_handler = FailingHandler(fail_times=2)
    step = RetryWorkflowStep(failing_handler, max_attempts=4, initial_backoff=0.01)
    outcome = await step.run({})
    assert outcome.status == StepStatus.COMPLETED
    assert outcome.updates == {"success": True}
    assert failing_handler.calls == 3


@pytest.mark.asyncio
async def test_retry_persists_attempt_count_in_state():
    failing_handler = FailingHandler(fail_times=1)
    step = RetryWorkflowStep(failing_handler, name="calc_step", max_attempts=3, initial_backoff=0.01)
    state = {}
    outcome = await step.run(state)
    assert outcome.status == StepStatus.COMPLETED
    assert state.get("_retry_attempts", {}).get("calc_step") == 2
