from __future__ import annotations

from datetime import UTC
from typing import Any
from unittest.mock import AsyncMock

from apps.cosa.policies.company_policy_client import CosaTenantPolicyClient
from apps.cosa.policies.snapshot import PolicySnapshot

__all__ = [
    "agent_authority_snapshot",
    "allow_all_policy_snapshot",
    "compliance_snapshot",
    "configure_mock_client_allows_data_use",
    "configure_mock_client_project_access",
    "fake_active_tenant_policy_client",
    "fake_data_access_claim",
    "policy_snapshot_with",
]


def agent_authority_snapshot(
    *,
    authorization_epoch: int = 1,
    grants: list[Any] | None = None,
) -> Any:
    from apps.cosa.policies.snapshot import AgentAuthorizationSnapshot

    return AgentAuthorizationSnapshot(
        authorization_epoch=authorization_epoch,
        grants=grants or [],
    )


def policy_snapshot_with(
    *,
    workspace_id: str = "test_ws_1",
    workspace_status: str = "active",
    principal_status: str = "active",
    control_rule: tuple[str, str] | None = None,
    agent_authority: Any | None = None,
) -> PolicySnapshot:
    rules = []
    if control_rule is not None:
        pattern, decision = control_rule
        rules.append({"tool_pattern": pattern, "decision": decision})
    return PolicySnapshot(
        workspace_id=workspace_id,
        workspace_status=workspace_status,
        principal_status=principal_status,
        rules=rules,
        snapshot_hash="test-policy-snapshot-hash",
        agent_authority=agent_authority,
    )


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
    from datetime import datetime

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
        "expires_at": datetime.now(UTC).isoformat(),
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


def configure_mock_client_project_access(
    mock_client: AsyncMock,
    *,
    workspace_id: str = "test_ws_1",
    denied_project_ids: set[str] | None = None,
) -> AsyncMock:
    """Cấu hình `mock_client.get` để trả lời `GET /operations/projects/:id`
    (Company Project read boundary — `apps/cosa/api/project_context.py`)
    một cách xác định: authorize bất kỳ project_id nào KHÔNG nằm trong
    `denied_project_ids` (echo lại đúng id đó, giả lập Company đã xác nhận
    project thuộc workspace này), và raise `CompanyServiceError(404)` cho
    project bị từ chối (giả lập không tồn tại / không thuộc workspace).

    KHÔNG dùng `mock_client.get.return_value` đơn giản ở đây — response phải
    khớp CHÍNH project_id trong URL request (test khác nhau dùng project_id
    khác nhau trong cùng 1 fixture), và test cross-tenant cần phân biệt được
    project bị từ chối với project được phép.
    """
    from apps.cosa.capabilities.client import CompanyServiceError

    denied = denied_project_ids or set()

    async def _get(path: str, *args, **kwargs):
        if path.startswith("/operations/projects/"):
            project_id = path.rsplit("/", 1)[-1]
            if project_id in denied:
                raise CompanyServiceError("Project not found", status_code=404)
            return {"id": project_id, "workspaceId": workspace_id, "title": f"Project {project_id}"}
        return {}

    mock_client.get.side_effect = _get
    return mock_client


class StubCompanyServiceClient:
    async def resolve_data_use(self, *args, **kwargs):
        from types import SimpleNamespace

        return SimpleNamespace(
            allowed=True,
            denial_code=None,
            provider_profile_version="v1",
            data_profile_version="v1",
            retention_policy_id=None,
            minimization_required=True,
        )


class StubTenantPolicyClient:
    def __init__(self, workspace_id: str = "test_ws_1", rules: list[dict] | None = None):
        self.workspace_id = workspace_id
        self.rules = rules or []

    async def get_snapshot(self, *args, **kwargs) -> PolicySnapshot:
        return PolicySnapshot(
            workspace_id=self.workspace_id,
            workspace_status="active",
            principal_status="active",
            rules=self.rules,
            snapshot_hash="test-snapshot-hash",
        )


def stub_active_tenant_policy_client(
    *,
    workspace_id: str = "test_ws_1",
    rules: list[dict] | None = None,
) -> StubTenantPolicyClient:
    return StubTenantPolicyClient(workspace_id=workspace_id, rules=rules)


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
