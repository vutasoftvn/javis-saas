# backend/app/tests/agents/test_mission_resume_job_model.py
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.platform.auth.models import User, Workspace
from app.workforce.agents.orchestration.mission_resume_models import MissionResumeJob


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


def _mission(db_session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"mrj-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"MRJ {workspace_id}"))
    db_session.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, agent_key="chief_of_staff", runtime="adk", status="running",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.flush()
    return workspace_id, mission_run


def test_mission_resume_job_round_trip(db_session):
    workspace_id, mission_run = _mission(db_session)
    job = MissionResumeJob(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        mission_run_id=mission_run.id,
        workflow_session_id="adk-session-xyz",
        checkpoint_key="specialist_join:987",
        idempotency_key=f"mission_resume:{mission_run.id}:specialist_join:987",
        reason="specialist_delegation_completed",
        status="queued",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    fetched = db_session.query(MissionResumeJob).filter(MissionResumeJob.id == job.id).one()
    assert fetched.status == "queued"
    assert fetched.claimed_by is None


def test_mission_resume_job_unique_checkpoint_per_mission(db_session):
    workspace_id, mission_run = _mission(db_session)
    first = MissionResumeJob(
        id=generate_snowflake_id(), workspace_id=workspace_id, mission_run_id=mission_run.id,
        workflow_session_id="adk-session-xyz", checkpoint_key="specialist_join:987",
        idempotency_key=f"mission_resume:{mission_run.id}:specialist_join:987",
        reason="specialist_delegation_completed", status="queued",
    )
    db_session.add(first)
    db_session.commit()

    dup = MissionResumeJob(
        id=generate_snowflake_id(), workspace_id=workspace_id, mission_run_id=mission_run.id,
        workflow_session_id="adk-session-xyz", checkpoint_key="specialist_join:987",
        idempotency_key=f"mission_resume:{mission_run.id}:specialist_join:987:dup",
        reason="specialist_delegation_completed", status="queued",
    )
    db_session.add(dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
