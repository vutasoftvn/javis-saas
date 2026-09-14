# Workspace/Project/OKR/Weekly/Tasks Foundation + Executive Board Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện luồng nền tảng end-to-end: UI lifecycle Workspace/Project, OKR sống thật, generator OKR→Weekly, Task soft-delete + liên kết Week/KR trực tiếp, và cơ chế Executive Board gợi ý activation theo Project stage — theo đúng spec `docs/superpowers/specs/2026-09-14-workspace-project-okr-weekly-executive-board-foundation-design.md`.

**Architecture:** Toàn bộ backend nghiệp vụ (`services/company`, Encore.ts + Drizzle) đã có sẵn hạ tầng lifecycle/OKR/operating-loop — công việc chính là thêm vài endpoint mới hẹp phạm vi (soft-delete task, stage-suggestion) và nối dây Flutter frontend đúng các route đã sống thật. Không đổi kiến trúc 4 vùng, không tạo Agent/Service mới.

**Tech Stack:** Encore.ts, Drizzle ORM (Postgres, schema `operating`/`strategy`/`identity`), Vitest; Flutter/Dart, GetX, `ApiClient`/`http`.

## Global Constraints

- Migration release chỉ Expand (ALTER TABLE ADD COLUMN nullable/CREATE — không DROP/rename cột đang dùng). Nguồn: CLAUDE.md Encore Guardrail #4.
- Handler chỉ khai báo endpoint/auth/validate/gọi service — không import `drizzle-orm`/`db.ts`/schema trực tiếp trong handler. Nguồn: CLAUDE.md Encore Guardrail #1.
- Lỗi từ public request dùng `APIError` tại boundary — không throw `Error` trần. Nguồn: CLAUDE.md Encore Guardrail #3.
- Không dùng `any`, `@ts-ignore`, `@ts-expect-error`, cast để che typecheck. Nguồn: CLAUDE.md Encore Guardrail #5.
- Không gate/tự động chuyển lifecycle stage hay tự động activate role mà không có xác nhận rõ ràng của founder — mọi transition/activation đều là hành động người dùng bấm xác nhận. Nguồn: CLAUDE.md "Bốn vùng kiến trúc" + spec mục 6.
- Route mới gọi từ `frontend/lib/**` phải nằm trong `shared/contracts/mvp-surface.json` — chạy `make frontend-api-contract-check` sau khi thêm. Nguồn: CLAUDE.md.
- Comment code mới viết bằng tiếng Việt cho phần giải thích why; định danh/log/error message giữ tiếng Anh. Nguồn: CLAUDE.md "Comment code".
- Không tạo git worktree; code trực tiếp trên `main`. Nguồn: CLAUDE.md.

---

## File Structure

**Backend (`services/company/operations`):**
- `migrations/024_task_week_kr_links_and_cycle_source.up.sql` / `.down.sql` — cột mới `weekly_plan_id`, `key_result_id` trên `tasks`; `source_objective_id` trên `twelve_week_cycles`.
- `services/task.service.ts` — thêm `deleteTaskService`, mở rộng `createTaskService`/`Task` type để đọc/ghi 2 cột mới.
- `handlers/task.handler.ts` — thêm `deleteTask` endpoint.
- `services/okr-weekly-generator.service.ts` (mới) — `generateCycleFromObjective` (tạo cycle + N weekly_plans rỗng từ 1 objective đã publish).
- `handlers/okr-weekly-generator.handler.ts` (mới) — expose `POST /operations/objectives/:objectiveId/generate-weekly-cycle`.
- `migrations/025_workspace_executive_role_activations.up.sql` / `.down.sql` (mới) — 2 bảng activation cấp Workspace cho cả 13 role Executive Board.
- `services/workspace-executive-role-activation.service.ts` (mới) — `getWorkspaceExecutiveRoleStates`/`activateWorkspaceExecutiveRole`/`disableWorkspaceExecutiveRole`.
- `services/executive-board-stage-presets.ts` (mới) — bảng mapping tĩnh Project stage → role keys gợi ý + hàm tính diff.
- `services/executive-role-activation.service.ts` — đổi `getProjectExecutiveRoleStates` sang đọc nguồn Workspace; thêm `getStageSuggestion`.
- `handlers/executive-role-activation.handler.ts` — thêm `activateWorkspaceExecutiveRoleApi`/`disableWorkspaceExecutiveRoleApi`/`getProjectExecutiveStageSuggestionApi`; deprecate 3 endpoint Project-scoped mutation cũ (trả lỗi hướng dẫn, không xoá).
- `handlers/twelve-week-year.handler.ts` — sửa dead-end message ở `updateCycle`.

**Backend (`services/company/identity`):** không thêm file mới — endpoint lifecycle đã đủ.

**Contracts:** `shared/contracts/mvp-surface.json` — thêm entry cho các route mới (task delete, OKR generator, Executive Board workspace activate/disable + stage-suggestion), đổi `enabled: false` cho 3 entry Project-scoped Executive Board cũ. Không đổi `executive-advisor-roles.json`/preset — cơ chế preset bị thay thế hoàn toàn bởi activation trực tiếp cấp Workspace (xem Task 9).

**Frontend (`frontend/lib`):**
- `modules/strategy/services/okr_service.dart` — viết lại, gọi API thật.
- `modules/strategy/services/okr_weekly_generator_service.dart` (mới) — gọi endpoint generator.
- `modules/strategy/widgets/okr_weekly_generator_dialog.dart` (mới).
- `modules/tasks/services/task_service.dart` — thêm `deleteTask`.
- `data/models/task_kanban_model.dart` — thêm field `weeklyPlanId`, `keyResultId`.
- `modules/hologram_hub/services/executive_advisory_board_service.dart` — đổi `activateRole`/`disableRole` sang `workspaceId`, xoá `selectPreset`.
- `modules/hologram_hub/controllers/executive_advisory_board_controller.dart` — đổi tương ứng, xoá `selectStartupPreset`.
- `core/lifecycle/lifecycle_service.dart` (mới) — service dùng chung cho Workspace + Project lifecycle transition/history.
- `core/lifecycle/widgets/lifecycle_settings_section.dart` (mới) — widget dùng chung, tham số hoá theo `entityType` (`workspace`|`project`).
- `modules/settings/views/settings_view.dart` — chèn `LifecycleSettingsSection` cho Workspace.
- Project Settings view tương ứng (xác định đường dẫn ở Task 13) — chèn `LifecycleSettingsSection` cho Project.
- `modules/projects/services/executive_board_stage_suggestion_service.dart` (mới).
- `modules/projects/widgets/executive_board_stage_suggestion_dialog.dart` (mới).
- Xoá: `modules/strategy/services/twelve_week_service.dart`, `modules/settings/workforce/views/profile_composition_view.dart`, `modules/organization/services/business_pack_service.dart`.

---

### Task 1: Migration — thêm cột Week/KR trên Task và `source_objective_id` trên Cycle

**Files:**
- Create: `services/company/operations/migrations/024_task_week_kr_links_and_cycle_source.up.sql`
- Create: `services/company/operations/migrations/024_task_week_kr_links_and_cycle_source.down.sql`
- Modify: `services/company/shared/db/schema/operations.ts:33-64` (bảng `tasks`), `:395-418` (bảng `twelveWeekCycles`)

**Interfaces:**
- Produces: cột `operating.tasks.weekly_plan_id` (bigint, nullable, FK→`operating.weekly_plans.id`, `ON DELETE SET NULL`), `operating.tasks.key_result_id` (bigint, nullable, FK→`strategy.key_results.id`, `ON DELETE SET NULL`), `operating.twelve_week_cycles.source_objective_id` (bigint, nullable, FK→`strategy.okr_objectives.id`, `ON DELETE SET NULL`). Drizzle field name: `tasks.weeklyPlanId`, `tasks.keyResultId`, `twelveWeekCycles.sourceObjectiveId` — Task 2/4/5 dùng đúng 3 tên này.

- [ ] **Step 1: Viết migration up**

```sql
-- Migration 024: Task liên kết trực tiếp Week/KR (nullable); Cycle ghi
-- nguồn Objective sinh ra nó (dùng bởi OKR→Weekly generator, Task 5).
ALTER TABLE operating.tasks
  ADD COLUMN weekly_plan_id bigint REFERENCES operating.weekly_plans(id) ON DELETE SET NULL,
  ADD COLUMN key_result_id bigint REFERENCES strategy.key_results(id) ON DELETE SET NULL;

ALTER TABLE operating.twelve_week_cycles
  ADD COLUMN source_objective_id bigint REFERENCES strategy.okr_objectives(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_tasks_weekly_plan_id ON operating.tasks(weekly_plan_id) WHERE weekly_plan_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_key_result_id ON operating.tasks(key_result_id) WHERE key_result_id IS NOT NULL;
```

- [ ] **Step 2: Viết migration down**

```sql
DROP INDEX IF EXISTS operating.idx_tasks_key_result_id;
DROP INDEX IF EXISTS operating.idx_tasks_weekly_plan_id;

ALTER TABLE operating.twelve_week_cycles
  DROP COLUMN IF EXISTS source_objective_id;

ALTER TABLE operating.tasks
  DROP COLUMN IF EXISTS key_result_id,
  DROP COLUMN IF EXISTS weekly_plan_id;
```

- [ ] **Step 3: Cập nhật Drizzle schema `tasks`**

Trong `services/company/shared/db/schema/operations.ts`, thêm 2 dòng vào định nghĩa `tasks` (sau dòng `weeklyCommitmentId`, dòng 47):

```typescript
  weeklyPlanId: bigint("weekly_plan_id", { mode: "bigint" }).references(() => weeklyPlans.id, { onDelete: "set null" }),
  keyResultId: bigint("key_result_id", { mode: "bigint" }).references(() => keyResults.id, { onDelete: "set null" }),
```

Lưu ý: `weeklyPlans` và `keyResults` đều được định nghĩa PHÍA SAU `tasks` trong file này (dòng 371, 420) — Drizzle table object cho phép forward reference vì cả hai đều là `export const` cùng module, JS hoisting xử lý được; nếu TypeScript báo lỗi "used before declaration", di chuyển định nghĩa `tasks` xuống sau `keyResults`/`weeklyPlans` thay vì đổi kiểu dữ liệu.

- [ ] **Step 4: Cập nhật Drizzle schema `twelveWeekCycles`**

Thêm vào cuối object field của `twelveWeekCycles` (trước `deletedAt`, dòng ~417):

```typescript
  sourceObjectiveId: bigint("source_objective_id", { mode: "bigint" }).references(() => okrObjectives.id, { onDelete: "set null" }),
```

- [ ] **Step 5: Chạy migration trên DB dev**

Run: `make services-migrate-company`
Expected: log hiển thị migration `024_task_week_kr_links_and_cycle_source` applied thành công, không lỗi.

- [ ] **Step 6: Typecheck**

Run: `cd services/company && npm run typecheck`
Expected: PASS, không lỗi liên quan `tasks`/`twelveWeekCycles`.

- [ ] **Step 7: Commit**

```bash
git add services/company/operations/migrations/024_task_week_kr_links_and_cycle_source.up.sql \
        services/company/operations/migrations/024_task_week_kr_links_and_cycle_source.down.sql \
        services/company/shared/db/schema/operations.ts
git commit -m "feat(operations): add task week/kr links + cycle source_objective_id (migration 024)"
```

---

### Task 2: Backend — Task soft-delete

**Files:**
- Modify: `services/company/operations/services/task.service.ts`
- Modify: `services/company/operations/handlers/task.handler.ts:37-42` (thêm export sau `getTask`)
- Test: `services/company/operations/tests/task.service.test.ts` (tạo mới nếu chưa có file test cho `task.service.ts` — kiểm tra bằng `ls services/company/operations/tests/ | grep task` trước khi quyết định tạo mới hay bổ sung)

**Interfaces:**
- Consumes: `db`, `schema.tasks` từ `../models/db` (pattern giống các hàm khác trong `task.service.ts`, xem `getTaskService`); `TenantContext` từ `../../shared/types/tenant_context`; helper `createTestWorkspaceWithMember` từ `./_helpers` (dùng trong test, xem `services/company/operations/tests/project-lifecycle.service.test.ts:1-4` làm mẫu).
- Produces: `deleteTaskService(id: string, ctx: TenantContext): Promise<{ id: string; deletedAt: string }>` — export từ `task.service.ts`, dùng bởi Task handler ở step 3.

- [ ] **Step 1: Đọc `getTaskService` hiện có để lấy đúng pattern tenant-scoping**

Run: `grep -n "export async function getTaskService" -A 25 services/company/operations/services/task.service.ts`
Mục đích: nắm cách hàm hiện tại select theo `workspaceId` + `isNull(tasks.deletedAt)` để viết `deleteTaskService` đúng convention (không đoán — copy pattern thật).

- [ ] **Step 2: Viết test thất bại trước**

Thêm vào `services/company/operations/tests/task.service.test.ts` (tạo file mới nếu chưa tồn tại, theo mẫu import ở `project-lifecycle.service.test.ts`):

```typescript
import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember } from "./_helpers";
import type { TenantContext } from "../../shared/types/tenant_context";
import { createProjectService } from "../services/project.service";
import { createTaskService, getTaskService, deleteTaskService } from "../services/task.service";

function ctxFor(workspaceId: string, userId = "1"): TenantContext {
  return Object.freeze({
    workspaceId,
    userId,
    workforceMemberId: userId,
    membershipRole: "founder",
    permissions: [],
    correlationId: "test-task-delete",
    platformUserId: null,
  }) as unknown as TenantContext;
}

describe("deleteTaskService (soft delete)", () => {
  it("marks the task deletedAt and excludes it from subsequent getTaskService", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const project = await createProjectService(ctx, { title: "Delete Task Test" });
    const task = await createTaskService(
      { workspaceId: ws.workspaceId, title: "To be deleted", projectId: project.id },
      undefined
    );

    const result = await deleteTaskService(task.id, ctx);
    expect(result.id).toBe(task.id);
    expect(result.deletedAt).toBeTruthy();

    await expect(getTaskService(task.id, ctx)).rejects.toThrow();
  });
});
```

- [ ] **Step 3: Chạy test, xác nhận fail vì `deleteTaskService` chưa tồn tại**

Run: `cd services/company && npx vitest run operations/tests/task.service.test.ts -t "deleteTaskService"`
Expected: FAIL — `deleteTaskService is not a function` hoặc lỗi import.

- [ ] **Step 4: Implement `deleteTaskService`**

Thêm vào `services/company/operations/services/task.service.ts` (sau `getTaskService`, dùng đúng import `and/eq/isNull` đã có sẵn ở đầu file — không import lại nếu đã có):

```typescript
/**
 * Soft-delete task: set deletedAt, không xoá cứng — giữ audit trail cho
 * Weekly Commitment / Executive Board evidence tham chiếu ngược.
 */
export async function deleteTaskService(
  id: string,
  ctx: TenantContext
): Promise<{ id: string; deletedAt: string }> {
  const wsId = BigInt(ctx.workspaceId);
  const taskId = BigInt(id);

  const [updated] = await db
    .update(tasks)
    .set({ deletedAt: new Date(), updatedAt: new Date() })
    .where(and(eq(tasks.id, taskId), eq(tasks.workspaceId, wsId), isNull(tasks.deletedAt)))
    .returning({ id: tasks.id, deletedAt: tasks.deletedAt });

  if (!updated) {
    throw APIError.notFound(`Task ${id} not found`);
  }

  return { id: updated.id.toString(), deletedAt: updated.deletedAt!.toISOString() };
}
```

Nếu `APIError` chưa được import ở đầu `task.service.ts`, thêm `import { APIError } from "encore.dev/api";`.

- [ ] **Step 5: Chạy lại test, xác nhận pass**

Run: `cd services/company && npx vitest run operations/tests/task.service.test.ts -t "deleteTaskService"`
Expected: PASS.

- [ ] **Step 6: Thêm endpoint handler**

Trong `services/company/operations/handlers/task.handler.ts`, thêm import `deleteTaskService` vào khối import từ `../services/task.service` (dòng 8-23), rồi thêm export mới sau `getTask` (sau dòng 58):

```typescript
export const deleteTask = api(
  { method: "DELETE", path: "/operations/tasks/:id", expose: true },
  async ({
    id,
    workspaceId,
    authorization,
  }: {
    id: string;
    workspaceId: Header<"X-Workspace-Id">;
    authorization?: Header<"Authorization">;
  }): Promise<{ id: string; deletedAt: string }> => {
    const ctx = await requireWorkspaceAccess(authorization, workspaceId);
    return deleteTaskService(id, ctx);
  }
);
```

- [ ] **Step 7: Đăng ký route trong contract**

Mở `shared/contracts/mvp-surface.json`, tìm entry của `agent.project_activity.detail` hoặc bất kỳ entry Task nào hiện có để copy đúng shape, thêm entry mới:

```json
{
  "id": "operations.task.delete",
  "enabled": true,
  "owner": "company-operations",
  "plane": "company",
  "method": "DELETE",
  "path": "/operations/tasks/:id",
  "schema": "operations.task.delete.v1",
  "source_kind": "company_db",
  "requires_workspace": true,
  "requires_project": false,
  "frontend_symbol": "TaskService.deleteTask"
}
```

Đặt vào đúng vị trí alphabet/nhóm `operations.task.*` nếu file có tổ chức theo nhóm — kiểm tra context xung quanh trước khi chèn.

- [ ] **Step 8: Verify boundary + contract**

Run: `make company-boundary-check && make encore-handler-boundary-check && make frontend-api-contract-check`
Expected: tất cả PASS (route mới đã khai báo trong contract dù frontend chưa gọi tới — kiểm tra flag `frontend-api-contract-check` có yêu cầu frontend_symbol thực sự tồn tại chưa; nếu có, hoãn bước này tới sau Task 4 khi frontend đã gọi thật, và ghi rõ trong PR description).

- [ ] **Step 9: Commit**

```bash
git add services/company/operations/services/task.service.ts \
        services/company/operations/handlers/task.handler.ts \
        services/company/operations/tests/task.service.test.ts \
        shared/contracts/mvp-surface.json
git commit -m "feat(operations): add soft-delete endpoint for tasks"
```

---

### Task 3: Backend — điền `weeklyPlanId`/`keyResultId` khi tạo Task, trả về trong response

**Files:**
- Modify: `services/company/operations/services/task.service.ts` (hàm `createTaskService`, type `Task`)
- Test: `services/company/operations/tests/task.service.test.ts` (bổ sung case)

**Interfaces:**
- Consumes: `weeklyCommitments` (có `weeklyPlanId`, `purposeType`, `purposeRef`), `initiatives` (có `keyResultId`) từ `../models/db` schema — đã import sẵn trong `task.service.ts` (xác nhận bằng `grep -n "weeklyCommitments\|initiatives" services/company/operations/services/task.service.ts | head`).
- Produces: `Task.weeklyPlanId?: string`, `Task.keyResultId?: string` thêm vào interface `Task` export ở đầu file — Task 4 (Flutter model) đọc 2 field JSON `weeklyPlanId`/`keyResultId` (camelCase, Encore serialize field JS gốc, không snake_case — xác nhận bằng response mẫu của 1 field khác đã có như `weeklyCommitmentId`).

- [ ] **Step 1: Đọc logic hiện tại resolve `projectId`/`weeklyCommitmentId` trong `createTaskService`**

Run: `grep -n "async function createTaskService" -A 60 services/company/operations/services/task.service.ts`
Xác nhận đoạn code dòng ~164-205 (theo audit trước) xử lý `weeklyCommitmentId` và `initiativeId` — đây là chỗ cần chèn logic điền `weeklyPlanId`/`keyResultId`.

- [ ] **Step 2: Viết test cho case gắn qua weeklyCommitment**

Thêm vào `task.service.test.ts`:

```typescript
describe("createTaskService week/kr denormalization", () => {
  it("fills weeklyPlanId when created with a weeklyCommitmentId", async () => {
    // Test này CHỈ viết khung — cần fixture weeklyCommitment/weeklyPlan thật.
    // Dùng helper createCycleAuthorized + createWeeklyPlanAuthorized +
    // service tạo weeklyCommitment (tìm tên hàm bằng
    // `grep -n "export async function create.*Commitment" services/company/operations/services/project-operating-loop.service.ts`)
    // để dựng fixture trước khi gọi createTaskService — không mock DB.
  });
});
```

Lưu ý cho engineer thực thi: đây là điểm cần đọc thêm `project-operating-loop.service.ts` để lấy đúng tên hàm tạo `weeklyCommitment` (không đoán tên) trước khi viết fixture đầy đủ, vì audit trước không xác nhận tên hàm này. Viết test thật (không khung rỗng) trước khi sang Step 3.

- [ ] **Step 3: Implement denormalize trong `createTaskService`**

Sau đoạn code hiện có resolve `weeklyCommitmentId` (đã validate tồn tại), thêm:

```typescript
  let weeklyPlanId: bigint | null = null;
  let keyResultId: bigint | null = null;

  if (resolvedWeeklyCommitmentId) {
    const [wc] = await db
      .select({ weeklyPlanId: weeklyCommitments.weeklyPlanId, purposeType: weeklyCommitments.purposeType, purposeRef: weeklyCommitments.purposeRef })
      .from(weeklyCommitments)
      .where(eq(weeklyCommitments.id, resolvedWeeklyCommitmentId))
      .limit(1);
    if (wc) {
      weeklyPlanId = wc.weeklyPlanId;
      if (wc.purposeType === "KR" && wc.purposeRef) {
        keyResultId = BigInt(wc.purposeRef);
      }
    }
  }

  if (!keyResultId && resolvedInitiativeId) {
    const [init] = await db
      .select({ keyResultId: initiatives.keyResultId })
      .from(initiatives)
      .where(eq(initiatives.id, resolvedInitiativeId))
      .limit(1);
    if (init) keyResultId = init.keyResultId;
  }
```

Biến `resolvedWeeklyCommitmentId`/`resolvedInitiativeId` phải khớp đúng tên biến thật trong hàm (đọc lại Step 1 output để xác nhận tên chính xác — không giả định, sửa cho khớp code thật trước khi tiếp tục). Sau đó thêm `weeklyPlanId` và `keyResultId` vào object `.values({...})` khi `db.insert(tasks)`, và vào object trả về (`toTask`/mapping function nếu có, hoặc trực tiếp trong return).

- [ ] **Step 4: Thêm field vào interface `Task`**

Tìm `export interface Task` ở đầu `task.service.ts`, thêm:

```typescript
  weeklyPlanId?: string;
  keyResultId?: string;
```

- [ ] **Step 5: Chạy test**

Run: `cd services/company && npx vitest run operations/tests/task.service.test.ts`
Expected: PASS toàn bộ file (bao gồm test cũ từ Task 2).

- [ ] **Step 6: Typecheck + commit**

Run: `cd services/company && npm run typecheck`
Expected: PASS.

```bash
git add services/company/operations/services/task.service.ts services/company/operations/tests/task.service.test.ts
git commit -m "feat(operations): denormalize weeklyPlanId/keyResultId onto Task at creation"
```

---

### Task 4: Frontend — Task soft-delete + hiển thị Week/KR

**Files:**
- Modify: `frontend/lib/modules/tasks/services/task_service.dart`
- Modify: `frontend/lib/data/models/task_kanban_model.dart`
- Test: `frontend/test/modules/tasks/task_service_test.dart` (tạo nếu chưa có — kiểm tra `ls frontend/test/modules/tasks/` trước)

**Interfaces:**
- Consumes: `ApiClient.get`/`ApiClient.post`/(cần xác nhận có `ApiClient.delete` chưa — `grep -n "static.*delete" frontend/lib/core/network/api_client.dart`; nếu chưa có, thêm method `delete` vào `ApiClient` theo đúng pattern `get`/`post` hiện có trước khi dùng ở đây).
- Produces: `TaskService.deleteTask(String id) -> Future<void>`; `TaskKanbanModel.weeklyPlanId`, `TaskKanbanModel.keyResultId` (nullable `String?`).

- [ ] **Step 1: Kiểm tra `ApiClient` có method `delete` chưa**

Run: `grep -n "static Future" frontend/lib/core/network/api_client.dart`

- [ ] **Step 2: Nếu chưa có, thêm `ApiClient.delete`**

Đọc implementation của `ApiClient.get`/`ApiClient.post` (thường wrap `http.get`/`http.post` + base URL + header workspace) và thêm hàm `delete` cùng pattern — code cụ thể phụ thuộc cấu trúc thật của file, đọc trước khi viết (không đoán chữ ký).

- [ ] **Step 3: Viết test cho `TaskKanbanModel.fromJson` với field mới**

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:javis_saas/data/models/task_kanban_model.dart';

void main() {
  test('TaskKanbanModel.fromJson parses weeklyPlanId and keyResultId when present', () {
    final model = TaskKanbanModel.fromJson({
      'id': '1',
      'title': 'Test',
      'status': 'todo',
      'weeklyPlanId': '42',
      'keyResultId': '99',
    });
    expect(model.weeklyPlanId, '42');
    expect(model.keyResultId, '99');
  });

  test('TaskKanbanModel.fromJson tolerates missing weeklyPlanId/keyResultId', () {
    final model = TaskKanbanModel.fromJson({'id': '1', 'title': 'Test', 'status': 'todo'});
    expect(model.weeklyPlanId, isNull);
    expect(model.keyResultId, isNull);
  });
}
```

(điều chỉnh import path `package:javis_saas/...` theo đúng tên package thật trong `pubspec.yaml` — `grep "^name:" frontend/pubspec.yaml`.)

- [ ] **Step 4: Chạy test, xác nhận fail**

Run: `cd frontend && flutter test test/modules/tasks/task_service_test.dart`
Expected: FAIL — field không tồn tại trên `TaskKanbanModel`.

- [ ] **Step 5: Thêm field vào `TaskKanbanModel`**

Đọc cấu trúc `fromJson` hiện có của `TaskKanbanModel` (constructor + factory) trước khi sửa — thêm 2 field cuối:

```dart
  final String? weeklyPlanId;
  final String? keyResultId;
```

và trong `factory TaskKanbanModel.fromJson`, thêm:

```dart
      weeklyPlanId: json['weeklyPlanId']?.toString(),
      keyResultId: json['keyResultId']?.toString(),
```

Cập nhật constructor chính và (nếu có) `toJson`/`copyWith` cho nhất quán — đọc toàn bộ file trước khi sửa để không bỏ sót chỗ nào cần thêm field.

- [ ] **Step 6: Chạy lại test, xác nhận pass**

Run: `cd frontend && flutter test test/modules/tasks/task_service_test.dart`
Expected: PASS.

- [ ] **Step 7: Thêm `TaskService.deleteTask`**

Trong `frontend/lib/modules/tasks/services/task_service.dart`, thêm sau `getTaskBlockers`:

```dart
  /// Soft-delete task qua endpoint Encore: DELETE /operations/tasks/:id
  Future<void> deleteTask(String taskId) async {
    if (taskId.isEmpty) throw ArgumentError('taskId cannot be empty');
    await _requireWorkspaceId();

    final response = await ApiClient.delete('/operations/tasks/$taskId');
    if (response.statusCode == 200) return;
    if (response.statusCode == 401 || response.statusCode == 403) {
      throw StateError('Authentication or workspace access denied: ${response.statusCode}');
    } else if (response.statusCode == 404) {
      throw StateError('Task $taskId not found (404)');
    } else {
      throw StateError('Failed to delete task: ${response.statusCode} ${response.body}');
    }
  }
```

- [ ] **Step 8: Chạy `make frontend-analyze` + toàn bộ test module tasks**

Run: `make frontend-analyze && cd frontend && flutter test test/modules/tasks/`
Expected: PASS, 0 warning mới.

- [ ] **Step 9: Commit**

```bash
git add frontend/lib/modules/tasks/services/task_service.dart \
        frontend/lib/data/models/task_kanban_model.dart \
        frontend/lib/core/network/api_client.dart \
        frontend/test/modules/tasks/task_service_test.dart
git commit -m "feat(tasks): wire soft-delete + surface weeklyPlanId/keyResultId on TaskKanbanModel"
```

*(Việc thêm nút "Xoá" vào Task card UI thật và badge hiển thị Week/KR trên card là việc UI thuần tuý — nếu `TasksView`/`TaskCard` widget đã tồn tại rõ ràng, bổ sung 1 `IconButton` gọi `deleteTask` + confirm dialog, và 1 `Chip`/`Text` nhỏ hiển thị `weeklyPlanId != null` / `keyResultId != null`. Vị trí chính xác trong widget tree cần đọc file thật lúc thực thi — không đoán trước ở đây.)*

---

### Task 5: Backend — OKR→Weekly generator

**Files:**
- Create: `services/company/operations/services/okr-weekly-generator.service.ts`
- Create: `services/company/operations/handlers/okr-weekly-generator.handler.ts`
- Modify: `services/company/operations/api.ts` (barrel export — thêm export handler mới, xem export pattern hiện có cho `task.handler`)
- Test: `services/company/operations/tests/okr-weekly-generator.service.test.ts`

**Interfaces:**
- Consumes: `createCycleAuthorized(ctx, { projectId, durationWeeks, ... }): Promise<CycleDto>` và `createWeeklyPlanAuthorized(ctx, { projectId, cycleId, weekNo, ... }): Promise<WeeklyPlanDto>` từ `../services/project-operating-loop.service.ts` (chữ ký đã xác nhận đọc trực tiếp file, dòng 442-499 và 501+). `okrObjectives`, `twelveWeekCycles` từ `../models/db` schema.
- Produces: `generateCycleFromObjective(ctx, objectiveId, durationWeeks): Promise<CycleDto>` — dùng bởi handler Step 3 và Flutter Task 6.

- [ ] **Step 1: Đọc `createWeeklyPlanAuthorized` đầy đủ để lấy tham số bắt buộc**

Run: `sed -n '501,560p' services/company/operations/services/project-operating-loop.service.ts`
Ghi lại chính xác các field bắt buộc/optional của `req` trước khi viết Step 4 — không đoán.

- [ ] **Step 2: Viết test thất bại trước**

```typescript
import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember } from "../tests/_helpers";
import type { TenantContext } from "../../shared/types/tenant_context";
import { createProjectService } from "../services/project.service";
import { createObjectiveService, publishObjectiveService } from "../services/okr.service";
import { generateCycleFromObjective } from "../services/okr-weekly-generator.service";
import { db, schema } from "../models/db";
import { eq } from "drizzle-orm";

function ctxFor(workspaceId: string, userId = "1"): TenantContext {
  return Object.freeze({
    workspaceId,
    userId,
    workforceMemberId: userId,
    membershipRole: "founder",
    permissions: [],
    correlationId: "test-okr-weekly-generator",
    platformUserId: null,
  }) as unknown as TenantContext;
}

describe("generateCycleFromObjective", () => {
  it("creates a cycle with the requested duration and one empty weekly_plan per week", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const project = await createProjectService(ctx, { title: "Generator Test" });
    const objective = await createObjectiveService(ctx, { projectId: project.id, title: "Grow MRR" });
    await publishObjectiveService(ctx, objective.id);

    const cycle = await generateCycleFromObjective(ctx, objective.id, 4);

    expect(cycle.durationWeeks).toBe(4);
    expect(cycle.sourceObjectiveId).toBe(objective.id);

    const plans = await db
      .select()
      .from(schema.weeklyPlans)
      .where(eq(schema.weeklyPlans.cycleId, BigInt(cycle.id)));
    expect(plans).toHaveLength(4);
    expect(plans.map((p) => p.weekNo).sort()).toEqual([1, 2, 3, 4]);
  });

  it("rejects when objective is not published", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const project = await createProjectService(ctx, { title: "Generator Draft Test" });
    const objective = await createObjectiveService(ctx, { projectId: project.id, title: "Draft objective" });

    await expect(generateCycleFromObjective(ctx, objective.id, 4)).rejects.toThrow();
  });
});
```

Ghi chú: nếu tên hàm thật của `okr.service.ts` khác `createObjectiveService`/`publishObjectiveService` (audit trước không xác nhận tên chính xác), chạy `grep -n "^export async function" services/company/operations/services/okr.service.ts` trước và sửa import cho khớp trước khi tiếp tục.

- [ ] **Step 3: Chạy test, xác nhận fail**

Run: `cd services/company && npx vitest run operations/tests/okr-weekly-generator.service.test.ts`
Expected: FAIL — module `okr-weekly-generator.service` chưa tồn tại.

- [ ] **Step 4: Implement `generateCycleFromObjective`**

```typescript
import { APIError } from "encore.dev/api";
import { eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { TenantContext } from "../../shared/types/tenant_context";
import { createCycleAuthorized, createWeeklyPlanAuthorized, CycleDto } from "./project-operating-loop.service";

const { okrObjectives } = schema;

/**
 * Sinh khung Operating Cycle + weekly_plans rỗng từ 1 Objective đã publish.
 * Không tự tạo initiative/commitment — founder/agent gắn KR vào từng tuần
 * thủ công sau đó, đúng nguyên tắc "generator chỉ dựng khung".
 */
export async function generateCycleFromObjective(
  ctx: TenantContext,
  objectiveId: string,
  durationWeeks: number
): Promise<CycleDto> {
  const wsId = BigInt(ctx.workspaceId);
  const objId = BigInt(objectiveId);

  const [objective] = await db
    .select()
    .from(okrObjectives)
    .where(eq(okrObjectives.id, objId))
    .limit(1);

  if (!objective || objective.workspaceId !== wsId) {
    throw APIError.notFound(`Objective ${objectiveId} not found`);
  }
  if (objective.status !== "published") {
    throw APIError.failedPrecondition("Objective must be published before generating a weekly cycle");
  }

  const cycle = await createCycleAuthorized(ctx, {
    projectId: objective.projectId.toString(),
    durationWeeks,
  });

  await db
    .update(schema.twelveWeekCycles)
    .set({ sourceObjectiveId: objId })
    .where(eq(schema.twelveWeekCycles.id, BigInt(cycle.id)));

  for (let weekNo = 1; weekNo <= durationWeeks; weekNo++) {
    await createWeeklyPlanAuthorized(ctx, {
      projectId: objective.projectId.toString(),
      cycleId: cycle.id,
      weekNo,
    });
  }

  return { ...cycle, sourceObjectiveId: objectiveId };
}
```

Lưu ý: nếu `CycleDto` (kiểu trả về của `createCycleAuthorized`) chưa có field `sourceObjectiveId`, thêm vào interface đó trong `project-operating-loop.service.ts` (map từ `row.sourceObjectiveId?.toString()` trong hàm `toCycle`) trước khi build — kiểm tra bằng `grep -n "interface CycleDto" -A 15 services/company/operations/services/project-operating-loop.service.ts`.

Kiểm tra tên thật của trường trạng thái publish (`objective.status !== "published"`) khớp giá trị enum thật ở `okr.service.ts` (`grep -n "'published'\|\"published\"" services/company/operations/services/okr.service.ts`) — sửa literal cho khớp nếu khác.

- [ ] **Step 5: Chạy lại test, xác nhận pass**

Run: `cd services/company && npx vitest run operations/tests/okr-weekly-generator.service.test.ts`
Expected: PASS cả 2 case.

- [ ] **Step 6: Viết handler**

```typescript
import { api, Header, APIError } from "encore.dev/api";
import { requireWorkspaceAccess } from "../../shared/auth/workspace-access";
import { generateCycleFromObjective } from "../services/okr-weekly-generator.service";
import { CycleDto } from "../services/project-operating-loop.service";

interface GenerateWeeklyCycleParams {
  authorization?: Header<"Authorization">;
  workspaceId: Header<"X-Workspace-Id">;
  objectiveId: string;
  durationWeeks: number;
}

export const generateWeeklyCycleFromObjectiveApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/objectives/:objectiveId/generate-weekly-cycle",
  },
  async (params: GenerateWeeklyCycleParams): Promise<CycleDto> => {
    if (params.durationWeeks < 1 || params.durationWeeks > 12) {
      throw APIError.invalidArgument("durationWeeks must be between 1 and 12");
    }
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return generateCycleFromObjective(ctx, params.objectiveId, params.durationWeeks);
  }
);
```

- [ ] **Step 7: Đăng ký barrel export**

Mở `services/company/operations/api.ts`, thêm export cho handler mới theo đúng pattern export `task.handler`/`project-lifecycle.handler` hiện có (đọc file trước khi sửa để copy đúng cú pháp — `export * from "./handlers/okr-weekly-generator.handler";` hoặc named export tuỳ convention thật của file).

- [ ] **Step 8: Thêm contract entry vào `mvp-surface.json`**

```json
{
  "id": "operations.okr.generate_weekly_cycle",
  "enabled": true,
  "owner": "company-operations",
  "plane": "company",
  "method": "POST",
  "path": "/operations/objectives/:objectiveId/generate-weekly-cycle",
  "schema": "operations.okr.generate_weekly_cycle.v1",
  "source_kind": "company_db",
  "requires_workspace": true,
  "requires_project": false,
  "frontend_symbol": "OkrWeeklyGeneratorService.generate"
}
```

- [ ] **Step 9: Typecheck + verify**

Run: `cd services/company && npm run typecheck && cd .. && cd .. && make company-boundary-check && make encore-handler-boundary-check`
Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add services/company/operations/services/okr-weekly-generator.service.ts \
        services/company/operations/handlers/okr-weekly-generator.handler.ts \
        services/company/operations/api.ts \
        services/company/operations/tests/okr-weekly-generator.service.test.ts \
        shared/contracts/mvp-surface.json
git commit -m "feat(operations): OKR-to-weekly-cycle generator triggered from a published Objective"
```

---

### Task 6: Frontend — nối dây OKR service

**Files:**
- Modify: `frontend/lib/modules/strategy/services/okr_service.dart`
- Test: `frontend/test/modules/strategy/okr_service_test.dart` (tạo mới)

**Interfaces:**
- Consumes: `ApiClient.get(path)`, `ApiClient.post(path, {body})`, `ApiClient.put(path, {body})`, `ApiClient.delete(path)` (xác nhận `put` tồn tại — `grep -n "static Future.*put" frontend/lib/core/network/api_client.dart`, thêm nếu thiếu theo đúng pattern `post`).
- Produces: mọi method public của `OkrService` giữ nguyên chữ ký hiện có (không đổi tên — các controller gọi `OkrService` không cần sửa), chỉ đổi phần thân từ `ApiClient.removed(...)` sang gọi thật.

- [ ] **Step 1: Xoá comment "PLANNED" ở đầu file, cập nhật docstring**

Thay dòng 1-3 của `okr_service.dart`:

```dart
// OKR module nối API thật (2026-09-14) — backend operations/handlers/okr.handler.ts
// đã sống, xem docs/superpowers/specs/2026-09-14-...-design.md mục 2.
import 'dart:convert';
```

- [ ] **Step 2: Viết test cho `getOkrCycles` gọi đúng path thật**

```dart
import 'package:flutter_test/flutter_test.dart';
// Import mock ApiClient theo đúng pattern test hiện có trong frontend/test/
// (tìm ví dụ: `grep -rl "ApiClient" frontend/test/ | head -3` để copy cách
// mock http client trước khi viết test này — không tự bịa cách mock).

void main() {
  test('OkrService.getOkrCycles calls GET /operations/okr-cycles (not removed)', () {
    // Khung test: assert request path thật == '/operations/okr-cycles',
    // KHÔNG chứa 'r1-removed'. Điền cụ thể theo pattern mock đã tìm ở trên.
  }, skip: 'điền mock client cụ thể theo pattern thật của repo trước khi bỏ skip');
}
```

Bước này CHỦ ĐÍCH để `skip` cho tới khi engineer xác nhận pattern mock `ApiClient` thật trong repo (không đoán — nhiều repo Flutter có `MockApiClient`/`http_mock_adapter` khác nhau). Sau khi xác nhận, xoá tham số `skip` và điền assertion thật, sau đó tiếp tục Step 3-5 như một task TDD bình thường.

- [ ] **Step 3: Viết lại từng method — ví dụ `getOkrCycles`**

```dart
  Future<StrategyListResult<Map<String, dynamic>>> getOkrCycles() async {
    final workspaceId = await getWorkspaceId();
    if (workspaceId == null) {
      return StrategyListResult.failure(L10nKey.errNoWorkspace.tr);
    }
    try {
      final response = await ApiClient.get('/operations/okr-cycles');
      return _decodeFlexibleList(response, 'cycles');
    } catch (e) {
      return StrategyListResult.failure(e.toString());
    }
  }

  Future<Map<String, dynamic>> createOkrCycle({
    required String name,
    DateTime? startDate,
    DateTime? endDate,
    String? status,
  }) async {
    await requireWorkspaceId();
    final response = await ApiClient.post('/operations/okr-cycles', body: {
      'name': name,
      if (startDate != null) 'startDate': startDate.toUtc().toIso8601String(),
      if (endDate != null) 'endDate': endDate.toUtc().toIso8601String(),
      if (status != null) 'status': status,
    });
    return decode(response);
  }
```

- [ ] **Step 4: Áp dụng cùng pattern cho toàn bộ method còn lại**

Thay từng `ApiClient.removed('r1-removed:<path>')` bằng đúng verb HTTP + path, theo bảng đã chốt trong design doc mục 2:

| Method Dart | Verb + path thật |
|---|---|
| `getObjectives` | `GET /operations/objectives${query}` |
| `createObjective` | `POST /operations/objectives`, body `{title, cycleId, status, why, ownerMemberId}` (lọc null) |
| `publishObjective` | `POST /operations/objectives/$objectiveId/publish` |
| `updateObjective` | `PUT /operations/objectives/$objectiveId`, body `{title, status}` (lọc null) — bỏ query `?workspace_id=` cũ, `ApiClient` tự gắn header `X-Workspace-Id` (xác nhận bằng cách đọc `ApiClient.get` implementation ở Step 1 Task 4) |
| `deleteObjective` | `DELETE /operations/objectives/$objectiveId` |
| `getKeyResults` | `GET /operations/key-results${query}` (bỏ nhánh gọi `/objectives/$objectiveId` để lấy `keyResults` lồng — dùng thẳng endpoint list có filter `objective_id`) |
| `createKeyResult` | `POST /operations/objectives/$objectiveId/key-results`, body `{title, baselineValue, currentValue, targetValue, unit, cadence, status, scoringType}` (lọc null) |
| `checkinKeyResult` | `POST /operations/key-results/$keyResultId/checkin`, body `{value}` |
| `updateKeyResult` | `PUT /operations/key-results/$keyResultId`, body `{currentValue, targetValue, unit, status}` (lọc null) |
| `deleteKeyResult` | `DELETE /operations/key-results/$keyResultId` |

Với mỗi method, bỏ luôn biến `workspaceId` không dùng nếu `ApiClient` tự gắn header (tránh cảnh báo `unused_local_variable` — và xoá dòng `// ignore_for_file: unused_local_variable...` ở đầu file nếu không còn cần).

- [ ] **Step 5: `flutter analyze` sạch cảnh báo unused**

Run: `make frontend-analyze`
Expected: không còn warning nào tại `okr_service.dart` (đặc biệt các `ignore_for_file` không còn cần thiết phải được xoá, không giữ lại "phòng hờ").

- [ ] **Step 6: Chạy test**

Run: `cd frontend && flutter test test/modules/strategy/okr_service_test.dart`
Expected: PASS (sau khi Step 2 đã được hoàn thiện, không còn `skip`).

- [ ] **Step 7: Commit**

```bash
git add frontend/lib/modules/strategy/services/okr_service.dart frontend/test/modules/strategy/okr_service_test.dart
git commit -m "fix(strategy): reconnect OkrService to live /operations/{okr-cycles,objectives,key-results} endpoints"
```

---

### Task 7: Frontend — dialog OKR→Weekly generator sau khi publish Objective

**Files:**
- Create: `frontend/lib/modules/strategy/services/okr_weekly_generator_service.dart`
- Create: `frontend/lib/modules/strategy/widgets/okr_weekly_generator_dialog.dart`
- Modify: điểm gọi `okrService.publishObjective(...)` trong controller thật (xác định file bằng `grep -rn "publishObjective(" frontend/lib/modules/strategy/controllers/` trước khi sửa — không đoán tên controller)

**Interfaces:**
- Consumes: `OkrWeeklyGeneratorService.generate(objectiveId, durationWeeks) -> Future<Map<String, dynamic>>` (tự định nghĩa ở service mới, gọi endpoint Task 5).
- Produces: hàm `showOkrWeeklyGeneratorDialog(BuildContext, {required String objectiveId}) -> Future<void>` dùng bởi controller.

- [ ] **Step 1: Viết `OkrWeeklyGeneratorService`**

```dart
import 'dart:convert';
import '../../../core/network/api_client.dart';
import '../../../core/network/workspace_scoped_service.dart';

class OkrWeeklyGeneratorService extends WorkspaceService {
  Future<Map<String, dynamic>> generate(String objectiveId, int durationWeeks) async {
    if (durationWeeks < 1 || durationWeeks > 12) {
      throw ArgumentError('durationWeeks must be between 1 and 12');
    }
    final response = await ApiClient.post(
      '/operations/objectives/$objectiveId/generate-weekly-cycle',
      body: {'durationWeeks': durationWeeks},
    );
    if (response.statusCode == 200 || response.statusCode == 201) {
      return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    }
    throw StateError('Failed to generate weekly cycle: ${response.statusCode} ${response.body}');
  }
}
```

- [ ] **Step 2: Viết dialog**

```dart
import 'package:flutter/material.dart';
import '../services/okr_weekly_generator_service.dart';

/// Hiện sau khi publish 1 Objective — hỏi founder có muốn tạo khung Operating
/// Cycle (weekly_plans rỗng) ngay không. Founder bỏ qua vẫn publish bình
/// thường (xem design doc mục 3 — generator không bắt buộc).
Future<void> showOkrWeeklyGeneratorDialog(
  BuildContext context, {
  required String objectiveId,
}) async {
  int durationWeeks = 12;
  final service = OkrWeeklyGeneratorService();

  await showDialog<void>(
    context: context,
    builder: (dialogContext) => StatefulBuilder(
      builder: (dialogContext, setState) => AlertDialog(
        title: const Text('Tạo Operating Cycle cho Objective này?'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Số tuần cho chu kỳ:'),
            Slider(
              value: durationWeeks.toDouble(),
              min: 1,
              max: 12,
              divisions: 11,
              label: '$durationWeeks tuần',
              onChanged: (v) => setState(() => durationWeeks = v.round()),
            ),
            Text('$durationWeeks tuần'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Bỏ qua'),
          ),
          ElevatedButton(
            onPressed: () async {
              try {
                await service.generate(objectiveId, durationWeeks);
                if (dialogContext.mounted) Navigator.of(dialogContext).pop();
              } catch (e) {
                if (dialogContext.mounted) {
                  ScaffoldMessenger.of(dialogContext).showSnackBar(
                    SnackBar(content: Text('Không tạo được cycle: $e')),
                  );
                }
              }
            },
            child: const Text('Xác nhận'),
          ),
        ],
      ),
    ),
  );
}
```

- [ ] **Step 3: Gọi dialog sau `publishObjective` thành công** — **PHẠM VI MỞ RỘNG (quyết định 2026-09-14, sau khi Task 7 chạy lần đầu và phát hiện gap thật):**

Implementer đầu tiên chạy Task 7 báo BLOCKED ở bước này: `frontend/lib/modules/strategy/` **hoàn toàn không có `controllers/`/`views/`** — không có UI nào gọi `okrService.publishObjective(...)` cả (chỉ có trong test). Giả định ban đầu của brief (đã có sẵn 1 controller/view gọi `publishObjective`) là SAI.

Founder quyết định (không phải chọn nhánh "chỉ hoãn Step 3"): **mở rộng Task 7** để build UI publish Objective tối thiểu VÀ mở route `strategy` thật (hiện đang bị `_plannedRoute(WorkspaceModule.strategy)` chặn trong `frontend/lib/core/routing/module_routes.dart:188`) — vì backend OKR (Task 5+6) đã sống hoàn toàn, khác các module khác vẫn bị chặn do backend chưa sẵn sàng (đã audit riêng, xem lịch sử phiên).

**Phạm vi bổ sung cụ thể:**

1. Model `MvpObjective` đã tồn tại (`frontend/lib/modules/strategy/models/mvp_strategy_models.dart:137-174`, field `id/workspaceId/cycleId/title/why/ownerMemberId/status/projectIds/createdAt`) — dùng nguyên, không tạo model mới. Lưu ý: default `status` trong `fromJson` là chuỗi `'DRAFT'` (viết hoa), nhưng backend thật (xác nhận ở Task 5 review) dùng literal thường `"draft"`/`"published"` — khi so sánh status trong UI (để hiện nút Publish), so sánh **không phân biệt hoa/thường** (`status.toLowerCase() == 'draft'`), không sửa default trong model (ngoài phạm vi task này).

2. Tạo `frontend/lib/modules/strategy/controllers/strategy_controller.dart` (GetX `GetxController`): `loadObjectives()` gọi `OkrService().getObjectives()`, lưu vào `RxList<MvpObjective>` (parse qua `MvpObjective.fromJson` từ `StrategyListResult.items`); `publish(String objectiveId)` gọi `OkrService().publishObjective(objectiveId)` rồi `loadObjectives()` lại để refresh danh sách. Controller không tự mở dialog (không có `BuildContext`) — chỉ trả `Future<void>`/throw khi lỗi, để View xử lý UI.

3. Tạo `frontend/lib/modules/strategy/bindings/strategy_binding.dart` (GetX `Bindings`), theo đúng pattern `TasksBinding`/`FinanceBinding` đã có (`grep -n "class TasksBinding" -A 10 frontend/lib/modules/tasks/bindings/tasks_binding.dart` để copy pattern).

4. Tạo `frontend/lib/modules/strategy/views/strategy_view.dart`: màn hình tối giản — `ListView` các Objective (title, badge status), mỗi item ở trạng thái `draft` có nút "Publish"; bấm Publish → gọi `controller.publish(id)` → nếu thành công, gọi `showOkrWeeklyGeneratorDialog(context, objectiveId: id)` (Task 7 Step 2, cùng file này có `BuildContext` thật vì là View, không phải Controller — đúng nguyên tắc "dialog gọi từ nơi có BuildContext thật" mà brief gốc đã nêu). Loading/error state tối thiểu (không cần đẹp — đây là UI tối giản để có chỗ test luồng, không phải thiết kế UI hoàn chỉnh).

5. Sửa `frontend/lib/core/routing/module_routes.dart`: đổi `_plannedRoute(WorkspaceModule.strategy)` (dòng 188) thành route thật, đúng pattern route `tasks`/`finance` đã có (`AppShell` + `StrategyBinding` + `StrategyView`, middlewares `[AuthMiddleware(), ProjectSetupGuardMiddleware()]`).

6. Cập nhật `docs/superpowers/specs/2026-09-14-...-design.md` mục 3 (nếu cần) để ghi nhận UI publish Objective giờ tồn tại thật — không bắt buộc, chỉ nếu có thời gian.

Sau khi hoàn thành 1-5, hoàn thiện đúng nội dung Step 3 gốc (nối dialog sau publish) trong `strategy_view.dart` như mô tả ở mục 4.

- [ ] **Step 4: `flutter analyze` + chạy toàn bộ test module strategy**

Run: `make frontend-analyze && cd frontend && flutter test test/modules/strategy/`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/modules/strategy/services/okr_weekly_generator_service.dart \
        frontend/lib/modules/strategy/widgets/okr_weekly_generator_dialog.dart
git add -u
git commit -m "feat(strategy): prompt to generate a weekly Operating Cycle after publishing an Objective"
```

---

### Task 8: Dọn dẹp Weekly execution — xoá file mồ côi, sửa dead-end resize

**Files:**
- Delete: `frontend/lib/modules/strategy/services/twelve_week_service.dart`
- Modify: `services/company/operations/handlers/twelve-week-year.handler.ts` (hàm `updateCycle`)

**Interfaces:** không có — task dọn dẹp thuần tuý, không thêm API mới.

- [ ] **Step 1: Xác nhận lại 0 call site của `twelve_week_service.dart`**

Run: `grep -rln "twelve_week_service\|TwelveWeekService" frontend/lib/ frontend/test/`
Expected: chỉ chính file đó xuất hiện (nếu có call site khác xuất hiện, DỪNG — không xoá, báo cáo lại thay vì tiếp tục theo plan).

**PHẠM VI MỞ RỘNG (quyết định 2026-09-14, sau khi Task 8 chạy lần đầu):**
Implementer đầu tiên chạy grep này và phát hiện `twelve_week_service.dart`
**KHÔNG mồ côi** — `strategy_service.dart` (facade `StrategyService`) import/
export/instantiate nó, và `HubCommandMixin.loadActiveCycleTimeline()`
(`frontend/lib/modules/hologram_hub/controllers/mixins/hub_command_mixin.dart:111-137`,
dùng bởi Hub — 1 trong số ít route đang sống thật) gọi trực tiếp
`strategyService.getTwelveWeekCycles()` → `TwelveWeekService.getTwelveWeekCycles()`
→ `GET /execution/twelve-week-cycles` (route không tồn tại, luôn fail âm
thầm — lỗi bị nuốt vào `debugPrint`, không hiện gì rõ ràng cho founder).

Founder quyết định: **KHÔNG xoá file — sửa nó gọi đúng backend thật**, thay
vì chỉ dừng lại báo cáo. Cụ thể:

1. `TwelveWeekService.getTwelveWeekCycles()` (dòng 11-22): đổi
   `ApiClient.get('/execution/twelve-week-cycles?workspace_id=$workspaceId')`
   thành `ApiClient.get('/operations/workspaces/$workspaceId/cycles')` — route
   thật đã có (`services/company/operations/handlers/twelve-week-year.handler.ts:30-35`,
   `listCycles`, trả `{ cycles: TwelveWeekCycle[] }`). Giữ nguyên
   `decodeList(response, 'cycles')` — key response khớp sẵn.
2. `TwelveWeekService.getCycleTimeline(String cycleId)` (dòng 45-55): route
   cũ `/execution/twelve-week-cycles/:id/timeline` không có thật thay thế
   trực tiếp. Route gần nhất có thật là
   `GET /operations/execution-cycle-view?projectId=...&cycleId=...`
   (`services/company/operations/handlers/execution-cycle-view.handler.ts:17-23`)
   — **bắt buộc `projectId`**, không chỉ `cycleId`. Đổi chữ ký hàm thành
   `getCycleTimeline(String cycleId, {required String projectId})`, gọi
   `ApiClient.get('/operations/execution-cycle-view?projectId=$projectId&cycleId=$cycleId')`.
   Đã xác nhận (grep) `activeCycleTimeline` (nơi lưu kết quả hàm này ở
   `hub_command_mixin.dart:48`) **hiện không được đọc/hiển thị ở bất kỳ view
   nào** — chỉ set giá trị, không render — nên đổi shape response không rủi
   ro vỡ UI hiện tại. Xác nhận lại bằng
   `grep -rn "activeCycleTimeline" frontend/lib/modules/hologram_hub/` trước
   khi sửa; nếu tìm thấy nơi render thật (khác lần audit này), dừng lại báo
   cáo thay vì đoán.
3. Sửa call site `hub_command_mixin.dart:129` (`getCycleTimeline(cycleId)`)
   thành truyền thêm `projectId: activeCycle['projectId']?.toString()` (field
   `projectId` chắc chắn có trên `TwelveWeekCycle` DTO vì cột DB
   `twelve_week_cycles.project_id NOT NULL` — xác nhận tên field camelCase
   thật bằng cách đọc response mẫu hoặc `TwelveWeekCycle` interface ở
   `twelve-week-year.service.ts` trước khi dùng). Nếu `projectId` null/rỗng,
   bỏ qua gọi `getCycleTimeline` (giữ nguyên hành vi an toàn, không throw).
4. Bỏ `?workspace_id=` khỏi các URL đã sửa nếu `ApiClient` tự gắn header
   `X-Workspace-Id` (xác nhận như các task Flutter trước — đọc
   `api_client.dart` nếu chưa chắc).
5. KHÔNG sửa các method khác trong `twelve_week_service.dart` (`createTwelveWeekCycle`,
   `getWeeklyPlans`, v.v.) — chúng cũng gọi `/execution/*` sai nhưng KHÔNG có
   call site thật nào từ Hub (chỉ 2 method trên được gọi qua
   `HubCommandMixin`) — ngoài phạm vi lần sửa này, để nguyên.

Sau khi hoàn thành 5 bước trên, mới tiếp tục đúng Step 3 gốc bên dưới (`flutter analyze`) — bỏ qua Step 2 gốc (xoá file, không còn áp dụng).

- [ ] **Step 3: `flutter analyze` xác nhận không còn import treo**

Run: `make frontend-analyze`
Expected: PASS, không lỗi "target of URI doesn't exist".

- [ ] **Step 4: Sửa dead-end resize trong `twelve-week-year.handler.ts`**

Run: `grep -n "operating-cycle\|Resize the operating cycle" services/company/operations/handlers/twelve-week-year.handler.ts`
Đọc đoạn code đó, thay message trỏ vào route không tồn tại bằng lỗi rõ ràng "not supported" (theo hướng (a) đã chọn trong design doc mục 4 — không thêm route resize mới):

```typescript
    throw APIError.invalidArgument(
      "Resizing an in-progress operating cycle is not supported. Complete or cancel the current cycle, then create a new one with the desired duration."
    );
```

Giữ nguyên phần còn lại của `updateCycle` không liên quan tới `durationWeeks`.

- [ ] **Step 5: Chạy test hiện có của `twelve-week-year.handler.ts` (nếu có)**

Run: `find services/company/operations/tests -iname "*twelve-week-year*"`
Nếu có file test, chạy `cd services/company && npx vitest run operations/tests/<tên file test>` và xác nhận PASS (sửa message lỗi trong assertion nếu test cũ so khớp message cũ y hệt).

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore(strategy,operations): remove orphan TwelveWeekService, fix dead-end cycle resize message"
```

---

### Task 9: Backend — Executive Board activation cấp Workspace + stage-suggestion

> **Bối cảnh quan trọng (đọc trước khi code):** Executive Board hiện có 1
> luồng Flutter ĐANG CHẠY THẬT, ĐÃ TEST (`frontend/lib/modules/hologram_hub/services/executive_advisory_board_service.dart`
> + `controllers/executive_advisory_board_controller.dart` + 2 file test),
> dựa trên bảng Project-scoped `project_executive_board_settings`/
> `project_executive_role_activations`. Theo quyết định thiết kế 2026-09-14
> (xem spec mục 6), activation chuyển sang Workspace-scoped cho **toàn bộ 13
> role** (không chỉ 4 role duy trì) — vì 1 công ty chỉ có 1 CFO/CRO/COO thật
> dù chạy nhiều Project song song ở stage khác nhau. Đã xác nhận
> `project_executive_deliberations*` chỉ tham chiếu `roleKey` dạng chuỗi,
> KHÔNG có FK tới activation record — không có ràng buộc kỹ thuật nào chặn
> việc này. Bảng cũ bị **ngừng dùng trong code, KHÔNG DROP** (Encore
> Guardrail #4 — destructive schema change cần release riêng). Task 10 xử
> lý việc cập nhật Flutter code đang dùng bảng cũ.
>
> **CẬP NHẬT 2026-09-14 (sau khi implementer đầu tiên dừng lại đúng lúc ở
> NEEDS_CONTEXT):** Xác minh code thật lộ ra 2 vấn đề brief ban đầu không
> lường hết, đã chốt hướng xử lý với founder:
>
> 1. **`services/company/operations/services/executive-deliberation.service.ts`
>    (~900 dòng, tính năng ĐANG CHẠY THẬT, có 3 test suite riêng:
>    `executive-deliberation.service.test.ts`,
>    `executive-deliberation.handler.test.ts`,
>    `executive-deliberation-callback.test.ts`)** gate authorization ở **3 vị
>    trí** (quanh dòng ~237 pin role vào frame, ~771 nhận callback phân tích,
>    ~949 verify trước khi chạy role) dựa vào bảng CŨ
>    `project_executive_role_activations`. Nếu Task 9 deprecate đường ghi vào
>    bảng cũ mà không sửa 3 chỗ đọc này, Executive Deliberation sẽ gãy hoàn
>    toàn (mọi role luôn bị coi "not ACTIVE"). **Quyết định: gộp việc sửa 3
>    vị trí này vào PHẠM VI Task 9** — đổi sang đọc `workspace_executive_role_activations`
>    (bảng mới) thay vì bảng project-scoped cũ, giữ đúng 1 nguồn sự thật cho
>    quyết định authorization (CLAUDE.md quy tắc #5). Cả 3 test suite trên
>    cũng cần cập nhật fixture (đổi từ gọi `activateExecutiveRole(ctx, projectId, roleKey, ...)`
>    sang `activateWorkspaceExecutiveRole(ctx, roleKey, ...)`) và chạy lại tới
>    khi pass — nằm trong phạm vi Task 9, không tách task riêng.
>
> 2. **Gate "role UNAVAILABLE cho tới khi agent nền tương ứng ACTIVE"**
>    (`executive-role-activation.service.ts`, dùng
>    `verifyUnderlyingAgentActive(workspaceId, projectId, requiredProfileKey)`
>    — 3 tham số thật, KHÔNG phải 1 tham số như brief gốc đoán, và bản chất
>    hàm này project-scoped không gỡ được) **được GIỮ LẠI**, không bỏ, nhưng
>    **định nghĩa lại ở cấp Workspace**: role coi là có "agent nền active" nếu
>    **có ít nhất 1 Project trong workspace** mà `verifyUnderlyingAgentActive(workspaceId, projectId, requiredProfileKey)`
>    trả `true` (aggregate OR qua toàn bộ Project của workspace, không phải
>    check 1 Project cụ thể). `getWorkspaceExecutiveRoleStates(ctx)` cần liệt
>    kê toàn bộ Project của `ctx.workspaceId` (dùng pattern tương tự
>    `listProjects`/`project.service.ts`) rồi loop kiểm tra — N+1 query chấp
>    nhận được ở quy mô MVP hiện tại, không cần tối ưu batch. 8 assertion
>    trong `executive-role-activation.service.test.ts` (dòng ~160-270, mã hoá
>    quy tắc UNAVAILABLE→AVAILABLE_NOT_ACTIVATED→ACTIVE theo agent nền) **viết
>    lại theo đúng ngữ nghĩa aggregate mới này** (không xoá quy tắc, chỉ đổi
>    phạm vi kiểm tra từ 1 project sang toàn workspace) — ví dụ: test "workspace
>    trắng, 0 Project nào có agent ACTIVE" phải mong đợi `UNAVAILABLE`, không
>    còn là `AVAILABLE_NOT_ACTIVATED` như test-case ban đầu brief viết (bản
>    thân test đó cũng cần viết lại theo hướng "tạo ít nhất 1 Project có agent
>    ACTIVE trước khi assert AVAILABLE_NOT_ACTIVATED").
>
> 3. Hàm service tầng thấp `selectStartupCorePreset`/`activateExecutiveRole`/`disableExecutiveRole`
>    (khác `activateWorkspaceExecutiveRole`/`disableWorkspaceExecutiveRole` mới)
>    vẫn còn ghi bảng project-scoped cũ và có thể vẫn còn call site thật
>    (fixture test của executive-deliberation trước khi sửa mục 1). Sau khi
>    mục 1 hoàn tất (deliberation test fixture chuyển sang dùng hàm workspace
>    mới), nếu 3 hàm service tầng thấp này không còn call site thật nào ngoài
>    test đã lỗi thời — an toàn để bỏ qua, không bắt buộc xoá trong Task 9,
>    nhưng KHÔNG được để handler cũ (Step 17) gọi chúng nữa (đã tự deprecate ở
>    tầng handler theo thiết kế gốc).

**Files:**
- Create: `services/company/operations/migrations/025_workspace_executive_role_activations.up.sql` / `.down.sql`
- Modify: `services/company/shared/db/schema/operations.ts` (thêm 2 bảng mới)
- Create: `services/company/operations/services/executive-board-stage-presets.ts`
- Create: `services/company/operations/services/workspace-executive-role-activation.service.ts`
- Modify: `services/company/operations/services/executive-role-activation.service.ts` (đổi `getProjectExecutiveRoleStates` sang đọc nguồn Workspace; thêm `getStageSuggestion`)
- Modify: `services/company/operations/handlers/executive-role-activation.handler.ts` (thêm endpoint Workspace-scoped mới, deprecate 3 endpoint Project-scoped mutation cũ)
- Test: `services/company/operations/tests/workspace-executive-role-activation.service.test.ts`, `services/company/operations/tests/executive-board-stage-presets.service.test.ts`

**Interfaces:**
- Consumes: `EXECUTIVE_ROLE_CATALOG`, `ExecutiveRoleKey`, danh sách đủ 13 key (`chief_of_staff, cfo, cmo, coo, cro, cpo, cco, chro, ciso, gc, cdo, caio, vpe`) từ `../../shared/contracts/executive-advisor-roles.generated` (đã import sẵn ở đầu `executive-role-activation.service.ts`); `verifyUnderlyingAgentActive` (đã có, giữ nguyên logic UNAVAILABLE cho role chưa có agent binding thật); `PROJECT_LIFECYCLE_STAGES`/`projects.lifecycleStage` (đọc `services/company/operations/services/project-lifecycle.service.ts:13-21` để dùng đúng 7 hằng số `P0_DISCOVERY`..`P6_SCALE_GOVERN`).
- Produces: `getWorkspaceExecutiveRoleStates(ctx): Promise<WorkspaceExecutiveBoardState>`, `activateWorkspaceExecutiveRole(ctx, roleKey, options): Promise<{id, roleKey, state, version}>`, `disableWorkspaceExecutiveRole(ctx, roleKey, options): Promise<{...}>` (Task 10/11 Flutter dùng qua endpoint HTTP, không import trực tiếp); `PERSISTENT_EXECUTIVE_ROLES: readonly ExecutiveRoleKey[]`, `roleKeysForStage(stage: string): ExecutiveRoleKey[]`, `getStageSuggestion(ctx, projectId): Promise<{ stage: string; toActivate: ExecutiveRoleKey[]; toSuggestDeactivate: ExecutiveRoleKey[] }>`.

- [ ] **Step 1: Migration — bảng activation cấp Workspace**

`services/company/operations/migrations/025_workspace_executive_role_activations.up.sql`:

```sql
-- Migration 025: Executive Board activation chuyển cấp Workspace (thay
-- project_executive_role_activations cho TOÀN BỘ 13 role — 1 công ty chỉ có
-- 1 CFO/CRO/COO thật dù chạy nhiều Project song song ở stage khác nhau).
-- Bảng project-scoped cũ KHÔNG bị xoá (Expand-only) — chỉ ngừng dùng trong code.
CREATE TABLE operating.workspace_executive_role_activations (
  id bigint PRIMARY KEY,
  workspace_id bigint NOT NULL,
  role_key varchar(64) NOT NULL,
  state varchar(32) NOT NULL, -- 'ACTIVE' | 'DISABLED'
  version integer NOT NULL DEFAULT 1,
  actor_id bigint NOT NULL,
  disabled_reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uix_workspace_executive_role_activations_ws_role UNIQUE (workspace_id, role_key)
);

CREATE INDEX idx_workspace_executive_role_activations_ws ON operating.workspace_executive_role_activations(workspace_id);

CREATE TABLE operating.workspace_executive_role_activation_events (
  id bigint PRIMARY KEY,
  workspace_id bigint NOT NULL,
  role_key varchar(64) NOT NULL,
  activation_id bigint NOT NULL REFERENCES operating.workspace_executive_role_activations(id) ON DELETE CASCADE,
  from_state varchar(32),
  to_state varchar(32) NOT NULL,
  actor_id bigint NOT NULL,
  version integer NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}',
  occurred_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_workspace_exec_role_act_events_act ON operating.workspace_executive_role_activation_events(activation_id, occurred_at);
```

`.down.sql`:

```sql
DROP TABLE IF EXISTS operating.workspace_executive_role_activation_events;
DROP TABLE IF EXISTS operating.workspace_executive_role_activations;
```

- [ ] **Step 2: Cập nhật Drizzle schema**

Thêm vào `services/company/shared/db/schema/operations.ts` (cạnh định nghĩa `projectExecutiveRoleActivations` dòng 856, để 2 khái niệm gần nhau khi đọc code):

```typescript
export const workspaceExecutiveRoleActivations = operatingSchema.table("workspace_executive_role_activations", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  roleKey: varchar("role_key", { length: 64 }).notNull(),
  state: varchar("state", { length: 32 }).notNull(),
  version: integer("version").default(1).notNull(),
  actorId: bigint("actor_id", { mode: "bigint" }).notNull(),
  disabledReason: text("disabled_reason"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  uixWsRole: uniqueIndex("uix_workspace_executive_role_activations_ws_role").on(t.workspaceId, t.roleKey),
  idxWs: index("idx_workspace_executive_role_activations_ws").on(t.workspaceId),
}));

export const workspaceExecutiveRoleActivationEvents = operatingSchema.table("workspace_executive_role_activation_events", {
  id: bigint("id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  roleKey: varchar("role_key", { length: 64 }).notNull(),
  activationId: bigint("activation_id", { mode: "bigint" }).notNull().references(() => workspaceExecutiveRoleActivations.id, { onDelete: "cascade" }),
  fromState: varchar("from_state", { length: 32 }),
  toState: varchar("to_state", { length: 32 }).notNull(),
  actorId: bigint("actor_id", { mode: "bigint" }).notNull(),
  version: integer("version").notNull(),
  payload: jsonb("payload").default({}).notNull(),
  occurredAt: timestamp("occurred_at", { withTimezone: true }).defaultNow().notNull(),
}, (t) => ({
  idxActivationOccurred: index("idx_workspace_exec_role_act_events_act").on(t.activationId, t.occurredAt),
}));
```

- [ ] **Step 3: Chạy migration**

Run: `make services-migrate-company`
Expected: migration `025_workspace_executive_role_activations` applied thành công.

- [ ] **Step 4: Viết test cho `workspace-executive-role-activation.service.ts` trước**

`services/company/operations/tests/workspace-executive-role-activation.service.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember } from "./_helpers";
import type { TenantContext } from "../../shared/types/tenant_context";
import {
  getWorkspaceExecutiveRoleStates,
  activateWorkspaceExecutiveRole,
  disableWorkspaceExecutiveRole,
} from "../services/workspace-executive-role-activation.service";

function ctxFor(workspaceId: string, userId = "1"): TenantContext {
  return Object.freeze({
    workspaceId,
    userId,
    workforceMemberId: userId,
    membershipRole: "founder",
    permissions: [],
    correlationId: "test-workspace-executive-activation",
    platformUserId: null,
  }) as unknown as TenantContext;
}

describe("workspace executive role activation", () => {
  it("lists all 13 roles as AVAILABLE_NOT_ACTIVATED before any activation", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);

    const board = await getWorkspaceExecutiveRoleStates(ctx);
    expect(board.roles).toHaveLength(13);
    const cfo = board.roles.find((r) => r.roleKey === "cfo");
    expect(cfo?.displayState).toBe("AVAILABLE_NOT_ACTIVATED");
  });

  it("activating a role is visible workspace-wide (shared instance, not per-project)", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);

    await activateWorkspaceExecutiveRole(ctx, "cfo", {});
    const board = await getWorkspaceExecutiveRoleStates(ctx);
    const cfo = board.roles.find((r) => r.roleKey === "cfo");
    expect(cfo?.displayState).toBe("ACTIVE");
  });

  it("disabling a role records disabledReason and flips state back", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);

    const activated = await activateWorkspaceExecutiveRole(ctx, "coo", {});
    await disableWorkspaceExecutiveRole(ctx, "coo", { expectedVersion: activated.version, reason: "not needed yet" });

    const board = await getWorkspaceExecutiveRoleStates(ctx);
    const coo = board.roles.find((r) => r.roleKey === "coo");
    expect(coo?.displayState).toBe("DISABLED");
  });
});
```

- [ ] **Step 5: Chạy test, xác nhận fail**

Run: `cd services/company && npx vitest run operations/tests/workspace-executive-role-activation.service.test.ts`
Expected: FAIL — module chưa tồn tại.

- [ ] **Step 6: Implement `workspace-executive-role-activation.service.ts`**

Đọc `services/company/operations/services/executive-role-activation.service.ts` từ đầu tới hết (đặc biệt `getProjectExecutiveRoleStates`, `activateExecutiveRole`, `disableExecutiveRole`, `verifyUnderlyingAgentActive`) trước khi viết — copy đúng pattern build `displayState` (UNAVAILABLE/AVAILABLE_NOT_ACTIVATED/ACTIVE/DISABLED) và optimistic locking `version`, chỉ đổi `projectId` → bỏ hẳn, khoá theo `workspaceId` + `roleKey`:

```typescript
import { APIError } from "encore.dev/api";
import { and, eq } from "drizzle-orm";
import { db, schema } from "../models/db";
import { generateSnowflake } from "../../shared/services/snowflake.service";
import { TenantContext } from "../../shared/types/tenant_context";
import {
  EXECUTIVE_ROLE_CATALOG,
  ExecutiveRoleKey,
  isExecutiveRoleKey,
} from "../../shared/contracts/executive-advisor-roles.generated";
import { verifyUnderlyingAgentActive } from "./founder-agent-compatibility.service";
import { requireExecutiveBoardFounderAuthority } from "./executive-role-activation.service";

const { workspaceExecutiveRoleActivations, workspaceExecutiveRoleActivationEvents } = schema;

export type ExecutiveRoleDisplayState = "UNAVAILABLE" | "AVAILABLE_NOT_ACTIVATED" | "ACTIVE" | "DISABLED";

export interface WorkspaceExecutiveRoleState {
  roleKey: ExecutiveRoleKey;
  label: string;
  advisoryRemit: string;
  displayState: ExecutiveRoleDisplayState;
  runtimeReadiness: string;
  requiredProfileKey: string;
  version: number;
  activatedAt?: string;
  actorId?: string;
  disabledReason?: string;
}

export interface WorkspaceExecutiveBoardState {
  workspaceId: string;
  roles: WorkspaceExecutiveRoleState[];
}

/**
 * Đọc trạng thái cả 13 role Executive Board — activation cấp Workspace,
 * chia sẻ cho mọi Project trong cùng workspace (xem spec mục 6, 2026-09-14).
 */
export async function getWorkspaceExecutiveRoleStates(ctx: TenantContext): Promise<WorkspaceExecutiveBoardState> {
  const wsId = BigInt(ctx.workspaceId);

  const activations = await db
    .select()
    .from(workspaceExecutiveRoleActivations)
    .where(eq(workspaceExecutiveRoleActivations.workspaceId, wsId));

  const activationByRole = new Map(activations.map((a) => [a.roleKey, a]));

  const roles: WorkspaceExecutiveRoleState[] = [];
  for (const roleKey of Object.keys(EXECUTIVE_ROLE_CATALOG) as ExecutiveRoleKey[]) {
    const def = EXECUTIVE_ROLE_CATALOG[roleKey];
    const activation = activationByRole.get(roleKey);
    const underlyingActive = await verifyUnderlyingAgentActive(def.requiredProfileKey);

    let displayState: ExecutiveRoleDisplayState;
    if (!underlyingActive) {
      displayState = "UNAVAILABLE";
    } else if (!activation) {
      displayState = "AVAILABLE_NOT_ACTIVATED";
    } else {
      displayState = activation.state === "ACTIVE" ? "ACTIVE" : "DISABLED";
    }

    roles.push({
      roleKey,
      label: def.label,
      advisoryRemit: def.advisoryRemit,
      displayState,
      runtimeReadiness: def.runtimeReadiness,
      requiredProfileKey: def.requiredProfileKey,
      version: activation?.version ?? 0,
      activatedAt: activation?.updatedAt?.toISOString(),
      actorId: activation?.actorId?.toString(),
      disabledReason: activation?.disabledReason ?? undefined,
    });
  }

  return { workspaceId: wsId.toString(), roles };
}

export async function activateWorkspaceExecutiveRole(
  ctx: TenantContext,
  roleKey: string,
  options: { expectedVersion?: number; idempotencyKey?: string }
): Promise<{ id: string; roleKey: string; state: string; version: number }> {
  if (!isExecutiveRoleKey(roleKey)) {
    throw APIError.invalidArgument(`Unknown executive role key '${roleKey}'`);
  }
  await requireExecutiveBoardFounderAuthorityForWorkspace(ctx);

  const wsId = BigInt(ctx.workspaceId);
  const actorId = BigInt(ctx.workforceMemberId ?? "0");

  return db.transaction(async (tx) => {
    const [existing] = await tx
      .select()
      .from(workspaceExecutiveRoleActivations)
      .where(and(eq(workspaceExecutiveRoleActivations.workspaceId, wsId), eq(workspaceExecutiveRoleActivations.roleKey, roleKey)))
      .limit(1);

    let row;
    if (!existing) {
      [row] = await tx
        .insert(workspaceExecutiveRoleActivations)
        .values({ id: generateSnowflake(), workspaceId: wsId, roleKey, state: "ACTIVE", version: 1, actorId })
        .returning();
    } else {
      if (options.expectedVersion !== undefined && existing.version !== options.expectedVersion) {
        throw APIError.aborted(`Role ${roleKey} activation changed; reload before retrying`);
      }
      [row] = await tx
        .update(workspaceExecutiveRoleActivations)
        .set({ state: "ACTIVE", version: existing.version + 1, actorId, disabledReason: null, updatedAt: new Date() })
        .where(eq(workspaceExecutiveRoleActivations.id, existing.id))
        .returning();
    }

    await tx.insert(workspaceExecutiveRoleActivationEvents).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      roleKey,
      activationId: row.id,
      fromState: existing?.state ?? null,
      toState: "ACTIVE",
      actorId,
      version: row.version,
      payload: { idempotencyKey: options.idempotencyKey ?? null },
    });

    return { id: row.id.toString(), roleKey, state: row.state, version: row.version };
  });
}

export async function disableWorkspaceExecutiveRole(
  ctx: TenantContext,
  roleKey: string,
  options: { expectedVersion?: number; reason?: string; idempotencyKey?: string }
): Promise<{ id: string; roleKey: string; state: string; version: number }> {
  if (!isExecutiveRoleKey(roleKey)) {
    throw APIError.invalidArgument(`Unknown executive role key '${roleKey}'`);
  }
  await requireExecutiveBoardFounderAuthorityForWorkspace(ctx);

  const wsId = BigInt(ctx.workspaceId);
  const actorId = BigInt(ctx.workforceMemberId ?? "0");

  return db.transaction(async (tx) => {
    const [existing] = await tx
      .select()
      .from(workspaceExecutiveRoleActivations)
      .where(and(eq(workspaceExecutiveRoleActivations.workspaceId, wsId), eq(workspaceExecutiveRoleActivations.roleKey, roleKey)))
      .limit(1);

    if (!existing) {
      throw APIError.failedPrecondition(`Role ${roleKey} was never activated for this workspace`);
    }
    if (options.expectedVersion !== undefined && existing.version !== options.expectedVersion) {
      throw APIError.aborted(`Role ${roleKey} activation changed; reload before retrying`);
    }

    const [row] = await tx
      .update(workspaceExecutiveRoleActivations)
      .set({ state: "DISABLED", version: existing.version + 1, actorId, disabledReason: options.reason ?? null, updatedAt: new Date() })
      .where(eq(workspaceExecutiveRoleActivations.id, existing.id))
      .returning();

    await tx.insert(workspaceExecutiveRoleActivationEvents).values({
      id: generateSnowflake(),
      workspaceId: wsId,
      roleKey,
      activationId: row.id,
      fromState: existing.state,
      toState: "DISABLED",
      actorId,
      version: row.version,
      payload: { reason: options.reason ?? null, idempotencyKey: options.idempotencyKey ?? null },
    });

    return { id: row.id.toString(), roleKey, state: row.state, version: row.version };
  });
}
```

Ghi chú quan trọng — 3 điểm PHẢI xác nhận bằng code thật trước khi coi bước này xong (không đoán chữ ký):
1. `EXECUTIVE_ROLE_CATALOG` — xác nhận đúng tên export + shape field (`label`, `advisoryRemit`, `runtimeReadiness`, `requiredProfileKey`) bằng `grep -n "EXECUTIVE_ROLE_CATALOG" -A 20 services/company/shared/contracts/executive-advisor-roles.generated.ts`.
2. `requireExecutiveBoardFounderAuthority(ctx, projectId)` (đã có, nhận `projectId`) — hàm mới cần bản KHÔNG có `projectId` (`requireExecutiveBoardFounderAuthorityForWorkspace(ctx)`, chỉ check `ctx.isAiAgent`/`membershipRole`, bỏ đoạn query bảng `projects`). Thêm hàm này vào `executive-role-activation.service.ts`, export, rồi import ở file mới — không gọi thẳng bản cũ vì nó đòi `projectId`.
3. `founder-agent-compatibility.service.ts` export đúng tên `verifyUnderlyingAgentActive` với chữ ký 1 tham số `requiredProfileKey: string` — xác nhận bằng `grep -n "export.*verifyUnderlyingAgentActive" services/company/operations/services/founder-agent-compatibility.service.ts`.

- [ ] **Step 7: Chạy lại test, xác nhận pass**

Run: `cd services/company && npx vitest run operations/tests/workspace-executive-role-activation.service.test.ts`
Expected: PASS cả 3 case.

- [ ] **Step 8: Viết bảng mapping tĩnh (stage → role gợi ý)**

`services/company/operations/services/executive-board-stage-presets.ts`:

```typescript
import { ExecutiveRoleKey } from "../../shared/contracts/executive-advisor-roles.generated";

/**
 * Mapping Project lifecycle stage → role Executive Board gợi ý kích hoạt.
 * Founder chốt bảng này 2026-09-14 — không tự động áp dụng, chỉ dùng để
 * tính diff gợi ý (xem getStageSuggestion trong executive-role-activation.service.ts).
 */
export const STAGE_ROLE_PRESETS: Readonly<Record<string, readonly ExecutiveRoleKey[]>> = Object.freeze({
  P0_DISCOVERY: ["chief_of_staff", "cfo", "cmo", "cpo"],
  P1_PROBLEM_VALIDATION: ["chief_of_staff", "cfo", "cmo", "cpo"],
  P2_SOLUTION_VALIDATION: ["coo", "vpe", "ciso", "gc", "cdo", "caio"],
  P3_BUILD_VALIDATE: ["coo", "vpe", "ciso", "gc", "cdo", "caio"],
  P4_GO_TO_MARKET: ["cro", "cco"],
  P5_OPERATE_GROWTH: ["chro"],
  P6_SCALE_GOVERN: ["chro"],
});

/** Role duy trì xuyên suốt — không bao giờ nằm trong toSuggestDeactivate. */
export const PERSISTENT_EXECUTIVE_ROLES: readonly ExecutiveRoleKey[] = Object.freeze([
  "chief_of_staff",
  "cfo",
  "cmo",
  "cpo",
]);

export function roleKeysForStage(stage: string): readonly ExecutiveRoleKey[] {
  return STAGE_ROLE_PRESETS[stage] ?? [];
}
```

- [ ] **Step 9: Viết test cho `roleKeysForStage`**

`services/company/operations/tests/executive-board-stage-presets.service.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { roleKeysForStage, PERSISTENT_EXECUTIVE_ROLES } from "../services/executive-board-stage-presets";

describe("executive board stage presets", () => {
  it("maps P0_DISCOVERY to chief_of_staff, cfo, cmo, cpo", () => {
    expect(roleKeysForStage("P0_DISCOVERY")).toEqual(["chief_of_staff", "cfo", "cmo", "cpo"]);
  });

  it("maps P4_GO_TO_MARKET to cro, cco", () => {
    expect(roleKeysForStage("P4_GO_TO_MARKET")).toEqual(["cro", "cco"]);
  });

  it("returns empty array for unknown stage", () => {
    expect(roleKeysForStage("UNKNOWN")).toEqual([]);
  });

  it("persistent roles are exactly chief_of_staff/cfo/cmo/cpo", () => {
    expect([...PERSISTENT_EXECUTIVE_ROLES].sort()).toEqual(["cfo", "chief_of_staff", "cmo", "cpo"]);
  });
});
```

- [ ] **Step 10: Chạy test, xác nhận pass (file mới, thuần function — không cần fail-first vì không có ambiguity về implementation)**

Run: `cd services/company && npx vitest run operations/tests/executive-board-stage-presets.service.test.ts`
Expected: PASS.

- [ ] **Step 11: Đổi nguồn dữ liệu của `getProjectExecutiveRoleStates` sang bảng Workspace**

Đọc `getProjectExecutiveRoleStates` hiện tại đầy đủ
(`grep -n "export async function getProjectExecutiveRoleStates" -A 40 services/company/operations/services/executive-role-activation.service.ts`)
để biết chính xác đoạn code đang query `projectExecutiveRoleActivations` theo `(workspaceId, projectId, roleKey)`. Sửa đoạn đó: bỏ điều kiện lọc theo `projectId`, đổi sang gọi
`getWorkspaceExecutiveRoleStates(ctx)` (Task 9 Step 6) làm nguồn activation
duy nhất, giữ nguyên shape trả về `ProjectExecutiveBoardState` (field
`settings` — vốn phản ánh preset đã chọn — trả `undefined` luôn từ nay vì
preset bị loại bỏ ở Task 10):

```typescript
export async function getProjectExecutiveRoleStates(
  ctx: TenantContext,
  projectId: string
): Promise<ProjectExecutiveBoardState> {
  await requireExecutiveBoardFounderAuthority(ctx, projectId); // giữ nguyên check Project tồn tại + thuộc đúng workspace
  const workspaceBoard = await getWorkspaceExecutiveRoleStates(ctx);

  return {
    projectId,
    settings: undefined,
    roles: workspaceBoard.roles.map((r) => ({
      roleKey: r.roleKey,
      label: r.label,
      advisoryRemit: r.advisoryRemit,
      displayState: r.displayState,
      runtimeReadiness: r.runtimeReadiness,
      requiredProfileKey: r.requiredProfileKey,
      version: r.version,
      activatedAt: r.activatedAt,
      actorId: r.actorId,
      disabledReason: r.disabledReason,
    })),
  };
}
```

Thêm `import { getWorkspaceExecutiveRoleStates } from "./workspace-executive-role-activation.service";` ở đầu file. Xoá code cũ query trực tiếp `projectExecutiveRoleActivations`/`projectExecutiveBoardSettings` trong hàm này (không xoá 2 bảng Drizzle export — Task 10 vẫn cần đọc chúng để migrate dữ liệu Flutter cũ nếu có).

- [ ] **Step 12: Chạy test hiện có của `executive-role-activation.service.ts` (nếu có), sửa fixture nếu fail**

Run: `find services/company/operations/tests -iname "*executive-role-activation*"`
Nếu có file, chạy `cd services/company && npx vitest run operations/tests/<tên file>` — sửa bất kỳ fixture nào đang gọi `activateExecutiveRole(ctx, projectId, roleKey, ...)` (project-scoped) sang `activateWorkspaceExecutiveRole(ctx, roleKey, ...)` (Task 9 Step 6) cho khớp nguồn dữ liệu mới, rồi chạy lại tới khi PASS.

- [ ] **Step 13: Viết `getStageSuggestion` — test trước**

`services/company/operations/tests/executive-role-activation-stage-suggestion.service.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember } from "../tests/_helpers";
import type { TenantContext } from "../../shared/types/tenant_context";
import { createProjectService } from "../services/project.service";
import { transitionProjectLifecycle } from "../services/project-lifecycle.service";
import { getStageSuggestion } from "../services/executive-role-activation.service";
import { activateWorkspaceExecutiveRole } from "../services/workspace-executive-role-activation.service";

function ctxFor(workspaceId: string, userId = "1"): TenantContext {
  return Object.freeze({
    workspaceId,
    userId,
    workforceMemberId: userId,
    membershipRole: "founder",
    permissions: [],
    correlationId: "test-stage-suggestion",
    platformUserId: null,
  }) as unknown as TenantContext;
}

describe("getStageSuggestion", () => {
  it("suggests P0 roles for a new project (defaults to P0_DISCOVERY)", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const project = await createProjectService(ctx, { title: "Stage Suggestion Test" });

    const suggestion = await getStageSuggestion(ctx, project.id);
    expect(suggestion.stage).toBe("P0_DISCOVERY");
    expect([...suggestion.toActivate].sort()).toEqual(["cfo", "chief_of_staff", "cmo", "cpo"]);
    expect(suggestion.toSuggestDeactivate).toEqual([]);
  });

  it("does not suggest deactivating a persistent role after moving to P2, and reflects the workspace-shared activation set immediately for a second project", async () => {
    const ws = await createTestWorkspaceWithMember();
    const ctx = ctxFor(ws.workspaceId, ws.userId);
    const projectA = await createProjectService(ctx, { title: "Stage Suggestion P2 Test A" });
    const projectB = await createProjectService(ctx, { title: "Stage Suggestion P2 Test B" });

    await activateWorkspaceExecutiveRole(ctx, "cmo", {});
    await activateWorkspaceExecutiveRole(ctx, "coo", {});
    await transitionProjectLifecycle(ctx, projectA.id, { toStage: "P1_PROBLEM_VALIDATION", expectedStageVersion: 0 });
    await transitionProjectLifecycle(ctx, projectA.id, { toStage: "P2_SOLUTION_VALIDATION", expectedStageVersion: 1 });

    const suggestionA = await getStageSuggestion(ctx, projectA.id);
    expect(suggestionA.stage).toBe("P2_SOLUTION_VALIDATION");
    expect(suggestionA.toSuggestDeactivate).toEqual([]); // cmo là persistent, coo đã có trong P2 preset — cả 2 không bị gợi ý deactivate
    expect(suggestionA.toActivate).toEqual(expect.arrayContaining(["vpe", "ciso", "gc", "cdo", "caio"]));

    // Project B vẫn ở P0 nhưng "thấy" coo đã ACTIVE (workspace-shared) dù coo
    // không nằm trong preset gợi ý P0 — không xuất hiện ở toActivate (đã
    // active rồi) và cũng không bị gợi ý deactivate (P0 không có rule
    // deactivate cho role ngoài preset persistent).
    const suggestionB = await getStageSuggestion(ctx, projectB.id);
    expect(suggestionB.stage).toBe("P0_DISCOVERY");
  });
});
```

- [ ] **Step 14: Chạy test, xác nhận fail**

Run: `cd services/company && npx vitest run operations/tests/executive-role-activation-stage-suggestion.service.test.ts`
Expected: FAIL — `getStageSuggestion is not a function`.

- [ ] **Step 15: Implement `getStageSuggestion` trong `executive-role-activation.service.ts`**

Thêm import: `import { roleKeysForStage, PERSISTENT_EXECUTIVE_ROLES } from "./executive-board-stage-presets";` và đảm bảo biến `projects` (từ `schema.projects`, đã destructure sẵn ở đầu file — kiểm tra dòng khai báo `const { ... } = schema;`) sẵn có.

```typescript
export interface StageSuggestion {
  stage: string;
  toActivate: ExecutiveRoleKey[];
  toSuggestDeactivate: ExecutiveRoleKey[];
}

/**
 * Tính diff gợi ý Executive Board theo stage hiện tại của Project — CHỈ gợi
 * ý, không tự activate/deactivate. Activation thật sự là hành động
 * Workspace-scoped (workspace-executive-role-activation.service.ts);
 * suggestion chỉ là "nên bật/nên xét tắt cho Project này" theo stage.
 */
export async function getStageSuggestion(
  ctx: TenantContext,
  projectId: string
): Promise<StageSuggestion> {
  const wsId = BigInt(ctx.workspaceId);
  const projId = BigInt(projectId);

  const [project] = await db
    .select({ lifecycleStage: projects.lifecycleStage })
    .from(projects)
    .where(and(eq(projects.id, projId), eq(projects.workspaceId, wsId)))
    .limit(1);

  if (!project) {
    throw APIError.notFound(`Project ${projectId} not found`);
  }

  const stage = project.lifecycleStage;
  const presetRoles = new Set(roleKeysForStage(stage));
  const persistent = new Set(PERSISTENT_EXECUTIVE_ROLES);

  const board = await getProjectExecutiveRoleStates(ctx, projectId);

  const toActivate: ExecutiveRoleKey[] = [];
  const toSuggestDeactivate: ExecutiveRoleKey[] = [];

  for (const role of board.roles) {
    const inPreset = presetRoles.has(role.roleKey);
    const isActive = role.displayState === "ACTIVE";

    if (inPreset && !isActive && role.displayState === "AVAILABLE_NOT_ACTIVATED") {
      toActivate.push(role.roleKey);
    }
    if (!inPreset && isActive && !persistent.has(role.roleKey)) {
      toSuggestDeactivate.push(role.roleKey);
    }
  }

  return { stage, toActivate, toSuggestDeactivate };
}
```

- [ ] **Step 16: Chạy lại test, xác nhận pass**

Run: `cd services/company && npx vitest run operations/tests/executive-role-activation-stage-suggestion.service.test.ts operations/tests/executive-board-stage-presets.service.test.ts operations/tests/workspace-executive-role-activation.service.test.ts`
Expected: PASS toàn bộ.

- [ ] **Step 17: Thêm endpoint Workspace-scoped activate/disable + stage-suggestion; deprecate 3 endpoint Project-scoped cũ**

Trong `services/company/operations/handlers/executive-role-activation.handler.ts`:

1. Thêm import `getWorkspaceExecutiveRoleStates, activateWorkspaceExecutiveRole, disableWorkspaceExecutiveRole` từ `../services/workspace-executive-role-activation.service`, và `getStageSuggestion, StageSuggestion` từ `../services/executive-role-activation.service`.
2. Thêm 2 endpoint mới:

```typescript
interface ActivateWorkspaceExecutiveRoleParams {
  authorization?: Header<"Authorization">;
  workspaceId: string;
  roleKey: string;
  expectedVersion?: number;
  idempotencyKey?: string;
}

export const activateWorkspaceExecutiveRoleApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/workspaces/:workspaceId/executive-roles/:roleKey/activate",
  },
  async (
    params: ActivateWorkspaceExecutiveRoleParams
  ): Promise<{ id: string; roleKey: string; state: string; version: number }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return await activateWorkspaceExecutiveRole(ctx, params.roleKey, {
      expectedVersion: params.expectedVersion,
      idempotencyKey: params.idempotencyKey,
    });
  }
);

interface DisableWorkspaceExecutiveRoleParams {
  authorization?: Header<"Authorization">;
  workspaceId: string;
  roleKey: string;
  expectedVersion?: number;
  reason?: string;
  idempotencyKey?: string;
}

export const disableWorkspaceExecutiveRoleApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/workspaces/:workspaceId/executive-roles/:roleKey/disable",
  },
  async (
    params: DisableWorkspaceExecutiveRoleParams
  ): Promise<{ id: string; roleKey: string; state: string; version: number }> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return await disableWorkspaceExecutiveRole(ctx, params.roleKey, {
      expectedVersion: params.expectedVersion,
      reason: params.reason,
      idempotencyKey: params.idempotencyKey,
    });
  }
);

export const getProjectExecutiveStageSuggestionApi = api(
  {
    expose: true,
    method: "GET",
    path: "/operations/projects/:projectId/executive-board/stage-suggestion",
  },
  async (params: ListProjectExecutiveRolesParams): Promise<StageSuggestion> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return await getStageSuggestion(ctx, params.projectId);
  }
);
```

3. Sửa `selectProjectExecutivePresetApi`, `activateProjectExecutiveRoleApi`, `disableProjectExecutiveRoleApi` (3 endpoint Project-scoped cũ) — thay toàn bộ thân hàm bằng lỗi hướng dẫn rõ ràng, KHÔNG xoá endpoint (tránh 404 đột ngột cho client cũ chưa kịp cập nhật, dù Task 10 sẽ cập nhật Flutter ngay trong đợt này):

```typescript
export const activateProjectExecutiveRoleApi = api(
  {
    expose: true,
    method: "POST",
    path: "/operations/projects/:projectId/executive-roles/:roleKey/activate",
  },
  async (): Promise<never> => {
    throw APIError.invalidArgument(
      "This endpoint is deprecated. Executive Board activation is now workspace-scoped — use POST /operations/workspaces/:workspaceId/executive-roles/:roleKey/activate instead."
    );
  }
);
```

(áp dụng cùng pattern cho `disableProjectExecutiveRoleApi` và `selectProjectExecutivePresetApi`, đổi câu message cho khớp từng hành động — đọc lại chữ ký tham số gốc của mỗi hàm trước khi xoá thân hàm cũ để giữ đúng type params, chỉ đổi phần return/throw). Thêm `import { APIError } from "encore.dev/api";` nếu handler chưa import.

- [ ] **Step 18: Contract entries**

Thêm 3 entry mới vào `shared/contracts/mvp-surface.json` (activate/disable Workspace-scoped + stage-suggestion — copy shape entry `operations.task.delete` đã thêm ở Task 2 Step 7):

```json
{
  "id": "operations.executive_board.workspace_role.activate",
  "enabled": true,
  "owner": "company-operations",
  "plane": "company",
  "method": "POST",
  "path": "/operations/workspaces/:workspaceId/executive-roles/:roleKey/activate",
  "schema": "operations.executive_board.workspace_role.activate.v1",
  "source_kind": "company_db",
  "requires_workspace": true,
  "requires_project": false,
  "frontend_symbol": "ExecutiveAdvisoryBoardService.activateRole"
},
{
  "id": "operations.executive_board.workspace_role.disable",
  "enabled": true,
  "owner": "company-operations",
  "plane": "company",
  "method": "POST",
  "path": "/operations/workspaces/:workspaceId/executive-roles/:roleKey/disable",
  "schema": "operations.executive_board.workspace_role.disable.v1",
  "source_kind": "company_db",
  "requires_workspace": true,
  "requires_project": false,
  "frontend_symbol": "ExecutiveAdvisoryBoardService.disableRole"
},
{
  "id": "operations.executive_board.stage_suggestion",
  "enabled": true,
  "owner": "company-operations",
  "plane": "company",
  "method": "GET",
  "path": "/operations/projects/:projectId/executive-board/stage-suggestion",
  "schema": "operations.executive_board.stage_suggestion.v1",
  "source_kind": "company_db",
  "requires_workspace": true,
  "requires_project": true,
  "frontend_symbol": "ExecutiveBoardStageSuggestionService.get"
}
```

Tìm 3 entry cũ `project.executive_roles.select_preset`/`.activate`/`.disable` trong cùng file, đổi `"enabled": true` thành `"enabled": false` (không xoá entry — endpoint vẫn tồn tại, chỉ không còn là đường dùng chính thức).

- [ ] **Step 19: Typecheck + verify + commit**

Run: `cd services/company && npm run typecheck && cd .. && cd .. && make company-boundary-check && make encore-handler-boundary-check`
Expected: PASS.

```bash
git add services/company/operations/migrations/025_workspace_executive_role_activations.up.sql \
        services/company/operations/migrations/025_workspace_executive_role_activations.down.sql \
        services/company/shared/db/schema/operations.ts \
        services/company/operations/services/executive-board-stage-presets.ts \
        services/company/operations/services/workspace-executive-role-activation.service.ts \
        services/company/operations/services/executive-role-activation.service.ts \
        services/company/operations/handlers/executive-role-activation.handler.ts \
        services/company/operations/tests/workspace-executive-role-activation.service.test.ts \
        services/company/operations/tests/executive-board-stage-presets.service.test.ts \
        services/company/operations/tests/executive-role-activation-stage-suggestion.service.test.ts \
        shared/contracts/mvp-surface.json
git commit -m "feat(operations): Executive Board activation moves to Workspace scope (all 13 roles) + P0-P6 stage-suggestion"
```

---

### Task 10: Frontend — chuyển `ExecutiveAdvisoryBoardService`/Controller sang endpoint Workspace-scoped, bỏ preset UI

**Files:**
- Modify: `frontend/lib/modules/hologram_hub/services/executive_advisory_board_service.dart`
- Modify: `frontend/lib/modules/hologram_hub/controllers/executive_advisory_board_controller.dart`
- Modify: `frontend/lib/core/network/mvp_endpoints.g.dart` (regenerate, không hand-edit)
- Modify: `shared/contracts/mvp-surface.json` (đã sửa `enabled: false` 3 entry cũ ở Task 9 Step 18 — dùng chung, không sửa lại)
- Test: `frontend/test/modules/hologram_hub/services/executive_advisory_board_service_test.dart`, `frontend/test/modules/hologram_hub/controllers/executive_advisory_board_controller_reload_test.dart` (file có sẵn — cập nhật, không tạo mới)

**Interfaces:**
- Consumes: 2 entry `mvp-surface.json` mới từ Task 9 Step 18 (`operations.executive_board.workspace_role.activate`/`.disable`) — sau khi chạy generator sẽ có `MvpEndpoint.workspaceExecutiveRolesActivate`/`.workspaceExecutiveRolesDisable` (tên chính xác do generator đặt, xác nhận ở Step 2 dưới đây, không đoán).
- Produces: `ExecutiveAdvisoryBoardService.activateRole({required String workspaceId, required String roleKey, required int expectedVersion, String? idempotencyKey})`, `.disableRole({...tương tự})` — đổi tham số đầu vào từ `projectId` sang `workspaceId`; `fetchRoles(projectId)` giữ nguyên (vẫn cần `projectId` để gọi `GET /operations/projects/:projectId/executive-roles`, response shape không đổi); `selectPreset` bị XOÁ khỏi service (không còn preset).

- [ ] **Step 1: Đọc file generator cho `mvp_endpoints.g.dart`**

Run: `grep -n "mvp-surface\|mvp_endpoints" scripts/gen-mvp-contracts.mjs | head -20`
Mục đích: xác nhận cách generator đặt tên field enum Dart từ `id` trong contract JSON (vd `operations.executive_board.workspace_role.activate` → tên field nào) trước khi chạy — không đoán tên.

- [ ] **Step 2: Chạy generator**

Run: `node scripts/gen-mvp-contracts.mjs`
Expected: `frontend/lib/core/network/mvp_endpoints.g.dart` được ghi đè, xuất hiện 2 field mới tương ứng 2 entry Task 9 Step 18 (tên chính xác lấy từ diff, dùng cho Step 4 dưới đây), và field ứng với 3 entry cũ (`projectExecutiveRolesSelectPreset`/`.Activate`/`.Disable`) vẫn còn (generator không tự xoá vì `enabled: false` khác `xoá entry`) — xác nhận bằng `git diff frontend/lib/core/network/mvp_endpoints.g.dart`.

- [ ] **Step 3: Viết test thất bại trước cho `activateRole` dùng `workspaceId`**

Mở `frontend/test/modules/hologram_hub/services/executive_advisory_board_service_test.dart` hiện có, đọc case test `activateRole` đang dùng `projectId`, sửa thành:

```dart
    // Sửa lại case activateRole hiện có: tham số đổi từ projectId sang
    // workspaceId, path params đổi tương ứng — giữ nguyên phần mock response.
    test('activateRole calls workspace-scoped endpoint', () async {
      final result = await service.activateRole(
        workspaceId: 'ws1',
        roleKey: 'cfo',
        expectedVersion: 1,
      );
      // assertion cụ thể theo pattern mock MvpRequestClient đã có sẵn trong
      // file test này — copy đúng cách mock request/verify pathParams hiện
      // tại, chỉ đổi key 'projectId' thành 'workspaceId' trong pathParams kỳ vọng.
    });
```

Điều chỉnh nội dung test theo đúng cấu trúc mock thật của file (đọc toàn bộ file trước khi sửa — không viết đè nếu cấu trúc khác giả định ở đây).

- [ ] **Step 4: Chạy test, xác nhận fail**

Run: `cd frontend && flutter test test/modules/hologram_hub/services/executive_advisory_board_service_test.dart`
Expected: FAIL.

- [ ] **Step 5: Sửa `ExecutiveAdvisoryBoardService`**

Xoá method `selectPreset` hoàn toàn. Sửa `activateRole`/`disableRole`:

```dart
  /// Kích hoạt một vai trò cố vấn (Founder-only) — Workspace-scoped, ảnh
  /// hưởng tới mọi Project trong cùng workspace (xem design doc mục 6).
  Future<ApiResult<ExecutiveRoleMutationReceipt>> activateRole({
    required String workspaceId,
    required String roleKey,
    required int expectedVersion,
    String? idempotencyKey,
  }) async {
    return _client.request<ExecutiveRoleMutationReceipt>(
      MvpEndpoint.workspaceExecutiveRolesActivate, // tên chính xác xác nhận ở Step 1-2
      pathParams: {
        'workspaceId': workspaceId,
        'roleKey': roleKey,
      },
      body: {
        'expectedVersion': expectedVersion,
        'idempotencyKey': ?idempotencyKey,
      },
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          return ExecutiveRoleMutationReceipt.fromJson(raw);
        }
        throw const FormatException('Invalid response format for activate executive role');
      },
    );
  }

  Future<ApiResult<ExecutiveRoleMutationReceipt>> disableRole({
    required String workspaceId,
    required String roleKey,
    required int expectedVersion,
    String? reason,
    String? idempotencyKey,
  }) async {
    return _client.request<ExecutiveRoleMutationReceipt>(
      MvpEndpoint.workspaceExecutiveRolesDisable,
      pathParams: {
        'workspaceId': workspaceId,
        'roleKey': roleKey,
      },
      body: {
        'expectedVersion': expectedVersion,
        'reason': ?reason,
        'idempotencyKey': ?idempotencyKey,
      },
      decode: (raw) {
        if (raw is Map<String, dynamic>) {
          return ExecutiveRoleMutationReceipt.fromJson(raw);
        }
        throw const FormatException('Invalid response format for disable executive role');
      },
    );
  }
```

- [ ] **Step 6: Chạy lại test, xác nhận pass**

Run: `cd frontend && flutter test test/modules/hologram_hub/services/executive_advisory_board_service_test.dart`
Expected: PASS.

- [ ] **Step 7: Sửa `ExecutiveAdvisoryBoardController`**

Xoá `selectStartupPreset` + field `selectedPreset` (không còn preset). Sửa `activateRole`/`disableRole` để nhận `workspaceId` thay vì lấy lại `currentProjectId` cho tham số activation — controller cần thêm field `String? currentWorkspaceId` (set ở `loadBoard` hoặc truyền riêng từ nơi gọi, tuỳ cách widget View hiện tại đang biết `workspaceId` — đọc View đang dùng controller này, tìm bằng `grep -rln "ExecutiveAdvisoryBoardController" frontend/lib/modules/hologram_hub/views/` trước khi quyết định điền `workspaceId` từ đâu, không đoán):

```dart
  Future<bool> activateRole({
    required String workspaceId,
    required String roleKey,
    required int expectedVersion,
    String? idempotencyKey,
  }) async {
    isMutating.value = true;
    errorMessage.value = null;

    final result = await _service.activateRole(
      workspaceId: workspaceId,
      roleKey: roleKey,
      expectedVersion: expectedVersion,
      idempotencyKey: idempotencyKey,
    );
    isMutating.value = false;

    if (result.isSuccess && result.dataOrNull != null) {
      if (currentProjectId != null) await loadBoard(currentProjectId!);
      return true;
    } else {
      errorMessage.value = result.failureOrNull?.message ?? 'Không thể kích hoạt vai trò';
      return false;
    }
  }
```

(áp dụng tương tự cho `disableRole`). Cập nhật lại `frontend/test/modules/hologram_hub/controllers/executive_advisory_board_controller_reload_test.dart` cho khớp chữ ký mới — đọc file, sửa từng call site `activateRole(projectId: ...)`/`disableRole(projectId: ...)` thành `workspaceId: ...`.

- [ ] **Step 8: Chạy lại toàn bộ test hologram_hub liên quan**

Run: `cd frontend && flutter test test/modules/hologram_hub/services/executive_advisory_board_service_test.dart test/modules/hologram_hub/controllers/executive_advisory_board_controller_reload_test.dart`
Expected: PASS.

- [ ] **Step 9: Tìm và sửa View đang gọi `selectStartupPreset`/truyền `projectId` vào `activateRole`/`disableRole`**

Run: `grep -rn "selectStartupPreset\|controller.activateRole\|controller.disableRole" frontend/lib/modules/hologram_hub/views/`
Với mỗi call site: xoá UI chọn preset (nút/dropdown liên quan `selectStartupPreset`) nếu có, và sửa lời gọi `activateRole`/`disableRole` truyền đúng `workspaceId` (lấy từ service/controller workspace hiện tại của app, tìm bằng cách xem các widget khác trong cùng file đang lấy `workspaceId` từ đâu — không hardcode).

- [ ] **Step 10: `flutter analyze` + test toàn module hologram_hub**

Run: `make frontend-analyze && cd frontend && flutter test test/modules/hologram_hub/`
Expected: PASS.

- [ ] **Step 11: Commit**

```bash
git add frontend/lib/modules/hologram_hub/services/executive_advisory_board_service.dart \
        frontend/lib/modules/hologram_hub/controllers/executive_advisory_board_controller.dart \
        frontend/lib/core/network/mvp_endpoints.g.dart \
        frontend/test/modules/hologram_hub/services/executive_advisory_board_service_test.dart \
        frontend/test/modules/hologram_hub/controllers/executive_advisory_board_controller_reload_test.dart
git add -u
git commit -m "fix(hologram_hub): migrate Executive Advisory Board activation to workspace-scoped endpoints, drop preset selection"
```

---

### Task 11: Frontend — dialog gợi ý Executive Board sau khi chuyển Project stage

**Files:**
- Create: `frontend/lib/modules/projects/services/executive_board_stage_suggestion_service.dart`
- Create: `frontend/lib/modules/projects/widgets/executive_board_stage_suggestion_dialog.dart`

**Interfaces:**
- Consumes: `ApiClient.get`, `ApiClient.post` (đã xác nhận tồn tại ở Task 4/6); endpoint Task 9 `GET /operations/projects/:projectId/executive-board/stage-suggestion`; endpoint activation Workspace-scoped Task 9 `POST /operations/workspaces/:workspaceId/executive-roles/:roleKey/activate`.
- Produces: `ExecutiveBoardStageSuggestionService.getSuggestion(projectId) -> Future<Map<String, dynamic>>`, `.activateRole(workspaceId, roleKey) -> Future<void>`; `showExecutiveBoardStageSuggestionDialog(BuildContext, {required String projectId, required String workspaceId}) -> Future<void>` — gọi từ widget lifecycle của Task 13 sau khi transition project thành công.

- [ ] **Step 1: Viết service**

```dart
import 'dart:convert';
import '../../../core/network/api_client.dart';
import '../../../core/network/workspace_scoped_service.dart';

class ExecutiveBoardStageSuggestionService extends WorkspaceService {
  Future<Map<String, dynamic>> getSuggestion(String projectId) async {
    final response = await ApiClient.get('/operations/projects/$projectId/executive-board/stage-suggestion');
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    }
    throw StateError('Failed to load stage suggestion: ${response.statusCode} ${response.body}');
  }

  /// Kích hoạt role — Workspace-scoped (Task 9), ảnh hưởng mọi Project cùng workspace.
  Future<void> activateRole(String workspaceId, String roleKey) async {
    final response = await ApiClient.post(
      '/operations/workspaces/$workspaceId/executive-roles/$roleKey/activate',
      body: const {},
    );
    if (response.statusCode != 200) {
      throw StateError('Failed to activate $roleKey: ${response.statusCode} ${response.body}');
    }
  }
}
```

- [ ] **Step 2: Viết dialog**

```dart
import 'package:flutter/material.dart';
import '../services/executive_board_stage_suggestion_service.dart';

/// Sau khi founder xác nhận chuyển Project lifecycle stage, hỏi có muốn
/// kích hoạt role Executive Board gợi ý cho stage mới không. Founder bấm
/// từng role muốn kích hoạt — KHÔNG có hành động "activate all" tự động,
/// đúng nguyên tắc CLAUDE.md "không tự động".
Future<void> showExecutiveBoardStageSuggestionDialog(
  BuildContext context, {
  required String projectId,
  required String workspaceId,
}) async {
  final service = ExecutiveBoardStageSuggestionService();
  Map<String, dynamic>? suggestion;
  try {
    suggestion = await service.getSuggestion(projectId);
  } catch (_) {
    return; // Không chặn luồng chuyển stage nếu suggestion tạm thời lỗi.
  }

  final toActivate = (suggestion['toActivate'] as List<dynamic>? ?? []).cast<String>();
  final toSuggestDeactivate = (suggestion['toSuggestDeactivate'] as List<dynamic>? ?? []).cast<String>();

  if (toActivate.isEmpty && toSuggestDeactivate.isEmpty) return;
  if (!context.mounted) return;

  final activated = <String>{};

  await showDialog<void>(
    context: context,
    builder: (dialogContext) => StatefulBuilder(
      builder: (dialogContext, setState) => AlertDialog(
        title: Text('Gợi ý Executive Board cho ${suggestion!['stage']}'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (toActivate.isNotEmpty) ...[
                const Text('Nên kích hoạt:', style: TextStyle(fontWeight: FontWeight.bold)),
                ...toActivate.map(
                  (role) => CheckboxListTile(
                    title: Text(role),
                    value: activated.contains(role),
                    onChanged: (checked) => setState(() {
                      if (checked == true) {
                        activated.add(role);
                      } else {
                        activated.remove(role);
                      }
                    }),
                  ),
                ),
              ],
              if (toSuggestDeactivate.isNotEmpty) ...[
                const SizedBox(height: 8),
                const Text('Có thể tắt (founder tự quyết ở màn Executive Board):', style: TextStyle(fontWeight: FontWeight.bold)),
                ...toSuggestDeactivate.map((role) => Text('- $role')),
              ],
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Bỏ qua'),
          ),
          ElevatedButton(
            onPressed: () async {
              for (final role in activated) {
                try {
                  await service.activateRole(workspaceId, role);
                } catch (_) {
                  // Bỏ qua lỗi từng role riêng lẻ — không chặn các role còn lại.
                }
              }
              if (dialogContext.mounted) Navigator.of(dialogContext).pop();
            },
            child: const Text('Xác nhận kích hoạt đã chọn'),
          ),
        ],
      ),
    ),
  );
}
```

- [ ] **Step 3: `flutter analyze`**

Run: `make frontend-analyze`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/modules/projects/services/executive_board_stage_suggestion_service.dart \
        frontend/lib/modules/projects/widgets/executive_board_stage_suggestion_dialog.dart
git commit -m "feat(projects): stage-suggestion dialog for Executive Board activation after lifecycle transition"
```

*(Việc gọi `showExecutiveBoardStageSuggestionDialog` được nối dây ở Task 13, ngay sau khi Project lifecycle transition thành công — cùng chỗ với widget `LifecycleSettingsSection` cho Project.)*

---

### Task 12: Frontend — Lifecycle service dùng chung (Workspace + Project)

**Files:**
- Create: `frontend/lib/core/lifecycle/lifecycle_service.dart`
- Test: `frontend/test/core/lifecycle/lifecycle_service_test.dart`

**Interfaces:**
- Produces: `enum LifecycleEntityType { workspace, project }`; `class LifecycleService` với `getState(LifecycleEntityType, String entityId) -> Future<Map<String, dynamic>>`, `transition(LifecycleEntityType, String entityId, {required String toStage, required int expectedStageVersion, String? rationale}) -> Future<Map<String, dynamic>>`, `getHistory(LifecycleEntityType, String entityId) -> Future<List<Map<String, dynamic>>>`. Dùng bởi Task 13.

- [ ] **Step 1: Viết test cho path resolution theo entity type**

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:javis_saas/core/lifecycle/lifecycle_service.dart';

void main() {
  test('workspace lifecycle path uses /identity/workspaces/:id/lifecycle', () {
    expect(
      LifecycleService.pathFor(LifecycleEntityType.workspace, 'ws1'),
      '/identity/workspaces/ws1/lifecycle',
    );
  });

  test('project lifecycle path uses /operations/projects/:id/lifecycle', () {
    expect(
      LifecycleService.pathFor(LifecycleEntityType.project, 'p1'),
      '/operations/projects/p1/lifecycle',
    );
  });
}
```

(sửa `package:javis_saas/...` theo tên package thật — xem Task 4 Step 3.)

- [ ] **Step 2: Chạy test, xác nhận fail**

Run: `cd frontend && flutter test test/core/lifecycle/lifecycle_service_test.dart`
Expected: FAIL — file `lifecycle_service.dart` chưa tồn tại.

- [ ] **Step 3: Implement**

```dart
import 'dart:convert';
import '../network/api_client.dart';
import '../network/workspace_scoped_service.dart';

enum LifecycleEntityType { workspace, project }

class LifecycleService extends WorkspaceService {
  static String pathFor(LifecycleEntityType type, String entityId) {
    switch (type) {
      case LifecycleEntityType.workspace:
        return '/identity/workspaces/$entityId/lifecycle';
      case LifecycleEntityType.project:
        return '/operations/projects/$entityId/lifecycle';
    }
  }

  Future<Map<String, dynamic>> getHistory(LifecycleEntityType type, String entityId) async {
    final response = await ApiClient.get('${pathFor(type, entityId)}/events');
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    }
    throw StateError('Failed to load lifecycle history: ${response.statusCode} ${response.body}');
  }

  Future<Map<String, dynamic>> transition(
    LifecycleEntityType type,
    String entityId, {
    required String toStage,
    required int expectedStageVersion,
    String? rationale,
  }) async {
    final response = await ApiClient.patch(
      pathFor(type, entityId),
      body: {
        'toStage': toStage,
        'expectedStageVersion': expectedStageVersion,
        if (rationale != null) 'rationale': rationale,
      },
    );
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    }
    throw StateError('Failed to transition lifecycle: ${response.statusCode} ${response.body}');
  }
}
```

Xác nhận `ApiClient.patch` tồn tại (`grep -n "static Future.*patch" frontend/lib/core/network/api_client.dart`) — nếu thiếu, thêm cùng pattern `post`/`delete` (Task 4 Step 2) trước khi build.

- [ ] **Step 4: Chạy lại test, xác nhận pass**

Run: `cd frontend && flutter test test/core/lifecycle/lifecycle_service_test.dart`
Expected: PASS.

- [ ] **Step 5: `flutter analyze` + commit**

Run: `make frontend-analyze`

```bash
git add frontend/lib/core/lifecycle/lifecycle_service.dart \
        frontend/lib/core/network/api_client.dart \
        frontend/test/core/lifecycle/lifecycle_service_test.dart
git commit -m "feat(core): shared LifecycleService for Workspace and Project stage transition/history"
```

---

### Task 13: Frontend — UI Lifecycle (Workspace Settings + Project Settings)

**Files:**
- Create: `frontend/lib/core/lifecycle/widgets/lifecycle_settings_section.dart`
- Modify: `frontend/lib/modules/settings/views/settings_view.dart` (chèn section cho Workspace)
- Modify: view Project Settings thật — xác định bằng `grep -rln "class.*ProjectSettings" frontend/lib/modules/` trước khi sửa (chèn section cho Project)

**Interfaces:**
- Consumes: `LifecycleService` (Task 12), `WorkspaceLifecycleStage`/`ProjectLifecycleStage` — danh sách stage cứng để hiển thị dropdown, copy đúng 6 giá trị Workspace (`W0_IDEA`..`W5_SCALE`, xem `workspace-lifecycle.service.ts:11-18`) và 7 giá trị Project (`P0_DISCOVERY`..`P6_SCALE_GOVERN`, xem `project-lifecycle.service.ts:13-21`) — không tự bịa danh sách khác.
- Produces: `LifecycleSettingsSection` widget nhận `entityType`, `entityId`, `currentStage`, `currentStageVersion`, optional `onTransitioned: void Function(String newStage)` (Task 11 dùng callback này để mở tiếp `showExecutiveBoardStageSuggestionDialog(context, projectId: entityId, workspaceId: <workspace hiện tại>)` khi `entityType == project` — `workspaceId` lấy từ cùng nguồn đang cấp `entityId` cho Workspace Settings, đọc file thật ở Step 3/4 để xác định biến chính xác, không hardcode).

- [ ] **Step 1: Viết widget `LifecycleSettingsSection`**

```dart
import 'package:flutter/material.dart';
import '../lifecycle_service.dart';

const _workspaceStages = [
  'W0_IDEA',
  'W1_PROBLEM_VALIDATION',
  'W2_SOLUTION_VALIDATION',
  'W3_MVP_BUILD',
  'W4_PRODUCT_MARKET_FIT',
  'W5_SCALE',
];

const _projectStages = [
  'P0_DISCOVERY',
  'P1_PROBLEM_VALIDATION',
  'P2_SOLUTION_VALIDATION',
  'P3_BUILD_VALIDATE',
  'P4_GO_TO_MARKET',
  'P5_OPERATE_GROWTH',
  'P6_SCALE_GOVERN',
];

class LifecycleSettingsSection extends StatefulWidget {
  const LifecycleSettingsSection({
    super.key,
    required this.entityType,
    required this.entityId,
    required this.currentStage,
    required this.currentStageVersion,
    this.onTransitioned,
  });

  final LifecycleEntityType entityType;
  final String entityId;
  final String currentStage;
  final int currentStageVersion;
  final void Function(String newStage)? onTransitioned;

  @override
  State<LifecycleSettingsSection> createState() => _LifecycleSettingsSectionState();
}

class _LifecycleSettingsSectionState extends State<LifecycleSettingsSection> {
  final _service = LifecycleService();
  bool _busy = false;

  List<String> get _stages =>
      widget.entityType == LifecycleEntityType.workspace ? _workspaceStages : _projectStages;

  Future<void> _transitionTo(String toStage) async {
    final isBackward = _stages.indexOf(toStage) < _stages.indexOf(widget.currentStage);
    String? rationale;
    if (isBackward) {
      rationale = await showDialog<String>(
        context: context,
        builder: (dialogContext) {
          final controller = TextEditingController();
          return AlertDialog(
            title: const Text('Lý do lùi giai đoạn'),
            content: TextField(controller: controller, autofocus: true, maxLines: 3),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(dialogContext).pop(),
                child: const Text('Huỷ'),
              ),
              ElevatedButton(
                onPressed: () => Navigator.of(dialogContext).pop(controller.text.trim()),
                child: const Text('Xác nhận'),
              ),
            ],
          );
        },
      );
      if (rationale == null || rationale.isEmpty) return;
    }

    setState(() => _busy = true);
    try {
      await _service.transition(
        widget.entityType,
        widget.entityId,
        toStage: toStage,
        expectedStageVersion: widget.currentStageVersion,
        rationale: rationale,
      );
      widget.onTransitioned?.call(toStage);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Không chuyển được giai đoạn: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final currentIndex = _stages.indexOf(widget.currentStage);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Giai đoạn hiện tại: ${widget.currentStage}', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              children: [
                if (currentIndex >= 0 && currentIndex < _stages.length - 1)
                  ElevatedButton(
                    onPressed: _busy ? null : () => _transitionTo(_stages[currentIndex + 1]),
                    child: Text('Tiến sang ${_stages[currentIndex + 1]}'),
                  ),
                if (currentIndex > 0)
                  OutlinedButton(
                    onPressed: _busy ? null : () => _showBackwardMenu(context, currentIndex),
                    child: const Text('Lùi giai đoạn'),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _showBackwardMenu(BuildContext context, int currentIndex) async {
    final target = await showMenu<String>(
      context: context,
      position: const RelativeRect.fromLTRB(0, 0, 0, 0),
      items: [
        for (var i = 0; i < currentIndex; i++)
          PopupMenuItem(value: _stages[i], child: Text(_stages[i])),
      ],
    );
    if (target != null) await _transitionTo(target);
  }
}
```

- [ ] **Step 2: `flutter analyze`**

Run: `make frontend-analyze`
Expected: PASS (widget mới, chưa gắn vào view nào — không có test bắt buộc riêng cho widget UI thuần tuý theo convention hiện có của repo, xác nhận bằng `ls frontend/test/core/` xem có thư mục test widget UI khác theo pattern golden/widget test không; nếu có, thêm 1 widget test đơn giản kiểm tra render đúng `currentStage`).

- [ ] **Step 3: Chèn vào Workspace Settings**

Đọc `frontend/lib/modules/settings/views/settings_view.dart` để tìm cấu trúc danh sách section hiện có (ListView/Column các Card), thêm:

```dart
LifecycleSettingsSection(
  entityType: LifecycleEntityType.workspace,
  entityId: /* lấy từ controller/service workspace hiện tại — đọc file để xác định biến đúng */,
  currentStage: /* tương tự */,
  currentStageVersion: /* tương tự */,
),
```

Giá trị `entityId`/`currentStage`/`currentStageVersion` phải lấy từ state Workspace thật đang có trong `settings_view.dart` hoặc controller liên kết — đọc file trước khi điền, không hardcode giá trị giả.

- [ ] **Step 4: Chèn vào Project Settings**

Tương tự Step 3 nhưng ở view Project Settings (xác định đường dẫn bằng grep đã nêu ở đầu Task), truyền thêm `onTransitioned: (newStage) => showExecutiveBoardStageSuggestionDialog(context, projectId: entityId, workspaceId: <biến workspaceId hiện tại đọc được ở Step 3>)` (import từ Task 11) — chỉ Project Settings mới cần callback này, Workspace Settings không truyền `onTransitioned`.

- [ ] **Step 5: `flutter analyze` + test toàn bộ 2 module đã sửa**

Run: `make frontend-analyze && cd frontend && flutter test test/modules/settings/ test/modules/projects/`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/core/lifecycle/widgets/lifecycle_settings_section.dart \
        frontend/lib/modules/settings/views/settings_view.dart
git add -u
git commit -m "feat(settings): Lifecycle transition + history UI for Workspace and Project"
```

---

### Task 14: Dọn dẹp dead code khác

**Files:**
- Delete: `frontend/lib/modules/settings/workforce/views/profile_composition_view.dart`
- Delete: `frontend/lib/modules/organization/services/business_pack_service.dart`

**Interfaces:** không có — dọn dẹp thuần tuý.

- [ ] **Step 1: Xác nhận lại 0 reference cho `profile_composition_view.dart`**

Run: `grep -rln "profile_composition_view\|ProfileCompositionView" frontend/lib/ frontend/test/`
Expected: chỉ chính file đó. Nếu có reference khác, DỪNG, không xoá.

- [ ] **Step 2: Xác nhận lại 0 reference cho `business_pack_service.dart`**

Run: `grep -rln "business_pack_service\|BusinessPackService" frontend/lib/ frontend/test/`
Expected: chỉ chính file đó.

- [ ] **Step 3: Xoá cả hai**

```bash
git rm frontend/lib/modules/settings/workforce/views/profile_composition_view.dart
git rm frontend/lib/modules/organization/services/business_pack_service.dart
```

- [ ] **Step 4: `flutter analyze` xác nhận không còn import treo**

Run: `make frontend-analyze`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git commit -m "chore(frontend): remove orphan profile_composition_view and business_pack_service (0 backend, 0 reference)"
```

---

### Task 15: Verify toàn diện

**Files:** không tạo/sửa — chỉ chạy gate.

- [ ] **Step 1: Company typecheck + boundary**

Run: `cd services/company && npm run typecheck`
Run: `make company-boundary-check && make encore-handler-boundary-check && make ts-suppression-check`
Expected: tất cả PASS.

- [ ] **Step 2: Company service test**

Run: `make services-test-company`
Expected: PASS, bao gồm toàn bộ test mới ở Task 2/3/5/9.

- [ ] **Step 3: Contract checks**

Run: `make frontend-api-contract-check && make contract-freeze-check`
Expected: PASS — 3 route mới (Task 2, 5, 9) đã đăng ký trong `mvp-surface.json`.

- [ ] **Step 4: Python typecheck (do đụng file generated Python ở Task 10)**

Run: `make typecheck-py`
Expected: PASS, không phát sinh lỗi mới so với baseline đã biết trước khi bắt đầu plan này (nếu baseline đã có lỗi từ trước — xem báo cáo P0 mypy 33 lỗi/14 file trong phiên làm việc trước — xác nhận KHÔNG tăng thêm, không yêu cầu phải về 0 vì đó là phạm vi công việc khác).

- [ ] **Step 5: Frontend**

Run: `make frontend-analyze && make frontend-test`
Expected: PASS.

- [ ] **Step 6: Full verify**

Run: `make verify`
Expected: PASS toàn bộ gate liên quan tới phạm vi đã sửa (services/company, packages liên quan Python generated file, frontend). Nếu gate không liên quan tới plan này thất bại vì lý do đã biết từ trước (vd baseline mypy 33 lỗi ở file khác), ghi rõ trong báo cáo hoàn tất — không tự ý sửa ngoài phạm vi plan.

- [ ] **Step 7: Commit nếu Step 1-6 phát sinh thay đổi (vd lock file, generated snapshot)**

```bash
git status --short
# Nếu có thay đổi phát sinh từ verify (snapshot route-inventory, v.v.), review rồi:
git add -A
git commit -m "chore: regenerate contract/route-inventory snapshots after foundation work"
```

---

## Self-Review (đã chạy trước khi bàn giao)

**Spec coverage:** mục 1→Task 12-13, mục 2→Task 6, mục 3→Task 5+7, mục 4→Task 8, mục 5→Task 1-4, mục 6→Task 9-11 (đã viết lại 2026-09-14 sau khi founder chốt activation là Workspace-scoped cho cả 13 role, không chỉ 4 role duy trì — xem spec mục 6 bản cập nhật), mục 7→Task 14. Đủ 7/7 mục của spec.

**Placeholder scan:** đã rà lại — các chỗ ghi "đọc file trước khi sửa/xác nhận tên hàm thật" là chỉ dẫn thao tác cụ thể (grep command kèm theo), không phải "TBD" mơ hồ; giữ nguyên vì audit trước đó xác nhận một số tên hàm nội bộ (`createObjectiveService`, hàm tạo weeklyCommitment, `ApiClient.patch/delete`, tên field generator đặt cho `mvp_endpoints.g.dart`) chưa được đọc trực tiếp — yêu cầu xác nhận bằng lệnh cụ thể trước khi code là đúng tinh thần "không đoán", không phải placeholder.

**Type consistency:** `LifecycleEntityType` (Task 12) dùng nhất quán ở Task 13; `deleteTaskService`/`TaskService.deleteTask` (Task 2/4) cùng convention `{id, deletedAt}`; `StageSuggestion{stage, toActivate, toSuggestDeactivate}` (Task 9) dùng nhất quán ở Task 11 (`suggestion['toActivate']`/`suggestion['toSuggestDeactivate']`); `CycleDto.sourceObjectiveId` (Task 5) khớp cột `source_objective_id` (Task 1); `activateRole`/`disableRole` đổi tham số `projectId`→`workspaceId` nhất quán giữa Task 9 (backend endpoint), Task 10 (Flutter service/controller hiện có), và Task 11 (dialog mới) — cả 3 đều gọi cùng 1 endpoint `POST /operations/workspaces/:workspaceId/executive-roles/:roleKey/activate`.

**Đã xác minh thêm trong vòng review thiết kế 2026-09-14 (không suy đoán):** `project_executive_deliberations*` chỉ tham chiếu `roleKey` dạng chuỗi/jsonb, không có FK tới `project_executive_role_activations` — xác nhận việc chuyển activation lên Workspace không phá vỡ luồng Deliberation (giữ nguyên, không sửa trong plan này). Đã phát hiện `ExecutiveAdvisoryBoardService`/`ExecutiveAdvisoryBoardController` (hologram_hub) là code ĐANG CHẠY THẬT dựa trên endpoint Project-scoped cũ — bổ sung hẳn Task 10 để migrate thay vì bỏ sót.
