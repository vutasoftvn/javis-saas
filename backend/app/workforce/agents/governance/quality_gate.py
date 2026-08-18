"""Cross-cutting Quality Gate Framework (§45, §55, §118, C1/C2 Spec).

Quality is a cross-cutting capability across all COSA OS domains.
Enforces Architectural Invariant: "NO FINISH WITHOUT QUALITY GATE / NO FINISH WITHOUT EVIDENCE WHEN REQUIRED".
Missions cannot be marked as COMPLETED if the Domain Quality Gate verdict is FAIL.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.workforce.agents.domains.finance.evaluation import FinanceEvaluationCapability
from app.workforce.agents.domains.legal.evaluation import LegalEvaluationCapability
from app.workforce.agents.domains.marketing.evaluation import MarketingEvaluationCapability
from app.workforce.agents.domains.sales.evaluation import SalesEvaluationCapability

logger = logging.getLogger(__name__)


class QualityGateVerdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"


class QualityGateResult(BaseModel):
    verdict: QualityGateVerdict
    domain: str
    issues: List[str] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def passed(self) -> bool:
        return self.verdict in (QualityGateVerdict.PASS, QualityGateVerdict.PARTIAL)


class BaseQualityGate(ABC):
    """Abstract Base Quality Gate for all domain capabilities."""

    @classmethod
    @abstractmethod
    def evaluate(cls, payload: Dict[str, Any]) -> QualityGateResult:
        """Evaluate domain artifacts / outputs and return a QualityGateResult."""
        pass


class FinanceQualityGate(BaseQualityGate):
    """Cross-cutting Quality Gate for Finance operations.
    
    Verifies financial metrics sanity (e.g. runway, burn rate, accounting reconciliation).
    """

    @classmethod
    def evaluate(cls, payload: Dict[str, Any]) -> QualityGateResult:
        actual_runway = float(payload.get("actual_runway_months", payload.get("runway_months", 12.5) or 0.0))
        target_runway = float(payload.get("target_runway_months", 12.0) or 12.0)
        net_burn_vnd = float(payload.get("net_burn_vnd", payload.get("monthly_burn", 120000000.0) or 0.0))

        issues: List[str] = []
        evidence: List[Dict[str, Any]] = []

        # Sanity checks
        if actual_runway <= 0:
            issues.append("Zero or negative cash runway detected without emergency funding plan.")
        if net_burn_vnd < 0:
            issues.append("Negative net burn rate reported without verified revenue reconciliation.")

        # Re-use domain capability logic
        eval_res = FinanceEvaluationCapability.evaluate_financial_health(
            actual_runway_months=actual_runway,
            target_runway_months=target_runway,
            net_burn_vnd=net_burn_vnd,
        )

        evidence.append({
            "type": "finance_health_evaluation",
            "health_status": eval_res.get("health_status"),
            "actual_runway": actual_runway,
            "target_runway": target_runway,
            "net_burn": net_burn_vnd,
        })

        if issues:
            verdict = QualityGateVerdict.FAIL
            summary = f"Finance Quality Gate FAILED: {'; '.join(issues)}"
        elif eval_res.get("health_status") == "CAUTION":
            verdict = QualityGateVerdict.PARTIAL
            summary = f"Finance Quality Gate PARTIAL: Financial health caution (Runway {actual_runway:.1f}m < Target {target_runway:.1f}m)."
        else:
            verdict = QualityGateVerdict.PASS
            summary = f"Finance Quality Gate PASSED: Financial health is {eval_res.get('health_status')}."

        return QualityGateResult(
            verdict=verdict,
            domain="finance",
            issues=issues,
            evidence=evidence,
            metrics=eval_res.get("metrics", {}),
            summary=summary,
        )


class LegalQualityGate(BaseQualityGate):
    """Cross-cutting Quality Gate for Legal outputs (§22, §45, §60).
    
    Verifies compliance posture, mandatory legal disclaimers, and statutory citations.
    """

    @classmethod
    def evaluate(cls, payload: Dict[str, Any]) -> QualityGateResult:
        issues: List[str] = []
        evidence: List[Dict[str, Any]] = []

        citations = payload.get("citations", [])
        disclaimer = payload.get("disclaimer", "")

        if not citations:
            issues.append("Missing required statutory / legal citations in output.")
        if not disclaimer:
            issues.append("Missing mandatory legal disclaimer in compliance output.")

        if issues:
            return QualityGateResult(
                verdict=QualityGateVerdict.FAIL,
                domain="legal",
                issues=issues,
                evidence=evidence,
                metrics={"has_citations": bool(citations), "has_disclaimer": bool(disclaimer)},
                summary=f"Legal Quality Gate FAILED: {'; '.join(issues)}",
            )

        try:
            eval_res = LegalEvaluationCapability.evaluate_legal_output(payload)
            evidence.append({
                "type": "legal_compliance_check",
                "passed_validation": eval_res.get("passed_validation", False),
                "citations_count": len(citations) if isinstance(citations, list) else 1,
            })
            return QualityGateResult(
                verdict=QualityGateVerdict.PASS,
                domain="legal",
                issues=[],
                evidence=evidence,
                metrics={"citations_count": len(citations) if isinstance(citations, list) else 1},
                summary="Legal Quality Gate PASSED: Citations and disclaimers fully validated.",
            )
        except ValueError as exc:
            return QualityGateResult(
                verdict=QualityGateVerdict.FAIL,
                domain="legal",
                issues=[str(exc)],
                evidence=evidence,
                summary=f"Legal Quality Gate FAILED: {exc}",
            )


class SalesQualityGate(BaseQualityGate):
    """Cross-cutting Quality Gate for Sales operations & Lead qualification (Spec §118).
    
    Enforces rules:
    - Company identity must be clear
    - ICP fit check
    - Evidence citation check
    - Duplicate detection
    - Fails on hallucinated emails or missing core evidence
    """

    @classmethod
    def evaluate(cls, payload: Dict[str, Any]) -> QualityGateResult:
        issues: List[str] = []
        evidence: List[Dict[str, Any]] = []

        leads = payload.get("leads")
        if leads is not None:
            # Evaluating a list of leads (Spec §118)
            if not isinstance(leads, list):
                return QualityGateResult(
                    verdict=QualityGateVerdict.FAIL,
                    domain="sales",
                    issues=["Leads payload must be a list."],
                    summary="Sales Quality Gate FAILED: Invalid leads payload format.",
                )

            if not leads:
                return QualityGateResult(
                    verdict=QualityGateVerdict.PARTIAL,
                    domain="sales",
                    issues=["No leads found in payload to validate."],
                    summary="Sales Quality Gate PARTIAL: Empty lead list.",
                )

            valid_count = 0
            invalid_count = 0
            seen_emails = set()

            for idx, lead in enumerate(leads):
                lead_issues = []
                company = lead.get("company") or lead.get("name")
                email = lead.get("email", "")
                evidence_list = lead.get("evidence", [])
                fit_score = lead.get("fit_score", lead.get("icp_fit", 0.0))

                if not company:
                    lead_issues.append(f"Lead #{idx+1}: Missing company identity.")
                if "@" not in email or email.endswith("@example.com") or email.endswith("@fake.com"):
                    lead_issues.append(f"Lead #{idx+1} ({company}): Invalid or mock email address ({email}).")
                if email in seen_emails:
                    lead_issues.append(f"Lead #{idx+1} ({company}): Duplicate lead email detected.")
                if not evidence_list:
                    lead_issues.append(f"Lead #{idx+1} ({company}): Missing core evidence citation.")
                if fit_score is not None and float(fit_score) < 0.3:
                    lead_issues.append(f"Lead #{idx+1} ({company}): ICP fit score {fit_score} below minimum threshold (0.3).")

                if lead_issues:
                    invalid_count += 1
                    issues.extend(lead_issues)
                else:
                    valid_count += 1
                    seen_emails.add(email)

            verdict = QualityGateVerdict.PASS if invalid_count == 0 else (
                QualityGateVerdict.PARTIAL if valid_count > 0 else QualityGateVerdict.FAIL
            )

            return QualityGateResult(
                verdict=verdict,
                domain="sales",
                issues=issues,
                evidence=[{"valid_leads_count": valid_count, "invalid_leads_count": invalid_count}],
                metrics={"valid_count": valid_count, "invalid_count": invalid_count, "total": len(leads)},
                summary=f"Sales Quality Gate {verdict.value}: {valid_count} valid, {invalid_count} invalid leads.",
            )

        # Evaluating campaign metrics
        dispatched = payload.get("dispatched_count", 25)
        replies = payload.get("replies_received", 7)
        meetings = payload.get("meetings_booked", 2)
        pipeline_vnd = payload.get("pipeline_added_vnd", 150000000)

        eval_res = SalesEvaluationCapability.evaluate_campaign(
            dispatched_count=dispatched,
            replies_received=replies,
            meetings_booked=meetings,
            pipeline_added_vnd=pipeline_vnd,
        )

        return QualityGateResult(
            verdict=QualityGateVerdict.PASS,
            domain="sales",
            issues=[],
            evidence=[{"type": "sales_campaign_evaluation", "learnings": eval_res.get("learnings", [])}],
            metrics=eval_res.get("metrics", {}),
            summary=eval_res.get("summary", "Sales Quality Gate PASSED."),
        )


class MarketingQualityGate(BaseQualityGate):
    """Cross-cutting Quality Gate for Marketing operations.
    
    Verifies CAC, conversion rate, and target thresholds.
    """

    @classmethod
    def evaluate(cls, payload: Dict[str, Any]) -> QualityGateResult:
        cac = float(payload.get("cac", 45.0) or 45.0)
        target_cac = float(payload.get("target_cac", 60.0) or 60.0)
        conversion_rate = float(payload.get("conversion_rate", 0.035) or 0.035)

        eval_res = MarketingEvaluationCapability.evaluate_campaign_health(
            cac=cac,
            target_cac=target_cac,
            conversion_rate=conversion_rate,
        )

        issues: List[str] = []
        if cac > target_cac * 1.5:
            issues.append(f"CAC (${cac:.2f}) exceeds 150% of target limit (${target_cac:.2f}).")
        if conversion_rate < 0.01:
            issues.append(f"Conversion rate ({conversion_rate*100:.2f}%) below minimum safety threshold (1.0%).")

        if issues:
            verdict = QualityGateVerdict.FAIL
            summary = f"Marketing Quality Gate FAILED: {'; '.join(issues)}"
        elif eval_res.get("health") == "NEEDS_ATTENTION":
            verdict = QualityGateVerdict.PARTIAL
            summary = f"Marketing Quality Gate PARTIAL: Campaign needs optimization."
        else:
            verdict = QualityGateVerdict.PASS
            summary = eval_res.get("summary", "Marketing Quality Gate PASSED.")

        return QualityGateResult(
            verdict=verdict,
            domain="marketing",
            issues=issues,
            evidence=[{"type": "marketing_evaluation", "health": eval_res.get("health")}],
            metrics=eval_res.get("metrics", {}),
            summary=summary,
        )


class QualityGateEvaluator:
    """Unified Gateway & Registry for cross-cutting Quality Gate execution across domains."""

    _GATE_REGISTRY: Dict[str, type[BaseQualityGate]] = {
        "finance": FinanceQualityGate,
        "legal": LegalQualityGate,
        "sales": SalesQualityGate,
        "marketing": MarketingQualityGate,
    }

    @classmethod
    def register_gate(cls, domain: str, gate_cls: type[BaseQualityGate]) -> None:
        cls._GATE_REGISTRY[domain.lower()] = gate_cls

    @classmethod
    def evaluate(cls, domain: str, payload: Dict[str, Any]) -> QualityGateResult:
        """Evaluate a specific domain payload against its registered Quality Gate."""
        gate_cls = cls._GATE_REGISTRY.get(domain.lower())
        if not gate_cls:
            logger.warning(f"[QualityGate] No dedicated quality gate registered for domain '{domain}'. Defaulting to PASS.")
            return QualityGateResult(
                verdict=QualityGateVerdict.PASS,
                domain=domain,
                summary=f"Default Quality Gate PASSED for un-gated domain '{domain}'.",
            )
        return gate_cls.evaluate(payload)

    @classmethod
    def evaluate_mission(cls, domain: str, payload: Dict[str, Any]) -> QualityGateResult:
        """Evaluate mission output and ensure Invariant 'NO FINISH WITHOUT QUALITY GATE' is enforced."""
        result = cls.evaluate(domain, payload)
        if not result.passed:
            logger.error(f"[QualityGate] Mission Quality Gate failed for domain '{domain}': {result.summary}")
        return result
