import json
from pathlib import Path

import pytest

from agent.contracts.done_criteria import (
    DoneCriteriaError,
    js_canonical_json_size,
    parse_done_criteria,
)

_FIXTURES = json.loads(
    (Path(__file__).resolve().parents[3] / "shared/contracts/done-criteria.fixtures.json").read_text(
        encoding="utf-8"
    )
)


@pytest.mark.parametrize("case", _FIXTURES["valid"], ids=lambda c: c["name"])
def test_valid_cases_normalize_like_typescript(case):
    assert parse_done_criteria(case["input"]) == case["normalized"]


@pytest.mark.parametrize("case", _FIXTURES["invalid"], ids=lambda c: c["name"])
def test_invalid_cases_raise_with_shared_message(case):
    with pytest.raises(DoneCriteriaError) as exc:
        parse_done_criteria(case["input"])
    assert str(exc.value) == case["error"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1.0, 1),  # JS "1"
        (1e16, 17),  # JS "10000000000000000"
        (1e21, 5),  # JS "1e+21"
        (1e-7, 4),  # JS "1e-7"
        (0.1, 3),
        (-0.0, 1),  # JS "0"
        (2**53 + 1, 16),  # through float64: 9007199254740992
        (123456789012345678901234567890, 22),  # JS "1.2345678901234568e+29"
        (float("inf"), 4),  # JS null
        ("\ud800", 8),  # JS "\ud800" escaped, 6 + 2 quotes
        ("\U0001f600", 6),  # valid pair stays 4 raw bytes
        ({"k": [True, None, {}]}, 20),
    ],
)
def test_js_canonical_json_size_matches_javascript(value, expected):
    assert js_canonical_json_size(value) == expected


def test_lone_surrogate_args_never_escape_as_unicode_error():
    raw = {
        "version": 1,
        "criteria": [
            {
                "id": "c1",
                "description": "d",
                "check": "deterministic",
                "predicate": {"kind": "field_present", "args": {"k": "\ud800" * 400}},
            }
        ],
    }
    with pytest.raises(DoneCriteriaError, match="^predicate args too large$"):
        parse_done_criteria(raw)


def test_non_json_args_raise_done_criteria_error():
    with pytest.raises(DoneCriteriaError):
        js_canonical_json_size({"k": {1, 2}})
    with pytest.raises(DoneCriteriaError):
        js_canonical_json_size({1: "x"})
