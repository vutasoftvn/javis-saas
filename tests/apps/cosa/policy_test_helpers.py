from __future__ import annotations

from unittest.mock import AsyncMock

from apps.cosa.policies.company_policy_client import CosaTenantPolicyClient
from apps.cosa.policies.snapshot import PolicySnapshot

__all__ = [
    "fake_active_tenant_policy_client",
    "allow_all_policy_snapshot",
    "compliance_snapshot",
    "fake_data_access_claim",
    "configure_mock_client_allows_data_use",
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


def fake_data_access_claim(
    *,
    workspace_id: str = "test_ws_1",
    deployment_id: str = "dep_1",
    capability_id: str = "model.input",
    categories: frozenset[str] | set[str] | None = None,
    subject_reference: str | None = None,
):
    """`DataAccessClaim` tối thiểu cho test không phải test riêng nhánh
    compliance data-egress (Task 7, 2026-08-30) — sau khi `CosaDataModelGate`
    bắt buộc deny khi thiếu claim thật trên đường compliance-gated (mọi run
    qua `build_cosa_agent_plane(runtime="openai_agents")`, xem
    `apps/cosa/compliance/data_model_gate.py`), các test không kiểm thử data
    governance nhưng vẫn chạy hết 1 run thật cần 1 claim hợp lệ để không bị
    chặn tại `prepare_initial_input`. Đây KHÔNG phải nguồn thật (chưa có
    capability/retrieval nào gắn claim thật — xem
    docs/superpowers/specs/2026-08-30-data-egress-context-prerequisite.md) —
    chỉ hợp lệ trong test, không dùng làm khuôn mẫu cho code sản xuất.
    """
    from apps.cosa.compliance.data_access_claim import DataAccessClaim

    return DataAccessClaim(
        workspace_id=workspace_id,
        deployment_id=deployment_id,
        capability_id=capability_id,
        source_ref="test://fixture/generic-input",
        source_hash="sha256:" + "0" * 64,
        categories=frozenset(categories or ["BUSINESS_CONFIDENTIAL"]),
        purpose_id="advisory",
        subject_reference=subject_reference,
        provider_key="deepseek",
        model_key="deepseek-chat",
    )


def configure_mock_client_allows_data_use(mock_client: AsyncMock) -> AsyncMock:
    """Cấu hình tường minh `mock_client.resolve_data_use` trả về 1 decision
    "allowed" xác định (Task 7, 2026-08-30) — KHÔNG để `AsyncMock` tự thoả
    mãn `hasattr`/truthiness một cách hời hợt (audit đã chỉ ra đây chính là
    lý do dead-code cũ "tests green" giả). Dùng cho test không kiểm thử data
    governance nhưng cần 1 run thật đi hết qua `CosaDataModelGate` với
    `company_client=mock_client`.
    """
    from types import SimpleNamespace

    mock_client.resolve_data_use.return_value = SimpleNamespace(
        allowed=True,
        denial_code=None,
        provider_profile_version="v1",
        data_profile_version="v1",
        retention_policy_id=None,
        minimization_required=True,
    )
    return mock_client


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

