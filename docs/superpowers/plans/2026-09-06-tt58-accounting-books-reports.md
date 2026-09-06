# F5 — TT58 Accounting Books & Reports Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a backend engine in `services/company/finance-legal` that
generates entity-scoped, period-scoped TT58 accounting books and reports
from classified book entries, using a founder-confirmable mapping registry
instead of throwing `UnimplementedError`.

**Architecture:** New Drizzle tables extend the existing `accounting_periods`
(F1's period-lock concept) and `accounting_fiscal_profiles` (regime/mode
selection) tables — both already exist and must not be duplicated. Mapping
content (TT58 report-line definitions) is authored once in
`accounting-mapping.ts`, seeded into a DB registry table keyed by content
hash (same exact-hash pattern already used for `AgentSpec`/skillpack
registries in `apps/cosa`), and only reaches `status=VERIFIED` after a
founder confirms it via an authenticated endpoint (reusing
`requireFounderCommand`, already used for IA01/IA19). Book entries reuse
F1's existing posting-lock guard (`assertOpenPostingPeriod`) so a closed
period cannot receive new entries, but report generation for a closed
period is explicitly allowed (that's when reports are normally finalized).

**Tech Stack:** Encore.ts, Drizzle ORM, PostgreSQL, Vitest (via `encore test`).

**Spec:** `docs/superpowers/specs/2026-09-06-tt58-accounting-books-reports-design.md`

## Global Constraints

- `services/company/finance-legal` handlers must not import `drizzle-orm`,
  `models/db`, or DB schema directly — only call service functions (Encore
  Guardrail #1).
- Business-facing errors go through `APIError` (`invalidArgument`,
  `unauthenticated`, `permissionDenied`, `notFound`, `alreadyExists`,
  `internal`, `failedPrecondition`) — never a bare `Error`.
- No `any`, `@ts-ignore`, `@ts-expect-error`, or casts to bypass typecheck.
- All amounts are `NUMERIC(38,0)` minor-unit strings (VND has no minor
  unit smaller than 1 đồng, so "minor" = whole đồng here) — never
  JavaScript `number`/`double` for money.
- Migration release is Expand-only — this plan only adds columns/tables,
  never drops or renames existing ones.
- A report/mapping never reaches `status=VERIFIED` without a real founder
  confirmation recorded in `accounting_mapping_confirmations` — no code
  path may set `VERIFIED` any other way.
- Do not fabricate official TT58 legal citations. Every mapping line's
  `sourceRef` must say plainly it is unverified until a human confirms it
  against the real circular text — this is a requirement from the spec,
  not an omission to fix later.

---

### Task 1: Migration — schema for periods, fiscal profiles, and new TT58 tables

**Files:**
- Create: `services/company/finance-legal/migrations/42_tt58_accounting_reports.up.sql`
- Create: `services/company/finance-legal/migrations/42_tt58_accounting_reports.down.sql`

**Interfaces:**
- Produces: tables `finance.accounting_book_entries`,
  `finance.accounting_report_snapshots`, `finance.accounting_report_mappings`,
  `finance.accounting_mapping_confirmations`; new columns
  `accounting_periods.fiscal_profile_id`, `accounting_periods.version`,
  `accounting_fiscal_profiles.legal_entity_id`,
  `accounting_fiscal_profiles.year_end`,
  `accounting_fiscal_profiles.mapping_version`,
  `accounting_fiscal_profiles.applicability_decision_id`.

- [ ] **Step 1: Write the up migration**

```sql
-- Migration 42: F5 — TT58 accounting books & reports engine
-- (docs/superpowers/specs/2026-09-06-tt58-accounting-books-reports-design.md)
--
-- accounting_periods = "kỳ" (F1 posting lock, đã entity-scoped từ migration 35).
-- accounting_fiscal_profiles = chọn regime/mode TT58 cho một năm (migration 5).
-- Đây là 2 bảng khác nhau đã tồn tại — migration này mở rộng cả hai, không
-- tạo bảng "fiscal profile" hay "period" song song.

ALTER TABLE finance.accounting_periods
  ADD COLUMN IF NOT EXISTS fiscal_profile_id BIGINT
    REFERENCES finance.accounting_fiscal_profiles(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;

ALTER TABLE finance.accounting_fiscal_profiles
  ADD COLUMN IF NOT EXISTS legal_entity_id BIGINT,
  ADD COLUMN IF NOT EXISTS year_end DATE,
  ADD COLUMN IF NOT EXISTS mapping_version VARCHAR(50),
  ADD COLUMN IF NOT EXISTS applicability_decision_id BIGINT;

-- Unique cũ (workspace_id, fiscal_year) không phân biệt pháp nhân — đổi
-- sang unique index NULL-safe theo đúng kỹ thuật migration 38 (IA12).
ALTER TABLE finance.accounting_fiscal_profiles
  DROP CONSTRAINT IF EXISTS uix_fiscal_profile_workspace_year;

CREATE UNIQUE INDEX IF NOT EXISTS uix_fiscal_profile_workspace_entity_year
  ON finance.accounting_fiscal_profiles (workspace_id, COALESCE(legal_entity_id, 0), fiscal_year);

CREATE TABLE finance.accounting_report_mappings (
  id BIGINT PRIMARY KEY,
  regime_code VARCHAR(50) NOT NULL,
  mapping_version VARCHAR(50) NOT NULL,
  report_code VARCHAR(10) NOT NULL,
  line_code VARCHAR(20) NOT NULL,
  official_code VARCHAR(50) NOT NULL,
  name TEXT NOT NULL,
  source_ref TEXT NOT NULL,
  rule_type VARCHAR(20) NOT NULL,
  bucket VARCHAR(20) NOT NULL,
  sign SMALLINT NOT NULL,
  rounding VARCHAR(20) NOT NULL,
  definition_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uix_report_mapping_line UNIQUE (regime_code, mapping_version, report_code, line_code)
);

CREATE TABLE finance.accounting_mapping_confirmations (
  id BIGINT PRIMARY KEY,
  regime_code VARCHAR(50) NOT NULL,
  mapping_version VARCHAR(50) NOT NULL,
  confirmed_by_member_id BIGINT NOT NULL,
  confirmed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uix_mapping_confirmation UNIQUE (regime_code, mapping_version)
);

CREATE TABLE finance.accounting_book_entries (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  legal_entity_id BIGINT NOT NULL,
  period_id BIGINT NOT NULL REFERENCES finance.accounting_periods(id) ON DELETE CASCADE,
  document_id BIGINT REFERENCES finance.accounting_documents(id) ON DELETE SET NULL,
  item TEXT NOT NULL,
  category VARCHAR(30) NOT NULL,
  amount_minor NUMERIC(38, 0) NOT NULL,
  currency VARCHAR(10) NOT NULL DEFAULT 'VND',
  effective_date DATE NOT NULL,
  source TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_book_entries_period ON finance.accounting_book_entries(period_id);
CREATE INDEX idx_book_entries_entity ON finance.accounting_book_entries(legal_entity_id);

CREATE TABLE finance.accounting_report_snapshots (
  id BIGINT PRIMARY KEY,
  workspace_id BIGINT NOT NULL,
  legal_entity_id BIGINT NOT NULL,
  period_id BIGINT NOT NULL REFERENCES finance.accounting_periods(id) ON DELETE CASCADE,
  report_code VARCHAR(10) NOT NULL,
  mapping_version VARCHAR(50) NOT NULL,
  input_watermark TEXT NOT NULL,
  lines JSONB NOT NULL DEFAULT '[]',
  status VARCHAR(20) NOT NULL,
  issues JSONB NOT NULL DEFAULT '[]',
  generated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_report_snapshots_period ON finance.accounting_report_snapshots(period_id, report_code);
```

- [ ] **Step 2: Write the down migration**

```sql
DROP TABLE IF EXISTS finance.accounting_report_snapshots;
DROP TABLE IF EXISTS finance.accounting_book_entries;
DROP TABLE IF EXISTS finance.accounting_mapping_confirmations;
DROP TABLE IF EXISTS finance.accounting_report_mappings;

ALTER TABLE finance.accounting_fiscal_profiles
  DROP CONSTRAINT IF EXISTS uix_fiscal_profile_workspace_entity_year;

CREATE UNIQUE INDEX IF NOT EXISTS uix_fiscal_profile_workspace_year
  ON finance.accounting_fiscal_profiles (workspace_id, fiscal_year);

ALTER TABLE finance.accounting_fiscal_profiles
  DROP COLUMN IF EXISTS applicability_decision_id,
  DROP COLUMN IF EXISTS mapping_version,
  DROP COLUMN IF EXISTS year_end,
  DROP COLUMN IF EXISTS legal_entity_id;

ALTER TABLE finance.accounting_periods
  DROP COLUMN IF EXISTS version,
  DROP COLUMN IF EXISTS fiscal_profile_id;
```

- [ ] **Step 3: Commit**

```bash
git add services/company/finance-legal/migrations/42_tt58_accounting_reports.up.sql \
        services/company/finance-legal/migrations/42_tt58_accounting_reports.down.sql
git commit -m "feat(company): thêm migration schema sổ/báo cáo TT58 (F5 phần 1)"
```

---

### Task 2: Drizzle schema — add table/column definitions

**Files:**
- Modify: `services/company/shared/db/schema/finance-legal.ts:22-34` (accountingPeriods),
  `:90-101` (accountingFiscalProfiles)

**Interfaces:**
- Consumes: migration 42 (Task 1) must be applied for these Drizzle
  definitions to match the real DB shape.
- Produces: exported `accountingPeriods`, `accountingFiscalProfiles`,
  `accountingBookEntries`, `accountingReportSnapshots`,
  `accountingReportMappings`, `accountingMappingConfirmations` — consumed by
  every later task in this plan.

- [ ] **Step 1: Add columns to existing tables**

In `accountingPeriods` (after `endDate`, before `status`):
```ts
  fiscalProfileId: bigint("fiscal_profile_id", { mode: "bigint" }),
  version: integer("version").default(1).notNull(),
```

In `accountingFiscalProfiles` (after `regulationCode`, before `mode`):
```ts
  legalEntityId: bigint("legal_entity_id", { mode: "bigint" }),
  yearEnd: date("year_end"),
  mappingVersion: varchar("mapping_version", { length: 50 }),
  applicabilityDecisionId: bigint("applicability_decision_id", { mode: "bigint" }),
```

- [ ] **Step 2: Add the 4 new table definitions**

Append after `accountingRegimeTransitionLogs` (around line 125):

```ts
export const accountingReportMappings = financeSchema.table("accounting_report_mappings", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  regimeCode: varchar("regime_code", { length: 50 }).notNull(),
  mappingVersion: varchar("mapping_version", { length: 50 }).notNull(),
  reportCode: varchar("report_code", { length: 10 }).notNull(),
  lineCode: varchar("line_code", { length: 20 }).notNull(),
  officialCode: varchar("official_code", { length: 50 }).notNull(),
  name: text("name").notNull(),
  sourceRef: text("source_ref").notNull(),
  ruleType: varchar("rule_type", { length: 20 }).notNull(),
  bucket: varchar("bucket", { length: 20 }).notNull(),
  sign: integer("sign").notNull(),
  rounding: varchar("rounding", { length: 20 }).notNull(),
  definitionHash: text("definition_hash").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const accountingMappingConfirmations = financeSchema.table("accounting_mapping_confirmations", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  regimeCode: varchar("regime_code", { length: 50 }).notNull(),
  mappingVersion: varchar("mapping_version", { length: 50 }).notNull(),
  confirmedByMemberId: bigint("confirmed_by_member_id", { mode: "bigint" }).notNull(),
  confirmedAt: timestamp("confirmed_at", { withTimezone: true }).defaultNow().notNull(),
});

export const accountingBookEntries = financeSchema.table("accounting_book_entries", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  legalEntityId: bigint("legal_entity_id", { mode: "bigint" }).notNull(),
  periodId: bigint("period_id", { mode: "bigint" }).notNull(),
  documentId: bigint("document_id", { mode: "bigint" }),
  item: text("item").notNull(),
  category: varchar("category", { length: 30 }).notNull(),
  amountMinor: numeric("amount_minor", { precision: 38, scale: 0 }).notNull(),
  currency: varchar("currency", { length: 10 }).default("VND").notNull(),
  effectiveDate: date("effective_date").notNull(),
  source: text("source").notNull(),
  version: integer("version").default(1).notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const accountingReportSnapshots = financeSchema.table("accounting_report_snapshots", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  legalEntityId: bigint("legal_entity_id", { mode: "bigint" }).notNull(),
  periodId: bigint("period_id", { mode: "bigint" }).notNull(),
  reportCode: varchar("report_code", { length: 10 }).notNull(),
  mappingVersion: varchar("mapping_version", { length: 50 }).notNull(),
  inputWatermark: text("input_watermark").notNull(),
  lines: jsonb("lines").default([]).notNull(),
  status: varchar("status", { length: 20 }).notNull(),
  issues: jsonb("issues").default([]).notNull(),
  generatedAt: timestamp("generated_at", { withTimezone: true }).defaultNow().notNull(),
});
```

- [ ] **Step 3: Typecheck**

Run: `cd services/company && npm run typecheck`
Expected: no new errors (existing errors, if any, are pre-existing and out
of scope — confirm by diffing error count against `git stash`).

- [ ] **Step 4: Commit**

```bash
git add services/company/shared/db/schema/finance-legal.ts
git commit -m "feat(company): thêm Drizzle schema cho bảng/cột TT58 mới (F5 phần 2)"
```

---

### Task 3: `accounting-mapping.ts` — mapping content, classification rules, hash

**Files:**
- Create: `services/company/finance-legal/services/accounting-mapping.ts`
- Test: `services/company/finance-legal/tests/accounting-mapping.test.ts`

**Interfaces:**
- Consumes: `computeCanonicalSha256` from
  `./compliance/canonical-hasher.ts`.
- Produces: `BookEntryCategory`, `LedgerBucket`, `classifyBookEntry(category, amountMinor): BucketEffect[]`,
  `ReportMappingLine`, `RegimeMapping`, `TT58_2026_MAPPING`,
  `computeMappingDefinitionHash(mapping): string` — consumed by Task 4
  (books), Task 5 (reports), Task 6 (confirmation).

- [ ] **Step 1: Write the failing test for classification rules**

```ts
import { describe, expect, it } from "vitest";
import { classifyBookEntry } from "../services/accounting-mapping";

describe("accounting-mapping — classifyBookEntry", () => {
  it("capital increases cash and capital equity", () => {
    expect(classifyBookEntry("capital", 100_000_000n)).toEqual([
      { bucket: "cash", amountMinor: 100_000_000n },
      { bucket: "capital", amountMinor: 100_000_000n },
    ]);
  });

  it("loan increases cash and loan liability", () => {
    expect(classifyBookEntry("loan", 20_000_000n)).toEqual([
      { bucket: "cash", amountMinor: 20_000_000n },
      { bucket: "loan", amountMinor: 20_000_000n },
    ]);
  });

  it("revenue accrues to receivable and profit, not cash", () => {
    expect(classifyBookEntry("revenue", 10_000_000n)).toEqual([
      { bucket: "receivable", amountMinor: 10_000_000n },
      { bucket: "profit", amountMinor: 10_000_000n },
    ]);
  });

  it("cost accrues to payable and reduces profit, not cash", () => {
    expect(classifyBookEntry("cost", 2_000_000n)).toEqual([
      { bucket: "payable", amountMinor: 2_000_000n },
      { bucket: "profit", amountMinor: -2_000_000n },
    ]);
  });

  it("receivable settlement reduces receivable and increases cash", () => {
    expect(classifyBookEntry("receivable", 6_000_000n)).toEqual([
      { bucket: "receivable", amountMinor: -6_000_000n },
      { bucket: "cash", amountMinor: 6_000_000n },
    ]);
  });

  it("payable settlement reduces payable and decreases cash", () => {
    expect(classifyBookEntry("payable", 2_000_000n)).toEqual([
      { bucket: "payable", amountMinor: -2_000_000n },
      { bucket: "cash", amountMinor: -2_000_000n },
    ]);
  });

  it("internal_transfer only moves cash, no P&L effect", () => {
    expect(classifyBookEntry("internal_transfer", 5_000_000n)).toEqual([
      { bucket: "cash", amountMinor: 5_000_000n },
    ]);
  });

  it("advance given reduces cash and creates an advance asset", () => {
    expect(classifyBookEntry("advance", 3_000_000n)).toEqual([
      { bucket: "cash", amountMinor: -3_000_000n },
      { bucket: "advance", amountMinor: 3_000_000n },
    ]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/company && npx vitest run finance-legal/tests/accounting-mapping.test.ts`
Expected: FAIL — `Cannot find module '../services/accounting-mapping'`

- [ ] **Step 3: Implement `accounting-mapping.ts`**

```ts
import { computeCanonicalSha256 } from "./compliance/canonical-hasher";

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

export interface BucketEffect {
  bucket: LedgerBucket;
  amountMinor: bigint;
}

/**
 * Phân loại một book entry thành các bucket bị ảnh hưởng. capital/loan là
 * tiền mặt nhận ngay; revenue/cost là dồn tích (chưa chạm cash cho tới khi
 * có dòng receivable/payable settlement riêng); receivable/payable ở đây
 * đại diện cho SỰ KIỆN THANH TOÁN (thu/chi tiền mặt đối trừ công nợ đã dồn
 * tích trước đó), không phải công nợ mới phát sinh không có nguồn gốc.
 */
export function classifyBookEntry(
  category: BookEntryCategory,
  amountMinor: bigint
): BucketEffect[] {
  switch (category) {
    case "capital":
      return [
        { bucket: "cash", amountMinor },
        { bucket: "capital", amountMinor },
      ];
    case "loan":
      return [
        { bucket: "cash", amountMinor },
        { bucket: "loan", amountMinor },
      ];
    case "revenue":
      return [
        { bucket: "receivable", amountMinor },
        { bucket: "profit", amountMinor },
      ];
    case "cost":
      return [
        { bucket: "payable", amountMinor },
        { bucket: "profit", amountMinor: -amountMinor },
      ];
    case "receivable":
      return [
        { bucket: "receivable", amountMinor: -amountMinor },
        { bucket: "cash", amountMinor },
      ];
    case "payable":
      return [
        { bucket: "payable", amountMinor: -amountMinor },
        { bucket: "cash", amountMinor: -amountMinor },
      ];
    case "internal_transfer":
      return [{ bucket: "cash", amountMinor }];
    case "advance":
      return [
        { bucket: "cash", amountMinor: -amountMinor },
        { bucket: "advance", amountMinor },
      ];
  }
}

export type ReportRuleType = "opening" | "movement" | "closing";

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

export interface RegimeMapping {
  regimeCode: string;
  mappingVersion: string;
  lines: ReportMappingLine[];
}

const UNVERIFIED_SOURCE =
  "CHƯA XÁC MINH — chờ founder xác nhận đối chiếu văn bản Thông tư 58/2024 " +
  "(https://www.mof.gov.vn/tin-tuc-tai-chinh/tin-chinh-sach-tai-chinh/quy-dinh-moi-ve-che-do-ke-toan-cho-doanh-nghiep-sieu-nho) " +
  "trước khi coi report dùng mapping này là VERIFIED.";

/**
 * Nội dung mapping TT58 rút gọn — chỉ đủ 5 dòng cần cho bộ fixture chính
 * thức trong spec (cash/receivable/loan/capital+profit/assets). Founder
 * PHẢI xác nhận qua POST /finance/accounting-mapping/:regimeCode/:mappingVersion/confirm
 * trước khi report dùng mapping_version này đạt status=VERIFIED — cho tới
 * lúc đó report vẫn INCOMPLETE dù mọi dòng có đủ data.
 */
export const TT58_2026_MAPPING: RegimeMapping = {
  regimeCode: "TT58_2026",
  mappingVersion: "v1",
  lines: [
    {
      reportCode: "B01",
      lineCode: "TS",
      officialCode: "TS",
      name: "Tổng tài sản (tiền + phải thu + tạm ứng)",
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
      reportCode: "B02",
      lineCode: "LOI_NHUAN",
      officialCode: "LOI_NHUAN",
      name: "Lợi nhuận kỳ (doanh thu - chi phí đã ghi nhận)",
      sourceRef: UNVERIFIED_SOURCE,
      ruleType: "movement",
      bucket: "profit",
      sign: 1,
      rounding: "VND_INTEGER",
    },
  ],
};

export function computeMappingDefinitionHash(mapping: RegimeMapping): string {
  return computeCanonicalSha256({
    regimeCode: mapping.regimeCode,
    mappingVersion: mapping.mappingVersion,
    lines: mapping.lines,
  });
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd services/company && npx vitest run finance-legal/tests/accounting-mapping.test.ts`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add services/company/finance-legal/services/accounting-mapping.ts \
        services/company/finance-legal/tests/accounting-mapping.test.ts
git commit -m "feat(company): thêm engine phân loại book entry và nội dung mapping TT58 (F5 phần 3)"
```

---

### Task 4: `accounting-books.service.ts` — book entry CRUD with posting-lock guard

**Files:**
- Create: `services/company/finance-legal/services/accounting-books.service.ts`
- Test: `services/company/finance-legal/tests/accounting-books.test.ts`

**Interfaces:**
- Consumes: `assertOpenPostingPeriod` from `./posting-guard.service.ts`
  (signature: `(tx, {workspaceId, legalEntityId, postingDate}): Promise<void>`);
  `BookEntryCategory` from `./accounting-mapping.ts`; `db, schema` from
  `../models/db`; `generateSnowflake` from
  `../../shared/services/snowflake.service`; `requireWorkspaceAccess` from
  `../../shared/auth/workspace-access`.
- Produces: `BookEntryView`, `CreateBookEntryInput`,
  `createBookEntryService(ctx, input): Promise<BookEntryView>`,
  `listBookEntriesService(ctx, params): Promise<BookEntryView[]>` — consumed
  by Task 5 (report generation reads entries via `listBookEntriesService`)
  and Task 7 (handler).

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createLegalEntityProfile } from "../services/legal-entity-profile.service";
import { openAccountingPeriodService, closeAccountingPeriodService } from "../services/accounting-period.service";
import {
  createBookEntryService,
  listBookEntriesService,
} from "../services/accounting-books.service";
import { resolveTenantContext } from "../../identity/services/tenant-context.service";

async function foundersSetup(displayName: string) {
  const session = await createTestSession({ role: "founder", displayName });
  const authorization = `Bearer ${session.accessToken}`;
  const entity = await createLegalEntityProfile({
    workspaceId: BigInt(session.workspaceId),
    entityType: "MICRO_ENTERPRISE",
  });
  const ctx = await resolveTenantContext({
    authorization,
    workspaceId: session.workspaceId,
  });
  return { session, ctx, authorization, legalEntityId: entity.id };
}

describe("accounting-books.service", () => {
  it("creates a book entry inside an open period", async () => {
    const { ctx, authorization, legalEntityId } = await foundersSetup("Books Create Ws");
    const period = await openAccountingPeriodService(
      {
        workspaceId: ctx.workspaceId,
        legalEntityId,
        startDate: "2026-01-01",
        endDate: "2026-12-31",
      },
      authorization
    );

    const entry = await createBookEntryService(ctx, {
      legalEntityId,
      periodId: period.id,
      item: "Góp vốn thành lập",
      category: "capital",
      amountMinor: "100000000",
      effectiveDate: "2026-01-05",
      source: "fixture:tt58-2026",
    });

    expect(entry.category).toBe("capital");
    expect(entry.amountMinor).toBe("100000000");

    const entries = await listBookEntriesService(ctx, { legalEntityId, periodId: period.id });
    expect(entries).toHaveLength(1);
  });

  it("rejects a book entry dated inside a closed period", async () => {
    const { ctx, authorization, legalEntityId } = await foundersSetup("Books Closed Ws");
    const period = await openAccountingPeriodService(
      {
        workspaceId: ctx.workspaceId,
        legalEntityId,
        startDate: "2025-01-01",
        endDate: "2025-12-31",
      },
      authorization
    );
    await closeAccountingPeriodService(period.id, authorization);

    await expect(
      createBookEntryService(ctx, {
        legalEntityId,
        periodId: period.id,
        item: "Chi phí muộn",
        category: "cost",
        amountMinor: "1000000",
        effectiveDate: "2025-06-15",
        source: "fixture:tt58-2026",
      })
    ).rejects.toThrow(/PERIOD_CLOSED/);
  });
});
```

Note: `openAccountingPeriodService`/`closeAccountingPeriodService` call
`requireWorkspaceAccess(authorization, workspaceId)` internally, which
throws `unauthenticated` on a missing/invalid token — always pass a real
`Bearer ${session.accessToken}` here, following the exact convention already
used in `tests/financial-integrity.test.ts`'s `makeAuthedWorkspace` helper
(confirmed by reading that file before writing this task).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/company && npx vitest run finance-legal/tests/accounting-books.test.ts`
Expected: FAIL — `Cannot find module '../services/accounting-books.service'`

- [ ] **Step 3: Implement `accounting-books.service.ts`**

```ts
import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { assertOpenPostingPeriod } from "./posting-guard.service";
import { BookEntryCategory } from "./accounting-mapping";

const { accountingBookEntries } = schema;

export interface BookEntryView {
  id: string;
  workspaceId: string;
  legalEntityId: string;
  periodId: string;
  documentId: string | null;
  item: string;
  category: BookEntryCategory;
  amountMinor: string;
  currency: string;
  effectiveDate: string;
  source: string;
  version: number;
}

export interface CreateBookEntryInput {
  legalEntityId: string;
  periodId: string;
  documentId?: string;
  item: string;
  category: BookEntryCategory;
  amountMinor: string;
  currency?: string;
  effectiveDate: string;
  source: string;
}

function toBookEntryView(row: typeof accountingBookEntries.$inferSelect): BookEntryView {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    legalEntityId: String(row.legalEntityId),
    periodId: String(row.periodId),
    documentId: row.documentId ? String(row.documentId) : null,
    item: row.item,
    category: row.category as BookEntryCategory,
    amountMinor: row.amountMinor,
    currency: row.currency,
    effectiveDate: String(row.effectiveDate),
    source: row.source,
    version: row.version,
  };
}

export async function createBookEntryService(
  ctx: TenantContext,
  input: CreateBookEntryInput
): Promise<BookEntryView> {
  const amount = BigInt(input.amountMinor);
  if (amount <= 0n) {
    throw APIError.invalidArgument("amountMinor must be positive");
  }

  return db.transaction(async (tx) => {
    await assertOpenPostingPeriod(tx, {
      workspaceId: ctx.workspaceId,
      legalEntityId: input.legalEntityId,
      postingDate: input.effectiveDate,
    });

    const [row] = await tx
      .insert(accountingBookEntries)
      .values({
        id: generateSnowflake(),
        workspaceId: BigInt(ctx.workspaceId),
        legalEntityId: BigInt(input.legalEntityId),
        periodId: BigInt(input.periodId),
        documentId: input.documentId ? BigInt(input.documentId) : null,
        item: input.item,
        category: input.category,
        amountMinor: input.amountMinor,
        currency: input.currency ?? "VND",
        effectiveDate: input.effectiveDate,
        source: input.source,
      })
      .returning();

    if (!row) throw APIError.internal("Failed to create book entry");
    return toBookEntryView(row);
  });
}

export interface ListBookEntriesParams {
  legalEntityId: string;
  periodId: string;
}

export async function listBookEntriesService(
  ctx: TenantContext,
  params: ListBookEntriesParams
): Promise<BookEntryView[]> {
  const rows = await db
    .select()
    .from(accountingBookEntries)
    .where(
      and(
        eq(accountingBookEntries.workspaceId, BigInt(ctx.workspaceId)),
        eq(accountingBookEntries.legalEntityId, BigInt(params.legalEntityId)),
        eq(accountingBookEntries.periodId, BigInt(params.periodId))
      )
    );

  return rows.map(toBookEntryView);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd services/company && npx vitest run finance-legal/tests/accounting-books.test.ts`
Expected: PASS (2 tests). If `openAccountingPeriod`/`closeAccountingPeriodService`
import paths don't match the real handler/service exports, adjust the
import to the actual exported names in
`services/company/finance-legal/handlers/accounting-period.handler.ts` and
`services/accounting-period.service.ts` — do not change the assertions.

- [ ] **Step 5: Commit**

```bash
git add services/company/finance-legal/services/accounting-books.service.ts \
        services/company/finance-legal/tests/accounting-books.test.ts
git commit -m "feat(company): thêm accounting-books.service với posting-lock guard (F5 phần 4)"
```

---

### Task 5: `accounting-reports.service.ts` — report generation engine

**Files:**
- Create: `services/company/finance-legal/services/accounting-reports.service.ts`
- Test: covered by Task 9's integration test (this task's own step 2 uses a
  narrower unit test first)

**Interfaces:**
- Consumes: `listBookEntriesService` (Task 4); `classifyBookEntry`,
  `TT58_2026_MAPPING`, `computeMappingDefinitionHash`, `ReportMappingLine`,
  `LedgerBucket` (Task 3); `computeCanonicalSha256` from
  `./compliance/canonical-hasher.ts`; `db, schema` from `../models/db`.
- Produces: `ReportLineView`, `ReportSnapshotView`,
  `generateReportService(ctx, input): Promise<ReportSnapshotView>`,
  `listReportSnapshotsService(ctx, params): Promise<ReportSnapshotView[]>`,
  `ensureMappingSeeded(regimeCode, mappingVersion): Promise<void>` —
  consumed by Task 6 (confirmation checks the same seeded rows) and Task 7
  (handler).

- [ ] **Step 1: Write the failing unit test for status logic**

```ts
import { describe, expect, it } from "vitest";
import { computeReportStatus } from "../services/accounting-reports.service";

describe("accounting-reports.service — computeReportStatus", () => {
  it("is INCOMPLETE when a required bucket has no covering line", () => {
    const result = computeReportStatus({
      requiredBuckets: ["cash", "receivable", "loan", "capital", "profit"],
      coveredBuckets: ["cash", "receivable"],
      mappingConfirmed: true,
    });
    expect(result.status).toBe("INCOMPLETE");
    expect(result.issues).toContain("missing_mapping_for_bucket:loan");
  });

  it("is INCOMPLETE when mapping is not founder-confirmed even if all buckets covered", () => {
    const result = computeReportStatus({
      requiredBuckets: ["cash"],
      coveredBuckets: ["cash"],
      mappingConfirmed: false,
    });
    expect(result.status).toBe("INCOMPLETE");
    expect(result.issues).toContain("mapping_not_confirmed_by_founder");
  });

  it("is VERIFIED when all buckets covered and mapping confirmed", () => {
    const result = computeReportStatus({
      requiredBuckets: ["cash"],
      coveredBuckets: ["cash"],
      mappingConfirmed: true,
    });
    expect(result.status).toBe("VERIFIED");
    expect(result.issues).toEqual([]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/company && npx vitest run finance-legal/tests/accounting-reports-status.test.ts`
(save the Step 1 test to this file). Expected: FAIL — module not found.

- [ ] **Step 3: Implement `accounting-reports.service.ts`**

```ts
import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { computeCanonicalSha256 } from "./compliance/canonical-hasher";
import { listBookEntriesService } from "./accounting-books.service";
import {
  classifyBookEntry,
  computeMappingDefinitionHash,
  LedgerBucket,
  ReportMappingLine,
  RegimeMapping,
  TT58_2026_MAPPING,
} from "./accounting-mapping";

const {
  accountingReportMappings,
  accountingMappingConfirmations,
  accountingReportSnapshots,
  accountingPeriods,
} = schema;

/**
 * Seed nội dung `accounting-mapping.ts` vào bảng registry theo exact-hash —
 * cùng pattern SpecResolver/skillpack registry đã dùng cho AgentSpec (không
 * tin trực tiếp object TS đang import). Idempotent: chỉ ghi lại khi hash
 * đổi (nội dung mapping trong code thay đổi).
 */
export async function ensureMappingSeeded(mapping: RegimeMapping = TT58_2026_MAPPING): Promise<void> {
  const definitionHash = computeMappingDefinitionHash(mapping);

  const existing = await db
    .select({ definitionHash: accountingReportMappings.definitionHash })
    .from(accountingReportMappings)
    .where(
      and(
        eq(accountingReportMappings.regimeCode, mapping.regimeCode),
        eq(accountingReportMappings.mappingVersion, mapping.mappingVersion)
      )
    )
    .limit(1);

  if (existing[0]?.definitionHash === definitionHash) {
    return;
  }

  await db.transaction(async (tx) => {
    await tx
      .delete(accountingReportMappings)
      .where(
        and(
          eq(accountingReportMappings.regimeCode, mapping.regimeCode),
          eq(accountingReportMappings.mappingVersion, mapping.mappingVersion)
        )
      );

    for (const line of mapping.lines) {
      await tx.insert(accountingReportMappings).values({
        id: generateSnowflake(),
        regimeCode: mapping.regimeCode,
        mappingVersion: mapping.mappingVersion,
        reportCode: line.reportCode,
        lineCode: line.lineCode,
        officialCode: line.officialCode,
        name: line.name,
        sourceRef: line.sourceRef,
        ruleType: line.ruleType,
        bucket: line.bucket,
        sign: line.sign,
        rounding: line.rounding,
        definitionHash,
      });
    }
  });
}

export interface ReportStatusInput {
  requiredBuckets: LedgerBucket[];
  coveredBuckets: LedgerBucket[];
  mappingConfirmed: boolean;
}

export interface ReportStatusResult {
  status: "INCOMPLETE" | "PROVIDER_NOT_READY" | "VERIFIED";
  issues: string[];
}

export function computeReportStatus(input: ReportStatusInput): ReportStatusResult {
  const issues: string[] = [];
  const covered = new Set(input.coveredBuckets);

  for (const bucket of input.requiredBuckets) {
    if (!covered.has(bucket)) {
      issues.push(`missing_mapping_for_bucket:${bucket}`);
    }
  }

  if (!input.mappingConfirmed) {
    issues.push("mapping_not_confirmed_by_founder");
  }

  return {
    status: issues.length === 0 ? "VERIFIED" : "INCOMPLETE",
    issues,
  };
}

export interface ReportLineView {
  lineCode: string;
  officialCode: string;
  name: string;
  sourceRef: string;
  amountMinor: string;
}

export interface ReportSnapshotView {
  id: string;
  legalEntityId: string;
  periodId: string;
  reportCode: string;
  mappingVersion: string;
  inputWatermark: string;
  lines: ReportLineView[];
  status: "INCOMPLETE" | "PROVIDER_NOT_READY" | "VERIFIED";
  issues: string[];
  generatedAt: string;
}

export interface GenerateReportInput {
  legalEntityId: string;
  periodId: string;
  reportCode: string;
  mappingVersion?: string;
  expectedPeriodVersion?: number;
}

export async function generateReportService(
  ctx: TenantContext,
  input: GenerateReportInput
): Promise<ReportSnapshotView> {
  const mapping = TT58_2026_MAPPING;
  if (input.mappingVersion && input.mappingVersion !== mapping.mappingVersion) {
    throw APIError.invalidArgument(
      `Unknown mappingVersion ${input.mappingVersion}; available: ${mapping.mappingVersion}`
    );
  }

  if (input.expectedPeriodVersion !== undefined) {
    const [period] = await db
      .select({ id: accountingPeriods.id, version: accountingPeriods.version })
      .from(accountingPeriods)
      .where(eq(accountingPeriods.id, BigInt(input.periodId)))
      .limit(1);
    if (!period) throw APIError.notFound(`accounting period ${input.periodId} not found`);
    if (period.version !== input.expectedPeriodVersion) {
      throw APIError.aborted(
        `VERSION_CONFLICT: expected period version ${input.expectedPeriodVersion} but current is ${period.version}`
      );
    }
  }

  await ensureMappingSeeded(mapping);

  const mappingLines = await db
    .select()
    .from(accountingReportMappings)
    .where(
      and(
        eq(accountingReportMappings.regimeCode, mapping.regimeCode),
        eq(accountingReportMappings.mappingVersion, mapping.mappingVersion),
        eq(accountingReportMappings.reportCode, input.reportCode)
      )
    );

  const [confirmation] = await db
    .select()
    .from(accountingMappingConfirmations)
    .where(
      and(
        eq(accountingMappingConfirmations.regimeCode, mapping.regimeCode),
        eq(accountingMappingConfirmations.mappingVersion, mapping.mappingVersion)
      )
    )
    .limit(1);

  const entries = await listBookEntriesService(ctx, {
    legalEntityId: input.legalEntityId,
    periodId: input.periodId,
  });

  const bucketTotals = new Map<LedgerBucket, bigint>();
  for (const entry of entries) {
    const effects = classifyBookEntry(entry.category, BigInt(entry.amountMinor));
    for (const effect of effects) {
      bucketTotals.set(effect.bucket, (bucketTotals.get(effect.bucket) ?? 0n) + effect.amountMinor);
    }
  }

  const lines: ReportLineView[] = mappingLines.map((row) => ({
    lineCode: row.lineCode,
    officialCode: row.officialCode,
    name: row.name,
    sourceRef: row.sourceRef,
    amountMinor: String((bucketTotals.get(row.bucket as LedgerBucket) ?? 0n) * BigInt(row.sign)),
  }));

  const requiredBuckets = mappingLines.map((row) => row.bucket as LedgerBucket);
  const coveredBuckets = requiredBuckets.filter((bucket) => bucketTotals.has(bucket));

  const { status, issues } = computeReportStatus({
    requiredBuckets,
    coveredBuckets,
    mappingConfirmed: Boolean(confirmation),
  });

  const inputWatermark = computeCanonicalSha256({
    mappingVersion: mapping.mappingVersion,
    entries: entries
      .map((e) => ({ id: e.id, category: e.category, amountMinor: e.amountMinor, version: e.version }))
      .sort((a, b) => a.id.localeCompare(b.id)),
  });

  const [row] = await db
    .insert(accountingReportSnapshots)
    .values({
      id: generateSnowflake(),
      workspaceId: BigInt(ctx.workspaceId),
      legalEntityId: BigInt(input.legalEntityId),
      periodId: BigInt(input.periodId),
      reportCode: input.reportCode,
      mappingVersion: mapping.mappingVersion,
      inputWatermark,
      lines,
      status,
      issues,
    })
    .returning();

  if (!row) throw APIError.internal("Failed to generate report snapshot");

  return {
    id: String(row.id),
    legalEntityId: String(row.legalEntityId),
    periodId: String(row.periodId),
    reportCode: row.reportCode,
    mappingVersion: row.mappingVersion,
    inputWatermark: row.inputWatermark,
    lines: row.lines as ReportLineView[],
    status: row.status as ReportSnapshotView["status"],
    issues: row.issues as string[],
    generatedAt: row.generatedAt.toISOString(),
  };
}

export interface ListReportSnapshotsParams {
  legalEntityId: string;
  periodId: string;
  reportCode?: string;
}

export async function listReportSnapshotsService(
  ctx: TenantContext,
  params: ListReportSnapshotsParams
): Promise<ReportSnapshotView[]> {
  const conditions = [
    eq(accountingReportSnapshots.workspaceId, BigInt(ctx.workspaceId)),
    eq(accountingReportSnapshots.legalEntityId, BigInt(params.legalEntityId)),
    eq(accountingReportSnapshots.periodId, BigInt(params.periodId)),
  ];
  if (params.reportCode) {
    conditions.push(eq(accountingReportSnapshots.reportCode, params.reportCode));
  }

  const rows = await db
    .select()
    .from(accountingReportSnapshots)
    .where(and(...conditions));

  return rows.map((row) => ({
    id: String(row.id),
    legalEntityId: String(row.legalEntityId),
    periodId: String(row.periodId),
    reportCode: row.reportCode,
    mappingVersion: row.mappingVersion,
    inputWatermark: row.inputWatermark,
    lines: row.lines as ReportLineView[],
    status: row.status as ReportSnapshotView["status"],
    issues: row.issues as string[],
    generatedAt: row.generatedAt.toISOString(),
  }));
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd services/company && npx vitest run finance-legal/tests/accounting-reports-status.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add services/company/finance-legal/services/accounting-reports.service.ts \
        services/company/finance-legal/tests/accounting-reports-status.test.ts
git commit -m "feat(company): thêm accounting-reports.service — generate report từ book entries (F5 phần 5)"
```

---

### Task 6: Founder mapping confirmation

**Files:**
- Modify: `services/company/finance-legal/services/accounting-reports.service.ts`
- Test: `services/company/finance-legal/tests/accounting-mapping-confirmation.test.ts`

**Interfaces:**
- Consumes: `requireFounderCommand` from `../../shared/auth/workspace-access`;
  `ensureMappingSeeded` (this file, Task 5).
- Produces: `confirmMappingService(ctx, regimeCode, mappingVersion): Promise<{confirmedAt: string}>`
  — consumed by Task 7 (handler).

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { resolveTenantContext } from "../../identity/services/tenant-context.service";
import { confirmMappingService } from "../services/accounting-reports.service";
import { TT58_2026_MAPPING } from "../services/accounting-mapping";

describe("accounting-reports.service — confirmMappingService", () => {
  it("requires founder role", async () => {
    const session = await createTestSession({ role: "member", displayName: "Non-founder confirm" });
    const ctx = await resolveTenantContext({
      authorization: `Bearer ${session.accessToken}`,
      workspaceId: session.workspaceId,
    });

    await expect(
      confirmMappingService(ctx, TT58_2026_MAPPING.regimeCode, TT58_2026_MAPPING.mappingVersion)
    ).rejects.toThrow(/Missing authority/);
  });

  it("records confirmation for a founder", async () => {
    const session = await createTestSession({ role: "founder", displayName: "Founder confirm" });
    const ctx = await resolveTenantContext({
      authorization: `Bearer ${session.accessToken}`,
      workspaceId: session.workspaceId,
    });

    const result = await confirmMappingService(
      ctx,
      TT58_2026_MAPPING.regimeCode,
      TT58_2026_MAPPING.mappingVersion
    );
    expect(result.confirmedAt).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd services/company && npx vitest run finance-legal/tests/accounting-mapping-confirmation.test.ts`
Expected: FAIL — `confirmMappingService is not a function`

- [ ] **Step 3: Add `confirmMappingService` to `accounting-reports.service.ts`**

Add import at the top (merge into the existing import from
`"../../shared/auth/workspace-access"` if Task 7 has already added one;
otherwise add a new line):

```ts
import { requireFounderCommand } from "../../shared/auth/workspace-access";
```

Append at the end of the file:

```ts
export async function confirmMappingService(
  ctx: TenantContext,
  regimeCode: string,
  mappingVersion: string
): Promise<{ confirmedAt: string }> {
  requireFounderCommand(ctx, "finance.accounting_mapping.confirm");

  if (regimeCode !== TT58_2026_MAPPING.regimeCode || mappingVersion !== TT58_2026_MAPPING.mappingVersion) {
    throw APIError.invalidArgument(`Unknown mapping ${regimeCode}/${mappingVersion}`);
  }
  await ensureMappingSeeded(TT58_2026_MAPPING);

  const [row] = await db
    .insert(accountingMappingConfirmations)
    .values({
      id: generateSnowflake(),
      regimeCode,
      mappingVersion,
      confirmedByMemberId: BigInt(ctx.workforceMemberId ?? ctx.userId),
    })
    .onConflictDoUpdate({
      target: [accountingMappingConfirmations.regimeCode, accountingMappingConfirmations.mappingVersion],
      set: {
        confirmedByMemberId: BigInt(ctx.workforceMemberId ?? ctx.userId),
        confirmedAt: new Date(),
      },
    })
    .returning();

  if (!row) throw APIError.internal("Failed to record mapping confirmation");
  return { confirmedAt: row.confirmedAt.toISOString() };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd services/company && npx vitest run finance-legal/tests/accounting-mapping-confirmation.test.ts`
Expected: PASS (2 tests). If `createTestSession` does not support a
`"member"` role literal, check
`services/company/identity/tests/helpers/test-session.ts` for the exact
non-founder role name it accepts and use that instead — do not change the
assertion that a non-founder is rejected.

- [ ] **Step 5: Commit**

```bash
git add services/company/finance-legal/services/accounting-reports.service.ts \
        services/company/finance-legal/tests/accounting-mapping-confirmation.test.ts
git commit -m "feat(company): thêm founder confirmation cho mapping TT58 (F5 phần 6)"
```

---

### Task 7: Wire HTTP endpoints in `finance-tt58.handler.ts`

**Files:**
- Modify: `services/company/finance-legal/handlers/finance-tt58.handler.ts`
  (append after the existing "6. Financial Snapshots" section, ~line 237)

**Interfaces:**
- Consumes: `createBookEntryService`, `listBookEntriesService` (Task 4);
  `generateReportService`, `listReportSnapshotsService`,
  `confirmMappingService` (Task 5/6).
- Produces: `POST /finance/books`, `GET /finance/books`,
  `POST /finance/reports/generate`, `GET /finance/reports`,
  `POST /finance/accounting-mapping/:regimeCode/:mappingVersion/confirm` —
  consumed by Task 9's integration test and (later, out of scope here) F6's
  Flutter client.

- [ ] **Step 1: Add imports**

At the top of the file, after the existing snapshot import block:

```ts
import {
  createBookEntryService,
  listBookEntriesService,
  BookEntryView,
} from "../services/accounting-books.service";
import {
  generateReportService,
  listReportSnapshotsService,
  confirmMappingService,
  ReportSnapshotView,
} from "../services/accounting-reports.service";
```

- [ ] **Step 2: Append endpoint definitions**

At the end of the file:

```ts
// 7. TT58 Books & Reports (F5)
export interface CreateBookEntryParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  legalEntityId: string;
  periodId: string;
  documentId?: string;
  item: string;
  category: "capital" | "loan" | "internal_transfer" | "revenue" | "cost" | "advance" | "payable" | "receivable";
  amountMinor: string;
  currency?: string;
  effectiveDate: string;
  source: string;
}

export const postBookEntry = api(
  { method: "POST", path: "/finance/books", expose: true },
  async (params: CreateBookEntryParams): Promise<BookEntryView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createBookEntryService(ctx, {
      legalEntityId: params.legalEntityId,
      periodId: params.periodId,
      documentId: params.documentId,
      item: params.item,
      category: params.category,
      amountMinor: params.amountMinor,
      currency: params.currency,
      effectiveDate: params.effectiveDate,
      source: params.source,
    });
  }
);

export interface ListBookEntriesParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  legalEntityId: Query<string>;
  periodId: Query<string>;
}

export const getBookEntries = api(
  { method: "GET", path: "/finance/books", expose: true },
  async (params: ListBookEntriesParams): Promise<{ entries: BookEntryView[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const entries = await listBookEntriesService(ctx, {
      legalEntityId: params.legalEntityId,
      periodId: params.periodId,
    });
    return { entries };
  }
);

export interface GenerateReportParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  legalEntityId: string;
  periodId: string;
  reportCode: string;
  mappingVersion?: string;
  expectedPeriodVersion?: number;
}

export const postGenerateReport = api(
  { method: "POST", path: "/finance/reports/generate", expose: true },
  async (params: GenerateReportParams): Promise<ReportSnapshotView> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return generateReportService(ctx, {
      legalEntityId: params.legalEntityId,
      periodId: params.periodId,
      reportCode: params.reportCode,
      mappingVersion: params.mappingVersion,
      expectedPeriodVersion: params.expectedPeriodVersion,
    });
  }
);

export interface ListReportsParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  legalEntityId: Query<string>;
  periodId: Query<string>;
  reportCode?: Query<string>;
}

export const getReports = api(
  { method: "GET", path: "/finance/reports", expose: true },
  async (params: ListReportsParams): Promise<{ reports: ReportSnapshotView[] }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    const reports = await listReportSnapshotsService(ctx, {
      legalEntityId: params.legalEntityId,
      periodId: params.periodId,
      reportCode: params.reportCode,
    });
    return { reports };
  }
);

export interface ConfirmMappingParams {
  regimeCode: string;
  mappingVersion: string;
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
}

export const postConfirmAccountingMapping = api(
  { method: "POST", path: "/finance/accounting-mapping/:regimeCode/:mappingVersion/confirm", expose: true },
  async (params: ConfirmMappingParams): Promise<{ confirmedAt: string }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return confirmMappingService(ctx, params.regimeCode, params.mappingVersion);
  }
);
```

- [ ] **Step 3: Typecheck**

Run: `cd services/company && npm run typecheck`
Expected: no new errors.

- [ ] **Step 4: Boundary gates**

Run: `make company-boundary-check && make encore-handler-boundary-check && make ts-suppression-check`
Expected: all PASS — this handler must not import `drizzle-orm`/DB schema
directly (it only calls the 5 service functions above).

- [ ] **Step 5: Commit**

```bash
git add services/company/finance-legal/handlers/finance-tt58.handler.ts
git commit -m "feat(company): expose endpoint books/reports/mapping-confirm TT58 (F5 phần 7)"
```

---

### Task 8: Fix `legal-applicability.service.ts` entity-scoped fallback

**Files:**
- Modify: `services/company/finance-legal/services/legal-applicability.service.ts:80-88`
- Test: existing legal-applicability tests (run, don't create new file
  unless the existing suite has no coverage for the no-`fiscalProfileId`
  fallback path)

**Interfaces:**
- Consumes: `legalEntityId` already in scope in this function (parameter
  used earlier in the same function per spec exploration, `services/legal-applicability.service.ts:60-67`).

- [ ] **Step 1: Locate the existing test file**

Run: `find services/company/finance-legal/tests -iname "legal-applicability*"`
Read the matching file(s) to confirm whether the no-`fiscalProfileId`
fallback path already has a test. If a test named similar to
`"falls back to the workspace's only fiscal profile when none specified"`
exists, it needs updating in Step 3 below; if not, add one exercising two
entities in the same workspace with different fiscal profiles.

- [ ] **Step 2: Write/update the test to assert entity-scoping**

```ts
it("does not leak another legal entity's fiscal profile when none is specified", async () => {
  // Tạo 2 entity trong cùng workspace, mỗi entity có 1 fiscal profile riêng.
  // Gọi applicability cho entity B mà không truyền fiscalProfileId phải
  // đọc đúng fiscal profile của entity B, không rơi vào .limit(1) của entity A.
  const session = await createTestSession({ role: "founder", displayName: "Applicability Entity Scope Ws" });
  const authorization = `Bearer ${session.accessToken}`;
  const wsId = BigInt(session.workspaceId);
  const entityA = await createLegalEntityProfile({ workspaceId: wsId, entityType: "MICRO_ENTERPRISE" });
  const entityB = await createLegalEntityProfile({ workspaceId: wsId, entityType: "MICRO_ENTERPRISE" });
  expect(entityA.id).not.toBe(entityB.id);
  await createFiscalProfileService(
    { workspaceId: session.workspaceId, fiscalYear: 2025, mode: "TT58_MODE_1" },
    authorization
  );
  const profileB = await createFiscalProfileService(
    { workspaceId: session.workspaceId, fiscalYear: 2026, mode: "TT58_MODE_1" },
    authorization
  );
  // gán legalEntityId cho profileB trực tiếp qua DB update (chưa có service
  // setter riêng ở phạm vi F5 — chỉ cần cho mục đích test entity-scoping)
  await db
    .update(accountingFiscalProfiles)
    .set({ legalEntityId: BigInt(entityB.id) })
    .where(eq(accountingFiscalProfiles.id, BigInt(profileB.id)));

  const result = await getLegalApplicabilityService(wsId, entityB.id, undefined, authorization);
  expect(result.facts.fiscalYearStart).toBe("2026-01-01");
});
```

`db`, `schema.accountingFiscalProfiles`, and `eq` need importing at the top
of the test file from `../models/db` and `drizzle-orm` respectively if not
already present — check the existing imports in
`legal-applicability*.test.ts` first, since it may already import `db` for
other assertions.

Adapt the exact helper/import names (especially
`getLegalApplicabilityService`'s real parameter order/count) to whatever the
existing `legal-applicability*.test.ts` file already uses (read it first —
don't invent a different test harness for this one file).

- [ ] **Step 3: Update the fallback query**

In `legal-applicability.service.ts`, change:

```ts
  } else {
    const [fp] = await db
      .select()
      .from(accountingFiscalProfiles)
      .where(eq(accountingFiscalProfiles.workspaceId, wsId))
      .limit(1);
    fiscalProfile = fp;
  }
```

to:

```ts
  } else {
    const [fp] = await db
      .select()
      .from(accountingFiscalProfiles)
      .where(
        and(
          eq(accountingFiscalProfiles.workspaceId, wsId),
          eq(accountingFiscalProfiles.legalEntityId, BigInt(legalEntityId))
        )
      )
      .limit(1);
    fiscalProfile = fp;
  }
```

Confirm `and` is already imported from `drizzle-orm` in this file (it is,
per the existing query at the top of the same function); if not, add it to
the existing `drizzle-orm` import.

- [ ] **Step 4: Run the test**

Run: `cd services/company && npx vitest run finance-legal/tests/legal-applicability*.test.ts`
Expected: PASS, including any pre-existing tests in this file (they must
not regress).

- [ ] **Step 5: Commit**

```bash
git add services/company/finance-legal/services/legal-applicability.service.ts \
        services/company/finance-legal/tests/legal-applicability*.test.ts
git commit -m "fix(company): legal applicability fallback phải lọc theo legal_entity_id sau khi F5 entity-scope fiscal profile"
```

---

### Task 9: Fixture and full integration test

**Files:**
- Create: `services/company/finance-legal/tests/fixtures/tt58-2026/basic-entity.json`
- Create: `services/company/finance-legal/tests/tt58-reports.test.ts`
- Modify: `services/company/finance-legal/services/accounting-period.service.ts`
  (`closeAccountingPeriodService` — increment `version` on close, needed for
  this task's CAS test; see Step 1b)

**Interfaces:**
- Consumes: everything from Tasks 4-7 (handlers), plus
  `createFiscalProfileService` from `../services/accounting-regime.service.ts`,
  `openAccountingPeriodService`/`closeAccountingPeriodService` from
  `../services/accounting-period.service.ts`.

- [ ] **Step 0: Bump `version` on period close (needed by the CAS test in Step 2)**

In `services/company/finance-legal/services/accounting-period.service.ts`,
add `version: number` to the `AccountingPeriod` interface and `toAccountingPeriod`:

```ts
export interface AccountingPeriod {
  id: string;
  workspaceId: string;
  legalEntityId: string | null;
  startDate: string;
  endDate: string;
  status: string;
  version: number;
  closedBy: string | null;
  closedAt: string | null;
}
```

```ts
function toAccountingPeriod(row: typeof accountingPeriods.$inferSelect): AccountingPeriod {
  return {
    id: String(row.id),
    workspaceId: String(row.workspaceId),
    legalEntityId: row.legalEntityId ? String(row.legalEntityId) : null,
    startDate: String(row.startDate),
    endDate: String(row.endDate),
    status: row.status,
    version: row.version,
    closedBy: row.closedBy ? String(row.closedBy) : null,
    closedAt: row.closedAt ? row.closedAt.toISOString() : null,
  };
}
```

In `closeAccountingPeriodService`, change the update call from:
```ts
    const [row] = await tx
      .update(accountingPeriods)
      .set({
        status: "CLOSED",
        closedAt: new Date(),
      })
      .where(eq(accountingPeriods.id, BigInt(id)))
      .returning();
```
to:
```ts
    const [row] = await tx
      .update(accountingPeriods)
      .set({
        status: "CLOSED",
        closedAt: new Date(),
        version: existing.version + 1,
      })
      .where(eq(accountingPeriods.id, BigInt(id)))
      .returning();
```

Run: `cd services/company && npx vitest run finance-legal/tests/financial-integrity.test.ts`
Expected: still PASS (this file already exercises
`closeAccountingPeriodService` — confirm the version bump doesn't break its
existing assertions before moving on).

- [ ] **Step 1: Write the fixture data file**

```json
{
  "description": "Fixture rút gọn theo docs/superpowers/plans/2026-09-05-business-agents-finance.md (F5, dòng 152) — KHÔNG có thuế, chỉ kiểm bất biến assets = liabilities + equity. Viết độc lập với accounting-reports.service.ts để tránh test tự xác nhận chính nó.",
  "entries": [
    { "item": "Góp vốn thành lập", "category": "capital", "amountMinor": "100000000", "effectiveDate": "2026-02-01" },
    { "item": "Vay ngân hàng", "category": "loan", "amountMinor": "20000000", "effectiveDate": "2026-02-02" },
    { "item": "Doanh thu dịch vụ hoàn tất", "category": "revenue", "amountMinor": "10000000", "effectiveDate": "2026-03-01" },
    { "item": "Thu tiền dịch vụ (một phần)", "category": "receivable", "amountMinor": "6000000", "effectiveDate": "2026-03-10" },
    { "item": "Chi phí dịch vụ mua đã nhận", "category": "cost", "amountMinor": "2000000", "effectiveDate": "2026-03-05" },
    { "item": "Trả tiền chi phí đã nhận", "category": "payable", "amountMinor": "2000000", "effectiveDate": "2026-03-06" }
  ],
  "expected": {
    "cashMinor": "124000000",
    "receivableMinor": "4000000",
    "loanMinor": "20000000",
    "equityMinor": "108000000",
    "assetsMinor": "128000000"
  }
}
```

- [ ] **Step 2: Write the failing integration test**

```ts
import { describe, expect, it } from "vitest";
import fixture from "./fixtures/tt58-2026/basic-entity.json";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createLegalEntityProfile } from "../services/legal-entity-profile.service";
import { resolveTenantContext } from "../../identity/services/tenant-context.service";
import { createFiscalProfileService } from "../services/accounting-regime.service";
import { openAccountingPeriodService, closeAccountingPeriodService } from "../services/accounting-period.service";
import { createBookEntryService } from "../services/accounting-books.service";
import { generateReportService, confirmMappingService } from "../services/accounting-reports.service";
import { TT58_2026_MAPPING } from "../services/accounting-mapping";

describe("F5 — TT58 report generation (fixture-based)", () => {
  it("generates INCOMPLETE report until founder confirms the mapping, then VERIFIED with correct balance-sheet totals", async () => {
    const session = await createTestSession({ role: "founder", displayName: "TT58 Fixture Ws" });
    const authorization = `Bearer ${session.accessToken}`;
    const ctx = await resolveTenantContext({
      authorization,
      workspaceId: session.workspaceId,
    });
    const entity = await createLegalEntityProfile({
      workspaceId: BigInt(session.workspaceId),
      entityType: "MICRO_ENTERPRISE",
    });
    await createFiscalProfileService(
      { workspaceId: session.workspaceId, fiscalYear: 2026 },
      authorization
    );
    const period = await openAccountingPeriodService(
      {
        workspaceId: session.workspaceId,
        legalEntityId: entity.id,
        startDate: "2026-01-01",
        endDate: "2026-12-31",
      },
      authorization
    );

    for (const entry of fixture.entries) {
      await createBookEntryService(ctx, {
        legalEntityId: entity.id,
        periodId: period.id,
        item: entry.item,
        category: entry.category as any,
        amountMinor: entry.amountMinor,
        effectiveDate: entry.effectiveDate,
        source: "fixture:tt58-2026/basic-entity",
      });
    }

    // Trước khi founder confirm — report phải INCOMPLETE dù đủ book entries.
    const beforeConfirm = await generateReportService(ctx, {
      legalEntityId: entity.id,
      periodId: period.id,
      reportCode: "B01",
    });
    expect(beforeConfirm.status).toBe("INCOMPLETE");
    expect(beforeConfirm.issues).toContain("mapping_not_confirmed_by_founder");

    await confirmMappingService(ctx, TT58_2026_MAPPING.regimeCode, TT58_2026_MAPPING.mappingVersion);

    const report = await generateReportService(ctx, {
      legalEntityId: entity.id,
      periodId: period.id,
      reportCode: "B01",
    });
    expect(report.status).toBe("VERIFIED");
    expect(report.issues).toEqual([]);

    const byLineCode = Object.fromEntries(report.lines.map((l) => [l.lineCode, l.amountMinor]));
    expect(byLineCode["TS"]).toBe(fixture.expected.cashMinor);
    expect(byLineCode["PHAI_THU"]).toBe(fixture.expected.receivableMinor);
    expect(byLineCode["NO_VAY"]).toBe(fixture.expected.loanMinor);
    expect(byLineCode["VON_GOP"]).toBe("100000000");

    const assetsMinor = BigInt(byLineCode["TS"]) + BigInt(byLineCode["PHAI_THU"]);
    const liabilitiesMinor = BigInt(byLineCode["NO_VAY"]);
    const b02 = await generateReportService(ctx, {
      legalEntityId: entity.id,
      periodId: period.id,
      reportCode: "B02",
    });
    const profitLine = b02.lines.find((l) => l.lineCode === "LOI_NHUAN")!;
    const equityMinor = BigInt(byLineCode["VON_GOP"]) + BigInt(profitLine.amountMinor);

    expect(assetsMinor).toBe(BigInt(fixture.expected.assetsMinor));
    expect(assetsMinor).toBe(liabilitiesMinor + equityMinor);
  });

  it("keeps the same input_watermark when regenerating with unchanged inputs, even after the period is closed", async () => {
    const session = await createTestSession({ role: "founder", displayName: "TT58 Idempotent Ws" });
    const authorization = `Bearer ${session.accessToken}`;
    const ctx = await resolveTenantContext({
      authorization,
      workspaceId: session.workspaceId,
    });
    const entity = await createLegalEntityProfile({
      workspaceId: BigInt(session.workspaceId),
      entityType: "MICRO_ENTERPRISE",
    });
    const period = await openAccountingPeriodService(
      {
        workspaceId: session.workspaceId,
        legalEntityId: entity.id,
        startDate: "2026-01-01",
        endDate: "2026-12-31",
      },
      authorization
    );
    await createBookEntryService(ctx, {
      legalEntityId: entity.id,
      periodId: period.id,
      item: "Góp vốn",
      category: "capital",
      amountMinor: "50000000",
      effectiveDate: "2026-01-10",
      source: "fixture:tt58-2026/idempotent",
    });
    await confirmMappingService(ctx, TT58_2026_MAPPING.regimeCode, TT58_2026_MAPPING.mappingVersion);

    const first = await generateReportService(ctx, { legalEntityId: entity.id, periodId: period.id, reportCode: "B01" });

    await closeAccountingPeriodService(period.id, authorization);

    // Generate vẫn được phép cho kỳ đã đóng — F1 chỉ khóa POSTING (thêm book
    // entry mới), không khóa việc generate report cho kỳ đó.
    const second = await generateReportService(ctx, { legalEntityId: entity.id, periodId: period.id, reportCode: "B01" });

    expect(second.inputWatermark).toBe(first.inputWatermark);

    // Thêm entry mới vào kỳ đã đóng phải bị chặn — không lặng lẽ đổi watermark.
    await expect(
      createBookEntryService(ctx, {
        legalEntityId: entity.id,
        periodId: period.id,
        item: "Entry muộn",
        category: "capital",
        amountMinor: "1000000",
        effectiveDate: "2026-06-01",
        source: "fixture:tt58-2026/idempotent",
      })
    ).rejects.toThrow(/PERIOD_CLOSED/);
  });

  it("rejects generate with a stale expectedPeriodVersion (VERSION_CONFLICT)", async () => {
    const session = await createTestSession({ role: "founder", displayName: "TT58 CAS Ws" });
    const authorization = `Bearer ${session.accessToken}`;
    const ctx = await resolveTenantContext({ authorization, workspaceId: session.workspaceId });
    const entity = await createLegalEntityProfile({
      workspaceId: BigInt(session.workspaceId),
      entityType: "MICRO_ENTERPRISE",
    });
    const period = await openAccountingPeriodService(
      {
        workspaceId: session.workspaceId,
        legalEntityId: entity.id,
        startDate: "2026-01-01",
        endDate: "2026-12-31",
      },
      authorization
    );
    await confirmMappingService(ctx, TT58_2026_MAPPING.regimeCode, TT58_2026_MAPPING.mappingVersion);

    // period.version bắt đầu = 1 (migration 42 default). Đóng kỳ tăng version.
    await closeAccountingPeriodService(period.id, authorization);

    await expect(
      generateReportService(ctx, {
        legalEntityId: entity.id,
        periodId: period.id,
        reportCode: "B01",
        expectedPeriodVersion: 1, // đã stale — period đã đóng, caller cần refresh version trước
      })
    ).rejects.toThrow(/VERSION_CONFLICT/);
  });
});
```

Note: this test assumes `closeAccountingPeriodService` bumps
`accounting_periods.version` on the OPEN→CLOSED transition. That bump is
NOT part of this plan's Task 1 migration (which only adds the column with a
default) — add one line to `closeAccountingPeriodService` in
`services/accounting-period.service.ts` incrementing `version` alongside
the existing `status`/`closedAt` update (in the same `tx.update(...).set({...})`
call already there) as part of this task's Step 3, since without it this
test's premise (version changed after close) doesn't hold and the CAS
check would never trigger in the closed-period case. Do not change
`assertOpenPostingPeriod` or any other F1 behavior while doing this — only
add the `version` increment to the existing close transition.

- [ ] **Step 2b: Run test to verify it fails**

Run: `cd services/company && npx vitest run finance-legal/tests/tt58-reports.test.ts`
Expected: FAIL initially if any import name doesn't match the real export
from Tasks 4-8 — fix the import, not the assertions, since the assertions
encode the fixture's official expected numbers from the spec.

- [ ] **Step 3: Run test to verify it passes**

Run: `cd services/company && npx vitest run finance-legal/tests/tt58-reports.test.ts`
Expected: PASS (2 tests)

- [ ] **Step 4: Commit**

```bash
git add services/company/finance-legal/tests/fixtures/tt58-2026/basic-entity.json \
        services/company/finance-legal/tests/tt58-reports.test.ts
git commit -m "test(company): fixture + integration test TT58 B01/B02 báo cáo (F5 phần 8)"
```

---

### Task 10: Mapping documentation + final gates

**Files:**
- Create: `docs/finance/tt58-2026-mapping.md`

- [ ] **Step 1: Write the human-readable mapping doc**

```markdown
# TT58/2026 — Mapping sổ/báo cáo (F5)

**Trạng thái: CHƯA XÁC MINH.** Nội dung dưới đây là bản rút gọn dùng để dựng
engine và fixture test — KHÔNG được đối chiếu với toàn văn Thông tư 58/2024
hay phụ lục chính thức. Founder phải xác nhận qua
`POST /finance/accounting-mapping/TT58_2026/v1/confirm` chỉ sau khi đã tự
đối chiếu nguồn chính thức tại
[Bộ Tài chính](https://www.mof.gov.vn/tin-tuc-tai-chinh/tin-chinh-sach-tai-chinh/quy-dinh-moi-ve-che-do-ke-toan-cho-doanh-nghiep-sieu-nho).
Trước khi confirm, mọi report dùng mapping_version này ở trạng thái
`INCOMPLETE` với issue `mapping_not_confirmed_by_founder` — đây là hành vi
đúng theo thiết kế, không phải lỗi.

## Nguồn nội dung

Nội dung mapping thật nằm trong
`services/company/finance-legal/services/accounting-mapping.ts`
(`TT58_2026_MAPPING`). File này là tài liệu tham chiếu, không phải nguồn dữ
liệu — sửa mapping phải sửa file TS, không sửa file markdown này.

## Dòng báo cáo hiện có (v1, rút gọn cho fixture)

| Report | Line code | Ý nghĩa | Bucket | Dấu |
|---|---|---|---|---|
| B01 | TS | Tổng tài sản (tiền mặt) | cash | + |
| B01 | PHAI_THU | Phải thu khách hàng | receivable | + |
| B01 | NO_VAY | Nợ vay | loan | + |
| B01 | VON_GOP | Vốn góp chủ sở hữu | capital | + |
| B02 | LOI_NHUAN | Lợi nhuận kỳ | profit | + |

## Chưa có trong v1

Dòng cho `advance`, `internal_transfer`, thuế, tài sản cố định, B03 (lưu
chuyển tiền tệ), F01 (thuyết minh) — thêm khi có yêu cầu thật và nguồn xác
minh được, không tự suy diễn trước.
```

- [ ] **Step 2: Run full gate suite**

Run in order:
```bash
cd services/company && npm run typecheck
cd /Volumes/SSD/javis-saas && make company-boundary-check
make encore-handler-boundary-check
make ts-suppression-check
cd services/company && npx vitest run finance-legal/tests/accounting-mapping.test.ts \
  finance-legal/tests/accounting-books.test.ts \
  finance-legal/tests/accounting-reports-status.test.ts \
  finance-legal/tests/accounting-mapping-confirmation.test.ts \
  finance-legal/tests/tt58-reports.test.ts \
  finance-legal/tests/legal-applicability*.test.ts
```
Expected: all PASS.

- [ ] **Step 3: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add docs/finance/tt58-2026-mapping.md
git commit -m "docs(finance): thêm tài liệu tham chiếu mapping TT58/2026 v1 (F5 phần 9, chưa xác minh)"
```

## Self-Review Notes (from writing-plans checklist)

- **Spec coverage:** schema (Task 1-2), mapping content + classification
  (Task 3), book entries + posting guard (Task 4), report generation +
  watermark + status (Task 5), founder confirmation (Task 6), API (Task 7),
  entity-scope fallback fix (Task 8), fixture + balance invariant (Task 9),
  docs (Task 10) — all sections of the design spec are covered.
- **Correction from spec:** the design spec's Task 6 wording ("kỳ khóa F1
  chặn report generate mới cho kỳ đã đóng") was imprecise; Task 9's second
  test asserts the correct behavior — closing a period blocks new *book
  entries*, not report *generation* for that period.
- **Out of scope, confirmed unchanged:** F6 (Flutter, budget summary), H1
  (E2E), TT199/TT200 content, VietQR — none of this plan's tasks touch
  those files.
