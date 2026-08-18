from typing import Any, Optional
from sqlalchemy.orm import Session

from app.core.snowflake import generate_snowflake_id
from app.workforce.agents.control_plane.context import ContextEnvelope
from app.workforce.agents.control_plane.models import AgentGoal, AgentPlan, AgentPlanStep


class GoalDecomposer:
    """Decomposes high-level founder goals or operational commands into structured, policy-annotated plan steps."""

    @classmethod
    def decompose(
        cls,
        goal_title: str,
        goal_type: str = "business_goal",
        target_metric: Optional[dict[str, Any]] = None,
        context: Optional[ContextEnvelope] = None,
        domain_hint: str = "founder",
    ) -> list[dict[str, Any]]:
        normalized = goal_title.lower()

        # 1. SALES DOMAIN PLAN
        if domain_hint == "sales" or any(w in normalized for w in ("sales", "lead", "khách", "pipeline", "deal", "prospect", "outreach")):
            return [
                {
                    "sequence_order": 1,
                    "title": "Audit current sales pipeline and baseline conversion",
                    "domain": "sales",
                    "capability": "data",
                    "tool_id": "sales.pipeline.read",
                    "policy_level": "L0_READ",
                    "input": {"scope": "all_stages", "target_metric": target_metric},
                    "expected_output": {"type": "pipeline_summary", "description": "Current pipeline volume, deal stages and conversion bottlenecks."},
                },
                {
                    "sequence_order": 2,
                    "title": "Research and identify ideal customer profile (ICP) target list",
                    "domain": "sales",
                    "capability": "research",
                    "tool_id": "web.search",
                    "policy_level": "L1_SUGGEST",
                    "input": {"icp_criteria": "high_growth_b2b"},
                    "expected_output": {"type": "prospect_list", "count": 25},
                },
                {
                    "sequence_order": 3,
                    "title": "Evaluate and score prospect readiness",
                    "domain": "sales",
                    "capability": "reasoning",
                    "tool_id": None,
                    "policy_level": "L1_SUGGEST",
                    "input": {"scoring_model": "fit_and_intent"},
                    "expected_output": {"type": "qualified_prospects", "min_score": 75},
                },
                {
                    "sequence_order": 4,
                    "title": "Generate tailored multi-channel outreach drafts",
                    "domain": "sales",
                    "capability": "communication",
                    "tool_id": None,
                    "policy_level": "L2_DRAFT",
                    "input": {"channel": "email_and_zalo", "tone": "consultative_expert"},
                    "expected_output": {"type": "message_drafts", "ready_for_review": True},
                },
                {
                    "sequence_order": 5,
                    "title": "Request Founder Approval and execute outbound campaign via n8n",
                    "domain": "sales",
                    "capability": "action",
                    "tool_id": "n8n.sales.outreach_dispatch",
                    "policy_level": "L3A_EXECUTE_WITH_APPROVAL",
                    "input": {"destination": "n8n_gateway", "risk": "medium"},
                    "expected_output": {"type": "delivery_receipt", "status": "dispatched"},
                },
                {
                    "sequence_order": 6,
                    "title": "Record activities and update CRM pipeline stages",
                    "domain": "sales",
                    "capability": "data",
                    "tool_id": "sales.crm.write",
                    "policy_level": "L2_DRAFT",
                    "input": {"update_stage": "contacted"},
                    "expected_output": {"type": "crm_sync_status", "records_updated": True},
                },
                {
                    "sequence_order": 7,
                    "title": "Evaluate campaign results, measure ROI and generate Next Actions",
                    "domain": "sales",
                    "capability": "evaluation",
                    "tool_id": None,
                    "policy_level": "L1_SUGGEST",
                    "input": {"kpis": ["reply_rate", "pipeline_delta"]},
                    "expected_output": {"type": "evaluation_report", "lessons": []},
                },
            ]

        # 2. FINANCE DOMAIN PLAN
        if domain_hint == "finance" or any(w in normalized for w in ("tài chính", "finance", "doanh thu", "chi phí", "dòng tiền", "runway", "lợi nhuận", "báo cáo")):
            return [
                {
                    "sequence_order": 1,
                    "title": "Query real financial ledgers and cash position",
                    "domain": "finance",
                    "capability": "data",
                    "tool_id": "finance.ledger.read",
                    "policy_level": "L0_READ",
                    "input": {"period": "current_month"},
                    "expected_output": {"type": "cash_position", "statement": "cashflow"},
                },
                {
                    "sequence_order": 2,
                    "title": "Run financial anomaly detection and burn-rate analysis",
                    "domain": "finance",
                    "capability": "reasoning",
                    "tool_id": None,
                    "policy_level": "L1_SUGGEST",
                    "input": {"threshold_percent": 15},
                    "expected_output": {"type": "anomalies_detected", "items": []},
                },
                {
                    "sequence_order": 3,
                    "title": "Draft runway projection and cost-optimization recommendations",
                    "domain": "finance",
                    "capability": "research",
                    "tool_id": None,
                    "policy_level": "L1_SUGGEST",
                    "input": {"projection_months": 6},
                    "expected_output": {"type": "runway_forecast", "months": 12},
                },
                {
                    "sequence_order": 4,
                    "title": "Prepare accounting review package for Founder confirmation",
                    "domain": "finance",
                    "capability": "action",
                    "tool_id": "finance.accounting.review_draft",
                    "policy_level": "L2_DRAFT",
                    "input": {"standard": "TT58"},
                    "expected_output": {"type": "accounting_package", "ready_for_signoff": True},
                },
            ]

        # 3. DEFAULT / CHIEF OF STAFF PLAN
        return [
            {
                "sequence_order": 1,
                "title": "Analyze company cross-domain context and active constraints",
                "domain": "founder",
                "capability": "research",
                "tool_id": None,
                "policy_level": "L0_READ",
                "input": {"goal": goal_title},
                "expected_output": {"type": "domain_readiness_assessment"},
            },
            {
                "sequence_order": 2,
                "title": "Synthesize strategic priorities and action dependencies",
                "domain": "founder",
                "capability": "reasoning",
                "tool_id": None,
                "policy_level": "L1_SUGGEST",
                "input": {"context_envelope": True},
                "expected_output": {"type": "priorities_synthesis"},
            },
            {
                "sequence_order": 3,
                "title": "Delegate domain initiatives and draft task allocations",
                "domain": "founder",
                "capability": "action",
                "tool_id": None,
                "policy_level": "L2_DRAFT",
                "input": {"delegations": ["sales", "finance"]},
                "expected_output": {"type": "delegation_packages"},
            },
            {
                "sequence_order": 4,
                "title": "Evaluate milestone progress and recommend next loop iteration",
                "domain": "founder",
                "capability": "evaluation",
                "tool_id": None,
                "policy_level": "L1_SUGGEST",
                "input": {},
                "expected_output": {"type": "pdca_loop_summary"},
            },
        ]


class ControlPlanePlanner:
    """Manages the creation and persistence of Plans and PlanSteps from Goals."""

    @classmethod
    def create_plan_for_goal(
        cls,
        db: Session,
        goal: AgentGoal,
        context: Optional[ContextEnvelope] = None,
        domain_hint: str = "founder",
    ) -> AgentPlan:
        step_definitions = GoalDecomposer.decompose(
            goal_title=goal.title,
            goal_type=goal.goal_type,
            target_metric=goal.target_metric_jsonb,
            context=context,
            domain_hint=domain_hint,
        )

        plan_id = generate_snowflake_id()
        plan = AgentPlan(
            id=plan_id,
            goal_id=goal.id,
            workspace_id=goal.workspace_id,
            company_id=goal.company_id,
            user_id=goal.user_id,
            title=f"Execution Plan: {goal.title}",
            rationale=f"System generated agentic plan composed of {len(step_definitions)} steps spanning domain capabilities.",
            status="draft",
            version=1,
        )
        db.add(plan)
        db.flush()

        step_ids = []
        for defn in step_definitions:
            step_id = generate_snowflake_id()
            step_ids.append(str(step_id))
            step = AgentPlanStep(
                id=step_id,
                plan_id=plan.id,
                sequence_order=defn["sequence_order"],
                title=defn["title"],
                domain=defn["domain"],
                capability=defn["capability"],
                tool_id=defn.get("tool_id"),
                policy_level=defn.get("policy_level", "L0_READ"),
                input_jsonb=defn.get("input"),
                expected_output_jsonb=defn.get("expected_output"),
                dependencies_jsonb=[step_ids[-2]] if len(step_ids) > 1 else [],
                status="pending",
            )
            db.add(step)

        db.commit()
        db.refresh(plan)
        return plan
