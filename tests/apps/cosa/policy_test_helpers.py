from __future__ import annotations

from unittest.mock import AsyncMock

from apps.cosa.policies.company_policy_client import CosaTenantPolicyClient
from apps.cosa.policies.snapshot import PolicySnapshot

__all__ = ["fake_active_tenant_policy_client"]


def fake_active_tenant_policy_client(
    *,
    company_id: str = "test_company_1",
    rules: list[dict] | None = None,
) -> AsyncMock:
    """Mock `CosaTenantPolicyClient` trả PolicySnapshot company/principal đều
    "active", không rule tenant nào (trừ khi truyền `rules`) — dùng cho test
    không quan tâm riêng tới policy wiring (Phase 3), chỉ cần run không bị
    fail-closed vì thiếu snapshot."""
    client = AsyncMock(spec=CosaTenantPolicyClient)
    client.get_snapshot.return_value = PolicySnapshot(
        company_id=company_id,
        company_status="active",
        principal_status="active",
        rules=rules or [],
        snapshot_hash="test-snapshot-hash",
    )
    return client
