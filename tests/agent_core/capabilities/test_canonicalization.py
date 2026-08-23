from __future__ import annotations

from agent_core.capabilities.canonicalization import (
    canonicalize_payload,
    compute_payload_hash,
)


def test_canonicalize_payload_key_sorting():
    dict1 = {"b": 2, "a": 1, "nested": {"z": 9, "y": 8}}
    dict2 = {"nested": {"y": 8, "z": 9}, "a": 1, "b": 2}

    json1 = canonicalize_payload(dict1)
    json2 = canonicalize_payload(dict2)

    assert json1 == '{"a":1,"b":2,"nested":{"y":8,"z":9}}'
    assert json1 == json2


def test_compute_payload_hash_invariance():
    dict1 = {"recipient": "vendor_1", "amount": 1500.5, "meta": {"urgent": True, "notes": "PO-101"}}
    dict2 = {"meta": {"notes": "PO-101", "urgent": True}, "amount": 1500.5, "recipient": "vendor_1"}

    hash1 = compute_payload_hash(dict1)
    hash2 = compute_payload_hash(dict2)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex string


def test_float_and_type_normalization():
    p1 = {"rate": 1.25000000}
    p2 = {"rate": 1.25}

    assert compute_payload_hash(p1) == compute_payload_hash(p2)
