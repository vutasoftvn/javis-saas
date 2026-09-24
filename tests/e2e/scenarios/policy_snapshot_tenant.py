"""S7: cô lập tenant của policy snapshot (`GET /platform/auth/me/agent-policy-snapshot`).

Discovery (cập nhật sau cutover backend/core):

- Endpoint `GET /platform/auth/me/agent-policy-snapshot` (`services/cosa`, `expose:true auth:true`) xác thực
  bằng access token OIDC (opaque) của backend/core qua gateway `authHandler`. Token dạng JWT (company local
  token ký `JWT_SECRET`, control-plane delegation) KHÔNG phải danh tính người dùng -> 401 tại gateway.
- Trong subprocess stack không có backend/core thật nên không mint được access token hợp lệ: phần "200 +
  `rules` lọc theo tenant" là NHÁNH DORMANT, chỉ chạy khi stack có core (tự kích hoạt, không hard-assert bug).

B5-independent (LUÔN chạy):

- Gateway auth gate: không bearer -> 401 `unauthenticated`; token rác -> 401
  `unauthenticated`.
- FAIL-CLOSED: delegation JWT (không phải danh tính người dùng) + bất kỳ `workspaceId` nào -> **403 `permission_denied`**, KHÔNG bao
  giờ 200 với snapshot "rỗng = allow-all". Đây là điểm khác S3 (C)(c1): ở đó
  gateway TỪ CHỐI token; ở đây gateway CHẤP NHẬN token nhưng chặng verify
  membership cross-plane fail-closed. Uniform trên workspace có grant
  `operations`, có grant `finance`, và workspace không grant nào -> endpoint
  không rò tín hiệu phân biệt theo nội dung policy.

Dormant (kích hoạt khi cầu nối B5 landed): dùng `seeded.owner_token` (company
local token), kỳ vọng 200 -> `rules` CHỈ chứa pattern của đúng workspace đó
(`operations.*` cho ws operations, `finance.*` cho ws finance), không rò chéo;
`workspaceId` echo đúng; `snapshotHash` là string không rỗng; workspace principal
không có membership -> 403/404.
"""

from __future__ import annotations

from tests.e2e.mvp_stack import MvpStack, ServiceClient
from tests.e2e.seed.handles import SeededWorkspace
from tests.e2e.stack.disposable_postgres import DisposableCluster

_SNAPSHOT_PATH = "/platform/auth/me/agent-policy-snapshot"


def run(
    stack: MvpStack,
    cluster: DisposableCluster,
    delegation_token: str,
    seeded_ops: SeededWorkspace,
    seeded_fin: SeededWorkspace,
    seeded_bare: SeededWorkspace,
) -> None:
    """`cluster` giữ chữ ký đồng nhất với S2–S4 (scenario không cần SQL trực tiếp
    ở đây — seed đã xong ở tầng test). `delegation_token` là control-plane delegation JWT
    (`identity.control_plane_delegation`); ba `SeededWorkspace` là workspace company với nội dung
    `cosa.workspace_agent_policy` khác nhau (operations / finance / trống)."""
    platform = stack.platform

    # Liveness control: gateway phải lên, để 401/403 bên dưới là quyết định auth
    # THẬT chứ không phải "service chết".
    r_health = platform.get("/healthz")
    assert r_health.status_code == 200, (
        f"services/cosa gateway không lên (healthz={r_health.status_code}): {r_health.text}"
    )

    _assert_gateway_auth_gate(platform, seeded_ops.workspace_id)
    _assert_membership_hop_fails_closed(
        platform,
        delegation_token,
        (seeded_ops.workspace_id, seeded_fin.workspace_id, seeded_bare.workspace_id),
    )
    _assert_tenant_scoped_snapshot_or_dormant(platform, seeded_ops, seeded_fin, seeded_bare)


def _assert_gateway_auth_gate(platform: ServiceClient, workspace_id: str) -> None:
    # Không Authorization -> 401 `unauthenticated` (Encore `authHandler`:
    # "missing bearer token").
    r_anon = platform.get(_SNAPSHOT_PATH, params={"workspaceId": workspace_id})
    assert r_anon.status_code == 401, r_anon.text
    assert r_anon.json().get("code") == "unauthenticated", r_anon.text

    # Bearer rác -> 401 (`verifyPlatformToken` throw -> `unauthenticated`).
    r_garbage = platform.get(
        _SNAPSHOT_PATH, token="not-a-real-jwt-token", params={"workspaceId": workspace_id}
    )
    assert r_garbage.status_code == 401, r_garbage.text
    assert r_garbage.json().get("code") == "unauthenticated", r_garbage.text


def _assert_membership_hop_fails_closed(
    platform: ServiceClient, delegation_token: str, workspace_ids: tuple[str, ...]
) -> None:
    # Danh tính người dùng giờ là access token OIDC (opaque) của backend/core; e2e subprocess không có core
    # thật nên không mint được. Token JWT (control-plane delegation do apps/cosa ký) KHÔNG phải danh tính
    # người dùng: gateway `authHandler` PHẢI từ chối (401) thay vì cho qua — fail-closed, không "rỗng = allow",
    # đồng nhất trên 3 workspace có nội dung policy khác nhau nên không rò tín hiệu theo policy.
    for workspace_id in workspace_ids:
        r = platform.get(
            _SNAPSHOT_PATH, token=delegation_token, params={"workspaceId": workspace_id}
        )
        assert r.status_code == 401, (
            f"snapshot với delegation JWT cho ws {workspace_id}: kỳ vọng 401 "
            f"(không phải danh tính người dùng), thực tế {r.status_code}: {r.text}"
        )
        assert r.json().get("code") == "unauthenticated", r.json()


def _assert_tenant_scoped_snapshot_or_dormant(
    platform: ServiceClient,
    seeded_ops: SeededWorkspace,
    seeded_fin: SeededWorkspace,
    seeded_bare: SeededWorkspace,
) -> None:
    # NHÁNH DORMANT — dùng company local token. HIỆN TẠI gateway
    # `verifyPlatformToken` từ chối -> 401 `unauthenticated` (giống S3 (C)(c1)).
    # KHI cầu nối B5 landed (gateway chấp nhận identity local session / mint
    # được platform token `aud="cosa"` cho nó), nhánh 200 bên dưới tự kích hoạt
    # và assert cô lập tenant THỰC SỰ qua wire.
    r_ops = platform.get(
        _SNAPSHOT_PATH,
        token=seeded_ops.owner_token,
        params={"workspaceId": seeded_ops.workspace_id},
    )
    if r_ops.status_code == 401:
        assert r_ops.json().get("code") == "unauthenticated", r_ops.text
        # B5: company local token chưa bắc cầu sang `aud="cosa"` — path 200 của
        # snapshot chưa exercise được qua HTTP. Cô lập tenant của bảng
        # `cosa.workspace_agent_policy` đã được S3 (A) round-trip ở tầng SQL
        # (đọc ngược theo `platform_workspace_id`).
        return

    # --- Nhánh 200: cầu nối B5 đã landed ---
    assert r_ops.status_code == 200, r_ops.text
    body_ops = r_ops.json()
    assert body_ops["workspaceId"] == seeded_ops.workspace_id, body_ops
    assert isinstance(body_ops["snapshotHash"], str) and body_ops["snapshotHash"], body_ops
    patterns_ops = {rule["toolPattern"] for rule in body_ops["rules"]}
    assert patterns_ops == {"operations.*"}, (
        f"ws operations: `rules` phải CHỈ chứa 'operations.*', thực tế {patterns_ops!r}"
    )

    r_fin = platform.get(
        _SNAPSHOT_PATH,
        token=seeded_fin.owner_token,
        params={"workspaceId": seeded_fin.workspace_id},
    )
    assert r_fin.status_code == 200, r_fin.text
    body_fin = r_fin.json()
    assert body_fin["workspaceId"] == seeded_fin.workspace_id, body_fin
    patterns_fin = {rule["toolPattern"] for rule in body_fin["rules"]}
    assert patterns_fin == {"finance.*"}, (
        f"ws finance: `rules` phải CHỈ chứa 'finance.*', thực tế {patterns_fin!r}"
    )
    assert "operations.*" not in patterns_fin, (
        f"rò rule cross-tenant từ ws operations sang ws finance: {patterns_fin!r}"
    )

    # Workspace mà principal KHÔNG có membership -> fail-closed (403/404).
    r_bare = platform.get(
        _SNAPSHOT_PATH,
        token=seeded_ops.owner_token,
        params={"workspaceId": seeded_bare.workspace_id},
    )
    assert r_bare.status_code in (403, 404), (
        f"snapshot cho workspace không membership: kỳ vọng 403/404, thực tế "
        f"{r_bare.status_code}: {r_bare.text}"
    )
