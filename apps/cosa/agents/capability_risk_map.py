"""Ánh xạ capability_id -> CapabilityRisk cho bộ classifier autonomy (WGA).

Dùng khi run phân rã mục tiêu gắn `capability_risk` cho từng execution-plan item
trước khi POST sang services/company (nơi classifier thuần chạy). Không tự đoán
risk — đọc trực tiếp từ `CapabilitySpec.risk` của các capability đã đăng ký.
"""

from __future__ import annotations

from typing import Literal

from apps.cosa.capabilities import (
    ENGAGEMENT_ASSIGNMENT_WRITE_SPEC,
    ENGAGEMENT_MESSAGE_SEND_SPEC,
    FINANCE_TRANSACTION_RECORD_SPEC,
    LEGAL_APPLICABILITY_ASSESS_SPEC,
    LEGAL_OBLIGATION_CREATE_DRAFT_SPEC,
    OPERATIONS_TASK_CREATE_DRAFT_SPEC,
    OPERATIONS_TASK_LIST_SPEC,
    OPERATIONS_TASK_READ_SPEC,
    STRATEGY_EVIDENCE_CREATE_SPEC,
    STRATEGY_EVIDENCE_LIST_SPEC,
    STRATEGY_GATE_EVALUATION_CREATE_SPEC,
    STRATEGY_NEXT_BEST_ACTION_GET_SPEC,
    STRATEGY_PROJECT_GET_SPEC,
    VENTURE_PROFILE_PROPOSE_UPDATE_SPEC,
    VENTURE_PROFILE_READ_SPEC,
    VENTURE_STAGE_ASSESS_SPEC,
)

__all__ = ["CAPABILITY_RISK_BY_ID", "capability_risk"]

RiskLiteral = Literal["LOW", "MEDIUM", "HIGH"]

_REGISTERED_SPECS = (
    ENGAGEMENT_ASSIGNMENT_WRITE_SPEC,
    ENGAGEMENT_MESSAGE_SEND_SPEC,
    FINANCE_TRANSACTION_RECORD_SPEC,
    LEGAL_APPLICABILITY_ASSESS_SPEC,
    LEGAL_OBLIGATION_CREATE_DRAFT_SPEC,
    OPERATIONS_TASK_CREATE_DRAFT_SPEC,
    OPERATIONS_TASK_LIST_SPEC,
    OPERATIONS_TASK_READ_SPEC,
    STRATEGY_EVIDENCE_CREATE_SPEC,
    STRATEGY_EVIDENCE_LIST_SPEC,
    STRATEGY_GATE_EVALUATION_CREATE_SPEC,
    STRATEGY_NEXT_BEST_ACTION_GET_SPEC,
    STRATEGY_PROJECT_GET_SPEC,
    VENTURE_PROFILE_PROPOSE_UPDATE_SPEC,
    VENTURE_PROFILE_READ_SPEC,
    VENTURE_STAGE_ASSESS_SPEC,
)


def _normalize(raw: object) -> RiskLiteral | None:
    """CapabilityRisk là StrEnum ('low'/'medium'/'high'/'critical')."""
    if raw is None:
        return None
    value = getattr(raw, "value", raw)
    text = str(value).strip().lower()
    if text in ("low",):
        return "LOW"
    if text in ("medium",):
        return "MEDIUM"
    if text in ("high", "critical"):
        return "HIGH"
    return None


CAPABILITY_RISK_BY_ID: dict[str, RiskLiteral] = {}
for _spec in _REGISTERED_SPECS:
    _risk = _normalize(getattr(_spec, "risk", None))
    if _risk is not None:
        CAPABILITY_RISK_BY_ID[_spec.id] = _risk


def capability_risk(capability_id: str | None) -> RiskLiteral | None:
    """Trả 'LOW'|'MEDIUM'|'HIGH' cho capability đã đăng ký; None nếu không rõ."""
    if not capability_id:
        return None
    return CAPABILITY_RISK_BY_ID.get(capability_id)
