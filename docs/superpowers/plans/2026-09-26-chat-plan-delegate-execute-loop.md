# Chat agent: lập kế hoạch → phân công → thực thi → báo cáo — phân tích và kế hoạch

Ngày: 2026-09-26. Tiếp nối `2026-09-26-chat-agent-reliability.md` (độ tin cậy của 1 lượt chat).
Tài liệu này xét **cả vòng khép kín** (WGA — Weekly Goal → Agent Execution) từ tin nhắn chat
tới task hoàn tất và kết quả quay lại chat.

Trạng thái: đã triển khai Task 1–9 trên nhánh `claude/festive-fermi-ami9pa` (xem mục 6).
Trục trạng thái: IMPLEMENTED + WIRED; VERIFIED ở mức test Python/Flutter + typecheck TS +
migration chạy thật trên Postgres; **chưa** VERIFIED qua `encore test`/E2E Encore (môi trường
không có `encore` CLI/runtime).

## 1. Luồng hiện tại (đã xác minh)

```text
Flutter chat ──POST /agent/conversations/:id/messages──▶ apps/cosa conversation_routes.create_message
  (verify project, locale, lưu message, schedule task "run")
        │
        ▼
worker handlers._execute_run_task_inner ── kernel ── LLM + tool
        │ run.completed
        ├─ nếu profile ∈ {operations, founder_assistant} và câu trông như mục tiêu tuần
        │  (goal_intent: heuristic → LLM classify ≥ 0.75) → chèn message JSON {"kind":"goal_confirm"}
        ▼
Flutter hiện thẻ xác nhận ──founder bấm──▶ POST /operations/strategy/projects/:pid/weekly-goal
        │ (services/company phát operating.weekly_goal.set.v1)
        ▼
events/router._PLATFORM_SELF_TRIGGER → task "goal_decomposition"
        ▼
wga_run.execute_goal_decomposition_task
  (spec operations → JSON plan 2–7 item → parse_plan_output → POST /operations/execution-plans [draft])
        ▼
Command Center: founder sửa item (owner/autonomy) → POST /execution-plans/:id/accept
  (materialize task + task_dependencies, gán AI WorkforceMember; phát execution_plan.accepted.v1)
        ▼
task "workspace_task_sweep" → GET /operations/tasks/agent-claimable
  → mỗi task AUTO: advance(in_progress) → run kernel theo ownerAgentProfile
  → COMPLETED: finalize_wga_task_completion | WAITING_APPROVAL: waiting_approval | lỗi: blocked
  → nếu batch đầy thì tự re-schedule (tối đa độ sâu 20)
```

Những điểm đã tốt, cần giữ: founder quyết định (goal_confirm, accept), phân loại autonomy
(`autonomy-classifier.ts`) và policy theo capability nằm trong code xác định, delegation JWT
theo phạm vi `{workspace_id, run_id, capability_ids}`, profile không có spec thì fail closed,
có kill-switch và rate-limit theo workspace.

## 2. Lỗ hổng (xếp theo mức độ ảnh hưởng)

### P0 — vòng lặp bị kẹt, không bao giờ xong

**G1. Task không bao giờ tới `done`, nên task phụ thuộc bị kẹt mãi.**
- `wga_run.finalize_wga_task_completion` gọi `POST /operations/tasks/:id/validate-completion`,
  nhưng `services/company` **không có endpoint này**. Chỉ có hàm service
  `operations/services/execution-outcome.service.ts::validateTaskCompletion`, không handler nào
  gọi nó. Lời gọi luôn ném lỗi, nên task luôn bị đặt `in_progress` + `completion_pending`.
- `listAgentClaimableTasksService` (`task.service.ts:674`) chỉ trả task có mọi dependency
  `status = 'done'`. Vì vậy mọi item có `depends_on_titles` **không bao giờ được chạy**.
- Payload gửi đi chỉ có `{taskId}`, trong khi `validateTaskCompletion` bắt buộc `evidenceRefs`
  không rỗng (xem `execution-outcome.test.ts:365`). Expose endpoint thôi chưa đủ: worker phải
  gửi evidence thật (id work product/artifact của run).

**G2. Lệch profile: company gán owner mà worker không chạy được.**
- `routeOwnerProfile` (`autonomy-classifier.ts:65-120`) trả về `research_intelligence`,
  `strategy`, `sales`, `coding`, ngoài `operations|finance|marketing`.
- `wga_run._SPEC_BY_PROFILE` chỉ có 3 profile, nên các task còn lại bị `blocked`
  (`unsupported_owner_agent_profile_*`) ngay khi sweep, dù catalog
  (`agents/catalog.py::public_profile_specs`, `AGENT_PROFILE_SPECS`) đã có spec cho nhiều profile.
- Prompt phân rã (`goal_decomposition.build_decomposition_prompt`) chỉ cho model chọn
  3 domain, nên cùng một hệ thống có 3 danh sách profile khác nhau.

**G3. Run của WGA không mang `project_id` (vi phạm quy tắc 14).**
- Payload `workspace_task_sweep` (`events/router._self_trigger_payload`) bỏ mất `projectId`.
  `agent-claimable` không trả `projectId`, sweep quét **toàn workspace**, và
  `run_core.prepare_run` không nhận `project_id`.
- Hệ quả: tool không tự điền `project_id` (vì `apply_run_scope` cần `project_id` trong metadata),
  không chặn đọc chéo project, `project_activity` không ghi được theo project.
- Cần test để xác nhận thêm: compliance/tool của profile trong `PROJECT_SCOPED_RUN_PROFILES`
  có từ chối run thiếu `project_id` hay không.

### P1 — chất lượng kế hoạch và phân công

**G4. Phân rã thiếu ngữ cảnh.** `build_decomposition_prompt` hỗ trợ `next_best_actions` và
`existing_task_titles`, nhưng `execute_goal_decomposition_task` chỉ truyền `lifecycle_stage`,
và cả giá trị đó cũng không có trong payload event (`weekly_goal.set.v1` không mang stage), nên
luôn là `"unknown"`. Hệ quả: plan trùng task cũ, không bám giai đoạn P0–P6.

**G5. `expected_capability` do model tự bịa, không đối chiếu catalog.** Không có bước kiểm
capability id có tồn tại trong spec của owner profile hay không. Item với capability sai vẫn
được AUTO, rồi run thất bại hoặc agent không có tool đó. Cần validate với catalog capability
(allowlist theo spec của profile được route tới) trước khi POST plan. Item không hợp lệ thì
đặt `expected_capability=null` và coi là việc người làm, hoặc đánh dấu `needs_review`.

**G6. Lỗi phân rã bị nuốt im lặng.** Các nhánh `RunCoreError`, `status != COMPLETED`,
`PlanSchemaError`, lỗi POST chỉ `logger.error` rồi `return`. Flutter
(`_burstReloadDraftPlans`) chờ plan không bao giờ đến. Chat không có message báo lỗi. JSON sai
schema không được retry kèm lỗi để model tự sửa.

**G7. `NEEDS_APPROVAL` không có đường chạy.** Company trả cả `AUTO` và `NEEDS_APPROVAL` là
claimable, nhưng worker lọc `== "AUTO"` (ghi rõ là ranh giới v1). Item NEEDS_APPROVAL nằm ở
`todo` mãi, không có checkpoint duyệt trước khi chạy.

### P2 — trải nghiệm chat

**G8. Chat agent không nhìn thấy kế hoạch và tiến độ.** `founder_assistant` và `operations`
chỉ có `operations.task.list/read/create_draft`, không có capability đọc execution plan hay
trạng thái item/run. Founder hỏi "kế hoạch tuần tới đâu rồi?" thì agent không trả lời chính xác
được.

**G9. Không có phản hồi tiến độ về chat.** Chỉ có 1 message cố định sau khi tạo plan. Task
hoàn tất, bị chặn hoặc chờ duyệt đều không được báo lại vào conversation gốc (`origin_ref`).

**G10. Ý định lập kế hoạch chỉ nhận "mục tiêu tuần".** `goal_intent` chỉ bắt câu có tín hiệu
tuần/mục tiêu, và bỏ qua câu hỏi (`?`). Yêu cầu như "lập kế hoạch ra mắt sản phẩm và giao cho
các agent" không có cách kích hoạt rõ ràng. Cần một hành động tường minh (nút hoặc lệnh "Lập kế
hoạch"), không suy diễn thêm từ văn bản.

## 3. Kế hoạch triển khai

Nguyên tắc: mỗi task là một commit độc lập, TDD (viết test fail trước), không đổi hành vi ngoài
phạm vi nêu, migration chỉ Expand. Thứ tự làm theo thứ tự phụ thuộc: phải mở khoá vòng lặp
trước rồi mới nâng chất lượng.

### Task 1 (G1) — Hoàn tất task có evidence thật
- `services/company/operations/handlers/task.handler.ts`: thêm
  `POST /operations/tasks/:id/validate-completion` (`expose: true`, guard
  `resolveCosaTaskContext` với `WGA_CAP_TASK_ADVANCE` và khớp `runId`), gọi
  `validateTaskCompletion`, lỗi trả qua `APIError`. Thêm route vào
  `shared/contracts/mvp-surface.json` nếu gate yêu cầu.
- `wga_run.finalize_wga_task_completion`: gửi `{runId, evidenceRefs}`. Evidence lấy từ
  work product/artifact của run; nếu run không có evidence thì giữ `completion_pending`
  (đúng R2: run xong chưa có nghĩa là task xong) và phát tín hiệu cần founder xác nhận.
- Bỏ `except Exception` rộng. Phân biệt 404/422 (log rõ ràng) với lỗi mạng.
- Test: company (endpoint + guard + evidence rỗng bị 422); worker (evidence được gửi; endpoint
  lỗi thì không advance `done`); tích hợp: plan A→B, A xong thì B xuất hiện trong
  `agent-claimable`.
- Gate: `make services-test-company`, `make encore-handler-boundary-check`,
  `make route-auth-allowlist-check`, `make apps-cosa-test`.

### Task 2 (G2) — Một nguồn sự thật cho owner profile
- `wga_run`: thay `_SPEC_BY_PROFILE` bằng `AGENT_PROFILE_SPECS` ∩ `RUN_ELIGIBLE_PROFILES`
  (bảng tường minh, giữ fail closed với profile không có spec, không fallback về operations).
- Sinh danh sách domain cho prompt phân rã từ cùng bảng đó.
- Test chéo ngôn ngữ: mọi `OwnerAgentProfile` mà `routeOwnerProfile` trả về phải có spec
  chạy được. Cách làm: snapshot danh sách vào `docs/architecture/generated/` qua generator, hoặc
  test đọc `autonomy-classifier.ts` và so với catalog Python. Nếu có profile không có spec
  (vd. `crm`), company phải route về profile khác hoặc đặt `FOUNDER_ONLY`, không để worker block.

### Task 3 (G3) — Run WGA mang project_id, sweep theo project
- Company: `agent-claimable` trả thêm `projectId` (join `executionPlans.projectId`) và nhận
  tham số `projectId` tuỳ chọn; event `execution_plan.accepted.v1` mang `projectId`.
- `events/router._self_trigger_payload`: chuyển `project_id` cho sweep; coalescing key
  `wga:sweep:{ws}:{project}`.
- `run_core.prepare_run(..., project_id)`: bắt buộc với profile trong
  `PROJECT_SCOPED_RUN_PROFILES`, thiếu thì `RunCoreError("missing_project_scope")` (fail closed).
  Đưa vào `metadata["project_id"]` để `apply_run_scope` hoạt động.
- Decomposition run cũng truyền `project_id`.
- Test: sweep thiếu project thì task bị `blocked` với lý do rõ ràng; tool nhận `project_id`
  mặc định; không đọc được project khác.

### Task 4 (G4, G5) — Phân rã có ngữ cảnh và capability hợp lệ
- Trước khi phân rã, gọi company (delegation read-only): stage Project, NBA
  (`strategy.next_best_action.get`), tiêu đề task đang mở. Truyền vào
  `build_decomposition_prompt`.
- Hàm thuần mới `validate_plan_capabilities(items, catalog)`: capability không nằm trong spec
  của profile được route tới thì đặt về `null` và thêm cờ `capability_unverified`. Company coi
  item đó là `FOUNDER_ONLY`.
- Test đơn vị cho hàm validate; test prompt có NBA và task đã có.

### Task 5 (G6) — Lỗi phân rã có kết quả nhìn thấy được
- Khi gặp `PlanSchemaError`: retry 1 lần, đưa thông báo lỗi schema cho model (tối đa 2 lượt).
- Mọi nhánh thất bại: ghi `execution_plan` trạng thái `failed` (cần migration Expand thêm giá trị
  status hoặc bảng `decomposition_attempts`) **hoặc** tối thiểu phát `project_activity`
  `plan.decomposition_failed`. Nếu `origin == "chat"` thì thêm message assistant kèm
  `user_message` từ `provider_errors` (tái dùng `apps/cosa/worker/provider_errors.py`).
- Flutter: `_burstReloadDraftPlans` dừng và hiện lỗi khi nhận trạng thái failed, không chờ vô hạn.

### Task 6 (G7) — Đường chạy cho NEEDS_APPROVAL
- Sweep: item `NEEDS_APPROVAL` chưa được duyệt thì tạo approval **trước khi chạy** (bind đúng
  `run_id + checkpoint_ref` theo quy tắc 5), đặt task `waiting_approval`. Khi duyệt thì dùng lại
  `decide_approval` → `execute_resume_task` → `advance_wga_task_after_resume` (đường đã có).
- Test qua process thật cho resume (quy tắc 6), không dùng instance thứ hai trong cùng process.

### Task 7 (G8, G9) — Chat thấy và báo tiến độ
- Capability read-only mới `operations.execution_plan.read` (list plan + trạng thái item, task,
  run gần nhất theo project), gán cho `founder_assistant` và `operations`. Trước khi tạo, kiểm
  tra có tái dùng được `operations.task.list` bằng cách thêm filter plan hay không (quy tắc 4).
- Phản hồi về chat: khi task WGA đổi sang `done | blocked | waiting_approval`, nếu plan có
  `origin=chat` thì thêm 1 message assistant có cấu trúc vào `origin_ref`:
  `{"kind":"plan_progress", plan_id, done, total, blocked:[...]}`. Gom theo plan, tối đa 1
  message mỗi lượt sweep. Flutter render thẻ, không parse văn bản (quy tắc 7).

### Task 8 (G10) — Kích hoạt lập kế hoạch tường minh
- Flutter: action "Lập kế hoạch & giao việc" trong chat (dùng lại `setWeeklyGoal` với
  `origin=chat`, `originRef=conversationId`). `goal_confirm` giữ vai trò gợi ý.
- Không mở rộng heuristic `goal_intent` để đoán thêm.

### Task 9 — Kiểm chứng end-to-end
- Test golden path mới trong `make e2e-test`: chat → goal_confirm → weekly-goal → plan draft →
  accept (có 1 dependency và 1 item profile `strategy`) → sweep → A done → B chạy → message
  `plan_progress` trong conversation.
- `make verify` trước khi báo xong. Ghi rõ trục trạng thái (IMPLEMENTED / WIRED / VERIFIED)
  cho từng task.

## 4. Rủi ro và quyết định cần founder chốt

1. **Evidence tối thiểu để task được coi là done** (Task 1): chỉ cần artifact của run, hay
   bắt buộc founder xác nhận với một số capability? Đề xuất: AUTO + có artifact thì tự `done`;
   NEEDS_APPROVAL cần founder xác nhận.
2. **Trạng thái `failed` của execution plan** (Task 5) cần migration Expand; phương án nhẹ hơn
   là chỉ ghi `project_activity`. Đề xuất: làm migration, vì UI cần trạng thái có cấu trúc.
3. **Profile không có spec** (vd. `crm`): route về profile gần nhất hay đặt `FOUNDER_ONLY`?
   Đề xuất: `FOUNDER_ONLY`, không đoán thay founder.

## 5. Ngoài phạm vi
- Fallback model lúc chạy và lỗi HTTP 500 dashboard: xem mục "Kế hoạch riêng cần làm sau"
  của `2026-09-26-chat-agent-reliability.md`.
- Canvas workflow mở (Hướng 3) và clone asset do founder cấu hình.

## 6. Nhật ký triển khai (2026-09-26)

| Task | Commit | Khác với kế hoạch ban đầu |
|---|---|---|
| 1 (G1) | `7716bf3` | Không thêm endpoint `validate-completion`. `advance(done)` của agent bắt buộc `evidenceRefs` (cùng chính sách IA22/IA23), vì endpoint riêng sẽ bỏ qua kiểm tra AI-member và `task_execution_records`. Evidence là `WorkspaceArtifact` (checksum) của output run. |
| 2 (G2) | `331bcd4` | Đúng kế hoạch. Có test chéo đọc union `OwnerAgentProfile` trong TS. |
| 3 (G3) | `dbc2ef1` | Đúng kế hoạch. |
| 4 (G4, G5) | `be9b55a` | Ngữ cảnh (stage, task đang mở) đi trong payload event `weekly_goal.set.v1` thay vì worker gọi thêm API. **Chưa** đưa next-best-actions vào prompt. Prompt liệt kê catalog capability thật; sweep chặn capability không thuộc profile. |
| 5 (G6) | `de7923e` | Migration 029 (Expand) trên `weekly_plans` thay vì thêm trạng thái `failed` cho `execution_plans` (plan chỉ tồn tại khi phân rã thành công). |
| 6 (G7) | `3b42287` | Không tạo approval trước khi chạy. Policy siết capability của item thành REQUIRE_APPROVAL, nên gateway tạo approval bind `tool_call_id` như đường hiện có. Run xong mà không qua checkpoint thì không tự đóng task. |
| 7 (G8, G9) | `7961638`, `86acbb9` | Thêm capability `operations.execution_plan.read` (operations 1.4.0, founder_assistant 1.2.0). Tiến độ gửi dạng message `plan_progress`, 1 message/plan/lượt sweep. Sửa thêm lỗi: thẻ `goal_confirm` không truyền `originRef`. |
| 8 (G10) | `932184e` | Đúng kế hoạch. |
| 9 | `07922be` | Test tích hợp phía worker với company giả lập, thay cho E2E Encore thật (không chạy được ở đây). |

**Gate đã chạy xanh:** `make lint`, `make typecheck-py`, `make apps-cosa-test` (84%),
`make frontend-test`, `flutter analyze`, `tsc --noEmit` (company), `boundary-check`,
`company-boundary-check`, `encore-handler-boundary-check`, `ts-suppression-check`,
`route-auth-allowlist-check`, `frontend-api-contract-check`, `contract-freeze-check`,
`migration-compat-check`, `skillpacks-validate`. Migration company 001–029 đã chạy thật trên
Postgres 16 (up, down, up lặp lại); golden fingerprint của group `workspace` cập nhật đúng các
cột mới.

**Chưa chạy được ở đây (cần máy có Encore):** `make services-test-company` (gồm test mới
`decomposition-state.test.ts` và các test đã sửa `task-advance`, `agent-claimable`,
`weekly-goal`), `make e2e-test` (các test cần `encore`), `tenancy-check` phần vitest DB.
`make agent-test` có 3 lỗi có sẵn từ trước, do cần Postgres ở cổng 5432.

**Còn mở:**
- Đưa next-best-actions vào prompt phân rã.
- Đẩy `plan_progress` qua SSE: hiện message chỉ hiện khi tải lại hội thoại.
- Fallback model và lỗi HTTP 500: xem kế hoạch reliability.
