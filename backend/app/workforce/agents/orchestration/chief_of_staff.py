import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from pydantic import BaseModel, Field
from sqlalchemy import func, text
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
from app.core.feature_flags import (
    FLAG_AGENT_DELEGATION,
    FLAG_AGENT_DELEGATION_CHIEF_OF_STAFF,
    FLAG_AGENT_RUNTIME_DEEPSEEK,
    is_enabled,
)
from app.core.snowflake import generate_snowflake_id
from app.founder_os.outcomes.models import Outcome, OutcomeRun, RunStep
from app.workforce.routing.deterministic import Intent
from app.workforce.agents.orchestration.specialist_registry import (
    AUTO_START_MAX_RISK,
    DEFAULT_ORCHESTRATION_DOMAINS,
    RISK_ORDER,
    SPECIALIST_REGISTRY,
    SpecialistSpec,
    classify_mission_risk,
)
from app.workforce.agents.orchestration.synthesis_helpers import (
    build_synthesis_prompt,
    create_approvals_and_proposals_for_action_plan,
    derive_priorities_and_actions,
)

logger = logging.getLogger(__name__)


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
        _continuation: Optional[
            tuple[
                int,
                Outcome,
                OutcomeRun,
                AgentRun,
                list[str],
                dict[str, Any],
            ]
        ] = None,
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

        delegated_reports: dict[str, Any] | None = None
        if _continuation is not None:
            (
                mission_id,
                outcome,
                outcome_run,
                agent_run,
                active_domains,
                delegated_reports,
            ) = _continuation
        elif _resume is not None:
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
                agent_run_id=None,
                status="queued",
                verification_status="UNKNOWN",
                started_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            )
            db.add(outcome_run)
            db.flush()

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
            db.flush()
            outcome_run.agent_run_id = mission_id
            db.commit()

            risk_level = classify_mission_risk(active_domains)
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

        if _continuation is not None:
            seq = int(
                db.query(func.max(AgentEventRecord.sequence))
                .filter(AgentEventRecord.run_id == mission_id)
                .scalar()
                or 0
            )
        else:
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

            if cls._durable_specialist_delegation_enabled(db, workspace_id):
                queued_domains = await cls._queue_specialist_delegations(
                    db=db,
                    workspace_id=workspace_id,
                    outcome_run=outcome_run,
                    active_domains=active_domains,
                    runtime=runtime,
                )
                if queued_domains:
                    outcome.status = "running"
                    outcome_run.status = "running"
                    db.commit()
                    return ChiefOfStaffResult(
                        mission_id=str(mission_id),
                        workspace_id=ws_str,
                        goal=goal,
                        diagnosis="Specialist work has been queued for durable execution.",
                        status="delegating",
                    )

        # 1/2. Delegation to each requested specialist domain (G3 Phase 1A —
        # generalized from 2 hardcoded sales/finance blocks into a loop over
        # SPECIALIST_REGISTRY; dispatching a 3rd/4th domain needs no new
        # branch here). Each delegation gets a REAL child `agent_runs` row
        # (parent_run_id=mission_id) — previously parent_run_id was only
        # threaded through AgentRunRequest for audit context, no child row
        # was ever inserted.
        specialist_reports: dict[str, Any] = dict(delegated_reports or {})
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

        synchronous_domains = [] if delegated_reports is not None else active_domains
        for domain in synchronous_domains:
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
            task_prompt = build_synthesis_prompt(goal, sales_data, fin_data)

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
        priorities, action_plan = derive_priorities_and_actions(sales_data, fin_data)

        seq += 1
        record_event("synthesis_completed", {"status": final_status}, seq)
        db.commit()

        required_approvals, created_proposals = create_approvals_and_proposals_for_action_plan(
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

    @staticmethod
    def _durable_specialist_delegation_enabled(
        db: Session,
        workspace_id: int,
    ) -> bool:
        return is_enabled(db, FLAG_AGENT_DELEGATION, workspace_id) and is_enabled(
            db,
            FLAG_AGENT_DELEGATION_CHIEF_OF_STAFF,
            workspace_id,
        )

    @classmethod
    async def _queue_specialist_delegations(
        cls,
        *,
        db: Session,
        workspace_id: int,
        outcome_run: OutcomeRun,
        active_domains: list[str],
        runtime: AgentRuntime | None,
    ) -> list[str]:
        from app.workforce.agents.delegation.manager import delegation_provider_manager
        from app.workforce.agents.delegation.task_board import TaskBoardService

        # API processes and workers own different manager lifecycles. Initialize
        # the canonical manager on demand before queue-time health validation;
        # tests and embedders may still inject an isolated manager explicitly.
        if TaskBoardService.provider_manager is delegation_provider_manager:
            await agent_runtime_manager.start()
            await delegation_provider_manager.start()

        runtime_name = runtime.runtime_name if runtime is not None else (
            "deepseek_harness"
            if is_enabled(db, FLAG_AGENT_RUNTIME_DEEPSEEK, workspace_id)
            else "mock"
        )
        existing_steps = db.query(RunStep).filter(RunStep.run_id == outcome_run.id).all()
        existing_by_domain = {
            inputs.get("report_key"): step
            for step in existing_steps
            if isinstance((inputs := step.inputs_jsonb), dict)
            and inputs.get("mission_kind") == "chief_of_staff_specialist"
        }
        queued: list[str] = []
        for domain in active_domains:
            spec = SPECIALIST_REGISTRY.get(domain)
            if spec is None or spec.delegate_via_profile_id is None:
                continue
            step = existing_by_domain.get(domain)
            if step is None:
                step = RunStep(
                    id=generate_snowflake_id(),
                    run_id=outcome_run.id,
                    type="agent",
                    inputs_jsonb={
                        "mission_kind": "chief_of_staff_specialist",
                        "report_key": domain,
                        "task": spec.task,
                        "required": True,
                        "failure_policy": "fail_mission",
                    },
                    expected_output=f"Structured {domain} specialist report",
                    risk_level=spec.risk_level,
                    depends_on_step_ids=[],
                    status="pending",
                )
                db.add(step)
                db.flush()
                existing_by_domain[domain] = step
            await TaskBoardService.assign_step(
                db=db,
                workspace_id=workspace_id,
                step_id=step.id,
                profile_id=spec.delegate_via_profile_id,
                runtime_name=runtime_name,
                provider_name="in_process",
                actor_agent_key="chief_of_staff",
            )
            queued.append(domain)
        return queued

    @classmethod
    async def resume_after_delegation(
        cls,
        db: Session,
        mission_id: int,
        runtime: AgentRuntime | None = None,
    ) -> ChiefOfStaffResult:
        """Resume synthesis once after all required durable steps terminate.

        PostgreSQL session advisory locking is non-blocking: concurrent workers
        never block the event loop, and a crashed owner automatically releases
        the lock when its connection closes.  The materialized mission_completed
        event is the durable idempotency record checked on every retry.
        """
        lock_acquired = True
        use_advisory_lock = db.get_bind().dialect.name == "postgresql"
        if use_advisory_lock:
            lock_acquired = bool(
                db.execute(
                    text("SELECT pg_try_advisory_lock(:mission_id)"),
                    {"mission_id": mission_id},
                ).scalar()
            )
        if not lock_acquired:
            return cls._delegating_result(db, mission_id)

        try:
            completed = (
                db.query(AgentEventRecord)
                .filter(
                    AgentEventRecord.run_id == mission_id,
                    AgentEventRecord.event_type == "mission_completed",
                )
                .order_by(AgentEventRecord.event_time.desc())
                .first()
            )
            completed_payload = completed.payload_jsonb if completed is not None else None
            if isinstance(completed_payload, dict) and isinstance(
                completed_payload.get("result"), dict
            ):
                return ChiefOfStaffResult.model_validate(completed_payload["result"])

            agent_run = (
                db.query(AgentRun)
                .filter(AgentRun.id == mission_id)
                .with_for_update()
                .one_or_none()
            )
            if agent_run is None:
                raise ValueError(f"Mission {mission_id} has no AgentRun")
            outcome_run = (
                db.query(OutcomeRun)
                .filter(OutcomeRun.agent_run_id == mission_id)
                .one_or_none()
            )
            if outcome_run is None:
                raise ValueError(f"Mission {mission_id} has no OutcomeRun")
            outcome = db.query(Outcome).filter(Outcome.id == outcome_run.outcome_id).one()
            steps = db.query(RunStep).filter(RunStep.run_id == outcome_run.id).all()
            delegation_steps = [
                step
                for step in steps
                if isinstance(step.inputs_jsonb, dict)
                and step.inputs_jsonb.get("mission_kind") == "chief_of_staff_specialist"
            ]
            if not delegation_steps or any(
                step.status not in {"completed", "failed", "cancelled", "skipped"}
                for step in delegation_steps
            ):
                return cls._delegating_result(db, mission_id)

            required_failures = [
                step
                for step in delegation_steps
                if step.status != "completed"
                and bool((step.inputs_jsonb or {}).get("required", True))
            ]
            meta = agent_run.metadata_jsonb or {}
            goal = str(meta.get("goal") or outcome.desired_result)
            if required_failures:
                result = ChiefOfStaffResult(
                    mission_id=str(mission_id),
                    workspace_id=str(outcome.workspace_id),
                    goal=goal,
                    diagnosis="Mission failed because a required specialist delegation did not complete.",
                    status="failed",
                )
                agent_run.status = "failed"
                agent_run.finished_at = datetime.now(timezone.utc)
                outcome_run.status = "failed"
                outcome_run.completed_at = datetime.now(timezone.utc)
                outcome.status = "failed"
                next_sequence = int(
                    db.query(func.max(AgentEventRecord.sequence))
                    .filter(AgentEventRecord.run_id == mission_id)
                    .scalar()
                    or 0
                ) + 1
                db.add(
                    AgentEventRecord(
                        id=generate_snowflake_id(),
                        run_id=mission_id,
                        company_id=agent_run.company_id,
                        sequence=next_sequence,
                        agent_key="chief_of_staff",
                        actor_type="chief_of_staff",
                        actor_id=str(mission_id),
                        status="failed",
                        event_type="mission_completed",
                        event_time=datetime.now(timezone.utc),
                        payload_jsonb={"result": result.model_dump(mode="json")},
                    )
                )
                db.commit()
                return result

            reports = {
                str(step.inputs_jsonb["report_key"]): (step.result_jsonb or {})
                for step in delegation_steps
                if step.status == "completed"
            }
            domains = list(meta.get("domains") or reports.keys())
            intent_value = meta.get("intent")
            return await cls.orchestrate(
                db=db,
                workspace_id=outcome.workspace_id,
                user_id=agent_run.user_id,
                goal=goal,
                company_id=agent_run.company_id,
                context=meta.get("context"),
                runtime=runtime,
                budget=MissionBudget.model_validate(agent_run.budget_jsonb or {}),
                domains=domains,
                intent=Intent(intent_value) if intent_value else None,
                _continuation=(
                    mission_id,
                    outcome,
                    outcome_run,
                    agent_run,
                    domains,
                    reports,
                ),
            )
        finally:
            if use_advisory_lock and lock_acquired:
                db.execute(
                    text("SELECT pg_advisory_unlock(:mission_id)"),
                    {"mission_id": mission_id},
                )

    @staticmethod
    def _delegating_result(db: Session, mission_id: int) -> ChiefOfStaffResult:
        agent_run = db.query(AgentRun).filter(AgentRun.id == mission_id).one_or_none()
        if agent_run is None:
            raise ValueError(f"Mission {mission_id} has no AgentRun")
        outcome_run = db.query(OutcomeRun).filter(
            OutcomeRun.agent_run_id == mission_id
        ).one()
        outcome = db.query(Outcome).filter(Outcome.id == outcome_run.outcome_id).one()
        meta = agent_run.metadata_jsonb or {}
        return ChiefOfStaffResult(
            mission_id=str(mission_id),
            workspace_id=str(outcome.workspace_id),
            goal=str(meta.get("goal") or outcome.desired_result),
            diagnosis="Specialist delegations are still running.",
            status="delegating",
        )

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
    def _resolve_runtime(db: Session, workspace_id: int) -> AgentRuntime:
        if is_enabled(db, FLAG_AGENT_RUNTIME_DEEPSEEK, workspace_id):
            return agent_runtime_manager.get_runtime("deepseek_harness")
        return agent_runtime_manager.get_runtime("mock")

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

