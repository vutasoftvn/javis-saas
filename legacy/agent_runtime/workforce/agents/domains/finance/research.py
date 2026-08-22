from typing import Any, Dict, List, Optional


class FinanceResearchCapability:
    """Capability for modeling financial runway scenarios, cost cutting proposals, and revenue forecasts."""

    @classmethod
    def model_runway_scenarios(
        cls,
        current_runway_months: float = 12.5,
        target_months: int = 18,
        monthly_burn_vnd: float = 120000000.0,
    ) -> Dict[str, Any]:
        scenarios = [
            {
                "name": "Baseline (Status Quo)",
                "projected_runway_months": current_runway_months,
                "monthly_burn_vnd": monthly_burn_vnd,
                "action": "Maintain current operating expenditure profile.",
            },
            {
                "name": "Expense Optimization (-15% Burn)",
                "projected_runway_months": round(current_runway_months * 1.18, 1),
                "monthly_burn_vnd": monthly_burn_vnd * 0.85,
                "action": "Audit SaaS subscriptions and consolidate cloud/infra spend.",
            },
            {
                "name": "Revenue Accelerated Growth (+20% Monthly Inflow)",
                "projected_runway_months": round(current_runway_months * 1.35, 1),
                "monthly_burn_vnd": monthly_burn_vnd,
                "action": "Execute Sales outbound pilot and expand pipeline conversion.",
            },
        ]

        return {
            "status": "success",
            "target_months": target_months,
            "scenarios": scenarios,
            "summary": f"Modeled 3 runway extension scenarios targeting {target_months} months runway.",
        }
