from app.core.snowflake import generate_snowflake_id
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from app.modules.strategy.models import (
    TwelveWeekCycle,
    WeeklyPlan,
    WeeklyCommitment,
    Milestone,
    Project,
)
from app.modules.tasks.models import Task
from app.modules.outcomes.models import Outcome
from app.modules.strategy.planning_compiler_service import PlanningCompilerService


def test_compile_cycle_blocks_when_inactive():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()

    db = MagicMock()
    # Cycle in draft status
    cycle = TwelveWeekCycle(id=cycle_id, workspace_id=ws_id, theme="Draft Cycle", status="draft")
    db.query.return_value.filter.return_value.first.return_value = cycle

    service = PlanningCompilerService(db, ws_id, user_id)
    with pytest.raises(HTTPException) as exc:
        service.compile_cycle(cycle_id)
    assert exc.value.status_code == 422
    assert "active" in exc.value.detail


def test_compile_cycle_success_creates_tasks_and_outcomes():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()
    plan_id = generate_snowflake_id()
    proj_id = generate_snowflake_id()

    db = MagicMock()
    cycle = TwelveWeekCycle(id=cycle_id, workspace_id=ws_id, theme="Active Cycle", status="active")
    plan = WeeklyPlan(id=plan_id, workspace_id=ws_id, cycle_id=cycle_id, week_no=1, focus="Week 1 MVP")

    c1 = WeeklyCommitment(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        weekly_plan_id=plan_id,
        title="Review Legal Terms with Founder",
        commitment_owner_type="FOUNDER",
        execution_mode="MANUAL",
    )
    c2 = WeeklyCommitment(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        weekly_plan_id=plan_id,
        title="Automated Data Pipeline Crawler",
        commitment_owner_type="AI_AGENT",
        execution_mode="AUTONOMOUS",
    )

    ms = Milestone(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        cycle_id=cycle_id,
        project_id=proj_id,
        name="Alpha Release",
        required_artifacts={"artifacts": ["Landing Page HTML", "Backend API"]},
        acceptance_criteria="Passes 100% tests",
    )

    def query_mock(model):
        m = MagicMock()
        if model == TwelveWeekCycle:
            m.filter.return_value.first.return_value = cycle
        elif model == WeeklyPlan:
            m.filter.return_value.all.return_value = [plan]
        elif model == WeeklyCommitment:
            m.filter.return_value.all.return_value = [c1, c2]
        elif model == Milestone:
            m.filter.return_value.all.return_value = [ms]
        elif model in (Task, Outcome):
            # No existing tasks/outcomes on first compile
            m.filter.return_value.first.return_value = None
        else:
            m.filter.return_value.first.return_value = None
            m.filter.return_value.all.return_value = []
        return m

    db.query.side_effect = query_mock

    service = PlanningCompilerService(db, ws_id, user_id)
    res = service.compile_cycle(cycle_id)

    assert res["status"] == "compiled"
    assert res["tasks_created"] == 2
    assert res["outcomes_created"] == 2
    assert db.commit.called
    assert db.add.call_count == 4  # 2 tasks + 2 outcomes


def test_compile_cycle_idempotent():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()
    plan_id = generate_snowflake_id()

    db = MagicMock()
    cycle = TwelveWeekCycle(id=cycle_id, workspace_id=ws_id, theme="Active Cycle", status="active")
    plan = WeeklyPlan(id=plan_id, workspace_id=ws_id, cycle_id=cycle_id, week_no=1, focus="Week 1 MVP")

    c1 = WeeklyCommitment(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        weekly_plan_id=plan_id,
        title="Existing Task Commitment",
    )

    existing_task = Task(id=generate_snowflake_id(), workspace_id=ws_id, title="Existing Task Commitment", weekly_commitment_id=c1.id)

    def query_mock(model):
        m = MagicMock()
        if model == TwelveWeekCycle:
            m.filter.return_value.first.return_value = cycle
        elif model == WeeklyPlan:
            m.filter.return_value.all.return_value = [plan]
        elif model == WeeklyCommitment:
            m.filter.return_value.all.return_value = [c1]
        elif model == Milestone:
            m.filter.return_value.all.return_value = []
        elif model == Task:
            m.filter.return_value.first.return_value = existing_task
        else:
            m.filter.return_value.first.return_value = None
            m.filter.return_value.all.return_value = []
        return m

    db.query.side_effect = query_mock

    service = PlanningCompilerService(db, ws_id, user_id)
    res = service.compile_cycle(cycle_id)

    assert res["tasks_created"] == 0
    assert res["tasks_existing"] == 1


def test_compile_weekly_plan():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()
    plan_id = generate_snowflake_id()

    db = MagicMock()
    cycle = TwelveWeekCycle(id=cycle_id, workspace_id=ws_id, theme="Active Cycle", status="active")
    plan = WeeklyPlan(id=plan_id, workspace_id=ws_id, cycle_id=cycle_id, week_no=2, focus="Week 2 Focus")

    c1 = WeeklyCommitment(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        weekly_plan_id=plan_id,
        title="Weekly Commitment Item",
        execution_mode="AI_ASSISTED",
    )

    def query_mock(model):
        m = MagicMock()
        if model == WeeklyPlan:
            m.filter.return_value.first.return_value = plan
        elif model == TwelveWeekCycle:
            m.filter.return_value.first.return_value = cycle
        elif model == WeeklyCommitment:
            m.filter.return_value.all.return_value = [c1]
        elif model == Task:
            m.filter.return_value.first.return_value = None
        else:
            m.filter.return_value.first.return_value = None
        return m

    db.query.side_effect = query_mock

    service = PlanningCompilerService(db, ws_id, user_id)
    res = service.compile_weekly_plan(plan_id)

    assert res["plan_id"] == str(plan_id)
    assert res["tasks_created"] == 1
    assert db.commit.called


def test_get_compilation_status():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()

    db = MagicMock()
    cycle = TwelveWeekCycle(id=cycle_id, workspace_id=ws_id, theme="Active Cycle", status="active")

    def query_mock(model):
        m = MagicMock()
        if model == TwelveWeekCycle:
            m.filter.return_value.first.return_value = cycle
        elif model == WeeklyPlan:
            m.filter.return_value.all.return_value = [MagicMock(id=generate_snowflake_id())]
        elif model == WeeklyCommitment:
            m.filter.return_value.all.return_value = [MagicMock(id=generate_snowflake_id()), MagicMock(id=generate_snowflake_id())]
        elif model == Task:
            m.filter.return_value.count.return_value = 1
        elif model == Milestone:
            m.filter.return_value.count.return_value = 3
        return m

    db.query.side_effect = query_mock

    service = PlanningCompilerService(db, ws_id, user_id)
    status_res = service.get_compilation_status(cycle_id)

    assert status_res["is_active"] is True
    assert status_res["total_commitments"] == 2
    assert status_res["compiled_tasks_count"] == 1
    assert status_res["uncompiled_commitments_count"] == 1
    assert status_res["total_milestones"] == 3
