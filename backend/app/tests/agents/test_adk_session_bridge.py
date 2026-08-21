# backend/app/tests/agents/test_adk_session_bridge.py
from datetime import datetime, timezone

import pytest
from google.adk.events.event import Event
from google.genai import types as genai_types
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker

from agent_runtime.events.models import AgentEventRecord
from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.platform.auth.models import User, Workspace
from app.workforce.agents.orchestration.adk.session_bridge import project_adk_event


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


def test_project_adk_event_writes_agent_event_record(db_session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"sb-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"SB {workspace_id}"))
    db_session.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, agent_key="chief_of_staff", runtime="adk", status="running",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.commit()

    event = Event(
        author="risk_classification_node",
        content=genai_types.Content(role="model", parts=[genai_types.Part(text="R0")]),
        output={"risk_level": "R0"},
    )

    record = project_adk_event(
        db_session, event, mission_run_id=mission_run.id, workspace_id=workspace_id,
    )
    db_session.commit()

    assert record.run_id == mission_run.id
    assert record.event_type == "adk.node_completed"
    assert record.payload_jsonb["author"] == "risk_classification_node"
    assert record.payload_jsonb["output"] == {"risk_level": "R0"}

    stored = db_session.query(AgentEventRecord).filter(AgentEventRecord.run_id == mission_run.id).all()
    assert len(stored) == 1

    # Sequence phải tự tăng đúng cách khi ghi thêm 1 event nữa
    event2 = Event(author="planning_node", output={"priorities": []})
    project_adk_event(db_session, event2, mission_run_id=mission_run.id, workspace_id=workspace_id)
    db_session.commit()
    max_seq = db_session.query(func.max(AgentEventRecord.sequence)).filter(
        AgentEventRecord.run_id == mission_run.id
    ).scalar()
    assert max_seq == 2
