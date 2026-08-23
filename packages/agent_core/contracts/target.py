from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from agent_core.governance.contracts import CapabilityRisk

__all__ = ["ExecutionTargetSnapshot"]


class ExecutionTargetSnapshot(BaseModel):
    """Snapshot định danh hệ thống đích sẽ nhận side effect theo Master Guide §8.
    
    Phục vụ cho quy trình Human Approval và chống Drift Target:
    - Nếu payload không đổi nhưng hệ thống đích (account, connector, endpoint, credential)
      đã thay đổi giữa lúc request và lúc resume -> approval cũ bị stale.
    """

    capability_id: str
    connector_id: Optional[str] = None
    connection_account_id: Optional[str] = None
    endpoint_resource_identity: Optional[str] = None
    schema_hash_version: Optional[str] = None
    credential_grant_version: Optional[str] = None
    capability_risk_at_request_time: CapabilityRisk = CapabilityRisk.LOW
    handler_catalog_version: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
