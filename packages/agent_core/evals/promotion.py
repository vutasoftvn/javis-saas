from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field

from agent_core.governance.contracts import PinnedSpecIdentity

__all__ = ["PromotionEvidence"]


class PromotionEvidence(BaseModel):
    """Bằng chứng bất biến cho quyết định promotion — Wave M4, theo
    COSA_MARIN_PATTERNS_INTEGRATION_AND_ADJUSTMENT_PLAN_2026-08-26.md §12.2.
    `agent_core` CHỈ tạo evidence này, KHÔNG tự quyết promote —
    PromotionDecision (quyền activate production) thuộc `services/cosa`, xem
    docs/implementation/M4_PROMOTION_CONTROL_PLANE_BOUNDARY.md."""

    evidence_id: str = Field(default_factory=lambda: f"promoevid_{uuid.uuid4().hex[:12]}")
    target_ref: PinnedSpecIdentity
    required_eval_run_ids: list[str] = Field(default_factory=list)
    observed_fingerprints: dict[str, str] = Field(default_factory=dict)
    policy_version: str
    policy_checks_passed: bool
    check_details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def is_stale(self, current_fingerprints: dict[str, str]) -> bool:
        """True nếu bất kỳ fingerprint nào (target hoặc dependency) đã quan
        sát tại thời điểm tạo evidence KHÔNG còn khớp fingerprint hiện tại —
        nghĩa là artifact đã đổi sau khi eval pass, evidence không còn tin
        cậy được cho quyết định promote (§12.2 pseudo-invariant
        `evaluated_fingerprint == current_candidate_fingerprint`)."""
        for name, observed_hash in self.observed_fingerprints.items():
            if current_fingerprints.get(name) != observed_hash:
                return True
        return False
