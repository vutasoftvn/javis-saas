from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any

from .contracts import (
    EngineeringEvidenceSnapshot,
    LocalExecutionGrant,
    LocalExecutionReceipt,
    ReceiptVerificationResult,
)

__all__ = [
    "GrantVerificationError",
    "canonical_input_hash",
    "compute_receipt_signature",
    "mint_grant",
    "verify_receipt_against_context",
]

_SECRET = os.environ.get("COSA_LOCAL_EXECUTOR_DELEGATION_SECRET", "dev-local-executor-secret-32-chars-long!")


class GrantVerificationError(Exception):
    pass


def canonical_input_hash(data: dict[str, Any]) -> str:
    """Tạo sha256 hash chuẩn hoá (deterministic canonical json) của input."""
    raw = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def compute_receipt_signature(receipt: LocalExecutionReceipt, secret: str = _SECRET) -> str:
    """Tính chữ ký HMAC cho biên lai thực thi."""
    payload = f"{receipt.receipt_id}:{receipt.grant_id}:{receipt.workspace_id}:{receipt.project_id}:{receipt.tool_call_id}:{receipt.status}:{receipt.manifest_hash}"
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def mint_grant(grant: LocalExecutionGrant) -> str:
    """Tạo representation hoặc token cho grant (ở đây là JSON kèm hash)."""
    return grant.model_dump_json()


def verify_receipt_against_context(
    receipt: LocalExecutionReceipt,
    *,
    expected_workspace_id: str,
    expected_tool_call_id: str | None = None,
    expected_project_id: str | None = None,
    require_signature: bool = False,
    secret: str = _SECRET,
) -> ReceiptVerificationResult:
    """Kiểm tra tính hợp lệ và ràng buộc (binding) của receipt với context hiện hành."""
    # 1. Workspace isolation
    if str(receipt.workspace_id) != str(expected_workspace_id):
        return ReceiptVerificationResult(
            is_valid=False,
            code="CROSS_WORKSPACE_ACCESS_DENIED",
            reason=f"Workspace mismatch: expected '{expected_workspace_id}', receipt belongs to '{receipt.workspace_id}'",
        )

    # 2. Tool-call binding
    if expected_tool_call_id is not None and receipt.tool_call_id != expected_tool_call_id:
        return ReceiptVerificationResult(
            is_valid=False,
            code="RECEIPT_BINDING_MISMATCH",
            reason=f"Tool call binding mismatch: expected '{expected_tool_call_id}', receipt has '{receipt.tool_call_id}'",
        )

    # 3. Project binding
    if expected_project_id is not None and receipt.project_id != expected_project_id:
        return ReceiptVerificationResult(
            is_valid=False,
            code="RECEIPT_BINDING_MISMATCH",
            reason=f"Project binding mismatch: expected '{expected_project_id}', receipt has '{receipt.project_id}'",
        )

    # 4. Signature check if required
    if require_signature:
        expected_sig = compute_receipt_signature(receipt, secret)
        if not hmac.compare_digest(receipt.signature, expected_sig):
            return ReceiptVerificationResult(
                is_valid=False,
                code="INVALID_SIGNATURE",
                reason="Receipt signature verification failed",
            )

    # Extract artifact hashes safely
    artifact_hashes = []
    if "artifact_hashes" in receipt.artifact_metadata and isinstance(receipt.artifact_metadata["artifact_hashes"], list):
        artifact_hashes = [str(h) for h in receipt.artifact_metadata["artifact_hashes"]]
    elif "artifacts" in receipt.artifact_metadata and isinstance(receipt.artifact_metadata["artifacts"], list):
        for art in receipt.artifact_metadata["artifacts"]:
            if isinstance(art, dict) and "sha256" in art:
                artifact_hashes.append(str(art["sha256"]))

    snapshot = EngineeringEvidenceSnapshot(
        workspace_id=receipt.workspace_id,
        project_id=receipt.project_id,
        tool_call_id=receipt.tool_call_id,
        status=receipt.status,
        manifest_hash=receipt.manifest_hash,
        artifact_hashes=artifact_hashes,
        verified=True,
    )

    return ReceiptVerificationResult(
        is_valid=True,
        code="OK",
        reason="Evidence verified successfully",
        snapshot=snapshot,
    )
