# COSA Runtime Closure — Phase 2 (Tenant/Security Closure) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close 3 real security gaps confirmed in `docs/implementation/production-runtime-closure.md` (rows 6.1, 6.2, 6.3): `workspace_id` is trusted from client headers with no server-side verification (only `company_id` is verified); a user's real, long-lived platform bearer token is persisted at rest in the durable `scheduled_tasks` queue; Flutter stores `auth_token` in plaintext `SharedPreferences` instead of platform secure storage.

**Architecture:**
1. `services/company` already has a fully-built, tested `resolveTenantContext()` (`services/company/identity/services/tenant-context.service.ts`) that verifies workspace membership server-side and returns an authoritative `TenantContext` — it is just never exposed for an external caller like `apps/cosa` (Python) to reach. Task 1 exposes it as a new HTTP endpoint following the exact pattern already used by `services/company/operations/handlers/task.handler.ts` (`Header<"Authorization">` param, `expose: true`, manual auth inside the service function — no Encore `auth: true` gate needed since `resolveTenantContext` already re-verifies the token itself).
2. `apps/cosa/auth/dependency.py::get_authenticated_identity()` gains a second cross-check call (after the existing `company_id` membership check) to this new endpoint, comparing the server-resolved `workspaceId` against the client's `X-Workspace-Id` header — mismatch is `403 tenant_scope_mismatch`, exactly like the existing `company_id` check.
3. Both `services/cosa` (`token.service.ts::signPlatformToken`) and `apps/cosa` (`jwt.py::verify_platform_token`) already share the same symmetric `PLATFORM_JWT_SECRET` HS256 secret and token shape (`{sub, aud: "cosa"}`). This means `apps/cosa` can mint its own short-TTL (10 min) "delegation" JWT with the same shape using `pyjwt` (already a dependency) — no `services/cosa` changes needed. `apps/cosa/api/routes.py` mints one of these at request time (while the user's real token is still in hand) and puts *that* in the durable queue payload instead of the user's real 7-day token; `apps/cosa/worker/handlers.py` uses it identically to how it used the real token today (it's just another valid platform JWT to the receiving endpoint).
4. Flutter: add `flutter_secure_storage`, migrate `auth_token` (the actual credential) plus the non-sensitive `workspace_id`/`brain_id`/`role` cache values out of `SharedPreferences`, with a one-time migration path so existing logged-in users aren't force-logged-out.

**Tech Stack:** Python 3.11 (FastAPI, pyjwt, httpx), TypeScript/Encore (`services/company`), Dart/Flutter.

## Global Constraints

- Comment mới giải thích *why* viết bằng tiếng Việt; tên định danh/thông báo lỗi hệ thống giữ tiếng Anh.
- `services/company` và `services/cosa` là 2 deploy unit độc lập (CLAUDE.md) — Task 1 chỉ sửa `services/company`, không đổi `services/cosa`.
- Endpoint nội bộ giữa service dùng `expose: false`; endpoint cho client ngoài gọi (ở đây: `apps/cosa`, một Python process ngoài Encore) dùng `expose: true` — theo đúng pattern `task.handler.ts`/`workspace.handler.ts` đã có.
- Lỗi Encore trả qua `APIError` (đã đúng sẵn trong `resolveTenantContext`), không throw `Error` trần.
- Fail closed: bất kỳ lỗi xác minh workspace nào (network, 403, 404, timeout) đều phải là DENY/lỗi rõ ràng, không phải ALLOW ngầm — cùng nguyên tắc đã áp dụng cho company_id check hiện có (`apps/cosa/auth/dependency.py:92-99`).
- `PLATFORM_JWT_SECRET` (env var, dev fallback `"cosa-super-secret-platform-jwt-key-change-in-prod"`) đã dùng chung giữa `apps/cosa/auth/jwt.py` và `services/cosa/services/token.service.ts` — Task 3 dùng lại đúng secret này, không tạo secret mới.
- Không đổi API/schema của `apps/cosa` ra bên ngoài (response shape của REST endpoint) trong plan này — chỉ đổi nội dung `scheduled_tasks.input_payload` (nội bộ, `apps/cosa` tự kiểm soát cả 2 đầu ghi/đọc).
- Chạy test sau mỗi task có sửa test — không tuyên bố "xong" khi chưa chạy (CLAUDE.md #11).
- Python test runner: `PYTHONPATH=. /Volumes/SSD/javis-saas/.venv/bin/pytest <args>` từ repo root.
- TypeScript test runner: `cd services/company && npm test` (= `vitest run`) — cần Postgres thật chạy trên `127.0.0.1:5432` (container `cosa_postgres`, đã có sẵn trong môi trường dev, database `javis`) vì `services/company/identity/tests/*.test.ts` dùng `createTestSession()` chạm DB thật, không mock.

---

### Task 1: Expose `resolveTenantContext` as an HTTP endpoint in `services/company`

**Files:**
- Create: `services/company/identity/handlers/tenant-context.handler.ts`
- Modify: `services/company/identity/handlers/index.ts`
- Create: `services/company/identity/tests/tenant-context-endpoint.test.ts`

**Interfaces:**
- Consumes: `resolveTenantContext(params: ResolveTenantContextParams): Promise<TenantContext>` (existing, `services/company/identity/services/tenant-context.service.ts:38`, unchanged).
- Produces: `POST /identity/tenant-context/resolve` — request body `{ companyId: string; workspaceId?: string; correlationId?: string }` + `Authorization` header; response body is the `TenantContext` JSON (`{companyId, workspaceId, userId, workforceMemberId?, membershipRole, permissions, correlationId}`, camelCase field names, matching `services/company/shared/types/tenant_context.ts`). Consumed by Task 2's Python client.

- [ ] **Step 1: Write the failing test**

Create `services/company/identity/tests/tenant-context-endpoint.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { createTestSession } from "./helpers/test-session";
import { resolveTenantContextEndpoint } from "../handlers/tenant-context.handler";

describe("resolveTenantContextEndpoint", () => {
  it("returns the caller's authoritative workspaceId given a valid local token and workspaceId", async () => {
    const user = await createTestSession({
      email: `tenant-endpoint-${Date.now()}@example.com`,
      displayName: "Endpoint Test",
    });

    const ctx = await resolveTenantContextEndpoint({
      companyId: user.workspaceId,
      workspaceId: user.workspaceId,
      authorization: `Bearer ${user.accessToken}`,
    });

    expect(ctx.workspaceId).toBe(user.workspaceId.toString());
    expect(ctx.userId).toBe(user.userId.toString());
  });

  it("rejects a request with no authorization header", async () => {
    await expect(
      resolveTenantContextEndpoint({
        companyId: "1",
        workspaceId: "1",
        authorization: undefined,
      })
    ).rejects.toThrow();
  });

  it("rejects a workspaceId the caller is not a member of (local identity token path)", async () => {
    const user = await createTestSession({
      email: `tenant-endpoint-deny-${Date.now()}@example.com`,
      displayName: "Endpoint Deny Test",
    });

    await expect(
      resolveTenantContextEndpoint({
        companyId: "999999999999",
        workspaceId: "999999999999",
        authorization: `Bearer ${user.accessToken}`,
      })
    ).rejects.toThrow();
  });
});
```

(This uses `createTestSession()`'s local-identity-token path, matching the existing convention in `tenant-context.test.ts`. It does not attempt to test the platform-token branch here — that branch is exercised end-to-end by Task 2's Python-side tests against a mocked HTTP boundary, and is out of scope for this TS unit test.)

- [ ] **Step 2: Run it to confirm it fails**

```bash
cd services/company && npm test -- tenant-context-endpoint
```
Expected: FAIL — `Cannot find module '../handlers/tenant-context.handler'`.

- [ ] **Step 3: Implement the handler**

Create `services/company/identity/handlers/tenant-context.handler.ts`:

```typescript
import { api, Header } from "encore.dev/api";
import { TenantContext } from "../../shared/types/tenant_context";
import { resolveTenantContext } from "../services/tenant-context.service";

export interface ResolveTenantContextRequest {
  companyId: string;
  workspaceId?: string;
  correlationId?: string;
  authorization?: Header<"Authorization">;
}

/**
 * Cross-check workspace membership server-side cho caller ngoài Encore
 * (apps/cosa, Python) — bọc resolveTenantContext() đã có sẵn và đã test kỹ
 * (services/company/identity/services/tenant-context.service.ts), theo
 * COSA_PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md §6.1: trước đây
 * apps/cosa chỉ verify company_id, còn workspace_id là client-provided
 * scope chưa cross-check.
 */
export const resolveTenantContextEndpoint = api(
  { method: "POST", path: "/identity/tenant-context/resolve", expose: true },
  async ({
    companyId,
    workspaceId,
    correlationId,
    authorization,
  }: ResolveTenantContextRequest): Promise<TenantContext> => {
    return resolveTenantContext({ authorization, companyId, workspaceId, correlationId });
  }
);
```

- [ ] **Step 4: Register the handler in the barrel export**

In `services/company/identity/handlers/index.ts`, add:
```typescript
export * from "./tenant-context.handler";
```
(alongside the existing `auth.handler`/`workforce.handler`/`sync.handler`/`workspace.handler` exports.)

- [ ] **Step 5: Run it to confirm it passes**

```bash
cd services/company && npm test -- tenant-context-endpoint
```
Expected: all 3 tests pass. If Postgres isn't reachable at `127.0.0.1:5432` in your environment, start it first — check `docker ps` for a container named `cosa_postgres` (it should already exist per this repo's dev setup); if stopped, `docker start cosa_postgres`. If genuinely unavailable, report `DONE_WITH_CONCERNS` and note it — do not skip verification silently.

- [ ] **Step 6: Also run the full identity test suite to check for regressions**

```bash
cd services/company && npm test -- identity
```
Expected: no new failures beyond whatever pre-existing baseline exists (check with `git stash` + re-run if unsure whether a failure predates this change).

- [ ] **Step 7: Commit**

```bash
git add services/company/identity/handlers/tenant-context.handler.ts services/company/identity/handlers/index.ts services/company/identity/tests/tenant-context-endpoint.test.ts
git commit -m "feat(company): expose resolveTenantContext as /identity/tenant-context/resolve for external callers"
```

---

### Task 2: Cross-check `workspace_id` server-side in `apps/cosa`

**Files:**
- Create: `apps/cosa/auth/company_client.py`
- Modify: `apps/cosa/auth/dependency.py`
- Modify: `tests/apps/cosa/auth/test_dependency.py`
- Modify: `tests/apps/cosa/auth_test_helpers.py`

**Interfaces:**
- Consumes: `POST /identity/tenant-context/resolve` (Task 1, `COMPANY_SERVICE_URL` — same env var and default `http://localhost:4000` already used by `apps/cosa/capabilities/client.py::CompanyServiceClient`).
- Produces: `apps.cosa.auth.company_client.CompanyTenantContextClient`, `apps.cosa.auth.company_client.CompanyTenantContextError`, `apps.cosa.auth.dependency.set_company_tenant_context_client` (test override, same pattern as existing `set_cosa_auth_client`). `AuthenticatedIdentity.workspace_id` now holds the *server-resolved* value, not the raw client header.

- [ ] **Step 1: Write the failing tests**

Add to `tests/apps/cosa/auth/test_dependency.py` (after the existing imports, add `from apps.cosa.auth.company_client import CompanyTenantContextClient` and `from apps.cosa.auth.dependency import set_company_tenant_context_client`; extend the `_reset_auth_client` fixture to also reset the new client):

```python
def _workspace_client_returning(workspace_id: str) -> CompanyTenantContextClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "companyId": "c1",
                "workspaceId": workspace_id,
                "userId": "99",
                "membershipRole": "founder",
                "permissions": ["*"],
                "correlationId": "corr-1",
            },
        )

    return CompanyTenantContextClient(base_url="http://test", transport=httpx.MockTransport(handler))
```

Update `_reset_auth_client` fixture:
```python
@pytest.fixture(autouse=True)
def _reset_auth_client():
    yield
    set_cosa_auth_client(None)
    set_company_tenant_context_client(None)
```

Add new tests:
```python
@pytest.mark.asyncio
async def test_workspace_id_mismatch_403_tenant_scope_mismatch():
    """Server-resolved workspaceId khác với X-Workspace-Id client gửi lên ->
    403, cùng nguyên tắc với company_id check."""
    set_cosa_auth_client(_client_returning([{"company_id": "c1", "name": "Acme", "role_id": "founder"}]))
    set_company_tenant_context_client(_workspace_client_returning("ws_authoritative"))

    with pytest.raises(HTTPException) as exc:
        await get_authenticated_identity(
            authorization=f"Bearer {_token(sub='99')}", x_company_id="c1", x_workspace_id="ws_client_claimed"
        )
    assert exc.value.status_code == 403
    assert exc.value.detail == "tenant_scope_mismatch"


@pytest.mark.asyncio
async def test_workspace_id_match_succeeds_and_uses_server_resolved_value():
    set_cosa_auth_client(_client_returning([{"company_id": "c1", "name": "Acme", "role_id": "founder"}]))
    set_company_tenant_context_client(_workspace_client_returning("ws_authoritative"))

    identity = await get_authenticated_identity(
        authorization=f"Bearer {_token(sub='99')}", x_company_id="c1", x_workspace_id="ws_authoritative"
    )
    assert identity.workspace_id == "ws_authoritative"


@pytest.mark.asyncio
async def test_workspace_verification_unavailable_fails_closed_502():
    set_cosa_auth_client(_client_returning([{"company_id": "c1", "name": "Acme", "role_id": "founder"}]))

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    set_company_tenant_context_client(
        CompanyTenantContextClient(base_url="http://test", transport=httpx.MockTransport(handler))
    )

    with pytest.raises(HTTPException) as exc:
        await get_authenticated_identity(authorization=f"Bearer {_token(sub='99')}", x_company_id="c1", x_workspace_id="ws1")
    assert exc.value.status_code == 502
```

Also update the existing `test_company_in_membership_list_succeeds` test — it currently doesn't set up a workspace client, so it will start failing once Step 3's wiring lands (no client configured → `get_cosa_auth_client()`-style lazy default would try to reach a real `http://localhost:4000` and fail). Add `set_company_tenant_context_client(_workspace_client_returning("ws1"))` as its first line, before the `get_authenticated_identity(...)` call, so it keeps asserting `identity.workspace_id == "ws1"` — now backed by the (mocked) server-resolved value instead of blind pass-through.

- [ ] **Step 2: Run it to confirm it fails**

```bash
PYTHONPATH=. /Volumes/SSD/javis-saas/.venv/bin/pytest tests/apps/cosa/auth/test_dependency.py -v
```
Expected: `ImportError` for `CompanyTenantContextClient`/`set_company_tenant_context_client` (don't exist yet).

- [ ] **Step 3: Implement the client**

Create `apps/cosa/auth/company_client.py`:

```python
from __future__ import annotations

import os
from typing import Optional

import httpx
from pydantic import BaseModel

__all__ = ["ResolvedTenantContext", "CompanyTenantContextClient", "CompanyTenantContextError"]


class ResolvedTenantContext(BaseModel):
    """Khớp `TenantContext` trong services/company/shared/types/tenant_context.ts."""

    company_id: str
    workspace_id: str
    user_id: str
    membership_role: str
    permissions: list[str]
    correlation_id: str


class CompanyTenantContextError(Exception):
    """Không resolve được TenantContext thật từ services/company — call site
    PHẢI coi đây là DENY, không phải ALLOW ngầm (cùng nguyên tắc §10.5
    freshness invariant đã áp dụng cho CosaControlPlaneAuthError)."""


class CompanyTenantContextClient:
    """Client mỏng gọi `POST /identity/tenant-context/resolve`
    (services/company, expose:true — apps/cosa/auth/company_client.py,
    xem services/company/identity/handlers/tenant-context.handler.ts) để
    cross-check workspace membership của principal đã xác thực — theo
    COSA_PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md §6.1."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        timeout: float = 5.0,
    ) -> None:
        self._base_url = (base_url or os.environ.get("COMPANY_SERVICE_URL", "http://localhost:4000")).rstrip("/")
        self._client = httpx.AsyncClient(base_url=self._base_url, transport=transport, timeout=timeout)

    async def resolve(self, bearer_token: str, company_id: str) -> ResolvedTenantContext:
        try:
            resp = await self._client.post(
                "/identity/tenant-context/resolve",
                json={"companyId": company_id},
                headers={"Authorization": f"Bearer {bearer_token}"},
            )
        except httpx.HTTPError as exc:
            raise CompanyTenantContextError(f"không gọi được services/company: {exc}") from exc

        if resp.status_code != 200:
            raise CompanyTenantContextError(
                f"services/company trả lỗi {resp.status_code}: {resp.text[:200]}"
            )

        try:
            data = resp.json()
        except ValueError as exc:
            raise CompanyTenantContextError(f"services/company trả response không phải JSON: {exc}") from exc

        try:
            return ResolvedTenantContext(
                company_id=data["companyId"],
                workspace_id=data["workspaceId"],
                user_id=data["userId"],
                membership_role=data["membershipRole"],
                permissions=data.get("permissions", []),
                correlation_id=data["correlationId"],
            )
        except KeyError as exc:
            raise CompanyTenantContextError(f"response thiếu field bắt buộc: {exc}") from exc

    async def aclose(self) -> None:
        await self._client.aclose()
```

- [ ] **Step 4: Wire it into `get_authenticated_identity()`**

In `apps/cosa/auth/dependency.py`:

Update `__all__`:
```python
__all__ = [
    "AuthenticatedIdentity",
    "get_authenticated_identity",
    "get_cosa_auth_client",
    "set_cosa_auth_client",
    "set_company_tenant_context_client",
]
```

Add import: `from apps.cosa.auth.company_client import CompanyTenantContextClient, CompanyTenantContextError`

Update `AuthenticatedIdentity`'s docstring (replace the `workspace_id` bullet, lines 29-32):
```python
    - `workspace_id`: `X-Workspace-Id` client gửi lên, nhưng chỉ được chấp
      nhận SAU KHI cross-check khớp với workspace thật trả về từ
      `POST /identity/tenant-context/resolve` (services/company) — cùng
      nguyên tắc với `company_id`, xem `apps/cosa/auth/company_client.py`.
```

Add a module-level client + accessor, mirroring `_cosa_auth_client`/`get_cosa_auth_client`/`set_cosa_auth_client`:
```python
_company_tenant_context_client: Optional[CompanyTenantContextClient] = None


def get_company_tenant_context_client() -> CompanyTenantContextClient:
    global _company_tenant_context_client
    if _company_tenant_context_client is None:
        _company_tenant_context_client = CompanyTenantContextClient()
    return _company_tenant_context_client


def set_company_tenant_context_client(client: Optional[CompanyTenantContextClient]) -> None:
    global _company_tenant_context_client
    _company_tenant_context_client = client
```

In `get_authenticated_identity()`, after the existing `matched = next(...)` / `if matched is None: raise ...` block (right before the final `return AuthenticatedIdentity(...)`), add:

```python
    tenant_client = get_company_tenant_context_client()
    try:
        resolved = await tenant_client.resolve(token, x_company_id)
    except CompanyTenantContextError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"workspace scope verification unavailable: {exc}",
        ) from exc

    if resolved.workspace_id != x_workspace_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant_scope_mismatch")
```

Change the final `return` to use the server-resolved value (defense in depth — even though it now equals `x_workspace_id` after the check above, using `resolved.workspace_id` explicitly keeps the source of truth server-side, not client-side, matching the same pattern `matched.role_id` already uses for `role_id`):
```python
    return AuthenticatedIdentity(
        principal_id=f"user:{principal_id}",
        company_id=x_company_id,
        workspace_id=resolved.workspace_id,
        role_id=matched.role_id,
        bearer_token=token,
    )
```

- [ ] **Step 5: Update `auth_test_helpers.py`**

`override_authenticated_identity()` in `tests/apps/cosa/auth_test_helpers.py` constructs `AuthenticatedIdentity` directly (not through `get_authenticated_identity()`), so it's unaffected by the new HTTP call and needs no change — confirm this by re-reading it: it does not call `get_company_tenant_context_client()` at all. No edit needed here; this step is a verification-only checkpoint, not a code change. (If, on inspection, you find it does need a change, note why in your report — the plan's expectation is zero changes to this file.)

- [ ] **Step 6: Run it to confirm it passes**

```bash
PYTHONPATH=. /Volumes/SSD/javis-saas/.venv/bin/pytest tests/apps/cosa/auth -v
```
Expected: all pass, including the 3 new tests and the updated `test_company_in_membership_list_succeeds`.

- [ ] **Step 7: Run the broader apps/cosa suite for regressions**

```bash
PYTHONPATH=. /Volumes/SSD/javis-saas/.venv/bin/pytest tests/apps/cosa -q --ignore=tests/apps/cosa/worker/test_crash_recovery_subprocess.py
```
Expected: no new failures beyond the established baseline (`test_build_cosa_agent_plane_can_opt_into_langchain_kernel` failing for missing `langchain_core`, and an ERROR in `test_sse_reconnect_e2e.py` — both pre-existing, unrelated). If any *other* test now fails because it goes through `get_authenticated_identity()` via `override_authenticated_identity()` (Step 5 established this helper is unaffected) or via a real, non-overridden path, investigate — this task must not silently break tenant-isolation tests that already pass today.

- [ ] **Step 8: Commit**

```bash
git add apps/cosa/auth/company_client.py apps/cosa/auth/dependency.py tests/apps/cosa/auth/test_dependency.py
git commit -m "fix(cosa): cross-check workspace_id server-side via services/company tenant-context resolve"
```

---

### Task 3: Remove the user's real bearer token from the durable queue

**Files:**
- Modify: `apps/cosa/auth/jwt.py`
- Modify: `apps/cosa/api/routes.py`
- Modify: `apps/cosa/worker/handlers.py`
- Create: `tests/apps/cosa/auth/test_jwt_delegation.py`
- Modify: `tests/apps/cosa/test_vertical_slice_2_write_approval.py` (uses `bearer_token` indirectly via `override_authenticated_identity` — verify, see Step 6)

**Interfaces:**
- Produces: `apps.cosa.auth.jwt.mint_delegation_token(platform_user_id: str, *, ttl_seconds: int = 600) -> str`.
- Changes the `scheduled_tasks.input_payload` shape: the key `"bearer_token"` is replaced by `"delegation_token"` in both the `"run"` and `"resume"` task payloads built by `apps/cosa/api/routes.py`, and consumed identically by `apps/cosa/worker/handlers.py`.

- [ ] **Step 1: Write the failing test for the minting function**

Create `tests/apps/cosa/auth/test_jwt_delegation.py`:

```python
from __future__ import annotations

import time

import jwt as pyjwt
import pytest

from apps.cosa.auth.jwt import mint_delegation_token, verify_platform_token

SECRET = "cosa-super-secret-platform-jwt-key-change-in-prod"


def test_mint_delegation_token_verifies_via_verify_platform_token():
    """Token tự mint phải verify được qua chính hàm verify_platform_token()
    hiện có — chứng minh tương thích với services/cosa
    token.service.ts::verifyPlatformToken() (cùng secret/aud/thuật toán)."""
    token = mint_delegation_token("99")
    assert verify_platform_token(token) == "99"


def test_mint_delegation_token_has_short_ttl_by_default():
    token = mint_delegation_token("99")
    payload = pyjwt.decode(token, SECRET, algorithms=["HS256"], audience="cosa")
    now = int(time.time())
    assert payload["exp"] - now <= 600
    assert payload["exp"] - now > 0


def test_mint_delegation_token_respects_custom_ttl():
    token = mint_delegation_token("99", ttl_seconds=30)
    payload = pyjwt.decode(token, SECRET, algorithms=["HS256"], audience="cosa")
    now = int(time.time())
    assert payload["exp"] - now <= 30


def test_mint_delegation_token_expired_fails_verification():
    token = mint_delegation_token("99", ttl_seconds=-1)
    with pytest.raises(Exception):
        verify_platform_token(token)
```

- [ ] **Step 2: Run it to confirm it fails**

```bash
PYTHONPATH=. /Volumes/SSD/javis-saas/.venv/bin/pytest tests/apps/cosa/auth/test_jwt_delegation.py -v
```
Expected: `ImportError: cannot import name 'mint_delegation_token'`.

- [ ] **Step 3: Implement the minting function**

In `apps/cosa/auth/jwt.py`, update `__all__` to `["InvalidPlatformTokenError", "verify_platform_token", "mint_delegation_token"]`, add `import time` to the imports, and append:

```python
def mint_delegation_token(platform_user_id: str, *, ttl_seconds: int = 600) -> str:
    """Mint 1 JWT ngắn hạn cùng shape với token do
    services/cosa/services/token.service.ts::signPlatformToken() phát hành
    ({sub, aud: "cosa"}, cùng PLATFORM_JWT_SECRET đối xứng) — dùng để thay
    thế bearer token dài hạn (7 ngày) của user thật khi cần lưu credential
    vào durable queue (`scheduled_tasks.input_payload`). TTL mặc định 10
    phút — đủ cho worker xử lý task trong thời gian hợp lý, nhưng giảm mạnh
    cửa sổ rủi ro nếu payload này bị lộ ở rest trong Postgres (COSA_
    PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md §6.2).

    KHÔNG mint token với TTL dài — nếu cần task chạy lâu hơn TTL, worker
    phải re-resolve authorization mới, không phải mint token sống lâu hơn.
    """
    secret = os.environ.get("PLATFORM_JWT_SECRET", _DEV_DEFAULT_SECRET)
    payload = {
        "sub": platform_user_id,
        "aud": "cosa",
        "exp": int(time.time()) + ttl_seconds,
    }
    return jwt.encode(payload, secret, algorithm="HS256")
```

- [ ] **Step 4: Run it to confirm it passes**

```bash
PYTHONPATH=. /Volumes/SSD/javis-saas/.venv/bin/pytest tests/apps/cosa/auth/test_jwt_delegation.py -v
```
Expected: all 4 pass.

- [ ] **Step 5: Wire it into the queue payload construction**

`AuthenticatedIdentity` already carries `principal_id` as `f"user:{principal_id}"` (the `"user:"` prefix is added in `dependency.py`, see `get_authenticated_identity()`'s `return`), but `mint_delegation_token()` needs the *raw* platform user id (matching what `verify_platform_token()` originally returned as `sub`, before the prefix). Add a new field to carry it:

In `apps/cosa/auth/dependency.py`, add a field to `AuthenticatedIdentity` (after `principal_id`):
```python
    principal_id: str
    platform_user_id: str
    company_id: str
```
And in `get_authenticated_identity()`'s final `return`, add `platform_user_id=principal_id,` (the raw `sub`-derived local variable already named `principal_id` in that function, before it gets prefixed into `f"user:{principal_id}"` for the `principal_id` field — both use the same source variable, just one keeps the raw form).

In `tests/apps/cosa/auth_test_helpers.py::override_authenticated_identity()`, add a `platform_user_id: str = "test_user"` parameter and pass it through to the `AuthenticatedIdentity(...)` constructor call — every existing caller of `override_authenticated_identity()` keeps working unchanged since this new parameter has a default.

In `apps/cosa/api/routes.py`:
- Add import: `from apps.cosa.auth.jwt import mint_delegation_token`
- In `create_message()` (the `POST /conversations/{conversation_id}/messages` handler), change the `input_payload` dict passed to `plane.scheduler.schedule(...)`: replace the line `"bearer_token": identity.bearer_token,` with `"delegation_token": mint_delegation_token(identity.platform_user_id),`.
- In `decide_approval()` (the `POST /approvals/{approval_id}/decision` handler), apply the identical change: replace `"bearer_token": identity.bearer_token,` with `"delegation_token": mint_delegation_token(identity.platform_user_id),`.

In `apps/cosa/worker/handlers.py`:
- In `execute_run_task()`: change `bearer_token = payload["bearer_token"]` to `bearer_token = payload["delegation_token"]` (the local variable name `bearer_token` stays — it's still a valid platform bearer token as far as every downstream consumer, e.g. `plane.tenant_policy_client.get_snapshot(bearer_token, company_id)`, is concerned; only its provenance and lifetime changed).
- In `execute_resume_task()`: apply the identical change, `bearer_token = payload["bearer_token"]` → `bearer_token = payload["delegation_token"]`.

- [ ] **Step 6: Update tests that construct these payloads or assert on `AuthenticatedIdentity`'s fields**

Check `tests/apps/cosa/auth_test_helpers.py`'s existing callers for any direct field access on the returned `AuthenticatedIdentity` that would break by the new required-with-default `platform_user_id` field (it has a default, so no caller breaks — this is a verification step, not an expected-edit step). Run:
```bash
PYTHONPATH=. /Volumes/SSD/javis-saas/.venv/bin/pytest tests/apps/cosa/test_vertical_slice_2_write_approval.py -v
```
This test exercises the full run → approval.required → decide → resume → completed flow through real HTTP + the durable scheduler, so it indirectly proves the `delegation_token` key round-trips correctly end-to-end (the worker must successfully call `tenant_policy_client.get_snapshot()` using it, or the run fails). If it fails, the most likely cause is a stale `"bearer_token"` key access left somewhere — grep for it: `grep -rn '"bearer_token"' apps/cosa/`.

- [ ] **Step 7: Add a payload-shape regression test**

Add to `tests/apps/cosa/test_vertical_slice_2_write_approval.py` (or a new small test file `tests/apps/cosa/test_no_bearer_token_in_queue_payload.py` if that file's fixture setup is easier to reuse standalone — prefer adding to the existing vertical-slice-2 test since it already drives a real run through the scheduler):

```python
@pytest.mark.asyncio
async def test_scheduled_task_payload_never_contains_raw_bearer_token(test_app):
    """§6.2: token dài hạn của user thật không được nằm ở rest trong
    scheduled_tasks.input_payload — chỉ delegation_token ngắn hạn."""
    app, plane, mock_client = test_app

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        res_conv = await ac.post("/agent/conversations", json={"title": "Payload Shape Check", "active_agent_profile": "finance"})
        conv_id = res_conv.json()["id"]
        await ac.post(
            f"/agent/conversations/{conv_id}/messages",
            json={"content": "Execute wire payout $500 to Vendor X"},
        )

    tasks = await plane.scheduler.poll_due_tasks()
    assert len(tasks) == 1
    payload = tasks[0].input_payload
    assert "bearer_token" not in payload
    assert "delegation_token" in payload
    assert payload["delegation_token"] != "test-bearer-token"  # not the raw override_authenticated_identity() token
```

Note: this test calls `poll_due_tasks()` directly instead of going through `drain_worker_queue()` (which would claim-and-dispatch the task, consuming it) — it needs to inspect the payload before dispatch. If `poll_due_tasks()` isn't idempotent/re-pollable in the existing `RunScheduler` test double and this causes a conflict with the rest of the test file's flow, place this as its own standalone test function with its own fresh `test_app` fixture invocation rather than sharing state with the main flow test.

- [ ] **Step 8: Run the full affected test set**

```bash
PYTHONPATH=. /Volumes/SSD/javis-saas/.venv/bin/pytest tests/apps/cosa/auth tests/apps/cosa/test_vertical_slice_1_read_path.py tests/apps/cosa/test_vertical_slice_2_write_approval.py tests/apps/cosa/worker/test_main.py -v
```
Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add apps/cosa/auth/jwt.py apps/cosa/auth/dependency.py apps/cosa/api/routes.py apps/cosa/worker/handlers.py tests/apps/cosa/auth/test_jwt_delegation.py tests/apps/cosa/auth_test_helpers.py tests/apps/cosa/test_vertical_slice_2_write_approval.py
git commit -m "fix(cosa): replace long-lived user bearer token in durable queue with short-TTL delegation token"
```

---

### Task 4: Cross-tenant adversarial test — 2 companies, same `workspace_id` collision

**Files:**
- Modify: `tests/apps/cosa/test_tenant_isolation.py`

**Interfaces:**
- Consumes: Task 2's server-side workspace verification (this test is the acceptance test for that fix — a workspace_id collision between two different companies must not leak data, which is only true once Task 2 lands).

- [ ] **Step 1: Write the test**

Add to `tests/apps/cosa/test_tenant_isolation.py`. This needs the `test_app` fixture's `tenant_policy_client=fake_active_tenant_policy_client()` plus a workspace-resolving stub — check `tests/apps/cosa/policy_test_helpers.py` for the shape of `fake_active_tenant_policy_client()` first (read it before writing this step, to follow its exact pattern for a matching `fake_workspace_resolving_client`-style helper, or inline a `CompanyTenantContextClient` with `httpx.MockTransport` directly as done in Task 2's tests):

```python
@pytest.mark.asyncio
async def test_workspace_id_collision_across_companies_does_not_leak(test_app):
    """Company A và Company B trùng workspace_id (vd do migration/seed data
    tình cờ) — server-side workspace resolve PHẢI trả về workspace thật
    thuộc company đang xác thực, không phải blindly trust client header, nên
    A và B (dù cùng gửi X-Workspace-Id: ws_shared) vẫn không nhìn thấy
    conversation của nhau."""
    from apps.cosa.auth.company_client import CompanyTenantContextClient
    from apps.cosa.auth.dependency import set_company_tenant_context_client
    import httpx as _httpx

    def _client_for(expected_company_id: str, resolved_workspace_id: str) -> CompanyTenantContextClient:
        def handler(request: _httpx.Request) -> _httpx.Response:
            return _httpx.Response(
                200,
                json={
                    "companyId": expected_company_id,
                    "workspaceId": resolved_workspace_id,
                    "userId": "u1",
                    "membershipRole": "founder",
                    "permissions": ["*"],
                    "correlationId": "corr-collision-test",
                },
            )

        return CompanyTenantContextClient(base_url="http://test", transport=_httpx.MockTransport(handler))

    override_authenticated_identity(test_app, principal_id="user:alice", company_id="company_a", workspace_id="ws_shared")
    set_company_tenant_context_client(_client_for("company_a", "ws_shared_a_internal"))

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=test_app), base_url="http://test") as ac:
        res_a = await ac.post("/agent/conversations", json={"title": "A's conversation, collided workspace_id"})
        assert res_a.status_code == 201
        conv_id = res_a.json()["id"]

        override_authenticated_identity(test_app, principal_id="user:bob", company_id="company_b", workspace_id="ws_shared")
        set_company_tenant_context_client(_client_for("company_b", "ws_shared_b_internal"))

        res_get = await ac.get(f"/agent/conversations/{conv_id}")
        assert res_get.status_code == 404
```

(This test relies on `_ensure_conversation_tenant_match()` in `apps/cosa/api/routes.py:95-101` already comparing both `company_id` AND `workspace_id` — it does. The new behavior this test locks in is that the *resolved* `workspace_id` values differ even though the client-sent `X-Workspace-Id` header was identical for both tenants, because Task 2 made `AuthenticatedIdentity.workspace_id` come from the server-resolved value, not the raw header.)

- [ ] **Step 2: Run it**

```bash
PYTHONPATH=. /Volumes/SSD/javis-saas/.venv/bin/pytest tests/apps/cosa/test_tenant_isolation.py -v
```
Expected: passes (this is confirming Task 2's fix, not introducing new production code — if it fails, Task 2 has a gap, go back and fix there rather than adjusting this test to match broken behavior).

- [ ] **Step 3: Run the full tenant isolation + auth suite together**

```bash
PYTHONPATH=. /Volumes/SSD/javis-saas/.venv/bin/pytest tests/apps/cosa/test_tenant_isolation.py tests/apps/cosa/auth -v
```
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add tests/apps/cosa/test_tenant_isolation.py
git commit -m "test(cosa): add cross-tenant workspace_id collision adversarial test"
```

---

### Task 5: Flutter secure storage for `auth_token`

**Files:**
- Modify: `frontend/pubspec.yaml`
- Modify: `frontend/lib/modules/auth/services/auth_service.dart`
- Modify: `frontend/lib/core/network/api_client.dart`
- Create: `frontend/test/modules/auth/auth_service_secure_storage_test.dart` (if `frontend/test/` already has a similar unit-test convention for `AuthService` — check `frontend/test/` for an existing `auth_service_test.dart` or similar before creating a new file; extend it instead if found)

**Interfaces:**
- Produces: `AuthService` reads/writes `auth_token` via `flutter_secure_storage` instead of `SharedPreferences`; `workspace_id`/`brain_id`/`role` (non-sensitive cache values, kept for parity with the original audit's scope) move alongside it for consistency, since they're written/read by the exact same call sites.
- `ApiClient._getHeaders()` reads `auth_token`/`workspace_id` from the new storage location.

- [ ] **Step 1: Add the dependency**

In `frontend/pubspec.yaml`, add under the existing `shared_preferences: ^2.5.5` line:
```yaml
  flutter_secure_storage: ^9.2.2
```
Run `flutter pub get` in `frontend/` to resolve it.

- [ ] **Step 2: Create a small storage helper with migration logic**

Create `frontend/lib/core/storage/secure_prefs.dart`:

```dart
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Thay the SharedPreferences (plaintext) bang flutter_secure_storage
/// (Keychain/macOS/iOS, Keystore/Android, Credential Manager/Windows,
/// Secret Service/keyring/Linux khi ho tro) cho cac gia tri auth-scoped:
/// auth_token, workspace_id, brain_id, role. Theo COSA_PRODUCTION_RUNTIME_
/// CLOSURE_ADJUSTMENT_2026-08-25.md muc 6.3.
///
/// _readWithMigration doc mot lan tu SharedPreferences (key cu) neu secure
/// storage chua co gia tri, ghi sang secure storage, roi xoa khoi
/// SharedPreferences - de user dang dang nhap khong bi force-logout khi
/// app update len phien ban nay.
class SecurePrefs {
  static const _storage = FlutterSecureStorage();

  static const List<String> migratedKeys = ['auth_token', 'workspace_id', 'brain_id', 'role'];

  static Future<String?> getString(String key) async {
    final secureValue = await _storage.read(key: key);
    if (secureValue != null) return secureValue;

    if (!migratedKeys.contains(key)) return null;

    final prefs = await SharedPreferences.getInstance();
    final legacyValue = prefs.getString(key);
    if (legacyValue != null) {
      await _storage.write(key: key, value: legacyValue);
      await prefs.remove(key);
      return legacyValue;
    }
    return null;
  }

  static Future<void> setString(String key, String value) async {
    await _storage.write(key: key, value: value);
  }

  static Future<void> remove(String key) async {
    await _storage.delete(key: key);
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(key);
  }
}
```

- [ ] **Step 3: Migrate `auth_service.dart`**

In `frontend/lib/modules/auth/services/auth_service.dart`:
- Add import: `import '../../../core/storage/secure_prefs.dart';`
- `init()` (currently reads `prefs.getString('auth_token')` directly): change to
  ```dart
  static Future<void> init() async {
    _cachedToken = await SecurePrefs.getString('auth_token');
  }
  ```
- `syncFromPlatform()`: replace
  ```dart
  final prefs = await SharedPreferences.getInstance();
  await prefs.setString('auth_token', token);
  ```
  with
  ```dart
  await SecurePrefs.setString('auth_token', token);
  ```
- `getMe()`: replace the three `prefs.setString(...)` calls (`workspace_id`, `brain_id`, `role`) with `SecurePrefs.setString(...)` equivalents, and remove the now-unused `final prefs = await SharedPreferences.getInstance();` line above them if nothing else in that function still needs `prefs`.
- `logout()`: replace
  ```dart
  final prefs = await SharedPreferences.getInstance();
  await prefs.remove('auth_token');
  await prefs.remove('workspace_id');
  await prefs.remove('brain_id');
  await prefs.remove('role');
  ```
  with
  ```dart
  await SecurePrefs.remove('auth_token');
  await SecurePrefs.remove('workspace_id');
  await SecurePrefs.remove('brain_id');
  await SecurePrefs.remove('role');
  ```
- `getCachedRole()`: replace
  ```dart
  final prefs = await SharedPreferences.getInstance();
  return prefs.getString('role');
  ```
  with
  ```dart
  return SecurePrefs.getString('role');
  ```
- Remove the now-unused `import 'package:shared_preferences/shared_preferences.dart';` at the top of the file only if nothing else in it still references `SharedPreferences` directly — grep the file first: `grep -n "SharedPreferences" frontend/lib/modules/auth/services/auth_service.dart` after the edits above; if the only remaining reference is inside `SecurePrefs` (a different file), remove the import.

- [ ] **Step 4: Migrate `api_client.dart`'s header construction**

In `frontend/lib/core/network/api_client.dart`, add import `import '../storage/secure_prefs.dart';`. In `_getHeaders()`, replace:
```dart
    if (requiresAuth) {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString('auth_token');
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }
      final workspaceId = prefs.getString('workspace_id');
      if (workspaceId != null && workspaceId.isNotEmpty) {
        headers['X-Workspace-Id'] = workspaceId;
      }
      final companyId = prefs.getString('company_id');
      if (companyId != null && companyId.isNotEmpty) {
        headers['X-Company-Id'] = companyId;
      }
    }
```
with:
```dart
    if (requiresAuth) {
      final token = await SecurePrefs.getString('auth_token');
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }
      final workspaceId = await SecurePrefs.getString('workspace_id');
      if (workspaceId != null && workspaceId.isNotEmpty) {
        headers['X-Workspace-Id'] = workspaceId;
      }
      // company_id is intentionally still read from SharedPreferences
      // directly here, unchanged — grep across the codebase found no call
      // site that ever writes 'company_id' via prefs.setString(...), so
      // this header is already never sent today; that is a pre-existing
      // gap out of scope for this task (secure-storage migration), not
      // something introduced or fixed here. Flag it to your human partner
      // rather than silently "fixing" it by guessing where it should be
      // set.
      final prefs = await SharedPreferences.getInstance();
      final companyId = prefs.getString('company_id');
      if (companyId != null && companyId.isNotEmpty) {
        headers['X-Company-Id'] = companyId;
      }
    }
```
(Keep the `shared_preferences` import in `api_client.dart` — it's still used for the `company_id` read above.)

- [ ] **Step 5: Check for other direct `SharedPreferences` reads of these 4 keys**

```bash
grep -rn "getString('auth_token')\|getString('workspace_id')\|getString('brain_id')\|getString('role')\|setString('auth_token'\|setString('workspace_id'\|setString('brain_id'\|setString('role'" frontend/lib
```
Any hit outside `auth_service.dart`/`api_client.dart` (already migrated in Steps 3-4) needs the same `SharedPreferences` → `SecurePrefs` swap applied, following the identical pattern. Do not leave a second, un-migrated read/write path for these 4 keys — that would silently defeat the migration for whichever code path still uses it.

- [ ] **Step 6: Manual verification (no automated Flutter test harness assumed)**

Run the app (`cd frontend && flutter run -d macos` or your usual dev target) and manually verify: (a) fresh install → login → app restart → still logged in (token persisted correctly via secure storage); (b) logout → app restart → not logged in, and confirm via platform tooling (e.g. Keychain Access.app on macOS, searching for the app's keychain entries) that `auth_token` is no longer present after logout. If a `frontend/test/` unit-test convention for `AuthService` already exists, add an automated test there instead of/in addition to manual verification — check first with `find frontend/test -iname "*auth_service*"`.

- [ ] **Step 7: Commit**

```bash
git add frontend/pubspec.yaml frontend/pubspec.lock frontend/lib/core/storage/secure_prefs.dart frontend/lib/modules/auth/services/auth_service.dart frontend/lib/core/network/api_client.dart
git commit -m "fix(frontend): store auth_token and related auth cache in flutter_secure_storage instead of SharedPreferences"
```

---

## Out of scope for this plan (tracked separately)

- The `company_id` header is currently never actually populated anywhere in the Flutter codebase (confirmed by grep during Task 5's research — no `prefs.setString('company_id', ...)` call site exists), meaning `X-Company-Id` is likely never sent from the app today. This is a real, separate bug — flagged in Task 5 Step 4's comment — but fixing *where* `company_id` should be persisted (likely after `finishAuthentication()` or the company-picker flow) is outside this plan's scope (workspace/token/storage security) and needs its own investigation into the company-selection UI flow.
- Phase 3 (Durable Queue Recovery — claim/lease/sweeper fields), Phase 4 (Local Capability Hardening — desktop worker `shell=True`), Phase 5 (Composition Lifecycle — FastAPI lifespan), Phase 6 (CI Green Gate & Docs Cleanup) — separate plans, per `docs/implementation/production-runtime-closure.md`.

## Verification (end of Phase 2)

```bash
PYTHONPATH=. /Volumes/SSD/javis-saas/.venv/bin/pytest tests/agent_core tests/apps/cosa packages/agent_testkit --ignore=packages/agent_testkit/kernel_conformance/test_langchain_kernel.py -q
cd services/company && npm test -- identity
```
Expected: no regressions beyond the established pre-existing baseline (documented in Phase 1's plan). Then:
- Grep the whole repo for any remaining raw `bearer_token` key writes into a `scheduled_tasks`-bound payload: `grep -rn '"bearer_token"' apps/cosa/` should show zero hits in `routes.py`/`handlers.py` (only in test files exercising the old/new behavior explicitly, and in unrelated code like `CosaControlPlaneAuthClient`/`CompanyTenantContextClient`/`CosaTenantPolicyClient`, which still legitimately take a `bearer_token` parameter name — they just now receive a short-TTL delegation token instead of the user's real one when called from the worker path).
- Manually confirm (Task 5 Step 6) that `auth_token` is not recoverable from `SharedPreferences`/plist/XML storage after this change, only from the platform secure storage.
