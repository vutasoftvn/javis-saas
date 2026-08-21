# backend/app/tests/agents/test_adk_preflight_nodes.py
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.sessions.models import AgentRun
from app.core.snowflake import generate_snowflake_id
from app.db.session import engine
from app.founder_os.outcomes.models import Outcome, OutcomeRun
from app.platform.auth.models import User, Workspace
from app.workforce.agents.orchestration.adk.nodes.build_company_context_node import (
    build_company_context_fn,
    build_company_context_node,
)
from app.workforce.agents.orchestration.adk.nodes.create_mission_node import (
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
async def test_create_mission_fn_creates_outcome_and_agent_run(db_session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"cm-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"CM {workspace_id}"))
    db_session.commit()

    ctx = SimpleNamespace(
        state={
            "db": db_session,
            "workspace_id": workspace_id,
            "user_id": user_id,
            "company_id": workspace_id,
            "goal": "Tăng trưởng MRR Q3",
            "domains": ["sales", "finance"],
            "intent": None,
            "context": None,
        }
    )

    out = await create_mission_fn(ctx)

    assert "mission_run_id" in out
    assert ctx.state["mission_run"].agent_key == "chief_of_staff"
    assert ctx.state["mission_run"].runtime == "adk"
    assert ctx.state["outcome"].desired_result == "Tăng trưởng MRR Q3"
    assert ctx.state["outcome_run"].agent_run_id == ctx.state["mission_run"].id


@pytest.mark.asyncio
async def test_build_company_context_fn_assembles_context(db_session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"bcc-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"BCC {workspace_id}"))
    db_session.commit()

    ctx = SimpleNamespace(
        state={
            "db": db_session,
            "workspace_id": workspace_id,
            "company_id": workspace_id,
            "domains": ["sales"],
            "intent": None,
            "context": None,
        }
    )

    out = await build_company_context_fn(ctx)

    assert "company_context" in out
    assert ctx.state["company_context"] is not None


def test_build_preflight_nodes_shapes():
    assert build_create_mission_node().name == "create_mission_node"
    assert build_company_context_node().name == "build_company_context_node"
