import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from workforce.models import UnifiedPermission, ApprovalRequest, AgentBudget, CostLedger, AgentDefinition
from workforce.governance.permission_engine import UnifiedPermissionEngine
from workforce.governance.risk_evaluator import RiskPolicyEvaluator, RiskTier
from workforce.governance.approval_service import ApprovalInboxService
from workforce.governance.budget_service import BudgetingEngine, BudgetExceededError
from workforce.governance.cost_ledger_service import CostLedgerService, USD_TO_VND_RATE
from workforce.dispatcher.task_dispatcher import AgentTaskDispatcher
from workforce.adapters.base import ExecutionResult, TokenUsage
from founder_os.tasks.models import Task


class TestUnifiedPermissionEngine:
    """Kiểm thử engine phân quyền hợp nhất cho cả Human và Agent."""

    @pytest.mark.asyncio
    async def test_grant_and_verify_permission(self):
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars().first.return_value = None
        mock_db.execute.return_value = mock_result

        engine = UnifiedPermissionEngine(mock_db)

        # 1. Grant permission
        perm = await engine.grant_permission(
            principal_type="AGENT",
            principal_id=101,
            resource_type="TOOL",
            resource_key="crm.update",
            action="EXECUTE",
            is_allowed=True,
            workspace_id=1,
        )
        assert perm.principal_type == "AGENT"
        assert perm.resource_key == "crm.update"
        assert perm.is_allowed is True
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_can_evaluates_explicit_and_default_safe_actions(self):
        mock_db = AsyncMock()

        # Case 1: DB has explicit allowed permission
        mock_perm = UnifiedPermission(
            principal_type="AGENT",
            principal_id=101,
            resource_type="TOOL",
            resource_key="crm.update",
            action="EXECUTE",
            is_allowed=True,
        )
        mock_res1 = MagicMock()
        mock_res1.scalars().first.return_value = mock_perm
        mock_db.execute.return_value = mock_res1

        engine = UnifiedPermissionEngine(mock_db)
        can_exec = await engine.can(
            principal_type="AGENT",
            principal_id=101,
            resource_type="TOOL",
            resource_key="crm.update",
            action="EXECUTE",
        )
        assert can_exec is True

        # Case 2: Safe read without explicit DB record -> defaults to True
        mock_res2 = MagicMock()
        mock_res2.scalars().first.return_value = None
        mock_db.execute.return_value = mock_res2

        can_read = await engine.can(
            principal_type="USER",
            principal_id=999,
            resource_type="TOOL",
            resource_key="knowledge.search",
            action="READ",
        )
        assert can_read is True


class TestRiskPolicyEvaluator3Tiers:
    """Kiểm thử ma trận đánh giá rủi ro 3 cấp (LOW, HIGH, CRITICAL)."""

    def test_low_risk_actions(self):
        eval_read = RiskPolicyEvaluator.evaluate(tool_key="knowledge.search", risk_level_int=0)
        assert eval_read.tier == RiskTier.LOW
        assert eval_read.requires_approval is False

    def test_high_risk_actions(self):
        eval_email = RiskPolicyEvaluator.evaluate(tool_key="email.send", risk_level_int=3)
        assert eval_email.tier == RiskTier.HIGH
        assert eval_email.requires_approval is True
        assert eval_email.required_role == "LEAD"

        eval_dev = RiskPolicyEvaluator.evaluate(tool_key="developer.claude_code", risk_level_int=3)
        assert eval_dev.tier == RiskTier.HIGH
        assert eval_dev.requires_approval is True

    def test_critical_risk_actions(self):
        eval_finance = RiskPolicyEvaluator.evaluate(tool_key="finance.post_entry", risk_level_int=4)
        assert eval_finance.tier == RiskTier.CRITICAL
        assert eval_finance.requires_approval is True
        assert eval_finance.required_role == "FOUNDER"


class TestApprovalInboxService:
    """Kiểm thử quy trình tạo phiếu và phê duyệt/từ chối của Approval Inbox."""

    @pytest.mark.asyncio
    async def test_create_and_approve_ticket(self):
        mock_db = AsyncMock()
        service = ApprovalInboxService(mock_db)

        eval_crit = RiskPolicyEvaluator.evaluate(tool_key="finance.post_entry", risk_level_int=4)
        ticket = await service.create_request(
            requester_agent_key="cfo_agent",
            action_type="FINANCIAL_ENTRY",
            risk_evaluation=eval_crit,
            payload={"amount": 50000000, "note": "Hạch toán thuế"},
            task_id=501,
            workspace_id=1,
        )

        assert ticket.status == "PENDING"
        assert ticket.risk_level == "CRITICAL"
        assert ticket.required_role == "FOUNDER"

        # Mock approve
        mock_res = MagicMock()
        mock_res.scalars().first.return_value = ticket
        mock_db.execute.return_value = mock_res

        approved = await service.approve(request_id=ticket.id, approver_user_id=1, comment="Duyệt chi")
        assert approved.status == "APPROVED"
        assert approved.approver_user_id == 1
        assert approved.approved_at is not None


class TestBudgetingEngine:
    """Kiểm thử quản trị ngân sách và Circuit Breaker."""

    @pytest.mark.asyncio
    async def test_budget_checking_and_spend_recording(self):
        mock_db = AsyncMock()
        engine = BudgetingEngine(mock_db)

        mock_budget = AgentBudget(
            agent_key="cfo_agent",
            limit_usd=10.0,
            spent_usd=2.0,
            soft_limit_percent=0.8,
            is_blocked=False,
        )
        mock_res = MagicMock()
        mock_res.scalars().first.return_value = mock_budget
        mock_db.execute.return_value = mock_res

        # Check quota OK
        quota = await engine.check_budget_quota("cfo_agent", workspace_id=1)
        assert quota["is_blocked"] is False
        assert quota["spent_usd"] == 2.0
        assert quota["remaining_usd"] == 8.0

        # Record spend
        await engine.record_spend("cfo_agent", amount_usd=1.5, workspace_id=1)
        assert mock_budget.spent_usd == 3.5

    @pytest.mark.asyncio
    async def test_circuit_breaker_when_budget_exceeded(self):
        mock_db = AsyncMock()
        engine = BudgetingEngine(mock_db)

        mock_budget = AgentBudget(
            agent_key="devops_agent",
            limit_usd=5.0,
            spent_usd=5.5,
            is_blocked=True,
        )
        mock_res = MagicMock()
        mock_res.scalars().first.return_value = mock_budget
        mock_db.execute.return_value = mock_res

        with pytest.raises(BudgetExceededError):
            await engine.check_budget_quota("devops_agent", workspace_id=1)


class TestCostLedgerService:
    """Kiểm thử ghi nhận sổ cái tài chính bất biến và quy đổi tỷ giá."""

    @pytest.mark.asyncio
    async def test_record_cost_ledger_entry(self):
        mock_db = AsyncMock()
        service = CostLedgerService(mock_db)

        entry = await service.record_entry(
            agent_key="founder_copilot",
            provider="claude",
            model_name="claude-3-5-sonnet-20241022",
            prompt_tokens=1000,
            completion_tokens=500,
            cost_usd=0.0105,
            task_id=123,
            workspace_id=1,
        )

        assert entry.total_tokens == 1500
        assert entry.cost_usd == 0.0105
        assert entry.cost_vnd == 0.0105 * USD_TO_VND_RATE
        mock_db.add.assert_called_once()


class TestTaskDispatcherGovernanceIntegration:
    """Kiểm thử tích hợp Governance vào quy trình Task Dispatcher."""

    @pytest.mark.asyncio
    async def test_dispatch_low_risk_task_executes_and_records_cost(self):
        mock_db = AsyncMock()
        mock_task = Task(
            id=101,
            workspace_id=1,
            title="Đọc tổng quan doanh thu",
            status="todo",
            priority="medium",
            source="cfo_agent",
        )
        agent = AgentDefinition(
            id=12345,
            key="cfo_agent",
            name="CFO Agent",
            default_model_profile="reasoning",
            system_prompt_key="finance.system",
            risk_level=1,
            status="idle",
            workspace_id=1,
            model_config_jsonb={},
        )
        mock_budget = AgentBudget(
            agent_key="cfo_agent",
            limit_usd=50.0,
            spent_usd=5.0,
            is_blocked=False,
        )

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
                trace_id="trace_gov_01",
                content="Báo cáo doanh thu quý 3 đầy đủ.",
                usage=TokenUsage(prompt_tokens=150, completion_tokens=70, total_tokens=220, cost_usd=0.0015),
                latency_ms=100,
            )

            res = await dispatcher.dispatch_task(task_id=101, agent_key="cfo_agent")

            assert res["status"] == "completed"
            assert mock_task.status == "done"
            assert res["cost_usd"] == 0.0015

    @pytest.mark.asyncio
    async def test_dispatch_critical_task_creates_approval_and_pauses(self):
        mock_db = AsyncMock()
        mock_task = Task(
            id=102,
            workspace_id=1,
            title="Thực hiện bút toán ghi sổ tài chính R4",
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
            risk_level=4,  # Critical
            status="idle",
            workspace_id=1,
            model_config_jsonb={},
        )
        mock_budget = AgentBudget(
            agent_key="cfo_agent",
            limit_usd=50.0,
            spent_usd=5.0,
            is_blocked=False,
        )

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
        res = await dispatcher.dispatch_task(task_id=102, agent_key="cfo_agent")

        assert res["status"] == "waiting_approval"
        assert res["risk_tier"] == "CRITICAL"
        assert res["required_role"] == "FOUNDER"
        assert mock_task.status == "waiting_approval"
