import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.workforce.models import (
    AgentDefinition, AgentHeartbeat, ApprovalRequest, AgentBudget, CostLedger,
    AgentRoutine, RoutineExecution, WorkProduct, DecisionRecord
)
from app.workforce.dashboard_service import ControlPlaneDashboardService
from app.workforce.automation.routine_service import RoutineService
from app.workforce.dispatcher.task_dispatcher import AgentTaskDispatcher
from app.workforce.governance.approval_service import ApprovalInboxService
from app.workforce.work_product.work_product_service import WorkProductService
from app.workforce.work_product.decision_service import DecisionRecordService
from app.workforce.adapters.base import ExecutionResult, TokenUsage
from app.founder_os.tasks.models import Task


class TestControlPlaneDashboardAggregator:
    """Kiểm thử API tổng hợp chỉ số Dashboard thời gian thực."""

    @pytest.mark.asyncio
    async def test_dashboard_summary_calculation(self):
        mock_db = AsyncMock()

        # Mock data across 6 models
        agents = [
            AgentDefinition(id=1, key="founder_copilot", name="Founder", department="executive"),
            AgentDefinition(id=2, key="cfo_agent", name="CFO", department="finance"),
            AgentDefinition(id=3, key="devops_agent", name="DevOps", department="engineering"),
        ]
        heartbeats = [
            AgentHeartbeat(agent_key="founder_copilot", status="HEALTHY"),
            AgentHeartbeat(agent_key="cfo_agent", status="HEALTHY"),
            AgentHeartbeat(agent_key="devops_agent", status="DEGRADED"),
        ]
        ledger_entries = [
            CostLedger(agent_key="cfo_agent", cost_usd=0.05, cost_vnd=1270.0, total_tokens=5000),
            CostLedger(agent_key="founder_copilot", cost_usd=0.02, cost_vnd=508.0, total_tokens=2000),
        ]
        budgets = [
            AgentBudget(agent_key="cfo_agent", limit_usd=100.0, spent_usd=0.05),
            AgentBudget(agent_key="founder_copilot", limit_usd=100.0, spent_usd=0.02),
        ]
        approvals = [
            ApprovalRequest(id=1, risk_level="CRITICAL", status="PENDING"),
            ApprovalRequest(id=2, risk_level="HIGH", status="PENDING"),
        ]
        routines = [AgentRoutine(key="monday_tactics_dispatch", name="Monday Routine")]
        routine_execs = [RoutineExecution(status="SUCCESS")]
        work_products = [
            WorkProduct(id=10, status="ACCEPTED"),
            WorkProduct(id=11, status="DRAFT"),
        ]
        decisions = [DecisionRecord(id=20, status="ACCEPTED")]

        def execute_side_effect(stmt):
            stmt_str = str(stmt)
            res_mock = MagicMock()
            if "agent_definitions" in stmt_str:
                res_mock.scalars().all.return_value = agents
            elif "agent_heartbeats" in stmt_str:
                res_mock.scalars().all.return_value = heartbeats
            elif "cost_ledger_entries" in stmt_str:
                res_mock.scalars().all.return_value = ledger_entries
            elif "agent_budgets" in stmt_str:
                res_mock.scalars().all.return_value = budgets
            elif "approval_requests" in stmt_str:
                res_mock.scalars().all.return_value = approvals
            elif "agent_routines" in stmt_str:
                res_mock.scalars().all.return_value = routines
            elif "routine_executions" in stmt_str:
                res_mock.scalars().all.return_value = routine_execs
            elif "work_products" in stmt_str:
                res_mock.scalars().all.return_value = work_products
            elif "decision_records" in stmt_str:
                res_mock.scalars().all.return_value = decisions
            else:
                res_mock.scalars().all.return_value = []
            return res_mock

        mock_db.execute.side_effect = execute_side_effect

        dashboard_service = ControlPlaneDashboardService(mock_db)
        summary = await dashboard_service.get_dashboard_summary(workspace_id=1)

        # Workforce
        assert summary["workforce"]["total_agents"] == 3
        assert summary["workforce"]["health_summary"]["HEALTHY"] == 2
        assert summary["workforce"]["health_summary"]["DEGRADED"] == 1

        # Financial
        assert summary["financial"]["total_spent_usd"] == 0.07
        assert summary["financial"]["total_tokens_consumed"] == 7000
        assert summary["financial"]["total_budget_limit_usd"] == 200.0

        # Governance
        assert summary["governance"]["pending_approvals_total"] == 2
        assert summary["governance"]["critical_risk_tickets"] == 1

        # Work Products & ADR
        assert summary["work_products"]["total_products"] == 2
        assert summary["work_products"]["status_breakdown"]["ACCEPTED"] == 1
        assert summary["work_products"]["decision_records_count"] == 1


class TestEndToEndFounderWorkflow:
    """Kiểm thử chu trình tích hợp E2E đầy đủ của Founder Operating System."""

    @pytest.mark.asyncio
    async def test_full_12wy_routine_governance_work_product_flow(self):
        mock_db = AsyncMock()

        # Step 1: Initialize Routine and Task
        routine = AgentRoutine(
            id=101,
            key="monday_tactics_dispatch",
            name="Monday Morning 12WY Tactics Dispatch",
            target_agent_key="founder_copilot",
            enabled=True,
            payload_template_jsonb={"title": "[12WY] Tactics Tuần 5", "priority": "high"},
        )
        task = Task(id=1001, workspace_id=1, title="[12WY] Tactics Tuần 5", status="todo", source="founder_copilot")
        agent = AgentDefinition(id=1, key="founder_copilot", name="Founder", risk_level=1, model_config_jsonb={})
        budget = AgentBudget(agent_key="founder_copilot", limit_usd=100.0, spent_usd=0.0, is_blocked=False)

        wp_mock = WorkProduct(id=5001, task_id=1001, agent_key="founder_copilot", title="[12WY] Tactics Tuần 5", status="DRAFT")

        def execute_side_effect(stmt):
            stmt_str = str(stmt)
            res_mock = MagicMock()
            if "agent_routines" in stmt_str:
                res_mock.scalars().first.return_value = routine
            elif "tasks" in stmt_str:
                res_mock.scalars().first.return_value = task
            elif "agent_definitions" in stmt_str:
                res_mock.scalars().first.return_value = agent
            elif "agent_budgets" in stmt_str:
                res_mock.scalars().first.return_value = budget
            elif "work_products" in stmt_str:
                res_mock.scalars().first.return_value = wp_mock
            else:
                res_mock.scalars().first.return_value = None
            return res_mock

        mock_db.execute.side_effect = execute_side_effect

        # Step 2: Trigger Routine & Task Execution
        routine_service = RoutineService(mock_db)
        with patch("app.workforce.dispatcher.task_dispatcher.AgentRunnerService.execute_run", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ExecutionResult(
                trace_id="e2e_trace_01",
                content="# KẾ HOẠCH TACTICS TUẦN 5\nSummary: 12 Tactics được phân bổ cho 6 phòng ban.\n\nChi tiết tactics.",
                usage=TokenUsage(prompt_tokens=200, completion_tokens=100, total_tokens=300, cost_usd=0.002),
                latency_ms=110,
            )

            res = await routine_service.trigger_routine("monday_tactics_dispatch", workspace_id=1)
            assert res["status"] == "SUCCESS"
            assert res["dispatch_result"]["status"] == "completed"
            assert "work_product_id" in res["dispatch_result"]

        # Step 3: Review and Accept Work Product
        wp_service = WorkProductService(mock_db)
        accepted_wp = await wp_service.accept_work_product(
            product_id=5001,
            reviewed_by=1,
            feedback="Duyệt bản kế hoạch",
        )
        assert accepted_wp.status == "ACCEPTED"
        assert task.status == "done"

        # Step 4: Create Decision Record (ADR)
        dr_service = DecisionRecordService(mock_db)
        dr = await dr_service.create_decision_record(
            title="ADR-005: Thông qua phân bổ Weekly Tactics Tuần 5",
            context_summary="Ưu tiên đẩy mạnh kênh B2B SaaS.",
            decision_content="Phân bổ 60% năng lực workforce cho Sales và Product.",
            author_agent_key="founder_copilot",
            work_product_id=5001,
            task_id=1001,
            workspace_id=1,
        )
        assert dr.title.startswith("ADR-005")
        assert dr.status == "PROPOSED"
