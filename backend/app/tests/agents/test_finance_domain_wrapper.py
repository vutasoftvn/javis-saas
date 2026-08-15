from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.core.snowflake import generate_snowflake_id
from app.db.base_class import Base
from app.modules.iam.models import User, Workspace, WorkspaceMember
from app.modules.finance.models import AccountingProfile, FinanceManagementSnapshot
from app.agents.governance.models import AgentApproval, AgentEventRecord, AgentToolCall
from app.agents.capabilities.models import CapabilityGrant
from app.agents.control_plane.models import AgentGoal, AgentPlan, AgentPlanStep
from app.agents.control_plane.planner import ControlPlanePlanner
from app.agents.control_plane.execution import ControlPlaneExecutionManager
from app.agents.control_plane.evaluator import PlanEvaluator
from app.agents.domains.finance import (
    FinanceDataCapability,
    FinanceReasoningCapability,
    FinanceResearchCapability,
    FinanceActionCapability,
    FinanceEvaluationCapability,
)


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"


@pytest.fixture
def in_memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [
        User.__table__,
        Workspace.__table__,
        WorkspaceMember.__table__,
        AccountingProfile.__table__,
        FinanceManagementSnapshot.__table__,
        AgentGoal.__table__,
        AgentPlan.__table__,
        AgentPlanStep.__table__,
        AgentApproval.__table__,
        AgentEventRecord.__table__,
        AgentToolCall.__table__,
        CapabilityGrant.__table__,
    ]
    Base.metadata.create_all(bind=engine, tables=tables)
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def finance_setup(in_memory_db: Session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()

    user = User(
        id=user_id,
        email=f"founder_{user_id}@cosa.local",
        password_hash="hash",
        display_name="Finance Founder",
        status="active",
    )
    workspace = Workspace(id=workspace_id, name="Finance Pilot Corp")
    member = WorkspaceMember(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        user_id=user_id,
        role="founder",
    )

    profile = AccountingProfile(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        mode="TT58_MODE_1",
        status="ACTIVE",
    )

    from datetime import date
    snapshot = FinanceManagementSnapshot(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        as_of=date.today(),
        cash=1500000000.0,
        burn=120000000.0,
        runway_months=12.5,
    )

    in_memory_db.add_all([user, workspace, member, profile, snapshot])
    in_memory_db.commit()

    return user, workspace, snapshot


def test_finance_capabilities_standalone(in_memory_db: Session, finance_setup):
    user, workspace, snapshot = finance_setup

    # 1. Data Capability
    data_res = FinanceDataCapability.read_financial_position(db=in_memory_db, workspace_id=workspace.id)
    assert data_res["status"] == "success"
    assert data_res["financial_summary"]["status"] == "success"
    assert data_res["financial_summary"]["cash_balance"] == 1500000000.0

    # 2. Reasoning Capability (Anomalies)
    reasoning_res = FinanceReasoningCapability.detect_anomalies(
        cash_balance=1500000000.0,
        burn_rate=120000000.0,
        runway_months=12.5,
    )
    assert reasoning_res["status"] == "success"
    assert reasoning_res["risk_level"] == "low"

    # 3. Critical Runway check
    crit_res = FinanceReasoningCapability.detect_anomalies(runway_months=4.5)
    assert crit_res["risk_level"] == "critical"
    assert len(crit_res["anomalies"]) >= 1

    # 4. Research Capability (Scenarios)
    scenario_res = FinanceResearchCapability.model_runway_scenarios(target_months=18)
    assert scenario_res["status"] == "success"
    assert len(scenario_res["scenarios"]) == 3

    # 5. Action Capability (TT58 Package)
    action_res = FinanceActionCapability.prepare_accounting_review_package()
    assert action_res["status"] == "success"
    assert action_res["package"]["approval_level"] == "L3A_EXECUTE_WITH_APPROVAL"
    assert action_res["package"]["regulation"] == "TT58"

    # 6. Evaluation Capability
    eval_res = FinanceEvaluationCapability.evaluate_financial_health()
    assert eval_res["status"] == "success"
    assert eval_res["health_status"] == "HEALTHY"


@pytest.mark.asyncio
async def test_finance_goal_execution_plan(in_memory_db: Session, finance_setup):
    user, workspace, snapshot = finance_setup

    # 1. Create Finance Goal
    goal = AgentGoal(
        id=generate_snowflake_id(),
        workspace_id=workspace.id,
        user_id=user.id,
        title="Tối ưu chi phí vận hành và mở rộng runway lên 18 tháng",
        goal_type="business_goal",
        target_metric_jsonb={"metric": "runway_months", "value": 18},
        status="active",
    )
    in_memory_db.add(goal)
    in_memory_db.commit()

    # 2. Control Plane creates Plan for Finance
    plan = ControlPlanePlanner.create_plan_for_goal(
        db=in_memory_db,
        goal=goal,
        domain_hint="finance",
    )
    assert len(plan.steps) >= 3

    # 3. Execute Step 1 (Data: Read financial position)
    res1 = await ControlPlaneExecutionManager.execute_next_pending_step(
        db=in_memory_db,
        plan_id=plan.id,
        user_id=user.id,
        workspace_id=workspace.id,
    )
    assert res1.status == "completed"
    assert "TT58" in str(res1.data)

    # 4. Execute Step 2 (Reasoning: Anomaly & Burn Variance)
    res2 = await ControlPlaneExecutionManager.execute_next_pending_step(
        db=in_memory_db,
        plan_id=plan.id,
        user_id=user.id,
        workspace_id=workspace.id,
    )
    assert res2.status == "completed"

    # 5. Execute Step 3 (Research: Model Runway Scenarios)
    res3 = await ControlPlaneExecutionManager.execute_next_pending_step(
        db=in_memory_db,
        plan_id=plan.id,
        user_id=user.id,
        workspace_id=workspace.id,
    )
    assert res3.status == "completed"
