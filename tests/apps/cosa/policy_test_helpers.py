from __future__ import annotations

from unittest.mock import AsyncMock

from apps.cosa.policies.company_policy_client import CosaTenantPolicyClient
from apps.cosa.policies.snapshot import PolicySnapshot

__all__ = [
    "fake_active_tenant_policy_client",
    "allow_all_policy_snapshot",
    "compliance_snapshot",
]


def allow_all_policy_snapshot() -> PolicySnapshot:
    return PolicySnapshot(
        workspace_id="test_ws_1",
        workspace_status="active",
        principal_status="active",
        rules=[
            {
                "tool_pattern": "*",
                "decision": "ALLOW",
                "reason": "Tenant allow all override",
            }
        ],
        snapshot_hash="allow-all-hash",
    )


def compliance_snapshot(
    allowed_capabilities: set[str] | frozenset[str] | None = None,
    prohibited_purpose: bool = False,
    mode: str = "ADVISORY_ONLY",
    status: str = "APPROVED_FOR_USE",
) -> dict:
    from datetime import datetime, timezone
    return {
        "workspace_id": "test_ws_1",
        "deployment_id": "dep_1",
        "assessment_id": "ass_1",
        "mode": mode,
        "status": status,
        "allowed_capabilities": list(allowed_capabilities or []),
        "provider_profile_version": "v1",
        "data_profile_version": "v1",
        "snapshot_hash": "sha256:test",
        "expires_at": datetime.now(timezone.utc).isoformat(),
        "prohibited_purpose": prohibited_purpose,
    }


def fake_active_tenant_policy_client(
    *,
    workspace_id: str = "test_ws_1",
    rules: list[dict] | None = None,
) -> AsyncMock:
    client = AsyncMock(spec=CosaTenantPolicyClient)
    client.get_snapshot.return_value = PolicySnapshot(
        workspace_id=workspace_id,
        workspace_status="active",
        principal_status="active",
        rules=rules or [],
        snapshot_hash="test-snapshot-hash",
    )
    return client

