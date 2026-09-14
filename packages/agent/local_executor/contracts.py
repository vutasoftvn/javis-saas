from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "EngineeringEvidenceSnapshot",
    "LocalExecutionGrant",
    "LocalExecutionReceipt",
    "ReceiptVerificationResult",
]


class LocalExecutionGrant(BaseModel):
    """Grant cấp quyền thực thi trong Safe Sandbox."""
    model_config = ConfigDict(extra="forbid")

    grant_id: str
    workspace_id: str
    project_id: str
    run_id: str
    tool_call_id: str
    checkpoint_id: str
    capability_id: str
    node_id: str
    template_id: str
    input_hash: str
    manifest_hash: str
    expires_at: datetime
    nonce: str


class LocalExecutionReceipt(BaseModel):
    """Biên lai thực thi do Safe Sandbox / Local Executor ký trả."""
    model_config = ConfigDict(extra="forbid")

    receipt_id: str
    grant_id: str
    workspace_id: str
    project_id: str
    tool_call_id: str
    status: str  # "SUCCESS" | "FAILED"
    manifest_hash: str
    artifact_metadata: dict[str, Any] = Field(default_factory=dict)
    signature: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EngineeringEvidenceSnapshot(BaseModel):
    """Hình chiếu chỉ đọc của bằng chứng kỹ thuật, không chứa command text hay secrets."""
    model_config = ConfigDict(extra="forbid")

    workspace_id: str
    project_id: str
    tool_call_id: str
    status: str
    manifest_hash: str
    artifact_hashes: list[str] = Field(default_factory=list)
    verified: bool = True


class ReceiptVerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_valid: bool
    code: str  # "OK" | "CROSS_WORKSPACE_ACCESS_DENIED" | "RECEIPT_BINDING_MISMATCH" | "INVALID_SIGNATURE"
    reason: str
    snapshot: EngineeringEvidenceSnapshot | None = None
