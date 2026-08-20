from decimal import Decimal
from datetime import datetime, timezone

import pytest

from agent_runtime.permissions.models import AgentToolCall
from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import SessionLocal
from app.founder_os.outcomes.models import Outcome, OutcomeRun, RunStep
from app.platform.auth.models import User, Workspace
from app.workforce.agents.delegation.models import DelegationJob
from app.workforce.agents.governance.budget import MissionBudget


def _budget_tree(db):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db.add(User(id=user_id, email=f"budget-{user_id}@example.invalid"))
    db.add(Workspace(id=workspace_id, name=f"Budget {workspace_id}"))
    db.flush()

    outcome = Outcome(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        function="strategy",
        title="Budget mission",
        desired_result="Stay inside the shared mission budget",
        requested_by=user_id,
        status="planning",
    )
    db.add(outcome)
    db.flush()
    outcome_run = OutcomeRun(
        id=generate_snowflake_id(),
        outcome_id=outcome.id,
        status="running",
        verification_status="UNKNOWN",
    )
    db.add(outcome_run)
    db.flush()
    root = AgentRun(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        company_id=workspace_id,
        user_id=user_id,
        outcome_run_id=outcome_run.id,
        agent_key="chief_of_staff",
        runtime="mock",
        status="running",
    )
    db.add(root)
    db.flush()
    outcome_run.agent_run_id = root.id

    steps = []
    jobs = []
    for attempt in (1, 2):
        step = RunStep(
            id=generate_snowflake_id(),
            run_id=outcome_run.id,
            type="agent",
            status="pending",
        )
        db.add(step)
        db.flush()
        job = DelegationJob(
            id=generate_snowflake_id(),
            workspace_id=workspace_id,
            run_step_id=step.id,
            root_agent_run_id=root.id,
            parent_agent_run_id=root.id,
            attempt_no=1,
            provider_kind="agent_runtime",
            provider_name="in_process",
            profile_id=f"specialist-{attempt}",
            runtime_name="mock",
            status="queued",
            idempotency_key=f"budget:{root.id}:{attempt}",
        )
        db.add(job)
        steps.append(step)
        jobs.append(job)
    db.flush()
    return root, steps, jobs


def test_active_reservations_cannot_exceed_root_budget():
    from app.workforce.agents.delegation.budget import (
        MissionBudgetExceeded,
        MissionBudgetService,
    )

    db = SessionLocal()
    try:
        root, _steps, jobs = _budget_tree(db)
        budget = MissionBudget(max_steps=2, max_tool_calls=2, max_api_cost_usd=1)

        MissionBudgetService.reserve(
            db,
            root.id,
            jobs[0].id,
            steps=1,
            tool_calls=1,
            cost_usd=Decimal("0.6"),
            budget=budget,
        )
        with pytest.raises(MissionBudgetExceeded, match="cost"):
            MissionBudgetService.reserve(
                db,
                root.id,
                jobs[1].id,
                steps=1,
                tool_calls=1,
                cost_usd=Decimal("0.6"),
                budget=budget,
            )

        db.refresh(jobs[1])
        assert jobs[1].reserved_cost_usd == Decimal("0")
    finally:
        db.rollback()
        db.close()


def test_reserve_is_idempotent_for_same_job_and_release_clears_it():
    from app.workforce.agents.delegation.budget import MissionBudgetService

    db = SessionLocal()
    try:
        root, _steps, jobs = _budget_tree(db)
        budget = MissionBudget(max_steps=1, max_tool_calls=1, max_api_cost_usd=1)

        for _ in range(2):
            MissionBudgetService.reserve(
                db,
                root.id,
                jobs[0].id,
                steps=1,
                tool_calls=1,
                cost_usd=Decimal("0.8"),
                budget=budget,
            )
        assert jobs[0].reserved_steps == 1
        assert jobs[0].reserved_tool_calls == 1
        assert jobs[0].reserved_cost_usd == Decimal("0.8")

        MissionBudgetService.release(db, root.id, jobs[0].id)
        assert jobs[0].reserved_steps == 0
        assert jobs[0].reserved_tool_calls == 0
        assert jobs[0].reserved_cost_usd == Decimal("0")
    finally:
        db.rollback()
        db.close()


def test_budget_tracker_check_tree_aggregates_descendant_usage():
    from app.workforce.agents.governance.budget import BudgetTracker

    db = SessionLocal()
    try:
        root, _steps, _jobs = _budget_tree(db)
        root.estimated_cost = 0.1
        child = AgentRun(
            id=generate_snowflake_id(),
            workspace_id=root.workspace_id,
            company_id=root.company_id,
            user_id=root.user_id,
            parent_run_id=root.id,
            agent_key="finance_specialist",
            runtime="mock",
            status="running",
            estimated_cost=0.6,
        )
        db.add(child)
        db.flush()
        db.add(
            AgentToolCall(
                id=generate_snowflake_id(),
                run_id=child.id,
                agent_key=child.agent_key,
                tool_name="finance.read",
                risk_level="R0",
                status="success",
                started_at=datetime.now(timezone.utc),
            )
        )
        db.flush()

        result = BudgetTracker.check_tree(
            db,
            root,
            MissionBudget(
                max_steps=10,
                max_tool_calls=10,
                max_api_cost_usd=0.5,
                max_wall_time_seconds=300,
            ),
        )

        assert result.is_exceeded is True
        assert result.reason_code == "COST_EXCEEDED"
        assert result.current_cost_usd == pytest.approx(0.7)
        assert result.current_tool_calls == 1
    finally:
        db.rollback()
        db.close()


@pytest.mark.asyncio
async def test_tool_bridge_checks_root_budget_before_governance_side_effect():
    from app.workforce.agents.runtime.tool_bridge import dispatch_tool_call
    from app.workforce.agents.runtime.types import AgentRunRequest

    db = SessionLocal()
    try:
        root, _steps, _jobs = _budget_tree(db)
        root.budget_jsonb = MissionBudget(
            max_steps=10,
            max_tool_calls=1,
            max_api_cost_usd=10,
            max_wall_time_seconds=300,
        ).model_dump()
        child = AgentRun(
            id=generate_snowflake_id(),
            workspace_id=root.workspace_id,
            company_id=root.company_id,
            user_id=root.user_id,
            parent_run_id=root.id,
            agent_key="finance_specialist",
            runtime="mock",
            status="running",
            metadata_jsonb={"root_agent_run_id": root.id},
        )
        db.add(child)
        db.flush()
        db.add(
            AgentToolCall(
                id=generate_snowflake_id(),
                run_id=child.id,
                agent_key=child.agent_key,
                tool_name="finance.read",
                risk_level="R0",
                status="success",
                started_at=datetime.now(timezone.utc),
            )
        )
        db.flush()

        result = await dispatch_tool_call(
            db,
            AgentRunRequest(
                company_id=str(root.company_id),
                workspace_id=str(root.workspace_id),
                user_id=str(root.user_id),
                agent_key=child.agent_key,
                task="Attempt another tool call",
                permission_profile="read_only",
                parent_run_id=str(child.id),
            ),
            "missing_tool_must_not_be_resolved",
            {},
            run_id=child.id,
        )

        assert result["status"] == "blocked"
        assert result["error_code"] == "TOOL_CALL_LIMIT_EXCEEDED"
    finally:
        db.rollback()
        db.close()
