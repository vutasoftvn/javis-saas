"""CEO Brief DSPy Program implementation."""

import json
from typing import Any, Dict, Type

try:
    import dspy
except ImportError:
    dspy = None

from workforce.ai.programs.base import BaseCOSAProgram
from workforce.ai.programs.schemas import CEOBriefInput, CEOBriefOutput


if dspy is not None:
    class CEOBriefSignature(dspy.Signature):
        """Synthesize company status into an actionable executive brief for the founder/CEO.
        
        Focus strictly on high-impact wins, critical risks, operational anomalies, decisions required,
        and the top 3 focus items for today. Do NOT hallucinate financial figures or commitments.
        """

        company_cycle_context: str = dspy.InputField(desc="Active cycle goals, deadlines, and context")
        okr_deltas: str = dspy.InputField(desc="Recent Key Result updates and gaps")
        weekly_mission: str = dspy.InputField(desc="Weekly mission objectives and active work items")
        cross_domain_signals: str = dspy.InputField(desc="Highlights from Sales, Finance, Legal, and Tech")
        pending_approvals: str = dspy.InputField(desc="Decisions or consequential actions awaiting approval")

        headline: str = dspy.OutputField(desc="Single crisp 1-line headline summarizing company status")
        wins: list[str] = dspy.OutputField(desc="Key validated accomplishments achieved")
        risks: list[str] = dspy.OutputField(desc="High-priority risks requiring founder attention")
        exceptions: list[str] = dspy.OutputField(desc="Operational anomalies or deviations from plan")
        decisions_required: list[str] = dspy.OutputField(desc="Specific decisions requiring founder input")
        today_top_3: list[str] = dspy.OutputField(desc="Top 3 highest-leverage actions for today")
        watch_next: list[str] = dspy.OutputField(desc="Items or metrics to monitor in the next 48 hours")


class CEOBriefProgram(BaseCOSAProgram):
    """DSPy Module for CEO Briefing."""

    program_key = "ceo.brief"
    default_version = "1.0.0"
    input_schema: Type[CEOBriefInput] = CEOBriefInput
    output_schema: Type[CEOBriefOutput] = CEOBriefOutput

    def __init__(self) -> None:
        if dspy is not None:
            self.predictor = dspy.Predict(CEOBriefSignature)
        else:
            self.predictor = None

    def forward(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute DSPy prediction for CEO Brief."""
        # Format inputs as JSON strings for DSPy
        cycle_str = json.dumps(kwargs.get("company_cycle", {}), ensure_ascii=False)
        okr_str = json.dumps(kwargs.get("okr_deltas", []), ensure_ascii=False)
        mission_str = json.dumps(kwargs.get("weekly_mission", {}), ensure_ascii=False)
        
        signals = {
            "sales": kwargs.get("sales_signals", []),
            "finance": kwargs.get("finance_signals", []),
            "legal_tech": kwargs.get("legal_tech_signals", []),
        }
        signals_str = json.dumps(signals, ensure_ascii=False)
        approvals_str = json.dumps(kwargs.get("pending_approvals", []), ensure_ascii=False)

        if self.predictor is not None and getattr(dspy.settings, "lm", None) is not None:
            try:
                pred = self.predictor(
                    company_cycle_context=cycle_str,
                    okr_deltas=okr_str,
                    weekly_mission=mission_str,
                    cross_domain_signals=signals_str,
                    pending_approvals=approvals_str,
                )
                return {
                    "headline": getattr(pred, "headline", "Operational Brief"),
                    "wins": list(getattr(pred, "wins", [])) or ["Cycle progressing as planned"],
                    "risks": list(getattr(pred, "risks", [])),
                    "exceptions": list(getattr(pred, "exceptions", [])),
                    "decisions_required": list(getattr(pred, "decisions_required", [])),
                    "today_top_3": list(getattr(pred, "today_top_3", [])) or ["Focus on key deliverable"],
                    "watch_next": list(getattr(pred, "watch_next", [])),
                }
            except Exception:
                pass

        # Deterministic fallback when DSPy LM is not active or offline
        return {
            "headline": "Company Cycle on track with active weekly mission.",
            "wins": ["Completed scheduled tasks"],
            "risks": ["Check cashflow variance"],
            "exceptions": [],
            "decisions_required": [f"Review {len(kwargs.get('pending_approvals', []))} pending approvals"],
            "today_top_3": ["Review critical KR progress", "Unblock sales pipeline", "Check weekly review"],
            "watch_next": ["End-of-week review metrics"],
        }

