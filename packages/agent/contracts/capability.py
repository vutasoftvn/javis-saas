from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from agent.governance.contracts import ApprovalPolicy, CapabilityRisk

__all__ = [
    "CapabilityImplementationIdentity",
    "CapabilityReadiness",
    "CapabilityReadinessReason",
    "CapabilitySpec",
]


class CapabilityReadinessReason(StrEnum):
    """Lý do trạng thái sẵn sàng kỹ thuật của capability theo Hermes Specification."""

    READY = "READY"
    MISSING_CREDENTIAL = "MISSING_CREDENTIAL"
    CONNECTOR_OFFLINE = "CONNECTOR_OFFLINE"
    TENANT_DISABLED = "TENANT_DISABLED"
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    DEPENDENCY_MISSING = "DEPENDENCY_MISSING"


class CapabilityReadiness(BaseModel):
    """Trạng thái sẵn sàng kỹ thuật của một Capability (tách biệt khỏi Authorization/Governance)."""

    capability_id: str
    ready: bool = True
    reason_code: CapabilityReadinessReason = CapabilityReadinessReason.READY
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ttl_seconds: int = 60
    connector_ref: str | None = None
    credential_ref: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class CapabilityImplementationIdentity(BaseModel):
    """L3 Capability Implementation Identity theo Master Guide §43.12 & ADR-A.

    Cho phép pin chính xác phiên bản của handler, schema và connector implementation
    để đảm bảo khả năng rollback an toàn tuyệt đối và audit kiểm thử.
    """

    capability_id: str
    handler_version: str = "1.0.0"
    schema_version: str = "1.0.0"
    connector_implementation_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def compute_identity_hash(self) -> str:
        raw = f"{self.capability_id}:{self.handler_version}:{self.schema_version}:{self.connector_implementation_hash or 'none'}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class CapabilitySpec(BaseModel):
    """Đặc tả khả năng/hành vi có thể thực thi theo Master Guide §16.1.

    Tách biệt khỏi legacy PermissionClass và là hợp đồng chuẩn cho cả
    công cụ nội bộ lẫn external connector.
    """

    id: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    risk: CapabilityRisk = CapabilityRisk.LOW
    approval_policy: ApprovalPolicy = ApprovalPolicy.POLICY_DRIVEN
    idempotency_semantics: str = "none"  # "none" | "key_based" | "payload_deterministic"
    audit_policy: dict[str, Any] = Field(default_factory=dict)
    eligibility: dict[str, Any] = Field(default_factory=dict)
    connector_requirements: dict[str, Any] = Field(default_factory=dict)
    implementation_identity: CapabilityImplementationIdentity | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
