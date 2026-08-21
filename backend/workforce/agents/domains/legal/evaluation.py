from typing import Any, Dict, List, Optional
from workforce.agents.domains.legal.reasoning import LEGAL_DISCLAIMER


class LegalEvaluationCapability:
    """Evaluation capability for verifying compliance posture, evidence citation presence, and disclaimer checks."""

    @classmethod
    def evaluate_legal_output(
        cls,
        output_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        has_citations = bool(output_data.get("citations"))
        has_disclaimer = bool(output_data.get("disclaimer"))
        is_valid = has_citations and has_disclaimer

        if not is_valid:
            raise ValueError(
                f"Legal output verification failed: citations={has_citations}, disclaimer={has_disclaimer} (§22)."
            )

        return {
            "status": "success",
            "passed_validation": True,
            "has_citations": has_citations,
            "has_disclaimer": has_disclaimer,
            "disclaimer": LEGAL_DISCLAIMER,
            "summary": "Legal output successfully passed governance and citation validation.",
        }
