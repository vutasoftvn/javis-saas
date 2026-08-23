from __future__ import annotations

import hashlib
from typing import Any, Optional
from pydantic import BaseModel, Field

from agent_core.governance.contracts import ApprovalPolicy, CapabilityRisk

from datetime import datetime, timezone
from enum import Enum

__all__ = [
    "CapabilitySpec",
    "ExecutionTargetSnapshot",
    "CapabilityImplementationIdentity",
    "CapabilityReadinessReason",
    "CapabilityReadiness",
]


class CapabilityReadinessReason(str, Enum):
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
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: int = 60
    connector_ref: Optional[str] = None
    credential_ref: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)


class CapabilityImplementationIdentity(BaseModel):
    """L3 Capability Implementation Identity theo Master Guide §43.12 & ADR-A.
    
    Cho phép pin chính xác phiên bản của handler, schema và connector implementation
    để đảm bảo khả năng rollback an toàn tuyệt đối và audit kiểm thử.
    """

    capability_id: str
    handler_version: str = "1.0.0"
    schema_version: str = "1.0.0"
    connector_implementation_hash: Optional[str] = None
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
    implementation_identity: Optional[CapabilityImplementationIdentity] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionTargetSnapshot(BaseModel):
    """Ảnh chụp mục tiêu thực thi bất biến tại thời điểm yêu cầu theo Master Guide §17.4.
    
    Bảo toàn snapshot định danh của external target để phát hiện Target Drift khi resume.
    """

    capability_id: str
    connector_id: Optional[str] = None
    target_id: Optional[str] = None
    endpoint_url: Optional[str] = None
    credential_scope: Optional[str] = None
    schema_hash_version: Optional[str] = None
    capability_risk_at_request_time: Optional[CapabilityRisk] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
