"""Seed danh tính + workspace qua đường THẬT của stack 4 plane.

Bối cảnh discovery (đã xác nhận đọc code, 2026-09-02):

- `services/company` KHÔNG hỏi `services/cosa` khi giải tenant-context cho các
  route `/operations/*` — `shared/auth/workspace-access.ts::requireWorkspaceAccess`
  gọi `identity/services/tenant-context.service.ts::resolveTenantContext`, hàm này
  (a) verify local access token bằng `JWT_SECRET` (`verifyAccessToken`), (b) tra
  `core.user_projections` theo `sub`, (c) tra `core.workspace_memberships` theo
  `(workspace_id, user_id)`. Tất cả nằm trong DB `workspace` của company.
- Đường seed hợp lệ duy nhất tạo đủ bộ đó + cấp local token là
  `POST /identity/_e2e/session` (`identity/handlers/e2e-session.handler.ts`,
  `expose:false` nhưng gọi được qua HTTP khi `E2E_TEST_SEED_ENABLED=1` — chính
  là pattern các test `tests/e2e/test_mvp_*_http.py` đang dùng). Nó insert
  `core.user_projections` + `core.workspaces` + `core.workspace_memberships`
  (role `founder`) trong 1 transaction rồi trả `{accessToken, userId, workspaceId}`.
- Cosa `POST /platform/auth/register` + `POST /platform/auth/sessions` là một
  plane danh tính KHÁC (bảng `cosa.users`, token ký bằng `PLATFORM_JWT_SECRET`,
  audience `cosa`). Giữ `register_user` / `login` cho scenario nào cần gọi
  `/platform/*`, nhưng token đó KHÔNG dùng được cho business API của company.
- `_e2e/session` luôn tạo workspace RIÊNG + membership `founder` cho user mới,
  nên "member của workspace owner" phải thêm bằng INSERT trực tiếp 1 hàng
  `core.workspace_memberships` (role `member`) vào DB `workspace` của company —
  đây là fallback seed hợp lệ (KHÔNG mock), khớp schema
  `services/company/shared/db/schema/identity.ts`.
"""

from __future__ import annotations

import secrets
import time

import httpx
import psycopg2

from tests.e2e.seed.handles import SeededWorkspace
from tests.e2e.stack.disposable_postgres import DisposableCluster

_TIMEOUT = 20.0


def _snowflake() -> int:
    """Sinh id bigint đơn điệu-tăng, đủ dùng làm PK cho hàng seed thêm tay.

    48 bit thời gian (ms) dịch trái 15 bit + 15 bit ngẫu nhiên — nằm gọn trong
    bigint signed, không đụng khoảng id do `generateSnowflake()` của service cấp.
    """
    return (int(time.time() * 1000) << 15) | secrets.randbits(15)


def register_user(cosa_base_url: str, *, email: str | None = None) -> tuple[str, str, str]:
    """`POST /platform/auth/register` trên `services/cosa` (expose:true, auth:false).

    Body thật: `{email, password, full_name?}` (xem `RegisterParams` trong
    `services/cosa/services/auth.service.ts`). KHÔNG truyền `workspace_name` để
    tránh kích hoạt `provisionVentureWorkspace`. Response: `TokenResponse` với
    `access_token` và `user.id`.

    Trả `(user_id, email, password)`. Lưu ý: đây là danh tính plane cosa, tách
    biệt với local session của company (xem docstring module).
    """
    email = email or f"e2e-{secrets.token_hex(6)}@example.test"
    password = f"Pw-{secrets.token_hex(8)}!"
    with httpx.Client(base_url=cosa_base_url, timeout=_TIMEOUT) as client:
        resp = client.post(
            "/platform/auth/register",
            json={"email": email, "password": password, "full_name": "E2E User"},
        )
    resp.raise_for_status()
    body = resp.json()
    user_id = str(body["user"]["id"])
    return user_id, email, password


def login(cosa_base_url: str, email: str, password: str) -> str:
    """`POST /platform/auth/sessions` trên `services/cosa` -> `access_token` (bearer)."""
    with httpx.Client(base_url=cosa_base_url, timeout=_TIMEOUT) as client:
        resp = client.post("/platform/auth/sessions", json={"email": email, "password": password})
    resp.raise_for_status()
    body = resp.json()
    token = body.get("access_token")
    if not token:
        raise AssertionError(f"login response thiếu access_token: {body}")
    return str(token)


def create_company_session(
    company_base_url: str, *, email: str | None = None, display_name: str = "E2E Owner"
) -> tuple[str, str, str]:
    """`POST /identity/_e2e/session` trên `services/company`.

    Tạo `core.user_projections` + `core.workspaces` + `core.workspace_memberships`
    (role `founder`) trong 1 transaction, trả `{accessToken, userId, workspaceId}`.
    Trả `(user_id, workspace_id, access_token)` — token này DÙNG ĐƯỢC ngay cho
    business API (đi qua `requireWorkspaceAccess`).
    """
    email = email or f"e2e-{secrets.token_hex(6)}@example.test"
    with httpx.Client(base_url=company_base_url, timeout=_TIMEOUT) as client:
        resp = client.post(
            "/identity/_e2e/session",
            json={"email": email, "displayName": display_name},
        )
    assert resp.status_code == 200, f"_e2e/session lỗi ({resp.status_code}): {resp.text}"
    body = resp.json()
    return str(body["userId"]), str(body["workspaceId"]), str(body["accessToken"])


def add_member(
    company_base_url: str,
    cluster: DisposableCluster,
    owner_workspace_id: str,
    *,
    display_name: str = "E2E Member",
    role: str = "member",
) -> tuple[str, str]:
    """Tạo user thứ 2 (qua `_e2e/session`, để service tự ký token thật) rồi
    INSERT 1 hàng `core.workspace_memberships` gắn user đó vào workspace của
    owner với role chỉ định.

    Không tự ký JWT trong Python: token do service phát để tránh phụ thuộc vào
    reproduce đúng thuật toán/secret. Chỉ hàng membership là SQL trực tiếp.
    Trả `(member_user_id, member_token)`.
    """
    member_user_id, _throwaway_ws, member_token = create_company_session(
        company_base_url, display_name=display_name
    )

    conn = psycopg2.connect(cluster.workspace_app_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO core.workspace_memberships (id, workspace_id, user_id, role)
                VALUES (%s, %s, %s, %s)
                """,
                (_snowflake(), int(owner_workspace_id), int(member_user_id), role),
            )
    finally:
        conn.close()

    return member_user_id, member_token


def seed_workspace(
    stack, cluster: DisposableCluster, *, with_member: bool = False
) -> SeededWorkspace:
    """Orchestrator: owner (founder) + tuỳ chọn 1 member cùng workspace.

    Deviation so với brief: chữ ký là `seed_workspace(stack, cluster, *, with_member)`
    (thêm `cluster` để INSERT hàng membership) và toàn bộ đi qua
    `POST /identity/_e2e/session` thay vì `provision_workspace` trên cosa — vì
    tenant-context của business API là company-local, không tra cosa (xem
    docstring module).
    """
    company_url = stack.company.base_url
    owner_user_id, workspace_id, owner_token = create_company_session(
        company_url, display_name="E2E Owner"
    )

    member_user_id: str | None = None
    member_token: str | None = None
    if with_member:
        member_user_id, member_token = add_member(company_url, cluster, workspace_id)

    return SeededWorkspace(
        workspace_id=workspace_id,
        owner_user_id=owner_user_id,
        owner_token=owner_token,
        member_user_id=member_user_id,
        member_token=member_token,
    )
