"""
End-to-End (E2E) Integration Test Suite for COSA Modernization (Phase 9)
Kiểm thử toàn diện toàn bộ chuỗi hệ thống:
1. Greeting Isolation E2E
2. Project Context Activation E2E
3. Tool Execution & Event Persistence E2E
4. Human-in-the-Loop Approval Lifecycle E2E
5. Session Forking & Safe Replay E2E
6. Clean Architecture Zero AI Imports Gate
"""
import ast
import os
import pytest
import tempfile

from agent.context.base import ContextBudget, ContextScope
from agent.context.context_engine import ContextEngine
from agent.events.base import AgentEvent, EventType
from agent.events.sqlite_event_store import SQLiteEventStore
from agent.models.base import ModelCallPayload, ModelCapabilityPolicy
from agent.models.gateway import model_gateway
from agent.profiles.registry import agent_profile_registry
from agent.routing.base import IntentCategory
from agent.routing.capability_resolver import CapabilityResolver
from agent.routing.intent_router import IntentRouter
from agent.runtime.base import AgentRuntimeState
from agent.sessions.session_manager import SessionManager
from agent.trajectory.trajectory_builder import TrajectoryBuilder
from storage.sqlite.connection import SQLiteManager
from tools.dispatcher import ToolDispatcher
from tools.finance import QueryPnLTool
from tools.hostinger import DeployStagingTool
from tools.registry import ToolRegistry


@pytest.fixture
def temp_sqlite():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    manager = SQLiteManager(db_path=db_path)
    yield manager
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.mark.asyncio
async def test_e2e_greeting_zero_context_flow():
    """
    Scenario 1: Greeting Isolation E2E (CLAUDE §9, §17)
    Người dùng gửi lời chào -> Intent Router bắt GREETING -> Zero Context Load -> Phản hồi lập tức.
    """
    router = IntentRouter()
    context_engine = ContextEngine()

    user_message = "Xin chào bạn"
    routing_result = await router.route_intent(user_message)

    # 1. Router phải nhận diện GREETING và không đòi context dự án
    assert routing_result.category == IntentCategory.GREETING
    assert routing_result.requires_project_context is False
    assert routing_result.target_project_id is None

    # 2. Kiểm tra Explicit Context Rule
    should_load = ContextEngine.should_load_project(intent_result=routing_result)
    assert should_load is False

    # 3. Context Engine chỉ nạp system context tối thiểu mà không nạp scope PROJECT
    resolved = await context_engine.resolve_context(
        scopes=[ContextScope.COMPANY],
        params={"company_id": "comp_cosa"}
    )
    assert ContextScope.PROJECT not in resolved.scopes
    assert resolved.system_instructions is not None


@pytest.mark.asyncio
async def test_e2e_project_mention_and_context_injection():
    """
    Scenario 2: Project Context Activation E2E (CLAUDE §10, §17)
    Người dùng gửi câu lệnh có gắn nhãn @mID -> Intent Router bóc tách target_project_id -> Context Engine nạp dữ liệu.
    """
    router = IntentRouter()
    context_engine = ContextEngine()

    user_message = "Hãy đánh giá tiến độ cho dự án @mID và lập kế hoạch OKR tuần tới."
    routing_result = await router.route_intent(user_message)

    assert routing_result.requires_project_context is True
    assert routing_result.target_project_id == "mID"

    # Context Engine nạp thông tin dự án mID
    resolved = await context_engine.resolve_context(
        scopes=[ContextScope.COMPANY, ContextScope.PROJECT],
        params={"company_id": "comp_cosa", "project_id": routing_result.target_project_id}
    )
    assert ContextScope.PROJECT in resolved.scopes
    assert "mID" in resolved.operational_data["project"]["project_name"]


@pytest.mark.asyncio
async def test_e2e_tool_execution_and_presenter_generation(temp_sqlite):
    """
    Scenario 3: Tool Execution & Event Persistence E2E (Structure §11, §12, §24)
    CFO Agent thực thi finance.query_pnl -> Event Store lưu sự kiện -> Presenter sinh view_type chuẩn -> Trajectory cập nhật.
    """
    event_store = SQLiteEventStore(temp_sqlite)
    registry = ToolRegistry()
    registry.register(QueryPnLTool())
    dispatcher = ToolDispatcher(registry=registry, event_store=event_store)

    session_id = "ses_e2e_pnl_01"

    # 1. Thực thi công cụ qua Dispatcher
    tool_result = await dispatcher.dispatch(
        tool_id="finance.query_pnl",
        input_data={"quarter": "Q1-2026", "include_forecast": True},
        context={},
        session_id=session_id
    )

    # 2. Kiểm tra kết quả và Presenter Payload (No raw JSON)
    assert tool_result.status == "success"
    assert tool_result.presenter_payload is not None
    assert tool_result.presenter_payload["view_type"] == "pnl_statement_card"
    assert "P&L" in tool_result.presenter_payload["title"]

    # 3. Kiểm tra sự kiện đã được lưu tự động trong SQLite Event Store
    events = await event_store.get_events_by_session(session_id=session_id)
    event_types = [e.type for e in events]
    assert EventType.TOOL_REQUESTED in event_types
    assert EventType.TOOL_COMPLETED in event_types

    # 4. Kiểm tra Trajectory Timeline
    trajectory = TrajectoryBuilder.build_timeline(
        session_id=session_id,
        profile_id="cfo",
        events=events
    )
    assert len(trajectory.steps) >= 1
    assert any("finance.query_pnl" in s.title for s in trajectory.steps)


@pytest.mark.asyncio
async def test_e2e_high_risk_approval_lifecycle(temp_sqlite):
    """
    Scenario 4: Human-in-the-Loop Approval Lifecycle E2E (Structure §11)
    Yêu cầu Deploy Staging -> Gặp Tool HIGH_RISK -> Chặn thực thi -> Phê duyệt -> Tiếp tục thành công.
    """
    event_store = SQLiteEventStore(temp_sqlite)
    registry = ToolRegistry()
    registry.register(DeployStagingTool())
    dispatcher = ToolDispatcher(registry=registry, event_store=event_store)

    session_id = "ses_e2e_deploy_01"

    # 1. Gọi Tool HIGH_RISK khi chưa phê duyệt (approved_by=None)
    res_pending = await dispatcher.dispatch(
        tool_id="deployment.deploy_staging",
        input_data={"branch": "main", "target_env": "staging"},
        context={},
        session_id=session_id
    )
    assert res_pending.status == "pending_approval"
    assert res_pending.presenter_payload["view_type"] == "approval_request_card"

    # 2. Founder gửi tín hiệu Phê duyệt (approved_by="founder")
    res_approved = await dispatcher.dispatch(
        tool_id="deployment.deploy_staging",
        input_data={"branch": "main", "target_env": "staging"},
        context={},
        session_id=session_id,
        approved_by="founder"
    )
    assert res_approved.status == "success"
    assert res_approved.presenter_payload["view_type"] == "deployment_status_card"
    assert "Triển khai Staging" in res_approved.presenter_payload["title"]


@pytest.mark.asyncio
async def test_e2e_session_fork_and_safe_replay(temp_sqlite):
    """
    Scenario 5: Session Forking & Safe Replay E2E (CLAUDE §19, §20)
    Tạo session cha -> Fork nhánh con -> Kế thừa toàn bộ sự kiện -> Safe Replay không tạo side-effects.
    """
    session_manager = SessionManager(temp_sqlite)

    # 1. Tạo session cha và ghi nhận 2 events
    parent = await session_manager.create_session(
        company_id="comp_123",
        user_id="user_founder",
        profile_id="cmo"
    )
    ev1 = AgentEvent(
        session_id=parent.id,
        type=EventType.USER_MESSAGE,
        actor={"type": "user", "id": "founder"},
        payload={"content": "Event 1"}
    )
    ev2 = AgentEvent(
        session_id=parent.id,
        type=EventType.TOOL_COMPLETED,
        actor={"type": "agent", "id": "cmo"},
        payload={"result": "Data 2", "has_side_effects": True}
    )
    await session_manager.event_store.append(ev1)
    await session_manager.event_store.append(ev2)

    # 2. Fork nhánh con
    child = await session_manager.fork_session(parent_session_id=parent.id, from_event_id=ev2.id)

    child_events = await session_manager.event_store.get_events_by_session(session_id=child.id)
    assert len(child_events) == 3  # session.started, ev1, ev2

    # 3. Safe Replay trên nhánh con
    replay_log = await session_manager.replay_session(session_id=child.id)
    assert len(replay_log) == 3
    assert replay_log[2]["side_effect_prevented"] is True


def test_e2e_clean_architecture_isolation_gate():
    """
    Scenario 6: Clean Architecture & Zero AI Imports Compliance Gate (CLAUDE §1, §14)
    Quét toàn bộ AST của backend/core/ đảm bảo 0% phụ thuộc vào các thư viện AI (openai, anthropic, langchain, deepseek).
    """
    core_dir = "/Volumes/SSD/javis-saas/backend/core"
    forbidden_modules = ["openai", "anthropic", "langchain", "deepseek", "vllm", "google.generativeai"]

    assert os.path.exists(core_dir), "Thư mục backend/core/ không tồn tại"

    for root, _, files in os.walk(core_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=file_path)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            for forbidden in forbidden_modules:
                                assert forbidden not in alias.name, f"Vi phạm kiến trúc: File {file_path} import '{alias.name}'"
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            for forbidden in forbidden_modules:
                                assert forbidden not in node.module, f"Vi phạm kiến trúc: File {file_path} from-import '{node.module}'"
