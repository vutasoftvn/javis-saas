import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.core.snowflake import generate_snowflake_id
from app.db.base_class import Base
from app.platform.auth.models import User, Workspace, WorkspaceMember
from app.workforce.agents.governance.models import AgentApproval, AgentEventRecord, AgentToolCall
from app.workforce.agents.capabilities.models import CapabilityGrant
from app.workforce.agents.control_plane.models import AgentGoal, AgentPlan, AgentPlanStep, AgentMemoryItem
from app.workforce.agents.control_plane.execution import ControlPlaneExecutionManager


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [
        User.__table__,
        Workspace.__table__,
        WorkspaceMember.__table__,
        AgentGoal.__table__,
        AgentPlan.__table__,
        AgentPlanStep.__table__,
        AgentMemoryItem.__table__,
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
def sample_workspace(db: Session):
    ws = Workspace(
        id=generate_snowflake_id(),
        name="Test Workspace",
    )
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return ws


@pytest.fixture
def sample_user(db: Session):
    user = User(
        id=generate_snowflake_id(),
        email="test@example.com",
        display_name="Test User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_execution_retry_on_transient_error_and_succeed(db: Session, sample_workspace, sample_user):
    ws_id = sample_workspace.id
    u_id = sample_user.id

    goal = AgentGoal(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        user_id=u_id,
        title="Retry Success Test Goal",
    )
    plan = AgentPlan(
        id=generate_snowflake_id(),
        goal_id=goal.id,
        workspace_id=ws_id,
        user_id=u_id,
        title="Retry Test Plan",
    )
    step = AgentPlanStep(
        id=generate_snowflake_id(),
        plan_id=plan.id,
        sequence_order=1,
        title="Score prospects with retry",
        domain="sales",
        capability="reasoning",
        policy_level="L2_DRAFT",
        max_retries=3,
        input_jsonb={"prospects": [{"name": "Test Company", "title": "CTO"}]},
    )
    db.add_all([goal, plan, step])
    db.commit()

    call_count = 0

    def mock_score_prospects(prospects):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("503 Service Unavailable: transient network glitch")
        return {"summary": "Scored successfully on retry", "prospects": prospects}

    with patch("app.workforce.agents.domains.sales.SalesReasoningCapability.score_prospects", side_effect=mock_score_prospects):
        res = await ControlPlaneExecutionManager.execute_step(
            db=db,
            plan_id=plan.id,
            step_id=step.id,
            user_id=u_id,
            workspace_id=ws_id,
            retry_delays=[0.001, 0.001],
        )

        assert res.success is True
        assert res.status == "completed"
        assert call_count == 2
        assert step.retry_count == 1

        # Check recorded events
        events = db.query(AgentEventRecord).filter(AgentEventRecord.plan_id == plan.id).all()
        event_types = [e.event_type for e in events]
        assert "step_retrying" in event_types
        assert "step_completed" in event_types


@pytest.mark.asyncio
async def test_execution_non_transient_error_aborts_immediately(db: Session, sample_workspace, sample_user):
    ws_id = sample_workspace.id
    u_id = sample_user.id

    goal = AgentGoal(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        user_id=u_id,
        title="Non-transient Error Goal",
    )
    plan = AgentPlan(
        id=generate_snowflake_id(),
        goal_id=goal.id,
        workspace_id=ws_id,
        user_id=u_id,
        title="Non-transient Plan",
    )
    step = AgentPlanStep(
        id=generate_snowflake_id(),
        plan_id=plan.id,
        sequence_order=1,
        title="Fail without retry",
        domain="sales",
        capability="reasoning",
        policy_level="L2_DRAFT",
        max_retries=3,
        input_jsonb={},
    )
    db.add_all([goal, plan, step])
    db.commit()

    call_count = 0

    def mock_fail(prospects):
        nonlocal call_count
        call_count += 1
        raise ValueError("403 Forbidden: Invalid credentials provided")

    with patch("app.workforce.agents.domains.sales.SalesReasoningCapability.score_prospects", side_effect=mock_fail):
        res = await ControlPlaneExecutionManager.execute_step(
            db=db,
            plan_id=plan.id,
            step_id=step.id,
            user_id=u_id,
            workspace_id=ws_id,
            retry_delays=[0.001],
        )

        assert res.success is False
        assert res.status == "failed_final"
        assert call_count == 1  # Did NOT retry
        assert step.retry_count == 0


@pytest.mark.asyncio
async def test_execution_exhausted_retries_uses_fallback(db: Session, sample_workspace, sample_user):
    ws_id = sample_workspace.id
    u_id = sample_user.id

    goal = AgentGoal(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        user_id=u_id,
        title="Fallback Goal",
    )
    plan = AgentPlan(
        id=generate_snowflake_id(),
        goal_id=goal.id,
        workspace_id=ws_id,
        user_id=u_id,
        title="Fallback Plan",
    )
    step = AgentPlanStep(
        id=generate_snowflake_id(),
        plan_id=plan.id,
        sequence_order=1,
        title="Retry then fallback",
        domain="sales",
        capability="reasoning",
        policy_level="L2_DRAFT",
        max_retries=2,
        input_jsonb={"fallback_handler": "rule_based_scorer"},
    )
    db.add_all([goal, plan, step])
    db.commit()

    with patch("app.workforce.agents.domains.sales.SalesReasoningCapability.score_prospects", side_effect=TimeoutError("504 Gateway Timeout")):
        res = await ControlPlaneExecutionManager.execute_step(
            db=db,
            plan_id=plan.id,
            step_id=step.id,
            user_id=u_id,
            workspace_id=ws_id,
            retry_delays=[0.001, 0.001],
        )

        assert res.success is True
        assert res.status == "completed"
        assert step.fallback_used is True

        events = db.query(AgentEventRecord).filter(AgentEventRecord.plan_id == plan.id).all()
        event_types = [e.event_type for e in events]
        assert "step_fallback" in event_types
