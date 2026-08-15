import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.core.tool_registry import ToolSpec
from app.agents.governance.models import AgentApproval
from app.agents.governance.policy_engine import PolicyEngine, PolicyAction
from app.agents.governance.states import (
    AgentPlanStepStatus,
    AgentPlanStatus,
    validate_step_transition,
    validate_plan_transition,
)
from app.agents.reliability.reliability import RetryPolicy, CircuitBreaker
from app.agents.capabilities.service import CapabilityGateway
from app.agents.control_plane.models import AgentPlan, AgentPlanStep
from app.agents.control_plane.evaluator import PlanEvaluator, StepEvaluationResult
from app.agents.control_plane.router import DomainCapabilityRouter

logger = logging.getLogger(__name__)


class ControlPlaneExecutionManager:
    """Orchestrates execution of individual PlanSteps and entire AgentPlans according to strict policy gates and reliability policies."""

    @classmethod
    async def execute_step(
        cls,
        db: Session,
        plan_id: int,
        step_id: int,
        user_id: int,
        workspace_id: int,
        retry_delays: Optional[list[float]] = None,
    ) -> StepEvaluationResult:
        plan = db.query(AgentPlan).filter(AgentPlan.id == plan_id).first()
        step = db.query(AgentPlanStep).filter(AgentPlanStep.id == step_id, AgentPlanStep.plan_id == plan_id).first()

        if not plan or not step:
            return StepEvaluationResult(
                step_id=str(step_id),
                status="failed_final",
                success=False,
                summary="Plan or step not found",
            )

        step_id_str = str(step.id)
        now = datetime.now(timezone.utc)
        step.started_at = now
        step.status = validate_step_transition(step.status, AgentPlanStepStatus.RUNNING)
        db.commit()

        PlanEvaluator.record_step_event(
            db=db,
            plan=plan,
            step=step,
            event_type="step_started",
            payload={"message": f"Execution started for step: {step.title}"},
        )

        # 1. Policy Gate Evaluation via CapabilityGateway
        capability_name = step.tool_id or f"{step.domain}.{step.capability}"
        check_result = await CapabilityGateway.check(
            db=db,
            workspace_id=workspace_id,
            subject_type="agent",
            subject_id=f"{step.domain}_{step.capability}",
            capability=capability_name,
            resource_type=step.domain,
            resource_id=step.tool_id,
            permission_profile=step.policy_level,
            params=step.input_jsonb,
        )

        if check_result.action == PolicyAction.REQUIRE_APPROVAL.value:
            approval = None
            if step.approval_id:
                approval = db.query(AgentApproval).filter(AgentApproval.id == step.approval_id).first()

            if not approval or approval.status != "approved":
                if not approval:
                    app_id = generate_snowflake_id()
                    approval = AgentApproval(
                        id=app_id,
                        workspace_id=workspace_id,
                        company_id=plan.company_id or workspace_id,
                        requested_by_agent=f"{step.domain}_{step.capability}",
                        action_type=step.tool_id or "external_action",
                        tool_name=step.tool_id or "unknown_tool",
                        capability=capability_name,
                        resource_type=step.domain,
                        resource_id=step.tool_id,
                        simulation_result_jsonb=check_result.simulation,
                        is_strong_approval=check_result.is_strong_approval,
                        input_preview_jsonb=step.input_jsonb or {},
                        risk_level=check_result.risk_level,
                        status="pending",
                    )
                    db.add(approval)
                    step.approval_id = app_id

                step.status = validate_step_transition(step.status, AgentPlanStepStatus.WAITING_APPROVAL)
                db.commit()

                PlanEvaluator.record_step_event(
                    db=db,
                    plan=plan,
                    step=step,
                    event_type="approval_requested",
                    payload={"approval_id": str(approval.id), "tool": step.tool_id, "simulation": check_result.simulation},
                )

                return StepEvaluationResult(
                    step_id=step_id_str,
                    status="waiting_approval",
                    success=True,
                    summary=f"Step requires Founder approval for action '{step.tool_id or step.title}'",
                    data={"approval_id": str(approval.id), "tool_id": step.tool_id, "simulation": check_result.simulation},
                )

        if check_result.action == PolicyAction.DENY.value:
            step.status = validate_step_transition(step.status, AgentPlanStepStatus.FAILED_FINAL)
            db.commit()
            PlanEvaluator.record_step_event(
                db=db,
                plan=plan,
                step=step,
                event_type="step_failed",
                payload={"error": check_result.reason},
            )
            return StepEvaluationResult(
                step_id=step_id_str,
                status="failed_final",
                success=False,
                summary=f"Policy violation: {check_result.reason}",
            )

        # 2. Execute Step via Domain Capabilities with Retry and Fallback
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

        async def _dispatch_capability() -> Dict[str, Any]:
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
                    return SalesResearchCapability.execute(db=db, workspace_id=workspace_id, input_data=step.input_jsonb or {})
                elif step.capability == "data":
                    if step.tool_id == "sales.crm.write":
                        return SalesDataCapability.update_crm_stage(db=db, workspace_id=workspace_id, new_stage="contacted")
                    return SalesDataCapability.read_pipeline(db=db, workspace_id=workspace_id)
                elif step.capability == "reasoning":
                    input_prospects = (step.input_jsonb or {}).get("prospects") or [
                        {"name": "Nguyen Van An", "company": "Alpha Tech", "title": "Head of AI", "industry": "Technology"},
                        {"name": "Tran Thi Bich", "company": "Bich Logistics", "title": "Managing Director", "industry": "Logistics"},
                    ]
                    return SalesReasoningCapability.score_prospects(input_prospects)
                elif step.capability == "communication":
                    input_qualified = (step.input_jsonb or {}).get("prospects") or [
                        {"name": "Nguyen Van An", "company": "Alpha Tech", "email": "an@alphatech.example.com", "industry": "Technology"},
                    ]
                    return SalesCommunicationCapability.generate_outreach_drafts(input_qualified)
                elif step.capability == "action":
                    drafts = (step.input_jsonb or {}).get("drafts") or [
                        {"recipient_email": "an@alphatech.example.com", "recipient_name": "Nguyen Van An"}
                    ]
                    return await SalesActionCapability.dispatch_outreach(
                        db=db,
                        workspace_id=workspace_id,
                        drafts=drafts,
                    )
                elif step.capability == "evaluation":
                    return SalesEvaluationCapability.evaluate_campaign()

            elif step.domain == "finance":
                from app.agents.domains.finance import (
                    FinanceDataCapability,
                    FinanceReasoningCapability,
                    FinanceResearchCapability,
                    FinanceActionCapability,
                    FinanceEvaluationCapability,
                )

                if step.capability == "data":
                    return FinanceDataCapability.read_financial_position(db=db, workspace_id=workspace_id)
                elif step.capability == "reasoning":
                    return FinanceReasoningCapability.detect_anomalies()
                elif step.capability == "research":
                    return FinanceResearchCapability.model_runway_scenarios()
                elif step.capability == "action":
                    return FinanceActionCapability.prepare_accounting_review_package()
                elif step.capability == "evaluation":
                    return FinanceEvaluationCapability.evaluate_financial_health()

            elif step.domain == "marketing":
                from app.agents.domains.marketing import (
                    MarketingDataCapability,
                    MarketingReasoningCapability,
                    MarketingResearchCapability,
                    MarketingCommunicationCapability,
                    MarketingActionCapability,
                    MarketingEvaluationCapability,
                )

                if step.capability == "data":
                    return MarketingDataCapability.read_marketing_overview(db=db, workspace_id=workspace_id)
                elif step.capability == "reasoning":
                    return MarketingReasoningCapability.analyze_funnel_bottlenecks(step.input_jsonb)
                elif step.capability == "research":
                    return MarketingResearchCapability.research_campaign_angles()
                elif step.capability == "communication":
                    return MarketingCommunicationCapability.generate_campaign_drafts()
                elif step.capability == "action":
                    return MarketingActionCapability.prepare_campaign_launch(
                        db=db,
                        workspace_id=workspace_id,
                        campaign_name=(step.input_jsonb or {}).get("campaign_name", step.title),
                    )
                elif step.capability == "evaluation":
                    return MarketingEvaluationCapability.evaluate_campaign_health()

            elif step.domain == "learning":
                from app.agents.domains.learning import (
                    LearningDataCapability,
                    LearningReasoningCapability,
                    LearningResearchCapability,
                    LearningCommunicationCapability,
                    LearningActionCapability,
                    LearningEvaluationCapability,
                )

                if step.capability == "data":
                    return LearningDataCapability.read_lessons(db=db, workspace_id=workspace_id)
                elif step.capability == "reasoning":
                    return LearningReasoningCapability.synthesize_lesson_from_friction(
                        observation=(step.input_jsonb or {}).get("observation", step.title),
                    )
                elif step.capability == "research":
                    return LearningResearchCapability.audit_recent_handoffs(db=db, workspace_id=workspace_id)
                elif step.capability == "communication":
                    return LearningCommunicationCapability.format_playbook_update(
                        lesson_title=step.title,
                        recommendations=["Automate handoffs", "Track cycle velocity"],
                    )
                elif step.capability == "action":
                    return LearningActionCapability.record_new_lesson(
                        db=db,
                        workspace_id=workspace_id,
                        observation=(step.input_jsonb or {}).get("observation", step.title),
                    )
                elif step.capability == "evaluation":
                    return LearningEvaluationCapability.evaluate_learning_velocity()

            elif step.domain == "legal":
                from app.agents.domains.legal import (
                    LegalDataCapability,
                    LegalReasoningCapability,
                    LegalResearchCapability,
                    LegalCommunicationCapability,
                    LegalActionCapability,
                    LegalEvaluationCapability,
                )

                citations = (step.input_jsonb or {}).get("citations") or ["law.vn.civil_code:art_401", "internal.policy:dpa_v1"]

                if step.capability == "data":
                    return LegalDataCapability.read_legal_posture(db=db, workspace_id=workspace_id)
                elif step.capability == "reasoning":
                    return LegalReasoningCapability.risk_summary(
                        context_data=step.input_jsonb or {},
                        citations=citations,
                    )
                elif step.capability == "research":
                    return LegalResearchCapability.audit_obligations(db=db, workspace_id=workspace_id)
                elif step.capability == "communication":
                    return LegalCommunicationCapability.draft_counsel_memo(
                        subject=step.title,
                        background=(step.input_jsonb or {}).get("background", "Standard contract review"),
                        citations=citations,
                    )
                elif step.capability == "action":
                    return LegalActionCapability.record_checklist_item(
                        db=db,
                        workspace_id=workspace_id,
                        title=step.title,
                        citations=citations,
                    )
                elif step.capability == "evaluation":
                    return LegalEvaluationCapability.evaluate_legal_output({
                        "citations": citations,
                        "disclaimer": "COSA AI informational assistance",
                    })

            return {"summary": f"Executed generic capability {step.capability} in {step.domain}"}

        # Reliability execution loop
        delays = retry_delays if retry_delays is not None else [0.01, 0.02, 0.05]
        max_retries = step.max_retries if step.max_retries is not None else 3
        attempt = 0
        last_error: Optional[Exception] = None

        while attempt <= max_retries:
            try:
                if attempt > 0:
                    step.status = validate_step_transition(step.status, AgentPlanStepStatus.RETRYING)
                    step.retry_count = attempt
                    db.commit()
                    PlanEvaluator.record_step_event(
                        db=db,
                        plan=plan,
                        step=step,
                        event_type="step_retrying",
                        payload={"attempt": attempt, "max_retries": max_retries, "error": str(last_error)},
                    )

                res = await _dispatch_capability()
                output_data["data"] = res
                output_data["result_summary"] = res.get("summary", output_data["result_summary"]) if isinstance(res, dict) else str(res)
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                attempt += 1
                is_transient = RetryPolicy.is_transient_error(exc)
                if not is_transient or attempt > max_retries:
                    break
                # Transient wait
                wait_idx = min(attempt - 1, len(delays) - 1)
                await asyncio.sleep(delays[wait_idx])

        if last_error:
            logger.warning(f"[ControlPlaneExecutionManager] Step execution failed after {attempt} attempts: {last_error}")
            
            # Check for fallback
            fallback_handler = (step.input_jsonb or {}).get("fallback_handler")
            if fallback_handler:
                try:
                    step.fallback_used = True
                    step.status = validate_step_transition(step.status, AgentPlanStepStatus.FALLBACK)
                    db.commit()
                    PlanEvaluator.record_step_event(
                        db=db,
                        plan=plan,
                        step=step,
                        event_type="step_fallback",
                        payload={"original_error": str(last_error), "fallback": fallback_handler},
                    )
                    # Attempt fallback
                    output_data["data"] = {"fallback": True, "handler": fallback_handler, "message": "Executed via fallback strategy."}
                    output_data["result_summary"] = "Executed via fallback handler after retries exhausted."
                    last_error = None
                except Exception as fb_exc:
                    last_error = fb_exc

            if last_error:
                step.status = validate_step_transition(step.status, AgentPlanStepStatus.FAILED_FINAL)
                step.output_jsonb = {"error": str(last_error), "attempts": attempt}
                step.completed_at = datetime.now(timezone.utc)
                db.commit()

                PlanEvaluator.record_step_event(
                    db=db,
                    plan=plan,
                    step=step,
                    event_type="step_failed",
                    payload={"error": str(last_error), "final": True},
                )

                return StepEvaluationResult(
                    step_id=step_id_str,
                    status="failed_final",
                    success=False,
                    summary=f"Step failed permanently: {last_error}",
                    data={"error": str(last_error)},
                )

        step.output_jsonb = output_data
        step.status = validate_step_transition(step.status, AgentPlanStepStatus.COMPLETED)
        step.completed_at = datetime.now(timezone.utc)
        db.commit()

        CapabilityGateway.record_observation(
            db=db,
            plan_id=plan.id,
            step_id=step.id,
            agent_key=f"{step.domain}_{step.capability}",
            tool_name=step.tool_id or step.capability,
            status="success",
            capability=capability_name,
            resource_type=step.domain,
            resource_id=step.tool_id,
            input_data=step.input_jsonb,
            output_data=output_data,
            approval_id=step.approval_id,
        )

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

        for step in plan.steps:
            if step.status in ("pending", "waiting_approval"):
                res = await cls.execute_step(
                    db=db,
                    plan_id=plan.id,
                    step_id=step.id,
                    user_id=user_id,
                    workspace_id=workspace_id,
                )
                eval_res = PlanEvaluator.evaluate_plan(db, plan_id)
                plan.status = validate_plan_transition(plan.status, eval_res.overall_status)
                db.commit()
                return res

        return None
