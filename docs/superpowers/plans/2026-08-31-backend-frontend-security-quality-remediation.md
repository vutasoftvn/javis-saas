# Backend and Frontend Security & Quality Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove confirmed tenant and authorization vulnerabilities, harden public entry points, and restore reproducible quality gates without changing the established three-data-plane architecture.

**Architecture:** The Control Plane remains the only authority for platform memberships and global roles. The Company Plane accepts a workspace only after resolving it from a verified local session; client payloads are treated as display input, never as authorization evidence. Public email capture is isolated in the landing application with strict validation, escaped output, truthful delivery reporting, and an independently enforced abuse limit.

**Tech Stack:** TypeScript/Encore/Drizzle/Vitest, Python/FastAPI/Ruff/Pytest, Flutter/Dart, Next.js/React/Resend, PostgreSQL, Caddy, GitHub Actions.

**Spec:** `docs/architecture/reports/2026-08-31-backend-frontend-audit-delta.md`

## Global Constraints

- `workspace_id` is the sole tenant boundary; tenant reads and writes verify `(workspace_id, resource_id)` or verify the resource belongs to the resolved workspace.
- `services/cosa` owns platform membership and global role authority; `services/company` stores only its verified local projection.
- The client never supplies a role, membership, entitlement, or authoritative delivery result.
- Treat every pre-existing uncommitted file as user-owned: do not modify or include `frontend/lib/core/network/api_client.dart`, `frontend/lib/core/services/secure_storage_service.dart`, `frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart`, `frontend/lib/modules/hologram_hub/services/cofounder_api_service.dart`, `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart`, `frontend/lib/modules/marketing/services/marketing_service.dart`, `frontend/lib/modules/strategy/services/strategy_service.dart`, `frontend/test/strategy_service_test.dart`, or either macOS entitlements file in these commits. Review the secure-storage fallback separately as a macOS Keychain security fix.
- Start every behavior change with a focused failing test. Run the stated focused test before implementation and the stated verification command before committing.
- Do not deploy, change CDN/WAF settings, rotate credentials, or change production Caddy images without explicit infrastructure authorization.
- Keep the existing `workspace` / `cosa` / `agent` database boundaries. No new cross-plane direct database access is allowed.

---

## Delivery order

| Wave | Deliverable | Exit gate |
| --- | --- | --- |
| 1 | Trusted membership sync and immutable global roles | Negative multi-workspace authorization tests pass |
| 2 | Scope every dependency read and bound local-session renewal | Company authorization tests and typecheck pass |
| 3 | Landing validation/delivery correctness and abuse controls | Landing route tests, lint, and production build pass |
| 4 | Enforced rate limiting, clean static analysis, and CI evidence | Staging/WAF evidence plus all local quality gates pass |

## File map

| Path | Responsibility after this plan |
| --- | --- |
| `services/company/identity/services/sync.service.ts` | Fetch and project memberships only from Control Plane evidence. |
| `services/company/identity/services/platform.client.ts` | Typed Control Plane membership lookup used by sync. |
| `services/company/identity/tests/sync.test.ts` | Regression tests against client-injected memberships. |
| `frontend/lib/modules/auth/services/auth_service.dart` | Send only the platform token during local projection sync. |
| `services/cosa/services/auth.service.ts` | Profile fields only; no caller-controlled global role mutation. |
| `services/company/operations/services/task-dependency.service.ts` | Read dependencies only after caller scope and task ownership verification. |
| `landing/src/lib/early-access.ts` | Validate, normalize, escape, and render early-access data. |
| `landing/src/app/api/early-access/route.ts` | Route-level request-size, WAF-facing abuse contract, and truthful delivery response. |
| `deploy/central_vps/Caddyfile` | Reverse proxy only; rate limiting is documented as external until a pinned module is approved. |
| `.github/workflows/quality.yml` | Require static analysis, coverage artifact, and landing route tests. |

### Task 1: Make Control Plane membership the sole source for local sync

**Files:**
- Modify: `services/company/identity/services/sync.service.ts:24-266`
- Modify: `services/company/identity/handlers/sync.handler.ts:1-17`
- Modify: `services/company/identity/tests/sync.test.ts:1-152`
- Modify: `frontend/lib/modules/auth/services/auth_service.dart:293-348`
- Modify: `frontend/lib/modules/auth/controllers/auth_controller.dart:109-119,260-270`
- Test: `frontend/test/auth_flow_test.dart`

**Interfaces:**
- Consumes: `listPlatformWorkspaceMemberships({ platformToken }) -> PlatformWorkspaceMembership[]` and `validatePlatformWorkspaceMembership({ platformToken, platformWorkspaceId })`.
- Produces: `syncFromPlatformService({ platform_access_token: string }) -> SyncFromPlatformResult`; the request has no `user` or `workspaces` fields.

- [ ] **Step 1: Write the failing server-side injection regression**

First, add this helper beneath `wm` so every existing test can resolve a verification response for every requested membership, not only the first one:

```ts
function mockVerifiedMemberships(memberships: Array<ReturnType<typeof wm>>) {
  (validatePlatformWorkspaceMembership as any).mockImplementation(
    async ({ platformWorkspaceId }: { platformWorkspaceId: string }) => {
      const membership = memberships.find((item) => item.platformWorkspaceId === platformWorkspaceId);
      return membership ? { valid: true, ...membership } : { valid: false };
    },
  );
}
```

Replace each one-shot `mockResolvedValueOnce` for `validatePlatformWorkspaceMembership` with `mockVerifiedMemberships([a, b])`, `mockVerifiedMemberships([w])`, or the equivalent fixture list. Then add this regression test. It proves a client-sent founder role is ignored and Control Plane data is persisted instead.

```ts
it("does not trust client-sent workspaces or roles", async () => {
  const canonical = wm({ workspaceName: "Control Plane Workspace", role: "member" });
  (listPlatformWorkspaceMemberships as any).mockResolvedValueOnce([canonical]);
  mockVerifiedMemberships([canonical]);

  const result = await syncFromPlatformService({
    platform_access_token: "tok",
    workspaces: [{
      workspace_id: pwId(),
      workspace_name: "Injected Workspace",
      role_id: "founder",
    }],
  } as any);

  expect(listPlatformWorkspaceMemberships).toHaveBeenCalledWith({ platformToken: "tok" });
  expect(result.workspaces).toEqual([{ workspaceId: canonical.platformWorkspaceId, name: canonical.workspaceName, role: "member", status: "active" }]);
});
```

- [ ] **Step 2: Run the focused test and confirm the vulnerable behavior**

Run: `cd services/company && pnpm vitest run identity/tests/sync.test.ts`

Expected before implementation: FAIL because the returned workspace is `Injected Workspace` with role `founder`, or because the Control Plane mock was not called.

- [ ] **Step 3: Remove the untrusted fast path and verify every returned membership**

Remove `SyncUserPayload`, `SyncWorkspacePayload`, `user`, `workspaces`, and the `isFastPath` branch. Replace source selection with the following shape, then use only the verified array in the transaction.

```ts
const workspaceMemberships = await listPlatformWorkspaceMemberships({ platformToken: token });
const verifiedMemberships = await Promise.all(
  workspaceMemberships.map(async (membership) => {
    const verified = await validatePlatformWorkspaceMembership({
      platformToken: token,
      platformWorkspaceId: membership.platformWorkspaceId,
    });
    if (!verified.valid || verified.userId !== platformUserId) {
      throw APIError.permissionDenied("control-plane membership verification failed");
    }
    return { ...membership, email: verified.email, displayName: verified.displayName, role: verified.role };
  })
);
```

Use `verifiedMemberships` for every workspace and membership upsert. Preserve the existing transaction and `platformMembershipId` uniqueness behavior. In Flutter, call `syncFromPlatform` with only `platform_access_token`; remove the now-unused `user` and `workspaces` parameters from its signature, `finishAuthentication`, and the two controller call sites. `loginResult.user`, `loginResult.rawWorkspaces`, and `companyResult.rawWorkspaces` must not cross the sync boundary.

- [ ] **Step 4: Verify focused server and client contracts**

Run:

```bash
cd services/company && pnpm typecheck && pnpm vitest run identity/tests/sync.test.ts identity/tests/gateway-auth.test.ts
cd ../../frontend && flutter test test/auth_flow_test.dart
```

Expected: all listed tests pass and no Flutter caller sends `workspaces:` to `/identity/sync-from-platform`.

- [ ] **Step 5: Commit the isolated security fix**

```bash
git add services/company/identity/services/sync.service.ts services/company/identity/handlers/sync.handler.ts services/company/identity/tests/sync.test.ts frontend/lib/modules/auth/services/auth_service.dart frontend/lib/modules/auth/controllers/auth_controller.dart frontend/test/auth_flow_test.dart
git commit -m "fix(identity): derive local memberships from control plane"
```

### Task 2: Prevent callers from assigning their own global role

**Files:**
- Modify: `services/cosa/services/auth.service.ts:74-81,280-326`
- Modify: `services/cosa/handlers/auth.handler.ts:78-96`
- Modify: `services/cosa/tests/control-plane.test.ts:57-75`
- Test: `services/cosa/tests/control-plane.test.ts`

**Interfaces:**
- Consumes: authenticated `AuthData.userID` and public profile fields `phone`, `full_name`, `avatar_url`, `headline`, `bio`.
- Produces: `UpdateMeParams` without `role_id`; `PATCH /platform/auth/me` cannot mutate `profiles.role_id`.

- [ ] **Step 1: Write the failing self-escalation test**

Add this test after the profile update test. It uses the existing exported helper and proves that even a direct caller cannot persist a global-role value.

```ts
it("does not mutate the global role from self-profile input", async () => {
  const userID = verifyPlatformToken(platformToken).sub;
  const before = await getMe({ userID });
  const updated = await updateMe({ userID }, { role_id: "superadmin" } as any);
  expect(updated.role_id).toBe(before.role_id);
});
```

The test must call `updateMe({ userID }, params)`, not a private SQL helper.

- [ ] **Step 2: Run the focused test**

Run: `cd services/cosa && pnpm vitest run tests/control-plane.test.ts`

Expected before implementation: FAIL because `role_id: "superadmin"` is written successfully.

- [ ] **Step 3: Narrow the request schema and reject role fields at the boundary**

Delete `role_id` from `UpdateMeParams`. Remove both `roleId: params.role_id` assignments from `updatePlatformUserProfile`. In `updatePlatformUserMe`, reject a request that contains `role_id` before it reaches the service.

```ts
export const updatePlatformUserMe = api(
  { method: "PATCH", path: "/platform/auth/me", expose: true, auth: true },
  async (params: UpdateMeParams & { role_id?: unknown }): Promise<PlatformUserProfile> => {
    if (params.role_id !== undefined) throw APIError.invalidArgument("role_id cannot be changed by profile update");
    return updateMe(await resolveAuthData(), params);
  }
);
```

Do not add an admin role-management endpoint in this task. Role assignment remains a controlled operational/migration action until a separately specified authorization model exists.
Remove `role_id: "founder"` from the existing normal-profile-update test input; founder remains its expected stored role, not a caller-selected profile field.

- [ ] **Step 4: Verify type and behavior**

Run: `cd services/cosa && pnpm typecheck && pnpm vitest run tests/control-plane.test.ts`

Expected: profile field updates pass; the direct regression test leaves the stored founder role unchanged; the HTTP handler rejects an unexpected `role_id` with `invalidArgument`.

- [ ] **Step 5: Commit the public-contract change**

```bash
git add services/cosa/services/auth.service.ts services/cosa/handlers/auth.handler.ts services/cosa/tests/control-plane.test.ts
git commit -m "fix(auth): prohibit self-assigned platform roles"
```

### Task 3: Scope task-dependency reads to an authenticated workspace

**Files:**
- Modify: `services/company/operations/handlers/task-dependency.handler.ts:28-34`
- Modify: `services/company/operations/services/task-dependency.service.ts:98-107`
- Modify: `services/company/operations/tests/task-dependency.test.ts:1-116`
- Test: `services/company/operations/tests/task-dependency.test.ts`

**Interfaces:**
- Consumes: `Authorization` and `X-Workspace-Id` headers plus `taskId`.
- Produces: `listTaskDependenciesService(taskId, workspaceId, authorization) -> Promise<TaskDependency[]>`; an unauthenticated or cross-workspace request is rejected.

- [ ] **Step 1: Write failing negative authorization tests**

Add both tests to the existing suite.

```ts
it("rejects dependency listing without an access token", async () => {
  await expect(listTaskDependencies({ taskId: "123" } as any)).rejects.toThrow(/authorization/i);
});

it("does not list dependencies for a task in another workspace", async () => {
  const a = await makeAuthedWorkspace("Dependency Read A");
  const b = await makeAuthedWorkspace("Dependency Read B");
  const task = await createTask({ workspaceId: a.workspaceId, title: "private", authorization: a.authorization });

  await expect(listTaskDependencies({ taskId: task.id, workspaceId: b.workspaceId, authorization: b.authorization } as any))
    .rejects.toThrow(/not in this workspace|not found/i);
});
```

- [ ] **Step 2: Run the focused Company suite**

Run: `cd services/company && pnpm vitest run operations/tests/task-dependency.test.ts`

Expected before implementation: FAIL because `listTaskDependencies` has no headers and returns a query result.

- [ ] **Step 3: Verify scope before querying dependencies**

Change the handler parameter type to `WithAuthHeaders<{ taskId: string }>` and pass both headers to the service. Implement the service boundary exactly once.

```ts
export async function listTaskDependenciesService(
  taskId: string | number,
  workspaceId: string,
  authorization?: string,
): Promise<TaskDependency[]> {
  const ctx = await requireWorkspaceAccess(authorization, workspaceId);
  await assertTasksInWorkspace([BigInt(taskId)], BigInt(ctx.workspaceId));
  const targetId = BigInt(taskId);
  const rows = await db.select().from(taskDependencies)
    .where(or(eq(taskDependencies.taskId, targetId), eq(taskDependencies.dependsOnTaskId, targetId)))
    .orderBy(asc(taskDependencies.id));
  return rows.map(toTaskDependency);
}
```

- [ ] **Step 4: Verify affected Company checks**

Run:

```bash
cd services/company && pnpm typecheck && pnpm vitest run operations/tests/task-dependency.test.ts
```

Expected: valid workspace reads pass; no-token and cross-workspace reads fail.

- [ ] **Step 5: Commit the read-path authorization fix**

```bash
git add services/company/operations/handlers/task-dependency.handler.ts services/company/operations/services/task-dependency.service.ts services/company/operations/tests/task-dependency.test.ts
git commit -m "fix(operations): scope task dependency reads"
```

### Task 4: Bound credential lifetime and improve registration policy

**Files:**
- Modify: `services/company/identity/services/token.service.ts:17-62`
- Modify: `services/company/identity/handlers/auth.handler.ts:64-82`
- Modify: `services/cosa/services/auth.service.ts:157-176`
- Modify: `services/company/identity/tests/gateway-auth.test.ts`
- Modify: `services/cosa/tests/control-plane.test.ts`
- Modify: `services/cosa/tests/agent-policy.test.ts`
- Modify: `frontend/lib/modules/auth/controllers/auth_controller.dart:180-205`
- Modify: `frontend/lib/modules/auth/views/register_view.dart:238`
- Modify: `frontend/test/auth_flow_test.dart:330-344`

**Interfaces:**
- Consumes: `COMPANY_LOCAL_SESSION_TTL` and new `COMPANY_LOCAL_SESSION_MAX_AGE_SECONDS` (default `604800`).
- Produces: local JWT claims `{ sub, auth_time }`; renewal preserves `auth_time` and rejects tokens older than the configured maximum age. Registration accepts passwords of 12–128 characters.

- [ ] **Step 1: Write failing bounded-renewal and password-policy tests**

Add a token test with a signed expired token whose `auth_time` is older than seven days, then assert renewal fails. Add registration tests for 11, 12, and 129 character passwords.

```ts
const expiredToken = jwt.sign(
  { sub: "expired-user", auth_time: Math.floor(Date.now() / 1000) - 8 * 24 * 60 * 60 },
  process.env.JWT_SECRET || "cosa-dev-jwt-secret-do-not-use-in-prod",
  { expiresIn: "-1s" },
);
expect(() => renewAccessToken(expiredToken))
  .toThrow(/maximum age/i);
await expect(registerPlatform({ email: "short@example.com", password: "12345678901" })).rejects.toThrow(/12/i);
await expect(registerPlatform({ email: "long@example.com", password: "1".repeat(129) })).rejects.toThrow(/128/i);
await expect(registerPlatform({ email: "valid@example.com", password: "123456789012" })).resolves.toMatchObject({ access_token: expect.any(String) });
```

- [ ] **Step 2: Run the focused tests**

Run:

```bash
cd services/company && pnpm vitest run identity/tests/gateway-auth.test.ts
cd ../cosa && pnpm vitest run tests/control-plane.test.ts tests/agent-policy.test.ts
cd ../../frontend && flutter test test/auth_flow_test.dart
```

Expected before implementation: an expired token inside the renewal grace window is renewed regardless of original authentication time, and 6–11 character passwords are accepted.

- [ ] **Step 3: Preserve original authentication time**

Use a typed payload and preserve `auth_time` across renewals.

```ts
export interface JwtPayload { sub: string; auth_time: number; }

export function signAccessToken(userId: string, authTime = Math.floor(Date.now() / 1000)): string {
  return jwt.sign({ sub: userId, auth_time: authTime }, getJwtSecret(), { expiresIn: getSessionTtl() as any });
}

if (Date.now() / 1000 - payload.auth_time > getMaximumSessionAgeSeconds()) {
  throw new Error("local session exceeds maximum age");
}
return signAccessToken(payload.sub, payload.auth_time);
```

Set the Control Plane password validation to `params.password.length < 12 || params.password.length > 128`. In the Flutter registration controller use the identical bounds and message; set the registration field label to `Mật khẩu (12–128 ký tự)`. Keep bcrypt hashing and do not log credentials. Login remains backward compatible for accounts created under the former six-character policy.

```dart
if (password.length < 12 || password.length > 128) {
  registerErrorMessage.value = 'Mật khẩu phải có từ 12 đến 128 ký tự';
  return;
}
```

Replace the existing 11-character `password123` registration fixtures with `password1234` in both `services/cosa/tests/control-plane.test.ts` and `services/cosa/tests/agent-policy.test.ts`. Update the Flutter validation assertion to expect `12 đến 128`.

- [ ] **Step 4: Verify authentication behavior**

Run:

```bash
cd services/company && pnpm typecheck && pnpm vitest run identity/tests/gateway-auth.test.ts
cd ../cosa && pnpm typecheck && pnpm vitest run tests/control-plane.test.ts tests/agent-policy.test.ts
cd ../../frontend && flutter test test/auth_flow_test.dart
```

Expected: normal renewal still works, max-age renewal fails, and only 12–128 character registration passwords are accepted.

- [ ] **Step 5: Commit the credential policy change**

```bash
git add services/company/identity/services/token.service.ts services/company/identity/handlers/auth.handler.ts services/company/identity/tests/gateway-auth.test.ts services/cosa/services/auth.service.ts services/cosa/tests/control-plane.test.ts services/cosa/tests/agent-policy.test.ts frontend/lib/modules/auth/controllers/auth_controller.dart frontend/lib/modules/auth/views/register_view.dart frontend/test/auth_flow_test.dart
git commit -m "fix(auth): bound local renewals and strengthen passwords"
```

### Task 5: Make early-access capture safe and truthful

**Files:**
- Create: `landing/src/lib/early-access.ts`
- Create: `landing/src/lib/early-access.test.ts`
- Create: `landing/src/app/api/early-access/route.test.ts`
- Create: `docs/operations/landing.md`
- Modify: `landing/src/app/api/early-access/route.ts:1-92`
- Modify: `landing/src/lib/resend.ts:1-253`
- Modify: `landing/package.json`
- Create: `landing/vitest.config.ts`

**Interfaces:**
- Consumes: raw JSON request body.
- Produces: `parseEarlyAccessRegistration(input) -> EarlyAccessRegistrationInput`, `escapeHtml(value) -> string`, and `sendEarlyAccessEmails(data) -> { userEmailSent: boolean; adminEmailSent: boolean; simulated?: boolean; error?: string }`.

- [ ] **Step 1: Add failing parser, escaping, and route tests**

Create `landing/src/lib/early-access.test.ts`.

```ts
import { describe, expect, it } from "vitest";
import { escapeHtml, parseEarlyAccessRegistration } from "./early-access";

describe("early access input", () => {
  it("rejects malformed or overlong input", () => {
    expect(() => parseEarlyAccessRegistration({ fullName: "A", email: "bad", phone: "1", company: "" })).toThrow();
    expect(() => parseEarlyAccessRegistration({ fullName: "A".repeat(121), email: "a@example.com", phone: "0912345678", company: "C" })).toThrow();
  });

  it("escapes all HTML metacharacters before email rendering", () => {
    expect(escapeHtml('<img src=x onerror=alert(1)>')).toBe('&lt;img src=x onerror=alert(1)&gt;');
  });
});
```

Create `landing/src/app/api/early-access/route.test.ts` with a mocked mailer. The four route cases must be present before implementation.

```ts
import type { NextRequest } from "next/server";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/resend", () => ({ sendEarlyAccessEmails: vi.fn() }));
import { POST } from "./route";
import { sendEarlyAccessEmails } from "@/lib/resend";

const validBody = { fullName: "Ada Lovelace", email: "ada@example.com", phone: "0912345678", company: "Analytical Engines" };
const post = (body: string) => POST(new Request("http://localhost/api/early-access", {
  method: "POST", headers: { "content-type": "application/json" }, body,
}) as NextRequest);

describe("POST /api/early-access", () => {
  it("returns 400 for invalid JSON", async () => expect((await post("{" )).status).toBe(400));
  it("returns 413 for an oversized body", async () => expect((await post(JSON.stringify({ ...validBody, note: "x".repeat(17_000) }))).status).toBe(413));
  it("returns 502 when the real user-email delivery fails", async () => {
    vi.mocked(sendEarlyAccessEmails).mockResolvedValueOnce({ userEmailSent: false, adminEmailSent: false, simulated: false, error: "provider down" });
    expect((await post(JSON.stringify(validBody))).status).toBe(502);
  });
  it("returns 200 only after real user-email delivery", async () => {
    vi.mocked(sendEarlyAccessEmails).mockResolvedValueOnce({ userEmailSent: true, adminEmailSent: true });
    expect((await post(JSON.stringify(validBody))).status).toBe(200);
  });
});
```

- [ ] **Step 2: Run the new test and confirm it fails**

Run: `cd landing && npm test -- src/lib/early-access.test.ts src/app/api/early-access/route.test.ts`

Expected before implementation: FAIL because neither the test script nor the parser module exists.

- [ ] **Step 3: Add strict parsing, bounded input, and context-safe rendering**

Add `zod` and `vitest` with `npm install zod` and `npm install -D vitest`; add `"test": "vitest run"` to `landing/package.json`. Create `landing/vitest.config.ts` with `environment: "node"` and the `@` alias mapped to `./src`. Implement exact field limits: full name 2–120, email valid and max 254, phone 8–32, company 2–160, role/team/interest max 80, note max 2,000. Escape `&`, `<`, `>`, `"`, and `'` before every interpolation in both email templates.

```ts
export const escapeHtml = (value: string) => value.replace(/[&<>"']/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[char]!));
```

Read the body as text; reject payloads over 16 KiB with HTTP 413 before calling `JSON.parse`, then pass the parsed value through `parseEarlyAccessRegistration`. For values in text or HTML-attribute contexts, use `escapeHtml`. For the `mailto:` and `tel:` attribute values, use `encodeURIComponent` and retain the escaped display text. In the route, return HTTP 502 when `emailResult.simulated` is false and `userEmailSent` is false. Only return `success: true` with the confirmation message after a real successful user-email delivery; in development, return `simulated: true` with a message that no email was sent.

Do not add a lead database in this slice: before launch, product/legal must explicitly choose either (a) an approved durable, privacy-governed lead store with retention/deletion policy or (b) outbound email as the documented system of record.

- [ ] **Step 4: Add abuse controls at the hosted edge**

Configure the landing host's WAF rule before publishing: accept at most 5 `POST /api/early-access` requests per IP in 10 minutes and return HTTP 429 for the sixth; block request bodies over 16 KiB. If bot management is available, add a separate browser challenge rule above 3 requests per minute and document its expected status/interaction independently of the deterministic 429 test. Add the exact limits to `docs/operations/landing.md`; do not claim Caddy enforces them because the landing route is not proxied by the checked-in Caddyfile.

- [ ] **Step 5: Verify route behavior, lint, and build**

Run:

```bash
cd landing && npm test -- src/lib/early-access.test.ts src/app/api/early-access/route.test.ts
npm run lint
npm run build
```

Expected: malformed input is 400, user input is escaped, an email-provider error is 502, and the production build succeeds.

- [ ] **Step 6: Commit the landing hardening slice**

```bash
git add landing/package.json landing/package-lock.json landing/vitest.config.ts landing/src/lib/early-access.ts landing/src/lib/early-access.test.ts landing/src/app/api/early-access/route.ts landing/src/app/api/early-access/route.test.ts landing/src/lib/resend.ts docs/operations/landing.md
git commit -m "fix(landing): validate and safely deliver early access leads"
```

### Task 6: Restore static analysis and make CI report frontend coverage

**Files:**
- Modify: `apps/cosa/academy/simulation/contracts.py:14,93`
- Modify: `apps/cosa/academy/simulation/engine.py:15,17`
- Modify: `apps/cosa/academy/template_export.py:17,20`
- Modify: `packages/agent/capabilities/enablements.py:8,42,48,82,88,161`
- Modify: `packages/agent/capabilities/gateway.py:24,289-290`
- Modify: `frontend/lib/data/models/pmf_scoreboard_model.dart:1`
- Modify: `frontend/lib/modules/approvals/views/widgets/action_preview_card.dart:64,78`
- Modify: `frontend/lib/modules/strategy/widgets/maturity_track_panel.dart:59,61`
- Modify: `frontend/lib/modules/strategy/widgets/pmf_scoreboard_panel.dart:104,206`
- Modify: `frontend/lib/modules/auth/services/auth_service.dart:163-164,314`
- Modify: `frontend/test/lifecycle_tranche_b1_flow_test.dart:69`
- Modify: `frontend/test/maturity_track_panel_test.dart:146`
- Modify: `.github/workflows/quality.yml`

**Interfaces:**
- Consumes: current Ruff and Flutter analyzer configurations.
- Produces: clean `make lint`, clean `flutter analyze`, and `test-results/frontend-lcov.info` uploaded by CI.

- [ ] **Step 1: Capture the exact failing baselines**

Run:

```bash
make lint
cd frontend && flutter analyze
```

Expected before implementation: Ruff reports 16 errors and Flutter reports 13 issues.

- [ ] **Step 2: Apply only mechanical, behavior-preserving corrections**

Run `ruff check --fix` only on the six listed Python files, then manually replace `datetime.now(timezone.utc)` with `datetime.now(UTC)`, flatten the nested enablement conditional, remove unused imports, and use direct `req.context.action_class` after `hasattr`. Replace each Dart `withOpacity(x)` with `withValues(alpha: x)`, remove unused imports/casts, and use null-aware collection entries in `auth_service.dart`. Do not change feature behavior or public API contracts.

```python
from datetime import UTC, datetime

now = datetime.now(UTC)
if hasattr(req.context, "action_class"):
    action_class = req.context.action_class
```

```dart
final highlight = color.withValues(alpha: 0.32);
final payload = {
  if (workspaceId != null) 'workspace_id': workspaceId,
};
```

- [ ] **Step 3: Add a Flutter coverage artifact without a speculative threshold**

Change the existing frontend CI test command to:

```bash
flutter test --coverage --machine > ../test-results/frontend.json
mv coverage/lcov.info ../test-results/frontend-lcov.info
```

Upload both files. Do not add a percentage threshold until the first three main-branch reports establish a stable baseline.

- [ ] **Step 4: Verify all quality gates**

Run:

```bash
make lint
cd frontend && flutter analyze && flutter test --coverage
cd ../landing && npm test -- --run && npm run lint && npm run build
```

Expected: all commands exit 0 and `frontend/coverage/lcov.info` exists.

- [ ] **Step 5: Commit quality gates separately from behavior changes**

```bash
git add apps/cosa/academy/simulation/contracts.py apps/cosa/academy/simulation/engine.py apps/cosa/academy/template_export.py packages/agent/capabilities/enablements.py packages/agent/capabilities/gateway.py frontend/lib/data/models/pmf_scoreboard_model.dart frontend/lib/modules/approvals/views/widgets/action_preview_card.dart frontend/lib/modules/strategy/widgets/maturity_track_panel.dart frontend/lib/modules/strategy/widgets/pmf_scoreboard_panel.dart frontend/lib/modules/auth/services/auth_service.dart frontend/test/lifecycle_tranche_b1_flow_test.dart frontend/test/maturity_track_panel_test.dart .github/workflows/quality.yml
git commit -m "chore(quality): restore static checks and publish frontend coverage"
```

### Task 7: Prove perimeter rate limits and ingress routing in staging

**Files:**
- Modify: `docs/operations/deployment.md`
- Modify: `docs/operations/landing.md`
- Modify: `apps/cosa/api/middleware.py:1-18`
- Create: `scripts/e2e/verify-public-ingress.sh`
- Test: `scripts/e2e/verify-public-ingress.sh`

**Interfaces:**
- Consumes: `CENTRAL_API_DOMAIN`, `LANDING_DOMAIN`, and a staging WAF configuration that implements the exact Task 5 rate limits.
- Produces: a repeatable public-ingress smoke script that verifies only declared public routes are reachable and a 429 is returned once the configured limit is exceeded.

- [ ] **Step 1: Write the failing ingress assertions**

Create the script with the following assertions; it must read URLs from environment and never contain production credentials.

```bash
#!/usr/bin/env bash
set -euo pipefail
: "${CENTRAL_API_DOMAIN:?set CENTRAL_API_DOMAIN}"
: "${LANDING_DOMAIN:?set LANDING_DOMAIN}"

curl --fail --silent --show-error "$CENTRAL_API_DOMAIN/healthz"
test "$(curl --silent --output /dev/null --write-out '%{http_code}' "$CENTRAL_API_DOMAIN/metrics")" = "403"
for attempt in 1 2 3 4 5 6; do
  status=$(curl --silent --output /dev/null --write-out '%{http_code}' --request POST "$LANDING_DOMAIN/api/early-access" --header 'Content-Type: application/json' --data '{}')
done
test "$status" = "429"
```

- [ ] **Step 2: Run against staging before edge configuration**

Run: `CENTRAL_API_DOMAIN=https://api-staging.example LANDING_DOMAIN=https://landing-staging.example scripts/e2e/verify-public-ingress.sh`

Expected before implementation: health/metrics behavior may pass, but the sixth landing request is not rate-limited.

- [ ] **Step 3: Record and enforce the public-route contract**

Document the two public origins, exact limits, incident owner, and review date. Verify `/metrics` remains CIDR-restricted in the existing Caddy configuration. Remove the claim in `apps/cosa/api/middleware.py` that Caddy rate-limits requests unless an approved Caddy image and configuration demonstrably do so. State the actual WAF/CDN enforcement point instead.

- [ ] **Step 4: Verify staging evidence and commit documentation/script**

Run the script twice from a non-allowlisted network. Save only status codes and timestamps in the deployment record; do not save lead PII or WAF tokens.

```bash
git add docs/operations/deployment.md docs/operations/landing.md scripts/e2e/verify-public-ingress.sh apps/cosa/api/middleware.py
git commit -m "docs(security): verify public ingress and rate limits"
```

## Deferred plans after this plan is accepted

1. **Flutter modularization plan:** split `ApiClient` into endpoint resolution, token resolution, transport, and retry/idempotency units; then divide the largest strategy and marketing views by feature responsibility.
2. **Landing experience plan:** server-render static sections, isolate interactive islands, add dialog focus management and labels, then add sitemap, robots, privacy, and terms pages.
3. **Session revocation plan:** add device/session records, signed `jti`, server-side revoke-on-role-change, and an offline policy approved by product/security.

## Self-review

- Spec coverage: Tasks 1–3 cover all confirmed authorization and tenant findings; Task 4 covers credential policy; Tasks 5 and 7 cover landing abuse, truthfulness, escaping, rate limits, and ingress; Task 6 covers each failed static gate.
- Placeholder scan: every task names concrete files, tests, commands, interfaces, and acceptance conditions.
- Type consistency: Task 1 removes client `workspaces` from sync; Task 3 defines the exact scoped dependency-list signature; Task 4 defines the `auth_time` claim; Task 5 defines parser and delivery return values.

## Execution handoff

Execute Waves 1–3 as separate reviewed changes. Wave 4 requires explicit infrastructure authorization before any staging edge configuration is changed.
