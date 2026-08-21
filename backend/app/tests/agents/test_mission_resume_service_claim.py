# backend/app/tests/agents/test_mission_resume_service_claim.py
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


def _queued_job(db_session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"mrc-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"MRC {workspace_id}"))
    db_session.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, agent_key="chief_of_staff", runtime="adk", status="running",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.flush()
    job = MissionResumeJobService.enqueue_resume(
        db_session, workspace_id=workspace_id, mission_run_id=mission_run.id,
        workflow_session_id="adk-session-1", checkpoint_key="specialist_join:111",
        reason="specialist_delegation_completed",
    )
    return job


def test_claim_next_is_exactly_once_across_two_simulated_workers(db_session):
    job = _queued_job(db_session)
    now = datetime.now(timezone.utc)

    claimed_id_a = MissionResumeJobService.claim_next(db_session, "worker-a", now)
    assert claimed_id_a == job.id
    db_session.refresh(job)
    assert job.status == "claimed"
    assert job.claimed_by == "worker-a"

    # Worker thứ 2 chạy claim_next ngay sau đó — không còn job "queued" nào để lấy.
    claimed_id_b = MissionResumeJobService.claim_next(db_session, "worker-b", now)
    assert claimed_id_b is None


def test_mark_completed_and_mark_failed(db_session):
    job = _queued_job(db_session)
    now = datetime.now(timezone.utc)
    MissionResumeJobService.claim_next(db_session, "worker-a", now)

    MissionResumeJobService.mark_completed(db_session, job.id)
    db_session.refresh(job)
    assert job.status == "completed"
    assert job.completed_at is not None

    job2 = _queued_job(db_session)
    MissionResumeJobService.claim_next(db_session, "worker-a", now)
    MissionResumeJobService.mark_failed(db_session, job2.id, "resume raised ValueError")
    db_session.refresh(job2)
    assert job2.status == "failed"
    assert job2.error_message == "resume raised ValueError"
