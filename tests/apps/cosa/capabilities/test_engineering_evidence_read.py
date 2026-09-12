from __future__ import annotations

from datetime import UTC, datetime, timedelta
import pytest

from agent.local_executor.contracts import LocalExecutionGrant, LocalExecutionReceipt
from agent.local_executor.grants import (
    canonical_input_hash,
    compute_receipt_signature,
    verify_receipt_against_context,
)
from agent.local_executor.repository import LocalExecutorRepository
from apps.cosa.capabilities.engineering_evidence_read import create_engineering_evidence_read_handler


@pytest.mark.asyncio
async def test_engineering_evidence_read_rejects_cross_workspace():
    receipt = LocalExecutionReceipt(
        receipt_id="rcpt-1",
        grant_id="grant-1",
        workspace_id="ws-b",
        project_id="proj-1",
        tool_call_id="call-1",
        status="SUCCESS",
        manifest_hash="hash-1",
        artifact_metadata={"artifact_hashes": ["art-hash-1"]},
    )

    handler = create_engineering_evidence_read_handler()
    # Current context is ws-a
    res = await handler(
        {"workspace_id": "ws-a", "tool_call_id": "call-1", "receipt": receipt.model_dump()},
        ctx={"workspace_id": "ws-a"},
    )
    assert res["code"] == "CROSS_WORKSPACE_ACCESS_DENIED"
    assert res["is_valid"] is False
    assert res["snapshot"] is None


@pytest.mark.asyncio
async def test_engineering_evidence_read_rejects_tool_call_mismatch():
    receipt = LocalExecutionReceipt(
        receipt_id="rcpt-1",
        grant_id="grant-1",
        workspace_id="ws-a",
        project_id="proj-1",
        tool_call_id="call-other",
        status="SUCCESS",
        manifest_hash="hash-1",
        artifact_metadata={"artifact_hashes": ["art-hash-1"]},
    )

    handler = create_engineering_evidence_read_handler()
    res = await handler(
        {"workspace_id": "ws-a", "tool_call_id": "call-expected", "receipt": receipt.model_dump()},
        ctx={"workspace_id": "ws-a"},
    )
    assert res["code"] == "RECEIPT_BINDING_MISMATCH"
    assert res["is_valid"] is False
    assert res["snapshot"] is None


@pytest.mark.asyncio
async def test_engineering_evidence_read_success_projection():
    receipt = LocalExecutionReceipt(
        receipt_id="rcpt-1",
        grant_id="grant-1",
        workspace_id="ws-a",
        project_id="proj-1",
        tool_call_id="call-1",
        status="SUCCESS",
        manifest_hash="hash-1",
        artifact_metadata={"artifact_hashes": ["art-hash-1"]},
    )

    handler = create_engineering_evidence_read_handler()
    res = await handler(
        {"workspace_id": "ws-a", "tool_call_id": "call-1", "receipt": receipt.model_dump()},
        ctx={"workspace_id": "ws-a"},
    )
    assert res["code"] == "OK"
    assert res["is_valid"] is True
    snap = res["snapshot"]
    assert snap is not None
    assert snap["workspace_id"] == "ws-a"
    assert snap["tool_call_id"] == "call-1"
    assert snap["manifest_hash"] == "hash-1"
    assert snap["artifact_hashes"] == ["art-hash-1"]
    assert snap["verified"] is True
    # Verify no command text or secrets leaked
    assert "command" not in snap
    assert "secret" not in snap
