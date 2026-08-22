# backend/app/tests/agents/test_tool_invocation_run_id_linkage.py
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.permissions.models import AgentToolCall
from agent_runtime.sessions.models import AgentRun
from core.snowflake import generate_snowflake_id
from db.session import engine
from platform_core.auth.models import User, Workspace
from workforce.agents.runtime.execution_scope import ExecutionScope
from workforce.tools.invocation.contracts import ToolInvocationRequest
from workforce.tools.invocation.service import ToolInvocationService


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
async def test_tool_invocation_links_agent_tool_call_to_run_id(db_session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"tiv-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"TIV {workspace_id}"))
    db_session.flush()
    mission_run = AgentRun(
        id=generate_snowflake_id(), workspace_id=workspace_id, company_id=workspace_id,
        user_id=user_id, agent_key="chief_of_staff", runtime="adk", status="running",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(mission_run)
    db_session.commit()

    scope = ExecutionScope(
        workspace_id=workspace_id, company_id=workspace_id, principal_user_id=user_id,
        principal_member_id=user_id, principal_role="owner", operating_unit_id=None,
        offering_id=None, initiative_id=None, profile_id=None, session_id=None, grants=(),
    )
    request = ToolInvocationRequest(
        scope=scope,
        tool_flat_name="finance_get_financial_summary",
        arguments={},
        source="adk_governed_tool",
        run_id=mission_run.id,
    )
    service = ToolInvocationService()
    await service.invoke(db_session, request)

    calls = db_session.query(AgentToolCall).filter(AgentToolCall.run_id == mission_run.id).all()
    assert len(calls) == 1
    assert calls[0].tool_name.endswith("get_financial_summary") or "finance" in calls[0].tool_name
