# backend/app/tests/agents/test_runtime_session_model.py
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.platform.auth.models import User, Workspace
from app.workforce.agents.orchestration.runtime_session_models import RuntimeSession


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


def test_runtime_session_round_trip(db_session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"rs-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"RS {workspace_id}"))
    db_session.flush()

    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, agent_key="chief_of_staff", runtime="adk", status="running",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.flush()

    session_row = RuntimeSession(
        id=generate_snowflake_id(),
        workspace_id=workspace_id,
        mission_run_id=mission_run.id,
        agent_run_id=None,
        runtime_type="ADK",
        external_session_id="adk-session-abc123",
        status="active",
        checkpoint_ref=None,
        metadata_jsonb={"workflow_name": "adk_cofounder_workflow"},
    )
    db_session.add(session_row)
    db_session.commit()
    db_session.refresh(session_row)

    fetched = db_session.query(RuntimeSession).filter(RuntimeSession.id == session_row.id).one()
    assert fetched.runtime_type == "ADK"
    assert fetched.external_session_id == "adk-session-abc123"
    assert fetched.metadata_jsonb["workflow_name"] == "adk_cofounder_workflow"
    assert fetched.finished_at is None
