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
    platform_base_url: str,
    display_name: str = "E2E Member",
    role: str = "member",
) -> tuple[str, str]:
    """Tạo user thứ 2 (qua `_e2e/session`, để service tự ký token thật) rồi
    INSERT 1 hàng `core.workspace_memberships` gắn user đó vào workspace của
    owner với role chỉ định.

    Không tự ký JWT trong Python: token do service phát để tránh phụ thuộc vào
    reproduce đúng thuật toán/secret. Chỉ hàng membership là SQL trực tiếp.

    B5 fix — `platform_base_url` BẮT BUỘC: link user này sang 1 platform user
    thật (`register_user`) rồi ghi `platform_user_id`, nếu không apps/cosa sẽ
    từ chối tạo run cho user này (thiếu platform identity thật — xem
    `_link_platform_user`).

    Trả `(member_user_id, member_token)`.
    """
    import psycopg2  # import cục bộ — psycopg2 chỉ có ở job e2e-cross-plane-smoke

    member_user_id, _throwaway_ws, member_token = create_company_session(
        company_base_url, display_name=display_name
    )
    member_platform_user_id, _email, _pw = register_user(platform_base_url)
    _link_platform_user(cluster, member_user_id, member_platform_user_id)

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


def _link_platform_user(
    cluster: DisposableCluster, local_user_id: str, platform_user_id: str
) -> None:
    """B5 fix — `_e2e/session` tạo user company-local KHÔNG đi qua platform
    (docstring module: 2 plane danh tính tách biệt), nên `platform_user_id`
    (cột `core.user_projections.platform_user_id`) mặc định rỗng. apps/cosa
    cần cột này để mint control-plane delegation (`AuthenticatedIdentity.
    mint_control_plane_delegation`) — không có nó, mọi call cross-plane thật
    (agent-policy-snapshot, /cosa/schedules*) bị chặn ở B5 dù apps/cosa đã
    fix, giống hệt user thật chưa từng `sync-from-platform`. Set trực tiếp
    bằng SQL (không mock) để mô phỏng đúng 1 user THẬT đã sync."""
    import psycopg2  # import cục bộ — psycopg2 chỉ có ở job e2e-cross-plane-smoke

    conn = psycopg2.connect(cluster.workspace_app_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE core.user_projections SET platform_user_id = %s WHERE id = %s",
                (platform_user_id, int(local_user_id)),
            )
    finally:
        conn.close()


def seed_workforce_founder(cluster: DisposableCluster, workspace_id: str, user_id: str) -> str:
    """Seed workforce_member row and founder role assignment in core schema."""
    import uuid

    import psycopg2

    conn = psycopg2.connect(cluster.workspace_app_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM core.workforce_members WHERE workspace_id = %s AND human_user_id = %s",
                (int(workspace_id), int(user_id)),
            )
            row = cur.fetchone()
            if row:
                wf_id = row[0]
            else:
                wf_id = _snowflake()
                cur.execute(
                    """
                    INSERT INTO core.workforce_members (id, workspace_id, member_type, human_user_id, role_title, status)
                    VALUES (%s, %s, 'HUMAN', %s, 'Founder', 'active')
                    """,
                    (wf_id, int(workspace_id), int(user_id)),
                )

            cur.execute(
                "SELECT id FROM core.workspace_roles WHERE workspace_id = %s AND role_key = 'founder'",
                (int(workspace_id),),
            )
            role_row = cur.fetchone()
            if role_row:
                role_id = role_row[0]
            else:
                role_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO core.workspace_roles (id, workspace_id, role_key, name, is_system, allowed_member_types)
                    VALUES (%s, %s, 'founder', 'Founder', true, ARRAY['HUMAN']::text[])
                    """,
                    (role_id, int(workspace_id)),
                )

            cur.execute(
                """
                INSERT INTO core.member_role_assignments (workspace_id, workforce_member_id, role_id)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (int(workspace_id), wf_id, role_id),
            )

            cur.execute(
                """
                INSERT INTO core.workspace_authorization_states (workspace_id, enforcement_mode, authorization_epoch)
                VALUES (%s, 'SHADOW', 1)
                ON CONFLICT (workspace_id) DO NOTHING
                """,
                (int(workspace_id),),
            )
        return str(wf_id)
    finally:
        conn.close()


def seed_workforce_agent(
    cluster: DisposableCluster,
    workspace_id: str,
    *,
    agent_spec_id: str = "operations",
    role_title: str = "Operations AI",
) -> str:
    """Seed AI_AGENT workforce_member row in core schema."""
    import psycopg2

    conn = psycopg2.connect(cluster.workspace_app_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM core.workforce_members WHERE workspace_id = %s AND agent_spec_id = %s",
                (int(workspace_id), agent_spec_id),
            )
            row = cur.fetchone()
            if row:
                agent_wf_id = row[0]
            else:
                agent_wf_id = _snowflake()
                cur.execute(
                    """
                    INSERT INTO core.workforce_members (id, workspace_id, member_type, agent_spec_id, agent_spec_version, role_title, status)
                    VALUES (%s, %s, 'AI_AGENT', %s, '1.0.0', %s, 'active')
                    """,
                    (agent_wf_id, int(workspace_id), agent_spec_id, role_title),
                )

            # Ensure agent has an operations role with operations.task.read permission
            cur.execute(
                "SELECT id FROM core.workspace_roles WHERE workspace_id = %s AND role_key = 'agent_operations'",
                (int(workspace_id),),
            )
            role_row = cur.fetchone()
            if role_row:
                agent_role_id = role_row[0]
            else:
                import uuid
                agent_role_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO core.workspace_roles (id, workspace_id, role_key, name, is_system, allowed_member_types)
                    VALUES (%s, %s, 'agent_operations', 'Operations Agent Role', false, ARRAY['HUMAN', 'AI_AGENT']::text[])
                    """,
                    (agent_role_id, int(workspace_id)),
                )
                cur.execute(
                    """
                    INSERT INTO core.role_permissions (role_id, permission_key, effect)
                    VALUES (%s, 'operations.task.read', 'ALLOW')
                    ON CONFLICT DO NOTHING
                    """,
                    (agent_role_id,),
                )

            cur.execute(
                """
                INSERT INTO core.member_role_assignments (workspace_id, workforce_member_id, role_id)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (int(workspace_id), agent_wf_id, agent_role_id),
            )

            return str(agent_wf_id)
    finally:
        conn.close()


def seed_default_project(cluster: DisposableCluster, workspace_id: str) -> int:
    """Seed default project in strategy.projects for operational tasks."""
    import psycopg2

    proj_id = _snowflake()
    conn = psycopg2.connect(cluster.workspace_app_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO strategy.projects (id, workspace_id, title, status)
                VALUES (%s, %s, 'Default E2E Project', 'ACTIVE')
                ON CONFLICT DO NOTHING
                """,
                (proj_id, int(workspace_id)),
            )
        return proj_id
    finally:
        conn.close()


def seed_workspace(
    stack, cluster: DisposableCluster, *, with_member: bool = False
) -> SeededWorkspace:
    """Orchestrator: owner (founder) + tuỳ chọn 1 member cùng workspace."""
    company_url = stack.company.base_url
    owner_user_id, workspace_id, owner_token = create_company_session(
        company_url, display_name="E2E Owner"
    )
    owner_platform_user_id, _owner_email, _owner_pw = register_user(stack.platform.base_url)
    _link_platform_user(cluster, owner_user_id, owner_platform_user_id)
    seed_workforce_founder(cluster, workspace_id, owner_user_id)
    seed_default_project(cluster, workspace_id)

    member_user_id: str | None = None
    member_token: str | None = None
    if with_member:
        member_user_id, member_token = add_member(
            company_url, cluster, workspace_id, platform_base_url=stack.platform.base_url
        )

    return SeededWorkspace(
        workspace_id=workspace_id,
        owner_user_id=owner_user_id,
        owner_token=owner_token,
        member_user_id=member_user_id,
        member_token=member_token,
    )

