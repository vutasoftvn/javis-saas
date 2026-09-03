# Kickoff Round Start & Concrete Review Schedule — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bước 3 của Project Kickoff nói rõ "chỉ chốt tuần 1"; buổi review được hiển thị bằng ngày/giờ cụ thể (chuỗi lặp hữu hạn); vòng đầu có `roundStartDate` (mặc định Thứ Hai kế tiếp) làm mốc; `projects.startDate` được set khi activate để Founder biết "đã triển khai bao lâu".

**Architecture:** `services/company` là source of truth. Thêm cột `round_start_date` vào `strategy.project_operating_setups`; `stageTargetDate` tính từ `roundStartDate` thay vì `now`. `activate` set `projects.start_date` khi còn null. Flutter thêm field vào model + 1 date picker ở bước 2, một helper thuần Dart resolve lịch review để hiển thị, và copy bước 3.

**Tech Stack:** Encore.ts + Drizzle/PostgreSQL + Vitest; Flutter/Dart + GetX + flutter_test.

**Spec nguồn:** hội thoại thiết kế 2026-09-03 (mục A/B/C/D). Không có file spec riêng — plan này là hợp đồng.

## Global Constraints

- Người dùng đã cho phép **recreate + reset database** sau khi thêm migration → migration 36 chỉ cần `ADD COLUMN` / `DROP COLUMN` (vẫn có cả `.up.sql` và `.down.sql`). Không cần evidence rollback N-1.
- Migration mới: `services/company/operations/migrations/36_operating_setup_round_start_date.{up,down}.sql`. Sau khi thêm: `node scripts/migrate.mjs` (hoặc `make services-migrate-company`).
- Không dùng `any`, `@ts-ignore`, `@ts-expect-error`, cast che typecheck (Encore Guardrail 5).
- Handler KHÔNG import `drizzle-orm` / `db` / schema — chỉ parse input, gọi service, map response/error (Encore Guardrail 1). File `project-operating-setup.handler.ts` hiện đã tuân thủ; giữ nguyên.
- Lỗi ở boundary dùng `APIError` (`invalidArgument`, `notFound`, ...), không `throw Error` trần.
- `expose: true` giữ nguyên `requireWorkspaceAccess`; mọi query bind `workspaceId`.
- `roundStartDate` truyền/nhận dạng chuỗi ISO-8601 (`"2026-09-08T00:00:00.000Z"`). Chuẩn hoá về đầu ngày UTC (`startOfUtcDay`).
- `stageDurationWeeks`: P0 = 1–2 tuần, P1 = 2–4 tuần (không đổi giới hạn hiện có).
- Không đổi `frontend/lib/core/contracts/enums.generated.dart`.
- Route `/operations/projects/:id/operating-setup*` đã nằm trong `scripts/frontend-api-contract-allowlist.json` — thêm field vào body KHÔNG tạo route mới; `make frontend-api-contract-check` vẫn phải xanh nhưng không cần sửa manifest.
- Comment giải thích "why" viết tiếng Việt; định danh/route/log tiếng Anh.
- Trước mỗi commit: `git status --short`, chỉ `git add` file của task đó, giữ nguyên thay đổi cục bộ khác.
- Format Dart trước khi commit: `dart format <file>`; format TS theo cấu hình repo (prettier chạy trong lint).
- Kết thúc commit message bằng:
  `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`

## File map

| Vùng | File | Trách nhiệm |
|---|---|---|
| Migration | `services/company/operations/migrations/36_operating_setup_round_start_date.{up,down}.sql` | Thêm/xoá cột `round_start_date TIMESTAMPTZ NULL`. |
| Schema | `services/company/shared/db/schema/strategy.ts` (bảng `projectOperatingSetups`, ~dòng 277–294) | Khai báo `roundStartDate`. |
| Domain/API | `services/company/operations/strategy/services/project-operating-setup.service.ts` | `roundStartDate` trong request/view; `nextMondayOnOrAfter`; `stageTargetDate` từ `roundStartDate`; activate set `projects.start_date`. |
| Handler | `services/company/operations/strategy/handlers/project-operating-setup.handler.ts` | Thêm `roundStartDate` vào `PutProjectOperatingSetupParams` + `ActivateProjectOperatingSetupParams` và forward. |
| Backend test | `services/company/operations/tests/project-operating-setup.test.ts` | Vitest cho default Monday, target date, `projects.start_date`. |
| Flutter data | `frontend/lib/data/models/project_operating_setup_model.dart` | `roundStartDate` trong `ProjectOperatingSetup` + `ProjectOperatingSetupDraft`. |
| Flutter helper | `frontend/lib/modules/strategy/domain/review_schedule.dart` (mới) | Resolve danh sách datetime buổi review (thuần, testable). |
| Flutter controller | `frontend/lib/modules/strategy/controllers/project_kickoff_controller.dart` | `roundStartDate` Rx, hydrate trong `load()`, gửi trong `buildDraft()`. |
| Flutter view | `frontend/lib/modules/strategy/views/project_kickoff_view.dart` | Date picker bước 2; copy + lịch review cụ thể bước 3. |
| Flutter view | `frontend/lib/modules/strategy/views/tabs/project_roadmap_tab.dart` (`_projectCard`, ~dòng 250–273) | Badge "đã triển khai N ngày". |
| Flutter test | `frontend/test/modules/strategy/domain/review_schedule_test.dart` (mới); `frontend/test/project_kickoff_view_test.dart` | Unit + widget. |

---

### Task 1: Backend — cột `round_start_date`, default Thứ Hai, `stageTargetDate` từ mốc vòng

**Files:**
- Create: `services/company/operations/migrations/36_operating_setup_round_start_date.up.sql`
- Create: `services/company/operations/migrations/36_operating_setup_round_start_date.down.sql`
- Modify: `services/company/shared/db/schema/strategy.ts` (bảng `projectOperatingSetups`)
- Modify: `services/company/operations/strategy/services/project-operating-setup.service.ts`
- Modify: `services/company/operations/strategy/handlers/project-operating-setup.handler.ts`
- Test: `services/company/operations/tests/project-operating-setup.test.ts`

**Interfaces:**
- Produces:
  - `ProjectOperatingSetupView.roundStartDate: string | null` (ISO)
  - `SaveProjectOperatingSetupRequest.roundStartDate?: string | null`
  - `ActivateProjectOperatingSetupRequest.roundStartDate?: string | null`
  - `export function nextMondayOnOrAfter(from: Date): Date` — trả về đầu ngày UTC của Thứ Hai vào/đúng sau `from`.
  - `export function startOfUtcDay(d: Date): Date`

- [ ] **Step 1: Viết migration up/down**

`36_operating_setup_round_start_date.up.sql`:
```sql
ALTER TABLE strategy.project_operating_setups
  ADD COLUMN round_start_date TIMESTAMPTZ NULL;
```

`36_operating_setup_round_start_date.down.sql`:
```sql
ALTER TABLE strategy.project_operating_setups
  DROP COLUMN IF EXISTS round_start_date;
```

- [ ] **Step 2: Khai báo cột trong Drizzle schema**

Trong `strategy.ts`, bảng `projectOperatingSetups`, thêm ngay sau dòng `stageTargetDate: timestamp("stage_target_date", { withTimezone: true }),`:
```ts
  roundStartDate: timestamp("round_start_date", { withTimezone: true }),
```

- [ ] **Step 3: Chạy migration + typecheck schema**

Run: `node scripts/migrate.mjs && cd services/company && npx tsc --noEmit -p tsconfig.json`
Expected: migration `36_...` applied; tsc PASS.

- [ ] **Step 4: Viết test Vitest (RED)**

Thêm vào `services/company/operations/tests/project-operating-setup.test.ts` (dùng đúng helper seed/ctx đã có trong file — đọc phần đầu file để lấy `makeCtx`/seed project):
```ts
describe("roundStartDate + stageTargetDate", () => {
  it("activate không có roundStartDate -> mặc định Thứ Hai kế tiếp, target = start + weeks*7d", async () => {
    const ctx = await makeCtx();
    const projectId = await seedProject(ctx);
    const res = await activateProjectOperatingSetup(ctx, projectId, {
      targetCustomer: "CFOs",
      problemStatement: "Reconciliation pain",
      evidenceLevel: "NONE",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      weeklyReviewWeekday: 5,
      weeklyReviewTime: "16:00",
      firstWeekOutcome: "Talk to 5 CFOs",
      firstWeekActions: [{ title: "List 10 prospects" }],
    });
    const start = new Date(res.setup.roundStartDate!);
    expect(start.getUTCDay()).toBe(1); // Monday
    const target = new Date(res.setup.stageTargetDate!);
    expect(target.getTime() - start.getTime()).toBe(2 * 7 * 24 * 60 * 60 * 1000);
  });

  it("activate với roundStartDate rõ ràng -> giữ nguyên (đầu ngày UTC)", async () => {
    const ctx = await makeCtx();
    const projectId = await seedProject(ctx);
    const res = await activateProjectOperatingSetup(ctx, projectId, {
      targetCustomer: "CFOs",
      problemStatement: "Reconciliation pain",
      evidenceLevel: "NONE",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 1,
      weeklyReviewWeekday: 5,
      weeklyReviewTime: "16:00",
      firstWeekOutcome: "Talk to 5 CFOs",
      firstWeekActions: [{ title: "List 10 prospects" }],
      roundStartDate: "2026-09-14T09:30:00.000Z",
    });
    expect(res.setup.roundStartDate).toBe("2026-09-14T00:00:00.000Z");
  });

  it("roundStartDate ngoài cửa sổ [hôm nay-1d, hôm nay+60d] -> invalidArgument", async () => {
    const ctx = await makeCtx();
    const projectId = await seedProject(ctx);
    await expect(
      activateProjectOperatingSetup(ctx, projectId, {
        targetCustomer: "CFOs",
        problemStatement: "x",
        evidenceLevel: "NONE",
        selectedStage: "P0_DISCOVERY",
        stageDurationWeeks: 2,
        weeklyReviewWeekday: 5,
        weeklyReviewTime: "16:00",
        firstWeekOutcome: "y",
        firstWeekActions: [{ title: "z" }],
        roundStartDate: "2020-01-01T00:00:00.000Z",
      })
    ).rejects.toThrow(/roundStartDate/);
  });
});
```
Nếu `makeCtx`/`seedProject` chưa tồn tại với tên đó, dùng đúng tên helper có sẵn trong file test này (đọc trước) — KHÔNG tự tạo helper seed mới.

Run: `cd services/company && npx vitest run operations/tests/project-operating-setup.test.ts -t "roundStartDate"`
Expected: FAIL (`roundStartDate` chưa có trong view / chưa validate).

- [ ] **Step 5: Cài helper ngày + field vào service**

Trong `project-operating-setup.service.ts`:

a) Thêm helper (đặt gần `DURATION_LIMITS`):
```ts
export function startOfUtcDay(d: Date): Date {
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
}

// Mặc định vòng bắt đầu Thứ Hai (chuẩn ISO-8601: tuần làm việc bắt đầu T2)
// vào/đúng sau `from`. Nếu `from` đã là Thứ Hai thì bắt đầu luôn hôm đó.
export function nextMondayOnOrAfter(from: Date): Date {
  const base = startOfUtcDay(from);
  const iso = base.getUTCDay() === 0 ? 7 : base.getUTCDay(); // 1=Mon..7=Sun
  const add = iso === 1 ? 0 : 8 - iso;
  base.setUTCDate(base.getUTCDate() + add);
  return base;
}

function resolveRoundStart(raw: string | null | undefined, now: Date): Date {
  if (raw === undefined || raw === null || !raw.trim()) {
    return nextMondayOnOrAfter(now);
  }
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) {
    throw APIError.invalidArgument("roundStartDate không phải ISO date hợp lệ");
  }
  const day = startOfUtcDay(parsed);
  const lo = startOfUtcDay(new Date(now.getTime() - 1 * 24 * 60 * 60 * 1000));
  const hi = startOfUtcDay(new Date(now.getTime() + 60 * 24 * 60 * 60 * 1000));
  if (day.getTime() < lo.getTime() || day.getTime() > hi.getTime()) {
    throw APIError.invalidArgument("roundStartDate phải nằm trong 60 ngày tới");
  }
  return day;
}
```

b) `ProjectOperatingSetupView`: thêm `roundStartDate: string | null;` (ngay sau `stageTargetDate`).

c) `SaveProjectOperatingSetupRequest` và `ActivateProjectOperatingSetupRequest`: thêm `roundStartDate?: string | null;`.

d) `toView`: thêm
```ts
    roundStartDate: row.roundStartDate ? row.roundStartDate.toISOString() : null,
```

e) `getProjectOperatingSetup` — nhánh "không có setup" (object literal `status: "NOT_STARTED"`): thêm `roundStartDate: null,`.

f) `saveProjectOperatingSetup`: sau khi có `durationWeeks`, thay khối tính `stageTargetDate` hiện tại bằng:
```ts
    const now = new Date();
    const resolvedRoundStart =
      req.roundStartDate !== undefined
        ? resolveRoundStart(req.roundStartDate, now)
        : existing?.roundStartDate ?? null;
    const anchorForTarget = resolvedRoundStart ?? now;
    const stageTargetDate =
      durationWeeks === null
        ? (req.stageDurationWeeks === undefined ? existing?.stageTargetDate ?? null : null)
        : new Date(anchorForTarget.getTime() + durationWeeks * 7 * 24 * 60 * 60 * 1000);
```
Xoá `const now = new Date();` cũ ở phía dưới nếu bị trùng khai báo. Trong `.values({...})` và `.set({...})` thêm:
```ts
        roundStartDate: resolvedRoundStart,
```

g) `activateProjectOperatingSetup`: thay
```ts
  const stageTargetDate = new Date(Date.now() + req.stageDurationWeeks * 7 * 24 * 60 * 60 * 1000);
```
bằng
```ts
  const roundStartDate = resolveRoundStart(req.roundStartDate, now);
  const stageTargetDate = new Date(
    roundStartDate.getTime() + req.stageDurationWeeks * 7 * 24 * 60 * 60 * 1000
  );
```
Trong cả `.values({...})` và `.set({...})` của insert `projectOperatingSetups` thêm `roundStartDate,`.

- [ ] **Step 6: Forward field ở handler**

Trong `project-operating-setup.handler.ts`:
- `PutProjectOperatingSetupParams`: thêm `roundStartDate?: string | null;`
- `ActivateProjectOperatingSetupParams`: thêm `roundStartDate?: string | null;`
- Trong `putProjectOperatingSetupEndpoint` body-map và `activateProjectOperatingSetupEndpoint` body-map: thêm `roundStartDate: params.roundStartDate,`

- [ ] **Step 7: Chạy test (GREEN)**

Run: `cd services/company && npx vitest run operations/tests/project-operating-setup.test.ts`
Expected: PASS toàn bộ file (bao gồm test cũ + 3 test mới).

- [ ] **Step 8: Gates**

Run:
```
cd services/company && npx tsc --noEmit -p tsconfig.json
cd /Volumes/SSD/javis-saas && make company-boundary-check && make encore-handler-boundary-check && make ts-suppression-check && make migration-check
```
Expected: tất cả PASS.

- [ ] **Step 9: Commit**

```bash
git add services/company/operations/migrations/36_operating_setup_round_start_date.up.sql \
        services/company/operations/migrations/36_operating_setup_round_start_date.down.sql \
        services/company/shared/db/schema/strategy.ts \
        services/company/operations/strategy/services/project-operating-setup.service.ts \
        services/company/operations/strategy/handlers/project-operating-setup.handler.ts \
        services/company/operations/tests/project-operating-setup.test.ts
git commit -m "feat(company): roundStartDate cho project operating setup, stageTargetDate tính từ mốc vòng

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Backend — `activate` set `projects.start_date` khi còn null

**Files:**
- Modify: `services/company/operations/strategy/services/project-operating-setup.service.ts` (`activateProjectOperatingSetup` transaction)
- Test: `services/company/operations/tests/project-operating-setup.test.ts`

**Interfaces:**
- Consumes: `nextMondayOnOrAfter`, `resolveRoundStart`, `roundStartDate` (Task 1).
- Produces: sau `activate`, `projects.start_date` = `roundStartDate` nếu trước đó null; nếu đã có giá trị thì giữ nguyên. `ActivateProjectOperatingSetupResponse.project.startDate` phản ánh giá trị này.

- [ ] **Step 1: Viết test (RED)**

Thêm vào cùng `describe` hoặc mới:
```ts
describe("activate populates projects.start_date", () => {
  it("set start_date = roundStartDate khi project chưa có start_date", async () => {
    const ctx = await makeCtx();
    const projectId = await seedProject(ctx); // seed KHÔNG set start_date
    const res = await activateProjectOperatingSetup(ctx, projectId, {
      targetCustomer: "CFOs",
      problemStatement: "pain",
      evidenceLevel: "NONE",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      weeklyReviewWeekday: 5,
      weeklyReviewTime: "16:00",
      firstWeekOutcome: "Talk to 5 CFOs",
      firstWeekActions: [{ title: "List 10 prospects" }],
    });
    expect(res.project.startDate).toBe(res.setup.roundStartDate);
  });

  it("không ghi đè start_date đã có", async () => {
    const ctx = await makeCtx();
    const projectId = await seedProject(ctx, { startDate: "2026-01-01T00:00:00.000Z" });
    const res = await activateProjectOperatingSetup(ctx, projectId, {
      targetCustomer: "CFOs",
      problemStatement: "pain",
      evidenceLevel: "NONE",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      weeklyReviewWeekday: 5,
      weeklyReviewTime: "16:00",
      firstWeekOutcome: "Talk to 5 CFOs",
      firstWeekActions: [{ title: "List 10 prospects" }],
    });
    expect(res.project.startDate).toBe("2026-01-01T00:00:00.000Z");
  });
});
```
Nếu `seedProject` chưa nhận option `startDate`, thêm param optional cho helper seed đó **trong file test** (không đụng helper production).

Run: `cd services/company && npx vitest run operations/tests/project-operating-setup.test.ts -t "populates projects.start_date"`
Expected: FAIL (`res.project.startDate` là `null`).

- [ ] **Step 2: Cập nhật transaction**

Trong `activateProjectOperatingSetup`, sau khi lấy `const [proj] = ...` và check tồn tại, trước phần transition stage, thêm:
```ts
    // Mốc "đã triển khai bao lâu" cho Founder — chỉ set lần đầu, không ghi đè.
    if (!proj.startDate) {
      await tx
        .update(projects)
        .set({ startDate: roundStartDate })
        .where(and(eq(projects.id, pId), eq(projects.workspaceId, wsId)));
    }
```
`refreshedProject` đã được select lại ở cuối transaction nên response tự phản ánh giá trị mới — không cần sửa `toProject`.

- [ ] **Step 3: Test (GREEN)**

Run: `cd services/company && npx vitest run operations/tests/project-operating-setup.test.ts`
Expected: PASS toàn bộ.

- [ ] **Step 4: Gates**

Run: `cd services/company && npx tsc --noEmit -p tsconfig.json && cd /Volumes/SSD/javis-saas && make company-boundary-check`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add services/company/operations/strategy/services/project-operating-setup.service.ts \
        services/company/operations/tests/project-operating-setup.test.ts
git commit -m "feat(company): activate operating setup set projects.start_date khi còn null

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Flutter data — `roundStartDate` trong model + draft

**Files:**
- Modify: `frontend/lib/data/models/project_operating_setup_model.dart`
- Test: `frontend/test/data/models/project_operating_setup_model_test.dart` (tạo nếu chưa có)

**Interfaces:**
- Produces:
  - `ProjectOperatingSetup.roundStartDate: DateTime?` (parse từ `json['roundStartDate']`)
  - `ProjectOperatingSetupDraft.roundStartDate: DateTime?` — `toJson()` phát `'roundStartDate': roundStartDate!.toUtc().toIso8601String()` khi không null.

- [ ] **Step 1: Viết test (RED)**

Tạo `frontend/test/data/models/project_operating_setup_model_test.dart`:
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/data/models/project_operating_setup_model.dart';

void main() {
  test('fromJson đọc roundStartDate', () {
    final s = ProjectOperatingSetup.fromJson({
      'projectId': 'p1',
      'workspaceId': 'w1',
      'status': 'ACTIVE',
      'roundStartDate': '2026-09-08T00:00:00.000Z',
    });
    expect(s.roundStartDate, DateTime.utc(2026, 9, 8));
  });

  test('fromJson roundStartDate null -> null', () {
    final s = ProjectOperatingSetup.fromJson({
      'projectId': 'p1',
      'workspaceId': 'w1',
      'status': 'IN_PROGRESS',
    });
    expect(s.roundStartDate, isNull);
  });

  test('draft.toJson phát roundStartDate ISO khi có', () {
    final d = ProjectOperatingSetupDraft(
      roundStartDate: DateTime.utc(2026, 9, 8),
      firstWeekActions: const [],
    );
    expect(d.toJson()['roundStartDate'], '2026-09-08T00:00:00.000Z');
  });

  test('draft.toJson bỏ roundStartDate khi null', () {
    final d = ProjectOperatingSetupDraft(firstWeekActions: const []);
    expect(d.toJson().containsKey('roundStartDate'), isFalse);
  });
}
```

Run: `cd frontend && flutter test test/data/models/project_operating_setup_model_test.dart`
Expected: FAIL (compile error — field chưa tồn tại).

- [ ] **Step 2: Thêm field vào `ProjectOperatingSetupDraft`**

- Thêm `this.roundStartDate,` vào constructor.
- Thêm `final DateTime? roundStartDate;`.
- Trong `toJson()`, trước dòng `'firstWeekActions': ...`:
```dart
    if (roundStartDate != null)
      'roundStartDate': roundStartDate!.toUtc().toIso8601String(),
```

- [ ] **Step 3: Thêm field vào `ProjectOperatingSetup`**

- Thêm `this.roundStartDate,` vào constructor.
- Thêm `final DateTime? roundStartDate;` (cạnh `stageTargetDate`).
- Trong `fromJson`, cạnh `stageTargetDate`:
```dart
      roundStartDate: json['roundStartDate'] != null
          ? DateTime.tryParse(json['roundStartDate'].toString())
          : null,
```

- [ ] **Step 4: Test (GREEN)**

Run: `cd frontend && flutter test test/data/models/project_operating_setup_model_test.dart`
Expected: PASS (4/4).

- [ ] **Step 5: Analyze + commit**

Run: `cd frontend && dart format lib/data/models/project_operating_setup_model.dart test/data/models/project_operating_setup_model_test.dart && flutter analyze lib/data/models/project_operating_setup_model.dart`
Expected: No issues.

```bash
git add frontend/lib/data/models/project_operating_setup_model.dart \
        frontend/test/data/models/project_operating_setup_model_test.dart
git commit -m "feat(strategy): roundStartDate trong ProjectOperatingSetup model + draft

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Flutter — helper `ReviewSchedule` (resolve lịch review, thuần)

**Files:**
- Create: `frontend/lib/modules/strategy/domain/review_schedule.dart`
- Test: `frontend/test/modules/strategy/domain/review_schedule_test.dart`

**Interfaces:**
- Produces:
```dart
class ReviewSchedule {
  const ReviewSchedule(this.occurrences);
  final List<DateTime> occurrences; // local DateTime, đã gắn giờ review

  /// weekday: 1=Thứ Hai .. 7=Chủ Nhật (khớp DateTime.weekday).
  /// time: 'HH:mm'. minGapDays: khoảng cách tối thiểu giữa mốc bắt đầu và
  /// buổi review đầu tiên (loại ca "hôm nay activate, mai review").
  static ReviewSchedule resolve({
    required DateTime roundStart,
    required int weekday,
    required String time,
    required int durationWeeks,
    int minGapDays = 3,
  });
}
```
- Quy tắc:
  - `first` = ngày sớm nhất có `.weekday == weekday`, `>= roundStart + minGapDays`, gắn giờ từ `time`.
  - Kế tiếp: `first + 7*k` ngày, `k = 1..`, chừng nào `<= roundStart + durationWeeks*7` (so sánh theo ngày, bỏ giờ).
  - Luôn có ít nhất 1 occurrence (kể cả khi `first` vượt target — trả về đúng `[first]`).

- [ ] **Step 1: Viết test (RED)**

`frontend/test/modules/strategy/domain/review_schedule_test.dart`:
```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/modules/strategy/domain/review_schedule.dart';

void main() {
  test('vòng 2 tuần, bắt đầu Thứ Hai, review Thứ Sáu -> 2 buổi', () {
    final s = ReviewSchedule.resolve(
      roundStart: DateTime(2026, 9, 7), // Monday
      weekday: DateTime.friday, // 5
      time: '16:00',
      durationWeeks: 2,
    );
    expect(s.occurrences.length, 2);
    expect(s.occurrences.first, DateTime(2026, 9, 11, 16, 0));
    expect(s.occurrences[1], DateTime(2026, 9, 18, 16, 0));
  });

  test('minGap loại buổi review ngay hôm sau mốc bắt đầu', () {
    // roundStart Thứ Năm, review Thứ Sáu -> buổi đầu bị đẩy sang Thứ Sáu tuần sau
    final s = ReviewSchedule.resolve(
      roundStart: DateTime(2026, 9, 10), // Thursday
      weekday: DateTime.friday,
      time: '09:00',
      durationWeeks: 2,
    );
    expect(s.occurrences.first, DateTime(2026, 9, 18, 9, 0));
  });

  test('vòng 1 tuần -> 1 buổi', () {
    final s = ReviewSchedule.resolve(
      roundStart: DateTime(2026, 9, 7),
      weekday: DateTime.friday,
      time: '16:00',
      durationWeeks: 1,
    );
    expect(s.occurrences.length, 1);
    expect(s.occurrences.first, DateTime(2026, 9, 11, 16, 0));
  });

  test('time không hợp lệ -> mặc định 00:00 (không ném)', () {
    final s = ReviewSchedule.resolve(
      roundStart: DateTime(2026, 9, 7),
      weekday: DateTime.friday,
      time: 'oops',
      durationWeeks: 1,
    );
    expect(s.occurrences.first, DateTime(2026, 9, 11, 0, 0));
  });
}
```

Run: `cd frontend && flutter test test/modules/strategy/domain/review_schedule_test.dart`
Expected: FAIL (file chưa tồn tại).

- [ ] **Step 2: Cài helper**

`frontend/lib/modules/strategy/domain/review_schedule.dart`:
```dart
/// Resolve lịch buổi review hằng tuần của một vòng kickoff thành danh sách
/// datetime cụ thể — dùng để hiển thị "Thứ Sáu 11/09 & 18/09, 16:00" thay vì
/// chỉ "Thứ Sáu". Thuần, không phụ thuộc Flutter/GetX để test được.
class ReviewSchedule {
  const ReviewSchedule(this.occurrences);

  final List<DateTime> occurrences;

  static ReviewSchedule resolve({
    required DateTime roundStart,
    required int weekday,
    required String time,
    required int durationWeeks,
    int minGapDays = 3,
  }) {
    final (h, m) = _parseTime(time);
    final startDay = DateTime(roundStart.year, roundStart.month, roundStart.day);
    final earliest = startDay.add(Duration(days: minGapDays));

    // Ngày đầu tiên >= earliest có đúng weekday.
    var firstDay = earliest;
    while (firstDay.weekday != weekday) {
      firstDay = firstDay.add(const Duration(days: 1));
    }

    final targetDay = startDay.add(Duration(days: durationWeeks * 7));
    final out = <DateTime>[];
    var cursor = firstDay;
    while (out.isEmpty || !cursor.isAfter(targetDay)) {
      out.add(DateTime(cursor.year, cursor.month, cursor.day, h, m));
      cursor = cursor.add(const Duration(days: 7));
    }
    return ReviewSchedule(out);
  }

  static (int, int) _parseTime(String time) {
    final match = RegExp(r'^([01]?\d|2[0-3]):([0-5]\d)$').firstMatch(time.trim());
    if (match == null) return (0, 0);
    return (int.parse(match.group(1)!), int.parse(match.group(2)!));
  }
}
```

- [ ] **Step 3: Test (GREEN)**

Run: `cd frontend && flutter test test/modules/strategy/domain/review_schedule_test.dart`
Expected: PASS (4/4).

- [ ] **Step 4: Analyze + commit**

Run: `cd frontend && dart format lib/modules/strategy/domain/review_schedule.dart test/modules/strategy/domain/review_schedule_test.dart && flutter analyze lib/modules/strategy/domain/review_schedule.dart`
Expected: No issues.

```bash
git add frontend/lib/modules/strategy/domain/review_schedule.dart \
        frontend/test/modules/strategy/domain/review_schedule_test.dart
git commit -m "feat(strategy): ReviewSchedule helper resolve lịch review cụ thể

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Flutter view — copy bước 3, lịch review cụ thể, date picker mốc vòng

**Files:**
- Modify: `frontend/lib/modules/strategy/controllers/project_kickoff_controller.dart`
- Modify: `frontend/lib/modules/strategy/views/project_kickoff_view.dart`
- Test: `frontend/test/project_kickoff_view_test.dart`

**Interfaces:**
- Consumes: `ReviewSchedule` (Task 4); `ProjectOperatingSetupDraft.roundStartDate`, `ProjectOperatingSetup.roundStartDate` (Task 3).
- Produces trên controller:
  - `final roundStartDate = Rxn<DateTime>();`
  - `DateTime defaultRoundStart()` — Thứ Hai kế tiếp (local), dùng khi `roundStartDate.value == null`.
  - `buildDraft()` gửi `roundStartDate: roundStartDate.value`.

- [ ] **Step 1: Controller — Rx + hydrate + draft**

Trong `project_kickoff_controller.dart`:

a) Cạnh `final weeklyReviewTime = '16:00'.obs;` thêm:
```dart
  final roundStartDate = Rxn<DateTime>();
```

b) Thêm method (gần `selectDuration`):
```dart
  // Mặc định vòng bắt đầu Thứ Hai kế tiếp (khớp backend nextMondayOnOrAfter).
  DateTime defaultRoundStart() {
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final add = today.weekday == DateTime.monday ? 0 : 8 - today.weekday;
    return today.add(Duration(days: add));
  }

  DateTime get effectiveRoundStart => roundStartDate.value ?? defaultRoundStart();

  void setRoundStart(DateTime d) {
    roundStartDate.value = DateTime(d.year, d.month, d.day);
  }
```

c) Trong `load()`, sau `weeklyReviewTime.value = ...`:
```dart
      roundStartDate.value = loaded.roundStartDate;
```

d) Trong `buildDraft()`, thêm vào constructor `ProjectOperatingSetupDraft(...)`:
```dart
      roundStartDate: roundStartDate.value,
```

- [ ] **Step 2: Widget test (RED)**

Thêm vào `frontend/test/project_kickoff_view_test.dart`:
```dart
  testWidgets('bước 3 hiển thị copy "chỉ chốt tuần 1" theo thời lượng vòng', (
    tester,
  ) async {
    await tester.pumpWidget(kickoffHarness(setup: completeP0Draft));
    await tester.pumpAndSettle();
    expect(find.textContaining('chỉ chốt chi tiết tuần 1'), findsOneWidget);
    expect(find.textContaining('2 tuần'), findsWidgets);
  });

  testWidgets('bước 3 hiển thị ngày buổi review cụ thể', (tester) async {
    await tester.pumpWidget(kickoffHarness(setup: completeP0Draft));
    await tester.pumpAndSettle();
    // completeP0Draft: weekday 5 (Thứ Sáu), 16:00, 2 tuần -> 2 buổi review.
    expect(find.textContaining('Buổi review'), findsOneWidget);
    expect(find.textContaining('16:00'), findsWidgets);
  });
```
`completeP0Draft` trong file test cần có `roundStartDate` để lịch ổn định — thêm `roundStartDate: '2026-09-07T00:00:00.000Z'` vào JSON/khởi tạo của `completeP0Draft` nếu nó là `ProjectOperatingSetup(...)` literal; nếu `FakeKickoffService` trả `initialSetup` thì set trên đó. Giữ assertion mềm (`findsWidgets`/`textContaining`) để không giòn theo format ngày.

Run: `cd frontend && flutter test test/project_kickoff_view_test.dart -n "bước 3"`
Expected: FAIL (copy + lịch chưa render).

- [ ] **Step 3: View — copy bước 3**

Trong `project_kickoff_view.dart`, `_buildStep3FirstWeek()`, ngay sau `Text('Bước 3: Chốt việc tuần đầu', ...)` và `SizedBox(height: 16)`, chèn một khối context (đọc `controller.selectedStage.value`, `controller.stageDurationWeeks.value`):
```dart
          Text(
            _step3ContextLine(),
            style: const TextStyle(
              color: AppTheme.textMutedDark,
              fontSize: 13,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 16),
```
Thêm method trong state class:
```dart
  String _step3ContextLine() {
    final weeks = controller.stageDurationWeeks.value;
    final stageLabel =
        controller.selectedStage.value == ProjectLifecycleStage.p1ProblemValidation
        ? 'Xác thực vấn đề (P1)'
        : 'Khám phá (P0)';
    return 'Vòng $stageLabel · $weeks tuần — giờ chỉ chốt chi tiết tuần 1. '
        'Các tuần sau sẽ lên kế hoạch trong buổi review hằng tuần.';
  }
```
Đổi nhãn `'Kết quả của tuần 1'` → giữ nguyên chữ, thêm dưới nó một dòng hint nhỏ:
```dart
          const Text(
            'Tuần 2 trở đi chốt ở buổi review, không nhập ở đây.',
            style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12),
          ),
          const SizedBox(height: 6),
```
(đặt giữa `Text('Kết quả của tuần 1')` và `TextField(... firstWeekOutcomeCtrl ...)`)

- [ ] **Step 4: View — lịch review cụ thể trong `_buildWeeklyReviewCadence`**

Cuối `_buildWeeklyReviewCadence()`, sau `Wrap(...)` chứa 2 dropdown, bọc lại thành `Column` và thêm dòng resolved:
```dart
          const SizedBox(height: 8),
          Builder(
            builder: (_) {
              final sched = ReviewSchedule.resolve(
                roundStart: controller.effectiveRoundStart,
                weekday: controller.weeklyReviewWeekday.value,
                time: controller.weeklyReviewTime.value,
                durationWeeks: controller.stageDurationWeeks.value,
              );
              final dd = sched.occurrences
                  .map((d) =>
                      '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}')
                  .join(' & ');
              final hh = controller.weeklyReviewTime.value;
              return Text(
                'Buổi review: $dd lúc $hh (giờ workspace) · lặp hằng tuần trong vòng.',
                style: const TextStyle(
                  color: AppTheme.textMutedDark,
                  fontSize: 12,
                  height: 1.4,
                ),
              );
            },
          ),
```
Import ở đầu file: `import '../domain/review_schedule.dart';`

- [ ] **Step 5: View — date picker mốc vòng ở bước 2**

Trong `_buildStep2Stage()`, sau khối "Thời lượng vòng này" (`Wrap(spacing: 8, children: _buildDurationChips())`) và trước `SizedBox(height: 24)` của Actions, thêm:
```dart
          const SizedBox(height: 20),
          const Text(
            'Vòng bắt đầu từ:',
            style: TextStyle(
              color: AppTheme.textDark,
              fontWeight: FontWeight.w600,
              fontSize: 14,
            ),
          ),
          const SizedBox(height: 8),
          _roundStartPicker(),
```
Method:
```dart
  Widget _roundStartPicker() {
    final d = controller.effectiveRoundStart;
    final label =
        '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';
    final isDefault = controller.roundStartDate.value == null;
    return Row(
      children: [
        OutlinedButton.icon(
          onPressed: () async {
            final now = DateTime.now();
            final picked = await showDatePicker(
              context: context,
              initialDate: d,
              firstDate: DateTime(now.year, now.month, now.day),
              lastDate: DateTime(now.year, now.month, now.day)
                  .add(const Duration(days: 60)),
            );
            if (picked != null) controller.setRoundStart(picked);
          },
          icon: const Icon(Icons.event_rounded, size: 16),
          label: Text(label),
        ),
        const SizedBox(width: 10),
        if (isDefault)
          const Text(
            'mặc định: Thứ Hai kế tiếp',
            style: TextStyle(color: AppTheme.textMutedDark, fontSize: 12),
          ),
      ],
    );
  }
```

- [ ] **Step 6: Test (GREEN) + toàn bộ file**

Run: `cd frontend && flutter test test/project_kickoff_view_test.dart`
Expected: PASS toàn bộ (bao gồm test cũ + 2 test mới).

- [ ] **Step 7: Analyze + format + commit**

Run: `cd frontend && dart format lib/modules/strategy/controllers/project_kickoff_controller.dart lib/modules/strategy/views/project_kickoff_view.dart test/project_kickoff_view_test.dart && flutter analyze lib/modules/strategy/controllers/project_kickoff_controller.dart lib/modules/strategy/views/project_kickoff_view.dart`
Expected: No issues.

```bash
git add frontend/lib/modules/strategy/controllers/project_kickoff_controller.dart \
        frontend/lib/modules/strategy/views/project_kickoff_view.dart \
        frontend/test/project_kickoff_view_test.dart
git commit -m "feat(strategy): bước 3 nói rõ chỉ chốt tuần 1, hiển thị lịch review cụ thể, picker mốc vòng

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: Flutter — badge "đã triển khai N ngày" trên project card

**Files:**
- Modify: `frontend/lib/modules/strategy/views/tabs/project_roadmap_tab.dart` (`_projectCard`, ~dòng 250–273)
- Test: `frontend/test/modules/strategy/views/project_roadmap_tab_test.dart` (tạo nếu chưa có; nếu tồn tại thì thêm case)

**Interfaces:**
- Consumes: `projects.start_date` do Task 2 backfill khi activate.
- Produces: khi `project['start_date']` có giá trị, `dateBadge` kết thúc bằng ` · đã triển khai N ngày` với `N = max(0, now - startDate).inDays`.

- [ ] **Step 1: Xác minh nguồn dữ liệu**

Run: `cd frontend && grep -n "start_date\|operations/projects\|roadmap" lib/modules/strategy/services/*.dart lib/modules/strategy/controllers/project_orchestration_controller.dart`
Kỳ vọng: `_projectCard` nhận map project có key `start_date` (đã dùng ở dòng ~254). Nếu endpoint list project KHÔNG trả `start_date`, DỪNG và báo lại — cần thêm field ở service `services/company` trước (ngoài plan này).

- [ ] **Step 2: Widget test (RED)**

Tạo `frontend/test/modules/strategy/views/project_roadmap_tab_test.dart` (hoặc thêm vào file có sẵn). Render `_projectCard` gián tiếp qua `ProjectRoadmapTab` với controller giả có 1 project `start_date` = 10 ngày trước; assert:
```dart
expect(find.textContaining('đã triển khai 10 ngày'), findsOneWidget);
```
Nếu dựng harness quá nặng, chuyển logic tính badge ra một hàm thuần `String? projectDateBadge(Map<String,dynamic> project, {DateTime? now})` trong cùng file và test hàm đó trực tiếp.

Run: `cd frontend && flutter test test/modules/strategy/views/project_roadmap_tab_test.dart`
Expected: FAIL.

- [ ] **Step 3: Cập nhật `_projectCard`**

Trong khối `if (startDateStr != null && startDateStr.isNotEmpty)`, sau khi tính `dateBadge`, thêm:
```dart
        final elapsedDays = DateTime.now().difference(startDt).inDays;
        if (elapsedDays >= 0) {
          dateBadge = '${dateBadge ?? 'Từ $startFmt/${startDt.year}'}'
              ' · đã triển khai $elapsedDays ngày';
        }
```
(đặt trong `try`, sau nhánh if/else hiện có)

- [ ] **Step 4: Test (GREEN)**

Run: `cd frontend && flutter test test/modules/strategy/views/project_roadmap_tab_test.dart`
Expected: PASS.

- [ ] **Step 5: Analyze + commit**

Run: `cd frontend && dart format lib/modules/strategy/views/tabs/project_roadmap_tab.dart test/modules/strategy/views/project_roadmap_tab_test.dart && flutter analyze lib/modules/strategy/views/tabs/project_roadmap_tab.dart`
Expected: No issues.

```bash
git add frontend/lib/modules/strategy/views/tabs/project_roadmap_tab.dart \
        frontend/test/modules/strategy/views/project_roadmap_tab_test.dart
git commit -m "feat(strategy): project card hiển thị 'đã triển khai N ngày'

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: Verify end-to-end + gates tổng

**Files:** không sửa code (chỉ chạy gate; fix nhỏ nếu gate đỏ).

- [ ] **Step 1: Backend**

Run:
```
cd services/company && npx vitest run operations/tests/project-operating-setup.test.ts operations/tests/project-kickoff-materialize.test.ts operations/tests/project-operating-setup-kickoff-materialize.test.ts
cd services/company && npx tsc --noEmit -p tsconfig.json
```
Expected: PASS.

- [ ] **Step 2: Migration rollback thử (an toàn vì DB sẽ reset)**

Run: `node scripts/migrate.mjs` rồi kiểm tra cột tồn tại; áp `36_...down.sql` thủ công trên DB dev nếu cần xác nhận `DROP COLUMN` chạy sạch. Sau đó re-apply.

- [ ] **Step 3: Frontend**

Run:
```
cd frontend && flutter analyze
cd frontend && flutter test test/data/models/project_operating_setup_model_test.dart test/modules/strategy/domain/review_schedule_test.dart test/project_kickoff_view_test.dart test/modules/strategy/
```
Expected: No analyze issues; tất cả test PASS.

- [ ] **Step 4: Repo gates**

Run:
```
cd /Volumes/SSD/javis-saas
make company-boundary-check
make encore-handler-boundary-check
make ts-suppression-check
make frontend-api-contract-check
make migration-check
```
Expected: tất cả PASS.

- [ ] **Step 5: Manual smoke (mô tả, không bắt buộc chạy)**

`/projects/new` → tạo project → bước 2 chọn P0 2 tuần, đổi "Vòng bắt đầu từ" → bước 3 thấy dòng "chỉ chốt chi tiết tuần 1" + "Buổi review: DD/MM & DD/MM lúc 16:00" → activate → mở lại danh sách project thấy "đã triển khai 0 ngày".

- [ ] **Step 6: Commit (nếu có fix gate)**

```bash
git add -p
git commit -m "chore(strategy): fix gate sau khi thêm roundStartDate

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- A (copy bước 3) → Task 5 Step 3.
- B (lịch review cụ thể + RRULE hữu hạn + guard khoảng cách) → Task 4 (helper + minGap) + Task 5 Step 4 (render).
- C (`round_start_date` migration + activate + contract + client + date picker + default Thứ Hai) → Task 1 (migration/schema/service/handler/default) + Task 3 (client model) + Task 5 Step 1/5 (controller + picker). Contract: allowlist đã có route, không cần sửa manifest (ghi ở Global Constraints).
- D (set `projects.startDate` khi activate + hiển thị elapsed) → Task 2 (backend) + Task 6 (frontend badge).

**Placeholder scan:** không có "TBD"/"handle edge cases" trần — mỗi step có code thật hoặc lệnh chạy cụ thể. Chỗ chưa chắc (endpoint list project có `start_date` không) được đưa thành Step verify tường minh ở Task 6 Step 1 với hành động rõ ("DỪNG và báo lại").

**Type consistency:**
- `roundStartDate`: TS `string | null` ở request/view; Drizzle `timestamp` → `Date | null` ở row; Dart `DateTime?`. Chuyển đổi: `toView` `.toISOString()`, `fromJson` `DateTime.tryParse`, `draft.toJson` `.toUtc().toIso8601String()`.
- `nextMondayOnOrAfter` / `startOfUtcDay` / `resolveRoundStart` khai báo ở Task 1, dùng lại ở Task 2 — cùng file, cùng chữ ký.
- `ReviewSchedule.resolve({roundStart, weekday, time, durationWeeks, minGapDays})` khai báo Task 4, gọi ở Task 5 Step 4 với đúng tên tham số.
- `controller.effectiveRoundStart` (getter) khai báo Task 5 Step 1, dùng Task 5 Step 4/5.

## Execution Handoff

Chọn cách thực thi:

1. **Subagent-Driven (khuyến nghị)** — mỗi task một subagent mới, review giữa các task.
2. **Inline Execution** — chạy tuần tự trong session này, checkpoint để review.
