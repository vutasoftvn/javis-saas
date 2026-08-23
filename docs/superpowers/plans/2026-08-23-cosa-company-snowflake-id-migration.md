# Migrate services/company sang Snowflake ID — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thay toàn bộ 55 cột `id` kiểu `bigserial` (Postgres auto-increment) trong `services/company` bằng snowflake ID sinh ở tầng ứng dụng (đúng chuẩn `db.md` và đúng pattern `services/cosa` đã dùng), đồng thời xoá sạch dữ liệu cũ.

**Architecture:** Một hàm sinh snowflake ID mới (copy nguyên thuật toán từ `services/cosa/services/snowflake.service.ts`) dùng chung trong `services/company`. Đổi cột schema từ `bigserial` sang `bigint` (bỏ auto-increment). Migration mới TRUNCATE dữ liệu cũ + DROP DEFAULT trên từng cột. Mọi lệnh `insert()` trong service code phải tự truyền `id: generateSnowflake()` — không còn dựa vào DB tự sinh.

**Tech Stack:** TypeScript, Drizzle ORM, PostgreSQL, Encore.ts, vitest (qua `encore test`).

## Global Constraints

- Không đổi `services/cosa` — đã đúng chuẩn snowflake sẵn.
- Không tạo bảng/handler/endpoint nghiệp vụ mới — chỉ đổi cách sinh ID.
- Xoá sạch dữ liệu cũ là **có chủ đích** (yêu cầu người dùng) — TRUNCATE trong migration không phải lỗi.
- Sau khi migration của một module chạy xong, MỌI `insert()` vào bảng thuộc module đó phải truyền `id` tường minh — thiếu một chỗ sẽ gây lỗi `null value in column "id" violates not-null constraint` ngay khi test chạy tới đó. Chạy test ngay sau mỗi task để bắt lỗi sớm.
- Chạy migration bằng `node scripts/migrate.mjs` (từ `services/company/`) hoặc `make services-migrate-company` (từ gốc repo) — script tự động track theo `public.schema_migrations`, chạy lại nhiều lần không lỗi (idempotent), nhưng file `.up.sql` mới chỉ chạy đúng 1 lần khi lần đầu xuất hiện.
- Không tuyên bố hoàn thành khi `make services-test-company` chưa xanh.

**[Bổ sung sau khi Task 1-2 hoàn tất — phát hiện thật, đã xác nhận với người dùng]:** `Number(bigIdValue)` với snowflake ID (18-19 chữ số) gây mất chính xác thật (`349872518395265058n` → `Number()` → `349872518395265100`, sai giá trị) — đã verify bằng `node -e`. Task 2 (module identity) đã tự phát hiện và sửa: đổi TOÀN BỘ trường ID/FK dạng number-based-on-snowflake (id, workspaceId, organizationId, ...) trong interface/return type của service+handler từ `number` sang `string` (giữ `BigInt`/`mode:"bigint"` ở tầng Drizzle, chỉ `.toString()` khi trả ra ngoài, không `Number(...)`). Người dùng xác nhận: áp dụng đồng bộ quy tắc này cho **toàn bộ** Task 3-6 (operations, operations/strategy, commercial, finance-legal) — mọi trường ID/FK có giá trị sinh từ `generateSnowflake()` (id của chính bảng, và mọi cột `*Id` tham chiếu tới bảng khác đã/sẽ migrate) phải là `string` trong TypeScript interface, request params, và response type — không chỉ ở nơi bảng đó tự sinh ID. Cập nhật test tương ứng: đổi assertion kiểu `expect(x.id).toBeGreaterThan(0)` thành `expect(x.id).toBeTruthy()` + `expect(typeof x.id).toBe("string")`, và mọi so sánh số cứng khác liên quan tới ID. Task 7 (regression cuối) cũng cần cập nhật `services/company/shared/tests/golden-path.e2e.test.ts` (viết ở phase trước, hiện giả định `workspaceId` là number) cho khớp — xem ghi chú bổ sung ở Task 7.

---

### Task 1: Snowflake ID generator dùng chung

**Files:**
- Create: `services/company/shared/services/snowflake.service.ts`

**Interfaces:**
- Produces: `generateSnowflake(): bigint` và `generateSnowflakeStr(): string` — dùng bởi mọi task sau.

- [ ] **Step 1: Viết file**

```ts
// services/company/shared/services/snowflake.service.ts
// Sinh 64-bit Snowflake ID ở tầng ứng dụng cho toàn bộ services/company —
// thay cho bigserial (Postgres auto-increment), đúng quy ước db.md. Thuật
// toán giống hệt services/cosa/services/snowflake.service.ts (mỗi app tự
// sinh ID độc lập trong DB riêng, không cần điều phối giữa 2 app).
const EPOCH = 1704067200000n; // 2024-01-01 00:00:00 UTC
const NODE_ID = BigInt(Math.floor(Math.random() * 1024)); // 10-bit node ID ngẫu nhiên, tránh đụng ID giữa các worker

let sequence = BigInt(Math.floor(Math.random() * 64));
let lastTimestamp = -1n;

export function generateSnowflake(): bigint {
  let timestamp = BigInt(Date.now());

  if (timestamp === lastTimestamp) {
    sequence = (sequence + 1n) & 4095n;
    if (sequence === 0n) {
      while (timestamp <= lastTimestamp) {
        timestamp = BigInt(Date.now());
      }
    }
  } else if (timestamp > lastTimestamp) {
    sequence = (sequence + 1n) & 4095n;
  } else {
    timestamp = lastTimestamp;
    sequence = (sequence + 1n) & 4095n;
  }

  lastTimestamp = timestamp;

  return (
    ((timestamp - EPOCH) << 22n) |
    (NODE_ID << 12n) |
    sequence
  );
}

export function generateSnowflakeStr(): string {
  return generateSnowflake().toString();
}
```

- [ ] **Step 2: Xác nhận biên dịch được**

Run: `cd services/company && npx tsc --noEmit shared/services/snowflake.service.ts 2>&1 | head -20`
Expected: không lỗi liên quan đến file này (lỗi về thiếu file khác trong dự án do chạy tsc đơn lẻ thì bỏ qua, miễn không có lỗi cú pháp trong chính file này).

- [ ] **Step 3: Xác nhận thủ công output đúng định dạng snowflake**

Run: `cd services/company && node -e "const {generateSnowflake}=require('./shared/services/snowflake.service.ts')" 2>&1 || node --experimental-strip-types -e "
import('./shared/services/snowflake.service.ts').then(m => {
  const a = m.generateSnowflake();
  const b = m.generateSnowflake();
  console.log('a=', a.toString(), 'b=', b.toString(), 'b>a:', b > a, 'digits:', a.toString().length);
});
"`
Expected: hai số khác nhau, `b > a` là `true` (tăng dần theo thời gian), độ dài 15-19 chữ số. Nếu lệnh node trên không chạy được do cú pháp TS, dùng cách khác tương đương (ví dụ viết file `.mjs` tạm biên dịch tay) — miễn xác nhận được 2 tính chất trên trước khi qua bước tiếp theo.

- [ ] **Step 4: Commit**

```bash
git add services/company/shared/services/snowflake.service.ts
git commit -m "feat(company): thêm snowflake ID generator dùng chung, thay cho bigserial"
```

---

### Task 2: Module identity (5 bảng: organizations, users, workforce_members, workspace_members, workspaces)

**Files:**
- Modify: `services/company/shared/db/schema/identity.ts`
- Create: `services/company/identity/migrations/4_snowflake_ids.up.sql`
- Modify: `services/company/identity/services/auth.service.ts` (3 insert sites: dòng ~76, ~87, ~95)
- Modify: `services/company/identity/services/organization.service.ts` (2 insert sites: dòng ~40, ~61)
- Modify: `services/company/identity/services/sync.service.ts` (3 insert sites: dòng ~59, ~96, ~122)
- Modify: `services/company/identity/services/workspace.service.ts` (1 insert site: dòng ~20)

**Interfaces:**
- Consumes: `generateSnowflake` từ `../../shared/services/snowflake.service` (Task 1).

- [ ] **Step 1: Đổi schema — bỏ bigserial**

Trong `services/company/shared/db/schema/identity.ts`:
- Thay **tất cả** (5 chỗ) `bigserial("id", { mode: "bigint" }).primaryKey(),` → `bigint("id", { mode: "bigint" }).primaryKey(),` (string thay thế giống hệt nhau ở cả 5 chỗ — dùng replace toàn file, không cần phân biệt từng bảng).
- Xoá `bigserial` khỏi dòng `import { pgSchema, text, bigint, bigserial, timestamp } from "drizzle-orm/pg-core";` (đầu file) — không còn dùng nữa.

- [ ] **Step 2: Viết migration**

```sql
-- services/company/identity/migrations/4_snowflake_ids.up.sql
-- Chuyển 5 bảng identity từ bigserial (auto-increment) sang snowflake ID sinh
-- ở tầng ứng dụng — đúng quy ước db.md. Xoá sạch dữ liệu cũ vì ID serial cũ
-- không còn tương thích với ID sinh mới (theo yêu cầu, không cần giữ lại).
TRUNCATE TABLE core.organizations, core.users, core.workforce_members, core.workspace_members, core.workspaces CASCADE;

ALTER TABLE core.organizations ALTER COLUMN id DROP DEFAULT;
ALTER TABLE core.users ALTER COLUMN id DROP DEFAULT;
ALTER TABLE core.workforce_members ALTER COLUMN id DROP DEFAULT;
ALTER TABLE core.workspace_members ALTER COLUMN id DROP DEFAULT;
ALTER TABLE core.workspaces ALTER COLUMN id DROP DEFAULT;
```

- [ ] **Step 3: Sửa 4 file service — thêm `id: generateSnowflake()` vào từng insert**

Với mỗi file, thêm dòng import (nếu chưa có) ngay dưới các import hiện có:
```ts
import { generateSnowflake } from "../../shared/services/snowflake.service";
```

Rồi ở MỖI lệnh `.insert(<table>).values({ ... })` liệt kê dưới đây, thêm `id: generateSnowflake(),` làm property ĐẦU TIÊN bên trong `{ ... }`:

- `auth.service.ts` dòng ~76 (`.insert(identityUsers)`), ~87 (`.insert(identityWorkspaces)`), ~95 (`tx.insert(identityWorkspaceMembers)`)
- `organization.service.ts` dòng ~40 (`.insert(identityOrganizations)`), ~61 (`.insert(identityWorkforceMembers)`)
- `sync.service.ts` dòng ~59 (`.insert(identityUsers)`), ~96 (`.insert(identityWorkspaces)`), ~122 (`tx.insert(identityWorkspaceMembers)`)
- `workspace.service.ts` dòng ~20 (`.insert(identityWorkspaces)`)

Số dòng là ước lượng tại thời điểm viết plan — tìm đúng bằng cách grep `\.insert(` trong từng file nếu số dòng đã lệch do các thay đổi trước đó.

- [ ] **Step 4: Chạy migration**

Run: `cd services/company && node scripts/migrate.mjs`
Expected: log áp dụng thành công `4_snowflake_ids.up.sql`, không lỗi.

- [ ] **Step 5: Chạy test module identity**

Run: `cd services/company && encore test identity`
Expected: toàn bộ test trong `identity/tests/` PASS.

- [ ] **Step 6: Commit**

```bash
git add services/company/shared/db/schema/identity.ts services/company/identity/migrations/4_snowflake_ids.up.sql services/company/identity/services/auth.service.ts services/company/identity/services/organization.service.ts services/company/identity/services/sync.service.ts services/company/identity/services/workspace.service.ts
git commit -m "feat(company): migrate module identity sang snowflake ID"
```

---

### Task 3: Module operations — phần chính (13 bảng: 6 operating + 7 strategy định nghĩa trong operations.ts)

**Files:**
- Modify: `services/company/shared/db/schema/operations.ts`
- Create: `services/company/operations/migrations/8_snowflake_ids.up.sql`
- Modify: `services/company/operations/services/initiative.service.ts` (1 site: `.insert(initiatives)`)
- Modify: `services/company/operations/services/okr.service.ts` (3 sites: `.insert(okrCycles)`, `.insert(okrObjectives)`, `.insert(keyResults)`)
- Modify: `services/company/operations/services/project.service.ts` (2 sites: `.insert(projects)`, `.insert(portfolios)`)
- Modify: `services/company/operations/services/task-dependency.service.ts` (2 sites: `.insert(taskDependencies)`, `.insert(taskSchedules)`)
- Modify: `services/company/operations/services/task.service.ts` (1 site: `.insert(tasks)`)
- Modify: `services/company/operations/services/twelve-week-year.service.ts` (3 sites: `.insert(twelveWeekCycles)`, `.insert(weeklyPlans)`, `.insert(weeklyCommitments)`)

**Interfaces:**
- Consumes: `generateSnowflake` từ `../../shared/services/snowflake.service`.
- Lưu ý: bảng `strategy.portfolio_projects` (định nghĩa trong `operations.ts`, biến `portfolioProjects`) hiện KHÔNG có lệnh `insert()` nào trong codebase (bảng chưa dùng) — chỉ cần đổi schema + migration, không cần sửa service nào cho bảng này.

- [ ] **Step 1: Đổi schema — bỏ bigserial**

Trong `services/company/shared/db/schema/operations.ts`: thay tất cả `bigserial("id", { mode: "bigint" }).primaryKey(),` → `bigint("id", { mode: "bigint" }).primaryKey(),` (replace toàn file). Xoá `bigserial` khỏi import đầu file.

- [ ] **Step 2: Viết migration**

```sql
-- services/company/operations/migrations/8_snowflake_ids.up.sql
TRUNCATE TABLE operating.task_dependencies, operating.task_schedules, operating.tasks, operating.twelve_week_cycles, operating.weekly_commitments, operating.weekly_plans, strategy.initiatives, strategy.okr_cycles, strategy.okr_objectives, strategy.key_results, strategy.portfolios, strategy.projects, strategy.portfolio_projects CASCADE;

ALTER TABLE operating.task_dependencies ALTER COLUMN id DROP DEFAULT;
ALTER TABLE operating.task_schedules ALTER COLUMN id DROP DEFAULT;
ALTER TABLE operating.tasks ALTER COLUMN id DROP DEFAULT;
ALTER TABLE operating.twelve_week_cycles ALTER COLUMN id DROP DEFAULT;
ALTER TABLE operating.weekly_commitments ALTER COLUMN id DROP DEFAULT;
ALTER TABLE operating.weekly_plans ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.initiatives ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.okr_cycles ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.okr_objectives ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.key_results ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.portfolios ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.projects ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.portfolio_projects ALTER COLUMN id DROP DEFAULT;
```

- [ ] **Step 3: Sửa 6 file service**

Cùng cách làm như Task 2 Step 3: thêm import `generateSnowflake` từ `"../../shared/services/snowflake.service"`, thêm `id: generateSnowflake(),` làm property đầu tiên ở mỗi lệnh `.insert(...).values({...})` liệt kê ở mục **Files** phía trên (tìm chính xác vị trí bằng grep `\.insert(` trong từng file).

- [ ] **Step 4: Chạy migration**

Run: `cd services/company && node scripts/migrate.mjs`

- [ ] **Step 5: Chạy test**

Run: `cd services/company && encore test operations/tests`
Expected: PASS toàn bộ (không chạy `operations/strategy/tests` ở bước này — thuộc Task 4).

- [ ] **Step 6: Commit**

```bash
git add services/company/shared/db/schema/operations.ts services/company/operations/migrations/8_snowflake_ids.up.sql services/company/operations/services/initiative.service.ts services/company/operations/services/okr.service.ts services/company/operations/services/project.service.ts services/company/operations/services/task-dependency.service.ts services/company/operations/services/task.service.ts services/company/operations/services/twelve-week-year.service.ts
git commit -m "feat(company): migrate module operations (core) sang snowflake ID"
```

---

### Task 4: Module operations/strategy (11 bảng còn lại: assumptions, decision_records, discovery_signals, evidence, experiments, gate_evaluations, interviews, next_action_candidates, next_action_rankings, stage_policies, stage_transitions)

**Files:**
- Modify: `services/company/shared/db/schema/strategy.ts`
- Create: `services/company/operations/migrations/9_strategy_snowflake_ids.up.sql`
- Modify: `services/company/operations/strategy/handlers/discovery-signal.handler.ts` (`.insert(discoverySignals)`)
- Modify: `services/company/operations/strategy/handlers/decision-record.handler.ts` (`.insert(decisionRecords)`)
- Modify: `services/company/operations/strategy/handlers/assumption.handler.ts` (`.insert(assumptions)`)
- Modify: `services/company/operations/strategy/handlers/evidence.handler.ts` (`.insert(evidence)`)
- Modify: `services/company/operations/strategy/handlers/gate-evaluation.handler.ts` (`.insert(gateEvaluations)`)
- Modify: `services/company/operations/strategy/handlers/interview.handler.ts` (`.insert(interviews)`)
- Modify: `services/company/operations/strategy/handlers/experiment.handler.ts` (`.insert(experiments)`)
- Modify: `services/company/operations/strategy/handlers/stage-policy.handler.ts` (`.insert(stagePolicies)`)
- Modify: `services/company/operations/strategy/handlers/stage-transition.handler.ts` (`.insert(stageTransitions)`)
- Modify: `services/company/operations/strategy/handlers/next-best-action.handler.ts` (2 sites: `.insert(nextActionCandidates)`, `.insert(nextActionRankings)`)

**Interfaces:**
- Consumes: `generateSnowflake` từ `"../../../shared/services/snowflake.service"` (chú ý: 3 cấp `../` vì các handler này nằm ở `operations/strategy/handlers/`, sâu hơn 1 cấp so với các service khác).
- Lưu ý kiến trúc: khác các module khác, insert() ở đây nằm thẳng trong file `handlers/*.ts` (không tách `services/`) — đây là pattern có sẵn của submodule này, giữ nguyên, không refactor tách file trong task này.

- [ ] **Step 1: Đổi schema — bỏ bigserial**

Trong `services/company/shared/db/schema/strategy.ts`: thay tất cả `bigserial("id", { mode: "bigint" }).primaryKey(),` → `bigint("id", { mode: "bigint" }).primaryKey(),`. Xoá `bigserial` khỏi import đầu file.

- [ ] **Step 2: Viết migration**

```sql
-- services/company/operations/migrations/9_strategy_snowflake_ids.up.sql
TRUNCATE TABLE strategy.assumptions, strategy.decision_records, strategy.discovery_signals, strategy.evidence, strategy.experiments, strategy.gate_evaluations, strategy.interviews, strategy.next_action_candidates, strategy.next_action_rankings, strategy.stage_policies, strategy.stage_transitions CASCADE;

ALTER TABLE strategy.assumptions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.decision_records ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.discovery_signals ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.evidence ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.experiments ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.gate_evaluations ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.interviews ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.next_action_candidates ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.next_action_rankings ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.stage_policies ALTER COLUMN id DROP DEFAULT;
ALTER TABLE strategy.stage_transitions ALTER COLUMN id DROP DEFAULT;
```

- [ ] **Step 3: Sửa 9 file handler**

Cùng cách làm Task 2 Step 3, nhưng import path là `"../../../shared/services/snowflake.service"`. Thêm `id: generateSnowflake(),` làm property đầu tiên ở mỗi `.insert(...).values({...})` liệt kê ở mục **Files**.

- [ ] **Step 4: Chạy migration**

Run: `cd services/company && node scripts/migrate.mjs`

- [ ] **Step 5: Chạy test**

Run: `cd services/company && encore test operations/strategy/tests`
Expected: PASS toàn bộ.

- [ ] **Step 6: Commit**

```bash
git add services/company/shared/db/schema/strategy.ts services/company/operations/migrations/9_strategy_snowflake_ids.up.sql services/company/operations/strategy/handlers/
git commit -m "feat(company): migrate module operations/strategy sang snowflake ID"
```

---

### Task 5: Module commercial (12 bảng: 7 commercial + 5 sales)

**Files:**
- Modify: `services/company/shared/db/schema/commercial.ts`
- Create: `services/company/commercial/migrations/7_snowflake_ids.up.sql`
- Modify: `services/company/commercial/services/account.service.ts` (`.insert(accounts)`)
- Modify: `services/company/commercial/services/contact.service.ts` (`.insert(contacts)`)
- Modify: `services/company/commercial/services/billing.service.ts` (2 sites: `.insert(invoices)`, `.insert(subscriptions)`)
- Modify: `services/company/commercial/services/customer.service.ts` (`.insert(customers)`)
- Modify: `services/company/commercial/services/marketing.service.ts` (3 sites: `.insert(marketingCampaigns)`, `.insert(campaignAssets)`, `.insert(marketingForms)`)
- Modify: `services/company/commercial/services/lead.service.ts` (`.insert(salesLeads)`)
- Modify: `services/company/commercial/services/opportunity.service.ts` (`.insert(salesOpportunities)`)

**Interfaces:**
- Consumes: `generateSnowflake` từ `"../../shared/services/snowflake.service"`.
- Lưu ý: bảng `commercial.marketing_contexts` và `commercial.marketing_lead_intakes` KHÔNG có lệnh `insert()` nào trong codebase — chỉ cần đổi schema + migration.

- [ ] **Step 1: Đổi schema — bỏ bigserial**

Trong `services/company/shared/db/schema/commercial.ts`: thay tất cả `bigserial("id", { mode: "bigint" }).primaryKey(),` → `bigint("id", { mode: "bigint" }).primaryKey(),`. Xoá `bigserial` khỏi import đầu file.

- [ ] **Step 2: Viết migration**

```sql
-- services/company/commercial/migrations/7_snowflake_ids.up.sql
TRUNCATE TABLE commercial.campaign_assets, commercial.invoices, commercial.marketing_campaigns, commercial.marketing_contexts, commercial.marketing_forms, commercial.marketing_lead_intakes, commercial.subscriptions, sales.accounts, sales.contacts, sales.customers, sales.sales_leads, sales.sales_opportunities CASCADE;

ALTER TABLE commercial.campaign_assets ALTER COLUMN id DROP DEFAULT;
ALTER TABLE commercial.invoices ALTER COLUMN id DROP DEFAULT;
ALTER TABLE commercial.marketing_campaigns ALTER COLUMN id DROP DEFAULT;
ALTER TABLE commercial.marketing_contexts ALTER COLUMN id DROP DEFAULT;
ALTER TABLE commercial.marketing_forms ALTER COLUMN id DROP DEFAULT;
ALTER TABLE commercial.marketing_lead_intakes ALTER COLUMN id DROP DEFAULT;
ALTER TABLE commercial.subscriptions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE sales.accounts ALTER COLUMN id DROP DEFAULT;
ALTER TABLE sales.contacts ALTER COLUMN id DROP DEFAULT;
ALTER TABLE sales.customers ALTER COLUMN id DROP DEFAULT;
ALTER TABLE sales.sales_leads ALTER COLUMN id DROP DEFAULT;
ALTER TABLE sales.sales_opportunities ALTER COLUMN id DROP DEFAULT;
```

- [ ] **Step 3: Sửa 7 file service**

Cùng cách làm Task 2 Step 3. Thêm `id: generateSnowflake(),` làm property đầu tiên ở mỗi `.insert(...).values({...})` liệt kê ở mục **Files**.

- [ ] **Step 4: Chạy migration**

Run: `cd services/company && node scripts/migrate.mjs`

- [ ] **Step 5: Chạy test**

Run: `cd services/company && encore test commercial`
Expected: PASS toàn bộ.

- [ ] **Step 6: Commit**

```bash
git add services/company/shared/db/schema/commercial.ts services/company/commercial/migrations/7_snowflake_ids.up.sql services/company/commercial/services/
git commit -m "feat(company): migrate module commercial sang snowflake ID"
```

---

### Task 6: Module finance-legal (14 bảng: 8 finance + 2 legal + 4 validation)

**Files:**
- Modify: `services/company/shared/db/schema/finance-legal.ts`
- Create: `services/company/finance-legal/migrations/10_snowflake_ids.up.sql`
- Modify: `services/company/finance-legal/services/accounting-period.service.ts` (`.insert(accountingPeriods)`)
- Modify: `services/company/finance-legal/services/accounting-profile.service.ts` (`.insert(accountingProfiles)`)
- Modify: `services/company/finance-legal/services/accounting-regime.service.ts` (2 sites: `.insert(accountingFiscalProfiles)`, `.insert(accountingCoaMappings)`)
- Modify: `services/company/finance-legal/services/finance-exception.service.ts` (`.insert(financeExceptions)`)
- Modify: `services/company/finance-legal/services/finance-snapshot.service.ts` (`.insert(financeManagementSnapshots)`)
- Modify: `services/company/finance-legal/services/financial-transaction.service.ts` (`.insert(financialTransactions)`)
- Modify: `services/company/finance-legal/services/legal-obligation.service.ts` (`.insert(legalObligations)`)
- Modify: `services/company/finance-legal/services/legal-checklist-item.service.ts` (`.insert(legalChecklistItems)`)
- Modify: `services/company/finance-legal/services/validation.service.ts` (3 sites: `.insert(validationHypotheses)`, `.insert(validationExperiments)`, `.insert(evidenceItems)`)

**Interfaces:**
- Consumes: `generateSnowflake` từ `"../../shared/services/snowflake.service"`.
- Lưu ý: bảng `finance.accounting_regime_transition_logs` và `validation.customer_interviews` KHÔNG có lệnh `insert()` nào trong codebase — chỉ cần đổi schema + migration.

- [ ] **Step 1: Đổi schema — bỏ bigserial**

Trong `services/company/shared/db/schema/finance-legal.ts`: thay tất cả `bigserial("id", { mode: "bigint" }).primaryKey(),` → `bigint("id", { mode: "bigint" }).primaryKey(),`. Xoá `bigserial` khỏi import đầu file.

- [ ] **Step 2: Viết migration**

```sql
-- services/company/finance-legal/migrations/10_snowflake_ids.up.sql
TRUNCATE TABLE finance.accounting_coa_mappings, finance.accounting_fiscal_profiles, finance.accounting_periods, finance.accounting_profiles, finance.accounting_regime_transition_logs, finance.finance_exceptions, finance.finance_management_snapshots, finance.financial_transactions, legal.legal_checklist_items, legal.legal_obligations, validation.customer_interviews, validation.evidence_items, validation.validation_experiments, validation.validation_hypotheses CASCADE;

ALTER TABLE finance.accounting_coa_mappings ALTER COLUMN id DROP DEFAULT;
ALTER TABLE finance.accounting_fiscal_profiles ALTER COLUMN id DROP DEFAULT;
ALTER TABLE finance.accounting_periods ALTER COLUMN id DROP DEFAULT;
ALTER TABLE finance.accounting_profiles ALTER COLUMN id DROP DEFAULT;
ALTER TABLE finance.accounting_regime_transition_logs ALTER COLUMN id DROP DEFAULT;
ALTER TABLE finance.finance_exceptions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE finance.finance_management_snapshots ALTER COLUMN id DROP DEFAULT;
ALTER TABLE finance.financial_transactions ALTER COLUMN id DROP DEFAULT;
ALTER TABLE legal.legal_checklist_items ALTER COLUMN id DROP DEFAULT;
ALTER TABLE legal.legal_obligations ALTER COLUMN id DROP DEFAULT;
ALTER TABLE validation.customer_interviews ALTER COLUMN id DROP DEFAULT;
ALTER TABLE validation.evidence_items ALTER COLUMN id DROP DEFAULT;
ALTER TABLE validation.validation_experiments ALTER COLUMN id DROP DEFAULT;
ALTER TABLE validation.validation_hypotheses ALTER COLUMN id DROP DEFAULT;
```

- [ ] **Step 3: Sửa 9 file service**

Cùng cách làm Task 2 Step 3. Thêm `id: generateSnowflake(),` làm property đầu tiên ở mỗi `.insert(...).values({...})` liệt kê ở mục **Files**.

- [ ] **Step 4: Chạy migration**

Run: `cd services/company && node scripts/migrate.mjs`

- [ ] **Step 5: Chạy test**

Run: `cd services/company && encore test finance-legal`
Expected: PASS toàn bộ.

- [ ] **Step 6: Commit**

```bash
git add services/company/shared/db/schema/finance-legal.ts services/company/finance-legal/migrations/10_snowflake_ids.up.sql services/company/finance-legal/services/
git commit -m "feat(company): migrate module finance-legal sang snowflake ID"
```

---

### Task 7: Regression toàn bộ + xác nhận DB sạch + xác nhận định dạng snowflake

**Files:**
- Modify (nếu cần theo kết quả Step 2): `services/company/shared/tests/golden-path.e2e.test.ts`

**Bổ sung quan trọng (xem Global Constraints — phần bổ sung sau Task 2):** file `golden-path.e2e.test.ts` (viết ở phase trước, đã merge vào nhánh này) hiện giả định `workspaceId` và các ID khác là `number` (ví dụ gọi trực tiếp handler rồi dùng kết quả làm tham số số). Sau khi Task 2-6 đổi toàn bộ ID/FK sang `string`, file này gần như chắc chắn có lỗi biên dịch/assertion sai kiểu — đây là việc DỰ KIẾN phải sửa ở task này, không phải bug ngoài phạm vi.

- [ ] **Step 1: Xác nhận DB đã trống sau toàn bộ migration**

Run: `docker exec company_db psql -U cosa -d company -c "SELECT (SELECT count(*) FROM core.workspaces) + (SELECT count(*) FROM operating.tasks) + (SELECT count(*) FROM sales.accounts) + (SELECT count(*) FROM finance.financial_transactions) AS total_leftover_rows;"`
Expected: `total_leftover_rows` = 0 (dữ liệu cũ đã bị xoá sạch bởi các migration TRUNCATE ở Task 2–6, chưa seed lại gì).

- [ ] **Step 2: Chạy lại toàn bộ suite**

Run: `cd /Volumes/SSD/javis-saas && make services-test-company`
Expected ban đầu có thể FAIL ở `golden-path.e2e.test.ts` do lỗi kiểu string/number như trên — nếu vậy, sửa file đó (đổi các biến/assertion liên quan ID sang `string`, giữ nguyên toàn bộ narrative nghiệp vụ và các `expect()` khác không liên quan ID) rồi chạy lại `make services-test-company` cho tới khi xanh hết.
Expected cuối cùng: tất cả test PASS (164 test cũ — không thêm/bớt số lượng test trong plan này — 0 FAIL).

- [ ] **Step 3: Xác nhận ID mới là snowflake, không phải serial nhỏ dần**

Trong lúc chạy test ở Step 2, test `identity/tests/register.test.ts` (hoặc bất kỳ test tạo bản ghi nào) đã tạo dữ liệu — kiểm tra:
Run: `docker exec company_db psql -U cosa -d company -c "SELECT id FROM core.workspaces ORDER BY id DESC LIMIT 3;"`
Expected: các `id` là số 15-19 chữ số (đặc trưng snowflake — ví dụ `1858234...`), không phải số nhỏ tuần tự như `1`, `2`, `3`.

- [ ] **Step 4: Nếu có FAIL ở Step 2**

Debug theo `superpowers:systematic-debugging`. Nguyên nhân thường gặp: bỏ sót 1 `insert()` chưa thêm `id`, hoặc migration chưa chạy đúng thứ tự (kiểm tra `public.schema_migrations` xem file `.up.sql` mới đã được áp chưa: `docker exec company_db psql -U cosa -d company -c "SELECT * FROM public.schema_migrations ORDER BY applied_at DESC LIMIT 10;"`).

- [ ] **Step 5: Báo cáo kết thúc**

Tổng hợp: số bảng đã migrate (55), số file service/handler đã sửa, kết quả test cuối, và nhắc rằng bước tiếp theo (sửa bug `/identity/me` + seed tài khoản demo đúng luồng platform, theo spec `2026-08-23-cosa-platform-login-and-me-fix-design.md`) sẽ cần một plan riêng, chạy sau khi plan này hoàn tất.
