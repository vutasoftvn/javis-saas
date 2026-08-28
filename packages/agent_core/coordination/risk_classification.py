from __future__ import annotations

from typing import Any

from agent_core.governance.contracts import CapabilityRisk

__all__ = ["RiskClassificationOutcome", "RiskClassifier"]


class RiskClassificationOutcome:
    def __init__(self, risk_level: CapabilityRisk, route: str, reasons: list[str]) -> None:
        self.risk_level = risk_level
        self.route = route  # "auto_start" | "needs_confirmation"
        self.reasons = reasons

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_level": self.risk_level.value,
            "route": self.route,
            "reasons": self.reasons,
        }


class RiskClassifier:
    """Framework-neutral risk classification primitive theo Master Guide §13 & §9.5."""

    HIGH_RISK_DOMAINS = frozenset(
        {"production_deploy", "legal", "payout", "banking", "billing_charge", "delete_data"}
    )

    def classify(
        self, active_domains: list[str], context: dict[str, Any] | None = None
    ) -> RiskClassificationOutcome:
        matched_high_risk = [d for d in active_domains if d in self.HIGH_RISK_DOMAINS]
        if matched_high_risk:
            return RiskClassificationOutcome(
                risk_level=CapabilityRisk.HIGH,
                route="needs_confirmation",
                reasons=[
                    f"Active domain '{d}' is classified as high-risk" for d in matched_high_risk
                ],
            )
        return RiskClassificationOutcome(
            risk_level=CapabilityRisk.LOW,
            route="auto_start",
            reasons=["All domains are standard or read-only"],
        )
