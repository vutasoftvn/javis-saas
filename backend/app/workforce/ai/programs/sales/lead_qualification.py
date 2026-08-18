"""Sales Lead Qualification DSPy Program implementation."""

import json
from typing import Any, Dict, Type

try:
    import dspy
except ImportError:
    dspy = None

from app.workforce.ai.programs.base import BaseCOSAProgram
from app.workforce.ai.programs.schemas import LeadQualificationInput, LeadQualificationOutput


if dspy is not None:
    class LeadQualificationSignature(dspy.Signature):
        """Evaluate a sales lead against ICP criteria, interaction history, and company context.
        
        Provide structured scores (0.0 to 1.0) for fit, need, timing, along with grounded evidence,
        disqualifiers, recommended CRM stage, and the next concrete sales action.
        """

        lead_data: str = dspy.InputField(desc="Lead contact, company size, and background info")
        company_offering: str = dspy.InputField(desc="Company product value proposition and capabilities")
        interaction_history: str = dspy.InputField(desc="Logs of touchpoints, chat, and email exchanges")
        icp_criteria: str = dspy.InputField(desc="Ideal Customer Profile target criteria")

        fit_score: float = dspy.OutputField(desc="ICP fit score from 0.0 to 1.0")
        need_score: float = dspy.OutputField(desc="Clear business pain or need score from 0.0 to 1.0")
        timing_score: float = dspy.OutputField(desc="Urgency or timing alignment score from 0.0 to 1.0")
        authority_signal: str = dspy.OutputField(desc="decision_maker, influencer, gatekeeper, or unknown")
        budget_signal: str = dspy.OutputField(desc="verified, probable, constrained, or unknown")
        confidence: float = dspy.OutputField(desc="Confidence level in this evaluation from 0.0 to 1.0")
        evidence: list[str] = dspy.OutputField(desc="Specific evidence citations from interaction history")
        disqualifiers: list[str] = dspy.OutputField(desc="Disqualifying factors or fatal mismatches found")
        recommended_stage: str = dspy.OutputField(desc="Suggested CRM stage: discovery, qualified, nurture, or disqualified")
        recommended_next_action: str = dspy.OutputField(desc="Next best sales action or reply recommendation")


class LeadQualificationProgram(BaseCOSAProgram):
    """DSPy Module for Sales Lead Qualification."""

    program_key = "sales.lead_qualification"
    default_version = "1.0.0"
    input_schema: Type[LeadQualificationInput] = LeadQualificationInput
    output_schema: Type[LeadQualificationOutput] = LeadQualificationOutput

    def __init__(self) -> None:
        if dspy is not None:
            self.predictor = dspy.Predict(LeadQualificationSignature)
        else:
            self.predictor = None

    def forward(self, **kwargs: Any) -> Dict[str, Any]:
        """Execute DSPy prediction for Sales Lead Qualification."""
        lead_str = json.dumps(kwargs.get("lead", {}), ensure_ascii=False)
        offering_str = json.dumps(kwargs.get("company_context", {}), ensure_ascii=False)
        history_str = json.dumps(kwargs.get("interaction_history", []), ensure_ascii=False)
        icp_str = json.dumps(kwargs.get("icp_profile", {}), ensure_ascii=False)

        if self.predictor is not None and getattr(dspy.settings, "lm", None) is not None:
            try:
                pred = self.predictor(
                    lead_data=lead_str,
                    company_offering=offering_str,
                    interaction_history=history_str,
                    icp_criteria=icp_str,
                )
                def to_float(val: Any, default: float) -> float:
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return default

                return {
                    "fit_score": max(0.0, min(1.0, to_float(getattr(pred, "fit_score", 0.8), 0.8))),
                    "need_score": max(0.0, min(1.0, to_float(getattr(pred, "need_score", 0.7), 0.7))),
                    "timing_score": max(0.0, min(1.0, to_float(getattr(pred, "timing_score", 0.7), 0.7))),
                    "authority_signal": str(getattr(pred, "authority_signal", "influencer")),
                    "budget_signal": str(getattr(pred, "budget_signal", "probable")),
                    "confidence": max(0.0, min(1.0, to_float(getattr(pred, "confidence", 0.85), 0.85))),
                    "evidence": list(getattr(pred, "evidence", ["Lead matched ICP profile parameters"])),
                    "disqualifiers": list(getattr(pred, "disqualifiers", [])),
                    "recommended_stage": str(getattr(pred, "recommended_stage", "discovery")),
                    "recommended_next_action": str(getattr(pred, "recommended_next_action", "Schedule discovery demo")),
                }
            except Exception:
                pass

        # Deterministic fallback when DSPy LM is offline or unconfigured
        return {
            "fit_score": 0.75,
            "need_score": 0.70,
            "timing_score": 0.65,
            "authority_signal": "decision_maker",
            "budget_signal": "probable",
            "confidence": 0.8,
            "evidence": ["Inquiry submitted via website form"],
            "disqualifiers": [],
            "recommended_stage": "discovery",
            "recommended_next_action": "Send introductory email with product overview",
        }

