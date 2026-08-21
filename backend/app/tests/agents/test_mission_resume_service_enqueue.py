# backend/app/tests/agents/test_mission_resume_service_enqueue.py
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.platform.auth.models import User, Workspace
from app.workforce.agents.orchestration.mission_resume_models import MissionResumeJob
from app.workforce.agents.orchestration.mission_resume_service import MissionResumeJobService


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
    db_session.add(User(id=user_id, email=f"mre-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"MRE {workspace_id}"))
    db_session.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, agent_key="chief_of_staff", runtime="adk", status="running",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.commit()
    return workspace_id, mission_run


def test_enqueue_resume_is_idempotent_per_checkpoint(db_session):
    workspace_id, mission_run = _mission(db_session)

    first = MissionResumeJobService.enqueue_resume(
        db_session, workspace_id=workspace_id, mission_run_id=mission_run.id,
        workflow_session_id="adk-session-1", checkpoint_key="specialist_join:111",
        reason="specialist_delegation_completed",
    )
    second = MissionResumeJobService.enqueue_resume(
        db_session, workspace_id=workspace_id, mission_run_id=mission_run.id,
        workflow_session_id="adk-session-1", checkpoint_key="specialist_join:111",
        reason="specialist_delegation_completed",
    )

    assert first.id == second.id
    rows = db_session.query(MissionResumeJob).filter(MissionResumeJob.mission_run_id == mission_run.id).all()
    assert len(rows) == 1


def test_enqueue_resume_allows_distinct_checkpoints(db_session):
    workspace_id, mission_run = _mission(db_session)

    first = MissionResumeJobService.enqueue_resume(
        db_session, workspace_id=workspace_id, mission_run_id=mission_run.id,
        workflow_session_id="adk-session-1", checkpoint_key="specialist_join:111",
        reason="specialist_delegation_completed",
    )
    second = MissionResumeJobService.enqueue_resume(
        db_session, workspace_id=workspace_id, mission_run_id=mission_run.id,
        workflow_session_id="adk-session-1", checkpoint_key="specialist_join:222",
        reason="specialist_delegation_completed",
    )

    assert first.id != second.id
