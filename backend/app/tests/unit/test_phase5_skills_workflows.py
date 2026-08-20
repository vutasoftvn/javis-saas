"""
Unit Tests for Phase 5: Skills Repository, Markdown Instructions & Workflow Engine
Kiểm tra tính toàn vẹn của Dynamic Markdown Loading, Prerequisites Validator, Sequential/Parallel Workflow & Approval Gate.
"""
import pytest
import tempfile
import os
from skills.repository import skill_repository
from workflows.engine import WorkflowEngine
from workflows.definitions import (
    get_market_analysis_workflow,
    get_lead_outreach_workflow,
    get_financial_health_workflow,
    get_staging_deployment_workflow,
)
from storage.sqlite.connection import SQLiteManager
from agent.events.sqlite_event_store import SQLiteEventStore
from agent.events.base import EventType
from tools.dispatcher import ToolDispatcher
from tools.registry import tool_registry


@pytest.fixture
def temp_event_store():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    manager = SQLiteManager(db_path=db_path)
    store = SQLiteEventStore(manager)
    yield store
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.mark.asyncio
async def test_skills_repository_and_markdown_loading():
    """Kiểm tra nạp 6 Skills và đọc nội dung hướng dẫn từ các tệp Markdown"""
    skills = skill_repository.list_skills()
    assert len(skills) >= 6

    # Kiểm tra nạp markdown của skill market-research
    mr_skill = skill_repository.get("market-research")
    assert mr_skill is not None
    instructions = await mr_skill.load_instructions()
    assert "TAM / SAM / SOM" in instructions
    assert len(instructions) > 100

    # Kiểm tra skill tt58-audit
    tt58_skill = skill_repository.get("tt58-audit")
    assert tt58_skill is not None
    tt58_inst = await tt58_skill.load_instructions()
    assert "Thông tư 58" in tt58_inst


def test_skills_prerequisites_validation():
    """Kiểm tra xác thực điều kiện tiên quyết (Prerequisites) của Skill"""
    # 1. Có đủ web.search, web.fetch -> market-research hợp lệ
    valid = skill_repository.validate_prerequisites("market-research", ["web.search", "web.fetch", "other.tool"])
    assert valid is True

    # 2. Thiếu web.fetch -> market-research không hợp lệ
    invalid = skill_repository.validate_prerequisites("market-research", ["web.search"])
    assert invalid is False


@pytest.mark.asyncio
async def test_workflow_sequential_and_parallel_execution(temp_event_store):
    """Kiểm tra WorkflowEngine chạy quy trình tuần tự kết hợp chạy song song (Parallel Tools)"""
    dispatcher = ToolDispatcher(registry=tool_registry, event_store=temp_event_store)
    engine = WorkflowEngine(tool_dispatcher=dispatcher, skills_repo=skill_repository, event_store=temp_event_store)
    session_id = "ses_wf_market_01"

    wf = get_market_analysis_workflow()
    res = await engine.execute_workflow(
        workflow=wf,
        initial_context={"user_query": "Nghiên cứu thị trường AI Agents"},
        session_id=session_id
    )

    assert res["status"] == "completed"
    assert len(res["executed_steps"]) == 3
    # Kiểm tra context tích lũy sau các bước
    assert "skill_market-research" in res["context"]
    assert "tool_web.search" in res["context"]
    assert "tool_web.fetch" in res["context"]
    assert "tool_filesystem.write" in res["context"]


@pytest.mark.asyncio
async def test_workflow_human_approval_pause_and_resume(temp_event_store):
    """Kiểm tra Workflow dừng lại an toàn ở bước HUMAN_APPROVAL và Resume chạy tiếp sau khi duyệt"""
    dispatcher = ToolDispatcher(registry=tool_registry, event_store=temp_event_store)
    engine = WorkflowEngine(tool_dispatcher=dispatcher, skills_repo=skill_repository, event_store=temp_event_store)
    session_id = "ses_wf_deploy_01"

    wf = get_staging_deployment_workflow()

    # 1. Chạy lần đầu -> Dừng lại ở bước step_approval (bước 2)
    res_paused = await engine.execute_workflow(
        workflow=wf,
        initial_context={},
        session_id=session_id
    )
    assert res_paused["status"] == "paused_waiting_approval"
    assert res_paused["waiting_step_id"] == "step_approval"
    assert "step_read_config" in res_paused["executed_steps"]

    # 2. Resume sau khi Founder duyệt -> Chạy tiếp bước 3 (step_deploy)
    res_resumed = await engine.execute_workflow(
        workflow=wf,
        initial_context=res_paused["context"],
        session_id=session_id,
        approved_step_id="step_approval"
    )
    assert res_resumed["status"] == "completed"
    assert "step_deploy" in res_resumed["executed_steps"]


@pytest.mark.asyncio
async def test_workflow_event_logging(temp_event_store):
    """Kiểm tra quy trình Workflow ghi nhật ký sự kiện tự động vào SQLite Event Store"""
    dispatcher = ToolDispatcher(registry=tool_registry, event_store=temp_event_store)
    engine = WorkflowEngine(tool_dispatcher=dispatcher, skills_repo=skill_repository, event_store=temp_event_store)
    session_id = "ses_wf_events_01"

    wf = get_financial_health_workflow()
    await engine.execute_workflow(
        workflow=wf,
        initial_context={},
        session_id=session_id
    )

    events = await temp_event_store.get_events_by_session(session_id)
    event_types = [e.type for e in events]

    assert EventType.WORKFLOW_STARTED in event_types
    assert EventType.SKILL_LOADED in event_types
    assert EventType.TOOL_COMPLETED in event_types
    assert EventType.WORKFLOW_STEP_COMPLETED in event_types
