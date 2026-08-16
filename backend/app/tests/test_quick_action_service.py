from unittest.mock import MagicMock
import pytest
from app.core.snowflake import generate_snowflake_id
from app.agents.capabilities.quick_action_service import execute_quick_action


def test_execute_quick_action_daily_brief():
    ws_id = generate_snowflake_id()
    db = MagicMock()
    query = MagicMock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.scalar.return_value = 0
    query.all.return_value = []
    query.first.return_value = None
    db.query.return_value = query

    result = execute_quick_action(
        db=db,
        workspace_id=ws_id,
        action_key="daily_brief",
        user_id=123,
    )

    assert result.intent == "daily_brief"
    assert result.capability == "operations.daily_brief"
    assert result.prompt_version == "daily_brief@v1.2.0"
    assert "Tổng Quan Vận Hành Hôm Nay" in result.content_markdown
    assert "CycleRepository" in result.tools_used
    assert len(result.actionable_recommendations) > 0


def test_execute_quick_action_okr_check():
    ws_id = generate_snowflake_id()
    db = MagicMock()
    query = MagicMock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.scalar.return_value = 0
    query.all.return_value = []
    query.first.return_value = None
    db.query.return_value = query

    result = execute_quick_action(
        db=db,
        workspace_id=ws_id,
        action_key="okr_check",
        user_id=123,
    )

    assert result.intent == "okr_health_check"
    assert result.capability == "strategy.okr_review"
    assert result.prompt_version == "okr_progress_review@v1.1.0"
    assert "Tiến Độ OKRs" in result.content_markdown
    assert "OKRRepository" in result.tools_used


def test_execute_quick_action_task_prioritize():
    ws_id = generate_snowflake_id()
    db = MagicMock()
    query = MagicMock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.scalar.return_value = 0
    query.all.return_value = []
    query.first.return_value = None
    db.query.return_value = query

    result = execute_quick_action(
        db=db,
        workspace_id=ws_id,
        action_key="task_prioritize",
        user_id=123,
    )

    assert result.intent == "execution_prioritization"
    assert result.capability == "execution.prioritizer"
    assert result.prompt_version == "execution_prioritize@v1.0.0"
    assert "Nhiệm Vụ Cần Ưu Tiên" in result.content_markdown
    assert "WorkRepository" in result.tools_used
