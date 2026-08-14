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
from app.db.models import WorkspaceMember
from app.modules.finance.models import AccountingProfile, FinanceManagementSnapshot


def _create_mock_db():
    db = MagicMock()
    snapshot = FinanceManagementSnapshot(
        id=generate_snowflake_id(),
        workspace_id=generate_snowflake_id(),
        as_of=date(2026, 8, 1),
        cash=Decimal("1500000000"),
        burn=Decimal("120000000"),
        runway_months=Decimal("12.5"),
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


@pytest.mark.asyncio
async def test_chief_of_staff_orchestration_flow():
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    db = _create_mock_db()

    goal = "Doanh thu quý này đang chậm. Hãy phân tích CRM và tài chính để lập kế hoạch tăng tốc."

    result = await ChiefOfStaffOrchestrator.orchestrate(
        db=db,
        workspace_id=ws_id,
        user_id=user_id,
        goal=goal,
    )

    assert result.status == "completed"
    assert result.workspace_id == str(ws_id)
    assert "sales" in result.specialist_reports
    assert "finance" in result.specialist_reports
    assert len(result.priorities) > 0
    assert len(result.action_plan) == 4
    assert len(result.required_approvals) > 0
    assert result.action_plan[0]["owner"] in ("sales_specialist", "finance_specialist", "chief_of_staff")


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


def test_mission_control_rest_endpoint(client: TestClient):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    member = MagicMock()
    member.workspace_id = ws_id
    member.user_id = user_id

    app.dependency_overrides[get_current_workspace_member] = lambda: member

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
        assert data["status"] == "completed"
        assert len(data["priorities"]) > 0
        assert len(data["action_plan"]) == 4

    finally:
        app.dependency_overrides.pop(get_current_workspace_member, None)
