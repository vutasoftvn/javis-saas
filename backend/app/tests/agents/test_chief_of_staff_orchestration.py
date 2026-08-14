import asyncio
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import get_current_workspace_member
from app.core.snowflake import generate_snowflake_id
from app.agents.orchestration.chief_of_staff import ChiefOfStaffOrchestrator
from app.agents.orchestration.mission_control_bus import mission_control_bus
from app.agents.runtime.adapters.mock import MockRuntime
from app.modules.finance.models import AccountingProfile, FinanceManagementSnapshot


def _create_mock_db(runway_months=Decimal("12.5")):
    db = MagicMock()
    snapshot = FinanceManagementSnapshot(
        id=generate_snowflake_id(),
        workspace_id=generate_snowflake_id(),
        as_of=date(2026, 8, 1),
        cash=Decimal("1500000000"),
        burn=Decimal("120000000"),
        runway_months=runway_months,
        revenue=Decimal("200000000"),
        expenses=Decimal("120000000"),
        budget_variance=Decimal("10000000"),
    )
    profile = AccountingProfile(
        id=generate_snowflake_id(),
        workspace_id=generate_snowflake_id(),
        mode="TT58_MODE_1",
        status="CONFIRMED",
    )

    def query_mock(*entities, **kwargs):
        model = entities[0] if entities else None
        m = MagicMock()
        m.filter.return_value = m
        m.order_by.return_value = m
        m.scalar.return_value = 0
        m.all.return_value = []
        m.limit.return_value.all.return_value = []
        if model is FinanceManagementSnapshot:
            m.first.return_value = snapshot
        elif model is AccountingProfile:
            m.first.return_value = profile
        else:
            m.first.return_value = None
        return m

    db.query.side_effect = query_mock
    return db


def _mock_funnel_metrics(monkeypatch, qualified_leads: int, total_leads: int):
    metrics = {
        "total_leads": total_leads,
        "qualified_leads": qualified_leads,
        "converted_leads": 1,
        "total_opportunities": 4,
        "won_opportunities": 1,
        "pipeline_value": 45000000.0,
    }
    monkeypatch.setattr(
        "app.modules.sales.sales_tools.FunnelMetricsService.get_funnel_metrics",
        lambda db, workspace_id: metrics,
    )
    return metrics


@pytest.mark.asyncio
async def test_chief_of_staff_orchestration_flow(monkeypatch):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = _create_mock_db()
    _mock_funnel_metrics(monkeypatch, qualified_leads=3, total_leads=5)

    goal = "Doanh thu quý này đang chậm. Hãy phân tích CRM và tài chính để lập kế hoạch tăng tốc."

    result = await ChiefOfStaffOrchestrator.orchestrate(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        goal=goal,
        runtime=MockRuntime(),
    )

    # MockRuntime cannot produce valid structured JSON, so the honest outcome is "partial" with
    # the raw synthesis text - not a polished "completed" plan invented client-side. That is the
    # point of this fix: no more hardcoded fake reasoning presented as if an LLM produced it.
    assert result.status == "partial"
    assert goal in result.diagnosis
    assert result.workspace_id == str(ws_id)
    assert "sales" in result.specialist_reports
    assert "finance" in result.specialist_reports
    assert len(result.priorities) > 0

    # priorities/action_plan are derived from the real (mocked) data, not invented: qualified
    # leads > 0 is the only condition that fires here (runway 12.5mo is above the 6mo trigger).
    assert len(result.action_plan) == 1
    assert result.action_plan[0]["automation_key"] == "sales.followup_email"

    # A real AgentApproval row must exist for the automation-bound action.
    assert len(result.required_approvals) == 1
    assert result.required_approvals[0]["tool_name"] == "sales.followup_email"
    assert result.required_approvals[0]["status"] == "pending"


@pytest.mark.asyncio
async def test_chief_of_staff_diagnosis_depends_on_goal(monkeypatch):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    _mock_funnel_metrics(monkeypatch, qualified_leads=0, total_leads=0)

    result_a = await ChiefOfStaffOrchestrator.orchestrate(
        db=_create_mock_db(),
        workspace_id=ws_id,
        user_id=user_id,
        goal="Tại sao doanh thu giảm trong tháng này?",
        runtime=MockRuntime(),
    )
    result_b = await ChiefOfStaffOrchestrator.orchestrate(
        db=_create_mock_db(),
        workspace_id=ws_id,
        user_id=user_id,
        goal="Kế hoạch marketing quý tới nên ưu tiên gì?",
        runtime=MockRuntime(),
    )

    # Regression guard for the original bug: diagnosis used to be identical hardcoded text
    # regardless of what the Founder actually asked.
    assert result_a.diagnosis != result_b.diagnosis
    assert "doanh thu giảm" in result_a.diagnosis
    assert "marketing" in result_b.diagnosis


@pytest.mark.asyncio
async def test_chief_of_staff_low_runway_creates_finance_action_without_automation_approval(monkeypatch):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = _create_mock_db(runway_months=Decimal("3.0"))
    _mock_funnel_metrics(monkeypatch, qualified_leads=0, total_leads=0)

    result = await ChiefOfStaffOrchestrator.orchestrate(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        goal="Tình hình tài chính công ty hiện tại thế nào?",
        runtime=MockRuntime(),
    )

    assert any(a["owner"] == "finance_specialist" for a in result.action_plan)
    # The finance review action has no automation_key (it is an internal review, not an
    # external dispatch), so it must not create an automation approval.
    assert len(result.required_approvals) == 0


@pytest.mark.asyncio
async def test_chief_of_staff_runtime_failure_degrades_without_crashing(monkeypatch):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    _mock_funnel_metrics(monkeypatch, qualified_leads=0, total_leads=0)

    crashing_runtime = MockRuntime()
    crashing_runtime.set_healthy(False)

    result = await ChiefOfStaffOrchestrator.orchestrate(
        db=_create_mock_db(),
        workspace_id=ws_id,
        user_id=user_id,
        goal="Phân tích tổng quan công ty",
        runtime=crashing_runtime,
    )

    assert result.status == "failed"
    assert "unavailable" in result.diagnosis.lower()


@pytest.mark.asyncio
async def test_mission_control_bus_subscription():
    run_id = "test_run_123"
    ws_id = "test_ws_456"

    async def emit_events():
        await asyncio.sleep(0.01)
        mission_control_bus.emit_event(run_id, ws_id, "mission_started", {"goal": "Test goal"})
        await asyncio.sleep(0.01)
        mission_control_bus.emit_event(run_id, ws_id, "mission_completed", {"status": "completed"})

    asyncio.create_task(emit_events())

    received = []
    async for event in mission_control_bus.subscribe(run_id):
        received.append(event)

    assert len(received) == 2
    assert received[0]["event_type"] == "mission_started"
    assert received[1]["event_type"] == "mission_completed"


def test_mission_control_rest_endpoint(client: TestClient, monkeypatch):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    member = MagicMock()
    member.workspace_id = ws_id
    member.user_id = user_id

    app.dependency_overrides[get_current_workspace_member] = lambda: member
    _mock_funnel_metrics(monkeypatch, qualified_leads=3, total_leads=5)

    try:
        from app.db.session import get_db
        mock_db = _create_mock_db()
        app.dependency_overrides[get_db] = lambda: mock_db

        payload = {
            "goal": "Phân tích tăng trưởng doanh số và đề xuất kế hoạch 4 tuần",
        }
        res = client.post("/api/v1/agents/mission-control/orchestrate", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "partial"
        assert len(data["priorities"]) > 0
        assert len(data["action_plan"]) == 1

    finally:
        app.dependency_overrides.pop(get_current_workspace_member, None)
