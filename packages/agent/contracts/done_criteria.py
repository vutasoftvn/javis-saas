"""DoneCriteria v1 — phản chiếu services/company/operations/services/done-criteria.ts.

Hai bên được khóa bằng shared/contracts/done-criteria.fixtures.json (test cả TS lẫn Python).
"""

from __future__ import annotations

import json
import re
from typing import Any

__all__ = ["DoneCriteriaError", "parse_done_criteria"]

_ID = re.compile(r"^[a-z0-9_-]{1,40}$")
# Whitespace set shared with done-criteria.ts (WS): JS WhiteSpace + LineTerminator.
# Python's str.strip() default differs (\x1c-\x1f, \x85, no BOM), so strip explicitly.
_WS = (
    "\t\n\v\f\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008"
    "\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
)
# Raw strings longer than 4x the limit are rejected before trimming (same rule in TS).
_RAW_FACTOR = 4
_MAX_ARGS_BYTES = 2048
_PREDICATE_KINDS = ("artifact_exists", "metric_gte", "field_present")


class DoneCriteriaError(ValueError):
    """Tiêu chí hoàn thành không hợp lệ; thông điệp trùng với bản TypeScript."""


def _parse_criterion(raw: object, seen: set[str]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise DoneCriteriaError("invalid criterion id")
    cid = raw.get("id")
    if not isinstance(cid, str) or not _ID.fullmatch(cid):
        raise DoneCriteriaError("invalid criterion id")
    if cid in seen:
        raise DoneCriteriaError("duplicate criterion id")
    seen.add(cid)

    description = raw.get("description")
    description = description if isinstance(description, str) else ""
    if len(description) > 300 * _RAW_FACTOR:
        raise DoneCriteriaError("description must be 1..300 chars")
    description = description.strip(_WS)
    if not 1 <= len(description) <= 300:
        raise DoneCriteriaError("description must be 1..300 chars")
    required = raw["required"] if isinstance(raw.get("required"), bool) else True

    check = raw.get("check")
    if check == "deterministic":
        predicate = raw.get("predicate")
        if not isinstance(predicate, dict):
            raise DoneCriteriaError("deterministic criterion requires predicate")
        if predicate.get("kind") not in _PREDICATE_KINDS:
            raise DoneCriteriaError("unknown predicate kind")
        if not isinstance(predicate.get("args"), dict):
            raise DoneCriteriaError("deterministic criterion requires predicate")
        encoded = json.dumps(predicate["args"], ensure_ascii=False, separators=(",", ":"))
        if len(encoded.encode("utf-8")) > _MAX_ARGS_BYTES:
            raise DoneCriteriaError("predicate args too large")
        return {
            "id": cid,
            "description": description,
            "required": required,
            "check": "deterministic",
            "predicate": {"kind": predicate["kind"], "args": predicate["args"]},
        }
    if check == "rubric":
        rubric = raw.get("rubric")
        rubric = rubric if isinstance(rubric, str) else ""
        if len(rubric) > 500 * _RAW_FACTOR:
            raise DoneCriteriaError("rubric criterion requires rubric")
        rubric = rubric.strip(_WS)
        if not 1 <= len(rubric) <= 500:
            raise DoneCriteriaError("rubric criterion requires rubric")
        return {
            "id": cid,
            "description": description,
            "required": required,
            "check": "rubric",
            "rubric": rubric,
        }
    raise DoneCriteriaError("invalid check")


def parse_done_criteria(raw: object) -> dict[str, Any]:
    # Version rule: number equal to 1 (1 and 1.0, as in JS ===); bool is rejected.
    version = raw.get("version") if isinstance(raw, dict) else None
    if isinstance(version, bool) or not isinstance(version, (int, float)) or version != 1:
        raise DoneCriteriaError("unsupported version")
    criteria = raw.get("criteria")
    if not isinstance(criteria, list) or not 1 <= len(criteria) <= 10:
        raise DoneCriteriaError("criteria must contain 1..10 items")
    seen: set[str] = set()
    return {"version": 1, "criteria": [_parse_criterion(c, seen) for c in criteria]}
