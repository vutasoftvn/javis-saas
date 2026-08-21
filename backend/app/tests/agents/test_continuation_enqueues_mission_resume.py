# backend/app/tests/agents/test_continuation_enqueues_mission_resume.py
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.founder_os.outcomes.models import Outcome, OutcomeRun, RunStep
from app.platform.auth.models import User, Workspace
from app.workforce.agents.orchestration.adk.nodes.specialist_delegation_node import interrupt_id_for_step
from app.workforce.agents.orchestration.continuation import maybe_resume_mission
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


@pytest.mark.asyncio
async def test_maybe_resume_mission_enqueues_job_for_completed_step(db_session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"cont-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"Cont {workspace_id}"))
    db_session.flush()
    outcome = Outcome(
        id=generate_snowflake_id(), workspace_id=workspace_id, function="strategy",
        title="Mission", desired_result="goal", requested_by=user_id, status="planning",
    )
    db_session.add(outcome)
    db_session.flush()
    outcome_run = OutcomeRun(id=generate_snowflake_id(), outcome_id=outcome.id, status="running", verification_status="UNKNOWN")
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
    step = RunStep(
        id=generate_snowflake_id(), run_id=outcome_run.id, type="agent", status="completed",
        inputs_jsonb={"mission_kind": "chief_of_staff_specialist", "report_key": "finance"},
        result_jsonb={"status": "success", "runway_months": 9},
    )
    db_session.add(step)
    db_session.commit()

    handled = await maybe_resume_mission(db_session, outcome_run.id, run_step_id=step.id)

    assert handled is True
    jobs = db_session.query(MissionResumeJob).filter(MissionResumeJob.mission_run_id == mission_run.id).all()
    assert len(jobs) == 1
    assert jobs[0].checkpoint_key == interrupt_id_for_step(step.id)
    assert jobs[0].status == "queued"
