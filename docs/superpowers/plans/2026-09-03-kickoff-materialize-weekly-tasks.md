# Materialize Kickoff First-Week vào Weekly Plan + Tasks — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Khi Founder thêm/xoá "hành động tuần đầu" hoặc kích hoạt vòng đầu trong Project Kickoff, backend tự động tạo/xoá `tasks` thật (không qua OKR) gắn vào 1 `weekly_plans` (tuần 1 của 1 `twelve_week_cycles` cho project đó) — thay vì chỉ ghi vào cột JSON `project_operating_setups.first_week_actions` như hiện tại.

**Architecture:** Thêm 1 helper transaction-scoped `materializeFirstWeekPlan()` diff action cũ/mới theo `id` ổn định (tái dùng chính snowflake id của action làm `tasks.id`), gọi từ cả `saveProjectOperatingSetup` (mỗi lần `addAction`/`removeAction` trigger saveDraft) và `activateProjectOperatingSetup`, trong cùng 1 DB transaction với việc ghi `project_operating_setups`.

**Tech Stack:** TypeScript, Encore.ts, Drizzle ORM, Postgres (schema `operating` + `strategy` trong cùng 1 database), Vitest (integration test chạy DB thật).

## Global Constraints

- Migration chỉ Expand (thêm cột/constraint, không đổi kiểu, không xoá) — theo `CLAUDE.md` guardrail #4.
- Handler không được import Drizzle/DB trực tiếp — theo `CLAUDE.md` Encore Guardrail #1 (không áp dụng ở đây vì không sửa handler, chỉ sửa `services/`).
- Không dùng `any`/`@ts-ignore` — theo Encore Guardrail #5.
- Sau khi thêm migration mới, chạy `cd services/company && node scripts/migrate.mjs` (hoặc `make services-migrate-company` từ root) trước khi chạy test liên quan.
- Test chạy bằng `cd services/company && npx vitest run <path>` (integration test, cần Postgres tại `postgresql://workspace_app:...@127.0.0.1:5432/workspace` đã chạy — dev stack qua `docker-compose`).
- Không đụng vào bảng/luồng OKR (`okr_cycles`, `okr_objectives`, `key_results`) — `weekly_commitments.initiativeId` luôn để `null` trong scope này.
- Không backfill dữ liệu `project_operating_setups` cũ — theo xác nhận của user, dữ liệu sẽ reset trước khi migration chạy.

---

## Task 1: Sửa lệch schema Drizzle + thêm 2 FK constraint mới

Bảng `operating.weekly_commitments` đã có cột `deleted_at` ở DB thật (migration `5_create_twelve_week_year.up.sql`) nhưng **không được khai báo trong Drizzle schema** (`operations.ts`) — nghĩa là code hiện tại không đọc/ghi được cột này qua ORM. Cần sửa trước khi dùng nó để soft-delete commitment ở Task 2. Đồng thời thêm FK còn thiếu: `twelve_week_cycles.project_id → strategy.projects.id` và `tasks.weekly_commitment_id → operating.weekly_commitments.id` (2 cột này đã tồn tại từ trước, chỉ chưa có ràng buộc FK).

**Files:**
- Modify: `services/company/shared/db/schema/operations.ts`
- Create: `services/company/operations/migrations/35_kickoff_weekly_task_fks.up.sql`
- Create: `services/company/operations/migrations/35_kickoff_weekly_task_fks.down.sql`
- Test: `services/company/operations/tests/kickoff-weekly-task-schema.test.ts`

**Interfaces:**
- Produces: `weeklyCommitments.deletedAt` (Drizzle column, type `Date | null`) — dùng ở Task 2/3.
- Produces: FK ràng buộc ở DB cho `twelveWeekCycles.projectId` và `tasks.weeklyCommitmentId` — không đổi type nào ở TS side ngoài việc `.references()` được thêm (không đổi tên cột, không đổi field khác dùng nó).

- [ ] **Step 1: Sửa `operations.ts` — thêm `deletedAt` vào `weeklyCommitments`, thêm `.references()` cho 2 cột**

Trong `services/company/shared/db/schema/operations.ts`, sửa định nghĩa `weeklyCommitments` (dòng 150-163 hiện tại) — thêm dòng `deletedAt` ngay sau `updatedAt`:

```ts
export const weeklyCommitments = operatingSchema.table("weekly_commitments", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  weeklyPlanId: bigint("weekly_plan_id", { mode: "bigint" }).notNull().references(() => weeklyPlans.id, { onDelete: "cascade" }),
  initiativeId: bigint("initiative_id", { mode: "bigint" }).references(() => initiatives.id, { onDelete: "set null" }),
  title: varchar("title", { length: 255 }).notNull(),
  status: varchar("status", { length: 50 }).default("todo").notNull(),
  plannedEffort: varchar("planned_effort", { length: 50 }),
  commitmentOwnerType: varchar("commitment_owner_type", { length: 50 }).default("FOUNDER"),
  executionMode: varchar("execution_mode", { length: 50 }).default("MANUAL"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
  deletedAt: timestamp("deleted_at", { withTimezone: true }),
});
```

Sửa `twelveWeekCycles.projectId` (dòng 117 hiện tại, trong khối `twelveWeekCycles`) từ:

```ts
  projectId: bigint("project_id", { mode: "bigint" }),
```

thành:

```ts
  projectId: bigint("project_id", { mode: "bigint" }).references(() => projects.id, { onDelete: "set null" }),
```

(Lưu ý: `projects` được định nghĩa Ở DƯỚI trong cùng file này — Drizzle dùng callback `() => projects.id` nên forward-reference này an toàn, đây là pattern chuẩn của thư viện, không cần đổi thứ tự khai báo. `tasks.initiativeId.references(() => initiatives.id, ...)` trong chính file này cũng là ví dụ tương tự đã chạy production.)

Sửa `tasks.weeklyCommitmentId` (dòng 31 hiện tại) từ:

```ts
  weeklyCommitmentId: bigint("weekly_commitment_id", { mode: "bigint" }),
```

thành:

```ts
  weeklyCommitmentId: bigint("weekly_commitment_id", { mode: "bigint" }).references(() => weeklyCommitments.id, { onDelete: "set null" }),
```

- [ ] **Step 2: Viết migration SQL**

`services/company/operations/migrations/35_kickoff_weekly_task_fks.up.sql`:

```sql
ALTER TABLE operating.twelve_week_cycles
  ADD CONSTRAINT fk_twelve_week_cycles_project_id
  FOREIGN KEY (project_id) REFERENCES strategy.projects(id) ON DELETE SET NULL;

ALTER TABLE operating.tasks
  ADD CONSTRAINT fk_tasks_weekly_commitment_id
  FOREIGN KEY (weekly_commitment_id) REFERENCES operating.weekly_commitments(id) ON DELETE SET NULL;
```

`services/company/operations/migrations/35_kickoff_weekly_task_fks.down.sql`:

```sql
ALTER TABLE operating.tasks
  DROP CONSTRAINT IF EXISTS fk_tasks_weekly_commitment_id;

ALTER TABLE operating.twelve_week_cycles
  DROP CONSTRAINT IF EXISTS fk_twelve_week_cycles_project_id;
```

- [ ] **Step 3: Chạy migration**

Run: `cd /Volumes/SSD/javis-saas/services/company && node scripts/migrate.mjs`
Expected: log hiển thị migration `35_kickoff_weekly_task_fks` đã áp dụng thành công, không lỗi.

Nếu Postgres dev stack chưa chạy, trước tiên: `cd /Volumes/SSD/javis-saas && docker-compose up -d` (khởi động Postgres/MinIO/LiveKit), đợi container `company_db` healthy rồi mới chạy migrate.

- [ ] **Step 4: Viết test xác nhận FK + cột `deletedAt` hoạt động**

```ts
// services/company/operations/tests/kickoff-weekly-task-schema.test.ts
import { describe, it, expect } from "vitest";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createProject } from "../handlers/project.handler";
import { createTestWorkspaceWithMember } from "./_helpers";

const { twelveWeekCycles, weeklyPlans, weeklyCommitments, tasks } = schema;

describe("Kickoff weekly/task schema corrections", () => {
  it("rejects a twelve_week_cycles row whose project_id does not exist", async () => {
    const ws = await createTestWorkspaceWithMember();
    await expect(
      db.insert(twelveWeekCycles).values({
        id: generateSnowflake(),
        workspaceId: BigInt(ws.workspaceId),
        projectId: generateSnowflake(), // random id, no matching project
        durationWeeks: 2,
      })
    ).rejects.toThrow();
  });

  it("rejects a tasks row whose weekly_commitment_id does not exist", async () => {
    const ws = await createTestWorkspaceWithMember();
    await expect(
      db.insert(tasks).values({
        id: generateSnowflake(),
        workspaceId: BigInt(ws.workspaceId),
        title: "Orphan task",
        weeklyCommitmentId: generateSnowflake(), // random id, no matching commitment
      })
    ).rejects.toThrow();
  });

  it("can set and read deletedAt on weekly_commitments", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Schema check project",
    });

    const [cycle] = await db.insert(twelveWeekCycles).values({
      id: generateSnowflake(),
      workspaceId: BigInt(ws.workspaceId),
      projectId: BigInt(project.id),
      durationWeeks: 2,
    }).returning();

    const [plan] = await db.insert(weeklyPlans).values({
      id: generateSnowflake(),
      workspaceId: BigInt(ws.workspaceId),
      cycleId: cycle!.id,
      weekNo: 1,
      focus: "Test focus",
    }).returning();

    const [commitment] = await db.insert(weeklyCommitments).values({
      id: generateSnowflake(),
      workspaceId: BigInt(ws.workspaceId),
      weeklyPlanId: plan!.id,
      title: "Test commitment",
    }).returning();

    expect(commitment!.deletedAt).toBeNull();

    const now = new Date();
    await db.update(weeklyCommitments)
      .set({ deletedAt: now })
      .where(eq(weeklyCommitments.id, commitment!.id));

    const [updated] = await db.select().from(weeklyCommitments).where(eq(weeklyCommitments.id, commitment!.id));
    expect(updated!.deletedAt).not.toBeNull();
  });
});
```

- [ ] **Step 5: Chạy test, xác nhận pass**

Run: `cd /Volumes/SSD/javis-saas/services/company && npx vitest run operations/tests/kickoff-weekly-task-schema.test.ts`
Expected: 3 test PASS.

- [ ] **Step 6: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/company/shared/db/schema/operations.ts \
  services/company/operations/migrations/35_kickoff_weekly_task_fks.up.sql \
  services/company/operations/migrations/35_kickoff_weekly_task_fks.down.sql \
  services/company/operations/tests/kickoff-weekly-task-schema.test.ts
git commit -m "fix(company): thêm deletedAt cho weekly_commitments, FK cho twelve_week_cycles.project_id và tasks.weekly_commitment_id

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: Viết `materializeFirstWeekPlan()` — helper transaction-scoped

**Files:**
- Create: `services/company/operations/strategy/services/project-kickoff-materialize.service.ts`
- Test: `services/company/operations/tests/project-kickoff-materialize.test.ts`

**Interfaces:**
- Consumes: `FirstWeekAction` (`{ id: string; title: string }`) và `BasicKickoffStage` từ `./project-operating-setup.service` — PHẢI dùng `import type` (không phải `import`) vì Task 3 làm `project-operating-setup.service.ts` import ngược lại `materializeFirstWeekPlan` từ file này; `import type` bị TypeScript erase lúc compile nên không tạo circular import runtime thật.
- Consumes: `TenantContext` (`{ workspaceId: string; userId?: string; membershipRole?: string }`) từ `../../../shared/types/tenant_context`.
- Produces: `materializeFirstWeekPlan(tx, ctx, params): Promise<void>` — dùng ở Task 3.
  - `tx: Parameters<Parameters<typeof db.transaction>[0]>[0]` (kiểu transaction chuẩn của codebase, xem `project-stage-lifecycle.service.ts:50`).
  - `params: MaterializeFirstWeekPlanParams` = `{ projectId: string; previousActions: FirstWeekAction[]; actions: FirstWeekAction[]; firstWeekOutcome: string | null; selectedStage: "P0_DISCOVERY" | "P1_PROBLEM_VALIDATION" | null; stageDurationWeeks: number | null }`.

- [ ] **Step 1: Viết test trước (integration, DB thật) cho case "2 action mới"**

```ts
// services/company/operations/tests/project-kickoff-materialize.test.ts
import { describe, it, expect } from "vitest";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { createProject } from "../handlers/project.handler";
import { createTestWorkspaceWithMember } from "./_helpers";
import { materializeFirstWeekPlan } from "../strategy/services/project-kickoff-materialize.service";
import { TenantContext } from "../../shared/types/tenant_context";

const { twelveWeekCycles, weeklyPlans, weeklyCommitments, tasks, taskProjects } = schema;

async function makeCtx(ws: { workspaceId: string; userId: string }): Promise<TenantContext> {
  return { workspaceId: ws.workspaceId, userId: ws.userId, membershipRole: "admin" };
}

describe("materializeFirstWeekPlan", () => {
  it("creates a cycle, week-1 plan, commitments and tasks for new actions", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Materialize test project",
    });
    const ctx = await makeCtx(ws);

    const actions = [
      { id: "1001", title: "Interview lead #1" },
      { id: "1002", title: "Interview lead #2" },
    ];

    await db.transaction(async (tx) => {
      await materializeFirstWeekPlan(tx, ctx, {
        projectId: project.id,
        previousActions: [],
        actions,
        firstWeekOutcome: "Talk to 2 leads",
        selectedStage: "P0_DISCOVERY",
        stageDurationWeeks: 2,
      });
    });

    const [cycle] = await db.select().from(twelveWeekCycles).where(eq(twelveWeekCycles.projectId, BigInt(project.id)));
    expect(cycle).toBeDefined();
    expect(cycle!.durationWeeks).toBe(2);

    const [plan] = await db.select().from(weeklyPlans).where(eq(weeklyPlans.cycleId, cycle!.id));
    expect(plan).toBeDefined();
    expect(plan!.weekNo).toBe(1);
    expect(plan!.focus).toBe("Talk to 2 leads");

    const commitments = await db.select().from(weeklyCommitments).where(eq(weeklyCommitments.weeklyPlanId, plan!.id));
    expect(commitments).toHaveLength(2);
    expect(commitments.every((c) => c.initiativeId === null)).toBe(true);

    const taskRows = await db.select().from(tasks).where(eq(tasks.id, BigInt("1001")));
    expect(taskRows).toHaveLength(1);
    expect(taskRows[0]!.title).toBe("Interview lead #1");
    expect(taskRows[0]!.weeklyCommitmentId).not.toBeNull();

    const links = await db.select().from(taskProjects).where(
      and(eq(taskProjects.taskId, BigInt("1001")), eq(taskProjects.projectId, BigInt(project.id)))
    );
    expect(links).toHaveLength(1);
  });
});
```

- [ ] **Step 2: Chạy test để xác nhận nó FAIL (chưa có implementation)**

Run: `cd /Volumes/SSD/javis-saas/services/company && npx vitest run operations/tests/project-kickoff-materialize.test.ts`
Expected: FAIL — lỗi import, module `project-kickoff-materialize.service` không tồn tại.

- [ ] **Step 3: Viết implementation**

```ts
// services/company/operations/strategy/services/project-kickoff-materialize.service.ts
import { and, desc, eq } from "drizzle-orm";
import { db } from "../../models/db";
import {
  twelveWeekCycles,
  weeklyPlans,
  weeklyCommitments,
  tasks,
  taskProjects,
} from "../../../shared/db/schema/operations";
import { TenantContext } from "../../../shared/types/tenant_context";
import { generateSnowflake } from "../../../shared/services/snowflake.service";
import type { FirstWeekAction, BasicKickoffStage } from "./project-operating-setup.service";

export interface MaterializeFirstWeekPlanParams {
  projectId: string;
  previousActions: FirstWeekAction[];
  actions: FirstWeekAction[];
  firstWeekOutcome: string | null;
  selectedStage: BasicKickoffStage | null;
  stageDurationWeeks: number | null;
}

type Tx = Parameters<Parameters<typeof db.transaction>[0]>[0];

/**
 * Nối first-week actions của Project Kickoff vào dữ liệu thực thi thật:
 * operating.twelve_week_cycles → operating.weekly_plans (tuần 1) →
 * operating.weekly_commitments (không OKR) → operating.tasks.
 * Diff theo `id` ổn định của action (tái dùng làm tasks.id luôn) — action
 * mới xuất hiện thì tạo task, action biến mất thì soft-delete task+commitment.
 * Phải chạy trong transaction chung với việc ghi project_operating_setups.
 */
export async function materializeFirstWeekPlan(
  tx: Tx,
  ctx: TenantContext,
  params: MaterializeFirstWeekPlanParams
): Promise<void> {
  const { projectId, previousActions, actions, firstWeekOutcome, selectedStage, stageDurationWeeks } = params;

  if (actions.length === 0 && previousActions.length === 0) {
    return;
  }

  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(projectId);

  let [cycle] = await tx
    .select()
    .from(twelveWeekCycles)
    .where(and(eq(twelveWeekCycles.projectId, pId), eq(twelveWeekCycles.workspaceId, wsId)))
    .orderBy(desc(twelveWeekCycles.createdAt))
    .limit(1);

  if (!cycle) {
    [cycle] = await tx
      .insert(twelveWeekCycles)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        projectId: pId,
        stageAtStart: selectedStage ?? "P0_DISCOVERY",
        durationWeeks: stageDurationWeeks ?? 2,
      })
      .returning();
  }

  const [plan] = await tx
    .insert(weeklyPlans)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      cycleId: cycle!.id,
      weekNo: 1,
      focus: firstWeekOutcome,
      mission: firstWeekOutcome,
    })
    .onConflictDoUpdate({
      target: [weeklyPlans.cycleId, weeklyPlans.weekNo],
      set: {
        focus: firstWeekOutcome,
        mission: firstWeekOutcome,
        updatedAt: new Date(),
      },
    })
    .returning();

  const previousIds = new Set(previousActions.map((a) => a.id));
  const newIds = new Set(actions.map((a) => a.id));

  const added = actions.filter((a) => !previousIds.has(a.id));
  const removed = previousActions.filter((a) => !newIds.has(a.id));

  for (const action of added) {
    const [commitment] = await tx
      .insert(weeklyCommitments)
      .values({
        id: generateSnowflake(),
        workspaceId: wsId,
        weeklyPlanId: plan!.id,
        initiativeId: null,
        title: action.title,
      })
      .returning();

    const taskId = BigInt(action.id);

    await tx.insert(tasks).values({
      id: taskId,
      workspaceId: wsId,
      title: action.title,
      source: "project_kickoff",
      weeklyCommitmentId: commitment!.id,
    });

    await tx
      .insert(taskProjects)
      .values({
        workspaceId: wsId,
        taskId,
        projectId: pId,
      })
      .onConflictDoNothing();
  }

  for (const action of removed) {
    const taskId = BigInt(action.id);
    const now = new Date();

    const [existingTask] = await tx
      .select({ weeklyCommitmentId: tasks.weeklyCommitmentId })
      .from(tasks)
      .where(and(eq(tasks.id, taskId), eq(tasks.workspaceId, wsId)))
      .limit(1);

    await tx
      .update(tasks)
      .set({ deletedAt: now, status: "cancelled" })
      .where(and(eq(tasks.id, taskId), eq(tasks.workspaceId, wsId)));

    if (existingTask?.weeklyCommitmentId) {
      await tx
        .update(weeklyCommitments)
        .set({ deletedAt: now })
        .where(
          and(
            eq(weeklyCommitments.id, existingTask.weeklyCommitmentId),
            eq(weeklyCommitments.workspaceId, wsId)
          )
        );
    }
  }
}
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas/services/company && npx vitest run operations/tests/project-kickoff-materialize.test.ts`
Expected: PASS.

- [ ] **Step 5: Thêm test cho case "tái sử dụng cycle/plan khi thêm action thứ 3" và case "xoá 1 action"**

Thêm 2 `it()` block vào cùng file test ở Step 1:

```ts
  it("reuses the existing cycle/plan when a 3rd action is added later", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Reuse cycle test",
    });
    const ctx = await makeCtx(ws);

    const firstTwo = [
      { id: "2001", title: "Action A" },
      { id: "2002", title: "Action B" },
    ];

    await db.transaction((tx) =>
      materializeFirstWeekPlan(tx, ctx, {
        projectId: project.id,
        previousActions: [],
        actions: firstTwo,
        firstWeekOutcome: "Outcome v1",
        selectedStage: "P0_DISCOVERY",
        stageDurationWeeks: 2,
      })
    );

    const allThree = [...firstTwo, { id: "2003", title: "Action C" }];

    await db.transaction((tx) =>
      materializeFirstWeekPlan(tx, ctx, {
        projectId: project.id,
        previousActions: firstTwo,
        actions: allThree,
        firstWeekOutcome: "Outcome v2",
        selectedStage: "P0_DISCOVERY",
        stageDurationWeeks: 2,
      })
    );

    const cycles = await db.select().from(twelveWeekCycles).where(eq(twelveWeekCycles.projectId, BigInt(project.id)));
    expect(cycles).toHaveLength(1);

    const plans = await db.select().from(weeklyPlans).where(eq(weeklyPlans.cycleId, cycles[0]!.id));
    expect(plans).toHaveLength(1);
    expect(plans[0]!.focus).toBe("Outcome v2");

    const commitments = await db.select().from(weeklyCommitments).where(eq(weeklyCommitments.weeklyPlanId, plans[0]!.id));
    expect(commitments).toHaveLength(3);

    const thirdTask = await db.select().from(tasks).where(eq(tasks.id, BigInt("2003")));
    expect(thirdTask).toHaveLength(1);
  });

  it("soft-deletes the task and commitment when an action is removed", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Remove action test",
    });
    const ctx = await makeCtx(ws);

    const threeActions = [
      { id: "3001", title: "Keep A" },
      { id: "3002", title: "Remove me" },
      { id: "3003", title: "Keep C" },
    ];

    await db.transaction((tx) =>
      materializeFirstWeekPlan(tx, ctx, {
        projectId: project.id,
        previousActions: [],
        actions: threeActions,
        firstWeekOutcome: "Outcome",
        selectedStage: "P0_DISCOVERY",
        stageDurationWeeks: 2,
      })
    );

    const twoActions = threeActions.filter((a) => a.id !== "3002");

    await db.transaction((tx) =>
      materializeFirstWeekPlan(tx, ctx, {
        projectId: project.id,
        previousActions: threeActions,
        actions: twoActions,
        firstWeekOutcome: "Outcome",
        selectedStage: "P0_DISCOVERY",
        stageDurationWeeks: 2,
      })
    );

    const [removedTask] = await db.select().from(tasks).where(eq(tasks.id, BigInt("3002")));
    expect(removedTask!.deletedAt).not.toBeNull();
    expect(removedTask!.status).toBe("cancelled");

    const [removedCommitment] = await db
      .select()
      .from(weeklyCommitments)
      .where(eq(weeklyCommitments.id, removedTask!.weeklyCommitmentId!));
    expect(removedCommitment!.deletedAt).not.toBeNull();

    const [keptTask] = await db.select().from(tasks).where(eq(tasks.id, BigInt("3001")));
    expect(keptTask!.deletedAt).toBeNull();
  });
```

- [ ] **Step 6: Chạy toàn bộ file test, xác nhận cả 3 test PASS**

Run: `cd /Volumes/SSD/javis-saas/services/company && npx vitest run operations/tests/project-kickoff-materialize.test.ts`
Expected: 3 test PASS.

- [ ] **Step 7: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/company/operations/strategy/services/project-kickoff-materialize.service.ts \
  services/company/operations/tests/project-kickoff-materialize.test.ts
git commit -m "feat(company): materializeFirstWeekPlan — nối kickoff first-week actions vào weekly_plans/tasks thật

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: Nối `materializeFirstWeekPlan` vào `saveProjectOperatingSetup` và `activateProjectOperatingSetup`

**Files:**
- Modify: `services/company/operations/strategy/services/project-operating-setup.service.ts`
- Test: `services/company/operations/tests/project-operating-setup-kickoff-materialize.test.ts`

**Interfaces:**
- Consumes: `materializeFirstWeekPlan` từ Task 2 (signature không đổi).
- `saveProjectOperatingSetup` và `activateProjectOperatingSetup` giữ nguyên signature public (`(ctx, projectId, req) => Promise<...>`) — không đổi contract cho handler/frontend.

- [ ] **Step 1: Viết test trước — `saveDraft` (PUT) tạo task ngay, không cần activate**

```ts
// services/company/operations/tests/project-operating-setup-kickoff-materialize.test.ts
import { describe, it, expect } from "vitest";
import { and, eq, isNull } from "drizzle-orm";
import { db, schema } from "../models/db";
import { createProject } from "../handlers/project.handler";
import {
  putProjectOperatingSetupEndpoint,
  activateProjectOperatingSetupEndpoint,
} from "../strategy/handlers/project-operating-setup.handler";
import { createTestWorkspaceWithMember } from "./_helpers";

const { twelveWeekCycles, weeklyPlans, weeklyCommitments, tasks, taskProjects } = schema;

describe("saveProjectOperatingSetup materializes first-week actions immediately", () => {
  it("creates a real task the moment an action is saved via draft, before activate", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Draft materialize project",
    });

    const saved = await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      firstWeekOutcome: "Interview 3 controllers",
      firstWeekActions: [{ title: "Prepare interview script" }],
    });

    expect(saved.status).toBe("IN_PROGRESS");
    expect(saved.firstWeekActions).toHaveLength(1);
    const actionId = saved.firstWeekActions[0]!.id;

    const [task] = await db.select().from(tasks).where(eq(tasks.id, BigInt(actionId)));
    expect(task).toBeDefined();
    expect(task!.title).toBe("Prepare interview script");
    expect(task!.deletedAt).toBeNull();

    const [link] = await db
      .select()
      .from(taskProjects)
      .where(and(eq(taskProjects.taskId, BigInt(actionId)), eq(taskProjects.projectId, BigInt(project.id))));
    expect(link).toBeDefined();

    const [cycle] = await db.select().from(twelveWeekCycles).where(eq(twelveWeekCycles.projectId, BigInt(project.id)));
    expect(cycle).toBeDefined();

    const [plan] = await db.select().from(weeklyPlans).where(eq(weeklyPlans.cycleId, cycle!.id));
    expect(plan!.focus).toBe("Interview 3 controllers");
  });

  it("removes the task when the action is dropped from a later draft save", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Draft remove project",
    });

    const saved = await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      firstWeekOutcome: "Outcome",
      firstWeekActions: [{ title: "Action to remove" }],
    });
    const actionId = saved.firstWeekActions[0]!.id;

    await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      firstWeekActions: [],
    });

    const [task] = await db.select().from(tasks).where(eq(tasks.id, BigInt(actionId)));
    expect(task!.deletedAt).not.toBeNull();
  });

  it("activate() also materializes even if the founder never saved a draft first", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Activate-only materialize project",
    });

    const result = await activateProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      targetCustomer: "Finance leads",
      problemStatement: "Slow close",
      evidenceLevel: "NONE",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      weeklyReviewWeekday: 5,
      weeklyReviewTime: "16:00",
      firstWeekOutcome: "Talk to 3 leads",
      firstWeekActions: [{ title: "List prospects" }, { title: "Book calls" }],
    });

    expect(result.setup.firstWeekActions).toHaveLength(2);

    for (const action of result.setup.firstWeekActions) {
      const [task] = await db.select().from(tasks).where(eq(tasks.id, BigInt(action.id)));
      expect(task).toBeDefined();
      expect(task!.deletedAt).toBeNull();
    }

    const [cycle] = await db.select().from(twelveWeekCycles).where(eq(twelveWeekCycles.projectId, BigInt(project.id)));
    const [plan] = await db.select().from(weeklyPlans).where(eq(weeklyPlans.cycleId, cycle!.id));
    const liveCommitments = await db
      .select()
      .from(weeklyCommitments)
      .where(and(eq(weeklyCommitments.weeklyPlanId, plan!.id), isNull(weeklyCommitments.deletedAt)));
    expect(liveCommitments).toHaveLength(2);
  });
});
```

- [ ] **Step 2: Chạy test, xác nhận FAIL** (chưa nối materialize vào 2 hàm)

Run: `cd /Volumes/SSD/javis-saas/services/company && npx vitest run operations/tests/project-operating-setup-kickoff-materialize.test.ts`
Expected: FAIL — `task` sẽ là `undefined` vì chưa có gì tạo ra nó.

- [ ] **Step 3: Sửa `saveProjectOperatingSetup` — bọc transaction + gọi materialize**

Trong `services/company/operations/strategy/services/project-operating-setup.service.ts`, thêm import ở đầu file (cạnh các import khác):

```ts
import { materializeFirstWeekPlan } from "./project-kickoff-materialize.service";
```

Thay toàn bộ thân hàm `saveProjectOperatingSetup` (hiện tại dòng 196-329, từ `export async function saveProjectOperatingSetup(` tới dấu `}` đóng hàm) bằng bản có transaction. Giữ nguyên y hệt mọi logic validate/tính toán hiện có (dòng 200-286), chỉ đổi phần truy vấn DB (`db.select`/`db.insert` → `tx.select`/`tx.insert`) và thêm bước materialize trước khi return:

```ts
export async function saveProjectOperatingSetup(
  ctx: TenantContext,
  projectId: string,
  req: SaveProjectOperatingSetupRequest
): Promise<ProjectOperatingSetupView> {
  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(projectId);

  return db.transaction(async (tx) => {
    const [proj] = await tx
      .select({ id: projects.id })
      .from(projects)
      .where(and(eq(projects.id, pId), eq(projects.workspaceId, wsId)))
      .limit(1);

    if (!proj) {
      throw APIError.notFound("Project không tồn tại trong workspace này");
    }

    const [existing] = await tx
      .select()
      .from(projectOperatingSetups)
      .where(and(eq(projectOperatingSetups.projectId, pId), eq(projectOperatingSetups.workspaceId, wsId)))
      .limit(1);

    if (existing && existing.status === "ACTIVE") {
      throw APIError.failedPrecondition("Operating setup đã được kích hoạt (ACTIVE), không thể lưu draft");
    }

    if (req.evidenceLevel && !VALID_EVIDENCE_LEVELS.includes(req.evidenceLevel)) {
      throw APIError.invalidArgument(`evidenceLevel không hợp lệ: ${req.evidenceLevel}`);
    }

    if (req.selectedStage && !VALID_STAGES.includes(req.selectedStage)) {
      throw APIError.invalidArgument(`selectedStage không hợp lệ: ${req.selectedStage}`);
    }

    if (req.firstWeekActions && req.firstWeekActions.length > 3) {
      throw APIError.invalidArgument("firstWeekActions cannot exceed 3 items");
    }

    const selectedStage = req.selectedStage ?? (existing?.selectedStage as BasicKickoffStage | null);
    const evidenceLevel = req.evidenceLevel ?? (existing?.evidenceLevel as EvidenceLevel | null);

    if (
      selectedStage === "P1_PROBLEM_VALIDATION" &&
      evidenceLevel &&
      !["FIVE_PLUS_INTERVIEWS", "PROTOTYPE_OR_REVENUE"].includes(evidenceLevel)
    ) {
      throw APIError.invalidArgument("P1 requires founder-confirmed qualifying evidence");
    }

    if (req.stageDurationWeeks !== undefined && req.stageDurationWeeks !== null) {
      const stageForDuration = selectedStage ?? "P0_DISCOVERY";
      const [min, max] = DURATION_LIMITS[stageForDuration] ?? [1, 2];
      if (req.stageDurationWeeks < min || req.stageDurationWeeks > max) {
        throw APIError.invalidArgument(
          `stageDurationWeeks must be between ${min} and ${max} for ${stageForDuration}`
        );
      }
    }

    if (req.weeklyReviewWeekday !== undefined && req.weeklyReviewWeekday !== null) {
      if (req.weeklyReviewWeekday < 1 || req.weeklyReviewWeekday > 7) {
        throw APIError.invalidArgument("weeklyReviewWeekday must be between 1 and 7");
      }
    }

    if (req.weeklyReviewTime !== undefined && req.weeklyReviewTime !== null) {
      if (!/^([01][0-9]|2[0-3]):[0-5][0-9]$/.test(req.weeklyReviewTime)) {
        throw APIError.invalidArgument("weeklyReviewTime must use HH:mm");
      }
    }

    const durationWeeks = req.stageDurationWeeks === undefined
      ? existing?.stageDurationWeeks ?? null
      : req.stageDurationWeeks;
    const stageTargetDate = req.stageDurationWeeks === undefined
      ? existing?.stageTargetDate ?? null
      : durationWeeks === null
        ? null
        : new Date(Date.now() + durationWeeks * 7 * 24 * 60 * 60 * 1000);

    const actions = req.firstWeekActions !== undefined
      ? normalizeFirstWeekActions(req.firstWeekActions)
      : ((existing?.firstWeekActions as FirstWeekAction[]) || []);

    const previousActions = (existing?.firstWeekActions as FirstWeekAction[]) || [];

    const resolvedOutcome = req.firstWeekOutcome !== undefined ? req.firstWeekOutcome : existing?.firstWeekOutcome ?? null;

    const recommendedStage = req.evidenceLevel !== undefined
      ? recommendKickoffStage(req.evidenceLevel)
      : existing?.recommendedStage ?? (evidenceLevel ? recommendKickoffStage(evidenceLevel) : null);

    const now = new Date();

    const [saved] = await tx
      .insert(projectOperatingSetups)
      .values({
        projectId: pId,
        workspaceId: wsId,
        status: "IN_PROGRESS",
        targetCustomer: req.targetCustomer !== undefined ? req.targetCustomer : existing?.targetCustomer ?? null,
        problemStatement: req.problemStatement !== undefined ? req.problemStatement : existing?.problemStatement ?? null,
        evidenceLevel: req.evidenceLevel !== undefined ? req.evidenceLevel : existing?.evidenceLevel ?? null,
        recommendedStage: recommendedStage as string | null,
        selectedStage: req.selectedStage !== undefined ? req.selectedStage : existing?.selectedStage ?? null,
        stageDurationWeeks: durationWeeks,
        stageTargetDate,
        weeklyReviewWeekday: req.weeklyReviewWeekday !== undefined ? req.weeklyReviewWeekday : existing?.weeklyReviewWeekday ?? null,
        weeklyReviewTime: req.weeklyReviewTime !== undefined ? req.weeklyReviewTime : existing?.weeklyReviewTime ?? null,
        firstWeekOutcome: resolvedOutcome,
        firstWeekActions: actions,
        createdAt: existing?.createdAt ?? now,
        updatedAt: now,
      })
      .onConflictDoUpdate({
        target: projectOperatingSetups.projectId,
        set: {
          status: "IN_PROGRESS",
          targetCustomer: req.targetCustomer !== undefined ? req.targetCustomer : existing?.targetCustomer ?? null,
          problemStatement: req.problemStatement !== undefined ? req.problemStatement : existing?.problemStatement ?? null,
          evidenceLevel: req.evidenceLevel !== undefined ? req.evidenceLevel : existing?.evidenceLevel ?? null,
          recommendedStage: recommendedStage as string | null,
          selectedStage: req.selectedStage !== undefined ? req.selectedStage : existing?.selectedStage ?? null,
          stageDurationWeeks: durationWeeks,
          stageTargetDate,
          weeklyReviewWeekday: req.weeklyReviewWeekday !== undefined ? req.weeklyReviewWeekday : existing?.weeklyReviewWeekday ?? null,
          weeklyReviewTime: req.weeklyReviewTime !== undefined ? req.weeklyReviewTime : existing?.weeklyReviewTime ?? null,
          firstWeekOutcome: resolvedOutcome,
          firstWeekActions: actions,
          updatedAt: now,
        },
      })
      .returning();

    await materializeFirstWeekPlan(tx, ctx, {
      projectId,
      previousActions,
      actions,
      firstWeekOutcome: resolvedOutcome,
      selectedStage: (saved.selectedStage as BasicKickoffStage | null),
      stageDurationWeeks: saved.stageDurationWeeks,
    });

    return toView(saved);
  });
}
```

- [ ] **Step 4: Sửa `activateProjectOperatingSetup` — thêm select `existing` + gọi materialize**

Trong cùng file, hàm `activateProjectOperatingSetup` — bên trong `db.transaction(async (tx) => {`, ngay sau khối `if (!proj) { throw ... }` (trước khối `if (req.selectedStage === "P1_PROBLEM_VALIDATION" ...)`), thêm:

```ts
    const [existing] = await tx
      .select({ firstWeekActions: projectOperatingSetups.firstWeekActions })
      .from(projectOperatingSetups)
      .where(and(eq(projectOperatingSetups.projectId, pId), eq(projectOperatingSetups.workspaceId, wsId)))
      .limit(1);
    const previousActions = (existing?.firstWeekActions as FirstWeekAction[]) || [];
```

Ngay sau khối `await appendOutboxEvent(tx, event);` (trước `const [refreshedProject] = await tx...`), thêm:

```ts
    await materializeFirstWeekPlan(tx, ctx, {
      projectId,
      previousActions,
      actions: normalizedActions,
      firstWeekOutcome: req.firstWeekOutcome.trim(),
      selectedStage: req.selectedStage,
      stageDurationWeeks: req.stageDurationWeeks,
    });
```

- [ ] **Step 5: Chạy test, xác nhận PASS**

Run: `cd /Volumes/SSD/javis-saas/services/company && npx vitest run operations/tests/project-operating-setup-kickoff-materialize.test.ts`
Expected: 3 test PASS.

- [ ] **Step 6: Chạy lại TOÀN BỘ test suite của `project-operating-setup` (file cũ) để đảm bảo không có regression**

Run: `cd /Volumes/SSD/javis-saas/services/company && npx vitest run operations/tests/project-operating-setup.test.ts`
Expected: tất cả test cũ (7 test, xem file hiện tại) vẫn PASS — đặc biệt test "rejects invalid activations and rolls back cleanly without side effects" vẫn phải PASS, xác nhận `materializeFirstWeekPlan` bên trong transaction không phá vỡ rollback khi validate fail ở các bước validate PHÍA TRƯỚC lời gọi materialize (materialize chỉ chạy sau khi mọi validate đã pass, nên các case reject sớm không chạm tới nó).

- [ ] **Step 7: Chạy toàn bộ test suite `operations/` để bắt regression rộng hơn**

Run: `cd /Volumes/SSD/javis-saas/services/company && npx vitest run operations/tests/`
Expected: toàn bộ PASS.

- [ ] **Step 8: Chạy `make company-boundary-check`, `make encore-handler-boundary-check`, `make ts-suppression-check`** (theo CLAUDE.md Encore Guardrail #6 — bắt buộc khi đổi code trong `services/company`)

Run (từ root repo): `make company-boundary-check && make encore-handler-boundary-check && make ts-suppression-check`
Expected: cả 3 lệnh pass, không cảnh báo mới (handler `project-operating-setup.handler.ts` không bị sửa, service không import gì mới ngoài phạm vi cho phép).

- [ ] **Step 9: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/company/operations/strategy/services/project-operating-setup.service.ts \
  services/company/operations/tests/project-operating-setup-kickoff-materialize.test.ts
git commit -m "feat(company): saveDraft và activate operating setup giờ materialize first-week actions thành tasks thật

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Ghi chú sau khi hoàn thành plan

- **Chưa verify UI**: Task/12WY module ở frontend (`frontend/lib/modules/tasks/`, `frontend/lib/modules/hologram_hub/widgets/twelve_wy/`) được giả định sẽ tự hiển thị task/cycle mới vì chúng query theo `workspaceId` chung — plan này KHÔNG chạy Flutter app để xác nhận bằng mắt. Khuyến nghị: sau khi merge, mở app thật, chạy hết luồng kickoff 3 bước, kiểm tra tab "Nhiệm vụ" và "Kế hoạch 12WY" có xuất hiện đúng task/cycle mới không.
- **Chưa có UI review tuần**: cột `weekly_plans.executionScore/outcomeScore/reflection` giờ có dữ liệu để review, nhưng chưa có màn hình nào ghi vào các cột này — đây là tính năng riêng, chưa nằm trong plan này.
