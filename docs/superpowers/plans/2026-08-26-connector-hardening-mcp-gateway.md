# Connector Control-Plane Hardening + MCP-qua-CapabilityGateway Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vá lỗ hổng cross-tenant P0 trong connector control plane (`services/cosa`), chứng minh bằng E2E test thật qua HTTP, rồi wire MCP tool đầu tiên đi qua `CapabilityGateway` có sẵn (không xây pipeline approval/audit song song), thay thế kế hoạch Agent Skills/Agent Plugins portability cũ.

**Architecture:** `services/cosa` connector endpoints hiện thiếu tenant/membership check ở nhiều chỗ — vá tại chỗ theo pattern `validateUserMembership()` + `AND(companyId, workspaceId)` đã dùng ở nơi khác trong cùng service. MCP tool được đăng ký thành `CapabilitySpec` (đã có `capability_adapter.py`, chỉ cần bổ sung `connector_requirements` + metadata pin version/schema hash) và thực thi qua `CapabilityGateway.execute()`; gateway được vá thêm 1 bước re-verify `ConnectorGrant` (hàm `verify_connector_grant()` đã tồn tại nhưng chưa được gọi ở đâu) ngay trước khi thực thi handler — chạy lại ở **mọi** lần gọi `execute()`, kể cả lần resume sau approval, để không dùng grant đã revoke/hết hạn.

**Tech Stack:** TypeScript/Encore (`services/cosa`), Python (`packages/agent_core`, `apps/cosa`), vitest, pytest, Drizzle ORM, Postgres.

## Global Constraints

- Không tạo `plugin_packages`/`workspace_plugin_installations`/`session_plugin_grants` tables, không tạo parser cho `plugin.json`/`mcp.json`/Agent Plugins v1, không tạo `apps/cosa/capabilities/plugin_component_gate.py` — pilot dùng COSA-native `SkillSpec` + `CapabilityGateway` sẵn có.
- Mọi MCP invocation phải đi qua `CapabilityGateway.execute()` — không có execution path riêng.
- Không đổi cơ chế auth hiện tại của `services/cosa` (`verifyPlatformToken` thủ công) sang Encore `auth: true` — ngoài phạm vi, giữ nguyên pattern đang dùng.
- Không log/trả `secretRef` hoặc raw credential trong bất kỳ response/event/audit nào.
- `packages/agent_core` không được import từ `services/company/*` (giữ nguyên `make boundary-check` pass).
- Test durability/tenant-isolation phải qua HTTP/process thật khi tài liệu yêu cầu — không coi unit-test service function hoặc mock endpoint là đủ bằng chứng.
- Chạy `git status` trước mọi thao tác, không dùng `--force`/`--no-verify`, không commit gì ngoài phạm vi task.

---

## Task 1: Migration 12 — thêm tenant scope vào `connector_authorizations`

**Files:**
- Create: `services/cosa/migrations/12_connector_authorization_tenant_scope.up.sql`
- Modify: `services/cosa/storage/control-plane-schema.ts` (thêm 2 cột vào Drizzle schema của `connectorAuthorizations`)

**Interfaces:**
- Produces: cột `company_id TEXT NOT NULL`, `workspace_id TEXT NOT NULL` trên bảng `control_plane.connector_authorizations`, index `idx_connector_authorizations_tenant (company_id, workspace_id)`. Task 2 dùng 2 cột này để viết WHERE clause tenant-scoped.

- [ ] **Step 1: Viết migration**

```sql
-- Migration 12: Tenant scope cho connector_authorizations — vá lỗ hổng
-- cross-tenant: registerConnectorAuthorization trước đây chỉ query theo
-- installation_id, không xác nhận installation thuộc đúng company/workspace
-- của caller.
ALTER TABLE control_plane.connector_authorizations
  ADD COLUMN company_id TEXT NOT NULL DEFAULT '',
  ADD COLUMN workspace_id TEXT NOT NULL DEFAULT '';

UPDATE control_plane.connector_authorizations ca
SET company_id = wci.company_id, workspace_id = wci.workspace_id
FROM control_plane.workspace_connector_installations wci
WHERE ca.installation_id = wci.id;

ALTER TABLE control_plane.connector_authorizations
  ALTER COLUMN company_id DROP DEFAULT,
  ALTER COLUMN workspace_id DROP DEFAULT;

CREATE INDEX IF NOT EXISTS idx_connector_authorizations_tenant
  ON control_plane.connector_authorizations(company_id, workspace_id);
```

(Migration 11 và các migration trước không có file `.down.sql` tương ứng — giữ đúng convention hiện có, không tạo down migration.)

- [ ] **Step 2: Cập nhật Drizzle schema**

Trong `services/cosa/storage/control-plane-schema.ts`, tìm định nghĩa `connectorAuthorizations` (khớp migration 11: có `installationId`, `principalId`, `secretRef`, `grantedScopes`, `state`, `expiresAt`). Thêm 2 field:

```ts
companyId: text("company_id").notNull(),
workspaceId: text("workspace_id").notNull(),
```

- [ ] **Step 3: Chạy migration trên DB test local**

Run: `cd services/cosa && node scripts/migrate.mjs`
Expected: migration 12 áp dụng thành công, không lỗi (yêu cầu Postgres local đang chạy — `docker compose -f docker-compose.yml up -d postgres` nếu chưa).

- [ ] **Step 4: Commit**

```bash
git add services/cosa/migrations/12_connector_authorization_tenant_scope.up.sql services/cosa/storage/control-plane-schema.ts
git commit -m "feat(cosa): add tenant scope columns to connector_authorizations"
```

---

## Task 2: Vá cross-tenant P0 ở `registerConnectorAuthorization`

**Files:**
- Modify: `services/cosa/services/workspace-connector.service.ts:73-113` (hàm `registerConnectorAuthorization`)
- Modify: `services/cosa/handlers/workspace-connector.handler.ts:12-18,65-81` (`AuthorizeConnectorParams`, `registerAuthorizationEndpoint`)
- Test: `services/cosa/tests/workspace-connector.test.ts`

**Interfaces:**
- Consumes: cột `companyId`/`workspaceId` từ Task 1.
- Produces: `registerConnectorAuthorization(input: { installationId, companyId, workspaceId, principalId, secretRef, grantedScopes, expiresAt })` — chữ ký mới, Task 4 (handler membership check) gọi hàm này với `companyId`/`workspaceId` đã xác thực.

- [ ] **Step 1: Viết failing test — cross-tenant installationId bị từ chối**

Thêm vào `services/cosa/tests/workspace-connector.test.ts`:

```ts
it("rejects registerConnectorAuthorization when installation belongs to a different company", async () => {
  const inst = await connectorSvc.installWorkspaceConnector({
    companyId: "company_a",
    workspaceId: "ws_a",
    connectorKey: "sandbox-read",
    installedBy: "user_a",
  });

  await expect(
    connectorSvc.registerConnectorAuthorization({
      installationId: inst.id,
      companyId: "company_b",
      workspaceId: "ws_b",
      principalId: "user_b",
      secretRef: "secret://cosa-connectors/sandbox-read/b",
      grantedScopes: ["read"],
      expiresAt: new Date(Date.now() + 3600_000),
    })
  ).rejects.toThrow(/not found/i);
});
```

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `cd services/cosa && npm test -- workspace-connector`
Expected: FAIL — hiện tại `registerConnectorAuthorization` không nhận `companyId`/`workspaceId` (TypeScript compile error) hoặc (nếu bạn tạm bỏ type check) thành công tạo authorization thay vì reject.

- [ ] **Step 3: Sửa `registerConnectorAuthorization`**

```ts
export async function registerConnectorAuthorization(input: {
  installationId: string;
  companyId: string;
  workspaceId: string;
  principalId: string;
  secretRef: string;
  grantedScopes: string[];
  expiresAt: Date;
}) {
  validateSecretRef(input.secretRef);

  const [installation] = await db
    .select()
    .from(workspaceConnectorInstallations)
    .where(
      and(
        eq(workspaceConnectorInstallations.id, input.installationId),
        eq(workspaceConnectorInstallations.companyId, input.companyId),
        eq(workspaceConnectorInstallations.workspaceId, input.workspaceId)
      )
    );

  if (!installation || installation.status !== "enabled") {
    throw new Error("installation not found or disabled");
  }

  const id = `conn_auth_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
  const [created] = await db
    .insert(connectorAuthorizations)
    .values({
      id,
      installationId: input.installationId,
      companyId: input.companyId,
      workspaceId: input.workspaceId,
      principalId: input.principalId,
      secretRef: input.secretRef,
      grantedScopes: input.grantedScopes,
      state: "active",
      expiresAt: input.expiresAt,
    })
    .returning();

  return {
    id: created.id,
    installationId: created.installationId,
    principalId: created.principalId,
    grantedScopes: created.grantedScopes,
    state: created.state as ConnectorAuthorizationState,
    expiresAt: created.expiresAt,
    hasSecret: true,
  };
}
```

- [ ] **Step 4: Sửa handler**

Trong `AuthorizeConnectorParams` thêm `companyId: string; workspaceId: string;`. Trong `registerAuthorizationEndpoint`:

```ts
export const registerAuthorizationEndpoint = api(
  { method: "POST", path: "/cosa/connectors/authorize", expose: true },
  async (params: AuthorizeConnectorParams) => {
    if (!params.authorization) throw new Error("missing authorization header");
    const token = params.authorization.replace(/^Bearer\s+/i, "");
    const claims = verifyPlatformToken(token);
    await validateUserMembership({ platformToken: token, companyId: params.companyId });

    const res = await connectorSvc.registerConnectorAuthorization({
      installationId: params.installationId,
      companyId: params.companyId,
      workspaceId: params.workspaceId,
      principalId: claims.sub,
      secretRef: params.secretRef,
      grantedScopes: params.grantedScopes,
      expiresAt: new Date(params.expiresAt),
    });
    return res;
  }
);
```

Thêm import: `import { validateUserMembership } from "../services/company.service";` ở đầu file.

- [ ] **Step 5: Chạy test, xác nhận pass**

Run: `cd services/cosa && npm test -- workspace-connector`
Expected: PASS — bao gồm cả test mới lẫn toàn bộ test cũ trong file (không regress test cross-tenant hiện có ở `grantConnectorToSession`).

- [ ] **Step 6: Commit**

```bash
git add services/cosa/services/workspace-connector.service.ts services/cosa/handlers/workspace-connector.handler.ts services/cosa/tests/workspace-connector.test.ts
git commit -m "fix(cosa): enforce tenant scope on connector authorization registration"
```

---

## Task 3: Thêm membership check cho install/grant/revoke endpoints

**Files:**
- Modify: `services/cosa/handlers/workspace-connector.handler.ts:48-63,83-118` (`installConnectorEndpoint`, `grantConnectorEndpoint`, `revokeGrantEndpoint`)
- Test: `services/cosa/tests/workspace-connector.test.ts`

**Interfaces:**
- Consumes: `validateUserMembership({ platformToken, companyId }): Promise<ValidateMembershipResult>` từ `services/cosa/services/company.service.ts:166-178` (throw `APIError.unauthenticated`/`permissionDenied` khi không hợp lệ — hàm đã tồn tại, không viết mới).

- [ ] **Step 1: Viết failing test — non-member bị từ chối install**

```ts
it("rejects installConnectorEndpoint when caller is not a member of companyId", async () => {
  const tokenNonMember = signPlatformToken("user_not_in_company_a");
  await expect(
    installConnectorEndpoint({
      authorization: `Bearer ${tokenNonMember}`,
      companyId: "company_a",
      workspaceId: "ws_a",
      connectorKey: "sandbox-read",
    })
  ).rejects.toThrow();
});
```

Import ở đầu file test: `import { installConnectorEndpoint, grantConnectorEndpoint, revokeGrantEndpoint, registerAuthorizationEndpoint } from "../handlers/workspace-connector.handler";` và `import { signPlatformToken } from "../services/token.service";`. Nếu môi trường test chưa có sẵn user/membership fixture cho "company_a", thêm setup insert trực tiếp vào bảng `users`/`companies`/`company_memberships` (theo đúng schema đã dùng ở `services/company.service.ts`) trong `beforeAll`/`beforeEach` của file test — dùng `db.insert(...)` giống cách các test khác trong file đã setup dữ liệu.

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `cd services/cosa && npm test -- workspace-connector`
Expected: FAIL — hiện tại `installConnectorEndpoint` không gọi membership check nào, request thành công thay vì bị reject.

- [ ] **Step 3: Thêm `validateUserMembership` vào 3 handler**

```ts
export const installConnectorEndpoint = api(
  { method: "POST", path: "/cosa/connectors/install", expose: true },
  async (params: InstallConnectorParams) => {
    if (!params.authorization) throw new Error("missing authorization header");
    const token = params.authorization.replace(/^Bearer\s+/i, "");
    const claims = verifyPlatformToken(token);
    await validateUserMembership({ platformToken: token, companyId: params.companyId });

    const res = await connectorSvc.installWorkspaceConnector({
      companyId: params.companyId,
      workspaceId: params.workspaceId,
      connectorKey: params.connectorKey,
      installedBy: claims.sub,
    });
    return res;
  }
);
```

```ts
export const grantConnectorEndpoint = api(
  { method: "POST", path: "/cosa/connectors/grant", expose: true },
  async (params: GrantConnectorParams) => {
    if (!params.authorization) throw new Error("missing authorization header");
    const token = params.authorization.replace(/^Bearer\s+/i, "");
    const claims = verifyPlatformToken(token);
    await validateUserMembership({ platformToken: token, companyId: params.companyId });

    const res = await connectorSvc.grantConnectorToSession({
      companyId: params.companyId,
      workspaceId: params.workspaceId,
      conversationId: params.conversationId,
      authorizationId: params.authorizationId,
      grantedBy: claims.sub,
      allowedActions: params.allowedActions || [],
      expiresAt: params.expiresAt ? new Date(params.expiresAt) : null,
    });
    return res;
  }
);
```

```ts
export const revokeGrantEndpoint = api(
  { method: "POST", path: "/cosa/connectors/revoke", expose: true },
  async (params: RevokeGrantParams) => {
    if (!params.authorization) throw new Error("missing authorization header");
    const token = params.authorization.replace(/^Bearer\s+/i, "");
    await validateUserMembership({ platformToken: token, companyId: params.companyId });

    const res = await connectorSvc.revokeSessionGrant({
      companyId: params.companyId,
      workspaceId: params.workspaceId,
      conversationId: params.conversationId,
      grantId: params.grantId,
    });
    return { ok: !!res };
  }
);
```

- [ ] **Step 4: Chạy test, xác nhận pass**

Run: `cd services/cosa && npm test -- workspace-connector`
Expected: PASS toàn bộ file, không regress test happy-path hiện có (member hợp lệ vẫn install/grant/revoke thành công).

- [ ] **Step 5: Commit**

```bash
git add services/cosa/handlers/workspace-connector.handler.ts services/cosa/tests/workspace-connector.test.ts
git commit -m "fix(cosa): require workspace membership on connector install/grant/revoke"
```

---

## Task 4: E2E thật qua HTTP cho vòng đời connector `sandbox-read`

**Files:**
- Create: `tests/apps/cosa/control_plane/test_connector_lifecycle_e2e.py`
- Reference (đọc để tái dùng pattern, không sửa): `tests/apps/cosa/worker/test_crash_recovery_subprocess.py` (fixture `control_plane_dsn`, `control_plane_service`), `tests/apps/cosa/test_tenant_isolation.py:184-187` (mint JWT bằng `pyjwt.encode`)

**Interfaces:**
- Không phụ thuộc code Task 1-3 về mặt import — nhưng **phải chạy sau** Task 1-3 vì test này là bằng chứng E2E cho toàn bộ Wave 0.

- [ ] **Step 1: Viết fixture khởi động control plane thật**

Copy nguyên fixture `control_plane_dsn` và `control_plane_service` từ `tests/apps/cosa/worker/test_crash_recovery_subprocess.py` (bao gồm cơ chế skip nếu thiếu Encore CLI, nếu file gốc có — giữ nguyên logic skip đó) vào file mới `tests/apps/cosa/control_plane/test_connector_lifecycle_e2e.py`. Không viết lại từ đầu — đây là hạ tầng đã kiểm chứng.

- [ ] **Step 2: Viết test happy-path + cross-tenant deny (failing trước khi Task 1-3 merge, dùng để xác nhận)**

```python
from __future__ import annotations

import time
import httpx
import jwt as pyjwt
import pytest

PLATFORM_JWT_SECRET = "cosa-super-secret-platform-jwt-key-change-in-prod"
WORKER_SERVICE_JWT_SECRET = "cosa-worker-service-jwt-key-change-in-prod-min32chars"


def _platform_token(sub: str) -> str:
    return pyjwt.encode(
        {"sub": sub, "aud": "cosa", "exp": int(time.time()) + 3600}, PLATFORM_JWT_SECRET, algorithm="HS256"
    )


def _worker_token() -> str:
    return pyjwt.encode(
        {"sub": "worker_e2e", "aud": "control_plane", "role": "worker_service", "exp": int(time.time()) + 3600},
        WORKER_SERVICE_JWT_SECRET,
        algorithm="HS256",
    )


@pytest.mark.integration
def test_connector_lifecycle_and_cross_tenant_deny(control_plane_service, control_plane_dsn):
    # Seed user_a/company_a/membership_a và user_b/company_b/membership_b trực
    # tiếp vào control_plane_dsn — theo đúng cách test_crash_recovery_subprocess.py
    # seed users/companies/memberships (đọc file đó để lấy đúng câu INSERT/schema
    # trước khi viết đoạn seed này).
    ...
    token_a = _platform_token("user_a")
    token_b = _platform_token("user_b")

    with httpx.Client(base_url=control_plane_service, timeout=10.0) as client:
        # 1. install (tenant A)
        r = client.post(
            "/cosa/connectors/install",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"companyId": "company_a", "workspaceId": "ws_a", "connectorKey": "sandbox-read"},
        )
        assert r.status_code == 200, r.text
        installation_id = r.json()["id"]

        # 2. authorize (tenant A) — response không được chứa secretRef
        r = client.post(
            "/cosa/connectors/authorize",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "installationId": installation_id,
                "companyId": "company_a",
                "workspaceId": "ws_a",
                "secretRef": "secret://cosa-connectors/sandbox-read/token",
                "grantedScopes": ["read"],
                "expiresAt": "2099-01-01T00:00:00Z",
            },
        )
        assert r.status_code == 200, r.text
        assert "secretRef" not in r.json()
        authorization_id = r.json()["id"]

        # 3. session grant (tenant A)
        r = client.post(
            "/cosa/connectors/grant",
            headers={"Authorization": f"Bearer {token_a}"},
            json={
                "companyId": "company_a",
                "workspaceId": "ws_a",
                "conversationId": "conv_a_1",
                "authorizationId": authorization_id,
                "allowedActions": ["read"],
            },
        )
        assert r.status_code == 200, r.text

        # 4. assert (worker) — usable
        r = client.post(
            "/cosa/connectors/assert",
            headers={"Authorization": f"Bearer {_worker_token()}"},
            json={
                "companyId": "company_a",
                "workspaceId": "ws_a",
                "conversationId": "conv_a_1",
                "connectorKey": "sandbox-read",
                "requiredScope": "read",
            },
        )
        assert r.status_code == 200 and r.json()["ok"] is True, r.text

        # 5. cross-tenant deny — tenant B cố authorize installation của tenant A
        r = client.post(
            "/cosa/connectors/authorize",
            headers={"Authorization": f"Bearer {token_b}"},
            json={
                "installationId": installation_id,
                "companyId": "company_b",
                "workspaceId": "ws_b",
                "secretRef": "secret://cosa-connectors/sandbox-read/hijack",
                "grantedScopes": ["read"],
                "expiresAt": "2099-01-01T00:00:00Z",
            },
        )
        assert r.status_code >= 400, r.text

        # 6. revoke (tenant A) -> assert sau đó fail-closed
        r = client.post(
            "/cosa/connectors/revoke",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"companyId": "company_a", "workspaceId": "ws_a", "conversationId": "conv_a_1", "grantId": r.json().get("id", "")},
        )
        r_assert = client.post(
            "/cosa/connectors/assert",
            headers={"Authorization": f"Bearer {_worker_token()}"},
            json={
                "companyId": "company_a",
                "workspaceId": "ws_a",
                "conversationId": "conv_a_1",
                "connectorKey": "sandbox-read",
            },
        )
        assert r_assert.json()["ok"] is False
```

(`grantId` ở bước 6 phải lấy từ response thật của bước 3, không phải biến `r` đã bị ghi đè ở bước 5 — sửa lại biến khi implement thật, đây là điểm cần cẩn thận khi code, không copy nguyên văn máy móc.)

- [ ] **Step 3: Chạy test, xác nhận fail nếu Task 1-3 chưa merge / pass nếu đã merge**

Run:
```bash
PYTHONPATH=. \
  CONTROL_PLANE_TEST_DATABASE_URL="postgresql://javis:javis@127.0.0.1:5432/cosa_control_plane" \
  PLATFORM_JWT_SECRET="cosa-super-secret-platform-jwt-key-change-in-prod" \
  WORKER_SERVICE_JWT_SECRET="cosa-worker-service-jwt-key-change-in-prod-min32chars" \
  .venv/bin/pytest tests/apps/cosa/control_plane/test_connector_lifecycle_e2e.py -v -m integration
```
Expected: PASS (task này chạy sau Task 1-3 trong plan, nên tại thời điểm chạy step này code vá đã có sẵn — vẫn chạy lại để xác nhận không có regression nào từ việc viết test muộn).

- [ ] **Step 4: Thêm case expiry và scope mismatch vào cùng file (mở rộng test hoặc thêm test riêng)**

```python
@pytest.mark.integration
def test_connector_assert_denies_expired_and_scope_mismatch(control_plane_service, control_plane_dsn):
    ...
    # Tạo authorization với expiresAt trong quá khứ, hoặc UPDATE trực tiếp DB
    # test lùi expiresAt sau khi tạo — rồi gọi /cosa/connectors/assert, expect
    # ok=False, error chứa "reauth" hoặc tương đương.
    # Tạo grant với allowedActions=["read"], gọi assert với requiredScope="write"
    # -> expect ok=False.
```

- [ ] **Step 5: Chạy toàn bộ file, xác nhận pass**

Run: (lệnh như Step 3, không thêm `-k`)
Expected: PASS toàn bộ.

- [ ] **Step 6: Thêm vào CI**

Trong `.github/workflows/quality.yml`, tìm job `apps-cosa` (đã chạy `pytest tests/apps/cosa -q`) — xác nhận `tests/apps/cosa/control_plane/` nằm trong path đã include (nó nằm dưới `tests/apps/cosa`, nên không cần sửa gì nếu lệnh hiện tại là `pytest tests/apps/cosa -q`). Đọc lại file CI để xác nhận không có `--ignore` loại trừ thư mục con nào trước khi kết luận không cần sửa.

- [ ] **Step 7: Commit**

```bash
git add tests/apps/cosa/control_plane/test_connector_lifecycle_e2e.py
git commit -m "test(cosa): add real HTTP E2E test for connector lifecycle and cross-tenant deny"
```

---

## Task 5: Fix duplicate `ExecutionTargetSnapshot` definition

**Files:**
- Modify: `packages/agent_core/contracts/capability.py:85-98` (xoá class trùng)
- Modify: `packages/agent_core/contracts/__init__.py:3-9` (đổi nguồn import)
- Test: `tests/agent_core/contracts/test_contracts_all.py` (đã import đúng từ `contracts.target` — chỉ cần xác nhận vẫn pass sau khi xoá)

**Interfaces:**
- Produces: `agent_core.contracts.ExecutionTargetSnapshot` (qua `__init__.py`) giờ là **cùng class** với `agent_core.contracts.target.ExecutionTargetSnapshot` (có `connection_account_id`, `credential_grant_version`, `handler_catalog_version`) — đây là class Task 6 sẽ populate thêm field.

- [ ] **Step 1: Viết failing test xác nhận bug hiện tại**

```python
def test_contracts_init_exports_same_class_as_target_module():
    from agent_core.contracts import ExecutionTargetSnapshot as FromInit
    from agent_core.contracts.target import ExecutionTargetSnapshot as FromTarget
    assert FromInit is FromTarget
```

Thêm vào `tests/agent_core/contracts/test_contracts_all.py`.

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `PYTHONPATH=. .venv/bin/pytest tests/agent_core/contracts/test_contracts_all.py -k same_class -v`
Expected: FAIL — `FromInit is not FromTarget` (2 class khác nhau).

- [ ] **Step 3: Xoá `ExecutionTargetSnapshot` khỏi `capability.py`, sửa `__init__.py`**

Trong `packages/agent_core/contracts/capability.py`, xoá toàn bộ class `ExecutionTargetSnapshot` (dòng 85-98) và xoá `"ExecutionTargetSnapshot"` khỏi `__all__` (dòng 14) của file này.

Trong `packages/agent_core/contracts/__init__.py`:
```python
from agent_core.contracts.capability import (
    CapabilityImplementationIdentity,
    CapabilityReadiness,
    CapabilityReadinessReason,
    CapabilitySpec,
)
from agent_core.contracts.target import ExecutionTargetSnapshot
```
(di chuyển import `ExecutionTargetSnapshot` sang dòng riêng từ `contracts.target`, giữ nguyên vị trí trong `__all__`.)

- [ ] **Step 4: Chạy test, xác nhận pass; chạy toàn bộ suite contracts để bắt regression**

Run: `PYTHONPATH=. .venv/bin/pytest tests/agent_core/contracts tests/agent_core/drift tests/agent_core/p1 tests/agent_core/capabilities -q`
Expected: PASS toàn bộ — không có nơi nào khác trong repo phụ thuộc field `target_id`/`endpoint_url`/`credential_scope` của bản `capability.py` cũ (đã xác nhận qua grep trước khi lên plan: không có import nào dùng riêng bản đó).

- [ ] **Step 5: Commit**

```bash
git add packages/agent_core/contracts/capability.py packages/agent_core/contracts/__init__.py tests/agent_core/contracts/test_contracts_all.py
git commit -m "fix(agent-core): remove duplicate ExecutionTargetSnapshot definition"
```

---

## Task 6: Vá `CapabilityGateway` — re-verify `ConnectorGrant` trước mỗi lần thực thi handler

**Files:**
- Modify: `packages/agent_core/capabilities/gateway.py` (constructor + `execute()`, chèn bước mới ngay trước comment "Bước 9 & 10: Execute Handler" ở dòng 339)
- Test: `tests/agent_core/capabilities/test_gateway_connector_grant.py` (mới)

**Interfaces:**
- Consumes: `ConnectorGrant`, `verify_connector_grant()` từ `packages/agent_core/capabilities/grants.py` (đã tồn tại, chữ ký: `verify_connector_grant(grant, *, action, tenant_id, principal, resource=None, current_time=None) -> GrantVerificationResult`).
- Produces: `CapabilityGateway.__init__(..., connector_grant_resolver: Optional[ConnectorGrantResolver] = None)` với `ConnectorGrantResolver = Callable[[str, GatewayExecutionRequest], Awaitable[Optional[ConnectorGrant]]]` — Task 8 (handler MCP thật) truyền vào 1 resolver gọi HTTP thật sang `services/cosa`.

- [ ] **Step 1: Viết failing test — revoked grant chặn thực thi**

Tạo `tests/agent_core/capabilities/test_gateway_connector_grant.py`:

```python
from __future__ import annotations

import pytest

from agent_core.contracts.capability import CapabilitySpec
from agent_core.governance.contracts import CapabilityRisk
from agent_core.capabilities.gateway import CapabilityGateway, GatewayExecutionRequest
from agent_core.capabilities.grants import ConnectorGrant
from agent_core.capabilities.registry import CapabilityRegistry
from agent_core.runs.repository import InMemoryRunRepository


def _mcp_read_spec() -> CapabilitySpec:
    return CapabilitySpec(
        id="mcp.sandbox_read.list_items",
        risk=CapabilityRisk.MEDIUM,
        connector_requirements={"connector_id": "sandbox-read"},
    )


@pytest.fixture
def gateway_with_grant(monkeypatch):
    registry = CapabilityRegistry()
    repo = InMemoryRunRepository()
    call_counts = {"n": 0}

    def handler(payload, ctx):
        call_counts["n"] += 1
        return {"items": []}

    registry.register(_mcp_read_spec(), handler)

    state = {"grant": ConnectorGrant(
        grant_id="grant_1", tenant_id="ws_a", principal="user_a",
        connector_id="sandbox-read", allowed_actions=("read",), is_revoked=False,
    )}

    async def resolver(connector_id, req):
        return state["grant"]

    gateway = CapabilityGateway(registry=registry, repository=repo, connector_grant_resolver=resolver)
    return gateway, repo, call_counts, state


@pytest.mark.asyncio
async def test_execute_denied_when_connector_grant_revoked(gateway_with_grant):
    gateway, repo, call_counts, state = gateway_with_grant
    state["grant"] = state["grant"].model_copy(update={"is_revoked": True})

    req = GatewayExecutionRequest(
        run_id="run_1", capability_id="mcp.sandbox_read.list_items",
        input_payload={}, workspace_id="ws_a", principal="user_a",
    )
    res = await gateway.execute(req)

    assert res.status == "denied"
    assert call_counts["n"] == 0


@pytest.mark.asyncio
async def test_execute_allowed_when_connector_grant_valid(gateway_with_grant):
    gateway, repo, call_counts, state = gateway_with_grant

    req = GatewayExecutionRequest(
        run_id="run_2", capability_id="mcp.sandbox_read.list_items",
        input_payload={}, workspace_id="ws_a", principal="user_a",
    )
    res = await gateway.execute(req)

    assert res.status == "completed"
    assert call_counts["n"] == 1


@pytest.mark.asyncio
async def test_resume_after_approval_rechecks_grant_and_denies_if_revoked_meanwhile():
    """Capability HIGH risk + connector_requirements -> lần gọi 1 waiting_approval,
    approve, nhưng grant bị revoke TRƯỚC lần gọi 2 (resume) -> resume phải denied,
    không thực thi handler. Đây là bằng chứng trực tiếp cho yêu cầu re-check tại
    thời điểm side effect, không chỉ tại dispatch ban đầu."""
    registry = CapabilityRegistry()
    repo = InMemoryRunRepository()
    call_counts = {"n": 0}

    def handler(payload, ctx):
        call_counts["n"] += 1
        return {"ok": True}

    spec = CapabilitySpec(
        id="mcp.sandbox_write.dangerous_action",
        risk=CapabilityRisk.HIGH,
        connector_requirements={"connector_id": "sandbox-write"},
    )
    registry.register(spec, handler)

    state = {"grant": ConnectorGrant(
        grant_id="grant_2", tenant_id="ws_a", principal="user_a",
        connector_id="sandbox-write", allowed_actions=("*",), is_revoked=False,
    )}

    async def resolver(connector_id, req):
        return state["grant"]

    gateway = CapabilityGateway(registry=registry, repository=repo, connector_grant_resolver=resolver)

    req = GatewayExecutionRequest(
        run_id="run_3", capability_id="mcp.sandbox_write.dangerous_action",
        input_payload={}, workspace_id="ws_a", principal="user_a",
        tool_call_id="call_resume_1", checkpoint_ref="ckpt_resume_1",
    )

    res1 = await gateway.execute(req)
    assert res1.status == "waiting_approval"

    await repo.decide_approval(res1.wait_descriptor.related_ref, reviewer="founder_1", approved=True)

    # Grant bị revoke SAU khi approve, TRƯỚC khi resume
    state["grant"] = state["grant"].model_copy(update={"is_revoked": True})

    res2 = await gateway.execute(req)
    assert res2.status == "denied"
    assert call_counts["n"] == 0
```

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `PYTHONPATH=. .venv/bin/pytest tests/agent_core/capabilities/test_gateway_connector_grant.py -v`
Expected: FAIL — `CapabilityGateway.__init__` chưa nhận `connector_grant_resolver`, `GatewayExecutionRequest` không tự gắn `connector_requirements`, mọi test lỗi TypeError/AttributeError.

- [ ] **Step 3: Implement — thêm resolver + verify step trong gateway.py**

Thêm import ở đầu `gateway.py`:
```python
from agent_core.capabilities.grants import ConnectorGrant, verify_connector_grant
```

Sửa `__init__`:
```python
    def __init__(
        self,
        registry: CapabilityRegistry,
        repository: Optional[RunRepository] = None,
        policy_evaluator: Optional[Callable[[str, dict[str, Any], dict[str, Any]], str]] = None,
        readiness_checker: Optional[CapabilityReadinessChecker] = None,
        governance_store: Optional[GovernanceStateStore] = None,
        connector_grant_resolver: Optional[
            Callable[[str, "GatewayExecutionRequest"], "Any"]
        ] = None,
    ) -> None:
        self._registry = registry
        self._repo = repository or InMemoryRunRepository()
        self._policy_evaluator = policy_evaluator
        self._readiness_checker = readiness_checker or RegistryCapabilityReadinessChecker(registry)
        self._governance_store = governance_store or InMemoryGovernanceStateStore()
        self._idempotency = IdempotencyClaimService(self._repo)
        self._connector_grant_resolver = connector_grant_resolver
```

Chèn bước mới trong `execute()`, ngay sau khối `if effective_outcome == PolicyOutcome.DENY: ...` (dòng 327-337) và **trước** comment `# Bước 9 & 10: Execute Handler` (dòng 339):

```python
        # Bước 8.5: Re-verify Connector Grant — chạy lại ở MỌI lần execute(),
        # kể cả lần resume sau approval (approval được duyệt không có nghĩa
        # grant vẫn còn hiệu lực tại thời điểm side effect thực sự xảy ra).
        connector_id = spec.connector_requirements.get("connector_id")
        if connector_id and self._connector_grant_resolver:
            grant = await self._connector_grant_resolver(connector_id, req)
            verification = verify_connector_grant(
                grant,
                action=req.capability_id,
                tenant_id=req.workspace_id or "",
                principal=req.principal,
            )
            if not verification.is_allowed:
                tc_record.status = "denied"
                tc_record.error_message = f"Connector grant check failed: {verification.reason}"
                await self._repo.save_tool_call(tc_record)
                await self._idempotency.fail(idem_claim.claim_id, error_message=verification.reason)
                await self._repo.append_event(
                    RunEventRecord(
                        run_id=req.run_id,
                        event_type="connector_grant.denied",
                        payload={"tool_call_id": req.tool_call_id, "connector_id": connector_id, "reason": verification.reason},
                    )
                )
                return GatewayExecutionResult(
                    tool_call_id=req.tool_call_id,
                    status="denied",
                    error_message=f"Execution of '{req.capability_id}' denied: {verification.reason}",
                )
```

Populate thêm field còn thiếu của `target_snapshot` (dòng 153-158) — thêm `connection_account_id`/`credential_grant_version` khi có grant (đặt sau bước verify mới, cập nhật object đã tạo ở bước 4 nếu grant hợp lệ):
```python
            target_snapshot.connection_account_id = grant.metadata.get("connection_account_id") if grant else None
            target_snapshot.credential_grant_version = grant.grant_id if grant else None
```
(Thêm 2 dòng này ngay sau khối `if not verification.is_allowed: ... return ...` — chỉ chạy khi verification pass.)

- [ ] **Step 4: Chạy test, xác nhận pass**

Run: `PYTHONPATH=. .venv/bin/pytest tests/agent_core/capabilities/test_gateway_connector_grant.py tests/agent_core/capabilities/test_gateway.py -v`
Expected: PASS toàn bộ — bao gồm cả test cũ `test_gateway.py` (capability không có `connector_requirements` phải hoàn toàn không bị ảnh hưởng, vì `connector_id` sẽ là `None` và bước mới bị skip).

- [ ] **Step 5: Chạy toàn bộ agent-core suite để bắt regression rộng hơn**

Run: `make agent-core-test`
Expected: PASS toàn bộ.

- [ ] **Step 6: Commit**

```bash
git add packages/agent_core/capabilities/gateway.py tests/agent_core/capabilities/test_gateway_connector_grant.py
git commit -m "feat(agent-core): re-verify connector grant before every capability execution"
```

---

## Task 7: Mở rộng `capability_adapter.py` — pin connector/schema cho MCP tool

**Files:**
- Modify: `packages/agent_integrations/mcp/capability_adapter.py`
- Test: `tests/agent_integrations/mcp/test_capability_adapter.py` (tạo mới nếu thư mục test tương ứng chưa tồn tại — kiểm tra `tests/agent_integrations/` có sẵn cấu trúc gì trước khi đặt file, giữ đúng convention đặt test)

**Interfaces:**
- Produces: `register_mcp_tools(registry, tools, caller, *, connector_key: str, catalog_version: str, capability_id_prefix="mcp", risk=CapabilityRisk.MEDIUM) -> list[str]` — thêm 2 tham số bắt buộc `connector_key`, `catalog_version`. Task 8 (handler MCP thật) gọi hàm này với `connector_key="sandbox-read"`.

- [ ] **Step 1: Viết failing test**

```python
from agent_core.capabilities.registry import CapabilityRegistry
from agent_integrations.mcp.capability_adapter import register_mcp_tools


def test_register_mcp_tools_sets_connector_requirements_and_schema_hash():
    registry = CapabilityRegistry()

    async def fake_caller(tool_name, payload):
        return {"ok": True}

    ids = register_mcp_tools(
        registry,
        tools=[{"name": "list_items", "description": "List items", "inputSchema": {"type": "object", "properties": {}}}],
        caller=fake_caller,
        connector_key="sandbox-read",
        catalog_version="1.0.0",
    )

    assert ids == ["mcp.list_items"]
    reg = registry.get("mcp.list_items")
    assert reg.spec.connector_requirements == {"connector_id": "sandbox-read"}
    assert reg.spec.metadata["mcp_server_name"] == "sandbox-read"
    assert "mcp_tool_schema_hash" in reg.spec.metadata
    assert reg.spec.implementation_identity is not None
    assert reg.spec.implementation_identity.schema_version == "1.0.0"
```

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `PYTHONPATH=. .venv/bin/pytest tests/agent_integrations/mcp/test_capability_adapter.py -v`
Expected: FAIL — `register_mcp_tools` chưa nhận `connector_key`/`catalog_version`, `connector_requirements`/`implementation_identity` chưa được set.

- [ ] **Step 3: Implement**

```python
from agent_core.contracts.capability import CapabilityImplementationIdentity, CapabilitySpec
from agent_core.capabilities.canonicalization import compute_payload_hash


def mcp_tool_to_capability_spec(
    tool: dict[str, Any],
    *,
    connector_key: str,
    catalog_version: str,
    capability_id_prefix: str = "mcp",
    risk: CapabilityRisk = CapabilityRisk.MEDIUM,
) -> CapabilitySpec:
    name = tool["name"]
    input_schema = tool.get("inputSchema") or {"type": "object", "properties": {}}
    schema_hash = compute_payload_hash(input_schema)
    return CapabilitySpec(
        id=f"{capability_id_prefix}.{name}",
        description=tool.get("description", ""),
        input_schema=input_schema,
        risk=risk,
        connector_requirements={"connector_id": connector_key},
        implementation_identity=CapabilityImplementationIdentity(
            capability_id=f"{capability_id_prefix}.{name}",
            schema_version=catalog_version,
        ),
        metadata={
            "mcp_tool_name": name,
            "mcp_source": "tools/list",
            "mcp_server_name": connector_key,
            "mcp_tool_schema_hash": schema_hash,
        },
    )


def register_mcp_tools(
    registry: CapabilityRegistry,
    tools: list[dict[str, Any]],
    caller: McpToolCaller,
    *,
    connector_key: str,
    catalog_version: str,
    capability_id_prefix: str = "mcp",
    risk: CapabilityRisk = CapabilityRisk.MEDIUM,
) -> list[str]:
    registered_ids: list[str] = []
    for tool in tools:
        spec = mcp_tool_to_capability_spec(
            tool,
            connector_key=connector_key,
            catalog_version=catalog_version,
            capability_id_prefix=capability_id_prefix,
            risk=risk,
        )
        tool_name = tool["name"]

        async def handler(
            payload: dict[str, Any], ctx: dict[str, Any], *, _tool_name: str = tool_name
        ) -> Any:
            return await caller(_tool_name, payload)

        registry.register(spec, handler)
        registered_ids.append(spec.id)
    return registered_ids
```

- [ ] **Step 4: Chạy test, xác nhận pass**

Run: `PYTHONPATH=. .venv/bin/pytest tests/agent_integrations/mcp/test_capability_adapter.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/agent_integrations/mcp/capability_adapter.py tests/agent_integrations/mcp/test_capability_adapter.py
git commit -m "feat(mcp): pin connector_id and schema hash on registered MCP capabilities"
```

---

## Task 8: Handler MCP `sandbox-read` thật + wiring vào `agent_plane.py`

**Files:**
- Create: `apps/cosa/capabilities/sandbox_read_mcp.py`
- Create: `apps/cosa/capabilities/connector_grant_client.py` (client HTTP gọi `/cosa/connectors/assert`, theo pattern `CompanyServiceClient` ở `apps/cosa/capabilities/client.py`)
- Modify: `apps/cosa/composition/agent_plane.py` (import + đăng ký capability mới quanh dòng 276-295, truyền `connector_grant_resolver` vào `CapabilityGateway`)
- Modify: `packages/pyproject.toml` (hoặc file dependency tương ứng — thêm `mcp` SDK, Python venv đã là 3.11 nên tương thích)

**Interfaces:**
- Consumes: `register_mcp_tools(...)` (Task 7), `CapabilityGateway.__init__(connector_grant_resolver=...)` (Task 6), endpoint `POST /cosa/connectors/assert` (đã hardened ở Task 1-3, không đổi contract).
- Produces: `ConnectorGrantHttpClient.assert_usable(connector_key, company_id, workspace_id, conversation_id, action) -> Optional[ConnectorGrant]` — dùng làm `connector_grant_resolver` cho Task 6.

- [ ] **Step 1: Thêm dependency `mcp` SDK**

Kiểm tra `packages/pyproject.toml` hiện có (đã xác nhận `requires-python = ">=3.11"`, venv thật `.venv/bin/python3` là 3.11.15 — tương thích). Thêm `mcp` vào danh sách dependencies theo đúng format các dependency khác trong file này (đọc file trước khi sửa để khớp style khai báo).

Run: `cd /Volumes/SSD/javis-saas && .venv/bin/pip install -e packages/` (hoặc lệnh cài đặt tương ứng repo đang dùng — kiểm tra `Makefile` mục cài dependency Python trước khi chạy).

- [ ] **Step 2: Viết `connector_grant_client.py`**

```python
from __future__ import annotations

import os
from typing import Optional
import httpx

from agent_core.capabilities.grants import ConnectorGrant

__all__ = ["ConnectorGrantHttpClient"]


class ConnectorGrantHttpClient:
    """Gọi `/cosa/connectors/assert` thật (đã hardened Task 1-3) để lấy trạng
    thái grant hiện tại — dùng làm `connector_grant_resolver` cho
    `CapabilityGateway`. Không tự cache lâu dài: mỗi lần gateway gọi lại,
    client này gọi lại HTTP thật, đúng yêu cầu re-check tại thời điểm side
    effect."""

    def __init__(self, base_url: Optional[str] = None, worker_token_provider=None, timeout: float = 10.0) -> None:
        self.base_url = (base_url or os.environ.get("COSA_CONTROL_PLANE_URL", "http://127.0.0.1:4001")).rstrip("/")
        self._worker_token_provider = worker_token_provider
        self.timeout = timeout

    async def assert_usable(
        self, connector_key: str, *, company_id: str, workspace_id: str, conversation_id: str, action: str
    ) -> Optional[ConnectorGrant]:
        token = self._worker_token_provider() if self._worker_token_provider else os.environ.get("COSA_WORKER_SERVICE_TOKEN", "")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.post(
                f"{self.base_url}/cosa/connectors/assert",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "companyId": company_id,
                    "workspaceId": workspace_id,
                    "conversationId": conversation_id,
                    "connectorKey": connector_key,
                    "action": action,
                },
            )
            data = res.json()
        if not data.get("ok"):
            return None
        return ConnectorGrant(
            grant_id=f"{connector_key}:{conversation_id}",
            tenant_id=workspace_id,
            principal="system",
            connector_id=connector_key,
            allowed_actions=(action,),
            is_revoked=False,
            metadata={"secret_ref": data.get("secretRef", "")},
        )
```

- [ ] **Step 3: Viết `sandbox_read_mcp.py`**

```python
from __future__ import annotations

import os
from typing import Any

from agent_core.capabilities.registry import CapabilityRegistry
from agent_integrations.mcp.capability_adapter import register_mcp_tools

__all__ = ["register_sandbox_read_mcp_tools"]

SANDBOX_READ_MCP_URL = os.environ.get("COSA_SANDBOX_READ_MCP_URL", "")


def register_sandbox_read_mcp_tools(registry: CapabilityRegistry) -> list[str]:
    """Đăng ký MCP tool đọc-only đầu tiên cho pilot (Wave B/C). Chỉ hỗ trợ
    `streamable-http`, chỉ đọc — theo đúng giới hạn pilot đã chốt. Không tự
    thực thi side effect ở đây — handler CHỈ gọi MCP server thật, mọi
    governance/approval/audit vẫn do CapabilityGateway.execute() quyết định."""
    from mcp.client.streamable_http import streamablehttp_client
    from mcp import ClientSession

    async def caller(tool_name: str, payload: dict[str, Any]) -> Any:
        async with streamablehttp_client(SANDBOX_READ_MCP_URL) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, payload)
                return result.model_dump()

    # tools/list tĩnh cho pilot — 1 tool duy nhất, đã review thủ công
    # (đúng nguyên tắc "first-party, reviewed" — không tự động discover
    # runtime từ server bên ngoài trong pilot).
    tools = [
        {
            "name": "list_sandbox_items",
            "description": "List read-only sandbox items for operations reporting.",
            "inputSchema": {"type": "object", "properties": {}},
        }
    ]

    return register_mcp_tools(
        registry,
        tools=tools,
        caller=caller,
        connector_key="sandbox-read",
        catalog_version="1.0.0",
    )
```

- [ ] **Step 4: Wire vào `agent_plane.py`**

Thêm import:
```python
from apps.cosa.capabilities.connector_grant_client import ConnectorGrantHttpClient
from apps.cosa.capabilities.sandbox_read_mcp import register_sandbox_read_mcp_tools
```

Sau dòng `cap_registry.register(FINANCE_TRANSACTION_RECORD_SPEC, ...)` (dòng 280):
```python
    register_sandbox_read_mcp_tools(cap_registry)
```

Sửa khối tạo `CapabilityGateway` (dòng 290-295) để truyền resolver:
```python
    connector_grant_client = ConnectorGrantHttpClient(base_url=control_plane_url)

    async def _connector_grant_resolver(connector_id: str, req):
        return await connector_grant_client.assert_usable(
            connector_id,
            company_id=req.context.get("company_id", ""),
            workspace_id=req.workspace_id or "",
            conversation_id=req.context.get("conversation_id", ""),
            action=req.capability_id,
        )

    gateway = CapabilityGateway(
        registry=cap_registry,
        repository=repo,
        policy_evaluator=policy_engine.evaluate,
        governance_store=gov_store,
        connector_grant_resolver=_connector_grant_resolver,
    )
```

- [ ] **Step 5: Test khởi động compose không lỗi**

Run: `PYTHONPATH=. .venv/bin/python -c "from apps.cosa.composition.agent_plane import build_cosa_agent_plane"`
Expected: import thành công, không lỗi (module `mcp` phải cài được ở Step 1; nếu môi trường CI chưa cho phép cài `mcp`, import `mcp.client.streamable_http` phải là **lazy import bên trong hàm** như đã viết ở Step 3 — không import ở top-level module — để không phá vỡ toàn bộ `agent_plane.py` nếu package chưa sẵn sàng).

- [ ] **Step 6: Chạy full apps-cosa test suite để bắt regression**

Run: `make apps-cosa-test`
Expected: PASS toàn bộ (bao gồm cả `test_tenant_isolation.py`, các test dùng `build_cosa_agent_plane` với `company_client` mock — xác nhận việc thêm `register_sandbox_read_mcp_tools` không phá test hiện có nào giả định số lượng capability cố định trong registry).

- [ ] **Step 7: Commit**

```bash
git add apps/cosa/capabilities/sandbox_read_mcp.py apps/cosa/capabilities/connector_grant_client.py apps/cosa/composition/agent_plane.py packages/pyproject.toml
git commit -m "feat(cosa): wire first-party sandbox-read MCP tool through CapabilityGateway"
```

---

## Task 9: Rewrite tài liệu tích hợp

**Files:**
- Modify: `docs/architecture/COSA_AGENT_SKILLS_AND_AGENT_PLUGINS_INTEGRATION_GUIDE_2026-08-26.md`

**Interfaces:** Không có — đây là tài liệu, không phải code.

- [ ] **Step 1: Viết lại toàn bộ tài liệu**

Cấu trúc mới:
1. Mục 1: Quyết định — COSA-native `SkillSpec` + MCP qua `CapabilityGateway`; lý do không theo Agent Skills/Agent Plugins ở pilot này (tóm tắt: mọi tính năng "mở" của 2 chuẩn đó đều bị tắt trong pilot, không có roadmap marketplace/đối tác cam kết — xem Wave P).
2. Mục 2: Baseline đã verify (SkillSpec/SkillResolver/publish_skill_spec — Task 5-8 KHÔNG động vào các file này, giữ nguyên).
3. Mục 3: Wave 0 — mô tả các fix Task 1-4 (lỗ hổng đã vá, migration 12, E2E test).
4. Mục 4: Wave B — mô tả `capability_adapter.py` mở rộng (Task 7), gateway connector-grant re-check (Task 6), `sandbox_read_mcp.py` (Task 8).
5. Mục 5: Wave C — cấu hình pilot (env `COSA_CONNECTOR_ALLOWED_KEYS=sandbox-read`, giới hạn 1 workspace).
6. Mục 6 (Wave P, parked): điều kiện để mở lại Agent Skills/Agent Plugins — chỉ khi có roadmap marketplace/đối tác cam kết bằng văn bản.
7. File-level implementation map: liệt kê đúng 8 file đã sửa/tạo ở Task 1-8, xoá hoàn toàn map cũ (không còn `plugin_packages`, `agent_plugins_v1.py`, `plugin_component_gate.py`...).
8. Xoá Mục 4, 5, 8 (route plugin-packages/plugin-installations/plugin-grants), 13 cũ.

- [ ] **Step 2: Đối chiếu lại tài liệu với code thật sau khi Task 1-8 đã merge**

Đọc lại từng file được liệt trong file-level implementation map mới, xác nhận tên hàm/class khớp chính xác những gì đã implement (không mô tả field/hàm chưa tồn tại).

- [ ] **Step 3: Commit**

```bash
git add docs/architecture/COSA_AGENT_SKILLS_AND_AGENT_PLUGINS_INTEGRATION_GUIDE_2026-08-26.md
git commit -m "docs(architecture): replace Agent Skills/Agent Plugins plan with native SkillSpec + CapabilityGateway MCP integration"
```

---

## Thứ tự thực hiện

Task 1 → 2 → 3 → 4 (Wave 0, phải xong và pass trước khi sang Wave B) → 5 → 6 → 7 → 8 (Wave B, Task 5 độc lập có thể làm song song với Task 1-4 nếu muốn) → 9 (cuối cùng, sau khi mọi code đã có thật).

## Self-Review

- **Spec coverage:** Wave 0 (hardening + E2E) → Task 1-4. Wave A (native SkillSpec, không xây mới) → không cần task riêng, đã ghi rõ trong Task 9 Mục 2. Wave B (MCP qua Gateway) → Task 5-8. Wave C (pilot config) → mô tả trong Task 9 Mục 5 (không cần task code riêng vì chỉ là biến môi trường). Docs → Task 9. Toàn bộ yêu cầu test trong đề bài (tenant bypass, cross-tenant, missing/expired/revoked, scope mismatch, MCP không gọi khi assertion fail, audit/idempotency, secret không lộ, drift khi resume) đều có mặt trong Task 2-4 và Task 6.
- **Placeholder scan:** không còn "TBD"/"tương tự Task N" — mọi step có code thật hoặc chỉ dẫn cụ thể tới đúng file cần đọc trước khi viết (vd. "đọc file gốc trước khi seed dữ liệu" — đây là chỉ dẫn thao tác cụ thể, không phải placeholder che giấu thiếu thiết kế).
- **Type consistency:** `ConnectorGrant`, `verify_connector_grant`, `GatewayExecutionRequest.workspace_id/principal/context` dùng nhất quán giữa Task 6 và Task 8. `register_mcp_tools(connector_key=..., catalog_version=...)` nhất quán giữa Task 7 và Task 8.
