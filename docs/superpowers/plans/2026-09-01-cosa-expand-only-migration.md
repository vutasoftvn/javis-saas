# COSA Expand-only Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace unapplied destructive COSA migration 26/27 behavior with an Expand-only schema that supports the current TypeScript API while preserving N-1 physical database names.

**Architecture:** Migration 26 remains additive. Migration 27 adds presentation/profile fields with safe defaults and leaves every table/column name and legacy table available. Drizzle exports keep logical workspace names but map to existing `platform_*` physical names; a future N+2 Contract release may rename/drop only after rollback evidence.

**Tech Stack:** PostgreSQL 16+, SQL migrations, Node migration runner, Drizzle ORM, schema fingerprint gates.

**Spec:** `docs/superpowers/specs/2026-09-01-backend-quality-and-encore-guardrails-design.md`

## Global Constraints

- Never edit a migration whose filename and checksum appear in `public.schema_migrations` on a non-disposable database.
- The release contains no `DROP TABLE`, `DROP COLUMN`, `RENAME`, destructive role deletion, or unsafe `SET NOT NULL`.
- Do not hand-edit `deploy/schema/fingerprints.json`; only update it through the fingerprint generator after review.
- Do not deploy this work; staging Gate G is an operator-owned verification step after code review.

---

### Task 1: Establish the migration-history decision before any edit

**Files:**
- Modify: none.
- Read: `services/cosa/scripts/migrate.mjs`, `services/cosa/migrations/26_workspace_agent_policy_and_drop_legacy_companies.up.sql`, `services/cosa/migrations/27_refactor_clean_roles_profiles_and_workspaces.up.sql`.

**Interfaces:**
- Consumes: `COSA_MIGRATOR_DATABASE_URL` and `public.schema_migrations(service, filename, sha256)`.
- Produces: a recorded decision of `unapplied-disposable` or `applied-immutable` for files 26 and 27.

- [ ] **Step 1: Query the local migration ledger with the migrator credential.**

```sql
SELECT service, filename, encode(sha256, 'hex') AS sha256, applied_at
FROM public.schema_migrations
WHERE service = 'cosa'
  AND filename IN (
    '26_workspace_agent_policy_and_drop_legacy_companies.up.sql',
    '27_refactor_clean_roles_profiles_and_workspaces.up.sql'
  )
ORDER BY filename;
```

- [ ] **Step 2: Classify the result before editing.**

An empty result permits replacing these unapplied files on that disposable
database. Any row makes its matching file immutable: run the existing down
migration against a disposable local database or create a new disposable local
database; do not alter the file and rerun it against the recorded checksum.

- [ ] **Step 3: Verify the runner sees no checksum drift before migration work.**

Run: `cd services/cosa && node scripts/migrate.mjs --check`

Expected: PASS on an unchanged database, or a documented checksum error that
requires the immutable path above.

### Task 2: Make migration 26 additive

**Files:**
- Modify: `services/cosa/migrations/26_workspace_agent_policy_and_drop_legacy_companies.up.sql:20-24`
- Test: `scripts/check-migration-backward-compat.mjs`

**Interfaces:**
- Consumes: `cosa.platform_workspaces(id)`.
- Produces: `cosa.workspace_agent_policy(platform_workspace_id, tool_pattern, decision, reason, timestamps)` and its two indexes.

- [ ] **Step 1: Run the compatibility checker to demonstrate the current violation.**

Run: `make migration-compat-check`

Expected: FAIL and report the five `DROP TABLE` statements in migration 26.

- [ ] **Step 2: Delete only the five legacy-company table drop statements.**

The resulting tail of migration 26 must end after creation of
`idx_workspace_agent_policy_workspace_tool`; retain the `CREATE TABLE` and both
indexes exactly as they reference `platform_workspaces` and
`platform_workspace_id`.

- [ ] **Step 3: Keep the down migration limited to the newly-created table.**

```sql
DROP TABLE IF EXISTS cosa.workspace_agent_policy CASCADE;
```

Do not add a down migration that drops `companies`, `licenses`, memberships,
entitlements or legacy policy tables.

- [ ] **Step 4: Run the migration compatibility checker.**

Run: `make migration-compat-check`

Expected: migration 26 no longer produces destructive-DDL violations; migration
27 may still fail until the next task.

- [ ] **Step 5: Commit the additive migration 26 change.**

```bash
git add services/cosa/migrations/26_workspace_agent_policy_and_drop_legacy_companies.up.sql \
  services/cosa/migrations/26_workspace_agent_policy_and_drop_legacy_companies.down.sql
git commit -m "fix(cosa): keep legacy company tables during expansion"
```

### Task 3: Convert migration 27 to safe additions only

**Files:**
- Modify: `services/cosa/migrations/27_refactor_clean_roles_profiles_and_workspaces.up.sql`
- Modify: `services/cosa/migrations/27_refactor_clean_roles_profiles_and_workspaces.down.sql`
- Test: `scripts/check-migration-backward-compat.mjs`

**Interfaces:**
- Consumes: baseline `cosa.roles`, `cosa.users`, `cosa.profiles`,
  `cosa.platform_workspaces`, `cosa.platform_workspace_memberships`,
  `cosa.platform_workspace_sync_log`, `cosa.workspace_licenses`, and
  `cosa.workspace_entitlements`.
- Produces: additive `roles.name`, `roles.category`, `roles.sort_order`,
  `profiles.role_id`, `profiles.bio`, and `profiles.headline`, while retaining
  all existing names and values.

- [ ] **Step 1: Run the compatibility checker and capture the 12 migration-27 violations.**

Run: `node scripts/check-migration-backward-compat.mjs`

Expected: FAIL with four column drops and eight table/column renames from
migration 27.

- [ ] **Step 2: Replace role mutations with safe additive columns and deterministic upserts.**

```sql
ALTER TABLE cosa.roles ADD COLUMN IF NOT EXISTS name TEXT NOT NULL DEFAULT 'Legacy role';
ALTER TABLE cosa.roles ADD COLUMN IF NOT EXISTS category TEXT NOT NULL DEFAULT 'legacy';
ALTER TABLE cosa.roles ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0;

INSERT INTO cosa.roles (id, name, category, sort_order, description) VALUES
  ('member', 'Thành viên', 'community', 11, 'Thành viên chung')
ON CONFLICT (id) DO UPDATE
SET name = EXCLUDED.name,
    category = EXCLUDED.category,
    sort_order = EXCLUDED.sort_order,
    description = EXCLUDED.description;
```

Retain the complete thirteen-role upsert list from the current migration. Remove
the `DELETE FROM cosa.roles`, `DROP COLUMN scope`, and `DROP COLUMN level`
statements.

- [ ] **Step 3: Keep legacy user/profile physical identifiers and add only profile fields.**

```sql
ALTER TABLE cosa.profiles
  ADD COLUMN IF NOT EXISTS role_id TEXT NOT NULL DEFAULT 'member'
  REFERENCES cosa.roles(id);
ALTER TABLE cosa.profiles ADD COLUMN IF NOT EXISTS bio TEXT;
ALTER TABLE cosa.profiles ADD COLUMN IF NOT EXISTS headline TEXT;
```

Remove both `cosa.users` column drops and the `profiles.user_id` → `id` rename.
Do not rename workspace tables, workspace foreign-key columns, membership role,
or synchronization-log columns.

- [ ] **Step 4: Write a reversible down migration for additions only.**

The down file drops `headline`, `bio`, `role_id`, `sort_order`, `category`, and
`name` in reverse dependency order. It must not rename tables/columns or drop
legacy tables, because the up migration never does either.

- [ ] **Step 5: Run the compatibility checker.**

Run: `make migration-compat-check`

Expected: PASS with no compatibility exemption marker.

- [ ] **Step 6: Commit migration 27 independently.**

```bash
git add services/cosa/migrations/27_refactor_clean_roles_profiles_and_workspaces.up.sql \
  services/cosa/migrations/27_refactor_clean_roles_profiles_and_workspaces.down.sql
git commit -m "fix(cosa): make workspace schema migration expand-only"
```

### Task 4: Map logical Drizzle names to N-1 physical schema names

**Files:**
- Modify: `services/cosa/storage/schema.ts:41-119`
- Test: `services/cosa/tests/workspace-connector.test.ts`
- Test: `services/cosa/tests/venture-workspace-handler.test.ts`

**Interfaces:**
- Consumes: physical columns `user_id`, `owner_user_id`, `platform_workspace_id`,
  `role`, and tables with `platform_` names.
- Produces: unchanged logical TypeScript exports `profiles.id`, `workspaces`,
  `workspaceMemberships`, `workspaceAgentPolicy`, `workspaceLicenses`,
  `workspaceEntitlements`, and `workspaceSyncLogs`.

- [ ] **Step 1: Add a failing schema-mapping assertion to each affected COSA integration test.**

```ts
await db.insert(workspaces).values({
  id: 2001n,
  workspaceName: "Compatibility workspace",
  ownerId: 1001n,
  status: "active",
});
const [stored] = await db.select().from(workspaces).where(eq(workspaces.id, 2001n));
expect(stored?.ownerId).toBe(1001n);
```

- [ ] **Step 2: Run the focused tests against the fresh migrated database.**

Run: `cd services/cosa && pnpm vitest run tests/workspace-connector.test.ts tests/venture-workspace-handler.test.ts`

Expected: FAIL until the Drizzle table and column names align with the preserved
physical schema.

- [ ] **Step 3: Change only physical table/column mappings in `storage/schema.ts`.**

```ts
export const profiles = cosaSchema.table("profiles", {
  id: bigint("user_id", { mode: "bigint" }).primaryKey().references(() => users.id, { onDelete: "cascade" }),
  // remaining logical fields unchanged
});

export const workspaces = cosaSchema.table("platform_workspaces", {
  ownerId: bigint("owner_user_id", { mode: "bigint" }).notNull().references(() => users.id, { onDelete: "cascade" }),
  // remaining logical fields unchanged
});

export const workspaceMemberships = cosaSchema.table("platform_workspace_memberships", {
  workspaceId: bigint("platform_workspace_id", { mode: "bigint" }).notNull().references(() => workspaces.id, { onDelete: "cascade" }),
  roleId: text("role").default("member").notNull().references(() => roles.id),
});
```

Apply the same physical-column mapping to `workspaceAgentPolicy`,
`workspaceLicenses`, `workspaceEntitlements`, and `workspaceSyncLogs`; map the
last table to `platform_workspace_sync_log`. Keep the backward-compatibility
export aliases at the bottom of the file.

- [ ] **Step 4: Run focused tests and COSA typecheck.**

Run: `pnpm vitest run tests/workspace-connector.test.ts tests/venture-workspace-handler.test.ts && pnpm typecheck`

Expected: PASS with unchanged logical DTO field names.

- [ ] **Step 5: Commit the schema mapping.**

```bash
git add services/cosa/storage/schema.ts services/cosa/tests/workspace-connector.test.ts \
  services/cosa/tests/venture-workspace-handler.test.ts
git commit -m "fix(cosa): map workspace schema to compatible storage names"
```

### Task 5: Prove migration, rollback, fingerprint, and staging readiness

**Files:**
- Modify: `deploy/schema/fingerprints.json` only through its generator.
- Create: `docs/operations/migration-gate-g-2026-09-01.md` only after the real staging run scheduled for this release.

**Interfaces:**
- Consumes: the three migration gates and the production `migrate` container.
- Produces: reviewed fingerprint and staging Gate G evidence.

- [ ] **Step 1: Run a fresh local bootstrap and all migration gates.**

Run: `make db-bootstrap && make dev-migrate && make migration-check && make test-migration-rollback`

Expected: PASS. If the local database is not disposable, stop and return to Task 1 rather than resetting it.

- [ ] **Step 2: Generate the fingerprint only after the preceding commands pass.**

Run: `make schema-fingerprint-write && git diff -- deploy/schema/fingerprints.json && make schema-fingerprint-check`

Expected: the diff shows retained legacy physical names plus the intended additive
columns; the final checker PASSes.

- [ ] **Step 3: Commit the reviewed fingerprint and migration evidence.**

```bash
git add deploy/schema/fingerprints.json
git commit -m "test(schema): record compatible cosa migration fingerprint"
```

- [ ] **Step 4: Run Gate G in staging through the production artifact.**

Run: `cd deploy/central_vps && docker compose -f docker-compose.prod.yaml --env-file .env.prod run --rm migrate`

Expected: the `migrate` container exits `0`, prints a passing schema fingerprint,
and no application container starts before it completes.

- [ ] **Step 5: Record staging evidence without secrets.**

Create `docs/operations/migration-gate-g-2026-09-01.md` with the commit SHA,
UTC date, `migrate` exit code, fingerprint result, and `/healthz` plus `/ready`
HTTP statuses. Do not include DSNs, logs containing credentials, or `.env.prod`.

- [ ] **Step 6: Commit the staging evidence after the operator run.**

```bash
git add docs/operations/migration-gate-g-2026-09-01.md
git commit -m "docs(operations): record staging migration gate"
```
