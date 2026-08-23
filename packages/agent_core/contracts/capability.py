from __future__ import annotations

import hashlib
from typing import Any, Optional
from pydantic import BaseModel, Field

from agent_core.governance.contracts import ApprovalPolicy, CapabilityRisk

__all__ = ["CapabilitySpec", "ExecutionTargetSnapshot", "CapabilityImplementationIdentity"]


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
