import pytest
from unittest.mock import AsyncMock, MagicMock

from app.workforce.identity.context import ExecutionContext
from app.workforce.models import ToolDefinition, AgentDefinition, AgentToolPermission
from app.workforce.gateway.policy import RiskLevel, RiskPolicyEvaluator
from app.workforce.gateway.gateway import AgentGateway, PermissionDeniedError, ApprovalRequiredError
from app.workforce.registry.tool_registry import ToolRegistryService
from app.workforce.registry.agent_registry import AgentRegistryService
from app.workforce.routing.deterministic import deterministic_intent, Intent
from app.workforce.routing.router import IntentRouter


class TestDeterministicRouting:
    """Kiểm thử router tất định ngăn chặn lỗi 'Chào -> Phân tích Project'."""

    @pytest.mark.parametrize("msg", [
        "chào",
        "Chào",
        "xin chào",
        "Chào bạn!",
        "hello",
        "Hello COSA?",
        "hi",
        "cảm ơn",
        "thanks!",
    ])
    def test_greeting_resolves_to_general_chat(self, msg: str):
        intent = deterministic_intent(msg)
        assert intent == Intent.GENERAL_CHAT

    @pytest.mark.parametrize("msg,expected_agent", [
        ("Kiểm tra doanh số tháng này và danh sách lead mới", "sales"),
        ("Báo cáo dòng tiền và chi phí quý 3", "finance"),
        ("Tạo chiến dịch marketing quảng cáo sản phẩm mới", "marketing"),
        ("Fix lỗi bug trong github repo và chạy sandbox", "developer"),
    ])
    @pytest.mark.asyncio
    async def test_intent_router_domains(self, msg: str, expected_agent: str):
        decision = await IntentRouter.route_message(msg)
        assert decision.target_agent_key == expected_agent


class TestRiskPolicyEvaluator:
    """Kiểm thử chuẩn hóa phân tầng rủi ro R0 - R4."""

    def test_r0_r1_is_auto_allowed(self):
        res_r0 = RiskPolicyEvaluator.evaluate(tool_risk_level=0)
        assert res_r0.allowed is True
        assert res_r0.requires_approval is False

        res_r1 = RiskPolicyEvaluator.evaluate(tool_risk_level=1)
        assert res_r1.allowed is True
        assert res_r1.requires_approval is False

    def test_r3_r4_requires_approval(self):
        res_r3 = RiskPolicyEvaluator.evaluate(tool_risk_level=3)
        assert res_r3.requires_approval is True

        res_r4 = RiskPolicyEvaluator.evaluate(tool_risk_level=4)
        assert res_r4.requires_approval is True


class TestAgentGateway:
    """Kiểm thử AgentGateway kiểm soát quyền hạn và human approval."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def context(self):
        return ExecutionContext(
            workspace_id=1001,
            user_id=2001,
            session_id=3001,
            agent_id=4001,
            agent_key="sales",
        )

    @pytest.mark.asyncio
    async def test_gateway_executes_safe_tool(self, mock_db, context):
        tool_reg = AsyncMock(spec=ToolRegistryService)
        tool_reg.get_tool_by_key.return_value = ToolDefinition(
            id=1, key="crm.search", name="CRM Search", risk_level=0, requires_approval=False
        )

        mock_res = MagicMock()
        mock_res.scalars.return_value.first.return_value = None  # No explicit deny
        mock_db.execute.return_value = mock_res

        gateway = AgentGateway(db=mock_db, tool_registry=tool_reg)
        gateway.register_handler("crm.search", lambda ctx, args: {"leads": ["lead1", "lead2"]})

        result = await gateway.execute(context, "crm.search", {"query": "tech"})
        assert result == {"leads": ["lead1", "lead2"]}

    @pytest.mark.asyncio
    async def test_gateway_pauses_for_r3_approval(self, mock_db, context):
        tool_reg = AsyncMock(spec=ToolRegistryService)
        tool_reg.get_tool_by_key.return_value = ToolDefinition(
            id=2, key="email.send", name="Send Email", risk_level=3, requires_approval=True
        )

        mock_res = MagicMock()
        mock_res.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_res

        gateway = AgentGateway(db=mock_db, tool_registry=tool_reg)

        with pytest.raises(ApprovalRequiredError) as exc_info:
            await gateway.execute(context, "email.send", {"to": "client@example.com"})

        assert exc_info.value.ticket.tool_key == "email.send"
        assert exc_info.value.ticket.risk_level == 3

    @pytest.mark.asyncio
    async def test_gateway_denies_unauthorized_permission(self, mock_db, context):
        tool_reg = AsyncMock(spec=ToolRegistryService)
        tool_reg.get_tool_by_key.return_value = ToolDefinition(
            id=3, key="finance.post_entry", name="Finance Post", risk_level=4
        )

        perm = AgentToolPermission(
            id=99, agent_id=context.agent_id, tool_id=3, allow_execute=False
        )
        mock_res = MagicMock()
        mock_res.scalars.return_value.first.return_value = perm
        mock_db.execute.return_value = mock_res

        gateway = AgentGateway(db=mock_db, tool_registry=tool_reg)

        with pytest.raises(PermissionDeniedError):
            await gateway.execute(context, "finance.post_entry", {"amount": 5000})

    @pytest.mark.asyncio
    async def test_gateway_routes_to_mcp_adapter(self, mock_db, context):
        tool_reg = AsyncMock(spec=ToolRegistryService)
        tool_reg.get_tool_by_key.return_value = ToolDefinition(
            id=4, key="mcp.github_search", name="MCP GitHub", transport="mcp", risk_level=0
        )
        mock_res = MagicMock()
        mock_res.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_res

        gateway = AgentGateway(db=mock_db, tool_registry=tool_reg)
        result = await gateway.execute(context, "mcp.github_search", {"repo": "cosa"})
        assert result["transport"] == "mcp"
        assert result["status"] in ("success", "fallback")

    @pytest.mark.asyncio
    async def test_gateway_routes_to_n8n_adapter(self, mock_db, context):
        tool_reg = AsyncMock(spec=ToolRegistryService)
        tool_reg.get_tool_by_key.return_value = ToolDefinition(
            id=5, key="n8n.schedule_timer", name="n8n Timer", transport="n8n", risk_level=2, requires_approval=False
        )
        mock_res = MagicMock()
        mock_res.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_res

        gateway = AgentGateway(db=mock_db, tool_registry=tool_reg)
        result = await gateway.execute(context, "n8n.schedule_timer", {"delay_days": 3})
        assert result["transport"] == "n8n"
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_gateway_routes_to_sandbox_adapter(self, mock_db, context):
        tool_reg = AsyncMock(spec=ToolRegistryService)
        tool_reg.get_tool_by_key.return_value = ToolDefinition(
            id=6, key="sandbox.execute", name="Sandbox Execute", transport="sandbox", risk_level=2, requires_approval=False
        )
        mock_res = MagicMock()
        mock_res.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_res

        gateway = AgentGateway(db=mock_db, tool_registry=tool_reg)
        result = await gateway.execute(context, "sandbox.execute", {"command": "pytest"})
        assert result["transport"] == "sandbox"
        assert result["exit_code"] == 0

    @pytest.mark.asyncio
    async def test_auto_register_domain_tools_executes_finance_and_crm(self, mock_db, context):
        from app.workforce.tools.auto_register import register_all_domain_tools

        tool_reg = AsyncMock(spec=ToolRegistryService)
        tool_reg.get_tool_by_key.return_value = ToolDefinition(
            id=10, key="finance.read_summary", name="Finance Summary", risk_level=0, requires_approval=False
        )
        mock_res = MagicMock()
        mock_res.scalars.return_value.first.return_value = None
        mock_res.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_res

        gateway = AgentGateway(db=mock_db, tool_registry=tool_reg)
        register_all_domain_tools(gateway, mock_db)

        # Execute finance.read_summary through registered handler
        result = await gateway.execute(context, "finance.read_summary", {})
        assert result["status"] in ("success", "empty")
        assert "workspace_id" in result

        # Execute marketing.content.generate
        tool_reg.get_tool_by_key.return_value = ToolDefinition(
            id=11, key="marketing.content.generate", name="Marketing Gen", risk_level=1, requires_approval=False
        )
        res_mkt = await gateway.execute(context, "marketing.content.generate", {"topic": "AI OS"})
        assert res_mkt["status"] == "success"
        assert "generated_content" in res_mkt

        # Execute developer.build_spec.create
        tool_reg.get_tool_by_key.return_value = ToolDefinition(
            id=12, key="developer.build_spec.create", name="Build Spec", risk_level=2, requires_approval=False
        )
        res_dev = await gateway.execute(context, "developer.build_spec.create", {"task_id": "DEV-200"})
        assert res_dev["status"] == "success"
        assert res_dev["task_id"] == "DEV-200"

        # Execute legal.compliance.check
        tool_reg.get_tool_by_key.return_value = ToolDefinition(
            id=13, key="legal.compliance.check", name="Legal Check", risk_level=1, requires_approval=False
        )
        res_legal = await gateway.execute(context, "legal.compliance.check", {})
        assert res_legal["status"] == "success"
        assert "total_checks" in res_legal

        # Execute policy.eligibility.eval
        tool_reg.get_tool_by_key.return_value = ToolDefinition(
            id=14, key="policy.eligibility.eval", name="Policy Eval", risk_level=1, requires_approval=False
        )
        res_pol = await gateway.execute(context, "policy.eligibility.eval", {"program_id": "SME-2026"})
        assert res_pol["status"] == "success"
        assert res_pol["eligible"] is True
