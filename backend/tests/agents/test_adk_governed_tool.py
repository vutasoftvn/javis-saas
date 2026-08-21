# backend/app/tests/agents/test_adk_governed_tool.py
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import sessionmaker

from agent_runtime.permissions.models import AgentToolCall
from agent_runtime.sessions.models import AgentRun
from core.snowflake import generate_snowflake_id
from db.session import engine
from platform_core.auth.models import User, Workspace
from workforce.agents.orchestration.adk.governed_tool import CosaGovernedTool
from workforce.agents.runtime.execution_scope import ExecutionScope


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
async def test_cosa_governed_tool_dispatches_and_records_audit(db_session):
    user_id = generate_snowflake_id()
    workspace_id = generate_snowflake_id()
    db_session.add(User(id=user_id, email=f"gt-{user_id}@example.invalid"))
    db_session.add(Workspace(id=workspace_id, name=f"GT {workspace_id}"))
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

    tool = CosaGovernedTool(
        tool_flat_name="finance_get_financial_summary",
        db_factory=lambda: db_session,
        scope_factory=lambda: scope,
        run_id_factory=lambda: mission_run.id,
        source="adk_workflow",
    )

    fake_tool_context = MagicMock()
    fake_tool_context.state = {"malicious_override": {"workspace_id": 999999}}

    result = await tool.run_async(args={}, tool_context=fake_tool_context)

    assert isinstance(result, dict)
    calls = db_session.query(AgentToolCall).filter(AgentToolCall.run_id == mission_run.id).all()
    assert len(calls) == 1
