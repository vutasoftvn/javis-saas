from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from agent_runtime.permissions.models import AgentToolCall
from agent_runtime.sessions.models import AgentRun
from founder_os.outcomes.models import RunStep
from workforce.agents.delegation.models import DelegationJob
from workforce.agents.governance.budget import MissionBudget


_RESERVING_STATES = {
    "queued",
    "waiting_approval",
    "claimed",
    "dispatching",
    "running",
    "retry_scheduled",
    "cancel_requested",
}


class MissionBudgetExceeded(RuntimeError):
    """A shared mission budget cannot accommodate a reservation."""


@dataclass(frozen=True)
class MissionUsage:
    steps: int
    tool_calls: int
    cost_usd: Decimal
    run_ids: tuple[int, ...]


class MissionBudgetService:
    """Aggregate and reserve the root budget across all descendant runs."""

    @classmethod
    def _resolve_tree(
        cls,
        db: Session,
        root: AgentRun,
    ) -> list[AgentRun]:
        runs = [root]
        visited = {root.id}
        frontier = [root.id]
        while frontier:
            children = (
                db.query(AgentRun)
                .filter(AgentRun.parent_run_id.in_(frontier))
                .all()
            )
            frontier = []
            for child in children:
                if child.workspace_id != root.workspace_id:
                    raise MissionBudgetExceeded(
                        f"Run {child.id} crosses workspace boundary in budget tree"
                    )
                if child.id in visited:
                    raise MissionBudgetExceeded(
                        f"Cycle detected in budget tree at run {child.id}"
                    )
                visited.add(child.id)
                runs.append(child)
                frontier.append(child.id)
        return runs

    @classmethod
    def snapshot(
        cls,
        db: Session,
        root_run_id: int,
    ) -> MissionUsage:
        root = db.query(AgentRun).filter(AgentRun.id == root_run_id).first()
        if root is None:
            raise MissionBudgetExceeded(f"Root agent run {root_run_id} does not exist")

        runs = cls._resolve_tree(db, root)
        run_ids = tuple(run.id for run in runs)
        outcome_run_ids = tuple(
            run.outcome_run_id for run in runs if run.outcome_run_id is not None
        )
        steps = 0
        if outcome_run_ids:
            steps = int(
                db.query(func.count(RunStep.id))
                .filter(
                    RunStep.run_id.in_(outcome_run_ids),
                    RunStep.status.in_(("running", "completed")),
                )
                .scalar()
                or 0
            )
        tool_calls = int(
            db.query(func.count(AgentToolCall.id))
            .filter(AgentToolCall.run_id.in_(run_ids))
            .scalar()
            or 0
        )
        cost = sum(
            (Decimal(str(run.estimated_cost or 0)) for run in runs),
            Decimal("0"),
        )
        return MissionUsage(
            steps=steps,
            tool_calls=tool_calls,
            cost_usd=cost,
            run_ids=run_ids,
        )

    @classmethod
    def reserve(
        cls,
        db: Session,
        root_run_id: int,
        job_id: int,
        *,
        steps: int,
        tool_calls: int,
        cost_usd: Decimal | float | str,
        budget: MissionBudget,
    ) -> DelegationJob:
        if steps < 0 or tool_calls < 0 or Decimal(str(cost_usd)) < 0:
            raise ValueError("Mission budget reservations cannot be negative")

        root = (
            db.query(AgentRun)
            .filter(AgentRun.id == root_run_id)
            .with_for_update()
            .first()
        )
        if root is None:
            raise MissionBudgetExceeded(f"Root agent run {root_run_id} does not exist")
        job = (
            db.query(DelegationJob)
            .filter(DelegationJob.id == job_id)
            .with_for_update()
            .first()
        )
        if job is None or job.root_agent_run_id != root_run_id:
            raise MissionBudgetExceeded(
                f"Delegation job {job_id} does not belong to root run {root_run_id}"
            )
        if job.workspace_id != root.workspace_id:
            raise MissionBudgetExceeded(
                f"Delegation job {job_id} crosses workspace boundary"
            )

        usage = cls.snapshot(db, root_run_id)
        reserved = (
            db.query(
                func.coalesce(func.sum(DelegationJob.reserved_steps), 0),
                func.coalesce(func.sum(DelegationJob.reserved_tool_calls), 0),
                func.coalesce(func.sum(DelegationJob.reserved_cost_usd), 0),
            )
            .filter(
                DelegationJob.root_agent_run_id == root_run_id,
                DelegationJob.status.in_(_RESERVING_STATES),
                DelegationJob.id != job_id,
            )
            .one()
        )
        total_steps = usage.steps + int(reserved[0]) + steps
        total_tool_calls = usage.tool_calls + int(reserved[1]) + tool_calls
        total_cost = usage.cost_usd + Decimal(str(reserved[2])) + Decimal(str(cost_usd))

        if total_steps > budget.max_steps:
            raise MissionBudgetExceeded(
                f"Step reservation exceeds root budget ({total_steps} > {budget.max_steps})"
            )
        if total_tool_calls > budget.max_tool_calls:
            raise MissionBudgetExceeded(
                "Tool call reservation exceeds root budget "
                f"({total_tool_calls} > {budget.max_tool_calls})"
            )
        if total_cost > Decimal(str(budget.max_api_cost_usd)):
            raise MissionBudgetExceeded(
                f"API cost reservation exceeds root budget "
                f"({total_cost} > {budget.max_api_cost_usd})"
            )

        job.reserved_steps = steps
        job.reserved_tool_calls = tool_calls
        job.reserved_cost_usd = Decimal(str(cost_usd))
        db.flush()
        return job

    @classmethod
    def release(
        cls,
        db: Session,
        root_run_id: int,
        job_id: int,
    ) -> DelegationJob:
        root = (
            db.query(AgentRun)
            .filter(AgentRun.id == root_run_id)
            .with_for_update()
            .first()
        )
        if root is None:
            raise MissionBudgetExceeded(f"Root agent run {root_run_id} does not exist")
        job = (
            db.query(DelegationJob)
            .filter(
                DelegationJob.id == job_id,
                DelegationJob.root_agent_run_id == root_run_id,
                DelegationJob.workspace_id == root.workspace_id,
            )
            .with_for_update()
            .first()
        )
        if job is None:
            raise MissionBudgetExceeded(
                f"Delegation job {job_id} does not belong to root run {root_run_id}"
            )
        job.reserved_steps = 0
        job.reserved_tool_calls = 0
        job.reserved_cost_usd = Decimal("0")
        db.flush()
        return job

    @classmethod
    def settle(
        cls,
        db: Session,
        root_run_id: int,
        job_id: int,
    ) -> DelegationJob:
        """Release a reservation after durable usage records have been written."""
        return cls.release(db, root_run_id, job_id)
