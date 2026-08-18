import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.workforce.agents.governance.budget import BudgetCheckResult
from app.workforce.agents.governance.models import AgentApproval, AgentRun, AgentToolCall
from app.workforce.agents.governance.stuck_detector import StuckAnalysisResult
from app.workforce.agents.runtime.adapters.deepseek_harness import DeepSeekHarnessAdapter
from app.workforce.agents.runtime.json_output import parse_structured_output, parse_tool_calls
from app.workforce.agents.runtime.tool_bridge import dispatch_tool_call
from app.workforce.agents.runtime.types import AgentRunRequest
from app.core.feature_flags import FLAG_AGENT_RUNTIME_TOOLS, set_feature_flag
from app.core.snowflake import generate_snowflake_id
from app.core.tool_dispatch import coerce_tool_args, execute_tool_spec
from app.core.tool_registry import register, ToolSpec
from app.db.base_class import Base
from app.platform.auth.models import User, Workspace


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
    mock_db.get.return_value = None  # forces the adapter to create a fresh AgentRun row
    mock_db.execute.return_value.scalar.return_value = 0
    mock_db.execute.return_value.scalars.return_value.all.return_value = []
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
         patch("app.workforce.agents.runtime.adapters.deepseek_harness.SessionLocal", return_value=db_session):

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

        # FK-safety: dispatch_tool_call must be given a run_id backed by a real AgentRun
        # row (created here since the request carried no parent_run_id), never the
        # adapter's disconnected internal trace id.
        assert db_session.get.called
        created_runs = [c.args[0] for c in db_session.add.call_args_list if isinstance(c.args[0], AgentRun)]
        assert len(created_runs) == 1
        assert created_runs[0].id == int(result.run_id)


@pytest.mark.asyncio
async def test_deepseek_harness_tool_loop_reuses_parent_run_id_for_fk_safety(db_session):
    """chief_of_staff.py already inserts an AgentRun keyed by mission_id and passes it as
    parent_run_id - the adapter must dispatch tools under that same id, not mint a new one,
    or AgentToolCall.run_id would point at a row that was never created."""
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()
    mission_id = generate_snowflake_id()

    @register("harness_test2", "noop", risk_level="low", permission_level="read_only", allowed_agent_keys=["sales_agent"])
    def noop_tool(db, workspace_id: int):
        return {"ok": True}

    mock_session = MagicMock()
    mock_session.run.side_effect = [
        MagicMock(session_id="s1", final_response='{"tool_call": {"name": "harness_test2_noop", "arguments": {}}}', finish_reason="completed"),
        MagicMock(session_id="s1", final_response='{"final": "done"}', finish_reason="completed"),
    ]
    mock_harness_instance = MagicMock()
    mock_harness_instance.start_session.return_value = mock_session

    # Simulate the AgentRun already inserted by chief_of_staff.py in another session.
    existing_run = AgentRun(
        id=mission_id, workspace_id=ws_id, user_id=user_id, agent_key="sales_agent",
        runtime="pending", status="running", permission_profile="L0_READ",
        started_at=datetime.now(timezone.utc),
    )
    db_session.get.return_value = existing_run

    adapter = DeepSeekHarnessAdapter(api_key="test-api-key")
    with patch.object(adapter, "_new_harness", return_value=mock_harness_instance), \
         patch("app.workforce.agents.runtime.adapters.deepseek_harness.SessionLocal", return_value=db_session):
        req = AgentRunRequest(
            workspace_id=str(ws_id), user_id=str(user_id), company_id=str(ws_id),
            agent_key="sales_agent", task="do the thing", permission_profile="L0_READ",
            context={"enable_tools": True}, parent_run_id=str(mission_id),
        )
        result = await adapter.run(req)

    assert result.status == "completed"
    # No second AgentRun should have been created - the existing one was reused.
    created_runs = [c.args[0] for c in db_session.add.call_args_list if isinstance(c.args[0], AgentRun)]
    assert created_runs == []


@pytest.mark.asyncio
async def test_deepseek_harness_tool_loop_aborts_when_budget_exceeded(db_session):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    mock_session = MagicMock()
    mock_harness_instance = MagicMock()
    mock_harness_instance.start_session.return_value = mock_session

    adapter = DeepSeekHarnessAdapter(api_key="test-api-key")
    exceeded = BudgetCheckResult(is_exceeded=True, reason_code="COST_EXCEEDED", message="API cost limit exceeded")

    with patch.object(adapter, "_new_harness", return_value=mock_harness_instance), \
         patch("app.workforce.agents.runtime.adapters.deepseek_harness.SessionLocal", return_value=db_session), \
         patch("app.workforce.agents.runtime.adapters.deepseek_harness.BudgetTracker.check", return_value=exceeded):
        req = AgentRunRequest(
            workspace_id=str(ws_id), user_id=str(user_id), company_id=str(ws_id),
            agent_key="sales_agent", task="do a lot of things", permission_profile="L0_READ",
            context={"enable_tools": True},
        )
        result = await adapter.run(req)

    assert result.status == "failed"
    assert result.structured_output["reason_code"] == "COST_EXCEEDED"
    mock_session.run.assert_not_called()


@pytest.mark.asyncio
async def test_deepseek_harness_tool_loop_aborts_when_stuck(db_session):
    ws_id = generate_snowflake_id()
    user_id = generate_snowflake_id()

    mock_session = MagicMock()
    mock_harness_instance = MagicMock()
    mock_harness_instance.start_session.return_value = mock_session

    adapter = DeepSeekHarnessAdapter(api_key="test-api-key")
    stuck = StuckAnalysisResult(
        is_stuck=True, loop_type="SAME_ACTION_LOOP", repeated_count=5,
        suggested_action="ABORT_RUN", detail="Identical action executed 5 times.",
    )

    with patch.object(adapter, "_new_harness", return_value=mock_harness_instance), \
         patch("app.workforce.agents.runtime.adapters.deepseek_harness.SessionLocal", return_value=db_session), \
         patch("app.workforce.agents.runtime.adapters.deepseek_harness.StuckDetector.analyze_run", return_value=stuck):
        req = AgentRunRequest(
            workspace_id=str(ws_id), user_id=str(user_id), company_id=str(ws_id),
            agent_key="sales_agent", task="loop forever", permission_profile="L0_READ",
            context={"enable_tools": True},
        )
        result = await adapter.run(req)

    assert result.status == "failed"
    assert result.structured_output["finish_reason"] == "stuck_loop"
    mock_session.run.assert_not_called()
