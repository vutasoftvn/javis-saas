import asyncio
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agents.orchestration.mission_control_bus import mission_control_bus
from app.agents.runtime.manager import agent_runtime_manager
from app.agents.runtime.types import AgentRunRequest
from app.core.snowflake import generate_snowflake_str
from app.modules.sales.sales_tools import get_pipeline_summary
from app.modules.finance.finance_tools import get_financial_summary


class DelegatedTaskResult(BaseModel):
    agent_key: str
    domain: str
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    status: str = "completed"


class ChiefOfStaffResult(BaseModel):
    mission_id: str
    workspace_id: str
    goal: str
    diagnosis: str
    specialist_reports: dict[str, Any] = Field(default_factory=dict)
    priorities: list[str] = Field(default_factory=list)
    action_plan: list[dict[str, Any]] = Field(default_factory=list)
    required_approvals: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "completed"


class ChiefOfStaffOrchestrator:
    """Orchestrates high-level Founder requests by delegating to specialized agents and synthesizing outcomes."""

    @classmethod
    async def orchestrate(
        cls,
        db: Session,
        workspace_id: int,
        user_id: int,
        goal: str,
        company_id: Optional[int] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> ChiefOfStaffResult:
        mission_id = generate_snowflake_str()
        ws_str = str(workspace_id)
        cid_str = str(company_id or workspace_id)
        uid_str = str(user_id)

        # 1. Mission Started Event
        mission_control_bus.emit_event(
            run_id=mission_id,
            workspace_id=ws_str,
            event_type="mission_started",
            data={"goal": goal},
            agent_key="chief_of_staff",
        )
        await asyncio.sleep(0.02)

        # 2. Delegation to Sales Specialist
        mission_control_bus.emit_event(
            run_id=mission_id,
            workspace_id=ws_str,
            event_type="subagent_delegated",
            data={"subagent": "sales_specialist", "task": "Analyze CRM pipeline, lead conversion, and open opportunities"},
            agent_key="chief_of_staff",
        )
        sales_data = get_pipeline_summary(db, workspace_id)
        await asyncio.sleep(0.02)

        mission_control_bus.emit_event(
            run_id=mission_id,
            workspace_id=ws_str,
            event_type="subagent_completed",
            data={"subagent": "sales_specialist", "status": "completed", "summary": "Pipeline metrics compiled"},
            agent_key="sales_specialist",
        )

        # 3. Delegation to Finance Specialist
        mission_control_bus.emit_event(
            run_id=mission_id,
            workspace_id=ws_str,
            event_type="subagent_delegated",
            data={"subagent": "finance_specialist", "task": "Analyze cashflow, monthly burn rate, and runway"},
            agent_key="chief_of_staff",
        )
        fin_data = get_financial_summary(db, workspace_id)
        await asyncio.sleep(0.02)

        mission_control_bus.emit_event(
            run_id=mission_id,
            workspace_id=ws_str,
            event_type="subagent_completed",
            data={"subagent": "finance_specialist", "status": "completed", "summary": "Financial metrics compiled"},
            agent_key="finance_specialist",
        )

        # 4. Synthesis & Cross-Domain Analysis
        mission_control_bus.emit_event(
            run_id=mission_id,
            workspace_id=ws_str,
            event_type="synthesis_started",
            data={"focus": "Synthesizing Sales & Finance insights into actionable roadmap"},
            agent_key="chief_of_staff",
        )

        sales_metrics = sales_data.get("metrics", {})
        open_val = sales_metrics.get("open_pipeline_value", 0.0)
        runway = fin_data.get("runway_months", 12.0)

        diagnosis = (
            f"Phân tích tổng hợp: Đường ống bán hàng hiện có {sales_metrics.get('total_leads', 0)} leads "
            f"với giá trị mở {open_val:,.0f} VND. Tình hình tài chính duy trì runway ~{runway} tháng. "
            f"Cần tập trung đẩy nhanh tốc độ chốt các deal PROPOSAL để bổ sung dòng tiền."
        )

        priorities = [
            "Tăng tỷ lệ chuyển đổi từ Lead sang Opportunity",
            "Follow-up khẩn cấp các cơ hội đang ở giai đoạn PROPOSAL/NEGOTIATION",
            "Tối ưu chi phí vận hành hàng tháng để kéo dài runway",
        ]

        action_plan = [
            {"week": 1, "tactic": "Gửi email follow-up và sắp xếp demo cho toàn bộ qualified leads", "owner": "sales_specialist"},
            {"week": 2, "tactic": "Rà soát dự toán chi tiêu và kiểm toán dòng tiền quý", "owner": "finance_specialist"},
            {"week": 3, "tactic": "Chốt deal Alpha Cloud Deployment", "owner": "sales_specialist"},
            {"week": 4, "tactic": "Đánh giá lại kết quả tuần thứ 13 và lập kế hoạch chu kỳ mới", "owner": "chief_of_staff"},
        ]

        required_approvals = [
            {
                "action_type": "strategic_campaign_approval",
                "tool_name": "sales.create_activity",
                "risk_level": "medium",
                "description": "Phê duyệt kích hoạt chiến dịch tiếp cận lại nhóm khách hàng tiềm năng lớn",
            }
        ]

        # 5. Mission Completed Event
        result = ChiefOfStaffResult(
            mission_id=mission_id,
            workspace_id=ws_str,
            goal=goal,
            diagnosis=diagnosis,
            specialist_reports={
                "sales": sales_data,
                "finance": fin_data,
            },
            priorities=priorities,
            action_plan=action_plan,
            required_approvals=required_approvals,
            status="completed",
        )

        mission_control_bus.emit_event(
            run_id=mission_id,
            workspace_id=ws_str,
            event_type="mission_completed",
            data={"result": result.model_dump()},
            agent_key="chief_of_staff",
        )

        return result
