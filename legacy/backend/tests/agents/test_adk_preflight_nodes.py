# backend/app/tests/agents/test_adk_preflight_nodes.py
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from core.snowflake import generate_snowflake_id
from db.session import engine
from founder_os.outcomes.models import Outcome, OutcomeRun
from platform_core.auth.models import User, Workspace
from workforce.agents.orchestration.adk.nodes import build_company_context_node as bcc_module
from workforce.agents.orchestration.adk.nodes import create_mission_node as cm_module
from workforce.agents.orchestration.adk.nodes.build_company_context_node import (
    build_company_context_fn,
    build_company_context_node,
)
from workforce.agents.orchestration.adk.nodes.create_mission_node import (
    build_create_mission_node,
    create_mission_fn,
)


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
async def test_create_mission_fn_creates_outcome_and_agent_run(db_session, monkeypatch):
    monkeypatch.setattr(cm_module, "SessionLocal", lambda: db_session)

    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"cm-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"CM {workspace_id}"))
    db_session.commit()

    ctx = SimpleNamespace(
        state={
            "workspace_id": workspace_id,
            "user_id": user_id,
            "company_id": workspace_id,
            "goal": "Tăng trưởng MRR Q3",
            "requested_domains": ["sales", "finance"],
            "intent": None,
        }
    )

    out = await create_mission_fn(ctx)

    assert "mission_id" in out
    mission_run = db_session.query(AgentRun).filter(AgentRun.id == ctx.state["mission_id"]).one()
    assert mission_run.agent_key == "chief_of_staff"
    assert mission_run.runtime == "adk"
    outcome = db_session.query(Outcome).filter(Outcome.id == ctx.state["outcome_id"]).one()
    assert outcome.desired_result == "Tăng trưởng MRR Q3"
    outcome_run = db_session.query(OutcomeRun).filter(OutcomeRun.id == ctx.state["outcome_run_id"]).one()
    assert outcome_run.agent_run_id == mission_run.id


@pytest.mark.asyncio
async def test_build_company_context_fn_assembles_context(db_session, monkeypatch):
    monkeypatch.setattr(bcc_module, "SessionLocal", lambda: db_session)

    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"bcc-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"BCC {workspace_id}"))
    db_session.commit()

    ctx = SimpleNamespace(
        state={
            "workspace_id": workspace_id,
            "company_id": workspace_id,
            "user_id": user_id,
            "active_domains": ["sales"],
            "intent": None,
        }
    )

    out = await build_company_context_fn(ctx)

    assert "agent_context" in out
    assert ctx.state["company_context"] is not None


def test_build_preflight_nodes_shapes():
    assert build_create_mission_node().name == "create_mission_node"
    assert build_company_context_node().name == "build_company_context_node"
