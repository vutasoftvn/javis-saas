# Company Business Schema Cleanup (Plan B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Normalize how `services/company` business records reference identity/tenant — single canonical tenant key (`workspace_id`), single canonical actor key (`workforce_members.id`) — and remove dead/duplicate business schema (unused validation subsystem, ghost FK-less columns, a ~20-table legacy Python domain with zero runtime consumer).

**Architecture:** This is the follow-up to Plan A (`docs/superpowers/plans/2026-08-23-identity-foundation-plan-a.md`, already merged — COSA is sole credential authority, Company's `core.user_projections`/`core.workspaces`/`core.workspace_memberships`/`core.workforce_members` are the local projection). Plan B does not touch identity/auth — it touches how *business* tables (`operations`/`strategy`/`sales`/`commercial`/`finance-legal` schemas) key into that identity. Canonical tenant key = `workspace_id` (business rows never store `company_id` alongside it — `core.workspaces.platform_company_id` is the only place that mapping lives). Canonical actor key = `workforce_members.id` (renamed uniformly to `*_member_id`, since an actor may be human or AI agent — never `user_id`).

**Tech Stack:** TypeScript, Encore.ts, Drizzle ORM (Postgres), vitest (integration tests against a real dev Postgres via `encore test` — never mock the DB layer).

## Global Constraints

- Forward-only migrations (`*.up.sql`, no `.down.sql`) tracked in `public.schema_migrations` by `(service, filename)`. Run via `node scripts/migrate.mjs` from `services/company`, or `encore test` triggers it implicitly for the test DB — always run the explicit migrate step per task below regardless.
- No destructive DB reset, no dropping/recreating the dev database. All changes are additive/forward migrations on the existing dev DB.
- Tests are real integration tests against live Postgres, run via `encore test` (plain `vitest run` fails with `ENCORE_RUNTIME_LIB not set` — this repo's tests require the Encore runtime).
- Snowflake IDs: always insert via `generateSnowflake()` (returns `bigint`), never `Number()`/`parseInt()` a Snowflake ID string — pass strings straight into `BigInt()`.
- Vietnamese for comments explaining *why* (per repo convention); identifiers, error messages, code stay in English/as established.
- Every task must leave `encore test` green (in the touched service) and `npx tsc --noEmit -p .` free of *new* errors before moving to the next task. (Note: at plan-authoring time `services/company` already has ~18 pre-existing `tsc` errors in `operations/strategy`/`operations/tests` unrelated to this plan, from an in-flight Snowflake-ID migration on those files — not introduced by Plan A or Plan B. Don't try to fix those; just don't add new ones.)
- Migration file numbering (next free number per module at plan-authoring time): `operations/migrations/` → next is `10`; `commercial/migrations/` → next is `8`; `finance-legal/migrations/` → this plan only adds a migration that drops tables, next is `11`.

---

## Task 1: Delete `finance-legal.validation` subsystem

**Why:** `validation.service.ts`/`validation.handler.ts` (schema `validation.*`, 4 tables) has zero consumers besides its own test and one demo block in `golden-path.e2e.test.ts`. The real, canonical assumption→experiment→evidence→gate→decision chain is `operations/strategy` (already covered by `operations/strategy/tests/strategy-handlers.test.ts`). The Flutter "Validation Studio" tab does not call this subsystem either — it calls a dead legacy route (verified during Plan A design, see `docs/superpowers/specs/2026-08-23-identity-foundation-plan-a-design.md` Context section) — so deleting this is not a behavior change for any real client.

**Files:**
- Delete: `services/company/finance-legal/services/validation.service.ts`
- Delete: `services/company/finance-legal/handlers/validation.handler.ts`
- Delete: `services/company/finance-legal/tests/validation.test.ts`
- Modify: `services/company/finance-legal/handlers/index.ts` (drop the barrel export line)
- Modify: `services/company/shared/db/schema/finance-legal.ts` (remove 4 table exports + the `validationSchema` export if nothing else uses it)
- Modify: `services/company/shared/tests/golden-path.e2e.test.ts` (remove the validation-chain block, lines 24 and 257-278)
- Create: `services/company/finance-legal/migrations/11_drop_validation_domain.up.sql`

- [ ] **Step 1: Confirm current test baseline passes**

```bash
cd services/company && encore test 2>&1 | tail -5
```
Expected: `37 passed (37)` (or whatever the current green count is) — establish a clean baseline before deleting anything.

- [ ] **Step 2: Read `shared/db/schema/finance-legal.ts` in full and remove the 4 validation tables**

Delete these 4 exports entirely (they currently sit at lines 142-192 of that file, inside a `validationSchema = pgSchema("validation")` block — delete the `validationSchema` export too if grep confirms nothing else references it):
```ts
export const validationHypotheses = validationSchema.table("validation_hypotheses", { ... });
export const validationExperiments = validationSchema.table("validation_experiments", { ... });
export const evidenceItems = validationSchema.table("evidence_items", { ... });
export const customerInterviews = validationSchema.table("customer_interviews", { ... });
```
Verify nothing else in the file references `validationSchema`:
```bash
grep -n "validationSchema" services/company/shared/db/schema/finance-legal.ts
```
If the only remaining hit is the `export const validationSchema = pgSchema("validation");` declaration line itself, delete that line too.

- [ ] **Step 3: Write the drop migration**

```sql
-- services/company/finance-legal/migrations/11_drop_validation_domain.up.sql

-- finance-legal.validation subsystem (validation_hypotheses/validation_experiments/
-- evidence_items/customer_interviews) không có consumer thật ngoài chính test của nó —
-- operations/strategy (assumption -> experiment -> evidence -> gate -> decision) mới là
-- chain canonical. Xem docs/superpowers/specs/2026-08-23-identity-foundation-plan-a-design.md
-- mục "Plan B — Company Business Schema Cleanup" điểm 1.
DROP TABLE IF EXISTS validation.evidence_items;
DROP TABLE IF EXISTS validation.validation_experiments;
DROP TABLE IF EXISTS validation.customer_interviews;
DROP TABLE IF EXISTS validation.validation_hypotheses;
DROP SCHEMA IF EXISTS validation;
```
(Drop order matters: `evidence_items` and `validation_experiments` both FK into other validation tables — children before parents, same reasoning as any other FK-respecting drop.)

- [ ] **Step 4: Delete the service, handler, and test files**

```bash
git rm services/company/finance-legal/services/validation.service.ts \
       services/company/finance-legal/handlers/validation.handler.ts \
       services/company/finance-legal/tests/validation.test.ts
```

- [ ] **Step 5: Fix the barrel export**

Edit `services/company/finance-legal/handlers/index.ts`, remove the line:
```ts
export * from "./validation.handler";
```

- [ ] **Step 6: Fix `golden-path.e2e.test.ts`**

Remove line 24:
```ts
import { createHypothesis, createExperiment, createEvidence } from "../../finance-legal/handlers/validation.handler";
```
Remove the block at lines 257-278 (everything from `const hypothesis = await createHypothesis({` through the closing `expect(evidence.experimentId).toBe(experiment.id);`), so the test now ends right after the `recordFinanceSnapshot` assertion (`expect(snapshot.workspaceId).toBe(workspaceId);`) that currently precedes it, followed directly by the test's closing `});`.

- [ ] **Step 7: Run the migration**

```bash
cd services/company && node scripts/migrate.mjs
```
Expected: `11_drop_validation_domain.up.sql` applies with no error, recorded in `public.schema_migrations`.

- [ ] **Step 8: Run the full test suite**

```bash
encore test 2>&1 | tail -20
```
Expected: all remaining tests PASS, `identity/tests/helpers/test-session.test.ts`-style baseline count minus the deleted `validation.test.ts`'s tests.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "refactor(company): delete finance-legal.validation subsystem — operations/strategy is the canonical assumption/experiment/evidence chain"
```

---

## Task 2: Delete ghost fields `brain_id`, `mvp_stage_id`, `offering_id`

**Why:** These columns exist on 5 `operations.ts` tables but there is no `knowledge.brains` or `commercial.offerings` table backing them anywhere in the current schema, and grepping every service that reads/writes them (`initiative.service.ts`, `project.service.ts`, `twelve-week-year.service.ts`) confirms they are pure pass-through DTO fields — set from client input (when accepted at all) and echoed back, never filtered/joined/used in any business logic. `okr_cycles.mvp_stage_id` and `portfolios.brain_id` are not referenced by any service code at all — dead even at the application layer.

**Files:**
- Modify: `services/company/shared/db/schema/operations.ts` (remove `brainId`/`offeringId` from `initiatives`; `brainId`/`mvpStageId` from `okrCycles`; `brainId` from `twelveWeekCycles`, `portfolios`, `projects`)
- Modify: `services/company/operations/services/initiative.service.ts`
- Modify: `services/company/operations/services/project.service.ts`
- Modify: `services/company/operations/services/twelve-week-year.service.ts`
- Create: `services/company/operations/migrations/10_drop_ghost_fields.up.sql`

- [ ] **Step 1: Write the migration**

```sql
-- services/company/operations/migrations/10_drop_ghost_fields.up.sql

-- brain_id/mvp_stage_id/offering_id là ghost field: không có bảng owner
-- (knowledge.brains, commercial.offerings không tồn tại), chỉ được set/đọc
-- xuyên suốt như DTO pass-through, không dùng trong bất kỳ query/filter nào.
-- Xem docs/superpowers/specs/2026-08-23-identity-foundation-plan-a-design.md
-- mục "Plan B" điểm 2.
ALTER TABLE strategy.initiatives DROP COLUMN brain_id;
ALTER TABLE strategy.initiatives DROP COLUMN offering_id;
ALTER TABLE strategy.okr_cycles DROP COLUMN brain_id;
ALTER TABLE strategy.okr_cycles DROP COLUMN mvp_stage_id;
ALTER TABLE operating.twelve_week_cycles DROP COLUMN brain_id;
ALTER TABLE strategy.portfolios DROP COLUMN brain_id;
ALTER TABLE strategy.projects DROP COLUMN brain_id;
```

- [ ] **Step 2: Update `shared/db/schema/operations.ts`**

In `initiatives` (currently lines 6-18), remove the `brainId` and `offeringId` lines:
```ts
export const initiatives = strategySchema.table("initiatives", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }),
  title: text("title").notNull(),
  status: text("status").default("active").notNull(),
  ownerId: bigint("owner_id", { mode: "bigint" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});
```
In `okrCycles` (currently lines 68-80), remove the `brainId` and `mvpStageId` lines:
```ts
export const okrCycles = strategySchema.table("okr_cycles", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  name: text("name").notNull(),
  startDate: timestamp("start_date", { withTimezone: true }),
  endDate: timestamp("end_date", { withTimezone: true }),
  status: text("status").default("draft").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});
```
In `twelveWeekCycles` (currently lines 115-133), remove the `brainId` line (keep `projectId`, which is a real, still-referenced field — do not touch it).
In `portfolios` (currently lines 167-178), remove the `brainId` line.
In `projects` (currently lines 180-199), remove the `brainId` line.

- [ ] **Step 3: Update `initiative.service.ts`**

Remove `brainId`/`offeringId` from the `Initiative` interface (currently lines 10-19) and from `toInitiative`'s object literal (unnamed inline mapper at line ~29-38: it inlines the mapping directly, not via a named `toInitiative` helper — read the file to confirm current shape before editing). `CreateInitiativeParams` already does not accept `brainId`/`offeringId` as input (confirmed by reading the file), so no param-side change needed there.

- [ ] **Step 4: Update `project.service.ts`**

Remove `brainId?: string | null;` from the `Project` interface, `brainId?: string | number | null;` from `CreateProjectRequest`, the `brainId: row.brainId ? row.brainId.toString() : null,` line from `toProject`, and the `brainId: req.brainId ? BigInt(req.brainId) : null,` line from `createProjectService`'s insert `.values({...})`.

- [ ] **Step 5: Update `twelve-week-year.service.ts`**

Same shape as Step 4: remove `brainId?: string | null;` from the response interface, `brainId?: string | number | null;` from the create-request interface, the `brainId: row.brainId ? ... : null,` mapping line, and the `brainId: req.brainId ? BigInt(req.brainId) : null,` insert line.

- [ ] **Step 6: Verify no other references remain**

```bash
cd /Volumes/SSD/javis-saas
grep -rn "brainId\|mvpStageId\|offeringId" services/company --include="*.ts"
```
Expected: 0 results (no test file references these fields either, per earlier verification — confirm that grep is still 0).

- [ ] **Step 7: Run the migration and the full test suite**

```bash
cd services/company && node scripts/migrate.mjs && encore test 2>&1 | tail -20
```
Expected: migration applies cleanly, all tests PASS (`initiative.test.ts`, `project.test.ts`, `twelve-week-year.test.ts`, `okr.test.ts` don't construct these fields, per earlier grep — no test edits needed).

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "refactor(company): drop ghost fields brain_id/mvp_stage_id/offering_id — no backing table, never used in queries"
```

---

## Task 3: Workspace-resolver helper (`companyId` → `workspaceId`)

**Why:** Task 4 needs a single place that turns a client-supplied platform `companyId` into the canonical local `workspaceId` (via `core.workspaces.platform_company_id`), so 9 strategy handlers stop storing `company_id` redundantly next to `workspace_id`.

**Files:**
- Create: `services/company/shared/services/workspace-resolver.service.ts`
- Test: `services/company/shared/tests/workspace-resolver.test.ts`

**Interfaces:**
- Consumes: `identityWorkspaces` (schema, has `platformCompanyId: text("platform_company_id").unique()`), `db`/`schema` from `services/company/models/db` (actually `../../models/db` relative to `shared/services/`, per existing sibling files like `shared/services/snowflake.service.ts`).
- Produces: `resolveWorkspaceId(params: { workspaceId?: string | number; companyId?: string | number }): Promise<bigint>` — Task 4's 9 strategy handlers import this.

- [ ] **Step 1: Write the failing test**

```ts
// services/company/shared/tests/workspace-resolver.test.ts
import { describe, expect, it } from "vitest";
import { resolveWorkspaceId } from "../services/workspace-resolver.service";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { db, schema } from "../../models/db";
import { eq } from "drizzle-orm";

describe("resolveWorkspaceId", () => {
  it("returns the workspaceId directly when workspaceId is given", async () => {
    const session = await createTestSession({ displayName: "Resolver Direct Test" });
    const resolved = await resolveWorkspaceId({ workspaceId: session.workspaceId });
    expect(resolved).toBe(BigInt(session.workspaceId));
  });

  it("resolves companyId to workspaceId via core.workspaces.platform_company_id", async () => {
    const session = await createTestSession({ displayName: "Resolver Company Test" });
    const platformCompanyId = `plat-co-${Date.now()}`;
    await db
      .update(schema.identityWorkspaces)
      .set({ platformCompanyId })
      .where(eq(schema.identityWorkspaces.id, BigInt(session.workspaceId)));

    const resolved = await resolveWorkspaceId({ companyId: platformCompanyId });
    expect(resolved).toBe(BigInt(session.workspaceId));
  });

  it("throws notFound when companyId does not match any workspace projection", async () => {
    await expect(resolveWorkspaceId({ companyId: `no-such-company-${Date.now()}` })).rejects.toThrow();
  });

  it("throws invalidArgument when neither workspaceId nor companyId is given", async () => {
    await expect(resolveWorkspaceId({})).rejects.toThrow();
  });
});
```

- [ ] **Step 2: Run it to confirm it fails**

```bash
cd services/company && encore test workspace-resolver 2>&1 | tail -20
```
Expected: FAIL — `resolveWorkspaceId` / `workspace-resolver.service` doesn't exist yet.

- [ ] **Step 3: Write the implementation**

```ts
// services/company/shared/services/workspace-resolver.service.ts
import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../../models/db";

const { identityWorkspaces } = schema;

export interface ResolveWorkspaceIdParams {
  workspaceId?: string | number;
  companyId?: string | number;
}

// companyId (platform-side id) chỉ dùng để tra ra workspaceId local qua
// core.workspaces.platform_company_id — business row không lưu song song
// company_id + workspace_id (xem Plan B, nguyên tắc canonical tenant key).
export async function resolveWorkspaceId(params: ResolveWorkspaceIdParams): Promise<bigint> {
  if (params.workspaceId !== undefined && params.workspaceId !== null && params.workspaceId !== "") {
    return BigInt(params.workspaceId);
  }

  if (params.companyId === undefined || params.companyId === null || params.companyId === "") {
    throw APIError.invalidArgument("workspaceId hoặc companyId là bắt buộc");
  }

  const [ws] = await db
    .select({ id: identityWorkspaces.id })
    .from(identityWorkspaces)
    .where(eq(identityWorkspaces.platformCompanyId, String(params.companyId)))
    .limit(1);

  if (!ws) {
    throw APIError.notFound(`không tìm thấy workspace projection cho companyId ${params.companyId}`);
  }

  return ws.id;
}
```

- [ ] **Step 4: Run the test again**

```bash
encore test workspace-resolver 2>&1 | tail -20
```
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add services/company/shared/services/workspace-resolver.service.ts services/company/shared/tests/workspace-resolver.test.ts
git commit -m "feat(company): add resolveWorkspaceId helper — resolves platform companyId to local workspaceId via core.workspaces"
```

---

## Task 4: Dedupe `companyId`/`workspaceId` on the 11 `strategy.ts` tables

**Why:** `stagePolicies`, `stageTransitions`, `assumptions`, `experiments`, `evidence`, `interviews`, `discoverySignals`, `gateEvaluations`, `decisionRecords`, `nextActionCandidates`, `nextActionRankings` all store both `company_id` and `workspace_id` NOT NULL, with every handler requiring and echoing both. One handler (`next-best-action.handler.ts`) already writes `companyId: projectRow.workspaceId` — i.e., it fabricates a companyId value out of the workspaceId because it has no real companyId to put there, which is itself evidence the column is pure duplication. Canonical tenant key becomes `workspace_id` alone.

**Files:**
- Modify: `services/company/shared/db/schema/strategy.ts` (remove `companyId` from all 11 tables)
- Modify: `services/company/operations/strategy/handlers/experiment.handler.ts` (full rewrite — this task's fully-detailed template)
- Modify: `services/company/operations/strategy/handlers/stage-policy.handler.ts`, `stage-transition.handler.ts`, `assumption.handler.ts`, `evidence.handler.ts`, `interview.handler.ts`, `discovery-signal.handler.ts`, `gate-evaluation.handler.ts`, `decision-record.handler.ts` (same transform, applied per-file — Step 5)
- Modify: `services/company/operations/strategy/handlers/next-best-action.handler.ts` (smaller — only writes to `nextActionCandidates`/`nextActionRankings`, no client-facing companyId param)
- Modify: `services/company/operations/strategy/tests/deterministic-services.test.ts`, `execution-planning-chain.test.ts`, `strategy-handlers.test.ts` (drop `companyId` from constructed request objects)
- Create: `services/company/operations/migrations/11_dedupe_strategy_company_workspace_id.up.sql`

**Interfaces:**
- Consumes: `resolveWorkspaceId` from Task 3.

- [ ] **Step 1: Write the migration**

```sql
-- services/company/operations/migrations/11_dedupe_strategy_company_workspace_id.up.sql

-- Canonical tenant key trong Company DB = workspace_id duy nhất.
-- core.workspaces.platform_company_id là nơi duy nhất giữ mapping sang
-- COSA companyId — business row không lưu song song company_id +
-- workspace_id nữa. Xem Plan B, nguyên tắc canonical tenant key.
ALTER TABLE strategy.stage_policies DROP COLUMN company_id;
ALTER TABLE strategy.stage_transitions DROP COLUMN company_id;
ALTER TABLE strategy.assumptions DROP COLUMN company_id;
ALTER TABLE strategy.experiments DROP COLUMN company_id;
ALTER TABLE strategy.evidence DROP COLUMN company_id;
ALTER TABLE strategy.interviews DROP COLUMN company_id;
ALTER TABLE strategy.discovery_signals DROP COLUMN company_id;
ALTER TABLE strategy.gate_evaluations DROP COLUMN company_id;
ALTER TABLE strategy.decision_records DROP COLUMN company_id;
ALTER TABLE strategy.next_action_candidates DROP COLUMN company_id;
ALTER TABLE strategy.next_action_rankings DROP COLUMN company_id;
```

- [ ] **Step 2: Update `shared/db/schema/strategy.ts`**

Remove the `companyId: bigint("company_id", { mode: "bigint" }).notNull(),` line from all 11 table definitions (`stagePolicies`, `stageTransitions`, `assumptions`, `experiments`, `evidence`, `interviews`, `discoverySignals`, `gateEvaluations`, `decisionRecords`, `nextActionCandidates`, `nextActionRankings`) — every one currently has it as the line immediately after `id: bigint("id", ...).primaryKey(),`, immediately before `workspaceId: bigint("workspace_id", ...).notNull(),`. Leave every other column untouched.

- [ ] **Step 3: Rewrite `experiment.handler.ts` in full (the template for Step 5)**

Replace the full file content with:
```ts
import { api, APIError } from "encore.dev/api";
import { eq, and, isNull } from "drizzle-orm";
import { db, schema } from "../../models/db";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { resolveWorkspaceId } from "../../../shared/services/workspace-resolver.service";
import { EXPERIMENT_CREATED, makeDomainEvent } from "../../../shared/events";
import { rankAssumptions } from "../services/assumption-ranking.service";
import { proposeExperimentsForAssumptions } from "../services/experiment-proposal.service";

const { experiments, assumptions } = schema;

export interface Experiment {
  id: string;
  workspaceId: string;
  projectId: string;
  assumptionId: string | null;
  hypothesis: string;
  method: string;
  successCriteria: string;
  budget: number;
  ownerWorkforceMemberId: string | null;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface CreateExperimentParams {
  workspaceId?: string | number;
  companyId?: string | number;
  projectId: string;
  assumptionId?: string | number;
  hypothesis: string;
  method: string;
  successCriteria: string;
  budget?: number;
  ownerWorkforceMemberId?: string | number;
  status?: string;
}

export interface ListExperimentsParams {
  workspaceId?: string | number;
  companyId?: string | number;
  projectId?: string | number;
  status?: string;
}

export interface UpdateExperimentParams {
  hypothesis?: string;
  method?: string;
  successCriteria?: string;
  budget?: number;
  ownerWorkforceMemberId?: string | number;
  status?: string;
}

function toExperiment(row: typeof experiments.$inferSelect): Experiment {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    projectId: row.projectId.toString(),
    assumptionId: row.assumptionId ? row.assumptionId.toString() : null,
    hypothesis: row.hypothesis,
    method: row.method,
    successCriteria: row.successCriteria,
    budget: row.budget,
    ownerWorkforceMemberId: row.ownerWorkforceMemberId ? row.ownerWorkforceMemberId.toString() : null,
    status: row.status,
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  };
}

export const createExperiment = api(
  { method: "POST", path: "/operations/strategy/experiments", expose: true },
  async (params: CreateExperimentParams): Promise<Experiment> => {
    if (!params.projectId || !params.hypothesis || !params.method || !params.successCriteria) {
      throw APIError.invalidArgument("projectId, hypothesis, method, and successCriteria are required");
    }
    const workspaceId = await resolveWorkspaceId({ workspaceId: params.workspaceId, companyId: params.companyId });

    const [row] = await db
      .insert(experiments)
      .values({
        id: generateSnowflake(),
        workspaceId,
        projectId: BigInt(params.projectId),
        assumptionId: params.assumptionId ? BigInt(params.assumptionId) : null,
        hypothesis: params.hypothesis,
        method: params.method,
        successCriteria: params.successCriteria,
        budget: params.budget ?? 0.0,
        ownerWorkforceMemberId: params.ownerWorkforceMemberId ? BigInt(params.ownerWorkforceMemberId) : null,
        status: params.status ?? "draft",
      })
      .returning();

    if (!row) throw APIError.internal("failed to create experiment");

    const event = makeDomainEvent(EXPERIMENT_CREATED, {
      experimentId: row.id.toString(),
      projectId: row.projectId.toString(),
      assumptionId: row.assumptionId ? row.assumptionId.toString() : null,
      workspaceId: row.workspaceId.toString(),
    });
    console.log(`[DomainEvent] ${EXPERIMENT_CREATED}:`, JSON.stringify(event));

    return toExperiment(row);
  }
);

export const getExperiment = api(
  { method: "GET", path: "/operations/strategy/experiments/:id", expose: true },
  async ({ id }: { id: string }): Promise<Experiment> => {
    const [row] = await db
      .select()
      .from(experiments)
      .where(and(eq(experiments.id, BigInt(id)), isNull(experiments.deletedAt)))
      .limit(1);

    if (!row) throw APIError.notFound(`experiment with id ${id} not found`);
    return toExperiment(row);
  }
);

export const listExperiments = api(
  { method: "GET", path: "/operations/strategy/experiments", expose: true },
  async (params: ListExperimentsParams): Promise<{ items: Experiment[] }> => {
    const conditions = [isNull(experiments.deletedAt)];

    if (params.workspaceId || params.companyId) {
      const workspaceId = await resolveWorkspaceId({ workspaceId: params.workspaceId, companyId: params.companyId });
      conditions.push(eq(experiments.workspaceId, workspaceId));
    }
    if (params.projectId) {
      conditions.push(eq(experiments.projectId, BigInt(params.projectId)));
    }
    if (params.status) {
      conditions.push(eq(experiments.status, params.status));
    }

    const rows = await db
      .select()
      .from(experiments)
      .where(and(...conditions));

    return { items: rows.map(toExperiment) };
  }
);

export const updateExperiment = api(
  { method: "PATCH", path: "/operations/strategy/experiments/:id", expose: true },
  async ({ id, ...params }: UpdateExperimentParams & { id: string }): Promise<Experiment> => {
    const updateValues: Record<string, any> = { updatedAt: new Date() };
    if (params.hypothesis !== undefined) updateValues.hypothesis = params.hypothesis;
    if (params.method !== undefined) updateValues.method = params.method;
    if (params.successCriteria !== undefined) updateValues.successCriteria = params.successCriteria;
    if (params.budget !== undefined) updateValues.budget = params.budget;
    if (params.ownerWorkforceMemberId !== undefined) {
      updateValues.ownerWorkforceMemberId = params.ownerWorkforceMemberId ? BigInt(params.ownerWorkforceMemberId) : null;
    }
    if (params.status !== undefined) updateValues.status = params.status;

    const [row] = await db
      .update(experiments)
      .set(updateValues)
      .where(and(eq(experiments.id, BigInt(id)), isNull(experiments.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound(`experiment with id ${id} not found`);
    return toExperiment(row);
  }
);

export const deleteExperiment = api(
  { method: "DELETE", path: "/operations/strategy/experiments/:id", expose: true },
  async ({ id }: { id: string }): Promise<{ success: boolean }> => {
    const [row] = await db
      .update(experiments)
      .set({ deletedAt: new Date(), updatedAt: new Date() })
      .where(and(eq(experiments.id, BigInt(id)), isNull(experiments.deletedAt)))
      .returning();

    if (!row) throw APIError.notFound(`experiment with id ${id} not found`);
    return { success: true };
  }
);

export const proposeExperiments = api(
  { method: "GET", path: "/operations/strategy/projects/:projectId/proposed-experiments", expose: true },
  async ({ projectId }: { projectId: string }) => {
    const assumptionRows = await db
      .select()
      .from(assumptions)
      .where(and(eq(assumptions.projectId, BigInt(projectId)), isNull(assumptions.deletedAt)));

    const experimentRows = await db
      .select({ assumptionId: experiments.assumptionId })
      .from(experiments)
      .where(and(eq(experiments.projectId, BigInt(projectId)), isNull(experiments.deletedAt)));

    const rankedAssumptions = rankAssumptions(
      assumptionRows.map((r) => ({
        id: r.id.toString(),
        projectId: r.projectId.toString(),
        statement: r.statement,
        importance: r.importance,
        uncertainty: r.uncertainty,
        status: r.status,
      }))
    );

    const proposals = proposeExperimentsForAssumptions(
      rankedAssumptions,
      experimentRows.map((e) => ({ assumptionId: e.assumptionId ? e.assumptionId.toString() : null }))
    );

    return { items: proposals };
  }
);
```
Note the shape of the change versus the original: (1) `companyId` dropped from the `Experiment` output type and from `toExperiment`/every inline response mapping — replaced with a shared `toExperiment` helper to avoid repeating the mapping 4 times; (2) `CreateExperimentParams`/`ListExperimentsParams` keep `companyId` as an **optional** accepted input (backward compatible for callers still sending it) alongside `workspaceId`, both now optional at the type level, resolved via `resolveWorkspaceId`; (3) the domain event payload drops `companyId: row.companyId.toString()`, keeping only `workspaceId`.

- [ ] **Step 4: Run this one handler's tests to confirm the pattern works**

```bash
cd services/company && encore test strategy-handlers 2>&1 | tail -30
```
Expected: FAILS at this point — `strategy-handlers.test.ts` still constructs `CreateExperimentParams` objects with a `companyId` used for assertions, and the 8 sibling handler files still reference the now-deleted `experiments.companyId`/etc. columns won't compile yet for those files specifically, but `experiment.handler.ts` itself should type-check standalone. Don't chase full green yet — proceed to Step 5, then fix tests in Step 6.

- [ ] **Step 5: Apply the identical transform to the remaining 8 handler files**

For each of `stage-policy.handler.ts`, `stage-transition.handler.ts`, `assumption.handler.ts`, `evidence.handler.ts`, `interview.handler.ts`, `discovery-signal.handler.ts`, `gate-evaluation.handler.ts`, `decision-record.handler.ts` — read the file in full, then apply this exact set of changes (every one of these 8 files was verified at plan-authoring time to follow the identical `create`/`get`/`list`/`update`/`delete` API shape as `experiment.handler.ts` above, with `companyId`/`workspaceId` appearing 11-13 times per file in the same positions):

1. Add the import: `import { resolveWorkspaceId } from "../../../shared/services/workspace-resolver.service";`
2. In the output interface (e.g. `StagePolicy`, `StageTransition`, ...): delete the `companyId: string;` line.
3. In the `Create*Params` interface: change `companyId: string;` + `workspaceId: string;` (both required) to `companyId?: string | number;` + `workspaceId?: string | number;` (both optional).
4. In the `List*Params` interface: `companyId`/`workspaceId` stay optional as they already are — no change needed there.
5. In the required-field validation at the top of the `create*` handler (e.g. `if (!params.workspaceId || !params.companyId || !params.stageKey) { throw APIError.invalidArgument(...) }`): drop `!params.workspaceId || !params.companyId ||` from the condition and drop `companyId, workspaceId, and ` from the error message — keep every other required-field check in that same `if` unchanged.
6. Immediately after that validation, insert: `const workspaceId = await resolveWorkspaceId({ workspaceId: params.workspaceId, companyId: params.companyId });`
7. In the `.insert(...).values({...})` block: delete the `companyId: BigInt(params.companyId),` line; change `workspaceId: BigInt(params.workspaceId),` to `workspaceId,` (reusing the resolved local variable from step 6).
8. In every response object literal (`return { ... }` in `create`, `get`, `list`, `update` — there are 3-4 per file, all structurally identical to each other within one file): delete the `companyId: row.companyId.toString(),` line.
9. In the `list*` handler's filter-building block: change
   ```ts
   if (params.workspaceId) {
     conditions.push(eq(table.workspaceId, BigInt(params.workspaceId)));
   }
   if (params.companyId) {
     conditions.push(eq(table.companyId, BigInt(params.companyId)));
   }
   ```
   to:
   ```ts
   if (params.workspaceId || params.companyId) {
     const workspaceId = await resolveWorkspaceId({ workspaceId: params.workspaceId, companyId: params.companyId });
     conditions.push(eq(table.workspaceId, workspaceId));
   }
   ```
   (substitute the file's actual table variable name, e.g. `stagePolicies`, `assumptions`, `evidence`, etc.)
10. `decision-record.handler.ts` additionally has `actorWorkforceMemberId` — leave that field untouched in this task (Task 5 renames it).

After each file, verify with:
```bash
grep -n "companyId" services/company/operations/strategy/handlers/<file>.handler.ts
```
Expected: 0 results (every `companyId` reference removed — the field only survives as an optional *input* param name, which greps as `companyId` too, so re-check: the only acceptable remaining hits are the `companyId?: string | number;` lines in `Create*Params`/`List*Params` interfaces and the two `resolveWorkspaceId({ workspaceId: params.workspaceId, companyId: params.companyId })` call sites — everything else must be gone).

- [ ] **Step 6: Fix `next-best-action.handler.ts`**

This file doesn't accept `companyId` as a client param — it currently fabricates one (`companyId: projectRow.workspaceId, // using project workspace/company`) when inserting into `nextActionCandidates`/`nextActionRankings`. Delete both `companyId: projectRow.workspaceId,` lines (one in the `nextActionCandidates` insert, one in the `nextActionRankings` insert) — no replacement needed, `workspaceId: projectRow.workspaceId,` on the next line already carries the correct value.

- [ ] **Step 7: Fix the 3 strategy test files**

`operations/strategy/tests/deterministic-services.test.ts`, `execution-planning-chain.test.ts`, `strategy-handlers.test.ts`: read each file, and remove any `companyId: ...` line from object literals passed into `createStagePolicy`/`createExperiment`/`createAssumption`/etc. (the handlers still *accept* `companyId` as optional input per Step 5, so leaving it in would still compile and pass — but since none of these tests need cross-company-id resolution behavior, drop it to keep tests aligned with the new canonical shape: pass only `workspaceId`). Also remove any assertion of the form `expect(result.companyId).toBe(...)` — the field no longer exists on any response type.

- [ ] **Step 8: Run the migration and the full test suite**

```bash
cd services/company && node scripts/migrate.mjs && npx tsc --noEmit -p . 2>&1 | grep -v "operations/strategy/tests\|operations/tests\|operations/services/task.service.ts\|operations/strategy/handlers/stage-policy.handler.ts" && encore test 2>&1 | tail -30
```
(The `grep -v` filters out the pre-existing, unrelated Snowflake-ID-migration `tsc` errors noted in Global Constraints — anything that survives the filter is a *new* error this task introduced and must be fixed before continuing.)
Expected: filtered `tsc` output empty, `encore test` all PASS.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "refactor(company): dedupe companyId/workspaceId on 11 strategy tables — workspaceId is the sole canonical tenant key, companyId resolved at the API boundary via resolveWorkspaceId"
```

---

## Task 5: Actor naming standardization

**Why:** Business tables use 3 different names for the same concept (an actor that can be human or AI agent): `owner_id` (initiatives, okr_objectives, projects, and 5 `sales.*` tables), `owner_workforce_member_id` (experiments), `actor_workforce_member_id` (decision_records) — plus `tasks.assignee_id`, a dead column already superseded by `tasks.assignee_member_id`. Canonical name becomes `*_member_id` (`owner_member_id`, `assignee_member_id` — already correct on `tasks` —, `actor_member_id`), referencing `core.workforce_members.id`.

**Files:**
- Modify: `services/company/shared/db/schema/operations.ts` (`initiatives.ownerId`→`ownerMemberId`; `tasks.assigneeId` dropped entirely)
- Modify: `services/company/shared/db/schema/strategy.ts` (`experiments.ownerWorkforceMemberId`→`ownerMemberId`; `decisionRecords.actorWorkforceMemberId`→`actorMemberId`)
- Modify: `services/company/shared/db/schema/commercial.ts` (`ownerId`→`ownerMemberId` on `accounts`, `contacts`, `salesLeads`, `salesOpportunities`, `customers`)
- Modify: `services/company/operations/services/initiative.service.ts`, `operations/services/okr.service.ts`, `operations/services/project.service.ts`, `operations/services/task.service.ts`
- Modify: `services/company/operations/strategy/handlers/experiment.handler.ts`, `decision-record.handler.ts`
- Modify: `services/company/commercial/services/account.service.ts`, `contact.service.ts`, `lead.service.ts`, `customer.service.ts`, `opportunity.service.ts`
- Modify: `services/company/operations/strategy/tests/deterministic-services.test.ts` (line 168, `actorWorkforceMemberId: 5` → `actorMemberId: 5`)
- Create: `services/company/operations/migrations/12_actor_naming_standardization.up.sql`
- Create: `services/company/commercial/migrations/8_actor_naming_standardization.up.sql`

- [ ] **Step 1: Write the operations migration**

```sql
-- services/company/operations/migrations/12_actor_naming_standardization.up.sql

-- Canonical actor = workforce_members.id (có thể là human hoặc AI agent),
-- không dùng user_id cho business actor. Chuẩn hoá tên cột về *_member_id.
-- tasks.assignee_id là cột chết (đã bị thay bởi assignee_member_id từ
-- trước, không còn service nào ghi vào nó) — xoá luôn, không rename.
ALTER TABLE operating.tasks DROP COLUMN assignee_id;
ALTER TABLE strategy.initiatives RENAME COLUMN owner_id TO owner_member_id;
ALTER TABLE strategy.okr_objectives RENAME COLUMN owner_id TO owner_member_id;
ALTER TABLE strategy.projects RENAME COLUMN owner_id TO owner_member_id;
ALTER TABLE strategy.experiments RENAME COLUMN owner_workforce_member_id TO owner_member_id;
ALTER TABLE strategy.decision_records RENAME COLUMN actor_workforce_member_id TO actor_member_id;
```

- [ ] **Step 2: Write the commercial migration**

```sql
-- services/company/commercial/migrations/8_actor_naming_standardization.up.sql

-- Đồng bộ với operations/migrations/12: canonical actor field name là
-- *_member_id trên toàn bộ business schema.
ALTER TABLE sales.accounts RENAME COLUMN owner_id TO owner_member_id;
ALTER TABLE sales.contacts RENAME COLUMN owner_id TO owner_member_id;
ALTER TABLE sales.sales_leads RENAME COLUMN owner_id TO owner_member_id;
ALTER TABLE sales.sales_opportunities RENAME COLUMN owner_id TO owner_member_id;
ALTER TABLE sales.customers RENAME COLUMN owner_id TO owner_member_id;
```

- [ ] **Step 3: Update `shared/db/schema/operations.ts`**

In `initiatives`, change `ownerId: bigint("owner_id", { mode: "bigint" }),` to `ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),`.
In `tasks`, delete the line `assigneeId: bigint("assignee_id", { mode: "bigint" }),` entirely (keep `assigneeMemberId`/`ownerMemberId`, already correctly named, untouched).
In `okrObjectives`, change `ownerId: bigint("owner_id", { mode: "bigint" }),` to `ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),`.
In `projects`, change `ownerId: bigint("owner_id", { mode: "bigint" }),` to `ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),`.

- [ ] **Step 4: Update `shared/db/schema/strategy.ts`**

In `experiments`, change `ownerWorkforceMemberId: bigint("owner_workforce_member_id", { mode: "bigint" }),` to `ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),`.
In `decisionRecords`, change `actorWorkforceMemberId: bigint("actor_workforce_member_id", { mode: "bigint" }),` to `actorMemberId: bigint("actor_member_id", { mode: "bigint" }),`.

- [ ] **Step 5: Update `shared/db/schema/commercial.ts`**

In each of `accounts`, `contacts`, `salesLeads`, `salesOpportunities`, `customers`, change `ownerId: bigint("owner_id", { mode: "bigint" }),` to `ownerMemberId: bigint("owner_member_id", { mode: "bigint" }),`.

- [ ] **Step 6: Update `operations/services/initiative.service.ts`**

Rename every `ownerId` occurrence to `ownerMemberId`: the `Initiative` interface field, `CreateInitiativeParams`'s `ownerId?: string | number;` field, the response-mapping line, and the insert `.values({...})` line (`ownerId: params.ownerId ? BigInt(params.ownerId) : null,` → `ownerMemberId: params.ownerMemberId ? BigInt(params.ownerMemberId) : null,`).

- [ ] **Step 7: Update `operations/services/okr.service.ts`**

Same rename (`ownerId`→`ownerMemberId`) on the `Objective` interface, `CreateObjectiveParams`, `createObjectiveService`'s insert values, and its return object.

- [ ] **Step 8: Update `operations/services/project.service.ts`**

Same rename on the `Project` interface, `CreateProjectRequest`, `toProject`, and `createProjectService`'s insert values.

- [ ] **Step 9: Update `operations/services/task.service.ts`**

Delete `assigneeId: string | null;` from the `Task` interface and delete `assigneeId: row.assigneeId ? row.assigneeId.toString() : null,` from `toTask`. (`CreateTaskParams` never had `assigneeId` — nothing to remove there. `assigneeMemberId`/`ownerMemberId` are untouched — they're already correctly named.)

- [ ] **Step 10: Update `operations/strategy/handlers/experiment.handler.ts`**

Rename `ownerWorkforceMemberId` to `ownerMemberId` everywhere in the file rewritten in Task 4 Step 3: the `Experiment` interface, `CreateExperimentParams`, `UpdateExperimentParams`, `toExperiment`, the insert `.values({...})`, and the `updateExperiment` handler's conditional update block.

- [ ] **Step 11: Update `operations/strategy/handlers/decision-record.handler.ts`**

Read the file in full (not pasted here — Task 4 Step 5 already applied the `companyId`/`workspaceId` dedupe transform to this file, so read its *current* post-Task-4 state), then rename `actorWorkforceMemberId` to `actorMemberId` in every occurrence: the response interface, the create-params interface, any update-params interface, the insert values, and every response-object mapping.

- [ ] **Step 12: Update the 5 commercial services**

In each of `commercial/services/account.service.ts`, `contact.service.ts`, `lead.service.ts`, `customer.service.ts`, `opportunity.service.ts`: rename every `ownerId` occurrence to `ownerMemberId` (interface field, create-params field, response mapping, insert value) — same 4-occurrence shape confirmed at plan-authoring time for `account.service.ts`/`contact.service.ts`/`lead.service.ts`/`customer.service.ts`; `opportunity.service.ts` only has the interface field + response mapping (2 occurrences, no create-param/insert — read the file to confirm before editing, since it may not accept `ownerId` as creatable input).

Note: the corresponding handler files (`commercial/handlers/account.handler.ts` etc.) don't need edits — they `extend` the service's param interfaces (`export interface CreateAccountParams extends BaseCreateAccountParams`), so the rename in the service file propagates automatically.

- [ ] **Step 13: Fix `deterministic-services.test.ts`**

Change line 168, `actorWorkforceMemberId: 5,` to `actorMemberId: 5,`.

- [ ] **Step 14: Verify no stale references remain**

```bash
cd /Volumes/SSD/javis-saas
grep -rn "\bownerId\b\|ownerWorkforceMemberId\|actorWorkforceMemberId\|assigneeId\b" services/company --include="*.ts"
```
Expected: 0 results.

- [ ] **Step 15: Run both migrations and the full test suite**

```bash
cd services/company && node scripts/migrate.mjs && npx tsc --noEmit -p . 2>&1 | grep -v "operations/strategy/tests\|operations/tests\|operations/services/task.service.ts\|operations/strategy/handlers/stage-policy.handler.ts" && encore test 2>&1 | tail -30
```
Expected: both migrations apply cleanly (`operating.tasks.assignee_id` dropped, 7 columns renamed across `operations`/`commercial`), filtered `tsc` output empty, all tests PASS.

- [ ] **Step 16: Commit**

```bash
git add -A
git commit -m "refactor(company): standardize actor naming to *_member_id (owner_member_id/assignee_member_id/actor_member_id) — canonical actor is workforce_members.id, drop dead tasks.assignee_id"
```

---

## Task 6: Delete Policies/Regulations legacy domain (with requirement-capture note)

**Why:** `legacy/platform/platform_core/policy_funding/` (Python/SQLAlchemy) defines 20 tables (`policy_source_documents`, `policy_source_snapshots`, `policy_programs`, `policy_program_rounds`, `policy_eligibility_rules`, `project_stage_assessments`, `project_trl_assessments`, `project_funding_needs`, `project_program_matches`, `project_eligibility_evaluations`, `project_missing_requirements`, `policy_applications`, `policy_application_sections`, `project_funding_awards`, `project_compliance_obligations`, `project_cost_allocations`, `admin_policy_inboxes`, `policy_program_claims`, `policy_verifications`, `policy_change_proposals`) implementing a Vietnamese government startup-funding matching engine. Zero import from `services/company` or `services/cosa` (the only currently-running TypeScript services) — confirmed via repo-wide grep. Per CLAUDE.md rule 10 and this plan's own precedent (Plan A §10), delete-with-requirement-note rather than silent delete, so the business intent isn't lost.

**Files:**
- Create: `docs/architecture/POLICY_FUNDING_DOMAIN_REQUIREMENTS.md`
- Delete: `legacy/platform/platform_core/policy_funding/` (entire directory)

- [ ] **Step 1: Write the requirement-capture doc**

```markdown
# Policy Funding Domain — Requirement Capture (pre-deletion note)

**Ngày ghi nhận:** 2026-08-23. **Lý do:** domain này (`legacy/platform/platform_core/policy_funding/`,
20 bảng SQLAlchemy, không có consumer nào trong `services/company`/`services/cosa` — 2 service
TypeScript đang chạy thật) bị xoá theo Plan B (`docs/superpowers/plans/2026-08-23-company-business-schema-cleanup-plan-b.md`,
Task 6). Ghi lại đây trước khi xoá để không mất business intent nếu sau này cần port lại thật.

## Mục đích

Engine khớp nối (matching) startup Việt Nam với các chương trình hỗ trợ/tài trợ của chính phủ
(grant, voucher, tín dụng ưu đãi, hỗ trợ lãi suất...) — từ phát hiện nguồn văn bản pháp lý, đến
đánh giá điều kiện, nộp hồ sơ, giải ngân, và tuân thủ hậu tài trợ.

## Entity chính (nhóm theo luồng nghiệp vụ)

1. **Nguồn & xác minh chính sách:** `SourceDocument` (văn bản pháp lý gốc: luật, nghị định,
   thông tư, tài liệu hội thảo — có `verification_status` để phân biệt "nguồn nói gì" vs
   "COSA đã xác minh gì"), `SourceSnapshot` (snapshot nội dung thô phục vụ audit diff),
   `PolicyProgramClaim` (claim-based architecture: mệnh đề trích xuất từ tài liệu, tách biệt
   khỏi giá trị đã verify), `PolicyVerification` (nhật ký kiểm chứng bởi Founder/Admin),
   `AdminPolicyInbox` (hộp thư chính sách mới phát hiện chờ duyệt), `PolicyChangeProposal`
   (đề xuất thay đổi do AI phát hiện hoặc người đề xuất, chờ review trước khi áp dụng).
2. **Danh mục chương trình:** `PolicyProgram` (chương trình/quỹ/voucher/tín dụng — có target
   criteria: company_types, project_stages, trl_min, industries; financials: funding_min/max,
   matching_fund_pct, eligible_costs), `ProgramRound` (đợt tiếp nhận hồ sơ), `EligibilityRule`
   (quy tắc HARD/SOFT theo category LEGAL/TECH_TRL/FINANCIAL/IP/MARKET/TEAM, có field_path +
   operator để evaluate động).
3. **Đánh giá dự án:** `ProjectStageAssessment` (company_type + stage của project, có AI-suggested
   + founder-confirmed), `TrlAssessment` (TRL 1-9 hiện tại/mục tiêu, gắn evidence artifact),
   `FundingNeed` (nhu cầu vốn theo category CASH/CLOUD_CREDIT/INFRASTRUCTURE/VOUCHER/ADVISORY/IP_FILING).
4. **Matching & hồ sơ:** `ProjectProgramMatch` (kết quả khớp — 3 dimension riêng biệt:
   eligibility_status, match_score, readiness_score; pipeline_stage từ DISCOVERED đến COMPLETED),
   `EligibilityEvaluation` (chi tiết pass/fail từng rule), `MissingRequirement` (điều kiện/minh
   chứng còn thiếu, có thể link sang `operating.tasks` để founder xử lý trong 12WY),
   `Application` (hồ sơ ứng tuyển), `ApplicationSection` (từng phần thuyết minh: BACKGROUND,
   OBJECTIVES, TECHNOLOGY, TRL, OUTPUT_KPIS, WORK_PLAN, COMMERCIALIZATION, BUDGET, TEAM, IP, RISKS).
5. **Hậu tài trợ:** `FundingAward` (khoản đã duyệt/giải ngân — award_type, cash/non_cash,
   matching_required/actual), `ComplianceObligation` (nghĩa vụ báo cáo sau tài trợ),
   `CostAllocation` (phân bổ chi phí — mục đích chính: "Double Funding Guard", chống khai trùng
   chi phí giữa nhiều nguồn tài trợ khác nhau).

## Business rule quan trọng (nếu port lại, đừng bỏ sót)

- **Claim vs Verified tách biệt:** dữ liệu chính sách luôn đi qua 2 lớp — "nguồn tài liệu nói gì"
  (`PolicyProgramClaim`, `source_claim`, `claimed_values_jsonb`) và "COSA/founder đã xác minh gì"
  (`verification_status`, `PolicyVerification.result_status`). Không publish thẳng claim chưa
  verify vào matching catalog (`publish_to_matching` gate trên `PolicyProgram`).
- **3 dimension đánh giá match độc lập:** `eligibility_status` (đủ điều kiện cứng chưa),
  `match_score` (mức độ phù hợp), `readiness_score` (project đã sẵn sàng nộp hồ sơ chưa) —
  không gộp thành 1 điểm số duy nhất, vì founder cần biết "không đủ điều kiện" khác với
  "đủ điều kiện nhưng project chưa sẵn sàng".
- **Double Funding Guard:** `CostAllocation` tồn tại chuyên để cảnh báo một hạng mục chi phí
  (work_package + cost_category) bị khai trùng ở nhiều `FundingAward`/`Application` khác nhau —
  đây là yêu cầu compliance, không phải tiện ích phụ.
- **EligibilityRule là data-driven, không hardcode:** `field_path` + `operator` (GTE/LTE/EQ/IN/
  CONTAINS/EXISTS) + `expected_value_jsonb` cho phép thêm rule mới mà không cần deploy code —
  nếu port lại, giữ nguyên thiết kế này thay vì hardcode từng rule theo chương trình.

## Vì sao xoá thay vì port

Không có consumer nào ở `services/company`/`services/cosa` (2 service Encore.ts đang chạy thật) —
routers (`policy_catalog_router.py`, `admin_policy_router.py`, `application_router.py`,
`project_funding_router.py`) và services (`matching_service.py`, `proposal_service.py`,
`automation_service.py`) chỉ tồn tại trong `legacy/backend`, không được mount vào bất kỳ app
đang chạy nào. Nếu nhu cầu policy-funding-matching quay lại, port lại từ tài liệu này thay vì
từ code legacy — schema ở trên đã đủ để dựng lại từ đầu đúng ý định gốc.
```

- [ ] **Step 2: Confirm zero runtime consumer one more time (safety check before deleting)**

```bash
cd /Volumes/SSD/javis-saas
grep -rln "policy_funding" services/company services/cosa 2>/dev/null
```
Expected: 0 results — if anything appears, STOP and investigate before proceeding (do not delete).

- [ ] **Step 3: Delete the legacy directory**

```bash
git rm -r legacy/platform/platform_core/policy_funding/
```

- [ ] **Step 4: Commit**

```bash
git add docs/architecture/POLICY_FUNDING_DOMAIN_REQUIREMENTS.md
git commit -m "docs+chore: capture policy-funding domain requirements, then delete legacy/platform/platform_core/policy_funding (20 tables, zero runtime consumer)"
```

---

## Task 7: Final verification pass

**Files:** none (verification only)

- [ ] **Step 1: Run the migration from a clean checkout state**

```bash
cd services/company && node scripts/migrate.mjs
```
Expected: all 6 new migration files from this plan (`finance-legal/migrations/11_drop_validation_domain.up.sql`, `operations/migrations/10_drop_ghost_fields.up.sql`, `operations/migrations/11_dedupe_strategy_company_workspace_id.up.sql`, `operations/migrations/12_actor_naming_standardization.up.sql`, `commercial/migrations/8_actor_naming_standardization.up.sql`) recorded in `public.schema_migrations`, no errors.

- [ ] **Step 2: Run the full test suite**

```bash
encore test 2>&1 | tail -20
```
Expected: all PASS.

- [ ] **Step 3: Grep-verify Definition of Done**

```bash
cd /Volumes/SSD/javis-saas
echo "validation subsystem refs (expect 0):" && grep -rn "validationHypotheses\|validationExperiments\|evidenceItems\|customerInterviews" services/company --include="*.ts" | wc -l
echo "ghost fields (expect 0):" && grep -rn "brainId\|mvpStageId\|offeringId" services/company --include="*.ts" | wc -l
echo "strategy companyId column refs (expect 0, only optional param name survives — check manually if nonzero):" && grep -rn "\.companyId\b" services/company/operations/strategy --include="*.ts" | wc -l
echo "old actor field names (expect 0):" && grep -rn "\bownerId\b\|ownerWorkforceMemberId\|actorWorkforceMemberId\|assigneeId\b" services/company --include="*.ts" | wc -l
echo "policy_funding legacy dir (expect 0):" && find legacy/platform/platform_core/policy_funding -type f 2>/dev/null | wc -l
echo "requirement note exists (expect 1):" && ls docs/architecture/POLICY_FUNDING_DOMAIN_REQUIREMENTS.md 2>/dev/null | wc -l
```
Expected: every count matches its "expect" value.

- [ ] **Step 4: tsc sanity check**

```bash
cd services/company && npx tsc --noEmit -p . 2>&1 | grep -v "operations/strategy/tests\|operations/tests\|operations/services/task.service.ts\|operations/strategy/handlers/stage-policy.handler.ts"
```
Expected: empty output (no new errors introduced by Plan B; the pre-existing unrelated Snowflake-ID-migration errors noted in Global Constraints are filtered out).

- [ ] **Step 5: Final commit (if Step 3/4 surfaced any fixes) or close out**

If Steps 3-4 found no issues, no commit needed — Plan B is complete. If they did, fix, re-run Steps 1-4, then commit the fix with an appropriate message.

---

## Self-Review Notes (completed during plan authoring)

- **Spec coverage:** all 5 numbered items in `docs/superpowers/specs/2026-08-23-identity-foundation-plan-a-design.md`'s "Plan B — Company Business Schema Cleanup" section map to a task: item 1→Task 1, item 2→Task 2, item 3→Tasks 3-4, item 4→Task 5, item 5→Task 6. Task 7 is final verification, matching Plan A's own Task 13 precedent.
- **Placeholder scan:** no TBD/TODO. Task 4 Step 5 and Task 5 Steps 6-12 describe a mechanical transform applied identically across several files rather than pasting every file's full diff — this mirrors Plan A Task 5's treatment of 20 near-identical test files (scripted/mechanical + explicit before/after patterns + grep verification), and was chosen because all 8 remaining strategy handlers were verified byte-for-byte structurally identical to the fully-pasted `experiment.handler.ts` template at plan-authoring time (same `companyId`/`workspaceId` occurrence shape, confirmed via direct file reads of `stage-policy.handler.ts` in full and grep-counted occurrences in the other 7).
- **Type consistency:** `resolveWorkspaceId(params: { workspaceId?, companyId? }): Promise<bigint>` (Task 3) is the single signature every Task 4 handler and the Task 4 Step 5 recipe consumes — verified consistent. `ownerMemberId`/`assigneeMemberId`/`actorMemberId` naming (Task 5) is applied uniformly; `tasks.assigneeMemberId`/`tasks.ownerMemberId` (already existing, untouched) are not confused with the renamed `initiatives`/`okrObjectives`/`projects`/`experiments`/`decisionRecords`/commercial `ownerId`→`ownerMemberId` renames.
