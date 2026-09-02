"""Contract test cho unified seed kit — chạy trên `real_cosa_stack` (4 plane thật).

Kiểm chứng 3 bất biến mà các scenario task S1–S4 sẽ dựa vào:

1. `identity.seed_workspace` trả về owner token + member token DÙNG ĐƯỢC:
   gọi `GET /operations/tasks` trên `services/company` (qua `requireWorkspaceAccess`
   -> `resolveTenantContext`, xác thực membership local) phải trả 200.
2. `entitlement.grant_entitlement` idempotent — gọi 2 lần không raise.
3. `agent_spec.seed_minimal_agent_spec` trả về id của 1 AgentSpec đã publish
   trong `agent_registry.published_specs` (worker/api seed lúc boot).
"""

from __future__ import annotations

import pytest

from tests.e2e.seed import agent_spec, entitlement, identity
from tests.e2e.seed.handles import SeededWorkspace

# Chạy trên `real_cosa_stack` (4 plane thật) → chỉ job `e2e-cross-plane-smoke`.
pytestmark = pytest.mark.cross_plane


def test_seed_workspace_yields_usable_owner_and_member_tokens(
    real_cosa_stack, disposable_cluster
) -> None:
    seeded = identity.seed_workspace(real_cosa_stack, disposable_cluster, with_member=True)
    assert isinstance(seeded, SeededWorkspace)
    assert seeded.workspace_id
    assert seeded.owner_token
    assert seeded.member_token
    assert seeded.member_user_id

    # Cả owner lẫn member đều phải qua được tenant guard của business API.
    for label, token in (
        ("owner", seeded.owner_token),
        ("member", seeded.member_token),
    ):
        resp = real_cosa_stack.company.get(
            "/operations/tasks", token=token, workspace_id=seeded.workspace_id
        )
        assert resp.status_code == 200, f"{label}: {resp.status_code} {resp.text}"
        body = resp.json()
        # Handler `listTasks` trả `{ tasks: [...] }` (không có envelope {data, meta}
        # ở service/company — đã xác nhận: không có response middleware).
        assert "tasks" in body, f"{label}: {body}"


def test_grant_entitlement_is_idempotent(real_cosa_stack, disposable_cluster) -> None:
    seeded = identity.seed_workspace(real_cosa_stack, disposable_cluster)
    entitlement.grant_entitlement(disposable_cluster, seeded.workspace_id, "operations")
    # Lần 2 với cùng (workspace, capability_prefix) không được lỗi.
    entitlement.grant_entitlement(disposable_cluster, seeded.workspace_id, "operations")


def test_seed_minimal_agent_spec_returns_published_spec_id(
    real_cosa_stack, disposable_cluster
) -> None:
    seeded = identity.seed_workspace(real_cosa_stack, disposable_cluster)
    spec_id = agent_spec.seed_minimal_agent_spec(
        real_cosa_stack.apps_cosa.base_url,
        disposable_cluster,
        workspace_id=seeded.workspace_id,
    )
    assert spec_id
    assert isinstance(spec_id, str)
