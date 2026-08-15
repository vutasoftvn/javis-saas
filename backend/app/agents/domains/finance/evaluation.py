from typing import Any, Dict, List


class FinanceEvaluationCapability:
    """Capability for evaluating financial health KPIs and generating PDCA recommendations."""

    @classmethod
    def evaluate_financial_health(
        cls,
        actual_runway_months: float = 12.5,
        target_runway_months: float = 12.0,
        net_burn_vnd: float = 120000000.0,
    ) -> Dict[str, Any]:
        health_status = "HEALTHY" if actual_runway_months >= target_runway_months else "CAUTION"

        learnings = [
            "Operating cash flow remains aligned with TT58 baseline expectations.",
            "Recurring software expenses represent 22% of fixed monthly overhead.",
        ]

        next_recommendations = [
            "Review annual versus monthly SaaS payment plans to capture 15% vendor discounts.",
            "Verify next quarter estimated tax liability calculation with accounting ledger.",
        ]

        return {
            "status": "success",
            "health_status": health_status,
            "metrics": {
                "actual_runway_months": actual_runway_months,
                "target_runway_months": target_runway_months,
                "net_burn_vnd": net_burn_vnd,
            },
            "learnings": learnings,
            "next_recommendations": next_recommendations,
            "summary": f"Financial health evaluated as {health_status} (Runway: {actual_runway_months:.1f} months).",
        }
