from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from core.snowflake import generate_snowflake_id
from db.session import engine
from founder_os.outcomes.models import Outcome, OutcomeRun, RunStep
from platform_core.auth.models import User, Workspace


@pytest.fixture
def transactional_sessions():
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db.add(User(id=user_id, email=f"executor-{user_id}@example.invalid"))
    db.add(Workspace(id=workspace_id, name=f"Executor {workspace_id}"))
    db.flush()
    outcome = Outcome(
        id=generate_snowflake_id(), workspace_id=workspace_id, function="test",
        title="Executor", desired_result="Test", requested_by=user_id, status="running",
    )
    db.add(outcome)
    db.flush()
    outcome_run = OutcomeRun(
        id=generate_snowflake_id(), outcome_id=outcome.id, status="running",
        verification_status="UNKNOWN",
    )
    db.add(outcome_run)
    db.flush()
    parent = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, outcome_run_id=outcome_run.id, agent_key="chief_of_staff",
        runtime="mock", status="running", started_at=datetime.now(timezone.utc),
    )
    db.add(parent)
    db.flush()
    outcome_run.agent_run_id = parent.id
    step = RunStep(
        id=generate_snowflake_id(), run_id=outcome_run.id, type="agent", status="running",
    )
    db.add(step)
    db.commit()
    try:
        yield db, factory, workspace_id, parent, step
    finally:
        db.close()
        transaction.rollback()
        connection.close()
