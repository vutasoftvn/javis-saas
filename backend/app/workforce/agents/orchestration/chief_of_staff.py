import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.workforce.agents.context import build_agent_context, CofounderContextAssembler
from app.workforce.agents.delegation.limits import MAX_SUBRUN_DEPTH
from app.workforce.agents.governance.approval_service import ApprovalService
from app.workforce.agents.governance.budget import BudgetTracker, MissionBudget
from app.workforce.agents.governance.kernel import GovernanceKernel
from app.workforce.agents.governance.models import AgentEventRecord, AgentRun
from app.workforce.agents.governance.quality_gate import QualityGateEvaluator, QualityGateVerdict
from app.workforce.agents.governance.states import validate_run_transition
from app.workforce.agents.governance.stuck_detector import StuckDetector
from app.workforce.agents.orchestration.mission_control_bus import mission_control_bus
from app.workforce.agents.proposals.service import AgentProposalService
from app.workforce.agents.registry import get_preset
from app.workforce.agents.runtime.base import AgentRuntime
from app.workforce.agents.runtime.errors import AgentRuntimeError
from app.workforce.agents.runtime.json_output import parse_structured_output
from app.workforce.agents.runtime.manager import agent_runtime_manager
from app.workforce.agents.runtime.tool_bridge import dispatch_tool_call
from app.workforce.agents.runtime.types import AgentRunRequest
from app.core.feature_flags import FLAG_AGENT_RUNTIME_DEEPSEEK, is_enabled
from app.core.snowflake import generate_snowflake_id
from app.founder_os.outcomes.models import Outcome, OutcomeRun
from app.business.sales.sales_tools import get_pipeline_summary
from app.business.finance.finance_tools import get_financial_summary
from app.business.legal.legal_tools import get_legal_posture_summary
from app.business.marketing.marketing_tools import get_marketing_overview
from app.workforce.routing.deterministic import Intent

logger = logging.getLogger(__name__)

# Ordered so max() by index picks the higher-risk tier (G2 §7.6 R0-R4 policy).
RISK_ORDER = ("R0", "R1", "R2", "R3", "R4")
# Missions at or below this risk auto-start; anything higher stays in "draft"
# until a founder explicitly confirms (G2 §7.3).
AUTO_START_MAX_RISK = "R1"


class DelegatedTaskResult(BaseModel):
    agent_key: str
    domain: str
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    status: str = "completed"


@dataclass(frozen=True)
class SpecialistSpec:
    """One entry in SPECIALIST_REGISTRY — everything orchestrate()'s
    delegation loop needs to dispatch a domain specialist generically (G3
    Phase 1A), without a new `if domain == "...":` branch per domain."""
    domain: str
    agent_key: str
    task: str
    tool_flat_name: str
    fetch_snapshot: Callable[[Session, int], dict[str, Any]]
    # Whether QualityGateEvaluator.evaluate(domain, snapshot) is safe to call
    # on this specialist's raw snapshot. False when the registered gate is
    # built for a different shape (e.g. an analysis/citation output) than
    # what this specialist's read-only snapshot produces — see "legal" below.
    quality_gate_compatible: bool = True
    # G2 §7.6 risk tier for what this specialist's fetch_snapshot actually
    # does. All current specialists are pure read-only DB queries (R0) — a
    # future specialist that sends/publishes/pays/deploys must be tagged R2+
    # so orchestrate() holds the mission in "draft" for founder confirmation
    # instead of auto-starting it.
    risk_level: str = "R0"


SPECIALIST_REGISTRY: dict[str, SpecialistSpec] = {
    "sales": SpecialistSpec(
        domain="sales",
        agent_key="sales_specialist",
        task="Analyze CRM pipeline",
        tool_flat_name="sales_get_pipeline_summary",
        # Dynamic module-attribute lookup at call time, NOT a frozen
        # reference to the function object as it was at import time — tests
        # patch "chief_of_staff.get_pipeline_summary" by module attribute
        # (unittest.mock.patch), which only a same-module name lookup at
        # call time (not a captured reference) will observe.
        fetch_snapshot=lambda db, ws: get_pipeline_summary(db, ws),
    ),
    "finance": SpecialistSpec(
        domain="finance",
        agent_key="finance_specialist",
        task="Analyze cashflow and runway",
        tool_flat_name="finance_get_financial_summary",
        fetch_snapshot=lambda db, ws: get_financial_summary(db, ws),
    ),
    "legal": SpecialistSpec(
        domain="legal",
        agent_key="legal_specialist",
        task="Review legal posture and obligations",
        tool_flat_name="legal_get_legal_posture_summary",
        fetch_snapshot=lambda db, ws: get_legal_posture_summary(db, ws),
        # LegalQualityGate is built to grade an analysis OUTPUT (citations +
        # disclaimer on a legal opinion), not a checklist/obligation
        # snapshot — evaluating it against this specialist's read-only
        # snapshot would always FAIL for a structural reason unrelated to
        # actual mission quality. Wiring a correct gate needs a
        # capability-aware shape mapping (Phase 1C/1E), not blind looping.
        quality_gate_compatible=False,
    ),
    "marketing": SpecialistSpec(
        domain="marketing",
        agent_key="marketing_specialist",
        task="Analyze marketing funnel and scorecard",
        tool_flat_name="marketing_get_marketing_overview",
        fetch_snapshot=lambda db, ws: get_marketing_overview(db, ws),
    ),
}

DEFAULT_ORCHESTRATION_DOMAINS: tuple[str, ...] = ("sales", "finance")

class ChiefOfStaffResult(BaseModel):
    mission_id: str
    workspace_id: str
    goal: str
    diagnosis: str
    specialist_reports: dict[str, Any] = Field(default_factory=dict)
    priorities: list[str] = Field(default_factory=list)
    action_plan: list[dict[str, Any]] = Field(default_factory=list)
    required_approvals: list[dict[str, Any]] = Field(default_factory=list)
    proposals: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "completed"



class ChiefOfStaffOrchestrator:
    """Orchestrates high-level Founder requests by delegating to specialized agents and synthesizing outcomes.

    The synthesis step (diagnosis) is a real AgentRuntime call, not templated text: it is
    genuinely a function of `goal` and the real Sales/Finance snapshots. `priorities`/
    `action_plan` are derived deterministically from the same real data (not invented by the
    LLM) so the approval chain below stays testable without depending on reliable free-form
    JSON generation from whichever runtime is configured.
    """

    @classmethod
    async def orchestrate(
        cls,
        db: Session,
        workspace_id: int,
        user_id: int,
        goal: str,
        company_id: Optional[int] = None,
        context: Optional[dict[str, Any]] = None,
        runtime: Optional[AgentRuntime] = None,
        budget: Optional[MissionBudget] = None,
        domains: Optional[list[str]] = None,
        intent: Optional[Intent] = None,
        _resume: Optional[tuple[int, Outcome, OutcomeRun, AgentRun, list[str]]] = None,
    ) -> ChiefOfStaffResult:
        """`domains` selects which SPECIALIST_REGISTRY entries to delegate to
        (default: sales + finance, matching prior fixed behavior). Any
        registry key works — dispatching a 3rd/4th domain (e.g. "legal")
        needs no new branch here, only a new SPECIALIST_REGISTRY entry
        (G3 Phase 1A).

        G2 §7.3 / G3 §12: a mission whose selected domains are all at or
        below AUTO_START_MAX_RISK auto-starts (read-only research). Anything
        riskier is created as a `draft` Outcome and returned with
        status="waiting_confirmation" WITHOUT running the delegation loop —
        `confirm_mission()` is the only way to actually execute it after
        that. `_resume` is internal-only, set by confirm_mission() to reuse
        the already-created draft rows instead of minting new ones.
        """
        ws_str = str(workspace_id)
        cid_str = str(company_id or workspace_id)
        uid_str = str(user_id)

        active_budget = budget
        if active_budget is None and context and context.get("budget"):
            try:
                active_budget = MissionBudget.model_validate(context["budget"])
            except Exception:
                active_budget = MissionBudget()
        elif active_budget is None:
            active_budget = MissionBudget()

        if _resume is not None:
            mission_id, outcome, outcome_run, agent_run, active_domains = _resume
            outcome.status = "planning"
            outcome_run.status = "running"
            agent_run.status = validate_run_transition(agent_run.status, "running")
            db.commit()
        else:
            active_domains = list(domains) if domains is not None else list(DEFAULT_ORCHESTRATION_DOMAINS)
            mission_id = generate_snowflake_id()

            outcome = Outcome(
                id=generate_snowflake_id(),
                workspace_id=workspace_id,
                function="strategy",
                title=f"Mission: {goal[:200]}",
                desired_result=goal,
                requested_by=user_id,
                status="draft",
                created_at=datetime.now(timezone.utc),
            )
            db.add(outcome)

            outcome_run = OutcomeRun(
                id=generate_snowflake_id(),
                outcome_id=outcome.id,
                agent_run_id=mission_id,
                status="queued",
                verification_status="UNKNOWN",
                started_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            )
            db.add(outcome_run)

            agent_run = AgentRun(
                id=mission_id,
                workspace_id=workspace_id,
                company_id=company_id or workspace_id,
                user_id=user_id,
                outcome_run_id=outcome_run.id,
                agent_key="chief_of_staff",
                runtime="pending",
                status="created",
                permission_profile="chief_of_staff_suggest",
                budget_jsonb=active_budget.model_dump(),
                # Stashed so confirm_mission() can replay this exact request
                # later without a separate Mission table (G2 §2.5 — reuse
                # Outcome/OutcomeRun/AgentRun instead of a new model).
                metadata_jsonb={
                    "goal": goal,
                    "domains": active_domains,
                    "context": context,
                    "intent": intent.value if intent else None,
                },
                started_at=datetime.now(timezone.utc),
            )
            db.add(agent_run)
            db.commit()

            risk_level = cls._classify_mission_risk(active_domains)
            if RISK_ORDER.index(risk_level) > RISK_ORDER.index(AUTO_START_MAX_RISK):
                return ChiefOfStaffResult(
                    mission_id=str(mission_id),
                    workspace_id=ws_str,
                    goal=goal,
                    diagnosis=(
                        f"Mission ở mức rủi ro {risk_level}, cần Founder xác nhận trước khi chạy "
                        f"(gọi confirm_mission với mission_id={mission_id})."
                    ),
                    specialist_reports={},
                    priorities=[],
                    action_plan=[],
                    required_approvals=[],
                    proposals=[],
                    status="waiting_confirmation",
                )

            outcome.status = "planning"
            outcome_run.status = "running"
            agent_run.status = validate_run_transition(agent_run.status, "running")
            db.commit()

        def record_event(event_type: str, data: dict[str, Any], sequence: int, status: Optional[str] = None) -> None:
            db.add(AgentEventRecord(
                id=generate_snowflake_id(),
                run_id=mission_id,
                company_id=company_id,
                sequence=sequence,
                agent_key="chief_of_staff",
                actor_type="chief_of_staff",
                actor_id=str(mission_id),
                status=status or "running",
                event_type=event_type,
                event_time=datetime.now(timezone.utc),
                payload_jsonb=data,
            ))
            mission_control_bus.emit_event(
                run_id=str(mission_id),
                workspace_id=ws_str,
                event_type=event_type,
                data=data,
                agent_key="chief_of_staff",
            )

        def check_governance(step_num: int) -> Optional[tuple[str, str]]:
            budget_res = BudgetTracker.check(db=db, agent_run=agent_run, budget=active_budget, current_step=step_num)
            if budget_res.is_exceeded:
                return (budget_res.reason_code or "BUDGET_EXCEEDED", budget_res.message)
            stuck_res = StuckDetector.analyze_run(db=db, run_id=mission_id)
            if stuck_res.is_stuck and stuck_res.suggested_action == "ABORT_RUN":
                return ("STUCK_LOOP", f"Stuck loop detected: {stuck_res.detail}")
            elif stuck_res.is_stuck and stuck_res.suggested_action == "WARN_CHANGE_STRATEGY":
                record_event("stuck_loop_warning", {"detail": stuck_res.detail, "loop_type": stuck_res.loop_type}, step_num)
                db.commit()
            return None

        seq = 1
        record_event("mission_started", {"goal": goal}, seq)
        db.commit()
        await asyncio.sleep(0.02)

        # Safety & Governance Check: Start
        gov_failure = check_governance(seq)
        if gov_failure:
            err_code, err_msg = gov_failure
            agent_run.status = "failed"
            agent_run.error_code = err_code
            agent_run.error_message = err_msg
            agent_run.finished_at = datetime.now(timezone.utc)
            outcome_run.status = "failed"
            outcome_run.completed_at = datetime.now(timezone.utc)
            outcome.status = "failed"
            seq += 1
            record_event("mission_failed", {"reason": err_code, "message": err_msg}, seq, status="failed")
            db.commit()
            return ChiefOfStaffResult(
                mission_id=str(mission_id),
                workspace_id=ws_str,
                goal=goal,
                diagnosis=f"Mission aborted: {err_msg}",
                specialist_reports={},
                priorities=[],
                action_plan=[],
                required_approvals=[],
                proposals=[],
                status="failed",
            )

        # 1/2. Delegation to each requested specialist domain (G3 Phase 1A —
        # generalized from 2 hardcoded sales/finance blocks into a loop over
        # SPECIALIST_REGISTRY; dispatching a 3rd/4th domain needs no new
        # branch here). Each delegation gets a REAL child `agent_runs` row
        # (parent_run_id=mission_id) — previously parent_run_id was only
        # threaded through AgentRunRequest for audit context, no child row
        # was ever inserted.
        specialist_reports: dict[str, Any] = {}
        child_run_ids: dict[str, str] = {}

        # G3 Phase 1E: refuse to delegate at all if this mission is itself
        # already a subrun (depth 1) — delegating further would create depth
        # 2, past MAX_SUBRUN_DEPTH. Checked once for the whole loop since it
        # depends only on the mission's own row, not on which domain.
        is_subrun = getattr(agent_run, "parent_run_id", None) is not None
        if is_subrun and active_domains:
            logger.warning(
                "[ChiefOfStaffOrchestrator] mission %s is itself a subrun (parent_run_id=%s) — "
                "refusing to delegate further, exceeds MAX_SUBRUN_DEPTH=%d",
                mission_id, agent_run.parent_run_id, MAX_SUBRUN_DEPTH,
            )
            active_domains = []

        for domain in active_domains:
            spec = SPECIALIST_REGISTRY.get(domain)
            if spec is None:
                logger.warning("[ChiefOfStaffOrchestrator] Unknown specialist domain %r requested; skipping.", domain)
                continue

            seq += 1
            record_event("subagent_delegated", {"subagent": spec.agent_key, "domain": domain, "task": spec.task}, seq)
            db.commit()

            child_run_id = generate_snowflake_id()
            child_run = AgentRun(
                id=child_run_id,
                workspace_id=workspace_id,
                company_id=company_id or workspace_id,
                user_id=user_id,
                parent_run_id=mission_id,
                agent_key=spec.agent_key,
                job_type=domain,
                runtime="sync_delegation",
                status="created",
                permission_profile="read_only",
                started_at=datetime.now(timezone.utc),
            )
            db.add(child_run)
            db.flush()
            child_run.status = validate_run_transition(child_run.status, "running")

            specialist_req = AgentRunRequest(
                company_id=cid_str,
                workspace_id=ws_str,
                user_id=uid_str,
                agent_key=spec.agent_key,
                task=spec.task,
                permission_profile="read_only",
                parent_run_id=str(mission_id),
            )
            GovernanceKernel.evaluate_and_audit_tool_call(
                db=db,
                request=specialist_req,
                tool_flat_name=spec.tool_flat_name,
                args={},
                run_id=mission_id,
            )

            try:
                snapshot = spec.fetch_snapshot(db, workspace_id)
                child_run.status = validate_run_transition(child_run.status, "completed")
            except Exception as exc:
                snapshot = {"status": "error", "message": str(exc)}
                child_run.status = validate_run_transition(child_run.status, "failed")
                logger.exception("[ChiefOfStaffOrchestrator] specialist fetch_snapshot failed for domain=%s", domain)
            child_run.finished_at = datetime.now(timezone.utc)

            specialist_reports[domain] = snapshot
            child_run_ids[domain] = str(child_run_id)

            seq += 1
            record_event(
                "subagent_completed",
                {"subagent": spec.agent_key, "domain": domain, "status": child_run.status, "child_run_id": str(child_run_id)},
                seq,
            )
            db.commit()

            gov_failure = check_governance(seq)
            if gov_failure:
                err_code, err_msg = gov_failure
                agent_run.status = "failed"
                agent_run.error_code = err_code
                agent_run.error_message = err_msg
                agent_run.finished_at = datetime.now(timezone.utc)
                outcome_run.status = "failed"
                outcome_run.completed_at = datetime.now(timezone.utc)
                outcome.status = "failed"
                seq += 1
                record_event("mission_failed", {"reason": err_code, "message": err_msg}, seq, status="failed")
                db.commit()
                return ChiefOfStaffResult(
                    mission_id=str(mission_id),
                    workspace_id=ws_str,
                    goal=goal,
                    diagnosis=f"Mission aborted: {err_msg}",
                    specialist_reports=dict(specialist_reports),
                    priorities=[],
                    action_plan=[],
                    required_approvals=[],
                    proposals=[],
                    status="failed",
                )

        # Backward-compatible aliases: synthesis prompt building and
        # priority/action-plan derivation below are still sales/finance-
        # specific (deriving real heuristics for arbitrary new domains is
        # separate business-logic scope from generalizing dispatch itself).
        sales_data = specialist_reports.get("sales", {})
        fin_data = specialist_reports.get("finance", {})

        # 2.5 Optional Sandbox Execution Delegation (Phase 2)
        sandbox_reports: dict[str, Any] = {}
        if context and context.get("sales_csv"):
            from app.workforce.agents.execution.analysis_service import DomainAnalysisService
            seq += 1
            record_event("sandbox_analysis_delegated", {"domain": "sales", "task": "Execute CSV analysis in sandbox"}, seq)
            db.commit()
            sales_job_res = await DomainAnalysisService.run_sales_analysis_now(
                db=db,
                workspace_id=workspace_id,
                user_id=user_id,
                csv_content=context["sales_csv"],
                agent_run_id=mission_id,
            )
            sandbox_reports["sales_sandbox"] = {
                "job_id": sales_job_res.job_id,
                "status": sales_job_res.status.value,
                "artifacts": [a.model_dump() for a in sales_job_res.artifacts],
            }
            seq += 1
            record_event("sandbox_analysis_completed", {"domain": "sales", "status": sales_job_res.status.value}, seq)
            db.commit()

        if context and context.get("finance_csv"):
            from app.workforce.agents.execution.analysis_service import DomainAnalysisService
            seq += 1
            record_event("sandbox_analysis_delegated", {"domain": "finance", "task": "Execute CSV analysis in sandbox"}, seq)
            db.commit()
            fin_job_res = await DomainAnalysisService.run_finance_analysis_now(
                db=db,
                workspace_id=workspace_id,
                user_id=user_id,
                csv_content=context["finance_csv"],
                agent_run_id=mission_id,
            )
            sandbox_reports["finance_sandbox"] = {
                "job_id": fin_job_res.job_id,
                "status": fin_job_res.status.value,
                "artifacts": [a.model_dump() for a in fin_job_res.artifacts],
            }
            seq += 1
            record_event("sandbox_analysis_completed", {"domain": "finance", "status": fin_job_res.status.value}, seq)
            db.commit()

        # Safety & Governance Check: Pre-Synthesis
        gov_failure = check_governance(seq)
        if gov_failure:
            err_code, err_msg = gov_failure
            agent_run.status = "failed"
            agent_run.error_code = err_code
            agent_run.error_message = err_msg
            agent_run.finished_at = datetime.now(timezone.utc)
            outcome_run.status = "failed"
            outcome_run.completed_at = datetime.now(timezone.utc)
            outcome.status = "failed"
            seq += 1
            record_event("mission_failed", {"reason": err_code, "message": err_msg}, seq, status="failed")
            db.commit()
            return ChiefOfStaffResult(
                mission_id=str(mission_id),
                workspace_id=ws_str,
                goal=goal,
                diagnosis=f"Mission aborted: {err_msg}",
                specialist_reports={**specialist_reports, **sandbox_reports},
                priorities=[],
                action_plan=[],
                required_approvals=[],
                proposals=[],
                status="failed",
            )

        # 3. Real synthesis call through AgentRuntime - this is what used to be hardcoded text.
        active_runtime = runtime or cls._resolve_runtime(db, workspace_id)
        agent_run.runtime = active_runtime.runtime_name
        db.commit()

        seq += 1
        record_event("synthesis_started", {"runtime": active_runtime.runtime_name}, seq)
        db.commit()

        agent_ctx = build_agent_context(
            db=db,
            workspace_id=workspace_id,
            company_id=company_id,
            agent_key="chief_of_staff",
            user_id=user_id,
        )

        # G2 §7.2 / G3 §12: Minimum Viable Context, scoped to `intent` (empty
        # for greetings, minimal for general chat, full bundle only for the
        # founder-coordination intents that actually reach orchestrate()).
        cofounder_context = CofounderContextAssembler.assemble(
            db=db,
            workspace_id=workspace_id,
            intent=intent or Intent.FOUNDER_COMMAND,
            # Scope business_signals to the domains THIS mission actually
            # delegated to — reuses the same data already fetched above
            # rather than an assembler default that could pull in a domain
            # this mission never touched.
            business_signal_domains=tuple(active_domains),
        )

        synthesis_ctx = {
            "agent_context": agent_ctx.model_dump(),
            "cofounder_context": cofounder_context,
            "sales_snapshot": sales_data,
            "finance_snapshot": fin_data,
            # Generic view so a domain beyond sales/finance still reaches the
            # synthesis LLM call even though the prompt template below only
            # names sales/finance explicitly (G3 Phase 1A).
            "specialist_reports": specialist_reports,
            **sandbox_reports,
        }

        cos_preset = get_preset("chief_of_staff")
        permission_profile = cos_preset.permission_profile if cos_preset else "chief_of_staff_suggest"

        from app.workforce.ai.prompt_registry import PromptRegistry

        try:
            prompt_registry = PromptRegistry.get_instance()
            task_prompt = prompt_registry.render_effective(
                db=db,
                workspace_id=workspace_id,
                domain="cosa",
                name="chief_of_staff_synthesis",
                variables={
                    "goal": goal,
                    "sales_data": json.dumps(sales_data, ensure_ascii=False),
                    "fin_data": json.dumps(fin_data, ensure_ascii=False),
                },
            )
        except Exception:
            task_prompt = cls._build_synthesis_prompt(goal, sales_data, fin_data)

        run_request = AgentRunRequest(
            company_id=cid_str,
            workspace_id=ws_str,
            user_id=uid_str,
            agent_key="chief_of_staff",
            task=task_prompt,
            context=synthesis_ctx,
            permission_profile=permission_profile,
            parent_run_id=str(mission_id),
        )

        try:
            run_result = await active_runtime.run(run_request)
            diagnosis, run_status = run_result.output_text or "", run_result.status
        except AgentRuntimeError as exc:
            diagnosis, run_status = f"Chief of Staff runtime unavailable: {exc.message}", "failed"

        parsed = parse_structured_output(diagnosis)
        if parsed is None and run_status not in ("failed", "cancelled"):
            # One repair attempt, per spec §24, before degrading to partial + raw text.
            try:
                retry_result = await active_runtime.run(run_request)
                parsed = parse_structured_output(retry_result.output_text or "")
                if parsed is not None:
                    diagnosis = retry_result.output_text or diagnosis
            except AgentRuntimeError:
                pass

        if parsed is not None:
            diagnosis = parsed.get("diagnosis", diagnosis)
            final_status = "completed" if run_status == "completed" else "partial"
        else:
            final_status = "partial" if run_status not in ("failed", "cancelled") else run_status

        # Cross-cutting Quality Gate Check (§45, §55)
        # Evaluates domain evidence before allowing Mission completion. Loops
        # generically over whichever domains were actually delegated to
        # (G3 Phase 1A) — but only the ones marked quality_gate_compatible in
        # SPECIALIST_REGISTRY, since a gate built for a different output
        # shape than what that specialist fetches would fail for a
        # structural reason unrelated to actual mission quality (see
        # "legal" in SPECIALIST_REGISTRY).
        gate_results: dict[str, Any] = {}
        any_gate_failed = False
        for domain, snapshot in specialist_reports.items():
            spec = SPECIALIST_REGISTRY.get(domain)
            if spec is None or not spec.quality_gate_compatible:
                continue
            gate_result = QualityGateEvaluator.evaluate(domain, snapshot)
            gate_results[domain] = gate_result
            if gate_result.verdict == QualityGateVerdict.FAIL:
                any_gate_failed = True

        if any_gate_failed and final_status == "completed":
            final_status = "failed"
            seq += 1
            record_event(
                "quality_gate_failed",
                {f"{domain}_gate": result.model_dump() for domain, result in gate_results.items()},
                seq,
            )
            db.commit()

        # priorities/action_plan are derived from the real data, not from LLM free text, so the
        # approval chain below is deterministic regardless of whether the runtime configured
        # (mock in CI, DeepSeek Harness in production) returned parseable structured output.
        priorities, action_plan = cls._derive_priorities_and_actions(sales_data, fin_data)

        seq += 1
        record_event("synthesis_completed", {"status": final_status}, seq)
        db.commit()

        required_approvals, created_proposals = cls._create_approvals_and_proposals_for_action_plan(
            db, workspace_id=workspace_id, run_id=mission_id, action_plan=action_plan
        )

        result = ChiefOfStaffResult(
            mission_id=str(mission_id),
            workspace_id=ws_str,
            goal=goal,
            diagnosis=diagnosis,
            specialist_reports={**specialist_reports, **sandbox_reports},
            priorities=priorities,
            action_plan=action_plan,
            required_approvals=required_approvals,
            proposals=created_proposals,
            status=final_status,
        )

        agent_run.status = validate_run_transition(agent_run.status, final_status)
        agent_run.finished_at = datetime.now(timezone.utc)
        outcome_run.status = "succeeded" if final_status == "completed" else ("failed" if final_status == "failed" else "running")
        outcome_run.completed_at = datetime.now(timezone.utc)
        outcome.status = "completed" if final_status == "completed" else ("failed" if final_status == "failed" else "planning")
        seq += 1
        record_event("mission_completed", {"result": result.model_dump()}, seq)
        db.commit()

        return result

    @classmethod
    async def confirm_mission(
        cls,
        db: Session,
        mission_id: int,
        user_id: int,
        workspace_id: Optional[int] = None,
        runtime: Optional[AgentRuntime] = None,
        budget: Optional[MissionBudget] = None,
    ) -> ChiefOfStaffResult:
        """Executes a mission previously created in `draft` status by
        orchestrate() (G2 §7.3: DRAFT → founder confirm → PLANNED → ACTIVE).
        Replays the original goal/domains/context stashed in
        `AgentRun.metadata_jsonb` — never trust a caller-supplied goal here,
        or a founder "confirming" mission #123 could silently execute
        different instructions than what they actually saw and approved.

        `workspace_id`, when given, must match the mission's own
        workspace_id or this raises PermissionError — defense in depth so a
        caller cannot confirm another workspace's mission just by guessing
        its id, even if the API layer's own membership check were ever
        bypassed or misconfigured.
        """
        outcome = db.query(Outcome).filter(Outcome.id == mission_id).first()
        if outcome is None:
            raise ValueError(f"Mission {mission_id} not found")
        if workspace_id is not None and outcome.workspace_id != workspace_id:
            raise PermissionError(f"Mission {mission_id} does not belong to workspace {workspace_id}")
        if outcome.status != "draft":
            raise ValueError(f"Mission {mission_id} is not awaiting confirmation (status={outcome.status})")

        agent_run = db.query(AgentRun).filter(AgentRun.id == mission_id).first()
        if agent_run is None:
            raise ValueError(f"Mission {mission_id} has no agent_run record")
        outcome_run = db.query(OutcomeRun).filter(OutcomeRun.outcome_id == outcome.id).first()
        if outcome_run is None:
            raise ValueError(f"Mission {mission_id} has no outcome_run record")

        meta = agent_run.metadata_jsonb or {}
        goal = meta.get("goal") or outcome.desired_result
        active_domains = meta.get("domains") or list(DEFAULT_ORCHESTRATION_DOMAINS)
        stashed_context = meta.get("context")
        intent_value = meta.get("intent")

        return await cls.orchestrate(
            db=db,
            workspace_id=outcome.workspace_id,
            user_id=user_id,
            goal=goal,
            company_id=agent_run.company_id,
            context=stashed_context,
            runtime=runtime,
            budget=budget,
            domains=active_domains,
            intent=Intent(intent_value) if intent_value else None,
            _resume=(mission_id, outcome, outcome_run, agent_run, active_domains),
        )

    @staticmethod
    def _classify_mission_risk(domains: list[str]) -> str:
        """Highest risk tier among the specialists this mission would
        delegate to — see SpecialistSpec.risk_level / AUTO_START_MAX_RISK."""
        highest = "R0"
        for domain in domains:
            spec = SPECIALIST_REGISTRY.get(domain)
            if spec is None:
                continue
            if RISK_ORDER.index(spec.risk_level) > RISK_ORDER.index(highest):
                highest = spec.risk_level
        return highest

    @staticmethod
    def _resolve_runtime(db: Session, workspace_id: int) -> AgentRuntime:
        if is_enabled(db, FLAG_AGENT_RUNTIME_DEEPSEEK, workspace_id):
            return agent_runtime_manager.get_runtime("deepseek_harness")
        return agent_runtime_manager.get_runtime("mock")

    @staticmethod
    def _build_synthesis_prompt(goal: str, sales_data: dict[str, Any], fin_data: dict[str, Any]) -> str:
        return (
            f"Founder goal: {goal}\n\n"
            f"Real sales pipeline snapshot: {json.dumps(sales_data, ensure_ascii=False)}\n"
            f"Real finance snapshot: {json.dumps(fin_data, ensure_ascii=False)}\n\n"
            "Diagnose the situation strictly from the data above and answer the Founder's goal. "
            "Respond as a single JSON object: "
            '{"diagnosis": "<2-4 sentence analysis grounded in the data above>"}. '
            "Do not invent numbers not present in the snapshots above."
        )

    @staticmethod
    def _parse_structured_output(text: str) -> Optional[dict[str, Any]]:
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def _derive_priorities_and_actions(
        sales_data: dict[str, Any], fin_data: dict[str, Any]
    ) -> tuple[list[str], list[dict[str, Any]]]:
        metrics = sales_data.get("metrics", {}) if isinstance(sales_data, dict) and sales_data.get("status") == "success" and isinstance(sales_data.get("metrics"), dict) else {}
        priorities: list[str] = []
        action_plan: list[dict[str, Any]] = []

        try:
            qualified = int(metrics.get("qualified_leads", 0))
            total_leads = int(metrics.get("total_leads", 0))
        except (TypeError, ValueError):
            qualified = 0
            total_leads = 0

        if qualified > 0:
            priorities.append(f"Follow up {qualified}/{total_leads} qualified leads currently in pipeline")
            action_plan.append({
                "tactic": f"Send follow-up outreach to {qualified} qualified leads",
                "owner": "sales_specialist",
                "automation_key": "sales.followup_email",
            })

        raw_runway = fin_data.get("runway_months") if isinstance(fin_data, dict) and fin_data.get("status") == "success" else None
        try:
            runway = float(raw_runway) if raw_runway is not None else None
        except (TypeError, ValueError):
            runway = None

        if runway is not None and runway < 6:
            priorities.append(f"Cash runway is {runway} months - review burn rate this week")
            action_plan.append({
                "tactic": f"Finance review: runway at {runway} months, below 6-month safety margin",
                "owner": "finance_specialist",
            })

        if not priorities:
            priorities.append("No urgent data-driven priorities identified from current Sales/Finance snapshots")

        return priorities, action_plan

    @staticmethod
    def _create_approvals_and_proposals_for_action_plan(
        db: Session, workspace_id: int, run_id: int, action_plan: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        created_approvals: list[dict[str, Any]] = []
        created_proposals: list[dict[str, Any]] = []

        for action in action_plan:
            # 1. Check for automation approval requirement
            automation_key = action.get("automation_key")
            if automation_key:
                approval = ApprovalService.create_approval(
                    db,
                    workspace_id=workspace_id,
                    agent_key="chief_of_staff",
                    action_type="automation_dispatch",
                    tool_name=automation_key,
                    input_preview=action,
                    risk_level="medium",
                    run_id=run_id,
                )
                created_approvals.append({
                    "approval_id": str(approval.id),
                    "action_type": approval.action_type,
                    "tool_name": approval.tool_name,
                    "risk_level": approval.risk_level,
                    "status": approval.status,
                })

            # 2. Check for strategy / OKR proposal requirement
            proposal_type = action.get("proposal_type")
            if proposal_type in ("okr_objective", "strategy_task"):
                proposal = AgentProposalService.create_proposal(
                    db=db,
                    workspace_id=workspace_id,
                    proposal_type=proposal_type,
                    title=action.get("title") or action.get("tactic", "Strategy Proposal"),
                    payload=action.get("payload") or action,
                    description=action.get("description"),
                    agent_key="chief_of_staff",
                    run_id=run_id,
                )
                created_proposals.append({
                    "proposal_id": str(proposal.id),
                    "proposal_type": proposal.proposal_type,
                    "title": proposal.title,
                    "status": proposal.status,
                })

        return created_approvals, created_proposals
