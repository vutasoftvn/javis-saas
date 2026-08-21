from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Allow SQLite to render Postgres specific types
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "TEXT"

@compiles(TSVECTOR, "sqlite")
def compile_tsvector_sqlite(type_, compiler, **kw):
    return "TEXT"

from main import app
from db.base_class import Base
from db.session import get_db
from core.snowflake import generate_snowflake_id
from core.auth import get_current_workspace_member
from db.models import Workspace, WorkspaceMember, User
from founder_os.outcomes.models import Outcome, OutcomeRun, RunStep, Artifact
from workforce.agents.governance.models import AgentRun, AgentEventRecord, AgentToolCall, AgentApproval
from core.feature_flags import FLAG_STRATEGY_MODULE_V13_2, is_enabled


from platform_core.core.models import FeatureFlag

@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from workforce.agents.orchestration.mission_resume_models import MissionResumeJob
    from workforce.agents.orchestration.runtime_session_models import RuntimeSession

    # Create only needed tables
    tables = [
        User.__table__,
        Workspace.__table__,
        WorkspaceMember.__table__,
        Outcome.__table__,
        OutcomeRun.__table__,
        RunStep.__table__,
        AgentRun.__table__,
        AgentEventRecord.__table__,
        AgentToolCall.__table__,
        Artifact.__table__,
        AgentApproval.__table__,
        FeatureFlag.__table__,
        RuntimeSession.__table__,
        MissionResumeJob.__table__,
    ]

    Base.metadata.create_all(bind=engine, tables=tables)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_setup(db_session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()

    user = User(
        id=user_id,
        email="founder_test@cosa.ai",
        display_name="Founder Test",
        password_hash="hashed_test_password",
        status="active",
    )
    db_session.add(user)

    workspace = Workspace(
        id=workspace_id,
        name="COSA HQ Test",
    )
    db_session.add(workspace)

    member = WorkspaceMember(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        user_id=user_id,
        role="owner",
    )
    db_session.add(member)
    db_session.commit()

    return {
        "user_id": user_id,
        "workspace_id": workspace_id,
        "member": member,
    }


def test_strategy_feature_flag_default_enabled(db_session, test_setup):
    ws_id = test_setup["workspace_id"]
    enabled = is_enabled(db_session, FLAG_STRATEGY_MODULE_V13_2, workspace_id=ws_id)
    assert FLAG_STRATEGY_MODULE_V13_2 == "strategy_module"


def test_list_and_get_mission_api(db_session, test_setup):
    ws_id = test_setup["workspace_id"]
    u_id = test_setup["user_id"]
    member = test_setup["member"]

    # 1. Seed Outcome + OutcomeRun + AgentRun
    outcome_id = generate_snowflake_id()
    outcome_run_id = generate_snowflake_id()
    agent_run_id = generate_snowflake_id()

    outcome = Outcome(
        id=outcome_id,
        workspace_id=ws_id,
        title="Nhiệm vụ: Mở rộng thị trường Q3",
        desired_result="Tìm 50 lead ICP fit và gửi bản thảo outreach",
        requested_by=u_id,
        status="running",
    )
    db_session.add(outcome)

    outcome_run = OutcomeRun(
        id=outcome_run_id,
        outcome_id=outcome_id,
        agent_run_id=agent_run_id,
        status="running",
        verification_status="VERIFIED",
        verification_jsonb={
            "verdict": "VERIFIED",
            "evidence": ["lead_contact_5501", "sales_crm_deal_9902"],
            "unresolved": [],
        },
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(outcome_run)

    agent_run = AgentRun(
        id=agent_run_id,
        workspace_id=ws_id,
        user_id=u_id,
        outcome_run_id=outcome_run_id,
        agent_key="chief_of_staff",
        status="running",
        estimated_cost=0.15,
        budget_jsonb={
            "max_steps": 10,
            "max_api_cost_usd": 0.50,
        },
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(agent_run)

    # Add Event
    event = AgentEventRecord(
        id=generate_snowflake_id(),
        run_id=agent_run_id,
        sequence=1,
        agent_key="chief_of_staff",
        event_type="mission_started",
        payload_jsonb={"goal": "Mở rộng thị trường Q3"},
    )
    db_session.add(event)

    # Add Tool Call
    tool_call = AgentToolCall(
        id=generate_snowflake_id(),
        run_id=agent_run_id,
        agent_key="sales_specialist",
        tool_name="crm.upsert_contact",
        status="success",
        risk_level="medium",
        capability="sales_crm",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(tool_call)

    # Add Artifact (Evidence)
    artifact = Artifact(
        id=generate_snowflake_id(),
        workspace_id=ws_id,
        outcome_id=outcome_id,
        run_id=outcome_run_id,
        title="Outcome Certificate - Market Expansion",
        type="external_action_receipt",
        status="approved",
        created_by=u_id,
    )
    db_session.add(artifact)
    db_session.commit()

    # Create test client with dependency override for member & db
    app.dependency_overrides[get_current_workspace_member] = lambda: member
    app.dependency_overrides[get_db] = lambda: db_session

    client = TestClient(app)

    try:
        # 2. Test GET /api/v1/workspaces/{ws_id}/missions
        resp = client.get(f"/api/v1/workspaces/{ws_id}/missions")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "success"
        assert data["total"] >= 1

        mission_item = next((m for m in data["data"] if m["mission_id"] == str(agent_run_id)), None)
        assert mission_item is not None
        assert mission_item["title"] == "Nhiệm vụ: Mở rộng thị trường Q3"
        assert mission_item["agent"] == "Chief Of Staff"
        assert mission_item["verification_status"] == "VERIFIED"
        assert mission_item["evidence_count"] >= 1
        assert mission_item["budget"]["max_cost_usd"] == 0.50
        assert mission_item["budget"]["current_cost_usd"] == 0.15
        assert mission_item["loop_health"]["status"] == "healthy"

        # 3. Test GET /api/v1/workspaces/{ws_id}/missions/{mission_id}
        detail_resp = client.get(f"/api/v1/workspaces/{ws_id}/missions/{agent_run_id}")
        assert detail_resp.status_code == 200, detail_resp.text
        detail = detail_resp.json()["data"]
        assert detail["mission_id"] == str(agent_run_id)
        assert len(detail["timeline"]) >= 1
        assert len(detail["tool_calls"]) >= 1
        assert len(detail["evidence"]) >= 1
        assert detail["verification_detail"]["verdict"] == "VERIFIED"

        # 4. Test Tenancy Security: wrong workspace returns 403
        wrong_ws_resp = client.get(f"/api/v1/workspaces/{generate_snowflake_id()}/missions")
        assert wrong_ws_resp.status_code == 403

    finally:
        app.dependency_overrides.clear()


def test_mission_detail_includes_resume_status_and_runtime_sessions(db_session, test_setup):
    from workforce.agents.orchestration.mission_resume_models import MissionResumeJob
    from workforce.agents.orchestration.runtime_session_models import RuntimeSession

    ws_id = test_setup["workspace_id"]
    u_id = test_setup["user_id"]
    member = test_setup["member"]

    outcome_id = generate_snowflake_id()
    outcome_run_id = generate_snowflake_id()
    agent_run_id = generate_snowflake_id()

    db_session.add(Outcome(
        id=outcome_id, workspace_id=ws_id, title="Nhiệm vụ chờ specialist",
        desired_result="Chờ finance specialist", requested_by=u_id, status="running",
    ))
    db_session.add(OutcomeRun(
        id=outcome_run_id, outcome_id=outcome_id, agent_run_id=agent_run_id,
        status="running", verification_status="UNKNOWN", started_at=datetime.now(timezone.utc),
    ))
    db_session.add(AgentRun(
        id=agent_run_id, workspace_id=ws_id, user_id=u_id, outcome_run_id=outcome_run_id,
        agent_key="chief_of_staff", status="running", started_at=datetime.now(timezone.utc),
    ))
    db_session.add(RuntimeSession(
        id=generate_snowflake_id(), workspace_id=ws_id, mission_run_id=agent_run_id,
        agent_run_id=None, runtime_type="ADK", external_session_id="adk-session-xyz",
        status="active",
    ))
    db_session.add(MissionResumeJob(
        id=generate_snowflake_id(), workspace_id=ws_id, mission_run_id=agent_run_id,
        workflow_session_id="adk-session-xyz", checkpoint_key="delegation_step:999",
        idempotency_key=f"mission_resume:{agent_run_id}:delegation_step:999",
        reason="specialist_delegation_completed", status="queued",
    ))
    db_session.commit()

    app.dependency_overrides[get_current_workspace_member] = lambda: member
    app.dependency_overrides[get_db] = lambda: db_session
    client = TestClient(app)
    try:
        resp = client.get(f"/api/v1/workspaces/{ws_id}/missions/{agent_run_id}")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["resume_status"] == "awaiting_specialist_resume"
        assert len(data["runtime_sessions"]) == 1
        assert data["runtime_sessions"][0]["runtime_type"] == "ADK"
        assert data["runtime_sessions"][0]["external_session_id"] == "adk-session-xyz"

        list_resp = client.get(f"/api/v1/workspaces/{ws_id}/missions")
        list_item = next(m for m in list_resp.json()["data"] if m["mission_id"] == str(agent_run_id))
        assert list_item["resume_status"] == "awaiting_specialist_resume"
    finally:
        app.dependency_overrides.clear()

