"""Mission Budget Enforcement for COSA OS (§P0.6, C1/C2 Spec).

Prevents unbounded agent loops, runaway API costs, and hanging execution runs.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cosa_core.governance.models import AgentRun, AgentToolCall

logger = logging.getLogger(__name__)


class MissionBudget(BaseModel):
    """Budget constraints for an agent execution run."""
    max_steps: int = Field(default=15, description="Maximum planning and synthesis steps")
    max_wall_time_seconds: float = Field(default=300.0, description="Maximum execution timeout in seconds")
    max_api_cost_usd: float = Field(default=1.00, description="Maximum model/API spend in USD")
    max_tool_calls: int = Field(default=20, description="Maximum allowed tool invocations")


class BudgetCheckResult(BaseModel):
    is_exceeded: bool
    reason_code: Optional[str] = None  # STEP_LIMIT_EXCEEDED, TIMEOUT_EXCEEDED, COST_EXCEEDED, TOOL_CALL_LIMIT_EXCEEDED
    message: str = "Budget within limits"
    current_steps: int = 0
    current_wall_time_seconds: float = 0.0
    current_cost_usd: float = 0.0
    current_tool_calls: int = 0


class BudgetTracker:
    """Tracks and enforces budget limits for AgentRun instances."""

    @classmethod
    def check(
        cls,
        db: Session,
        agent_run: AgentRun,
        budget: Optional[MissionBudget] = None,
        current_step: int = 0,
    ) -> BudgetCheckResult:
        """Evaluate if the run has exceeded any of its budget thresholds."""
        active_budget = budget
        if active_budget is None and agent_run.budget_jsonb:
            try:
                active_budget = MissionBudget.model_validate(agent_run.budget_jsonb)
            except Exception:
                active_budget = MissionBudget()
        elif active_budget is None:
            active_budget = MissionBudget()

        now = datetime.now(timezone.utc)
        start_time = agent_run.started_at
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        wall_time_s = (now - start_time).total_seconds()

        # Count tool calls
        raw_tool_count = db.execute(
            select(func.count(AgentToolCall.id)).where(AgentToolCall.run_id == agent_run.id)
        ).scalar()
        try:
            tool_call_count = int(raw_tool_count) if raw_tool_count is not None else 0
        except (TypeError, ValueError):
            tool_call_count = 0

        # Current estimated cost
        raw_cost = agent_run.estimated_cost
        try:
            cost_usd = float(raw_cost) if raw_cost is not None else 0.0
        except (TypeError, ValueError):
            cost_usd = 0.0

        # 1. Step limit
        if current_step > active_budget.max_steps:
            return BudgetCheckResult(
                is_exceeded=True,
                reason_code="STEP_LIMIT_EXCEEDED",
                message=f"Step limit of {active_budget.max_steps} exceeded (current: {current_step})",
                current_steps=current_step,
                current_wall_time_seconds=wall_time_s,
                current_cost_usd=cost_usd,
                current_tool_calls=tool_call_count,
            )

        # 2. Tool call limit
        if tool_call_count >= active_budget.max_tool_calls:
            return BudgetCheckResult(
                is_exceeded=True,
                reason_code="TOOL_CALL_LIMIT_EXCEEDED",
                message=f"Tool call limit of {active_budget.max_tool_calls} reached (current: {tool_call_count})",
                current_steps=current_step,
                current_wall_time_seconds=wall_time_s,
                current_cost_usd=cost_usd,
                current_tool_calls=tool_call_count,
            )

        # 3. Wall time limit
        if wall_time_s > active_budget.max_wall_time_seconds:
            return BudgetCheckResult(
                is_exceeded=True,
                reason_code="TIMEOUT_EXCEEDED",
                message=f"Execution timeout of {active_budget.max_wall_time_seconds}s exceeded ({wall_time_s:.1f}s)",
                current_steps=current_step,
                current_wall_time_seconds=wall_time_s,
                current_cost_usd=cost_usd,
                current_tool_calls=tool_call_count,
            )

        # 4. API Cost limit
        if cost_usd > active_budget.max_api_cost_usd:
            return BudgetCheckResult(
                is_exceeded=True,
                reason_code="COST_EXCEEDED",
                message=f"API cost limit of ${active_budget.max_api_cost_usd:.2f} exceeded (${cost_usd:.2f})",
                current_steps=current_step,
                current_wall_time_seconds=wall_time_s,
                current_cost_usd=cost_usd,
                current_tool_calls=tool_call_count,
            )

        return BudgetCheckResult(
            is_exceeded=False,
            current_steps=current_step,
            current_wall_time_seconds=wall_time_s,
            current_cost_usd=cost_usd,
            current_tool_calls=tool_call_count,
        )

    @classmethod
    def check_tree(
        cls,
        db: Session,
        root_run: AgentRun,
        budget: Optional[MissionBudget] = None,
        current_step: int = 0,
    ) -> BudgetCheckResult:
        """Evaluate committed usage across a root run and all descendants."""
        # COSA-CORE-BOUNDARY-EXCEPTION: workforce.agents.delegation.budget (Batch 2)
        # Lazy import to avoid circular dependency — workforce.agents.delegation not yet
        # extracted to cosa_core (scheduled for Batch 2). See docs/architecture/2026-08-22-cosa-core-extraction-plan.md
        from workforce.agents.delegation.budget import MissionBudgetService

        active_budget = budget
        if active_budget is None and root_run.budget_jsonb:
            try:
                active_budget = MissionBudget.model_validate(root_run.budget_jsonb)
            except Exception:
                active_budget = MissionBudget()
        elif active_budget is None:
            active_budget = MissionBudget()

        usage = MissionBudgetService.snapshot(db, root_run.id)
        step_count = max(usage.steps, current_step)
        start_time = root_run.started_at
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        wall_time_s = (datetime.now(timezone.utc) - start_time).total_seconds()
        cost_usd = float(usage.cost_usd)

        values = {
            "current_steps": step_count,
            "current_wall_time_seconds": wall_time_s,
            "current_cost_usd": cost_usd,
            "current_tool_calls": usage.tool_calls,
        }
        if step_count > active_budget.max_steps:
            return BudgetCheckResult(
                is_exceeded=True,
                reason_code="STEP_LIMIT_EXCEEDED",
                message=(
                    f"Shared step limit of {active_budget.max_steps} exceeded "
                    f"(current: {step_count})"
                ),
                **values,
            )
        if usage.tool_calls >= active_budget.max_tool_calls:
            return BudgetCheckResult(
                is_exceeded=True,
                reason_code="TOOL_CALL_LIMIT_EXCEEDED",
                message=(
                    f"Shared tool call limit of {active_budget.max_tool_calls} reached "
                    f"(current: {usage.tool_calls})"
                ),
                **values,
            )
        if wall_time_s > active_budget.max_wall_time_seconds:
            return BudgetCheckResult(
                is_exceeded=True,
                reason_code="TIMEOUT_EXCEEDED",
                message=(
                    f"Shared execution timeout of {active_budget.max_wall_time_seconds}s "
                    f"exceeded ({wall_time_s:.1f}s)"
                ),
                **values,
            )
        if cost_usd > active_budget.max_api_cost_usd:
            return BudgetCheckResult(
                is_exceeded=True,
                reason_code="COST_EXCEEDED",
                message=(
                    f"Shared API cost limit of ${active_budget.max_api_cost_usd:.2f} "
                    f"exceeded (${cost_usd:.2f})"
                ),
                **values,
            )
        return BudgetCheckResult(is_exceeded=False, **values)
