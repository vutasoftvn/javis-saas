from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.agents.governance.models import AgentApproval
from app.agents.control_plane.models import AgentPlan, AgentPlanStep
from app.agents.control_plane.evaluator import PlanEvaluator, StepEvaluationResult
from app.agents.control_plane.router import DomainCapabilityRouter

logger = logging.getLogger(__name__)


class ControlPlaneExecutionManager:
    """Orchestrates execution of individual PlanSteps and entire AgentPlans according to strict policy gates."""

    @classmethod
    async def execute_step(
        cls,
        db: Session,
        plan_id: int,
        step_id: int,
        user_id: int,
        workspace_id: int,
    ) -> StepEvaluationResult:
        plan = db.query(AgentPlan).filter(AgentPlan.id == plan_id).first()
        step = db.query(AgentPlanStep).filter(AgentPlanStep.id == step_id, AgentPlanStep.plan_id == plan_id).first()

        if not plan or not step:
            return StepEvaluationResult(
                step_id=str(step_id),
                status="failed",
                success=False,
                summary="Plan or step not found",
            )

        step_id_str = str(step.id)
        now = datetime.now(timezone.utc)
        step.started_at = now
        step.status = "running"
        db.commit()

        PlanEvaluator.record_step_event(
            db=db,
            plan=plan,
            step=step,
            event_type="step_started",
            payload={"message": f"Execution started for step: {step.title}"},
        )

        # 1. Check Policy Level Gate
        if step.policy_level == "L3A_EXECUTE_WITH_APPROVAL":
            # Check existing approval
            approval = None
            if step.approval_id:
                approval = db.query(AgentApproval).filter(AgentApproval.id == step.approval_id).first()

            if not approval or approval.status != "approved":
                # Create pending approval if none exists
                if not approval:
                    app_id = generate_snowflake_id()
                    approval = AgentApproval(
                        id=app_id,
                        workspace_id=workspace_id,
                        company_id=plan.company_id or workspace_id,
                        requested_by_agent=f"{step.domain}_{step.capability}",
                        action_type=step.tool_id or "external_action",
                        tool_name=step.tool_id or "unknown_tool",
                        input_preview_jsonb=step.input_jsonb or {},
                        risk_level="medium",
                        status="pending",
                    )
                    db.add(approval)
                    step.approval_id = app_id
                
                step.status = "waiting_approval"
                db.commit()

                PlanEvaluator.record_step_event(
                    db=db,
                    plan=plan,
                    step=step,
                    event_type="approval_requested",
                    payload={"approval_id": str(approval.id), "tool": step.tool_id},
                )

                return StepEvaluationResult(
                    step_id=step_id_str,
                    status="waiting_approval",
                    success=True,
                    summary=f"Step requires Founder approval for external action '{step.tool_id}'",
                    data={"approval_id": str(approval.id), "tool_id": step.tool_id},
                )

        # 2. Execute Step via Domain Capabilities
        route = DomainCapabilityRouter.resolve_route(step.domain, step.capability)
        output_data: Dict[str, Any] = {
            "handler": route.handler_name,
            "domain": step.domain,
            "capability": step.capability,
            "tool_id": step.tool_id,
            "executed_at": now.isoformat(),
            "status": "success",
            "result_summary": f"Completed {step.capability} task in {step.domain} domain.",
        }

        if step.domain == "sales":
            from app.agents.domains.sales import (
                SalesResearchCapability,
                SalesDataCapability,
                SalesReasoningCapability,
                SalesCommunicationCapability,
                SalesActionCapability,
                SalesEvaluationCapability,
            )

            if step.capability == "research":
                res = SalesResearchCapability.execute(db=db, workspace_id=workspace_id, input_data=step.input_jsonb or {})
                output_data["data"] = res
                output_data["result_summary"] = res.get("summary", output_data["result_summary"])
            elif step.capability == "data":
                if step.tool_id == "sales.crm.write":
                    res = SalesDataCapability.update_crm_stage(db=db, workspace_id=workspace_id, new_stage="contacted")
                else:
                    res = SalesDataCapability.read_pipeline(db=db, workspace_id=workspace_id)
                output_data["data"] = res
                output_data["result_summary"] = res.get("summary", "Sales pipeline and CRM data queried.")
            elif step.capability == "reasoning":
                # Score sample prospects
                sample_prospects = [
                    {"name": "Nguyen Van An", "company": "Alpha Tech", "title": "Head of AI", "industry": "Technology"},
                    {"name": "Tran Thi Bich", "company": "Bich Logistics", "title": "Managing Director", "industry": "Logistics"},
                ]
                res = SalesReasoningCapability.score_prospects(sample_prospects)
                output_data["data"] = res
                output_data["result_summary"] = res.get("summary", output_data["result_summary"])
            elif step.capability == "communication":
                sample_qualified = [
                    {"name": "Nguyen Van An", "company": "Alpha Tech", "email": "an@alphatech.example.com", "industry": "Technology"},
                ]
                res = SalesCommunicationCapability.generate_outreach_drafts(sample_qualified)
                output_data["data"] = res
                output_data["result_summary"] = res.get("summary", output_data["result_summary"])
            elif step.capability == "action":
                res = await SalesActionCapability.dispatch_outreach(
                    db=db,
                    workspace_id=workspace_id,
                    drafts=[{"recipient_email": "an@alphatech.example.com", "recipient_name": "Nguyen Van An"}],
                )
                output_data["data"] = res
                output_data["result_summary"] = res.get("summary", output_data["result_summary"])
            elif step.capability == "evaluation":
                res = SalesEvaluationCapability.evaluate_campaign()
                output_data["data"] = res
                output_data["result_summary"] = res.get("summary", output_data["result_summary"])

        elif step.domain == "finance":
            from app.agents.domains.finance import (
                FinanceDataCapability,
                FinanceReasoningCapability,
                FinanceResearchCapability,
                FinanceActionCapability,
                FinanceEvaluationCapability,
            )

            if step.capability == "data":
                res = FinanceDataCapability.read_financial_position(db=db, workspace_id=workspace_id)
                output_data["data"] = res
                output_data["result_summary"] = res.get("summary", output_data["result_summary"])
            elif step.capability == "reasoning":
                res = FinanceReasoningCapability.detect_anomalies()
                output_data["data"] = res
                output_data["result_summary"] = res.get("summary", output_data["result_summary"])
            elif step.capability == "research":
                res = FinanceResearchCapability.model_runway_scenarios()
                output_data["data"] = res
                output_data["result_summary"] = res.get("summary", output_data["result_summary"])
            elif step.capability == "action":
                res = FinanceActionCapability.prepare_accounting_review_package()
                output_data["data"] = res
                output_data["result_summary"] = res.get("summary", output_data["result_summary"])
            elif step.capability == "evaluation":
                res = FinanceEvaluationCapability.evaluate_financial_health()
                output_data["data"] = res
                output_data["result_summary"] = res.get("summary", output_data["result_summary"])

        step.output_jsonb = output_data
        step.status = "completed"
        step.completed_at = datetime.now(timezone.utc)
        db.commit()

        PlanEvaluator.record_step_event(
            db=db,
            plan=plan,
            step=step,
            event_type="step_completed",
            payload={"output": output_data},
        )

        return StepEvaluationResult(
            step_id=step_id_str,
            status="completed",
            success=True,
            summary=output_data["result_summary"],
            data=output_data,
        )

    @classmethod
    async def execute_next_pending_step(
        cls,
        db: Session,
        plan_id: int,
        user_id: int,
        workspace_id: int,
    ) -> Optional[StepEvaluationResult]:
        plan = db.query(AgentPlan).filter(AgentPlan.id == plan_id).first()
        if not plan:
            return None

        # Find first non-completed step
        for step in plan.steps:
            if step.status in ("pending", "waiting_approval"):
                res = await cls.execute_step(
                    db=db,
                    plan_id=plan.id,
                    step_id=step.id,
                    user_id=user_id,
                    workspace_id=workspace_id,
                )
                # Check if plan status needs update
                eval_res = PlanEvaluator.evaluate_plan(db, plan_id)
                plan.status = eval_res.overall_status
                db.commit()
                return res

        return None
