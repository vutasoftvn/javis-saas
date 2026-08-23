# Identity Foundation (Plan A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make COSA Control Plane (`services/cosa`) the sole identity/credential authority and Company (`services/company`) a correct, bug-free projection of it — no local password auth, no silent tenant fallbacks, no stale/duplicate membership state.

**Architecture:** COSA owns users/companies/`company_memberships` (renamed from `company_roles`) and exposes `POST /platform/internal/validate-membership` (extended with `membershipId`/`membershipUpdatedAt`). Company's `core.user_projections`/`core.workspaces`/`core.workspace_memberships` are a one-way projection populated only via `POST /identity/sync-from-platform`. `workforce_members` (workforce identity: human or AI agent) drops the `organizations` 1:1 wrapper and points straight at `workspaces`.

**Tech Stack:** TypeScript, Encore.ts, Drizzle ORM (Postgres), vitest (integration tests against a real dev Postgres — no mocking of DB), bcryptjs (removed by this plan), jsonwebtoken.

## Global Constraints

- Forward-only migrations (`*.up.sql`, no `.down.sql` files exist in this repo) tracked in `public.schema_migrations` by `(service, filename)`. Run via `node scripts/migrate.mjs` from `services/company` or `services/cosa`.
- No destructive DB reset. No dropping/recreating the dev database. All changes are additive/forward migrations on the existing dev DB.
- Tests are real integration tests against a live Postgres (started via docker-compose) — never introduce mocking of the DB layer.
- Snowflake IDs: always insert via `generateSnowflake()` (returns `bigint`), never `Number()`/`parseInt()` a Snowflake ID string (precision loss on 18-19 digit IDs) — pass strings straight into `BigInt()`.
- Vietnamese for comments explaining *why* (per repo convention); identifiers, error messages, code stay in English/as established.
- Every task must leave `vitest run` green in the touched service before moving to the next task — this repo has ~22 test files coupled to identity via `registerUserService`, so several tasks are intentionally larger than "bite-sized" to avoid landing a non-compiling/red-test intermediate state.

---

## Task 1: COSA — rename `company_roles` → `company_memberships`, extend validate-membership response

**Files:**
- Modify: `services/cosa/storage/schema.ts:58-65`
- Modify: `services/cosa/services/auth.service.ts` (lines ~8, 141-146, 164-169)
- Modify: `services/cosa/services/company.service.ts` (lines ~7, 38-47, 54-75, 104-119, 138-162, 164-221)
- Create: `services/cosa/migrations/5_rename_company_roles.up.sql`
- Test: `services/cosa/tests/control-plane.test.ts` (existing, run as-is — no new test needed, this is a pure rename + additive field)

**Interfaces:**
- Produces: `ValidateMembershipResult` (in `services/cosa/services/company.service.ts`) now has 2 new fields: `membershipId: string`, `membershipUpdatedAt: string` (ISO timestamp). Task 2 consumes this.

- [ ] **Step 1: Create the migration**

```sql
-- services/cosa/migrations/5_rename_company_roles.up.sql
ALTER TABLE cosa.company_roles RENAME TO company_memberships;
```

- [ ] **Step 2: Rename the table export in schema.ts**

Edit `services/cosa/storage/schema.ts:58`, change:
```ts
export const companyRoles = cosaSchema.table("company_roles", {
```
to:
```ts
export const companyMemberships = cosaSchema.table("company_memberships", {
```
(keep every column definition inside unchanged — only the export name and the `.table(...)` string argument change.)

- [ ] **Step 3: Rename every `companyRoles` reference to `companyMemberships`**

Run from repo root:
```bash
sed -i '' 's/\bcompanyRoles\b/companyMemberships/g' \
  services/cosa/services/auth.service.ts \
  services/cosa/services/company.service.ts
```
This is a pure identifier rename (import destructure, `.values({...})`, `.from(...)`, `.where(eq(companyMemberships...))`) — no other token in either file matches `companyRoles`, so the rename is safe as a blind substitution. Verify with `grep -rn "companyRoles" services/cosa` → must return 0 results.

- [ ] **Step 4: Extend `ValidateMembershipResult` + `validateUserMembership` with membership freshness fields**

Edit `services/cosa/services/company.service.ts:38-47`, change:
```ts
export interface ValidateMembershipResult {
  valid: boolean;
  userId: string;
  email: string | null;
  phone: string | null;
  displayName: string | null;
  companyId: string;
  companyName: string;
  roleId: string;
}
```
to:
```ts
export interface ValidateMembershipResult {
  valid: boolean;
  userId: string;
  email: string | null;
  phone: string | null;
  displayName: string | null;
  companyId: string;
  companyName: string;
  roleId: string;
  membershipId: string;
  membershipUpdatedAt: string;
}
```

Then edit the `validateUserMembership` function (~line 193-221): the `membershipRow` select currently is
```ts
  const [membershipRow] = await db
    .select({
      roleId: companyMemberships.roleId,
      companyName: companies.name,
    })
    .from(companyMemberships)
    .innerJoin(companies, eq(companies.id, companyMemberships.companyId))
    .where(
      and(
        eq(companyMemberships.userId, userId),
        eq(companyMemberships.companyId, companyId),
        eq(companies.status, "active")
      )
    )
    .limit(1);
```
Change the `.select({...})` to also fetch `id` and `updatedAt`:
```ts
  const [membershipRow] = await db
    .select({
      id: companyMemberships.id,
      roleId: companyMemberships.roleId,
      companyName: companies.name,
      updatedAt: companyMemberships.updatedAt,
    })
    .from(companyMemberships)
    .innerJoin(companies, eq(companies.id, companyMemberships.companyId))
    .where(
      and(
        eq(companyMemberships.userId, userId),
        eq(companyMemberships.companyId, companyId),
        eq(companies.status, "active")
      )
    )
    .limit(1);
```
And the function's final `return { valid: true, ... }` object — add the 2 new fields:
```ts
  return {
    valid: true,
    userId: userRow.id.toString(),
    email: userRow.email,
    phone: userRow.phone,
    displayName: userRow.fullName,
    companyId: companyId.toString(),
    companyName: membershipRow.companyName,
    roleId: membershipRow.roleId,
    membershipId: membershipRow.id.toString(),
    membershipUpdatedAt: membershipRow.updatedAt.toISOString(),
  };
```
(Read the existing tail of the function first — `services/cosa/services/company.service.ts:213-221` — to confirm the exact current field list before editing, since line numbers may have shifted after Step 3's sed.)

- [ ] **Step 5: Run COSA tests**

```bash
cd services/cosa && node scripts/migrate.mjs && npx vitest run
```
Expected: all existing tests in `services/cosa/tests/control-plane.test.ts` PASS (no behavior change to any test-visible flow — `company_memberships` is an internal rename, the 2 new response fields are additive).

- [ ] **Step 6: Commit**

```bash
git add services/cosa/storage/schema.ts services/cosa/services/auth.service.ts services/cosa/services/company.service.ts services/cosa/migrations/5_rename_company_roles.up.sql
git commit -m "refactor(cosa): rename company_roles to company_memberships, expose membership freshness in validate-membership"
```

---

## Task 2: Company — extend `platform.client.ts` to carry membership freshness fields

**Files:**
- Modify: `services/company/identity/services/platform.client.ts:13-22`

**Interfaces:**
- Consumes: Task 1's extended `ValidateMembershipResult` response body (COSA already returns the new fields — this task just stops discarding them on the Company side).
- Produces: `ValidateMembershipResult` (Company-side, in `platform.client.ts`) now has `membershipId: string` and `membershipUpdatedAt: string`. Task 7 (sync fix) consumes these.

- [ ] **Step 1: Add the 2 fields to the interface**

Edit `services/company/identity/services/platform.client.ts:13-22`, change:
```ts
export interface ValidateMembershipResult {
  valid: boolean;
  userId: string;
  email: string | null;
  phone: string | null;
  displayName: string | null;
  companyId: string;
  companyName: string;
  roleId: string;
}
```
to:
```ts
export interface ValidateMembershipResult {
  valid: boolean;
  userId: string;
  email: string | null;
  phone: string | null;
  displayName: string | null;
  companyId: string;
  companyName: string;
  roleId: string;
  membershipId: string;
  membershipUpdatedAt: string;
}
```
No other change needed — `validatePlatformMembership()` already does `return data as ValidateMembershipResult` (the whole JSON body), so the new fields flow through automatically.

- [ ] **Step 2: Verify with a quick manual check (no dedicated test file exists for platform.client.ts)**

```bash
cd services/company && npx vitest run identity
```
Expected: all pre-existing `identity/tests/*.test.ts` still PASS (this is a type-only additive change, nothing calls the new fields yet).

- [ ] **Step 3: Commit**

```bash
git add services/company/identity/services/platform.client.ts
git commit -m "feat(company): carry membership freshness fields from platform validate-membership response"
```

---

## Task 3: Company — rename `core.users`→`user_projections`, `core.workspace_members`→`workspace_memberships`, add sync-tracking columns + uniqueness

**Files:**
- Modify: `services/company/shared/db/schema/identity.ts`
- Create: `services/company/identity/migrations/5_identity_projection_rework.up.sql`

**Interfaces:**
- Produces: `identityUserProjections` (renamed from `identityUsers`, table `core.user_projections`, columns: `id, email, phone, displayName, status, platformUserId, createdAt, updatedAt, deletedAt` — `passwordHash` and `role` REMOVED). `identityWorkspaceMemberships` (renamed from `identityWorkspaceMembers`, table `core.workspace_memberships`, adds `platformMembershipId: text`, `sourceUpdatedAt: timestamp`, `syncedAt: timestamp`, plus a `UNIQUE(workspace_id, user_id)` DB constraint). Every later task in this plan imports these two new export names from `schema/identity.ts`.

- [ ] **Step 1: Write the migration**

```sql
-- services/company/identity/migrations/5_identity_projection_rework.up.sql

-- core.users -> core.user_projections: Company không còn là credential
-- authority. password_hash và role bị xoá — password chỉ COSA giữ, role chỉ
-- nằm ở membership (một user có thể có role khác nhau ở mỗi workspace).
ALTER TABLE core.users RENAME TO user_projections;
ALTER TABLE core.user_projections DROP COLUMN password_hash;
ALTER TABLE core.user_projections DROP COLUMN role;

-- core.workspace_members -> core.workspace_memberships: track nguồn gốc
-- sync (platform_membership_id, source_updated_at, synced_at) để debug
-- "role này lấy từ đâu, lúc nào", và enforce uniqueness ở DB level để
-- concurrent sync không tạo duplicate membership.
ALTER TABLE core.workspace_members RENAME TO workspace_memberships;
ALTER TABLE core.workspace_memberships ADD COLUMN platform_membership_id TEXT;
ALTER TABLE core.workspace_memberships ADD COLUMN source_updated_at TIMESTAMPTZ;
ALTER TABLE core.workspace_memberships ADD COLUMN synced_at TIMESTAMPTZ;
ALTER TABLE core.workspace_memberships ADD CONSTRAINT workspace_memberships_workspace_user_unique UNIQUE (workspace_id, user_id);
```

- [ ] **Step 2: Update the schema file**

Edit `services/company/shared/db/schema/identity.ts` in full, replacing the current `identityUsers` and `identityWorkspaceMembers` exports:

```ts
import { pgSchema, text, bigint, timestamp } from "drizzle-orm/pg-core";

export const coreSchema = pgSchema("core");

export const identityWorkspaces = coreSchema.table("workspaces", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  name: text("name").notNull(),
  companyStage: text("company_stage").default("S0_GENESIS").notNull(),
  platformCompanyId: text("platform_company_id").unique(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const identityUserProjections = coreSchema.table("user_projections", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  email: text("email").unique(),
  phone: text("phone").unique(),
  displayName: text("display_name"),
  status: text("status").default("active").notNull(),
  platformUserId: text("platform_user_id").unique(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const identityWorkspaceMemberships = coreSchema.table("workspace_memberships", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull().references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  userId: bigint("user_id", { mode: "bigint" }).notNull().references(() => identityUserProjections.id, { onDelete: "cascade" }),
  role: text("role").default("member").notNull(),
  platformMembershipId: text("platform_membership_id"),
  sourceUpdatedAt: timestamp("source_updated_at", { withTimezone: true }),
  syncedAt: timestamp("synced_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const identityOrganizations = coreSchema.table("organizations", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull().unique().references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  name: text("name").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const identityWorkforceMembers = coreSchema.table("workforce_members", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  organizationId: bigint("organization_id", { mode: "bigint" }).notNull().references(() => identityOrganizations.id, { onDelete: "cascade" }),
  memberType: text("member_type").notNull(),
  humanUserId: bigint("human_user_id", { mode: "bigint" }).references(() => identityUserProjections.id, { onDelete: "cascade" }),
  agentDefinitionId: bigint("agent_definition_id", { mode: "bigint" }),
  agentProfileId: text("agent_profile_id"),
  roleTitle: text("role_title").notNull(),
  status: text("status").default("active").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});
```

(`identityOrganizations`/`identityWorkforceMembers` are left untouched in this task — Task 8 handles those. Only the `humanUserId` FK target changes here, from `identityUsers.id` to `identityUserProjections.id`, since the referenced export is being renamed.)

- [ ] **Step 3: Rename every `identityUsers`/`identityWorkspaceMembers` reference across `services/company`**

```bash
cd /Volumes/SSD/javis-saas
grep -rl '\bidentityUsers\b' services/company --include="*.ts" | xargs sed -i '' 's/\bidentityUsers\b/identityUserProjections/g'
grep -rl '\bidentityWorkspaceMembers\b' services/company --include="*.ts" | xargs sed -i '' 's/\bidentityWorkspaceMembers\b/identityWorkspaceMemberships/g'
```
This will touch (at minimum) `identity/services/auth.service.ts`, `identity/services/sync.service.ts`, `identity/services/tenant-context.service.ts`, `identity/services/workspace.service.ts` (if it destructures `schema`), `identity/tests/*.test.ts`. Verify: `grep -rn '\bidentityUsers\b\|\bidentityWorkspaceMembers\b' services/company` → must return 0 results.

- [ ] **Step 4: Fix the now-broken `.role`/`.passwordHash` references on `identityUserProjections`**

The sed in Step 3 renames the *table export*, but code still reading/writing the now-deleted `role`/`passwordHash` **columns** on that table won't compile. Grep for them:
```bash
grep -rn "identityUserProjections\.\(role\|passwordHash\)\|passwordHash:\|role: member\.roleId" services/company/identity
```
This will surface 3 known call sites — leave them broken for now (do not fix here, Task 6 removes local auth entirely and Task 7 fixes the sync role bug; fixing them here would be premature and this task's own scope is schema-only). Instead, confirm the migration + schema compiles in isolation:
```bash
cd services/company && npx tsc --noEmit -p . 2>&1 | grep -c "error"
```
Expected: a small nonzero number of errors, ALL in `auth.service.ts` (passwordHash) and `sync.service.ts` (role) — confirm no errors anywhere else (i.e., the rename itself was mechanically complete). This is the one task in this plan that's allowed to leave TypeScript red, because the schema rename and the auth/sync code fixes are inherently coupled and split across Tasks 3, 6, 7 for reviewability — Task 7 is the last of the three and must leave `tsc --noEmit` and `vitest run` fully green again.

- [ ] **Step 5: Run the migration on the dev DB**

```bash
cd services/company && node scripts/migrate.mjs
```
Expected: migration `5_identity_projection_rework.up.sql` applies without error, recorded in `public.schema_migrations`.

- [ ] **Step 6: Commit**

```bash
git add services/company/shared/db/schema/identity.ts services/company/identity/migrations/5_identity_projection_rework.up.sql
git commit -m "refactor(company): rename core.users->user_projections, core.workspace_members->workspace_memberships, add sync tracking + uniqueness"
```
(Do NOT `git add -A` here — the sed in Step 3 already touched many files across the tree; stage only the schema+migration in this commit, the renamed references land as part of Tasks 4-8's commits where each file's other changes also land. If your working tree tooling requires committing the sed output now to keep history clean, run `git add -u services/company` instead and commit everything the sed touched under this same message — either ordering is fine as long as Task 7's commit is what finally makes `tsc --noEmit` clean again.)

---

## Task 4: Company — add a DB-level test session helper (replaces local register/login in tests)

**Files:**
- Create: `services/company/identity/tests/helpers/test-session.ts`

**Interfaces:**
- Consumes: `identityUserProjections`, `identityWorkspaces`, `identityWorkspaceMemberships` (Task 3), `generateSnowflake()` (`shared/services/snowflake.service.ts`), `signAccessToken()` (`identity/services/token.service.ts`).
- Produces: `createTestSession(params?: { email?: string; displayName?: string; role?: string }): Promise<{ accessToken: string; userId: string; workspaceId: string }>` — Task 5 imports this into 22 test files as the drop-in replacement for `registerUserService`.

**Why this exists:** after Task 6 deletes local password register/login, tests need a way to get "a user with a token, in an admin-owned workspace" without spinning up COSA and running a real `sync-from-platform` HTTP round-trip. This helper inserts the projection rows directly — it is test-only scaffolding, never imported by production code.

- [ ] **Step 1: Write the helper**

```ts
// services/company/identity/tests/helpers/test-session.ts
//
// Test-only bootstrap: chèn thẳng user_projection + workspace +
// workspace_membership vào DB, bỏ qua sync-from-platform HTTP thật (vì test
// ở services/company không muốn phụ thuộc services/cosa đang chạy). Thay
// thế cho registerUserService cũ (đã xoá cùng local password auth).
import { db, schema } from "../../models/db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { signAccessToken } from "../../services/token.service";

const { identityUserProjections, identityWorkspaces, identityWorkspaceMemberships } = schema;

export interface CreateTestSessionParams {
  email?: string;
  displayName?: string;
  role?: string;
}

export interface TestSession {
  accessToken: string;
  userId: string;
  workspaceId: string;
}

export async function createTestSession(params: CreateTestSessionParams = {}): Promise<TestSession> {
  const displayName = params.displayName || "Test User";
  const email =
    params.email ||
    `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`;
  const role = params.role || "admin";

  const userId = generateSnowflake();
  const workspaceId = generateSnowflake();
  const membershipId = generateSnowflake();

  await db.transaction(async (tx) => {
    await tx.insert(identityUserProjections).values({
      id: userId,
      email,
      displayName,
    });

    await tx.insert(identityWorkspaces).values({
      id: workspaceId,
      name: `Workspace của ${displayName}`,
    });

    await tx.insert(identityWorkspaceMemberships).values({
      id: membershipId,
      workspaceId,
      userId,
      role,
    });
  });

  return {
    accessToken: signAccessToken(userId.toString()),
    userId: userId.toString(),
    workspaceId: workspaceId.toString(),
  };
}
```

- [ ] **Step 2: Write a test for the helper itself**

```ts
// services/company/identity/tests/helpers/test-session.test.ts
import { describe, expect, it } from "vitest";
import { createTestSession } from "./test-session";
import { resolveTenantContext } from "../../services/tenant-context.service";

describe("createTestSession", () => {
  it("creates a user+workspace+admin membership usable by resolveTenantContext", async () => {
    const session = await createTestSession({ displayName: "Helper Test" });
    expect(session.accessToken).toBeTruthy();
    expect(session.userId).toBeTruthy();
    expect(session.workspaceId).toBeTruthy();

    const ctx = await resolveTenantContext({
      authorization: `Bearer ${session.accessToken}`,
      workspaceId: session.workspaceId,
    });
    expect(ctx.userId).toBe(session.userId);
    expect(ctx.workspaceId).toBe(session.workspaceId);
    expect(ctx.membershipRole).toBe("admin");
  });

  it("honors a custom role", async () => {
    const session = await createTestSession({ displayName: "Viewer Test", role: "viewer" });
    const ctx = await resolveTenantContext({
      authorization: `Bearer ${session.accessToken}`,
      workspaceId: session.workspaceId,
    });
    expect(ctx.membershipRole).toBe("viewer");
  });
});
```

- [ ] **Step 3: Run it**

```bash
cd services/company && npx vitest run identity/tests/helpers/test-session.test.ts
```
Expected: PASS. (`resolveTenantContext` itself is unmodified at this point — Task 3 already renamed the tables it reads from, and Task 3's Step 3 sed already fixed `tenant-context.service.ts`'s references, so this should work today even before Tasks 6/7/9/10 land.)

- [ ] **Step 4: Commit**

```bash
git add services/company/identity/tests/helpers/test-session.ts services/company/identity/tests/helpers/test-session.test.ts
git commit -m "test(company): add DB-level test session helper to replace local register/login in tests"
```

---

## Task 5: Company — migrate all test files off `registerUserService`/`registerUser`

**Files:**
- Modify (mechanical, via script): `services/company/operations/tests/task.test.ts`, `task-dependency.test.ts`, `initiative.test.ts`, `services/company/operations/strategy/tests/execution-planning-chain.test.ts`, `services/company/commercial/tests/{lead,billing,marketing,contact,opportunity,account,customer}.test.ts`, `services/company/finance-legal/tests/{legal-obligation,accounting-regime,finance-snapshot,financial-transaction,accounting-period,accounting-profile,legal-checklist-item,finance-exception,validation}.test.ts`
- Modify (by hand): `services/company/identity/tests/tenant-context.test.ts`, `services/company/identity/tests/me.test.ts`, `services/company/shared/tests/golden-path.e2e.test.ts`
- Delete: `services/company/identity/tests/register.test.ts`, `services/company/identity/tests/login.test.ts`, `services/company/identity/tests/password.test.ts`

**Interfaces:**
- Consumes: `createTestSession` from Task 4.

- [ ] **Step 1: Script the mechanical replacement for the 20 files at `<module>/tests/*.test.ts` depth (2 dirs under `services/company`)**

Every one of these files has the identical 3-line shape confirmed by direct inspection (`import { registerUserService } from "../../identity/services/auth.service";`, `registerUserService({ email: ..., password: "password123", displayName, })`). Run:

```bash
cd /Volumes/SSD/javis-saas/services/company
FILES_DEPTH2=$(grep -rl 'registerUserService' operations/tests commercial/tests finance-legal/tests --include="*.test.ts")
for f in $FILES_DEPTH2; do
  sed -i '' \
    -e 's#import { registerUserService } from "\.\./\.\./identity/services/auth\.service";#import { createTestSession } from "../../identity/tests/helpers/test-session";#' \
    -e 's/registerUserService({/createTestSession({/' \
    -e '/^\s*password: "password123",\s*$/d' \
    "$f"
done
```

- [ ] **Step 2: Fix the one file that's 3 dirs deep**

`services/company/operations/strategy/tests/execution-planning-chain.test.ts` needs `../../../identity/tests/helpers/test-session` (one extra `../`):

```bash
sed -i '' \
  -e 's#import { registerUserService } from "\.\./\.\./\.\./identity/services/auth\.service";#import { createTestSession } from "../../../identity/tests/helpers/test-session";#' \
  -e 's/registerUserService({/createTestSession({/' \
  -e '/^\s*password: "password123",\s*$/d' \
  services/company/operations/strategy/tests/execution-planning-chain.test.ts
```

- [ ] **Step 3: Verify the mechanical migration**

```bash
grep -rn "registerUserService" services/company/operations services/company/commercial services/company/finance-legal
```
Expected: 0 results. Then spot-check one file compiles as expected by reading it:
```bash
sed -n '1,15p' services/company/operations/tests/task.test.ts
```
Expected output shows `import { createTestSession } from "../../identity/tests/helpers/test-session";` and `const user = await createTestSession({ email: ..., displayName });` (no `password` line).

- [ ] **Step 4: Hand-fix `tenant-context.test.ts`**

This file imports `registerUserService` directly from `../services/auth.service` (it's inside `identity/tests/`, not `<module>/tests/`) — different relative path, not covered by the scripted sed. Edit `services/company/identity/tests/tenant-context.test.ts:1-6`, change:
```ts
import { describe, expect, it } from "vitest";
import { registerUserService } from "../services/auth.service";
import { createWorkspaceRecord } from "../services/workspace.service";
import { resolveTenantContext } from "../services/tenant-context.service";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
```
to:
```ts
import { describe, expect, it } from "vitest";
import { createTestSession } from "./helpers/test-session";
import { createWorkspaceRecord } from "../services/workspace.service";
import { resolveTenantContext } from "../services/tenant-context.service";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
```
Then replace every one of the 5 occurrences of:
```ts
    const user = await registerUserService({
      email: `tenant-<slug>-${Date.now()}@example.com`,
      password: "Password123!",
      displayName: "<Name>",
    });
```
with:
```ts
    const user = await createTestSession({
      email: `tenant-<slug>-${Date.now()}@example.com`,
      displayName: "<Name>",
    });
```
(keep each call's own `<slug>`/`<Name>` values unchanged — there are 5 call sites: `tenant-corr-`, `tenant-fwd-`, `tenant-immut-`, `tenant-switch-`, and the one inside the "rejects invalid" test has no `registerUserService` call so leave it as-is).

- [ ] **Step 5: Hand-fix `me.test.ts`**

Edit `services/company/identity/tests/me.test.ts` in full:
```ts
import { describe, expect, it } from "vitest";
import { createTestSession } from "./helpers/test-session";
import { getMe } from "../handlers/auth.handler";

describe("getMe", () => {
  it("resolves the current user's profile and workspace info", async () => {
    const email = `me-${Date.now()}@example.com`;
    const session = await createTestSession({ email, displayName: "Me User" });

    const me = await getMe({ userID: session.userId });
    expect(me.id).toBe(session.userId);
    expect(me.email).toBe(email);
    expect(me.displayName).toBe("Me User");
    expect(me.workspaceId).toBe(session.workspaceId);
    expect(me.role).toBe("admin");
  });
});
```
(`getMe({ userID })` takes `AuthData`, matching the existing handler signature at `auth.handler.ts:61` — unchanged by this plan.)

- [ ] **Step 6: Hand-fix `golden-path.e2e.test.ts`**

Edit `services/company/shared/tests/golden-path.e2e.test.ts:1-2`, change:
```ts
import { describe, expect, it } from "vitest";
import { registerUser } from "../../identity/handlers/auth.handler";
```
to:
```ts
import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
```
Then in the test body (~line 28-32), change:
```ts
    const email = `golden-${Date.now()}@quocgiakhoinghiep.vn`;
    const register = await registerUser({
      email,
      password: "StartupNation#2026",
      displayName: "Founder Quốc Gia Khởi Nghiệp",
    });
    expect(register.workspaceId).toBeTruthy();
    expect(typeof register.workspaceId).toBe("string");
    const workspaceId = register.workspaceId;
    const auth = `Bearer ${register.accessToken}`;
```
to:
```ts
    const email = `golden-${Date.now()}@quocgiakhoinghiep.vn`;
    const session = await createTestSession({
      email,
      displayName: "Founder Quốc Gia Khởi Nghiệp",
    });
    expect(session.workspaceId).toBeTruthy();
    expect(typeof session.workspaceId).toBe("string");
    const workspaceId = session.workspaceId;
    const auth = `Bearer ${session.accessToken}`;
```
(Leave the rest of the file — including `createOrganization`/`hireWorkforceMember({ organizationId: ... })` calls — untouched here; Task 8 updates those in the same file separately.)

- [ ] **Step 7: Delete the 3 dead test files**

```bash
git rm services/company/identity/tests/register.test.ts services/company/identity/tests/login.test.ts services/company/identity/tests/password.test.ts
```
These test features (`registerUser`, `login`, `hashPassword`/`verifyPassword`) that Task 6 deletes entirely — there is nothing left to test.

- [ ] **Step 8: Run the full Company test suite**

```bash
cd services/company && npx vitest run
```
Expected: every test file that used to depend on `registerUserService`/`registerUser` still PASSES (now via `createTestSession`). `tsc --noEmit` will still show the errors noted in Task 3 Step 4 (auth.service.ts / sync.service.ts) until Tasks 6-7 land — that's expected at this point.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "test(company): migrate all test files from local register/login to createTestSession helper"
```

---

## Task 6: Company — remove local password authentication

**Files:**
- Modify: `services/company/identity/services/auth.service.ts` (keep `getMeProfile`, delete `loginUser`/`registerUserService`/their param+result interfaces)
- Modify: `services/company/identity/handlers/auth.handler.ts` (delete `login`/`registerUser` endpoints)
- Modify: `services/company/identity/services/index.ts` (drop the `password.service` export)
- Delete: `services/company/identity/services/password.service.ts`

**Interfaces:**
- Produces: `auth.service.ts` now only exports `getMeProfile(userIdStr: string): Promise<MeResponse>`. `auth.handler.ts` now only exports `auth` (gateway handler — fixed in Task 9), `gateway`, `getMe`, `meEndpoint`.

- [ ] **Step 1: Rewrite `auth.service.ts`**

Replace the full file content with:
```ts
import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";

const { identityUserProjections, identityWorkspaceMemberships } = schema;

export interface MeResponse {
  id: string;
  email: string | null;
  displayName: string | null;
  workspaceId: string | null;
  role: string | null;
}

export async function getMeProfile(userIdStr: string): Promise<MeResponse> {
  const userId = BigInt(userIdStr);
  const [userRow] = await db
    .select({
      id: identityUserProjections.id,
      email: identityUserProjections.email,
      displayName: identityUserProjections.displayName,
    })
    .from(identityUserProjections)
    .where(eq(identityUserProjections.id, userId))
    .limit(1);

  if (!userRow) throw APIError.notFound("user not found");

  const [membershipRow] = await db
    .select({
      workspaceId: identityWorkspaceMemberships.workspaceId,
      role: identityWorkspaceMemberships.role,
    })
    .from(identityWorkspaceMemberships)
    .where(eq(identityWorkspaceMemberships.userId, userId))
    .limit(1);

  return {
    id: userRow.id.toString(),
    email: userRow.email,
    displayName: userRow.displayName,
    workspaceId: membershipRow ? membershipRow.workspaceId.toString() : null,
    role: membershipRow?.role ?? null,
  };
}
```

- [ ] **Step 2: Rewrite `auth.handler.ts`**

Replace the full file content with (the `auth`/gateway function body is fixed properly in Task 9 — for now just drop the `login`/`registerUser` endpoints and their imports):
```ts
import { api, Header, Gateway, APIError } from "encore.dev/api";
import { authHandler } from "encore.dev/auth";
import { verifyAccessToken } from "../services/token.service";
import { verifyPlatformToken } from "../services/platform.client";
import { MeResponse, getMeProfile } from "../services/auth.service";

export { MeResponse };

export interface AuthParams {
  authorization?: Header<"Authorization">;
}

export interface AuthData {
  userID: string;
}

export const auth = authHandler<AuthParams, AuthData>(async (params) => {
  const header = params.authorization;
  if (!header || !header.startsWith("Bearer ")) {
    throw APIError.unauthenticated("missing bearer token");
  }
  const token = header.slice("Bearer ".length);
  try {
    const decoded = verifyAccessToken(token);
    return { userID: decoded.sub };
  } catch {
    try {
      const pDecoded = verifyPlatformToken(token);
      return { userID: pDecoded.sub };
    } catch {
      throw APIError.unauthenticated("invalid or expired token");
    }
  }
});

export const gateway = new Gateway({ authHandler: auth });

export async function getMe(authData: AuthData): Promise<MeResponse> {
  return getMeProfile(authData.userID);
}

export const meEndpoint = api(
  { method: "GET", path: "/identity/me", expose: true, auth: true },
  async (): Promise<MeResponse> => {
    let authData: AuthData | null = null;
    try {
      // @ts-ignore
      const mod = await import("~encore/auth");
      authData = mod.getAuthData();
    } catch {
      // fallback
    }
    if (!authData?.userID) {
      throw APIError.unauthenticated("missing auth data");
    }
    return getMeProfile(authData.userID);
  }
);
```
(The `authHandler`'s platform-token fallback branch is intentionally left as-is here — Task 9 removes it in its own reviewable step, since that's a behavior change, not just a deletion.)

- [ ] **Step 3: Delete `password.service.ts` and its barrel export**

```bash
git rm services/company/identity/services/password.service.ts
```
Edit `services/company/identity/services/index.ts`, remove the line `export * from "./password.service";`.

- [ ] **Step 4: Remove `bcryptjs` dependency if nothing else uses it**

```bash
grep -rln "bcryptjs" services/company --include="*.ts"
```
Expected: 0 results (password.service.ts was the only consumer). Then:
```bash
cd services/company && npm uninstall bcryptjs
```

- [ ] **Step 5: Confirm the codebase compiles clean again**

```bash
cd services/company && npx tsc --noEmit -p .
```
Expected: 0 errors related to `auth.service.ts`/`auth.handler.ts`/`password.service.ts` (the `sync.service.ts` `role` error from Task 3 Step 4 is still expected here — fixed in Task 7).

- [ ] **Step 6: Run the Company test suite**

```bash
npx vitest run
```
Expected: all tests PASS except any file still directly exercising `sync.service.ts`'s current (buggy) role logic — there are none yet (Task 7 adds the first such test).

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat(company): remove local password authentication — COSA is the sole credential authority"
```

---

## Task 7: Company — fix `syncFromPlatformService` role bug + atomic upsert + membership tracking

**Files:**
- Modify: `services/company/identity/services/sync.service.ts`
- Test: `services/company/identity/tests/sync.test.ts` (new)

**Interfaces:**
- Consumes: `member.roleId`, `member.membershipId`, `member.membershipUpdatedAt` from `validatePlatformMembership()` (Task 2). `identityWorkspaceMemberships` with `platformMembershipId`/`sourceUpdatedAt`/`syncedAt`/unique constraint (Task 3).
- Produces: `syncFromPlatformService` now correctly projects the platform role on every call (not just workspace creation), and is safe under concurrent invocation.

- [ ] **Step 1: Write the failing regression test**

```ts
// services/company/identity/tests/sync.test.ts
import { describe, expect, it, vi } from "vitest";
import { db, schema } from "../models/db";

const { identityWorkspaceMemberships } = schema;

vi.mock("../services/platform.client", () => ({
  validatePlatformMembership: vi.fn(),
}));

import { validatePlatformMembership } from "../services/platform.client";
import { syncFromPlatformService } from "../services/sync.service";
import { eq } from "drizzle-orm";

describe("syncFromPlatformService", () => {
  it("updates the local membership role when the platform role changes on re-sync", async () => {
    const platformUserId = `plat-user-${Date.now()}`;
    const platformCompanyId = `plat-company-${Date.now()}`;

    (validatePlatformMembership as any).mockResolvedValueOnce({
      valid: true,
      userId: platformUserId,
      email: `sync-${Date.now()}@example.com`,
      phone: null,
      displayName: "Sync Test",
      companyId: platformCompanyId,
      companyName: "Sync Test Co",
      roleId: "member",
      membershipId: "mem-1",
      membershipUpdatedAt: new Date(2026, 0, 1).toISOString(),
    });

    const first = await syncFromPlatformService({
      platform_access_token: "irrelevant-because-mocked",
      company_id: platformCompanyId,
    });
    expect(first.access_token).toBeTruthy();

    (validatePlatformMembership as any).mockResolvedValueOnce({
      valid: true,
      userId: platformUserId,
      email: `sync-${Date.now()}@example.com`,
      phone: null,
      displayName: "Sync Test",
      companyId: platformCompanyId,
      companyName: "Sync Test Co",
      roleId: "founder",
      membershipId: "mem-1",
      membershipUpdatedAt: new Date(2026, 0, 2).toISOString(),
    });

    await syncFromPlatformService({
      platform_access_token: "irrelevant-because-mocked",
      company_id: platformCompanyId,
    });

    const rows = await db
      .select({ role: identityWorkspaceMemberships.role, platformMembershipId: identityWorkspaceMemberships.platformMembershipId })
      .from(identityWorkspaceMemberships);
    const match = rows.find((r) => r.platformMembershipId === "mem-1");
    expect(match?.role).toBe("founder");
  });

  it("does not create duplicate memberships on concurrent sync for the same user+workspace", async () => {
    const platformUserId = `plat-concurrent-${Date.now()}`;
    const platformCompanyId = `plat-concurrent-co-${Date.now()}`;

    (validatePlatformMembership as any).mockResolvedValue({
      valid: true,
      userId: platformUserId,
      email: `concurrent-${Date.now()}@example.com`,
      phone: null,
      displayName: "Concurrent Test",
      companyId: platformCompanyId,
      companyName: "Concurrent Co",
      roleId: "member",
      membershipId: "mem-concurrent",
      membershipUpdatedAt: new Date().toISOString(),
    });

    await Promise.all([
      syncFromPlatformService({ platform_access_token: "x", company_id: platformCompanyId }),
      syncFromPlatformService({ platform_access_token: "x", company_id: platformCompanyId }),
    ]);

    const rows = await db
      .select({ id: identityWorkspaceMemberships.id })
      .from(identityWorkspaceMemberships)
      .where(eq(identityWorkspaceMemberships.platformMembershipId, "mem-concurrent"));
    expect(rows.length).toBe(1);
  });
});
```

- [ ] **Step 2: Run it to confirm it fails**

```bash
cd services/company && npx vitest run identity/tests/sync.test.ts
```
Expected: FAIL — `sync.service.ts` still writes `role: isNewWorkspace ? "admin" : "member"` and still references the now-dropped `identityUserProjections.role` column, so this either throws a DB error or the role assertion fails.

- [ ] **Step 3: Rewrite `sync.service.ts`**

```ts
import { APIError } from "encore.dev/api";
import { eq, sql, and } from "drizzle-orm";
import { db, schema } from "../models/db";
import { signAccessToken } from "./token.service";
import { validatePlatformMembership } from "./platform.client";
import { generateSnowflake } from "../../shared/services/snowflake.service";

// Đồng bộ một chiều control-plane (cloud tenancy source of truth) -> identity
// (local projection), map qua platformUserId/platformCompanyId. Đây KHÔNG
// phải bản sao trùng lặp của cùng một khái niệm — xem
// docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md mục "control-plane vs
// identity — two-tier ownership".
const { identityUserProjections, identityWorkspaces, identityWorkspaceMemberships } = schema;

export interface SyncFromPlatformParams {
  platform_access_token?: string;
  platformAccessToken?: string;
  company_id?: string | number;
  companyId?: string | number;
}

export interface SyncFromPlatformResult {
  access_token: string;
  token_type: string;
}

export async function syncFromPlatformService(params: SyncFromPlatformParams): Promise<SyncFromPlatformResult> {
  const token = params.platform_access_token || params.platformAccessToken;
  const compId = params.company_id || params.companyId;

  if (!token || !compId) {
    throw APIError.invalidArgument("vui lòng cung cấp platform_access_token và company_id");
  }

  const member = await validatePlatformMembership({
    platformToken: token,
    companyId: String(compId),
  });

  const localUserId = await db.transaction(async (tx) => {
    // 1. Tim hoac tao local user projection tuong ung voi platform user nay
    let [localUser] = await tx
      .select({ id: identityUserProjections.id })
      .from(identityUserProjections)
      .where(eq(identityUserProjections.platformUserId, member.userId))
      .limit(1);

    if (!localUser && member.email) {
      [localUser] = await tx
        .select({ id: identityUserProjections.id })
        .from(identityUserProjections)
        .where(eq(sql`LOWER(${identityUserProjections.email})`, member.email.toLowerCase()))
        .limit(1);
    }

    let userId: bigint;

    if (!localUser) {
      const [created] = await tx
        .insert(identityUserProjections)
        .values({
          id: generateSnowflake(),
          email: member.email || null,
          phone: member.phone || null,
          displayName: member.displayName || null,
          platformUserId: member.userId,
        })
        .returning({ id: identityUserProjections.id });

      if (!created) throw APIError.internal("failed to create local user projection");
      userId = created.id;
    } else {
      userId = localUser.id;
      await tx
        .update(identityUserProjections)
        .set({
          platformUserId: member.userId,
          displayName: member.displayName || undefined,
        })
        .where(eq(identityUserProjections.id, userId));
    }

    // 2. Tim hoac tao workspace local cho company nay
    const [workspace] = await tx
      .select({ id: identityWorkspaces.id })
      .from(identityWorkspaces)
      .where(eq(identityWorkspaces.platformCompanyId, member.companyId))
      .limit(1);

    let workspaceId: bigint;

    if (!workspace) {
      const [createdWorkspace] = await tx
        .insert(identityWorkspaces)
        .values({
          id: generateSnowflake(),
          name: member.companyName,
          platformCompanyId: member.companyId,
        })
        .returning({ id: identityWorkspaces.id });

      if (!createdWorkspace) throw APIError.internal("failed to create workspace");
      workspaceId = createdWorkspace.id;
    } else {
      workspaceId = workspace.id;
    }

    // 3. Upsert membership atomic — role/trạng thái LUÔN lấy từ platform,
    // kể cả ở lần sync thứ 2 trở đi (bug cũ: chỉ set role khi tạo mới,
    // dùng "admin"/"member" suy diễn theo isNewWorkspace thay vì role thật).
    await tx
      .insert(identityWorkspaceMemberships)
      .values({
        id: generateSnowflake(),
        workspaceId,
        userId,
        role: member.roleId,
        platformMembershipId: member.membershipId,
        sourceUpdatedAt: new Date(member.membershipUpdatedAt),
        syncedAt: new Date(),
      })
      .onConflictDoUpdate({
        target: [identityWorkspaceMemberships.workspaceId, identityWorkspaceMemberships.userId],
        set: {
          role: member.roleId,
          platformMembershipId: member.membershipId,
          sourceUpdatedAt: new Date(member.membershipUpdatedAt),
          syncedAt: new Date(),
          updatedAt: new Date(),
        },
      });

    return userId;
  });

  const localAccessToken = signAccessToken(localUserId.toString());
  return {
    access_token: localAccessToken,
    token_type: "bearer",
  };
}
```

- [ ] **Step 4: Run the test again**

```bash
npx vitest run identity/tests/sync.test.ts
```
Expected: PASS.

- [ ] **Step 5: Confirm the whole codebase compiles and the full suite is green**

```bash
npx tsc --noEmit -p . && npx vitest run
```
Expected: 0 TypeScript errors, all tests PASS. This closes out the "intentionally red between Task 3 and here" window noted in Task 3 Step 4.

- [ ] **Step 6: Commit**

```bash
git add services/company/identity/services/sync.service.ts services/company/identity/tests/sync.test.ts
git commit -m "fix(company): sync-from-platform now projects real role/status on every sync, atomic upsert prevents duplicate membership"
```

---

## Task 8: Company — drop `organizations` 1:1 wrapper, rework `workforce_members`

**Files:**
- Modify: `services/company/shared/db/schema/identity.ts`
- Create: `services/company/identity/migrations/6_workforce_drop_organizations.up.sql`
- Delete: `services/company/identity/services/organization.service.ts`, `services/company/identity/handlers/organization.handler.ts`
- Create: `services/company/identity/services/workforce.service.ts`, `services/company/identity/handlers/workforce.handler.ts`
- Modify: `services/company/identity/services/index.ts`
- Modify (rename import path + call shape): `services/company/identity/tests/organization.test.ts` → `services/company/identity/tests/workforce.test.ts`, `services/company/operations/tests/task.test.ts`, `services/company/shared/tests/golden-path.e2e.test.ts`, `services/company/scripts/seed-demo.mjs`
- Modify: `services/company/identity/services/tenant-context.service.ts` (drop unused `identityOrganizations` import, switch workforce lookup to `workspaceId`)

**Interfaces:**
- Produces: `hireWorkforceMember(params: { workspaceId, memberType: "HUMAN" | "AI_AGENT", roleTitle, humanUserId?, agentSpecId?, agentSpecVersion?, managerMemberId? }): Promise<WorkforceMember>`, `getWorkforceMember({ id }): Promise<WorkforceMember>`, where `WorkforceMember` is `{ id, workspaceId, memberType, humanUserId, agentSpecId, agentSpecVersion, managerMemberId, roleTitle, status }`.

- [ ] **Step 1: Write the migration**

```sql
-- services/company/identity/migrations/6_workforce_drop_organizations.up.sql

-- organizations luôn 1:1 với workspace (workspace_id UNIQUE) nên không tạo
-- bounded context mới — chỉ thêm 1 join thừa. workforce_members trỏ thẳng
-- workspace_id.
ALTER TABLE core.workforce_members ADD COLUMN workspace_id BIGINT REFERENCES core.workspaces(id) ON DELETE CASCADE;

UPDATE core.workforce_members wm
SET workspace_id = o.workspace_id
FROM core.organizations o
WHERE wm.organization_id = o.id;

ALTER TABLE core.workforce_members ALTER COLUMN workspace_id SET NOT NULL;
ALTER TABLE core.workforce_members DROP COLUMN organization_id;
DROP TABLE core.organizations;

-- agent_definition_id (BIGINT, không FK) là residue của một workforce-agent
-- row legacy — canonical agent identity giờ là AgentSpec registry của
-- packages/agent_core (id + version dạng text), không phải numeric FK.
ALTER TABLE core.workforce_members RENAME COLUMN agent_definition_id TO agent_spec_id_bigint_deprecated;
ALTER TABLE core.workforce_members ADD COLUMN agent_spec_id TEXT;
ALTER TABLE core.workforce_members ADD COLUMN agent_spec_version TEXT;
ALTER TABLE core.workforce_members DROP COLUMN agent_spec_id_bigint_deprecated;
ALTER TABLE core.workforce_members DROP COLUMN agent_profile_id;

-- org hierarchy tối thiểu (không tạo workforce.org_units — chưa cần org-chart thật).
ALTER TABLE core.workforce_members ADD COLUMN manager_member_id BIGINT REFERENCES core.workforce_members(id) ON DELETE SET NULL;

-- Chặn hybrid member vô nghĩa ở tầng DB.
ALTER TABLE core.workforce_members ADD CONSTRAINT workforce_members_type_consistency CHECK (
  (member_type = 'HUMAN' AND human_user_id IS NOT NULL AND agent_spec_id IS NULL)
  OR
  (member_type = 'AI_AGENT' AND human_user_id IS NULL AND agent_spec_id IS NOT NULL)
);
```

- [ ] **Step 2: Update the schema file**

Edit `services/company/shared/db/schema/identity.ts`, delete the `identityOrganizations` export entirely, and replace `identityWorkforceMembers` with:
```ts
export const identityWorkforceMembers = coreSchema.table("workforce_members", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull().references(() => identityWorkspaces.id, { onDelete: "cascade" }),
  memberType: text("member_type").notNull(),
  humanUserId: bigint("human_user_id", { mode: "bigint" }).references(() => identityUserProjections.id, { onDelete: "cascade" }),
  agentSpecId: text("agent_spec_id"),
  agentSpecVersion: text("agent_spec_version"),
  managerMemberId: bigint("manager_member_id", { mode: "bigint" }),
  roleTitle: text("role_title").notNull(),
  status: text("status").default("active").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});
```
(the self-referencing `managerMemberId` FK is enforced by the migration's `REFERENCES core.workforce_members(id)`, not expressed as a Drizzle `.references()` here to avoid a circular type reference — this matches how Drizzle self-FKs are commonly declared when the table is being defined in the same statement.)

- [ ] **Step 3: Write `workforce.service.ts`**

```ts
// services/company/identity/services/workforce.service.ts
import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { identityWorkforceMembers } = schema;

export interface WorkforceMember {
  id: string;
  workspaceId: string;
  memberType: "HUMAN" | "AI_AGENT";
  humanUserId: string | null;
  agentSpecId: string | null;
  agentSpecVersion: string | null;
  managerMemberId: string | null;
  roleTitle: string;
  status: string;
}

export interface HireWorkforceMemberParams {
  workspaceId: string | number;
  memberType: "HUMAN" | "AI_AGENT";
  roleTitle: string;
  humanUserId?: string | number;
  agentSpecId?: string;
  agentSpecVersion?: string;
  managerMemberId?: string | number;
}

function toWorkforceMember(row: {
  id: bigint;
  workspaceId: bigint;
  memberType: string;
  humanUserId: bigint | null;
  agentSpecId: string | null;
  agentSpecVersion: string | null;
  managerMemberId: bigint | null;
  roleTitle: string;
  status: string;
}): WorkforceMember {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    memberType: row.memberType as "HUMAN" | "AI_AGENT",
    humanUserId: row.humanUserId ? row.humanUserId.toString() : null,
    agentSpecId: row.agentSpecId,
    agentSpecVersion: row.agentSpecVersion,
    managerMemberId: row.managerMemberId ? row.managerMemberId.toString() : null,
    roleTitle: row.roleTitle,
    status: row.status,
  };
}

export async function hireWorkforceMemberRecord(params: HireWorkforceMemberParams): Promise<WorkforceMember> {
  const [row] = await db
    .insert(identityWorkforceMembers)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(params.workspaceId),
      memberType: params.memberType,
      humanUserId: params.humanUserId ? BigInt(params.humanUserId) : null,
      agentSpecId: params.agentSpecId || null,
      agentSpecVersion: params.agentSpecVersion || null,
      managerMemberId: params.managerMemberId ? BigInt(params.managerMemberId) : null,
      roleTitle: params.roleTitle,
    })
    .returning();

  if (!row) throw APIError.internal("failed to hire workforce member");
  return toWorkforceMember(row);
}

export async function getWorkforceMemberRecord(id: string | number): Promise<WorkforceMember> {
  const [row] = await db
    .select()
    .from(identityWorkforceMembers)
    .where(eq(identityWorkforceMembers.id, BigInt(id)))
    .limit(1);

  if (!row) throw APIError.notFound(`workforce member ${id} not found`);
  return toWorkforceMember(row);
}
```

- [ ] **Step 4: Write `workforce.handler.ts`**

```ts
// services/company/identity/handlers/workforce.handler.ts
import { api } from "encore.dev/api";
import {
  WorkforceMember,
  HireWorkforceMemberParams,
  hireWorkforceMemberRecord,
  getWorkforceMemberRecord,
} from "../services/workforce.service";

export { WorkforceMember, HireWorkforceMemberParams };

export const hireWorkforceMember = api(
  { method: "POST", path: "/identity/workforce-members", expose: true },
  async (params: HireWorkforceMemberParams): Promise<WorkforceMember> => {
    return hireWorkforceMemberRecord(params);
  }
);

export const getWorkforceMember = api(
  { method: "GET", path: "/identity/workforce-members/:id", expose: true },
  async ({ id }: { id: string }): Promise<WorkforceMember> => {
    return getWorkforceMemberRecord(id);
  }
);
```

- [ ] **Step 5: Delete the old organization files, update the barrel export**

```bash
git rm services/company/identity/services/organization.service.ts services/company/identity/handlers/organization.handler.ts
```
Edit `services/company/identity/services/index.ts`, replace `export * from "./organization.service";` with `export * from "./workforce.service";`.

- [ ] **Step 6: Fix `tenant-context.service.ts`'s workforce lookup**

It currently imports `identityOrganizations` (unused in the function body, dead import) and looks up workforce membership by `humanUserId` only — that part is unaffected by the schema change (still `eq(identityWorkforceMembers.humanUserId, localUser.id)`), so just drop the dead import. Edit the top of `services/company/identity/services/tenant-context.service.ts`:
```ts
const {
  identityUserProjections,
  identityWorkspaces,
  identityWorkspaceMemberships,
  identityWorkforceMembers,
} = schema;
```
(removes `identityOrganizations` from the destructure — Task 3's sed already renamed `identityUsers`→`identityUserProjections` and `identityWorkspaceMembers`→`identityWorkspaceMemberships` here, so only the dead `identityOrganizations` entry needs removing.)

- [ ] **Step 7: Rename and rewrite `organization.test.ts` → `workforce.test.ts`**

```bash
git mv services/company/identity/tests/organization.test.ts services/company/identity/tests/workforce.test.ts
```
Replace its content with:
```ts
import { describe, expect, it } from "vitest";
import { createWorkspace } from "../handlers/workspace.handler";
import { hireWorkforceMember, getWorkforceMember } from "../handlers/workforce.handler";

describe("hireWorkforceMember + getWorkforceMember", () => {
  it("hires a human member and fetches it back", async () => {
    const workspace = await createWorkspace({ name: "Hire Test Inc" });

    const member = await hireWorkforceMember({
      workspaceId: workspace.id,
      memberType: "HUMAN",
      roleTitle: "Ops Lead",
    });
    expect(member.id).toBeTruthy();
    expect(typeof member.id).toBe("string");
    expect(member.memberType).toBe("HUMAN");
    expect(member.workspaceId).toBe(workspace.id);
    expect(member.status).toBe("active");

    const fetched = await getWorkforceMember({ id: member.id });
    expect(fetched).toEqual(member);
  });

  it("hires an AI_AGENT member with an agentSpecId + agentSpecVersion reference", async () => {
    const workspace = await createWorkspace({ name: "AI Hire Test Inc" });

    const member = await hireWorkforceMember({
      workspaceId: workspace.id,
      memberType: "AI_AGENT",
      roleTitle: "CFO Agent",
      agentSpecId: "finance-cfo",
      agentSpecVersion: "1.0",
    });
    expect(member.agentSpecId).toBe("finance-cfo");
    expect(member.agentSpecVersion).toBe("1.0");
    expect(member.humanUserId).toBeNull();
  });

  it("supports a manager hierarchy via managerMemberId", async () => {
    const workspace = await createWorkspace({ name: "Hierarchy Test Inc" });
    const manager = await hireWorkforceMember({ workspaceId: workspace.id, memberType: "HUMAN", roleTitle: "VP Ops" });
    const report = await hireWorkforceMember({
      workspaceId: workspace.id,
      memberType: "HUMAN",
      roleTitle: "Ops Associate",
      managerMemberId: manager.id,
    });
    expect(report.managerMemberId).toBe(manager.id);
  });

  it("throws not found for a missing member id", async () => {
    await expect(getWorkforceMember({ id: 999999999 })).rejects.toThrow();
  });
});
```

- [ ] **Step 8: Fix `task.test.ts`**

Edit `services/company/operations/tests/task.test.ts:3` and its `hireWorkforceMember` call. Change:
```ts
import { createOrganization, hireWorkforceMember } from "../../identity/handlers/organization.handler";
```
to:
```ts
import { hireWorkforceMember } from "../../identity/handlers/workforce.handler";
```
And wherever it does:
```ts
const org = await createOrganization({ workspaceId: workspace.id, name: ... });
const member = await hireWorkforceMember({ organizationId: org.id, memberType: "HUMAN", roleTitle: "Ops" });
```
change to (dropping the `createOrganization` call entirely):
```ts
const member = await hireWorkforceMember({ workspaceId: workspace.id, memberType: "HUMAN", roleTitle: "Ops" });
```
(Read the file first to confirm the exact surrounding variable names — `workspace`/`workspaceId` — before editing, since this plan doesn't have the full file content on hand.)

- [ ] **Step 9: Fix `golden-path.e2e.test.ts`**

Change the import line:
```ts
import { createOrganization, hireWorkforceMember } from "../../identity/handlers/organization.handler";
```
to:
```ts
import { hireWorkforceMember } from "../../identity/handlers/workforce.handler";
```
Replace:
```ts
    const organization = await createOrganization({ workspaceId, name: "Quốc Gia Khởi Nghiệp" });
    expect(organization.id).toBeTruthy();
    expect(typeof organization.id).toBe("string");

    const coFounder = await hireWorkforceMember({
      organizationId: organization.id,
      memberType: "HUMAN",
      roleTitle: "Co-founder / COO",
    });
    expect(coFounder.memberType).toBe("HUMAN");

    const aiMember = await hireWorkforceMember({
      organizationId: organization.id,
      memberType: "AI_AGENT",
      roleTitle: "AI Ops Copilot",
      agentProfileId: "cosa-ops-copilot",
    });
    expect(aiMember.memberType).toBe("AI_AGENT");
```
with:
```ts
    const coFounder = await hireWorkforceMember({
      workspaceId,
      memberType: "HUMAN",
      roleTitle: "Co-founder / COO",
    });
    expect(coFounder.memberType).toBe("HUMAN");

    const aiMember = await hireWorkforceMember({
      workspaceId,
      memberType: "AI_AGENT",
      roleTitle: "AI Ops Copilot",
      agentSpecId: "cosa-ops-copilot",
      agentSpecVersion: "1.0",
    });
    expect(aiMember.memberType).toBe("AI_AGENT");
```

- [ ] **Step 10: Fix `scripts/seed-demo.mjs`**

Read `services/company/scripts/seed-demo.mjs` around the lines the earlier grep found (`68-90`), and apply the same transform: drop the `POST /identity/organizations` call, change the 2 `hireWorkforceMember`-equivalent calls (likely raw `call("POST", "/identity/workforce-members", { organizationId: organization.id, ... })`) to pass `workspaceId` instead of `organizationId`, and `agentProfileId` → `agentSpecId`/`agentSpecVersion` if present. Since this is a standalone Node script (not part of `vitest run`), verify it manually after the migration is applied:
```bash
cd services/company && node scripts/seed-demo.mjs
```
Expected: script completes without HTTP errors and prints workforce member ids.

- [ ] **Step 11: Run the migration and the full test suite**

```bash
cd services/company && node scripts/migrate.mjs && npx tsc --noEmit -p . && npx vitest run
```
Expected: migration `6_workforce_drop_organizations.up.sql` applies cleanly, 0 TypeScript errors, all tests PASS.

- [ ] **Step 12: Commit**

```bash
git add -A
git commit -m "refactor(company): drop organizations 1:1 wrapper, rework workforce_members (agent_spec_id/version, manager hierarchy, type-consistency CHECK)"
```

---

## Task 9: Company — gateway auth must not accept raw platform tokens

**Files:**
- Modify: `services/company/identity/handlers/auth.handler.ts`
- Test: `services/company/identity/tests/gateway-auth.test.ts` (new)

**Interfaces:**
- Produces: `authHandler` (the Encore gateway auth function) now rejects any token that isn't a valid local Company session token — no silent fallback to `verifyPlatformToken`.

**Why:** `sync-from-platform` (`sync.handler.ts:11`) already uses `auth: false` and validates the platform token itself — it never goes through this gateway. No other `auth: true` endpoint should legitimately receive a raw platform token, because every downstream consumer (`getMeProfile`, and any future `auth: true` handler) treats `authData.userID` as a local Snowflake ID string suitable for `BigInt()`. A platform token's `sub` is a *platform* user ID — a different ID namespace. (`resolveTenantContext`/`requireWorkspaceAccess`, used by finance-legal/commercial/operations endpoints, is a *separate* mechanism that legitimately still accepts platform tokens directly — that one is untouched by this task; see Task 10.)

- [ ] **Step 1: Write the failing test**

```ts
// services/company/identity/tests/gateway-auth.test.ts
import { describe, expect, it } from "vitest";
import jwt from "jsonwebtoken";
import { auth } from "../handlers/auth.handler";
import { createTestSession } from "./helpers/test-session";

const PLATFORM_JWT_SECRET = process.env.PLATFORM_JWT_SECRET || "cosa-super-secret-platform-jwt-key-change-in-prod";

describe("gateway authHandler", () => {
  it("accepts a valid local Company session token", async () => {
    const session = await createTestSession({ displayName: "Gateway Test" });
    const authData = await auth({ authorization: `Bearer ${session.accessToken}` });
    expect(authData.userID).toBe(session.userId);
  });

  it("rejects a raw platform token (not a local session token)", async () => {
    const platformToken = jwt.sign({ sub: "platform-user-123", aud: "cosa" }, PLATFORM_JWT_SECRET);
    await expect(auth({ authorization: `Bearer ${platformToken}` })).rejects.toThrow();
  });

  it("rejects a missing authorization header", async () => {
    await expect(auth({})).rejects.toThrow();
  });
});
```

- [ ] **Step 2: Run it to confirm the platform-token test fails**

```bash
cd services/company && npx vitest run identity/tests/gateway-auth.test.ts
```
Expected: the first and third tests PASS, the second ("rejects a raw platform token") FAILS — current code accepts it.

- [ ] **Step 3: Remove the platform-token fallback branch**

Edit `services/company/identity/handlers/auth.handler.ts`, change:
```ts
export const auth = authHandler<AuthParams, AuthData>(async (params) => {
  const header = params.authorization;
  if (!header || !header.startsWith("Bearer ")) {
    throw APIError.unauthenticated("missing bearer token");
  }
  const token = header.slice("Bearer ".length);
  try {
    const decoded = verifyAccessToken(token);
    return { userID: decoded.sub };
  } catch {
    try {
      const pDecoded = verifyPlatformToken(token);
      return { userID: pDecoded.sub };
    } catch {
      throw APIError.unauthenticated("invalid or expired token");
    }
  }
});
```
to:
```ts
export const auth = authHandler<AuthParams, AuthData>(async (params) => {
  const header = params.authorization;
  if (!header || !header.startsWith("Bearer ")) {
    throw APIError.unauthenticated("missing bearer token");
  }
  const token = header.slice("Bearer ".length);
  try {
    const decoded = verifyAccessToken(token);
    return { userID: decoded.sub };
  } catch {
    throw APIError.unauthenticated("invalid or expired token");
  }
});
```
And remove the now-unused `import { verifyPlatformToken } from "../services/platform.client";` line.

- [ ] **Step 4: Run the test again**

```bash
npx vitest run identity/tests/gateway-auth.test.ts
```
Expected: all 3 PASS.

- [ ] **Step 5: Run the full suite**

```bash
npx tsc --noEmit -p . && npx vitest run
```
Expected: 0 errors, all PASS (nothing else in the codebase calls the gateway `auth` function with a platform token).

- [ ] **Step 6: Commit**

```bash
git add services/company/identity/handlers/auth.handler.ts services/company/identity/tests/gateway-auth.test.ts
git commit -m "fix(company): gateway auth no longer accepts raw platform tokens, closing an ID-namespace confusion bug"
```

---

## Task 10: Company — remove `TenantContext`'s implicit `workspaceId = "1"` fallbacks

**Files:**
- Modify: `services/company/identity/services/tenant-context.service.ts`
- Test: `services/company/identity/tests/tenant-context.test.ts` (add 2 new cases)

**Interfaces:**
- Produces: `resolveTenantContext` throws `APIError.notFound` instead of defaulting to workspace `"1"` in the 2 identified branches. The already-correct "explicit `workspaceId` + not a member → `permissionDenied`" branch (local-token path) is untouched.

- [ ] **Step 1: Write the failing tests**

Add to `services/company/identity/tests/tenant-context.test.ts` (append inside the existing `describe("resolveTenantContext", ...)` block, after the last `it(...)`):
```ts
  it("throws instead of defaulting to workspace 1 when a local-token user has no membership and no workspaceId is given", async () => {
    const session = await createTestSession({ displayName: "No Membership Test", role: "admin" });
    // Xoá membership vừa tạo để mô phỏng user không thuộc workspace nào cả.
    const { db, schema } = await import("../models/db");
    await db.delete(schema.identityWorkspaceMemberships).where(
      require("drizzle-orm").eq(schema.identityWorkspaceMemberships.userId, BigInt(session.userId))
    );

    await expect(
      resolveTenantContext({ authorization: `Bearer ${session.accessToken}` })
    ).rejects.toThrow();
  });
```
(This test file already imports `createTestSession` from Task 5's edit — no new import needed for that part. `require("drizzle-orm")` inline avoids adding a new top-level import purely for one assertion; if the project's lint config forbids `require` in ESM test files, add `import { eq } from "drizzle-orm";` at the top instead and use `eq(...)` directly.)

- [ ] **Step 2: Run it to confirm it fails**

```bash
cd services/company && npx vitest run identity/tests/tenant-context.test.ts
```
Expected: new test FAILS — current code returns a context with `workspaceId: "1"` instead of throwing.

- [ ] **Step 3: Fix the local-token branch**

Edit `services/company/identity/services/tenant-context.service.ts`, in the `else` branch (no `params.workspaceId` provided), change:
```ts
  } else {
    // Lấy membership đầu tiên của user
    const [firstMembership] = await db
      .select({
        workspaceId: identityWorkspaceMemberships.workspaceId,
        role: identityWorkspaceMemberships.role,
      })
      .from(identityWorkspaceMemberships)
      .where(eq(identityWorkspaceMemberships.userId, localUserId))
      .limit(1);

    if (firstMembership) {
      targetWorkspaceId = firstMembership.workspaceId;
      memberRole = firstMembership.role;
    } else {
      targetWorkspaceId = BigInt(1);
    }
  }
```
to:
```ts
  } else {
    // Lấy membership đầu tiên của user
    const [firstMembership] = await db
      .select({
        workspaceId: identityWorkspaceMemberships.workspaceId,
        role: identityWorkspaceMemberships.role,
      })
      .from(identityWorkspaceMemberships)
      .where(eq(identityWorkspaceMemberships.userId, localUserId))
      .limit(1);

    if (!firstMembership) {
      throw APIError.notFound("user không thuộc workspace nào — không thể suy diễn workspace mặc định");
    }

    targetWorkspaceId = firstMembership.workspaceId;
    memberRole = firstMembership.role;
  }
```

- [ ] **Step 4: Fix the platform-token branch**

Change:
```ts
    let workspaceIdStr = ws ? ws.id.toString() : (params.workspaceId ? String(params.workspaceId) : "1");
```
to:
```ts
    if (!ws && !params.workspaceId) {
      throw APIError.notFound(
        "chưa có workspace projection cho company này — gọi sync-from-platform trước, hoặc truyền workspaceId tường minh"
      );
    }
    const workspaceIdStr = ws ? ws.id.toString() : String(params.workspaceId);
```
(Insert this right before the existing `let [localUser] = await db.select...` line in that branch, replacing the single `let workspaceIdStr = ...` line.)

- [ ] **Step 5: Run the tests again**

```bash
npx vitest run identity/tests/tenant-context.test.ts
```
Expected: all PASS, including the new one.

- [ ] **Step 6: Run the full suite**

```bash
npx tsc --noEmit -p . && npx vitest run
```
Expected: 0 errors, all PASS. (If any other test relied on the old workspace-"1" fallback behavior, it will surface here — read the failure and fix the test to pass an explicit `workspaceId` or set up a real membership first, rather than reverting the fix.)

- [ ] **Step 7: Commit**

```bash
git add services/company/identity/services/tenant-context.service.ts services/company/identity/tests/tenant-context.test.ts
git commit -m "fix(company): TenantContext no longer defaults to workspace \"1\" — throws explicitly when tenant cannot be resolved"
```

---

## Task 11: Company — make local session TTL configurable, default 8h

**Files:**
- Modify: `services/company/identity/services/token.service.ts`
- Test: `services/company/identity/tests/token-ttl.test.ts` (new)

**Interfaces:**
- Produces: `signAccessToken` now signs with an env-configurable TTL, default `"8h"`.

- [ ] **Step 1: Write the failing test**

```ts
// services/company/identity/tests/token-ttl.test.ts
import { describe, expect, it, afterEach } from "vitest";
import jwt from "jsonwebtoken";

const JWT_SECRET = process.env.JWT_SECRET || "cosa-dev-jwt-secret-do-not-use-in-prod";

describe("signAccessToken TTL", () => {
  const originalTtl = process.env.COMPANY_LOCAL_SESSION_TTL;

  afterEach(() => {
    if (originalTtl === undefined) delete process.env.COMPANY_LOCAL_SESSION_TTL;
    else process.env.COMPANY_LOCAL_SESSION_TTL = originalTtl;
    vi_resetModules();
  });

  function vi_resetModules() {
    // token.service.ts reads process.env.COMPANY_LOCAL_SESSION_TTL at import
    // time in this plan's implementation (module-level const) — tests must
    // re-import the module after changing the env var. vitest's `vi` is
    // globally available via the `vitest` test globals config in this repo;
    // if not, switch signAccessToken to read process.env at call time
    // instead of at module load time (see Step 2 note).
  }

  it("defaults to an 8h expiry when COMPANY_LOCAL_SESSION_TTL is unset", async () => {
    delete process.env.COMPANY_LOCAL_SESSION_TTL;
    const { signAccessToken } = await import("../services/token.service");
    const token = signAccessToken("12345");
    const decoded = jwt.verify(token, JWT_SECRET) as jwt.JwtPayload;
    const lifetimeSeconds = (decoded.exp as number) - (decoded.iat as number);
    expect(lifetimeSeconds).toBe(8 * 60 * 60);
  });

  it("honors COMPANY_LOCAL_SESSION_TTL when set", async () => {
    process.env.COMPANY_LOCAL_SESSION_TTL = "2h";
    const { signAccessToken } = await import("../services/token.service");
    const token = signAccessToken("12345");
    const decoded = jwt.verify(token, JWT_SECRET) as jwt.JwtPayload;
    const lifetimeSeconds = (decoded.exp as number) - (decoded.iat as number);
    expect(lifetimeSeconds).toBe(2 * 60 * 60);
  });
});
```
Note: because `token.service.ts` reads `process.env.JWT_SECRET`/`process.env.COMPANY_LOCAL_SESSION_TTL` at module load time (matching the existing `JWT_SECRET` pattern in the file), the test uses `await import(...)` per-test after mutating `process.env` so each test gets a fresh module evaluation — this requires vitest's default per-test module isolation (already the case for this repo, since no `vitest.config.ts` override to `isolate: false` was found in the codebase exploration for this plan; if that turns out to not hold, switch `signAccessToken` to read `process.env.COMPANY_LOCAL_SESSION_TTL` at call time inside the function body instead of as a module-level `const`, which sidesteps the whole caching concern — see Step 2's alternative).

- [ ] **Step 2: Run it to confirm it fails**

```bash
cd services/company && npx vitest run identity/tests/token-ttl.test.ts
```
Expected: FAIL — current code hardcodes `expiresIn: "7d"`.

- [ ] **Step 3: Update `token.service.ts`**

Replace the full file content with:
```ts
import jwt from "jsonwebtoken";

const JWT_SECRET = process.env.JWT_SECRET || "cosa-dev-jwt-secret-do-not-use-in-prod";

export interface JwtPayload {
  sub: string;
}

function getSessionTtl(): string {
  return process.env.COMPANY_LOCAL_SESSION_TTL?.trim() || "8h";
}

export function signAccessToken(userId: string): string {
  return jwt.sign({ sub: userId }, JWT_SECRET, { expiresIn: getSessionTtl() });
}

export function verifyAccessToken(token: string): JwtPayload {
  return jwt.verify(token, JWT_SECRET) as JwtPayload;
}
```
(Reading the TTL inside `getSessionTtl()` at call time — not as a module-level `const` — means the test in Step 1 works correctly under vitest's module caching regardless of isolation settings, since every `signAccessToken()` call re-reads `process.env` fresh.)

- [ ] **Step 4: Run the test again**

```bash
npx vitest run identity/tests/token-ttl.test.ts
```
Expected: PASS.

- [ ] **Step 5: Run the full suite**

```bash
npx tsc --noEmit -p . && npx vitest run
```
Expected: 0 errors, all PASS.

- [ ] **Step 6: Commit**

```bash
git add services/company/identity/services/token.service.ts services/company/identity/tests/token-ttl.test.ts
git commit -m "feat(company): make local session TTL configurable via COMPANY_LOCAL_SESSION_TTL, default 8h (was hardcoded 7d)"
```

---

## Task 12: Docs — fix `COSA_CANONICAL_OWNERSHIP_MAP.md` drift

**Files:**
- Modify: `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`

- [ ] **Step 1: Read the current file in full**

```bash
cat docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md
```

- [ ] **Step 2: Fix the 2 confirmed drift points**

At line 3, the doc claims `Status: Fully Promoted Canonical Architecture (Promotion Completed — Phases 0–11 Completed)` — add a dated note that Plan A/B superseded parts of the identity/storage design (do not simply delete the status line; append context so history isn't erased):
```markdown
> **Status:** Fully Promoted Canonical Architecture (Promotion Completed — Phases 0–11 Completed)
> **Update 2026-08-23:** Identity/workforce storage section below was revised by
> `docs/superpowers/specs/2026-08-23-identity-foundation-plan-a-design.md` — see
> that spec for the current `core`/`workforce` schema and ownership boundary.
```

At line 41, the doc's ownership table row:
```
| **Hybrid Workforce Identity** | `services/identity` (`WorkforceMember`) | Encore Identity Service | Active Canonical Identity Source |
```
Fix the path (code lives at `services/company/identity/`, there is no standalone `services/identity`) and reflect the post-Plan-A schema:
```
| **Hybrid Workforce Identity** | `services/company/identity` (`core.workforce_members`) | Encore Identity Module (part of `services/company`) | Active Canonical Identity Source |
```

- [ ] **Step 3: Spot-check the rest of the doc for the same `services/identity` mistake**

```bash
grep -n "services/identity\b" docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md
```
Fix every remaining occurrence the same way (`services/identity` → `services/company/identity`), reading enough surrounding context each time to keep the sentence grammatical.

- [ ] **Step 4: Commit**

```bash
git add docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md
git commit -m "docs: fix COSA_CANONICAL_OWNERSHIP_MAP.md drift — services/identity was never a real path, note Plan A schema revision"
```

---

## Task 13: Final verification pass (both services)

**Files:** none (verification only)

- [ ] **Step 1: Run both services' migrations from a clean checkout state**

```bash
cd services/cosa && node scripts/migrate.mjs
cd ../company && node scripts/migrate.mjs
```
Expected: both complete with no errors, all new migration files (`services/cosa/migrations/5_rename_company_roles.up.sql`, `services/company/identity/migrations/5_identity_projection_rework.up.sql`, `services/company/identity/migrations/6_workforce_drop_organizations.up.sql`) recorded in `public.schema_migrations`.

- [ ] **Step 2: Run both full test suites**

```bash
cd services/cosa && npx vitest run
cd ../company && npx vitest run
```
Expected: all PASS in both.

- [ ] **Step 3: Grep-verify the Definition of Done from the spec**

```bash
cd /Volumes/SSD/javis-saas
echo "password_hash refs (expect 0):" && grep -rn "password_hash\|passwordHash" services/company --include="*.ts" | grep -v "\.test\.ts" | wc -l
echo "identityOrganizations refs (expect 0):" && grep -rn "identityOrganizations" services/company --include="*.ts" | wc -l
echo "agent_definition_id refs (expect 0):" && grep -rn "agent_definition_id\|agentDefinitionId" services/company --include="*.ts" | wc -l
echo "companyRoles refs in cosa (expect 0):" && grep -rn "companyRoles" services/cosa --include="*.ts" | wc -l
echo "verifyPlatformToken in gateway auth.handler.ts (expect 0):" && grep -n "verifyPlatformToken" services/company/identity/handlers/auth.handler.ts | wc -l
echo "workspace fallback to \"1\" (expect 0):" && grep -n '"1"' services/company/identity/services/tenant-context.service.ts | wc -l
echo "hardcoded 7d TTL (expect 0):" && grep -rn '"7d"' services/company/identity/services/token.service.ts | wc -l
```
Expected: every count is `0`.

- [ ] **Step 4: Manual smoke test of the sync flow (optional but recommended if docker-compose is running)**

```bash
docker compose up -d postgres
cd services/cosa && npm run dev &
cd ../company && npm run dev &
# then, once both are up:
curl -s -X POST http://localhost:4001/platform/auth/register -H 'Content-Type: application/json' \
  -d '{"email":"smoketest@example.com","password":"Password123!","full_name":"Smoke Test"}'
# take the returned access_token, then:
curl -s -X POST http://localhost:4000/identity/sync-from-platform -H 'Content-Type: application/json' \
  -d '{"platform_access_token":"<token from above>","company_id":"<company id from register response>"}'
```
Expected: the second call returns `{ "access_token": "...", "token_type": "bearer" }` with no error — confirms the whole COSA-login → sync-from-platform → local Company session chain works end-to-end through real HTTP, not just in-process tests.

- [ ] **Step 5: Final commit (if Step 4 required any fixes) or close out**

If Step 4 surfaced no issues, no commit needed — Plan A is complete. If it did, fix, re-run Steps 2-4, then commit the fix with an appropriate message.

---

## Self-Review Notes (completed during plan authoring)

- **Spec coverage:** all 10 numbered items in `docs/superpowers/specs/2026-08-23-identity-foundation-plan-a-design.md`'s "Plan A — Thay đổi cụ thể" map to a task: item 1→Task 6, item 2→Tasks 3-5, item 3→Tasks 2+7, item 4→Task 8, item 5→Task 8, item 6→Task 1, item 7→Task 9, item 8→Task 10, item 9→Task 11, item 10→Task 12.
- **Placeholder scan:** no TBD/TODO; the two spots that read as "figure it out at execution time" (Task 8 Step 8/10's "read the file first to confirm exact variable names") are flagged explicitly as such because this plan was written without live access to `task.test.ts`'s full body and `seed-demo.mjs`'s full body at authoring time — both are small, mechanical edits fully specified in shape (what to remove, what to change it to), just not pasted as an exact diff against unseen surrounding lines. Everything else has full code.
- **Type consistency:** `WorkforceMember`/`HireWorkforceMemberParams` field names (`workspaceId`, `agentSpecId`, `agentSpecVersion`, `managerMemberId`) are consistent between Task 8's service, handler, and test. `TestSession`/`createTestSession` return shape (`accessToken`, `userId`, `workspaceId`) is consistent between Task 4's helper and every Task 5/9/10 consumer. `ValidateMembershipResult`'s `membershipId`/`membershipUpdatedAt` are consistent between Task 1 (COSA) and Task 2 (Company) and Task 7 (sync.service.ts usage).
