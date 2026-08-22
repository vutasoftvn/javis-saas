# services/finance-legal Cluster (Phase 1: Finance ledger core + Legal) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up `services/finance-legal` as an Encore.ts service owning a minimal, real financial ledger (accounting profile, period, transaction, exception, cash/burn snapshot) and Legal (checklist item, obligation) — ported field-for-field from `backend/business_core/finance/models.py` and `backend/business_core/legal/models.py`, with `workspace_id` validated against `services/identity`.

**Architecture:** One Encore service (`services/finance-legal`), one `SQLDatabase("finance_legal")`, tables under two schemas — `finance` and `legal` — matching the Postgres schema naming already used by the Python backend. Same cross-cluster reference rule as every prior plan: any column pointing outside this cluster becomes a plain nullable `BIGINT`/`number` with no DB FK, validated via direct import only where a real function exists to validate against.

**Tech Stack:** Encore.ts (`encore.dev` ^1.57.13, already in `services/package.json` — no new dependencies), Vitest.

## Global Constraints

- Column names/types must match `backend/business_core/finance/models.py` / `backend/business_core/legal/models.py` — do not invent new field names.
- `workspace_id` is validated on every create by calling `services/identity`'s `getWorkspace`. `confirmed_by`/`closed_by`/`reviewer_id`-style plain `core.users` references are **not** validated — same deferral reasoning as every prior plan (`services/identity` has no `getUser(id)` endpoint, no consumer needs it).
- **Money columns are `NUMERIC(20,2)` in Postgres and come back from the driver as JS `string`, not `number`** — this is deliberate (avoids float precision loss on currency), not an oversight. Every TS interface field backed by a `Numeric`/`Decimal` column (`amount`, `cash`, `burn`, `revenue`, `expenses`, `budget_variance`, `runway_months`) is typed `string`. Do not cast these to `number` in application code without a real decimal library — that reintroduces the precision bug the DB type was chosen to avoid.
- **Out of scope for this plan** (do not implement — explicitly deferred, not overlooked):
  - **The entire Vietnamese accounting-regime framework**: `AccountingFiscalProfile`, `AccountingCoaMapping`, `AccountingRegimeTransitionLog`, `AccountingRegulation`, `AccountingRegulationVersion`, `AccountingBookTemplate`, `FinancialStatementTemplate`, `AccountingDocument`, `AccountingRecord` (9 of `finance/models.py`'s 14 tables). This is a large, TT58/TT199-regulation-specific compliance subsystem — `AccountingRecord` alone depends on both `AccountingBookTemplate` and `AccountingPeriod` and would pull in the whole chain. Nothing in `services/` consumes it today. `backend/regulations/vn/tt58_2026/{metadata,modes}.yaml` (static regulation config, not a DB model) is coupled to this same deferred chain and is deferred with it.
  - **The entire `backend/business_core/validation/` domain** (`evidence_chain.py`, `customer_discovery.py`, `session.py`, `enums.py` — ~17 tables: `ValidationAssumption`, `ValidationHypothesis`, `ValidationExperiment`, `ValidationEvidence`, `ValidationReview`, `ValidationDecision`, `CustomerContact`, `CustomerInterviewSession`, `VerbatimQuote`, `ProblemSeverityScorecard`, `PainPattern`, `EarlyAdopterCandidate`, `ValidationSession`, `StructuredClaim`, `FieldRevision`, `DimensionState`, `ProjectStageHistory`). Unlike the finance framework above, this one is **structurally blocked**, not just large: every single table has a `NOT NULL project_id` foreign key into `strategy.projects`, and `Project` was explicitly deferred as out-of-scope in the `services/operations` plan (no consumer needed it yet). Porting Validation now would mean either inventing a `Project` table with no real requirement behind it, or making `project_id` nullable everywhere — which breaks the actual meaning of these tables (a `ValidationAssumption` with no project isn't a coherent concept the way a `Task` with no `initiative` is). This needs `Project` built first, in its own plan, before Validation can be ported meaningfully.
  - **Net effect on cluster composition**: this plan delivers `finance-legal` as **Finance ledger core + Legal** only — matching the pattern already noted in the `services/commercial` plan (Marketing deferred out of `commercial`). Validation and the VN accounting-regime framework need their own future plans, and Validation specifically needs `Project` (a `services/operations` follow-up) before it can be scoped at all.
  - Within the ported Finance subset: `FinancialTransaction.documentId`/`.projectId`/`.cycleId`/`.workItemId` are unvalidated nullable `BIGINT` (their target tables are either deferred above, or — for `workItemId` → `operating.tasks` in `services/operations` — a real cross-cluster table that exists but isn't validated against here, consistent with how the `commercial` plan left `SalesLead.keyResultId` unvalidated: no `getTask`-by-id-only-for-existence-check pattern has been established as worth the extra cross-service call yet).
- No existing consumer calls anything under `/finance-legal` today — no cutover coordination needed.

---

## File Structure

```text
services/finance-legal/
├── encore.service.ts              # Service("finance-legal") registration
├── db.ts                           # financeLegalDB = new SQLDatabase("finance_legal", {...})
├── migrations/
│   ├── 1_create_accounting_profile_period.up.sql   # finance.accounting_profiles, finance.accounting_periods
│   ├── 2_create_transactions_exceptions.up.sql      # finance.financial_transactions, finance.finance_exceptions
│   ├── 3_create_finance_snapshots.up.sql             # finance.finance_management_snapshots
│   └── 4_create_legal.up.sql                          # legal.legal_checklist_items, legal.legal_obligations
├── accounting-profile.ts             # createAccountingProfile, getAccountingProfileByWorkspace
├── accounting-period.ts               # openAccountingPeriod, getAccountingPeriod, closeAccountingPeriod
├── financial-transaction.ts            # recordFinancialTransaction, getFinancialTransaction, listFinancialTransactions
├── finance-exception.ts                 # raiseFinanceException, getFinanceException, resolveFinanceException
├── finance-snapshot.ts                   # recordFinanceSnapshot, getLatestFinanceSnapshot
├── legal-checklist-item.ts                # createChecklistItem, getChecklistItem, completeChecklistItem
├── legal-obligation.ts                     # createObligation, getObligation, fulfillObligation
├── accounting-profile.test.ts
├── accounting-period.test.ts
├── financial-transaction.test.ts
├── finance-exception.test.ts
├── finance-snapshot.test.ts
├── legal-checklist-item.test.ts
└── legal-obligation.test.ts
```

---

### Task 1: Scaffold the service and database

**Files:**
- Create: `services/finance-legal/encore.service.ts`
- Create: `services/finance-legal/db.ts`

**Interfaces:**
- Produces: `financeLegalDB: SQLDatabase`, used by every subsequent task.

- [ ] **Step 1: Create the service file**

`services/finance-legal/encore.service.ts` (Encore service names must be valid TS identifiers when imported as a directory — Encore allows hyphens in the *directory* name but the `Service()` name string can be anything; keep the string `"finance-legal"` to match the directory and the parent spec's cluster name):

```typescript
import { Service } from "encore.dev/service";

export default new Service("finance-legal");
```

- [ ] **Step 2: Create the database**

`services/finance-legal/db.ts` (the `SQLDatabase` name itself must be a valid identifier-ish string without hyphens per Encore convention already used elsewhere — `"finance_legal"`, matching the `operations`/`commercial` precedent of using the directory's underscore-safe form):

```typescript
import { SQLDatabase } from "encore.dev/storage/sqldb";

export const financeLegalDB = new SQLDatabase("finance_legal", {
  migrations: "./migrations",
});
```

- [ ] **Step 3: Verify the app still type-checks**

Run: `cd /Volumes/SSD/javis-saas/services && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/finance-legal/encore.service.ts services/finance-legal/db.ts
git commit -m "feat(finance-legal): scaffold service and database"
```

---

### Task 2: AccountingProfile + AccountingPeriod schema and API

**Files:**
- Create: `services/finance-legal/migrations/1_create_accounting_profile_period.up.sql`
- Create: `services/finance-legal/accounting-profile.ts`
- Create: `services/finance-legal/accounting-profile.test.ts`
- Create: `services/finance-legal/accounting-period.ts`
- Create: `services/finance-legal/accounting-period.test.ts`

**Interfaces:**
- Consumes: `financeLegalDB` (Task 1), `getWorkspace` from `services/identity/workspace.ts`.
- Produces: `AccountingProfile`/`AccountingPeriod` interfaces, `createAccountingProfile`/`getAccountingProfileByWorkspace`, `openAccountingPeriod`/`getAccountingPeriod`/`closeAccountingPeriod`.

- [ ] **Step 1: Write the migration**

`services/finance-legal/migrations/1_create_accounting_profile_period.up.sql` — column names/types match `backend/business_core/finance/models.py::AccountingProfile/AccountingPeriod`:

```sql
CREATE SCHEMA IF NOT EXISTS finance;

CREATE TABLE finance.accounting_profiles (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  mode TEXT NOT NULL DEFAULT 'TT58_MODE_1',
  status TEXT NOT NULL DEFAULT 'DRAFT',
  confirmed_by BIGINT,
  confirmed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (workspace_id)
);

CREATE TABLE finance.accounting_periods (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  status TEXT NOT NULL DEFAULT 'OPEN',
  closed_by BIGINT,
  closed_at TIMESTAMPTZ
);

CREATE INDEX idx_accounting_periods_workspace_id ON finance.accounting_periods(workspace_id);
```

- [ ] **Step 2: Write the failing accounting-profile test**

`services/finance-legal/accounting-profile.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { createAccountingProfile, getAccountingProfileByWorkspace } from "./accounting-profile";

describe("createAccountingProfile", () => {
  it("creates a profile with canonical defaults", async () => {
    const workspace = await createWorkspace({ name: "Profile Test Inc" });
    const profile = await createAccountingProfile({ workspaceId: workspace.id });
    expect(profile.id).toBeGreaterThan(0);
    expect(profile.mode).toBe("TT58_MODE_1");
    expect(profile.status).toBe("DRAFT");
  });

  it("rejects a profile for a workspace that doesn't exist", async () => {
    await expect(createAccountingProfile({ workspaceId: 999999999 })).rejects.toThrow();
  });

  it("rejects a second profile for the same workspace", async () => {
    const workspace = await createWorkspace({ name: "Dup Profile Inc" });
    await createAccountingProfile({ workspaceId: workspace.id });
    await expect(createAccountingProfile({ workspaceId: workspace.id })).rejects.toThrow();
  });
});

describe("getAccountingProfileByWorkspace", () => {
  it("fetches the profile for a workspace", async () => {
    const workspace = await createWorkspace({ name: "Fetch Profile Inc" });
    const created = await createAccountingProfile({ workspaceId: workspace.id });
    const fetched = await getAccountingProfileByWorkspace({ workspaceId: workspace.id });
    expect(fetched).toEqual(created);
  });

  it("throws not found when no profile exists yet", async () => {
    const workspace = await createWorkspace({ name: "No Profile Inc" });
    await expect(getAccountingProfileByWorkspace({ workspaceId: workspace.id })).rejects.toThrow();
  });
});
```

- [ ] **Step 3: Run it to confirm it fails**

Run: `cd /Volumes/SSD/javis-saas/services && encore test accounting-profile.test.ts`
Expected: FAIL — `Cannot find module './accounting-profile'`

- [ ] **Step 4: Implement accounting-profile.ts**

```typescript
import { api, APIError } from "encore.dev/api";
import { financeLegalDB } from "./db";
import { getWorkspace } from "../identity/workspace";

export interface AccountingProfile {
  id: number;
  workspaceId: number;
  mode: string;
  status: string;
  confirmedBy: number | null;
  confirmedAt: string | null;
  createdAt: string;
}

export interface CreateAccountingProfileParams {
  workspaceId: number;
  mode?: string;
}

interface AccountingProfileRow {
  id: number;
  workspace_id: number;
  mode: string;
  status: string;
  confirmed_by: number | null;
  confirmed_at: Date | null;
  created_at: Date;
}

function rowToProfile(row: AccountingProfileRow): AccountingProfile {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    mode: row.mode,
    status: row.status,
    confirmedBy: row.confirmed_by,
    confirmedAt: row.confirmed_at ? row.confirmed_at.toISOString() : null,
    createdAt: row.created_at.toISOString(),
  };
}

export const createAccountingProfile = api(
  { method: "POST", path: "/finance-legal/accounting-profiles", expose: true },
  async (params: CreateAccountingProfileParams): Promise<AccountingProfile> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await financeLegalDB.queryRow<AccountingProfileRow>`
      INSERT INTO finance.accounting_profiles (workspace_id, mode)
      VALUES (${params.workspaceId}, ${params.mode ?? "TT58_MODE_1"})
      RETURNING id, workspace_id, mode, status, confirmed_by, confirmed_at, created_at
    `;
    if (!row) throw APIError.internal("failed to create accounting profile");
    return rowToProfile(row);
  }
);

export const getAccountingProfileByWorkspace = api(
  { method: "GET", path: "/finance-legal/accounting-profiles/by-workspace/:workspaceId", expose: true },
  async ({ workspaceId }: { workspaceId: number }): Promise<AccountingProfile> => {
    const row = await financeLegalDB.queryRow<AccountingProfileRow>`
      SELECT id, workspace_id, mode, status, confirmed_by, confirmed_at, created_at
      FROM finance.accounting_profiles WHERE workspace_id = ${workspaceId}
    `;
    if (!row) throw APIError.notFound(`no accounting profile for workspace ${workspaceId}`);
    return rowToProfile(row);
  }
);
```

- [ ] **Step 5: Run the accounting-profile test to confirm it passes**

Run: `cd /Volumes/SSD/javis-saas/services && encore test accounting-profile.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 6: Write the failing accounting-period test**

`services/finance-legal/accounting-period.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { openAccountingPeriod, getAccountingPeriod, closeAccountingPeriod } from "./accounting-period";

describe("openAccountingPeriod", () => {
  it("opens a period with the default OPEN status", async () => {
    const workspace = await createWorkspace({ name: "Period Test Inc" });
    const period = await openAccountingPeriod({
      workspaceId: workspace.id,
      startDate: "2026-01-01",
      endDate: "2026-01-31",
    });
    expect(period.id).toBeGreaterThan(0);
    expect(period.status).toBe("OPEN");
  });

  it("rejects a period for a workspace that doesn't exist", async () => {
    await expect(
      openAccountingPeriod({ workspaceId: 999999999, startDate: "2026-01-01", endDate: "2026-01-31" })
    ).rejects.toThrow();
  });
});

describe("getAccountingPeriod/closeAccountingPeriod", () => {
  it("fetches a period and closes it", async () => {
    const workspace = await createWorkspace({ name: "Close Period Test Inc" });
    const created = await openAccountingPeriod({
      workspaceId: workspace.id,
      startDate: "2026-02-01",
      endDate: "2026-02-28",
    });

    const fetched = await getAccountingPeriod({ id: created.id });
    expect(fetched).toEqual(created);

    const closed = await closeAccountingPeriod({ id: created.id });
    expect(closed.status).toBe("CLOSED");
  });

  it("throws not found for a missing id", async () => {
    await expect(getAccountingPeriod({ id: 999999999 })).rejects.toThrow();
  });
});
```

- [ ] **Step 7: Run it to confirm it fails**

Run: `cd /Volumes/SSD/javis-saas/services && encore test accounting-period.test.ts`
Expected: FAIL — `Cannot find module './accounting-period'`

- [ ] **Step 8: Implement accounting-period.ts**

```typescript
import { api, APIError } from "encore.dev/api";
import { financeLegalDB } from "./db";
import { getWorkspace } from "../identity/workspace";

export interface AccountingPeriod {
  id: number;
  workspaceId: number;
  startDate: string;
  endDate: string;
  status: string;
  closedBy: number | null;
  closedAt: string | null;
}

export interface OpenAccountingPeriodParams {
  workspaceId: number;
  startDate: string;
  endDate: string;
}

interface AccountingPeriodRow {
  id: number;
  workspace_id: number;
  start_date: Date;
  end_date: Date;
  status: string;
  closed_by: number | null;
  closed_at: Date | null;
}

function rowToPeriod(row: AccountingPeriodRow): AccountingPeriod {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    startDate: row.start_date.toISOString(),
    endDate: row.end_date.toISOString(),
    status: row.status,
    closedBy: row.closed_by,
    closedAt: row.closed_at ? row.closed_at.toISOString() : null,
  };
}

export const openAccountingPeriod = api(
  { method: "POST", path: "/finance-legal/accounting-periods", expose: true },
  async (params: OpenAccountingPeriodParams): Promise<AccountingPeriod> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await financeLegalDB.queryRow<AccountingPeriodRow>`
      INSERT INTO finance.accounting_periods (workspace_id, start_date, end_date)
      VALUES (${params.workspaceId}, ${params.startDate}, ${params.endDate})
      RETURNING id, workspace_id, start_date, end_date, status, closed_by, closed_at
    `;
    if (!row) throw APIError.internal("failed to open accounting period");
    return rowToPeriod(row);
  }
);

export const getAccountingPeriod = api(
  { method: "GET", path: "/finance-legal/accounting-periods/:id", expose: true },
  async ({ id }: { id: number }): Promise<AccountingPeriod> => {
    const row = await financeLegalDB.queryRow<AccountingPeriodRow>`
      SELECT id, workspace_id, start_date, end_date, status, closed_by, closed_at
      FROM finance.accounting_periods WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`accounting period ${id} not found`);
    return rowToPeriod(row);
  }
);

export const closeAccountingPeriod = api(
  { method: "POST", path: "/finance-legal/accounting-periods/:id/close", expose: true },
  async ({ id }: { id: number }): Promise<AccountingPeriod> => {
    const row = await financeLegalDB.queryRow<AccountingPeriodRow>`
      UPDATE finance.accounting_periods SET status = 'CLOSED', closed_at = now()
      WHERE id = ${id}
      RETURNING id, workspace_id, start_date, end_date, status, closed_by, closed_at
    `;
    if (!row) throw APIError.notFound(`accounting period ${id} not found`);
    return rowToPeriod(row);
  }
);
```

- [ ] **Step 9: Run the accounting-period test to confirm it passes**

Run: `cd /Volumes/SSD/javis-saas/services && encore test accounting-period.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 10: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/finance-legal/migrations/1_create_accounting_profile_period.up.sql services/finance-legal/accounting-profile.ts services/finance-legal/accounting-profile.test.ts services/finance-legal/accounting-period.ts services/finance-legal/accounting-period.test.ts
git commit -m "feat(finance-legal): AccountingProfile and AccountingPeriod schema and API"
```

---

### Task 3: FinancialTransaction + FinanceException schema and API

**Files:**
- Create: `services/finance-legal/migrations/2_create_transactions_exceptions.up.sql`
- Create: `services/finance-legal/financial-transaction.ts`
- Create: `services/finance-legal/financial-transaction.test.ts`
- Create: `services/finance-legal/finance-exception.ts`
- Create: `services/finance-legal/finance-exception.test.ts`

**Interfaces:**
- Consumes: `financeLegalDB` (Task 1), `getWorkspace` (identity).
- Produces: `FinancialTransaction`/`FinanceException` interfaces, `recordFinancialTransaction`/`getFinancialTransaction`/`listFinancialTransactions`, `raiseFinanceException`/`getFinanceException`/`resolveFinanceException`.

- [ ] **Step 1: Write the migration**

`services/finance-legal/migrations/2_create_transactions_exceptions.up.sql` — column names/types match `backend/business_core/finance/models.py::FinancialTransaction/FinanceException`; `document_id`/`project_id`/`cycle_id`/`work_item_id` nullable no FK per Global Constraints:

```sql
CREATE TABLE finance.financial_transactions (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  document_id BIGINT,
  project_id BIGINT,
  cycle_id BIGINT,
  work_item_id BIGINT,
  transaction_date DATE NOT NULL,
  description TEXT NOT NULL,
  amount NUMERIC(20, 2) NOT NULL,
  direction TEXT NOT NULL,
  category TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_financial_transactions_workspace_id ON finance.financial_transactions(workspace_id);

CREATE TABLE finance.finance_exceptions (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  transaction_id BIGINT REFERENCES finance.financial_transactions(id),
  exception_type TEXT NOT NULL,
  severity TEXT NOT NULL DEFAULT 'WARNING',
  details JSONB,
  status TEXT NOT NULL DEFAULT 'OPEN',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_finance_exceptions_workspace_id ON finance.finance_exceptions(workspace_id);
CREATE INDEX idx_finance_exceptions_transaction_id ON finance.finance_exceptions(transaction_id);
```

- [ ] **Step 2: Write the failing financial-transaction test**

`services/finance-legal/financial-transaction.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { recordFinancialTransaction, getFinancialTransaction, listFinancialTransactions } from "./financial-transaction";

describe("recordFinancialTransaction", () => {
  it("records a transaction with the exact decimal amount as a string", async () => {
    const workspace = await createWorkspace({ name: "Txn Test Inc" });
    const txn = await recordFinancialTransaction({
      workspaceId: workspace.id,
      transactionDate: "2026-01-15",
      description: "Client invoice payment",
      amount: "12345678.90",
      direction: "IN",
    });
    expect(txn.id).toBeGreaterThan(0);
    expect(txn.amount).toBe("12345678.90");
    expect(txn.direction).toBe("IN");
  });

  it("rejects a transaction for a workspace that doesn't exist", async () => {
    await expect(
      recordFinancialTransaction({
        workspaceId: 999999999,
        transactionDate: "2026-01-15",
        description: "Orphan",
        amount: "1.00",
        direction: "IN",
      })
    ).rejects.toThrow();
  });
});

describe("getFinancialTransaction/listFinancialTransactions", () => {
  it("fetches a transaction and lists it by workspace", async () => {
    const workspace = await createWorkspace({ name: "List Txn Test Inc" });
    const created = await recordFinancialTransaction({
      workspaceId: workspace.id,
      transactionDate: "2026-01-16",
      description: "Fetch me",
      amount: "500.00",
      direction: "OUT",
    });

    const fetched = await getFinancialTransaction({ id: created.id });
    expect(fetched).toEqual(created);

    const { transactions } = await listFinancialTransactions({ workspaceId: workspace.id });
    expect(transactions.map((t) => t.id)).toContain(created.id);
  });

  it("throws not found for a missing id", async () => {
    await expect(getFinancialTransaction({ id: 999999999 })).rejects.toThrow();
  });
});
```

- [ ] **Step 3: Run it to confirm it fails**

Run: `cd /Volumes/SSD/javis-saas/services && encore test financial-transaction.test.ts`
Expected: FAIL — `Cannot find module './financial-transaction'`

- [ ] **Step 4: Implement financial-transaction.ts**

```typescript
import { api, APIError } from "encore.dev/api";
import { financeLegalDB } from "./db";
import { getWorkspace } from "../identity/workspace";

export interface FinancialTransaction {
  id: number;
  workspaceId: number;
  documentId: number | null;
  projectId: number | null;
  cycleId: number | null;
  workItemId: number | null;
  transactionDate: string;
  description: string;
  amount: string;
  direction: "IN" | "OUT";
  category: string | null;
  createdAt: string;
}

export interface RecordFinancialTransactionParams {
  workspaceId: number;
  transactionDate: string;
  description: string;
  amount: string;
  direction: "IN" | "OUT";
  category?: string;
  workItemId?: number;
}

interface FinancialTransactionRow {
  id: number;
  workspace_id: number;
  document_id: number | null;
  project_id: number | null;
  cycle_id: number | null;
  work_item_id: number | null;
  transaction_date: Date;
  description: string;
  amount: string;
  direction: string;
  category: string | null;
  created_at: Date;
}

const TRANSACTION_COLUMNS = `id, workspace_id, document_id, project_id, cycle_id, work_item_id,
  transaction_date, description, amount, direction, category, created_at`;

function rowToTransaction(row: FinancialTransactionRow): FinancialTransaction {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    documentId: row.document_id,
    projectId: row.project_id,
    cycleId: row.cycle_id,
    workItemId: row.work_item_id,
    transactionDate: row.transaction_date.toISOString(),
    description: row.description,
    amount: row.amount,
    direction: row.direction as "IN" | "OUT",
    category: row.category,
    createdAt: row.created_at.toISOString(),
  };
}

export const recordFinancialTransaction = api(
  { method: "POST", path: "/finance-legal/transactions", expose: true },
  async (params: RecordFinancialTransactionParams): Promise<FinancialTransaction> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await financeLegalDB.queryRow<FinancialTransactionRow>`
      INSERT INTO finance.financial_transactions (workspace_id, work_item_id, transaction_date, description, amount, direction, category)
      VALUES (
        ${params.workspaceId}, ${params.workItemId ?? null}, ${params.transactionDate}, ${params.description},
        ${params.amount}, ${params.direction}, ${params.category ?? null}
      )
      RETURNING ${TRANSACTION_COLUMNS}
    `;
    if (!row) throw APIError.internal("failed to record financial transaction");
    return rowToTransaction(row);
  }
);

export const getFinancialTransaction = api(
  { method: "GET", path: "/finance-legal/transactions/:id", expose: true },
  async ({ id }: { id: number }): Promise<FinancialTransaction> => {
    const row = await financeLegalDB.queryRow<FinancialTransactionRow>`
      SELECT ${TRANSACTION_COLUMNS} FROM finance.financial_transactions WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`financial transaction ${id} not found`);
    return rowToTransaction(row);
  }
);

export const listFinancialTransactions = api(
  { method: "GET", path: "/finance-legal/transactions", expose: true },
  async ({ workspaceId }: { workspaceId: number }): Promise<{ transactions: FinancialTransaction[] }> => {
    const rows = financeLegalDB.query<FinancialTransactionRow>`
      SELECT ${TRANSACTION_COLUMNS} FROM finance.financial_transactions WHERE workspace_id = ${workspaceId}
      ORDER BY transaction_date DESC
    `;
    const transactions: FinancialTransaction[] = [];
    for await (const row of rows) {
      transactions.push(rowToTransaction(row));
    }
    return { transactions };
  }
);
```

- [ ] **Step 5: Run the financial-transaction test to confirm it passes**

Run: `cd /Volumes/SSD/javis-saas/services && encore test financial-transaction.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 6: Write the failing finance-exception test**

`services/finance-legal/finance-exception.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { recordFinancialTransaction } from "./financial-transaction";
import { raiseFinanceException, getFinanceException, resolveFinanceException } from "./finance-exception";

describe("raiseFinanceException", () => {
  it("raises an exception linked to a transaction with the default WARNING severity", async () => {
    const workspace = await createWorkspace({ name: "Exception Test Inc" });
    const txn = await recordFinancialTransaction({
      workspaceId: workspace.id,
      transactionDate: "2026-01-15",
      description: "Suspicious txn",
      amount: "999999.99",
      direction: "OUT",
    });

    const exception = await raiseFinanceException({
      workspaceId: workspace.id,
      transactionId: txn.id,
      exceptionType: "UNUSUAL_AMOUNT",
    });
    expect(exception.id).toBeGreaterThan(0);
    expect(exception.severity).toBe("WARNING");
    expect(exception.status).toBe("OPEN");
  });

  it("rejects an exception for a workspace that doesn't exist", async () => {
    await expect(
      raiseFinanceException({ workspaceId: 999999999, exceptionType: "ORPHAN" })
    ).rejects.toThrow();
  });
});

describe("getFinanceException/resolveFinanceException", () => {
  it("fetches an exception and resolves it", async () => {
    const workspace = await createWorkspace({ name: "Resolve Exception Test Inc" });
    const created = await raiseFinanceException({ workspaceId: workspace.id, exceptionType: "MISSING_RECEIPT" });

    const fetched = await getFinanceException({ id: created.id });
    expect(fetched).toEqual(created);

    const resolved = await resolveFinanceException({ id: created.id });
    expect(resolved.status).toBe("RESOLVED");
  });

  it("throws not found for a missing id", async () => {
    await expect(getFinanceException({ id: 999999999 })).rejects.toThrow();
  });
});
```

- [ ] **Step 7: Run it to confirm it fails**

Run: `cd /Volumes/SSD/javis-saas/services && encore test finance-exception.test.ts`
Expected: FAIL — `Cannot find module './finance-exception'`

- [ ] **Step 8: Implement finance-exception.ts**

```typescript
import { api, APIError } from "encore.dev/api";
import { financeLegalDB } from "./db";
import { getWorkspace } from "../identity/workspace";

export interface FinanceException {
  id: number;
  workspaceId: number;
  transactionId: number | null;
  exceptionType: string;
  severity: string;
  details: Record<string, unknown> | null;
  status: string;
  createdAt: string;
}

export interface RaiseFinanceExceptionParams {
  workspaceId: number;
  exceptionType: string;
  transactionId?: number;
  severity?: string;
  details?: Record<string, unknown>;
}

interface FinanceExceptionRow {
  id: number;
  workspace_id: number;
  transaction_id: number | null;
  exception_type: string;
  severity: string;
  details: Record<string, unknown> | null;
  status: string;
  created_at: Date;
}

const EXCEPTION_COLUMNS = `id, workspace_id, transaction_id, exception_type, severity, details, status, created_at`;

function rowToException(row: FinanceExceptionRow): FinanceException {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    transactionId: row.transaction_id,
    exceptionType: row.exception_type,
    severity: row.severity,
    details: row.details,
    status: row.status,
    createdAt: row.created_at.toISOString(),
  };
}

export const raiseFinanceException = api(
  { method: "POST", path: "/finance-legal/exceptions", expose: true },
  async (params: RaiseFinanceExceptionParams): Promise<FinanceException> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await financeLegalDB.queryRow<FinanceExceptionRow>`
      INSERT INTO finance.finance_exceptions (workspace_id, transaction_id, exception_type, severity, details)
      VALUES (
        ${params.workspaceId}, ${params.transactionId ?? null}, ${params.exceptionType},
        ${params.severity ?? "WARNING"}, ${params.details ? JSON.stringify(params.details) : null}
      )
      RETURNING ${EXCEPTION_COLUMNS}
    `;
    if (!row) throw APIError.internal("failed to raise finance exception");
    return rowToException(row);
  }
);

export const getFinanceException = api(
  { method: "GET", path: "/finance-legal/exceptions/:id", expose: true },
  async ({ id }: { id: number }): Promise<FinanceException> => {
    const row = await financeLegalDB.queryRow<FinanceExceptionRow>`
      SELECT ${EXCEPTION_COLUMNS} FROM finance.finance_exceptions WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`finance exception ${id} not found`);
    return rowToException(row);
  }
);

export const resolveFinanceException = api(
  { method: "POST", path: "/finance-legal/exceptions/:id/resolve", expose: true },
  async ({ id }: { id: number }): Promise<FinanceException> => {
    const row = await financeLegalDB.queryRow<FinanceExceptionRow>`
      UPDATE finance.finance_exceptions SET status = 'RESOLVED'
      WHERE id = ${id}
      RETURNING ${EXCEPTION_COLUMNS}
    `;
    if (!row) throw APIError.notFound(`finance exception ${id} not found`);
    return rowToException(row);
  }
);
```

- [ ] **Step 9: Run the finance-exception test to confirm it passes**

Run: `cd /Volumes/SSD/javis-saas/services && encore test finance-exception.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 10: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/finance-legal/migrations/2_create_transactions_exceptions.up.sql services/finance-legal/financial-transaction.ts services/finance-legal/financial-transaction.test.ts services/finance-legal/finance-exception.ts services/finance-legal/finance-exception.test.ts
git commit -m "feat(finance-legal): FinancialTransaction and FinanceException schema and API"
```

---

### Task 4: FinanceManagementSnapshot schema and API

**Files:**
- Create: `services/finance-legal/migrations/3_create_finance_snapshots.up.sql`
- Create: `services/finance-legal/finance-snapshot.ts`
- Create: `services/finance-legal/finance-snapshot.test.ts`

**Interfaces:**
- Consumes: `financeLegalDB` (Task 1), `getWorkspace` (identity).
- Produces: `FinanceManagementSnapshot` interface, `recordFinanceSnapshot`, `getLatestFinanceSnapshot`.

- [ ] **Step 1: Write the migration**

`services/finance-legal/migrations/3_create_finance_snapshots.up.sql` — column names/types match `backend/business_core/finance/models.py::FinanceManagementSnapshot`; `cycle_id` nullable no FK per Global Constraints:

```sql
CREATE TABLE finance.finance_management_snapshots (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  cycle_id BIGINT,
  as_of DATE NOT NULL,
  cash NUMERIC(20, 2) NOT NULL,
  burn NUMERIC(20, 2) NOT NULL,
  runway_months NUMERIC(12, 2),
  revenue NUMERIC(20, 2) NOT NULL DEFAULT 0,
  expenses NUMERIC(20, 2) NOT NULL DEFAULT 0,
  budget_variance NUMERIC(20, 2),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_finance_snapshots_workspace_id ON finance.finance_management_snapshots(workspace_id);
CREATE INDEX idx_finance_snapshots_workspace_as_of ON finance.finance_management_snapshots(workspace_id, as_of DESC);
```

- [ ] **Step 2: Write the failing test**

`services/finance-legal/finance-snapshot.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { recordFinanceSnapshot, getLatestFinanceSnapshot } from "./finance-snapshot";

describe("recordFinanceSnapshot", () => {
  it("records a snapshot with exact decimal cash/burn as strings", async () => {
    const workspace = await createWorkspace({ name: "Snapshot Test Inc" });
    const snapshot = await recordFinanceSnapshot({
      workspaceId: workspace.id,
      asOf: "2026-01-31",
      cash: "500000.00",
      burn: "50000.00",
    });
    expect(snapshot.id).toBeGreaterThan(0);
    expect(snapshot.cash).toBe("500000.00");
    expect(snapshot.burn).toBe("50000.00");
    expect(snapshot.revenue).toBe("0.00");
  });

  it("rejects a snapshot for a workspace that doesn't exist", async () => {
    await expect(
      recordFinanceSnapshot({ workspaceId: 999999999, asOf: "2026-01-31", cash: "1.00", burn: "1.00" })
    ).rejects.toThrow();
  });
});

describe("getLatestFinanceSnapshot", () => {
  it("returns the most recent snapshot by as_of date", async () => {
    const workspace = await createWorkspace({ name: "Latest Snapshot Test Inc" });
    await recordFinanceSnapshot({ workspaceId: workspace.id, asOf: "2026-01-31", cash: "100.00", burn: "10.00" });
    const latest = await recordFinanceSnapshot({ workspaceId: workspace.id, asOf: "2026-02-28", cash: "90.00", burn: "10.00" });

    const fetched = await getLatestFinanceSnapshot({ workspaceId: workspace.id });
    expect(fetched.id).toBe(latest.id);
    expect(fetched.cash).toBe("90.00");
  });

  it("throws not found when no snapshot exists yet", async () => {
    const workspace = await createWorkspace({ name: "No Snapshot Inc" });
    await expect(getLatestFinanceSnapshot({ workspaceId: workspace.id })).rejects.toThrow();
  });
});
```

- [ ] **Step 3: Run it to confirm it fails**

Run: `cd /Volumes/SSD/javis-saas/services && encore test finance-snapshot.test.ts`
Expected: FAIL — `Cannot find module './finance-snapshot'`

- [ ] **Step 4: Implement finance-snapshot.ts**

```typescript
import { api, APIError } from "encore.dev/api";
import { financeLegalDB } from "./db";
import { getWorkspace } from "../identity/workspace";

export interface FinanceManagementSnapshot {
  id: number;
  workspaceId: number;
  cycleId: number | null;
  asOf: string;
  cash: string;
  burn: string;
  runwayMonths: string | null;
  revenue: string;
  expenses: string;
  budgetVariance: string | null;
  createdAt: string;
}

export interface RecordFinanceSnapshotParams {
  workspaceId: number;
  asOf: string;
  cash: string;
  burn: string;
  revenue?: string;
  expenses?: string;
}

interface FinanceSnapshotRow {
  id: number;
  workspace_id: number;
  cycle_id: number | null;
  as_of: Date;
  cash: string;
  burn: string;
  runway_months: string | null;
  revenue: string;
  expenses: string;
  budget_variance: string | null;
  created_at: Date;
}

const SNAPSHOT_COLUMNS = `id, workspace_id, cycle_id, as_of, cash, burn, runway_months, revenue, expenses,
  budget_variance, created_at`;

function rowToSnapshot(row: FinanceSnapshotRow): FinanceManagementSnapshot {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    cycleId: row.cycle_id,
    asOf: row.as_of.toISOString(),
    cash: row.cash,
    burn: row.burn,
    runwayMonths: row.runway_months,
    revenue: row.revenue,
    expenses: row.expenses,
    budgetVariance: row.budget_variance,
    createdAt: row.created_at.toISOString(),
  };
}

export const recordFinanceSnapshot = api(
  { method: "POST", path: "/finance-legal/snapshots", expose: true },
  async (params: RecordFinanceSnapshotParams): Promise<FinanceManagementSnapshot> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await financeLegalDB.queryRow<FinanceSnapshotRow>`
      INSERT INTO finance.finance_management_snapshots (workspace_id, as_of, cash, burn, revenue, expenses)
      VALUES (
        ${params.workspaceId}, ${params.asOf}, ${params.cash}, ${params.burn},
        ${params.revenue ?? "0"}, ${params.expenses ?? "0"}
      )
      RETURNING ${SNAPSHOT_COLUMNS}
    `;
    if (!row) throw APIError.internal("failed to record finance snapshot");
    return rowToSnapshot(row);
  }
);

export const getLatestFinanceSnapshot = api(
  { method: "GET", path: "/finance-legal/snapshots/latest", expose: true },
  async ({ workspaceId }: { workspaceId: number }): Promise<FinanceManagementSnapshot> => {
    const row = await financeLegalDB.queryRow<FinanceSnapshotRow>`
      SELECT ${SNAPSHOT_COLUMNS} FROM finance.finance_management_snapshots
      WHERE workspace_id = ${workspaceId}
      ORDER BY as_of DESC LIMIT 1
    `;
    if (!row) throw APIError.notFound(`no finance snapshot for workspace ${workspaceId}`);
    return rowToSnapshot(row);
  }
);
```

- [ ] **Step 5: Run the test to confirm it passes**

Run: `cd /Volumes/SSD/javis-saas/services && encore test finance-snapshot.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/finance-legal/migrations/3_create_finance_snapshots.up.sql services/finance-legal/finance-snapshot.ts services/finance-legal/finance-snapshot.test.ts
git commit -m "feat(finance-legal): FinanceManagementSnapshot schema and API"
```

---

### Task 5: Legal (LegalChecklistItem + LegalObligation) schema and API

**Files:**
- Create: `services/finance-legal/migrations/4_create_legal.up.sql`
- Create: `services/finance-legal/legal-checklist-item.ts`
- Create: `services/finance-legal/legal-checklist-item.test.ts`
- Create: `services/finance-legal/legal-obligation.ts`
- Create: `services/finance-legal/legal-obligation.test.ts`

**Interfaces:**
- Consumes: `financeLegalDB` (Task 1), `getWorkspace` (identity).
- Produces: `LegalChecklistItem`/`LegalObligation` interfaces, `createChecklistItem`/`getChecklistItem`/`completeChecklistItem`, `createObligation`/`getObligation`/`fulfillObligation`.

- [ ] **Step 1: Write the migration**

`services/finance-legal/migrations/4_create_legal.up.sql` — column names/types match `backend/business_core/legal/models.py::LegalChecklistItem/LegalObligation`; `evidence_artifact_id` nullable no FK (`runtime_ops.artifacts` not ported anywhere):

```sql
CREATE SCHEMA IF NOT EXISTS legal;

CREATE TABLE legal.legal_checklist_items (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'OPEN',
  evidence_artifact_id BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_legal_checklist_items_workspace_id ON legal.legal_checklist_items(workspace_id);

CREATE TABLE legal.legal_obligations (
  id BIGSERIAL PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  due_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'OPEN',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_legal_obligations_workspace_id ON legal.legal_obligations(workspace_id);
```

- [ ] **Step 2: Write the failing legal-checklist-item test**

`services/finance-legal/legal-checklist-item.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { createChecklistItem, getChecklistItem, completeChecklistItem } from "./legal-checklist-item";

describe("createChecklistItem", () => {
  it("creates a checklist item with the default OPEN status", async () => {
    const workspace = await createWorkspace({ name: "Checklist Test Inc" });
    const item = await createChecklistItem({ workspaceId: workspace.id, title: "Register business license" });
    expect(item.id).toBeGreaterThan(0);
    expect(item.status).toBe("OPEN");
  });

  it("rejects an item for a workspace that doesn't exist", async () => {
    await expect(
      createChecklistItem({ workspaceId: 999999999, title: "Orphan item" })
    ).rejects.toThrow();
  });
});

describe("getChecklistItem/completeChecklistItem", () => {
  it("fetches an item and marks it done", async () => {
    const workspace = await createWorkspace({ name: "Complete Checklist Inc" });
    const created = await createChecklistItem({ workspaceId: workspace.id, title: "Fetch me" });

    const fetched = await getChecklistItem({ id: created.id });
    expect(fetched).toEqual(created);

    const done = await completeChecklistItem({ id: created.id });
    expect(done.status).toBe("DONE");
  });

  it("throws not found for a missing id", async () => {
    await expect(getChecklistItem({ id: 999999999 })).rejects.toThrow();
  });
});
```

- [ ] **Step 3: Run it to confirm it fails**

Run: `cd /Volumes/SSD/javis-saas/services && encore test legal-checklist-item.test.ts`
Expected: FAIL — `Cannot find module './legal-checklist-item'`

- [ ] **Step 4: Implement legal-checklist-item.ts**

```typescript
import { api, APIError } from "encore.dev/api";
import { financeLegalDB } from "./db";
import { getWorkspace } from "../identity/workspace";

export interface LegalChecklistItem {
  id: number;
  workspaceId: number;
  title: string;
  status: string;
  evidenceArtifactId: number | null;
  createdAt: string;
}

export interface CreateChecklistItemParams {
  workspaceId: number;
  title: string;
}

interface LegalChecklistItemRow {
  id: number;
  workspace_id: number;
  title: string;
  status: string;
  evidence_artifact_id: number | null;
  created_at: Date;
}

function rowToChecklistItem(row: LegalChecklistItemRow): LegalChecklistItem {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    title: row.title,
    status: row.status,
    evidenceArtifactId: row.evidence_artifact_id,
    createdAt: row.created_at.toISOString(),
  };
}

export const createChecklistItem = api(
  { method: "POST", path: "/finance-legal/checklist-items", expose: true },
  async (params: CreateChecklistItemParams): Promise<LegalChecklistItem> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await financeLegalDB.queryRow<LegalChecklistItemRow>`
      INSERT INTO legal.legal_checklist_items (workspace_id, title)
      VALUES (${params.workspaceId}, ${params.title})
      RETURNING id, workspace_id, title, status, evidence_artifact_id, created_at
    `;
    if (!row) throw APIError.internal("failed to create checklist item");
    return rowToChecklistItem(row);
  }
);

export const getChecklistItem = api(
  { method: "GET", path: "/finance-legal/checklist-items/:id", expose: true },
  async ({ id }: { id: number }): Promise<LegalChecklistItem> => {
    const row = await financeLegalDB.queryRow<LegalChecklistItemRow>`
      SELECT id, workspace_id, title, status, evidence_artifact_id, created_at
      FROM legal.legal_checklist_items WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`checklist item ${id} not found`);
    return rowToChecklistItem(row);
  }
);

export const completeChecklistItem = api(
  { method: "POST", path: "/finance-legal/checklist-items/:id/complete", expose: true },
  async ({ id }: { id: number }): Promise<LegalChecklistItem> => {
    const row = await financeLegalDB.queryRow<LegalChecklistItemRow>`
      UPDATE legal.legal_checklist_items SET status = 'DONE'
      WHERE id = ${id}
      RETURNING id, workspace_id, title, status, evidence_artifact_id, created_at
    `;
    if (!row) throw APIError.notFound(`checklist item ${id} not found`);
    return rowToChecklistItem(row);
  }
);
```

- [ ] **Step 5: Run the legal-checklist-item test to confirm it passes**

Run: `cd /Volumes/SSD/javis-saas/services && encore test legal-checklist-item.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 6: Write the failing legal-obligation test**

`services/finance-legal/legal-obligation.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { createWorkspace } from "../identity/workspace";
import { createObligation, getObligation, fulfillObligation } from "./legal-obligation";

describe("createObligation", () => {
  it("creates an obligation with the default OPEN status", async () => {
    const workspace = await createWorkspace({ name: "Obligation Test Inc" });
    const obligation = await createObligation({ workspaceId: workspace.id, title: "File annual report" });
    expect(obligation.id).toBeGreaterThan(0);
    expect(obligation.status).toBe("OPEN");
  });

  it("rejects an obligation for a workspace that doesn't exist", async () => {
    await expect(
      createObligation({ workspaceId: 999999999, title: "Orphan obligation" })
    ).rejects.toThrow();
  });
});

describe("getObligation/fulfillObligation", () => {
  it("fetches an obligation and marks it fulfilled", async () => {
    const workspace = await createWorkspace({ name: "Fulfill Obligation Inc" });
    const created = await createObligation({ workspaceId: workspace.id, title: "Fetch me" });

    const fetched = await getObligation({ id: created.id });
    expect(fetched).toEqual(created);

    const fulfilled = await fulfillObligation({ id: created.id });
    expect(fulfilled.status).toBe("FULFILLED");
  });

  it("throws not found for a missing id", async () => {
    await expect(getObligation({ id: 999999999 })).rejects.toThrow();
  });
});
```

- [ ] **Step 7: Run it to confirm it fails**

Run: `cd /Volumes/SSD/javis-saas/services && encore test legal-obligation.test.ts`
Expected: FAIL — `Cannot find module './legal-obligation'`

- [ ] **Step 8: Implement legal-obligation.ts**

```typescript
import { api, APIError } from "encore.dev/api";
import { financeLegalDB } from "./db";
import { getWorkspace } from "../identity/workspace";

export interface LegalObligation {
  id: number;
  workspaceId: number;
  title: string;
  description: string | null;
  dueAt: string | null;
  status: string;
  createdAt: string;
}

export interface CreateObligationParams {
  workspaceId: number;
  title: string;
  description?: string;
  dueAt?: string;
}

interface LegalObligationRow {
  id: number;
  workspace_id: number;
  title: string;
  description: string | null;
  due_at: Date | null;
  status: string;
  created_at: Date;
}

function rowToObligation(row: LegalObligationRow): LegalObligation {
  return {
    id: row.id,
    workspaceId: row.workspace_id,
    title: row.title,
    description: row.description,
    dueAt: row.due_at ? row.due_at.toISOString() : null,
    status: row.status,
    createdAt: row.created_at.toISOString(),
  };
}

export const createObligation = api(
  { method: "POST", path: "/finance-legal/obligations", expose: true },
  async (params: CreateObligationParams): Promise<LegalObligation> => {
    await getWorkspace({ id: params.workspaceId });

    const row = await financeLegalDB.queryRow<LegalObligationRow>`
      INSERT INTO legal.legal_obligations (workspace_id, title, description, due_at)
      VALUES (${params.workspaceId}, ${params.title}, ${params.description ?? null}, ${params.dueAt ?? null})
      RETURNING id, workspace_id, title, description, due_at, status, created_at
    `;
    if (!row) throw APIError.internal("failed to create obligation");
    return rowToObligation(row);
  }
);

export const getObligation = api(
  { method: "GET", path: "/finance-legal/obligations/:id", expose: true },
  async ({ id }: { id: number }): Promise<LegalObligation> => {
    const row = await financeLegalDB.queryRow<LegalObligationRow>`
      SELECT id, workspace_id, title, description, due_at, status, created_at
      FROM legal.legal_obligations WHERE id = ${id}
    `;
    if (!row) throw APIError.notFound(`obligation ${id} not found`);
    return rowToObligation(row);
  }
);

export const fulfillObligation = api(
  { method: "POST", path: "/finance-legal/obligations/:id/fulfill", expose: true },
  async ({ id }: { id: number }): Promise<LegalObligation> => {
    const row = await financeLegalDB.queryRow<LegalObligationRow>`
      UPDATE legal.legal_obligations SET status = 'FULFILLED'
      WHERE id = ${id}
      RETURNING id, workspace_id, title, description, due_at, status, created_at
    `;
    if (!row) throw APIError.notFound(`obligation ${id} not found`);
    return rowToObligation(row);
  }
);
```

- [ ] **Step 9: Run the legal-obligation test to confirm it passes**

Run: `cd /Volumes/SSD/javis-saas/services && encore test legal-obligation.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 10: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/finance-legal/migrations/4_create_legal.up.sql services/finance-legal/legal-checklist-item.ts services/finance-legal/legal-checklist-item.test.ts services/finance-legal/legal-obligation.ts services/finance-legal/legal-obligation.test.ts
git commit -m "feat(finance-legal): LegalChecklistItem and LegalObligation schema and API"
```

---

### Task 6: Full-suite verification + parity note

**Files:**
- Modify: `docs/superpowers/specs/2026-08-22-services-cluster-model-design.md` (append parity note)

**Interfaces:**
- Consumes: everything from Tasks 1–5.
- Produces: nothing new — verification checkpoint. **This is also the last plan in the parent spec's original 4-cluster sequence** (`identity` → `operations` → `commercial` → `finance-legal`).

- [ ] **Step 1: Run the entire `services/` test suite**

Run: `cd /Volumes/SSD/javis-saas/services && encore test`
Expected: PASS — every test file under `identity/`, `operations/`, `commercial/`, `finance-legal/`, plus `shared/`, all green.

- [ ] **Step 2: Type-check the whole services app**

Run: `cd /Volumes/SSD/javis-saas/services && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Smoke-test the ledger end-to-end by hand**

Run: `cd /Volumes/SSD/javis-saas/services && encore run` (leave running in one terminal)
In another terminal:
```bash
WORKSPACE_ID=$(curl -s -X POST http://localhost:4000/identity/workspaces -H 'Content-Type: application/json' -d '{"name":"Finance Smoke Test"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
curl -s -X POST http://localhost:4000/finance-legal/transactions -H 'Content-Type: application/json' \
  -d "{\"workspaceId\":$WORKSPACE_ID,\"transactionDate\":\"2026-01-01\",\"description\":\"Smoke txn\",\"amount\":\"1000.50\",\"direction\":\"IN\"}"
```
Expected: JSON response with `amount: "1000.50"` (a string, not `1000.5` — confirms the NUMERIC-as-string decision from Global Constraints held through the real HTTP path, not just the in-process test). Stop `encore run` (Ctrl+C) once confirmed.

- [ ] **Step 4: Record the parity status**

Append to `docs/superpowers/specs/2026-08-22-services-cluster-model-design.md`, after the `services/commercial` parity note added by the prior plan:

```markdown

**Parity status — `services/finance-legal` (Phase 1, done):** AccountingProfile, AccountingPeriod, FinancialTransaction, FinanceException, FinanceManagementSnapshot ported from `backend/business_core/finance/models.py`; LegalChecklistItem, LegalObligation ported from `backend/business_core/legal/models.py`. Known gaps, deliberately deferred (see the Phase 1 plan's Global Constraints): the full VN TT58/TT199 accounting-regime framework (9 of 14 finance tables — `AccountingFiscalProfile`, `AccountingCoaMapping`, `AccountingRegimeTransitionLog`, `AccountingRegulation`/`Version`, `AccountingBookTemplate`, `FinancialStatementTemplate`, `AccountingDocument`, `AccountingRecord`) not ported, along with the coupled `backend/regulations/vn/` static config; the entire `backend/business_core/validation/` domain (~17 tables) not ported — structurally blocked on `Project` (deferred in the `operations` plan) rather than merely deferred by size. **Cluster composition note**: with Marketing also deferred out of `services/commercial` (see that plan's parity note), the 4-cluster split from `docs/superpowers/specs/2026-08-22-services-cluster-model-design.md` §"Mô hình service mới" has, in practice, delivered a leaner MVP surface than originally sketched — Marketing and Validation (and the VN accounting-regime framework) are real future work, not abandoned scope, and should be re-planned once there's an actual consumer or a `Project` cluster/module to build on.
```

- [ ] **Step 5: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add docs/superpowers/specs/2026-08-22-services-cluster-model-design.md
git commit -m "docs: record services/finance-legal Phase 1 parity status"
```

---

## Self-Review Notes

- **Spec coverage**: parent spec's `services/finance-legal` row lists "Finance, Legal, Validation/Evidence chain, Regulations (VN)". This plan delivers a Finance ledger core + Legal — Validation and the VN regulation framework are explicitly named out-of-scope in Global Constraints with concrete structural reasoning (Validation is blocked on `Project`, not merely large), matching the transparency standard set by the `operations` and `commercial` plans.
- **Cross-cluster/deferred-domain reference rule applied consistently**: `workspace_id` validated via `identity.getWorkspace` on every create across all seven entity files; `confirmed_by`/`closed_by` left unvalidated with the established reasoning; `FinancialTransaction.documentId`/`.projectId`/`.cycleId`/`.workItemId` left unvalidated with reasoning specific to each (deferred tables, or a real table with no established validation pattern yet).
- **Money-as-string decision applied consistently**: every `Numeric`/`Decimal`-backed field (`amount`, `cash`, `burn`, `revenue`, `expenses`, `budget_variance`, `runway_months`) is typed `string` in both the TS interfaces and the row-mapper functions, and the Task 3/4 tests assert on exact string values (e.g. `"12345678.90"`) rather than casting to `number`, catching a regression if a future edit accidentally introduces a numeric cast.
- **Type consistency checked**: entity interfaces, row-mappers, and shared `*_COLUMNS` constants are used consistently between each implementation file and its test file, matching the pattern established in the `commercial` plan.

## Next Plan

This plan completes the parent spec's original 4-cluster sequence (`identity` → `operations` → `commercial` → `finance-legal`). Deferred work surfaced across all three business-cluster plans that needs its own future plan, roughly in priority order: (1) `Project` (a `services/operations` follow-up — unblocks Validation and is referenced by `Initiative`/`FinancialTransaction`/`MarketingContext` alike), (2) Marketing (currently deferred out of `commercial`, likely deserves its own cluster given its size), (3) Validation (blocked on `Project`), (4) the VN accounting-regime framework (blocked on nothing technically, just large — lowest urgency without a compliance deadline driving it), (5) Billing (no source of truth yet — needs a real requirement before it can be scoped at all).
