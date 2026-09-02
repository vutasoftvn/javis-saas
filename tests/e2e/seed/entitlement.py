"""Bật một capability prefix cho một workspace (cho scenario S3 — capability gating).

Discovery (2026-09-02):

- Nguồn sự thật cho "workspace X được phép dùng tool prefix Y" ở COSA Control
  Plane là bảng `cosa.workspace_agent_policy` (migration
  `26_workspace_agent_policy_and_drop_legacy_companies.up.sql`): cột
  `platform_workspace_id`, `tool_pattern`, `decision IN ('ALLOW',
  'REQUIRE_APPROVAL','DENY')`, UNIQUE `(platform_workspace_id, tool_pattern)`.
  `services/cosa/services/agent-policy.service.ts::getTenantPolicyForTool` khớp
  `tool_pattern` kết thúc `.*` theo prefix — nên grant = upsert 1 hàng
  `"<prefix>.*" -> ALLOW`.
- `platform_workspace_id` có FK tới `cosa.platform_workspaces(id)` (view alias
  của `cosa.workspaces`), và `cosa.workspaces.owner_user_id` FK tới
  `cosa.users(id)`. Workspace do `POST /identity/_e2e/session` tạo chỉ tồn tại
  trong DB `workspace` của company, chưa có hàng tương ứng ở cosa — nên hàm này
  tự seed hàng `cosa.users` (tối thiểu) + `cosa.workspaces` cùng id trước khi
  upsert policy. Toàn bộ là INSERT trực tiếp theo schema (KHÔNG mock), idempotent
  qua `ON CONFLICT`.

Không có route HTTP expose:true để grant entitlement/policy (chỉ
`POST /platform/internal/agent-policy` expose:false, và nó cũng vướng đúng FK
trên), nên SQL trực tiếp vào `cluster.cosa_app_url` là đường seed hợp lệ.
"""

from __future__ import annotations

import secrets
import time

import psycopg2

from tests.e2e.stack.disposable_postgres import DisposableCluster


def _snowflake() -> int:
    return (int(time.time() * 1000) << 15) | secrets.randbits(15)


def grant_entitlement(
    cluster: DisposableCluster, workspace_id: str, capability_prefix: str
) -> None:
    """Upsert `cosa.workspace_agent_policy`: `"<capability_prefix>.*" -> ALLOW`
    cho `workspace_id`. Idempotent — gọi lại với cùng tham số chỉ `DO UPDATE`.

    Deviation so với brief: chữ ký là `grant_entitlement(cluster, workspace_id,
    capability_prefix)` (bỏ `cosa_base_url` + `owner_token` — không có route
    HTTP dùng được, phải INSERT theo schema).
    """
    wid = int(workspace_id)
    tool_pattern = f"{capability_prefix}.*"

    conn = psycopg2.connect(cluster.cosa_app_url, connect_timeout=10)
    try:
        with conn, conn.cursor() as cur:
            # Đảm bảo có hàng workspace ở cosa để thoả FK của workspace_agent_policy.
            cur.execute("SELECT 1 FROM cosa.workspaces WHERE id = %s", (wid,))
            if cur.fetchone() is None:
                owner_id = _snowflake()
                # `cosa.users` có CHECK `users_email_or_phone_required` — phải có
                # ít nhất email hoặc phone; email lại UNIQUE nên derive theo id.
                cur.execute(
                    """
                    INSERT INTO cosa.users (id, email, hashed_password)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (owner_id, f"e2e-seed-{owner_id}@example.test", "e2e-seed-not-a-real-hash"),
                )
                cur.execute(
                    """
                    INSERT INTO cosa.workspaces (id, workspace_name, owner_user_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (wid, f"E2E seeded workspace {wid}", owner_id),
                )

            cur.execute(
                """
                INSERT INTO cosa.workspace_agent_policy
                    (id, platform_workspace_id, tool_pattern, decision)
                VALUES (%s, %s, %s, 'ALLOW')
                ON CONFLICT (platform_workspace_id, tool_pattern)
                DO UPDATE SET decision = EXCLUDED.decision, updated_at = now()
                """,
                (_snowflake(), wid, tool_pattern),
            )
    finally:
        conn.close()
