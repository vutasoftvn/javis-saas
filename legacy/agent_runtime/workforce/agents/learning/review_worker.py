"""Learning Review Worker (G1 §6 / G3 Phase 1E).

Turns 3 real signals into reviewable candidates for a human to approve:
1. A mission finishing (`mission_control_bus` MISSION_COMPLETED event).
2. A WorkProduct being rejected or sent back for revision.
3. An ApprovalRequest being rejected or sent back for revision.

Safety invariant (G1 §6, enforced structurally, not just by convention):
this worker READS mission/run/tool-call history and WRITES exactly two
things - an `AgentProposal` row (`proposal_type="learning_candidate"`) and,
for completed missions, a `SkillTrajectoryCandidate` row via the existing
`SkillLifecycleService.create_candidate_from_trajectory()` safety-scanned
pipeline. It never touches `ApprovalRequest`/`WorkProduct`/`AgentRun`/
`Outcome` state, never sends/publishes/pays/deletes, and never creates or
confirms a Mission. `learning_candidate` proposals are also structurally
inert at the AgentProposal layer: `AgentProposalService.apply_proposal()`'s
type-dispatch only recognizes `okr_objective`/`strategy_task`/
`project_cycle` and safely 400s on anything else (see
`agents/proposals/service.py`), so even a mis-click can't auto-apply one.

Every entry point below opens its OWN `SessionLocal()`, commits, and closes
- callers never pass in their session. This keeps the worker fully decoupled
from the caller's transaction: a worker failure can never roll back the
founder's real WorkProduct/ApprovalRequest state change, and vice versa.
Every entry point catches its own exceptions and logs rather than raising,
matching `mission_control_bus.add_global_listener()`'s contract for the
mission-event path and staying consistent for the other two call sites.
"""
from datetime import datetime, timezone
import logging
from typing import Any, Optional

from core.snowflake import generate_snowflake_id
from db.session import SessionLocal
from workforce.agents.orchestration.mission_control_bus import MISSION_COMPLETED
from workforce.agents.proposals.models import AgentProposal

logger = logging.getLogger(__name__)

CREATED_BY = "learning_review_worker"


class LearningReviewWorker:
    """See module docstring for the safety invariant this class must uphold."""

    # ---- Entry point 1: mission_control_bus global listener --------------

    @classmethod
    def on_mission_terminal_event(cls, event: dict[str, Any]) -> None:
        """Registered via `mission_control_bus.add_global_listener()` - must
        stay synchronous and must never raise (see that method's docstring).
        Only MISSION_COMPLETED carries a real trajectory worth reviewing;
        MISSION_FAILED's payload is just an error code/message, nothing to
        extract a candidate from."""
        if event.get("event_type") != MISSION_COMPLETED:
            return
        try:
            cls._review_completed_mission(event)
        except Exception:
            logger.exception(
                "[LearningReviewWorker] failed to review completed mission run_id=%s",
                event.get("run_id"),
            )

    @classmethod
    def _review_completed_mission(cls, event: dict[str, Any]) -> None:
        from workforce.agents.governance.models import AgentRun, AgentToolCall
        from founder_os.outcomes.models import OutcomeRun
        from workforce.skills.service import SkillLifecycleService

        run_id_raw = event.get("run_id")
        workspace_id_raw = event.get("workspace_id")
        if not run_id_raw or not workspace_id_raw:
            return
        mission_id = int(run_id_raw)
        workspace_id = int(workspace_id_raw)

        result = (event.get("data") or {}).get("result") or {}
        goal = result.get("goal") or ""
        diagnosis = result.get("diagnosis") or ""
        specialist_reports: dict[str, Any] = result.get("specialist_reports") or {}
        action_plan: list = result.get("action_plan") or []
        domains = sorted(specialist_reports.keys())
        if not domains:
            # No specialist was actually delegated to - nothing trajectory-shaped to learn from.
            return

        db = SessionLocal()
        try:
            child_run_ids = [
                r[0] for r in db.query(AgentRun.id).filter(AgentRun.parent_run_id == mission_id).all()
            ]
            tool_call_run_ids = [mission_id, *child_run_ids]
            tool_calls = (
                db.query(AgentToolCall.id, AgentToolCall.tool_name)
                .filter(AgentToolCall.run_id.in_(tool_call_run_ids))
                .all()
            )
            tools_used = sorted({t.tool_name for t in tool_calls})
            evidence_ids = [str(t.id) for t in tool_calls] + [str(cid) for cid in child_run_ids]

            source_outcome_id: Optional[int] = None
            agent_run = db.query(AgentRun).filter(AgentRun.id == mission_id).first()
            if agent_run and agent_run.outcome_run_id:
                outcome_run = db.query(OutcomeRun).filter(OutcomeRun.id == agent_run.outcome_run_id).first()
                if outcome_run:
                    source_outcome_id = outcome_run.outcome_id

            domain = domains[0] if len(domains) == 1 else "cross_domain"
            sop_lines = [f"Goal: {goal}", f"Diagnosis: {diagnosis}"]
            for i, step in enumerate(action_plan, start=1):
                sop_lines.append(f"{i}. {step}")
            extracted_sop = "\n".join(sop_lines)

            now = datetime.now(timezone.utc)
            proposal = AgentProposal(
                id=generate_snowflake_id(),
                workspace_id=workspace_id,
                company_id=workspace_id,
                run_id=mission_id,
                proposal_type="learning_candidate",
                created_by_agent=CREATED_BY,
                title=f"Learning candidate from completed mission: {goal[:120] or mission_id}",
                description=diagnosis or None,
                payload_jsonb={
                    "source_type": "mission_completed",
                    "mission_id": str(mission_id),
                    "domains": domains,
                    "tools_used": tools_used,
                    "specialist_reports": specialist_reports,
                },
                status="pending",
                domain=domain,
                target_key=f"mission:{mission_id}",
                evidence_ids_jsonb=evidence_ids or None,
                source_outcome_id=source_outcome_id,
                created_at=now,
                updated_at=now,
            )
            db.add(proposal)
            db.commit()

            if extracted_sop.strip():
                try:
                    SkillLifecycleService.create_candidate_from_trajectory(
                        db=db,
                        workspace_id=workspace_id,
                        domain=domain,
                        proposed_name=f"trajectory.{domain}.{mission_id}",
                        extracted_sop=extracted_sop,
                        mission_id=str(mission_id),
                        run_id=mission_id,
                        tools_used=tools_used,
                    )
                except Exception:
                    # Safety-scan rejection or any other failure here must not
                    # take down the AgentProposal write above, which already
                    # committed - the human-reviewable candidate still exists.
                    logger.exception(
                        "[LearningReviewWorker] skill trajectory candidate extraction failed for mission_id=%s",
                        mission_id,
                    )
        finally:
            db.close()

    # ---- Entry points 2 & 3: rejection/revision hooks ---------------------

    @classmethod
    def on_work_product_rejected(
        cls,
        *,
        workspace_id: int,
        work_product_id: int,
        agent_key: str,
        title: str,
        feedback: str,
        run_id: Optional[int] = None,
        rejection_kind: str = "revision_requested",
    ) -> None:
        """Call after a WorkProduct is rejected/sent back for revision - the
        founder's real feedback text is evidence-grounded input for a
        learning candidate, never fabricated."""
        try:
            cls._write_rejection_candidate(
                workspace_id=workspace_id,
                domain=agent_key,
                target_key=f"work_product:{work_product_id}",
                title=f"Learning candidate from {rejection_kind} work product: {title[:100]}",
                description=feedback,
                payload={
                    "source_type": f"work_product_{rejection_kind}",
                    "work_product_id": str(work_product_id),
                    "agent_key": agent_key,
                    "feedback": feedback,
                },
                run_id=run_id,
            )
        except Exception:
            logger.exception(
                "[LearningReviewWorker] failed to review rejected work_product_id=%s",
                work_product_id,
            )

    @classmethod
    def on_approval_rejected(
        cls,
        *,
        workspace_id: int,
        request_id: int,
        agent_key: str,
        action_type: str,
        reason: str,
        run_id: Optional[int] = None,
        rejection_kind: str = "rejected",
    ) -> None:
        try:
            cls._write_rejection_candidate(
                workspace_id=workspace_id,
                domain=agent_key,
                target_key=f"approval_request:{request_id}",
                title=f"Learning candidate from {rejection_kind} approval: {action_type}",
                description=reason,
                payload={
                    "source_type": f"approval_{rejection_kind}",
                    "approval_request_id": str(request_id),
                    "agent_key": agent_key,
                    "action_type": action_type,
                    "reason": reason,
                },
                run_id=run_id,
            )
        except Exception:
            logger.exception(
                "[LearningReviewWorker] failed to review rejected approval request_id=%s",
                request_id,
            )

    @classmethod
    def _write_rejection_candidate(
        cls,
        *,
        workspace_id: int,
        domain: str,
        target_key: str,
        title: str,
        description: str,
        payload: dict[str, Any],
        run_id: Optional[int],
    ) -> None:
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            proposal = AgentProposal(
                id=generate_snowflake_id(),
                workspace_id=workspace_id,
                company_id=workspace_id,
                run_id=run_id,
                proposal_type="learning_candidate",
                created_by_agent=CREATED_BY,
                title=title[:255],
                description=description or None,
                payload_jsonb=payload,
                status="pending",
                domain=domain,
                target_key=target_key,
                created_at=now,
                updated_at=now,
            )
            db.add(proposal)
            db.commit()
        finally:
            db.close()
