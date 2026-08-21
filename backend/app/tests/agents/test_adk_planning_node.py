# backend/app/tests/agents/test_adk_planning_node.py
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.founder_os.outcomes.models import Outcome, OutcomeRun
from app.platform.auth.models import User, Workspace
from app.workforce.agents.orchestration.adk.nodes.planning_node import build_planning_node, planning_fn


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
async def test_planning_fn_transitions_to_running_and_selects_default_domains(db_session, monkeypatch):
    from app.workforce.agents.orchestration.adk.nodes import planning_node as node_module

    monkeypatch.setattr(node_module, "SessionLocal", lambda: db_session)

    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"pl-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"PL {workspace_id}"))
    db_session.flush()
    outcome = Outcome(
        id=generate_snowflake_id(), workspace_id=workspace_id, function="strategy",
        title="Mission", desired_result="goal", requested_by=user_id, status="draft",
    )
    db_session.add(outcome)
    db_session.flush()
    outcome_run = OutcomeRun(id=generate_snowflake_id(), outcome_id=outcome.id, status="queued", verification_status="UNKNOWN")
    db_session.add(outcome_run)
    db_session.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, outcome_run_id=outcome_run.id, agent_key="chief_of_staff",
        runtime="adk", status="created", started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.commit()

    ctx = SimpleNamespace(state={
        "outcome_id": outcome.id, "outcome_run_id": outcome_run.id,
        "mission_id": mission_run.id, "active_domains": [],
    })

    result = await planning_fn(ctx)

    assert result["active_domains"] == ["sales", "finance"]
    outcome = db_session.query(Outcome).filter(Outcome.id == outcome.id).one()
    outcome_run = db_session.query(OutcomeRun).filter(OutcomeRun.id == outcome_run.id).one()
    mission_run = db_session.query(AgentRun).filter(AgentRun.id == mission_run.id).one()
    assert outcome.status == "planning"
    assert outcome_run.status == "running"
    assert mission_run.status == "running"



def test_build_planning_node_shape():
    node = build_planning_node()
    assert node.name == "planning_node"
