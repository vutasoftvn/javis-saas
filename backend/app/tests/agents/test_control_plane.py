import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.db.base_class import Base
from app.db.session import get_db
from app.core.auth import get_current_workspace_member
from app.core.snowflake import generate_snowflake_id
from app.modules.iam.models import User, Workspace, WorkspaceMember
from app.modules.sales.models import SalesLead, SalesOpportunity, SalesActivity
from app.agents.governance.models import AgentApproval, AgentEventRecord, AgentRun, AgentToolCall
from app.agents.capabilities.models import CapabilityGrant
from app.agents.control_plane.models import AgentGoal, AgentPlan, AgentPlanStep, AgentMemoryItem
from app.agents.control_plane.context import ContextResolver
from app.agents.control_plane.planner import ControlPlanePlanner
from app.agents.control_plane.execution import ControlPlaneExecutionManager
from app.agents.control_plane.evaluator import PlanEvaluator


# Enable JSONB type rendering in SQLite test database
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
    # Only create the control plane, sales, and governance tables needed for these tests
    tables = [
        User.__table__,
        Workspace.__table__,
        WorkspaceMember.__table__,
        SalesLead.__table__,
        SalesOpportunity.__table__,
        SalesActivity.__table__,
        AgentGoal.__table__,
        AgentPlan.__table__,
        AgentPlanStep.__table__,
        AgentMemoryItem.__table__,
        AgentApproval.__table__,
        AgentRun.__table__,
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
def test_setup(in_memory_db: Session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()

    user = User(
        id=user_id,
        email=f"founder_{user_id}@cosa.local",
        password_hash="test_hash",
        display_name="Founder",
        status="active",
    )
    in_memory_db.add(user)

    workspace = Workspace(
        id=workspace_id,
        name=f"COSA OS Workspace {workspace_id}",
    )
    in_memory_db.add(workspace)

    member = WorkspaceMember(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        user_id=user_id,
        role="founder",
    )
    in_memory_db.add(member)
    in_memory_db.commit()

    return user, workspace


def test_context_resolver(in_memory_db: Session, test_setup):
    user, workspace = test_setup

    goal = AgentGoal(
        id=generate_snowflake_id(),
        workspace_id=workspace.id,
        user_id=user.id,
        title="Increase Pipeline Q1",
        description="Target 500M VND",
        status="active",
    )
    in_memory_db.add(goal)
    in_memory_db.commit()

    ctx = ContextResolver.resolve(
        db=in_memory_db,
        workspace_id=workspace.id,
        user_id=user.id,
        goal_id=goal.id,
    )

    assert ctx.workspace_id == str(workspace.id)
    assert ctx.user["id"] == str(user.id)
    assert ctx.goal["id"] == str(goal.id)
    assert ctx.goal["title"] == "Increase Pipeline Q1"
    assert ctx.cycle["goal_id"] == str(goal.id)
    assert "time_context" in ctx.model_dump()
    assert "permissions" in ctx.model_dump()
    assert "L3A_EXECUTE_WITH_APPROVAL" in ctx.permissions


def test_goal_decomposition_and_planning(in_memory_db: Session, test_setup):
    user, workspace = test_setup

    goal_id = generate_snowflake_id()
    goal = AgentGoal(
        id=goal_id,
        workspace_id=workspace.id,
        user_id=user.id,
        title="Tăng pipeline sales lên 500 triệu",
        goal_type="business_goal",
        target_metric_jsonb={"metric": "pipeline_value", "value": 500000000},
        status="active",
    )
    in_memory_db.add(goal)
    in_memory_db.commit()

    plan = ControlPlanePlanner.create_plan_for_goal(
        db=in_memory_db,
        goal=goal,
        domain_hint="sales",
    )

    assert plan.goal_id == goal.id
    assert len(plan.steps) >= 6
    assert plan.status == "draft"

    # Verify policy levels assigned to steps
    step_policies = [s.policy_level for s in plan.steps]
    assert "L0_READ" in step_policies
    assert "L1_SUGGEST" in step_policies
    assert "L2_DRAFT" in step_policies
    assert "L3A_EXECUTE_WITH_APPROVAL" in step_policies


@pytest.mark.asyncio
async def test_policy_gate_l3a_approval_requirement(in_memory_db: Session, test_setup):
    user, workspace = test_setup

    goal = AgentGoal(
        id=generate_snowflake_id(),
        workspace_id=workspace.id,
        user_id=user.id,
        title="Test Sales Campaign Execution",
        status="active",
    )
    in_memory_db.add(goal)
    in_memory_db.commit()

    plan = ControlPlanePlanner.create_plan_for_goal(
        db=in_memory_db,
        goal=goal,
        domain_hint="sales",
    )

    # Step 1: L0_READ - should complete automatically
    step1 = plan.steps[0]
    res1 = await ControlPlaneExecutionManager.execute_step(
        db=in_memory_db,
        plan_id=plan.id,
        step_id=step1.id,
        user_id=user.id,
        workspace_id=workspace.id,
    )
    assert res1.status == "completed"
    assert step1.status == "completed"

    # Find L3A step (Step 5)
    l3a_step = next(s for s in plan.steps if s.policy_level == "L3A_EXECUTE_WITH_APPROVAL")
    res_l3a = await ControlPlaneExecutionManager.execute_step(
        db=in_memory_db,
        plan_id=plan.id,
        step_id=l3a_step.id,
        user_id=user.id,
        workspace_id=workspace.id,
    )
    assert res_l3a.status == "waiting_approval"
    assert l3a_step.status == "waiting_approval"
    assert l3a_step.approval_id is not None

    # Simulate Founder Approval
    approval = in_memory_db.query(AgentApproval).filter(AgentApproval.id == l3a_step.approval_id).first()
    assert approval is not None
    approval.status = "approved"
    approval.reviewed_by = user.id
    approval.reviewed_at = datetime.now(timezone.utc)
    in_memory_db.commit()

    # Re-execute step after approval -> should succeed and complete
    res_approved = await ControlPlaneExecutionManager.execute_step(
        db=in_memory_db,
        plan_id=plan.id,
        step_id=l3a_step.id,
        user_id=user.id,
        workspace_id=workspace.id,
    )
    assert res_approved.status == "completed"
    assert l3a_step.status == "completed"


def test_control_plane_rest_endpoints(client: TestClient, in_memory_db: Session, test_setup):
    user, workspace = test_setup

    member = WorkspaceMember(
        id=generate_snowflake_id(),
        workspace_id=workspace.id,
        user_id=user.id,
        role="founder",
    )
    app.dependency_overrides[get_current_workspace_member] = lambda: member
    app.dependency_overrides[get_db] = lambda: in_memory_db

    try:
        # 1. Create Goal with Auto-Plan
        resp = client.post(
            "/api/v1/agent/goals",
            json={
                "title": "Tăng trưởng doanh thu quý 3",
                "goal_type": "business_goal",
                "target_metric": {"metric": "revenue", "value": 1000000000},
                "auto_plan": True,
                "domain_hint": "sales",
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["title"] == "Tăng trưởng doanh thu quý 3"
        assert data["active_plan_id"] is not None
        plan_id = data["active_plan_id"]

        # 2. Get Plan details
        plan_resp = client.get(f"/api/v1/agent/plans/{plan_id}")
        assert plan_resp.status_code == 200
        plan_data = plan_resp.json()
        assert len(plan_data["steps"]) >= 6
        assert plan_data["evaluation"]["overall_status"] in ("draft", "in_progress")

        # 3. Create Business Memory
        mem_resp = client.post(
            "/api/v1/agent/memories",
            json={
                "memory_type": "founder_preference",
                "domain": "sales",
                "key": "preferred_outreach_channel",
                "value": {"channel": "email_and_zalo", "tone": "formal"},
            },
        )
        assert mem_resp.status_code == 200
        mem_data = mem_resp.json()
        assert mem_data["key"] == "preferred_outreach_channel"

        # 5. List Business Memories
        list_resp = client.get("/api/v1/agent/memories?domain=sales")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert len(list_data) >= 1

        # 6. List Agent Runs
        runs_resp = client.get("/api/v1/agent/runs")
        assert runs_resp.status_code == 200
        runs_data = runs_resp.json()
        assert "items" in runs_data

        # 7. Get Plan Events
        events_resp = client.get(f"/api/v1/agent/plans/{plan_id}/events")
        assert events_resp.status_code == 200
        assert isinstance(events_resp.json(), list)
    finally:
        app.dependency_overrides.pop(get_current_workspace_member, None)
        app.dependency_overrides.pop(get_db, None)
