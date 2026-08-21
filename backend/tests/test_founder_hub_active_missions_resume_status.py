# backend/app/tests/test_founder_hub_active_missions_resume_status.py
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from core.snowflake import generate_snowflake_id
from db.session import engine
from founder_os.outcomes.models import Outcome, OutcomeRun
from platform_core.auth.models import User, Workspace
from platform_core.core.founder_hub_service import get_founder_command_center_data
from workforce.agents.orchestration.mission_resume_models import MissionResumeJob


@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


def test_active_missions_includes_resume_status(db_session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"fh-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"FH {workspace_id}"))
    db_session.flush()
    outcome = Outcome(
        id=generate_snowflake_id(), workspace_id=workspace_id, function="strategy",
        title="Mission chờ specialist", desired_result="goal", requested_by=user_id, status="running",
    )
    db_session.add(outcome)
    db_session.flush()
    outcome_run = OutcomeRun(
        id=generate_snowflake_id(), outcome_id=outcome.id, status="running",
        verification_status="UNKNOWN", created_at=datetime.now(timezone.utc),
    )
    db_session.add(outcome_run)
    db_session.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, outcome_run_id=outcome_run.id, agent_key="chief_of_staff",
        runtime="adk", status="running", started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.flush()
    outcome_run.agent_run_id = mission_run.id
    db_session.add(MissionResumeJob(
        id=generate_snowflake_id(), workspace_id=workspace_id, mission_run_id=mission_run.id,
        workflow_session_id="adk-session-1", checkpoint_key="delegation_step:1",
        idempotency_key=f"mission_resume:{mission_run.id}:delegation_step:1",
        reason="specialist_delegation_completed", status="queued",
    ))
    db_session.commit()

    data = get_founder_command_center_data(db_session, workspace_id, user_id)
    mission_item = next(m for m in data["active_missions"] if m["mission_id"] == str(mission_run.id))
    assert mission_item["resume_status"] == "awaiting_specialist_resume"
