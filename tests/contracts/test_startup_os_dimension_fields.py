"""Đối chiếu bảng field 7 chiều onboarding giữa Company (TS) và agent (Python).

Company lưu dữ liệu và từ chối field lạ; agent dùng bảng Python để kiểm payload và
dựng kịch bản phỏng vấn. Lệch hai bên ⇒ agent hỏi/gửi field Company không nhận
(trước đây: `arr`, `burn_rate_weekly`… bị bỏ âm thầm và lưu null).
"""

from __future__ import annotations

import re
from pathlib import Path

from apps.cosa.workflows.onboarding_dimensions import ENUM_VALUES, ONBOARD_DIMENSION_FIELDS

_TS = (
    Path(__file__).resolve().parents[2]
    / "services/company/operations/services/onboard-dimension-fields.ts"
)


def _ts_source() -> str:
    return _TS.read_text(encoding="utf-8")


def _ts_dimension_fields() -> dict[str, dict[str, str]]:
    match = re.search(
        r"export const ONBOARD_DIMENSION_FIELDS = \{(.*?)\n\} as const", _ts_source(), re.S
    )
    assert match, f"ONBOARD_DIMENSION_FIELDS not found in {_TS}"
    body = match.group(1)
    tables: dict[str, dict[str, str]] = {}
    for dim, fields in re.findall(r"\n  (\w+): \{(.*?)\n  \},", body, re.S):
        tables[dim] = dict(re.findall(r"(\w+): \"(\w+)\"", fields))
    return tables


def _ts_enum_values() -> dict[str, tuple[str, ...]]:
    match = re.search(r"const ENUM_VALUES[^=]*=\s*\{(.*?)\n\};", _ts_source(), re.S)
    assert match, "ENUM_VALUES not found"
    return {
        field: tuple(re.findall(r"\"(\w+)\"", values))
        for field, values in re.findall(r"(\w+): \[(.*?)\]", match.group(1))
    }


def test_python_dimension_fields_match_company():
    assert _ts_dimension_fields() == ONBOARD_DIMENSION_FIELDS


def test_python_enum_values_match_company():
    assert _ts_enum_values() == ENUM_VALUES
