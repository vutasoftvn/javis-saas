import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.core.snowflake import generate_snowflake_id
from app.db.base_class import Base
from app.platform.auth.models import User, Workspace, WorkspaceMember
from app.business.sales.models import SalesLead, SalesActivity, SalesOpportunity
from app.workforce.agents.governance.models import AgentApproval, AgentEventRecord, AgentToolCall
from app.workforce.agents.capabilities.models import CapabilityGrant
from app.workforce.agents.control_plane.models import AgentGoal, AgentPlan, AgentPlanStep
from app.workforce.agents.control_plane.planner import ControlPlanePlanner
from app.workforce.agents.control_plane.execution import ControlPlaneExecutionManager
from app.workforce.agents.control_plane.evaluator import PlanEvaluator
from app.workforce.agents.domains.sales import (
    SalesResearchCapability,
    SalesDataCapability,
    SalesReasoningCapability,
    SalesCommunicationCapability,
    SalesActionCapability,
    SalesEvaluationCapability,
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
        SalesLead.__table__,
        SalesOpportunity.__table__,
        SalesActivity.__table__,
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
def pilot_setup(in_memory_db: Session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()

    user = User(
        id=user_id,
        email=f"founder_{user_id}@cosa.local",
        password_hash="hash",
        display_name="Sales Founder",
        status="active",
    )
    in_memory_db.add(user)

    workspace = Workspace(
        id=workspace_id,
        name="Sales Pilot Corp",
    )
    in_memory_db.add(workspace)

    member = WorkspaceMember(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        user_id=user_id,
        role="founder",
    )
    in_memory_db.add(member)

    # Seed 2 active leads
    lead1 = SalesLead(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        name="Nguyen Van An",
        company="Alpha Tech",
        stage="new",
        fit_score=85,
    )
    lead2 = SalesLead(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        name="Tran Thi Bich",
        company="Bich Logistics",
        stage="new",
        fit_score=78,
    )
    in_memory_db.add_all([lead1, lead2])
    in_memory_db.commit()

    return user, workspace, [lead1, lead2]


def test_sales_capabilities_standalone(in_memory_db: Session, pilot_setup):
    user, workspace, leads = pilot_setup

    # 1. Research
    res = SalesResearchCapability.execute(
        db=in_memory_db,
        workspace_id=workspace.id,
        input_data={"icp_criteria": "high_growth_b2b"},
    )
    assert res["status"] == "success"
    assert len(res["prospects"]) >= 3

    # 2. Reasoning (Scoring)
    reasoning_res = SalesReasoningCapability.score_prospects(res["prospects"])
    assert reasoning_res["status"] == "success"
    assert reasoning_res["high_priority_count"] >= 1

    # 3. Communication (Outreach Drafts)
    comm_res = SalesCommunicationCapability.generate_outreach_drafts(reasoning_res["qualified_prospects"])
    assert comm_res["status"] == "success"
    assert len(comm_res["drafts"]) >= 3
    assert "email_draft" in comm_res["drafts"][0]
    assert "zalo_draft" in comm_res["drafts"][0]

    # 4. Evaluation
    eval_res = SalesEvaluationCapability.evaluate_campaign(
        dispatched_count=30,
        replies_received=9,
        meetings_booked=3,
        pipeline_added_vnd=200000000,
    )
    assert eval_res["metrics"]["reply_rate"] == 0.30
    assert eval_res["metrics"]["meetings_booked"] == 3
    assert len(eval_res["learnings"]) >= 2


@pytest.mark.asyncio
async def test_sales_goal_full_pilot_execution(in_memory_db: Session, pilot_setup):
    user, workspace, leads = pilot_setup

    # 1. Create Founder Goal: "Tạo thêm 50 qualified leads và gửi chiến dịch tiếp cận"
    goal = AgentGoal(
        id=generate_snowflake_id(),
        workspace_id=workspace.id,
        user_id=user.id,
        title="Tạo thêm 50 qualified leads và gửi chiến dịch tiếp cận",
        goal_type="campaign_goal",
        target_metric_jsonb={"metric": "qualified_leads", "value": 50},
        status="active",
    )
    in_memory_db.add(goal)
    in_memory_db.commit()

    # 2. Control Plane creates Plan
    plan = ControlPlanePlanner.create_plan_for_goal(
        db=in_memory_db,
        goal=goal,
        domain_hint="sales",
    )
    assert len(plan.steps) == 7

    # 3. Execute Step 1 (Data: Read pipeline)
    step1_res = await ControlPlaneExecutionManager.execute_next_pending_step(
        db=in_memory_db,
        plan_id=plan.id,
        user_id=user.id,
        workspace_id=workspace.id,
    )
    assert step1_res.status == "completed"

    # 4. Execute Step 2 (Research: ICP target scan)
    step2_res = await ControlPlaneExecutionManager.execute_next_pending_step(
        db=in_memory_db,
        plan_id=plan.id,
        user_id=user.id,
        workspace_id=workspace.id,
    )
    assert step2_res.status == "completed"

    # 5. Execute Step 3 (Reasoning: Lead scoring)
    step3_res = await ControlPlaneExecutionManager.execute_next_pending_step(
        db=in_memory_db,
        plan_id=plan.id,
        user_id=user.id,
        workspace_id=workspace.id,
    )
    assert step3_res.status == "completed"

    # 6. Execute Step 4 (Communication: Outreach drafts)
    step4_res = await ControlPlaneExecutionManager.execute_next_pending_step(
        db=in_memory_db,
        plan_id=plan.id,
        user_id=user.id,
        workspace_id=workspace.id,
    )
    assert step4_res.status == "completed"

    # 7. Execute Step 5 (Action: Dispatches - Policy Level L3A requires approval!)
    step5_res = await ControlPlaneExecutionManager.execute_next_pending_step(
        db=in_memory_db,
        plan_id=plan.id,
        user_id=user.id,
        workspace_id=workspace.id,
    )
    assert step5_res.status == "waiting_approval"

    # Verify Approval object was created in DB
    step5 = plan.steps[4]
    approval = in_memory_db.query(AgentApproval).filter(AgentApproval.id == step5.approval_id).first()
    assert approval is not None
    assert approval.status == "pending"

    # Simulate Founder reviewing and approving the outreach in Approval Inbox
    approval.status = "approved"
    approval.reviewed_by = user.id
    approval.reviewed_at = datetime.now(timezone.utc)
    in_memory_db.commit()

    # Re-execute Step 5 after Founder Approval
    step5_approved_res = await ControlPlaneExecutionManager.execute_step(
        db=in_memory_db,
        plan_id=plan.id,
        step_id=step5.id,
        user_id=user.id,
        workspace_id=workspace.id,
    )
    assert step5_approved_res.status == "completed"
    assert "n8n" in str(step5.output_jsonb).lower()
    assert "dispatched" in str(step5.output_jsonb).lower()

    # 8. Execute Step 6 (Data: CRM stage update)
    step6_res = await ControlPlaneExecutionManager.execute_next_pending_step(
        db=in_memory_db,
        plan_id=plan.id,
        user_id=user.id,
        workspace_id=workspace.id,
    )
    assert step6_res.status == "completed"

    # 9. Execute Step 7 (Evaluation: Campaign metrics & PDCA lessons)
    step7_res = await ControlPlaneExecutionManager.execute_next_pending_step(
        db=in_memory_db,
        plan_id=plan.id,
        user_id=user.id,
        workspace_id=workspace.id,
    )
    assert step7_res.status == "completed"

    # 10. Check Overall Plan Evaluation
    final_eval = PlanEvaluator.evaluate_plan(db=in_memory_db, plan_id=plan.id)
    assert final_eval.overall_status == "completed"
    assert final_eval.completed_steps == 7
