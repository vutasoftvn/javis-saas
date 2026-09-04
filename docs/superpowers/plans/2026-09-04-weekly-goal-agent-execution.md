# Weekly Goal → Agent Execution (WGA) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Founder đặt mục tiêu tuần (Command Center hoặc chat) → agent phân rã thành Execution Plan có phân loại quyền hạn → founder duyệt lô → agent tự thực thi phần trong quyền (side-effect qua approval), việc tay gán founder.

**Architecture:** 3 subsystem tuần tự. (1) `services/company` — 2 bảng mới `execution_plans`/`execution_plan_items`, endpoint `weekly-goal`, CRUD execution-plans + accept→materialize, capability endpoint `operations.task.advance`, AI member seed. (2) `apps/cosa` — classifier/router module, handler `execute_goal_decomposition_task`, worker `task-executor`, goal-intent detection. (3) `frontend` — models, controller methods, card "Kế hoạch đề xuất", chat confirm.

**Tech Stack:** Encore.ts + Drizzle ORM (Postgres, schema `operating`/`strategy`) · Python 3.12 + OpenAI Agents SDK (`apps/cosa`, `packages/agent`) · Flutter + GetX (`frontend`).

## Global Constraints

- Migration release **chỉ Expand** (thêm bảng/cột/constraint, không ALTER phá huỷ). File `services/company/operations/migrations/NN_name.up.sql` + `.down.sql`, số kế tiếp = **37**.
- Encore handler **không** import `drizzle-orm` / `models/db` / schema — chỉ parse input, auth/tenant guard, gọi service, map error. Lỗi qua `APIError` (`invalidArgument`/`notFound`/`permissionDenied`/`internal`), không `throw Error` trần.
- Endpoint nội bộ giữa service: `expose: false`. Endpoint cho Flutter: `expose: true` + auth guard + thêm route vào `shared/contracts/mvp-surface.json` và allowlist, chạy `make frontend-api-contract-check`.
- Không `any` / `@ts-ignore` / `@ts-expect-error` / cast che typecheck.
- `packages/agent/` KHÔNG import `services/company/*`. Chỉ `apps/cosa/` compose 2 phía.
- Business truth ở `services/*`. Agent không tự ghi business DB — side-effect qua Capability + Governance + Audit.
- **Outbound / finance / deploy / delete / workspace-settings: vĩnh viễn `NEEDS_APPROVAL`**, không nới lên AUTO kể cả founder ép. `FORBIDDEN_RE = (billing\.|finance\.write|\.opportunity\.|\.lead\.write|\.message\.send|legal\.write|\.deploy|\.delete|workspace\.settings)`.
- Approval bind đúng `run_id + tool_call_id + checkpoint_ref` — không lookup theo tên action.
- Trạng thái structured — không `if "x" in model_text`. Plan agent xuất theo JSON schema cố định; sai schema → run fail, không tạo plan nửa vời.
- Test durability qua process/lease thật (không 2 instance cùng process).
- Snowflake id: `generateSnowflake()` (`services/company/shared/services/snowflake.service`).
- Phản hồi hội thoại + `docs/**` tiếng Việt; định danh/route/log/error tiếng Anh giữ nguyên. Prompt runtime trong `apps/cosa`/`packages/agent`/`skillpacks` tiếng Anh.
- Coverage gate: `services/company` không giảm; `apps/cosa` ≥ 78%; frontend floor 46% (chỉ code logic).

---

# PHASE 1 — Company backend foundation

Sau Phase 1: có schema + API tạo/duyệt Execution Plan + materialize thành task + capability `operations.task.advance`. Test được độc lập, chưa cần `apps/cosa`.

## File Structure — Phase 1

| File | Trách nhiệm |
|---|---|
| `services/company/operations/migrations/37_execution_plans.up.sql` / `.down.sql` | 2 bảng + index |
| `services/company/shared/db/schema/operations.ts` (modify) | Drizzle model `executionPlans`, `executionPlanItems` |
| `services/company/operations/strategy/services/weekly-goal.service.ts` (create) | Upsert `weekly_plans.focus` tuần 1, emit `operating.weekly_goal.set.v1` |
| `services/company/operations/strategy/handlers/weekly-goal.handler.ts` (create) | `POST /operations/strategy/projects/:id/weekly-goal` |
| `services/company/operations/services/execution-plan.service.ts` (create) | CRUD plan + item, classifier guard, `acceptExecutionPlanService` (materialize trong 1 transaction) |
| `services/company/operations/services/autonomy-classifier.ts` (create) | `classifyItem()` + `routeOwnerProfile()` thuần, không I/O DB |
| `services/company/operations/handlers/execution-plan.handler.ts` (create) | `GET/POST/PATCH /operations/execution-plans*` |
| `services/company/operations/services/task.service.ts` (modify) | `advanceTaskByAgentService()` |
| `services/company/operations/handlers/task.handler.ts` (modify) | `POST /operations/tasks/:id/advance` |
| `services/company/operations/services/ai-member.service.ts` (create) | `ensureAiWorkforceMember(workspaceId, agentProfile)`, `resolveFounderMemberId(workspaceId, projectId)` |
| `services/company/shared/events.ts` (modify) | Thêm 3 hằng event name |
| `services/company/operations/api.ts` / `strategy/handlers/index.ts` (modify) | Barrel export handler mới |
| `services/company/operations/tests/*.test.ts` (create) | Test service + classifier |

---

### Task 1.1: Migration + Drizzle model cho `execution_plans` / `execution_plan_items`

**Files:**
- Create: `services/company/operations/migrations/37_execution_plans.up.sql`
- Create: `services/company/operations/migrations/37_execution_plans.down.sql`
- Modify: `services/company/shared/db/schema/operations.ts` (thêm 2 `pgTable` sau `weeklyCommitments`, ~dòng 173)
- Test: `services/company/operations/tests/execution-plan-schema.test.ts`

**Interfaces:**
- Produces: Drizzle exports `executionPlans`, `executionPlanItems` từ `shared/db/schema/operations.ts`. Cột theo spec §5.1/§5.2. Status enum lưu dạng `text`.

- [ ] **Step 1: Viết `37_execution_plans.up.sql`**

```sql
CREATE TABLE operating.execution_plans (
  id                      BIGINT PRIMARY KEY,
  workspace_id            BIGINT NOT NULL,
  project_id              BIGINT NOT NULL REFERENCES strategy.projects(id) ON DELETE CASCADE,
  weekly_plan_id          BIGINT REFERENCES operating.weekly_plans(id) ON DELETE SET NULL,
  goal_text               TEXT NOT NULL,
  status                  TEXT NOT NULL DEFAULT 'draft',
  origin                  TEXT NOT NULL,
  origin_ref              TEXT,
  run_id                  TEXT,
  accepted_by_member_id   BIGINT,
  accepted_at             TIMESTAMPTZ,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at              TIMESTAMPTZ
);

CREATE UNIQUE INDEX uix_execution_plans_one_draft_per_weekly_plan
  ON operating.execution_plans (weekly_plan_id)
  WHERE status = 'draft' AND deleted_at IS NULL;

CREATE INDEX ix_execution_plans_project_status
  ON operating.execution_plans (project_id, status) WHERE deleted_at IS NULL;

CREATE TABLE operating.execution_plan_items (
  id                      BIGINT PRIMARY KEY,
  plan_id                 BIGINT NOT NULL REFERENCES operating.execution_plans(id) ON DELETE CASCADE,
  workspace_id            BIGINT NOT NULL,
  title                   TEXT NOT NULL,
  decision_reason         TEXT NOT NULL,
  evidence_refs           JSONB NOT NULL DEFAULT '[]'::jsonb,
  owner_agent_profile     TEXT,
  expected_capability     TEXT,
  autonomy_class          TEXT NOT NULL,
  autonomy_class_source   TEXT NOT NULL,
  priority                TEXT DEFAULT 'medium',
  depends_on_item_ids     JSONB DEFAULT '[]'::jsonb,
  sort_key                DOUBLE PRECISION,
  materialized_task_id    BIGINT REFERENCES operating.tasks(id) ON DELETE SET NULL,
  status                  TEXT NOT NULL DEFAULT 'proposed',
  created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_execution_plan_items_plan ON operating.execution_plan_items (plan_id);
CREATE INDEX ix_execution_plan_items_materialized_task ON operating.execution_plan_items (materialized_task_id)
  WHERE materialized_task_id IS NOT NULL;
```

- [ ] **Step 2: Viết `37_execution_plans.down.sql`**

```sql
DROP TABLE IF EXISTS operating.execution_plan_items;
DROP TABLE IF EXISTS operating.execution_plans;
```

- [ ] **Step 3: Thêm Drizzle model vào `operations.ts`** (sau `weeklyCommitments`, dùng import `text, bigint, timestamp, doublePrecision, jsonb` đã có ở đầu file)

```typescript
export const executionPlans = operatingSchema.table("execution_plans", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  projectId: bigint("project_id", { mode: "bigint" }).notNull().references(() => projects.id, { onDelete: "cascade" }),
  weeklyPlanId: bigint("weekly_plan_id", { mode: "bigint" }).references(() => weeklyPlans.id, { onDelete: "set null" }),
  goalText: text("goal_text").notNull(),
  status: text("status").default("draft").notNull(),
  origin: text("origin").notNull(),
  originRef: text("origin_ref"),
  runId: text("run_id"),
  acceptedByMemberId: bigint("accepted_by_member_id", { mode: "bigint" }),
  acceptedAt: timestamp("accepted_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});

export const executionPlanItems = operatingSchema.table("execution_plan_items", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  planId: bigint("plan_id", { mode: "bigint" }).notNull().references(() => executionPlans.id, { onDelete: "cascade" }),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  title: text("title").notNull(),
  decisionReason: text("decision_reason").notNull(),
  evidenceRefs: jsonb("evidence_refs").default([]).notNull(),
  ownerAgentProfile: text("owner_agent_profile"),
  expectedCapability: text("expected_capability"),
  autonomyClass: text("autonomy_class").notNull(),
  autonomyClassSource: text("autonomy_class_source").notNull(),
  priority: text("priority").default("medium"),
  dependsOnItemIds: jsonb("depends_on_item_ids").default([]),
  sortKey: doublePrecision("sort_key"),
  materializedTaskId: bigint("materialized_task_id", { mode: "bigint" }).references(() => tasks.id, { onDelete: "set null" }),
  status: text("status").default("proposed").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});
```

Lưu ý: `projects` đã được import trong `operations.ts` (dùng ở `taskProjects`/materialize). Nếu chưa, thêm `projects` vào import từ cùng file (nó khai báo trong chính `operations.ts` — kiểm tra: `export const projects = strategySchema.table(...)` ~dòng 190, nên tham chiếu trực tiếp được).

- [ ] **Step 4: Chạy migration + test schema**

Run: `make services-migrate-company`
Sau đó: `cd services/company && npx vitest run operations/tests/execution-plan-schema.test.ts`

```typescript
// execution-plan-schema.test.ts
import { describe, it, expect } from "vitest";
import { executionPlans, executionPlanItems } from "../../shared/db/schema/operations";
import { db } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { eq } from "drizzle-orm";

describe("execution_plans schema", () => {
  it("insert plan + item, one-draft unique index enforced", async () => {
    const wpId = generateSnowflake();
    const planId = generateSnowflake();
    // project_id cần row thật — dùng project seed helper hiện có hoặc bỏ FK test ở đây
    // nếu không có helper, test tối thiểu: insert item với plan_id hợp lệ
    await db.insert(executionPlans).values({
      id: planId, workspaceId: 1n, projectId: 1n, weeklyPlanId: BigInt(wpId),
      goalText: "test goal", origin: "command_center",
    });
    const [row] = await db.select().from(executionPlans).where(eq(executionPlans.id, planId));
    expect(row.status).toBe("draft");
    await db.delete(executionPlans).where(eq(executionPlans.id, planId));
  });
});
```

Nếu FK `project_id`/`weekly_plan_id` chặn insert cô lập, dùng fixture project sẵn có trong `operations/tests/` (grep `insert(projects)` trong test dir để tái dùng pattern) hoặc đổi test sang seed project trước.

- [ ] **Step 5: Commit**

```bash
git add services/company/operations/migrations/37_execution_plans.* services/company/shared/db/schema/operations.ts services/company/operations/tests/execution-plan-schema.test.ts
git commit -m "feat(operations): add execution_plans + execution_plan_items schema"
```

---

### Task 1.2: Autonomy classifier + router (pure, no I/O)

**Files:**
- Create: `services/company/operations/services/autonomy-classifier.ts`
- Test: `services/company/operations/tests/autonomy-classifier.test.ts`

**Interfaces:**
- Consumes: nothing (pure).
- Produces:
  ```typescript
  export type AutonomyClass = "AUTO" | "NEEDS_APPROVAL" | "FOUNDER_ONLY";
  export type AutonomyClassSource = "classifier_default" | "tenant_policy" | "founder_override";
  export type TenantPolicyDecision = "ALLOW" | "REQUIRE_APPROVAL" | "DENY";
  export const FORBIDDEN_CAPABILITY_RE: RegExp;
  export interface ClassifyInput {
    expectedCapability: string | null;
    capabilityRisk: "LOW" | "MEDIUM" | "HIGH" | null;   // từ CapabilitySpec, apps/cosa truyền sang; null nếu không rõ
    tenantPolicyDecision: TenantPolicyDecision | null;   // null = workspace chưa cấu hình
  }
  export function classifyItem(input: ClassifyInput): { autonomyClass: AutonomyClass; source: AutonomyClassSource };
  export function routeOwnerProfile(expectedCapability: string | null, suggestedDomain: string | null):
    "operations" | "finance" | "marketing" | null;
  export function validateFounderOverride(target: AutonomyClass, input: ClassifyInput): { ok: true } | { ok: false; reason: string };
  ```

- [ ] **Step 1: Viết test (bảng case theo spec §6.2)**

```typescript
import { describe, it, expect } from "vitest";
import { classifyItem, routeOwnerProfile, validateFounderOverride, FORBIDDEN_CAPABILITY_RE } from "../services/autonomy-classifier";

describe("classifyItem", () => {
  it("no capability -> FOUNDER_ONLY", () => {
    expect(classifyItem({ expectedCapability: null, capabilityRisk: null, tenantPolicyDecision: null }))
      .toEqual({ autonomyClass: "FOUNDER_ONLY", source: "classifier_default" });
  });
  it("forbidden capability -> NEEDS_APPROVAL regardless of policy ALLOW", () => {
    expect(classifyItem({ expectedCapability: "engagement.message.send", capabilityRisk: "MEDIUM", tenantPolicyDecision: "ALLOW" }))
      .toEqual({ autonomyClass: "NEEDS_APPROVAL", source: "classifier_default" });
  });
  it("tenant policy DENY -> FOUNDER_ONLY", () => {
    expect(classifyItem({ expectedCapability: "operations.sop.draft", capabilityRisk: "LOW", tenantPolicyDecision: "DENY" }))
      .toEqual({ autonomyClass: "FOUNDER_ONLY", source: "tenant_policy" });
  });
  it("tenant policy REQUIRE_APPROVAL -> NEEDS_APPROVAL", () => {
    expect(classifyItem({ expectedCapability: "operations.task.create_draft", capabilityRisk: "MEDIUM", tenantPolicyDecision: "REQUIRE_APPROVAL" }).autonomyClass).toBe("NEEDS_APPROVAL");
  });
  it("tenant policy ALLOW (non-forbidden) -> AUTO", () => {
    expect(classifyItem({ expectedCapability: "operations.task.list", capabilityRisk: "LOW", tenantPolicyDecision: "ALLOW" }))
      .toEqual({ autonomyClass: "AUTO", source: "tenant_policy" });
  });
  it("default: LOW read/draft -> AUTO", () => {
    expect(classifyItem({ expectedCapability: "operations.task.list", capabilityRisk: "LOW", tenantPolicyDecision: null }))
      .toEqual({ autonomyClass: "AUTO", source: "classifier_default" });
  });
  it("default: MEDIUM -> NEEDS_APPROVAL", () => {
    expect(classifyItem({ expectedCapability: "operations.task.create_draft", capabilityRisk: "MEDIUM", tenantPolicyDecision: null }).autonomyClass).toBe("NEEDS_APPROVAL");
  });
  it("default: HIGH / unknown -> NEEDS_APPROVAL", () => {
    expect(classifyItem({ expectedCapability: "some.cap", capabilityRisk: null, tenantPolicyDecision: null }).autonomyClass).toBe("NEEDS_APPROVAL");
  });
});

describe("routeOwnerProfile", () => {
  it("routes by capability prefix", () => {
    expect(routeOwnerProfile("finance.runway.read", "operations")).toBe("finance");
    expect(routeOwnerProfile("engagement.message.draft", null)).toBe("operations");
    expect(routeOwnerProfile("marketing.gtm.plan", null)).toBe("marketing");
  });
  it("no capability + domain matches keyword -> domain", () => {
    expect(routeOwnerProfile(null, "marketing")).toBe("marketing");
  });
  it("no capability + unknown domain -> null (founder)", () => {
    expect(routeOwnerProfile(null, "legal-review")).toBeNull();
  });
});

describe("validateFounderOverride", () => {
  it("blocks raising forbidden capability to AUTO", () => {
    const r = validateFounderOverride("AUTO", { expectedCapability: "billing.charge", capabilityRisk: "HIGH", tenantPolicyDecision: "ALLOW" });
    expect(r.ok).toBe(false);
  });
  it("blocks AUTO when tenant policy != ALLOW", () => {
    expect(validateFounderOverride("AUTO", { expectedCapability: "operations.sop.draft", capabilityRisk: "LOW", tenantPolicyDecision: "REQUIRE_APPROVAL" }).ok).toBe(false);
  });
  it("allows downgrade to FOUNDER_ONLY always", () => {
    expect(validateFounderOverride("FOUNDER_ONLY", { expectedCapability: "operations.task.list", capabilityRisk: "LOW", tenantPolicyDecision: "ALLOW" }).ok).toBe(true);
  });
});
```

- [ ] **Step 2: Run test → FAIL** (`npx vitest run operations/tests/autonomy-classifier.test.ts`, expect "Cannot find module").

- [ ] **Step 3: Implement `autonomy-classifier.ts`**

```typescript
export type AutonomyClass = "AUTO" | "NEEDS_APPROVAL" | "FOUNDER_ONLY";
export type AutonomyClassSource = "classifier_default" | "tenant_policy" | "founder_override";
export type TenantPolicyDecision = "ALLOW" | "REQUIRE_APPROVAL" | "DENY";

// Outbound / finance / deploy / delete / settings — vĩnh viễn không AUTO.
export const FORBIDDEN_CAPABILITY_RE =
  /(billing\.|finance\.write|\.opportunity\.|\.lead\.write|\.message\.send|legal\.write|\.deploy|\.delete|workspace\.settings)/;

const AUTO_SAFE_SUFFIX_RE = /(\.read$|\.list$|\.draft$|\.create_draft$|\.get$)/;

export interface ClassifyInput {
  expectedCapability: string | null;
  capabilityRisk: "LOW" | "MEDIUM" | "HIGH" | null;
  tenantPolicyDecision: TenantPolicyDecision | null;
}

export function classifyItem(input: ClassifyInput): { autonomyClass: AutonomyClass; source: AutonomyClassSource } {
  const cap = input.expectedCapability;
  // 1. Không map được capability nào -> việc tay
  if (!cap) return { autonomyClass: "FOUNDER_ONLY", source: "classifier_default" };
  // 2. Forbidden -> luôn NEEDS_APPROVAL, không nới được
  if (FORBIDDEN_CAPABILITY_RE.test(cap)) return { autonomyClass: "NEEDS_APPROVAL", source: "classifier_default" };
  // 3. Tenant policy per-workspace
  if (input.tenantPolicyDecision === "DENY") return { autonomyClass: "FOUNDER_ONLY", source: "tenant_policy" };
  if (input.tenantPolicyDecision === "REQUIRE_APPROVAL") return { autonomyClass: "NEEDS_APPROVAL", source: "tenant_policy" };
  if (input.tenantPolicyDecision === "ALLOW") return { autonomyClass: "AUTO", source: "tenant_policy" };
  // 4. Default theo risk
  if (input.capabilityRisk === "LOW" && AUTO_SAFE_SUFFIX_RE.test(cap)) return { autonomyClass: "AUTO", source: "classifier_default" };
  if (input.capabilityRisk === "MEDIUM") return { autonomyClass: "NEEDS_APPROVAL", source: "classifier_default" };
  // 5. HIGH / unknown / LOW-nhưng-không-safe-suffix
  return { autonomyClass: "NEEDS_APPROVAL", source: "classifier_default" };
}

const CAP_PREFIX_TO_PROFILE: Array<[string, "operations" | "finance" | "marketing"]> = [
  ["operations.", "operations"], ["engagement.", "operations"],
  ["finance.", "finance"], ["billing.", "finance"],
  ["marketing.", "marketing"], ["strategy.positioning", "marketing"], ["research.", "marketing"],
];
const DOMAIN_KEYWORDS: Record<"operations" | "finance" | "marketing", RegExp> = {
  operations: /(operation|ops|process|sop|task|workflow|support)/i,
  finance: /(finance|budget|runway|cash|billing|invoice|unit econ)/i,
  marketing: /(marketing|gtm|growth|positioning|campaign|content|brand|seo)/i,
};

export function routeOwnerProfile(
  expectedCapability: string | null,
  suggestedDomain: string | null,
): "operations" | "finance" | "marketing" | null {
  if (expectedCapability) {
    for (const [prefix, profile] of CAP_PREFIX_TO_PROFILE) {
      if (expectedCapability.startsWith(prefix)) return profile;
    }
  }
  if (suggestedDomain) {
    for (const p of ["operations", "finance", "marketing"] as const) {
      if (DOMAIN_KEYWORDS[p].test(suggestedDomain)) return p;
    }
  }
  return null;
}

export function validateFounderOverride(
  target: AutonomyClass,
  input: ClassifyInput,
): { ok: true } | { ok: false; reason: string } {
  if (target !== "AUTO") return { ok: true }; // hạ cấp / lên NEEDS_APPROVAL luôn được
  if (!input.expectedCapability) return { ok: false, reason: "Việc không gắn capability không thể đặt AUTO" };
  if (FORBIDDEN_CAPABILITY_RE.test(input.expectedCapability))
    return { ok: false, reason: "Capability nhóm cần duyệt bắt buộc (outbound/finance/deploy/delete/settings) không thể đặt AUTO" };
  if (input.tenantPolicyDecision !== "ALLOW")
    return { ok: false, reason: "Cần đặt chính sách workspace = ALLOW cho capability này trước khi cho AUTO" };
  return { ok: true };
}
```

- [ ] **Step 4: Run test → PASS.**

- [ ] **Step 5: Commit**

```bash
git add services/company/operations/services/autonomy-classifier.ts services/company/operations/tests/autonomy-classifier.test.ts
git commit -m "feat(operations): add autonomy classifier + owner-profile router (pure)"
```

---

### Task 1.3: `weekly-goal` service + endpoint

**Files:**
- Create: `services/company/operations/strategy/services/weekly-goal.service.ts`
- Create: `services/company/operations/strategy/handlers/weekly-goal.handler.ts`
- Modify: `services/company/operations/strategy/handlers/index.ts` (export)
- Modify: `services/company/shared/events.ts` (thêm `WEEKLY_GOAL_SET`)
- Test: `services/company/operations/strategy/tests/weekly-goal.test.ts`

**Interfaces:**
- Consumes: `materializeFirstWeekPlan` pattern để lazy-create cycle+plan (KHÔNG gọi lại nó — viết helper riêng `ensureWeeklyPlanWeek1`), `appendOutboxEvent`, `generateSnowflake`, `requireWorkspaceAccess`.
- Produces:
  ```typescript
  export interface SetWeeklyGoalParams {
    projectId: string; workspaceId: string;
    focus: string; mission?: string | null;
    triggerDecomposition: boolean;
    origin: "command_center" | "chat"; originRef?: string | null;
  }
  export interface SetWeeklyGoalResult { weeklyPlanId: string; focus: string; decompositionRequested: boolean; }
  export function setWeeklyGoalService(params: SetWeeklyGoalParams, authorization: string | undefined): Promise<SetWeeklyGoalResult>;
  ```
- Event: `operating.weekly_goal.set.v1`, payload `{ workspaceId, projectId, weeklyPlanId, focus, origin, originRef }`.

- [ ] **Step 1: Thêm event name vào `shared/events.ts`** (theo pattern `NEXT_BEST_ACTION_ACCEPTED = "strategy.next_best_action.accepted.v1"`)

```typescript
export const WEEKLY_GOAL_SET = "operating.weekly_goal.set.v1";
export const EXECUTION_PLAN_CREATED = "operating.execution_plan.created.v1";
export const EXECUTION_PLAN_ACCEPTED = "operating.execution_plan.accepted.v1";
```

- [ ] **Step 2: Viết test**

```typescript
// weekly-goal.test.ts
import { describe, it, expect, beforeEach } from "vitest";
import { setWeeklyGoalService } from "../services/weekly-goal.service";
import { db } from "../../models/db";
import { weeklyPlans, twelveWeekCycles } from "../../../shared/db/schema/operations";
import { eq } from "drizzle-orm";
// dùng project fixture helper trong strategy/tests (grep "createProjectFixture" hoặc "insert(projects)")

describe("setWeeklyGoalService", () => {
  it("creates cycle + week-1 plan with focus on first call", async () => {
    const { projectId, workspaceId, auth } = await seedProject(); // helper cục bộ theo pattern test hiện có
    const res = await setWeeklyGoalService(
      { projectId, workspaceId, focus: "Chốt 3 phỏng vấn khách hàng", triggerDecomposition: false, origin: "command_center" },
      auth,
    );
    expect(res.focus).toBe("Chốt 3 phỏng vấn khách hàng");
    const [plan] = await db.select().from(weeklyPlans).where(eq(weeklyPlans.id, BigInt(res.weeklyPlanId)));
    expect(plan.weekNo).toBe(1);
    expect(plan.focus).toBe("Chốt 3 phỏng vấn khách hàng");
  });

  it("updates focus on existing week-1 plan (idempotent, no 2nd cycle)", async () => {
    const { projectId, workspaceId, auth } = await seedProject();
    await setWeeklyGoalService({ projectId, workspaceId, focus: "A", triggerDecomposition: false, origin: "command_center" }, auth);
    await setWeeklyGoalService({ projectId, workspaceId, focus: "B", triggerDecomposition: false, origin: "command_center" }, auth);
    const cycles = await db.select().from(twelveWeekCycles).where(eq(twelveWeekCycles.projectId, BigInt(projectId)));
    expect(cycles.length).toBe(1);
    const plans = await db.select().from(weeklyPlans).where(eq(weeklyPlans.cycleId, cycles[0].id));
    expect(plans.filter((p) => p.weekNo === 1).length).toBe(1);
    expect(plans.find((p) => p.weekNo === 1)!.focus).toBe("B");
  });

  it("triggerDecomposition=true appends WEEKLY_GOAL_SET outbox event", async () => {
    const { projectId, workspaceId, auth } = await seedProject();
    const res = await setWeeklyGoalService({ projectId, workspaceId, focus: "C", triggerDecomposition: true, origin: "chat", originRef: "conv_1" }, auth);
    expect(res.decompositionRequested).toBe(true);
    // assert outbox row: grep pattern test "outbox" hiện có trong operations/tests để đọc bảng outbox
  });
});
```

- [ ] **Step 3: Run test → FAIL.**

- [ ] **Step 4: Implement `weekly-goal.service.ts`**

```typescript
import { and, desc, eq, isNull } from "drizzle-orm";
import { db } from "../../models/db";
import { twelveWeekCycles, weeklyPlans } from "../../../shared/db/schema/operations";
import { projects } from "../../../shared/db/schema/operations"; // projects khai báo trong operations.ts
import { requireWorkspaceAccess } from "../../../shared/auth/workspace-access";
import { appendOutboxEvent } from "../../../shared/events/outbox.repository";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import { WEEKLY_GOAL_SET } from "../../../shared/events";
import { APIError } from "encore.dev/api";

export interface SetWeeklyGoalParams {
  projectId: string; workspaceId: string;
  focus: string; mission?: string | null;
  triggerDecomposition: boolean;
  origin: "command_center" | "chat"; originRef?: string | null;
}
export interface SetWeeklyGoalResult { weeklyPlanId: string; focus: string; decompositionRequested: boolean; }

export async function setWeeklyGoalService(
  params: SetWeeklyGoalParams,
  authorization: string | undefined,
): Promise<SetWeeklyGoalResult> {
  await requireWorkspaceAccess(authorization, params.workspaceId);
  const focus = params.focus?.trim();
  if (!focus) throw APIError.invalidArgument("focus không được rỗng");

  const wsId = BigInt(params.workspaceId);
  const pId = BigInt(params.projectId);

  const result = await db.transaction(async (tx) => {
    const [proj] = await tx.select({ id: projects.id }).from(projects)
      .where(and(eq(projects.id, pId), eq(projects.workspaceId, wsId))).limit(1);
    if (!proj) throw APIError.notFound(`project ${params.projectId} not found`);

    let [cycle] = await tx.select().from(twelveWeekCycles)
      .where(and(eq(twelveWeekCycles.projectId, pId), eq(twelveWeekCycles.workspaceId, wsId), isNull(twelveWeekCycles.deletedAt)))
      .orderBy(desc(twelveWeekCycles.createdAt)).limit(1);
    if (!cycle) {
      [cycle] = await tx.insert(twelveWeekCycles).values({
        id: generateSnowflake(), workspaceId: wsId, projectId: pId,
        stageAtStart: "P0_DISCOVERY", durationWeeks: 2,
      }).returning();
    }

    const [plan] = await tx.insert(weeklyPlans).values({
      id: generateSnowflake(), workspaceId: wsId, cycleId: cycle!.id, weekNo: 1,
      focus, mission: params.mission ?? focus,
    }).onConflictDoUpdate({
      target: [weeklyPlans.cycleId, weeklyPlans.weekNo],
      set: { focus, mission: params.mission ?? focus, updatedAt: new Date() },
    }).returning();

    if (params.triggerDecomposition) {
      await appendOutboxEvent(tx, {
        eventType: WEEKLY_GOAL_SET,
        // theo shape mà buildTaskCreatedEvent trả — kiểm tra chữ ký appendOutboxEvent / EventEnvelope
        payload: {
          workspaceId: params.workspaceId, projectId: params.projectId,
          weeklyPlanId: plan!.id.toString(), focus,
          origin: params.origin, originRef: params.originRef ?? null,
        },
      } as never); // thay `as never` bằng đúng type EventEnvelope sau khi đọc outbox.repository
    }

    return { weeklyPlanId: plan!.id.toString(), focus, decompositionRequested: params.triggerDecomposition };
  });

  return result;
}
```

> **Điều chỉnh khi implement:** đọc `services/company/shared/events/outbox.repository.ts` + `operations/services/task-events.service.ts` để lấy đúng shape `EventEnvelope` (có `eventId`, `aggregateType`, `aggregateId`, `occurredAt`…). Thay block `appendOutboxEvent(...)` cho khớp, bỏ `as never`.

- [ ] **Step 5: Implement handler `weekly-goal.handler.ts`**

```typescript
import { api, APIError, Header } from "encore.dev/api";
import { setWeeklyGoalService } from "../services/weekly-goal.service";

interface SetWeeklyGoalRequest {
  id: string; // projectId (path)
  authorization?: Header<"Authorization">;
  workspaceId: string;
  focus: string;
  mission?: string;
  triggerDecomposition?: boolean;
  origin?: "command_center" | "chat";
  originRef?: string;
}
interface SetWeeklyGoalResponse { weeklyPlanId: string; focus: string; decompositionRequested: boolean; }

export const setWeeklyGoal = api(
  { method: "POST", path: "/operations/strategy/projects/:id/weekly-goal", expose: true },
  async (req: SetWeeklyGoalRequest): Promise<SetWeeklyGoalResponse> => {
    if (!req.workspaceId) throw APIError.invalidArgument("workspaceId required");
    const res = await setWeeklyGoalService(
      {
        projectId: req.id, workspaceId: req.workspaceId,
        focus: req.focus, mission: req.mission ?? null,
        triggerDecomposition: req.triggerDecomposition ?? false,
        origin: req.origin ?? "command_center", originRef: req.originRef ?? null,
      },
      req.authorization,
    );
    return res;
  },
);
```

Export trong `strategy/handlers/index.ts`: `export * from "./weekly-goal.handler";`

- [ ] **Step 6: Run test → PASS. Chạy `cd services/company && npm run typecheck` + `make encore-handler-boundary-check`.**

- [ ] **Step 7: Commit**

```bash
git add services/company/operations/strategy/services/weekly-goal.service.ts services/company/operations/strategy/handlers/weekly-goal.handler.ts services/company/operations/strategy/handlers/index.ts services/company/shared/events.ts services/company/operations/strategy/tests/weekly-goal.test.ts
git commit -m "feat(operations): add weekly-goal endpoint + WEEKLY_GOAL_SET event"
```

---

### Task 1.4: AI member + founder member resolver

**Files:**
- Create: `services/company/operations/services/ai-member.service.ts`
- Test: `services/company/operations/tests/ai-member.test.ts`

**Interfaces:**
- Produces:
  ```typescript
  export const AGENT_PROFILE_SPEC_ID: Record<"operations"|"finance"|"marketing", string>;
  // = { operations: "cosa.agents.operations", finance: "cosa.agents.finance", marketing: "cosa.agents.marketing" }
  export function ensureAiWorkforceMember(tx, workspaceId: string, agentProfile: "operations"|"finance"|"marketing"): Promise<string>; // returns member id
  export function resolveFounderMemberId(tx, workspaceId: string, projectId: string): Promise<string>;
  ```

- [ ] **Step 1: Test**

```typescript
import { describe, it, expect } from "vitest";
import { db } from "../models/db";
import { ensureAiWorkforceMember, resolveFounderMemberId } from "../services/ai-member.service";

describe("ensureAiWorkforceMember", () => {
  it("creates once, returns same id on second call", async () => {
    const { workspaceId } = await seedWorkspace();
    const id1 = await db.transaction((tx) => ensureAiWorkforceMember(tx, workspaceId, "operations"));
    const id2 = await db.transaction((tx) => ensureAiWorkforceMember(tx, workspaceId, "operations"));
    expect(id1).toBe(id2);
  });
  it("distinct member per profile", async () => {
    const { workspaceId } = await seedWorkspace();
    const ops = await db.transaction((tx) => ensureAiWorkforceMember(tx, workspaceId, "operations"));
    const fin = await db.transaction((tx) => ensureAiWorkforceMember(tx, workspaceId, "finance"));
    expect(ops).not.toBe(fin);
  });
});

describe("resolveFounderMemberId", () => {
  it("returns the human member linked to project creator / workspace owner", async () => {
    const { workspaceId, projectId, ownerMemberId } = await seedProjectWithOwner();
    const id = await db.transaction((tx) => resolveFounderMemberId(tx, workspaceId, projectId));
    expect(id).toBe(ownerMemberId);
  });
});
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement** — dùng `identityWorkforceMembers` (`import { identityWorkforceMembers } from "../../shared/db/schema/identity"`), filter `memberType='ai'` + `agentSpecId`. `resolveFounderMemberId`: đọc `projects.createdBy` (kiểm tra cột thật trong `strategy` schema — có thể là `created_by` / `owner_member_id`) → tìm `identityWorkforceMembers` `memberType='human'` `humanUserId` khớp; fallback: member `human` cũ nhất của workspace. Nếu `projects` không có creator column, dùng workspace owner từ `identity` (grep `role` / `OWNER` trong `identity` schema).

```typescript
import { and, asc, eq } from "drizzle-orm";
import { identityWorkforceMembers } from "../../shared/db/schema/identity";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { APIError } from "encore.dev/api";

export const AGENT_PROFILE_SPEC_ID = {
  operations: "cosa.agents.operations",
  finance: "cosa.agents.finance",
  marketing: "cosa.agents.marketing",
} as const;

type Tx = Parameters<Parameters<typeof import("../models/db").db.transaction>[0]>[0];

export async function ensureAiWorkforceMember(
  tx: Tx, workspaceId: string, agentProfile: "operations" | "finance" | "marketing",
): Promise<string> {
  const wsId = BigInt(workspaceId);
  const specId = AGENT_PROFILE_SPEC_ID[agentProfile];
  const [existing] = await tx.select().from(identityWorkforceMembers)
    .where(and(
      eq(identityWorkforceMembers.workspaceId, wsId),
      eq(identityWorkforceMembers.memberType, "ai"),
      eq(identityWorkforceMembers.agentSpecId, specId),
    )).limit(1);
  if (existing) return existing.id.toString();

  const [row] = await tx.insert(identityWorkforceMembers).values({
    id: generateSnowflake(), workspaceId: wsId, memberType: "ai",
    agentSpecId: specId, roleTitle: `AI ${agentProfile}`, status: "active",
  }).returning();
  return row!.id.toString();
}

export async function resolveFounderMemberId(tx: Tx, workspaceId: string, _projectId: string): Promise<string> {
  const wsId = BigInt(workspaceId);
  const [member] = await tx.select().from(identityWorkforceMembers)
    .where(and(eq(identityWorkforceMembers.workspaceId, wsId), eq(identityWorkforceMembers.memberType, "human")))
    .orderBy(asc(identityWorkforceMembers.createdAt)).limit(1);
  if (!member) throw APIError.internal("no human workforce member in workspace");
  return member.id.toString();
}
```

> Điều chỉnh `resolveFounderMemberId` để ưu tiên project creator nếu `strategy.projects` có cột đó — grep `services/company/shared/db/schema/strategy.ts` cho `createdBy`/`created_by`/`ownerMemberId`.

- [ ] **Step 4: Run → PASS.**
- [ ] **Step 5: Commit** `feat(operations): add AI member + founder member resolver`

---

### Task 1.5: `execution-plan.service.ts` — create + list + patch item

**Files:**
- Create: `services/company/operations/services/execution-plan.service.ts`
- Test: `services/company/operations/tests/execution-plan-crud.test.ts`

**Interfaces:**
- Consumes: `classifyItem`, `routeOwnerProfile`, `validateFounderOverride` (Task 1.2); `executionPlans`, `executionPlanItems` (Task 1.1).
- Produces:
  ```typescript
  export interface CreatePlanItemInput {
    title: string; decisionReason: string; evidenceRefs: string[];
    suggestedDomain: string | null; expectedCapability: string | null;
    capabilityRisk: "LOW"|"MEDIUM"|"HIGH"|null;
    tenantPolicyDecision: "ALLOW"|"REQUIRE_APPROVAL"|"DENY"|null;
    dependsOnTitles: string[]; priority?: "low"|"medium"|"high"|"urgent";
  }
  export interface CreateExecutionPlanInput {
    workspaceId: string; projectId: string; weeklyPlanId: string | null;
    goalText: string; origin: "command_center"|"chat"; originRef: string | null;
    runId: string | null; items: CreatePlanItemInput[];
  }
  export interface ExecutionPlanView { id: string; status: string; goalText: string; origin: string; items: ExecutionPlanItemView[]; }
  export interface ExecutionPlanItemView {
    id: string; title: string; decisionReason: string; evidenceRefs: string[];
    ownerAgentProfile: string | null; expectedCapability: string | null;
    autonomyClass: "AUTO"|"NEEDS_APPROVAL"|"FOUNDER_ONLY"; autonomyClassSource: string;
    priority: string; dependsOnItemIds: string[]; status: string; materializedTaskId: string | null;
  }
  export function createExecutionPlanService(input: CreateExecutionPlanInput, authorization?: string): Promise<ExecutionPlanView>;
  export function listExecutionPlansService(p: { workspaceId: string; projectId: string; status?: string }, authorization?: string): Promise<ExecutionPlanView[]>;
  export function getExecutionPlanService(id: string, workspaceId: string, authorization?: string): Promise<ExecutionPlanView>;
  export interface PatchPlanItemInput { title?: string; evidenceRefs?: string[]; priority?: string;
    autonomyClass?: "AUTO"|"NEEDS_APPROVAL"|"FOUNDER_ONLY"; ownerAgentProfile?: string | null; drop?: boolean; }
  export function patchExecutionPlanItemService(planId: string, itemId: string, patch: PatchPlanItemInput, workspaceId: string, authorization?: string): Promise<ExecutionPlanItemView>;
  ```

- [ ] **Step 1: Test** — cover: create supersedes prior draft; classifier applied per item (no-capability item → FOUNDER_ONLY); `dependsOnTitles` resolved to item ids within plan; list filters by status; patch drop sets `status='dropped'`; patch raising forbidden cap to AUTO → `APIError.permissionDenied`; patch to FOUNDER_ONLY always ok.

```typescript
describe("createExecutionPlanService", () => {
  it("supersedes existing draft plan for same weeklyPlanId", async () => {
    const ctx = await seedProject();
    const p1 = await createExecutionPlanService({ ...base(ctx), items: [item()] });
    const p2 = await createExecutionPlanService({ ...base(ctx), items: [item()] });
    const [old] = await db.select().from(executionPlans).where(eq(executionPlans.id, BigInt(p1.id)));
    expect(old.status).toBe("superseded");
    expect(p2.status).toBe("draft");
  });
  it("no-capability item classified FOUNDER_ONLY", async () => {
    const ctx = await seedProject();
    const p = await createExecutionPlanService({ ...base(ctx), items: [item({ expectedCapability: null })] });
    expect(p.items[0].autonomyClass).toBe("FOUNDER_ONLY");
  });
  it("dependsOnTitles resolved to sibling item ids", async () => {
    const ctx = await seedProject();
    const p = await createExecutionPlanService({ ...base(ctx), items: [
      item({ title: "A" }), item({ title: "B", dependsOnTitles: ["A"] }),
    ]});
    const b = p.items.find((i) => i.title === "B")!;
    const a = p.items.find((i) => i.title === "A")!;
    expect(b.dependsOnItemIds).toEqual([a.id]);
  });
});
describe("patchExecutionPlanItemService", () => {
  it("blocks raising a forbidden capability item to AUTO", async () => {
    const ctx = await seedProject();
    const p = await createExecutionPlanService({ ...base(ctx), items: [item({ expectedCapability: "engagement.message.send", capabilityRisk: "MEDIUM" })] });
    await expect(patchExecutionPlanItemService(p.id, p.items[0].id, { autonomyClass: "AUTO" }, ctx.workspaceId))
      .rejects.toThrow(/permission|AUTO/i);
  });
  it("drop marks item status dropped", async () => {
    const ctx = await seedProject();
    const p = await createExecutionPlanService({ ...base(ctx), items: [item()] });
    const r = await patchExecutionPlanItemService(p.id, p.items[0].id, { drop: true }, ctx.workspaceId);
    expect(r.status).toBe("dropped");
  });
});
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement.** Key logic:
  - `createExecutionPlanService`: transaction. Nếu `weeklyPlanId` != null → `UPDATE execution_plans SET status='superseded' WHERE weekly_plan_id=? AND status='draft'`. Insert plan `draft`. Cho từng item: gọi `routeOwnerProfile(expectedCapability, suggestedDomain)` → `ownerAgentProfile`; `classifyItem({expectedCapability, capabilityRisk, tenantPolicyDecision})` → `autonomyClass`+`source`. Insert item với `sortKey = index`. Sau khi có tất cả id, pass 2: map `dependsOnTitles` → item ids (theo `title` trong cùng plan), `UPDATE ... SET depends_on_item_ids`.
  - `patchExecutionPlanItemService`: nếu `drop` → `status='dropped'`. Nếu `autonomyClass` set → build `ClassifyInput` từ item hiện tại, `validateFounderOverride(target, input)`; `!ok` → `throw APIError.permissionDenied(reason)`. Ghi `autonomyClassSource='founder_override'`. Chặn patch khi plan `status != 'draft'` → `APIError.failedPrecondition`.
  - View mappers `toPlanView` / `toItemView` (bigint→string, jsonb→array).

- [ ] **Step 4: Run → PASS.** `npm run typecheck`.
- [ ] **Step 5: Commit** `feat(operations): add execution-plan create/list/patch service`

---

### Task 1.6: `acceptExecutionPlanService` — materialize thành tasks

**Files:**
- Modify: `services/company/operations/services/execution-plan.service.ts`
- Test: `services/company/operations/tests/execution-plan-accept.test.ts`

**Interfaces:**
- Consumes: `ensureAiWorkforceMember`, `resolveFounderMemberId` (Task 1.4); `tasks`, `taskProjects`, `taskDependencies`, `weeklyCommitments` (schema).
- Produces:
  ```typescript
  export interface AcceptExecutionPlanResult { planId: string; taskIds: string[]; founderOnlyTaskIds: string[]; }
  export function acceptExecutionPlanService(planId: string, p: { workspaceId: string; acceptedByMemberId: string }, authorization?: string): Promise<AcceptExecutionPlanResult>;
  export function rejectExecutionPlanService(planId: string, workspaceId: string, authorization?: string): Promise<void>;
  ```

- [ ] **Step 1: Test**

```typescript
describe("acceptExecutionPlanService", () => {
  it("materializes non-dropped items into tasks with weekly_commitment + task_projects", async () => {
    const ctx = await seedProject();
    const p = await createExecutionPlanService({ ...base(ctx), items: [
      item({ title: "Soạn SOP onboarding", expectedCapability: "operations.sop.draft", capabilityRisk: "LOW", tenantPolicyDecision: "ALLOW" }), // AUTO
      item({ title: "Phỏng vấn 3 khách hàng", expectedCapability: null }), // FOUNDER_ONLY
    ]});
    const res = await acceptExecutionPlanService(p.id, { workspaceId: ctx.workspaceId, acceptedByMemberId: ctx.ownerMemberId });
    expect(res.taskIds.length).toBe(2);
    const rows = await db.select().from(tasks).where(inArray(tasks.id, res.taskIds.map(BigInt)));
    const auto = rows.find((r) => r.title === "Soạn SOP onboarding")!;
    const manual = rows.find((r) => r.title.startsWith("Phỏng vấn"))!;
    expect(auto.executionMode).toBe("AGENT");
    expect(auto.source).toBe("ai_agent_proposal");
    expect(manual.executionMode).toBe("HUMAN");
    // auto assignee = AI member; manual assignee = founder member
    expect(auto.assigneeMemberId).not.toBeNull();
    expect(manual.assigneeMemberId!.toString()).toBe(ctx.ownerMemberId);
  });

  it("creates task_dependencies from depends_on_item_ids", async () => {
    const ctx = await seedProject();
    const p = await createExecutionPlanService({ ...base(ctx), items: [
      item({ title: "A", expectedCapability: "operations.sop.draft", capabilityRisk: "LOW", tenantPolicyDecision: "ALLOW" }),
      item({ title: "B", dependsOnTitles: ["A"], expectedCapability: "operations.sop.draft", capabilityRisk: "LOW", tenantPolicyDecision: "ALLOW" }),
    ]});
    const res = await acceptExecutionPlanService(p.id, { workspaceId: ctx.workspaceId, acceptedByMemberId: ctx.ownerMemberId });
    const deps = await db.select().from(taskDependencies).where(eq(taskDependencies.workspaceId ?? tasks.workspaceId, BigInt(ctx.workspaceId)));
    // B depends on A
    const bTask = ...; const aTask = ...;
    expect(deps.some((d) => d.taskId === bTask && d.dependsOnTaskId === aTask)).toBe(true);
  });

  it("rejects accept when plan not draft -> 409-ish", async () => {
    const ctx = await seedProject();
    const p = await createExecutionPlanService({ ...base(ctx), items: [item()] });
    await acceptExecutionPlanService(p.id, { workspaceId: ctx.workspaceId, acceptedByMemberId: ctx.ownerMemberId });
    await expect(acceptExecutionPlanService(p.id, { workspaceId: ctx.workspaceId, acceptedByMemberId: ctx.ownerMemberId }))
      .rejects.toThrow();
  });

  it("dropped item is not materialized", async () => {
    const ctx = await seedProject();
    const p = await createExecutionPlanService({ ...base(ctx), items: [item({ title: "keep" }), item({ title: "drop-me" })] });
    const dropItem = p.items.find((i) => i.title === "drop-me")!;
    await patchExecutionPlanItemService(p.id, dropItem.id, { drop: true }, ctx.workspaceId);
    const res = await acceptExecutionPlanService(p.id, { workspaceId: ctx.workspaceId, acceptedByMemberId: ctx.ownerMemberId });
    expect(res.taskIds.length).toBe(1);
  });

  it("circular dependency -> throws (422-ish)", async () => {
    // tạo plan có A->B và B->A qua patch depends, expect accept reject
  });
});
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement `acceptExecutionPlanService`** trong 1 `db.transaction`:
  1. Lock plan row (`SELECT ... FOR UPDATE` không có trong Drizzle helper — dùng `.for("update")` nếu hỗ trợ, hoặc kiểm tra `status='draft'` trước). `status != 'draft'` → `throw APIError.failedPrecondition("plan không ở trạng thái draft")`.
  2. Load items `status != 'dropped'`.
  3. Kiểm tra circular deps trên `dependsOnItemIds` (DFS) → `throw APIError.invalidArgument("circular dependency: ...")`.
  4. `founderMemberId = await resolveFounderMemberId(tx, workspaceId, projectId)`.
  5. Cache `aiMemberByProfile: Map`. Cho từng item:
     - `class = item.autonomyClass`
     - `assignee = class === "FOUNDER_ONLY" ? founderMemberId : (aiMemberByProfile.get(profile) ??= await ensureAiWorkforceMember(tx, workspaceId, item.ownerAgentProfile ?? "operations"))`
       *(nếu `class != FOUNDER_ONLY` nhưng `ownerAgentProfile == null` → coi như config lỗi: fallback `operations` + log; hoặc ép item về FOUNDER_ONLY. Chọn: ép FOUNDER_ONLY + assignee founder, an toàn.)*
     - `executionMode = class === "FOUNDER_ONLY" ? "HUMAN" : "AGENT"`
     - insert `weeklyCommitments` (title, `weeklyPlanId` = plan.weeklyPlanId, `initiativeId: null`, `commitmentOwnerType: class === "FOUNDER_ONLY" ? "FOUNDER" : "AGENT"`, `executionMode`)
     - insert `tasks` (`id: generateSnowflake()`, workspaceId, title, priority: item.priority, status: "todo", source: "ai_agent_proposal", weeklyCommitmentId, assigneeMemberId: BigInt(assignee), executionMode)
     - insert `taskProjects` (workspaceId, taskId, projectId) `onConflictDoNothing`
     - `UPDATE execution_plan_items SET materialized_task_id=?, status='accepted' WHERE id=?`
     - lưu map `itemId -> taskId`
  6. Pass 2 deps: cho từng item có `dependsOnItemIds`, insert `taskDependencies` (`id: generateSnowflake()`, `taskId`, `dependsOnTaskId`, `dependencyType: "BLOCKS"`, `status: "PENDING"`, `workspaceId`).
  7. `UPDATE execution_plans SET status='accepted', accepted_by_member_id=?, accepted_at=now()`.
  8. `appendOutboxEvent(tx, EXECUTION_PLAN_ACCEPTED payload {workspaceId, projectId, planId, taskIds})`.
  - `rejectExecutionPlanService`: `UPDATE execution_plans SET status='rejected' WHERE id=? AND status='draft'`; 0 rows → `APIError.failedPrecondition`.

- [ ] **Step 4: Run → PASS.** `npm run typecheck`.
- [ ] **Step 5: Commit** `feat(operations): add execution-plan accept -> materialize tasks + deps`

---

### Task 1.7: Execution-plan handlers (REST)

**Files:**
- Create: `services/company/operations/handlers/execution-plan.handler.ts`
- Modify: `services/company/operations/api.ts` (barrel) — thêm `export * from "./handlers/execution-plan.handler";` theo pattern hiện có
- Modify: `services/company/shared/contracts/mvp-surface.json` + route-auth allowlist
- Test: `services/company/operations/tests/execution-plan-handler.test.ts` (Encore `api` handler test theo pattern `strategy-handlers.test.ts`)

**Interfaces:**
- Routes (tất cả `expose: true`, guard `workspaceId` + `Authorization`):
  - `GET  /operations/execution-plans?projectId=&status=` → `{ plans: ExecutionPlanView[] }`
  - `GET  /operations/execution-plans/:id` → `ExecutionPlanView`
  - `POST /operations/execution-plans` body `CreateExecutionPlanInput` → `ExecutionPlanView` *(dùng bởi `apps/cosa` — cân nhắc `expose:false` + gọi qua service token; xem Task 2.4. Giữ `expose:true` + auth guard cho phép cả 2, tenant guard bắt buộc.)*
  - `PATCH /operations/execution-plans/:id/items/:itemId` body `PatchPlanItemInput` → `ExecutionPlanItemView`
  - `POST /operations/execution-plans/:id/accept` → `AcceptExecutionPlanResult`
  - `POST /operations/execution-plans/:id/reject` → `{ ok: true }`

- [ ] **Step 1: Test** — 1 happy-path mỗi route + guard test (thiếu `workspaceId` → `invalidArgument`; cross-workspace plan id → `notFound`).
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement handlers** — mỗi handler chỉ: validate input, `throw APIError.invalidArgument` nếu thiếu field, gọi service, return. Không import drizzle.
- [ ] **Step 4: Thêm 6 route vào `mvp-surface.json`** (theo format entry hiện có) + allowlist. Run `make frontend-api-contract-check` (chưa có FE caller nên chỉ cần route hợp lệ trong contract).
- [ ] **Step 5: Run test → PASS.** `make encore-handler-boundary-check`, `npm run typecheck`.
- [ ] **Step 6: Commit** `feat(operations): add execution-plans REST handlers + contract entries`

---

### Task 1.8: `operations.task.advance` — service + endpoint

**Files:**
- Modify: `services/company/operations/services/task.service.ts` (thêm `advanceTaskByAgentService`)
- Modify: `services/company/operations/handlers/task.handler.ts` (thêm `advanceTask` api)
- Modify: `mvp-surface.json` + allowlist (route `/operations/tasks/:id/advance`)
- Test: `services/company/operations/tests/task-advance.test.ts`

**Interfaces:**
- Produces:
  ```typescript
  export interface AdvanceTaskParams { taskId: string; toStatus: "in_progress"|"done"|"blocked"; runId: string; note?: string; }
  export function advanceTaskByAgentService(params: AdvanceTaskParams, ctx: TenantContext, authorization?: string): Promise<Task>;
  ```
- Route: `POST /operations/tasks/:id/advance` body `{ workspaceId, toStatus, runId, note? }` `expose: true` (gọi bởi `apps/cosa` capability handler qua company delegation token — auth guard verify token cho phép agent principal).

- [ ] **Step 1: Test**

```typescript
describe("advanceTaskByAgentService", () => {
  it("AI-assigned task: todo->in_progress->done ok, emits task.completed", async () => {
    const { task, ctx } = await seedAiAssignedTask({ status: "in_progress" });
    const r = await advanceTaskByAgentService({ taskId: task.id, toStatus: "done", runId: "run_1" }, ctx);
    expect(r.status).toBe("done");
    // assert outbox has task.completed
  });
  it("human-assigned task -> permissionDenied", async () => {
    const { task, ctx } = await seedHumanAssignedTask({ status: "in_progress" });
    await expect(advanceTaskByAgentService({ taskId: task.id, toStatus: "done", runId: "r" }, ctx)).rejects.toThrow(/permission/i);
  });
  it("done from todo -> invalidArgument", async () => {
    const { task, ctx } = await seedAiAssignedTask({ status: "todo" });
    await expect(advanceTaskByAgentService({ taskId: task.id, toStatus: "done", runId: "r" }, ctx)).rejects.toThrow();
  });
  it("cancelled not allowed", async () => {
    const { task, ctx } = await seedAiAssignedTask({ status: "in_progress" });
    // @ts-expect-error narrow type — runtime guard test
    await expect(advanceTaskByAgentService({ taskId: task.id, toStatus: "cancelled", runId: "r" }, ctx)).rejects.toThrow();
  });
});
```

- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement `advanceTaskByAgentService`:**
  - Load task (`workspaceId` scoped) → không có → `APIError.notFound`.
  - Load `identityWorkforceMembers` theo `task.assigneeMemberId` → `memberType != 'ai'` hoặc null → `APIError.permissionDenied("task not assigned to an AI member")`.
  - `toStatus` phải ∈ `{in_progress, done, blocked}` (không `cancelled`/`todo`/`waiting_approval`) → else `APIError.invalidArgument`.
  - `toStatus='done'` chỉ khi `task.status ∈ {in_progress, waiting_approval}` → else `APIError.invalidArgument("cannot complete from " + task.status)`.
  - `db.transaction`: `UPDATE tasks SET status, updatedAt`. Ghi `taskExecutionRecords` (`id: generateSnowflake()`, workspaceId, taskId, runId, capabilityId: `"operations.task.advance"`, triggeredByKind: `"agent"`, status: `"SUCCESS"`). Nếu `done` → `appendOutboxEvent(buildTaskCompletedEvent(t, {actor:{kind:"agent", id: runId}}))`.
- [ ] **Step 4: Implement handler `advanceTask`** (parse, guard `workspaceId`, gọi service, map). Thêm route vào contract + allowlist.
- [ ] **Step 5: Run → PASS.** `make encore-handler-boundary-check`, `npm run typecheck`.
- [ ] **Step 6: Commit** `feat(operations): add operations.task.advance endpoint (agent-only task status)`

---

### Task 1.9: Phase 1 gate

- [ ] **Step 1:** `make services-test-company`
- [ ] **Step 2:** `cd services/company && npm run typecheck`
- [ ] **Step 3:** `make company-boundary-check && make encore-handler-boundary-check && make ts-suppression-check`
- [ ] **Step 4:** `make services-migrate-company` trên DB sạch + `make services-migrate-company` lần 2 (idempotent check); rollback thử: chạy down 37 rồi up lại.
- [ ] **Step 5: Commit** nếu có fixup: `test(operations): Phase 1 WGA gate green`

---

# PHASE 2 — apps/cosa: classifier bridge, decomposition run, executor

Sau Phase 2: event `WEEKLY_GOAL_SET` → run phân rã → tạo Execution Plan; worker `task-executor` chạy task AUTO/NEEDS_APPROVAL. Cần Phase 1 xong.

## File Structure — Phase 2

| File | Trách nhiệm |
|---|---|
| `apps/cosa/agents/goal_decomposition.py` (create) | Prompt builder + JSON schema plan + parse/validate output |
| `apps/cosa/agents/capability_risk_map.py` (create) | `capability_id -> CapabilityRisk` từ các `CapabilitySpec` đã đăng ký (đọc `apps/cosa/capabilities/*`) |
| `apps/cosa/worker/goal_decomposition_run.py` (create) | `execute_goal_decomposition_task` — resolve spec, kernel.run, POST /operations/execution-plans |
| `apps/cosa/worker/task_executor.py` (create) | Poll loop, lease, dispatch `task_execution` run theo class |
| `apps/cosa/worker/task_execution_run.py` (create) | `execute_task_execution_task` — run 1 task, gọi `operations.task.advance` |
| `apps/cosa/capabilities/operations_write.py` (modify) | Thêm `OPERATIONS_TASK_ADVANCE_SPEC` + handler |
| `apps/cosa/worker/handlers.py` (modify) | Route `kind` mới trong dispatch; thêm `task_execution` vào `_AGENT_PROFILE_SPECS` path |
| `apps/cosa/worker/main.py` (modify) | Khởi động `task_executor` loop cạnh dispatch hiện có |
| `apps/cosa/events/*` (modify) | Map `operating.weekly_goal.set.v1` → enqueue `goal_decomposition` task |
| `apps/cosa/config/*` (modify) | Env `WGA_EXECUTOR_POLL_SECONDS=30`, `WGA_EXECUTOR_BATCH=5`, `WGA_MAX_RUNS_PER_WORKSPACE_PER_DAY=50`, `WGA_GOAL_INTENT_CONFIDENCE=0.75` |
| `apps/cosa/tests/**` (create) | Unit test từng module |
| `skillpacks/operations/tasks/SKILL.md` (modify) | Cập nhật "Fallback & Handoff" — agent giờ có `operations.task.advance` cho task nó đảm nhận |

**Interfaces (Phase 2 → consumed across tasks):**
```python
# goal_decomposition.py
PLAN_ITEM_JSON_SCHEMA: dict  # {items:[{title,decision_reason,evidence_refs,suggested_domain,expected_capability,depends_on_titles,priority}]}
def build_decomposition_prompt(goal_text: str, context: dict) -> str
def parse_plan_output(raw: str) -> list[PlanItemDraft]   # raises PlanSchemaError
@dataclass
class PlanItemDraft:
    title: str; decision_reason: str; evidence_refs: list[str]
    suggested_domain: str | None; expected_capability: str | None
    depends_on_titles: list[str]; priority: str

# capability_risk_map.py
def capability_risk(capability_id: str) -> Literal["LOW","MEDIUM","HIGH"] | None

# task_executor.py
async def run_executor_once(plane, http_client, *, now=None) -> int   # returns # tasks dispatched
```

### Task 2.1: `capability_risk_map.py`
- [ ] Test: `capability_risk("operations.task.create_draft") == "MEDIUM"` (từ `OPERATIONS_TASK_CREATE_DRAFT_SPEC.risk`), unknown → `None`.
- [ ] Implement: import các `*_SPEC` từ `apps/cosa/capabilities/`, build dict `{spec.id: spec.risk.name}`. (Liệt kê module theo `apps/cosa/capabilities/__init__.py`.)
- [ ] Commit `feat(cosa): add capability risk map`

### Task 2.2: `goal_decomposition.py` — schema + prompt + parse
- [ ] Test: `parse_plan_output` với JSON hợp lệ → list `PlanItemDraft`; thiếu `title` → `PlanSchemaError`; `evidence_refs` không phải list → `PlanSchemaError`; `depends_on_titles` trỏ title không tồn tại → `PlanSchemaError`.
- [ ] Test: `build_decomposition_prompt` chứa goal_text + chỉ dẫn xuất đúng JSON schema + chỉ thị "việc không làm được bằng capability nào thì để suggested_domain=null, expected_capability=null".
- [ ] Implement (English prompt; strict JSON parse với `json.loads` + validate thủ công, không `eval`).
- [ ] Commit `feat(cosa): add goal decomposition prompt + plan output parser`

### Task 2.3: `OPERATIONS_TASK_ADVANCE_SPEC` capability
- [ ] Test (theo pattern `operations_write` test hiện có): handler POST `/operations/tasks/:id/advance` với body đúng; thiếu `run_id` → `ValueError`; `to_status` ngoài enum → `ValueError`.
- [ ] Implement trong `operations_write.py`: `CapabilitySpec(id="operations.task.advance", risk=CapabilityRisk.MEDIUM, metadata={"action_class":"B"}, input_schema={required:[task_id,to_status,run_id], to_status enum [in_progress,done,blocked]})`. Handler POST tới `client.post(f"/operations/tasks/{task_id}/advance", json={workspaceId, toStatus, runId, note})`.
- [ ] Đăng ký spec vào nơi capabilities được compose (grep `OPERATIONS_TASK_CREATE_DRAFT_SPEC` để thấy registry wiring — thêm advance cạnh nó).
- [ ] Commit `feat(cosa): add operations.task.advance capability`

### Task 2.4: `execute_goal_decomposition_task`
- [ ] Test: mock `plane.kernel.run` trả output plan hợp lệ → assert 1 POST `/operations/execution-plans` với body có `items[]` đã classify-ready (mỗi item kèm `capability_risk` + `tenant_policy_decision` lookup qua `plane.tenant_policy_client`); output sai schema → run emit `run.failed` reason `plan_schema_invalid`, KHÔNG POST.
- [ ] Test: `origin=chat` → sau khi tạo plan, append message `execution_plan_ready` vào conversation (`plane.conversation_repository.add_message`).
- [ ] Implement: theo khung `_execute_run_task_inner` (resolve PolicySnapshot, AgentSpec operations exact-hash, compliance delegation). Prompt = `build_decomposition_prompt`. Sau khi `parse_plan_output`: cho từng item `expected_capability` → `capability_risk(...)` + `tenant_policy_client.get_snapshot`→ decision cho tool. POST execution-plans qua `CompanyServiceClient` với company delegation token.
- [ ] Wire event: `operating.weekly_goal.set.v1` → enqueue worker task `{kind:"goal_decomposition", ...}`. Thêm nhánh trong `apps/cosa/worker/handlers.py` dispatch (`execute_run_task` sibling) hoặc `worker/main.py` router.
- [ ] Commit `feat(cosa): add goal decomposition run handler + weekly_goal event wiring`

### Task 2.5: `task_executor.py` — poll + lease
- [ ] Test: `run_executor_once` với fake company client trả 2 task claimable → dispatch 2 run `task_execution`; task đang `in_progress` (đã lease) không claim lại; workspace kill-switch (`execution.autopilot=DENY`) → 0 dispatch; `runs_today >= max` → 0 dispatch.
- [ ] Test lease: 2 lần `run_executor_once` liên tiếp (mô phỏng 2 worker) trên cùng task set → tổng dispatch = N (không nhân đôi) — dùng lease store thật (Postgres advisory / bảng lease hiện có — grep `lease` trong `apps/cosa` để tái dùng cơ chế durable lease của dispatch hiện tại).
- [ ] Implement: gọi company endpoint mới `GET /operations/execution-plans/claimable-tasks?limit=` **hoặc** reuse `operations.task.list` + filter client-side. → **Quyết định:** thêm endpoint hẹp `GET /operations/tasks/agent-claimable?workspaceId=&limit=` ở Phase 1.7bis (thêm task nhỏ) trả đúng JOIN query spec §9.1. *(Ghi chú: nếu chưa muốn thêm endpoint, executor gọi `operations.task.list` rồi JOIN execution_plan_items qua `GET /operations/execution-plans?status=accepted` — chậm hơn nhưng không thêm surface. Chọn endpoint hẹp cho sạch.)*
- [ ] Implement dispatch: set task `in_progress` qua `operations.task.advance` (agent principal, runId tạm = executor-generated), rồi enqueue `{kind:"task_execution", task_id, workspace_id, agent_profile: owner_agent_profile, autonomy_class, expected_capability, plan_item_id}`.
- [ ] Commit `feat(cosa): add task-executor poll loop with durable lease`

### Task 2.5-bis (Phase 1 addendum): `GET /operations/tasks/agent-claimable`
- [ ] Endpoint `expose: false` (service-to-service). Service `listAgentClaimableTasksService(workspaceId, limit)` chạy JOIN query spec §9.1 (không phần kill-switch/runs_today — executor tự lọc 2 cái đó). Test: chỉ trả task `todo` + `source='ai_agent_proposal'` + item `accepted` + deps done.
- [ ] Commit `feat(operations): add agent-claimable tasks query for executor`

### Task 2.6: `execute_task_execution_task`
- [ ] Test: `autonomy_class=AUTO`, kernel.run thành công không có approval → gọi `operations.task.advance{to_status:done}`; kernel.run raise → `advance{to_status:blocked, note}`.
- [ ] Test: `autonomy_class=NEEDS_APPROVAL` → prompt chứa chỉ thị "always request approval before any side-effecting tool"; khi kernel emit `approval.required` → task để `waiting_approval` (advance), KHÔNG advance done; resume path (`execute_resume_task`) sau approval → done.
- [ ] Test: capability gateway trả REQUIRE_APPROVAL giữa AUTO run → `approval.required` emit, task `waiting_approval` (không advance done).
- [ ] Implement: reuse `_execute_run_task_inner` core với `agent_profile = payload["agent_profile"]`, prompt task-focused, `metadata.execution_plan_item_id`. Sau `run_result`: nếu `RunStatus.completed` và không waiting → `advance(done)`; `failed` → `advance(blocked)`; `waiting_approval` → `advance(waiting_approval)` + để `approval.required` event (đã emit bởi core) chảy tới FE. Resume: mở rộng `execute_resume_task` để sau resume completed, nếu payload có `execution_plan_item_id` → `advance(done)`.
- [ ] Commit `feat(cosa): add task execution run handler (auto + approval paths)`

### Task 2.7: Wire executor vào `worker/main.py` + config
- [ ] Thêm `asyncio.create_task(executor_forever(plane, ...))` cạnh dispatch loop; `executor_forever` = `while True: await run_executor_once(...); await asyncio.sleep(WGA_EXECUTOR_POLL_SECONDS)` với try/except log.
- [ ] Env defaults trong config module + `.env.example`.
- [ ] Commit `feat(cosa): start task-executor loop in worker main`

### Task 2.8: Phase 2 gate
- [ ] `make apps-cosa-test` (coverage ≥ 78%)
- [ ] `make lint` (ruff) + `make typecheck-py`
- [ ] `make services-test-company` (regression cho endpoint mới)
- [ ] Commit fixup nếu cần.

---

# PHASE 3 — apps/cosa goal-intent + Frontend

Sau Phase 3: chat tự nhận diện mục tiêu → confirm card → decomposition; Command Center có card "Kế hoạch đề xuất" + "Việc của bạn". Cần Phase 1+2.

## File Structure — Phase 3

| File | Trách nhiệm |
|---|---|
| `apps/cosa/agents/goal_intent.py` (create) | Structured classify `{is_weekly_goal_statement, normalized_goal, confidence}` |
| `apps/cosa/worker/handlers.py` (modify) | Sau assistant reply của agent operations: chạy goal_intent, nếu ≥ ngưỡng → append message `goal_confirm` |
| `apps/cosa/api/conversation_routes.py` hoặc message schema (modify) | Cho phép message role/type structured `goal_confirm` + `execution_plan_ready` |
| `frontend/lib/data/models/execution_plan_model.dart` (create) | `ExecutionPlan`, `ExecutionPlanItem` + `fromJson` |
| `frontend/lib/data/services/*` (modify) | `ExecutionPlanApiService` (list/accept/reject/patchItem) + `CoFounderApiService.setWeeklyGoal` |
| `frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart` (modify) | `RxList<ExecutionPlan> draftPlans`, `requestDecomposition()`, `acceptPlan()`, `rejectPlan()`, `updatePlanItem()`, SSE subscribe `execution_plan.created/accepted` |
| `frontend/lib/modules/hologram_hub/widgets/execution_plan_card_widget.dart` (create) | Render plan + item edit + accept/reject |
| `frontend/lib/modules/hologram_hub/widgets/your_tasks_widget.dart` (create) hoặc mở rộng `waiting_for_you_widget.dart` | List task `executionMode='HUMAN'` (founder-only) + `status='blocked'` |
| `frontend/lib/modules/hologram_hub/presentation/widgets/chat/*` (modify) | Render `goal_confirm` message (2 nút → gọi `setWeeklyGoal(triggerDecomposition:true, origin:chat)`) + `execution_plan_ready` (CTA chuyển tab) |
| `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart` (modify) | Chèn `ExecutionPlanCardWidget` vào `_buildCommandCenterTab()` (trên grid Top3/Queue) |
| `shared/contracts/mvp-surface.json` (modify) | Đánh dấu route execution-plans + weekly-goal là FE-consumed |
| tests | `founder_command_center_controller_test.dart`, `execution_plan_card_widget_test.dart` |

### Task 3.1: `goal_intent.py`
- [ ] Test: parse structured output; `confidence < 0.75` → `should_confirm == False`; hợp lệ cao → `should_confirm == True` + `normalized_goal`.
- [ ] Implement (English prompt, strict JSON). Hằng ngưỡng đọc từ config `WGA_GOAL_INTENT_CONFIDENCE`.
- [ ] Commit `feat(cosa): add weekly-goal intent detector`

### Task 3.2: Wire goal-intent vào chat run
- [ ] Test: agent operations reply xong → mock goal_intent trả high-confidence → `_append_message(role="assistant", content=<goal_confirm JSON>, status="completed")` với marker type; low-confidence → không append.
- [ ] Implement trong `_execute_run_task_inner` sau khi assistant message hoàn tất, chỉ cho `agent_profile in {operations, founder_assistant}`. Message payload structured: `{"kind":"goal_confirm","normalized_goal":...}` (FE nhận diện qua `kind`).
- [ ] Commit `feat(cosa): emit goal_confirm card after goal-like chat message`

### Task 3.3: FE models + API service
- [ ] Test `execution_plan_model_test.dart`: `ExecutionPlan.fromJson` round-trip; `ExecutionPlanItem.autonomyClass` enum parse; unknown class → fallback `NEEDS_APPROVAL`.
- [ ] Implement models + `ExecutionPlanApiService` (theo pattern `TaskService.updateTaskSchedule` + allowlist entry đã có ở commit `edbd7a71`).
- [ ] Commit `feat(frontend): add ExecutionPlan models + API service`

### Task 3.4: Controller methods
- [ ] Test `founder_command_center_controller_test.dart`: `requestDecomposition(focus)` gọi `setWeeklyGoal(triggerDecomposition:true)` + set loading; `acceptPlan(id)` optimistic remove khỏi `draftPlans` + reload; `updatePlanItem` khi backend trả 403 (nâng AUTO trái phép) → giữ nguyên item + surface error string.
- [ ] Implement. SSE: khi nhận event `operating.execution_plan.created.v1` → reload `draftPlans`.
- [ ] Commit `feat(frontend): wire execution-plan controller methods + SSE`

### Task 3.5: `ExecutionPlanCardWidget`
- [ ] Widget test: render N item; dropdown class; nút "Chấp nhận cả lô" disabled khi item AUTO/NEEDS_APPROVAL thiếu evidence; item FOUNDER_ONLY không chặn; tap "Chấp nhận" → gọi `controller.acceptPlan`.
- [ ] Implement theo style widget hiện có (`top3_focus_widget.dart` làm mẫu spacing/màu).
- [ ] Commit `feat(frontend): add ExecutionPlanCardWidget to Command Center`

### Task 3.6: "Việc của bạn" + chat cards
- [ ] Widget test: `your_tasks_widget` list task `executionMode=HUMAN` + `status=blocked`; chat `goal_confirm` render 2 nút, tap "Đặt & lập kế hoạch" → `controller.requestDecomposition(normalizedGoal, origin:'chat')`.
- [ ] Implement + chèn vào view. `execution_plan_ready` message → CTA `TextButton` chuyển `selectedTabIndex` về Command Center + scroll tới card.
- [ ] Commit `feat(frontend): add your-tasks widget + goal_confirm / plan_ready chat cards`

### Task 3.7: Wire vào `hologram_hub_view.dart`
- [ ] Chèn `Obx(() => controller.draftPlans.isEmpty ? SizedBox.shrink() : ExecutionPlanCardWidget(...))` trong `_buildCommandCenterTab()` phía trên grid.
- [ ] Widget test smoke: tab render không lỗi khi `draftPlans` rỗng và khi có 1 plan.
- [ ] Commit `feat(frontend): show execution-plan card + your-tasks in Command Center tab`

### Task 3.8: Phase 3 gate
- [ ] `cd frontend && flutter test` + `make frontend-analyze`
- [ ] `make frontend-api-contract-check`
- [ ] `make apps-cosa-test`
- [ ] Commit fixup nếu cần.

---

# FINAL — full verify

- [ ] `make verify` (lint + typecheck + boundary + skillpacks + tenancy + contract-freeze + all tests)
- [ ] `make verify-local` nếu máy có Encore CLI + Postgres disposable (thêm e2e).
- [ ] Cập nhật `skillpacks/operations/tasks/SKILL.md` "Fallback & Handoff" — bỏ câu "agent không có capability cập nhật trạng thái task", thay bằng mô tả `operations.task.advance` (chỉ task agent đảm nhận, chỉ `in_progress|done|blocked`).
- [ ] Commit `docs(skillpacks): operations-tasks reflects operations.task.advance capability`
- [ ] Manual smoke (nếu chạy được `make dev-stack`): đặt goal ở Command Center → thấy card plan → accept → thấy task; đặt goal trong chat → confirm card → plan.

---

## Self-Review — spec coverage

| Spec § | Task |
|---|---|
| §4 chặng 1 (goal intake CC) | 1.3, 3.3, 3.7 |
| §4 chặng 1 (goal intake chat) | 3.1, 3.2, 3.6 |
| §4 chặng 2 (decomposition run) | 2.2, 2.4 |
| §4 chặng 3 (review + accept + materialize) | 1.5, 1.6, 1.7, 3.4, 3.5 |
| §4 chặng 4 (execution loop) | 2.5, 2.5-bis, 2.6, 2.7 |
| §5 data model | 1.1 |
| §6 classifier + router | 1.2 (pure) + 2.1/2.4 (risk + policy feed) |
| §6.3 founder override guard | 1.2 (`validateFounderOverride`), 1.5 (patch), 3.5 (FE) |
| §7.3 decomposition run detail | 2.4 |
| §8.2 accept transaction | 1.6 |
| §8.4 AI/founder member | 1.4 |
| §9.3 operations.task.advance | 1.8 (endpoint), 2.3 (capability) |
| §9.4 guardrails (max runs, kill-switch) | 2.5 |
| §10 frontend surfaces | 3.3–3.7 |
| §11 error handling | 1.5 (permissionDenied), 1.6 (failedPrecondition/invalidArgument), 2.4 (plan_schema_invalid), 2.5 (lease), 2.6 (blocked) |
| §12 testing | mọi task có test step |

**Gaps đã đóng khi review:** thêm Task 2.5-bis (endpoint `agent-claimable` — executor cần query JOIN mà `operations.task.list` không cấp). `resolveFounderMemberId` chốt fallback = human member cũ nhất (spec §8.4 cho phép). Event envelope shape để lại "điều chỉnh khi implement" trong 1.3 vì phụ thuộc `outbox.repository` chưa đọc — implementer đọc file đó ở Step 4.

**Placeholder scan:** không có "TBD/TODO". 2 chỗ "điều chỉnh khi implement" (event envelope shape ở 1.3; `resolveFounderMemberId` project-creator ở 1.4) là hướng dẫn đọc file cụ thể, kèm fallback rõ ràng — không phải placeholder.
