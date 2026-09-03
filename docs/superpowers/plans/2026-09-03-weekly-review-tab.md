# Tab "Review tuần" trong module 12WY — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thêm khả năng chấm `executionScore`/`outcomeScore`/`reflection` cho 1 `weekly_plans` đã tồn tại (backend + frontend), hiển thị qua 1 tab mới "Review tuần" trong `StrategyView`.

**Architecture:** Thêm `updateWeeklyPlanService` ở backend (Encore/Drizzle), đăng ký qua contract `shared/contracts/mvp-surface.json` (nguồn sự thật duy nhất cho route MVP, sinh code 2 phía qua `node scripts/gen-mvp-contracts.mjs`). Frontend thêm `StrategyMvpClient.updateWeeklyPlan()` + `TwelveWyService.updateWeeklyPlan()`, rồi 1 tab mới `WeeklyReviewTab` đọc `TwelveWyService.getWeeklyPlans()`/`getWeeklyCommitments()` (đã tồn tại) và gọi hàm update mới khi Founder lưu review.

**Tech Stack:** Encore.ts, Drizzle ORM, Flutter/GetX, hệ thống contract-gen MVP (`shared/contracts/mvp-surface.json`).

## Global Constraints

- `executionScore`/`outcomeScore` dùng thang **0.0 → 100.0** — đã xác nhận khớp
  `WeeklyExecutionGauge.score` (`frontend/lib/modules/hologram_hub/widgets/twelve_wy/weekly_execution_gauge.dart:4`,
  comment `// 0.0 -> 100.0%`). Validate ở backend: `0 <= score <= 100`.
- Route mới PHẢI đi qua `shared/contracts/mvp-surface.json` + `node scripts/gen-mvp-contracts.mjs`
  — không tự viết `MvpEndpoint` tay, không gọi endpoint bằng string cứng ở
  frontend (CLAUDE.md Encore Guardrail #7, `make frontend-api-contract-check`).
- Không tạo tuần mới (weekNo mới) trong plan này — chỉ update `weekly_plans`
  đã tồn tại.
- Không đổi `weekly_execution_gauge.dart`/`TwelveWyDashboardModel` — đã xác
  nhận `currentWeekExecutionScore` hiện đọc từ `overallExecutionScore` CỦA
  CẢ CYCLE (`twelve_wy_service.dart:35-46`), không phải điểm riêng từng tuần
  — đây là hạn chế có sẵn, KHÔNG sửa trong plan này (ngoài phạm vi spec §3).
  Tab mới đọc trực tiếp từ danh sách `weekly_plans` thật qua
  `TwelveWyService.getWeeklyPlans()`, không qua `getDashboard()`.

---

## Task 1: Backend — `updateWeeklyPlanService`

**Files:**
- Modify: `services/company/operations/services/twelve-week-year.service.ts`
- Test: `services/company/operations/tests/twelve-week-plan-update.test.ts`

**Interfaces:**
- Consumes: `WeeklyPlan` (interface đã tồn tại, dòng 39-52), `weeklyPlans` (Drizzle schema, đã import), `requireWorkspaceAccess` (đã dùng ở các hàm khác trong cùng file).
- Produces: `UpdateWeeklyPlanRequest` (interface mới), `updateWeeklyPlanService(planId: string, req: UpdateWeeklyPlanRequest): Promise<WeeklyPlan>` — dùng ở Task 2.

- [ ] **Step 1: Viết test trước**

```ts
// services/company/operations/tests/twelve-week-plan-update.test.ts
import { describe, expect, it } from "vitest";
import { createTestSession } from "../../identity/tests/helpers/test-session";
import { createCycle, createWeeklyPlan } from "../handlers/twelve-week-year.handler";
import { updateWeeklyPlanService } from "../services/twelve-week-year.service";

async function makeAuthedWorkspace(displayName: string) {
  const user = await createTestSession({
    email: `${displayName.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`,
    displayName,
  });
  return { workspaceId: user.workspaceId, authorization: `Bearer ${user.accessToken}` };
}

describe("updateWeeklyPlanService", () => {
  it("updates executionScore, outcomeScore and reflection", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Weekly Review Test");
    const cycle = await createCycle({ workspaceId, authorization, theme: "Blitz", visionStatement: "MVP", durationWeeks: 2 });
    const plan = await createWeeklyPlan({ workspaceId, authorization, cycleId: cycle.id, weekNo: 1, focus: "Tuần 1" });

    const updated = await updateWeeklyPlanService(plan.id, {
      workspaceId,
      authorization,
      executionScore: 85.5,
      outcomeScore: 70,
      reflection: "Đã hoàn thành hầu hết cam kết, cần cải thiện tốc độ phản hồi khách hàng.",
    });

    expect(updated.executionScore).toBe(85.5);
    expect(updated.outcomeScore).toBe(70);
    expect(updated.reflection).toBe("Đã hoàn thành hầu hết cam kết, cần cải thiện tốc độ phản hồi khách hàng.");
  });

  it("rejects executionScore out of 0-100 range", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Weekly Review Range Test");
    const cycle = await createCycle({ workspaceId, authorization, theme: "Blitz", visionStatement: "MVP", durationWeeks: 2 });
    const plan = await createWeeklyPlan({ workspaceId, authorization, cycleId: cycle.id, weekNo: 1, focus: "Tuần 1" });

    await expect(
      updateWeeklyPlanService(plan.id, { workspaceId, authorization, executionScore: 150 })
    ).rejects.toThrow(/executionScore/i);
  });

  it("rejects cross-workspace update with not_found or permission_denied", async () => {
    const wsA = await makeAuthedWorkspace("Workspace A Weekly");
    const wsB = await makeAuthedWorkspace("Workspace B Weekly");
    const cycle = await createCycle({ workspaceId: wsA.workspaceId, authorization: wsA.authorization, theme: "A", visionStatement: "A", durationWeeks: 2 });
    const plan = await createWeeklyPlan({ workspaceId: wsA.workspaceId, authorization: wsA.authorization, cycleId: cycle.id, weekNo: 1, focus: "A" });

    await expect(
      updateWeeklyPlanService(plan.id, { workspaceId: wsB.workspaceId, authorization: wsB.authorization, executionScore: 50 })
    ).rejects.toThrow();
  });
});
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd services/company && npx vitest run operations/tests/twelve-week-plan-update.test.ts`
Expected: FAIL — `updateWeeklyPlanService` chưa tồn tại.

- [ ] **Step 3: Viết `updateWeeklyPlanService`**

Thêm vào `services/company/operations/services/twelve-week-year.service.ts`,
ngay sau `createWeeklyPlanService` (sau dòng 177):

```ts
export interface UpdateWeeklyPlanRequest {
  workspaceId: string | number;
  authorization?: string;
  executionScore?: number | null;
  outcomeScore?: number | null;
  reflection?: string | null;
}

export async function updateWeeklyPlanService(
  planId: string,
  req: UpdateWeeklyPlanRequest
): Promise<WeeklyPlan> {
  const ctx = await requireWorkspaceAccess(req.authorization, String(req.workspaceId));
  const wsId = BigInt(ctx.workspaceId);
  const planIdBig = BigInt(planId);

  if (req.executionScore !== undefined && req.executionScore !== null) {
    if (req.executionScore < 0 || req.executionScore > 100) {
      throw APIError.invalidArgument("executionScore must be between 0 and 100");
    }
  }
  if (req.outcomeScore !== undefined && req.outcomeScore !== null) {
    if (req.outcomeScore < 0 || req.outcomeScore > 100) {
      throw APIError.invalidArgument("outcomeScore must be between 0 and 100");
    }
  }

  const [existing] = await db
    .select()
    .from(weeklyPlans)
    .where(and(eq(weeklyPlans.id, planIdBig), eq(weeklyPlans.workspaceId, wsId)))
    .limit(1);

  if (!existing) {
    throw APIError.notFound(`weekly plan ${planId} not found`);
  }

  const [updated] = await db
    .update(weeklyPlans)
    .set({
      executionScore: req.executionScore !== undefined ? req.executionScore : existing.executionScore,
      outcomeScore: req.outcomeScore !== undefined ? req.outcomeScore : existing.outcomeScore,
      reflection: req.reflection !== undefined ? req.reflection : existing.reflection,
      updatedAt: new Date(),
    })
    .where(eq(weeklyPlans.id, planIdBig))
    .returning();

  return {
    id: updated.id.toString(),
    workspaceId: updated.workspaceId.toString(),
    cycleId: updated.cycleId.toString(),
    weekNo: updated.weekNo,
    startDate: updated.startDate ? updated.startDate.toISOString() : null,
    endDate: updated.endDate ? updated.endDate.toISOString() : null,
    focus: updated.focus,
    mission: updated.mission,
    executionScore: updated.executionScore,
    outcomeScore: updated.outcomeScore,
    reflection: updated.reflection,
    createdAt: updated.createdAt.toISOString(),
  };
}
```

Cần thêm `APIError` vào import đầu file nếu chưa có
(`import { APIError } from "encore.dev/api";`) — kiểm tra import hiện có của
file trước khi thêm trùng.

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd services/company && npx vitest run operations/tests/twelve-week-plan-update.test.ts`
Expected: PASS (cả 3 test).

- [ ] **Step 5: `npx tsc --noEmit` sạch**

Run: `cd services/company && npx tsc --noEmit -p tsconfig.json`
Expected: Không lỗi.

- [ ] **Step 6: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/company/operations/services/twelve-week-year.service.ts \
  services/company/operations/tests/twelve-week-plan-update.test.ts
git commit -m "feat(company): updateWeeklyPlanService cham executionScore/outcomeScore/reflection

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: Backend handler + contract MVP + regenerate

**Files:**
- Modify: `shared/contracts/mvp-surface.json`
- Modify: `services/company/operations/handlers/twelve-week-year.handler.ts`
- Generated (chạy script, không tự sửa tay): `services/company/shared/contracts/mvp-surface.generated.ts`, `frontend/lib/core/network/mvp_endpoints.g.dart`
- Test: `services/company/operations/tests/mvp-okr-twelve-week.test.ts` (thêm case mới vào file đã có)

**Interfaces:**
- Consumes: `updateWeeklyPlanService` (Task 1).
- Produces: endpoint Encore `PATCH /operations/twelve-week-plans/:id`, entry `MvpEndpoint.strategyTwelveWeekPlanUpdate` (Dart, tự sinh) — dùng ở Task 3.

- [ ] **Step 1: Thêm entry vào `shared/contracts/mvp-surface.json`**

Tìm object có `"id": "strategy.twelve_week.plan.list"` trong mảng
`capabilities`, thêm 1 object MỚI ngay sau nó (giữ định dạng JSON hợp lệ,
dấu phẩy đúng chỗ):

```json
{
  "id": "strategy.twelve_week.plan.update",
  "enabled": true,
  "owner": "company-operations",
  "plane": "company",
  "method": "PATCH",
  "path": "/operations/twelve-week-plans/:id",
  "schema": "strategy.twelve_week.plan.update.v1",
  "source_kind": "company_db",
  "requires_workspace": true,
  "frontend_symbol": "StrategyMvpClient.updateWeeklyPlan",
  "backend_test": "services/company/operations/tests/mvp-okr-twelve-week.test.ts",
  "flutter_test": "frontend/test/strategy_mvp_service_test.dart",
  "integration_test": "tests/e2e/test_mvp_strategy_runtime_http.py"
}
```

- [ ] **Step 2: Thêm handler Encore**

Thêm vào `services/company/operations/handlers/twelve-week-year.handler.ts`,
ngay sau `createWeeklyPlan` (sau dòng 44):

```ts
export const updateWeeklyPlan = api(
  { expose: true, method: "PATCH", path: "/operations/twelve-week-plans/:id" },
  async ({
    id,
    authorization,
    workspaceId,
    executionScore,
    outcomeScore,
    reflection,
  }: {
    id: string;
    authorization?: Header<"Authorization">;
    workspaceId: Header<"X-Workspace-Id">;
    executionScore?: number | null;
    outcomeScore?: number | null;
    reflection?: string | null;
  }): Promise<WeeklyPlan> => {
    const { updateWeeklyPlanService } = await import("../services/twelve-week-year.service");
    return updateWeeklyPlanService(id, {
      workspaceId,
      authorization,
      executionScore,
      outcomeScore,
      reflection,
    });
  }
);
```

- [ ] **Step 3: Regenerate contract code**

Run: `cd /Volumes/SSD/javis-saas && node scripts/gen-mvp-contracts.mjs`
Expected: Log xác nhận đã ghi lại
`services/company/shared/contracts/mvp-surface.generated.ts` và
`frontend/lib/core/network/mvp_endpoints.g.dart`, không lỗi parse JSON.

- [ ] **Step 4: Xác nhận `strategyTwelveWeekPlanUpdate` đã xuất hiện trong file sinh ra**

Run: `grep -n "strategyTwelveWeekPlanUpdate" frontend/lib/core/network/mvp_endpoints.g.dart`
Expected: thấy đúng 1 entry với `method: 'PATCH'`, `path: '/operations/twelve-week-plans/:id'`.

- [ ] **Step 5: Thêm test tích hợp mới vào `mvp-okr-twelve-week.test.ts`**

Thêm import `updateWeeklyPlan` vào khối import đã có
(`from "../handlers/twelve-week-year.handler"`), thêm 1 `it()` mới vào
`describe("MVP OKR & 12-Week Contracts", ...)`:

```ts
  it("updates a weekly plan's review fields via the MVP endpoint", async () => {
    const { workspaceId, authorization } = await makeAuthedWorkspace("Weekly Review MVP Test");

    const cycle = await createCycle({ workspaceId, authorization, theme: "Blitz", visionStatement: "MVP", durationWeeks: 2 });
    const plan = await createWeeklyPlan({ workspaceId, authorization, cycleId: cycle.id, weekNo: 1, focus: "Tuần 1" });

    const updated = await updateWeeklyPlan({
      id: plan.id,
      workspaceId,
      authorization,
      executionScore: 90,
      outcomeScore: 80,
      reflection: "Tốt",
    });

    expect(updated.executionScore).toBe(90);
    expect(updated.outcomeScore).toBe(80);
    expect(updated.reflection).toBe("Tốt");
  });
```

- [ ] **Step 6: Chạy test, xác nhận PASS**

Run: `cd services/company && npx vitest run operations/tests/mvp-okr-twelve-week.test.ts`
Expected: PASS (kể cả các test cũ trong file — không regression).

- [ ] **Step 7: `npx tsc --noEmit` sạch cả 2 phía**

Run: `cd services/company && npx tsc --noEmit -p tsconfig.json`
Run: `cd frontend && dart analyze lib/core/network/`
Expected: Không lỗi ở cả 2.

- [ ] **Step 8: Chạy `make frontend-api-contract-check`**

Run: `cd /Volumes/SSD/javis-saas && make frontend-api-contract-check`
Expected: `✅` — route mới khớp contract, không có route lạ/lệch.

- [ ] **Step 9: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add shared/contracts/mvp-surface.json \
  services/company/shared/contracts/mvp-surface.generated.ts \
  frontend/lib/core/network/mvp_endpoints.g.dart \
  services/company/operations/handlers/twelve-week-year.handler.ts \
  services/company/operations/tests/mvp-okr-twelve-week.test.ts
git commit -m "feat(company): PATCH /operations/twelve-week-plans/:id qua contract MVP

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: Frontend — `StrategyMvpClient.updateWeeklyPlan` + `TwelveWyService.updateWeeklyPlan`

**Files:**
- Modify: `frontend/lib/modules/strategy/services/strategy_mvp_client.dart`
- Modify: `frontend/lib/modules/strategy/services/twelve_wy_service.dart`
- Test: `frontend/test/strategy_mvp_service_test.dart` (thêm case mới vào file đã có)

**Interfaces:**
- Consumes: `MvpEndpoint.strategyTwelveWeekPlanUpdate` (Task 2, tự sinh), `MvpWeeklyPlan` (đã tồn tại, `frontend/lib/modules/strategy/models/mvp_strategy_models.dart:273-`).
- Produces: `StrategyMvpClient.updateWeeklyPlan({required String id, double? executionScore, double? outcomeScore, String? reflection}) → Future<ApiResult<MvpWeeklyPlan>>`, `TwelveWyService.updateWeeklyPlan(...) → Future<ApiResult<MvpWeeklyPlan>>` (chữ ký giống hệt, chỉ forward) — dùng ở Task 4.

- [ ] **Step 1: Viết test trước — đọc `test/strategy_mvp_service_test.dart` để bám đúng pattern mock hiện có, rồi thêm case mới**

```dart
// thêm vào frontend/test/strategy_mvp_service_test.dart, theo đúng pattern
// MockClient đã dùng cho listTwelveWeekPlans/updateCanvas trong file này
test('updateWeeklyPlan sends PATCH with review fields and decodes response', () async {
  ApiClient.client = MockClient((request) async {
    expect(request.method, 'PATCH');
    expect(request.url.path, '/operations/twelve-week-plans/plan-1');
    final body = jsonDecode(request.body) as Map<String, dynamic>;
    expect(body['executionScore'], 90);
    expect(body['outcomeScore'], 80);
    expect(body['reflection'], 'Tốt');
    return http.Response(
      jsonEncode({
        'id': 'plan-1',
        'workspaceId': 'workspace-1',
        'cycleId': 'cycle-1',
        'weekNo': 1,
        'executionScore': 90,
        'outcomeScore': 80,
        'reflection': 'Tốt',
        'createdAt': DateTime.now().toIso8601String(),
      }),
      200,
    );
  });

  final result = await StrategyMvpClient().updateWeeklyPlan(
    id: 'plan-1',
    executionScore: 90,
    outcomeScore: 80,
    reflection: 'Tốt',
  );

  expect(result, isA<ApiSuccess<MvpWeeklyPlan>>());
  expect((result as ApiSuccess<MvpWeeklyPlan>).data.executionScore, 90);
});
```

Đọc phần đầu `strategy_mvp_service_test.dart` (import, `setUp`/`tearDown`
`ApiClient.client`) trước khi thêm — dùng ĐÚNG helper/setup đã có trong file,
không tạo bộ setup thứ 2.

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd frontend && flutter test test/strategy_mvp_service_test.dart --plain-name "updateWeeklyPlan"`
Expected: FAIL — `updateWeeklyPlan` chưa tồn tại trên `StrategyMvpClient`.

- [ ] **Step 3: Viết `StrategyMvpClient.updateWeeklyPlan`**

Thêm vào `frontend/lib/modules/strategy/services/strategy_mvp_client.dart`,
ngay sau `listTwelveWeekPlans` (dòng 193-203):

```dart
  Future<ApiResult<MvpWeeklyPlan>> updateWeeklyPlan({
    required String id,
    double? executionScore,
    double? outcomeScore,
    String? reflection,
  }) async {
    return _client.request<MvpWeeklyPlan>(
      MvpEndpoint.strategyTwelveWeekPlanUpdate,
      pathParams: {'id': id},
      body: {
        'executionScore': ?executionScore,
        'outcomeScore': ?outcomeScore,
        'reflection': ?reflection,
      },
      decode: (json) => MvpWeeklyPlan.fromJson(json as Map<String, dynamic>),
    );
  }
```

Cú pháp `'key': ?value` (null-aware spread trong map literal) đã được dùng ở
`updateCanvas` (dòng 58-59) trong cùng file — dùng đúng cú pháp đó, không đổi
cách khác.

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd frontend && flutter test test/strategy_mvp_service_test.dart --plain-name "updateWeeklyPlan"`
Expected: PASS.

- [ ] **Step 5: Thêm `TwelveWyService.updateWeeklyPlan` (forward mỏng)**

Thêm vào `frontend/lib/modules/strategy/services/twelve_wy_service.dart`,
ngay sau `getWeeklyCommitments` (cuối file, trước dấu `}` đóng class):

```dart
  Future<ApiResult<MvpWeeklyPlan>> updateWeeklyPlan({
    required String id,
    double? executionScore,
    double? outcomeScore,
    String? reflection,
  }) async {
    return _client.updateWeeklyPlan(
      id: id,
      executionScore: executionScore,
      outcomeScore: outcomeScore,
      reflection: reflection,
    );
  }
```

Kiểm tra `MvpWeeklyPlan` đã được import trong file này (dùng bởi
`getWeeklyPlans()` sẵn) — không cần thêm import mới.

- [ ] **Step 6: Viết test cho forward method**

```dart
// frontend/test/modules/strategy/services/twelve_wy_service_test.dart — thêm test mới vào file đã có
test('updateWeeklyPlan forwards to StrategyMvpClient.updateWeeklyPlan', () async {
  ApiClient.client = MockClient((request) async {
    expect(request.method, 'PATCH');
    return http.Response(
      jsonEncode({
        'id': 'plan-1',
        'workspaceId': 'workspace-1',
        'cycleId': 'cycle-1',
        'weekNo': 1,
        'executionScore': 60,
        'createdAt': DateTime.now().toIso8601String(),
      }),
      200,
    );
  });

  final result = await TwelveWyService().updateWeeklyPlan(id: 'plan-1', executionScore: 60);
  expect(result, isA<ApiSuccess<MvpWeeklyPlan>>());
});
```

Đọc file `twelve_wy_service_test.dart` trước để dùng đúng `setUp`/import
`ApiClient` đã có trong file (theo đúng pattern các test khác trong đó).

- [ ] **Step 7: Chạy lại toàn bộ 2 file test, `dart analyze` sạch**

Run: `cd frontend && flutter test test/strategy_mvp_service_test.dart test/modules/strategy/services/twelve_wy_service_test.dart && dart analyze lib/modules/strategy/services/`
Expected: Tất cả PASS; No issues found.

- [ ] **Step 8: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/strategy/services/strategy_mvp_client.dart \
  frontend/lib/modules/strategy/services/twelve_wy_service.dart \
  frontend/test/strategy_mvp_service_test.dart \
  frontend/test/modules/strategy/services/twelve_wy_service_test.dart
git commit -m "feat(strategy): StrategyMvpClient/TwelveWyService.updateWeeklyPlan

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: `WeeklyReviewTab` — tab thứ 7 trong `StrategyView`

**Files:**
- Create: `frontend/lib/modules/strategy/views/tabs/weekly_review_tab.dart`
- Modify: `frontend/lib/modules/strategy/views/strategy_view.dart`
- Test: `frontend/test/modules/strategy/views/tabs/weekly_review_tab_test.dart`

**Interfaces:**
- Consumes: `TwelveWyService.getWeeklyPlans()`, `getWeeklyCommitments()`, `updateWeeklyPlan(...)` (Task 3), `MvpWeeklyPlan`, `MvpWeeklyCommitment`.

- [ ] **Step 1: Viết test trước — chọn plan, hiển thị commitment, lưu review gọi đúng service**

```dart
// frontend/test/modules/strategy/views/tabs/weekly_review_tab_test.dart
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:get/get.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:frontend/core/network/api_client.dart';
import 'package:frontend/modules/strategy/views/tabs/weekly_review_tab.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late http.Client realClient;

  setUp(() {
    realClient = ApiClient.client;
    SharedPreferences.setMockInitialValues({'workspace_id': 'workspace-1'});
  });

  tearDown(() {
    ApiClient.client = realClient;
  });

  testWidgets('shows plan focus, commitments, and saves review on submit', (
    tester,
  ) async {
    var updateCalled = false;

    ApiClient.client = MockClient((request) async {
      if (request.method == 'GET' && request.url.path == '/operations/twelve-week-plans') {
        return http.Response(
          jsonEncode([
            {
              'id': 'plan-1',
              'workspaceId': 'workspace-1',
              'cycleId': 'cycle-1',
              'weekNo': 1,
              'focus': 'Xác thực vấn đề',
              'createdAt': DateTime.now().toIso8601String(),
            },
          ]),
          200,
        );
      }
      if (request.method == 'GET' && request.url.path == '/operations/twelve-week-commitments') {
        return http.Response(
          jsonEncode([
            {
              'id': 'commit-1',
              'workspaceId': 'workspace-1',
              'weeklyPlanId': 'plan-1',
              'title': 'Phỏng vấn 5 khách hàng',
              'status': 'done',
              'createdAt': DateTime.now().toIso8601String(),
            },
          ]),
          200,
        );
      }
      if (request.method == 'PATCH' && request.url.path == '/operations/twelve-week-plans/plan-1') {
        updateCalled = true;
        return http.Response(
          jsonEncode({
            'id': 'plan-1',
            'workspaceId': 'workspace-1',
            'cycleId': 'cycle-1',
            'weekNo': 1,
            'focus': 'Xác thực vấn đề',
            'executionScore': 80,
            'createdAt': DateTime.now().toIso8601String(),
          }),
          200,
        );
      }
      return http.Response('not found', 404);
    });

    await tester.pumpWidget(
      const GetMaterialApp(home: Scaffold(body: WeeklyReviewTab())),
    );
    await tester.pumpAndSettle();

    expect(find.text('Xác thực vấn đề'), findsOneWidget);
    expect(find.text('Phỏng vấn 5 khách hàng'), findsOneWidget);

    await tester.enterText(find.byKey(const Key('execution_score_field')), '80');
    await tester.tap(find.text('Lưu review'));
    await tester.pumpAndSettle();

    expect(updateCalled, isTrue);
  });
}
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd frontend && flutter test test/modules/strategy/views/tabs/weekly_review_tab_test.dart`
Expected: FAIL — `WeeklyReviewTab` chưa tồn tại.

- [ ] **Step 3: Viết `WeeklyReviewTab`**

```dart
// frontend/lib/modules/strategy/views/tabs/weekly_review_tab.dart
import 'package:flutter/material.dart';
import '../../../../core/network/api_result.dart';
import '../../../../core/theme/app_theme.dart';
import '../../models/mvp_strategy_models.dart';
import '../../services/twelve_wy_service.dart';

class WeeklyReviewTab extends StatefulWidget {
  const WeeklyReviewTab({super.key});

  @override
  State<WeeklyReviewTab> createState() => _WeeklyReviewTabState();
}

class _WeeklyReviewTabState extends State<WeeklyReviewTab> {
  final _service = TwelveWyService();
  bool _isLoading = true;
  String? _error;
  List<MvpWeeklyPlan> _plans = [];
  List<MvpWeeklyCommitment> _commitments = [];
  MvpWeeklyPlan? _selectedPlan;

  final _executionCtrl = TextEditingController();
  final _outcomeCtrl = TextEditingController();
  final _reflectionCtrl = TextEditingController();
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _executionCtrl.dispose();
    _outcomeCtrl.dispose();
    _reflectionCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    final plansResult = await _service.getWeeklyPlans();
    final commitmentsResult = await _service.getWeeklyCommitments();

    if (plansResult is ApiSuccess<List<MvpWeeklyPlan>>) {
      _plans = plansResult.data;
    } else {
      _error = 'Không tải được danh sách tuần';
    }
    if (commitmentsResult is ApiSuccess<List<MvpWeeklyCommitment>>) {
      _commitments = commitmentsResult.data;
    }

    if (_plans.isNotEmpty) {
      _selectedPlan = _plans.reduce((a, b) => a.weekNo >= b.weekNo ? a : b);
      _executionCtrl.text = _selectedPlan?.executionScore?.toString() ?? '';
      _outcomeCtrl.text = _selectedPlan?.outcomeScore?.toString() ?? '';
      _reflectionCtrl.text = _selectedPlan?.reflection ?? '';
    }

    setState(() => _isLoading = false);
  }

  List<MvpWeeklyCommitment> get _commitmentsForSelectedPlan {
    final planId = _selectedPlan?.id;
    if (planId == null) return [];
    return _commitments.where((c) => c.weeklyPlanId == planId).toList();
  }

  Future<void> _save() async {
    final plan = _selectedPlan;
    if (plan == null) return;
    setState(() => _isSaving = true);
    final result = await _service.updateWeeklyPlan(
      id: plan.id,
      executionScore: double.tryParse(_executionCtrl.text),
      outcomeScore: double.tryParse(_outcomeCtrl.text),
      reflection: _reflectionCtrl.text.trim().isEmpty ? null : _reflectionCtrl.text.trim(),
    );
    setState(() => _isSaving = false);
    if (result is ApiSuccess<MvpWeeklyPlan>) {
      setState(() {
        final idx = _plans.indexWhere((p) => p.id == plan.id);
        if (idx != -1) _plans[idx] = result.data;
        _selectedPlan = result.data;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null) {
      return Center(
        child: Text(_error!, style: const TextStyle(color: AppTheme.error)),
      );
    }
    if (_plans.isEmpty) {
      return const Center(
        child: Text(
          'Chưa có tuần nào để review. Kickoff dự án trước để tạo tuần 1.',
          style: TextStyle(color: AppTheme.textMutedDark),
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          DropdownButton<String>(
            value: _selectedPlan?.id,
            items: _plans
                .map((p) => DropdownMenuItem(
                      value: p.id,
                      child: Text('Tuần ${p.weekNo}${p.focus != null ? " — ${p.focus}" : ""}'),
                    ))
                .toList(),
            onChanged: (id) {
              final plan = _plans.firstWhere((p) => p.id == id);
              setState(() {
                _selectedPlan = plan;
                _executionCtrl.text = plan.executionScore?.toString() ?? '';
                _outcomeCtrl.text = plan.outcomeScore?.toString() ?? '';
                _reflectionCtrl.text = plan.reflection ?? '';
              });
            },
          ),
          const SizedBox(height: 16),
          if (_selectedPlan?.focus != null)
            Text(_selectedPlan!.focus!, style: const TextStyle(color: AppTheme.textDark, fontSize: 16, fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          const Text('Cam kết tuần này', style: TextStyle(color: AppTheme.textDark, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          for (final c in _commitmentsForSelectedPlan)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                children: [
                  Icon(
                    c.status == 'done' ? Icons.check_circle : Icons.radio_button_unchecked,
                    size: 16,
                    color: c.status == 'done' ? AppTheme.success : AppTheme.textMutedDark,
                  ),
                  const SizedBox(width: 8),
                  Expanded(child: Text(c.title, style: const TextStyle(color: AppTheme.textDark))),
                ],
              ),
            ),
          const SizedBox(height: 20),
          TextField(
            key: const Key('execution_score_field'),
            controller: _executionCtrl,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Điểm thực thi (0-100)'),
          ),
          const SizedBox(height: 12),
          TextField(
            key: const Key('outcome_score_field'),
            controller: _outcomeCtrl,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Điểm kết quả (0-100)'),
          ),
          const SizedBox(height: 12),
          TextField(
            key: const Key('reflection_field'),
            controller: _reflectionCtrl,
            maxLines: 4,
            decoration: const InputDecoration(labelText: 'Ghi chú / bài học tuần này'),
          ),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: _isSaving ? null : _save,
            child: Text(_isSaving ? 'Đang lưu...' : 'Lưu review'),
          ),
        ],
      ),
    );
  }
}
```

- [ ] **Step 4: Chạy lại test, xác nhận PASS**

Run: `cd frontend && flutter test test/modules/strategy/views/tabs/weekly_review_tab_test.dart`
Expected: PASS.

- [ ] **Step 5: Thêm tab thứ 7 vào `StrategyView`**

Sửa `frontend/lib/modules/strategy/views/strategy_view.dart`: thêm import
`weekly_review_tab.dart`, đổi `DefaultTabController(length: 6, ...)` (dòng
24-26) thành `length: 7`, thêm 1 `Tab` mới vào `tabs:` (sau tab 6, dòng
76-132) và 1 `WeeklyReviewTab()` mới vào `TabBarView`'s `children:`
(dòng 152-159), tương ứng đúng vị trí thứ 7 — số lượng `Tab`, số lượng
children trong `TabBarView`, và `length` của `DefaultTabController` phải
khớp nhau cả 3 (Flutter throw runtime error nếu lệch).

```dart
// thêm vào tabs: [...]
Tab(
  child: Row(
    mainAxisSize: MainAxisSize.min,
    children: const [
      Icon(Icons.rate_review_outlined, size: 16),
      SizedBox(width: 6),
      Text('Review tuần'),
    ],
  ),
),

// thêm vào TabBarView's children: [...]
WeeklyReviewTab(),
```

- [ ] **Step 6: `dart analyze` sạch, chạy lại toàn bộ test module strategy**

Run: `cd frontend && dart analyze lib/modules/strategy/ && flutter test test/modules/strategy/`
Expected: No issues found; tất cả PASS — đặc biệt các test hiện có của
`StrategyView` (nếu có assert số lượng tab cố định) vẫn phải pass với 7 tab
thay vì 6.

- [ ] **Step 7: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add frontend/lib/modules/strategy/views/tabs/weekly_review_tab.dart \
  frontend/lib/modules/strategy/views/strategy_view.dart \
  frontend/test/modules/strategy/views/tabs/weekly_review_tab_test.dart
git commit -m "feat(strategy): tab Review tuan (thu 7) trong StrategyView

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```
