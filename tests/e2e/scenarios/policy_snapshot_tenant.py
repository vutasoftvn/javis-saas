"""S7: cô lập tenant của policy snapshot (`GET /platform/auth/me/agent-policy-snapshot`).

Endpoint là `expose:true auth:false`: handler tự xác thực control-plane delegation JWT (apps/cosa ký, scoped
`{sub, workspace_id, role}`) qua `resolveCallerAuthorizedForWorkspace`, rồi đọc `cosa.organization_agent_policy`.
Danh tính người dùng do backend/core cấp; e2e không có core thật nên seed bản chiếu user/organization/membership
trực tiếp vào DB cosa (`identity.project_cosa_identity`) và mint delegation bằng `identity.control_plane_delegation`.

Luôn chạy (không cần core):

- Không bearer -> 401 `unauthenticated`; bearer dạng JWT nhưng không phải delegation hợp lệ -> 401.
- Delegation đúng workspace -> 200, `rules` CHỈ chứa policy của tenant đó (operations / finance), workspace
  không có policy không rò rule của tenant khác.
- Delegation của workspace này dùng cho workspace khác -> 403 (fail-closed).
"""

from __future__ import annotations

from tests.e2e.mvp_stack import MvpStack, ServiceClient
from tests.e2e.seed.handles import SeededWorkspace
from tests.e2e.stack.disposable_postgres import DisposableCluster

_SNAPSHOT_PATH = "/platform/auth/me/agent-policy-snapshot"


def run(
    stack: MvpStack,
    cluster: DisposableCluster,
    delegation_for,
    seeded_ops: SeededWorkspace,
    seeded_fin: SeededWorkspace,
    seeded_bare: SeededWorkspace,
) -> None:
    """`delegation_for(workspace_id)` trả control-plane delegation JWT (apps/cosa ký) của user đã được chiếu
    vào DB cosa làm thành viên của workspace đó (`identity.project_cosa_identity`). Ba `SeededWorkspace` có
    nội dung `cosa.organization_agent_policy` khác nhau (operations / finance / trống)."""
    platform = stack.platform

    r_health = platform.get("/healthz")
    assert r_health.status_code == 200, (
        f"services/cosa gateway không lên (healthz={r_health.status_code}): {r_health.text}"
    )

    _assert_auth_gate(platform, seeded_ops.workspace_id)
    _assert_tenant_scoped_snapshot(platform, delegation_for, seeded_ops, seeded_fin, seeded_bare)


def _assert_auth_gate(platform: ServiceClient, workspace_id: str) -> None:
    # Không Authorization -> 401 `unauthenticated`.
    r_anon = platform.get(_SNAPSHOT_PATH, params={"workspaceId": workspace_id})
    assert r_anon.status_code == 401, r_anon.text
    assert r_anon.json().get("code") == "unauthenticated", r_anon.text

    # Bearer dạng JWT nhưng không phải delegation hợp lệ -> 401 (handler verify ký + audience).
    r_garbage = platform.get(
        _SNAPSHOT_PATH, token="not.a.real-jwt-token", params={"workspaceId": workspace_id}
    )
    assert r_garbage.status_code == 401, r_garbage.text
    assert r_garbage.json().get("code") == "unauthenticated", r_garbage.text


def _rule_patterns(body: dict) -> set[str]:
    return {rule["toolPattern"] for rule in body["rules"]}


def _assert_tenant_scoped_snapshot(
    platform: ServiceClient,
    delegation_for,
    seeded_ops: SeededWorkspace,
    seeded_fin: SeededWorkspace,
    seeded_bare: SeededWorkspace,
) -> None:
    # Delegation scoped đúng workspace -> 200 và `rules` CHỈ chứa policy của tenant đó.
    r_ops = platform.get(
        _SNAPSHOT_PATH,
        token=delegation_for(seeded_ops.workspace_id),
        params={"workspaceId": seeded_ops.workspace_id},
    )
    assert r_ops.status_code == 200, r_ops.text
    body_ops = r_ops.json()
    assert body_ops["workspaceId"] == seeded_ops.workspace_id, body_ops
    assert isinstance(body_ops["snapshotHash"], str) and body_ops["snapshotHash"], body_ops
    assert _rule_patterns(body_ops) == {"operations.*"}, body_ops

    r_fin = platform.get(
        _SNAPSHOT_PATH,
        token=delegation_for(seeded_fin.workspace_id),
        params={"workspaceId": seeded_fin.workspace_id},
    )
    assert r_fin.status_code == 200, r_fin.text
    patterns_fin = _rule_patterns(r_fin.json())
    assert patterns_fin == {"finance.*"}, (
        f"ws finance: `rules` phải CHỈ chứa 'finance.*', thực tế {patterns_fin!r}"
    )

    # Workspace không có policy -> 200 nhưng KHÔNG rò rule của tenant khác.
    r_bare = platform.get(
        _SNAPSHOT_PATH,
        token=delegation_for(seeded_bare.workspace_id),
        params={"workspaceId": seeded_bare.workspace_id},
    )
    assert r_bare.status_code == 200, r_bare.text
    patterns_bare = _rule_patterns(r_bare.json())
    assert not (patterns_bare & {"operations.*", "finance.*"}), (
        f"rò rule cross-tenant sang workspace không có policy: {patterns_bare!r}"
    )

    # Delegation của workspace ops KHÔNG dùng được cho workspace khác -> 403 (fail-closed).
    r_cross = platform.get(
        _SNAPSHOT_PATH,
        token=delegation_for(seeded_ops.workspace_id),
        params={"workspaceId": seeded_fin.workspace_id},
    )
    assert r_cross.status_code == 403, (
        f"delegation của ws ops truy cập ws finance: kỳ vọng 403, thực tế {r_cross.status_code}: {r_cross.text}"
    )
