"""DoneCriteria v1 — phản chiếu services/company/operations/services/done-criteria.ts.

Hai bên được khóa bằng shared/contracts/done-criteria.fixtures.json (test cả TS lẫn Python).
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

__all__ = ["DoneCriteriaError", "js_canonical_json_size", "parse_done_criteria"]

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


# --- Canonical size of predicate.args -------------------------------------------------
# Both languages measure the UTF-8 byte length of the *JavaScript* JSON.stringify form:
#  - strings: JSON.stringify escapes (" \ \b \f \n \r \t, other < 0x20 as \u00xx, lone
#    surrogates as \udxxx lowercase); everything else is emitted raw (UTF-8 encoded);
#  - numbers: ECMAScript Number::toString (1.0 -> "1", 1e21 -> "1e+21", ints go through
#    float64 like JSON.parse would); non-finite -> "null";
#  - objects keep insertion order, separators "," and ":", no whitespace.
_ESCAPE_RE = re.compile('[\x00-\x1f"\\\\\ud800-\udfff]')
_SHORT_ESCAPES = {
    '"': '\\"',
    "\\": "\\\\",
    "\b": "\\b",
    "\f": "\\f",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
}


def _escape_char(m: re.Match[str]) -> str:
    ch = m.group(0)
    return _SHORT_ESCAPES.get(ch) or f"\\u{ord(ch):04x}"


def _js_string(s: str) -> str:
    return '"' + _ESCAPE_RE.sub(_escape_char, s) + '"'


def _js_number(value: int | float) -> str:
    """ECMAScript Number::toString as used by JSON.stringify (non-finite -> null)."""
    try:
        x = float(value)
    except OverflowError:  # JSON.parse of such an integer yields Infinity
        return "null"
    if x != x or x in (float("inf"), float("-inf")):
        return "null"
    if x == 0:
        return "0"  # also -0
    sign = "-" if x < 0 else ""
    _, digit_tuple, exp = Decimal(repr(abs(x))).as_tuple()
    raw_digits = "".join(map(str, digit_tuple))
    digits = raw_digits.rstrip("0") or "0"
    k = len(digits)
    n = len(raw_digits) + int(exp)  # value = 0.<digits> * 10**n
    if k <= n <= 21:
        body = digits + "0" * (n - k)
    elif 0 < n <= 21:
        body = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        body = "0." + "0" * -n + digits
    else:
        e = n - 1
        mant = digits[0] + ("." + digits[1:] if k > 1 else "")
        body = f"{mant}e{'+' if e >= 0 else '-'}{abs(e)}"
    return sign + body


class _Raw:
    __slots__ = ("text",)

    def __init__(self, text: str) -> None:
        self.text = text


def js_canonical_json_size(value: object) -> int:
    """UTF-8 byte length of JS JSON.stringify(value); DoneCriteriaError if not encodable.

    Iterative, so nesting depth is not limited by the Python recursion limit.
    """
    out: list[str] = []
    stack: list[object] = [value]
    while stack:
        item = stack.pop()
        if isinstance(item, _Raw):
            out.append(item.text)
        elif item is None:
            out.append("null")
        elif item is True:
            out.append("true")
        elif item is False:
            out.append("false")
        elif isinstance(item, (int, float)):
            out.append(_js_number(item))
        elif isinstance(item, str):
            out.append(_js_string(item))
        elif isinstance(item, list):
            stack.append(_Raw("]"))
            for i in range(len(item) - 1, -1, -1):
                stack.append(item[i])
                if i:
                    stack.append(_Raw(","))
            out.append("[")
        elif isinstance(item, dict):
            stack.append(_Raw("}"))
            entries = list(item.items())
            for i in range(len(entries) - 1, -1, -1):
                key, val = entries[i]
                if not isinstance(key, str):
                    raise DoneCriteriaError("predicate args too large")
                stack.append(val)
                stack.append(_Raw(_js_string(key) + ":"))
                if i:
                    stack.append(_Raw(","))
            out.append("{")
        else:
            raise DoneCriteriaError("predicate args too large")
    try:
        return len("".join(out).encode("utf-8"))
    except UnicodeEncodeError as exc:  # unreachable: surrogates are escaped
        raise DoneCriteriaError("predicate args too large") from exc


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
        if js_canonical_json_size(predicate["args"]) > _MAX_ARGS_BYTES:
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
