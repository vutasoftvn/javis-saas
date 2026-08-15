import asyncio
import json
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.governance.models import AgentApproval, AgentRun, AgentToolCall
from app.agents.runtime.adapters.deepseek_harness import DeepSeekHarnessAdapter
from app.agents.runtime.json_output import parse_structured_output, parse_tool_calls
from app.agents.runtime.tool_bridge import dispatch_tool_call
from app.agents.runtime.types import AgentRunRequest
from app.core.feature_flags import FLAG_AGENT_RUNTIME_TOOLS, set_feature_flag
from app.core.snowflake import generate_snowflake_id
from app.core.tool_dispatch import coerce_tool_args, execute_tool_spec
from app.core.tool_registry import register, ToolSpec
from app.db.base_class import Base
from app.modules.iam.models import User, Workspace


@pytest.fixture
def db_session():
    mock_db = MagicMock()
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    
    ws = Workspace(id=ws_id, name="Test WS")
    u = User(id=user_id, email="test@cosa.ai", display_name="cosa_tester")
    
    def mock_query(model):
        q = MagicMock()
        if model == Workspace:
            q.first.return_value = ws
        elif model == User:
            q.first.return_value = u
        elif model == AgentApproval:
            q.filter.return_value.first.return_value = AgentApproval(
                id=generate_snowflake_id(),
                workspace_id=ws_id,
                requested_by_agent="test_agent",
                action_type="tool_execution",
                tool_name="bridge_test.write_critical",
                status="pending",
            )
        return q
    
    mock_db.query.side_effect = mock_query
    return mock_db


def test_json_output_parsing():
    # 1. Clean JSON
    res1 = parse_structured_output('{"key": "value"}')
    assert res1 == {"key": "value"}

    # 2. Markdown fenced block
    res2 = parse_structured_output('Here is the plan:\n```json\n{"diagnosis": "Healthy pipeline"}\n```')
    assert res2 == {"diagnosis": "Healthy pipeline"}

    # 3. Outer bracket extraction
    res3 = parse_structured_output('prefix {"a": 1, "b": [2, 3]} suffix')
    assert res3 == {"a": 1, "b": [2, 3]}

    # 4. Invalid
    assert parse_structured_output('not json at all') is None


def test_parse_tool_calls():
    # Format 1: single tool_call
    t1 = '{"tool_call": {"name": "sales_pipeline_summary", "arguments": {"time_window_days": 30}}}'
    calls1 = parse_tool_calls(t1)
    assert len(calls1) == 1
    assert calls1[0]["name"] == "sales_pipeline_summary"
    assert calls1[0]["arguments"] == {"time_window_days": 30}

    # Format 2: multiple tool_calls
    t2 = '{"tool_calls": [{"name": "finance_summary", "arguments": {}}, {"name": "strategy_list_okrs", "arguments": {"limit": 5}}]}'
    calls2 = parse_tool_calls(t2)
    assert len(calls2) == 2
    assert calls2[1]["name"] == "strategy_list_okrs"

    # Format 3: action format
    t3 = '{"action": "call_tool", "tool": "custom_tool", "args": {"foo": "bar"}}'
    calls3 = parse_tool_calls(t3)
    assert len(calls3) == 1
    assert calls3[0]["name"] == "custom_tool"


def test_tool_dispatch_coercion():
    @register("testdispatch", "sample_tool", risk_level="low")
    def dummy_tool(db, workspace_id: int, lead_id: int, name: str):
        return {"lead_id": lead_id, "name": name}

    from app.core.tool_registry import get_tool_by_flat_name
    spec = get_tool_by_flat_name("testdispatch_sample_tool")
    assert spec is not None

    coerced = coerce_tool_args(spec, {
        "workspace_id": 9999,  # Should be stripped (injected)
        "lead_id": "12345",   # Should be coerced to int
        "name": "Acme Corp",
        "random_extra": "junk",  # Should be dropped
    })
    assert coerced == {"lead_id": 12345, "name": "Acme Corp"}


@pytest.mark.asyncio
async def test_tool_bridge_allow_deny_approval(db_session):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    run_id = generate_snowflake_id()

    # 1. Register test tools
    @register("bridge_test", "read_safe", risk_level="low", permission_level="read_only", allowed_agent_keys=["test_agent"])
    def safe_read_tool(db, workspace_id: int):
        return {"data": "read_success", "workspace_id": workspace_id}

    @register("bridge_test", "write_critical", risk_level="critical", permission_level="admin_write", allowed_agent_keys=["test_agent"])
    def dangerous_write_tool(db, workspace_id: int):
        return {"status": "executed"}

    @register("bridge_test", "unauthorized_agent", risk_level="low", permission_level="read_only", allowed_agent_keys=["other_agent"])
    def restricted_tool(db, workspace_id: int):
        return {"status": "ok"}

    req = AgentRunRequest(
        workspace_id=str(ws_id),
        user_id=str(user_id),
        company_id=str(ws_id),
        agent_key="test_agent",
        task="Testing tool bridge",
        permission_profile="L0_READ",
        parent_run_id=str(run_id),
    )

    # A. ALLOW branch
    res_allow = await dispatch_tool_call(
        db=db_session,
        request=req,
        tool_flat_name="bridge_test_read_safe",
        args={},
        run_id=run_id,
    )
    assert res_allow.get("data") == "read_success"
    assert db_session.add.called
    assert db_session.commit.called

    # B. DENY branch (agent key mismatch)
    res_deny = await dispatch_tool_call(
        db=db_session,
        request=req,
        tool_flat_name="bridge_test_unauthorized_agent",
        args={},
        run_id=run_id,
    )
    assert res_deny.get("status") == "blocked"

    # C. REQUIRE_APPROVAL branch (critical risk)
    res_app = await dispatch_tool_call(
        db=db_session,
        request=req,
        tool_flat_name="bridge_test_write_critical",
        args={"target": "production"},
        run_id=run_id,
    )
    assert res_app.get("status") == "awaiting_approval"
    assert "approval_id" in res_app


@pytest.mark.asyncio
async def test_deepseek_harness_adapter_react_tool_loop(db_session):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    @register("harness_test", "query_sales", risk_level="low", permission_level="read_only", allowed_agent_keys=["sales_agent"])
    def query_sales(db, workspace_id: int):
        return {"pipeline_total": 500000}

    # Mock session & harness
    mock_session = MagicMock()
    # Turn 1 returns tool_call, Turn 2 returns final answer
    mock_run_result_1 = MagicMock(
        session_id="sess_123",
        final_response='{"tool_call": {"name": "harness_test_query_sales", "arguments": {}}}',
        finish_reason="completed",
    )
    mock_run_result_2 = MagicMock(
        session_id="sess_123",
        final_response='{"final": "Pipeline total is $500,000"}',
        finish_reason="completed",
    )
    mock_session.run.side_effect = [mock_run_result_1, mock_run_result_2]

    mock_harness_instance = MagicMock()
    mock_harness_instance.start_session.return_value = mock_session

    adapter = DeepSeekHarnessAdapter(api_key="test-api-key")

    with patch.object(adapter, "_new_harness", return_value=mock_harness_instance), \
         patch("app.agents.runtime.adapters.deepseek_harness.SessionLocal", return_value=db_session):

        req = AgentRunRequest(
            workspace_id=str(ws_id),
            user_id=str(user_id),
            company_id=str(ws_id),
            agent_key="sales_agent",
            task="What is the pipeline total?",
            permission_profile="L0_READ",
            context={"enable_tools": True},
        )

        result = await adapter.run(req)

        assert result.status == "completed"
        assert "Pipeline total is $500,000" in (result.output_text or "")
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["tool"] == "harness_test_query_sales"
        assert result.tool_calls[0]["output"] == {"pipeline_total": 500000}
