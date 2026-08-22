from typing import Any, Dict, List, Optional


class FinanceReasoningCapability:
    """Capability for detecting financial anomalies, analyzing burn-rate variances, and calculating runway risk."""

    @classmethod
    def detect_anomalies(
        cls,
        cash_balance: float = 1500000000.0,
        burn_rate: float = 120000000.0,
        runway_months: float = 12.5,
        budget_variance_pct: float = 8.5,
    ) -> Dict[str, Any]:
        anomalies = []
        risk_level = "low"

        if runway_months < 6.0:
            risk_level = "critical"
            anomalies.append({
                "category": "runway_danger",
                "severity": "critical",
                "message": f"Runway is critically low ({runway_months:.1f} months). Urgent expense reduction or revenue acceleration required.",
            })
        elif runway_months < 9.0:
            risk_level = "medium"
            anomalies.append({
                "category": "runway_warning",
                "severity": "medium",
                "message": f"Runway under 9 months threshold ({runway_months:.1f} months). Recommend monitoring discretionary spending.",
            })

        if budget_variance_pct > 15.0:
            anomalies.append({
                "category": "budget_overrun",
                "severity": "medium",
                "message": f"Operating expenses exceeded monthly baseline budget by {budget_variance_pct:.1f}%.",
            })

        return {
            "status": "success",
            "risk_level": risk_level,
            "anomalies_count": len(anomalies),
            "anomalies": anomalies,
            "summary": f"Financial anomaly check completed: risk level '{risk_level}', detected {len(anomalies)} anomalies.",
        }
