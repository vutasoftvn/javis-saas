# F6a — Budget Summary Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a project budget envelope backend in
`services/company/finance-legal` that computes a founder-facing budget
summary from real payment-request/allocation data, enforces the budget
limit at payment-approval time (with a founder-override escape hatch), and
replaces 2 hard-coded `UNAVAILABLE` stubs in the S4 project-action-context
adapter with real data.

**Architecture:** A new `project_budget_envelopes` table plus 2 new
columns on the existing `payment_requests` table. A single aggregation
function (`computeProjectBudgetPosition`) is shared between the read-only
summary endpoint and the enforcement check inside
`approvePaymentRequestService` (already shipped in F4) — both run inside a
`db.transaction`, and the enforcement path additionally row-locks the
envelope so two concurrent approvals can't both pass a stale "under limit"
check.

**Tech Stack:** Encore.ts, Drizzle ORM, PostgreSQL, Vitest (via plain `npx
vitest run`, confirmed working in this dev environment without `encore
test`).

**Spec:** `docs/superpowers/specs/2026-09-06-f6a-budget-summary-design.md`

## Global Constraints

- No `any`, `@ts-ignore`, `@ts-expect-error`, or casts to bypass typecheck.
  For a function that must accept either `db` or an open transaction, use
  this codebase's existing pattern:
  `type Tx = Parameters<Parameters<typeof db.transaction>[0]>[0];`
  (already used in `operations/strategy/services/project-kickoff-materialize.service.ts:30`
  and `project-operating-setup.service.ts:170` — do not invent a different
  approach).
- All amounts are `NUMERIC(38,0)` minor-unit strings — arithmetic uses
  `bigint`, never JS `number`/`double`. Sum rows in application code with
  `bigint` accumulation (this codebase has no established SQL-level
  `SUM(...)` aggregation helper for money columns — don't introduce one).
- `forecastUnapproved` is informational only — it must NOT be subtracted
  when computing `remainingAfterCommitments`. Verbatim from the spec's
  worked example: `limitMinor=10000000, actualPaidMinor=1500000,
  committedUnpaidMinor=2000000` → `remainingAfterCommitmentsMinor=6500000`
  (= limit − actualPaid − committedUnpaid), even though
  `forecastUnapprovedMinor=1000000` is also present in that same example.
- `coverage` has exactly 2 values in this task: `"NO_ENVELOPE"` (no
  envelope covers `asOf`) and `"COMPLETE"` (an envelope was found). Do not
  invent additional coverage states.
- Handlers must not import `drizzle-orm`, `models/db`, or DB schema
  directly — only call service functions (Encore Guardrail #1).
- Business errors go through `APIError`, never a bare `Error`.
- Migration release is Expand-only — this plan only adds a table and 2
  columns, never drops/renames existing ones.

---

### Task 1: Migration — `project_budget_envelopes` table + payment_requests override columns

**Files:**
- Create: `services/company/finance-legal/migrations/44_project_budget_envelopes.up.sql`
- Create: `services/company/finance-legal/migrations/44_project_budget_envelopes.down.sql`

**Interfaces:**
- Produces: table `finance.project_budget_envelopes`; new columns
  `payment_requests.budget_override_reason`,
  `payment_requests.budget_override_by_member_id`.

- [ ] **Step 1: Confirm 44 is still the next free migration number, then write the up migration**

Run: `ls services/company/finance-legal/migrations/*.up.sql | sed -E 's/.*\/([0-9]+)_.*/\1/' | sort -n | tail -3`
Expected: highest number is `43`. If it's higher (another migration landed
since this plan was written), rename both files in this task to the next
free number instead of `44`, and use that number everywhere else this
task and later tasks reference it.

```sql
-- Migration 44: F6a — project budget envelopes + payment-request override audit
-- (docs/superpowers/specs/2026-09-06-f6a-budget-summary-design.md)

CREATE TABLE finance.project_budget_envelopes (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  legal_entity_id BIGINT NOT NULL,
  currency VARCHAR(10) NOT NULL DEFAULT 'VND',
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  limit_minor NUMERIC(38, 0) NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  owner_member_id BIGINT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_budget_envelopes_project
  ON finance.project_budget_envelopes(project_id, period_start, period_end);

ALTER TABLE finance.payment_requests
  ADD COLUMN IF NOT EXISTS budget_override_reason TEXT,
  ADD COLUMN IF NOT EXISTS budget_override_by_member_id BIGINT;
```

- [ ] **Step 2: Write the down migration**

```sql
ALTER TABLE finance.payment_requests
  DROP COLUMN IF EXISTS budget_override_by_member_id,
  DROP COLUMN IF EXISTS budget_override_reason;

DROP TABLE IF EXISTS finance.project_budget_envelopes;
```

- [ ] **Step 3: Commit**

```bash
git add services/company/finance-legal/migrations/44_project_budget_envelopes.up.sql \
        services/company/finance-legal/migrations/44_project_budget_envelopes.down.sql
git commit -m "feat(company): thêm migration project_budget_envelopes (F6a phần 1)"
```

---

### Task 2: Drizzle schema — table + column definitions

**Files:**
- Modify: `services/company/shared/db/schema/finance-legal.ts`

**Interfaces:**
- Consumes: migration 44 (Task 1) must be applied for these definitions to
  match the real DB shape.
- Produces: exported `projectBudgetEnvelopes` table; `paymentRequests`
  gains `budgetOverrideReason`, `budgetOverrideByMemberId` — consumed by
  Task 3 (budget-summary.service.ts) and Task 4 (payment-request.service.ts).

- [ ] **Step 1: Add the 2 new columns to the existing `paymentRequests` table**

Find `export const paymentRequests = financeSchema.table("payment_requests", {`
(around line 447) and add these 2 lines right before the closing `});`
(after `deletedAt`):

```ts
  budgetOverrideReason: text("budget_override_reason"),
  budgetOverrideByMemberId: bigint("budget_override_by_member_id", { mode: "bigint" }),
```

- [ ] **Step 2: Add the new table definition**

Append immediately after the `paymentRequests` table definition (before
`paymentAllocations`):

```ts
export const projectBudgetEnvelopes = financeSchema.table("project_budget_envelopes", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull(),
  legalEntityId: bigint("legal_entity_id", { mode: "bigint" }).notNull(),
  currency: varchar("currency", { length: 10 }).default("VND").notNull(),
  periodStart: date("period_start").notNull(),
  periodEnd: date("period_end").notNull(),
  limitMinor: numeric("limit_minor", { precision: 38, scale: 0 }).notNull(),
  version: integer("version").default(1).notNull(),
  ownerMemberId: bigint("owner_member_id", { mode: "bigint" }).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});
```

Confirm `varchar`, `date`, `numeric`, `integer`, `timestamp`, `bigint` are
already imported from `drizzle-orm/pg-core` at the top of this file (they
are — this file already imports all of these for other tables); do not add
a duplicate import.

- [ ] **Step 3: Typecheck**

Run: `cd services/company && npm run typecheck`
Expected: no new errors.

- [ ] **Step 4: Commit**

```bash
git add services/company/shared/db/schema/finance-legal.ts
git commit -m "feat(company): thêm Drizzle schema cho project_budget_envelopes (F6a phần 2)"
```

---

### Task 3: `budget-summary.service.ts` — aggregation engine + read API

**Files:**
- Create: `services/company/finance-legal/services/budget-summary.service.ts`
- Test: `services/company/finance-legal/tests/budget-summary.test.ts`

**Interfaces:**
- Consumes: `db, schema` from `../models/db`; `generateSnowflake` from
  `../../shared/services/snowflake.service`; `requireFounderCommand` from
  `../../shared/auth/workspace-access`; `TenantContext` from
  `../../shared/types/tenant_context`.
- Produces: `Tx` (transaction type alias), `BudgetCoverage`,
  `BudgetSummaryView`, `BudgetPosition`,
  `computeProjectBudgetPosition(tx, params, lockEnvelope): Promise<BudgetPosition>`,
  `getBudgetSummary(ctx, projectId): Promise<BudgetSummaryView>`,
  `CreateBudgetEnvelopeInput`,
  `createBudgetEnvelopeService(ctx, input): Promise<BudgetEnvelopeView>` —
  consumed by Task 4 (`computeProjectBudgetPosition` reused inside
  `approvePaymentRequestService`) and Task 5 (handler).

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createLegalEntityProfile } from "../services/legal-entity-profile.service";
import { createProject } from "../../operations/handlers/project.handler";
import { resolveTenantContext } from "../../identity/services/tenant-context.service";
import {
  createBudgetEnvelopeService,
  getBudgetSummary,
} from "../services/budget-summary.service";
import { createPaymentRequest, submitPaymentRequest, approvePaymentRequest } from "../handlers/payment-request.handler";

async function foundersSetup(displayName: string) {
  const session = await createTestSession({ role: "founder", displayName });
  const authorization = `Bearer ${session.accessToken}`;
  const entity = await createLegalEntityProfile({
    workspaceId: BigInt(session.workspaceId),
    entityType: "MICRO_ENTERPRISE",
  });
  const project = await createProject({
    authorization,
    workspaceId: session.workspaceId,
    title: "Budget test project",
  });
  const ctx = await resolveTenantContext({ authorization, workspaceId: session.workspaceId });
  return { session, authorization, ctx, legalEntityId: entity.id, projectId: project.id };
}

describe("budget-summary.service — computeProjectBudgetPosition / getBudgetSummary", () => {
  it("returns coverage=NO_ENVELOPE when no envelope covers the project", async () => {
    const { ctx, projectId } = await foundersSetup("Budget No Envelope Ws");

    const summary = await getBudgetSummary(ctx, projectId);
    expect(summary.coverage).toBe("NO_ENVELOPE");
  });

  it("computes actualPaid/committedUnpaid/forecastUnapproved correctly and does not subtract forecast from remaining", async () => {
    const { authorization, ctx, legalEntityId, projectId } = await foundersSetup("Budget Math Ws");

    await createBudgetEnvelopeService(ctx, {
      projectId,
      legalEntityId,
      currency: "VND",
      periodStart: "2026-01-01",
      periodEnd: "2026-12-31",
      limitMinor: "10000000",
    });

    // APPROVED, fully unpaid -> committedUnpaid = 2,000,000
    const approvedReq = await createPaymentRequest({
      authorization,
      workspaceId: ctx.workspaceId,
      legalEntityId,
      projectId,
      amountMinor: "2000000",
      currency: "VND",
      beneficiaryBankBin: "970415",
      beneficiaryAccountNumber: "111",
      beneficiaryName: "NCC A",
      purpose: "chi A",
      idempotencyKey: "budget-math-approved",
    });
    const submittedReq = await submitPaymentRequest({
      id: approvedReq.id, expectedVersion: approvedReq.version,
      authorization, workspaceId: ctx.workspaceId,
    });
    await approvePaymentRequest({
      id: submittedReq.id, expectedVersion: submittedReq.version,
      authorization, workspaceId: ctx.workspaceId,
    });

    // DRAFT (forecast only) -> forecastUnapproved = 1,000,000, must NOT reduce remaining
    await createPaymentRequest({
      authorization,
      workspaceId: ctx.workspaceId,
      legalEntityId,
      projectId,
      amountMinor: "1000000",
      currency: "VND",
      beneficiaryBankBin: "970415",
      beneficiaryAccountNumber: "222",
      beneficiaryName: "NCC B",
      purpose: "chi B (forecast)",
      idempotencyKey: "budget-math-forecast",
    });

    const summary = await getBudgetSummary(ctx, projectId);
    expect(summary.committedUnpaidMinor).toBe("2000000");
    expect(summary.forecastUnapprovedMinor).toBe("1000000");
    expect(summary.actualPaidMinor).toBe("0");
    expect(summary.remainingAfterCommitmentsMinor).toBe("8000000"); // 10,000,000 - 0 - 2,000,000
    expect(summary.coverage).toBe("COMPLETE");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/company && npx vitest run finance-legal/tests/budget-summary.test.ts`
Expected: FAIL — `Cannot find module '../services/budget-summary.service'`

- [ ] **Step 3: Implement `budget-summary.service.ts`**

```ts
import { APIError } from "encore.dev/api";
import { and, eq, gte, lte, inArray, isNull, desc } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { requireFounderCommand } from "../../shared/auth/workspace-access";

const { projectBudgetEnvelopes, paymentRequests, paymentAllocations } = schema;

export type Tx = Parameters<Parameters<typeof db.transaction>[0]>[0];

export type BudgetCoverage = "NO_ENVELOPE" | "COMPLETE";

export interface BudgetPosition {
  envelopeId: string | null;
  limitMinor: bigint;
  actualPaidMinor: bigint;
  committedUnpaidMinor: bigint;
  forecastUnapprovedMinor: bigint;
  coverage: BudgetCoverage;
}

export interface BudgetPositionParams {
  workspaceId: string;
  projectId: string;
  currency: string;
  asOf: Date;
}

const OPEN_SETTLEMENT_STATES = ["UNPAID", "REPORTED", "PARTIAL", "EXCEPTION"];

/**
 * Tính vị trí ngân sách hiện tại của một project — dùng chung cho
 * getBudgetSummary (đọc, lockEnvelope=false) và
 * approvePaymentRequestService (enforcement, lockEnvelope=true, gọi trong
 * cùng transaction với việc duyệt chi để khóa envelope, chống 2 request
 * đồng thời cùng đọc "còn dư" rồi cùng được duyệt).
 */
export async function computeProjectBudgetPosition(
  tx: Tx,
  params: BudgetPositionParams,
  lockEnvelope: boolean
): Promise<BudgetPosition> {
  const wsId = BigInt(params.workspaceId);
  const projectId = BigInt(params.projectId);
  const asOfDate = params.asOf.toISOString().split("T")[0];

  const envelopeQuery = tx
    .select()
    .from(projectBudgetEnvelopes)
    .where(
      and(
        eq(projectBudgetEnvelopes.workspaceId, wsId),
        eq(projectBudgetEnvelopes.projectId, projectId),
        eq(projectBudgetEnvelopes.currency, params.currency),
        lte(projectBudgetEnvelopes.periodStart, asOfDate),
        gte(projectBudgetEnvelopes.periodEnd, asOfDate),
        isNull(projectBudgetEnvelopes.deletedAt)
      )
    );

  const envelopeRows = lockEnvelope ? await envelopeQuery.for("update") : await envelopeQuery;
  // Không có unique constraint chống chồng kỳ (out of scope, xem spec) —
  // nếu có nhiều hơn 1 dòng phủ asOf, lấy dòng tạo gần nhất.
  const envelope = envelopeRows.length
    ? envelopeRows.reduce((latest, row) => (row.createdAt > latest.createdAt ? row : latest))
    : undefined;

  if (!envelope) {
    return {
      envelopeId: null,
      limitMinor: 0n,
      actualPaidMinor: 0n,
      committedUnpaidMinor: 0n,
      forecastUnapprovedMinor: 0n,
      coverage: "NO_ENVELOPE",
    };
  }

  const requests = await tx
    .select()
    .from(paymentRequests)
    .where(
      and(
        eq(paymentRequests.workspaceId, wsId),
        eq(paymentRequests.projectId, projectId),
        eq(paymentRequests.currency, params.currency)
      )
    );

  const requestIds = requests.map((r) => r.id);
  const allocations = requestIds.length
    ? await tx
        .select()
        .from(paymentAllocations)
        .where(and(inArray(paymentAllocations.requestId, requestIds), eq(paymentAllocations.status, "ACTIVE")))
    : [];

  const allocatedByRequest = new Map<string, bigint>();
  for (const a of allocations) {
    const key = String(a.requestId);
    allocatedByRequest.set(key, (allocatedByRequest.get(key) ?? 0n) + BigInt(a.amountMinor));
  }

  let actualPaidMinor = 0n;
  let committedUnpaidMinor = 0n;
  let forecastUnapprovedMinor = 0n;

  for (const r of requests) {
    const allocated = allocatedByRequest.get(String(r.id)) ?? 0n;
    actualPaidMinor += allocated;

    if (r.approvalState === "APPROVED" && OPEN_SETTLEMENT_STATES.includes(r.settlementState)) {
      const outstanding = BigInt(r.amountMinor) - allocated;
      if (outstanding > 0n) committedUnpaidMinor += outstanding;
    } else if (r.approvalState === "DRAFT" || r.approvalState === "SUBMITTED") {
      forecastUnapprovedMinor += BigInt(r.amountMinor);
    }
  }

  return {
    envelopeId: String(envelope.id),
    limitMinor: BigInt(envelope.limitMinor),
    actualPaidMinor,
    committedUnpaidMinor,
    forecastUnapprovedMinor,
    coverage: "COMPLETE",
  };
}

export interface BudgetSummaryView {
  currency: string;
  limitMinor: string;
  actualPaidMinor: string;
  committedUnpaidMinor: string;
  forecastUnapprovedMinor: string;
  remainingAfterCommitmentsMinor: string;
  coverage: BudgetCoverage;
  asOf: string;
}

export async function getBudgetSummary(
  ctx: TenantContext,
  projectId: string,
  currency: string = "VND"
): Promise<BudgetSummaryView> {
  const asOf = new Date();
  const position = await db.transaction((tx) =>
    computeProjectBudgetPosition(
      tx,
      { workspaceId: ctx.workspaceId, projectId, currency, asOf },
      false
    )
  );

  const remaining = position.limitMinor - position.actualPaidMinor - position.committedUnpaidMinor;

  return {
    currency,
    limitMinor: String(position.limitMinor),
    actualPaidMinor: String(position.actualPaidMinor),
    committedUnpaidMinor: String(position.committedUnpaidMinor),
    forecastUnapprovedMinor: String(position.forecastUnapprovedMinor),
    remainingAfterCommitmentsMinor: String(remaining),
    coverage: position.coverage,
    asOf: asOf.toISOString(),
  };
}

export interface CreateBudgetEnvelopeInput {
  projectId: string;
  legalEntityId: string;
  currency?: string;
  periodStart: string;
  periodEnd: string;
  limitMinor: string;
}

export interface BudgetEnvelopeView {
  id: string;
  projectId: string;
  legalEntityId: string;
  currency: string;
  periodStart: string;
  periodEnd: string;
  limitMinor: string;
  version: number;
}

export async function createBudgetEnvelopeService(
  ctx: TenantContext,
  input: CreateBudgetEnvelopeInput
): Promise<BudgetEnvelopeView> {
  requireFounderCommand(ctx, "finance.budget.envelope.set");

  const amount = BigInt(input.limitMinor);
  if (amount <= 0n) {
    throw APIError.invalidArgument("limitMinor must be positive");
  }

  const [row] = await db
    .insert(projectBudgetEnvelopes)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(ctx.workspaceId),
      projectId: BigInt(input.projectId),
      legalEntityId: BigInt(input.legalEntityId),
      currency: input.currency ?? "VND",
      periodStart: input.periodStart,
      periodEnd: input.periodEnd,
      limitMinor: input.limitMinor,
      ownerMemberId: BigInt(ctx.workforceMemberId ?? ctx.userId),
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create budget envelope");

  return {
    id: String(row.id),
    projectId: String(row.projectId),
    legalEntityId: String(row.legalEntityId),
    currency: row.currency,
    periodStart: String(row.periodStart),
    periodEnd: String(row.periodEnd),
    limitMinor: row.limitMinor,
    version: row.version,
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd services/company && npx vitest run finance-legal/tests/budget-summary.test.ts`
Expected: PASS (2 tests). If `submitPaymentRequest`/`approvePaymentRequest`
handler parameter shapes differ slightly from what's written above (e.g.
`PaymentRequestActionApiRequest` doesn't accept extra fields cast via `as
any` — remove that cast and pass only `{id, expectedVersion, authorization,
workspaceId}` if that's all `approvePaymentRequest` accepts at this point;
Task 4 adds `overrideReason` to this same interface, so if you're
implementing tasks in order this cast won't be needed once Task 4 lands —
but Task 3 runs BEFORE Task 4, so `approvePaymentRequest` does not yet
accept `overrideReason` at this point in the plan; the request in this
test doesn't exceed any envelope limit so no override is needed — just
pass the 4 base fields, no cast).

- [ ] **Step 5: Commit**

```bash
git add services/company/finance-legal/services/budget-summary.service.ts \
        services/company/finance-legal/tests/budget-summary.test.ts
git commit -m "feat(company): thêm budget-summary.service — tính vị trí ngân sách project (F6a phần 3)"
```

---

### Task 4: Enforcement in `approvePaymentRequestService`

**Files:**
- Modify: `services/company/finance-legal/services/payment-request.service.ts`
- Modify: `services/company/finance-legal/handlers/payment-request.handler.ts`
- Test: `services/company/finance-legal/tests/payment-request.test.ts` (add
  new test cases; do not remove or rewrite existing ones)

**Interfaces:**
- Consumes: `computeProjectBudgetPosition`, `Tx` from
  `./budget-summary.service.ts` (Task 3); `requireFounderCommand` (already
  importable from `../../shared/auth/workspace-access`, not yet imported in
  this file — add it).
- Produces: `PaymentRequestView` gains `budgetOverrideReason: string |
  null`, `budgetOverrideByMemberId: string | null`; `ApprovePaymentRequestInput`-equivalent
  (the `p` parameter of `approvePaymentRequestService`) gains
  `overrideReason?: string`.

- [ ] **Step 1: Write the failing test — over-limit approval requires founder + reason**

Add to `services/company/finance-legal/tests/payment-request.test.ts`,
inside the existing `describe("F4 — payment request state machine", ...)`
block (reuse the existing `foundersSetup` helper already defined at the top
of this file):

```ts
describe("F6a — budget envelope enforcement on approve", () => {
  it("rejects approval over the budget limit for a non-founder, requires overrideReason for a founder", async () => {
    const { session, authorization, legalEntityId } = await foundersSetup("Budget Enforce Ws");
    const { createProject } = await import("../../operations/handlers/project.handler");
    const project = await createProject({
      authorization, workspaceId: session.workspaceId, title: "Budget enforce project",
    });
    const { createBudgetEnvelopeService } = await import("../services/budget-summary.service");
    const { resolveTenantContext } = await import("../../identity/services/tenant-context.service");
    const ctx = await resolveTenantContext({ authorization, workspaceId: session.workspaceId });
    await createBudgetEnvelopeService(ctx, {
      projectId: project.id,
      legalEntityId,
      periodStart: "2026-01-01",
      periodEnd: "2026-12-31",
      limitMinor: "1000000",
    });

    const created = await createPaymentRequest({
      authorization, workspaceId: session.workspaceId,
      legalEntityId, projectId: project.id,
      amountMinor: "1500000", currency: "VND",
      beneficiaryBankBin: "970415", beneficiaryAccountNumber: "999",
      beneficiaryName: "NCC Over Limit", purpose: "vuot ngan sach",
      idempotencyKey: "budget-enforce-over-limit",
    });
    const submitted = await submitPaymentRequest({
      id: created.id, expectedVersion: created.version, authorization, workspaceId: session.workspaceId,
    });

    // Không có overrideReason -> founder vẫn bị chặn
    await expect(
      approvePaymentRequest({
        id: submitted.id, expectedVersion: submitted.version, authorization, workspaceId: session.workspaceId,
      })
    ).rejects.toThrow(/BUDGET_LIMIT_EXCEEDED/);

    // Có overrideReason -> qua, ghi đúng cột override
    const approved = await approvePaymentRequest({
      id: submitted.id, expectedVersion: submitted.version, authorization, workspaceId: session.workspaceId,
      overrideReason: "Founder chấp nhận chi vượt để giữ tiến độ dự án",
    });
    expect(approved.approvalState).toBe("APPROVED");
    expect(approved.budgetOverrideReason).toBe("Founder chấp nhận chi vượt để giữ tiến độ dự án");
    expect(approved.budgetOverrideByMemberId).not.toBeNull();
  });

  it("does not require override when the request stays within the budget limit", async () => {
    const { session, authorization, legalEntityId } = await foundersSetup("Budget Within Limit Ws");
    const { createProject } = await import("../../operations/handlers/project.handler");
    const project = await createProject({
      authorization, workspaceId: session.workspaceId, title: "Budget within-limit project",
    });
    const { createBudgetEnvelopeService } = await import("../services/budget-summary.service");
    const { resolveTenantContext } = await import("../../identity/services/tenant-context.service");
    const ctx = await resolveTenantContext({ authorization, workspaceId: session.workspaceId });
    await createBudgetEnvelopeService(ctx, {
      projectId: project.id,
      legalEntityId,
      periodStart: "2026-01-01",
      periodEnd: "2026-12-31",
      limitMinor: "10000000",
    });

    const created = await createPaymentRequest({
      authorization, workspaceId: session.workspaceId,
      legalEntityId, projectId: project.id,
      amountMinor: "1000000", currency: "VND",
      beneficiaryBankBin: "970415", beneficiaryAccountNumber: "888",
      beneficiaryName: "NCC Within Limit", purpose: "trong han muc",
      idempotencyKey: "budget-within-limit",
    });
    const submitted = await submitPaymentRequest({
      id: created.id, expectedVersion: created.version, authorization, workspaceId: session.workspaceId,
    });
    const approved = await approvePaymentRequest({
      id: submitted.id, expectedVersion: submitted.version, authorization, workspaceId: session.workspaceId,
    });

    expect(approved.approvalState).toBe("APPROVED");
    expect(approved.budgetOverrideReason).toBeNull();
    expect(approved.budgetOverrideByMemberId).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/company && npx vitest run finance-legal/tests/payment-request.test.ts`
Expected: FAIL — `overrideReason` unknown property / no BUDGET_LIMIT_EXCEEDED
thrown yet, and the 10 pre-existing tests in this file must still show as
passing at this point (only the 2 new ones fail).

- [ ] **Step 3: Add `budgetOverrideReason`/`budgetOverrideByMemberId` to `PaymentRequestView` and `toView`**

In `services/company/finance-legal/services/payment-request.service.ts`,
add to the `PaymentRequestView` interface (after `updatedAt`):

```ts
  budgetOverrideReason: string | null;
  budgetOverrideByMemberId: string | null;
```

Add to `toView` (after the `updatedAt` line):

```ts
    budgetOverrideReason: r.budgetOverrideReason ?? null,
    budgetOverrideByMemberId: r.budgetOverrideByMemberId ? String(r.budgetOverrideByMemberId) : null,
```

- [ ] **Step 4: Replace `approvePaymentRequestService` with the enforcement-aware version**

Add imports at the top of `payment-request.service.ts`:

```ts
import { requireFounderCommand } from "../../shared/auth/workspace-access";
import { computeProjectBudgetPosition } from "./budget-summary.service";
```

Replace the ENTIRE existing `approvePaymentRequestService` function body
(from `export async function approvePaymentRequestService` through its
closing `}`) with this complete version — the budget check and the final
update now share one `db.transaction` so the envelope row lock is held
until this approval's own write commits:

```ts
export async function approvePaymentRequestService(
  ctx: TenantContext,
  p: { id: string; expectedVersion: number; overrideReason?: string }
): Promise<PaymentRequestView> {
  const wsId = BigInt(ctx.workspaceId);
  const id = BigInt(p.id);
  const current = await loadOwnRequest(wsId, id);

  await requireCommandAuthority(
    ctx,
    "finance.request.approve",
    { workspaceId: ctx.workspaceId, legalEntityId: String(current.legalEntityId), projectId: current.projectId ? String(current.projectId) : undefined },
    { amount: { minor: current.amountMinor, currency: current.currency } }
  );

  return db.transaction(async (tx) => {
    if (current.version !== p.expectedVersion) {
      const err = APIError.aborted(
        `CAS mismatch: expected version ${p.expectedVersion} but current is ${current.version}`
      );
      (err as any).code = "CONCURRENT_MODIFICATION";
      throw err;
    }
    if (current.approvalState !== "SUBMITTED") {
      throw APIError.invalidArgument(
        `Invalid payment request transition from ${current.approvalState} to APPROVED`
      );
    }

    const nextVersion = current.version + 1;
    let budgetOverrideReason: string | null = null;
    let budgetOverrideByMemberId: bigint | null = null;

    if (current.projectId) {
      const position = await computeProjectBudgetPosition(
        tx,
        {
          workspaceId: String(current.workspaceId),
          projectId: String(current.projectId),
          currency: current.currency,
          asOf: new Date(),
        },
        true
      );

      if (position.coverage === "COMPLETE") {
        const wouldBeTotal = position.committedUnpaidMinor + position.actualPaidMinor + BigInt(current.amountMinor);
        if (wouldBeTotal > position.limitMinor) {
          requireFounderCommand(ctx, "finance.budget.override");
          if (!p.overrideReason?.trim()) {
            throw APIError.failedPrecondition(
              "BUDGET_LIMIT_EXCEEDED: cần overrideReason khi duyệt vượt ngân sách"
            );
          }
          budgetOverrideReason = p.overrideReason;
          budgetOverrideByMemberId = BigInt(ctx.workforceMemberId ?? ctx.userId);
        }
      }
    }

    const approvalHash = computeApprovalHash({
      workspaceId: String(current.workspaceId),
      legalEntityId: String(current.legalEntityId),
      requestId: String(current.id),
      version: nextVersion,
      beneficiaryBankBin: current.beneficiaryBankBin,
      beneficiaryAccountNumber: current.beneficiaryAccountNumber,
      beneficiaryName: current.beneficiaryName,
      amountMinor: current.amountMinor,
      currency: current.currency,
      transferReference: current.transferReference,
    });

    const now = new Date();
    const [updated] = await tx
      .update(paymentRequests)
      .set({
        approvalState: "APPROVED",
        version: nextVersion,
        approvalHash,
        approvedVersion: nextVersion,
        approvedByMemberId: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
        approvedAt: now,
        updatedAt: now,
        budgetOverrideReason,
        budgetOverrideByMemberId,
      })
      .where(
        and(
          eq(paymentRequests.id, id),
          eq(paymentRequests.workspaceId, wsId),
          eq(paymentRequests.version, current.version)
        )
      )
      .returning();

    if (!updated) {
      const err = APIError.aborted("Concurrent modification during payment request approval");
      (err as any).code = "CONCURRENT_MODIFICATION";
      throw err;
    }

    return toView(updated);
  });
}
```

Note what changed vs. the original: `requireCommandAuthority` (role/amount
check, unrelated to budget) still runs BEFORE opening the transaction,
unchanged; everything from the version/state checks onward now runs
inside `db.transaction(async (tx) => {...})`, using `tx.update(...)`
instead of the original bare `db.update(...)`; the budget check sits
between the state-machine check and building `approvalHash`; the final
`.set({...})` gains the 2 new columns.

- [ ] **Step 5: Add `overrideReason` to the handler**

In `services/company/finance-legal/handlers/payment-request.handler.ts`,
change `PaymentRequestActionApiRequest` (used by `approvePaymentRequest`)
— do NOT change the other endpoints that reuse this same interface
(`submitPaymentRequest`, `rejectPaymentRequest`'s base, `cancelPaymentRequest`)
if they'd be affected; instead give `approvePaymentRequest` its own request
type:

```ts
export interface ApprovePaymentRequestApiRequest extends PaymentRequestActionApiRequest {
  overrideReason?: string;
}

export const approvePaymentRequest = api(
  { method: "POST", path: "/finance-legal/payment-requests/:id/approve", expose: true },
  async (req: ApprovePaymentRequestApiRequest): Promise<PaymentRequestView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return approvePaymentRequestService(ctx, req);
  }
);
```

Replace the existing `approvePaymentRequest` export definition with this
one (same path/method, just the new request type).

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd services/company && npx vitest run finance-legal/tests/payment-request.test.ts finance-legal/tests/budget-summary.test.ts`
Expected: PASS (12 + 2 = 14 tests: 10 pre-existing + 2 new in
payment-request.test.ts, 2 in budget-summary.test.ts).

- [ ] **Step 7: Typecheck**

Run: `cd services/company && npm run typecheck`
Expected: no new errors.

- [ ] **Step 8: Commit**

```bash
git add services/company/finance-legal/services/payment-request.service.ts \
        services/company/finance-legal/handlers/payment-request.handler.ts \
        services/company/finance-legal/tests/payment-request.test.ts
git commit -m "feat(company): chặn duyệt payment-request vượt ngân sách, founder override có lý do (F6a phần 4)"
```

---

### Task 5: `budget-summary.handler.ts` — HTTP endpoints

**Files:**
- Create: `services/company/finance-legal/handlers/budget-summary.handler.ts`

**Interfaces:**
- Consumes: `getBudgetSummary`, `createBudgetEnvelopeService`,
  `BudgetSummaryView`, `BudgetEnvelopeView` from `../services/budget-summary.service`
  (Task 3).
- Produces: `POST /finance/budget-envelopes`, `GET /finance/budget-summary`
  — consumed by Task 6 is NOT applicable (Task 6 calls the service function
  directly, not the HTTP endpoint) but by F6c later (out of scope here).

- [ ] **Step 1: Write the handler file**

```ts
import { api, Header, Query } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  createBudgetEnvelopeService,
  getBudgetSummary,
  CreateBudgetEnvelopeInput,
  BudgetEnvelopeView,
  BudgetSummaryView,
} from "../services/budget-summary.service";

export interface CreateBudgetEnvelopeApiRequest extends CreateBudgetEnvelopeInput {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const postBudgetEnvelope = api(
  { method: "POST", path: "/finance/budget-envelopes", expose: true },
  async (req: CreateBudgetEnvelopeApiRequest): Promise<BudgetEnvelopeView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return createBudgetEnvelopeService(ctx, {
      projectId: req.projectId,
      legalEntityId: req.legalEntityId,
      currency: req.currency,
      periodStart: req.periodStart,
      periodEnd: req.periodEnd,
      limitMinor: req.limitMinor,
    });
  }
);

export interface GetBudgetSummaryApiRequest {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  projectId: Query<string>;
  currency?: Query<string>;
}

export const getBudgetSummaryEndpoint = api(
  { method: "GET", path: "/finance/budget-summary", expose: true },
  async (req: GetBudgetSummaryApiRequest): Promise<BudgetSummaryView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return getBudgetSummary(ctx, req.projectId, req.currency ?? "VND");
  }
);
```

- [ ] **Step 2: Typecheck**

Run: `cd services/company && npm run typecheck`
Expected: no new errors.

- [ ] **Step 3: Boundary gates**

Run: `cd /Volumes/SSD/javis-saas && make company-boundary-check && make encore-handler-boundary-check && make ts-suppression-check`
Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add services/company/finance-legal/handlers/budget-summary.handler.ts
git commit -m "feat(company): expose endpoint budget-envelopes/budget-summary (F6a phần 5)"
```

---

### Task 6: Wire S4 context (`project-action-context.service.ts`)

**Files:**
- Modify: `services/company/operations/strategy/services/project-action-context.service.ts`
- Modify: `services/company/operations/strategy/tests/project-action-context.test.ts`

**Interfaces:**
- Consumes: `getFinancialSnapshotsService` from
  `../../../finance-legal/services/financial-snapshot.service` (existing,
  F1); `getBudgetSummary` from
  `../../../finance-legal/services/budget-summary.service` (Task 3) — 3
  levels up from `operations/strategy/services/` lands at
  `services/company/`, then into `finance-legal/services/` (verified via
  `os.path.relpath` against the real directory layout, not guessed).

- [ ] **Step 1: Update the existing test's expectations first (TDD: this makes the test fail against the still-stubbed code)**

In `services/company/operations/strategy/tests/project-action-context.test.ts`,
replace the test `"marks cashSummary and budgetSummary as UNAVAILABLE with reason instead of zero-filling"` with two separate tests:

```ts
  it("marks cashSummary UNAVAILABLE with a real reason when no finance snapshot exists yet", async () => {
    const { ctx, project } = await seedProjectFixture();

    const context = await getProjectActionContext(ctx, project.id);
    expect(context.cashSummary.availability).toBe("UNAVAILABLE");
    if (context.cashSummary.availability === "UNAVAILABLE") {
      expect(context.cashSummary.reason).not.toContain("F6");
    }
  });

  it("marks budgetSummary UNAVAILABLE when the project has no budget envelope, READY with real numbers once one exists", async () => {
    const { ctx, project } = await seedProjectFixture();

    const before = await getProjectActionContext(ctx, project.id);
    expect(before.budgetSummary.availability).toBe("UNAVAILABLE");
    if (before.budgetSummary.availability === "UNAVAILABLE") {
      expect(before.budgetSummary.reason).not.toContain("F6");
    }

    const { createBudgetEnvelopeService } = await import(
      "../../../finance-legal/services/budget-summary.service"
    );
    const { createLegalEntityProfile } = await import(
      "../../../finance-legal/services/legal-entity-profile.service"
    );
    const entity = await createLegalEntityProfile({
      workspaceId: BigInt(ctx.workspaceId),
      entityType: "MICRO_ENTERPRISE",
    });
    await createBudgetEnvelopeService(ctx, {
      projectId: project.id,
      legalEntityId: entity.id,
      periodStart: "2020-01-01",
      periodEnd: "2030-12-31",
      limitMinor: "5000000",
    });

    const after = await getProjectActionContext(ctx, project.id);
    expect(after.budgetSummary.availability).toBe("READY");
    if (after.budgetSummary.availability === "READY") {
      expect(after.budgetSummary.data.totalBudget).toBe(5000000);
      expect(after.budgetSummary.data.remaining).toBe(5000000);
    }
  });
```

Note: `seedProjectFixture`'s `ctx` (defined earlier in this file) is a
plain object literal with `membershipRole: "founder"` already — confirm
`createBudgetEnvelopeService`'s `requireFounderCommand` check passes
against it as-is (it should, since it checks
`ctx.membershipRole.toLowerCase()` against `["founder","co-founder"]` and
this fixture already sets exactly that).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/company && npx vitest run operations/strategy/tests/project-action-context.test.ts`
Expected: the 2 new/changed tests FAIL (old stub still returns the "F6"
reason and never reaches READY); other tests in this file still PASS.

- [ ] **Step 3: Replace the stub in `project-action-context.service.ts`**

Add these imports near the top (alongside the other relative imports):

```ts
import { getFinancialSnapshotsService } from "../../../finance-legal/services/financial-snapshot.service";
import { getBudgetSummary } from "../../../finance-legal/services/budget-summary.service";
```

Replace the existing block:

```ts
  // 7. Finance & Budget Adapters (Prior to F6, returns UNAVAILABLE with reason)
  const cashSummary: ContextPart<{ cashBalance: number; monthlyBurn: number; runwayMonths: number }> = {
    availability: "UNAVAILABLE",
    reason: "Finance cash summary integration not yet available (scheduled in F6)",
  };

  const budgetSummary: ContextPart<{ totalBudget: number; spent: number; remaining: number }> = {
    availability: "UNAVAILABLE",
    reason: "Budget tracking adapter not yet available (scheduled in F6)",
  };
```

with:

```ts
  // 7. Finance & Budget Adapters (F6a — đọc dữ liệu thật từ F1 snapshot và
  // budget envelope, không còn stub cứng).
  const snapshots = await getFinancialSnapshotsService(BigInt(ctx.workspaceId));
  const latestSnapshot = snapshots[0];
  const cashSummary: ContextPart<{ cashBalance: number; monthlyBurn: number; runwayMonths: number }> =
    latestSnapshot
      ? {
          availability: "READY",
          data: {
            cashBalance: latestSnapshot.currentCash != null ? Number(latestSnapshot.currentCash) : 0,
            monthlyBurn: latestSnapshot.monthlyNetBurn != null ? Number(latestSnapshot.monthlyNetBurn) : 0,
            runwayMonths: latestSnapshot.runwayMonths != null ? Number(latestSnapshot.runwayMonths) : 0,
          },
          asOf: latestSnapshot.snapshotDate,
          sourceVersion: latestSnapshot.id,
        }
      : {
          availability: "UNAVAILABLE",
          reason: "Chưa có finance snapshot nào cho workspace này",
        };

  const budgetPosition = await getBudgetSummary(ctx, projectId);
  const budgetSummary: ContextPart<{ totalBudget: number; spent: number; remaining: number }> =
    budgetPosition.coverage === "NO_ENVELOPE"
      ? {
          availability: "UNAVAILABLE",
          reason: "Dự án chưa có budget envelope",
        }
      : {
          availability: "READY",
          data: {
            totalBudget: Number(budgetPosition.limitMinor),
            spent: Number(budgetPosition.actualPaidMinor) + Number(budgetPosition.committedUnpaidMinor),
            remaining: Number(budgetPosition.remainingAfterCommitmentsMinor),
          },
          asOf: budgetPosition.asOf,
          sourceVersion: budgetPosition.coverage,
        };
```

Confirm the enclosing function is already `async` (it must be, since it
already `await`s other adapters above this block per the existing file) —
`await getFinancialSnapshotsService(...)` and `await getBudgetSummary(...)`
require that.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd services/company && npx vitest run operations/strategy/tests/project-action-context.test.ts`
Expected: PASS, all tests in this file (including the pre-existing ones
unrelated to cashSummary/budgetSummary).

- [ ] **Step 5: Typecheck**

Run: `cd services/company && npm run typecheck`
Expected: no new errors.

- [ ] **Step 6: Commit**

```bash
git add services/company/operations/strategy/services/project-action-context.service.ts \
        services/company/operations/strategy/tests/project-action-context.test.ts
git commit -m "feat(company): nối S4 cashSummary/budgetSummary vào dữ liệu thật, bỏ stub F6 (F6a phần 6)"
```

---

### Task 7: Final gate suite

**Files:** none (verification only)

- [ ] **Step 1: Run every test file this plan touched, in one command**

```bash
cd services/company && npx vitest run \
  finance-legal/tests/budget-summary.test.ts \
  finance-legal/tests/payment-request.test.ts \
  operations/strategy/tests/project-action-context.test.ts
```
Expected: all PASS.

- [ ] **Step 2: Run full gates**

```bash
cd services/company && npm run typecheck
cd /Volumes/SSD/javis-saas && make company-boundary-check
make encore-handler-boundary-check
make ts-suppression-check
```
Expected: all PASS.

- [ ] **Step 3: Run the full company suite once for regression awareness**

```bash
cd services/company && npx vitest run 2>&1 | grep -E "^ FAIL|Test Files|Tests "
```
Expected: no NEW failures beyond the 2 already-known, unrelated
pre-existing environmental flakes (`finance-legal/tests/cas-ingestion-contract.test.ts`,
`operations/tests/execution-cycle-calendar.test.ts` — both caused by dirty
shared dev-Postgres state from long-running test sessions, not by any code
this plan touches). If a NEW file fails that isn't one of these two, treat
it as a real regression and investigate before reporting done.

- [ ] **Step 4: Commit is a no-op if Steps 1-3 only ran verification** (no
  file changes expected in this task — if everything already passed after
  Task 6's commit, there's nothing new to commit here).

## Self-Review Notes (from writing-plans checklist)

- **Spec coverage:** schema (Task 1-2), aggregation math + coverage
  semantics (Task 3), enforcement + founder override (Task 4), API (Task
  5), S4 wiring (Task 6) — all sections of the design spec are covered.
  "Ngoài phạm vi" items (Flutter, agent tools, overlapping-envelope
  validation, arbitrary `asOf`) are confirmed untouched by any task above.
- **Type consistency check:** `BudgetSummaryView`/`BudgetPosition`/`Tx`
  defined in Task 3 are used with identical names and shapes in Task 4
  (`computeProjectBudgetPosition`, `Tx`) and Task 6
  (`getBudgetSummary`'s return shape's `coverage`/`limitMinor`/etc. fields
  match what Task 6 destructures).
- **Placeholder scan:** no TBD/TODO; every step has real code or an
  explicit run command.
