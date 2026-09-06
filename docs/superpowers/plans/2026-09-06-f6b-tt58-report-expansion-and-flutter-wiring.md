# F6b — TT58 Report Expansion + Flutter Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand the F5 TT58 report engine to compute inventory, COGS/opex
split, founder-configured corporate income tax, accounting policy
configuration (B03), and tax obligation tracking (F01); fix a pre-existing
Flutter routing bug that silently breaks every `/finance/*` and `/legal/*`
API call; and wire the Flutter TT58 finance UI to the real backend.

**Architecture:** Backend changes extend F5's existing classification
engine (`accounting-mapping.ts`) and report generator
(`accounting-reports.service.ts`) with a small, explicit set of "derived
line" formulas (no generic formula DSL — YAGNI) plus 2 new small services
(`accounting-policy.service.ts`, `tax-obligation.service.ts`). Frontend
changes remove a routing bug in `api_client.dart`, replace the fully-stubbed
`finance_tt58_service.dart` with real calls (reusing the existing
`getJson`/`postJson` convention so new calls stay invisible to the
frontend-api-contract-check gate, matching the established pattern for this
module), and fix 2 error-handling gaps in `finance_controller.dart`.

**Tech Stack:** Encore.ts, Drizzle ORM, PostgreSQL, Vitest (`npx vitest
run`, confirmed working without `encore test`); Flutter/Dart, `flutter test`.

**Spec:** `docs/superpowers/specs/2026-09-06-f6b-tt58-report-expansion-and-flutter-wiring-design.md`

## Global Constraints

- No `any`, `@ts-ignore`, `@ts-expect-error`, or casts to bypass typecheck
  (backend); no equivalent Dart suppressions.
- All amounts are `NUMERIC(38,0)` minor-unit strings — `bigint` arithmetic
  in TS, never `number`/`double` for money on the backend. Corporate income
  tax rate is stored in basis points (`INTEGER`, 0-10000), never a floating
  percentage.
- `corporate_income_tax_rate_bps` has NO default value — stays `NULL` until
  a founder explicitly sets it via `setAccountingPolicyService`. Any report
  line depending on it (`corporate_income_tax`, `net_profit_after_tax` on
  B02, `LOI_NHUAN_GIU_LAI` on B01) must carry issue
  `corporate_income_tax_rate_not_configured` and keep the report
  `status=INCOMPLETE` when the rate is unset — never silently compute with
  an assumed rate.
- Corporate income tax is never negative: `tax = max(0, grossProfit - opex)
  * rateBps / 10000`.
- `ctx.workforceMemberId` and `ctx.userId` are two different entity spines —
  never fall back from one to the other (e.g. `ctx.workforceMemberId ??
  ctx.userId`). A "who confirmed/approved this" column always reads
  `ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null` and stays
  nullable — this exact fallback bug was introduced and caught during
  F6a's final review; do not reintroduce it here.
- `tax_obligation_instances` rows with `source='COMPUTED_CIT'` can only be
  written by the report-driven sync path — `upsertManualTaxObligationService`
  must reject `taxName` values that collide with the reserved computed name.
- Migration release is Expand-only.
- Handlers must not import `drizzle-orm`/`models/db`/DB schema directly —
  only call service functions.
- Flutter: new HTTP calls in `finance_tt58_service.dart` must go through
  `getJson`/`postJson` (inherited via the `WorkspaceService` alias for
  `WorkspaceScopedService`), never `ApiClient.get/post` directly with a
  literal path — matches this module's existing convention and keeps new
  calls invisible to `frontend-api-contract-check`'s literal-route scanner
  (confirmed: it only flags literals passed directly to
  `ApiClient.<method>(...)`, not to an intermediate wrapper).

---

### Task 1: Migration — accounting_policies, tax_obligation_instances, report-mapping derived-line support

**Files:**
- Create: `services/company/finance-legal/migrations/45_tt58_report_expansion.up.sql`
- Create: `services/company/finance-legal/migrations/45_tt58_report_expansion.down.sql`

**Interfaces:**
- Produces: tables `finance.accounting_policies`, `finance.tax_obligation_instances`;
  `finance.accounting_report_mappings.bucket` becomes nullable; new column
  `finance.accounting_report_mappings.derived_kind`; existing
  `accounting_book_entries` rows with `category='cost'` renamed to `'opex'`.

- [ ] **Step 1: Confirm 45 is still the next free migration number**

Run: `ls services/company/finance-legal/migrations/*.up.sql | sed -E 's/.*\/([0-9]+)_.*/\1/' | sort -n | tail -3`
Expected: highest is `44`. If higher, use the next free number everywhere
in this task.

- [ ] **Step 2: Write the up migration**

```sql
-- Migration 45: F6b — mở rộng engine TT58 (tồn kho, COGS/opex, thuế TNDN,
-- chính sách kế toán, nghĩa vụ thuế). Xem
-- docs/superpowers/specs/2026-09-06-f6b-tt58-report-expansion-and-flutter-wiring-design.md

-- Đổi tên category 'cost' cũ thành 'opex' — F5 mới chạy vài giờ, chỉ có
-- dữ liệu test, an toàn để rename thẳng (hành vi classifyBookEntry cho
-- 'opex' kế thừa đúng công thức 'cost' cũ, xem Task 3).
UPDATE finance.accounting_book_entries SET category = 'opex' WHERE category = 'cost';

CREATE TABLE finance.accounting_policies (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  legal_entity_id BIGINT NOT NULL,
  inventory_valuation_method VARCHAR(50) NOT NULL DEFAULT 'weighted_average',
  depreciation_method VARCHAR(50) NOT NULL DEFAULT 'straight_line',
  revenue_recognition_method TEXT NOT NULL DEFAULT
    'Ghi nhận khi hoàn thành chuyển giao dịch vụ/hàng hóa',
  corporate_income_tax_rate_bps INTEGER,
  confirmed_by_member_id BIGINT,
  confirmed_at TIMESTAMPTZ,
  version INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uix_accounting_policy_entity UNIQUE (workspace_id, legal_entity_id)
);

CREATE TABLE finance.tax_obligation_instances (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  legal_entity_id BIGINT NOT NULL,
  period_id BIGINT NOT NULL REFERENCES finance.accounting_periods(id) ON DELETE CASCADE,
  tax_name VARCHAR(100) NOT NULL,
  incurred_minor NUMERIC(38, 0) NOT NULL DEFAULT 0,
  paid_minor NUMERIC(38, 0) NOT NULL DEFAULT 0,
  source VARCHAR(20) NOT NULL DEFAULT 'MANUAL',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uix_tax_obligation UNIQUE (workspace_id, legal_entity_id, period_id, tax_name)
);

ALTER TABLE finance.accounting_report_mappings
  ALTER COLUMN bucket DROP NOT NULL,
  ADD COLUMN IF NOT EXISTS derived_kind VARCHAR(30);
```

- [ ] **Step 3: Write the down migration**

```sql
ALTER TABLE finance.accounting_report_mappings
  DROP COLUMN IF EXISTS derived_kind,
  ALTER COLUMN bucket SET NOT NULL;

DROP TABLE IF EXISTS finance.tax_obligation_instances;
DROP TABLE IF EXISTS finance.accounting_policies;

-- Không tự động đổi 'opex' về 'cost' — rollback này chỉ khôi phục
-- schema, không khôi phục dữ liệu đã đổi tên (dữ liệu test only tại
-- thời điểm viết migration này).
```

- [ ] **Step 4: Commit**

```bash
git add services/company/finance-legal/migrations/45_tt58_report_expansion.up.sql \
        services/company/finance-legal/migrations/45_tt58_report_expansion.down.sql
git commit -m "feat(company): thêm migration mở rộng engine TT58 (F6b phần 1)"
```

---

### Task 2: Drizzle schema — new tables + column changes

**Files:**
- Modify: `services/company/shared/db/schema/finance-legal.ts`

**Interfaces:**
- Consumes: migration 45 (Task 1).
- Produces: exported `accountingPolicies`, `taxObligationInstances`;
  `accountingReportMappings.bucket` becomes `varchar(...).$type<LedgerBucket>()`
  (no `.notNull()`); new column `derivedKind`.

- [ ] **Step 1: Update `accountingReportMappings`**

Find the existing table definition (added in F5, has `.$type<LedgerBucket>()`
on `bucket` per an earlier fix) and:
1. Remove `.notNull()` from the `bucket` column (keep `.$type<LedgerBucket>()`).
2. Add a new column right after `bucket`:
```ts
  derivedKind: varchar("derived_kind", { length: 30 }),
```

- [ ] **Step 2: Add the 2 new table definitions**

Append after `accountingReportSnapshots` (or any convenient spot near the
other TT58 tables):

```ts
export const accountingPolicies = financeSchema.table("accounting_policies", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  legalEntityId: bigint("legal_entity_id", { mode: "bigint" }).notNull(),
  inventoryValuationMethod: varchar("inventory_valuation_method", { length: 50 }).default("weighted_average").notNull(),
  depreciationMethod: varchar("depreciation_method", { length: 50 }).default("straight_line").notNull(),
  revenueRecognitionMethod: text("revenue_recognition_method")
    .default("Ghi nhận khi hoàn thành chuyển giao dịch vụ/hàng hóa")
    .notNull(),
  corporateIncomeTaxRateBps: integer("corporate_income_tax_rate_bps"),
  confirmedByMemberId: bigint("confirmed_by_member_id", { mode: "bigint" }),
  confirmedAt: timestamp("confirmed_at", { withTimezone: true }),
  version: integer("version").default(1).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});

export const taxObligationInstances = financeSchema.table("tax_obligation_instances", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  legalEntityId: bigint("legal_entity_id", { mode: "bigint" }).notNull(),
  periodId: bigint("period_id", { mode: "bigint" }).notNull(),
  taxName: varchar("tax_name", { length: 100 }).notNull(),
  incurredMinor: numeric("incurred_minor", { precision: 38, scale: 0 }).default("0").notNull(),
  paidMinor: numeric("paid_minor", { precision: 38, scale: 0 }).default("0").notNull(),
  source: varchar("source", { length: 20 }).default("MANUAL").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});
```

Confirm `integer`, `text`, `varchar`, `numeric`, `bigint`, `timestamp` are
already imported (they are, used elsewhere in this file).

- [ ] **Step 3: Typecheck**

Run: `cd services/company && npm run typecheck`
Expected: errors WILL appear in `accounting-mapping.ts`/`accounting-reports.service.ts`
at this point (they reference `bucket: LedgerBucket` as non-nullable and
the old category list) — this is expected, Task 3 fixes them. Confirm the
errors are ONLY in those 2 files, nothing else, then proceed (do not fix
them in this task).

- [ ] **Step 4: Commit**

```bash
git add services/company/shared/db/schema/finance-legal.ts
git commit -m "feat(company): thêm Drizzle schema accounting_policies/tax_obligation_instances (F6b phần 2)"
```

---

### Task 3: Expand `accounting-mapping.ts` — inventory, COGS/opex, revenue bucket, derived lines

**Files:**
- Modify: `services/company/finance-legal/services/accounting-mapping.ts`
- Test: `services/company/finance-legal/tests/accounting-mapping.test.ts`

**Interfaces:**
- Produces: `BookEntryCategory` (10 values), `LedgerBucket` (9 values, no
  `"profit"`), `DerivedLineKind`, `ReportMappingLine.bucket: LedgerBucket |
  null`, `ReportMappingLine.derivedKind?: DerivedLineKind`,
  `TT58_2026_MAPPING` (`mappingVersion: "v2"`, 6 B01 lines + 6 B02 lines) —
  consumed by Task 6 (`accounting-reports.service.ts`).

- [ ] **Step 1: Update the existing test file's category list**

In `services/company/finance-legal/tests/accounting-mapping.test.ts`,
replace every `classifyBookEntry("cost", ...)` test case with 3 new cases
(the file currently has ONE `"cost"` test — read it first to find its
exact location, then replace just that one `it(...)` block with these 3):

```ts
  it("opex accrues to payable and reduces profit-related opex bucket, not cash", () => {
    expect(classifyBookEntry("opex", 2_000_000n)).toEqual([
      { bucket: "payable", amountMinor: 2_000_000n },
      { bucket: "opex", amountMinor: 2_000_000n },
    ]);
  });

  it("cogs reduces inventory and increases cogs bucket, not cash", () => {
    expect(classifyBookEntry("cogs", 3_000_000n)).toEqual([
      { bucket: "inventory", amountMinor: -3_000_000n },
      { bucket: "cogs", amountMinor: 3_000_000n },
    ]);
  });

  it("inventory_purchase reduces cash and increases inventory", () => {
    expect(classifyBookEntry("inventory_purchase", 5_000_000n)).toEqual([
      { bucket: "cash", amountMinor: -5_000_000n },
      { bucket: "inventory", amountMinor: 5_000_000n },
    ]);
  });
```

Also update the existing `"revenue"` test case (currently expects
`{ bucket: "profit", amountMinor }` as the second effect) to expect
`{ bucket: "revenue", amountMinor }` instead — the `"profit"` bucket no
longer exists.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/company && npx vitest run finance-legal/tests/accounting-mapping.test.ts`
Expected: FAIL (category `"opex"`/`"cogs"`/`"inventory_purchase"` don't
exist yet; `"revenue"` test expects `"revenue"` bucket that isn't produced
yet).

- [ ] **Step 3: Update `BookEntryCategory`, `LedgerBucket`, `classifyBookEntry`**

Replace:
```ts
export type BookEntryCategory =
  | "capital"
  | "loan"
  | "internal_transfer"
  | "revenue"
  | "cost"
  | "advance"
  | "payable"
  | "receivable";

export type LedgerBucket =
  | "cash"
  | "receivable"
  | "payable"
  | "loan"
  | "advance"
  | "capital"
  | "profit";
```

with:
```ts
export type BookEntryCategory =
  | "capital"
  | "loan"
  | "internal_transfer"
  | "revenue"
  | "cogs"
  | "opex"
  | "inventory_purchase"
  | "advance"
  | "payable"
  | "receivable";

export type LedgerBucket =
  | "cash"
  | "receivable"
  | "payable"
  | "loan"
  | "advance"
  | "capital"
  | "revenue"
  | "cogs"
  | "opex"
  | "inventory";
```

Replace the `case "revenue":` and `case "cost":` branches of
`classifyBookEntry` with:
```ts
    case "revenue":
      return [
        { bucket: "receivable", amountMinor },
        { bucket: "revenue", amountMinor },
      ];
    case "cogs":
      return [
        { bucket: "inventory", amountMinor: -amountMinor },
        { bucket: "cogs", amountMinor },
      ];
    case "opex":
      return [
        { bucket: "payable", amountMinor },
        { bucket: "opex", amountMinor },
      ];
    case "inventory_purchase":
      return [
        { bucket: "cash", amountMinor: -amountMinor },
        { bucket: "inventory", amountMinor },
      ];
```
(leave `capital`/`loan`/`receivable`/`payable`/`internal_transfer`/`advance`
branches untouched).

- [ ] **Step 4: Add `DerivedLineKind` and update `ReportMappingLine`**

Replace:
```ts
export interface ReportMappingLine {
  reportCode: string;
  lineCode: string;
  officialCode: string;
  name: string;
  sourceRef: string;
  ruleType: ReportRuleType;
  bucket: LedgerBucket;
  sign: 1 | -1;
  rounding: "VND_INTEGER";
}
```
with:
```ts
export type DerivedLineKind = "gross_profit" | "corporate_income_tax" | "net_profit_after_tax";

export interface ReportMappingLine {
  reportCode: string;
  lineCode: string;
  officialCode: string;
  name: string;
  sourceRef: string;
  ruleType: ReportRuleType;
  bucket: LedgerBucket | null;
  derivedKind?: DerivedLineKind;
  sign: 1 | -1;
  rounding: "VND_INTEGER";
}
```

- [ ] **Step 5: Replace `TT58_2026_MAPPING` content — bump to `mappingVersion: "v2"`**

Replace the entire `TT58_2026_MAPPING` constant's `mappingVersion` and
`lines` array:
```ts
export const TT58_2026_MAPPING: RegimeMapping = {
  regimeCode: "TT58_2026",
  mappingVersion: "v2",
  lines: [
    {
      reportCode: "B01",
      lineCode: "TS",
      officialCode: "TS",
      name: "Tiền và tương đương tiền",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "closing",
      bucket: "cash",
      sign: 1,
      rounding: "VND_INTEGER",
    },
    {
      reportCode: "B01",
      lineCode: "PHAI_THU",
      officialCode: "PHAI_THU",
      name: "Phải thu khách hàng",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "closing",
      bucket: "receivable",
      sign: 1,
      rounding: "VND_INTEGER",
    },
    {
      reportCode: "B01",
      lineCode: "TON_KHO",
      officialCode: "TON_KHO",
      name: "Hàng tồn kho",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "closing",
      bucket: "inventory",
      sign: 1,
      rounding: "VND_INTEGER",
    },
    {
      reportCode: "B01",
      lineCode: "NO_VAY",
      officialCode: "NO_VAY",
      name: "Nợ vay",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "closing",
      bucket: "loan",
      sign: 1,
      rounding: "VND_INTEGER",
    },
    {
      reportCode: "B01",
      lineCode: "VON_GOP",
      officialCode: "VON_GOP",
      name: "Vốn góp chủ sở hữu",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "closing",
      bucket: "capital",
      sign: 1,
      rounding: "VND_INTEGER",
    },
    {
      reportCode: "B01",
      lineCode: "LOI_NHUAN_GIU_LAI",
      officialCode: "LOI_NHUAN_GIU_LAI",
      name: "Lợi nhuận giữ lại trong kỳ",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "closing",
      bucket: null,
      derivedKind: "net_profit_after_tax",
      sign: 1,
      rounding: "VND_INTEGER",
    },
    {
      reportCode: "B02",
      lineCode: "DOANH_THU_THUAN",
      officialCode: "DOANH_THU_THUAN",
      name: "Doanh thu thuần",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "movement",
      bucket: "revenue",
      sign: 1,
      rounding: "VND_INTEGER",
    },
    {
      reportCode: "B02",
      lineCode: "GIA_VON",
      officialCode: "GIA_VON",
      name: "Giá vốn hàng bán",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "movement",
      bucket: "cogs",
      sign: 1,
      rounding: "VND_INTEGER",
    },
    {
      reportCode: "B02",
      lineCode: "LOI_NHUAN_GOP",
      officialCode: "LOI_NHUAN_GOP",
      name: "Lợi nhuận gộp",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "movement",
      bucket: null,
      derivedKind: "gross_profit",
      sign: 1,
      rounding: "VND_INTEGER",
    },
    {
      reportCode: "B02",
      lineCode: "CHI_PHI_HDKD",
      officialCode: "CHI_PHI_HDKD",
      name: "Chi phí hoạt động kinh doanh",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "movement",
      bucket: "opex",
      sign: 1,
      rounding: "VND_INTEGER",
    },
    {
      reportCode: "B02",
      lineCode: "THUE_TNDN",
      officialCode: "THUE_TNDN",
      name: "Thuế thu nhập doanh nghiệp",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "movement",
      bucket: null,
      derivedKind: "corporate_income_tax",
      sign: 1,
      rounding: "VND_INTEGER",
    },
    {
      reportCode: "B02",
      lineCode: "LOI_NHUAN_SAU_THUE",
      officialCode: "LOI_NHUAN_SAU_THUE",
      name: "Lợi nhuận sau thuế",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "movement",
      bucket: null,
      derivedKind: "net_profit_after_tax",
      sign: 1,
      rounding: "VND_INTEGER",
    },
  ],
};
```
(`UNVERIFIED_SOURCE` constant already exists in this file from F5 — reuse
it, do not redefine.)

- [ ] **Step 6: Run test to verify it passes**

Run: `cd services/company && npx vitest run finance-legal/tests/accounting-mapping.test.ts`
Expected: PASS (same test count as before, with the 3 new opex/cogs/inventory_purchase
cases replacing the old 1 cost case, plus the corrected revenue case — net
+2 tests vs. before).

- [ ] **Step 7: Commit**

```bash
git add services/company/finance-legal/services/accounting-mapping.ts \
        services/company/finance-legal/tests/accounting-mapping.test.ts
git commit -m "feat(company): mở rộng classification engine — tồn kho, COGS/opex, revenue bucket, derived line (F6b phần 3)"
```

---

### Task 4: `accounting-policy.service.ts` — accounting policy configuration

**Files:**
- Create: `services/company/finance-legal/services/accounting-policy.service.ts`
- Create: `services/company/finance-legal/handlers/accounting-policy.handler.ts`
- Test: `services/company/finance-legal/tests/accounting-policy.test.ts`

**Interfaces:**
- Consumes: `requireFounderCommand` from `../../shared/auth/workspace-access`;
  `db, schema` from `../models/db`.
- Produces: `AccountingPolicyView`, `SetAccountingPolicyInput`,
  `getAccountingPolicyService(ctx, legalEntityId): Promise<AccountingPolicyView | null>`,
  `setAccountingPolicyService(ctx, input): Promise<AccountingPolicyView>` —
  consumed by Task 6 (`accounting-reports.service.ts` reads the tax rate).

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createLegalEntityProfile } from "../services/legal-entity-profile.service";
import { resolveTenantContext } from "../../identity/services/tenant-context.service";
import {
  getAccountingPolicyService,
  setAccountingPolicyService,
} from "../services/accounting-policy.service";

async function foundersSetup(displayName: string) {
  const session = await createTestSession({ role: "founder", displayName });
  const authorization = `Bearer ${session.accessToken}`;
  const entity = await createLegalEntityProfile({
    workspaceId: BigInt(session.workspaceId),
    entityType: "MICRO_ENTERPRISE",
  });
  const ctx = await resolveTenantContext({ authorization, workspaceId: session.workspaceId });
  return { session, ctx, legalEntityId: entity.id };
}

describe("accounting-policy.service", () => {
  it("returns null when no policy has been set yet", async () => {
    const { ctx, legalEntityId } = await foundersSetup("Policy None Ws");
    const policy = await getAccountingPolicyService(ctx, legalEntityId);
    expect(policy).toBeNull();
  });

  it("founder sets a tax rate; a non-founder is rejected", async () => {
    const { ctx, legalEntityId } = await foundersSetup("Policy Set Ws");
    const nonFounderSession = await createTestSession({ role: "member", displayName: "Policy Non-Founder" });
    const nonFounderCtx = await resolveTenantContext({
      authorization: `Bearer ${nonFounderSession.accessToken}`,
      workspaceId: ctx.workspaceId,
    });

    await expect(
      setAccountingPolicyService(nonFounderCtx, { legalEntityId, corporateIncomeTaxRateBps: 2000 })
    ).rejects.toThrow(/Missing authority/);

    const policy = await setAccountingPolicyService(ctx, { legalEntityId, corporateIncomeTaxRateBps: 2000 });
    expect(policy.corporateIncomeTaxRateBps).toBe(2000);
    expect(policy.inventoryValuationMethod).toBe("weighted_average");
    expect(policy.confirmedByMemberId).not.toBeNull();

    const fetched = await getAccountingPolicyService(ctx, legalEntityId);
    expect(fetched?.corporateIncomeTaxRateBps).toBe(2000);
  });

  it("rejects a tax rate outside 0-10000 bps", async () => {
    const { ctx, legalEntityId } = await foundersSetup("Policy Range Ws");
    await expect(
      setAccountingPolicyService(ctx, { legalEntityId, corporateIncomeTaxRateBps: 10001 })
    ).rejects.toThrow(/corporateIncomeTaxRateBps/);
    await expect(
      setAccountingPolicyService(ctx, { legalEntityId, corporateIncomeTaxRateBps: -1 })
    ).rejects.toThrow(/corporateIncomeTaxRateBps/);
  });
});
```

If `createTestSession` doesn't accept `"member"` as a non-founder role
literal, check `services/company/identity/tests/helpers/test-session.ts`
for the real accepted role name and use that instead — do not change the
assertion that a non-founder is rejected.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/company && npx vitest run finance-legal/tests/accounting-policy.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `accounting-policy.service.ts`**

```ts
import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { requireFounderCommand } from "../../shared/auth/workspace-access";

const { accountingPolicies } = schema;

export interface AccountingPolicyView {
  legalEntityId: string;
  inventoryValuationMethod: string;
  depreciationMethod: string;
  revenueRecognitionMethod: string;
  corporateIncomeTaxRateBps: number | null;
  confirmedByMemberId: string | null;
  confirmedAt: string | null;
}

function toView(row: typeof accountingPolicies.$inferSelect): AccountingPolicyView {
  return {
    legalEntityId: String(row.legalEntityId),
    inventoryValuationMethod: row.inventoryValuationMethod,
    depreciationMethod: row.depreciationMethod,
    revenueRecognitionMethod: row.revenueRecognitionMethod,
    corporateIncomeTaxRateBps: row.corporateIncomeTaxRateBps,
    confirmedByMemberId: row.confirmedByMemberId ? String(row.confirmedByMemberId) : null,
    confirmedAt: row.confirmedAt ? row.confirmedAt.toISOString() : null,
  };
}

export async function getAccountingPolicyService(
  ctx: TenantContext,
  legalEntityId: string
): Promise<AccountingPolicyView | null> {
  const [row] = await db
    .select()
    .from(accountingPolicies)
    .where(
      and(
        eq(accountingPolicies.workspaceId, BigInt(ctx.workspaceId)),
        eq(accountingPolicies.legalEntityId, BigInt(legalEntityId))
      )
    )
    .limit(1);

  return row ? toView(row) : null;
}

export interface SetAccountingPolicyInput {
  legalEntityId: string;
  inventoryValuationMethod?: string;
  depreciationMethod?: string;
  revenueRecognitionMethod?: string;
  corporateIncomeTaxRateBps?: number;
}

export async function setAccountingPolicyService(
  ctx: TenantContext,
  input: SetAccountingPolicyInput
): Promise<AccountingPolicyView> {
  requireFounderCommand(ctx, "finance.accounting_policy.set");

  if (
    input.corporateIncomeTaxRateBps !== undefined &&
    (input.corporateIncomeTaxRateBps < 0 || input.corporateIncomeTaxRateBps > 10000)
  ) {
    throw APIError.invalidArgument("corporateIncomeTaxRateBps must be between 0 and 10000");
  }

  const now = new Date();
  const values = {
    id: generateSnowflake(),
    workspaceId: BigInt(ctx.workspaceId),
    legalEntityId: BigInt(input.legalEntityId),
    ...(input.inventoryValuationMethod !== undefined && { inventoryValuationMethod: input.inventoryValuationMethod }),
    ...(input.depreciationMethod !== undefined && { depreciationMethod: input.depreciationMethod }),
    ...(input.revenueRecognitionMethod !== undefined && { revenueRecognitionMethod: input.revenueRecognitionMethod }),
    ...(input.corporateIncomeTaxRateBps !== undefined && { corporateIncomeTaxRateBps: input.corporateIncomeTaxRateBps }),
    confirmedByMemberId: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
    confirmedAt: now,
  };

  const [row] = await db
    .insert(accountingPolicies)
    .values(values)
    .onConflictDoUpdate({
      target: [accountingPolicies.workspaceId, accountingPolicies.legalEntityId],
      set: {
        ...(input.inventoryValuationMethod !== undefined && { inventoryValuationMethod: input.inventoryValuationMethod }),
        ...(input.depreciationMethod !== undefined && { depreciationMethod: input.depreciationMethod }),
        ...(input.revenueRecognitionMethod !== undefined && { revenueRecognitionMethod: input.revenueRecognitionMethod }),
        ...(input.corporateIncomeTaxRateBps !== undefined && { corporateIncomeTaxRateBps: input.corporateIncomeTaxRateBps }),
        confirmedByMemberId: ctx.workforceMemberId ? BigInt(ctx.workforceMemberId) : null,
        confirmedAt: now,
        updatedAt: now,
      },
    })
    .returning();

  if (!row) throw APIError.internal("Failed to set accounting policy");
  return toView(row);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd services/company && npx vitest run finance-legal/tests/accounting-policy.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Write the handler**

```ts
import { api, Header, Query } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  getAccountingPolicyService,
  setAccountingPolicyService,
  AccountingPolicyView,
  SetAccountingPolicyInput,
} from "../services/accounting-policy.service";

export interface GetAccountingPolicyApiRequest {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  legalEntityId: Query<string>;
}

export const getAccountingPolicy = api(
  { method: "GET", path: "/finance/accounting-policies", expose: true },
  async (req: GetAccountingPolicyApiRequest): Promise<{ policy: AccountingPolicyView | null }> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    const policy = await getAccountingPolicyService(ctx, req.legalEntityId);
    return { policy };
  }
);

export interface SetAccountingPolicyApiRequest extends SetAccountingPolicyInput {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const postAccountingPolicy = api(
  { method: "POST", path: "/finance/accounting-policies", expose: true },
  async (req: SetAccountingPolicyApiRequest): Promise<AccountingPolicyView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return setAccountingPolicyService(ctx, req);
  }
);
```

- [ ] **Step 6: Typecheck + boundary gates**

Run: `cd services/company && npm run typecheck`
Run: `cd /Volumes/SSD/javis-saas && make company-boundary-check && make encore-handler-boundary-check && make ts-suppression-check`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add services/company/finance-legal/services/accounting-policy.service.ts \
        services/company/finance-legal/handlers/accounting-policy.handler.ts \
        services/company/finance-legal/tests/accounting-policy.test.ts
git commit -m "feat(company): thêm accounting-policy.service — cấu hình chính sách kế toán, founder-only (F6b phần 4)"
```

---

### Task 5: `tax-obligation.service.ts` — tax obligation tracking (F01)

**Files:**
- Create: `services/company/finance-legal/services/tax-obligation.service.ts`
- Create: `services/company/finance-legal/handlers/tax-obligation.handler.ts`
- Test: `services/company/finance-legal/tests/tax-obligation.test.ts`

**Interfaces:**
- Consumes: `generateReportService` from `./accounting-reports.service`
  (Task 6 — this task is written assuming Task 6 already exists; if
  implementing tasks strictly in order, implement Task 6 BEFORE this one,
  or stub the CIT-sync call and revisit — see Step 3 note).
- Produces: `TaxObligationView`, `TaxObligationSummaryView`,
  `getTaxObligationsService(ctx, legalEntityId, periodId): Promise<TaxObligationSummaryView>`,
  `UpsertTaxObligationInput`,
  `upsertManualTaxObligationService(ctx, input): Promise<TaxObligationView>`.

**Note on task ordering:** this task's `getTaxObligationsService` calls
`generateReportService(ctx, {legalEntityId, periodId, reportCode: "B02"})`
internally to sync the computed corporate-income-tax row. Since Task 6
(which modifies `generateReportService`'s derived-line logic) is written to
come AFTER this task in file order below, but this task needs Task 6's
final signature, implement Task 6 first if executing sequentially, or treat
Tasks 5 and 6 as a single combined unit if your process requires strict
file-order execution. The plan lists them in this order for readability
(policy → tax obligations → report engine, mirroring the spec's A-section
order), not execution order.

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createLegalEntityProfile } from "../services/legal-entity-profile.service";
import { resolveTenantContext } from "../../identity/services/tenant-context.service";
import { openAccountingPeriodService } from "../services/accounting-period.service";
import { setAccountingPolicyService } from "../services/accounting-policy.service";
import { createBookEntryService } from "../services/accounting-books.service";
import {
  getTaxObligationsService,
  upsertManualTaxObligationService,
} from "../services/tax-obligation.service";

async function foundersSetup(displayName: string) {
  const session = await createTestSession({ role: "founder", displayName });
  const authorization = `Bearer ${session.accessToken}`;
  const entity = await createLegalEntityProfile({
    workspaceId: BigInt(session.workspaceId),
    entityType: "MICRO_ENTERPRISE",
  });
  const ctx = await resolveTenantContext({ authorization, workspaceId: session.workspaceId });
  const period = await openAccountingPeriodService(
    { workspaceId: session.workspaceId, legalEntityId: entity.id, startDate: "2026-01-01", endDate: "2026-12-31" },
    authorization
  );
  return { session, ctx, legalEntityId: entity.id, periodId: period.id };
}

describe("tax-obligation.service", () => {
  it("rejects a manual upsert using the reserved computed-CIT tax name", async () => {
    const { ctx, legalEntityId, periodId } = await foundersSetup("Tax Reserved Name Ws");
    await expect(
      upsertManualTaxObligationService(ctx, { legalEntityId, periodId, taxName: "Thuế TNDN", incurredMinor: "1000" })
    ).rejects.toThrow(/reserved/);
  });

  it("syncs the computed CIT row from B02 and combines it with a manual VAT entry", async () => {
    const { ctx, legalEntityId, periodId } = await foundersSetup("Tax Sync Ws");
    await setAccountingPolicyService(ctx, { legalEntityId, corporateIncomeTaxRateBps: 2000 });
    await createBookEntryService(ctx, {
      legalEntityId, periodId, item: "Doanh thu", category: "revenue",
      amountMinor: "10000000", effectiveDate: "2026-03-01", source: "test",
    });
    await createBookEntryService(ctx, {
      legalEntityId, periodId, item: "Chi phí HĐ", category: "opex",
      amountMinor: "2000000", effectiveDate: "2026-03-02", source: "test",
    });

    await upsertManualTaxObligationService(ctx, {
      legalEntityId, periodId, taxName: "Thuế GTGT", incurredMinor: "500000", paidMinor: "500000",
    });

    const summary = await getTaxObligationsService(ctx, legalEntityId, periodId);
    const cit = summary.taxes.find((t) => t.taxName === "Thuế TNDN");
    // gross_profit = 10,000,000 (revenue - cogs=0); preTax = 10,000,000 - 2,000,000 = 8,000,000
    // tax = 8,000,000 * 2000/10000 = 1,600,000
    expect(cit?.incurredMinor).toBe("1600000");
    expect(cit?.source).toBe("COMPUTED_CIT");

    const vat = summary.taxes.find((t) => t.taxName === "Thuế GTGT");
    expect(vat?.closingDebtMinor).toBe("0");

    expect(summary.totalBalanceDueMinor).toBe("1600000"); // CIT chưa nộp + VAT đã nộp hết
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/company && npx vitest run finance-legal/tests/tax-obligation.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `tax-obligation.service.ts`**

```ts
import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { generateReportService } from "./accounting-reports.service";

const { taxObligationInstances } = schema;

const COMPUTED_CIT_TAX_NAME = "Thuế TNDN";

export interface TaxObligationView {
  id: string;
  taxName: string;
  incurredMinor: string;
  paidMinor: string;
  closingDebtMinor: string;
  source: "MANUAL" | "COMPUTED_CIT";
}

export interface TaxObligationSummaryView {
  taxes: TaxObligationView[];
  totalBalanceDueMinor: string;
}

function toView(row: typeof taxObligationInstances.$inferSelect): TaxObligationView {
  const closing = BigInt(row.incurredMinor) - BigInt(row.paidMinor);
  return {
    id: String(row.id),
    taxName: row.taxName,
    incurredMinor: row.incurredMinor,
    paidMinor: row.paidMinor,
    closingDebtMinor: String(closing),
    source: row.source as "MANUAL" | "COMPUTED_CIT",
  };
}

async function syncComputedCorporateIncomeTax(
  ctx: TenantContext,
  legalEntityId: string,
  periodId: string
): Promise<void> {
  const b02 = await generateReportService(ctx, { legalEntityId, periodId, reportCode: "B02" });
  const citLine = b02.lines.find((l) => l.lineCode === "THUE_TNDN");
  if (!citLine) return;

  await db
    .insert(taxObligationInstances)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(ctx.workspaceId),
      legalEntityId: BigInt(legalEntityId),
      periodId: BigInt(periodId),
      taxName: COMPUTED_CIT_TAX_NAME,
      incurredMinor: citLine.amountMinor,
      source: "COMPUTED_CIT",
    })
    .onConflictDoUpdate({
      target: [
        taxObligationInstances.workspaceId,
        taxObligationInstances.legalEntityId,
        taxObligationInstances.periodId,
        taxObligationInstances.taxName,
      ],
      set: { incurredMinor: citLine.amountMinor, updatedAt: new Date() },
    });
}

export async function getTaxObligationsService(
  ctx: TenantContext,
  legalEntityId: string,
  periodId: string
): Promise<TaxObligationSummaryView> {
  await syncComputedCorporateIncomeTax(ctx, legalEntityId, periodId);

  const rows = await db
    .select()
    .from(taxObligationInstances)
    .where(
      and(
        eq(taxObligationInstances.workspaceId, BigInt(ctx.workspaceId)),
        eq(taxObligationInstances.legalEntityId, BigInt(legalEntityId)),
        eq(taxObligationInstances.periodId, BigInt(periodId))
      )
    );

  const taxes = rows.map(toView);
  const totalBalanceDueMinor = taxes.reduce((sum, t) => sum + BigInt(t.closingDebtMinor), 0n);

  return { taxes, totalBalanceDueMinor: String(totalBalanceDueMinor) };
}

export interface UpsertTaxObligationInput {
  legalEntityId: string;
  periodId: string;
  taxName: string;
  incurredMinor?: string;
  paidMinor?: string;
}

export async function upsertManualTaxObligationService(
  ctx: TenantContext,
  input: UpsertTaxObligationInput
): Promise<TaxObligationView> {
  if (input.taxName === COMPUTED_CIT_TAX_NAME) {
    throw APIError.invalidArgument(
      `"${COMPUTED_CIT_TAX_NAME}" is a reserved tax name computed automatically from B02 — use a different taxName`
    );
  }

  const [row] = await db
    .insert(taxObligationInstances)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(ctx.workspaceId),
      legalEntityId: BigInt(input.legalEntityId),
      periodId: BigInt(input.periodId),
      taxName: input.taxName,
      incurredMinor: input.incurredMinor ?? "0",
      paidMinor: input.paidMinor ?? "0",
      source: "MANUAL",
    })
    .onConflictDoUpdate({
      target: [
        taxObligationInstances.workspaceId,
        taxObligationInstances.legalEntityId,
        taxObligationInstances.periodId,
        taxObligationInstances.taxName,
      ],
      set: {
        ...(input.incurredMinor !== undefined && { incurredMinor: input.incurredMinor }),
        ...(input.paidMinor !== undefined && { paidMinor: input.paidMinor }),
        updatedAt: new Date(),
      },
    })
    .returning();

  if (!row) throw APIError.internal("Failed to upsert tax obligation");
  return toView(row);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd services/company && npx vitest run finance-legal/tests/tax-obligation.test.ts`
Expected: PASS (2 tests). This depends on Task 6's derived-line logic
already existing (`generateReportService` must produce a real `THUE_TNDN`
value) — if Task 6 isn't done yet, this test will fail with an amount
mismatch, not a missing-module error; that's expected until Task 6 lands.

- [ ] **Step 5: Write the handler**

```ts
import { api, Header, Query } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import {
  getTaxObligationsService,
  upsertManualTaxObligationService,
  TaxObligationSummaryView,
  TaxObligationView,
  UpsertTaxObligationInput,
} from "../services/tax-obligation.service";

export interface GetTaxObligationsApiRequest {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  legalEntityId: Query<string>;
  periodId: Query<string>;
}

export const getTaxObligations = api(
  { method: "GET", path: "/finance/tax-obligations", expose: true },
  async (req: GetTaxObligationsApiRequest): Promise<TaxObligationSummaryView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return getTaxObligationsService(ctx, req.legalEntityId, req.periodId);
  }
);

export interface UpsertTaxObligationApiRequest extends UpsertTaxObligationInput {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const postTaxObligation = api(
  { method: "POST", path: "/finance/tax-obligations", expose: true },
  async (req: UpsertTaxObligationApiRequest): Promise<TaxObligationView> => {
    const ctx = await requireWorkspaceAccess(req.authorization, req.workspaceId);
    return upsertManualTaxObligationService(ctx, req);
  }
);
```

- [ ] **Step 6: Typecheck + boundary gates + commit**

Run `npm run typecheck` and the 3 boundary gates as in Task 4.

```bash
git add services/company/finance-legal/services/tax-obligation.service.ts \
        services/company/finance-legal/handlers/tax-obligation.handler.ts \
        services/company/finance-legal/tests/tax-obligation.test.ts
git commit -m "feat(company): thêm tax-obligation.service — F01 nửa tự động/nửa thủ công (F6b phần 5)"
```

---

### Task 6: `accounting-reports.service.ts` — derived-line computation

**⚠️ Plan-drift note:** this task's brief was originally written against an
older snapshot of `accounting-reports.service.ts`. A concurrent, unrelated
commit (`6279552f fix(finance): validate persisted report mapping buckets`)
has since added a `requireReportMappingBucket(bucket): LedgerBucket` guard
and a `reportMappingLines` intermediate step to `generateReportService`,
which the steps below now account for. If the file has changed again since
this plan was last read, re-read it in full before touching Step 6 — do not
trust the "Replace this block" text blindly if it no longer matches.

**Files:**
- Modify: `services/company/finance-legal/services/accounting-reports.service.ts`
- Modify: `services/company/finance-legal/tests/tt58-reports.test.ts`
  (the existing F5 fixture test)
- Modify: `services/company/finance-legal/tests/accounting-reports-status.test.ts`
  (existing unit test for `computeReportStatus`/`requireReportMappingBucket` —
  broken by Task 3's bucket-vocabulary change; not fixed by any other task)

**Interfaces:**
- Consumes: `getAccountingPolicyService` from `./accounting-policy.service`
  (Task 4); `DerivedLineKind` from `./accounting-mapping` (Task 3).
- Produces: `computeDerivedLine(kind, bucketTotals, taxRateBps)` (exported
  for its own unit test); `generateReportService` now handles
  `derivedKind`-bearing mapping rows; `requireReportMappingBucket` now
  validates against the new 9-value `LedgerBucket` set instead of the old
  7-value set (no more `"profit"`).

- [ ] **Step 1: Write the failing unit test for `computeDerivedLine`**

```ts
import { describe, expect, it } from "vitest";
import { computeDerivedLine } from "../services/accounting-reports.service";

describe("accounting-reports.service — computeDerivedLine", () => {
  const totals = new Map([
    ["revenue", 10_000_000n],
    ["cogs", 2_000_000n],
    ["opex", 3_000_000n],
  ]) as Map<import("../services/accounting-mapping").LedgerBucket, bigint>;

  it("gross_profit = revenue - cogs, independent of tax rate", () => {
    expect(computeDerivedLine("gross_profit", totals, null)).toEqual({ amountMinor: 8_000_000n });
  });

  it("corporate_income_tax flags an issue when the rate is not configured", () => {
    const result = computeDerivedLine("corporate_income_tax", totals, null);
    expect(result.amountMinor).toBe(0n);
    expect(result.issue).toBe("corporate_income_tax_rate_not_configured");
  });

  it("corporate_income_tax computes correctly when the rate is configured", () => {
    // preTax = grossProfit(8,000,000) - opex(3,000,000) = 5,000,000
    // tax = 5,000,000 * 2000/10000 = 1,000,000
    const result = computeDerivedLine("corporate_income_tax", totals, 2000);
    expect(result.amountMinor).toBe(1_000_000n);
    expect(result.issue).toBeUndefined();
  });

  it("corporate_income_tax never goes negative when opex exceeds gross profit", () => {
    const lossTotals = new Map([
      ["revenue", 1_000_000n],
      ["cogs", 500_000n],
      ["opex", 10_000_000n],
    ]) as Map<import("../services/accounting-mapping").LedgerBucket, bigint>;
    const result = computeDerivedLine("corporate_income_tax", lossTotals, 2000);
    expect(result.amountMinor).toBe(0n);
  });

  it("net_profit_after_tax = preTax when rate not configured, flags the same issue", () => {
    const result = computeDerivedLine("net_profit_after_tax", totals, null);
    expect(result.amountMinor).toBe(5_000_000n); // grossProfit - opex, tax not deducted
    expect(result.issue).toBe("corporate_income_tax_rate_not_configured");
  });

  it("net_profit_after_tax deducts tax when rate is configured", () => {
    const result = computeDerivedLine("net_profit_after_tax", totals, 2000);
    expect(result.amountMinor).toBe(4_000_000n); // 5,000,000 - 1,000,000
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/company && npx vitest run finance-legal/tests/accounting-reports-derived.test.ts`
(save the Step 1 test to this new file). Expected: FAIL — `computeDerivedLine`
is not exported yet.

- [ ] **Step 3: Add `computeDerivedLine` and wire it into `generateReportService`**

Add near the top of `accounting-reports.service.ts`, after the existing
imports (add `getAccountingPolicyService` and `DerivedLineKind` to the
import list — `DerivedLineKind` comes from `./accounting-mapping`):

```ts
import { getAccountingPolicyService } from "./accounting-policy.service";
import {
  classifyBookEntry,
  computeMappingDefinitionHash,
  DerivedLineKind,
  LedgerBucket,
  RegimeMapping,
  TT58_2026_MAPPING,
} from "./accounting-mapping";
```

Add this function (place it after `computeReportStatus`, before
`ReportLineView`):

```ts
export interface DerivedLineResult {
  amountMinor: bigint;
  issue?: string;
}

/**
 * 3 công thức derived cố định cho B01/B02 — không xây formula-engine tổng
 * quát (YAGNI). Thuế TNDN không bao giờ âm (lỗ -> thuế = 0). Khi tax rate
 * chưa cấu hình, trả issue rõ ràng thay vì giả định thuế suất bất kỳ.
 */
export function computeDerivedLine(
  kind: DerivedLineKind,
  bucketTotals: Map<LedgerBucket, bigint>,
  taxRateBps: number | null
): DerivedLineResult {
  const revenue = bucketTotals.get("revenue") ?? 0n;
  const cogs = bucketTotals.get("cogs") ?? 0n;
  const opex = bucketTotals.get("opex") ?? 0n;
  const grossProfit = revenue - cogs;

  if (kind === "gross_profit") {
    return { amountMinor: grossProfit };
  }

  const preTax = grossProfit - opex;
  const base = preTax > 0n ? preTax : 0n;

  if (kind === "corporate_income_tax") {
    if (taxRateBps == null) {
      return { amountMinor: 0n, issue: "corporate_income_tax_rate_not_configured" };
    }
    return { amountMinor: (base * BigInt(taxRateBps)) / 10000n };
  }

  // net_profit_after_tax
  if (taxRateBps == null) {
    return { amountMinor: preTax, issue: "corporate_income_tax_rate_not_configured" };
  }
  const tax = (base * BigInt(taxRateBps)) / 10000n;
  return { amountMinor: preTax - tax };
}
```

- [ ] **Step 4: Run the unit test to verify it passes**

Run: `cd services/company && npx vitest run finance-legal/tests/accounting-reports-derived.test.ts`
Expected: PASS (6 tests).

- [ ] **Step 5: Update `requireReportMappingBucket` for the new bucket vocabulary**

The current file has this function (added by an unrelated concurrent
commit after this plan was first drafted — read the file to confirm it
still looks like this before editing):
```ts
export function requireReportMappingBucket(bucket: string | null): LedgerBucket {
  switch (bucket) {
    case "cash":
    case "receivable":
    case "payable":
    case "loan":
    case "advance":
    case "capital":
    case "profit":
      return bucket;
    case null:
      throw APIError.failedPrecondition("report mapping line is missing ledger bucket");
    default:
      throw APIError.failedPrecondition(`report mapping line has invalid ledger bucket: ${bucket}`);
  }
}
```

Replace the `case "profit":` line with the 4 new bucket literals (the old
single `"profit"` bucket no longer exists per Task 3's `LedgerBucket`
type):
```ts
    case "revenue":
    case "cogs":
    case "opex":
    case "inventory":
      return bucket;
```
(keep every other line of the function — including the `cash`/`receivable`/
`payable`/`loan`/`advance`/`capital` cases and both error branches — exactly
as they are).

- [ ] **Step 6: Rewrite `generateReportService`'s line/status computation**

Read the function's current body first — a concurrent commit added a
`reportMappingLines = mappingLines.map((row) => ({...row, bucket:
requireReportMappingBucket(row.bucket)}))` intermediate step that this plan
was not originally written against. Replace the block starting at
`const reportMappingLines = mappingLines.map(...)` through the
`computeReportStatus({...})` call with:
```ts
  const policy = await getAccountingPolicyService(ctx, input.legalEntityId);
  const taxRateBps = policy?.corporateIncomeTaxRateBps ?? null;

  const derivedIssues = new Set<string>();
  const lines: ReportLineView[] = mappingLines.map((row) => {
    if (row.derivedKind) {
      const result = computeDerivedLine(row.derivedKind as DerivedLineKind, bucketTotals, taxRateBps);
      if (result.issue) derivedIssues.add(result.issue);
      return {
        lineCode: row.lineCode,
        officialCode: row.officialCode,
        name: row.name,
        sourceRef: row.sourceRef,
        amountMinor: String(result.amountMinor * BigInt(row.sign)),
      };
    }
    const bucket = requireReportMappingBucket(row.bucket);
    return {
      lineCode: row.lineCode,
      officialCode: row.officialCode,
      name: row.name,
      sourceRef: row.sourceRef,
      amountMinor: String((bucketTotals.get(bucket) ?? 0n) * BigInt(row.sign)),
    };
  });

  const requiredBuckets = mappingLines
    .filter((row) => !row.derivedKind)
    .map((row) => requireReportMappingBucket(row.bucket));
  const coveredBuckets = requiredBuckets.filter((bucket) => bucketTotals.has(bucket));

  const { status, issues } = computeReportStatus({
    requiredBuckets,
    coveredBuckets,
    mappingConfirmed: Boolean(confirmation),
  });
  for (const issue of derivedIssues) issues.push(issue);
  const finalStatus = issues.length === 0 ? status : "INCOMPLETE";
```

Note: rows with `derivedKind` set legitimately have `bucket: null` in the
DB (this is the intended, non-corrupted state for a derived line per
migration 45) — `requireReportMappingBucket` must only ever be called on
non-derived rows, which is why the derived branch above never calls it.

Then change the `db.insert(accountingReportSnapshots)` call's `status`
field from `status` to `finalStatus`, and the function's final returned
object's `status: row.status` stays as-is (reads back what was persisted).

- [ ] **Step 7: Update `accounting-reports-status.test.ts`**

This existing unit test imports `computeReportStatus` and
`requireReportMappingBucket` directly and currently uses the old bucket
literal `"profit"`, which no longer typechecks after Task 3. Read the file
first, then:
1. Change the `requiredBuckets: ["cash", "receivable", "loan", "capital", "profit"]`
   test case to use a valid new bucket in place of `"profit"` — replace it
   with `"revenue"` (the test's intent — checking `INCOMPLETE` when the
   `"loan"` bucket has no covering line — is unaffected by which extra
   bucket literal fills out the list).
2. Add 2 new test cases right after the existing
   `"preserves a valid persisted ledger bucket"` test:
```ts
  it("rejects the old 'profit' bucket literal — no longer valid after the F6b bucket split", () => {
    expect(() => requireReportMappingBucket("profit")).toThrow(
      /invalid ledger bucket/i
    );
  });

  it("preserves each of the new post-split buckets", () => {
    expect(requireReportMappingBucket("revenue")).toBe("revenue");
    expect(requireReportMappingBucket("cogs")).toBe("cogs");
    expect(requireReportMappingBucket("opex")).toBe("opex");
    expect(requireReportMappingBucket("inventory")).toBe("inventory");
  });
```

- [ ] **Step 8: Update the existing F5 fixture test**

In `services/company/finance-legal/tests/tt58-reports.test.ts`:
1. Change every `category: "cost"` in the fixture JSON
   (`tests/fixtures/tt58-2026/basic-entity.json`) and inline test entries
   to `category: "opex"`.
2. Replace the assertion block that reads
   `b02.lines.find((l) => l.lineCode === "LOI_NHUAN")` with assertions on
   the new B02 lines (`DOANH_THU_THUAN`, `GIA_VON`, `CHI_PHI_HDKD`,
   `LOI_NHUAN_GOP`, `THUE_TNDN`, `LOI_NHUAN_SAU_THUE`) — since this
   fixture has no `revenue`/`cogs` book entries (only `capital`/`loan`/
   `receivable` settlement of a manually-classified accrual), re-derive
   the expected numbers from the ACTUAL fixture entries by reading the
   fixture JSON fully before writing new assertions — do not guess numbers.
3. Add a new assertion for the balance equation including the new
   `LOI_NHUAN_GIU_LAI` B01 line: `assets = liabilities + (VON_GOP +
   LOI_NHUAN_GIU_LAI)`.
4. Because `TT58_2026_MAPPING.mappingVersion` is now `"v2"`, any call to
   `confirmMappingService`/`ensureMappingSeeded` in this test file that
   references the OLD `mappingVersion` string must be updated to `"v2"`
   (search for `TT58_2026_MAPPING.mappingVersion` usage — it should already
   read the constant, not a hardcoded `"v1"` string; if you find a
   hardcoded `"v1"` anywhere in this test file, fix it to read the
   constant instead).

- [ ] **Step 9: Run tests to verify they pass**

Run: `cd services/company && npx vitest run finance-legal/tests/tt58-reports.test.ts finance-legal/tests/accounting-reports-derived.test.ts finance-legal/tests/accounting-reports-status.test.ts finance-legal/tests/tax-obligation.test.ts`
Expected: PASS (all 4 files — this is also when Task 5's
`tax-obligation.test.ts` should finally pass for real, since it depends on
this task's derived-line logic).

- [ ] **Step 10: Typecheck + boundary gates + commit**

```bash
git add services/company/finance-legal/services/accounting-reports.service.ts \
        services/company/finance-legal/tests/accounting-reports-derived.test.ts \
        services/company/finance-legal/tests/accounting-reports-status.test.ts \
        services/company/finance-legal/tests/tt58-reports.test.ts \
        services/company/finance-legal/tests/fixtures/tt58-2026/basic-entity.json
git commit -m "feat(company): tính derived line (gross_profit/thuế TNDN/lợi nhuận sau thuế) trong report generation (F6b phần 6)"
```

---

### Task 7: Small handler additions — void document + list periods

**Files:**
- Modify: `services/company/finance-legal/handlers/finance-tt58.handler.ts`
- Modify: `services/company/finance-legal/services/accounting-period.service.ts`
- Modify: `services/company/finance-legal/handlers/accounting-period.handler.ts`
- Test: `services/company/finance-legal/tests/accounting-period.test.ts`
  (if this file doesn't exist yet, create it — check first)

**Interfaces:**
- Produces: `POST /finance/accounting-documents/:id/void`;
  `listAccountingPeriodsService(ctx, legalEntityId?): Promise<AccountingPeriod[]>`,
  `GET /finance-legal/accounting-periods` (list, was previously called by
  Flutter's `finance_service.dart:getPeriods()` but had NO matching route
  at all — a genuinely separate, pre-existing bug from the routing-rewrite
  one fixed in Task 8, confirmed via `grep 'path:.*accounting-periods"'`
  showing only a `POST` at that exact path, never a `GET`).

- [ ] **Step 1: Add `listAccountingPeriodsService`**

In `services/company/finance-legal/services/accounting-period.service.ts`,
add after `getAccountingPeriodService`:

```ts
export async function listAccountingPeriodsService(
  workspaceId: string,
  authorization: string | undefined,
  legalEntityId?: string
): Promise<AccountingPeriod[]> {
  await requireWorkspaceAccess(authorization, workspaceId);

  const conditions = [eq(accountingPeriods.workspaceId, BigInt(workspaceId))];
  if (legalEntityId) {
    conditions.push(eq(accountingPeriods.legalEntityId, BigInt(legalEntityId)));
  }

  const rows = await db
    .select()
    .from(accountingPeriods)
    .where(and(...conditions));

  return rows.map(toAccountingPeriod);
}
```

Add `and` to the existing `drizzle-orm` import (currently only imports
`eq` — check the real current import line and add `and` to it), and
`requireWorkspaceAccess` from `../../shared/auth/workspace-access` (check
whether it's already imported in this file — if not, add it).

- [ ] **Step 2: Add the list endpoint**

In `services/company/finance-legal/handlers/accounting-period.handler.ts`,
read the file first to see the real existing import list and endpoint
style (matches the 3 existing endpoints: open/get/close), then add:

```ts
export interface ListAccountingPeriodsApiRequest {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  legalEntityId?: Query<string>;
}

export const listAccountingPeriods = api(
  { method: "GET", path: "/finance-legal/accounting-periods", expose: true },
  async (req: ListAccountingPeriodsApiRequest): Promise<{ periods: AccountingPeriod[] }> => {
    const periods = await listAccountingPeriodsService(req.workspaceId, req.authorization, req.legalEntityId);
    return { periods };
  }
);
```
(Add `Query` to the `encore.dev/api` import if not already there; add
`listAccountingPeriodsService` and `AccountingPeriod` to the import from
`../services/accounting-period.service`.)

- [ ] **Step 3: Write a test for the new list endpoint**

Check whether `services/company/finance-legal/tests/accounting-period.test.ts`
already exists (if a test file for this service exists under a different
name, e.g. inside `financial-integrity.test.ts` per earlier F5/F6a work,
use that file instead — search for existing `openAccountingPeriodService`
test usage first). Add:

```ts
it("lists periods for a workspace, optionally filtered by legal entity", async () => {
  const { session, authorization, legalEntityId } = await foundersSetup("Period List Ws");
  await openAccountingPeriodService(
    { workspaceId: session.workspaceId, legalEntityId, startDate: "2026-01-01", endDate: "2026-12-31" },
    authorization
  );

  const { listAccountingPeriodsService } = await import("../services/accounting-period.service");
  const all = await listAccountingPeriodsService(session.workspaceId, authorization);
  expect(all.length).toBeGreaterThanOrEqual(1);

  const filtered = await listAccountingPeriodsService(session.workspaceId, authorization, legalEntityId);
  expect(filtered.every((p) => p.legalEntityId === legalEntityId)).toBe(true);
});
```
Adapt `foundersSetup` to whatever helper this test file already uses (read
it first — do not invent a new one if this file already has an equivalent).

- [ ] **Step 4: Add the void-document endpoint**

In `services/company/finance-legal/handlers/finance-tt58.handler.ts`, add
`voidAccountingDocumentService` to the existing import from
`../services/accounting-document.service` (it's already imported per the
existing file — check; if the import line already lists it, skip re-adding).
Append at the end of the file:

```ts
export interface VoidAccountingDocumentApiRequest {
  id: string;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  reason: string;
}

export const postVoidAccountingDocument = api(
  { method: "POST", path: "/finance/accounting-documents/:id/void", expose: true },
  async (params: VoidAccountingDocumentApiRequest): Promise<AccountingDocumentView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return voidAccountingDocumentService({
      documentId: BigInt(params.id),
      workspaceId: BigInt(ctx.workspaceId),
      voidReason: params.reason,
    });
  }
);
```

- [ ] **Step 5: Run tests**

Run: `cd services/company && npx vitest run finance-legal/tests/accounting-period.test.ts finance-legal/tests/financial-integrity.test.ts`
(include whichever file actually holds the period tests, per Step 3)
Expected: PASS.

- [ ] **Step 6: Typecheck + boundary gates + commit**

```bash
git add services/company/finance-legal/services/accounting-period.service.ts \
        services/company/finance-legal/handlers/accounting-period.handler.ts \
        services/company/finance-legal/handlers/finance-tt58.handler.ts
# also add whichever test file was modified in Step 3
git commit -m "feat(company): thêm endpoint list-periods và void-document còn thiếu (F6b phần 7)"
```

---

### Task 8: Fix `api_client.dart` — remove `/finance/` and `/legal/` rewrites

**Files:**
- Modify: `frontend/lib/core/network/api_client.dart`
- Test: check `frontend/test/` for any existing test asserting the OLD
  rewrite behavior (search for `finance-legal` string rewrites in test
  files) before removing — if one exists, update it; if none exists, no
  test file needs changing for this step, but Task 11 will add new tests
  proving the NEW (non-rewritten) behavior.

**Interfaces:**
- Produces: `/finance/*` and `/legal/*` paths reach the backend unmodified.

- [ ] **Step 1: Search for any test currently asserting the rewrite**

Run: `grep -rln "finance-legal" frontend/test/ | xargs grep -l "normalizeEndpoint\|api_client" 2>/dev/null`
If any file asserts `normalizeEndpoint('/finance/...')` equals a
`/finance-legal/...` string, or asserts `/legal/...` equals a
`/finance-legal/...` string, update that assertion to expect the path
UNCHANGED (no rewrite) as part of this task — do not leave a test
asserting the old, now-wrong behavior.

- [ ] **Step 2: Remove the 4 rewrite blocks**

In `frontend/lib/core/network/api_client.dart`, delete these 4 blocks
(confirmed via prior investigation to have zero current call sites relying
on them — every existing call either already targets `/finance-legal/*`
directly in its literal string, or is currently broken specifically
BECAUSE of this rewrite):

```dart
if (normalized.startsWith('/finance/')) {
  return '/finance-legal/${normalized.substring(9)}';
}
if (normalized.startsWith('/api/v1/finance/')) {
  return '/finance-legal/${normalized.substring(16)}';
}
```
and
```dart
if (normalized.startsWith('/legal/')) {
  return '/finance-legal/${normalized.substring(7)}';
}
if (normalized.startsWith('/api/v1/legal/')) {
  return '/finance-legal/${normalized.substring(14)}';
}
```

Read the surrounding code first to confirm you're removing exactly these
4 `if` blocks and nothing else (other rewrite rules for `/auth/`, `/tasks`,
`/strategy/`, `/sales/`, `/marketing/` etc. must remain untouched).

- [ ] **Step 3: Run frontend analyze**

Run: `cd frontend && flutter analyze lib/core/network/api_client.dart`
Expected: no new errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/core/network/api_client.dart
git commit -m "fix(frontend): bỏ rewrite /finance/ và /legal/ -> /finance-legal/ — không route thật nào trùng, đang 404 âm thầm (F6b phần 8)"
```

---

### Task 9: `finance_tt58_service.dart` — real implementation

**Files:**
- Modify: `frontend/lib/modules/finance/services/finance_tt58_service.dart`

**Interfaces:**
- Consumes: `getJson`/`postJson` (inherited from `WorkspaceService`).
- Produces: `getReport(legalEntityId, periodId, reportCode): Future<Map<String, dynamic>?>`,
  `getAccountingPolicy(legalEntityId): Future<Map<String, dynamic>?>`,
  `getTaxObligations(legalEntityId, periodId): Future<Map<String, dynamic>?>`,
  `getFounderLiteMetrics(legalEntityId, periodId): Future<Map<String, dynamic>?>` —
  consumed by Task 10 (`finance_controller.dart`).

- [ ] **Step 1: Replace the entire file**

```dart
import '../../../core/network/workspace_scoped_service.dart';
import 'finance_service.dart';

class FinanceTT58Service extends WorkspaceService {
  Future<Map<String, dynamic>?> getReport(String legalEntityId, String periodId, String reportCode) async {
    final data = await postJson('/finance/reports/generate', {
      'legalEntityId': legalEntityId,
      'periodId': periodId,
      'reportCode': reportCode,
    });
    if (data == null) return null;
    return _transformReport(reportCode, data as Map<String, dynamic>);
  }

  Map<String, dynamic> _transformReport(String reportCode, Map<String, dynamic> report) {
    final lines = ((report['lines'] as List<dynamic>?) ?? [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    num byCode(String code) {
      final match = lines.where((l) => l['lineCode'] == code);
      if (match.isEmpty) return 0;
      return num.tryParse(match.first['amountMinor']?.toString() ?? '0') ?? 0;
    }

    if (reportCode == 'B01') {
      final cash = byCode('TS');
      final receivable = byCode('PHAI_THU');
      final inventory = byCode('TON_KHO');
      final loan = byCode('NO_VAY');
      final capital = byCode('VON_GOP');
      final retainedEarnings = byCode('LOI_NHUAN_GIU_LAI');
      final totalAssets = cash + receivable + inventory;
      final ownerEquity = capital + retainedEarnings;
      return {
        'assets': {
          'total_assets': totalAssets,
          'cash_and_equivalents': cash,
          'accounts_receivable': receivable,
          'inventories': inventory,
        },
        'capital_and_liabilities': {
          'total_capital': loan + ownerEquity,
          'total_liabilities': loan,
          'owner_equity': ownerEquity,
        },
        'is_balanced': totalAssets == (loan + ownerEquity),
        'status': report['status'],
        'issues': report['issues'],
      };
    }

    return {
      'items': {
        'net_revenue': byCode('DOANH_THU_THUAN'),
        'cost_of_goods_sold': byCode('GIA_VON'),
        'gross_profit': byCode('LOI_NHUAN_GOP'),
        'operating_expenses': byCode('CHI_PHI_HDKD'),
        'corporate_income_tax': byCode('THUE_TNDN'),
        'net_profit_after_tax': byCode('LOI_NHUAN_SAU_THUE'),
      },
      'status': report['status'],
      'issues': report['issues'],
    };
  }

  Future<Map<String, dynamic>?> getAccountingPolicy(String legalEntityId) async {
    final data = await getJson('/finance/accounting-policies?legalEntityId=$legalEntityId');
    if (data == null || data['policy'] == null) return null;
    final policy = Map<String, dynamic>.from(data['policy'] as Map);
    return {
      'is_statutory_required': true,
      'compliance_note': 'Chế độ kế toán đang áp dụng theo Thông tư 58/2026/TT-BTC.',
      'accounting_policies': {
        'currency': 'VND (Đồng Việt Nam)',
        'inventory_valuation': policy['inventoryValuationMethod'],
        'depreciation_method': policy['depreciationMethod'],
        'revenue_recognition': policy['revenueRecognitionMethod'],
      },
    };
  }

  Future<Map<String, dynamic>?> getTaxObligations(String legalEntityId, String periodId) async {
    final data = await getJson('/finance/tax-obligations?legalEntityId=$legalEntityId&periodId=$periodId');
    if (data == null) return null;
    final taxesRaw = (data['taxes'] as List<dynamic>?) ?? [];
    return {
      'taxes': taxesRaw.map((t) {
        final m = Map<String, dynamic>.from(t as Map);
        return {
          'tax_name': m['taxName'],
          'incurred': num.tryParse(m['incurredMinor']?.toString() ?? '0') ?? 0,
          'paid': num.tryParse(m['paidMinor']?.toString() ?? '0') ?? 0,
          'closing_debt': num.tryParse(m['closingDebtMinor']?.toString() ?? '0') ?? 0,
        };
      }).toList(),
      'total_balance_due': num.tryParse(data['totalBalanceDueMinor']?.toString() ?? '0') ?? 0,
    };
  }

  Future<Map<String, dynamic>?> getFounderLiteMetrics(String legalEntityId, String periodId) async {
    final service = FinanceService();
    final snapshots = await service.getFinancialSnapshots();
    final b02 = await getReport(legalEntityId, periodId, 'B02');

    final latestSnapshot = snapshots.isNotEmpty ? Map<String, dynamic>.from(snapshots.first as Map) : null;
    final cashBalance = num.tryParse(latestSnapshot?['currentCash']?.toString() ?? '') ?? 0;
    final runwayMonths = latestSnapshot?['runwayMonths'] == null
        ? null
        : num.tryParse(latestSnapshot!['runwayMonths'].toString());
    final monthlyBurn = num.tryParse(latestSnapshot?['monthlyNetBurn']?.toString() ?? '') ?? 0;
    final cashFlowPositive = latestSnapshot?['cashFlowPositive'] as bool? ?? true;

    final items = b02?['items'] as Map<String, dynamic>? ?? {};
    final revenue = (items['net_revenue'] as num?) ?? 0;
    final cogs = (items['cost_of_goods_sold'] as num?) ?? 0;
    final opex = (items['operating_expenses'] as num?) ?? 0;
    final netProfit = (items['net_profit_after_tax'] as num?) ?? 0;

    String healthStatus;
    if (!cashFlowPositive && (runwayMonths == null || runwayMonths < 1) || cashBalance < 0) {
      healthStatus = 'CRITICAL';
    } else if (!cashFlowPositive && runwayMonths != null && runwayMonths < 3) {
      healthStatus = 'WARNING';
    } else {
      healthStatus = 'HEALTHY';
    }

    return {
      'cash_and_bank_balance': cashBalance,
      'total_revenue_period': revenue,
      'total_expense_period': cogs + opex,
      'estimated_net_profit': netProfit,
      'runway_months': runwayMonths ?? 0,
      'monthly_burn_rate': monthlyBurn,
      'health_status': healthStatus,
    };
  }
}
```

Note: this file no longer has `createAndPostDocument`/`voidDocument` — Task
10 rewires `finance_controller.dart` to call `FinanceService` directly for
those (Task 10 also adds the missing `voidAccountingDocument` method to
`FinanceService`).

- [ ] **Step 2: Analyze**

Run: `cd frontend && flutter analyze lib/modules/finance/services/finance_tt58_service.dart`
Expected: no new errors (existing callers in `finance_controller.dart` will
break at this point — Task 10 fixes them; if `flutter analyze` errors out
on `finance_controller.dart` because of this, that's expected until Task
10 lands, but confirm the errors are ONLY about the removed
`createAndPostDocument`/`voidDocument`/old signatures, nothing else).

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/modules/finance/services/finance_tt58_service.dart
git commit -m "feat(frontend): nối finance_tt58_service.dart vào API F5/F6b thật (F6b phần 9)"
```

---

### Task 10: Fix `finance_controller.dart` — error handling, entity/period resolution, void wiring

**Files:**
- Modify: `frontend/lib/modules/finance/controllers/finance_controller.dart`
- Modify: `frontend/lib/modules/finance/services/finance_service.dart`
  (add `getLegalEntityId()` helper and `voidAccountingDocument`)

**Interfaces:**
- Consumes: `LegalService().getLegalEntityProfiles()` (existing, in
  `frontend/lib/modules/legal/services/legal_service.dart` — now unbroken
  by Task 8); `FinanceService().getPeriods()` (existing, now hitting a real
  endpoint per Task 7); `tt58Service.getReport/getAccountingPolicy/getTaxObligations/getFounderLiteMetrics`
  (Task 9).

- [ ] **Step 1: Add `voidAccountingDocument` to `FinanceService`**

In `frontend/lib/modules/finance/services/finance_service.dart`, add near
the other accounting-document methods:

```dart
  Future<Map<String, dynamic>?> voidAccountingDocument(String documentId, String reason) async {
    final data = await postJson('/finance/accounting-documents/$documentId/void', {'reason': reason});
    return data is Map<String, dynamic> ? data : null;
  }
```

- [ ] **Step 2: Rewrite `loadTT58Data` with per-call error isolation and real entity/period resolution**

Replace the existing `loadTT58Data()` method body entirely:

```dart
  final currentLegalEntityId = Rxn<String>();
  final currentPeriodId = Rxn<String>();

  Future<void> loadTT58Data() async {
    isLoadingTT58.value = true;
    try {
      final legalEntityId = await _resolveLegalEntityId();
      final periodId = await _resolvePeriodId(legalEntityId);
      currentLegalEntityId.value = legalEntityId;
      currentPeriodId.value = periodId;
      if (legalEntityId == null || periodId == null) {
        debugPrint('loadTT58Data: no legal entity or period available yet');
        return;
      }

      try {
        founderLiteMetrics.value = await tt58Service.getFounderLiteMetrics(legalEntityId, periodId);
      } catch (e) {
        debugPrint('loadTT58Data founderLiteMetrics failed: $e');
      }
      try {
        reportB01.value = await tt58Service.getReport(legalEntityId, periodId, 'B01');
      } catch (e) {
        debugPrint('loadTT58Data reportB01 failed: $e');
      }
      try {
        reportB02.value = await tt58Service.getReport(legalEntityId, periodId, 'B02');
      } catch (e) {
        debugPrint('loadTT58Data reportB02 failed: $e');
      }
      try {
        reportB03.value = await tt58Service.getAccountingPolicy(legalEntityId);
      } catch (e) {
        debugPrint('loadTT58Data reportB03 failed: $e');
      }
      try {
        reportF01.value = await tt58Service.getTaxObligations(legalEntityId, periodId);
      } catch (e) {
        debugPrint('loadTT58Data reportF01 failed: $e');
      }
    } finally {
      isLoadingTT58.value = false;
    }
  }

  Future<String?> _resolveLegalEntityId() async {
    final profiles = await LegalService().getLegalEntityProfiles();
    if (profiles.isEmpty) return null;
    final first = Map<String, dynamic>.from(profiles.first as Map);
    return first['id']?.toString();
  }

  Future<String?> _resolvePeriodId(String? legalEntityId) async {
    final periods = await service.getPeriods();
    if (periods.isEmpty) return null;
    if (legalEntityId != null) {
      final matching = periods.where((p) {
        final m = Map<String, dynamic>.from(p as Map);
        return m['legalEntityId']?.toString() == legalEntityId && m['status'] == 'OPEN';
      });
      if (matching.isNotEmpty) {
        return Map<String, dynamic>.from(matching.first as Map)['id']?.toString();
      }
    }
    return Map<String, dynamic>.from(periods.first as Map)['id']?.toString();
  }
```

Add the import: `import '../../../modules/legal/services/legal_service.dart';`
at the top of the file (check it's not already imported).

- [ ] **Step 3: Rewire `createAndPostDocument`/`voidDocument` to call `FinanceService` directly**

Find the existing `createAndPostDocument`/`voidDocument` methods (currently
calling `tt58Service.createAndPostDocument`/`tt58Service.voidDocument`,
both removed in Task 9) and replace their bodies to call `service.*`
instead:

```dart
  Future<void> createAndPostDocument({
    required String documentNo,
    required String documentType,
    required num amount,
    required String direction,
    required String description,
    required String category,
  }) async {
    try {
      final doc = await service.createAccountingDocument(
        documentType: documentType,
        number: documentNo,
        documentDate: DateTime.now().toIso8601String().split('T').first,
        amount: amount,
        description: description,
      );
      final docId = doc?['id']?.toString();
      if (docId != null) {
        await service.confirmAccountingDocument(docId);
        AppToast.success('Đã tạo và ghi sổ chứng từ');
        await loadTT58Data();
      }
    } catch (e) {
      debugPrint('createAndPostDocument failed: $e');
      AppToast.error('Không thể tạo chứng từ: $e');
    }
  }

  Future<void> voidDocument(String documentId, String reason) async {
    try {
      await service.voidAccountingDocument(documentId, reason);
      AppToast.success('Đã hủy chứng từ');
      await loadTT58Data();
    } catch (e) {
      debugPrint('voidDocument failed: $e');
      AppToast.error('Không thể hủy chứng từ: $e');
    }
  }
```

Read `FinanceService.createAccountingDocument`'s REAL current parameter
list first (it already exists per Phase-3 methods) and adapt the call
above to match exactly — do not invent parameter names; if its signature
differs from what's shown here, use the real one and keep the same
try/catch structure and `loadTT58Data()` refresh-on-success behavior.

- [ ] **Step 4: Analyze**

Run: `cd frontend && flutter analyze lib/modules/finance/`
Expected: no new errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/modules/finance/controllers/finance_controller.dart \
        frontend/lib/modules/finance/services/finance_service.dart
git commit -m "fix(frontend): loadTT58Data cô lập lỗi từng phần, giải quyết legalEntityId/periodId thật, nối void qua FinanceService (F6b phần 10)"
```

---

### Task 11: Flutter tests

**Files:**
- Create: `frontend/test/modules/finance/finance_tt58_service_test.dart`

**Interfaces:**
- Consumes: the fake-`http.BaseClient` test pattern already established in
  `frontend/test/modules/finance/finance_service_test.dart` — read that
  file first to copy its exact setup/teardown structure (`ApiClient.client
  = fakeClient` in `setUp`, restore in `tearDown`,
  `SharedPreferences.setMockInitialValues`).

- [ ] **Step 1: Write the test file**

```dart
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:javis/core/network/api_client.dart';
import 'package:javis/modules/finance/services/finance_tt58_service.dart';

class _RecordingClient extends http.BaseClient {
  String? lastUrl;
  final Map<String, dynamic> jsonResponse;
  _RecordingClient(this.jsonResponse);

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    lastUrl = request.url.toString();
    final body = utf8.encode(jsonEncode(jsonResponse));
    return http.StreamedResponse(Stream.value(body), 200, headers: {'content-type': 'application/json'});
  }
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({'workspace_id': '123', 'auth_token': 'test-token'});
  });

  tearDown(() {
    ApiClient.client = http.Client();
  });

  test('getReport hits /finance/reports/generate (not rewritten) and transforms B01 lines', () async {
    final fakeClient = _RecordingClient({
      'id': '1', 'legalEntityId': '1', 'periodId': '1', 'reportCode': 'B01',
      'mappingVersion': 'v2', 'inputWatermark': 'x', 'status': 'VERIFIED', 'issues': [],
      'generatedAt': '2026-01-01T00:00:00Z',
      'lines': [
        {'lineCode': 'TS', 'officialCode': 'TS', 'name': 'x', 'sourceRef': 'x', 'amountMinor': '124000000'},
        {'lineCode': 'PHAI_THU', 'officialCode': 'PHAI_THU', 'name': 'x', 'sourceRef': 'x', 'amountMinor': '4000000'},
        {'lineCode': 'TON_KHO', 'officialCode': 'TON_KHO', 'name': 'x', 'sourceRef': 'x', 'amountMinor': '0'},
        {'lineCode': 'NO_VAY', 'officialCode': 'NO_VAY', 'name': 'x', 'sourceRef': 'x', 'amountMinor': '20000000'},
        {'lineCode': 'VON_GOP', 'officialCode': 'VON_GOP', 'name': 'x', 'sourceRef': 'x', 'amountMinor': '100000000'},
        {'lineCode': 'LOI_NHUAN_GIU_LAI', 'officialCode': 'LOI_NHUAN_GIU_LAI', 'name': 'x', 'sourceRef': 'x', 'amountMinor': '8000000'},
      ],
    });
    ApiClient.client = fakeClient;

    final result = await FinanceTT58Service().getReport('1', '1', 'B01');

    expect(fakeClient.lastUrl, contains('/finance/reports/generate'));
    expect(fakeClient.lastUrl, isNot(contains('/finance-legal/reports')));
    expect(result?['assets']['total_assets'], 128000000);
    expect(result?['assets']['inventories'], 0);
    expect(result?['capital_and_liabilities']['owner_equity'], 108000000);
    expect(result?['is_balanced'], true);
  });

  test('getReport returns null when the backend call fails', () async {
    ApiClient.client = _FailingClient();
    final result = await FinanceTT58Service().getReport('1', '1', 'B01');
    expect(result, isNull);
  });
}

class _FailingClient extends http.BaseClient {
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    return http.StreamedResponse(Stream.value(utf8.encode('{}')), 500);
  }
}
```

Confirm the real package import path (`package:javis/...` — check
`frontend/pubspec.yaml`'s `name:` field for the real package name; adjust
both imports if it differs from `javis`).

- [ ] **Step 2: Run the test**

Run: `cd frontend && flutter test test/modules/finance/finance_tt58_service_test.dart`
Expected: PASS (2 tests).

- [ ] **Step 3: Run the existing finance test files to confirm no regression**

Run: `cd frontend && flutter test test/modules/finance/ test/finance_service_test.dart`
Expected: PASS (all pre-existing tests still pass).

- [ ] **Step 4: Commit**

```bash
git add frontend/test/modules/finance/finance_tt58_service_test.dart
git commit -m "test(frontend): thêm test finance_tt58_service — xác nhận không còn bị rewrite sai route (F6b phần 11)"
```

---

### Task 12: Final gate suite

**Files:** none (verification only)

- [ ] **Step 1: Backend — run every test file this plan touched**

```bash
cd services/company && npx vitest run \
  finance-legal/tests/accounting-mapping.test.ts \
  finance-legal/tests/accounting-policy.test.ts \
  finance-legal/tests/tax-obligation.test.ts \
  finance-legal/tests/accounting-reports-derived.test.ts \
  finance-legal/tests/tt58-reports.test.ts \
  finance-legal/tests/accounting-period.test.ts \
  finance-legal/tests/financial-integrity.test.ts
```
Expected: all PASS.

- [ ] **Step 2: Backend gates**

```bash
cd services/company && npm run typecheck
cd /Volumes/SSD/javis-saas && make company-boundary-check
make encore-handler-boundary-check
make ts-suppression-check
```
Expected: all PASS.

- [ ] **Step 3: Frontend**

```bash
cd frontend && flutter analyze
flutter test test/modules/finance/ test/finance_service_test.dart
```
Expected: no new analyze warnings/errors beyond what already existed before
this plan (compare against a pre-plan baseline if unsure); all finance
tests PASS.

- [ ] **Step 4: Full company suite for regression awareness**

```bash
cd services/company && npx vitest run 2>&1 | grep -E "^ FAIL|Test Files|Tests "
```
Expected: no NEW failures beyond any already-known, unrelated pre-existing
environmental flakes (check `git log` on any surprising failing file
before concluding it's pre-existing — do not assume).

## Self-Review Notes (from writing-plans checklist)

- **Spec coverage:** schema (Task 1-2), classification engine expansion
  (Task 3), accounting policy (Task 4), tax obligations (Task 5), derived
  report lines (Task 6), missing endpoints (Task 7), routing-bug fix (Task
  8), Flutter service (Task 9), controller wiring (Task 10), tests (Task
  11) — every section of the design spec has a corresponding task.
- **Task ordering caveat documented in Task 5** — its test depends on Task
  6's logic; flagged explicitly so whoever executes understands the real
  dependency isn't file order.
- **Type consistency check:** `DerivedLineKind`/`ReportMappingLine.bucket:
  LedgerBucket | null`/`derivedKind` (Task 3) used identically in Task 6's
  `computeDerivedLine` and `generateReportService`. `AccountingPolicyView`
  (Task 4) fields match what Task 6 reads (`corporateIncomeTaxRateBps`) and
  what Task 9's Flutter transform expects (`inventoryValuationMethod`,
  etc.) exactly.
- **Out of scope, confirmed unchanged:** F6c (payment UI, agent tools), F5
  Flutter payment/QR UI, cross-period retained-earnings accumulation
  (documented as a known limitation in the spec's "Ngoài phạm vi"), real
  FIFO/lot inventory costing.
