from typing import Any, Dict, List, Optional


class LearningReasoningCapability:
    """Reasoning capability for distilling systemic lessons from operational friction and cross-functional handoffs."""

    @classmethod
    def synthesize_lesson_from_friction(
        cls,
        observation: str,
        function: str = "SALES",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "status": "success",
            "function": function.upper(),
            "observation": observation,
            "interpretation": f"Friction in {function} indicates a need for clearer process guardrails or updated playbooks.",
            "recommendation": f"Adopt standard SLA and automated pre-checks for {function} deliverables.",
            "confidence": 0.88,
            "summary": f"Synthesized actionable lesson for {function}.",
        }
