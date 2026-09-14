from __future__ import annotations

import asyncio
from typing import Any

from agent.workflows.models import StepOutcome, StepStatus

__all__ = ["RetryWorkflowStep"]


class RetryWorkflowStep:
    """Bounded retry step with exponential backoff and attempt tracking."""

    def __init__(
        self,
        step_or_handler: Any,
        *,
        name: str = "retry_step",
        max_attempts: int = 3,
        initial_backoff: float = 0.1,
        backoff_factor: float = 2.0,
        max_backoff: float = 5.0,
    ) -> None:
        from agent.workflows.approval_step import ApprovalGateStep

        if isinstance(step_or_handler, ApprovalGateStep):
            raise TypeError("RetryWorkflowStep cannot wrap an ApprovalGateStep")

        if not (1 <= max_attempts <= 10):
            raise ValueError(f"max_attempts must be between 1 and 10, got {max_attempts}")

        self.name = getattr(step_or_handler, "name", name) or name
        self._inner = step_or_handler
        self.max_attempts = max_attempts
        self.initial_backoff = initial_backoff
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        self.attempts_made = 0

    async def run(self, state: dict[str, Any]) -> StepOutcome:
        retry_map = state.setdefault("_retry_attempts", {})
        last_outcome: StepOutcome | None = None

        for attempt in range(1, self.max_attempts + 1):
            self.attempts_made = attempt
            retry_map[self.name] = attempt

            try:
                if hasattr(self._inner, "run"):
                    outcome = await self._inner.run(state)
                elif callable(self._inner):
                    res = self._inner(state)
                    if asyncio.iscoroutine(res):
                        outcome = await res
                    else:
                        outcome = res
                    if not isinstance(outcome, StepOutcome):
                        if isinstance(outcome, dict):
                            outcome = StepOutcome(status=StepStatus.COMPLETED, updates=outcome)
                        else:
                            outcome = StepOutcome(status=StepStatus.COMPLETED)
                else:
                    return StepOutcome(
                        status=StepStatus.FAILED,
                        error=f"Unexecutable retry target of type {type(self._inner)}",
                    )
            except Exception as exc:
                outcome = StepOutcome(status=StepStatus.FAILED, error=str(exc))

            last_outcome = outcome
            if outcome.status != StepStatus.FAILED:
                return outcome

            if attempt < self.max_attempts and self.initial_backoff > 0:
                backoff = min(
                    self.initial_backoff * (self.backoff_factor ** (attempt - 1)),
                    self.max_backoff,
                )
                if backoff > 0:
                    await asyncio.sleep(backoff)

        assert last_outcome is not None
        return last_outcome
