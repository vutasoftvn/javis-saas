# Bước 3 Kickoff Wizard — AI gợi ý outcome + việc tuần đầu — Design

**Ngày:** 2026-09-04
**Trạng thái:** Approved (brainstorming), chờ writing-plans
**Liên quan:**
- `docs/superpowers/specs/2026-09-01-founder-project-kickoff-design.md` — spec gốc wizard 3 bước; xác nhận Bước 3 vốn cố tình để input thuần thủ công.
- `docs/superpowers/specs/2026-09-04-weekly-goal-agent-execution-design.md` — WGA, nguồn tham chiếu pattern "task_type tường minh" cho worker dispatch, nhưng KHÔNG tái dùng bảng `execution_plans`/`weekly_plans` (project chưa activate, chưa có `weekly_plan_id`).
- `services/company/commercial/services/customer-engagement/copilot-cosa-client.ts` + `apps/cosa/api/copilot_routes.py` + `apps/cosa/worker/copilot_run.py` — pattern round-trip company↔cosa được tái dùng trực tiếp cho spec này (async dispatch + webhook callback).
- `ADR-AGENT-REG-001`, `ADR-COSA-DELEGATION-002`.

## 1. Vấn đề

`ProjectKickoffView` Bước 3 ("Chốt tuần đầu") hiện là input hoàn toàn thủ công: Founder phải tự nghĩ và gõ "Kết quả tuần 1" + 1-3 việc cần làm, dù tại thời điểm này backend đã có đủ ngữ cảnh (Bước 1: `target_customer`, `problem_statement`, `evidence_level`; Bước 2: `selected_stage`, `stage_duration_weeks` — đã autosave qua `saveCurrentStep()` ở mỗi bước, xem `frontend/lib/modules/strategy/controllers/project_kickoff_controller.dart:241-260`). Founder nên được AI gợi ý sẵn nội dung hợp lý để accept hoặc sửa, thay vì viết từ đầu.

### Xác nhận hiện trạng (đã verify bằng code)

| Mảnh | Hiện có | Vị trí |
|---|---|---|
| Project + operating_setup draft đã tồn tại **trước** Bước 1 | `ProjectSetupController.submitForm()` → `StrategyService().createBasicProject()` tạo `project_id` trước khi vào kickoff | `frontend/lib/modules/strategy/controllers/project_setup_controller.dart:88-108` |
| Autosave từng bước | `saveCurrentStep()` gọi `PUT /operations/projects/:id/operating-setup` sau mỗi "Tiếp tục" và mỗi thay đổi nhỏ ở Bước 3 | `project_kickoff_controller.dart:227-260`, `project_kickoff_view.dart:358,512,719` |
| Bảng draft | `strategy.project_operating_setups` (PK `project_id`), cột `target_customer/problem_statement/evidence_level/selected_stage/stage_duration_weeks/first_week_outcome/first_week_actions` | `services/company/operations/migrations/34_project_operating_setups.up.sql` |
| Route hiện có | `GET/PUT /operations/projects/:id/operating-setup`, `POST .../activate` | `services/company/operations/strategy/handlers/project-operating-setup.handler.ts:72-101` |
| Pattern round-trip company↔cosa đã chứng minh | company POST context → cosa `202 {run_id}` → worker `kernel.run` → callback webhook `POST .../result` (`X-Cosa-Service-Token`) → company cập nhật DB | `copilot-cosa-client.ts`, `copilot_routes.py:33-86`, `copilot_run.py:59-92` (`callback_company_result`) |
| FE gọi thẳng cosa (chat) — **không** dùng cho spec này | `agentOsBaseUrl`, `/agent/conversations/*` (`api_client.dart:113-230`, `agent_chat_service.dart`) | Đối chiếu, xem §3 Quyết định kiến trúc |
| Không có route đồng bộ nào trong `apps/cosa` | Mọi run đều 202 + async (kể cả copilot) | Đã verify grep toàn bộ `apps/cosa/api/*.py` |

## 2. Quyết định phạm vi (đã chốt với user)

| Câu hỏi | Chốt |
|---|---|
| Trigger gợi ý lần đầu | **Tự động** ngay khi Founder bấm "Tiếp tục" ở Bước 2 (chuyển `currentStep→2`) — không cần bấm nút |
| Tạo lại gợi ý | Icon **"✨ AI"** cạnh tiêu đề Bước 3, Founder chủ động bấm bất kỳ lúc nào |
| Ghi đè khi tạo lại | **Luôn ghi đè toàn bộ** outcome + actions hiện có, không hỏi xác nhận |
| Ghi đè lần tự động đầu tiên | Không áp dụng — lúc autotrigger các ô đang trống (mới vào Bước 3 lần đầu) |
| Kiến trúc round-trip | **Cách A**: company điều phối (giống pattern copilot), KHÔNG cho FE gọi thẳng cosa |

## 3. Quyết định kiến trúc: company điều phối, không phải FE→cosa trực tiếp

FE vốn đã có đường gọi thẳng `apps/cosa` cho chat (SSE, `agentOsBaseUrl`), và về mặt kỹ thuật có thể tự POST context + nghe SSE để lấy gợi ý nhanh hơn (không cần polling). Nhưng **chọn Cách A (company điều phối, webhook callback, FE polling)** vì:

1. Nhất quán với 2 tính năng "AI sinh nội dung nghiệp vụ" đã có (WGA, copilot customer-support) — cả hai đều để `services/company` đứng giữa làm hệ thống ghi nhận sự thật (CLAUDE.md rule #1: "Business truth thuộc services/*, không thuộc LLM runtime"). FE chỉ gọi thẳng cosa cho tương tác chat, chưa từng tự điều phối 1 quy trình nghiệp vụ.
2. Không cần dựng thêm cơ chế mới (SSE payload structured ngoài chat) — tái dùng nguyên vẹn pattern webhook đã có, đã test, đã chạy production (`copilot_run.py`).
3. Đánh đổi: độ trễ hiển thị thêm vài giây do polling 2s thay vì SSE tức thì — chấp nhận được vì đây là gợi ý điền sẵn, không phải hội thoại real-time.

## 4. Kiến trúc — luồng round-trip

```
Bước 2 "Tiếp tục" → saveCurrentStep() OK → currentStep.value = 2
                                   │
                    FE: requestKickoffSuggestion(overwrite: false)
                                   │
        POST /operations/projects/:id/kickoff-suggestion   (không cần body)
                                   │
   company (project-operating-setup.service.ts, hàm mới `requestKickoffSuggestion`):
     - validate draft đã có target_customer + problem_statement + evidence_level
       (chưa đủ → 422 "Hoàn thành Bước 1 trước", FE bỏ qua auto-trigger im lặng)
     - mint run_id (uuid), UPDATE ai_suggestion_status='dispatched',
       ai_suggestion_run_id=run_id, ai_suggestion_requested_at=now()
     - gọi cosa client (mẫu copilot-cosa-client.ts) — KHÔNG chờ cosa xử lý xong
     - trả 202 {runId} ngay
                                   │
        POST apps/cosa /agent/kickoff/first-week-suggestion
        { workspaceId, projectId, runId, targetCustomer, problemStatement,
          evidenceLevel, selectedStage, stageDurationWeeks }
        auth: X-Cosa-Service-Token == COSA_SERVICE_TOKEN (giống copilot_routes.py)
                                   │
   cosa route: validate input → plane.scheduler.schedule(
                 task_type='kickoff_suggestion', payload={...}) → trả 202 {run_id}
                                   │
   cosa worker (apps/cosa/worker/handlers.py, dispatch theo task_type tường minh,
                KHÔNG dùng cờ boolean kiểu copilot cũ):
     execute_kickoff_suggestion_task(plane, payload):
       - resolve PolicySnapshot + AgentSpec operations exact-hash (như run thường)
       - build prompt: context Bước 1+2 + định nghĩa P0/P1 (tái dùng nội dung
         "COSA đề xuất" tĩnh đang hiển thị ở Bước 2 làm system context)
       - kernel.run — KHÔNG capability_refs nào được gọi (thuần suy luận,
         giống execute_goal_decomposition_task, không ghi DB nghiệp vụ nào)
       - parse structured output theo Pydantic schema cố định:
           { outcome: str (<=200 ký tự), actions: list[str] (1-3 item,
             mỗi item bắt đầu bằng động từ hành động) }
       - schema sai / kernel lỗi/timeout → callback status='failed'
       - OK → callback status='completed' kèm outcome + actions
                                   │
        POST company /operations/projects/:id/kickoff-suggestion/result
        { runId, status, outcome?, actions? }
        auth: X-Cosa-Service-Token (giống copilot.handler.ts applyCopilotResultApi)
                                   │
   company (applyKickoffSuggestion): tìm project theo runId ==
     ai_suggestion_run_id đang lưu — không khớp (đã bị request mới hơn ghi đè)
     → no-op, trả 200 (không cho cosa retry)
     khớp → UPDATE ai_suggestion_status, ai_suggested_outcome, ai_suggested_actions
                                   │
   FE: poll GET /operations/projects/:id/operating-setup mỗi 2s (timeout 30s)
     kể từ lúc gọi requestKickoffSuggestion, tới khi ai_suggestion_status
     ∈ {completed, failed} hoặc hết timeout
       completed → set firstWeekOutcomeCtrl.text + firstWeekActions.assignAll(...)
                   → saveCurrentStep() (autosave như Founder tự gõ)
       failed/timeout → dừng poll, ẩn loading, không chặn wizard
```

Icon "✨ AI" ở Bước 3 gọi lại đúng luồng trên với `overwrite: true` — khi `completed`, ghi đè thẳng `firstWeekOutcomeCtrl.text` + `firstWeekActions` bất kể đang có gì.

## 5. Data model (Expand-only)

Thêm 5 cột nullable vào `strategy.project_operating_setups` (migration mới, `services/company/operations/migrations/`, tiếp theo sau `39_workspace_capability_policy`):

| Cột | Kiểu | Ghi chú |
|---|---|---|
| `ai_suggestion_status` | text null | `NULL \| 'dispatched' \| 'completed' \| 'failed'` |
| `ai_suggestion_run_id` | text null | uuid do company mint, dùng khớp callback |
| `ai_suggested_outcome` | text null | |
| `ai_suggested_actions` | jsonb null | mảng string, tối đa 3 |
| `ai_suggestion_requested_at` | timestamptz null | |

Không bảng mới — 1 project chỉ có 1 draft, mỗi lần gọi ghi đè cột hiện có (không cần lịch sử các lần gợi ý trước — xem §8 Ngoài phạm vi). CHECK constraint cho `ai_suggestion_status`.

## 6. Backend `services/company/operations/strategy`

### 6.1 Route mới (`project-operating-setup.handler.ts`)

- `POST /operations/projects/:id/kickoff-suggestion` — `expose: true`, `requireWorkspaceAccess` như route hiện có. Không cần body (server tự đọc draft hiện tại theo `id`). Trả `202 { runId }` hoặc `422` nếu thiếu Bước 1.
- `POST /operations/projects/:id/kickoff-suggestion/result` — `expose: true` nhưng auth riêng: header `X-Cosa-Service-Token` so khớp `COSA_SERVICE_TOKEN` (đúng pattern `copilot.handler.ts::applyCopilotResultApi`), **không** qua `requireWorkspaceAccess` (service-to-service, không có user session).
- `GET /operations/projects/:id/operating-setup` (đã có) — mở rộng `ProjectOperatingSetupView` thêm field `aiSuggestion: { status, outcome, actions, runId } | null`.

### 6.2 Service (`project-operating-setup.service.ts`)

- `requestKickoffSuggestion(id, workspaceId)`:
  - đọc draft hiện tại; thiếu `targetCustomer`/`problemStatement`/`evidenceLevel` → throw `APIError.invalidArgument`.
  - mint `runId` (uuid v4), `UPDATE ... SET ai_suggestion_status='dispatched', ai_suggestion_run_id=$runId, ai_suggestion_requested_at=now()`.
  - gọi `kickoffSuggestionCosaClient.dispatch({...})` (file mới `services/company/operations/strategy/services/kickoff-suggestion-cosa-client.ts`, mẫu 1-1 theo `copilot-cosa-client.ts`) — bọc try/catch, lỗi gọi cosa → set `ai_suggestion_status='failed'` ngay, KHÔNG throw ra FE (trả `202` bình thường, FE tự thấy `failed` khi poll).
  - trả `{ runId }`.
- `applyKickoffSuggestionResult(runId, status, outcome?, actions?)`:
  - tìm project theo `ai_suggestion_run_id = runId` — không thấy → no-op (log warning, có thể do request mới hơn đã ghi đè `run_id`).
  - `UPDATE ai_suggestion_status=$status, ai_suggested_outcome=$outcome, ai_suggested_actions=$actions`.

### 6.3 Validate output từ cosa

Company **không tin** `actions` cosa gửi về nguyên trạng — validate lại: tối đa 3 phần tử, mỗi phần tử non-empty string sau `trim()`, cắt bớt nếu cosa lỡ trả >3 (không throw, chỉ log warning + cắt — lỗi hiếm, không đáng chặn cả response).

## 7. `apps/cosa`

### 7.1 Route (`apps/cosa/api/kickoff_suggestion_routes.py`, mới — theo mẫu `copilot_routes.py`)

`POST /agent/kickoff/first-week-suggestion` — auth `COSA_SERVICE_TOKEN` (service-to-service, giống copilot). Input Pydantic model `{ workspace_id, project_id, run_id, target_customer, problem_statement, evidence_level, selected_stage, stage_duration_weeks }`. Validate xong → `plane.scheduler.schedule(task_type="kickoff_suggestion", payload=input.model_dump())` → trả `202 {"run_id": run_id}`.

### 7.2 Worker handler (`apps/cosa/worker/handlers.py`)

`execute_kickoff_suggestion_task(plane, payload)` — dispatch theo `task_type == "kickoff_suggestion"` (bảng dispatch tường minh, theo đúng convention `_dispatch_wga_task` đã dùng cho WGA — không dùng cờ boolean như nhánh copilot cũ để tránh nhầm lẫn CLAUDE.md rule về "không dựa fallback ngầm"):

1. Resolve PolicySnapshot + AgentSpec `operations` exact-hash (như run thường).
2. Build prompt: nối context Founder (Bước 1+2) + đoạn mô tả tĩnh P0/P1 hiện đang hiển thị ở Bước 2 UI (copy nguyên văn nội dung "COSA đề xuất: Khám phá P0 trong 2 tuần..." làm system context, để AI hiểu đúng khung tương tự Founder đang thấy).
3. `kernel.run` — **không** capability nào trong `capability_refs` của call này được dùng (thuần structured-output reasoning, giống `execute_goal_decomposition_task` khi không gọi capability).
4. Parse output theo Pydantic schema cố định (`KickoffSuggestionOutput{outcome: str, actions: list[str]}`, `@validator` giới hạn `len(actions) in [1,3]`, mỗi `actions[i]` non-empty).
5. Schema sai / kernel lỗi / timeout → `except` bắt hết → `callback_kickoff_result(run_id, "failed")`.
6. OK → `callback_kickoff_result(run_id, "completed", outcome, actions)`.

### 7.3 Callback (`apps/cosa/worker/kickoff_suggestion_run.py`, mẫu `copilot_run.py:59-92`)

`callback_kickoff_result(run_id, status, outcome=None, actions=None)` — `httpx.AsyncClient(timeout=10.0)`, `POST {COMPANY_SERVICE_URL}/operations/projects/{project_id}/kickoff-suggestion/result` (cần lưu `project_id` kèm task payload để build URL), header `X-Cosa-Service-Token`. Lỗi → log warning, **không retry** (đúng hành vi `copilot_run.py`).

## 8. Frontend

| Thay đổi | File |
|---|---|
| Model | `ProjectOperatingSetup` thêm field `aiSuggestionStatus`, `aiSuggestedOutcome`, `aiSuggestedActions` | `frontend/lib/data/models/project_operating_setup_model.dart` |
| Service | `requestKickoffSuggestion(id)` — `POST .../kickoff-suggestion` | `frontend/lib/modules/strategy/services/project_operating_setup_service.dart` |
| Controller | `aiSuggestionLoading` (Rx bool), `requestKickoffSuggestion({required bool overwrite})`, `_pollSuggestion()` (Timer.periodic 2s, hủy sau 30s hoặc khi terminal); gọi tự động ngay sau `saveCurrentStep()` thành công của nút "Tiếp tục" Bước 2 | `project_kickoff_controller.dart` |
| View | Icon `✨` + `CircularProgressIndicator` nhỏ cạnh "Bước 3: Chốt việc tuần đầu"; `onPressed: () => controller.requestKickoffSuggestion(overwrite: true)` | `project_kickoff_view.dart` (`_buildStep3FirstWeek()`) |
| Contract | thêm 2 route mới vào `shared/contracts/mvp-surface.json`, chạy `make frontend-api-contract-check` | |

Khi `completed` (dù auto lần đầu hay bấm icon overwrite): set `firstWeekOutcomeCtrl.text = suggestion.outcome`, `firstWeekActions.assignAll(suggestion.actions.map((t) => FirstWeekActionDraft(title: t)))`, rồi gọi `saveCurrentStep()` — nhất quán với autosave đã có, Founder rời màn giữa chừng không mất gợi ý đã nhận.

Poll dùng lại `_service.get(id)` đã có (route `GET .../operating-setup`), không cần route mới cho FE đọc kết quả.

## 9. Xử lý lỗi

| Tình huống | Xử lý |
|---|---|
| company gọi cosa lỗi (network/5xx) | company set `ai_suggestion_status='failed'` ngay trong `requestKickoffSuggestion`, không throw; FE thấy `failed` ở lần poll đầu, dừng ngay |
| Draft thiếu Bước 1 (target_customer/problem_statement/evidence_level rỗng) | `422`; FE bỏ qua auto-trigger, không hiện loading, không gọi lại |
| Callback `run_id` không khớp bản ghi hiện tại | company no-op, trả `200` (đã bị request mới hơn ghi đè, không phải lỗi) |
| Callback không đến trong 30s | FE tự dừng poll, ẩn loading; Founder tự gõ bình thường; Founder có thể bấm icon AI thử lại |
| AI trả schema sai / >3 actions / action rỗng | cosa: schema sai → `failed` (không callback nửa vời); company: nếu lỡ lọt qua, cắt bớt actions >3 + lọc action rỗng, log warning |
| Founder rời Bước 3 giữa lúc đang chờ rồi quay lại | trạng thái `ai_suggestion_status` đã lưu server-side; poll lại từ đầu khi `load()` thấy `status='dispatched'` |
| Founder bấm icon AI 2 lần liên tiếp trước khi lần đầu xong | lần gọi sau ghi đè `run_id` mới → callback của lần trước tới sau sẽ no-op (run_id lệch) — đúng theo thiết kế §9 dòng "Callback run_id không khớp" |

## 10. Testing

**`services/company`:**
- `requestKickoffSuggestion`: thiếu Bước 1 → invalidArgument; đủ điều kiện → set `dispatched` + gọi cosa client với đúng payload; cosa client throw → set `failed`, không throw ra ngoài.
- `applyKickoffSuggestionResult`: khớp `run_id` → update đúng cột; không khớp → no-op; `actions` >3 phần tử → cắt còn 3; action rỗng sau trim → lọc bỏ.
- Webhook route: thiếu/sai `X-Cosa-Service-Token` → 401/403.
- `GET operating-setup`: trả đúng field `aiSuggestion`.

**`apps/cosa`:**
- `execute_kickoff_suggestion_task`: mock kernel trả JSON hợp lệ → callback `completed` đúng payload; JSON sai schema → callback `failed`, không throw ra worker loop; không capability nào được gọi trong suốt run (assert gateway không nhận capability call nào).
- Route `POST /agent/kickoff/first-week-suggestion`: sai `COSA_SERVICE_TOKEN` → 401; input hợp lệ → 202 + schedule task đúng `task_type`.

**Frontend (`flutter test`):**
- Controller: auto-trigger sau "Tiếp tục" Bước 2 khi Bước 1 đã đủ; không auto-trigger khi thiếu; poll dừng đúng lúc `completed`/`failed`/timeout 30s; icon AI luôn ghi đè bất kể nội dung hiện tại.
- Widget: icon `✨` hiện loading state khi `dispatched`; ẩn khi terminal.

**Gate:** `make services-test-company`, `make apps-cosa-test`, `cd frontend && flutter test`, `make frontend-analyze`, `make frontend-api-contract-check`, `make company-boundary-check`, `make encore-handler-boundary-check`, `make ts-suppression-check`, migration gate (rollback down.sql).

## 11. Ngoài phạm vi

- Không sinh gợi ý cho tuần 2+ sau khi project đã activate — đã có WGA (`weekly-goal` + `execution-plans`) riêng cho việc đó.
- Không lưu lịch sử nhiều lần gợi ý (mỗi lần ghi đè cột, không insert row mới) — nếu sau này cần audit trail, làm bảng riêng lúc đó.
- Không cho Founder chỉnh sửa prompt/tham số AI dùng để gợi ý.
- Không tự nới `WGA_MAX_RUNS...` hay rate-limit riêng cho tính năng này (mỗi lần bấm icon AI là 1 run, không có giới hạn per-workspace/ngày ở v1 — rủi ro thấp vì đây là action thủ công của chính Founder trên project của họ, không phải autopilot).
