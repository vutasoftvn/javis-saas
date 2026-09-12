from __future__ import annotations

from datetime import UTC, datetime, timedelta
import pytest

from agent.local_executor.contracts import LocalExecutionGrant, LocalExecutionReceipt
from agent.local_executor.grants import (
    canonical_input_hash,
    compute_receipt_signature,
    mint_grant,
    verify_receipt_against_context,
)
from agent.local_executor.repository import LocalExecutorRepository


def test_canonical_input_hash_deterministic():
    data1 = {"b": 2, "a": 1}
    data2 = {"a": 1, "b": 2}
    assert canonical_input_hash(data1) == canonical_input_hash(data2)


def test_nonce_can_be_consumed_once():
    repo = LocalExecutorRepository()
    future = datetime.now(UTC) + timedelta(minutes=5)
    assert repo.consume_nonce("nonce-1", expires_at=future) is True
    assert repo.consume_nonce("nonce-1", expires_at=future) is False  # Replay fails


def test_expired_nonce_rejected():
    repo = LocalExecutorRepository()
    past = datetime.now(UTC) - timedelta(minutes=5)
    assert repo.consume_nonce("nonce-2", expires_at=past) is False


def test_receipt_signature_verification():
    receipt = LocalExecutionReceipt(
        receipt_id="r1",
        grant_id="g1",
        workspace_id="ws1",
        project_id="p1",
        tool_call_id="t1",
        status="SUCCESS",
        manifest_hash="m1",
        signature="",
    )
    sig = compute_receipt_signature(receipt)
    receipt.signature = sig

    res = verify_receipt_against_context(receipt, expected_workspace_id="ws1", require_signature=True)
    assert res.is_valid is True
    assert res.code == "OK"

    # Corrupt signature
    receipt.signature = "invalid-sig"
    res_bad = verify_receipt_against_context(receipt, expected_workspace_id="ws1", require_signature=True)
    assert res_bad.is_valid is False
    assert res_bad.code == "INVALID_SIGNATURE"
