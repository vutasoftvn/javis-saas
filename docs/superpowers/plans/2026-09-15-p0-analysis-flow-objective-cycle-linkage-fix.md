# P0 Analysis Flow — Fix Broken Objective/Cycle/KeyResult Linkage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the bug where completing the founder P0 "Phân tích & Lập Kế hoạch Tuần" wizard leaves an orphaned draft `okr_objectives` row, an unlinked `ACTIVE` `twelve_week_cycles` row, zero Key Results, and silently-failed Weekly Commitments/Tasks — so the founder's Hub dashboard shows "0/0 Mục tiêu đúng hạn" / "0 Missions đang chạy" even though they already submitted the wizard.

**Architecture:** Two independent backend gaps and one frontend orchestration bug, found by reading the actual runtime data in Postgres and tracing every write path:

1. `createCycleApi` (`services/company/operations/handlers/project-operating-loop.handler.ts`) silently drops the `sourceObjectiveId` field even though the service layer (`createCycleAuthorized`) already supports it — added specifically to prevent "cycle exists without objective attached" (see the Vietnamese comment at `project-operating-loop.service.ts:504-506`). This is exactly the bug in production.
2. `createKeyResultAuthorized` never sets `baselineValue`/`currentValue` on a new Key Result (only `targetValue`/`unit` are settable, and only if the caller passes them). `publishObjectiveService` (`okr.service.ts:264-280`) requires **all four** of `targetValue`, `unit`, `currentValue`, `baselineValue` to be non-null before it will publish an objective. Today, **no Key Result created through the public API can ever be published**, regardless of what the frontend sends — a pre-existing gap the frontend fix would otherwise run straight into.
3. `ProjectAnalysisFlowController.submitAndActivate()` (`frontend/lib/modules/projects/controllers/project_analysis_flow_controller.dart:222-331`) creates the Cycle *before* the Objective (so it can never link them), never creates any Key Result, never calls `publishObjective`, and wraps every step in its own `try { } catch (e) { debugPrint(...) }` that always lets `submitAndActivate()` return `true` — so a founder sees "success" even when every write after the first one failed.

The fix reorders the frontend sequence to Objective → Key Results (from the founder's selected core assumptions) → Publish → Cycle (with `sourceObjectiveId`) → Week → Commitment → Tasks, fixes both backend gaps that block that sequence from working, and replaces the silent `catch`-and-continue with real failure surfacing.

**Tech Stack:** Encore.ts/TypeScript (`services/company`), Drizzle ORM, `encore test` (vitest under the hood), Flutter/Dart, GetX controller, `flutter_test`.

## Global Constraints

- Handlers must not import Drizzle/`db`/schema directly — only call service functions (existing repo rule).
- No `any`, `@ts-ignore`, or `@ts-expect-error` in any TypeScript change.
- All new/changed comments explaining *why* (not *what*) go in Vietnamese, per repo convention; identifiers/log/error strings stay in English/as-is.
- Publishing an Objective requires 1–3 Key Results (`okr.service.ts:259-263`) and, under the default `FOUNDER_ONLY` workspace policy, caller role `founder`/`co-founder` (`strategy-governance-authorization.service.ts:53-59`) — tests must use `createTestWorkspaceWithMember({ role: "founder" })`.
- Do not touch `advanceCycleWeekAuthorized`, `weekly_plans` skeleton materialization, or any other Task 5 (2026-09-14 remediation) behavior — out of scope, already correct.
- After the TS changes: run `cd services/company && npx vitest run <new test file>`, then `make company-boundary-check` and `make encore-handler-boundary-check` before considering Task 1 done.
- After the Dart changes: run `cd frontend && flutter test test/modules/projects/...` for the touched files, then `make frontend-analyze`.

---

## File Structure

| File | Responsibility |
|---|---|
| `services/company/operations/handlers/project-operating-loop.handler.ts` | Add `sourceObjectiveId` to `CreateCycleBody` and forward it; add `baselineValue`/`currentValue` to `CreateKeyResultBody` and forward them |
| `services/company/operations/services/project-operating-loop.service.ts` | `createKeyResultAuthorized`: accept and persist `baselineValue`/`currentValue` (default `0` when omitted) |
| `services/company/operations/tests/project-operating-loop-objective-cycle-linkage.handler.test.ts` (new) | End-to-end regression test proving Objective → KR → Publish → Cycle(sourceObjectiveId) actually links and publishes |
| `frontend/lib/modules/projects/services/project_operating_loop_service.dart` | `createCycle()`: add `sourceObjectiveId` param; `createKeyResult()`: add `baselineValue`/`currentValue` params |
| `frontend/test/modules/projects/services/project_operating_loop_service_test.dart` | Extend to cover the new request fields |
| `frontend/lib/modules/projects/controllers/project_analysis_flow_controller.dart` | Reorder `submitAndActivate()`; replace silent-swallow error handling with real failure surfacing |
| `frontend/test/modules/projects/controllers/project_analysis_flow_controller_test.dart` (new) | Verify the corrected call order and that failures surface in `errorMessage` / return value |

---

### Task 1: Backend — link Cycle to Objective and make Key Results publishable

**Files:**
- Modify: `services/company/operations/handlers/project-operating-loop.handler.ts:54-62` (`CreateCycleBody`), `:38-44` (`CreateKeyResultBody`), `:123-134` (`createObjectiveApi` — unchanged, just for reference when writing the test), `:136-149` (`createKeyResultApi`), `:166-181` (`createCycleApi`)
- Modify: `services/company/operations/services/project-operating-loop.service.ts:397-439` (`createKeyResultAuthorized`)
- Test: `services/company/operations/tests/project-operating-loop-objective-cycle-linkage.handler.test.ts` (new)

**Interfaces:**
- Consumes: existing `createObjectiveApi`, `createKeyResultApi`, `createCycleApi` (`project-operating-loop.handler.ts`), `publishObjective` (`okr.handler.ts:189-203`), `createTestWorkspaceWithMember` (`tests/_helpers.ts`, returns `{ workspaceId, userId, bearerToken, projectId }`)
- Produces: `createCycleApi` request body gains `sourceObjectiveId?: string | null`; `createKeyResultApi` request body gains `baselineValue?: number | null`, `currentValue?: number | null`. Both are consumed by Task 2/3's Dart service layer.

- [ ] **Step 1: Write the failing end-to-end test**

Create `services/company/operations/tests/project-operating-loop-objective-cycle-linkage.handler.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { createTestWorkspaceWithMember } from "./_helpers";
import {
  createObjectiveApi,
  createKeyResultApi,
  createCycleApi,
} from "../handlers/project-operating-loop.handler";
import { publishObjective } from "../handlers/okr.handler";

describe("P0 analysis flow — Objective/KeyResult/Cycle end-to-end linkage", () => {
  it("creates a publishable objective and links a new cycle to it via sourceObjectiveId", async () => {
    const w = await createTestWorkspaceWithMember({ role: "founder" });

    const objective = await createObjectiveApi({
      authorization: w.bearerToken,
      workspaceId: w.workspaceId,
      projectId: w.projectId,
      title: "[P0] Xác định rõ tệp khách hàng tiên phong",
      why: "Khách hàng: Founder - Vấn đề: pháp lý",
    });
    expect(objective.status).toBe("draft");

    const kr = await createKeyResultApi({
      authorization: w.bearerToken,
      workspaceId: w.workspaceId,
      projectId: w.projectId,
      objectiveId: objective.id,
      title: "Giả định cốt lõi #1 đã được kiểm chứng",
      targetValue: 1,
      unit: "validated",
      baselineValue: 0,
      currentValue: 0,
    });
    expect(kr.objectiveId).toBe(objective.id);

    const published = await publishObjective({
      id: objective.id,
      authorization: w.bearerToken,
      workspaceId: w.workspaceId,
    });
    expect(published.status).toBe("published");

    const cycle = await createCycleApi({
      authorization: w.bearerToken,
      workspaceId: w.workspaceId,
      projectId: w.projectId,
      durationWeeks: 2,
      sourceObjectiveId: objective.id,
    });

    expect(cycle.sourceObjectiveId).toBe(objective.id);
    expect(cycle.durationWeeks).toBe(2);
  });

  it("still refuses to publish an objective with an unset baseline/current/target/unit", async () => {
    const w = await createTestWorkspaceWithMember({ role: "founder" });

    const objective = await createObjectiveApi({
      authorization: w.bearerToken,
      workspaceId: w.workspaceId,
      projectId: w.projectId,
      title: "Objective without a real KR",
    });

    await createKeyResultApi({
      authorization: w.bearerToken,
      workspaceId: w.workspaceId,
      projectId: w.projectId,
      objectiveId: objective.id,
      title: "Bare title, no target/unit",
    });

    await expect(
      publishObjective({
        id: objective.id,
        authorization: w.bearerToken,
        workspaceId: w.workspaceId,
      })
    ).rejects.toThrow(/valid targetValue|valid unit/i);
  });
});
```

- [ ] **Step 2: Run the test and record the ACTUAL failure**

Run: `cd services/company && npx vitest run tests/project-operating-loop-objective-cycle-linkage.handler.test.ts`

Expected (first run, before any fix): the first test fails. Read the exact error — it will fail either at `expect(cycle.sourceObjectiveId).toBe(objective.id)` (received `null`/`undefined`, because `createCycleApi` drops the field) or earlier at the `publishObjective` call (`APIError.failedPrecondition` naming `baselineValue` or `currentValue`, because `createKeyResultAuthorized` never sets them even though the test passed them in). Do not assume which one fails first — fix exactly what the error message names, in the order the test hits them.

- [ ] **Step 3: Fix `createKeyResultAuthorized` to accept and persist baseline/current value**

In `services/company/operations/services/project-operating-loop.service.ts`, replace the function at lines 397-439:

```typescript
export async function createKeyResultAuthorized(
  ctx: TenantContext,
  req: {
    projectId: string;
    objectiveId: string;
    title: string;
    metricId?: string | null;
    targetValue?: number | null;
    unit?: string | null;
    // Fix (2026-09-15) — trước đây 2 field này không có cách nào set qua API
    // công khai, khiến publishObjectiveService (yêu cầu cả 2 non-null) luôn
    // reject bất kỳ Key Result nào tạo qua endpoint này. Default 0 khi không
    // truyền, giống cách `scoringType` đã default "LINEAR_INCREASE" ở dưới.
    baselineValue?: number | null;
    currentValue?: number | null;
  }
): Promise<KeyResultDto> {
  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(req.projectId);
  const objId = BigInt(req.objectiveId);
  await verifyProjectInWorkspace(wsId, pId);

  const [obj] = await db
    .select()
    .from(okrObjectives)
    .where(and(eq(okrObjectives.id, objId), eq(okrObjectives.workspaceId, wsId), eq(okrObjectives.projectId, pId)));

  if (!obj) {
    throw APIError.invalidArgument("Objective does not belong to project/workspace");
  }

  const [row] = await db
    .insert(keyResults)
    .values({
      id: generateSnowflake(),
      workspaceId: wsId,
      objectiveId: objId,
      title: req.title,
      metricId: req.metricId ? BigInt(req.metricId) : null,
      targetValue: req.targetValue ?? null,
      unit: req.unit || null,
      baselineValue: req.baselineValue ?? 0,
      currentValue: req.currentValue ?? 0,
      scoringType: "LINEAR_INCREASE",
      status: "draft",
    })
    .returning();

  if (!row) throw APIError.internal("Failed to create key result");
  return toKeyResult(row);
}
```

- [ ] **Step 4: Forward the new fields through the handler layer**

In `services/company/operations/handlers/project-operating-loop.handler.ts`, update `CreateKeyResultBody` (lines 38-44):

```typescript
export interface CreateKeyResultBody {
  objectiveId: string;
  title: string;
  metricId?: string | null;
  targetValue?: number | null;
  unit?: string | null;
  baselineValue?: number | null;
  currentValue?: number | null;
}
```

And `createKeyResultApi` (lines 136-149):

```typescript
export const createKeyResultApi = api(
  { expose: true, method: "POST", path: "/operations/projects/:projectId/operating-loop/key-results" },
  async (params: ProjectLoopParams & CreateKeyResultBody): Promise<KeyResultDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createKeyResultAuthorized(ctx, {
      projectId: params.projectId,
      objectiveId: params.objectiveId,
      title: params.title,
      metricId: params.metricId,
      targetValue: params.targetValue,
      unit: params.unit,
      baselineValue: params.baselineValue,
      currentValue: params.currentValue,
    });
  }
);
```

Update `CreateCycleBody` (lines 54-62):

```typescript
export interface CreateCycleBody {
  theme?: string | null;
  visionStatement?: string | null;
  durationWeeks?: number;
  timezone?: string;
  startLocalDate?: string;
  startDate?: string;
  endDate?: string;
  sourceObjectiveId?: string | null;
}
```

And `createCycleApi` (lines 166-181):

```typescript
export const createCycleApi = api(
  { expose: true, method: "POST", path: "/operations/projects/:projectId/operating-loop/cycles" },
  async (params: ProjectLoopParams & CreateCycleBody): Promise<CycleDto> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return createCycleAuthorized(ctx, {
      projectId: params.projectId,
      theme: params.theme,
      visionStatement: params.visionStatement,
      durationWeeks: params.durationWeeks,
      timezone: params.timezone,
      startLocalDate: params.startLocalDate,
      startDate: params.startDate,
      endDate: params.endDate,
      sourceObjectiveId: params.sourceObjectiveId,
    });
  }
);
```

- [ ] **Step 5: Run the test again, iterate until both cases pass**

Run: `cd services/company && npx vitest run tests/project-operating-loop-objective-cycle-linkage.handler.test.ts`
Expected: both tests PASS. If the first test still fails, read the new error and fix only what it names — do not pre-emptively change anything not named by the failure.

- [ ] **Step 6: Run the full operations test suite to check for regressions**

Run: `cd services/company && npx vitest run operations/tests/project-operating-loop.service.test.ts operations/tests/project-operating-loop-objective-cycle-linkage.handler.test.ts`
Expected: all PASS (the pre-existing `project-operating-loop.service.test.ts` never passes `baselineValue`/`currentValue`, so it must keep passing unchanged with the `?? 0` defaults).

- [ ] **Step 7: Boundary checks**

Run: `cd /Volumes/SSD/javis-saas && make company-boundary-check && make encore-handler-boundary-check`
Expected: both pass (no new `db`/Drizzle import was added to the handler file).

- [ ] **Step 8: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/company/operations/handlers/project-operating-loop.handler.ts \
        services/company/operations/services/project-operating-loop.service.ts \
        services/company/operations/tests/project-operating-loop-objective-cycle-linkage.handler.test.ts
git commit -m "fix(operations): link cycle to source objective and make key results publishable"
```

---

### Task 2: Frontend service layer — expose `sourceObjectiveId` and baseline/current value

**Files:**
- Modify: `frontend/lib/modules/projects/services/project_operating_loop_service.dart:95-109` (`createCycle`), `:50-70` (`createKeyResult`)
- Test: `frontend/test/modules/projects/services/project_operating_loop_service_test.dart` (extend)

**Interfaces:**
- Consumes: `MvpRequestClient`, `MvpEndpoint.projectCycleWrite`, `MvpEndpoint.projectKeyResultWrite` (unchanged endpoints, new body fields only — no contract/route change, so `make frontend-api-contract-check` is unaffected)
- Produces: `createCycle(projectId, {required durationWeeks, required startDate, String? sourceObjectiveId})`; `createKeyResult(projectId, {required objectiveId, required title, String? metricId, double? targetValue, String? unit, double? baselineValue, double? currentValue})` — both consumed by Task 3's controller.

- [ ] **Step 1: Read the existing test file to confirm the request-capturing pattern**

Read `frontend/test/modules/projects/services/project_operating_loop_service_test.dart` in full before editing — it already has a `MockClient`-based pattern for asserting outgoing request bodies for this exact service class. Reuse that pattern; do not invent a new one.

- [ ] **Step 2: Write the failing tests**

Add to `frontend/test/modules/projects/services/project_operating_loop_service_test.dart` (inside the existing `main()`/`group`, following the file's established `MockClient` + request-body-capture pattern):

```dart
test('createCycle sends sourceObjectiveId when provided', () async {
  Map<String, dynamic>? capturedBody;
  final mockHttp = MockClient((request) async {
    capturedBody = jsonDecode(request.body) as Map<String, dynamic>;
    return http.Response(
      jsonEncode({'data': {'id': 'cycle_1'}, 'meta': _testMeta()}),
      200,
      headers: {'content-type': 'application/json'},
    );
  });
  final service = ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp));

  final result = await service.createCycle(
    '42',
    durationWeeks: 2,
    startDate: '2026-09-15',
    sourceObjectiveId: 'obj_1',
  );

  expect(capturedBody?['sourceObjectiveId'], 'obj_1');
  result.when(
    success: (data, _) => expect(data['id'], 'cycle_1'),
    failure: (f) => fail('expected success, got failure: ${f.message}'),
  );
});

test('createKeyResult sends baselineValue and currentValue when provided', () async {
  Map<String, dynamic>? capturedBody;
  final mockHttp = MockClient((request) async {
    capturedBody = jsonDecode(request.body) as Map<String, dynamic>;
    return http.Response(
      jsonEncode({'data': {'id': 'kr_1'}, 'meta': _testMeta()}),
      200,
      headers: {'content-type': 'application/json'},
    );
  });
  final service = ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp));

  await service.createKeyResult(
    '42',
    objectiveId: 'obj_1',
    title: 'Giả định #1',
    targetValue: 1,
    unit: 'validated',
    baselineValue: 0,
    currentValue: 0,
  );

  expect(capturedBody?['baselineValue'], 0);
  expect(capturedBody?['currentValue'], 0);
});
```

If the file has no `_testMeta()` helper yet, add one at file scope matching whatever meta shape the file's existing tests already use for a successful envelope (copy it verbatim from an existing passing test in the same file — do not guess the shape).

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd frontend && flutter test test/modules/projects/services/project_operating_loop_service_test.dart`
Expected: FAIL — `capturedBody?['sourceObjectiveId']` and the two KR fields are absent (`null`) because the service methods don't send them yet.

- [ ] **Step 4: Implement — add the new parameters**

In `frontend/lib/modules/projects/services/project_operating_loop_service.dart`, replace `createCycle` (lines 95-109):

```dart
  Future<ApiResult<Map<String, dynamic>>> createCycle(
    String projectId, {
    required int durationWeeks,
    required String startDate,
    String? sourceObjectiveId,
  }) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.projectCycleWrite,
      pathParams: {'projectId': projectId},
      body: {
        'durationWeeks': durationWeeks,
        'startDate': startDate,
        'sourceObjectiveId': ?sourceObjectiveId,
      },
      decode: (raw) => raw is Map<String, dynamic> ? raw : {},
    );
  }
```

Replace `createKeyResult` (lines 50-70):

```dart
  // `CreateKeyResultBody` — endpoint mới Task 3 (`project.key_result.write`).
  Future<ApiResult<Map<String, dynamic>>> createKeyResult(
    String projectId, {
    required String objectiveId,
    required String title,
    String? metricId,
    double? targetValue,
    String? unit,
    double? baselineValue,
    double? currentValue,
  }) async {
    return _client.request<Map<String, dynamic>>(
      MvpEndpoint.projectKeyResultWrite,
      pathParams: {'projectId': projectId},
      body: {
        'objectiveId': objectiveId,
        'title': title,
        'metricId': ?metricId,
        'targetValue': ?targetValue,
        'unit': ?unit,
        'baselineValue': ?baselineValue,
        'currentValue': ?currentValue,
      },
      decode: (raw) => raw is Map<String, dynamic> ? raw : {},
    );
  }
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd frontend && flutter test test/modules/projects/services/project_operating_loop_service_test.dart`
Expected: PASS, including all pre-existing tests in the file (no regression).

- [ ] **Step 6: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/projects/services/project_operating_loop_service.dart \
        frontend/test/modules/projects/services/project_operating_loop_service_test.dart
git commit -m "feat(frontend): support sourceObjectiveId and KR baseline/current in operating loop service"
```

---

### Task 3: Frontend controller — fix the submit order and stop swallowing failures

**Files:**
- Modify: `frontend/lib/modules/projects/controllers/project_analysis_flow_controller.dart:1-9` (imports), `:221-331` (`submitAndActivate`)
- Test: `frontend/test/modules/projects/controllers/project_analysis_flow_controller_test.dart` (new)

**Interfaces:**
- Consumes: `ProjectOperatingLoopService.createObjective/createKeyResult/createCycle/createWeek/createCommitment/createTask` (Task 2's updated signatures), `OkrService.publishObjective(String objectiveId)` (`frontend/lib/modules/strategy/services/okr_service.dart:140-143`, already exists and already calls `POST /operations/objectives/:id/publish`)
- Produces: `submitAndActivate()` returns `Future<bool>` — `true` only when Objective+≥1 KR+Publish+Cycle all succeeded (the parts later steps depend on); `false` with a human-readable `errorMessage` set when any of those fail. Commitment/Task failures no longer abort the flow but are appended to `errorMessage` as a warning instead of being silently dropped.

- [ ] **Step 1: Write the failing controller test**

Create `frontend/test/modules/projects/controllers/project_analysis_flow_controller_test.dart`. First read `frontend/test/modules/projects/controllers/project_operating_loop_controller_test.dart` in full (already shown above) to reuse its `MockClient` + `SharedPreferences`/`SecureStorageService` setup pattern and its JSON envelope helper — do not invent a new fixture style.

```dart
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/mvp_request_client.dart';
import 'package:frontend/core/services/secure_storage_service.dart';
import 'package:frontend/data/models/stage_model.dart';
import 'package:frontend/modules/projects/controllers/project_analysis_flow_controller.dart';
import 'package:frontend/modules/projects/services/project_operating_loop_service.dart';

Map<String, dynamic> _envelope(Object? data) => {
      'data': data,
      'meta': {
        'dataState': 'populated',
        'observedAt': '2026-09-15T12:00:00Z',
        'sources': [
          {'kind': 'company_db', 'ref': 'operating'},
        ],
      },
    };

void main() {
  setUp(() async {
    SharedPreferences.setMockInitialValues({'workspace_id': '1001'});
    await SecureStorageService.write('auth_token', 'test-token');
  });

  ProjectAnalysisFlowController buildController(
    Future<http.Response> Function(http.Request) handler,
  ) {
    final mockHttp = MockClient(handler);
    final controller = ProjectAnalysisFlowController(
      projectId: '42',
      projectTitle: 'Test Project',
      initialStage: ProjectStage.p0Discovery,
    );
    // service is created internally by the controller with a default client;
    // ProjectAnalysisFlowController must accept an injectable service for
    // this test to intercept HTTP calls — see Step 3.
    controller.debugOverrideService(
      ProjectOperatingLoopService(client: MvpRequestClient(httpClient: mockHttp)),
    );
    return controller;
  }

  test('submitAndActivate creates objective before cycle and links sourceObjectiveId', () async {
    final calls = <String>[];
    final controller = buildController((request) async {
      calls.add('${request.method} ${request.url.path}');
      if (request.url.path.endsWith('/operating-loop/objectives')) {
        return http.Response(jsonEncode(_envelope({'id': 'obj_1', 'status': 'draft'})), 200);
      }
      if (request.url.path.endsWith('/operating-loop/key-results')) {
        return http.Response(jsonEncode(_envelope({'id': 'kr_1'})), 200);
      }
      if (request.url.path.endsWith('/publish')) {
        return http.Response(jsonEncode({'id': 'obj_1', 'status': 'published'}), 200);
      }
      if (request.url.path.endsWith('/operating-loop/cycles')) {
        final body = jsonDecode(request.body) as Map<String, dynamic>;
        expect(body['sourceObjectiveId'], 'obj_1');
        return http.Response(jsonEncode(_envelope({'id': 'cycle_1'})), 200);
      }
      if (request.url.path.endsWith('/operating-loop/weeks')) {
        return http.Response(jsonEncode(_envelope({'id': 'week_1'})), 200);
      }
      if (request.url.path.endsWith('/operating-loop/commitments')) {
        return http.Response(jsonEncode(_envelope({'id': 'commit_1'})), 200);
      }
      if (request.url.path.endsWith('/operating-loop/tasks')) {
        return http.Response(jsonEncode(_envelope({'id': 'task_1'})), 200);
      }
      return http.Response(jsonEncode(_envelope({})), 200);
    });

    controller.targetCustomerCtrl.text = 'Founder gặp khó khăn pháp lý';
    controller.problemStatementCtrl.text = 'Không nắm vững pháp lý';
    controller.selectedAssumptions.assignAll(['Giả định 1', 'Giả định 2']);
    controller.firstWeekOutcomeCtrl.text = 'Xác thực giải pháp';
    controller.addFirstWeekAction('Hành động 1');

    final ok = await controller.submitAndActivate();

    expect(ok, isTrue);
    expect(controller.errorMessage.value, isNull);
    final objectiveIdx = calls.indexWhere((c) => c.endsWith('/operating-loop/objectives'));
    final cycleIdx = calls.indexWhere((c) => c.endsWith('/operating-loop/cycles'));
    final publishIdx = calls.indexWhere((c) => c.endsWith('/publish'));
    expect(objectiveIdx, greaterThanOrEqualTo(0));
    expect(publishIdx, greaterThan(objectiveIdx));
    expect(cycleIdx, greaterThan(publishIdx));
  });

  test('submitAndActivate surfaces failure and returns false when objective creation fails', () async {
    final controller = buildController((request) async {
      if (request.url.path.endsWith('/operating-loop/objectives')) {
        return http.Response(jsonEncode({'error': 'boom'}), 500);
      }
      return http.Response(jsonEncode(_envelope({'id': 'x'})), 200);
    });

    controller.targetCustomerCtrl.text = 'Founder';
    controller.problemStatementCtrl.text = 'Problem';
    controller.selectedAssumptions.assignAll(['Giả định 1']);
    controller.firstWeekOutcomeCtrl.text = 'Outcome';
    controller.addFirstWeekAction('Action 1');

    final ok = await controller.submitAndActivate();

    expect(ok, isFalse);
    expect(controller.errorMessage.value, isNotNull);
  });
}
```

- [ ] **Step 2: Run the test to verify it fails to compile**

Run: `cd frontend && flutter test test/modules/projects/controllers/project_analysis_flow_controller_test.dart`
Expected: compile error — `debugOverrideService` does not exist yet on `ProjectAnalysisFlowController`.

- [ ] **Step 3: Add an injectable service to the controller**

In `frontend/lib/modules/projects/controllers/project_analysis_flow_controller.dart`, change line 21 from a `final` to a mutable field with a test-only override hook, and add the `OkrService` import:

```dart
import '../../strategy/services/okr_service.dart';
```

```dart
  ProjectOperatingLoopService _loopService = ProjectOperatingLoopService();
  OkrService _okrService = OkrService();

  /// Chỉ dùng trong test để tiêm HTTP client giả — không gọi ở code sản phẩm.
  void debugOverrideService(
    ProjectOperatingLoopService loopService, {
    OkrService? okrService,
  }) {
    _loopService = loopService;
    if (okrService != null) _okrService = okrService;
  }
```

(Replace the existing `final ProjectOperatingLoopService _loopService = ProjectOperatingLoopService();` line entirely with the block above.)

- [ ] **Step 4: Run the test again to confirm it now fails on assertions, not compilation**

Run: `cd frontend && flutter test test/modules/projects/controllers/project_analysis_flow_controller_test.dart`
Expected: compiles; both tests FAIL on assertions — the first because the call order is still cycle-before-objective with no `sourceObjectiveId`/publish/KR calls, the second because `submitAndActivate()` still always returns `true`.

- [ ] **Step 5: Rewrite `submitAndActivate()`**

Replace the entire method at `frontend/lib/modules/projects/controllers/project_analysis_flow_controller.dart:222-331` with:

```dart
  /// Kích hoạt kế hoạch phân tích và vật lý hoá vào Project Operating Loop.
  ///
  /// Thứ tự bắt buộc: Objective → Key Result(s) → Publish → Cycle (gắn
  /// `sourceObjectiveId` ngay lúc tạo) → Week → Commitment → Task. Cycle phải
  /// được tạo SAU khi Objective đã publish, nếu không cycle sẽ vĩnh viễn
  /// không gắn được với objective nào (bug gốc: cycle tạo trước, objective
  /// tạo sau, không có field nào nối 2 bên).
  Future<bool> submitAndActivate() async {
    if (!validateCurrentStep()) return false;
    isSubmitting.value = true;
    errorMessage.value = null;
    final isEn = isEnglish;
    final warnings = <String>[];

    try {
      // 1. Cập nhật lifecycleStage của Project nếu người dùng đổi stage.
      if (currentStage.value != initialStage) {
        try {
          await ApiClient.put(
            '/operations/projects/$projectId',
            body: {'lifecycleStage': currentStage.value.wireValue},
          );
        } catch (e) {
          warnings.add('lifecycleStage: $e');
        }
      }

      // 2. Tạo Objective OKR nền tảng từ Problem & Stage.
      String? objectiveId;
      final objRes = await _loopService.createObjective(
        projectId,
        title: '[${currentStage.value.code}] ${guidance.focusHeadline}',
        why: isEn
            ? 'Customer: ${targetCustomerCtrl.text.trim()} - Problem: ${problemStatementCtrl.text.trim()}'
            : 'Khách hàng: ${targetCustomerCtrl.text.trim()} - Vấn đề: ${problemStatementCtrl.text.trim()}',
      );
      objRes.when(
        success: (data, _) => objectiveId = data['id']?.toString(),
        failure: (f) => warnings.add('createObjective: ${f.message}'),
      );

      if (objectiveId == null) {
        errorMessage.value = isEn
            ? 'Could not create the strategic objective. Please try again.'
            : 'Không thể tạo mục tiêu chiến lược (Objective). Vui lòng thử lại.';
        return false;
      }

      // 3. Tạo 1..3 Key Result từ giả định cốt lõi đã chọn — publishObjective
      // (bước 4) bắt buộc objective phải có 1..3 Key Result hợp lệ mới cho
      // publish (okr.service.ts: requireStrategyGovernanceAuthority + KR
      // validation).
      var keyResultCount = 0;
      for (final assumption in selectedAssumptions.take(3)) {
        final krRes = await _loopService.createKeyResult(
          projectId,
          objectiveId: objectiveId!,
          title: assumption,
          targetValue: 1,
          unit: isEn ? 'validated' : 'đã kiểm chứng',
          baselineValue: 0,
          currentValue: 0,
        );
        krRes.when(
          success: (_, __) => keyResultCount++,
          failure: (f) => warnings.add('createKeyResult: ${f.message}'),
        );
      }

      if (keyResultCount == 0) {
        errorMessage.value = isEn
            ? 'Could not create any key result for the objective. Please try again.'
            : 'Không thể tạo Key Result nào cho mục tiêu. Vui lòng thử lại.';
        return false;
      }

      // 4. Publish Objective — nếu bỏ qua bước này, Cycle ở bước 5 sẽ liên
      // kết tới 1 objective mãi ở trạng thái draft.
      try {
        await _okrService.publishObjective(objectiveId!);
      } catch (e) {
        errorMessage.value = isEn
            ? 'Could not publish the objective: $e'
            : 'Không thể công bố (publish) mục tiêu: $e';
        return false;
      }

      // 5. Tạo Operating Cycle, gắn thẳng sourceObjectiveId ngay lúc tạo.
      final now = DateTime.now();
      final startDateStr = now.toIso8601String().split('T').first;
      String? cycleId;
      final cycleRes = await _loopService.createCycle(
        projectId,
        durationWeeks: cycleDurationWeeks.value,
        startDate: startDateStr,
        sourceObjectiveId: objectiveId,
      );
      cycleRes.when(
        success: (data, _) => cycleId = data['id']?.toString(),
        failure: (f) => warnings.add('createCycle: ${f.message}'),
      );

      if (cycleId == null) {
        errorMessage.value = isEn
            ? 'Could not create the operating cycle. Please try again.'
            : 'Không thể tạo chu kỳ hoạt động (Operating Cycle). Vui lòng thử lại.';
        return false;
      }

      // 6. Tạo Tuần 1 (Weekly Plan).
      String? weeklyPlanId;
      final weekRes = await _loopService.createWeek(
        projectId,
        cycleId: cycleId!,
        weekNo: 1,
        focus: firstWeekOutcomeCtrl.text.trim(),
      );
      weekRes.when(
        success: (data, _) => weeklyPlanId = data['id']?.toString(),
        failure: (f) => warnings.add('createWeek: ${f.message}'),
      );

      // 7. Tạo Commitment và các Action Task — không chặn submit nếu lỗi ở
      // đây, nhưng phải báo cho founder biết thay vì debugPrint âm thầm.
      if (weeklyPlanId != null) {
        String? commitmentId;
        final comRes = await _loopService.createCommitment(
          projectId,
          weeklyPlanId: weeklyPlanId!,
          title: firstWeekOutcomeCtrl.text.trim(),
        );
        comRes.when(
          success: (data, _) => commitmentId = data['id']?.toString(),
          failure: (f) => warnings.add('createCommitment: ${f.message}'),
        );

        if (commitmentId != null) {
          for (final actionTitle in firstWeekActions) {
            final taskRes = await _loopService.createTask(
              projectId,
              title: actionTitle,
              weeklyCommitmentId: commitmentId!,
              priority: 'high',
            );
            taskRes.when(
              success: (_, __) {},
              failure: (f) => warnings.add('createTask($actionTitle): ${f.message}'),
            );
          }
        } else {
          warnings.add('createCommitment did not return an id, skipping tasks');
        }
      }

      if (warnings.isNotEmpty) {
        errorMessage.value = isEn
            ? 'Plan activated with warnings: ${warnings.join('; ')}'
            : 'Kế hoạch đã kích hoạt nhưng có cảnh báo: ${warnings.join('; ')}';
      }

      return true;
    } catch (e) {
      errorMessage.value = isEn ? 'Activation error: $e' : 'Lỗi kích hoạt: $e';
      return false;
    } finally {
      isSubmitting.value = false;
    }
  }
```

- [ ] **Step 6: Run the controller test to verify it passes**

Run: `cd frontend && flutter test test/modules/projects/controllers/project_analysis_flow_controller_test.dart`
Expected: both tests PASS.

- [ ] **Step 7: Run the existing localization test for this controller to check for regressions**

Run: `cd frontend && flutter test test/modules/projects/views/project_analysis_flow_localization_test.dart`
Expected: PASS unchanged (that test covers UI copy, not `submitAndActivate` — should be unaffected, but confirm).

- [ ] **Step 8: Static analysis**

Run: `cd /Volumes/SSD/javis-saas && make frontend-analyze`
Expected: no new warnings/errors from the touched files.

- [ ] **Step 9: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/projects/controllers/project_analysis_flow_controller.dart \
        frontend/test/modules/projects/controllers/project_analysis_flow_controller_test.dart
git commit -m "fix(frontend): reorder P0 analysis submit flow and surface step failures"
```

---

## Manual Verification (after all 3 tasks)

- [ ] Run `make dev-stack` (or confirm it's already up), open the app, create a fresh Workspace + Project, go through the P0 "Phân tích & Lập Kế hoạch Tuần" wizard end-to-end with real customer/problem text and at least one core assumption, and submit.
- [ ] Re-run the exact DB queries used during this debugging session against the live `workspace` database to confirm on a NEW project (not the old broken one from this conversation):
  ```bash
  docker exec cosa_postgres psql -U postgres -d workspace -c \
    "select c.id, c.status, c.source_objective_id, o.id as objective_id, o.status as objective_status \
     from operating.twelve_week_cycles c \
     left join strategy.okr_objectives o on o.id = c.source_objective_id \
     where c.project_id = <new_project_id> order by c.created_at desc limit 1;"
  ```
  Expected: `source_objective_id` is non-null and equals `objective_id`; `objective_status = 'published'`.
- [ ] Confirm the Hub dashboard now shows the created objective/mission instead of "0/0".
- [ ] The old broken project (`project_id = 716178278192250880`) from this debugging session is NOT touched by this plan — it stays orphaned. Ask the user separately whether they want a one-off data-repair (publish its existing draft objective + backfill `source_objective_id` on its cycle) or want to just discard/recreate that project; this plan does not include a data-migration task because that's a decision for the user, not an automatic side effect of a bug fix.
