# Command Center Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign COSA's Command Center dashboard (`/hub`) per founder feedback: move the 4 pulse stats to the top of the page, turn "Hành động tuần đầu" into an editable checklist (time + done checkbox) inside the left column card, and narrow the right-column "Hàng đợi" card.

**Architecture:** Backend (`services/company`) exposes a new narrow endpoint to edit a task's `plannedStartAt` and enriches `ProjectOperatingSetupView.firstWeekActions` with the live `status`/`plannedStartAt`/`updatedAt` already sitting on the materialized `operating.tasks` row (no new DB columns). Frontend (Flutter/GetX) extracts a `PulseStatBarWidget`, adds a checklist section to `Top3FocusWidget`, and wires two new controller methods that call the existing status endpoint and the new schedule endpoint, then refresh `activeProjectSetup`.

**Tech Stack:** Encore.ts + Drizzle ORM (services/company), Flutter + GetX (frontend), Vitest (backend tests), `flutter test` (frontend tests).

## Global Constraints

- Design doc: `docs/superpowers/specs/2026-09-04-command-center-dashboard-redesign-design.md` — every task below implements one of its 3 sections.
- Mọi comment mới trong code phải bằng tiếng Việt cho phần giải thích "why"; định danh/route/log giữ tiếng Anh (CLAUDE.md §Comment code).
- Không dùng `any`, `@ts-ignore`, `@ts-expect-error` trong code TypeScript (Encore Guardrail #5).
- Lỗi từ public request dùng `APIError` tại boundary, không throw `Error` trần (Encore Guardrail #3).
- Handler (`operations/handlers/task.handler.ts`) không được import Drizzle/DB trực tiếp — mọi logic DB nằm trong `services/task.service.ts` (Encore Guardrail #1).
- Không tạo git worktree; code trực tiếp trên `main` tại root repo (CLAUDE.md §Quy tắc Git & Workspace).
- Route mới gọi từ `frontend/lib/**` phải có entry trong `scripts/frontend-api-contract-allowlist.json` (route không nằm trong `shared/contracts/mvp-surface.json`) — nếu không, `make frontend-api-contract-check` sẽ fail.
- Mỗi task kết thúc bằng test xanh trước khi sang task kế — không gộp nhiều fix chưa test.
- Sau task cuối, chạy `make verify`-scoped gates liệt kê ở Task 9 trước khi coi plan là hoàn tất.

---

### Task 1: Backend — endpoint `POST /operations/tasks/:id/schedule`

**Files:**
- Modify: `services/company/operations/services/task.service.ts` (thêm hàm cuối file, sau `updateTaskStatusService` dòng 221)
- Modify: `services/company/operations/handlers/task.handler.ts` (thêm import + endpoint mới sau `updateTaskStatus`, dòng 76)
- Test: `services/company/operations/tests/task.test.ts` (thêm `describe` block mới sau dòng 214, trước `describe("linkTaskProjects...`)

**Interfaces:**
- Produces: `updateTaskScheduleService(id: string, plannedStartAt: string | null, ctx: TenantContext): Promise<Task>` (trong `task.service.ts`) và endpoint Encore `updateTaskSchedule` (`POST /operations/tasks/:id/schedule`, params `{ id: string; plannedStartAt: string | null; workspaceId: Header<"X-Workspace-Id">; authorization?: Header<"Authorization"> }`, trả `Task`) — Task 2 và Task 9 (test) dùng lại tên hàm/route này y hệt.

- [ ] **Step 1: Viết test thất bại trong `task.test.ts`**

  Sửa dòng 4 (import) thành:

  ```ts
  import { createTask, getTask, listTasks, updateTaskStatus, updateTaskSchedule, linkTaskProjects_Endpoint, getTaskProjects, unlinkTaskProject_Endpoint } from "../handlers/task.handler";
  ```

  Chèn block sau vào giữa dòng 214 (`});` đóng `describe("updateTaskStatus"...`) và dòng 216 (`describe("linkTaskProjects...`):

  ```ts
  describe("updateTaskSchedule", () => {
    it("sets plannedStartAt from an ISO string", async () => {
      const { workspaceId, authorization } = await makeAuthedWorkspace("Schedule Test Inc");
      const created = await createTask({ workspaceId, title: "Interview lead", authorization });
      expect(created.plannedStartAt).toBeNull();

      const scheduled = await updateTaskSchedule({
        id: created.id,
        plannedStartAt: "2026-09-08T09:00:00.000Z",
        workspaceId,
        authorization,
      });

      expect(scheduled.plannedStartAt).toBe("2026-09-08T09:00:00.000Z");
    });

    it("clears plannedStartAt when null is passed", async () => {
      const { workspaceId, authorization } = await makeAuthedWorkspace("Schedule Clear Test Inc");
      const created = await createTask({ workspaceId, title: "Interview lead", authorization });
      await updateTaskSchedule({
        id: created.id,
        plannedStartAt: "2026-09-08T09:00:00.000Z",
        workspaceId,
        authorization,
      });

      const cleared = await updateTaskSchedule({
        id: created.id,
        plannedStartAt: null,
        workspaceId,
        authorization,
      });

      expect(cleared.plannedStartAt).toBeNull();
    });

    it("rejects an invalid (non-ISO) plannedStartAt string", async () => {
      const { workspaceId, authorization } = await makeAuthedWorkspace("Schedule Bad Date Test Inc");
      const created = await createTask({ workspaceId, title: "Interview lead", authorization });

      await expect(
        updateTaskSchedule({ id: created.id, plannedStartAt: "not-a-date", workspaceId, authorization })
      ).rejects.toThrow();
    });

    it("throws not found for a missing id", async () => {
      const { workspaceId, authorization } = await makeAuthedWorkspace("Missing Task Schedule Test");
      await expect(
        updateTaskSchedule({ id: "999999999", plannedStartAt: null, workspaceId, authorization })
      ).rejects.toThrow();
    });

    it("does not allow a workspace B member to schedule a task from workspace A (404, not 403)", async () => {
      const workspaceA = await makeAuthedWorkspace("Task Schedule Isolation Ws A");
      const workspaceB = await makeAuthedWorkspace("Task Schedule Isolation Ws B");
      const taskA = await createTask({
        workspaceId: workspaceA.workspaceId,
        title: "Task in A",
        authorization: workspaceA.authorization,
      });

      await expect(
        updateTaskSchedule({
          id: taskA.id,
          plannedStartAt: "2026-09-08T09:00:00.000Z",
          workspaceId: workspaceB.workspaceId,
          authorization: workspaceB.authorization,
        })
      ).rejects.toThrow(/not found/i);
    });
  });
  ```

- [ ] **Step 2: Chạy test, xác nhận thất bại (chưa có `updateTaskSchedule`)**

  Run: `cd services/company && npx vitest run operations/tests/task.test.ts`
  Expected: FAIL — `updateTaskSchedule is not a function` hoặc lỗi import tương tự.

- [ ] **Step 3: Implement `updateTaskScheduleService` trong `task.service.ts`**

  Thêm vào cuối file (sau `updateTaskStatusService`, dòng 221-222):

  ```ts
  export async function updateTaskScheduleService(
    id: string,
    plannedStartAt: string | null,
    ctx: TenantContext
  ): Promise<Task> {
    let parsedPlannedStartAt: Date | null = null;
    if (plannedStartAt !== null && plannedStartAt !== undefined) {
      parsedPlannedStartAt = new Date(plannedStartAt);
      if (Number.isNaN(parsedPlannedStartAt.getTime())) {
        throw APIError.invalidArgument("plannedStartAt phải là ISO date hợp lệ");
      }
    }

    const [row] = await db
      .update(tasks)
      .set({ plannedStartAt: parsedPlannedStartAt, updatedAt: new Date() })
      .where(and(eq(tasks.id, BigInt(id)), eq(tasks.workspaceId, BigInt(ctx.workspaceId))))
      .returning();

    if (!row) throw APIError.notFound(`task ${id} not found`);
    return toTask(row);
  }
  ```

- [ ] **Step 4: Implement endpoint trong `task.handler.ts`**

  Sửa import (dòng 2-11) thành:

  ```ts
  import {
    Task,
    TaskStatus,
    TASK_STATUSES,
    CreateTaskParams as BaseCreateTaskParams,
    createTaskService,
    getTaskService,
    listTasksService,
    updateTaskStatusService,
    updateTaskScheduleService,
  } from "../services/task.service";
  ```

  Chèn ngay sau khối `updateTaskStatus` (sau dòng 76, trước `export interface LinkProjectsParams`):

  ```ts
  export const updateTaskSchedule = api(
    { method: "POST", path: "/operations/tasks/:id/schedule", expose: true },
    async ({
      id,
      plannedStartAt,
      workspaceId,
      authorization,
    }: {
      id: string;
      plannedStartAt: string | null;
      workspaceId: Header<"X-Workspace-Id">;
      authorization?: Header<"Authorization">;
    }): Promise<Task> => {
      const ctx = await requireWorkspaceAccess(authorization, workspaceId);
      return updateTaskScheduleService(id, plannedStartAt, ctx);
    }
  );
  ```

- [ ] **Step 5: Chạy test, xác nhận pass**

  Run: `cd services/company && npx vitest run operations/tests/task.test.ts`
  Expected: PASS — tất cả test trong `task.test.ts`, bao gồm `describe("updateTaskSchedule"...)`.

- [ ] **Step 6: Typecheck + boundary gates**

  Run: `cd services/company && npm run typecheck`
  Run (từ root): `make encore-handler-boundary-check && make ts-suppression-check`
  Expected: cả 3 lệnh pass — không có DB access trong handler, không `@ts-ignore`.

- [ ] **Step 7: Commit**

  ```bash
  git add services/company/operations/services/task.service.ts services/company/operations/handlers/task.handler.ts services/company/operations/tests/task.test.ts
  git commit -m "feat(operations): add POST /operations/tasks/:id/schedule endpoint"
  ```

---

### Task 2: Backend — `ProjectOperatingSetupView.firstWeekActions` mang theo status/plannedStartAt/updatedAt

**Files:**
- Modify: `services/company/operations/strategy/services/project-operating-setup.service.ts`
- Test: `services/company/operations/tests/project-operating-setup-kickoff-materialize.test.ts`

**Interfaces:**
- Consumes: `updateTaskSchedule` (handler, Task 1), `Task` interface (`plannedStartAt`, `status`, `updatedAt` fields) từ `../../services/task.service`.
- Produces: `FirstWeekActionView { id, title, status: TaskStatus, plannedStartAt: string | null, updatedAt: string | null }`, `ProjectOperatingSetupView.firstWeekActions: FirstWeekActionView[]` — Task 3 (Dart model) parse đúng 3 field mới này.

- [ ] **Step 1: Viết test thất bại**

  Trong `project-operating-setup-kickoff-materialize.test.ts`, sửa import (dòng 5-8) thành:

  ```ts
  import {
    putProjectOperatingSetupEndpoint,
    activateProjectOperatingSetupEndpoint,
    getProjectOperatingSetupEndpoint,
  } from "../strategy/handlers/project-operating-setup.handler";
  import { updateTaskStatus, updateTaskSchedule } from "../handlers/task.handler";
  ```

  Thêm `describe` block mới ở cuối file (sau describe `"kickoff materialize round-trips ids without churn end-to-end"`):

  ```ts
  describe("firstWeekActions view includes live task status/schedule fields", () => {
    it("returns status/plannedStartAt/updatedAt per action, and reflects later updates", async () => {
      const ws = await createTestWorkspaceWithMember();
      const project = await createProject({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        title: "First week action view project",
      });

      const activated = await activateProjectOperatingSetupEndpoint({
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
        firstWeekActions: [{ title: "List prospects" }],
      });

      const action = activated.setup.firstWeekActions[0]!;
      expect(action.status).toBe("todo");
      expect(action.plannedStartAt).toBeNull();
      expect(action.updatedAt).not.toBeNull();

      await updateTaskStatus({
        id: action.id,
        status: "done",
        workspaceId: ws.workspaceId,
        authorization: ws.bearerToken,
      });
      await updateTaskSchedule({
        id: action.id,
        plannedStartAt: "2026-09-08T09:00:00.000Z",
        workspaceId: ws.workspaceId,
        authorization: ws.bearerToken,
      });

      const refreshed = await getProjectOperatingSetupEndpoint({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        id: project.id,
      });
      const refreshedAction = refreshed.firstWeekActions[0]!;
      expect(refreshedAction.status).toBe("done");
      expect(refreshedAction.plannedStartAt).toBe("2026-09-08T09:00:00.000Z");
    });
  });
  ```

- [ ] **Step 2: Chạy test, xác nhận thất bại**

  Run: `cd services/company && npx vitest run operations/tests/project-operating-setup-kickoff-materialize.test.ts`
  Expected: FAIL — `action.status`/`action.plannedStartAt` là `undefined` (kiểu `FirstWeekAction` hiện tại chỉ có `id`/`title`).

- [ ] **Step 3: Implement — mở rộng `toView()` trong `project-operating-setup.service.ts`**

  Sửa dòng 2 (import drizzle-orm):

  ```ts
  import { and, eq, inArray } from "drizzle-orm";
  ```

  Sửa dòng 5 (import schema) thành:

  ```ts
  import { projects, tasks } from "../../../shared/db/schema/operations";
  ```

  Thêm import type ngay dưới dòng 17 (`import { materializeFirstWeekPlan } from "./project-kickoff-materialize.service";`):

  ```ts
  import type { TaskStatus } from "../../services/task.service";
  ```

  Thêm interface mới ngay sau `FirstWeekAction` (dòng 29-32):

  ```ts
  export interface FirstWeekActionView extends FirstWeekAction {
    status: TaskStatus;
    plannedStartAt: string | null;
    updatedAt: string | null;
  }
  ```

  Sửa `ProjectOperatingSetupView.firstWeekActions` (dòng 49) từ `FirstWeekAction[]` thành `FirstWeekActionView[]`.

  Thêm type `Tx` và hàm `enrichFirstWeekActions` ngay trước `function toView(...)` (dòng 154):

  ```ts
  type Tx = Parameters<Parameters<typeof db.transaction>[0]>[0];

  async function enrichFirstWeekActions(
    actions: FirstWeekAction[],
    dbOrTx: typeof db | Tx,
    workspaceId: bigint
  ): Promise<FirstWeekActionView[]> {
    if (actions.length === 0) return [];

    const ids = actions.map((a) => BigInt(a.id));
    const rows = await dbOrTx
      .select({
        id: tasks.id,
        status: tasks.status,
        plannedStartAt: tasks.plannedStartAt,
        updatedAt: tasks.updatedAt,
      })
      .from(tasks)
      .where(and(eq(tasks.workspaceId, workspaceId), inArray(tasks.id, ids)));

    const byId = new Map(rows.map((r) => [r.id.toString(), r]));

    return actions.map((a) => {
      const t = byId.get(a.id);
      return {
        id: a.id,
        title: a.title,
        status: (t?.status as TaskStatus) ?? "todo",
        plannedStartAt: t?.plannedStartAt ? t.plannedStartAt.toISOString() : null,
        updatedAt: t?.updatedAt ? t.updatedAt.toISOString() : null,
      };
    });
  }
  ```

  Sửa `toView` (dòng 154-173) thành async, nhận thêm `dbOrTx`:

  ```ts
  async function toView(
    row: typeof projectOperatingSetups.$inferSelect,
    dbOrTx: typeof db | Tx = db
  ): Promise<ProjectOperatingSetupView> {
    const actions = (row.firstWeekActions as FirstWeekAction[]) || [];
    return {
      projectId: row.projectId.toString(),
      workspaceId: row.workspaceId.toString(),
      status: row.status as OperatingSetupStatus,
      targetCustomer: row.targetCustomer,
      problemStatement: row.problemStatement,
      evidenceLevel: row.evidenceLevel as EvidenceLevel | null,
      recommendedStage: row.recommendedStage as BasicKickoffStage | null,
      selectedStage: row.selectedStage as BasicKickoffStage | null,
      stageDurationWeeks: row.stageDurationWeeks,
      stageTargetDate: row.stageTargetDate ? row.stageTargetDate.toISOString() : null,
      roundStartDate: row.roundStartDate ? row.roundStartDate.toISOString() : null,
      weeklyReviewWeekday: row.weeklyReviewWeekday,
      weeklyReviewTime: row.weeklyReviewTime,
      firstWeekOutcome: row.firstWeekOutcome,
      firstWeekActions: await enrichFirstWeekActions(actions, dbOrTx, row.workspaceId),
      updatedAt: row.updatedAt ? row.updatedAt.toISOString() : null,
    };
  }
  ```

  Sửa 3 call site:
  1. `getProjectOperatingSetup` (dòng 238): `return toView(setup);` → `return toView(setup, db);`
  2. `saveProjectOperatingSetup` (dòng 412, trong transaction): `return toView(saved);` → `return toView(saved, tx);`
  3. `activateProjectOperatingSetup` (dòng 609-612):

     ```ts
     return {
       setup: await toView(savedSetup, tx),
       project: toProject(refreshedProject ?? proj),
     };
     ```

- [ ] **Step 4: Chạy test, xác nhận pass**

  Run: `cd services/company && npx vitest run operations/tests/project-operating-setup-kickoff-materialize.test.ts operations/tests/project-kickoff-materialize.test.ts operations/tests/task.test.ts`
  Expected: PASS toàn bộ (bao gồm các test cũ đã có từ trước — xác nhận không phá hành vi hiện tại).

- [ ] **Step 5: Typecheck + boundary gates**

  Run: `cd services/company && npm run typecheck`
  Run (từ root): `make company-boundary-check && make encore-handler-boundary-check && make ts-suppression-check`
  Expected: cả 4 lệnh pass.

- [ ] **Step 6: Commit**

  ```bash
  git add services/company/operations/strategy/services/project-operating-setup.service.ts services/company/operations/tests/project-operating-setup-kickoff-materialize.test.ts
  git commit -m "feat(operations): enrich firstWeekActions with live task status/schedule"
  ```

---

### Task 3: Frontend — `FirstWeekActionDraft` mang status/plannedStartAt/updatedAt

**Files:**
- Modify: `frontend/lib/data/models/project_operating_setup_model.dart`
- Test: `frontend/test/data/models/project_operating_setup_model_test.dart`

**Interfaces:**
- Consumes: JSON shape từ Task 2 (`{ id, title, status, plannedStartAt, updatedAt }` mỗi phần tử `firstWeekActions`).
- Produces: `FirstWeekActionDraft { id, title, status: TaskKanbanStatus, plannedStartAt: DateTime?, updatedAt: DateTime? }` — Task 6 (checklist UI) và Task 8 (controller) dùng đúng field names này.

- [ ] **Step 1: Viết test thất bại**

  Thêm vào đầu `project_operating_setup_model_test.dart` (dòng 1-2):

  ```dart
  import 'package:flutter_test/flutter_test.dart';
  import 'package:frontend/data/models/project_operating_setup_model.dart';
  import 'package:frontend/data/models/task_kanban_model.dart';
  ```

  Thêm 2 test mới trước dấu `}` đóng `main()` (sau dòng 35):

  ```dart
  test('fromJson đọc status/plannedStartAt/updatedAt của firstWeekActions', () {
    final s = ProjectOperatingSetup.fromJson({
      'projectId': 'p1',
      'workspaceId': 'w1',
      'status': 'ACTIVE',
      'firstWeekActions': [
        {
          'id': 'a1',
          'title': 'Interview lead',
          'status': 'done',
          'plannedStartAt': '2026-09-08T09:00:00.000Z',
          'updatedAt': '2026-09-08T09:05:00.000Z',
        },
      ],
    });
    final action = s.firstWeekActions.single;
    expect(action.status, TaskKanbanStatus.done);
    expect(action.plannedStartAt, DateTime.utc(2026, 9, 8, 9));
    expect(action.updatedAt, DateTime.utc(2026, 9, 8, 9, 5));
  });

  test('fromJson thiếu status/plannedStartAt -> mặc định todo/null', () {
    final s = ProjectOperatingSetup.fromJson({
      'projectId': 'p1',
      'workspaceId': 'w1',
      'status': 'ACTIVE',
      'firstWeekActions': [
        {'id': 'a1', 'title': 'No schedule yet'},
      ],
    });
    final action = s.firstWeekActions.single;
    expect(action.status, TaskKanbanStatus.todo);
    expect(action.plannedStartAt, isNull);
  });
  ```

- [ ] **Step 2: Chạy test, xác nhận thất bại**

  Run: `cd frontend && flutter test test/data/models/project_operating_setup_model_test.dart`
  Expected: FAIL — `The getter 'status' isn't defined for the class 'FirstWeekActionDraft'`.

- [ ] **Step 3: Implement trong `project_operating_setup_model.dart`**

  Thêm import ở đầu file (dòng 1):

  ```dart
  import '../../core/contracts/enums.generated.dart';
  import 'task_kanban_model.dart';
  ```

  Sửa `FirstWeekActionDraft` (dòng 44-53) thành:

  ```dart
  class FirstWeekActionDraft {
    const FirstWeekActionDraft({
      this.id,
      required this.title,
      this.status = TaskKanbanStatus.todo,
      this.plannedStartAt,
      this.updatedAt,
    });
    final String? id;
    final String title;
    final TaskKanbanStatus status;
    final DateTime? plannedStartAt;
    final DateTime? updatedAt;

    bool get isDone => status == TaskKanbanStatus.done;

    Map<String, dynamic> toJson() => {
      if (id != null) 'id': id,
      'title': title.trim(),
    };
  }
  ```

  Sửa phần map `firstWeekActions` trong `ProjectOperatingSetup.fromJson` (dòng 185-194) thành:

  ```dart
      firstWeekActions:
          (json['firstWeekActions'] as List?)
              ?.map(
                (e) => FirstWeekActionDraft(
                  id: e['id']?.toString(),
                  title: (e['title'] ?? '').toString(),
                  status: TaskKanbanStatus.fromString(e['status']?.toString()),
                  plannedStartAt: e['plannedStartAt'] != null
                      ? DateTime.tryParse(e['plannedStartAt'].toString())
                      : null,
                  updatedAt: e['updatedAt'] != null
                      ? DateTime.tryParse(e['updatedAt'].toString())
                      : null,
                ),
              )
              .toList() ??
          const [],
  ```

- [ ] **Step 4: Chạy test, xác nhận pass**

  Run: `cd frontend && flutter test test/data/models/project_operating_setup_model_test.dart`
  Expected: PASS toàn bộ (kể cả 4 test cũ).

- [ ] **Step 5: Commit**

  ```bash
  git add frontend/lib/data/models/project_operating_setup_model.dart frontend/test/data/models/project_operating_setup_model_test.dart
  git commit -m "feat(frontend): parse status/plannedStartAt/updatedAt on FirstWeekActionDraft"
  ```

---

### Task 4: Frontend — `TaskService.updateTaskSchedule` + allowlist route mới

**Files:**
- Modify: `frontend/lib/modules/tasks/services/task_service.dart`
- Modify: `scripts/frontend-api-contract-allowlist.json`
- Test: `frontend/test/task_service_test.dart`

**Interfaces:**
- Consumes: `POST /operations/tasks/:id/schedule` (Task 1).
- Produces: `TaskService.updateTaskSchedule(String taskId, DateTime? plannedStartAt): Future<void>` — Task 8 (controller) gọi hàm này.

- [ ] **Step 1: Viết test thất bại**

  Thêm `group` mới vào cuối `task_service_test.dart`, trước dấu `}` đóng `main()` (sau dòng 134):

  ```dart
  group('updateTaskSchedule', () {
    test('sends plannedStartAt as an ISO string', () async {
      ApiClient.client = MockClient((request) async {
        expect(request.method, 'POST');
        expect(request.url.path, '/operations/tasks/1/schedule');
        expect(jsonDecode(request.body), {'plannedStartAt': '2026-09-08T09:00:00.000Z'});
        return http.Response(jsonEncode({'id': '1', 'status': 'todo'}), 200);
      });

      await TaskService().updateTaskSchedule('1', DateTime.utc(2026, 9, 8, 9));
    });

    test('sends null to clear the schedule', () async {
      ApiClient.client = MockClient((request) async {
        expect(jsonDecode(request.body), {'plannedStartAt': null});
        return http.Response(jsonEncode({'id': '1', 'status': 'todo'}), 200);
      });

      await TaskService().updateTaskSchedule('1', null);
    });

    test('throws StateError on a 404 response', () async {
      ApiClient.client = MockClient((request) async => http.Response('Not found', 404));
      expect(() => TaskService().updateTaskSchedule('1', null), throwsA(isA<StateError>()));
    });

    test('throws ArgumentError on empty taskId', () async {
      expect(() => TaskService().updateTaskSchedule('', null), throwsArgumentError);
    });
  });
  ```

- [ ] **Step 2: Chạy test, xác nhận thất bại**

  Run: `cd frontend && flutter test test/task_service_test.dart`
  Expected: FAIL — `The method 'updateTaskSchedule' isn't defined for the class 'TaskService'`.

- [ ] **Step 3: Implement trong `task_service.dart`**

  Thêm method mới ngay sau `updateTaskStatus` (sau dòng 114):

  ```dart
    /// Cập nhật giờ dự kiến thực hiện task qua endpoint Encore: POST /operations/tasks/:id/schedule
    Future<void> updateTaskSchedule(String taskId, DateTime? plannedStartAt) async {
      if (taskId.isEmpty) throw ArgumentError('taskId cannot be empty');
      await _requireWorkspaceId();

      final response = await ApiClient.post(
        '/operations/tasks/$taskId/schedule',
        body: {'plannedStartAt': plannedStartAt?.toUtc().toIso8601String()},
      );
      if (response.statusCode == 200) return;
      if (response.statusCode == 401 || response.statusCode == 403) {
        throw StateError('Authentication or workspace access denied: ${response.statusCode}');
      } else if (response.statusCode == 404) {
        throw StateError('Task $taskId not found (404)');
      } else {
        throw StateError('Failed to update task schedule: ${response.statusCode} ${response.body}');
      }
    }
  ```

- [ ] **Step 4: Chạy test, xác nhận pass**

  Run: `cd frontend && flutter test test/task_service_test.dart`
  Expected: PASS toàn bộ.

- [ ] **Step 5: Thêm allowlist entry cho route mới**

  Trong `scripts/frontend-api-contract-allowlist.json`, chèn entry sau entry `/operations/tasks/:taskId/status` (dòng 1965-1971):

  ```json
      {
        "path": "/operations/tasks/:taskId/schedule",
        "method": "POST",
        "owner": "company-operations",
        "reason": "New endpoint (Command Center dashboard task checklist, 2026-09-04) for editing a first-week-action task's plannedStartAt; not part of the curated MVP capability manifest yet, same class as the pre-existing /operations/tasks/:taskId/status entry above.",
        "expires_on": "2026-12-31"
      },
  ```

- [ ] **Step 6: Xác nhận contract check pass**

  Run (từ root): `make frontend-api-contract-check`
  Expected: PASS — route mới được allowlist nhận diện.

- [ ] **Step 7: Commit**

  ```bash
  git add frontend/lib/modules/tasks/services/task_service.dart frontend/test/task_service_test.dart scripts/frontend-api-contract-allowlist.json
  git commit -m "feat(frontend): add TaskService.updateTaskSchedule + allowlist entry"
  ```

---

### Task 5: Frontend — tách `PulseStatBarWidget`, đưa lên đầu trang

**Files:**
- Create: `frontend/lib/modules/hologram_hub/widgets/pulse_stat_bar_widget.dart`
- Modify: `frontend/lib/modules/hologram_hub/widgets/cofounder_card_widget.dart`
- Modify: `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart`
- Test: `frontend/test/modules/hologram_hub/widgets/pulse_stat_bar_widget_test.dart` (new)

**Interfaces:**
- Consumes: `CompanyPulseModel?` (đã có, không đổi).
- Produces: `PulseStatBarWidget({required CompanyPulseModel? pulse})` — dùng trong `hologram_hub_view.dart` Task 5 Step 5.

- [ ] **Step 1: Viết test thất bại cho widget mới**

  Tạo `frontend/test/modules/hologram_hub/widgets/pulse_stat_bar_widget_test.dart`:

  ```dart
  import 'package:flutter/material.dart';
  import 'package:flutter_test/flutter_test.dart';
  import 'package:frontend/data/models/company_pulse_model.dart';
  import 'package:frontend/modules/hologram_hub/widgets/pulse_stat_bar_widget.dart';

  void main() {
    testWidgets('renders all 4 pulse stat labels and values', (tester) async {
      final pulse = CompanyPulseModel(
        goalsOnTrack: 3,
        totalActiveGoals: 5,
        activeMissions: 2,
        needsDecisionCount: 1,
        majorRisksCount: 0,
        updatedAt: DateTime.utc(2026, 9, 4),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: PulseStatBarWidget(pulse: pulse)),
        ),
      );

      expect(find.text('3/5'), findsOneWidget);
      expect(find.text('Mục tiêu đúng hạn'), findsOneWidget);
      expect(find.text('2'), findsOneWidget);
      expect(find.text('Missions đang chạy'), findsOneWidget);
      expect(find.text('1'), findsOneWidget);
      expect(find.text('Quyết định cần chốt'), findsOneWidget);
      expect(find.text('0'), findsOneWidget);
      expect(find.text('Rủi ro cần lưu ý'), findsOneWidget);
    });

    testWidgets('renders zeroed stats when pulse is null', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: PulseStatBarWidget(pulse: null)),
        ),
      );

      expect(find.text('0/0'), findsOneWidget);
    });
  }
  ```

  (Constructor thật của `CompanyPulseModel` — `frontend/lib/data/models/company_pulse_model.dart:64-74` — đã verify: không có field `companyHealth`; `updatedAt` là `DateTime` bắt buộc; `goalsOnTrack`/`totalActiveGoals`/`activeMissions`/`needsDecisionCount`/`majorRisksCount` đều `int` mặc định 0.)

- [ ] **Step 2: Chạy test, xác nhận thất bại**

  Run: `cd frontend && flutter test test/modules/hologram_hub/widgets/pulse_stat_bar_widget_test.dart`
  Expected: FAIL — file `pulse_stat_bar_widget.dart` chưa tồn tại.

- [ ] **Step 3: Tạo `pulse_stat_bar_widget.dart`**

  ```dart
  import 'package:flutter/material.dart';
  import '../../../data/models/company_pulse_model.dart';

  class PulseStatBarWidget extends StatelessWidget {
    final CompanyPulseModel? pulse;

    const PulseStatBarWidget({super.key, required this.pulse});

    @override
    Widget build(BuildContext context) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        decoration: BoxDecoration(
          color: const Color(0xFF1E293B).withValues(alpha: 0.6),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFF334155)),
        ),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final isNarrow = constraints.maxWidth < 550;
            final stats = [
              _buildPulseStat(
                icon: Icons.check_circle_outline,
                color: const Color(0xFF10B981),
                value: '${pulse?.goalsOnTrack ?? 0}/${pulse?.totalActiveGoals ?? 0}',
                label: 'Mục tiêu đúng hạn',
              ),
              _buildPulseStat(
                icon: Icons.rocket_launch_outlined,
                color: const Color(0xFF3B82F6),
                value: '${pulse?.activeMissions ?? 0}',
                label: 'Missions đang chạy',
              ),
              _buildPulseStat(
                icon: Icons.gavel_outlined,
                color: const Color(0xFFF59E0B),
                value: '${pulse?.needsDecisionCount ?? 0}',
                label: 'Quyết định cần chốt',
              ),
              _buildPulseStat(
                icon: Icons.warning_amber_outlined,
                color: const Color(0xFFEF4444),
                value: '${pulse?.majorRisksCount ?? 0}',
                label: 'Rủi ro cần lưu ý',
              ),
            ];

            if (isNarrow) {
              return Wrap(
                alignment: WrapAlignment.spaceAround,
                spacing: 20,
                runSpacing: 14,
                children: stats,
              );
            }

            return Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: stats.map((s) => Expanded(child: s)).toList(),
            );
          },
        ),
      );
    }

    Widget _buildPulseStat({
      required IconData icon,
      required Color color,
      required String value,
      required String label,
    }) {
      return Column(
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, color: color, size: 18),
              const SizedBox(width: 6),
              Text(
                value,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: 11,
              color: Colors.white.withValues(alpha: 0.6),
            ),
          ),
        ],
      );
    }
  }
  ```

- [ ] **Step 4: Chạy test, xác nhận pass**

  Run: `cd frontend && flutter test test/modules/hologram_hub/widgets/pulse_stat_bar_widget_test.dart`
  Expected: PASS.

- [ ] **Step 5: Xoá stat bar khỏi `cofounder_card_widget.dart`**

  Thay thế đoạn từ `const SizedBox(height: 20),` (dòng 282) đến hết file (dòng 402, sau `_buildPulseStat`) bằng:

  ```dart
              },
            ),
          ],
        ),
      );
    }
  }
  ```

  (Giữ nguyên toàn bộ `LayoutBuilder` header ở trên — dòng 40-281 không đổi; class không còn `_buildPulseStat` nữa.)

- [ ] **Step 6: Đưa `PulseStatBarWidget` lên đầu trang trong `hologram_hub_view.dart`**

  Thêm import sau dòng 6 (`import '../widgets/cofounder_card_widget.dart';`):

  ```dart
  import '../widgets/pulse_stat_bar_widget.dart';
  ```

  Sửa `_buildCommandCenterTab` (dòng 410-416) thành:

  ```dart
          if (controller.hasProjects.value) ...[
            // A0. Thống kê nhanh — đặt trên cùng theo feedback founder (2026-09-04)
            // xem docs/superpowers/specs/2026-09-04-command-center-dashboard-redesign-design.md
            PulseStatBarWidget(pulse: controller.pulse.value),
            const SizedBox(height: 16),

            // A. Hero Co-Founder Card
            CoFounderCardWidget(
              pulse: controller.pulse.value,
              onAskCosa: () => Get.find<ChatPanelController>().open(),
            ),
            const SizedBox(height: 24),
  ```

- [ ] **Step 7: `flutter analyze` sạch**

  Run: `cd frontend && flutter analyze lib/modules/hologram_hub`
  Expected: không lỗi/warning mới (đặc biệt: `cofounder_card_widget.dart` không còn hàm `_buildPulseStat` unused).

- [ ] **Step 8: Chạy toàn bộ test hologram_hub, xác nhận không phá hành vi cũ**

  Run: `cd frontend && flutter test test/modules/hologram_hub`
  Expected: PASS toàn bộ (không test nào phụ thuộc vào layout cũ của `CoFounderCardWidget` bị vỡ).

- [ ] **Step 9: Commit**

  ```bash
  git add frontend/lib/modules/hologram_hub/widgets/pulse_stat_bar_widget.dart frontend/lib/modules/hologram_hub/widgets/cofounder_card_widget.dart frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart frontend/test/modules/hologram_hub/widgets/pulse_stat_bar_widget_test.dart
  git commit -m "feat(frontend): extract PulseStatBarWidget and move stats to the top of Command Center"
  ```

---

### Task 6: Frontend — checklist "Hành động tuần đầu" trong `Top3FocusWidget`

**Files:**
- Modify: `frontend/lib/modules/hologram_hub/widgets/top3_focus_widget.dart`
- Test: `frontend/test/modules/hologram_hub/widgets/top3_focus_widget_checklist_test.dart` (new)

**Interfaces:**
- Consumes: `FirstWeekActionDraft` (Task 3).
- Produces: `Top3FocusWidget` gets 3 new optional constructor params — `firstWeekActions: List<FirstWeekActionDraft>` (default `const []`), `onToggleActionStatus: ValueChanged<FirstWeekActionDraft>?`, `onScheduleAction: void Function(FirstWeekActionDraft, DateTime?)?` — Task 7 truyền các callback này từ `hologram_hub_view.dart`.

- [ ] **Step 1: Viết test thất bại**

  Tạo `frontend/test/modules/hologram_hub/widgets/top3_focus_widget_checklist_test.dart`:

  ```dart
  import 'package:flutter/material.dart';
  import 'package:flutter_test/flutter_test.dart';
  import 'package:frontend/data/models/company_pulse_model.dart';
  import 'package:frontend/data/models/project_operating_setup_model.dart';
  import 'package:frontend/data/models/task_kanban_model.dart';
  import 'package:frontend/modules/hologram_hub/widgets/top3_focus_widget.dart';

  void main() {
    testWidgets('renders first-week-action checklist with checkbox and time badge', (tester) async {
      FirstWeekActionDraft? toggled;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Top3FocusWidget(
              actions: const <NextBestActionModel>[],
              onActionTap: (_) {},
              firstWeekActions: const [
                FirstWeekActionDraft(id: 'a1', title: 'Interview lead #1'),
              ],
              onToggleActionStatus: (action) => toggled = action,
            ),
          ),
        ),
      );

      expect(find.text('Interview lead #1'), findsOneWidget);
      expect(find.text('Chưa đặt giờ'), findsOneWidget);
      expect(find.byType(Checkbox), findsOneWidget);

      await tester.tap(find.byType(Checkbox));
      await tester.pump();

      expect(toggled?.id, 'a1');
    });

    testWidgets('shows a checked box when the action is done', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Top3FocusWidget(
              actions: const <NextBestActionModel>[],
              onActionTap: (_) {},
              firstWeekActions: const [
                FirstWeekActionDraft(id: 'a1', title: 'Done action', status: TaskKanbanStatus.done),
              ],
            ),
          ),
        ),
      );

      final checkbox = tester.widget<Checkbox>(find.byType(Checkbox));
      expect(checkbox.value, isTrue);
    });

    testWidgets('renders nothing extra when firstWeekActions is empty', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Top3FocusWidget(
              actions: const <NextBestActionModel>[],
              onActionTap: (_) {},
            ),
          ),
        ),
      );

      expect(find.byType(Checkbox), findsNothing);
    });
  }
  ```

- [ ] **Step 2: Chạy test, xác nhận thất bại**

  Run: `cd frontend && flutter test test/modules/hologram_hub/widgets/top3_focus_widget_checklist_test.dart`
  Expected: FAIL — `No named parameter with the name 'firstWeekActions'`.

- [ ] **Step 3: Implement checklist trong `top3_focus_widget.dart`**

  Sửa import (dòng 1-2) thành:

  ```dart
  import 'package:flutter/material.dart';
  import '../../../data/models/company_pulse_model.dart';
  import '../../../data/models/project_operating_setup_model.dart';
  import '../../../data/models/task_kanban_model.dart';
  ```

  Sửa class declaration + constructor (dòng 4-12) thành:

  ```dart
  class Top3FocusWidget extends StatelessWidget {
    final List<NextBestActionModel> actions;
    final Function(NextBestActionModel) onActionTap;
    final List<FirstWeekActionDraft> firstWeekActions;
    final ValueChanged<FirstWeekActionDraft>? onToggleActionStatus;
    final void Function(FirstWeekActionDraft action, DateTime? plannedStartAt)?
        onScheduleAction;

    const Top3FocusWidget({
      super.key,
      required this.actions,
      required this.onActionTap,
      this.firstWeekActions = const [],
      this.onToggleActionStatus,
      this.onScheduleAction,
    });
  ```

  Thay toàn bộ `build()` (dòng 14-100, từ `Widget build(BuildContext context) {` đến `}` đóng method, ngay trước `Widget _buildActionCard(...)`) bằng:

  ```dart
    @override
    Widget build(BuildContext context) {
      final hasNextBestActions = actions.isNotEmpty;
      final hasFirstWeekActions = firstWeekActions.isNotEmpty;

      return Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: const Color(0xFF1E293B).withValues(alpha: 0.6),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFF334155)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  hasNextBestActions ? Icons.stars : Icons.stars_outlined,
                  color: const Color(0xFFF59E0B),
                  size: 20,
                ),
                const SizedBox(width: 8),
                const Expanded(
                  child: Text(
                    'TOP 3 TRỌNG TÂM HÔM NAY (12-Week Year Focus)',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                      letterSpacing: 0.5,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (hasNextBestActions) ...[
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: const Color(0xFF3B82F6).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Text(
                      'Next Best Actions',
                      style: TextStyle(fontSize: 11, color: Color(0xFF60A5FA), fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
              ],
            ),
            const SizedBox(height: 12),
            if (hasNextBestActions)
              ...actions.asMap().entries.map((entry) {
                final idx = entry.key + 1;
                final item = entry.value;
                return _buildActionCard(idx, item);
              })
            else
              Text(
                'Chưa có hành động ưu tiên nào được sinh ra cho dự án. Hãy bắt đầu bằng việc thiết lập các giả định quan trọng của giai đoạn P1 (Problem Validation) hoặc kích hoạt chu trình 12 tuần.',
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.7),
                  fontSize: 13,
                  height: 1.4,
                ),
              ),
            if (hasFirstWeekActions) ...[
              const SizedBox(height: 20),
              const Divider(color: Color(0xFF334155), height: 1),
              const SizedBox(height: 16),
              const Text(
                'Hành động tuần đầu',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                  letterSpacing: 0.3,
                ),
              ),
              const SizedBox(height: 10),
              ...firstWeekActions.map((action) => _buildChecklistItem(context, action)),
            ],
          ],
        ),
      );
    }

    Widget _buildChecklistItem(BuildContext context, FirstWeekActionDraft action) {
      final isDone = action.isDone;
      return Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Checkbox(
              value: isDone,
              activeColor: const Color(0xFF10B981),
              onChanged: onToggleActionStatus == null
                  ? null
                  : (_) => onToggleActionStatus!(action),
            ),
            Expanded(
              child: Text(
                action.title,
                style: TextStyle(
                  color: isDone ? Colors.white.withValues(alpha: 0.5) : Colors.white,
                  fontSize: 13.5,
                  decoration: isDone ? TextDecoration.lineThrough : null,
                ),
              ),
            ),
            InkWell(
              onTap: onScheduleAction == null ? null : () => _pickSchedule(context, action),
              borderRadius: BorderRadius.circular(8),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: const Color(0xFF0F172A),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFF334155)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.schedule, size: 13, color: Color(0xFF94A3B8)),
                    const SizedBox(width: 4),
                    Text(
                      action.plannedStartAt != null
                          ? TimeOfDay.fromDateTime(action.plannedStartAt!.toLocal()).format(context)
                          : 'Chưa đặt giờ',
                      style: const TextStyle(fontSize: 11.5, color: Color(0xFF94A3B8)),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      );
    }

    Future<void> _pickSchedule(BuildContext context, FirstWeekActionDraft action) async {
      final now = DateTime.now();
      final initialDate = action.plannedStartAt?.toLocal() ?? now;
      final date = await showDatePicker(
        context: context,
        initialDate: initialDate,
        firstDate: now.subtract(const Duration(days: 1)),
        lastDate: now.add(const Duration(days: 90)),
      );
      if (date == null || !context.mounted) return;
      final time = await showTimePicker(
        context: context,
        initialTime: TimeOfDay.fromDateTime(initialDate),
      );
      if (time == null) return;
      final picked = DateTime(date.year, date.month, date.day, time.hour, time.minute);
      onScheduleAction?.call(action, picked);
    }
  ```

  Giữ nguyên `_buildActionCard(...)` (dòng 102-207 gốc) không đổi.

- [ ] **Step 4: Chạy test, xác nhận pass**

  Run: `cd frontend && flutter test test/modules/hologram_hub/widgets/top3_focus_widget_checklist_test.dart`
  Expected: PASS.

- [ ] **Step 5: `flutter analyze` sạch**

  Run: `cd frontend && flutter analyze lib/modules/hologram_hub/widgets/top3_focus_widget.dart`
  Expected: không lỗi.

- [ ] **Step 6: Commit**

  ```bash
  git add frontend/lib/modules/hologram_hub/widgets/top3_focus_widget.dart frontend/test/modules/hologram_hub/widgets/top3_focus_widget_checklist_test.dart
  git commit -m "feat(frontend): add editable first-week-action checklist to Top3FocusWidget"
  ```

---

### Task 7: Frontend — nối checklist vào `hologram_hub_view.dart`, thu hẹp cột "Hàng đợi", xoá chip cũ

**Files:**
- Modify: `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart`

**Interfaces:**
- Consumes: `Top3FocusWidget` params mới (Task 6), `controller.toggleFirstWeekActionStatus`/`controller.updateFirstWeekActionSchedule` (Task 8 — CHƯA tồn tại khi chạy task này; xem Step 5 lưu ý thứ tự).

> Lưu ý thứ tự: bước wiring này gọi 2 method controller chưa được implement (Task 8). Làm Step 1-2 (xoá chip cũ, đổi flex) trước — không phụ thuộc controller — rồi mới làm Step 3 (truyền props Top3FocusWidget); nếu build lỗi vì thiếu method, tạm thời implement Task 8 trước rồi quay lại, HOẶC làm cả Task 7 + Task 8 trong cùng một lượt review (khuyến nghị nếu chạy inline, không tách agent riêng).

- [ ] **Step 1: Xoá chip tĩnh "Hành động tuần đầu" khỏi banner "Vòng hiện tại"**

  Trong `_buildActiveOperatingSetupCard` (dòng 592 trở đi), xoá đoạn từ dòng 685 đến 717:

  ```dart
            if (setup.firstWeekActions.isNotEmpty) ...[
              const SizedBox(height: 10),
              const Text(
                'Hành động tuần đầu:',
                style: TextStyle(
                  color: Color(0xFF94A3B8),
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 6),
              Wrap(
                spacing: 8,
                runSpacing: 6,
                children: setup.firstWeekActions.asMap().entries.map((entry) {
                  return Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0F172A),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: const Color(0xFF334155)),
                    ),
                    child: Text(
                      '${entry.key + 1}. ${entry.value.title}',
                      style: const TextStyle(color: Colors.white, fontSize: 13),
                    ),
                  );
                }).toList(),
              ),
            ],
  ```

  (Giữ nguyên khối `if (setup.firstWeekOutcome != null...)` ngay phía trên nó — chỉ xoá đúng khối `firstWeekActions`.)

- [ ] **Step 2: Đổi tỉ lệ flex cột phải từ 6/5 sang 7/3**

  Trong grid desktop (dòng 435-468), sửa `flex: 6` (Top3FocusWidget) → `flex: 7`, và `flex: 5` (WaitingForYouWidget) → `flex: 3`.

- [ ] **Step 3: Truyền checklist props vào cả 2 vị trí gọi `Top3FocusWidget`**

  Desktop (trong khối `Expanded(flex: 7, child: Top3FocusWidget(...))`, dòng ~442-446):

  ```dart
                  Expanded(
                    flex: 7,
                    child: Top3FocusWidget(
                      actions: controller.top3Actions.toList(),
                      onActionTap: (action) =>
                          _handleActionTap(context, controller, action),
                      firstWeekActions:
                          controller.activeProjectSetup.value?.firstWeekActions ??
                              const [],
                      onToggleActionStatus: (action) =>
                          controller.toggleFirstWeekActionStatus(action),
                      onScheduleAction: (action, plannedStartAt) => controller
                          .updateFirstWeekActionSchedule(action, plannedStartAt),
                    ),
                  ),
  ```

  Mobile stacked (dòng ~471-475):

  ```dart
              Top3FocusWidget(
                actions: controller.top3Actions.toList(),
                onActionTap: (action) =>
                    _handleActionTap(context, controller, action),
                firstWeekActions:
                    controller.activeProjectSetup.value?.firstWeekActions ??
                        const [],
                onToggleActionStatus: (action) =>
                    controller.toggleFirstWeekActionStatus(action),
                onScheduleAction: (action, plannedStartAt) => controller
                    .updateFirstWeekActionSchedule(action, plannedStartAt),
              ),
  ```

- [ ] **Step 4: `flutter analyze` sạch**

  Run: `cd frontend && flutter analyze lib/modules/hologram_hub`
  Expected: không lỗi (nếu Task 8 đã hoàn tất; nếu chưa, lỗi "method not defined" là kỳ vọng tạm thời — hoàn tất Task 8 trước khi coi bước này xong).

- [ ] **Step 5: Chạy toàn bộ test hologram_hub**

  Run: `cd frontend && flutter test test/modules/hologram_hub`
  Expected: PASS toàn bộ — không test nào còn assert trên chip cũ hay tỉ lệ flex cũ.

- [ ] **Step 6: Commit**

  ```bash
  git add frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart
  git commit -m "feat(frontend): wire first-week-action checklist into Command Center, narrow queue column"
  ```

---

### Task 8: Frontend — controller methods `toggleFirstWeekActionStatus` / `updateFirstWeekActionSchedule`

**Files:**
- Modify: `frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart`
- Test: `frontend/test/modules/hologram_hub/founder_command_center_first_week_actions_test.dart` (new)

**Interfaces:**
- Consumes: `TaskService.updateTaskStatus` (đã có sẵn), `TaskService.updateTaskSchedule` (Task 4), `ProjectOperatingSetupService.get` (đã có sẵn).
- Produces: `Future<void> toggleFirstWeekActionStatus(FirstWeekActionDraft action)`, `Future<void> updateFirstWeekActionSchedule(FirstWeekActionDraft action, DateTime? plannedStartAt)` trên `FounderCommandCenterController` — Task 7 gọi 2 hàm này.

- [ ] **Step 1: Viết test thất bại**

  Tạo `frontend/test/modules/hologram_hub/founder_command_center_first_week_actions_test.dart`:

  ```dart
  import 'dart:convert';
  import 'package:flutter_test/flutter_test.dart';
  import 'package:get/get.dart';
  import 'package:http/http.dart' as http;
  import 'package:http/testing.dart';
  import 'package:shared_preferences/shared_preferences.dart';
  import 'package:frontend/core/network/api_client.dart';
  import 'package:frontend/data/models/project_operating_setup_model.dart';
  import 'package:frontend/data/models/task_kanban_model.dart';
  import 'package:frontend/modules/hologram_hub/controllers/founder_command_center_controller.dart';

  void main() {
    TestWidgetsFlutterBinding.ensureInitialized();

    late http.Client originalClient;

    setUp(() {
      SharedPreferences.setMockInitialValues({'workspace_id': 'ws_123'});
      Get.testMode = true;
      Get.reset();
      originalClient = ApiClient.client;
    });

    tearDown(() {
      ApiClient.client = originalClient;
      Get.reset();
    });

    FounderCommandCenterController controllerWithOneAction(
      List<Map<String, dynamic>> statusCalls,
      List<Map<String, dynamic>> scheduleCalls,
    ) {
      ApiClient.client = MockClient((request) async {
        if (request.method == 'POST' && request.url.path == '/operations/tasks/a1/status') {
          statusCalls.add(jsonDecode(request.body) as Map<String, dynamic>);
          return http.Response(jsonEncode({'id': 'a1', 'status': 'done', 'title': 'Action A'}), 200);
        }
        if (request.method == 'POST' && request.url.path == '/operations/tasks/a1/schedule') {
          scheduleCalls.add(jsonDecode(request.body) as Map<String, dynamic>);
          return http.Response(jsonEncode({'id': 'a1', 'status': 'todo', 'title': 'Action A'}), 200);
        }
        if (request.method == 'GET' && request.url.path == '/operations/projects/proj-1/operating-setup') {
          return http.Response(
            jsonEncode({
              'projectId': 'proj-1',
              'workspaceId': 'ws_123',
              'status': 'ACTIVE',
              'firstWeekActions': [
                {'id': 'a1', 'title': 'Action A', 'status': 'done'},
              ],
            }),
            200,
          );
        }
        return http.Response('{}', 200);
      });

      final controller = FounderCommandCenterController();
      controller.projectsList.assignAll([
        {'id': 'proj-1', 'title': 'Project 1'},
      ]);
      return controller;
    }

    test('toggleFirstWeekActionStatus posts the flipped status and refreshes the setup', () async {
      final statusCalls = <Map<String, dynamic>>[];
      final controller = controllerWithOneAction(statusCalls, []);

      await controller.toggleFirstWeekActionStatus(
        const FirstWeekActionDraft(id: 'a1', title: 'Action A', status: TaskKanbanStatus.todo),
      );

      expect(statusCalls, [
        {'status': 'done'},
      ]);
      expect(controller.activeProjectSetup.value?.firstWeekActions.single.status, TaskKanbanStatus.done);
    });

    test('updateFirstWeekActionSchedule posts the new plannedStartAt and refreshes the setup', () async {
      final scheduleCalls = <Map<String, dynamic>>[];
      final controller = controllerWithOneAction([], scheduleCalls);

      await controller.updateFirstWeekActionSchedule(
        const FirstWeekActionDraft(id: 'a1', title: 'Action A'),
        DateTime.utc(2026, 9, 8, 9),
      );

      expect(scheduleCalls, [
        {'plannedStartAt': '2026-09-08T09:00:00.000Z'},
      ]);
    });

    test('toggleFirstWeekActionStatus is a no-op when the action has no id', () async {
      final statusCalls = <Map<String, dynamic>>[];
      final controller = controllerWithOneAction(statusCalls, []);

      await controller.toggleFirstWeekActionStatus(
        const FirstWeekActionDraft(title: 'No id yet'),
      );

      expect(statusCalls, isEmpty);
    });
  }
  ```

- [ ] **Step 2: Chạy test, xác nhận thất bại**

  Run: `cd frontend && flutter test test/modules/hologram_hub/founder_command_center_first_week_actions_test.dart`
  Expected: FAIL — `The method 'toggleFirstWeekActionStatus' isn't defined for the class 'FounderCommandCenterController'`.

- [ ] **Step 3: Implement trong `founder_command_center_controller.dart`**

  Thêm import sau dòng 18 (`import '../../../modules/strategy/services/project_operating_setup_service.dart';`):

  ```dart
  import '../../../data/models/task_kanban_model.dart';
  import '../../../modules/tasks/services/task_service.dart';
  ```

  Thêm 3 method mới ngay sau `togglePack` (sau dòng 482, trước `/// Gửi tin nhắn trao đổi với COSA Co-Founder`):

  ```dart
    /// Đánh dấu hoàn thành / chưa hoàn thành 1 "Hành động tuần đầu" — `action.id`
    /// chính là id của `operating.tasks` (đã materialize 1-1 khi lưu/activate
    /// operating setup, xem
    /// docs/superpowers/specs/2026-09-04-command-center-dashboard-redesign-design.md).
    Future<void> toggleFirstWeekActionStatus(FirstWeekActionDraft action) async {
      final actionId = action.id;
      if (actionId == null) return;
      final newStatus = action.status == TaskKanbanStatus.done
          ? TaskKanbanStatus.todo
          : TaskKanbanStatus.done;
      try {
        await TaskService().updateTaskStatus(actionId, newStatus.value);
        await _refreshActiveProjectSetup();
      } catch (e) {
        debugPrint('[FounderCommandCenter] toggleFirstWeekActionStatus error: $e');
        AppToast.error('Không thể cập nhật trạng thái task: $e');
      }
    }

    /// Đặt/xoá giờ dự kiến thực hiện cho 1 "Hành động tuần đầu".
    Future<void> updateFirstWeekActionSchedule(
      FirstWeekActionDraft action,
      DateTime? plannedStartAt,
    ) async {
      final actionId = action.id;
      if (actionId == null) return;
      try {
        await TaskService().updateTaskSchedule(actionId, plannedStartAt);
        await _refreshActiveProjectSetup();
      } catch (e) {
        debugPrint('[FounderCommandCenter] updateFirstWeekActionSchedule error: $e');
        AppToast.error('Không thể cập nhật giờ thực hiện: $e');
      }
    }

    Future<void> _refreshActiveProjectSetup() async {
      final activeProjectId = projectsList.isNotEmpty
          ? projectsList.first['id']?.toString()
          : null;
      if (activeProjectId == null) return;
      try {
        activeProjectSetup.value =
            await ProjectOperatingSetupService().get(activeProjectId);
      } catch (e) {
        debugPrint('[FounderCommandCenter] refresh setup error: $e');
      }
    }
  ```

- [ ] **Step 4: Chạy test, xác nhận pass**

  Run: `cd frontend && flutter test test/modules/hologram_hub/founder_command_center_first_week_actions_test.dart`
  Expected: PASS toàn bộ 3 test.

- [ ] **Step 5: `flutter analyze` sạch**

  Run: `cd frontend && flutter analyze lib/modules/hologram_hub/controllers/founder_command_center_controller.dart`
  Expected: không lỗi.

- [ ] **Step 6: Hoàn tất wiring của Task 7 (nếu chưa build sạch ở đó) + chạy lại toàn bộ test hologram_hub**

  Run: `cd frontend && flutter test test/modules/hologram_hub`
  Expected: PASS toàn bộ, bao gồm test Task 6/7/8.

- [ ] **Step 7: Commit**

  ```bash
  git add frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart frontend/test/modules/hologram_hub/founder_command_center_first_week_actions_test.dart
  git commit -m "feat(frontend): add controller methods to toggle/schedule first-week actions"
  ```

---

### Task 9: Verify toàn bộ + dọn allowlist/contract gates

**Files:** Không tạo/sửa file mới — chỉ chạy gate tổng hợp trên các thay đổi Task 1-8.

- [ ] **Step 1: Backend — test + typecheck + boundary gates**

  ```bash
  cd services/company && npm run typecheck
  cd /Volumes/SSD/javis-saas && make services-test-company
  make company-boundary-check
  make encore-handler-boundary-check
  make ts-suppression-check
  ```
  Expected: tất cả pass.

- [ ] **Step 2: Frontend — test + analyze + contract check**

  ```bash
  cd /Volumes/SSD/javis-saas/frontend && flutter test
  flutter analyze
  cd /Volumes/SSD/javis-saas && make frontend-api-contract-check
  ```
  Expected: tất cả pass; coverage gate (`make frontend-test`, floor theo `[[javis-saas: frontend coverage gate]]`) không tụt do các file mới đã có test.

- [ ] **Step 3: Smoke thủ công (nếu có dev stack chạy sẵn)**

  Nếu `make dev-stack` đang chạy: mở `/hub`, xác nhận (a) 4 số liệu nằm trên cùng, banner "COSA Co-Founder" ngay dưới; (b) card trái "TOP 3 TRỌNG TÂM" có thêm checklist "Hành động tuần đầu" với checkbox + badge giờ, tick được, bấm giờ mở date/time picker; (c) banner "Vòng hiện tại" không còn hiện lại chip "Hành động tuần đầu:"; (d) cột "Hàng đợi" bên phải rõ ràng hẹp hơn cột trái.

  Nếu không có dev stack sẵn sàng, ghi rõ trong báo cáo hoàn tất: "Chưa smoke-test UI thật, chỉ verify qua widget/unit test" — không tuyên bố "đã kiểm tra trên app thật" nếu chưa làm (CLAUDE.md quy tắc #11).

- [ ] **Step 4: Báo cáo hoàn tất**

  Tổng hợp: 8 task đã commit riêng lẻ, toàn bộ gate ở Step 1-2 pass, kèm ghi chú kết quả Step 3.

---

## Self-Review (đã chạy trước khi giao plan)

- **Spec coverage:** Phần 1 (stat bar lên top) → Task 5. Phần 2 (checklist giờ/checkbox, gộp card trái) → Task 1-4, 6, 8. Phần 3 (hàng đợi gọn) → Task 7 Step 2. Không có phần nào trong spec thiếu task.
- **Placeholder scan:** không còn "TBD"/"tương tự Task N" — mọi step có code hoặc lệnh cụ thể. Constructor thật của `CompanyPulseModel` đã được đọc và verify trước khi chốt Task 5 Step 1 (không còn giả định chưa kiểm chứng).
- **Type consistency:** `FirstWeekActionView`/`FirstWeekActionDraft`/`toggleFirstWeekActionStatus`/`updateFirstWeekActionSchedule`/`updateTaskSchedule` dùng tên nhất quán xuyên suốt Task 1→9.
