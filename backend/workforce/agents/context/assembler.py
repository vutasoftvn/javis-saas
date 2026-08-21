"""CofounderContextAssembler — Minimum Viable Context per intent (G2 §7.2, G3 §12).

`build_agent_context` (builder.py, in this same package) already existed but
doesn't fit this job: it always eager-loads a fixed 4 sections (sales,
finance, okrs, projects) regardless of intent — exactly what G2 §7.2 says
NOT to do ("Không load toàn bộ database"). `ProgressiveContextCompiler`
(compiler.py) DOES respect intent-based scoping but reads virtual markdown
files, not the real DB tables this assembler needs (TwelveWeekCycle,
WeeklyPlan, FounderDecision, ApprovalRequest, Outcome, EvidenceItem...).
Neither is a drop-in fit, so this is a new, focused assembler — but it
reuses real data sources wherever they already exist (SPECIALIST_REGISTRY's
fetch_snapshot functions for business_signals) rather than re-querying.

Every field is graceful-degrading (a failed sub-query yields an empty/absent
value, never raises) — a context bundle is best-effort background material
for a synthesis prompt, not a request that should itself fail because one
optional signal was unavailable.
"""
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from workforce.routing.deterministic import Intent

# Intents that need the full bundle (founder-facing strategic/coordination intents).
_FULL_CONTEXT_INTENTS = frozenset({
    Intent.FOUNDER_REVIEW,
    Intent.FOUNDER_DECISION,
    Intent.FOUNDER_COMMAND,
    Intent.FOUNDER_REFLECTION,
})

# Intents that map to exactly one business_signals domain.
_DOMAIN_INTENTS = {
    Intent.SALES: "sales",
    Intent.FINANCE: "finance",
    Intent.MARKETING: "marketing",
    Intent.LEGAL: "legal",
}


class CofounderContextAssembler:
    """Builds the G2 §7.2-shaped context bundle, scoped to what `intent` actually needs."""

    @classmethod
    def assemble(
        cls,
        db: Session,
        workspace_id: int,
        intent: Intent,
        project_id: Optional[int] = None,
        business_signal_domains: Optional[tuple[str, ...]] = None,
    ) -> dict[str, Any]:
        """`business_signal_domains`, when given, overrides which domains
        business_signals covers for the "full context" intents — e.g. a
        mission that only delegates to "finance" shouldn't have this bundle
        silently also fetch sales/legal snapshots nothing asked for. Falls
        back to the default (sales+finance+legal) when not given, e.g. for
        a caller that wants the bundle without having run a delegation loop
        first."""
        if intent == Intent.GREETING:
            return {}

        if intent in _FULL_CONTEXT_INTENTS:
            domains_needed = tuple(business_signal_domains) if business_signal_domains else ("sales", "finance", "legal")
        elif intent in _DOMAIN_INTENTS:
            domains_needed = (_DOMAIN_INTENTS[intent],)
        else:
            # GENERAL_CHAT and anything not explicitly scoped above: minimal only.
            return {
                "workspace": cls._workspace(db, workspace_id),
                "founder_profile": cls._founder_profile(db, workspace_id),
            }

        context: dict[str, Any] = {
            "workspace": cls._workspace(db, workspace_id),
            "project": cls._current_project(db, workspace_id, project_id),
            "stage": cls._stage(db, workspace_id),
            "founder_profile": cls._founder_profile(db, workspace_id),
            "active_12wy": cls._active_12wy(db, workspace_id),
            "pending_decisions": cls._pending_decisions(db, workspace_id),
            "business_signals": cls._business_signals(db, workspace_id, domains_needed),
        }

        if intent in _FULL_CONTEXT_INTENTS:
            context["weekly_plan"] = cls._weekly_plan(db, workspace_id, context["active_12wy"])
            context["top_blockers"] = context["weekly_plan"].get("blockers") or [] if context["weekly_plan"] else []
            context["pending_approvals"] = cls._pending_approvals(db, workspace_id)
            context["evidence"] = cls._recent_evidence(db, workspace_id)
            context["recent_outcomes"] = cls._recent_outcomes(db, workspace_id)

        return context

    # ------------------------------------------------------------------
    # Individual field builders — each independently try/except-safe so one
    # missing/erroring table never takes down the whole bundle.
    # ------------------------------------------------------------------

    @staticmethod
    def _workspace(db: Session, workspace_id: int) -> dict[str, Any]:
        try:
            from platform_core.auth.models import Workspace
            ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
            if not ws:
                return {}
            return {"id": str(ws.id), "name": ws.name, "company_stage": ws.company_stage}
        except Exception:
            return {}

    @staticmethod
    def _founder_profile(db: Session, workspace_id: int) -> dict[str, Any]:
        try:
            from platform_core.auth.models import Workspace, WorkspaceMember, User
            member = (
                db.query(WorkspaceMember)
                .filter(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.role == "admin")
                .first()
            )
            if not member:
                return {}
            user = db.query(User).filter(User.id == member.user_id).first()
            if not user:
                return {}
            return {"display_name": user.display_name}
        except Exception:
            return {}

    @staticmethod
    def _current_project(db: Session, workspace_id: int, project_id: Optional[int]) -> dict[str, Any]:
        try:
            from founder_os.strategy.models import Project
            query = db.query(Project).filter(Project.workspace_id == workspace_id)
            if project_id is not None:
                query = query.filter(Project.id == project_id)
            else:
                query = query.filter(Project.status == "active")
            project = query.order_by(desc(Project.created_at)).first()
            if not project:
                return {}
            return {
                "id": str(project.id),
                "title": project.title,
                "description": project.description,
                "status": project.status,
                "project_stage": project.project_stage,
            }
        except Exception:
            return {}

    @staticmethod
    def _stage(db: Session, workspace_id: int) -> dict[str, Any]:
        try:
            from platform_core.auth.models import Workspace
            ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
            return {"company_stage": ws.company_stage} if ws else {}
        except Exception:
            return {}

    @staticmethod
    def _active_12wy(db: Session, workspace_id: int) -> dict[str, Any]:
        try:
            from founder_os.strategy.models import TwelveWeekCycle
            cycle = (
                db.query(TwelveWeekCycle)
                .filter(TwelveWeekCycle.workspace_id == workspace_id, TwelveWeekCycle.status == "ACTIVE")
                .order_by(desc(TwelveWeekCycle.created_at))
                .first()
            )
            if not cycle:
                return {}
            return {
                "id": str(cycle.id),
                "theme": cycle.theme,
                "vision_statement": cycle.vision_statement,
                "current_week": cycle.current_week,
                "duration_weeks": cycle.duration_weeks,
            }
        except Exception:
            return {}

    @staticmethod
    def _weekly_plan(db: Session, workspace_id: int, active_12wy: dict[str, Any]) -> dict[str, Any]:
        if not active_12wy:
            return {}
        try:
            from founder_os.strategy.models import WeeklyPlan
            cycle_id = int(active_12wy["id"])
            plan = (
                db.query(WeeklyPlan)
                .filter(WeeklyPlan.cycle_id == cycle_id)
                .order_by(desc(WeeklyPlan.week_no))
                .first()
            )
            if not plan:
                return {}
            return {
                "week_no": plan.week_no,
                "focus": plan.focus,
                "mission": plan.mission,
                "blockers": list((plan.blockers_jsonb or {}).values()) if isinstance(plan.blockers_jsonb, dict) else (plan.blockers_jsonb or []),
            }
        except Exception:
            return {}

    @staticmethod
    def _pending_decisions(db: Session, workspace_id: int, limit: int = 5) -> list[dict[str, Any]]:
        try:
            from workforce.models import FounderDecision
            rows = (
                db.query(FounderDecision)
                .filter(FounderDecision.workspace_id == workspace_id, FounderDecision.status == "PENDING")
                .order_by(desc(FounderDecision.created_at))
                .limit(limit)
                .all()
            )
            return [{"id": str(r.id), "domain": r.domain, "question": r.question} for r in rows]
        except Exception:
            return []

    @staticmethod
    def _pending_approvals(db: Session, workspace_id: int, limit: int = 5) -> list[dict[str, Any]]:
        try:
            from workforce.models import ApprovalRequest
            rows = (
                db.query(ApprovalRequest)
                .filter(ApprovalRequest.workspace_id == workspace_id, ApprovalRequest.status == "PENDING")
                .order_by(desc(ApprovalRequest.created_at))
                .limit(limit)
                .all()
            )
            return [{"id": str(r.id), "action_type": r.action_type, "risk_level": r.risk_level} for r in rows]
        except Exception:
            return []

    @staticmethod
    def _recent_evidence(db: Session, workspace_id: int, limit: int = 5) -> list[dict[str, Any]]:
        try:
            from founder_os.strategy.models import EvidenceItem
            rows = (
                db.query(EvidenceItem)
                .filter(EvidenceItem.workspace_id == workspace_id)
                .order_by(desc(EvidenceItem.captured_at))
                .limit(limit)
                .all()
            )
            return [{"id": str(r.id), "title": r.title, "source_type": r.source_type, "reliability": r.reliability} for r in rows]
        except Exception:
            return []

    @staticmethod
    def _recent_outcomes(db: Session, workspace_id: int, limit: int = 5) -> list[dict[str, Any]]:
        try:
            from founder_os.outcomes.models import Outcome
            rows = (
                db.query(Outcome)
                .filter(Outcome.workspace_id == workspace_id)
                .order_by(desc(Outcome.updated_at))
                .limit(limit)
                .all()
            )
            return [{"id": str(r.id), "title": r.title, "status": r.status} for r in rows]
        except Exception:
            return []

    @staticmethod
    def _business_signals(db: Session, workspace_id: int, domains: tuple[str, ...]) -> dict[str, Any]:
        # Reuses SPECIALIST_REGISTRY's fetch_snapshot — the same real,
        # already-governance-audited data source chief_of_staff.py's
        # delegation loop uses, so this bundle never carries a second,
        # divergent snapshot of the same domain.
        from workforce.agents.orchestration.specialist_registry import SPECIALIST_REGISTRY


        signals: dict[str, Any] = {}
        for domain in domains:
            spec = SPECIALIST_REGISTRY.get(domain)
            if spec is None:
                continue
            try:
                signals[domain] = spec.fetch_snapshot(db, workspace_id)
            except Exception:
                signals[domain] = {"status": "error"}
        return signals
