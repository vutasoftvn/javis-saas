import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from agentos.api.app import app
from agentos.api.chat.routes import set_agent_runtime
from agentos.api.db.models import Base
from agentos.api.db.session import get_db_session
from agentos.core.factory import build_cosa_agent_plane
from agentos.core.model_provider import ModelResponse, StubModelProvider, ToolCallRequest
from agentos.core.models import AgentRunStatus, TaskContext
from agentos.core.policy import PermissionLevel


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db_session] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def setup_runtime():
    provider = StubModelProvider([ModelResponse(text="Hello founder!")])
    runtime = build_cosa_agent_plane(model_provider=provider)
    set_agent_runtime(runtime)
    yield runtime
    set_agent_runtime(None)


import jwt
from agentos.api.auth import JWT_SECRET


def make_token(user_id="user-1", workspace_id="ws-1", company_id="comp-1", role="founder"):
    return jwt.encode(
        {
            "sub": user_id,
            "workspace_id": workspace_id,
            "company_id": company_id,
            "role": role,
        },
        JWT_SECRET,
        algorithm="HS256",
    )


def test_create_conversation_defaults_to_co_founder_profile(client):
    token = make_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "x-company-id": "comp-1",
        "x-workspace-id": "ws-1",
        "x-user-id": "user-1",
        "x-membership-role": "founder",
    }
    # No active_agent_profile or agent_profile_id passed
    res = client.post("/agent/conversations", json={"title": "Test Chat"}, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["active_agent_profile"] == "co-founder"


def test_create_conversation_with_explicit_profile(client):
    token = make_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "x-company-id": "comp-1",
        "x-workspace-id": "ws-1",
        "x-user-id": "user-1",
        "x-membership-role": "founder",
    }
    res = client.post(
        "/agent/conversations",
        json={"title": "Market Chat", "agent_profile_id": "sales.researcher"},
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["active_agent_profile"] == "sales.researcher"


@pytest.mark.asyncio
async def test_runtime_respects_profile_permission_level_and_tools():
    provider = StubModelProvider([ModelResponse(text="Task completed")])
    runtime = build_cosa_agent_plane(model_provider=provider)

    sales_profile = runtime._profile_registry.get("sales.researcher")
    assert sales_profile.permission_level == PermissionLevel.L2_DRAFT
    assert "commercial.lead.create" in sales_profile.tools_allow

    task = TaskContext(
        goal="research market",
        agent_key="sales.researcher",
        workspace_id="ws-1",
        role="founder",
        metadata={
            "allowed_tools": sales_profile.tools_allow,
            "allowed_skills": sales_profile.skills,
            "mission": sales_profile.mission,
            "max_tool_calls": sales_profile.max_tool_calls,
        },
    )

    result = await runtime.run(task)
    assert result.status == AgentRunStatus.COMPLETED

    # Verify context built with restricted tool names and mission
    assert runtime.last_context is not None
    for tool_name in runtime.last_context.tool_names:
        assert tool_name in sales_profile.tools_allow
    assert "Nghiên cứu thị trường" in runtime.last_context.system_policy
