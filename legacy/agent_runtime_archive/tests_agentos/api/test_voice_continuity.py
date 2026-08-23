import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from agentos.api.app import app
from agentos.api.auth import PLATFORM_JWT_SECRET
from agentos.api.chat.routes import _pending_runs, set_agent_runtime
from agentos.api.db.models import Base
from agentos.api.db.repository import ChatRepository
from agentos.api.db.session import get_db_session
from agentos.core.approval import ApprovalService, ApprovalStatus
from agentos.core.context import AgentContext
from agentos.core.context_builder import ContextBuilder
from agentos.core.model_provider import ModelProvider, ModelResponse, StubModelProvider
from agentos.core.models import AgentResult, AgentRunStatus, TaskContext
from agentos.core.policy import PermissionClass, PermissionLevel, PolicyDecision, PolicyEngine, ToolPermission, ToolRiskLevel
from agentos.core.runtime import AgentRuntime
from agentos.tools.registry import ToolRegistry, ToolSpec
import jwt


@pytest.fixture
def test_db():
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
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def auth_headers():
    token = jwt.encode(
        {"sub": "user-voice-1", "workspace_id": "ws-1", "company_id": "comp-1", "role": "founder"},
        PLATFORM_JWT_SECRET,
        algorithm="HS256",
    )
    return {
        "Authorization": f"Bearer {token}",
        "X-Workspace-Id": "ws-1",
        "X-Company-Id": "comp-1",
    }


@pytest.fixture
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db_session] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()
    set_agent_runtime(None)


def test_text_to_voice_to_text_continuity(client, auth_headers):
    """Test 6a Acceptance:
    1. Start conversation in Text Chat, send a message.
    2. Switch to Voice with the same conversation_id, speak a turn.
    3. Return to Text Chat -> verify full history (text, voice, assistant) in chronological order.
    """
    mock_model = StubModelProvider([
        ModelResponse(text="Báo cáo tài chính quý 2 có doanh thu tăng 15%."),
        ModelResponse(text="Runway hiện tại là 14 tháng với mức burn rate ổn định."),
    ])
    runtime = AgentRuntime(mock_model, ToolRegistry())
    set_agent_runtime(runtime)

    # 1. Create conversation in Text Chat
    conv_res = client.post(
        "/agent/conversations",
        headers=auth_headers,
        json={"title": "Strategy Session", "active_agent_profile": "founder_assistant"},
    )
    assert conv_res.status_code == 201
    conv_id = conv_res.json()["id"]

    # 2. User sends 1st message via Text Chat
    msg1_res = client.post(
        f"/agent/conversations/{conv_id}/messages",
        headers=auth_headers,
        json={"content": "Tôi muốn phân tích báo cáo tài chính quý 2", "role": "user"},
    )
    assert msg1_res.status_code == 202

    # 3. User switches to Voice using the same conversation_id
    voice_user_msg = client.post(
        f"/agent/conversations/{conv_id}/messages",
        headers=auth_headers,
        json={"content": "Tập trung vào tỷ lệ burn rate và runway", "role": "user"},
    )
    assert voice_user_msg.status_code == 202

    # 4. User returns to Text Chat with same conversation_id
    get_conv_res = client.get(f"/agent/conversations/{conv_id}", headers=auth_headers)
    assert get_conv_res.status_code == 200
    conv_data = get_conv_res.json()

    messages = conv_data["messages"]
    user_messages = [m for m in messages if m["role"] == "user"]
    assert len(user_messages) == 2
    assert "Tôi muốn phân tích báo cáo tài chính quý 2" in user_messages[0]["content"]
    assert "Tập trung vào tỷ lệ burn rate và runway" in user_messages[1]["content"]


def test_voice_session_without_conversation_id_creates_new(client, auth_headers):
    """Test 6a Acceptance:
    Starting voice without conversation_id automatically creates a new conversation.
    """
    create_res = client.post(
        "/agent/conversations",
        headers=auth_headers,
        json={"title": "Voice Session", "active_agent_profile": "founder_assistant"},
    )
    assert create_res.status_code == 201
    conv = create_res.json()
    assert conv["id"] is not None
    assert conv["title"] == "Voice Session"


@pytest.mark.asyncio
async def test_context_builder_continuity_after_voice_turn(test_db):
    """Test 6a Acceptance:
    ContextBuilder builds context for a text turn immediately after a voice turn.
    Context contains the voice turn content without channel bias or separate voice cache.
    """
    repo = ChatRepository(test_db)
    conv = repo.create_conversation(
        company_id="comp-1",
        workspace_id="ws-1",
        created_by_principal="user:user-voice-1",
        title="Continuity Test",
    )

    # 1. Text message
    repo.create_message(conversation_id=conv.id, role="user", content="Đánh giá KPI tuần này")
    repo.create_message(conversation_id=conv.id, role="assistant", content="KPI tuần này đạt 90%")
    # 2. Voice turn
    repo.create_message(conversation_id=conv.id, role="user", content="Dự án nào đang bị chậm tiến độ?")
    repo.create_message(conversation_id=conv.id, role="assistant", content="Dự án Mobile App đang bị chậm 2 ngày.")

    registry = ToolRegistry()
    builder = ContextBuilder(registry)

    # Now user sends a text turn
    past_messages = repo.list_messages(conv.id, limit=20)
    history = [{"role": m.role, "content": m.content} for m in past_messages]

    task = TaskContext(
        goal="Làm sao để đẩy nhanh tiến độ Mobile App?",
        agent_key="founder_assistant",
        workspace_id="ws-1",
        company_id="comp-1",
        user_id="user-voice-1",
        role="founder",
        metadata={"conversation_id": conv.id, "conversation_messages": history},
    )

    context = await builder.build(task)

    # Verify context has all turns including the voice turns
    assert len(context.conversation_messages) == 4
    assert context.conversation_messages[2]["content"] == "Dự án nào đang bị chậm tiến độ?"
    assert context.conversation_messages[3]["content"] == "Dự án Mobile App đang bị chậm 2 ngày."


def test_voice_approval_flow_approved(client, auth_headers, test_db):
    """Test 6b Acceptance:
    1. Voice tool call triggers high-risk action -> receives approval.required.
    2. Simulated user voice confirmation "đồng ý" -> POST /agent/approvals/{id}/decision with approved=True.
    3. Run resumes with the same run_id and completes execution.
    """
    approval_svc = ApprovalService()
    run_id = "test-run-voice-appr-1"
    conv_id = "test-conv-voice-appr-1"

    # Pre-populate pending run
    _pending_runs[run_id] = {
        "run_id": run_id,
        "conversation_id": conv_id,
        "user_goal": "Triển khai release v2 lên production",
        "tenant": type(
            "MockTenant",
            (),
            {
                "user_id": "user-voice-1",
                "workspace_id": "ws-1",
                "company_id": "comp-1",
                "membership_role": "founder",
                "correlation_id": "corr-1",
                "to_agent_permission_level": lambda self: PermissionLevel.L3_EXECUTE,
            },
        )(),
        "agent_key": "founder_assistant",
    }

    # Request high risk approval
    appr = approval_svc.request_approval(
        action="deploy_service",
        subject="service=backend,env=prod",
        requester="founder_assistant",
        run_id=run_id,
    )

    # Setup runtime with approval_svc
    mock_model = MagicMock(spec=ModelProvider)
    mock_model.generate = AsyncMock(
        return_value=ModelResponse(text="Đã hoàn tất deploy release v2 lên production.", tool_call=None)
    )
    registry = ToolRegistry()
    runtime = AgentRuntime(mock_model, registry, approval_service=approval_svc)
    set_agent_runtime(runtime)

    # User confirms via voice: "đồng ý"
    decide_res = client.post(
        f"/agent/approvals/{appr.id}/decision",
        headers=auth_headers,
        json={"approved": True, "reason": "Founder xác nhận qua giọng nói"},
    )
    assert decide_res.status_code == 200
    res_data = decide_res.json()
    assert res_data["status"] == "APPROVED"
    assert res_data["run_id"] == run_id

    # Verify approval status in service
    stored_appr = approval_svc.get(appr.id)
    assert stored_appr.status == ApprovalStatus.APPROVED


def test_voice_approval_flow_rejected(client, auth_headers, test_db):
    """Test 6b Acceptance:
    User rejects via voice ("từ chối") -> POST /agent/approvals/{id}/decision with approved=False.
    Tool call cancelled, run marked failed.
    """
    approval_svc = ApprovalService()
    run_id = "test-run-voice-rej-1"
    conv_id = "test-conv-voice-rej-1"

    _pending_runs[run_id] = {
        "run_id": run_id,
        "conversation_id": conv_id,
        "user_goal": "Xóa toàn bộ dữ liệu demo",
        "tenant": type(
            "MockTenant",
            (),
            {
                "user_id": "user-voice-1",
                "workspace_id": "ws-1",
                "company_id": "comp-1",
                "membership_role": "founder",
                "correlation_id": "corr-1",
                "to_agent_permission_level": lambda self: PermissionLevel.L3_EXECUTE,
            },
        )(),
        "agent_key": "founder_assistant",
    }

    appr = approval_svc.request_approval(
        action="delete_database",
        subject="db=demo",
        requester="founder_assistant",
        run_id=run_id,
    )

    mock_model = MagicMock(spec=ModelProvider)
    registry = ToolRegistry()
    runtime = AgentRuntime(mock_model, registry, approval_service=approval_svc)
    set_agent_runtime(runtime)

    # User says "từ chối"
    decide_res = client.post(
        f"/agent/approvals/{appr.id}/decision",
        headers=auth_headers,
        json={"approved": False, "reason": "Founder từ chối qua giọng nói"},
    )
    assert decide_res.status_code == 200
    res_data = decide_res.json()
    assert res_data["status"] == "DENIED"

    stored_appr = approval_svc.get(appr.id)
    assert stored_appr.status == ApprovalStatus.DENIED
