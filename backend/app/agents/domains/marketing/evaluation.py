from typing import Any, Dict, Optional


class MarketingEvaluationCapability:
    """Evaluation capability for monitoring campaign performance, ROAS, and CAC metrics."""

    @classmethod
    def evaluate_campaign_health(
        cls,
        cac: float = 45.0,
        target_cac: float = 60.0,
        conversion_rate: float = 0.035,
    ) -> Dict[str, Any]:
        is_healthy = cac <= target_cac and conversion_rate >= 0.02
        return {
            "status": "success",
            "health": "HEALTHY" if is_healthy else "NEEDS_ATTENTION",
            "metrics": {
                "cac": cac,
                "target_cac": target_cac,
                "conversion_rate": conversion_rate,
            },
            "summary": f"Marketing performance is {'HEALTHY' if is_healthy else 'NEEDS_ATTENTION'} (CAC: ${cac}, Target: ${target_cac}).",
        }
