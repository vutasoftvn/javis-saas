# Founder Trial R1 — Node A0 + A1: Hotfix, Manifest & Founder Trial Board

> Đây là 2 node đầu của DAG R1. Xem blueprint tổng:
> [`docs/superpowers/specs/2026-09-09-founder-trial-r1-reconciled-plan.md`](../specs/2026-09-09-founder-trial-r1-reconciled-plan.md).
> Spec sản phẩm: [`2026-09-09-founder-trial-domain-agent-mvp-design.md`](../specs/2026-09-09-founder-trial-domain-agent-mvp-design.md).
>
> **A0 là PR độc lập, không phụ thuộc gì** — làm và merge trước.
> **A1 phụ thuộc A0.** B và C phụ thuộc A1. E phụ thuộc B+C. D là post-R1.

**Goal:** (A0) sửa dứt điểm việc `cycleDurationWeeks` không round-trip và việc
review chưa được schedule ở luồng kickoff; (A1) cho founder một shell trung thực
với `WorkspaceCapabilityManifest` server-owned và một **Founder Trial Board** ghép
từ dữ liệu thật hiện có, **không tạo bảng lifecycle mới**.

**Không làm trong A0/A1:** bảng `venture_lifecycle_plans`, state machine
`DRAFT→PROPOSED→CONFIRMED→SUPERSEDED`, revision snapshot, AI plan proposal,
multi-phase executable lifecycle, bảng `operating.cycle_assumptions`. Tất cả
chuyển R1.1 và chỉ thêm khi founder trial chứng minh cần (proposal AI + nhiều
phương án + lịch sử versioned + diff/amend/revert + workflow xác nhận riêng).

## Non-negotiable constraints

- Làm trên `main`, giữ nguyên thay đổi không liên quan; không tạo worktree.
- Mọi thay đổi schema là expand-first và có down migration chạy được. A0 **cố
  gắng không cần migration** (column `cycle_duration_weeks` đã tồn tại, nullable,
  không CHECK) — validation bounded làm ở code. Nếu team muốn DB CHECK thì tách
  migration riêng, review riêng.
- Company Plane là chủ duy nhất của project/cycle/review/evidence/decision truth.
- Founder — không phải agent — xác nhận cycle, đổi phase, ghi business decision.
- Duration chọn theo Operating Cycle; 12 chỉ là template gợi ý. Phase-1 vẫn tôn
  trọng `DURATION_LIMITS` P0/P1 và P1 evidence gate hiện có.
- Không sửa response `module-visibility` legacy. Manifest mới là endpoint typed
  mới; `module-visibility` giữ byte-for-byte trong lúc migrate.
- Không biến lỗi thành dashboard rỗng. Loading, unavailable,
  configuration-required, empty-real-data, planned là 5 trạng thái khác nhau.
- Hypothesis sống ở `strategy.assumptions`, không JSON, không `first actions`.

## File map

| Area | Files |
|---|---|
| A0 backend | `services/company/operations/strategy/handlers/project-operating-setup.handler.ts`, `services/company/operations/strategy/services/project-operating-setup.service.ts`, `services/company/operations/strategy/services/project-kickoff-materialize.service.ts`, `services/company/operations/services/execution-calendar.ts` (đọc), `services/company/operations/strategy/services/cycle-review.service.ts` (đọc) |
| A0 frontend | `frontend/lib/data/models/project_operating_setup_model.dart`, `frontend/lib/modules/strategy/widgets/cycle_review_timeline.dart`, `frontend/lib/modules/strategy/views/project_kickoff_view.dart` |
| A1 manifest (COSA) | `services/cosa/migrations/35_workspace_capability_manifest.*`, `services/cosa/services/workspace-settings.service.ts`, `services/cosa/handlers/workspace-settings.handler.ts` |
| A1 contract | `shared/contracts/mvp-surface.json`, `scripts/gen-mvp-contracts.mjs` (chạy), generated TS/Py/Dart clients |
| A1 board (Company) | `services/company/operations/strategy/services/founder-trial-board.service.ts`, `services/company/operations/strategy/handlers/founder-trial-board.handler.ts`, `services/company/operations/strategy/services/experiment-proposal.service.ts` (thêm path validated), `services/company/operations/strategy/handlers/experiment.handler.ts` |
| A1 Flutter | `frontend/lib/core/services/workspace_capability_manifest_*.dart`, `frontend/lib/core/widgets/surface_state_view.dart`, `frontend/lib/modules/strategy/founder_trial/*` |
| Tests | Company strategy tests, COSA workspace-settings tests, Flutter unit/widget tests |

---

## A0 — Hotfix: cycle duration round-trip + review scheduling ở activate/confirm

### A0.1 — Viết test đỏ

**Files:**
- Modify: `services/company/operations/tests/execution-cycle-calendar.test.ts`
- Create: `services/company/operations/tests/cycle-duration-roundtrip.test.ts`
- Modify: `frontend/test/data/models/project_operating_setup_model_test.dart`

Cover:
- `PUT /operations/projects/:id/operating-setup` với `cycleDurationWeeks = 8` →
  GET trả lại đúng `8`; `activate` với `cycleDurationWeeks = 6` → GET trả `6`.
- `cycleDurationWeeks = 0` và `13` bị từ chối `invalidArgument`; `1` và `12` hợp lệ.
- Save **draft** (chưa activate) **không tạo** dòng `cycle_reviews` nào.
- `activate` tạo đúng bộ slot theo `buildCycleReviewSchedule(durationWeeks)`
  (WEEKLY 1..n, MID_CYCLE nếu n≥4 & policy AUTO, END_CYCLE tại n).
- `activate` gọi 2 lần (idempotent) không nhân đôi `cycle_reviews`.
- Setup đã active đổi `cycleDurationWeeks` 6→10 → `rescheduleCycleReviews`:
  slot ngoài lịch mới thành `SUPERSEDED`, slot mới được thêm, `COMPLETED` giữ nguyên.
- Flutter `ProjectOperatingSetup.fromJson`/`toJson` và `ProjectOperatingSetupDraft.toJson`
  round-trip `cycleDurationWeeks`.

### A0.2 — Chạy đỏ

```
cd services/company && encore test operations/tests/cycle-duration-roundtrip.test.ts operations/tests/execution-cycle-calendar.test.ts
cd frontend && flutter test test/data/models/project_operating_setup_model_test.dart
```
Kỳ vọng: FAIL (handler bỏ field; scheduler không được gọi ở kickoff; Flutter model thiếu field).

### A0.3 — Triển khai

**`project-operating-setup.handler.ts`:**
- Thêm `cycleDurationWeeks?: number` vào `PutProjectOperatingSetupParams` và
  `ActivateProjectOperatingSetupParams`.
- Forward `cycleDurationWeeks` trong cả 2 handler body (hiện build request
  object field-by-field và bỏ sót nó).

**`project-operating-setup.service.ts`:**
- Đưa `cycleDurationWeeks` vào **cả 2 khối `.values({...})` insert**
  (`saveProjectOperatingSetup` ~L446-464, `activateProjectOperatingSetup`
  ~L614-632), không chỉ nhánh `onConflictDoUpdate.set`.
- Thêm validation bounded: số nguyên dương, `1..12` cho R1. Đặt hằng
  `FOUNDER_TRIAL_MAX_CYCLE_WEEKS = 12` cạnh `DURATION_LIMITS`; tái dùng ý tưởng
  `validateDurationWeeks` (`operations/services/execution-calendar.ts`) rồi thêm
  ceiling. Không đụng `DURATION_LIMITS` P0/P1 và P1 evidence gate.

**Review scheduling — điểm mấu chốt:**
- `materializeFirstWeekPlan` (`project-kickoff-materialize.service.ts`)
  **KHÔNG** gọi `scheduleInitialCycleReviews`. Nó chạy ngay lúc save draft;
  gọi scheduler ở đó tạo review "ma" cho draft. Giữ nguyên phần insert
  `twelve_week_cycles` + `weekly_plans` + tasks như hiện tại.
- Trong `activateProjectOperatingSetup` (và path confirm nếu bổ sung sau): sau
  khi cycle row tồn tại trong cùng transaction, gọi
  `scheduleInitialCycleReviews(tx, cycle, settings)` — guard idempotent bằng
  cách kiểm tra đã có `cycle_reviews` cho `cycleId` chưa (chỉ schedule khi chưa có).
- Khi setup đã active và request đổi `cycleDurationWeeks` (old ≠ new): gọi
  `rescheduleCycleReviews(tx, cycleId, ws, oldDuration, newDuration, settings, startLocalDate, timezone)`.
- Lấy `settings` qua `getWorkspaceStrategySettings` như `twelve-week-year.service.ts` đang làm.

**Flutter:**
- `project_operating_setup_model.dart`: thêm `int? cycleDurationWeeks` vào
  `ProjectOperatingSetup` (parse trong `fromJson`, thêm vào `copyWith`) và gửi
  trong `ProjectOperatingSetupDraft.toJson`.
- Nối `CycleReviewTimeline` (widget đã khai sẵn `int? cycleDurationWeeks`,
  hiện không được dùng ở đâu trong `frontend/lib`) vào view kickoff/review, hoặc
  tối thiểu truyền `controller.cycleDurationWeeks` xuống. Thêm
  `cycleDurationWeeks` (obs) vào `project_kickoff_controller.dart`.

### A0.4 — Chạy xanh

```
cd services/company && encore test operations/tests/cycle-duration-roundtrip.test.ts operations/tests/execution-cycle-calendar.test.ts operations/tests/project-operating-setup.test.ts operations/tests/project-operating-setup-kickoff-materialize.test.ts
cd frontend && flutter test test/data/models/project_operating_setup_model_test.dart && flutter analyze --no-pub
make company-boundary-check encore-handler-boundary-check ts-suppression-check
```
Kỳ vọng: PASS. `cycleDurationWeeks` round-trip cả 2 chiều; draft không tạo review;
activate tạo & không nhân đôi; đổi duration reschedule đúng.

### A0.5 — Merge

A0 merge như một PR riêng trước khi bắt đầu A1.

---

## A1 — Truthful shell + WorkspaceCapabilityManifest + Founder Trial Board

**Depends on:** A0.

### A1.1 — WorkspaceCapabilityManifest (COSA)

**Files:**
- Create: `services/cosa/migrations/35_workspace_capability_manifest.up.sql` / `.down.sql`
- Modify: `services/cosa/services/workspace-settings.service.ts`
- Modify: `services/cosa/handlers/workspace-settings.handler.ts`
- Modify: `shared/contracts/mvp-surface.json` → regenerate 3 clients
- Create: `services/cosa/tests/workspace-capability-manifest.test.ts`

**Response shape — đúng spec §7.1:**

```ts
type SurfaceStatus =
  | "AVAILABLE" | "PILOT" | "PLANNED"
  | "CONFIGURATION_REQUIRED" | "UNAVAILABLE";

interface WorkspaceCapabilityManifest {
  version: string;
  workspaceId: string;
  surfaces: Array<{
    moduleKey: string;
    featureKey: string;
    surfaceStatus: SurfaceStatus;
    requiredCapabilities: string[];
    requiredConnectorKeys: string[];
    entitled: boolean;
    reasons: string[];
    contractEndpoint: string | null;   // capability id trong mvp-surface.json
    releaseNote: string | null;
    updatedAt: string;
  }>;
}
```

**Test đỏ:**
- Chỉ workspace membership fetch được manifest; người ngoài → 404 không lộ tồn tại.
- Chỉ operator sửa được workspace override; user preference **không** nâng
  `PLANNED` → `AVAILABLE`.
- CAS chưa có active connection → surface finance = `CONFIGURATION_REQUIRED`
  với `requiredConnectorKeys` chứa CAS key.
- Output `module-visibility` cũ **không đổi** (byte-for-byte schema).

**Triển khai:**
- `GET /platform/workspaces/:workspaceId/capability-manifest` — **không** overload
  `module-visibility`.
- Resolver compose `surfaceStatus` từ: (1) static released-surface policy;
  (2) `mvp-surface.json` (`enabled`/`id`/`path`/`method`), key theo `id` →
  `contractEndpoint`; (3) entitlement/module preference (`workspaceModuleConfigs`,
  `userWorkspaceModulePreferences`, `OPTIONAL_MODULE_KEYS`); (4) connector status
  (CAS via finance-legal bank-connection); (5) operator override.
- **Chỉ** persist + audit operator override (migration 35). Không lưu bản sao
  toàn bộ manifest.
- 3 key legacy `finance/legal/crm` xuất hiện thành 3 surface entry.
- Đăng ký route trong `mvp-surface.json` với `backend_test`/`flutter_test`/
  `integration_test` ownership; chạy `scripts/gen-mvp-contracts.mjs`. Không xóa
  route legacy, không thêm allowlist cho backend thiếu.
- **Follow-up task (ghi vào issue, không làm ở A1):** Flutter ngừng gọi
  `module-visibility` sau khi mọi consumer đọc manifest → retire endpoint cũ.

**Chạy xanh:** `make mvp-contracts-check mvp-surface-check frontend-api-contract-check`
+ `cd services/cosa && npx vitest run tests/workspace-capability-manifest.test.ts`.

### A1.2 — Founder Trial Board read model (Company)

**Files:**
- Create: `services/company/operations/strategy/services/founder-trial-board.service.ts`
- Create: `services/company/operations/strategy/handlers/founder-trial-board.handler.ts`
- Create: `services/company/operations/tests/founder-trial-board.service.test.ts`
- Modify: `shared/contracts/mvp-surface.json`

**Test đỏ (dùng fixture dữ liệu thật, không mock authority):**
- Seed: 1 project + operating cycle (duration 8), 3 assumptions (importance/
  uncertainty khác nhau, `status=untested`), 1 experiment link assumption,
  1 evidence `approved` gắn `experimentId`, 1 evidence `candidate` **không**
  `experimentId`, 1 decision record.
- Board trả: cycle (duration/revision/stage/calendar state + slot từ `cycle_reviews`);
  top 1–3 assumption theo `getRankedAssumptionsByProjectInWorkspace`;
  experiments join assumption; evidence nhóm candidate/approved/rejected, mỗi item
  cờ `linkedToExperiment`; decisions.
- Evidence không `experimentId` được gắn `unlinked: true` và nằm ngoài mọi
  tính toán readiness.
- Project ở workspace khác → không đọc được (mọi read filter project + workspace).
- Adapter finance/marketing trả typed `{ state: "unavailable" | "configuration_required" }`,
  không nuốt lỗi thành rỗng.

**Triển khai:** `GET /operations/projects/:projectId/founder-trial-board` —
composition thuần, **không bảng mới**. Đọc:
`twelve_week_cycles` + `cycle_reviews` + `getRankedAssumptionsByProjectInWorkspace`
+ `listExperimentsInWorkspace({projectId})` + `strategy.evidence` (filter project)
+ `listDecisionRecordsInWorkspace({projectId})`. Finance/marketing gọi qua
service in-process, bắt lỗi thành trạng thái typed.

### A1.3 — Quy tắc Founder Trial nghiêm hơn generic (blocking R1)

**Files:**
- Modify: `services/company/operations/strategy/services/experiment-proposal.service.ts`
- Modify: `services/company/operations/strategy/handlers/experiment.handler.ts`
- Modify: `services/company/operations/tests/experiment.service.test.ts`

**Test đỏ:** command/path Founder-Trial cho experiment-create **từ chối** khi
thiếu `assumptionId`, hoặc `method` rỗng, hoặc `successCriteria` rỗng; `assumptionId`
phải resolve trong cùng workspace + project. Generic `POST /operations/strategy/experiments`
**vẫn permissive** (regression test giữ nguyên hành vi cũ).

**Triển khai:** thêm cờ `founderTrial: true` (hoặc endpoint
`POST /operations/projects/:projectId/founder-trial/experiments`) đi qua nhánh
validate nghiêm. `successCriteria` giữ dạng text — chỉ hiển thị ngưỡng founder
đặt, **không** tự tính verdict. Không migration, không JSON.

### A1.4 — Flutter: shell trung thực + board

**Files:**
- Create: `frontend/lib/core/services/workspace_capability_manifest_model.dart`
- Create: `frontend/lib/core/services/workspace_capability_manifest_service.dart`
- Create: `frontend/lib/core/services/workspace_capability_manifest_controller.dart`
- Create: `frontend/lib/core/widgets/surface_state_view.dart`
- Create: `frontend/lib/modules/strategy/founder_trial/founder_trial_board_controller.dart`
- Create: `frontend/lib/modules/strategy/founder_trial/founder_trial_board_view.dart`
- Modify: `frontend/lib/core/routing/module_routes.dart`
- Tests: `frontend/test/core/services/workspace_capability_manifest_controller_test.dart`,
  `frontend/test/modules/strategy/founder_trial_board_view_test.dart`

**Test đỏ:**
- Manifest controller fail-closed trước khi có snapshot; map đủ 5 `surfaceStatus`;
  giữ lỗi API là `UNAVAILABLE` + retry.
- Board hiển thị chuỗi `Operating Cycle → Assumptions (top 1–3) → Experiments →
  Evidence (candidate/approved/rejected, đánh dấu unlinked) → Decision`.
- Experiment form Founder-Trial bắt buộc chọn assumption + nhập method +
  successCriteria; không cho submit khi thiếu.
- Card PLANNED (Vision/Mission/Value, PESTEL, SWOT/TOWS, BSC, Vault/RAG,
  workflow builder, voice) render roadmap, **không** CTA thao tác.

**Triển khai:** `SurfaceStateView` phân biệt rõ AVAILABLE / PILOT /
CONFIGURATION_REQUIRED / PLANNED / UNAVAILABLE. Shell cards stage-aware:
`Start / This week / Evidence / Cash / Decision` (spec §9 Slice A). Dùng
`MvpRequestClient` cho endpoint typed mới.

### A1.5 — Verify slice

```
make mvp-contracts-check mvp-surface-check frontend-api-contract-check route-inventory-check company-boundary-check encore-handler-boundary-check ts-suppression-check
cd services/company && encore test operations/tests/founder-trial-board.service.test.ts operations/tests/experiment.service.test.ts
cd services/cosa && npx vitest run tests/workspace-capability-manifest.test.ts
cd frontend && flutter test test/core/services/workspace_capability_manifest_controller_test.dart test/modules/strategy/founder_trial_board_view_test.dart && flutter analyze --no-pub
```
Kỳ vọng: PASS; không state nào che lỗi request thành workspace rỗng; không CTA
live nào thiếu backend contract.
