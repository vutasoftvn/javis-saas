"""Field hợp lệ cho 7 chiều onboarding Startup OS — bản Python của
`services/company/operations/services/onboard-dimension-fields.ts`.

Company là nguồn sự thật (nó lưu dữ liệu và từ chối field lạ). Bảng này tồn tại để
agent kiểm payload TRƯỚC khi gọi Company và để kịch bản phỏng vấn chỉ hỏi đúng field
được lưu. `tests/contracts/test_startup_os_dimension_fields.py` đối chiếu hai bên —
trước đây workflow gửi `arr`/`burn_rate_weekly`… và Company bỏ âm thầm (ghi null).
"""

from __future__ import annotations

import math
from typing import Any, Final

__all__ = [
    "ONBOARD_DIMENSIONS",
    "ONBOARD_DIMENSION_FIELDS",
    "OnboardDimensionDataError",
    "validate_dimension_data",
]

ONBOARD_DIMENSION_FIELDS: Final[dict[str, dict[str, str]]] = {
    "identity": {
        "whatTheyDo": "string",
        "whoTheyServe": "string",
        "foundingWhy": "string",
        "oneSentencePitch": "string",
        "values": "value_list",
        "notCaptured": "string_array",
    },
    "stage_scale": {
        "headcountFt": "integer",
        "headcountContractor": "integer",
        "revenueArr": "number",
        "revenueCurrency": "string",
        "runwayMonths": "number",
        "stage": "string",
        "whatBrokeLast90d": "string",
        "notCaptured": "string_array",
    },
    "founder": {
        "founderName": "string",
        "role": "string",
        "superpower": "string",
        "blindSpots": "string",
        "archetype": "string",
        "whatKeepsUp": "string",
        "cofounderCritique": "string",
        "notCaptured": "string_array",
    },
    "team_culture": {
        "threeWords": "string_array",
        "lastRealConflict": "string",
        "conflictResolution": "string",
        "strongestLeader": "string",
        "weakestLeader": "string",
        "hasRealConflict": "boolean",
        "notCaptured": "string_array",
    },
    "market": {
        "marketDescription": "string",
        "unfairAdvantage": "string",
        "competitiveThreat": "string",
        "hasRealCompetition": "boolean",
        "competitors": "competitor_list",
        "notCaptured": "string_array",
    },
    "challenges": {
        "priorityProduct": "integer",
        "priorityGrowth": "integer",
        "priorityPeople": "integer",
        "priorityMoney": "integer",
        "priorityOperations": "integer",
        "avoidedDecision": "string",
        "extraDayAnswer": "string",
        "notCaptured": "string_array",
    },
    "goals_ambition": {
        "goal12MonthsText": "string",
        "goal36MonthsText": "string",
        "exitOrientation": "string",
        "personalSuccessDefinition": "string",
        "notCaptured": "string_array",
    },
}

ONBOARD_DIMENSIONS: Final[tuple[str, ...]] = tuple(ONBOARD_DIMENSION_FIELDS)

ENUM_VALUES: Final[dict[str, tuple[str, ...]]] = {
    "stage": ("pre_pmf", "scaling", "optimizing"),
    "archetype": ("product", "sales", "technical", "operator", "hybrid"),
    "exitOrientation": ("exit", "build_forever", "undecided"),
}

_PRIORITY_FIELDS: Final[frozenset[str]] = frozenset(
    {"priorityProduct", "priorityGrowth", "priorityPeople", "priorityMoney", "priorityOperations"}
)


class OnboardDimensionDataError(ValueError):
    """Payload 1 chiều không khớp hợp đồng field của Company."""


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _check(dimension: str, field: str, kind: str, value: Any) -> None:
    def fail(reason: str) -> None:
        raise OnboardDimensionDataError(
            f"onboard dimension '{dimension}' field '{field}': {reason}"
        )

    if value is None:
        return
    if kind == "string":
        if not isinstance(value, str):
            fail("must be a string")
        allowed = ENUM_VALUES.get(field)
        if allowed and value not in allowed:
            fail(f"must be one of {', '.join(allowed)}")
    elif kind == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            fail("must be an integer")
        if field in _PRIORITY_FIELDS and not 1 <= value <= 5:
            fail("must be between 1 and 5")
        if value < 0:
            fail("must not be negative")
    elif kind == "number":
        if not _is_number(value) or not math.isfinite(value):
            fail("must be a finite number")
        if value < 0:
            fail("must not be negative")
    elif kind == "boolean":
        if not isinstance(value, bool):
            fail("must be a boolean")
    elif kind == "string_array":
        if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
            fail("must be an array of strings")
    elif kind == "value_list":
        if not isinstance(value, list):
            fail("must be an array")
        for item in value:
            if isinstance(item, str):
                continue
            if not isinstance(item, dict) or not str(item.get("valueText") or "").strip():
                fail("each item must be a string or { valueText }")
            if "isFireWorthy" in item and not isinstance(item["isFireWorthy"], bool):
                fail("isFireWorthy must be a boolean")
            if "realityStatus" in item and item["realityStatus"] not in (
                "real",
                "poster",
                "unclear",
            ):
                fail("realityStatus must be one of real, poster, unclear")
    elif kind == "competitor_list":
        if not isinstance(value, list):
            fail("must be an array")
        for item in value:
            if not isinstance(item, dict) or not str(item.get("name") or "").strip():
                fail("each competitor must be { name }")
            if "whyWinning" in item and not isinstance(item["whyWinning"], str):
                fail("whyWinning must be a string")
            if "threatLevel" in item and item["threatLevel"] not in ("low", "medium", "high"):
                fail("threatLevel must be one of low, medium, high")
    else:  # pragma: no cover — bảng field chỉ dùng các kind ở trên
        fail(f"unsupported field kind '{kind}'")


def validate_dimension_data(dimension: str, data: Any) -> dict[str, Any]:
    """Kiểm payload theo đúng luật của Company; trả lại dict đã kiểm."""
    fields = ONBOARD_DIMENSION_FIELDS.get(dimension)
    if fields is None:
        raise OnboardDimensionDataError(f"unknown onboard dimension '{dimension}'")
    if not isinstance(data, dict):
        raise OnboardDimensionDataError(f"onboard dimension '{dimension}': data must be an object")
    unknown = sorted(set(data) - set(fields))
    if unknown:
        raise OnboardDimensionDataError(
            f"onboard dimension '{dimension}': unknown field(s) {', '.join(unknown)}; "
            f"allowed: {', '.join(fields)}"
        )
    for field, kind in fields.items():
        _check(dimension, field, kind, data.get(field))
    captured = [f for f in fields if f != "notCaptured" and data.get(f) is not None]
    if not captured:
        raise OnboardDimensionDataError(
            f"onboard dimension '{dimension}': at least one field must be provided"
        )
    if dimension == "founder" and not str(data.get("founderName") or "").strip():
        raise OnboardDimensionDataError(
            "onboard dimension 'founder' field 'founderName': is required"
        )
    return data
