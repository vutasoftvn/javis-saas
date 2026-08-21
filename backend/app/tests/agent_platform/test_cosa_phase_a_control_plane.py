import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.workforce.models import AgentDefinition, AgentHierarchy, LegacyPlatformAgentRun, AgentStep, AgentBudget
from app.workforce.registry.agent_registry import AgentRegistryService
from app.workforce.registry.defaults import DEFAULT_AGENT_MANIFESTS
from app.workforce.adapters.base import (
    BaseRuntimeAdapter, ExecutionPayload, ExecutionResult, TokenUsage, Message, ModelRole
)
from app.workforce.adapters.claude_adapter import ClaudeCodeAdapter
from app.workforce.adapters.gemini_adapter import GeminiAdapter
from app.workforce.adapters.deepseek_adapter import DeepSeekAdapter
from app.workforce.adapters.http_generic_adapter import GenericHttpAdapter
from app.workforce.adapters.factory import RuntimeAdapterFactory
from app.workforce.dispatcher.context_builder import AgentContextBuilder
from app.workforce.dispatcher.runner import AgentRunnerService
from app.workforce.dispatcher.task_dispatcher import AgentTaskDispatcher
from app.founder_os.tasks.models import Task


class TestCosaPhaseAAdapters:
    """Kiểm thử Runtime Adapter Layer đa nhà cung cấp (Model Agnostic)."""

    @pytest.mark.asyncio
    async def test_runtime_adapter_factory_resolution(self):
        adapter_claude = RuntimeAdapterFactory.get_adapter(provider="claude")
        assert isinstance(adapter_claude, ClaudeCodeAdapter)

        adapter_gemini = RuntimeAdapterFactory.get_adapter(provider="gemini")
        assert isinstance(adapter_gemini, GeminiAdapter)

        adapter_deepseek = RuntimeAdapterFactory.get_adapter(provider="deepseek")
        assert isinstance(adapter_deepseek, DeepSeekAdapter)

        adapter_local = RuntimeAdapterFactory.get_adapter(provider="http")
        assert isinstance(adapter_local, GenericHttpAdapter)

        # Test model profile mapping
        fast_adapter = RuntimeAdapterFactory.get_adapter(model_profile="fast")
        assert isinstance(fast_adapter, GeminiAdapter)

    @pytest.mark.asyncio
    async def test_mock_claude_execution(self):
        adapter = ClaudeCodeAdapter(api_key=None)
        payload = ExecutionPayload(
            trace_id="trace_test_01",
            agent_key="cfo_agent",
            model_name="claude-3-5-sonnet-20241022",
            messages=[
                Message(role=ModelRole.SYSTEM, content="System prompt"),
                Message(role=ModelRole.USER, content="Analyze cashflow Q3"),
            ]
        )
        res = await adapter.execute(payload)
        assert res.trace_id == "trace_test_01"
        assert "[Claude Mock Response for cfo_agent]" in res.content
        assert res.usage.prompt_tokens > 0
        assert res.usage.cost_usd > 0.0

    @pytest.mark.asyncio
    async def test_mock_gemini_execution(self):
        adapter = GeminiAdapter(api_key=None)
        payload = ExecutionPayload(
            trace_id="trace_test_02",
            agent_key="founder_copilot",
            model_name="gemini-2.0-flash",
            messages=[
                Message(role=ModelRole.SYSTEM, content="System prompt"),
                Message(role=ModelRole.USER, content="Review 12WY objectives"),
            ]
        )
        res = await adapter.execute(payload)
        assert res.trace_id == "trace_test_02"
        assert "[Gemini Mock Response for founder_copilot]" in res.content
        assert res.usage.total_tokens > 0

    @pytest.mark.asyncio
    async def test_mock_deepseek_execution(self):
        adapter = DeepSeekAdapter(api_key=None)
        payload = ExecutionPayload(
            trace_id="trace_test_03",
            agent_key="tech_lead_agent",
            model_name="deepseek-reasoner",
            messages=[
                Message(role=ModelRole.SYSTEM, content="System prompt"),
                Message(role=ModelRole.USER, content="Evaluate Tech Radar P0-P5"),
            ]
        )
        res = await adapter.execute(payload)
        assert res.trace_id == "trace_test_03"
        assert "[DeepSeek Mock Response for tech_lead_agent]" in res.content
        assert res.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_adapter_capabilities_and_health(self):
        adapter_claude = ClaudeCodeAdapter(api_key=None)
        cap = await adapter_claude.check_capability()
        health = await adapter_claude.health()
        assert cap["runtime"] == "claude_code"
        assert cap["installed"] is True
        assert health["adapter"] == "ClaudeCodeAdapter"

        adapter_deepseek = DeepSeekAdapter(api_key="test_key")
        cap_ds = await adapter_deepseek.check_capability()
        assert cap_ds["runtime"] == "deepseek"
        assert cap_ds["authenticated"] is True

    @pytest.mark.asyncio
    async def test_runtime_fallback_chain(self):
        fallback_chain = RuntimeAdapterFactory.get_fallback_chain("claude")
        assert "deepseek" in fallback_chain
        assert "gemini" in fallback_chain
        assert "http" in fallback_chain

        resolved = await RuntimeAdapterFactory.resolve_adapter_with_fallback(primary_provider="claude")
        assert isinstance(resolved, ClaudeCodeAdapter)



class TestAgentRegistryAndOrgChart:
    """Kiểm thử Agent Registry và cấu trúc Org Chart phân cấp."""

    @pytest.mark.asyncio
    async def test_seed_manifest_contains_core_12_agents(self):
        keys = [m["key"] for m in DEFAULT_AGENT_MANIFESTS]
        expected_core = [
            "founder_copilot", "cfo_agent", "cmo_agent", "sales_agent",
            "tech_lead_agent", "devops_agent", "legal_agent", "hr_agent",
            "product_agent", "data_analyst_agent", "researcher_agent", "operations_agent"
        ]
        for exp in expected_core:
            assert exp in keys, f"Expected agent '{exp}' missing in defaults manifest"

    @pytest.mark.asyncio
    async def test_agent_registration_and_status(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = None
        mock_db.execute.return_value = mock_result

        service = AgentRegistryService(mock_db)
        agent = await service.register_agent(
            key="cfo_agent",
            name="CFO Agent",
            role_title="Chief Financial Officer",
            department="Finance",
            agent_type="specialist",
            default_model_profile="reasoning",
            system_prompt_key="finance.system",
            risk_level=2,
            workspace_id=1001,
        )

        assert agent.key == "cfo_agent"
        assert agent.department == "Finance"
        assert agent.status == "idle"
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_agent_persists_profile_slug(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = None
        mock_db.execute.return_value = mock_result

        service = AgentRegistryService(mock_db)
        agent = await service.register_agent(
            key="finance_agent_test",
            name="Finance Agent",
            profile_slug="finance",
            workspace_id=None,
        )

        assert agent.profile_slug == "finance"


class TestAgentRunnerAndTaskDispatcher:
    """Kiểm thử Dispatcher và Runner kết nối chu trình Task -> Execution -> Audit."""

    @pytest.mark.asyncio
    async def test_agent_runner_lifecycle(self):
        mock_db = AsyncMock()
        agent = AgentDefinition(
            id=12345,
            key="cfo_agent",
            name="CFO Agent",
            default_model_profile="reasoning",
            system_prompt_key="finance.system",
            status="idle",
            workspace_id=1,
            model_config_jsonb={},
        )

        payload = ExecutionPayload(
            trace_id="trace_runner_01",
            agent_key="cfo_agent",
            model_name="claude-3-5-sonnet-20241022",
            messages=[
                Message(role=ModelRole.SYSTEM, content="System prompt"),
                Message(role=ModelRole.USER, content="Analyze cashflow"),
            ]
        )

        runner = AgentRunnerService(mock_db)
        res = await runner.execute_run(payload, agent, task_id=999, workspace_id=1)

        assert res.trace_id == "trace_runner_01"
        assert agent.status == "idle"  # Reset back to idle after completion
        # Verify AgentRun and AgentStep were added
        assert mock_db.add.call_count >= 2

    @pytest.mark.asyncio
    async def test_task_dispatcher_flow(self):
        mock_db = AsyncMock()
        mock_task = Task(
            id=777,
            workspace_id=1,
            title="Dự báo chi phí hoạt động tháng 9",
            status="todo",
            priority="high",
            source="cfo_agent",
        )
        agent = AgentDefinition(
            id=12345,
            key="cfo_agent",
            name="CFO Agent",
            default_model_profile="reasoning",
            system_prompt_key="finance.system",
            status="idle",
            workspace_id=1,
            model_config_jsonb={},
        )

        mock_budget = AgentBudget(
            agent_key="cfo_agent",
            limit_usd=50.0,
            spent_usd=0.0,
            soft_limit_percent=0.8,
            is_blocked=False,
        )

        # Mock query return for task, agent, budget, and prompt
        def execute_side_effect(stmt):
            res_mock = MagicMock()
            stmt_str = str(stmt)
            if "tasks" in stmt_str:
                res_mock.scalars().first.return_value = mock_task
            elif "agent_definitions" in stmt_str:
                res_mock.scalars().first.return_value = agent
            elif "agent_budgets" in stmt_str:
                res_mock.scalars().first.return_value = mock_budget
            else:
                res_mock.scalars().first.return_value = None
            return res_mock

        mock_db.execute.side_effect = execute_side_effect

        dispatcher = AgentTaskDispatcher(mock_db)
        with patch.object(dispatcher.runner, "execute_run", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ExecutionResult(
                trace_id="trace_disp_01",
                content="Báo cáo phân tích chi phí tháng 9 đã hoàn thành.",
                usage=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150, cost_usd=0.001),
                latency_ms=120,
            )

            result = await dispatcher.dispatch_task(task_id=777, agent_key="cfo_agent")

            assert result["status"] == "completed"
            assert mock_task.status == "done"
            assert "Báo cáo phân tích chi phí" in result["full_content"]
