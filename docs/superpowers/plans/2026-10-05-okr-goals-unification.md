# Hợp nhất Goals / OKR (Dự án A0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Một họ bảng OKR duy nhất (`okr_objectives` + `key_results`) có `scope` company/project, nối vào `goals` và `projects`, bỏ họ `strategy.objectives` + `cosa_key_results`.

**Architecture:** Migration theo expand → contract (`038` cộng thêm cột/ràng buộc, `039` đổi FK, xóa họ cũ). Service TypeScript đọc/ghi một họ bảng; tiến độ tính bằng `okr-scoring.service.ts`. Giữ nguyên hình dạng response của `/operations/goals/*` để Flutter không đổi.

**Tech Stack:** Encore.ts (`services/company`), Drizzle ORM, PostgreSQL 16, Vitest chạy dưới `encore test`, Python (`apps/cosa` capability), Flutter (chỉ kiểm tra).

Spec: `docs/superpowers/specs/2026-10-05-okr-goals-unification-design.md` (đọc mục 2.1 trước).

## Global Constraints

- Code trực tiếp trên `main`, **không** tạo git worktree, **không** `git init` mới (CLAUDE.md).
- TypeScript hiện đại, `import` ES, không `require`; dùng `fetch` có sẵn nếu cần HTTP.
- Migration Company đánh số tiếp theo `037`: dùng `038` và `039`; mỗi file có `.up.sql` + `.down.sql`. Thứ tự chạy Agent Core → COSA → Company.
- **Cấm** `TRUNCATE ... CASCADE` trên bảng họ cũ: `strategy.projects` có FK trỏ vào `strategy.objectives`, CASCADE sẽ xóa cả project và task. Dùng `UPDATE projects SET objective_id = NULL` rồi `DELETE`.
- Mọi bảng có `workspace_id NOT NULL`; FK tham chiếu dùng khóa ghép `(id, workspace_id)`.
- Không sửa `instructions`/`capability_refs` trong `apps/cosa/agents/specs.py` (đổi hash AgentSpec, vỡ `tests/contracts/test_company_agent_spec_pins.py`).
- Tên tiếng Việt cho thông báo lỗi hướng người dùng, đúng phong cách file hiện có; thông báo kỹ thuật tiếng Anh giữ nguyên như `okr.service.ts`.
- Chỉ chạy migration/test trên DB dev (cổng 5431). Không đụng staging/production.
- Gate cuối: `make verify` (xem Task 6).

## File Structure

| File | Trách nhiệm | Task |
|---|---|---|
| `services/company/operations/migrations/038_okr_unification_expand.{up,down}.sql` | Cột `scope/goal_id/cycle_id/parent_objective_id`, CHECK, FK ghép, trigger cơ bản | 1 |
| `services/company/operations/migrations/039_okr_unification_contract.{up,down}.sql` | Đổi FK `projects.objective_id`, trigger liên bảng, xóa họ cũ | 4 |
| `services/company/shared/db/schema/operations.ts` | `okrObjectives` thêm cột, `projectId` nullable | 1 |
| `services/company/shared/db/schema/goals.ts` | Bỏ `objectives`, `cosaKeyResults` | 4 |
| `services/company/operations/services/okr.service.ts` | Tạo/đọc objective theo scope, validate căn chỉnh | 2 |
| `services/company/operations/services/goal-okr-stats.service.ts` (mới) | Map objective→goal hiệu lực, thống kê KR theo goal | 3 |
| `services/company/operations/services/goals.service.ts` | Tree/complete đọc họ OKR; bỏ objective/KR bản Startup OS | 3 |
| `services/company/operations/handlers/goals.handler.ts` | Bỏ 3 endpoint `/operations/cosa/*` | 3 |
| `services/company/operations/services/discovery-project.service.ts` | Triage dùng `okr_objectives` | 4 |
| `apps/cosa/capabilities/okr_write.py` | Trả thêm `scope/goalId/parentObjectiveId` | 5 |
| Tests: xem từng Task | | |

---

### Task 1: Migration 038 (expand) và schema Drizzle

**Files:**
- Create: `services/company/operations/migrations/038_okr_unification_expand.up.sql`
- Create: `services/company/operations/migrations/038_okr_unification_expand.down.sql`
- Modify: `services/company/shared/db/schema/operations.ts` (`okrObjectives`, quanh dòng 367-382)
- Test: `services/company/operations/tests/okr-unification-schema.test.ts` (mới)

**Interfaces:**
- Produces: cột `strategy.okr_objectives.{scope text DEFAULT 'project', goal_id bigint, cycle_id bigint, parent_objective_id bigint}`; Drizzle fields `okrObjectives.{scope, goalId, cycleId, parentObjectiveId}`, `projectId` thành `bigint | null`.

- [ ] **Step 1: Viết test ràng buộc (thất bại)**

```ts
// services/company/operations/tests/okr-unification-schema.test.ts
import { describe, expect, it } from "vitest";
import { sql } from "drizzle-orm";
import { db } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { createTestSession } from "../../identity/tests/helpers/test-session";

async function seed() {
  const user = await createTestSession({
    email: `okr-schema-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName: "OKR Schema",
    role: "founder",
  });
  const ws = BigInt(user.workspaceId);
  const goalId = generateSnowflake();
  await db.execute(sql`
    INSERT INTO strategy.goals (id, workspace_id, title, goal_type)
    VALUES (${goalId}, ${ws}, 'G', 'strategic')`);
  return { ws, projectId: BigInt(user.projectId), goalId };
}

async function dbError(p: Promise<unknown>): Promise<string> {
  try {
    await p;
  } catch (e) {
    const err = e as { message?: string; cause?: { message?: string } };
    return `${err.message ?? ""} ${err.cause?.message ?? ""}`;
  }
  return "";
}

describe("okr_objectives unification constraints (038)", () => {
  it("legacy-style insert (project_id only) defaults to scope=project", async () => {
    const { ws, projectId } = await seed();
    const id = generateSnowflake();
    await db.execute(sql`
      INSERT INTO strategy.okr_objectives (id, workspace_id, project_id, title)
      VALUES (${id}, ${ws}, ${projectId}, 'legacy')`);
    const rows = await db.execute(sql`SELECT scope FROM strategy.okr_objectives WHERE id = ${id}`);
    expect((rows.rows ?? rows)[0].scope).toBe("project");
  });

  it("rejects a company objective without goal_id", async () => {
    const { ws } = await seed();
    const msg = await dbError(db.execute(sql`
      INSERT INTO strategy.okr_objectives (id, workspace_id, scope, title)
      VALUES (${generateSnowflake()}, ${ws}, 'company', 'no goal')`));
    expect(msg).toMatch(/chk_okr_objectives_scope_shape/);
  });

  it("rejects a company objective that has a project_id", async () => {
    const { ws, projectId, goalId } = await seed();
    const msg = await dbError(db.execute(sql`
      INSERT INTO strategy.okr_objectives (id, workspace_id, scope, goal_id, project_id, title)
      VALUES (${generateSnowflake()}, ${ws}, 'company', ${goalId}, ${projectId}, 'bad')`));
    expect(msg).toMatch(/chk_okr_objectives_scope_shape/);
  });

  it("rejects a project objective without project_id", async () => {
    const { ws } = await seed();
    const msg = await dbError(db.execute(sql`
      INSERT INTO strategy.okr_objectives (id, workspace_id, scope, title)
      VALUES (${generateSnowflake()}, ${ws}, 'project', 'orphan')`));
    expect(msg).toMatch(/chk_okr_objectives_scope_shape/);
  });

  it("accepts company objective then project objective aligned to it", async () => {
    const { ws, projectId, goalId } = await seed();
    const companyId = generateSnowflake();
    await db.execute(sql`
      INSERT INTO strategy.okr_objectives (id, workspace_id, scope, goal_id, title)
      VALUES (${companyId}, ${ws}, 'company', ${goalId}, 'Company O')`);
    const projId = generateSnowflake();
    await db.execute(sql`
      INSERT INTO strategy.okr_objectives (id, workspace_id, scope, project_id, parent_objective_id, title)
      VALUES (${projId}, ${ws}, 'project', ${projectId}, ${companyId}, 'Project O')`);
    const rows = await db.execute(sql`SELECT parent_objective_id FROM strategy.okr_objectives WHERE id = ${projId}`);
    expect(String((rows.rows ?? rows)[0].parent_objective_id)).toBe(companyId.toString());
  });

  it("rejects a parent that is itself a project objective", async () => {
    const { ws, projectId } = await seed();
    const a = generateSnowflake();
    await db.execute(sql`
      INSERT INTO strategy.okr_objectives (id, workspace_id, project_id, title)
      VALUES (${a}, ${ws}, ${projectId}, 'A')`);
    const msg = await dbError(db.execute(sql`
      INSERT INTO strategy.okr_objectives (id, workspace_id, project_id, parent_objective_id, title)
      VALUES (${generateSnowflake()}, ${ws}, ${projectId}, ${a}, 'B')`));
    expect(msg).toMatch(/company-scope objective/);
  });

  it("rejects a goal from another workspace (composite FK)", async () => {
    const mine = await seed();
    const other = await seed();
    const msg = await dbError(db.execute(sql`
      INSERT INTO strategy.okr_objectives (id, workspace_id, scope, goal_id, title)
      VALUES (${generateSnowflake()}, ${mine.ws}, 'company', ${other.goalId}, 'cross-tenant')`));
    expect(msg).toMatch(/fk_okr_objective_goal_ws/);
  });
});
```

- [ ] **Step 2: Chạy để xác nhận thất bại**

Run: `cd services/company && encore test operations/tests/okr-unification-schema.test.ts`
Expected: FAIL (cột `scope` chưa tồn tại).

- [ ] **Step 3: Viết migration up**

```sql
-- 038_okr_unification_expand.up.sql
-- Dự án A0 (expand): một họ OKR duy nhất. Chỉ CỘNG THÊM; họ cũ bị xóa ở 039.

-- Khóa ghép để FK ghép (id, workspace_id) theo chuẩn tenancy.
ALTER TABLE strategy.goals       ADD CONSTRAINT uix_goals_id_workspace       UNIQUE (id, workspace_id);
ALTER TABLE strategy.okr_cycles  ADD CONSTRAINT uix_okr_cycles_id_workspace  UNIQUE (id, workspace_id);

ALTER TABLE strategy.okr_objectives
    ADD COLUMN scope               text   NOT NULL DEFAULT 'project',
    ADD COLUMN goal_id             bigint,
    ADD COLUMN cycle_id            bigint,
    ADD COLUMN parent_objective_id bigint;

ALTER TABLE strategy.okr_objectives ALTER COLUMN project_id DROP NOT NULL;

ALTER TABLE strategy.okr_objectives
    ADD CONSTRAINT chk_okr_objectives_scope CHECK (scope IN ('company', 'project')),
    ADD CONSTRAINT chk_okr_objectives_scope_shape CHECK (
        (scope = 'company' AND project_id IS NULL AND parent_objective_id IS NULL AND goal_id IS NOT NULL)
        OR (scope = 'project' AND project_id IS NOT NULL)
    ),
    ADD CONSTRAINT fk_okr_objective_goal_ws
        FOREIGN KEY (goal_id, workspace_id) REFERENCES strategy.goals (id, workspace_id) ON DELETE RESTRICT,
    ADD CONSTRAINT fk_okr_objective_cycle_ws
        FOREIGN KEY (cycle_id, workspace_id) REFERENCES strategy.okr_cycles (id, workspace_id)
        ON DELETE SET NULL (cycle_id),
    ADD CONSTRAINT fk_okr_objective_parent_ws
        FOREIGN KEY (parent_objective_id, workspace_id) REFERENCES strategy.okr_objectives (id, workspace_id)
        ON DELETE SET NULL (parent_objective_id);

CREATE INDEX IF NOT EXISTS idx_okr_objectives_goal   ON strategy.okr_objectives (workspace_id, goal_id)   WHERE goal_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_okr_objectives_cycle  ON strategy.okr_objectives (workspace_id, cycle_id)  WHERE cycle_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_okr_objectives_parent ON strategy.okr_objectives (parent_objective_id)     WHERE parent_objective_id IS NOT NULL;

-- Phần căn chỉnh cùng bảng. Phần so với projects.objective_id thêm ở 039.
CREATE OR REPLACE FUNCTION strategy.fn_okr_objective_alignment() RETURNS trigger AS $$
DECLARE
    parent_scope text;
BEGIN
    IF NEW.parent_objective_id IS NULL THEN
        RETURN NEW;
    END IF;
    SELECT scope INTO parent_scope
      FROM strategy.okr_objectives
     WHERE id = NEW.parent_objective_id AND workspace_id = NEW.workspace_id;
    IF parent_scope IS DISTINCT FROM 'company' THEN
        RAISE EXCEPTION 'parent_objective_id must reference a company-scope objective in the same workspace'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_okr_objective_alignment ON strategy.okr_objectives;
CREATE TRIGGER trg_okr_objective_alignment
    BEFORE INSERT OR UPDATE OF parent_objective_id, scope, workspace_id ON strategy.okr_objectives
    FOR EACH ROW EXECUTE FUNCTION strategy.fn_okr_objective_alignment();
```

```sql
-- 038_okr_unification_expand.down.sql
DROP TRIGGER IF EXISTS trg_okr_objective_alignment ON strategy.okr_objectives;
DROP FUNCTION IF EXISTS strategy.fn_okr_objective_alignment();
DROP INDEX IF EXISTS strategy.idx_okr_objectives_parent;
DROP INDEX IF EXISTS strategy.idx_okr_objectives_cycle;
DROP INDEX IF EXISTS strategy.idx_okr_objectives_goal;
ALTER TABLE strategy.okr_objectives
    DROP CONSTRAINT IF EXISTS fk_okr_objective_parent_ws,
    DROP CONSTRAINT IF EXISTS fk_okr_objective_cycle_ws,
    DROP CONSTRAINT IF EXISTS fk_okr_objective_goal_ws,
    DROP CONSTRAINT IF EXISTS chk_okr_objectives_scope_shape,
    DROP CONSTRAINT IF EXISTS chk_okr_objectives_scope;
DELETE FROM strategy.okr_objectives WHERE scope = 'company';
ALTER TABLE strategy.okr_objectives
    DROP COLUMN IF EXISTS parent_objective_id,
    DROP COLUMN IF EXISTS cycle_id,
    DROP COLUMN IF EXISTS goal_id,
    DROP COLUMN IF EXISTS scope;
ALTER TABLE strategy.okr_objectives ALTER COLUMN project_id SET NOT NULL;
ALTER TABLE strategy.okr_cycles DROP CONSTRAINT IF EXISTS uix_okr_cycles_id_workspace;
ALTER TABLE strategy.goals      DROP CONSTRAINT IF EXISTS uix_goals_id_workspace;
```

- [ ] **Step 4: Cập nhật Drizzle `okrObjectives`** (`operations.ts`)

Trong `okrObjectives` (dòng ~367-382): đổi `projectId` và thêm 4 cột.

```ts
  projectId: bigint("project_id", { mode: "bigint" }),
  scope: text("scope").default("project").notNull(), // 'company' | 'project'
  goalId: bigint("goal_id", { mode: "bigint" }),
  cycleId: bigint("cycle_id", { mode: "bigint" }),
  parentObjectiveId: bigint("parent_objective_id", { mode: "bigint" }),
```

(`projectId` bỏ `.notNull()`; các cột mới đặt ngay sau `projectId`.)

- [ ] **Step 5: Áp migration lên DB dev và chạy test**

Run: `make dev-migrate` (hoặc `make services-migrate-company`)
Run: `cd services/company && encore test operations/tests/okr-unification-schema.test.ts`
Expected: PASS 7 test.

- [ ] **Step 6: Typecheck sửa lỗi null của `projectId`**

Run: `cd services/company && npm run typecheck`
Expected: lỗi tại nơi dùng `okrObjectives.$inferSelect.projectId` như `okr.service.ts toObjective` (`row.projectId.toString()`), `okr-weekly-generator.service.ts:44` (`objective.projectId.toString()`), `project-operating-loop.service.ts:243 toObjective`. Sửa tạm bằng `row.projectId?.toString() ?? ""` ở `okr-weekly-generator.service.ts:44` (objective ở đây luôn có project) và `project-operating-loop.service.ts` (các truy vấn đã lọc `eq(okrObjectives.projectId, pId)`). `okr.service.ts toObjective` sẽ viết lại ở Task 2, nên chỉ cần biên dịch được: `projectId: row.projectId ? row.projectId.toString() : ""`.
Run lại `npm run typecheck`. Expected: không lỗi.

- [ ] **Step 7: Commit**

```bash
git add services/company/operations/migrations/038_okr_unification_expand.up.sql \
        services/company/operations/migrations/038_okr_unification_expand.down.sql \
        services/company/shared/db/schema/operations.ts \
        services/company/operations/services/okr.service.ts \
        services/company/operations/services/okr-weekly-generator.service.ts \
        services/company/operations/services/project-operating-loop.service.ts \
        services/company/operations/tests/okr-unification-schema.test.ts
git commit -m "feat(okr): thêm scope, goal, cycle, parent vào okr_objectives (migration 038)"
```

(Chạy trong thư mục `javis-saas`, đúng repo git của nó.)

---

### Task 2: `okr.service.ts` — tạo/đọc objective theo scope

**Files:**
- Modify: `services/company/operations/services/okr.service.ts` (`Objective`, `CreateObjectiveParams`, `toObjective`, `createObjectiveService`)
- Modify: `services/company/operations/handlers/okr.handler.ts` (export type nếu cần)
- Test: `services/company/operations/tests/okr.test.ts` (thêm describe mới)

**Interfaces:**
- Consumes: Task 1 cột `scope/goalId/cycleId/parentObjectiveId`.
- Produces:
  - `Objective` thêm: `scope: "company" | "project"`, `goalId: string | null`, `parentObjectiveId: string | null`, `projectId: string | null`, `cycleId: string | null`.
  - `CreateObjectiveParams` thêm: `scope?: "company" | "project"`, `goalId?: string`, `parentObjectiveId?: string`.
  - `createObjectiveService(params): Promise<Objective>` (chữ ký không đổi).

**Hành vi:**
- `scope='company'`: bắt buộc `goalId` (thuộc workspace), cấm `projectId`/`parentObjectiveId`.
- `scope='project'` (mặc định): cần `projectId` thuộc workspace; cấm `goalId`; `parentObjectiveId` (nếu có) phải là objective company cùng workspace.
- Thiếu `projectId` ở scope project: chỉ cho phép khi workspace có **đúng một** project (giữ tương thích test hiện có); nhiều project thì lỗi `invalidArgument`.
- `cycleId` được lưu (trước đây bị bỏ).

- [ ] **Step 1: Viết test thất bại** (thêm vào cuối `okr.test.ts`)

```ts
describe("createObjective scope & alignment (A0)", () => {
  async function makeGoal(workspaceId: string) {
    const { createGoalService } = await import("../services/goals.service");
    const { goalId } = await createGoalService({ workspaceId, title: "G", goalType: "strategic" });
    return goalId;
  }

  it("creates a company objective bound to a goal", async () => {
    const { workspace, authorization } = await makeCycle();
    const goalId = await makeGoal(workspace.id);
    const o = await createObjective({
      workspaceId: workspace.id, scope: "company", goalId, title: "Company O", authorization,
    });
    expect(o.scope).toBe("company");
    expect(o.goalId).toBe(goalId);
    expect(o.projectId).toBeNull();
  });

  it("rejects a company objective without goalId", async () => {
    const { workspace, authorization } = await makeCycle();
    await expect(
      createObjective({ workspaceId: workspace.id, scope: "company", title: "x", authorization }),
    ).rejects.toThrow(/goalId is required/);
  });

  it("rejects a company objective that sets projectId", async () => {
    const { workspace, authorization } = await makeCycle();
    const goalId = await makeGoal(workspace.id);
    await expect(
      createObjective({
        workspaceId: workspace.id, scope: "company", goalId, projectId: workspace.projectId, title: "x", authorization,
      }),
    ).rejects.toThrow(/cannot have projectId/);
  });

  it("creates a project objective aligned to a company objective and stores cycleId", async () => {
    const { workspace, cycle, authorization } = await makeCycle();
    const goalId = await makeGoal(workspace.id);
    const company = await createObjective({
      workspaceId: workspace.id, scope: "company", goalId, title: "C", authorization,
    });
    const o = await createObjective({
      workspaceId: workspace.id, projectId: workspace.projectId, cycleId: cycle.id,
      parentObjectiveId: company.id, title: "P", authorization,
    });
    expect(o.scope).toBe("project");
    expect(o.parentObjectiveId).toBe(company.id);
    expect(o.cycleId).toBe(cycle.id);
  });

  it("rejects goalId on a project objective", async () => {
    const { workspace, authorization } = await makeCycle();
    const goalId = await makeGoal(workspace.id);
    await expect(
      createObjective({
        workspaceId: workspace.id, projectId: workspace.projectId, goalId, title: "x", authorization,
      }),
    ).rejects.toThrow(/goalId is derived/);
  });

  it("rejects a parent that is not a company objective", async () => {
    const { workspace, authorization } = await makeCycle();
    const a = await createObjective({ workspaceId: workspace.id, projectId: workspace.projectId, title: "A", authorization });
    await expect(
      createObjective({
        workspaceId: workspace.id, projectId: workspace.projectId, parentObjectiveId: a.id, title: "B", authorization,
      }),
    ).rejects.toThrow(/company-scope objective/);
  });

  it("requires projectId when the workspace has more than one project", async () => {
    const { workspace, authorization } = await makeCycle();
    await createProject({
      workspaceId: workspace.id, title: "Second", authorization,
    } as never);
    await expect(
      createObjective({ workspaceId: workspace.id, title: "ambiguous", authorization }),
    ).rejects.toThrow(/projectId is required/);
  });
});
```

Kiểm tra chữ ký thật của `createProject` trong `operations/handlers/project.handler.ts` trước khi chạy; nếu khác `{workspaceId,title,authorization}`, sửa đối số cho khớp (cùng test dùng `createProject` ở đầu file import).

- [ ] **Step 2: Chạy để xác nhận thất bại**

Run: `cd services/company && encore test operations/tests/okr.test.ts -t "scope & alignment"`
Expected: FAIL (`scope` chưa có trong params/kết quả).

- [ ] **Step 3: Viết lại `Objective`, `CreateObjectiveParams`, `toObjective`**

```ts
export type ObjectiveScope = "company" | "project";

export interface Objective {
  id: string;
  workspaceId: string;
  scope: ObjectiveScope;
  projectId: string | null;
  goalId: string | null;
  parentObjectiveId: string | null;
  cycleId: string | null;
  title: string;
  why: string | null;
  ownerMemberId: string | null;
  status: string;
  publishedByMemberId?: string | null;
  publishedAt?: string | null;
  projectIds: string[];
  createdAt: string;
}

export interface CreateObjectiveParams {
  workspaceId: string;
  scope?: ObjectiveScope;
  projectId?: string;
  goalId?: string;
  parentObjectiveId?: string;
  cycleId?: string;
  title: string;
  why?: string;
  ownerMemberId?: string;
  authorization?: string;
}
```

```ts
function toObjective(row: typeof okrObjectives.$inferSelect): Objective {
  return {
    id: row.id.toString(),
    workspaceId: row.workspaceId.toString(),
    scope: row.scope as ObjectiveScope,
    projectId: row.projectId ? row.projectId.toString() : null,
    goalId: row.goalId ? row.goalId.toString() : null,
    parentObjectiveId: row.parentObjectiveId ? row.parentObjectiveId.toString() : null,
    cycleId: row.cycleId ? row.cycleId.toString() : null,
    title: row.title,
    why: row.why,
    ownerMemberId: row.ownerMemberId ? row.ownerMemberId.toString() : null,
    status: row.status,
    publishedByMemberId: row.publishedByMemberId ? row.publishedByMemberId.toString() : null,
    publishedAt: row.publishedAt ? row.publishedAt.toISOString() : null,
    projectIds: row.projectId ? [row.projectId.toString()] : [],
    createdAt: row.createdAt.toISOString(),
  };
}
```

Thêm `goals` vào destructure schema: `const { okrCycles, okrObjectives, keyResults, projects, goals } = schema;`

- [ ] **Step 4: Viết lại `createObjectiveService`**

```ts
export async function createObjectiveService(params: CreateObjectiveParams): Promise<Objective> {
  await requireWorkspaceAccess(params.authorization, params.workspaceId);
  await getWorkspaceRecord(params.workspaceId);

  const wsId = BigInt(params.workspaceId);
  const scope: ObjectiveScope = params.scope ?? "project";
  const cycleId = params.cycleId ? BigInt(params.cycleId) : null;

  if (cycleId) {
    const [cycle] = await db
      .select({ id: okrCycles.id })
      .from(okrCycles)
      .where(and(eq(okrCycles.id, cycleId), eq(okrCycles.workspaceId, wsId)))
      .limit(1);
    if (!cycle) {
      throw APIError.notFound(`OKR cycle ${params.cycleId} not found in workspace`);
    }
  }

  let projectId: bigint | null = null;
  let goalId: bigint | null = null;
  let parentObjectiveId: bigint | null = null;

  if (scope === "company") {
    if (!params.goalId) {
      throw APIError.invalidArgument("goalId is required for a company objective");
    }
    if (params.projectId || params.parentObjectiveId) {
      throw APIError.invalidArgument("a company objective cannot have projectId or parentObjectiveId");
    }
    goalId = BigInt(params.goalId);
    const [goal] = await db
      .select({ id: goals.id })
      .from(goals)
      .where(and(eq(goals.id, goalId), eq(goals.workspaceId, wsId)))
      .limit(1);
    if (!goal) throw APIError.notFound(`goal ${params.goalId} not found in workspace`);
  } else {
    if (params.goalId) {
      throw APIError.invalidArgument(
        "goalId is derived from the parent company objective; do not set it on a project objective",
      );
    }
    if (params.projectId) {
      projectId = BigInt(params.projectId);
      const [project] = await db
        .select({ id: projects.id })
        .from(projects)
        .where(and(eq(projects.id, projectId), eq(projects.workspaceId, wsId), isNull(projects.deletedAt)))
        .limit(1);
      if (!project) throw APIError.notFound(`project ${params.projectId} not found in workspace`);
    } else {
      // Chỉ suy ra project khi workspace có đúng một project; nhiều project thì phải chỉ rõ.
      const candidates = await db
        .select({ id: projects.id })
        .from(projects)
        .where(and(eq(projects.workspaceId, wsId), isNull(projects.deletedAt)))
        .limit(2);
      if (candidates.length !== 1) {
        throw APIError.invalidArgument("projectId is required when the workspace has more than one project");
      }
      projectId = candidates[0]!.id;
    }
    if (params.parentObjectiveId) {
      parentObjectiveId = BigInt(params.parentObjectiveId);
      const [parent] = await db
        .select({ scope: okrObjectives.scope })
        .from(okrObjectives)
        .where(
          and(
            eq(okrObjectives.id, parentObjectiveId),
            eq(okrObjectives.workspaceId, wsId),
            isNull(okrObjectives.deletedAt),
          ),
        )
        .limit(1);
      if (!parent || parent.scope !== "company") {
        throw APIError.invalidArgument(
          "parentObjectiveId must reference a company-scope objective in the same workspace",
        );
      }
    }
  }

  const [row] = await db
    .insert(okrObjectives)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      scope,
      projectId,
      goalId,
      cycleId,
      parentObjectiveId,
      title: params.title,
      why: params.why || null,
      ownerMemberId: params.ownerMemberId ? BigInt(params.ownerMemberId) : null,
    })
    .returning();

  if (!row) throw APIError.internal("failed to create objective");
  return toObjective(row);
}
```

- [ ] **Step 5: Chạy test**

Run: `cd services/company && encore test operations/tests/okr.test.ts`
Expected: toàn bộ PASS (kể cả test cũ không truyền `projectId`, vì workspace chỉ có một project).

- [ ] **Step 6: Chạy các test OKR khác và typecheck**

Run: `cd services/company && npm run typecheck && encore test operations/tests/okr-weekly-generator.service.test.ts operations/tests/mvp-okr-twelve-week.test.ts operations/strategy/tests/execution-planning-chain.test.ts shared/tests/golden-path.e2e.test.ts`
Expected: PASS. Nếu có test dùng `objective.projectId` như string bắt buộc, sửa bằng `objective.projectId!`.

- [ ] **Step 7: Commit**

```bash
git add services/company/operations/services/okr.service.ts services/company/operations/handlers/okr.handler.ts services/company/operations/tests/okr.test.ts
git commit -m "feat(okr): objective theo scope company/project, lưu cycleId, bỏ chọn project ngẫu nhiên"
```

---

### Task 3: Goal tree và complete đọc họ OKR; bỏ API `/operations/cosa/*`

**Files:**
- Create: `services/company/operations/services/goal-okr-stats.service.ts`
- Modify: `services/company/operations/services/goals.service.ts` (xóa `createObjectiveService`, `addKeyResultService`, `updateKeyResultValueService`, `assertObjectiveInWorkspace`; viết lại `getGoalTreeService` stats và `completeGoalService`)
- Modify: `services/company/operations/handlers/goals.handler.ts` (xóa 3 endpoint `/operations/cosa/*` và các type liên quan)
- Modify: `tests/quality/test_route_auth_allowlist.py` nếu có tham chiếu `cosa/objectives|cosa/key-results`
- Test: `services/company/operations/tests/goal-okr-stats.test.ts` (mới)

**Interfaces:**
- Consumes: Task 2 `createObjectiveService`, `addKeyResultService`, `checkinService` từ `okr.service.ts`.
- Produces:
  - `loadObjectiveGoalMap(wsId: bigint): Promise<Map<string, string>>` — objectiveId → goalId hiệu lực.
  - `loadGoalStats(wsId: bigint): Promise<Map<string, { objectiveCount: number; krTotal: number; krAchieved: number }>>`.
  - `GoalTreeNode` giữ nguyên hình dạng (Flutter không đổi).

- [ ] **Step 1: Viết test thất bại**

```ts
// services/company/operations/tests/goal-okr-stats.test.ts
import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createGoalService, getGoalTreeService, completeGoalService } from "../services/goals.service";
import { createObjectiveService, addKeyResultService, checkinService } from "../services/okr.service";

async function setup() {
  const user = await createTestSession({
    email: `goal-stats-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName: "Goal Stats",
    role: "founder",
  });
  const authorization = `Bearer ${user.accessToken}`;
  const { goalId } = await createGoalService({
    workspaceId: user.workspaceId, title: "Goal", goalType: "strategic",
  });
  const company = await createObjectiveService({
    workspaceId: user.workspaceId, scope: "company", goalId, title: "Company O", authorization,
  });
  const project = await createObjectiveService({
    workspaceId: user.workspaceId, projectId: user.projectId,
    parentObjectiveId: company.id, title: "Project O", authorization,
  });
  return { user, authorization, goalId, company, project };
}

describe("goal tree stats from unified OKR", () => {
  it("counts company and aligned project objectives and KRs under the goal", async () => {
    const { user, authorization, goalId, company, project } = await setup();
    await addKeyResultService({ objectiveId: company.id, title: "KR company", targetValue: 10, authorization });
    await addKeyResultService({ objectiveId: project.id, title: "KR project", targetValue: 10, authorization });

    const { tree } = await getGoalTreeService(user.workspaceId);
    const node = tree.find((n) => n.id === goalId)!;
    expect(node.objectiveCount).toBe(2);
    expect(node.krTotal).toBe(2);
    expect(node.krAchieved).toBe(0);
  });

  it("marks a decrease KR achieved by progress, not by current >= target", async () => {
    const { user, authorization, goalId, project } = await setup();
    const kr = await addKeyResultService({
      objectiveId: project.id, title: "Churn", targetValue: 5, baselineValue: 10,
      scoringType: "LINEAR_DECREASE", authorization,
    });
    await checkinService(kr.id, 5, authorization);
    const { tree } = await getGoalTreeService(user.workspaceId);
    expect(tree.find((n) => n.id === goalId)!.krAchieved).toBe(1);
  });

  it("does not count a project objective without a parent under any goal", async () => {
    const { user, authorization, goalId } = await setup();
    await createObjectiveService({
      workspaceId: user.workspaceId, projectId: user.projectId, title: "Unaligned", authorization,
    });
    const { tree } = await getGoalTreeService(user.workspaceId);
    expect(tree.find((n) => n.id === goalId)!.objectiveCount).toBe(2);
  });

  it("completeGoal requires force while objectives are open, then closes objectives and KRs", async () => {
    const { user, authorization, goalId, project } = await setup();
    const kr = await addKeyResultService({ objectiveId: project.id, title: "KR", targetValue: 10, authorization });
    await expect(
      completeGoalService({ workspaceId: user.workspaceId, goalId }),
    ).rejects.toThrow(/objective/);
    const res = await completeGoalService({
      workspaceId: user.workspaceId, goalId, forceCompleteActiveObjectives: true,
    });
    expect(res.completedObjectivesCount).toBe(2);
    const { tree } = await getGoalTreeService(user.workspaceId);
    expect(tree.find((n) => n.id === goalId)!.status).toBe("completed");
    expect(kr.id).toBeTruthy();
  });
});
```

- [ ] **Step 2: Chạy để xác nhận thất bại**

Run: `cd services/company && encore test operations/tests/goal-okr-stats.test.ts`
Expected: FAIL (`objectiveCount` 0 vì tree vẫn đọc `strategy.objectives`).

- [ ] **Step 3: Tạo `goal-okr-stats.service.ts`**

```ts
import { and, eq, isNull } from "drizzle-orm";
import { db, schema } from "../models/db";
import { computeKeyResultProgress, KrScoringType } from "./okr-scoring.service";

const { okrObjectives, keyResults, projects } = schema;

export interface GoalStats {
  objectiveCount: number;
  krTotal: number;
  krAchieved: number;
}

/**
 * objectiveId → goalId hiệu lực.
 * - Objective công ty: chính `goal_id`.
 * - Objective dự án: goal của objective công ty cha; cha lấy từ `parent_objective_id`,
 *   nếu NULL thì từ `projects.objective_id` (thừa kế). Không có cha thì không thuộc goal nào.
 */
export async function loadObjectiveGoalMap(wsId: bigint): Promise<Map<string, string>> {
  const rows = await db
    .select({
      id: okrObjectives.id,
      scope: okrObjectives.scope,
      goalId: okrObjectives.goalId,
      parentObjectiveId: okrObjectives.parentObjectiveId,
      projectObjectiveId: projects.objectiveId,
    })
    .from(okrObjectives)
    .leftJoin(
      projects,
      and(eq(projects.id, okrObjectives.projectId), eq(projects.workspaceId, okrObjectives.workspaceId)),
    )
    .where(and(eq(okrObjectives.workspaceId, wsId), isNull(okrObjectives.deletedAt)));

  const companyGoal = new Map<string, string>();
  for (const r of rows) {
    if (r.scope === "company" && r.goalId) companyGoal.set(r.id.toString(), r.goalId.toString());
  }

  const result = new Map<string, string>();
  for (const r of rows) {
    const id = r.id.toString();
    if (r.scope === "company") {
      const g = companyGoal.get(id);
      if (g) result.set(id, g);
      continue;
    }
    const parent = r.parentObjectiveId ?? r.projectObjectiveId;
    const g = parent ? companyGoal.get(parent.toString()) : undefined;
    if (g) result.set(id, g);
  }
  return result;
}

export async function loadGoalStats(wsId: bigint): Promise<Map<string, GoalStats>> {
  const goalOf = await loadObjectiveGoalMap(wsId);
  const stats = new Map<string, GoalStats>();
  const bucket = (goalId: string): GoalStats => {
    let s = stats.get(goalId);
    if (!s) {
      s = { objectiveCount: 0, krTotal: 0, krAchieved: 0 };
      stats.set(goalId, s);
    }
    return s;
  };

  for (const goalId of goalOf.values()) bucket(goalId).objectiveCount += 1;

  const krs = await db
    .select()
    .from(keyResults)
    .where(and(eq(keyResults.workspaceId, wsId), isNull(keyResults.deletedAt)));

  for (const kr of krs) {
    const goalId = goalOf.get(kr.objectiveId.toString());
    if (!goalId) continue;
    const s = bucket(goalId);
    s.krTotal += 1;
    const progress = computeKeyResultProgress({
      baseline: kr.baselineValue,
      target: kr.targetValue,
      current: kr.currentValue,
      scoringType: kr.scoringType as KrScoringType,
    });
    if (progress !== null && progress >= 1) s.krAchieved += 1;
  }
  return stats;
}
```

- [ ] **Step 4: Sửa `goals.service.ts`**

1. Dòng 7: `const { goals, okrObjectives, keyResults, onboardSnapshots } = schema;` và thêm import `import { computeKeyResultProgress, KrScoringType } from "./okr-scoring.service";` và `import { loadGoalStats, loadObjectiveGoalMap } from "./goal-okr-stats.service";`.
2. Xóa hàm `assertObjectiveInWorkspace` (dòng 46-55), `createObjectiveService` (350-378), `addKeyResultService` (380-406), `updateKeyResultValueService` (408-473).
3. Trong `getGoalTreeService`, thay khối truy vấn `statsRows`/`statsMap` (dòng 148-168) bằng:

```ts
  const statsMap = await loadGoalStats(wsId);
```

và dòng `const st = statsMap.get(idStr) || {...}` giữ nguyên.
4. Viết lại `completeGoalService` thân hàm sau `assertGoalInWorkspace`:

```ts
  const goalOf = await loadObjectiveGoalMap(wsId);
  const objectiveIds = [...goalOf.entries()]
    .filter(([, g]) => g === gId.toString())
    .map(([id]) => BigInt(id));

  const openObjectives = objectiveIds.length
    ? await db
        .select({ id: okrObjectives.id })
        .from(okrObjectives)
        .where(
          and(
            eq(okrObjectives.workspaceId, wsId),
            inArray(okrObjectives.id, objectiveIds),
            notInArray(okrObjectives.status, ["completed", "abandoned"]),
          ),
        )
    : [];

  if (openObjectives.length > 0 && !params.forceCompleteActiveObjectives) {
    throw APIError.failedPrecondition(
      `Không thể hoàn thành Goal vì còn ${openObjectives.length} objective đang hoạt động. Hãy hoàn thành các objective trước hoặc chọn hoàn thành bắt buộc.`,
    );
  }

  const now = new Date();
  await db
    .update(goals)
    .set({ status: "completed", completedAt: now })
    .where(and(eq(goals.id, gId), eq(goals.workspaceId, wsId)));

  if (openObjectives.length > 0) {
    await db
      .update(okrObjectives)
      .set({ status: "completed", updatedAt: now })
      .where(
        and(
          eq(okrObjectives.workspaceId, wsId),
          inArray(okrObjectives.id, openObjectives.map((o) => o.id)),
        ),
      );
  }

  if (objectiveIds.length > 0) {
    const krRows = await db
      .select()
      .from(keyResults)
      .where(
        and(
          eq(keyResults.workspaceId, wsId),
          inArray(keyResults.objectiveId, objectiveIds),
          isNull(keyResults.deletedAt),
          notInArray(keyResults.status, ["achieved", "missed", "archived"]),
        ),
      );
    for (const kr of krRows) {
      const progress = computeKeyResultProgress({
        baseline: kr.baselineValue,
        target: kr.targetValue,
        current: kr.currentValue,
        scoringType: kr.scoringType as KrScoringType,
      });
      await db
        .update(keyResults)
        .set({ status: progress !== null && progress >= 1 ? "achieved" : "missed", updatedAt: now })
        .where(and(eq(keyResults.id, kr.id), eq(keyResults.workspaceId, wsId)));
    }
  }

  return {
    success: true,
    completedObjectivesCount: openObjectives.length,
    reviewAmbitionPrompt:
      "Mục tiêu chiến lược đã hoàn thành. Hãy kiểm tra lại tham vọng (Goals & Ambition) để chuẩn bị cho chu kỳ tiếp theo.",
  };
```

Cập nhật import drizzle đầu file: `import { eq, and, sql, desc, isNull, inArray, notInArray } from "drizzle-orm";` (bỏ `desc`, `sql` nếu không còn dùng; `getGoalsNeedingReviewService` vẫn dùng `sql`).

- [ ] **Step 5: Sửa `goals.handler.ts`**

Xóa import `createObjectiveService`, `addKeyResultService`, `updateKeyResultValueService`; xóa các type `CreateCosaObjectiveParams`, `AddCosaKeyResultParams`, `CheckinKeyResultParams`, `*Response` tương ứng và ba endpoint `createCosaObjective`, `addCosaKeyResult`, `checkinCosaKeyResult` (đoạn dòng 190-225).

- [ ] **Step 6: Typecheck và chạy test**

Run: `cd services/company && npm run typecheck && encore test operations/tests/goal-okr-stats.test.ts operations/tests/startup-os.test.ts operations/tests/startup-os-auth.test.ts`
Expected: `startup-os-auth.test.ts` có thể tham chiếu endpoint cosa bị xóa → xóa/đổi test đó sang endpoint `/operations/objectives`; nếu `discovery-project.service.ts` lỗi import `assertObjectiveInWorkspace`/`createObjectiveService`, **để Task 4 sửa** (tạm thời giữ biên dịch bằng cách chạy Task 4 ngay sau; nếu typecheck đỏ chỉ vì file đó, tiếp tục sang Task 4 trước khi commit).

- [ ] **Step 7: Cập nhật allowlist route**

Run: `grep -n "cosa/objectives\|cosa/key-results" tests/quality/test_route_auth_allowlist.py`
Nếu có, xóa các dòng đó; chạy `make route-auth-allowlist-check`.

- [ ] **Step 8: Commit** (sau khi Task 4 làm typecheck xanh nếu bị chặn ở Step 6)

```bash
git add services/company/operations/services/goal-okr-stats.service.ts services/company/operations/services/goals.service.ts services/company/operations/handlers/goals.handler.ts services/company/operations/tests tests/quality/test_route_auth_allowlist.py
git commit -m "feat(goals): tree và complete đọc họ OKR hợp nhất, bỏ API /operations/cosa"
```

---

### Task 4: Migration 039 (contract) và discovery triage

**Files:**
- Create: `services/company/operations/migrations/039_okr_unification_contract.up.sql` và `.down.sql`
- Modify: `services/company/shared/db/schema/goals.ts` (bỏ `objectives`, `cosaKeyResults`)
- Modify: `services/company/operations/services/discovery-project.service.ts`
- Modify: `services/company/scripts/preflight-workspace-tenancy.sql` (nếu liệt kê bảng cũ)
- Test: `services/company/operations/tests/discovery-triage.test.ts` (mới)

**Interfaces:**
- Consumes: Task 2 `Objective` scope; Task 3 đã bỏ code dùng họ cũ.
- Produces: `projects.objective_id` → FK ghép tới `okr_objectives(id, workspace_id)`; trigger `trg_project_objective_alignment`; `triageProjectService` hành vi mới (xem Step 4).

- [ ] **Step 1: Xác nhận không còn tham chiếu họ cũ**

Run: `cd services/company && grep -rnE "cosaKeyResults|\bobjectives\b.*schema|strategy\.objectives|cosa_key_results|v_goal_tree" --include='*.ts' --include='*.sql' . | grep -vE "node_modules|encore.gen|migrations/(001|028)"`
Expected: chỉ còn `discovery-project.service.ts` (sẽ sửa ở Step 4), `goals.ts` (Step 5), có thể `scripts/preflight-workspace-tenancy.sql`. `v_goal_tree` không được dùng trong mã (đã kiểm tra: chỉ có trong migration 028).

- [ ] **Step 2: Viết test thất bại**

```ts
// services/company/operations/tests/discovery-triage.test.ts
import { describe, expect, it } from "vitest";
import { sql } from "drizzle-orm";
import { db } from "../models/db";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createGoalService } from "../services/goals.service";
import { createObjectiveService } from "../services/okr.service";
import { triageProjectService } from "../services/discovery-project.service";

async function setup() {
  const user = await createTestSession({
    email: `triage-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName: "Triage",
    role: "founder",
  });
  const authorization = `Bearer ${user.accessToken}`;
  const { goalId } = await createGoalService({ workspaceId: user.workspaceId, title: "G", goalType: "strategic" });
  const company = await createObjectiveService({
    workspaceId: user.workspaceId, scope: "company", goalId, title: "C", authorization,
  });
  return { user, authorization, goalId, company };
}

async function projectObjectiveId(projectId: string) {
  const r = await db.execute(sql`SELECT objective_id, link_status FROM strategy.projects WHERE id = ${BigInt(projectId)}`);
  return (r.rows ?? r)[0] as { objective_id: string | null; link_status: string };
}

describe("project triage on unified OKR", () => {
  it("link attaches a project to a company objective", async () => {
    const { user, company } = await setup();
    await triageProjectService({
      workspaceId: user.workspaceId, projectId: user.projectId, action: "link", targetObjectiveId: company.id,
    });
    const row = await projectObjectiveId(user.projectId);
    expect(String(row.objective_id)).toBe(company.id);
    expect(row.link_status).toBe("linked");
  });

  it("link rejects a project-scope objective", async () => {
    const { user, authorization } = await setup();
    const projObj = await createObjectiveService({
      workspaceId: user.workspaceId, projectId: user.projectId, title: "P", authorization,
    });
    await expect(
      triageProjectService({
        workspaceId: user.workspaceId, projectId: user.projectId, action: "link", targetObjectiveId: projObj.id,
      }),
    ).rejects.toThrow(/company/);
  });

  it("link rejects when the project already has an objective aligned to a different parent", async () => {
    const { user, authorization, goalId, company } = await setup();
    const other = await createObjectiveService({
      workspaceId: user.workspaceId, scope: "company", goalId, title: "Other", authorization,
    });
    await createObjectiveService({
      workspaceId: user.workspaceId, projectId: user.projectId, parentObjectiveId: other.id, title: "P", authorization,
    });
    await expect(
      triageProjectService({
        workspaceId: user.workspaceId, projectId: user.projectId, action: "link", targetObjectiveId: company.id,
      }),
    ).rejects.toThrow(/parent/);
  });

  it("roll_to_new_goal creates a company objective under the new goal and links the project", async () => {
    const { user } = await setup();
    const { goalId: newGoal } = await createGoalService({
      workspaceId: user.workspaceId, title: "Next", goalType: "tactical",
    });
    await triageProjectService({
      workspaceId: user.workspaceId, projectId: user.projectId, action: "roll_to_new_goal",
      newGoalId: newGoal, newObjectiveTitle: "Rolled",
    });
    const row = await projectObjectiveId(user.projectId);
    expect(row.objective_id).not.toBeNull();
    expect(row.link_status).toBe("linked");
  });

  it("DB trigger blocks pointing projects.objective_id at a project-scope objective", async () => {
    const { user, authorization } = await setup();
    const projObj = await createObjectiveService({
      workspaceId: user.workspaceId, projectId: user.projectId, title: "P", authorization,
    });
    let message = "";
    try {
      await db.execute(sql`UPDATE strategy.projects SET objective_id = ${BigInt(projObj.id)} WHERE id = ${BigInt(user.projectId)}`);
    } catch (e) {
      const err = e as { message?: string; cause?: { message?: string } };
      message = `${err.message ?? ""} ${err.cause?.message ?? ""}`;
    }
    expect(message).toMatch(/company-scope objective/);
  });
});
```

Run: `cd services/company && encore test operations/tests/discovery-triage.test.ts`
Expected: FAIL.

- [ ] **Step 3: Viết migration 039**

```sql
-- 039_okr_unification_contract.up.sql
-- Dự án A0 (contract). Dữ liệu họ cũ chỉ là dữ liệu thử (đã xác nhận 2026-10-05).
-- KHÔNG dùng TRUNCATE ... CASCADE: strategy.projects có FK vào strategy.objectives.

-- 1. Gỡ liên kết cũ: project phải được người dùng link lại vào objective công ty.
UPDATE strategy.projects
   SET objective_id = NULL,
       link_status  = 'pending_review'
 WHERE objective_id IS NOT NULL;

ALTER TABLE strategy.projects DROP CONSTRAINT IF EXISTS fk_projects_objective;

-- 2. Xóa họ cũ và view phụ thuộc.
DROP VIEW IF EXISTS strategy.v_goal_tree;
DROP TABLE IF EXISTS strategy.cosa_key_results;
DROP TABLE IF EXISTS strategy.objectives;

-- 3. FK mới: project phục vụ một objective cấp công ty.
ALTER TABLE strategy.projects
    ADD CONSTRAINT fk_projects_objective
    FOREIGN KEY (objective_id, workspace_id) REFERENCES strategy.okr_objectives (id, workspace_id)
    ON DELETE SET NULL (objective_id);

-- 4. Căn chỉnh liên bảng.
CREATE OR REPLACE FUNCTION strategy.fn_okr_objective_alignment() RETURNS trigger AS $$
DECLARE
    parent_scope text;
    project_objective bigint;
BEGIN
    IF NEW.parent_objective_id IS NOT NULL THEN
        SELECT scope INTO parent_scope
          FROM strategy.okr_objectives
         WHERE id = NEW.parent_objective_id AND workspace_id = NEW.workspace_id;
        IF parent_scope IS DISTINCT FROM 'company' THEN
            RAISE EXCEPTION 'parent_objective_id must reference a company-scope objective in the same workspace'
                USING ERRCODE = '23514';
        END IF;

        IF NEW.scope = 'project' AND NEW.project_id IS NOT NULL THEN
            SELECT objective_id INTO project_objective
              FROM strategy.projects
             WHERE id = NEW.project_id AND workspace_id = NEW.workspace_id;
            IF project_objective IS NOT NULL AND project_objective <> NEW.parent_objective_id THEN
                RAISE EXCEPTION 'parent_objective_id must equal the project objective_id'
                    USING ERRCODE = '23514';
            END IF;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION strategy.fn_project_objective_alignment() RETURNS trigger AS $$
DECLARE
    obj_scope text;
BEGIN
    IF NEW.objective_id IS NULL THEN
        RETURN NEW;
    END IF;
    SELECT scope INTO obj_scope
      FROM strategy.okr_objectives
     WHERE id = NEW.objective_id AND workspace_id = NEW.workspace_id;
    IF obj_scope IS DISTINCT FROM 'company' THEN
        RAISE EXCEPTION 'projects.objective_id must reference a company-scope objective'
            USING ERRCODE = '23514';
    END IF;
    IF EXISTS (
        SELECT 1 FROM strategy.okr_objectives o
         WHERE o.project_id = NEW.id
           AND o.workspace_id = NEW.workspace_id
           AND o.parent_objective_id IS NOT NULL
           AND o.parent_objective_id <> NEW.objective_id
    ) THEN
        RAISE EXCEPTION 'project has objectives aligned to a different parent objective'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_project_objective_alignment ON strategy.projects;
CREATE TRIGGER trg_project_objective_alignment
    BEFORE INSERT OR UPDATE OF objective_id ON strategy.projects
    FOR EACH ROW EXECUTE FUNCTION strategy.fn_project_objective_alignment();
```

```sql
-- 039_okr_unification_contract.down.sql
-- Không khôi phục dữ liệu họ cũ (đã bị xóa). Chỉ dựng lại cấu trúc để down không hỏng chuỗi migration.
DROP TRIGGER IF EXISTS trg_project_objective_alignment ON strategy.projects;
DROP FUNCTION IF EXISTS strategy.fn_project_objective_alignment();
ALTER TABLE strategy.projects DROP CONSTRAINT IF EXISTS fk_projects_objective;
UPDATE strategy.projects SET objective_id = NULL WHERE objective_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS strategy.objectives (
    id BIGINT PRIMARY KEY,
    goal_id BIGINT NOT NULL REFERENCES strategy.goals(id) ON DELETE CASCADE,
    workspace_id BIGINT NOT NULL REFERENCES core.workspaces(id) ON DELETE CASCADE,
    title TEXT NOT NULL, description TEXT, owner_user_id BIGINT,
    weight NUMERIC(4,2) DEFAULT 1.0, display_order INT DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','completed','abandoned')),
    progress_pct NUMERIC(5,2) DEFAULT 0, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS strategy.cosa_key_results (
    id BIGINT PRIMARY KEY,
    objective_id BIGINT NOT NULL REFERENCES strategy.objectives(id) ON DELETE CASCADE,
    metric_name TEXT NOT NULL, baseline NUMERIC, target NUMERIC NOT NULL,
    current_value NUMERIC DEFAULT 0, unit TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active','achieved','missed','archived')),
    display_order INT DEFAULT 0
);
ALTER TABLE strategy.projects
    ADD CONSTRAINT fk_projects_objective FOREIGN KEY (objective_id) REFERENCES strategy.objectives(id) ON DELETE SET NULL;

-- Trả hàm căn chỉnh objective về phiên bản 038 (chỉ kiểm tra cùng bảng).
CREATE OR REPLACE FUNCTION strategy.fn_okr_objective_alignment() RETURNS trigger AS $$
DECLARE parent_scope text;
BEGIN
    IF NEW.parent_objective_id IS NULL THEN RETURN NEW; END IF;
    SELECT scope INTO parent_scope FROM strategy.okr_objectives
     WHERE id = NEW.parent_objective_id AND workspace_id = NEW.workspace_id;
    IF parent_scope IS DISTINCT FROM 'company' THEN
        RAISE EXCEPTION 'parent_objective_id must reference a company-scope objective in the same workspace'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

- [ ] **Step 4: Viết lại `discovery-project.service.ts`**

Thay import/destructure và các nhánh `link`, `roll_to_new_goal`:

```ts
import { APIError } from "encore.dev/api";
import { eq, and, isNull, ne, isNotNull } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";

const { projects, okrObjectives, goals } = schema;
```

Hàm trợ giúp (đặt trên `triageProjectService`):

```ts
async function assertCompanyObjective(wsId: bigint, objectiveId: bigint): Promise<void> {
  const [row] = await db
    .select({ scope: okrObjectives.scope })
    .from(okrObjectives)
    .where(
      and(
        eq(okrObjectives.id, objectiveId),
        eq(okrObjectives.workspaceId, wsId),
        isNull(okrObjectives.deletedAt),
      ),
    )
    .limit(1);
  if (!row) throw APIError.notFound("Không tìm thấy Objective trong workspace này.");
  if (row.scope !== "company") {
    throw APIError.invalidArgument("Dự án chỉ có thể liên kết với Objective cấp công ty (company).");
  }
}

async function assertNoConflictingChildren(wsId: bigint, projectId: bigint, parentId: bigint): Promise<void> {
  const conflicts = await db
    .select({ id: okrObjectives.id })
    .from(okrObjectives)
    .where(
      and(
        eq(okrObjectives.workspaceId, wsId),
        eq(okrObjectives.projectId, projectId),
        isNotNull(okrObjectives.parentObjectiveId),
        ne(okrObjectives.parentObjectiveId, parentId),
      ),
    )
    .limit(1);
  if (conflicts.length > 0) {
    throw APIError.failedPrecondition(
      "Dự án đang có objective căn chỉnh với parent objective khác; hãy đổi parent trước khi liên kết.",
    );
  }
}
```

Nhánh `link`:

```ts
      const objId = BigInt(params.targetObjectiveId);
      await assertCompanyObjective(wsId, objId);
      await assertNoConflictingChildren(wsId, pId, objId);
      await db.update(projects).set({ objectiveId: objId, linkStatus: "linked" }).where(eq(projects.id, pId));
```

Nhánh `roll_to_new_goal`:

```ts
      const newGoalId = BigInt(params.newGoalId);
      const [goal] = await db
        .select({ id: goals.id })
        .from(goals)
        .where(and(eq(goals.id, newGoalId), eq(goals.workspaceId, wsId)))
        .limit(1);
      if (!goal) throw APIError.notFound("Không tìm thấy Goal trong workspace này.");

      const objectiveId = generateSnowflake();
      await db.insert(okrObjectives).values({
        id: objectiveId,
        workspaceId: wsId,
        scope: "company",
        goalId: newGoalId,
        title: params.newObjectiveTitle,
      });
      await assertNoConflictingChildren(wsId, pId, objectiveId);
      await db.update(projects).set({ objectiveId, linkStatus: "linked" }).where(eq(projects.id, pId));
```

Giữ nguyên đầu hàm (`wsId`, `pId`, lấy `project`) như hiện có; kiểm tra tên biến trong file và bỏ import `objectives`.

- [ ] **Step 5: Sửa `goals.ts`**

Xóa toàn bộ khối `objectives` (dòng 39-63) và `cosaKeyResults` (dòng 65-82) cùng các import chỉ dùng cho chúng (`integer`, `numeric` nếu không còn dùng — `goals` vẫn dùng `numeric` cho `durationWeeks`). Giữ `goals`.

- [ ] **Step 6: Cập nhật preflight tenancy**

Run: `grep -n "objectives\|cosa_key" services/company/scripts/preflight-workspace-tenancy.sql`
Nếu có `strategy.objectives`/`cosa_key_results`, xóa dòng tương ứng; thêm dòng cho cột mới:
`UNION ALL SELECT 'okr_objectives.goal_id_cross_tenant', count(*) FROM strategy.okr_objectives o JOIN strategy.goals g ON g.id = o.goal_id WHERE g.workspace_id <> o.workspace_id`

- [ ] **Step 7: Áp migration, chạy gate DB và test**

Run:
```bash
make dev-migrate
make schema-fingerprint-write
make tenancy-check migration-check
cd services/company && npm run typecheck && encore test operations/tests/discovery-triage.test.ts operations/tests/goal-okr-stats.test.ts operations/tests/okr.test.ts operations/tests/okr-unification-schema.test.ts
```
Expected: PASS. `fk_projects_objective` composite có thể làm test cũ INSERT `strategy.projects ... objective_id` thất bại; sửa test đó để không đặt `objective_id`.

- [ ] **Step 8: Commit**

```bash
git add services/company/operations/migrations/039_okr_unification_contract.up.sql services/company/operations/migrations/039_okr_unification_contract.down.sql services/company/shared/db/schema/goals.ts services/company/operations/services/discovery-project.service.ts services/company/operations/tests/discovery-triage.test.ts services/company/scripts/preflight-workspace-tenancy.sql
git commit -m "feat(okr): migration 039 xóa họ OKR cũ, project liên kết objective công ty"
```

(Thêm file fingerprint do `make schema-fingerprint-write` sinh ra vào `git add`.)

---

### Task 5: Capability agent trả thêm scope và goal

**Files:**
- Modify: `apps/cosa/capabilities/okr_write.py` (`create_okr_objective_list_handler`, dòng 172-182)
- Test: `tests/apps/cosa/test_okr_capabilities.py`

**Interfaces:**
- Consumes: `GET /operations/objectives` trả thêm `scope`, `goalId`, `parentObjectiveId`.
- Produces: mỗi objective trong `okr.objective.list` có `scope`, `goalId`, `parentObjectiveId`.

- [ ] **Step 1: Sửa test hiện có để thất bại** (`test_objective_list_nests_key_results_with_labels`)

Đổi dữ liệu objective đầu vào thành `{"id": "o1", "title": "Tăng trưởng", "status": "published", "projectId": "p1", "scope": "project", "goalId": None, "parentObjectiveId": "c1"}` và thêm assert:

```python
    assert obj["scope"] == "project"
    assert obj["parentObjectiveId"] == "c1"
    assert "goalId" in obj
```

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/test_okr_capabilities.py -q`
Expected: FAIL (KeyError `scope`).

- [ ] **Step 2: Sửa handler**

```python
        return {
            "objectives": [
                {
                    "id": obj.get("id"),
                    "title": obj.get("title"),
                    "why": obj.get("why"),
                    "scope": obj.get("scope"),
                    "projectId": obj.get("projectId"),
                    "goalId": obj.get("goalId"),
                    "parentObjectiveId": obj.get("parentObjectiveId"),
                    "statusLabel": _status_label(obj.get("status"), locale),
                    "keyResults": by_objective.get(str(obj.get("id")), []),
                }
                for obj in objectives
            ]
        }
```

Cập nhật mô tả `OKR_OBJECTIVE_LIST_SPEC.description` thêm cụm "scope (company/project) and the goal/parent it is aligned to". Mô tả nằm trong `CapabilitySpec`, **không** thuộc AgentSpec hash; chạy test pin để chắc.

- [ ] **Step 3: Chạy test**

Run:
```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/test_okr_capabilities.py tests/contracts/test_company_agent_spec_pins.py tests/apps/cosa/test_access_matrix_parity.py -q
```
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add apps/cosa/capabilities/okr_write.py tests/apps/cosa/test_okr_capabilities.py
git commit -m "feat(agent): okr.objective.list trả scope, goal và parent"
```

---

### Task 6: Contract, frontend, gate tổng

**Files:**
- Modify (nếu cần): `shared/contracts/mvp-surface.json` + file sinh ra
- Check: `frontend/lib/modules/strategy/models/mvp_strategy_models.dart`, `frontend/lib/modules/projects/views/widgets/okr_section.dart`, `frontend/lib/modules/projects/models/project_operating_loop.dart`
- Modify (nếu cần): `tests/e2e/test_startup_os_http.py`, `tests/db_baseline_candidate/test_startup_core_schema.py`, `tests/e2e/test_startup_core_clean_baseline.py`

- [ ] **Step 1: Contract surface**

Run: `make mvp-contracts-check route-inventory-check contract-freeze-check`
Expected: PASS. Nếu `mvp-contracts-check` đỏ vì endpoint cosa bị xóa không nằm trong surface thì không có gì; nếu đỏ vì lệch thì `make mvp-contracts-gen` rồi commit file sinh.

- [ ] **Step 2: Frontend parse `projectId` nullable**

Run: `grep -nE "projectId|class .*Objective" frontend/lib/modules/strategy/models/mvp_strategy_models.dart frontend/lib/modules/projects/models/project_operating_loop.dart frontend/lib/modules/projects/views/widgets/okr_section.dart`
Nếu model Dart parse `projectId` là `String` bắt buộc cho **objective từ `/operations/objectives`**, đổi sang `String?` và thêm `scope`, `goalId`, `parentObjectiveId` (tùy chọn). Objective của `operating-loop` luôn thuộc project nên giữ.
Run: `make frontend-api-contract-check frontend-test frontend-analyze`
Expected: PASS.

- [ ] **Step 3: Test Python e2e và baseline**

Run:
```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/db_baseline_candidate/test_startup_core_schema.py tests/e2e/test_startup_core_clean_baseline.py tests/quality/test_route_auth_allowlist.py -q
```
Expected: PASS. Nếu baseline test liệt kê bảng `strategy.objectives`/`cosa_key_results`, xóa khỏi danh sách và thêm `okr_objectives` cột mới.

- [ ] **Step 4: Gate tổng**

Run: `make verify`
Expected: PASS toàn bộ (lint, typecheck, boundary, skillpacks, tenancy, contract-freeze, agent-test, apps-cosa-test, services-test, frontend-test/analyze).

Nếu đỏ do test không liên quan đến OKR đã đỏ từ trước, ghi lại riêng, không sửa trong dự án này.

- [ ] **Step 5: Kiểm tra thủ công đầu-cuối** (dev stack: `make dev-stack`)

1. `POST /operations/goals` tạo goal.
2. `POST /operations/objectives` với `scope=company, goalId`.
3. `POST /operations/objectives` với `projectId`, `parentObjectiveId` trỏ objective trên.
4. `POST /operations/objectives/:id/key-results`, rồi `POST /operations/key-results/:id/checkin`.
5. `GET /operations/goals/tree` → `objectiveCount`, `krTotal`, `krAchieved` tăng đúng.
6. `POST /operations/projects/triage` action `link` với objective công ty; thử link vào objective `scope=project` phải bị từ chối.

- [ ] **Step 6: Commit**

```bash
git add -A shared/contracts frontend/lib tests
git commit -m "chore(okr): đồng bộ contract, frontend và test baseline sau hợp nhất"
```

---

## Self-Review (đối chiếu spec)

- **Spec 3.1 (DB):** reset dữ liệu, cột mới, CHECK, trigger cơ bản → Task 1; đổi FK, trigger liên bảng, drop họ cũ → Task 4; preflight và fingerprint → Task 4 Step 6-7.
- **Spec 3.2 (service):** `okr.service` → Task 2; `goals.service` → Task 3; `discovery-project` → Task 4; API hợp nhất → Task 3 (xóa `/operations/cosa/*`, điều chỉnh 2.1).
- **Spec 3.3 (agent):** Task 5. **3.4 (frontend):** Task 6 Step 2. **3.5 (test):** các test mới trong Task 1-5, test hiện có chạy lại ở Task 2 Step 6 và Task 6.
- **Điều chỉnh 2.1:** `goal_id` chỉ bắt buộc cho company (Task 1 CHECK), không bắt buộc cycle khi publish (không đổi `publishObjectiveService`), không tạo view tiến độ (Task 3 dùng `okr-scoring`), `scope` default `project` (Task 1).
- **Chuỗi nhất quán `task.project_id` ↔ `objective.project_id` qua KR:** chưa có ràng buộc DB; để dự án A (ancestry) kiểm ở tầng service khi phân giải, ghi nhận không nằm trong A0.
- **Nhất quán kiểu:** `ObjectiveScope`, `Objective`, `loadObjectiveGoalMap`, `loadGoalStats` được định nghĩa trước khi dùng; `createObjectiveService` giữ chữ ký.

## Khoảng trống cần xác nhận khi thực thi

- Chữ ký thật của `createProject` (Task 2 Step 1) và các hàm test-session (`projectId`, `accessToken`) lấy theo `okr.test.ts` hiện có.
- Có test cũ nào `INSERT strategy.projects ... objective_id` trỏ họ cũ (Task 4 Step 7): chạy `grep -rn "objective_id" services/company/operations/tests`.
- Môi trường chạy `make dev-migrate` là DB dev :5431; không chạy trên môi trường khác.
