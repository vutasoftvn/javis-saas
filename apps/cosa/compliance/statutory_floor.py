from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.cosa.compliance.contracts import ComplianceSnapshot


@dataclass(frozen=True)
class FloorDecision:
    action: str  # "DENY" or "CONTINUE"
    reasons: tuple[str, ...] = ()

    @classmethod
    def deny(cls, reason: str) -> FloorDecision:
        return cls(action="DENY", reasons=(reason,))

    @classmethod
    def continue_(cls) -> FloorDecision:
        return cls(action="CONTINUE", reasons=())

    @property
    def is_deny(self) -> bool:
        return self.action == "DENY"


class StatutoryFloor:
    def evaluate(
        self,
        capability_id: str,
        payload: dict[str, Any],
        snapshot: ComplianceSnapshot | dict[str, Any] | None,
    ) -> FloorDecision:
        if snapshot is None:
            return FloorDecision.deny("COMPLIANCE_SNAPSHOT_MISSING")

        mode = (
            snapshot.get("mode") if isinstance(snapshot, dict) else getattr(snapshot, "mode", None)
        )
        status = (
            snapshot.get("status")
            if isinstance(snapshot, dict)
            else getattr(snapshot, "status", None)
        )
        allowed_caps = (
            snapshot.get("allowed_capabilities")
            if isinstance(snapshot, dict)
            else getattr(snapshot, "allowed_capabilities", None)
        )
        allowed_set = set(allowed_caps or [])
        prohibited = (
            snapshot.get("prohibited_purpose")
            if isinstance(snapshot, dict)
            else getattr(snapshot, "prohibited_purpose", False)
        )

        if (
            prohibited
            or capability_id.startswith("hr.")
            or "candidate.rank" in capability_id
            or "credit.score" in capability_id
        ):
            return FloorDecision.deny("PROHIBITED_DECISION_DOMAIN")

        if status != "APPROVED_FOR_USE":
            return FloorDecision.deny("DEPLOYMENT_NOT_APPROVED")

        if mode != "ADVISORY_ONLY":
            return FloorDecision.deny("NON_ADVISORY_MODE")

        if "*" not in allowed_set and capability_id not in allowed_set:
            return FloorDecision.deny("CAPABILITY_NOT_BOUND")

        return FloorDecision.continue_()
