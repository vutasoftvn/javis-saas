# Maintainable MVP Company Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Company-owned Strategy, Runtime, and Marketing MVP capabilities typed, truthful, and maintainable by splitting application orchestration from domain contracts and persistence adapters inside the existing Company service.

**Architecture:** Keep `services/company` as one deployable owner. Introduce narrow application use-case modules that depend on domain ports; retain Encore handlers as HTTP adapters and Drizzle/Postgres code as infrastructure. Migrate a handler only when its contract test and owner-route test are green. No Agent record becomes Company data and no Company record becomes Agent data.

**Tech Stack:** TypeScript, Encore, Drizzle/PostgreSQL, Vitest, existing Company migrations and contract tests.

**Spec:** `docs/superpowers/specs/2026-08-31-maintainable-modular-truthful-mvp-design.md`

**Depends on:** Foundation Tasks 1–4 from `2026-08-31-maintainable-mvp-foundation.md`.

## Global Constraints

- Read and obey the master plan and Foundation plan before this plan. Use the strict `ApiResult` and generated surface contract; do not create a one-off response wrapper.
- Existing Company migrations are immutable. A new migration is permitted only for new durable Company-owned data, with up/down scripts and isolated apply/rollback/reapply evidence.
- A Runtime source status is evidence-based. `healthy`, `degraded`, or `unavailable` needs an observed result and timestamp; otherwise return `not_observed` with no invented timestamp/evidence ref.
- A human-readable label built from system mechanics must be `{ origin: "system_derived", ... }`; it must never claim to be Agent- or user-authored content.
- `TenantContext.workforceMemberId` is the member identity. Do not add `memberId` aliases or rely on browser workspace IDs for authorization.
- Do not move a file merely to lower its line count. Each extraction needs a port/use-case contract and a direct test.

## Target module map

```text
services/company/
  operations/
    domain/
      runtime-observation.ts
      canvas.ts
    application/
      canvas/{canvas-query.ts,canvas-command.ts,canvas.port.ts}
      runtime/{runtime-overview-query.ts,runtime-signal-projector.ts,runtime-observation.port.ts}
    infrastructure/
      canvas/drizzle-canvas.repository.ts
      runtime/drizzle-runtime-observation.repository.ts
    handlers/                         # HTTP/Encore adapters only
  commercial/
    domain/marketing/{marketing-context.ts,marketing-evidence.ts,marketing.port.ts}
    application/marketing/{context-query.ts,context-command.ts,experiment-command.ts}
    infrastructure/marketing/drizzle-marketing.repository.ts
    handlers/                         # HTTP/Encore adapters only
```

The precise filename may change only when an existing same-purpose module already exists. Preserve this direction of dependencies: `handler -> application -> domain port <- infrastructure`; no domain module imports Encore, Drizzle, HTTP, or an Agent package.

## Task 1: Establish compile-time Company module boundaries

**Files:**

- Create: `services/company/operations/domain/runtime-observation.ts`
- Create: `services/company/operations/application/runtime/runtime-observation.port.ts`
- Create: `services/company/operations/application/canvas/canvas.port.ts`
- Create: `services/company/commercial/domain/marketing/marketing.port.ts`
- Create: `scripts/check_company_boundaries.mjs`
- Modify: `Makefile`
- Modify: `.github/workflows/quality.yml`
- Test: `services/company/operations/tests/module-boundaries.test.ts`
- Test: `services/company/commercial/tests/module-boundaries.test.ts`

**Interfaces:**

```ts
export interface RuntimeObservation {
  readonly sourceKind: "company" | "agent";
  readonly status: "healthy" | "degraded" | "unavailable" | "not_observed";
  readonly observedAt: Date | null;
  readonly evidenceRef: string | null;
}

export interface RuntimeObservationPort {
  latest(workspaceId: string, sourceKind: RuntimeObservation["sourceKind"]): Promise<RuntimeObservation | null>;
}
```

- [ ] **Step 1: Write the failing dependency-direction tests.**

  The Operations fixture must prove a domain file importing `encore.dev/*`, Drizzle, HTTP, or `packages/agent` is rejected. The Commercial fixture must prove an application file importing a handler is rejected. Confirm a valid `application -> domain` and `infrastructure -> domain` fixture passes.

  Run:

  ```bash
  cd services/company && npx vitest run operations/tests/module-boundaries.test.ts commercial/tests/module-boundaries.test.ts
  ```

  Expected: FAIL because the scanner and module contracts do not exist.

- [ ] **Step 2: Define only domain/port contracts and scanner.**

  `runtime-observation.ts` must use the exact states above and expose no status default. Canvas and Marketing ports must accept `workspaceId: string`, actor/member identity where a command needs it, and Snowflake identifiers as `string`. The scanner resolves local imports and fails on invalid direction; it scans handwritten source only, excluding tests and generated output.

- [ ] **Step 3: Wire the Company boundary check.**

  Add:

  ```make
  company-boundary-check:
	 node scripts/check_company_boundaries.mjs
  ```

  Add the target to the quality workflow. It may initially scan only newly created `domain`, `application`, and `infrastructure` directories; it must not falsely assert legacy files have already been migrated.

- [ ] **Step 4: Run proof and commit.**

  Run:

  ```bash
  cd services/company && npx vitest run operations/tests/module-boundaries.test.ts commercial/tests/module-boundaries.test.ts
  make company-boundary-check
  cd services/company && npx tsc --noEmit
  ```

  Expected: PASS.

  ```bash
  git add services/company/operations/domain/runtime-observation.ts services/company/operations/application/runtime/runtime-observation.port.ts services/company/operations/application/canvas/canvas.port.ts services/company/commercial/domain/marketing/marketing.port.ts scripts/check_company_boundaries.mjs Makefile .github/workflows/quality.yml services/company/operations/tests/module-boundaries.test.ts services/company/commercial/tests/module-boundaries.test.ts
  git commit -m "test(company): enforce internal module boundaries"
  ```

## Task 2: Strangle the Strategy Canvas orchestration into typed use cases

**Files:**

- Create: `services/company/operations/domain/canvas.ts`
- Create: `services/company/operations/application/canvas/canvas-query.ts`
- Create: `services/company/operations/application/canvas/canvas-command.ts`
- Create: `services/company/operations/infrastructure/canvas/drizzle-canvas.repository.ts`
- Modify: `services/company/operations/services/canvas.service.ts`
- Modify: `services/company/operations/handlers/canvas.handler.ts`
- Modify: `services/company/operations/handlers/okr.handler.ts` only to consume the Canvas public use case where it currently duplicates Canvas persistence
- Test: `services/company/operations/tests/canvas.contract.test.ts`
- Test: `services/company/operations/tests/canvas.tenant-isolation.test.ts`
- Test: `services/company/operations/tests/canvas-use-case.test.ts`

**Interfaces:**

```ts
export interface CanvasRepository extends CanvasReadPort, CanvasWritePort {}

export interface ListCanvasInput {
  workspaceId: string;
  actorId: string;
}

export interface CanvasQuery {
  list(input: ListCanvasInput): Promise<CanvasReadModel>;
}
```

`CanvasReadModel` must preserve the existing generated MVP response fields and their truth states. It must not expose a Drizzle row or `Record<string, unknown>` as the handler response.

- [ ] **Step 1: Inventory actual Canvas handler callers and freeze response compatibility.**

  Run:

  ```bash
  rg -n "canvas\.service|CanvasService|canvas.*handler" services/company/operations services/company -g '*.ts'
  rg -n 'strategy\.canvas' shared/contracts/mvp-surface.json docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  ```

  Add contract assertions for fields, source-state behavior, string IDs, authorization failures, and empty-but-success responses. Do not add assertions for invented examples.

- [ ] **Step 2: Write failing use-case tests through an in-test port stub.**

  Cover: correct workspace forwarded unchanged; tenant mismatch denied; an empty repository result renders contract-declared `data_state: empty`; and a repository failure becomes an explicit owner error. The stub may return test fixtures but no production source may import it.

  Run: `cd services/company && npx vitest run operations/tests/canvas-use-case.test.ts`

  Expected: FAIL before the use case exists.

- [ ] **Step 3: Extract read/write mapping in three constrained moves.**

  1. Move Canvas domain vocabulary and read models into `domain/canvas.ts`; no database code.
  2. Move all Drizzle queries/mapping into `drizzle-canvas.repository.ts`, returning typed records and preserving error identity.
  3. Have `canvas-query.ts` and `canvas-command.ts` own authorization-aware orchestration; leave `canvas.service.ts` as a deprecated delegating compatibility facade until `rg` shows no callers. Handler accepts/parses HTTP and delegates only.

  Do not migrate Projects, Portfolios, Lifecycle, templates, or Twelve Week logic just because they share the legacy service. Give each its own later port after the Canvas vertical slice is green.

- [ ] **Step 4: Verify behavior, types, and legacy facade scope.**

  Run:

  ```bash
  cd services/company && npx vitest run operations/tests/canvas.contract.test.ts operations/tests/canvas.tenant-isolation.test.ts operations/tests/canvas-use-case.test.ts
  cd services/company && npx tsc --noEmit
  rg -n "CanvasService|canvas\.service" services/company/operations -g '*.ts'
  ```

  Expected: tests/types pass; every remaining legacy-facade caller is listed in the acceptance ledger under `legacy_callers`.

- [ ] **Step 5: Commit the vertical slice.**

  ```bash
  git add services/company/operations/domain/canvas.ts services/company/operations/application/canvas services/company/operations/infrastructure/canvas services/company/operations/services/canvas.service.ts services/company/operations/handlers/canvas.handler.ts services/company/operations/handlers/okr.handler.ts services/company/operations/tests/canvas.contract.test.ts services/company/operations/tests/canvas.tenant-isolation.test.ts services/company/operations/tests/canvas-use-case.test.ts docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "refactor(company): isolate canvas application boundary"
  ```

## Task 3: Make Workspace Runtime a truthful observation projection

**Files:**

- Create: `services/company/operations/application/runtime/runtime-overview-query.ts`
- Create: `services/company/operations/application/runtime/runtime-signal-projector.ts`
- Create: `services/company/operations/infrastructure/runtime/drizzle-runtime-observation.repository.ts`
- Modify: `services/company/operations/services/workspace-runtime.service.ts`
- Modify: `services/company/operations/handlers/workspace-runtime.handler.ts`
- Test: `services/company/operations/tests/workspace-runtime-observation.test.ts`
- Test: `services/company/operations/tests/workspace-runtime.tenant-isolation.test.ts`

**Interfaces:**

```ts
export interface RuntimePresentation {
  readonly id: string;
  readonly title: string;
  readonly titleOrigin: "source" | "system_derived";
  readonly description: string | null;
  readonly descriptionOrigin: "source" | "system_derived" | null;
  readonly observations: readonly RuntimeObservation[];
}
```

- [ ] **Step 1: Write failing truth-state tests.**

  Cover each source independently:

  - no recorded observation returns `not_observed`, `observedAt: null`, `evidenceRef: null`;
  - an actual successful health/signal record returns its stored status, timestamp, and evidence reference;
  - a recorded error returns `degraded`/`unavailable`, never `healthy`;
  - a correlation-derived presentation title is explicitly `system_derived` and cannot masquerade as a task description;
  - cross-workspace signal evidence is never returned.

  Run: `cd services/company && npx vitest run operations/tests/workspace-runtime-observation.test.ts operations/tests/workspace-runtime.tenant-isolation.test.ts`

  Expected: FAIL because the existing service emits `HEALTHY` and current time for sources it has not observed.

- [ ] **Step 2: Reuse the existing immutable runtime signal store.**

  `services/company/shared/db/schema/operations.ts::runtimeSourceSignals` and migration `33_mvp_strategy_canvas_runtime` already persist `workspace_id`, `source_kind`, `source_id`, source `state`, `observed_at`, `correlation_id`, and `payload_hash`. Build the repository on this table. Its durable evidence reference is `operating.runtime_source_signals:<id>`; do not add a parallel observations table, index, or migration in this task.

- [ ] **Step 3: Replace fabricated projection logic with stored observations.**

  Implement repository reads and projector mapping. Remove every `new Date()` used to fill an unobserved source, every unconditional health status, and labels/descriptions that imply data absent from the source signal. Use the declared `workforceMemberId` contract. The HTTP handler may assemble an envelope but cannot derive business/source state itself.

- [ ] **Step 4: Verify migration, handler contract, and Company type check.**

  Run:

  ```bash
  cd services/company && npx vitest run operations/tests/workspace-runtime-observation.test.ts operations/tests/workspace-runtime.tenant-isolation.test.ts operations/tests/mvp-canvas-runtime.test.ts
  cd services/company && npx vitest run operations/tests/mvp-runtime.test.ts
  cd services/company && npx tsc --noEmit
  rg -n "HEALTHY|new Date\(\)|Agent Action Required" services/company/operations/services/workspace-runtime.service.ts services/company/operations/application/runtime
  ```

  Expected: all tests/types pass; the last scan has no unobserved-source fallback.

- [ ] **Step 5: Update ledger and commit.**

  ```bash
  git add services/company/operations/domain/runtime-observation.ts services/company/operations/application/runtime services/company/operations/infrastructure/runtime services/company/operations/services/workspace-runtime.service.ts services/company/operations/handlers/workspace-runtime.handler.ts services/company/operations/tests/workspace-runtime-observation.test.ts services/company/operations/tests/workspace-runtime.tenant-isolation.test.ts docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "fix(company): project runtime from observed source state"
  ```

## Task 4: Split Marketing context orchestration from its persistence and HTTP adapter

**Files:**

- Create: `services/company/commercial/domain/marketing/marketing-context.ts`
- Create: `services/company/commercial/domain/marketing/marketing-evidence.ts`
- Create: `services/company/commercial/application/marketing/context-query.ts`
- Create: `services/company/commercial/application/marketing/context-command.ts`
- Create: `services/company/commercial/application/marketing/experiment-command.ts`
- Create: `services/company/commercial/infrastructure/marketing/drizzle-marketing.repository.ts`
- Modify: `services/company/commercial/services/marketing-context.service.ts`
- Modify: `services/company/commercial/services/marketing-mvp.service.ts`
- Modify: `services/company/commercial/handlers/marketing-context.handler.ts`
- Modify: `services/company/commercial/handlers/marketing-mvp.handler.ts`
- Test: `services/company/commercial/tests/marketing-use-case.test.ts`
- Test: `services/company/commercial/tests/marketing-mvp.contract.test.ts`
- Test: `services/company/commercial/tests/marketing.tenant-isolation.test.ts`

**Interfaces:**

```ts
export interface MarketingContextRepository {
  read(workspaceId: string): Promise<MarketingContextRecord | null>;
  save(input: SaveMarketingContextInput): Promise<MarketingContextRecord>;
}

export interface MarketingContextQuery {
  get(input: { workspaceId: string; actorId: string }): Promise<MarketingContextReadModel>;
}
```

- [ ] **Step 1: Capture the service’s current responsibilities and write failing use-case tests.**

  Enumerate every export of `marketing-context.service.ts` and `marketing-mvp.service.ts` as read, command, mapping, persistence, or HTTP concern. Tests must cover empty source data as `data_state: empty`, persisted evidence with its true timestamp/reference, rejected foreign-workspace access, and a persistence failure as an explicit error. Do not introduce sample campaign metrics.

  Run: `cd services/company && npx vitest run commercial/tests/marketing-use-case.test.ts`

  Expected: FAIL before application modules exist.

- [ ] **Step 2: Extract domain types and repository port first.**

  Move validation-independent Marketing context/evidence vocabulary into `domain/marketing`. Preserve nullable facts as nullable; do not use `||` to invent names, dates, owners, or metric values. Repository methods return typed records, not `any` or raw Drizzle results.

- [ ] **Step 3: Move one use case at a time.**

  In this order: context read, context update, experiment command, then MVP aggregate read. Each use case performs authorization/context validation, calls the port, and maps known empty source data to `empty`. Existing service exports delegate during transition. Handlers parse request/emit response and have no SQL or cross-context composition logic.

- [ ] **Step 4: Prove behavior and structural separation.**

  Run:

  ```bash
  cd services/company && npx vitest run commercial/tests/marketing-use-case.test.ts commercial/tests/marketing-mvp.contract.test.ts commercial/tests/marketing.tenant-isolation.test.ts commercial/tests/mvp-marketing.test.ts
  cd services/company && npx tsc --noEmit
  make company-boundary-check
  rg -n "\bany\b|as any|new Date\(\).*observed" services/company/commercial/application services/company/commercial/domain services/company/commercial/infrastructure
  ```

  Expected: tests/types/boundary pass and final scan has no forbidden `any`/invented observation timestamps. Correct a real untyped boundary rather than excluding it from the scan.

- [ ] **Step 5: Commit and record migration state.**

  ```bash
  git add services/company/commercial/domain/marketing services/company/commercial/application/marketing services/company/commercial/infrastructure/marketing services/company/commercial/services/marketing-context.service.ts services/company/commercial/services/marketing-mvp.service.ts services/company/commercial/handlers/marketing-context.handler.ts services/company/commercial/handlers/marketing-mvp.handler.ts services/company/commercial/tests/marketing-use-case.test.ts services/company/commercial/tests/marketing-mvp.contract.test.ts services/company/commercial/tests/marketing.tenant-isolation.test.ts docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "refactor(company): modularize marketing mvp application layer"
  ```

## Task 5: Remove only proven-dead Company compatibility facades

**Files:**

- Modify/Delete only after scans are empty: `services/company/operations/services/canvas.service.ts`
- Modify/Delete only after scans are empty: `services/company/commercial/services/marketing-context.service.ts`
- Modify/Delete only after scans are empty: `services/company/commercial/services/marketing-mvp.service.ts`
- Modify: caller files found by Step 1
- Modify: `docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md`
- Test: existing Canvas/Runtime/Marketing tests

- [ ] **Step 1: Create a caller inventory.**

  Run:

  ```bash
  rg -n "canvas\.service|CanvasService|marketing-context\.service|MarketingContextService|marketing-mvp\.service|MarketingMvpService" services/company -g '*.ts'
  ```

  Expected: every caller is either migrated in this task or retained with an explicit ledger owner/reason. Do not delete a facade while any production caller remains.

- [ ] **Step 2: Migrate the remaining caller(s) to public application contracts.**

  Write/update a focused test per caller before changing its import. No handler may import infrastructure directly.

- [ ] **Step 3: Prove empty scans and run owner tests.**

  Run:

  ```bash
  rg -n "canvas\.service|marketing-context\.service|marketing-mvp\.service" services/company -g '*.ts'
  cd services/company && npx vitest run operations/tests/canvas.contract.test.ts operations/tests/workspace-runtime-observation.test.ts commercial/tests/marketing-mvp.contract.test.ts
  cd services/company && npx tsc --noEmit
  make company-boundary-check
  ```

  Expected: import scan returns no production code (test history excluded); all tests/checks pass.

- [ ] **Step 4: Delete/deprecate precisely and commit.**

  Delete a facade only when every production caller is gone. If external callers remain, retain a one-line delegating deprecated facade with an expiry/ledger owner instead of breaking them silently.

  ```bash
  git add services/company docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "refactor(company): retire migrated mvp service facades"
  ```
