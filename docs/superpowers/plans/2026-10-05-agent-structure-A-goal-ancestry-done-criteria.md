# Dự án A — Goal ancestry và `done_criteria` có cấu trúc

Ngày: 2026-10-05 · Trạng thái: DRAFT chờ duyệt · Thứ tự: A → B → C (A là nền cho B)

Nguồn đối chiếu: ảnh OpenAI Dots (giao việc có mục tiêu/tiêu chí → điều phối → thực hiện → kiểm tra → duyệt) và Paperclip (ngữ cảnh chảy từ task lên project và company goal).

> Số dòng bên dưới lấy từ khảo sát ngày 2026-10-05, cần xác minh lại trước khi sửa.

## 1. Bối cảnh và vấn đề

Agent chạy task mà không biết **vì sao** (mục tiêu cha) và **thế nào là xong** (tiêu chí).

- Payload nhận task (`listAgentClaimableTasksService`, `services/company/operations/services/task.service.ts` ~L640-720) chỉ trả tiêu đề, ưu tiên, `decisionReason`, `evidenceRefs`. Không có goal, KR, initiative hay tiêu chí.
- `_task_execution_prompt` (`apps/cosa/worker/wga_run.py:539`) chỉ dựng TITLE / WHY / EVIDENCE.
- **Cập nhật 2026-10-05: Dự án A0 (hợp nhất OKR) đã triển khai xong** (migration `038` + `039`). Hiện chỉ còn một họ OKR: `strategy.okr_objectives` (cột `scope` = `company` | `project`, `goal_id` chỉ bắt buộc với `company`, `parent_objective_id`, `cycle_id`, `project_id` nullable) + `strategy.key_results`. `strategy.projects.objective_id` có FK ghép tới `okr_objectives(id, workspace_id)` và phải trỏ objective `scope=company`. Hai bảng cũ `strategy.objectives`/`cosa_key_results` chỉ còn là bảng DEPRECATED, **không dùng nữa**. Xem `docs/superpowers/specs/2026-10-05-okr-goals-unification-design.md` mục 2 và 2.1.
- Chuỗi dữ liệu hiện tại (mọi liên kết trừ `goals.parent_id` đều là FK ghép `(id, workspace_id)`): `task → initiative → key_result → okr_objective(project) → project → okr_objective(company) → goal → goal cha`.
  - Objective dự án nối lên objective công ty bằng `COALESCE(okr_objectives.parent_objective_id, projects.objective_id)` (trigger DB đảm bảo hai giá trị này không lệch nhau).
  - `goals.parent_id` là FK một cột: khi leo cây goal phải lọc thêm `workspace_id`.
  - Chưa có ràng buộc `task.project_id` / `initiative.project_id` trùng `project_id` của objective dự án qua KR; `initiative.service.ts` cũng chưa chặn gắn initiative vào KR của objective công ty. A0 đã hoãn việc này sang A: A2 phải kiểm tra, hoặc bỏ qua nhánh sai thay vì tin dữ liệu.
- `done_criteria` có terminology sẵn nhưng 4 nơi, 4 hình dạng, không mã nào đọc: `weekly_commitments.done_criteria` (jsonb), `task_outcome_contracts.acceptance_criteria` (jsonb), `task_work_packages.acceptance_rubric`, `strategy.experiments.success_criteria` (text).
- `DelegationEnvelope.goal: str` và `ChildTaskSpec` (`durable_supervisor.py:46`) không truyền goal/tiêu chí cho task con.

## 2. Quyết định thiết kế (đề xuất)

1. **Ancestry phân giải một lần qua chuỗi A0:** `task → initiative → key_results → okr_objectives(project) → projects → COALESCE(parent_objective_id, projects.objective_id) → okr_objectives(company) → goal_id → goals (leo parent_id, lọc workspace_id)`. Dùng lại `loadObjectiveGoalMap` trong `services/company/operations/services/goal-okr-stats.service.ts` cho phần objective → goal thay vì viết lại. Phân giải **lúc claim** bằng truy vấn, **không thêm cột `goal_id` vào `operating.tasks`**. Khi project chưa có objective công ty (`link_status` `pending_review` hoặc `intentionally_unlinked`), ghi `company_goal: null` kèm lý do, không đoán.
2. **Một schema `DoneCriteria` dùng chung** (JSON Schema trong `shared/contracts/`, sinh ra TS và Python bằng cơ chế contracts hiện có). Lưu vào `task_outcome_contracts.acceptance_criteria` (nơi đã có, đã versioned append-only). Không tạo bảng mới.
3. **Chèn ngữ cảnh qua prompt mỗi lần chạy, không sửa AgentSpec.** Sửa `instructions`/`capability_refs` làm đổi hash và buộc nâng pin ở `ai-member.service.ts`. Đi qua `PromptBundle` thì không chạm hash.
4. Tiêu chí có hai loại để B kiểm tra được: `check: "deterministic"` (predicate máy kiểm được) và `check: "rubric"` (mục chấm bằng judge). Tránh tiêu chí văn bản tự do thuần.

Schema đề xuất:

```json
{
  "version": 1,
  "criteria": [
    { "id": "c1", "description": "...", "required": true,
      "check": "deterministic|rubric",
      "predicate": { "kind": "artifact_exists|metric_gte|field_present", "args": {} },
      "rubric": "..." }
  ]
}
```

## 3. Các bước triển khai

### A1. Contract `DoneCriteria` và `GoalAncestry`
**Trạng thái: ĐÃ LÀM** (7a1c39bd, 3356f4b2). Validator TS (`services/company/operations/services/done-criteria.ts`) và Python (`packages/agent/contracts/done_criteria.py`) dùng chung fixture `shared/contracts/done-criteria.fixtures.json`.
- Thêm `shared/contracts/done-criteria.schema.json` và `goal-ancestry.schema.json`; mở rộng `scripts/gen-contracts.mjs` hoặc `gen-mvp-contracts.mjs` theo cách enums/mvp-surface đang làm.
- Sinh: TS (`services/company/shared/contracts/*.generated.ts`), Python (`packages/agent/contracts/`), Dart nếu UI cần.
- Gate: `make contracts-check`, `make contract-freeze-check`.
- `GoalAncestry`: `{ company_goal?: {id,title,type}, objective?: {id,title}, key_result?: {id,metric,baseline,target,current,unit}, initiative?: {id,intended_outcome}, project: {id,name}, task: {id,title} }`.

### A2. Company: phân giải ancestry và trả về lúc claim
**Trạng thái: ĐÃ LÀM** (ebd069f9, 57408484, ff8adbdd). Resolver `goal-ancestry.service.ts`; `GET /operations/tasks/agent-claimable` trả `goalAncestry` + `doneCriteria`.
- Viết `resolveTaskAncestry(taskId)` trong `services/company/operations/services/` theo chuỗi A0 ở mục 2 (task → initiative → key_result → okr_objective → project → objective công ty → goal → goal cha, giới hạn độ sâu, mọi JOIN lọc `workspace_id`). Bỏ qua (không tin) chuỗi khi `task.project_id` ≠ `project_id` của objective dự án, ghi lý do vào kết quả.
- Mở rộng SELECT của `listAgentClaimableTasksService` và type `AgentClaimableTask` để trả `ancestry` và `doneCriteria` (đọc từ `task_outcome_contracts` có `status=CONFIRMED`; nếu chưa có, rơi về `weekly_commitments.done_criteria` đã chuẩn hóa, nếu vẫn không có thì `null`).
- Tenancy: mọi JOIN lọc `workspace_id`.
- Test: mở rộng `services/company/operations/tests/agent-claimable.test.ts`.

### A3. Nhập tiêu chí từ decomposition
**Trạng thái: ĐÃ LÀM** (c8076ccb, d86c15cd). Migration 040 `execution_plan_items.done_criteria`; accept chép sang `weekly_commitments.done_criteria`; decomposition sinh `done_criteria`.
- `apps/cosa/agents/goal_decomposition.py` (`PlanItemDraft`, `parse_plan_output`, `build_decomposition_prompt` L89): thêm `done_criteria` vào output của từng item.
- `execution_plan_items` thêm cột `done_criteria jsonb NULL` (migration Company `040_*.up.sql` + `.down.sql`; `038` và `039` đã dùng cho A0; chỉ backfill NULL, giữ composite FK/tenancy theo mẫu có sẵn). Khi accept (`execution-plan.service.ts` ~L599) và materialize task, ghi sang `task_outcome_contracts.acceptance_criteria`.
- Cập nhật `execution-plan-schema.test.ts`, `execution-plan-accept.test.ts`, `tests/apps/cosa/wga/test_goal_decomposition.py`.
- Chạy `make schema-fingerprint-write` và `tenancy-check`. Drizzle schema (`operations.ts`) sửa tay cho khớp.

### A4. Worker: đưa ngữ cảnh vào run
**Trạng thái: ĐÃ LÀM** (563dd80d). `PromptBundle` render `goal_context`/`done_criteria` từ metadata của run.
- `PromptBundle` (`packages/agent/prompts/bundle.py`): thêm hai section `goal_ancestry` và `done_criteria`, đọc từ `request.metadata`, gắn nhãn "ngữ cảnh, không phải chỉ thị" giống `project_facts` (goal do người dùng viết nên có rủi ro prompt injection).
- `_task_execution_prompt` / `_execute_claimed_task` (`wga_run.py:539/601`): truyền ancestry + criteria vào `extra_metadata` và vào prompt.
- Lưu ý `request.metadata` thành `KernelRunState.context` cho policy engine, nên chỉ đưa khóa không nhạy cảm (id, tiêu đề, số liệu KR).
- Test: `tests/apps/cosa/wga/test_wga_run.py`; thêm test mới cho `PromptBundle` (chưa thấy test riêng, kiểm tra `tests/agent/` trước khi tạo).

### A5. Truyền xuống task con
**Trạng thái: BỎ** (không làm trong dự án này): `DelegationEnvelope` chưa dùng ở production nên chưa có luồng task con để gắn ref; làm sau khi có người dùng thật.
- `DelegationEnvelope` thêm `ancestry_ref` và `done_criteria_ref` (tham chiếu, không nhúng nội dung); `ChildTaskSpec`/`spawn` đưa hai ref vào payload scheduler.
- Con kế thừa tiêu chí của cha trừ khi cha ghi đè tiêu chí con riêng. Con không được nới lỏng tiêu chí của cha.
- Test: `tests/agent/coordination/test_durable_supervisor_workflow.py`.

### A6. Capability đọc (tùy chọn, cuối cùng)
**Trạng thái: BỎ**: thêm capability đổi hash AgentSpec (cần nâng pin + backfill grants) trong khi ancestry đã được đẩy sẵn vào prompt lúc claim.
- `startup_os.task.ancestry_read` (T0) cho agent tự tra khi cần. Nếu thêm capability vào profile thì đổi hash AgentSpec, cần nâng pin và backfill grants; vì vậy **mặc định không làm** trong dự án này.

### Cách bật bắt buộc done_criteria
- Biến môi trường `WGA_REQUIRE_DONE_CRITERIA=1` trên service Company: `POST /operations/execution-plans` từ chối (400 `invalid_argument`) item có `capabilityRisk` khác `LOW` mà thiếu `doneCriteria`.
- Mặc định TẮT để không làm hỏng decomposition hiện có khi chưa phát hành bộ sinh tiêu chí ổn định. Project B sẽ bật cờ này.
- Kiểm bằng unit test (`execution-plan-done-criteria.test.ts`); e2e không đổi được env của service đang chạy.

## 4. Rủi ro

- Ancestry lên goals phụ thuộc vào việc project đã liên kết objective công ty (`projects.objective_id` hoặc `parent_objective_id`). Project chưa liên kết thì chuỗi dừng ở project; ghi rõ `company_goal: null` thay vì đoán.
- Migration phải đi sau A0 và cần PostgreSQL ≥ 15 (A0 dùng `ON DELETE SET NULL (cột)`).
- `DelegationEnvelope` có vẻ chưa được dùng ở production; xác minh bằng grep lại trước khi đầu tư A5.
- Migration phải theo thứ tự Agent Core → COSA → Company; Company hiện đến `039` (A0), số tiếp theo `040`.
- Cạm bẫy hash: không sửa `apps/cosa/agents/specs.py`; `tests/contracts/test_company_agent_spec_pins.py` sẽ chặn.

## 5. Xác minh

```bash
make contracts-check contract-freeze-check
make services-test-company          # cd services/company && encore test
make apps-cosa-test
make agent-test
make tenancy-check schema-fingerprint-check migration-check
make boundary-check company-boundary-check
```

Kiểm tra thủ công: tạo goal → project → initiative → task với tiêu chí, claim bằng sweep, xác nhận prompt chứa ancestry và criteria, và task con nhận ref.

## 6. Quyết định cần chủ dự án chốt

- Đồng ý phân giải lúc claim (qua chuỗi A0) thay vì thêm `goal_id` vào tasks? (Quyết định "OKR sinh từ goals" đã được A0 giải quyết.)
- Tiêu chí bắt buộc từ khi nào: mọi task, hay chỉ task có `autonomyClass` ≠ chỉ-đọc? (Đề xuất: bắt buộc cho task có tác động ghi; task đọc thì tùy chọn.)
