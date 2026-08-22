import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from workforce.models import (
    WorkProduct, DecisionRecord, AgentDefinition, AgentBudget
)
from workforce.work_product.transformer import WorkProductTransformer
from workforce.work_product.work_product_service import WorkProductService
from workforce.work_product.decision_service import DecisionRecordService
from workforce.dispatcher.task_dispatcher import AgentTaskDispatcher
from workforce.adapters.base import ExecutionResult, TokenUsage
from founder_os.tasks.models import Task


class TestWorkProductTransformer:
    """Kiểm thử bộ chuyển đổi WorkProductTransformer."""

    def test_transform_markdown_report(self):
        raw = """# BÁO CÁO TÀI CHÍNH QUÝ 3
Summary: Doanh thu Q3 tăng trưởng 35% so với cùng kỳ, vượt mục tiêu 12WY đề ra.

Chi tiết phân bổ doanh thu:
```sql
SELECT department, SUM(revenue) FROM sales GROUP BY department;
```
"""
        output = WorkProductTransformer.transform(raw, task_title="Báo cáo tài chính", agent_key="cfo_agent")

        assert output.title == "BÁO CÁO TÀI CHÍNH QUÝ 3"
        assert output.product_type == "FINANCIAL_REPORT"
        assert "Doanh thu Q3 tăng trưởng 35%" in output.summary
        assert len(output.artifacts) == 1
        assert output.artifacts[0]["language"] == "sql"


class TestWorkProductLifecycle:
    """Kiểm thử vòng đời Work Product: Tạo Draft -> Yêu cầu sửa -> Nghiệm thu."""

    @pytest.mark.asyncio
    async def test_create_revise_and_accept_work_product(self):
        mock_db = AsyncMock()
        mock_task = Task(id=401, workspace_id=1, title="Soạn thảo kế hoạch marketing", status="in_progress")

        service = WorkProductService(mock_db)
        raw_text = "# Kế hoạch Marketing Tháng 10\nSummary: Chiến dịch nhắm vào 500 SMEs.\n\nNội dung chi tiết ở đây."

        # 1. Tạo Work Product từ Run
        wp = await service.create_from_execution(
            task=mock_task,
            agent_key="cmo_agent",
            raw_content=raw_text,
            workspace_id=1,
        )
        assert wp.status == "DRAFT"
        assert wp.agent_key == "cmo_agent"
        mock_db.add.assert_called_once()

        # Mock DB get by table name
        def execute_side_effect(stmt):
            stmt_str = str(stmt)
            res_mock = MagicMock()
            if "work_products" in stmt_str:
                res_mock.scalars().first.return_value = wp
            elif "tasks" in stmt_str:
                res_mock.scalars().first.return_value = mock_task
            else:
                res_mock.scalars().first.return_value = None
            return res_mock

        mock_db.execute.side_effect = execute_side_effect

        # 2. Yêu cầu sửa lại (Request Revision)
        revised = await service.request_revision(
            product_id=wp.id,
            reviewed_by=1,
            feedback="Bổ sung thêm kênh Tiktok Ads",
        )
        assert revised.status == "REVISION_REQUESTED"
        assert "Bổ sung thêm kênh Tiktok Ads" in revised.metadata_jsonb["revision_feedback"]
        assert mock_task.status == "in_progress"

        # 3. Nghiệm thu chấp thuận (Accept)
        accepted = await service.accept_work_product(
            product_id=wp.id,
            reviewed_by=1,
            feedback="Rất tốt, duyệt ngân sách",
        )
        assert accepted.status == "ACCEPTED"
        assert accepted.reviewed_by == 1
        assert mock_task.status == "done"


class TestDecisionRecordGeneration:
    """Kiểm thử tạo và quản lý Decision Record (ADR)."""

    @pytest.mark.asyncio
    async def test_create_and_accept_decision_record(self):
        mock_db = AsyncMock()
        service = DecisionRecordService(mock_db)

        dr = await service.create_decision_record(
            title="ADR-001: Lựa chọn Claude Code Adapter cho Tech Lead Agent",
            context_summary="Cần khả năng chạy CLI và đọc AST trực tiếp trên repository.",
            decision_content="Sử dụng Claude Code Adapter thay vì generic chat API.",
            consequences="Tốc độ phân tích repo nhanh gấp 3 lần.",
            alternatives_considered="Generic HTTP OpenAI API.",
            author_agent_key="tech_lead_agent",
            workspace_id=1,
        )

        assert dr.title.startswith("ADR-001")
        assert dr.status == "PROPOSED"
        mock_db.add.assert_called_once()

        mock_res = MagicMock()
        mock_res.scalars().first.return_value = dr
        mock_db.execute.return_value = mock_res

        accepted_dr = await service.accept_decision(dr.id, user_id=1)
        assert accepted_dr.status == "ACCEPTED"
        assert accepted_dr.approved_by_user_id == 1


class TestTaskDispatcherWorkProductIntegration:
    """Kiểm thử Task Dispatcher tự động tạo Work Product khi hoàn tất task."""

    @pytest.mark.asyncio
    async def test_dispatch_task_generates_work_product(self):
        mock_db = AsyncMock()
        mock_task = Task(id=555, workspace_id=1, title="Lập dự toán chi phí máy chủ Q4", status="todo", source="devops_agent")
        mock_agent = AgentDefinition(id=2, key="devops_agent", name="DevOps Agent", risk_level=1, model_config_jsonb={})
        mock_budget = AgentBudget(agent_key="devops_agent", limit_usd=50.0, spent_usd=0.0, is_blocked=False)

        def execute_side_effect(stmt):
            stmt_str = str(stmt)
            res_mock = MagicMock()
            if "tasks" in stmt_str:
                res_mock.scalars().first.return_value = mock_task
            elif "agent_definitions" in stmt_str:
                res_mock.scalars().first.return_value = mock_agent
            elif "agent_budgets" in stmt_str:
                res_mock.scalars().first.return_value = mock_budget
            else:
                res_mock.scalars().first.return_value = None
            return res_mock

        mock_db.execute.side_effect = execute_side_effect

        dispatcher = AgentTaskDispatcher(mock_db)
        with patch.object(dispatcher.runner, "execute_run", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ExecutionResult(
                trace_id="wp_trace_01",
                content="# BÁO CÁO DỰ TOÁN CLOUD Q4\nSummary: Tổng chi phí ước tính là 4,500 USD.\n\nBảng phân bổ chi tiết.",
                usage=TokenUsage(prompt_tokens=120, completion_tokens=60, total_tokens=180, cost_usd=0.0012),
                latency_ms=95,
            )

            res = await dispatcher.dispatch_task(task_id=555, agent_key="devops_agent")

            assert res["status"] == "completed"
            assert "work_product_id" in res
            assert res["work_product_id"] is not None
            assert "4,500 USD" in res["result_summary"]
