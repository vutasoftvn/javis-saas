# Kickoff Bước 3 AI Suggestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Founder tới Bước 3 ("Chốt tuần đầu") của Project Kickoff Wizard được AI tự động gợi ý sẵn `firstWeekOutcome` + 1-3 `firstWeekActions` (dựa trên context Bước 1/2 đã autosave), có thể accept nguyên trạng hoặc sửa tự do; icon "✨" cho phép tạo lại bất kỳ lúc nào.

**Architecture:** `services/company` điều phối (mint `run_id`, gọi `apps/cosa` qua HTTP service-to-service, nhận callback webhook) — tái dùng nguyên khuôn round-trip đã chứng minh ở `copilot_routes.py`/`copilot_run.py` (customer-support copilot). `apps/cosa` chạy `kernel.run` với agent `operations`, KHÔNG gọi capability nào (thuần suy luận, giống `execute_goal_decomposition_task` của WGA), parse output theo schema cố định, rồi POST callback kết quả về company. FE poll `GET .../operating-setup` (route đã có) mỗi 2s/timeout 30s.

**Tech Stack:** Encore.ts + Drizzle (`services/company`), FastAPI + Python worker (`apps/cosa`), Flutter/GetX (`frontend`).

## Global Constraints

- Migration release chỉ Expand — không sửa/xoá cột hiện có, chỉ thêm cột nullable mới (Encore Guardrail #4).
- Handler Encore không import `drizzle-orm`/`db.ts`/DB schema trực tiếp — chỉ gọi service (Encore Guardrail #1).
- Không dùng `any`, `@ts-ignore`, `@ts-expect-error` (Encore Guardrail #5).
- Route webhook callback (`.../result`) xác thực bằng `X-Cosa-Service-Token` so khớp `COSA_SERVICE_TOKEN`, KHÔNG qua `requireWorkspaceAccess` — đúng pattern `applyCopilotResultApi` đã có, và KHÔNG cần thêm vào `EXPLICIT_UNAUTHENTICATED_ALLOWLIST` (route không khai `auth: false` tường minh trong object literal, nên gate `route-auth-allowlist-check` không flag nó — xác nhận bằng việc `applyCopilotResultApi` hiện tại cũng không có trong allowlist).
- KHÔNG cần cập nhật `shared/contracts/mvp-surface.json` — đã xác nhận 3 route hiện có của `project-operating-setup` (GET/PUT/activate) cũng không nằm trong file này; đây là allowlist riêng cho một tập "MVP surface" capability, không phải registry toàn bộ route.
- KHÔNG cần env var mới — `COSA_SERVICE_TOKEN`, `COSA_INTERNAL_URL`, `COMPANY_SERVICE_URL` đã tồn tại và có dev-default (`is_strict_env()`/`isStrict()` false ở dev/test).
- Mọi thay đổi `services/company` chạy `cd services/company && npx tsc --noEmit`, `make company-boundary-check`, `make encore-handler-boundary-check`, `make ts-suppression-check` sau khi xong.
- Mọi thay đổi Python chạy qua `.venv/bin/python` (`source .venv/bin/activate` trước khi gọi `pytest` lẻ).
- Comment code mới bằng tiếng Việt cho phần giải thích lý do; định danh/log giữ tiếng Anh (CLAUDE.md).

---

## File Structure

**Mới:**
- `services/company/operations/migrations/40_kickoff_ai_suggestion.up.sql` / `.down.sql`
- `services/company/operations/strategy/services/kickoff-suggestion-cosa-client.ts` — HTTP client gọi `apps/cosa` (mẫu `copilot-cosa-client.ts`)
- `services/company/operations/tests/kickoff-suggestion.test.ts` — test cho dispatch + callback service
- `apps/cosa/agents/kickoff_suggestion.py` — pure helpers: prompt + schema + parser (mẫu `goal_decomposition.py`)
- `apps/cosa/worker/kickoff_suggestion_run.py` — worker execution + callback (mẫu lai `copilot_run.py`/`wga_run.py`)
- `apps/cosa/api/kickoff_suggestion_routes.py` — FastAPI route (mẫu `copilot_routes.py`)
- `tests/apps/cosa/test_kickoff_suggestion.py` — unit test parser/prompt
- `tests/apps/cosa/worker/test_kickoff_suggestion_run.py` — test worker execution (mock plane)
- `tests/apps/cosa/test_kickoff_suggestion_route.py` — test FastAPI route

**Sửa:**
- `services/company/shared/db/schema/strategy.ts` — thêm 5 cột vào `projectOperatingSetups`
- `services/company/operations/strategy/services/project-operating-setup.service.ts` — mở rộng `ProjectOperatingSetupView`/`toView` + thêm `requestKickoffSuggestion`/`applyKickoffSuggestionResult`
- `services/company/operations/strategy/handlers/project-operating-setup.handler.ts` — thêm 2 endpoint
- `apps/cosa/api/app.py` — đăng ký router mới
- `apps/cosa/worker/main.py` — thêm nhánh dispatch `task_type == "kickoff_suggestion"`
- `frontend/lib/data/models/project_operating_setup_model.dart` — thêm field AI suggestion
- `frontend/lib/modules/strategy/services/project_operating_setup_service.dart` — thêm `requestKickoffSuggestion()`
- `frontend/lib/modules/strategy/controllers/project_kickoff_controller.dart` — thêm polling + trigger
- `frontend/lib/modules/strategy/views/project_kickoff_view.dart` — hook auto-trigger Bước 2, icon Bước 3
- `frontend/test/modules/strategy/controllers/project_kickoff_controller_test.dart`
- `frontend/test/data/models/project_operating_setup_model_test.dart`
- `frontend/test/modules/strategy/services/project_operating_setup_service_test.dart`

---

### Task 1: Data model — migration + Drizzle schema

**Files:**
- Create: `services/company/operations/migrations/40_kickoff_ai_suggestion.up.sql`
- Create: `services/company/operations/migrations/40_kickoff_ai_suggestion.down.sql`
- Modify: `services/company/shared/db/schema/strategy.ts:277-295` (bảng `projectOperatingSetups`)

**Interfaces:**
- Produces: 5 cột mới trên `strategy.project_operating_setups` — `ai_suggestion_status`, `ai_suggestion_run_id`, `ai_suggested_outcome`, `ai_suggested_actions`, `ai_suggestion_requested_at`. Task 2 dùng các cột này qua field Drizzle tương ứng (`aiSuggestionStatus`, `aiSuggestionRunId`, `aiSuggestedOutcome`, `aiSuggestedActions`, `aiSuggestionRequestedAt`).

- [ ] **Step 1: Viết migration up**

```sql
-- Kickoff wizard Bước 3 — AI gợi ý outcome + việc tuần đầu (spec
-- docs/superpowers/specs/2026-09-04-kickoff-step3-ai-suggestion-design.md).
-- Company điều phối round-trip company<->apps/cosa; ghi đè trực tiếp lên
-- draft, không lưu lịch sử nhiều lần gợi ý (ngoài phạm vi §11).
ALTER TABLE strategy.project_operating_setups
  ADD COLUMN ai_suggestion_status TEXT NULL
    CHECK (ai_suggestion_status IN ('dispatched', 'completed', 'failed')),
  ADD COLUMN ai_suggestion_run_id TEXT NULL,
  ADD COLUMN ai_suggested_outcome TEXT NULL,
  ADD COLUMN ai_suggested_actions JSONB NULL,
  ADD COLUMN ai_suggestion_requested_at TIMESTAMPTZ NULL;
```

Lưu vào `services/company/operations/migrations/40_kickoff_ai_suggestion.up.sql`.

- [ ] **Step 2: Viết migration down**

```sql
ALTER TABLE strategy.project_operating_setups
  DROP COLUMN IF EXISTS ai_suggestion_status,
  DROP COLUMN IF EXISTS ai_suggestion_run_id,
  DROP COLUMN IF EXISTS ai_suggested_outcome,
  DROP COLUMN IF EXISTS ai_suggested_actions,
  DROP COLUMN IF EXISTS ai_suggestion_requested_at;
```

Lưu vào `services/company/operations/migrations/40_kickoff_ai_suggestion.down.sql`.

- [ ] **Step 3: Cập nhật Drizzle schema**

Trong `services/company/shared/db/schema/strategy.ts`, sửa bảng `projectOperatingSetups` (dòng 277-295):

```typescript
// 13d. Project Operating Setups (Founder Project Kickoff)
export const projectOperatingSetups = strategySchema.table("project_operating_setups", {
  projectId: bigint("project_id", { mode: "bigint" }).primaryKey(),
  workspaceId: bigint("workspace_id", { mode: "bigint" }).notNull(),
  status: varchar("status", { length: 20 }).default("NOT_STARTED").notNull(),
  targetCustomer: text("target_customer"),
  problemStatement: text("problem_statement"),
  evidenceLevel: varchar("evidence_level", { length: 40 }),
  recommendedStage: varchar("recommended_stage", { length: 50 }),
  selectedStage: varchar("selected_stage", { length: 50 }),
  stageDurationWeeks: integer("stage_duration_weeks"),
  stageTargetDate: timestamp("stage_target_date", { withTimezone: true }),
  roundStartDate: timestamp("round_start_date", { withTimezone: true }),
  weeklyReviewWeekday: integer("weekly_review_weekday"),
  weeklyReviewTime: varchar("weekly_review_time", { length: 5 }),
  firstWeekOutcome: text("first_week_outcome"),
  firstWeekActions: jsonb("first_week_actions").default([]).notNull(),
  aiSuggestionStatus: varchar("ai_suggestion_status", { length: 20 }),
  aiSuggestionRunId: text("ai_suggestion_run_id"),
  aiSuggestedOutcome: text("ai_suggested_outcome"),
  aiSuggestedActions: jsonb("ai_suggested_actions"),
  aiSuggestionRequestedAt: timestamp("ai_suggestion_requested_at", { withTimezone: true }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).defaultNow().notNull(),
});
```

- [ ] **Step 4: Chạy migration + verify rollback**

```bash
cd /Volumes/SSD/javis-saas
bash -lc 'source scripts/load-dev-env.sh && node services/company/scripts/migrate.mjs'
```

Expected: log in ra `applying operations/40_kickoff_ai_suggestion.up.sql` rồi `applied N migration(s)` không lỗi.

Verify cột đã tạo:

```bash
PGPASSWORD=dev-postgres-password psql -h 127.0.0.1 -U postgres -d company -c "\d strategy.project_operating_setups" | grep ai_suggestion
```

Expected: 5 dòng cột mới xuất hiện.

Verify rollback chạy được (không cần giữ trạng thái rollback, chỉ xác nhận down.sql hợp lệ rồi migrate up lại):

```bash
PGPASSWORD=dev-postgres-password psql -h 127.0.0.1 -U postgres -d company -f services/company/operations/migrations/40_kickoff_ai_suggestion.down.sql
bash -lc 'source scripts/load-dev-env.sh && node services/company/scripts/migrate.mjs'
```

- [ ] **Step 5: Commit**

```bash
git add services/company/operations/migrations/40_kickoff_ai_suggestion.up.sql \
        services/company/operations/migrations/40_kickoff_ai_suggestion.down.sql \
        services/company/shared/db/schema/strategy.ts
git commit -m "feat(company): thêm cột AI suggestion vào project_operating_setups"
```

---

### Task 2: Company — mở rộng read view (`ProjectOperatingSetupView`)

**Files:**
- Modify: `services/company/operations/strategy/services/project-operating-setup.service.ts:41-58` (interface), `:216-239` (`toView`)
- Modify: `services/company/operations/tests/project-operating-setup.test.ts` (thêm test)

**Interfaces:**
- Consumes: cột Drizzle từ Task 1 (`row.aiSuggestionStatus`, `row.aiSuggestionRunId`, `row.aiSuggestedOutcome`, `row.aiSuggestedActions`).
- Produces: `ProjectOperatingSetupView.aiSuggestionStatus: 'dispatched' | 'completed' | 'failed' | null`, `.aiSuggestedOutcome: string | null`, `.aiSuggestedActions: string[] | null` — Task 3/4/Frontend Task 8 dùng các field này.

- [ ] **Step 1: Viết test cho GET trả field mới (RED)**

Thêm vào cuối `services/company/operations/tests/project-operating-setup.test.ts` — file này test qua endpoint (`getProjectOperatingSetupEndpoint`/`putProjectOperatingSetupEndpoint`), dùng helper `createTestWorkspaceWithMember()` (trả `{workspaceId, bearerToken, ...}`) + `createProject({authorization, workspaceId, title})` đã import sẵn ở đầu file (dòng 8, 15):

```typescript
describe("aiSuggestion fields on ProjectOperatingSetupView", () => {
  it("trả về null cho aiSuggestionStatus/aiSuggestedOutcome/aiSuggestedActions khi chưa từng gọi AI suggestion", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Discovery",
    });

    const view = await getProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });

    expect(view.aiSuggestionStatus).toBeNull();
    expect(view.aiSuggestedOutcome).toBeNull();
    expect(view.aiSuggestedActions).toBeNull();
  });
});
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

```bash
cd services/company && npx vitest run operations/tests/project-operating-setup.test.ts -t "aiSuggestion fields"
```

Expected: FAIL — `view.aiSuggestionStatus` là `undefined` (chưa có field) chứ không phải lỗi biên dịch (vì TS interface chưa có field, test file sẽ lỗi biên dịch trước — đó cũng là FAIL hợp lệ, ghi nhận rồi qua Step 3).

- [ ] **Step 3: Mở rộng interface + `toView`**

Trong `project-operating-setup.service.ts`, sửa `ProjectOperatingSetupView` (dòng 41-58):

```typescript
export interface ProjectOperatingSetupView {
  projectId: string;
  workspaceId: string;
  status: OperatingSetupStatus;
  targetCustomer: string | null;
  problemStatement: string | null;
  evidenceLevel: EvidenceLevel | null;
  recommendedStage: BasicKickoffStage | null;
  selectedStage: BasicKickoffStage | null;
  stageDurationWeeks: number | null;
  stageTargetDate: string | null;
  roundStartDate: string | null;
  weeklyReviewWeekday: number | null;
  weeklyReviewTime: string | null;
  firstWeekOutcome: string | null;
  firstWeekActions: FirstWeekActionView[];
  aiSuggestionStatus: "dispatched" | "completed" | "failed" | null;
  aiSuggestedOutcome: string | null;
  aiSuggestedActions: string[] | null;
  updatedAt: string | null;
}
```

Sửa hàm `toView` (dòng 216-239) — thêm 3 field vào object trả về:

```typescript
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
    aiSuggestionStatus: (row.aiSuggestionStatus as "dispatched" | "completed" | "failed" | null) ?? null,
    aiSuggestedOutcome: row.aiSuggestedOutcome ?? null,
    aiSuggestedActions: (row.aiSuggestedActions as string[] | null) ?? null,
    updatedAt: row.updatedAt ? row.updatedAt.toISOString() : null,
  };
}
```

Trong `getProjectOperatingSetup` (dòng 260-305), nhánh trả default khi chưa có `setup` (dòng 283-301) — thêm 3 field null:

```typescript
  if (!setup) {
    return {
      projectId,
      workspaceId: ctx.workspaceId,
      status: "NOT_STARTED",
      targetCustomer: null,
      problemStatement: null,
      evidenceLevel: null,
      recommendedStage: "P0_DISCOVERY",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
      stageTargetDate: null,
      roundStartDate: null,
      weeklyReviewWeekday: 5,
      weeklyReviewTime: "16:00",
      firstWeekOutcome: null,
      firstWeekActions: [],
      aiSuggestionStatus: null,
      aiSuggestedOutcome: null,
      aiSuggestedActions: null,
      updatedAt: null,
    };
  }
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

```bash
cd services/company && npx vitest run operations/tests/project-operating-setup.test.ts -t "aiSuggestion fields"
```

Expected: PASS.

- [ ] **Step 5: Chạy toàn bộ test file + typecheck**

```bash
cd services/company && npx vitest run operations/tests/project-operating-setup.test.ts
cd services/company && npx tsc --noEmit
```

Expected: tất cả PASS, không lỗi biên dịch (các call site khác dựng `ProjectOperatingSetupView` thủ công, nếu có, sẽ lộ lỗi thiếu field ở bước này — sửa bổ sung nếu tsc báo).

- [ ] **Step 6: Commit**

```bash
git add services/company/operations/strategy/services/project-operating-setup.service.ts \
        services/company/operations/tests/project-operating-setup.test.ts
git commit -m "feat(company): mở rộng ProjectOperatingSetupView với field AI suggestion"
```

---

### Task 3: Company — dispatch (`requestKickoffSuggestion` + cosa client + route)

Test trong task này gọi qua **endpoint** (`requestKickoffSuggestionEndpoint`), đúng convention đã có của `project-operating-setup.test.ts` (test qua `getProjectOperatingSetupEndpoint`/`putProjectOperatingSetupEndpoint`, không dựng `TenantContext` tay) — vì vậy service + handler được viết cùng 1 task thay vì tách riêng.

**Files:**
- Create: `services/company/operations/strategy/services/kickoff-suggestion-cosa-client.ts`
- Modify: `services/company/operations/strategy/services/project-operating-setup.service.ts` (thêm hàm `requestKickoffSuggestion`)
- Modify: `services/company/operations/strategy/handlers/project-operating-setup.handler.ts` (thêm 1 endpoint)
- Create: `services/company/operations/tests/kickoff-suggestion.test.ts`

**Interfaces:**
- Consumes: `TenantContext` (đã import sẵn trong service.ts), `randomUUID` (đã import sẵn), `recommendKickoffStage` (đã có trong cùng file, dòng 136), `requireWorkspaceAccess` (đã import sẵn trong handler.ts), helper test `createTestWorkspaceWithMember`/`createProject` (đã import sẵn trong `project-operating-setup.test.ts`, dùng lại ở đây).
- Produces: `dispatchKickoffSuggestionRun(payload): Promise<void>` + `setCustomKickoffSuggestionRunner(runner): void` (test injection seam); `requestKickoffSuggestion(ctx, projectId): Promise<KickoffSuggestionDispatchResult>` (service, dùng nội bộ bởi handler); route `POST /operations/projects/:id/kickoff-suggestion` — Frontend Task 8 gọi qua `ApiClient.post`. Task 4 tái dùng `KickoffSuggestionDispatchResult` không cần import lại (cùng file service).

- [ ] **Step 1: Viết test cho client (RED)**

Tạo `services/company/operations/tests/kickoff-suggestion.test.ts`:

```typescript
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
  dispatchKickoffSuggestionRun,
  setCustomKickoffSuggestionRunner,
} from "../strategy/services/kickoff-suggestion-cosa-client";

describe("kickoff-suggestion-cosa-client", () => {
  afterEach(() => {
    setCustomKickoffSuggestionRunner(null);
  });

  it("gọi runner tuỳ chỉnh khi được set (test injection seam)", async () => {
    let received: any = null;
    setCustomKickoffSuggestionRunner(async (payload) => {
      received = payload;
    });

    await dispatchKickoffSuggestionRun({
      workspaceId: "ws1",
      projectId: "p1",
      runId: "run-abc",
      targetCustomer: "Founder B2B SaaS",
      problemStatement: "Không biết validate ý tưởng",
      evidenceLevel: "NONE",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
    });

    expect(received).toEqual({
      workspaceId: "ws1",
      projectId: "p1",
      runId: "run-abc",
      targetCustomer: "Founder B2B SaaS",
      problemStatement: "Không biết validate ý tưởng",
      evidenceLevel: "NONE",
      selectedStage: "P0_DISCOVERY",
      stageDurationWeeks: 2,
    });
  });

  it("throw khi runner tuỳ chỉnh throw (không nuốt lỗi)", async () => {
    setCustomKickoffSuggestionRunner(async () => {
      throw new Error("cosa unreachable");
    });

    await expect(
      dispatchKickoffSuggestionRun({
        workspaceId: "ws1",
        projectId: "p1",
        runId: "run-abc",
        targetCustomer: "x",
        problemStatement: "y",
        evidenceLevel: "NONE",
        selectedStage: "P0_DISCOVERY",
        stageDurationWeeks: 2,
      })
    ).rejects.toThrow("cosa unreachable");
  });
});
```

- [ ] **Step 2: Chạy test, xác nhận FAIL (module chưa tồn tại)**

```bash
cd services/company && npx vitest run operations/tests/kickoff-suggestion.test.ts
```

Expected: FAIL — `Cannot find module '../strategy/services/kickoff-suggestion-cosa-client'`.

- [ ] **Step 3: Viết `kickoff-suggestion-cosa-client.ts`**

```typescript
import { requireCosaInternalUrl, requireCosaServiceToken } from "../../../shared/events/service-identity";

export interface DispatchKickoffSuggestionPayload {
  workspaceId: string;
  projectId: string;
  runId: string;
  targetCustomer: string;
  problemStatement: string;
  evidenceLevel: string;
  selectedStage: string;
  stageDurationWeeks: number;
}

export type DispatchKickoffSuggestionRunner = (
  payload: DispatchKickoffSuggestionPayload
) => Promise<void>;

let customRunner: DispatchKickoffSuggestionRunner | null = null;

export function setCustomKickoffSuggestionRunner(runner: DispatchKickoffSuggestionRunner | null): void {
  customRunner = runner;
}

export async function dispatchKickoffSuggestionRun(
  payload: DispatchKickoffSuggestionPayload
): Promise<void> {
  if (customRunner) {
    await customRunner(payload);
    return;
  }

  const cosaBaseUrl = requireCosaInternalUrl();
  const serviceToken = requireCosaServiceToken();

  const response = await fetch(`${cosaBaseUrl}/agent/kickoff/first-week-suggestion`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Cosa-Service-Token": serviceToken,
    },
    body: JSON.stringify({
      workspace_id: payload.workspaceId,
      project_id: payload.projectId,
      run_id: payload.runId,
      target_customer: payload.targetCustomer,
      problem_statement: payload.problemStatement,
      evidence_level: payload.evidenceLevel,
      selected_stage: payload.selectedStage,
      stage_duration_weeks: payload.stageDurationWeeks,
    }),
  });

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`COSA returned ${response.status}: ${errText}`);
  }
}
```

- [ ] **Step 4: Chạy test client, xác nhận PASS**

```bash
cd services/company && npx vitest run operations/tests/kickoff-suggestion.test.ts
```

Expected: 2 test PASS.

- [ ] **Step 5: Viết test cho endpoint `requestKickoffSuggestion` (RED)**

Thêm vào `services/company/operations/tests/kickoff-suggestion.test.ts` (import thêm `createTestWorkspaceWithMember`, `createProject`, `putProjectOperatingSetupEndpoint`, `getProjectOperatingSetupEndpoint` — đúng như đầu `project-operating-setup.test.ts` đã làm):

```typescript
import { and, eq } from "drizzle-orm";
import { db } from "../models/db";
import * as schema from "../../shared/db/schema/strategy";
import { createProject } from "../handlers/project.handler";
import { createTestWorkspaceWithMember } from "./_helpers";
import {
  getProjectOperatingSetupEndpoint,
  putProjectOperatingSetupEndpoint,
  requestKickoffSuggestionEndpoint,
} from "../strategy/handlers/project-operating-setup.handler";

describe("requestKickoffSuggestionEndpoint", () => {
  afterEach(() => {
    setCustomKickoffSuggestionRunner(null);
  });

  it("throw khi Bước 1 chưa đủ (targetCustomer/problemStatement/evidenceLevel rỗng)", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Discovery",
    });

    await expect(
      requestKickoffSuggestionEndpoint({
        authorization: ws.bearerToken,
        workspaceId: ws.workspaceId,
        id: project.id,
      })
    ).rejects.toThrow();
  });

  it("set aiSuggestionStatus=dispatched và gọi cosa client khi Bước 1 đủ", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Discovery",
    });
    await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      targetCustomer: "Founder B2B SaaS",
      problemStatement: "Không biết validate ý tưởng",
      evidenceLevel: "NONE",
    });

    let dispatchedPayload: any = null;
    setCustomKickoffSuggestionRunner(async (payload) => {
      dispatchedPayload = payload;
    });

    const result = await requestKickoffSuggestionEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    expect(result.status).toBe("dispatched");
    expect(dispatchedPayload.projectId).toBe(project.id);
    expect(dispatchedPayload.targetCustomer).toBe("Founder B2B SaaS");
    expect(dispatchedPayload.runId).toBe(result.runId);

    const view = await getProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    expect(view.aiSuggestionStatus).toBe("dispatched");
  });

  it("set aiSuggestionStatus=failed khi cosa client throw, không throw endpoint ra ngoài", async () => {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Discovery",
    });
    await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      targetCustomer: "x",
      problemStatement: "y",
      evidenceLevel: "NONE",
    });

    setCustomKickoffSuggestionRunner(async () => {
      throw new Error("cosa down");
    });

    const result = await requestKickoffSuggestionEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    expect(result.status).toBe("failed");

    const view = await getProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    expect(view.aiSuggestionStatus).toBe("failed");
  });
});
```

- [ ] **Step 6: Chạy test, xác nhận FAIL**

```bash
cd services/company && npx vitest run operations/tests/kickoff-suggestion.test.ts -t "requestKickoffSuggestionEndpoint"
```

Expected: FAIL — `requestKickoffSuggestionEndpoint` chưa được export từ handler.

- [ ] **Step 7: Viết `requestKickoffSuggestion` trong service + endpoint trong handler**

Thêm vào cuối `services/company/operations/strategy/services/project-operating-setup.service.ts` (sau `activateProjectOperatingSetup`), và thêm import `dispatchKickoffSuggestionRun` ở đầu file cạnh các import khác:

```typescript
import {
  dispatchKickoffSuggestionRun,
} from "./kickoff-suggestion-cosa-client";
```

```typescript
export interface KickoffSuggestionDispatchResult {
  runId: string;
  status: "dispatched" | "failed";
}

export async function requestKickoffSuggestion(
  ctx: TenantContext,
  projectId: string
): Promise<KickoffSuggestionDispatchResult> {
  const wsId = BigInt(ctx.workspaceId);
  const pId = BigInt(projectId);

  const [proj] = await db
    .select({ id: projects.id })
    .from(projects)
    .where(and(eq(projects.id, pId), eq(projects.workspaceId, wsId)))
    .limit(1);
  if (!proj) {
    throw APIError.notFound("Project không tồn tại trong workspace này");
  }

  const [existing] = await db
    .select()
    .from(projectOperatingSetups)
    .where(and(eq(projectOperatingSetups.projectId, pId), eq(projectOperatingSetups.workspaceId, wsId)))
    .limit(1);

  if (
    !existing ||
    !existing.targetCustomer?.trim() ||
    !existing.problemStatement?.trim() ||
    !existing.evidenceLevel
  ) {
    throw APIError.failedPrecondition(
      "Hoàn thành Bước 1 (đối tượng, vấn đề, mức bằng chứng) trước khi tạo gợi ý AI"
    );
  }

  const runId = randomUUID();

  await db
    .update(projectOperatingSetups)
    .set({
      aiSuggestionStatus: "dispatched",
      aiSuggestionRunId: runId,
      aiSuggestionRequestedAt: new Date(),
    })
    .where(and(eq(projectOperatingSetups.projectId, pId), eq(projectOperatingSetups.workspaceId, wsId)));

  const selectedStage =
    (existing.selectedStage as BasicKickoffStage | null) ??
    recommendKickoffStage(existing.evidenceLevel as EvidenceLevel);

  try {
    await dispatchKickoffSuggestionRun({
      workspaceId: ctx.workspaceId,
      projectId,
      runId,
      targetCustomer: existing.targetCustomer,
      problemStatement: existing.problemStatement,
      evidenceLevel: existing.evidenceLevel,
      selectedStage,
      stageDurationWeeks: existing.stageDurationWeeks ?? 2,
    });
    return { runId, status: "dispatched" };
  } catch {
    await db
      .update(projectOperatingSetups)
      .set({ aiSuggestionStatus: "failed" })
      .where(and(eq(projectOperatingSetups.projectId, pId), eq(projectOperatingSetups.workspaceId, wsId)));
    return { runId, status: "failed" };
  }
}
```

Trong `services/company/operations/strategy/handlers/project-operating-setup.handler.ts`, sửa khối import (dòng 3-13) thêm `requestKickoffSuggestion` và `KickoffSuggestionDispatchResult`:

```typescript
import {
  getProjectOperatingSetup,
  saveProjectOperatingSetup,
  activateProjectOperatingSetup,
  requestKickoffSuggestion,
  ProjectOperatingSetupView,
  SaveProjectOperatingSetupRequest,
  ActivateProjectOperatingSetupRequest,
  KickoffSuggestionDispatchResult,
  OperatingSetupStatus,
  EvidenceLevel,
  BasicKickoffStage,
  FirstWeekAction,
} from "../services/project-operating-setup.service";

export type {
  ProjectOperatingSetupView,
  SaveProjectOperatingSetupRequest,
  ActivateProjectOperatingSetupRequest,
  KickoffSuggestionDispatchResult,
  OperatingSetupStatus,
  EvidenceLevel,
  BasicKickoffStage,
  FirstWeekAction,
};
```

Thêm cuối file (sau `activateProjectOperatingSetupEndpoint`):

```typescript
export interface RequestKickoffSuggestionParams {
  id: string;
  workspaceId: Header<"X-Workspace-Id">;
  authorization?: Header<"Authorization">;
}

// ── POST /operations/projects/:id/kickoff-suggestion ──
export const requestKickoffSuggestionEndpoint = api(
  { method: "POST", path: "/operations/projects/:id/kickoff-suggestion", expose: true },
  async (params: RequestKickoffSuggestionParams): Promise<KickoffSuggestionDispatchResult> => {
    const ctx = await requireWorkspaceAccess(params.authorization, params.workspaceId);
    return requestKickoffSuggestion(ctx, params.id);
  }
);
```

- [ ] **Step 8: Chạy test, xác nhận PASS**

```bash
cd services/company && npx vitest run operations/tests/kickoff-suggestion.test.ts
cd services/company && npx tsc --noEmit
```

Expected: tất cả PASS, không lỗi biên dịch.

- [ ] **Step 9: Commit**

```bash
git add services/company/operations/strategy/services/kickoff-suggestion-cosa-client.ts \
        services/company/operations/strategy/services/project-operating-setup.service.ts \
        services/company/operations/strategy/handlers/project-operating-setup.handler.ts \
        services/company/operations/tests/kickoff-suggestion.test.ts
git commit -m "feat(company): dispatch kickoff AI suggestion sang apps/cosa"
```

---

### Task 4: Company — callback + route webhook mới

Cũng test qua endpoint, tiếp tục dùng `createTestWorkspaceWithMember`/`createProject`/`putProjectOperatingSetupEndpoint`/`requestKickoffSuggestionEndpoint` (Task 3) để dựng state `dispatched` trước khi gọi callback.

**Files:**
- Modify: `services/company/operations/strategy/services/project-operating-setup.service.ts` (thêm `applyKickoffSuggestionResult`)
- Modify: `services/company/operations/strategy/handlers/project-operating-setup.handler.ts` (thêm 1 endpoint)
- Modify: `services/company/operations/tests/kickoff-suggestion.test.ts` (thêm test callback)

**Interfaces:**
- Consumes: `requestKickoffSuggestionEndpoint` (Task 3), `getProjectOperatingSetupEndpoint` (Task 2/3).
- Produces: `POST /operations/projects/:id/kickoff-suggestion/result` → `{applied: boolean}` — `apps/cosa` (Task 6) gọi endpoint này qua HTTP webhook, không import trực tiếp.

- [ ] **Step 1: Viết test cho endpoint callback (RED)**

Thêm vào `kickoff-suggestion.test.ts` (thêm `applyKickoffSuggestionResultEndpoint` vào import đã có ở Task 3 Step 5):

```typescript
import { applyKickoffSuggestionResultEndpoint } from "../strategy/handlers/project-operating-setup.handler";

describe("applyKickoffSuggestionResultEndpoint", () => {
  afterEach(() => {
    setCustomKickoffSuggestionRunner(null);
  });

  async function dispatchedProject() {
    const ws = await createTestWorkspaceWithMember();
    const project = await createProject({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      title: "Discovery",
    });
    await putProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
      targetCustomer: "x",
      problemStatement: "y",
      evidenceLevel: "NONE",
    });
    setCustomKickoffSuggestionRunner(async () => {});
    const { runId } = await requestKickoffSuggestionEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    return { ws, project, runId };
  }

  it("cập nhật outcome/actions khi runId khớp và status=completed", async () => {
    const { ws, project, runId } = await dispatchedProject();

    const result = await applyKickoffSuggestionResultEndpoint({
      id: project.id,
      runId,
      status: "completed",
      outcome: "Hoàn thành 5 cuộc phỏng vấn khách hàng mục tiêu",
      actions: ["Phỏng vấn 5 khách hàng mục tiêu", "Ghi chép pain point vào bảng theo dõi"],
      serviceToken: "local-dev-service-token",
    });

    expect(result.applied).toBe(true);
    const view = await getProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    expect(view.aiSuggestionStatus).toBe("completed");
    expect(view.aiSuggestedOutcome).toBe("Hoàn thành 5 cuộc phỏng vấn khách hàng mục tiêu");
    expect(view.aiSuggestedActions).toEqual([
      "Phỏng vấn 5 khách hàng mục tiêu",
      "Ghi chép pain point vào bảng theo dõi",
    ]);
  });

  it("no-op (applied=false) khi runId không khớp (đã bị request mới hơn ghi đè)", async () => {
    const { project } = await dispatchedProject();

    const result = await applyKickoffSuggestionResultEndpoint({
      id: project.id,
      runId: "run-khong-ton-tai",
      status: "completed",
      outcome: "x",
      actions: ["y"],
      serviceToken: "local-dev-service-token",
    });

    expect(result.applied).toBe(false);
  });

  it("cắt actions còn tối đa 3 và lọc action rỗng", async () => {
    const { ws, project, runId } = await dispatchedProject();

    await applyKickoffSuggestionResultEndpoint({
      id: project.id,
      runId,
      status: "completed",
      outcome: "x",
      actions: ["a", "  ", "b", "c", "d"],
      serviceToken: "local-dev-service-token",
    });

    const view = await getProjectOperatingSetupEndpoint({
      authorization: ws.bearerToken,
      workspaceId: ws.workspaceId,
      id: project.id,
    });
    expect(view.aiSuggestedActions).toEqual(["a", "b", "c"]);
  });

  it("throw unauthenticated khi thiếu serviceToken", async () => {
    const { project, runId } = await dispatchedProject();
    await expect(
      applyKickoffSuggestionResultEndpoint({
        id: project.id,
        runId,
        status: "completed",
      })
    ).rejects.toThrow();
  });

  it("throw unauthenticated khi serviceToken sai", async () => {
    const { project, runId } = await dispatchedProject();
    await expect(
      applyKickoffSuggestionResultEndpoint({
        id: project.id,
        runId,
        status: "completed",
        serviceToken: "wrong-token",
      })
    ).rejects.toThrow();
  });
});
```

*(Ghi chú: test dùng `serviceToken: "local-dev-service-token"` — giá trị mặc định dev của `COSA_SERVICE_TOKEN` khi biến môi trường không được set, xem `process.env.COSA_SERVICE_TOKEN || "local-dev-service-token"` trong handler Step 3 dưới đây. Vitest chạy với `NODE_ENV=test` nên không strict.)*

- [ ] **Step 2: Chạy test, xác nhận FAIL**

```bash
cd services/company && npx vitest run operations/tests/kickoff-suggestion.test.ts -t "applyKickoffSuggestionResultEndpoint"
```

Expected: FAIL — `applyKickoffSuggestionResultEndpoint`/`applyKickoffSuggestionResult` chưa tồn tại.

- [ ] **Step 3: Viết `applyKickoffSuggestionResult`**

Thêm vào cuối `project-operating-setup.service.ts`:

```typescript
export interface ApplyKickoffSuggestionResultInput {
  projectId: string;
  runId: string;
  status: "completed" | "failed";
  outcome?: string | null;
  actions?: string[] | null;
}

export async function applyKickoffSuggestionResult(
  input: ApplyKickoffSuggestionResultInput
): Promise<{ applied: boolean }> {
  const pId = BigInt(input.projectId);

  const [existing] = await db
    .select({
      workspaceId: projectOperatingSetups.workspaceId,
      aiSuggestionRunId: projectOperatingSetups.aiSuggestionRunId,
    })
    .from(projectOperatingSetups)
    .where(eq(projectOperatingSetups.projectId, pId))
    .limit(1);

  if (!existing || existing.aiSuggestionRunId !== input.runId) {
    return { applied: false };
  }

  const cleanActions = (input.actions ?? [])
    .map((a) => (typeof a === "string" ? a.trim() : ""))
    .filter((a) => a.length > 0)
    .slice(0, 3);

  await db
    .update(projectOperatingSetups)
    .set({
      aiSuggestionStatus: input.status,
      aiSuggestedOutcome: input.status === "completed" ? (input.outcome?.trim() || null) : null,
      aiSuggestedActions: input.status === "completed" ? cleanActions : null,
    })
    .where(
      and(
        eq(projectOperatingSetups.projectId, pId),
        eq(projectOperatingSetups.workspaceId, existing.workspaceId)
      )
    );

  return { applied: true };
}
```

- [ ] **Step 4: Chạy test service, xác nhận PASS**

```bash
cd services/company && npx vitest run operations/tests/kickoff-suggestion.test.ts
```

Expected: tất cả PASS.

- [ ] **Step 5: Thêm endpoint callback vào handler**

Trong `services/company/operations/strategy/handlers/project-operating-setup.handler.ts`, sửa khối import (đã sửa ở Task 3) thêm `applyKickoffSuggestionResult`:

```typescript
import {
  getProjectOperatingSetup,
  saveProjectOperatingSetup,
  activateProjectOperatingSetup,
  requestKickoffSuggestion,
  applyKickoffSuggestionResult,
  ProjectOperatingSetupView,
  SaveProjectOperatingSetupRequest,
  ActivateProjectOperatingSetupRequest,
  KickoffSuggestionDispatchResult,
  OperatingSetupStatus,
  EvidenceLevel,
  BasicKickoffStage,
  FirstWeekAction,
} from "../services/project-operating-setup.service";
```

Thêm cuối file (sau `requestKickoffSuggestionEndpoint` đã thêm ở Task 3):

```typescript
export interface ApplyKickoffSuggestionResultParams {
  id: string;
  runId: string;
  status: string;
  outcome?: string;
  actions?: string[];
  serviceToken?: Header<"X-Cosa-Service-Token">;
}

// ── POST /operations/projects/:id/kickoff-suggestion/result (Internal callback from COSA) ──
export const applyKickoffSuggestionResultEndpoint = api(
  { method: "POST", path: "/operations/projects/:id/kickoff-suggestion/result", expose: true },
  async (params: ApplyKickoffSuggestionResultParams): Promise<{ applied: boolean }> => {
    const expectedToken = process.env.COSA_SERVICE_TOKEN || "local-dev-service-token";
    if (!params.serviceToken || params.serviceToken !== expectedToken) {
      throw APIError.unauthenticated("invalid or missing service token");
    }
    if (params.status !== "completed" && params.status !== "failed") {
      throw APIError.invalidArgument("status must be 'completed' or 'failed'");
    }
    return applyKickoffSuggestionResult({
      projectId: params.id,
      runId: params.runId,
      status: params.status,
      outcome: params.outcome,
      actions: params.actions,
    });
  }
);
```

- [ ] **Step 6: Chạy toàn bộ test + typecheck + boundary gate**

```bash
cd services/company && npx vitest run operations/tests/kickoff-suggestion.test.ts
cd services/company && npx tsc --noEmit
cd /Volumes/SSD/javis-saas && make company-boundary-check
make encore-handler-boundary-check
make ts-suppression-check
```

Expected: tất cả PASS.

- [ ] **Step 7: Commit**

```bash
git add services/company/operations/strategy/services/project-operating-setup.service.ts \
        services/company/operations/strategy/handlers/project-operating-setup.handler.ts \
        services/company/operations/tests/kickoff-suggestion.test.ts
git commit -m "feat(company): thêm webhook callback kickoff AI suggestion"
```

---

### Task 5: `apps/cosa` — pure helpers (prompt + schema + parser)

**Files:**
- Create: `apps/cosa/agents/kickoff_suggestion.py`
- Create: `tests/apps/cosa/test_kickoff_suggestion.py`

**Interfaces:**
- Produces: `KickoffSuggestion(outcome: str, actions: list[str])`, `SuggestionSchemaError`, `build_suggestion_prompt(*, target_customer, problem_statement, evidence_level, selected_stage, stage_duration_weeks) -> str`, `parse_suggestion_output(raw: str) -> KickoffSuggestion` — Task 6 import cả 4.

- [ ] **Step 1: Viết test parser (RED)**

Tạo `tests/apps/cosa/test_kickoff_suggestion.py`:

```python
import json

import pytest

from apps.cosa.agents.kickoff_suggestion import (
    SuggestionSchemaError,
    build_suggestion_prompt,
    parse_suggestion_output,
)


def _output(**over):
    data = {
        "outcome": "Hoàn thành 5 cuộc phỏng vấn khách hàng mục tiêu",
        "actions": ["Phỏng vấn 5 khách hàng mục tiêu", "Ghi chép pain point"],
    }
    data.update(over)
    return json.dumps(data)


def test_parses_valid_output():
    result = parse_suggestion_output(_output())
    assert result.outcome == "Hoàn thành 5 cuộc phỏng vấn khách hàng mục tiêu"
    assert result.actions == ["Phỏng vấn 5 khách hàng mục tiêu", "Ghi chép pain point"]


def test_parses_output_with_markdown_fence():
    raw = "```json\n" + _output() + "\n```"
    result = parse_suggestion_output(raw)
    assert len(result.actions) == 2


def test_single_action_is_valid():
    result = parse_suggestion_output(_output(actions=["Chỉ 1 việc"]))
    assert result.actions == ["Chỉ 1 việc"]


def test_empty_output_raises():
    with pytest.raises(SuggestionSchemaError):
        parse_suggestion_output("")


def test_non_json_raises():
    with pytest.raises(SuggestionSchemaError):
        parse_suggestion_output("not json at all")


def test_missing_outcome_raises():
    with pytest.raises(SuggestionSchemaError):
        parse_suggestion_output(json.dumps({"actions": ["a"]}))


def test_empty_outcome_raises():
    with pytest.raises(SuggestionSchemaError):
        parse_suggestion_output(_output(outcome=""))


def test_zero_actions_raises():
    with pytest.raises(SuggestionSchemaError):
        parse_suggestion_output(_output(actions=[]))


def test_four_actions_raises():
    with pytest.raises(SuggestionSchemaError):
        parse_suggestion_output(_output(actions=["a", "b", "c", "d"]))


def test_empty_action_item_raises():
    with pytest.raises(SuggestionSchemaError):
        parse_suggestion_output(_output(actions=["a", ""]))


def test_outcome_over_200_chars_is_truncated_not_rejected():
    long_outcome = "x" * 250
    result = parse_suggestion_output(_output(outcome=long_outcome))
    assert len(result.outcome) == 200


def test_build_prompt_includes_context():
    prompt = build_suggestion_prompt(
        target_customer="Founder B2B SaaS",
        problem_statement="Không biết validate ý tưởng",
        evidence_level="NONE",
        selected_stage="P0_DISCOVERY",
        stage_duration_weeks=2,
    )
    assert "Founder B2B SaaS" in prompt
    assert "Không biết validate ý tưởng" in prompt
    assert "Chưa nói chuyện với khách hàng" in prompt
    assert "2 tuần" in prompt
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

```bash
cd /Volumes/SSD/javis-saas
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/test_kickoff_suggestion.py -q
```

Expected: FAIL — `ModuleNotFoundError: No module named 'apps.cosa.agents.kickoff_suggestion'`.

- [ ] **Step 3: Viết `apps/cosa/agents/kickoff_suggestion.py`**

```python
"""Kickoff wizard Bước 3 — gợi ý outcome + việc tuần đầu (AI suggestion).

Pure helpers: JSON schema cố định, prompt, và strict parser. Không I/O, không
LLM call ở đây — worker (`kickoff_suggestion_run.py`) chạy kernel và feed raw
text vào `parse_suggestion_output`. Mẫu theo `goal_decomposition.py` (WGA).
"""

from __future__ import annotations

import json
from dataclasses import dataclass

__all__ = [
    "KickoffSuggestion",
    "SuggestionSchemaError",
    "build_suggestion_prompt",
    "parse_suggestion_output",
]

_STAGE_LABEL = {
    "P0_DISCOVERY": "Khám phá (P0) — khảo sát pain point ban đầu",
    "P1_PROBLEM_VALIDATION": "Xác thực vấn đề (P1) — đòi hỏi từ 5 cuộc phỏng vấn hoặc prototype",
}

_EVIDENCE_LABEL = {
    "NONE": "Chưa nói chuyện với khách hàng",
    "ONE_TO_FOUR_INTERVIEWS": "Đã có 1-4 cuộc trao đổi",
    "FIVE_PLUS_INTERVIEWS": "Có từ 5 cuộc trao đổi",
    "PROTOTYPE_OR_REVENUE": "Đã có prototype hoặc khách trả tiền",
}


class SuggestionSchemaError(ValueError):
    """Raised khi output của agent không đúng schema bắt buộc."""


@dataclass
class KickoffSuggestion:
    outcome: str
    actions: list[str]


def build_suggestion_prompt(
    *,
    target_customer: str,
    problem_statement: str,
    evidence_level: str,
    selected_stage: str,
    stage_duration_weeks: int,
) -> str:
    stage_label = _STAGE_LABEL.get(selected_stage, selected_stage)
    evidence_label = _EVIDENCE_LABEL.get(evidence_level, evidence_level)

    return (
        "Bạn đang giúp 1 founder chốt kế hoạch TUẦN ĐẦU của vòng khởi nghiệp.\n\n"
        f"ĐỐI TƯỢNG GẶP VẤN ĐỀ: {target_customer.strip()}\n"
        f"VẤN ĐỀ GÂY ẢNH HƯỞNG: {problem_statement.strip()}\n"
        f"MỨC BẰNG CHỨNG HIỆN TẠI: {evidence_label}\n"
        f"VÒNG ĐÃ CHỌN: {stage_label}, kéo dài {stage_duration_weeks} tuần\n\n"
        "Đề xuất:\n"
        "1. outcome: 1 câu mô tả KẾT QUẢ cụ thể, đo được, founder nên đạt được "
        "sau TUẦN ĐẦU tiên của vòng này (không phải cả vòng).\n"
        "2. actions: 1 đến 3 việc CỤ THỂ founder nên làm trong tuần đầu để đạt "
        "outcome đó. Mỗi việc bắt đầu bằng động từ hành động, đủ cụ thể để làm "
        "ngay (vd 'Phỏng vấn 5 khách hàng mục tiêu về...', không nói chung "
        "chung 'Nghiên cứu thị trường').\n\n"
        "Trả về DUY NHẤT 1 JSON object dạng "
        '{"outcome": "...", "actions": ["...", "..."]}, không kèm giải thích, '
        "không dùng markdown fence."
    )


def _strip_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def parse_suggestion_output(raw: str) -> KickoffSuggestion:
    """Parse + validate output. Raises SuggestionSchemaError cho mọi lỗi cấu
    trúc (không bao giờ trả kết quả nửa vời)."""
    if not raw or not raw.strip():
        raise SuggestionSchemaError("empty suggestion output")

    try:
        data = json.loads(_strip_fences(raw))
    except json.JSONDecodeError as exc:
        raise SuggestionSchemaError(f"invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise SuggestionSchemaError("top-level output must be a JSON object")

    outcome = data.get("outcome")
    if not isinstance(outcome, str) or not outcome.strip():
        raise SuggestionSchemaError("'outcome' must be a non-empty string")
    outcome = outcome.strip()
    if len(outcome) > 200:
        outcome = outcome[:200].rstrip()

    actions = data.get("actions")
    if not isinstance(actions, list) or not (1 <= len(actions) <= 3):
        raise SuggestionSchemaError("'actions' must be an array of 1 to 3 items")

    cleaned_actions: list[str] = []
    for i, a in enumerate(actions):
        if not isinstance(a, str) or not a.strip():
            raise SuggestionSchemaError(f"actions[{i}] must be a non-empty string")
        cleaned_actions.append(a.strip())

    return KickoffSuggestion(outcome=outcome, actions=cleaned_actions)
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/test_kickoff_suggestion.py -q
```

Expected: 12 test PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/cosa/agents/kickoff_suggestion.py tests/apps/cosa/test_kickoff_suggestion.py
git commit -m "feat(cosa): pure helper prompt+schema+parser cho kickoff AI suggestion"
```

---

### Task 6: `apps/cosa` — worker execution + callback

**Files:**
- Create: `apps/cosa/worker/kickoff_suggestion_run.py`
- Create: `tests/apps/cosa/worker/test_kickoff_suggestion_run.py`

**Interfaces:**
- Consumes: `build_suggestion_prompt`, `parse_suggestion_output`, `SuggestionSchemaError` (Task 5); `prepare_run`, `run_kernel`, `RunCoreError` (`apps/cosa/worker/run_core.py`, đã có); `COSA_OPERATIONS_AGENT_SPEC` (`apps/cosa/agents/specs.py`, đã có); `require_internal_url`, `require_service_token` (`apps/cosa/config/service_identity.py`, đã có).
- Produces: `execute_kickoff_suggestion_task(plane, stream_mgr, payload) -> None`, `callback_kickoff_result(project_id, run_id, status, outcome=None, actions=None) -> None` — Task 7's dispatch wiring trong `worker/main.py` import `execute_kickoff_suggestion_task`.

- [ ] **Step 1: Viết test worker (RED)**

Tạo `tests/apps/cosa/worker/test_kickoff_suggestion_run.py` (mẫu chính xác theo `tests/apps/cosa/wga/test_wga_run.py`):

```python
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from agent.contracts.run import RunStatus
from apps.cosa.worker import kickoff_suggestion_run


def _run_result(status, final_output="", errors=None):
    return SimpleNamespace(
        status=status, final_output=final_output, errors=errors or [], interruptions_waits=[]
    )


def _plane(*, kernel_result):
    kernel = AsyncMock()
    kernel.run.return_value = kernel_result
    resolver = AsyncMock()
    resolver.resolve_for_run.return_value = {"_company_delegation_token": "jwt-x"}
    return SimpleNamespace(
        kernel=kernel,
        compliance_resolver=resolver,
        spec_registry=SimpleNamespace(),
    )


@pytest.fixture(autouse=True)
def _patch_resolve_spec(monkeypatch):
    async def _fake_resolve_spec(plane, *, run_id, local_spec):
        return SimpleNamespace(
            to_pinned_identity=lambda: "cosa.agents.operations@1.2.0#h",
            spec_id="cosa.agents.operations",
        )

    monkeypatch.setattr("apps.cosa.worker.run_core.resolve_spec", _fake_resolve_spec)
    monkeypatch.setenv("COSA_COMPANY_DELEGATION_SECRET", "x" * 40)


_VALID_OUTPUT = json.dumps(
    {
        "outcome": "Hoàn thành 5 cuộc phỏng vấn khách hàng mục tiêu",
        "actions": ["Phỏng vấn 5 khách hàng mục tiêu", "Ghi chép pain point"],
    }
)

_PAYLOAD = {
    "run_id": "kickoff_sugg_1",
    "workspace_id": "ws1",
    "project_id": "proj1",
    "target_customer": "Founder B2B SaaS",
    "problem_statement": "Không biết validate ý tưởng",
    "evidence_level": "NONE",
    "selected_stage": "P0_DISCOVERY",
    "stage_duration_weeks": 2,
}


@pytest.mark.asyncio
async def test_execute_task_callbacks_completed_on_valid_output():
    plane = _plane(kernel_result=_run_result(RunStatus.COMPLETED, {"response": _VALID_OUTPUT}))

    with patch.object(kickoff_suggestion_run, "callback_kickoff_result", new=AsyncMock()) as cb:
        await kickoff_suggestion_run.execute_kickoff_suggestion_task(plane, None, _PAYLOAD)

    cb.assert_awaited_once_with(
        "proj1",
        "kickoff_sugg_1",
        "completed",
        outcome="Hoàn thành 5 cuộc phỏng vấn khách hàng mục tiêu",
        actions=["Phỏng vấn 5 khách hàng mục tiêu", "Ghi chép pain point"],
    )
    # Không capability nào được gọi — plane không có capability_registry trong
    # fixture này, nên bất kỳ truy cập nào vào nó sẽ tự raise AttributeError
    # và làm test fail nếu code lỡ gọi capability.


@pytest.mark.asyncio
async def test_execute_task_callbacks_failed_on_invalid_schema():
    plane = _plane(kernel_result=_run_result(RunStatus.COMPLETED, {"response": "not json"}))

    with patch.object(kickoff_suggestion_run, "callback_kickoff_result", new=AsyncMock()) as cb:
        await kickoff_suggestion_run.execute_kickoff_suggestion_task(plane, None, _PAYLOAD)

    cb.assert_awaited_once_with("proj1", "kickoff_sugg_1", "failed")


@pytest.mark.asyncio
async def test_execute_task_callbacks_failed_on_kernel_non_completed():
    plane = _plane(kernel_result=_run_result(RunStatus.FAILED, errors=["boom"]))

    with patch.object(kickoff_suggestion_run, "callback_kickoff_result", new=AsyncMock()) as cb:
        await kickoff_suggestion_run.execute_kickoff_suggestion_task(plane, None, _PAYLOAD)

    cb.assert_awaited_once_with("proj1", "kickoff_sugg_1", "failed")


@pytest.mark.asyncio
async def test_callback_kickoff_result_posts_to_company(monkeypatch):
    monkeypatch.setenv("COMPANY_SERVICE_URL", "http://127.0.0.1:4000")
    monkeypatch.setenv("COSA_SERVICE_TOKEN", "test-token-" + "x" * 30)

    captured = {}

    class _FakeResponse:
        status_code = 200

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json=None, headers=None):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return _FakeResponse()

    with patch("apps.cosa.worker.kickoff_suggestion_run.httpx.AsyncClient", _FakeAsyncClient):
        await kickoff_suggestion_run.callback_kickoff_result(
            "proj1", "run1", "completed", outcome="x", actions=["y"]
        )

    assert captured["url"] == "http://127.0.0.1:4000/operations/projects/proj1/kickoff-suggestion/result"
    assert captured["json"] == {"runId": "run1", "status": "completed", "outcome": "x", "actions": ["y"]}
    assert captured["headers"]["X-Cosa-Service-Token"] == "test-token-" + "x" * 30
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/worker/test_kickoff_suggestion_run.py -q
```

Expected: FAIL — `ModuleNotFoundError: No module named 'apps.cosa.worker.kickoff_suggestion_run'`.

- [ ] **Step 3: Viết `apps/cosa/worker/kickoff_suggestion_run.py`**

```python
"""Kickoff wizard Bước 3 — headless task run của AI suggestion (outcome +
1-3 việc tuần đầu). KHÔNG gọi capability nào (thuần suy luận từ context
Founder đã nhập ở Bước 1/2, giống execute_goal_decomposition_task của WGA khi
không gọi capability). Kết quả callback thẳng về services/company qua
service token (giống pattern copilot_run.py), KHÔNG qua mint_company_delegation
— route callback không phải capability-scoped, chỉ webhook 1 chiều.

Khác WGA goal_decomposition (im lặng return khi lỗi): task này LUÔN callback
company (completed/failed) vì company đang poll `ai_suggestion_status` để
biết khi nào dừng — im lặng return sẽ khiến FE poll treo tới hết timeout.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from agent.contracts.run import RunStatus

from apps.cosa.agents.kickoff_suggestion import (
    SuggestionSchemaError,
    build_suggestion_prompt,
    parse_suggestion_output,
)
from apps.cosa.agents.specs import COSA_OPERATIONS_AGENT_SPEC
from apps.cosa.composition.agent_plane import CosaAgentPlane
from apps.cosa.config.service_identity import require_internal_url, require_service_token
from apps.cosa.worker.run_core import RunCoreError, prepare_run, run_kernel

logger = logging.getLogger(__name__)

__all__ = ["callback_kickoff_result", "execute_kickoff_suggestion_task"]


def _extract_text(run_result: Any) -> str:
    fo = getattr(run_result, "final_output", None)
    if isinstance(fo, dict):
        return str(fo.get("response", fo))
    return str(fo or "")


async def callback_kickoff_result(
    project_id: str,
    run_id: str,
    status: str,
    outcome: str | None = None,
    actions: list[str] | None = None,
) -> None:
    company_base_url = require_internal_url(
        "COMPANY_SERVICE_URL", purpose="kickoff suggestion callback", default_dev="http://127.0.0.1:4000"
    )
    service_token = require_service_token("COSA_SERVICE_TOKEN", purpose="kickoff suggestion callback")

    url = f"{company_base_url}/operations/projects/{project_id}/kickoff-suggestion/result"
    headers = {
        "Content-Type": "application/json",
        "X-Cosa-Service-Token": service_token,
    }
    body: dict[str, Any] = {"runId": run_id, "status": status}
    if outcome is not None:
        body["outcome"] = outcome
    if actions is not None:
        body["actions"] = actions

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=body, headers=headers)
            if resp.status_code >= 400:
                logger.warning(
                    "Failed to callback company kickoff-suggestion result for run %s: status %s",
                    run_id,
                    resp.status_code,
                )
    except Exception as e:
        logger.warning("Exception during kickoff-suggestion callback for run %s: %s", run_id, e)


async def execute_kickoff_suggestion_task(
    plane: CosaAgentPlane,
    stream_mgr: Any,
    payload: dict[str, Any],
) -> None:
    run_id = payload["run_id"]
    workspace_id = payload["workspace_id"]
    project_id = payload["project_id"]

    prompt = build_suggestion_prompt(
        target_customer=payload.get("target_customer", ""),
        problem_statement=payload.get("problem_statement", ""),
        evidence_level=payload.get("evidence_level", ""),
        selected_stage=payload.get("selected_stage", ""),
        stage_duration_weeks=int(payload.get("stage_duration_weeks") or 2),
    )

    try:
        prep = await prepare_run(
            plane,
            run_id=run_id,
            local_spec=COSA_OPERATIONS_AGENT_SPEC,
            prompt=prompt,
            principal=f"system:kickoff_suggestion:{workspace_id}",
            workspace_id=workspace_id,
            conversation_id=f"kickoff_suggestion_{run_id}",
            policy_snapshot=None,
        )
    except RunCoreError as exc:
        logger.error("kickoff_suggestion prep failed run=%s reason=%s", run_id, exc.reason_code)
        await callback_kickoff_result(project_id, run_id, "failed")
        return

    run_result, _ = await run_kernel(plane, prep, workspace_id=workspace_id, run_id=run_id)
    if run_result.status != RunStatus.COMPLETED:
        logger.error("kickoff_suggestion kernel run=%s status=%s", run_id, run_result.status)
        await callback_kickoff_result(project_id, run_id, "failed")
        return

    try:
        suggestion = parse_suggestion_output(_extract_text(run_result))
    except SuggestionSchemaError as exc:
        logger.error("kickoff_suggestion schema_invalid run=%s: %s", run_id, exc)
        await callback_kickoff_result(project_id, run_id, "failed")
        return

    await callback_kickoff_result(
        project_id, run_id, "completed", outcome=suggestion.outcome, actions=suggestion.actions
    )
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/worker/test_kickoff_suggestion_run.py -q
```

Expected: 4 test PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/cosa/worker/kickoff_suggestion_run.py tests/apps/cosa/worker/test_kickoff_suggestion_run.py
git commit -m "feat(cosa): worker execution kickoff AI suggestion (không capability)"
```

---

### Task 7: `apps/cosa` — API route + wiring dispatch

**Files:**
- Create: `apps/cosa/api/kickoff_suggestion_routes.py`
- Create: `tests/apps/cosa/test_kickoff_suggestion_route.py`
- Modify: `apps/cosa/api/app.py:14` (import), `:207` (register)
- Modify: `apps/cosa/worker/main.py:132-263` (thêm dispatch helper + branch)

**Interfaces:**
- Consumes: `execute_kickoff_suggestion_task` (Task 6), `get_cosa_event_stream_manager` (đã có, dùng trong `main.py`).
- Produces: route `POST /agent/kickoff/first-week-suggestion` — Company Task 3's `kickoff-suggestion-cosa-client.ts` gọi endpoint này.

- [ ] **Step 1: Viết test route (RED)**

Tạo `tests/apps/cosa/test_kickoff_suggestion_route.py` (mẫu chính xác `tests/apps/cosa/test_copilot_route.py`):

```python
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import httpx
import pytest
from fastapi import FastAPI
from apps.cosa.api.kickoff_suggestion_routes import create_kickoff_suggestion_router


@pytest.fixture
def test_app():
    app = FastAPI()
    router = create_kickoff_suggestion_router()
    app.include_router(router)

    mock_plane = MagicMock()
    mock_scheduler = MagicMock()
    mock_scheduler.schedule = AsyncMock()
    mock_plane.scheduler = mock_scheduler
    app.state.plane = mock_plane
    return app


_VALID_BODY = {
    "workspace_id": "ws_123",
    "project_id": "proj_456",
    "run_id": "run-abc-123",
    "target_customer": "Founder B2B SaaS",
    "problem_statement": "Không biết validate ý tưởng",
    "evidence_level": "NONE",
    "selected_stage": "P0_DISCOVERY",
    "stage_duration_weeks": 2,
}


@pytest.mark.asyncio
async def test_dispatch_unauthorized_missing_token(test_app):
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/agent/kickoff/first-week-suggestion", json=_VALID_BODY)
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dispatch_authorized_schedules_task(test_app, monkeypatch):
    monkeypatch.setenv("COSA_SERVICE_TOKEN", "secret-test-token")
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/agent/kickoff/first-week-suggestion",
            headers={"X-Cosa-Service-Token": "secret-test-token"},
            json=_VALID_BODY,
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["run_id"] == "run-abc-123"

        scheduler = test_app.state.plane.scheduler
        assert scheduler.schedule.await_count == 1
        call_args = scheduler.schedule.call_args.kwargs
        assert call_args["target_spec_id"] == "cosa.agents.operations"
        payload = call_args["input_payload"]
        assert payload["task_type"] == "kickoff_suggestion"
        assert payload["run_id"] == "run-abc-123"
        assert payload["project_id"] == "proj_456"
        assert payload["target_customer"] == "Founder B2B SaaS"
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/test_kickoff_suggestion_route.py -q
```

Expected: FAIL — module chưa tồn tại.

- [ ] **Step 3: Viết `apps/cosa/api/kickoff_suggestion_routes.py`**

```python
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel

from apps.cosa.config.service_identity import require_service_token

__all__ = ["create_kickoff_suggestion_router"]


class KickoffSuggestionRequest(BaseModel):
    workspace_id: str
    project_id: str
    run_id: str
    target_customer: str
    problem_statement: str
    evidence_level: str
    selected_stage: str
    stage_duration_weeks: int


def create_kickoff_suggestion_router() -> APIRouter:
    router = APIRouter(prefix="/agent/kickoff", tags=["kickoff-suggestion"])

    @router.post("/first-week-suggestion", status_code=status.HTTP_202_ACCEPTED)
    async def dispatch_kickoff_suggestion(
        body: KickoffSuggestionRequest,
        request: Request,
        x_cosa_service_token: str | None = Header(default=None),
    ) -> dict[str, str]:
        expected_token = require_service_token(
            "COSA_SERVICE_TOKEN", purpose="kickoff suggestion route auth"
        )
        if not x_cosa_service_token or x_cosa_service_token != expected_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid or missing service token",
            )

        plane = getattr(request.app.state, "plane", None)
        if plane is None or getattr(plane, "scheduler", None) is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="COSA plane scheduler not available",
            )

        await plane.scheduler.schedule(
            target_spec_id="cosa.agents.operations",
            input_payload={
                "task_type": "kickoff_suggestion",
                "run_id": body.run_id,
                "workspace_id": body.workspace_id,
                "project_id": body.project_id,
                "target_customer": body.target_customer,
                "problem_statement": body.problem_statement,
                "evidence_level": body.evidence_level,
                "selected_stage": body.selected_stage,
                "stage_duration_weeks": body.stage_duration_weeks,
            },
        )

        return {"run_id": body.run_id}

    return router
```

- [ ] **Step 4: Chạy test route, xác nhận PASS**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/test_kickoff_suggestion_route.py -q
```

Expected: 2 test PASS.

- [ ] **Step 5: Đăng ký router trong `app.py`**

Trong `apps/cosa/api/app.py`, thêm import cạnh dòng 14:

```python
from apps.cosa.api.copilot_routes import create_copilot_router
from apps.cosa.api.kickoff_suggestion_routes import create_kickoff_suggestion_router
```

Thêm đăng ký cạnh dòng 207:

```python
    app.include_router(create_copilot_router())
    app.include_router(create_kickoff_suggestion_router())
    app.include_router(create_autopilot_metrics_router())
```

- [ ] **Step 6: Thêm dispatch helper + branch trong `worker/main.py`**

Thêm hàm mới ngay sau `_dispatch_wga_task` (sau dòng 172, trước `async def _run_with_heartbeats`):

```python
async def _dispatch_kickoff_suggestion_task(plane: CosaAgentPlane, task, payload: dict) -> None:
    """Dispatch kickoff wizard Bước 3 AI-suggestion task — task claim fencing
    only (no RunLeaseManager), giống `_dispatch_wga_task`. Handler tự callback
    company (completed/failed) trong mọi nhánh, không rơi vào im lặng."""
    try:
        from apps.cosa.worker.kickoff_suggestion_run import execute_kickoff_suggestion_task

        stream_mgr = get_cosa_event_stream_manager()

        async def _execute_handler():
            await execute_kickoff_suggestion_task(plane, stream_mgr, payload)

        await _heartbeat_task_claim_only(plane, task.task_id, task.claim_token, _execute_handler())

        ok = await plane.scheduler.complete_task(
            task.task_id, worker_id=WORKER_ID, claim_token=task.claim_token, success=True
        )
        if not ok:
            logger.warning(
                "worker=%s task=%s (kickoff_suggestion) completed but fencing rejected",
                WORKER_ID,
                task.task_id,
            )
    except Exception as exc:
        logger.exception("task=%s (kickoff_suggestion) failed during execution", task.task_id)
        await plane.scheduler.complete_task(
            task.task_id,
            worker_id=WORKER_ID,
            claim_token=task.claim_token,
            success=False,
            error=str(exc),
        )
```

Thêm branch trong `dispatch_one_task`, ngay sau nhánh WGA (sau dòng 263 `return`, trước `if not run_id:` ở dòng 265):

```python
            # Branch: kickoff wizard Bước 3 AI-suggestion — task claim fencing
            # only, giống WGA headless task.
            if task_type == "kickoff_suggestion":
                await _dispatch_kickoff_suggestion_task(plane, task, payload)
                return

```

- [ ] **Step 7: Viết test dispatch wiring**

Tạo test bổ sung trong `tests/apps/cosa/worker/test_kickoff_suggestion_run.py`... KHÔNG — dispatch wiring thuộc `worker/main.py`, viết file test riêng `tests/apps/cosa/worker/test_main_dispatch_kickoff_suggestion.py`:

```python
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from apps.cosa.worker import main as worker_main


@pytest.mark.asyncio
async def test_dispatch_one_task_routes_kickoff_suggestion(monkeypatch):
    task = SimpleNamespace(task_id="t1", claim_token="claim1", input_payload={
        "task_type": "kickoff_suggestion",
        "run_id": "run1",
        "workspace_id": "ws1",
        "project_id": "p1",
    })
    scheduler = AsyncMock()
    scheduler.complete_task.return_value = True
    plane = SimpleNamespace(scheduler=scheduler)

    with patch(
        "apps.cosa.worker.kickoff_suggestion_run.execute_kickoff_suggestion_task", new=AsyncMock()
    ) as exec_mock:
        await worker_main.dispatch_one_task(plane, task)

    exec_mock.assert_awaited_once()
    scheduler.complete_task.assert_awaited_once()
    assert scheduler.complete_task.call_args.kwargs["success"] is True
```

- [ ] **Step 8: Chạy test dispatch, xác nhận PASS**

```bash
source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/worker/test_main_dispatch_kickoff_suggestion.py -q
```

Expected: 1 test PASS. Nếu FAIL vì `dispatch_one_task` cần thêm field trong `payload`/`task` (vd `log_context`, `trace_span` cần workspace_id — đã có trong payload test), điều chỉnh `SimpleNamespace` cho khớp field thực tế `dispatch_one_task` đọc (đọc lại `apps/cosa/worker/main.py:223-263` nếu lỗi AttributeError để bổ sung đúng field).

- [ ] **Step 9: Chạy toàn bộ `apps-cosa-test` để đảm bảo không phá test khác**

```bash
make apps-cosa-test
```

Expected: PASS, coverage vẫn ≥78%.

- [ ] **Step 10: Commit**

```bash
git add apps/cosa/api/kickoff_suggestion_routes.py apps/cosa/api/app.py apps/cosa/worker/main.py \
        tests/apps/cosa/test_kickoff_suggestion_route.py \
        tests/apps/cosa/worker/test_main_dispatch_kickoff_suggestion.py
git commit -m "feat(cosa): route + dispatch wiring cho kickoff AI suggestion"
```

---

### Task 8: Frontend — model + service

**Files:**
- Modify: `frontend/lib/data/models/project_operating_setup_model.dart`
- Modify: `frontend/lib/modules/strategy/services/project_operating_setup_service.dart`
- Modify: `frontend/test/data/models/project_operating_setup_model_test.dart`
- Modify: `frontend/test/modules/strategy/services/project_operating_setup_service_test.dart`

**Interfaces:**
- Produces: `ProjectOperatingSetup.aiSuggestionStatus: String?`, `.aiSuggestedOutcome: String?`, `.aiSuggestedActions: List<String>?`; `ProjectOperatingSetupService.requestKickoffSuggestion(String projectId): Future<void>` — Task 9 (controller) dùng cả 4.

- [ ] **Step 1: Viết test model (RED)**

Thêm vào `frontend/test/data/models/project_operating_setup_model_test.dart` (đọc file hiện có trước để dùng đúng style `group`/`test` đã có):

```dart
test('fromJson đọc đúng field aiSuggestion', () {
  final setup = ProjectOperatingSetup.fromJson({
    'projectId': 'p1',
    'workspaceId': 'w1',
    'status': 'IN_PROGRESS',
    'aiSuggestionStatus': 'completed',
    'aiSuggestedOutcome': 'Hoàn thành 5 cuộc phỏng vấn',
    'aiSuggestedActions': ['Phỏng vấn 5 khách hàng', 'Ghi chép pain point'],
  });

  expect(setup.aiSuggestionStatus, 'completed');
  expect(setup.aiSuggestedOutcome, 'Hoàn thành 5 cuộc phỏng vấn');
  expect(setup.aiSuggestedActions, ['Phỏng vấn 5 khách hàng', 'Ghi chép pain point']);
});

test('fromJson trả null cho aiSuggestion khi thiếu field', () {
  final setup = ProjectOperatingSetup.fromJson({
    'projectId': 'p1',
    'workspaceId': 'w1',
    'status': 'NOT_STARTED',
  });

  expect(setup.aiSuggestionStatus, isNull);
  expect(setup.aiSuggestedOutcome, isNull);
  expect(setup.aiSuggestedActions, isNull);
});
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

```bash
cd frontend && flutter test test/data/models/project_operating_setup_model_test.dart
```

Expected: FAIL — `The getter 'aiSuggestionStatus' isn't defined`.

- [ ] **Step 3: Sửa `ProjectOperatingSetup` model**

Trong `project_operating_setup_model.dart`, sửa constructor (dòng 144-162):

```dart
class ProjectOperatingSetup {
  const ProjectOperatingSetup({
    required this.projectId,
    required this.workspaceId,
    required this.status,
    this.targetCustomer,
    this.problemStatement,
    this.evidenceLevel,
    this.recommendedStage,
    this.selectedStage,
    this.stageDurationWeeks,
    this.stageTargetDate,
    this.roundStartDate,
    this.weeklyReviewWeekday,
    this.weeklyReviewTime,
    this.firstWeekOutcome,
    this.firstWeekActions = const [],
    this.aiSuggestionStatus,
    this.aiSuggestedOutcome,
    this.aiSuggestedActions,
    this.updatedAt,
  });

  final String projectId;
  final String workspaceId;
  final OperatingSetupStatus status;
  final String? targetCustomer;
  final String? problemStatement;
  final KickoffEvidenceLevel? evidenceLevel;
  final ProjectLifecycleStage? recommendedStage;
  final ProjectLifecycleStage? selectedStage;
  final int? stageDurationWeeks;
  final DateTime? stageTargetDate;
  final DateTime? roundStartDate;
  final int? weeklyReviewWeekday;
  final String? weeklyReviewTime;
  final String? firstWeekOutcome;
  final List<FirstWeekActionDraft> firstWeekActions;
  final String? aiSuggestionStatus;
  final String? aiSuggestedOutcome;
  final List<String>? aiSuggestedActions;
  final DateTime? updatedAt;
```

Sửa `fromJson` (thêm trước `updatedAt:` ở dòng ~233):

```dart
      aiSuggestionStatus: json['aiSuggestionStatus'] as String?,
      aiSuggestedOutcome: json['aiSuggestedOutcome'] as String?,
      aiSuggestedActions: (json['aiSuggestedActions'] as List?)
          ?.map((e) => e.toString())
          .toList(),
      updatedAt: json['updatedAt'] != null
          ? DateTime.tryParse(json['updatedAt'].toString())
          : null,
```

Sửa `copyWith` (dòng 242-261) để không làm rơi 3 field mới khi optimistic-update `firstWeekActions`:

```dart
  ProjectOperatingSetup copyWith({List<FirstWeekActionDraft>? firstWeekActions}) {
    return ProjectOperatingSetup(
      projectId: projectId,
      workspaceId: workspaceId,
      status: status,
      targetCustomer: targetCustomer,
      problemStatement: problemStatement,
      evidenceLevel: evidenceLevel,
      recommendedStage: recommendedStage,
      selectedStage: selectedStage,
      stageDurationWeeks: stageDurationWeeks,
      stageTargetDate: stageTargetDate,
      roundStartDate: roundStartDate,
      weeklyReviewWeekday: weeklyReviewWeekday,
      weeklyReviewTime: weeklyReviewTime,
      firstWeekOutcome: firstWeekOutcome,
      firstWeekActions: firstWeekActions ?? this.firstWeekActions,
      aiSuggestionStatus: aiSuggestionStatus,
      aiSuggestedOutcome: aiSuggestedOutcome,
      aiSuggestedActions: aiSuggestedActions,
      updatedAt: updatedAt,
    );
  }
```

- [ ] **Step 4: Chạy test model, xác nhận PASS**

```bash
cd frontend && flutter test test/data/models/project_operating_setup_model_test.dart
```

Expected: PASS.

- [ ] **Step 5: Viết test service (RED)**

Thêm vào `frontend/test/modules/strategy/services/project_operating_setup_service_test.dart` (file dùng `ApiClient.client = MockClient((request) async {...})` — override field tĩnh `ApiClient.client` bằng `MockClient` từ package `http/testing.dart`, xem `test('get loads operating setup model from API')` ở dòng 60-76 làm mẫu):

```dart
test('requestKickoffSuggestion posts to correct endpoint', () async {
  ApiClient.client = MockClient((request) async {
    expect(request.method, 'POST');
    expect(
      request.url.path,
      '/operations/projects/p-1/kickoff-suggestion',
    );
    return http.Response(
      jsonEncode({'runId': 'run-1', 'status': 'dispatched'}),
      202,
    );
  });

  await ProjectOperatingSetupService().requestKickoffSuggestion('p-1');
});

test('requestKickoffSuggestion throws StrategyApiException on non-2xx', () async {
  ApiClient.client = MockClient((request) async {
    return http.Response(
      jsonEncode({'detail': 'Hoàn thành Bước 1 trước khi tạo gợi ý AI'}),
      412,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );
  });

  expect(
    () => ProjectOperatingSetupService().requestKickoffSuggestion('p-1'),
    throwsA(isA<StrategyApiException>()),
  );
});
```

- [ ] **Step 6: Chạy test, xác nhận FAIL**

```bash
cd frontend && flutter test test/modules/strategy/services/project_operating_setup_service_test.dart
```

Expected: FAIL — `The method 'requestKickoffSuggestion' isn't defined`.

- [ ] **Step 7: Thêm method vào service**

Thêm vào cuối class `ProjectOperatingSetupService`:

```dart
  Future<void> requestKickoffSuggestion(String projectId) async {
    final response = await ApiClient.post(
      '/operations/projects/$projectId/kickoff-suggestion',
    );
    decode(response); // throws StrategyApiException nếu không phải 2xx
  }
```

- [ ] **Step 8: Chạy test, xác nhận PASS**

```bash
cd frontend && flutter test test/modules/strategy/services/project_operating_setup_service_test.dart
cd frontend && flutter test test/data/models/project_operating_setup_model_test.dart
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add frontend/lib/data/models/project_operating_setup_model.dart \
        frontend/lib/modules/strategy/services/project_operating_setup_service.dart \
        frontend/test/data/models/project_operating_setup_model_test.dart \
        frontend/test/modules/strategy/services/project_operating_setup_service_test.dart
git commit -m "feat(frontend): model+service cho kickoff AI suggestion"
```

---

### Task 9: Frontend — controller (auto-trigger + polling)

**Files:**
- Modify: `frontend/lib/modules/strategy/controllers/project_kickoff_controller.dart`
- Modify: `frontend/test/modules/strategy/controllers/project_kickoff_controller_test.dart`

**Interfaces:**
- Consumes: `ProjectOperatingSetupService.requestKickoffSuggestion` (Task 8), `ProjectOperatingSetup.aiSuggestionStatus/aiSuggestedOutcome/aiSuggestedActions` (Task 8).
- Produces: `ProjectKickoffController.aiSuggestionLoading: RxBool`, `.requestKickoffSuggestion({required bool overwrite}): Future<void>` — Task 10 (view) gọi cả 2.

- [ ] **Step 1: Viết test controller (RED)**

Thêm vào `frontend/test/modules/strategy/controllers/project_kickoff_controller_test.dart` — mở rộng `FakeProjectOperatingSetupService` (đã có trong file, xem đầu file) với 1 field `getOverride` mà `get()` trả về nếu set (không dùng `copyWith` vì nó không nhận tham số `aiSuggestionStatus`/`aiSuggestedOutcome`/`aiSuggestedActions` — Task 8 chỉ thêm chúng vào constructor, dựng `ProjectOperatingSetup(...)` mới đầy đủ field thay vì gọi `copyWith` khi cần override trong test):

```dart
class FakeProjectOperatingSetupService extends ProjectOperatingSetupService {
  // (các field/method hiện có giữ nguyên)

  int requestKickoffSuggestionCallCount = 0;
  bool throwOnRequestKickoffSuggestion = false;
  ProjectOperatingSetup? getOverride;

  @override
  Future<void> requestKickoffSuggestion(String projectId) async {
    requestKickoffSuggestionCallCount++;
    if (throwOnRequestKickoffSuggestion) {
      throw StrategyApiException(500, 'cosa down');
    }
  }

  @override
  Future<ProjectOperatingSetup> get(String projectId) async {
    return getOverride ?? _setup;
  }
}
```

Test cases:

```dart
group('requestKickoffSuggestion', () {
  test('không gọi service khi overwrite=false và outcome đã có nội dung', () async {
    final service = FakeProjectOperatingSetupService();
    final controller = ProjectKickoffController(service: service);
    await controller.load('p1');
    controller.firstWeekOutcomeCtrl.text = 'Đã tự gõ rồi';

    await controller.requestKickoffSuggestion(overwrite: false);

    expect(service.requestKickoffSuggestionCallCount, 0);
  });

  test('gọi service khi overwrite=true dù outcome đã có nội dung', () async {
    final service = FakeProjectOperatingSetupService();
    final controller = ProjectKickoffController(service: service);
    await controller.load('p1');
    controller.firstWeekOutcomeCtrl.text = 'Đã tự gõ rồi';
    service.getOverride = const ProjectOperatingSetup(
      projectId: 'p1',
      workspaceId: 'w1',
      status: OperatingSetupStatus.inProgress,
      aiSuggestionStatus: 'completed',
      aiSuggestedOutcome: 'Gợi ý AI mới',
      aiSuggestedActions: ['Việc AI gợi ý'],
    );

    await controller.requestKickoffSuggestion(overwrite: true);
    await Future.delayed(const Duration(milliseconds: 2100));

    expect(service.requestKickoffSuggestionCallCount, 1);
    expect(controller.firstWeekOutcomeCtrl.text, 'Gợi ý AI mới');
    expect(controller.firstWeekActions.map((a) => a.title).toList(), ['Việc AI gợi ý']);
    expect(controller.aiSuggestionLoading.value, false);
  });

  test('dừng loading ngay khi service throw (không poll)', () async {
    final service = FakeProjectOperatingSetupService()
      ..throwOnRequestKickoffSuggestion = true;
    final controller = ProjectKickoffController(service: service);
    await controller.load('p1');

    await controller.requestKickoffSuggestion(overwrite: true);

    expect(controller.aiSuggestionLoading.value, false);
  });

  test('dừng poll và tắt loading khi status=failed', () async {
    final service = FakeProjectOperatingSetupService();
    final controller = ProjectKickoffController(service: service);
    await controller.load('p1');
    service.getOverride = const ProjectOperatingSetup(
      projectId: 'p1',
      workspaceId: 'w1',
      status: OperatingSetupStatus.inProgress,
      aiSuggestionStatus: 'failed',
    );

    await controller.requestKickoffSuggestion(overwrite: true);
    await Future.delayed(const Duration(milliseconds: 2100));

    expect(controller.aiSuggestionLoading.value, false);
    expect(controller.firstWeekOutcomeCtrl.text, isEmpty);
  });
}, timeout: const Timeout(Duration(seconds: 10)));
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

```bash
cd frontend && flutter test test/modules/strategy/controllers/project_kickoff_controller_test.dart
```

Expected: FAIL — `aiSuggestionLoading`/`requestKickoffSuggestion` chưa tồn tại trên controller.

- [ ] **Step 3: Thêm polling + trigger vào controller**

Thêm import ở đầu file:

```dart
import 'dart:async';
```

Thêm field mới (sau dòng 33 `final newActionCtrl = TextEditingController();`):

```dart
  final aiSuggestionLoading = false.obs;
  Timer? _suggestionPollTimer;
  int _suggestionPollElapsedMs = 0;
  static const _suggestionPollIntervalMs = 2000;
  static const _suggestionPollTimeoutMs = 30000;
```

Sửa `onClose` (dòng 35-42) — huỷ timer trước khi dispose controller:

```dart
  @override
  void onClose() {
    _suggestionPollTimer?.cancel();
    targetCustomerCtrl.dispose();
    problemStatementCtrl.dispose();
    firstWeekOutcomeCtrl.dispose();
    newActionCtrl.dispose();
    super.onClose();
  }
```

Thêm 2 method mới (sau `updateWeeklyReviewCadence`, trước `bool get isP1Allowed`):

```dart
  // Bước 2 "Tiếp tục" gọi với overwrite:false (không đụng nội dung Founder đã
  // có sẵn); icon "✨" ở Bước 3 gọi với overwrite:true (luôn ghi đè — đã chốt
  // ở spec §2). Không await ở FE — gọi fire-and-forget, wizard chuyển bước
  // ngay, loading hiện cạnh tiêu đề Bước 3 trong lúc chờ.
  Future<void> requestKickoffSuggestion({required bool overwrite}) async {
    if (projectId.value.isEmpty || aiSuggestionLoading.value) return;
    if (!overwrite &&
        (firstWeekOutcomeCtrl.text.trim().isNotEmpty || firstWeekActions.isNotEmpty)) {
      return;
    }
    aiSuggestionLoading.value = true;
    _suggestionPollElapsedMs = 0;
    try {
      await _service.requestKickoffSuggestion(projectId.value);
    } catch (_) {
      aiSuggestionLoading.value = false;
      return;
    }
    _pollSuggestion();
  }

  void _pollSuggestion() {
    _suggestionPollTimer?.cancel();
    _suggestionPollTimer = Timer.periodic(
      const Duration(milliseconds: _suggestionPollIntervalMs),
      (timer) async {
        _suggestionPollElapsedMs += _suggestionPollIntervalMs;
        if (_suggestionPollElapsedMs >= _suggestionPollTimeoutMs) {
          timer.cancel();
          aiSuggestionLoading.value = false;
          return;
        }
        final ProjectOperatingSetup latest;
        try {
          latest = await _service.get(projectId.value);
        } catch (_) {
          return; // lỗi mạng tạm thời — thử lại ở tick sau, không dừng poll
        }
        if (latest.aiSuggestionStatus == 'completed') {
          timer.cancel();
          aiSuggestionLoading.value = false;
          firstWeekOutcomeCtrl.text = latest.aiSuggestedOutcome ?? '';
          firstWeekActions.assignAll(
            (latest.aiSuggestedActions ?? [])
                .map((t) => FirstWeekActionDraft(title: t)),
          );
          await saveCurrentStep();
        } else if (latest.aiSuggestionStatus == 'failed') {
          timer.cancel();
          aiSuggestionLoading.value = false;
        }
      },
    );
  }
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

```bash
cd frontend && flutter test test/modules/strategy/controllers/project_kickoff_controller_test.dart
```

Expected: tất cả PASS (test có `await Future.delayed(2100ms)` để chờ đúng 1 tick poll — timeout group đã set 10s để đủ dư).

- [ ] **Step 5: Chạy toàn bộ `flutter test` + `flutter analyze`**

```bash
cd frontend && flutter test
cd frontend && flutter analyze
```

Expected: PASS, không warning mới.

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/modules/strategy/controllers/project_kickoff_controller.dart \
        frontend/test/modules/strategy/controllers/project_kickoff_controller_test.dart
git commit -m "feat(frontend): auto-trigger + polling kickoff AI suggestion trong controller"
```

---

### Task 10: Frontend — view (hook Bước 2 + icon Bước 3)

**Files:**
- Modify: `frontend/lib/modules/strategy/views/project_kickoff_view.dart:715-734` (nút "Tiếp tục" Bước 2), `:837-844` (tiêu đề Bước 3)
- Modify: `frontend/test/project_kickoff_view_test.dart`

**Interfaces:**
- Consumes: `controller.requestKickoffSuggestion({required bool overwrite})`, `controller.aiSuggestionLoading` (Task 9).

- [ ] **Step 1: Viết test widget (RED)**

Trong `frontend/test/project_kickoff_view_test.dart`, thêm field đếm vào `FakeKickoffService` (class đã có ở đầu file, dòng 12-64) — thêm ngay dưới `final ProjectOperatingSetup? initialSetup;` (dòng 14):

```dart
  int requestKickoffSuggestionCallCount = 0;
  bool overwriteOnLastCall = false;

  @override
  Future<void> requestKickoffSuggestion(String projectId) async {
    requestKickoffSuggestionCallCount++;
  }
```

Thêm 3 test mới cuối `void main()` (dùng `draftP0Setup` — resume ở Bước 2 vì `selectedStage`/`stageDurationWeeks` chưa set — và `completeP0Draft` — resume thẳng Bước 3 — cả hai fixture đã có sẵn ở dòng 99-123):

```dart
  testWidgets('bấm Tiếp tục ở Bước 2 gọi requestKickoffSuggestion', (
    tester,
  ) async {
    Get.reset();
    final service = FakeKickoffService(initialSetup: draftP0Setup);
    Get.put(
      ProjectKickoffController(service: service),
      tag: draftP0Setup.projectId,
    );
    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ProjectKickoffView(
            projectId: draftP0Setup.projectId,
            onBack: () {},
            onActivated: (_) {},
            onOpenAdvancedRoadmap: () {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // draftP0Setup resume ở Bước 2 ("Chọn vòng đầu").
    expect(find.text('Bước 2: Chọn vòng đầu'), findsOneWidget);

    final buttonFinder = find.widgetWithText(ElevatedButton, 'Tiếp tục');
    await tester.ensureVisible(buttonFinder);
    await tester.tap(buttonFinder);
    await tester.pumpAndSettle();

    expect(service.requestKickoffSuggestionCallCount, 1);
  });

  testWidgets('icon AI ở Bước 3 hiện CircularProgressIndicator khi đang loading', (
    tester,
  ) async {
    await tester.pumpWidget(kickoffHarness(setup: completeP0Draft));
    await tester.pumpAndSettle();

    final controller = Get.find<ProjectKickoffController>(
      tag: completeP0Draft.projectId,
    );
    controller.aiSuggestionLoading.value = true;
    await tester.pump();

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    expect(find.byTooltip('Tạo lại gợi ý bằng AI'), findsNothing);
  });

  testWidgets('bấm icon AI ở Bước 3 gọi requestKickoffSuggestion', (
    tester,
  ) async {
    Get.reset();
    final service = FakeKickoffService(initialSetup: completeP0Draft);
    Get.put(
      ProjectKickoffController(service: service),
      tag: completeP0Draft.projectId,
    );
    await tester.pumpWidget(
      GetMaterialApp(
        home: Scaffold(
          body: ProjectKickoffView(
            projectId: completeP0Draft.projectId,
            onBack: () {},
            onActivated: (_) {},
            onOpenAdvancedRoadmap: () {},
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final iconFinder = find.byTooltip('Tạo lại gợi ý bằng AI');
    expect(iconFinder, findsOneWidget);
    await tester.tap(iconFinder);
    await tester.pumpAndSettle();

    expect(service.requestKickoffSuggestionCallCount, 1);
  });
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

```bash
cd frontend && flutter test test/project_kickoff_view_test.dart
```

Expected: FAIL — icon AI/`CircularProgressIndicator` chưa tồn tại trong Bước 3, nút "Tiếp tục" Bước 2 chưa gọi `requestKickoffSuggestion`.

- [ ] **Step 3: Sửa nút "Tiếp tục" Bước 2**

Trong `project_kickoff_view.dart`, sửa khối `ElevatedButton.icon` (dòng 715-734):

```dart
              ElevatedButton.icon(
                onPressed: controller.isSaving.value
                    ? null
                    : () async {
                        final ok = await controller.saveCurrentStep();
                        if (ok) {
                          controller.currentStep.value = 2;
                          controller.requestKickoffSuggestion(overwrite: false);
                        }
                      },
                icon: const Icon(Icons.arrow_forward_rounded, size: 16),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  foregroundColor: AppTheme.backgroundDarker,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 20,
                    vertical: 12,
                  ),
                ),
                label: Text(
                  controller.isSaving.value ? 'Đang lưu...' : 'Tiếp tục',
                ),
              ),
```

(chỉ thêm dòng `controller.requestKickoffSuggestion(overwrite: false);` — không `await`, fire-and-forget).

- [ ] **Step 4: Sửa tiêu đề Bước 3 thêm icon AI**

Trong `_buildStep3FirstWeek()`, thay khối tiêu đề (dòng 837-844):

```dart
          const Text(
            'Bước 3: Chốt việc tuần đầu',
            style: TextStyle(
              color: AppTheme.textDark,
              fontSize: 17,
              fontWeight: FontWeight.bold,
            ),
          ),
```

bằng:

```dart
          Row(
            children: [
              const Text(
                'Bước 3: Chốt việc tuần đầu',
                style: TextStyle(
                  color: AppTheme.textDark,
                  fontSize: 17,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(width: 8),
              if (controller.aiSuggestionLoading.value)
                const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              else
                IconButton(
                  icon: const Icon(Icons.auto_awesome, size: 20),
                  color: AppTheme.primary,
                  tooltip: 'Tạo lại gợi ý bằng AI',
                  onPressed: () =>
                      controller.requestKickoffSuggestion(overwrite: true),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
                ),
            ],
          ),
```

(Không cần bọc `Obx` riêng — toàn bộ `_buildStepContent()` đã nằm trong 1 `Obx` duy nhất ở tầng ngoài của file, đọc `controller.aiSuggestionLoading.value` ở đây được tracking bình thường.)

- [ ] **Step 5: Chạy test widget, xác nhận PASS**

```bash
cd frontend && flutter test test/project_kickoff_view_test.dart
```

Expected: PASS.

- [ ] **Step 6: Chạy toàn bộ frontend test + analyze**

```bash
cd frontend && flutter test
cd frontend && flutter analyze
```

Expected: PASS, không warning mới.

- [ ] **Step 7: Commit**

```bash
git add frontend/lib/modules/strategy/views/project_kickoff_view.dart \
        frontend/test/project_kickoff_view_test.dart
git commit -m "feat(frontend): hook auto-trigger Bước 2 + icon AI Bước 3 kickoff wizard"
```

---

### Task 11: Verify toàn bộ gate

**Files:** không tạo/sửa file — chỉ chạy gate.

- [ ] **Step 1: Chạy gate company**

```bash
cd /Volumes/SSD/javis-saas
cd services/company && npx tsc --noEmit && npx vitest run
cd /Volumes/SSD/javis-saas
make company-boundary-check
make encore-handler-boundary-check
make ts-suppression-check
```

- [ ] **Step 2: Chạy gate apps/cosa**

```bash
make apps-cosa-test
make typecheck-py
```

- [ ] **Step 3: Chạy gate frontend**

```bash
make frontend-test
make frontend-analyze
```

- [ ] **Step 4: Chạy gate migration + tổng hợp**

```bash
make schema-fingerprint-check
make verify
```

Nếu `make verify` fail ở phần không liên quan tới thay đổi này (đối chiếu với danh sách "Lỗi có sẵn KHÔNG liên quan" đã ghi trong `docs/superpowers/specs/2026-09-04-weekly-goal-agent-execution-design.md` §15.5), ghi chú lại và tiếp tục — không sửa phạm vi ngoài spec này.

- [ ] **Step 5: Test thủ công qua trình duyệt (golden path)**

```bash
make dev-status
```

Đảm bảo cả 4 tiến trình healthy, sau đó:
1. Mở Flutter app, tạo project mới → vào wizard kickoff.
2. Bước 1: điền đủ 3 câu hỏi → Tiếp tục.
3. Bước 2: giữ nguyên đề xuất P0/2 tuần → Tiếp tục.
4. Quan sát Bước 3: icon loading cạnh tiêu đề xuất hiện, sau vài giây (≤30s) tự điền `firstWeekOutcome` + action(s) vào 2 ô tương ứng.
5. Bấm icon "✨" lại — xác nhận nội dung bị ghi đè bằng gợi ý mới (khác câu trước, hoặc log giống nhau chấp nhận được do cùng context — quan trọng là request thực sự chạy lại, xem log worker `apps.cosa.worker.main`).
6. Sửa tay outcome/action rồi bấm "Xác nhận vòng đầu" — xác nhận activate thành công bình thường (không bị AI suggestion can thiệp vào flow activate cũ).

- [ ] **Step 6: Commit cuối (nếu Step 1-4 có sửa nhỏ để qua gate)**

```bash
git add -A
git commit -m "chore: sửa gate fail phát sinh từ kickoff AI suggestion (nếu có)"
```

Nếu không có gì cần sửa, bỏ qua bước này.
