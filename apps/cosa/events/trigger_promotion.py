"""Gate enable một EventTriggerRule bằng immutable eval/promotion evidence
(P1 Task 8). Nối `agent_core.evals.PromotionGate` (chỉ trả kết quả, không tự
activate) vào quyết định enable/resolve của trigger.

- artifact-only evidence chỉ mở artifact-only rule (không proposal/write).
- write rule đòi human approval decision ngay cả khi evidence khớp.
- fingerprint (agent/skill/policy) hoặc event schema drift ⇒ reject.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from agent_core.evals.promotion import PromotionEvidence
from agent_core.evals.promotion_gate import PromotionGate

__all__ = ["GateResult", "can_enable_trigger"]

_BOUNDARY_RANK = {"artifact_only": 0, "proposal": 1, "write": 2}


@dataclass(frozen=True)
class GateResult:
    allowed: bool
    reason: Optional[str] = None
    requires_human_approval: bool = False


def can_enable_trigger(
    rule,
    evidence: Optional[PromotionEvidence],
    current_fingerprints: dict[str, str],
    *,
    policy_version: str,
) -> GateResult:
    if evidence is None or not getattr(rule, "eval_evidence_ref", None):
        return GateResult(False, "no_eval_evidence")

    gate = PromotionGate(policy_version=policy_version).check(evidence, current_fingerprints)
    if not gate.approved:
        stale = any("stale" in issue.lower() for issue in gate.blocking_issues)
        return GateResult(False, "stale_evidence" if stale else "checks_failed")

    ev_schema = evidence.check_details.get("event_schema_version")
    rule_schema = getattr(rule, "event_schema_version", ev_schema)
    if ev_schema is not None and rule_schema != ev_schema:
        return GateResult(False, "event_schema_changed")

    ev_boundary = evidence.check_details.get("action_boundary", "artifact_only")
    if _BOUNDARY_RANK[rule.mode] > _BOUNDARY_RANK.get(ev_boundary, 0):
        return GateResult(False, "action_boundary_exceeded")

    return GateResult(True, None, requires_human_approval=(rule.mode == "write"))
