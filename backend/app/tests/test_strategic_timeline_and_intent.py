from unittest.mock import MagicMock
from app.core.snowflake import generate_snowflake_id
from app.modules.company_runtime.intent_classifier import WorkIntentClassifier
from app.modules.strategy.models import (
    Project,
    TwelveWeekCycle,
    WeeklyPlan,
    WeeklyCommitment,
)
from app.modules.tasks.models import Task
from app.modules.outcomes.models import Outcome
from app.modules.strategy.timeline_service import StrategicTimelineService
from app.modules.strategy.execution_router import (
    create_twelve_week_cycle,
    TwelveWeekCycleCreate,
    get_cycle_timeline,
)
from app.db.models import WorkspaceMember


def test_work_intent_classifier_extracts_duration_weeks():
    # Test 6 weeks extraction
    res1 = WorkIntentClassifier.classify("Lập chu kỳ 6 tuần kiểm chứng PMF cho Dự án Voice Desktop")
    assert res1["intent"] == "CYCLE_CHANGE"
    assert res1["duration_weeks"] == 6
    assert res1["project_hint"] == "Voice Desktop"
    assert "6 tuần" in res1["confirmation_prompt"]

    # Test default 13 weeks
    res2 = WorkIntentClassifier.classify("Lập kế hoạch chiến lược mới cho dự án SaaS Platform")
    assert res2["intent"] in ("CYCLE_CHANGE", "STRATEGIC")
    assert res2["duration_weeks"] == 13
    assert res2["project_hint"] == "SaaS Platform"
    assert "13 tuần" in res2["confirmation_prompt"]

    # Test 4-week sprint
    res3 = WorkIntentClassifier.classify("Replan 4 tuần ra mắt beta")
    assert res3["intent"] == "CYCLE_CHANGE"
    assert res3["duration_weeks"] == 4


def test_strategic_timeline_service_aggregation():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    cycle_id = generate_snowflake_id()
    proj_id = generate_snowflake_id()

    db = MagicMock()

    project = Project(
        id=proj_id,
        workspace_id=ws_id,
        title="Javis Voice Desktop",
        status="active",
    )

    cycle = TwelveWeekCycle(
        id=cycle_id,
        workspace_id=ws_id,
        project_id=proj_id,
        theme="PMF Validation",
        duration_weeks=6,
        status="active",
    )

    plans = []
    for w in range(1, 7):
        p = WeeklyPlan(
            id=generate_snowflake_id(),
            workspace_id=ws_id,
            cycle_id=cycle_id,
            week_no=w,
            focus=f"Focus Week {w}",
            mission=f"Mission Week {w}",
        )
        plans.append(p)

    comm = WeeklyCommitment(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        weekly_plan_id=plans[0].id,
        title="Legal check",
    )

    task = Task(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        weekly_commitment_id=comm.id,
        title="Legal terms review",
        function="LEGAL",
        status="completed",
    )

    outcome = Outcome(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        task_id=task.id,
        function="LEGAL",
        title="Legal signoff",
        status="approved",
    )

    def mock_query(model):
        m = MagicMock()
        if model == TwelveWeekCycle:
            m.filter.return_value.first.return_value = cycle
        elif model == Project:
            m.filter.return_value.first.return_value = project
        elif model == WeeklyPlan:
            m.filter.return_value.order_by.return_value.all.return_value = plans
        elif model == WeeklyCommitment:
            m.filter.return_value.all.return_value = [comm]
        elif model == Task:
            m.filter.return_value.all.return_value = [task]
        elif model == Outcome:
            m.filter.return_value.all.return_value = [outcome]
        return m

    db.query.side_effect = mock_query

    timeline_service = StrategicTimelineService(db, ws_id, user_id)
    timeline_card = timeline_service.get_cycle_timeline(cycle_id)

    assert timeline_card["type"] == "STRATEGIC_TIMELINE_CARD"
    data = timeline_card["data"]
    assert data["cycle_id"] == str(cycle_id)
    assert data["project_id"] == str(proj_id)
    assert data["project_name"] == "Javis Voice Desktop"
    assert data["total_weeks"] == 6
    assert len(data["timeline_steps"]) == 6

    # Week 1 completed
    step1 = data["timeline_steps"][0]
    assert step1["week_no"] == 1
    assert step1["status"] == "completed"
    assert step1["progress_percent"] == 100.0
    assert "LEGAL" in step1["owner_functions"]

    # Week 6 transition
    step6 = data["timeline_steps"][5]
    assert step6["week_no"] == 6
    assert step6["is_transition_week"] is True


def test_create_and_timeline_endpoints():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    member = MagicMock(spec=WorkspaceMember)
    member.user_id = user_id
    member.workspace_id = ws_id
    member.role = "admin"

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    create_data = TwelveWeekCycleCreate(
        theme="8 Week Rapid Growth",
        duration_weeks=8,
    )
    cycle_res = create_twelve_week_cycle(ws_id, create_data, member, db)
    assert cycle_res["theme"] == "8 Week Rapid Growth"
    assert cycle_res["duration_weeks"] == 8
