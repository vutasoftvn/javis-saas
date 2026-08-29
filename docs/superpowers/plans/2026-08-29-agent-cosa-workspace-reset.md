# Agent, COSA, Workspace Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace development database and agent-platform names with `agent`,
`cosa`, and `workspace`, reset the empty development topology, and port the
missing Customer Engagement P0 service layer without merging the stale branch.

**Architecture:** PostgreSQL has three isolated databases owned by migration
roles and accessed by three DML-only app roles. `services/company` remains the
business-service boundary but uses `WORKSPACE_DATABASE_URL`. The Agent platform
moves to Python package/schema/database `agent`; COSA stays the control plane.
Customer Engagement P0 is ported service-by-service into the P1–P3 mainline.

**Tech Stack:** PostgreSQL 16, Docker Compose, Python 3.11/asyncpg/SQLAlchemy,
TypeScript/Encore/Drizzle/Vitest, FastAPI, Flutter.

**Spec:** `docs/superpowers/specs/2026-08-29-agent-cosa-workspace-naming-design.md`

## Global Constraints

- This is an empty development reset; do not copy data from old databases.
- Canonical runtime variables are `AGENT_DATABASE_URL`, `COSA_DATABASE_URL`,
  and `WORKSPACE_DATABASE_URL`; no retired runtime fallback exists.
- `workspace_id` remains the product-side tenant key.
- `services/company` remains a source/service name; only its database contract
  becomes `workspace`.
- Keep historical `docs/archive/**` unchanged.
- Do not merge `ce-p0`; port only tested P0 code that does not exist on `main`.
- Every production behavior change starts with a focused failing test.

---

### Task 1: Establish canonical configuration contracts

**Files:**
- Modify: `services/company/tests/db-url-resolution.test.ts`
- Modify: `services/cosa/tests/db-url-resolution.test.ts`
- Modify: `tests/apps/cosa/composition/test_agent_plane.py`
- Modify: `services/company/shared/db/client.ts`
- Modify: `services/cosa/storage/client.ts`
- Modify: `apps/cosa/composition/agent_plane.py`

**Interfaces:**
- Produces `resolveWorkspaceDatabaseUrl(): string`.
- Uses `AGENT_DATABASE_URL` for the Agent platform.
- Uses only `COSA_DATABASE_URL` for the COSA database.

- [ ] **Step 1: Write failing configuration tests**

```ts
it("resolves WORKSPACE_DATABASE_URL and rejects retired variables", () => {
  process.env.WORKSPACE_DATABASE_URL = "postgresql://workspace_app:x@db/workspace";
  process.env.COMPANY_DATABASE_URL = "postgresql://old:x@db/company";
  expect(resolveWorkspaceDatabaseUrl()).toContain("/workspace");
});
```

```py
def test_agent_plane_reads_agent_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_DATABASE_URL", "postgresql+asyncpg://agent_app:x@db/agent")
    assert build_cosa_agent_plane(...).repository is not None
```

- [ ] **Step 2: Run focused tests and confirm they fail because the canonical names are unsupported.**

Run: `cd services/company && npx vitest run tests/db-url-resolution.test.ts`

Run: `PYTHONPATH=. pytest tests/apps/cosa/composition/test_agent_plane.py -q`

- [ ] **Step 3: Implement the canonical resolvers and error messages.**

```ts
export function resolveWorkspaceDatabaseUrl(): string {
  const url = process.env.WORKSPACE_DATABASE_URL;
  if (!url) throw new Error("WORKSPACE_DATABASE_URL is required");
  return url;
}
```

```py
resolved_url = database_url or os.environ.get("AGENT_DATABASE_URL")
```

- [ ] **Step 4: Re-run focused tests, then Company and COSA typechecks.**

- [ ] **Step 5: Commit.**

### Task 2: Build a fresh three-database development topology

**Files:**
- Modify: `deploy/postgres/init/01-create-app-roles.sql`
- Modify: `docker-compose.yml`
- Modify: `services/docker-compose.yml`
- Modify: `.env.example`, `.env.e2e`, `.env.staging.example`
- Modify: `deploy/central_vps/.env.prod.example`, `deploy/central_vps/docker-compose.prod.yaml`
- Modify: `Makefile`, `scripts/check-dev-preflight.sh`, `scripts/load-dev-env.sh`
- Test: `tests/db_baseline_candidate/test_dev_bootstrap_contract.py`

**Interfaces:**
- PostgreSQL bootstrap creates `agent`, `cosa`, `workspace` and their app and
  migration roles.
- All external PostgreSQL ports bind to `127.0.0.1`.

- [ ] **Step 1: Write a failing bootstrap-contract test that requires the three exact database and role names.**

```py
def test_bootstrap_declares_only_canonical_data_planes(sql: str) -> None:
    assert "CREATE DATABASE agent" in sql
    assert "CREATE DATABASE cosa" in sql
    assert "CREATE DATABASE workspace" in sql
    assert "agent_app" in sql and "cosa_app" in sql and "workspace_app" in sql
```

- [ ] **Step 2: Run the test and confirm it fails against the old `javis`/`company`/`cosa_control_plane` bootstrap.**

- [ ] **Step 3: Implement idempotent role/database creation and least-privilege grants.**

```sql
CREATE ROLE agent_app LOGIN PASSWORD :'agent_app_password';
CREATE DATABASE agent OWNER agent_migrator;
REVOKE CONNECT ON DATABASE agent FROM PUBLIC;
GRANT CONNECT ON DATABASE agent TO agent_app, agent_migrator;
```

- [ ] **Step 4: Replace Compose and environment URLs with the same names; remove the public `5433` binding.**

- [ ] **Step 5: Run bootstrap-contract tests and `docker compose config --quiet` for dev and production Compose files.**

- [ ] **Step 6: Commit.**

### Task 3: Rename the reusable Agent package and persistence schema

**Files:**
- Move: `packages/agent_core/` → `packages/agent/`
- Move: `tests/agent_core/` → `tests/agent/`
- Modify: `pyproject.toml`, `Makefile`, `deploy/Dockerfile.migrate`,
  `deploy/central_vps/Dockerfile.migrate`, `scripts/run-agent-core-migrations.sh`
- Modify: every active Python import `agent_core.*` → `agent.*`
- Modify: `packages/agent/migrations/*.sql` and repository SQL from
  `agent_core.` → `agent.`
- Test: `tests/agent/scripts/test_migrate.py`

**Interfaces:**
- Python imports resolve from `agent.*`.
- `python -m packages.agent.scripts.migrate` migrates database `agent`.
- The primary persistent schema is `agent`.

- [ ] **Step 1: Add failing migration and import tests for package `agent`, schema `agent`, and `AGENT_DATABASE_URL`.**

```py
def test_sorted_migrations_create_agent_schema(migrations_dir: Path) -> None:
    assert "CREATE SCHEMA IF NOT EXISTS agent" in (migrations_dir / "001_canonical_agent_core_schema.sql").read_text()
```

- [ ] **Step 2: Run those tests and confirm they fail before moving the package or changing SQL.**

- [ ] **Step 3: Move package/test directories with Git, mechanically update active imports and Python tooling, then change schema-qualified SQL.**

- [ ] **Step 4: Update migration runner service name to `agent`, use advisory lock, and keep checksum behavior.**

```py
await conn.execute("SELECT pg_advisory_lock(hashtext('agent:migrations'))")
try:
    await apply_migrations(...)
finally:
    await conn.execute("SELECT pg_advisory_unlock(hashtext('agent:migrations'))")
```

- [ ] **Step 5: Run focused migration/import tests, `ruff`, `mypy`, and the Agent unit suite.**

- [ ] **Step 6: Commit.**

### Task 4: Make COSA and Workspace migrations deterministic

**Files:**
- Modify: `services/cosa/scripts/migrate.mjs`
- Modify: `services/company/scripts/migrate.mjs`
- Modify: `services/company/**/db.ts`
- Modify: `services/company/vitest.config.ts`, `services/cosa/vitest.config.ts`
- Test: `services/company/tests/db-url-resolution.test.ts`,
  `services/cosa/tests/db-url-resolution.test.ts`

**Interfaces:**
- Company migrations use `WORKSPACE_DATABASE_URL`; COSA uses
  `COSA_DATABASE_URL`.
- Migration execution takes a database advisory lock.
- Equal numeric migration prefixes sort deterministically by filename.

- [ ] **Step 1: Add failing unit tests for canonical runner URL resolution and tie-break ordering.**
- [ ] **Step 2: Verify the tests fail under the legacy aliases and unordered comparator.**
- [ ] **Step 3: Implement canonical URLs, `pg_advisory_lock`, and `numericPrefix || localeCompare` ordering.**
- [ ] **Step 4: Run Company/COSA migration tests and typechecks.**
- [ ] **Step 5: Commit.**

### Task 5: Port Customer Engagement P0 into the P1–P3 mainline

**Files:**
- Add/adapt from `ce-p0`: `thread.service.ts`, `thread-state.ts`,
  `sla.service.ts`, `message.service.ts`, `assignment.service.ts`,
  `escalation.service.ts`, `decision-authority.service.ts`,
  `decision-request-state.ts`, `decision-request.service.ts`,
  `customer360.service.ts`, `identity-resolution.service.ts`
- Add: `services/company/commercial/handlers/customer-engagement/desk.handler.ts`
- Modify: `services/company/commercial/handlers/customer-engagement/index.ts`
- Modify: `services/company/commercial/db.ts` and
  `services/company/shared/db/schema/customer-engagement.ts` only when the
  current P1–P3 schema needs an explicit compatible field.
- Add/adapt P0 tests under `services/company/commercial/tests/customer-engagement/`

**Interfaces:**
- Human-desk endpoints manage thread, message, assignment and decision flows.
- All reads and mutations require authenticated workspace context.
- P1–P3 channel, copilot, automation and autopilot behavior remains unchanged.

- [ ] **Step 1: Port one failing thread lifecycle test and run it against `main`.**

```ts
it("opens a workspace-scoped thread with an immutable SLA snapshot", async () => {
  const thread = await openThread({ inboxId, correlationId }, ctx);
  expect(thread.workspaceId).toBe(ctx.workspaceId);
  expect(thread.slaSnapshot).toBeDefined();
});
```

- [ ] **Step 2: Implement only `thread-state`, SLA and thread lifecycle until the test passes.**
- [ ] **Step 3: Repeat red-green cycles for messages, assignment/takeover,
  escalation, decision authority, customer-360 and identity resolution.**
- [ ] **Step 4: Add handlers using existing `requireWorkspaceAccess` and
  `APIError`, including cross-workspace denial tests.**
- [ ] **Step 5: Run all Customer Engagement tests together, then Company typecheck.**
- [ ] **Step 6: Commit.**

### Task 6: Reset and verify the empty development databases

**Files:**
- Modify if needed: `scripts/dev-reset-databases.sh`
- Modify: `README.md`, `services/README.md`, `docs/operations/migrations.md`,
  `docs/operations/deployment.md`, `docs/operations/secrets.md`
- Test: `tests/scripts/test_check_dev_preflight.sh`

**Interfaces:**
- A reset command targets only named development volumes and starts a fresh
  canonical topology.
- All active operational docs give `agent`, `cosa`, `workspace` URLs.

- [ ] **Step 1: Add a failing dry-run test that rejects unnamed/broad volume targets.**
- [ ] **Step 2: Implement the reset script with explicit Docker volume names,
  `--dry-run`, preflight confirmation, and no recursive filesystem deletion.**
- [ ] **Step 3: Run a dry-run, then use the user-authorized empty-dev reset to
  recreate only the validated PostgreSQL volumes.**
- [ ] **Step 4: Run all three migration runners against the fresh cluster and
  check their schema fingerprints.**
- [ ] **Step 5: Update active operational documentation and generated
  inventories, leaving `docs/archive/**` unchanged.**
- [ ] **Step 6: Commit.**

### Task 7: Final verification and migration-quality closure

**Files:**
- Modify only generated artifacts that their check commands report stale.
- Test: affected Agent, COSA, Company and Customer Engagement suites.

- [ ] **Step 1: Run `git diff --check`, contract generation check, route
  inventory check, Company usage inventory check, and all targeted tests.**
- [ ] **Step 2: Run Python lint/mypy, TypeScript typechecks, Flutter analysis,
  migration compatibility check and the fresh-schema fingerprint check.**
- [ ] **Step 3: Record unrelated pre-existing failures separately; fix every
  failure introduced by this change.**
- [ ] **Step 4: Commit the final verified implementation.**
