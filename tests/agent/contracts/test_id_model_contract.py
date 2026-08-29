"""M0 contract freeze — ID serialization contract (SpineId Snowflake / LeafId UUIDv7).

Test này chạy được ngay với generator hiện tại; nó khoá hợp đồng wire cho M2/M3.
Xem ADR-ID-MODEL-001 + M0-contract-freeze.md §Test plan.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_FIXTURES = json.loads((_REPO_ROOT / "shared/contracts/fixtures/id-samples.json").read_text())


# ---- SpineId: Snowflake decimal string, không mất precision ----------------

def test_snowflake_decimal_string_round_trip_exact() -> None:
    for s in _FIXTURES["snowflake_decimal_strings"]["samples"]:
        n = int(s)  # parse
        assert str(n) == s  # serialize -> chuỗi gốc
        assert 0 <= n <= (2**63 - 1)


def test_snowflake_large_values_would_break_as_double() -> None:
    """Chứng minh vì sao wire phải là string: double làm hỏng các giá trị 63-bit."""
    for s in _FIXTURES["snowflake_decimal_strings"]["must_not_equal_after_double_roundtrip"]:
        n = int(s)
        assert n > 2**53
        assert int(float(n)) != n  # double round-trip mất mát


def test_snowflake_json_payload_stays_string() -> None:
    payload = {"workspace_id": _FIXTURES["snowflake_decimal_strings"]["samples"][-1]}
    decoded = json.loads(json.dumps(payload))
    assert isinstance(decoded["workspace_id"], str)
    assert decoded["workspace_id"] == "9223372036854775807"


# ---- LeafId: UUIDv7 format + đơn điệu thời gian ---------------------------

def _is_uuidv7(value: str) -> bool:
    u = uuid.UUID(value)
    if u.version != 7:
        return False
    # variant RFC 4122: hai bit cao của clock_seq_hi là 10
    return (u.int >> 62) & 0b11 == 0b10


def test_uuidv7_samples_parse_and_are_v7() -> None:
    for s in _FIXTURES["uuidv7"]["ordered_samples"]:
        assert _is_uuidv7(s), s
        # canonical string round-trip
        assert str(uuid.UUID(s)) == s


def test_uuidv7_time_ordering_is_lexicographic() -> None:
    ordered = _FIXTURES["uuidv7"]["ordered_samples"]
    assert ordered == sorted(ordered), "UUIDv7 phải sắp xếp lexicographic theo thời gian"


def test_v4_and_non_v7_rejected() -> None:
    for s in _FIXTURES["uuidv7"]["not_v7"]:
        assert not _is_uuidv7(s), s


@pytest.mark.parametrize("bad", ["not-a-uuid", "", "017f22e2-79b0-7cc3-98c4"])
def test_malformed_uuid_raises(bad: str) -> None:
    with pytest.raises(ValueError):
        uuid.UUID(bad)
