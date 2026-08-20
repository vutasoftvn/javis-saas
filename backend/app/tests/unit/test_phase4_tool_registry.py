"""
Unit Tests for Phase 4: Tool Registry, Capabilities, Risk Interceptor & Presenters
Kiểm tra tính toàn vẹn của Central Tool Registry, ToolDispatcher, Event Logging, Approval Gate và Presenters.
"""
import pytest
import tempfile
import os
from tools.registry import tool_registry, ToolRegistry
from tools.dispatcher import ToolDispatcher
from tools.base import RiskLevel
from storage.sqlite.connection import SQLiteManager
from agent.events.sqlite_event_store import SQLiteEventStore
from agent.events.base import EventType


@pytest.fixture
def temp_event_store():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    manager = SQLiteManager(db_path=db_path)
    store = SQLiteEventStore(manager)
    yield store
    if os.path.exists(db_path):
        os.remove(db_path)


def test_tool_registry_lookup_and_domains():
    """Kiểm tra tra cứu tool theo ID và lọc theo Domain"""
    # Tra cứu tool cụ thể
    web_tool = tool_registry.get("web.search")
    assert web_tool is not None
    assert web_tool.risk_level == RiskLevel.LOW

    # Lọc tools theo domain
    crm_tools = tool_registry.list_tools(domain="crm")
    assert len(crm_tools) >= 2
    tool_ids = [t.id for t in crm_tools]
    assert "crm.search_leads" in tool_ids
    assert "crm.create_lead" in tool_ids


def test_tool_schema_export_for_llm_function_calling():
    """Kiểm tra xuất JSON Schema chuẩn cho LLM Function Calling"""
    schemas = tool_registry.export_schemas_for_model(allowed_tool_ids=["web.search", "finance.query_pnl"])
    assert len(schemas) == 2
    assert schemas[0]["type"] == "function"
    assert schemas[0]["function"]["name"] == "web.search"
    assert "query" in schemas[0]["function"]["parameters"]["properties"]


@pytest.mark.asyncio
async def test_tool_dispatcher_execution_and_auto_events(temp_event_store):
    """Kiểm tra ToolDispatcher thực thi tool LOW risk và tự động ghi log sự kiện"""
    dispatcher = ToolDispatcher(registry=tool_registry, event_store=temp_event_store)
    session_id = "ses_tool_test_01"

    result = await dispatcher.dispatch(
        tool_id="finance.query_pnl",
        input_data={"quarter": "Q1-2026"},
        context={},
        session_id=session_id
    )

    assert result.status == "success"
    assert result.data["gross_profit"] == 200000000
    assert result.presenter_payload is not None
    assert result.presenter_payload["view_type"] == "pnl_statement_card"
    assert "duration_ms" in result.metadata

    # Kiểm tra 2 sự kiện: tool.requested và tool.completed được ghi vào Event Store
    events = await temp_event_store.get_events_by_session(session_id)
    assert len(events) == 2
    assert events[0].type == EventType.TOOL_REQUESTED
    assert events[1].type == EventType.TOOL_COMPLETED


@pytest.mark.asyncio
async def test_high_risk_tool_approval_gate(temp_event_store):
    """
    Kiểm tra chốt chặn an toàn (Approval Interceptor):
    Tool HIGH/CRITICAL risk không được chạy tự động nếu chưa có approved_by.
    """
    dispatcher = ToolDispatcher(registry=tool_registry, event_store=temp_event_store)
    session_id = "ses_approval_test_01"

    # 1. Thử chạy lệnh Shell (Risk: HIGH) mà không có approval -> pending_approval
    res_shell = await dispatcher.dispatch(
        tool_id="shell.execute",
        input_data={"command": "rm -rf /tmp/old_data"},
        context={},
        session_id=session_id
    )
    assert res_shell.status == "pending_approval"
    assert res_shell.metadata["risk_level"] == "HIGH"
    assert res_shell.presenter_payload["view_type"] == "approval_request_card"

    # Kiểm tra event approval.requested được ghi nhận
    events = await temp_event_store.get_events_by_session(session_id)
    assert len(events) == 1
    assert events[0].type == EventType.APPROVAL_REQUESTED

    # 2. Chạy lại khi đã có Founder duyệt (approved_by="founder") -> Thành công
    res_approved = await dispatcher.dispatch(
        tool_id="shell.execute",
        input_data={"command": "ls -la"},
        context={},
        session_id=session_id,
        approved_by="founder"
    )
    assert res_approved.status == "success"
    assert res_approved.data["exit_code"] == 0


def test_tool_presenters_formatting():
    """Kiểm tra toàn bộ Tools sinh Presenter Payload chuẩn cho Hologram Hub UI"""
    for tool in tool_registry.list_tools():
        payload = tool.format_presenter({"status": "ok"})
        assert "title" in payload
        assert "summary" in payload
