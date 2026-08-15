# Đóng các gap còn lại của COSA Agentic Architecture Adjustment (v13.1/v13.2)

## Context

Một audit trước đó đối chiếu `COSA_Agentic_Architecture_Adjustment_v13.1_v13.2.md` với code hiện có trong `backend/app/agents/` (đang ở working tree, chưa commit) cho thấy phần lớn khung P0–P2 đã tồn tại nhưng có 8 gap cụ thể khiến hệ thống chưa đạt DoD của Phase A/B trong spec: chưa có Agent Gateway thống nhất, hai Context Resolver song song không nhất quán, bảng `agent_events` thiếu cột, state machine Run/Plan/Step chưa hoàn chỉnh (không có retry/fallback), L3A chưa phải governance level chính thức, dispatch outreach sang n8n bị mock, Agent Activity UI mồ côi không gắn API, và domain agent mới có Sales/Finance (thiếu Marketing/Legal/Learning).

Kế hoạch này đóng toàn bộ 8 gap theo hướng **additive, tenant-scoped, test-first** đúng CLAUDE.md — không rewrite, không đổi stack, không bật lại module đang disable. Người dùng đã chốt 3 quyết định kiến trúc quan trọng: (1) nối n8n thật bằng cách mở rộng `agents/execution/n8n_bridge.py` thay vì dùng lại `automations/runtime/adapters/n8n.py`; (2) triển khai luôn Legal domain agent (net-new reasoning logic) cùng đợt với Marketing/Learning; (3) làm đủ state machine bao gồm RETRYING/FALLBACK/FAILED_FINAL ngay, nối với `CircuitBreaker`/`RetryPolicy` đã có sẵn trong `agents/reliability/reliability.py`.

Toàn bộ 6 router hiện tại (`/agents/runtime`, `/agents/execution`, `/agents/approvals`, `/agent` control-plane, `/agents/proposals`, `/orchestrator`, `/agents/mission-control`) vẫn giữ nguyên endpoint — không có thay đổi phá vỡ hợp đồng API. `agents/orchestrator/` (deterministic command router) và `agents/orchestration/` (Chief-of-Staff AI reasoning role) đã xác nhận là hai hệ thống hợp lệ khác nhau theo đúng spec §5 vs §11 — **không gộp lại**.

---

## Phase 1 — Governance data model + đầy đủ state machine (Gap 3, 4, 5)

Phase nặng nhất, làm trước vì các phase sau (Gateway, Activity UI, n8n dispatch) đều đọc/ghi vào `agent_events`/`agent_runs`/`agent_plan_steps`.

**1a. Schema (`agent_events`)**
- `backend/app/agents/governance/models.py`: thêm cột nullable `company_id, plan_id, step_id, actor_type, actor_id, tool_id, status` vào `AgentEventRecord`; đổi `run_id` sang `nullable=True`.
- Migration mới `backend/alembic/versions/v13_040_agent_events_columns.py` (7× `op.add_column`, đổi `run_id` nullable).
- Sửa 3 call site ghi event (`agents/execution/service.py:202-214`, `agents/orchestration/chief_of_staff.py:89-97`, `agents/control_plane/evaluator.py:42-59`) để ghi trực tiếp vào cột mới thay vì nhét vào `payload_jsonb`; bỏ hack `run_id=run_id or plan.id` ở `evaluator.py:44`.
- Thêm `GET /agent/plans/{plan_id}/events` vào `control_plane/router_api.py` (lọc theo `plan_id` — không cần tạo `AgentRun` giả cho mỗi plan).

**1b. State machine enums**
- File mới `backend/app/agents/governance/states.py`: 3 enum `AgentRunStatus`, `AgentPlanStatus`, `AgentPlanStepStatus` (giữ nguyên giá trị đang dùng thực tế + bổ sung giá trị spec yêu cầu: `CREATED, PLANNING, READY, RUNNING, WAITING_TOOL, WAITING_APPROVAL, EVALUATING, COMPLETED, RETRYING, FALLBACK, FAILED, FAILED_FINAL, CANCELLED, SKIPPED`), mỗi enum có `ALLOWED_TRANSITIONS` map + `validate_transition(old, new)` raise khi transition không hợp lệ.
- Giữ cột DB là `String(50)` (không đổi sang Postgres native ENUM — không có tiền lệ ENUM nào trong 39 migration hiện tại, và `ALTER TYPE ADD VALUE` có giới hạn transaction rủi ro hơn). Validate ở tầng ứng dụng, theo đúng pattern `PermissionLevel`/`normalize_permission_level` đã có trong `policy_engine.py`.
- `AgentRun.status` default đổi từ `"completed"` → `"created"` (migration `v13_041_agent_run_status_default.py`, `op.alter_column` server_default; hiện tại default sai là `"completed"` từ `v13_027_agent_automation_governance.py:33`).
- Thêm cột `retry_count`, `max_retries`, `fallback_used` (Integer/Integer/Boolean, default 0/3/false) vào `AgentPlanStep` — migration `v13_042_agent_plan_step_retry_columns.py`.

**1c. Nối Retry/Fallback/Circuit Breaker thật vào execution**
- `backend/app/agents/control_plane/execution.py`: bọc lệnh gọi domain-capability dispatch (khối `execute_step`, hiện ở dòng ~41-94 + domain-dispatch ~108-186) bằng `RetryPolicy.execute_with_backoff` (đã có ở `agents/reliability/reliability.py`, hiện chỉ dùng cho `ModelGateway`) — phân loại lỗi transient (timeout/429/5xx/network/n8n tạm lỗi) theo đúng bảng ở spec §24.1, không retry lỗi permission/policy/approval-rejected/validation.
- Khi hết `max_retries`: nếu domain/step có fallback provider cấu hình (tái dùng `CircuitBreaker` theo connector) → set `status=FALLBACK`, thử 1 lần; fallback cũng fail → `status=FAILED_FINAL`, cascade `run.status=FAILED_FINAL` nếu step này là bắt buộc (không có nhánh song song khác).
- Mỗi transition ghi một `agent_events` row (dùng cột `status` mới ở 1a) để Activity UI (Phase 4) thấy được đúng timeline retry.
- Gọi `states.validate_transition(...)` trước mỗi lần set `.status` (6 call site hiện tại: `execution.py:41,77,189,233`; `router_api.py:279`; `chief_of_staff.py:259`).

**1d. L3A chính thức + gộp 2 đường gating**
- `governance/policy_engine.py`: thêm `L3A_EXECUTE_WITH_APPROVAL` vào `PermissionLevel`; sửa `normalize_permission_level()` để check `"l3a"` **trước** `"l3"`/`"execute"` (hiện bug này khiến L3A tự động fold về `L3_EXECUTE` nếu đi qua `PolicyEngine.evaluate`); thêm nhánh L3A → `REQUIRE_APPROVAL` trong `PolicyEngine.evaluate()`.
- `control_plane/execution.py:53`: thay so sánh string-literal `"L3A_EXECUTE_WITH_APPROVAL"` trực tiếp bằng gọi qua `PolicyEngine.evaluate()` — gộp 2 đường gating (enum-based đang không dùng thật + string-literal đang dùng thật trong execution) thành một.

**Test (test-first):**
`backend/app/tests/agents/test_agent_state_machine.py` (transition hợp lệ/không hợp lệ cho cả 3 enum), `test_agent_retry_fallback.py` (transient error → retry → success; hết retry → fallback → fail → FAILED_FINAL; non-transient error → FAILED_FINAL ngay không retry), `test_agent_events_schema.py`, mở rộng `test_governance_policy_approval.py` (L3A normalize + forced approval) và `test_control_plane.py`/`test_governance_e2e.py` cho đường gating gộp.

---

## Phase 2 — Agent Gateway thống nhất (Gap 1)

- File mới `backend/app/agents/gateway/router.py`: `APIRouter` **không có business logic riêng**, chỉ mount lại 6 router hiện có (`agents.router`, `agents.execution_router`, `agents.approvals_router`, `control_plane.router_api`, `proposals.router`, `orchestrator.router`, `orchestration.router`) tại đúng prefix cũ (zero blast radius cho Flutter — `control_plane_service.dart`, `execution_service.dart`, `mission_control_service.dart` không cần sửa), cộng thêm `GET /api/v1/agents/_meta` liệt kê 7 sub-surface (tên, prefix, mục đích) để observability.
- `backend/app/main.py`: thay 7 lệnh `include_router` rời rạc bằng 1 lệnh `app.include_router(agents_gateway_router)`.
- Không gộp `orchestrator/` và `orchestration/` — chỉ gộp điểm mount.

**Test:** `backend/app/tests/agents/test_agent_gateway.py` — gọi qua `TestClient(app)` xác nhận tất cả path cũ vẫn hoạt động y hệt, cộng test cho `_meta`.

---

## Phase 3 — Gộp lớp fetch của Context Resolver (Gap 2)

- `ContextEnvelope` (`control_plane/context.py`) và `AgentContext` (`agents/context/builder.py`) có shape khác hẳn nhau và đang dùng ở 2 subsystem tách biệt hoàn toàn (control-plane goal/plan flow vs Chief-of-Staff) — không gộp thành 1 class (quá tốn công so với lợi ích).
- Chỉ gộp **tầng fetch dữ liệu domain**: `ContextResolver.resolve()` (bước "Domain Snapshots", `context.py:76-87`) gọi `build_agent_context()` thay vì gọi lại `get_pipeline_summary`/`get_financial_summary` trực tiếp, map `.sections["sales"].data`/`.sections["finance"].data` vào `sales_snapshot`/`finance_snapshot`.
- Sửa bug 4 field chết (`project`, `goal`, `cycle`, `knowledge_refs` trong `ContextEnvelope` luôn rỗng dù `resolve()` nhận `goal_id`): fetch thật `AgentGoal` row khi có `goal_id`, populate `goal`/`cycle`; `project` lấy từ goal nếu có liên kết; `knowledge_refs` để rỗng có kiểm soát (không fake data) cho tới khi Knowledge Base thật được nối (ngoài phạm vi 8 gap này).

**Test:** mở rộng `test_context_builder.py` và `test_control_plane.py` để assert `ContextResolver.resolve()`'s snapshots khớp với `build_agent_context()`'s sections, và cover việc populate `goal`/`cycle` khi có `goal_id`.

---

## Phase 4 — Gắn Agent Activity UI vào dữ liệu thật (Gap 7)

- Backend: thêm `GET /agent/runs` (list, scoped `workspace_id`, phân trang) vào `control_plane/router_api.py` — hiện chưa có endpoint list run nào.
- `frontend/lib/data/services/control_plane_service.dart`: thêm `listRuns()`; `getRunEvents(runId)` đã có sẵn nhưng chưa ai gọi — dùng lại.
- `frontend/lib/modules/agents/views/agents_view.dart`: thêm khu vực activity render `agent_activity_timeline_widget.dart` (hiện mồ côi, không import ở đâu), nối `listRuns()` + `getRunEvents()`.
- Xoá method trùng lặp ở `frontend/lib/data/services/outcomes_service.dart:60-68` (endpoint khác, cũng không ai gọi) sau khi màn hình mới dùng đường chính thức.

**Test:** `frontend/test/control_plane_service_test.dart` (thêm case `listRuns`/`getRunEvents`), test mới cho widget nối dữ liệu thật, backend `test_control_plane.py` thêm case `GET /agent/runs`.

---

## Phase 5 — Nối thật dispatch outreach qua n8n (Gap 6)

Theo quyết định: mở rộng `agents/execution/n8n_bridge.py` thay vì dùng `automations/runtime/adapters/n8n.py`.

- `agents/execution/n8n_bridge.py`: tách phần HMAC-sign + POST hiện có trong `dispatch_job_callback` (dòng 41-46 + helper `generate_hmac_signature`) thành hàm dùng chung `_send_signed_payload(url, secret, payload_dict, timeout)`; thêm hàm mới `dispatch_outbound_action(webhook_url, webhook_secret, action_type, payload, timeout=10.0)` dùng chung helper đó nhưng KHÔNG ép shape `ExecutionJobResult` — nhận `action_type` (`"sales.outreach"`) + `payload` dict tự do (`recipient_email`, `channel`, `message`, `draft_id`, `correlation_id`).
- Config webhook: thêm `COSA_N8N_SALES_OUTREACH_WEBHOOK_URL` + `COSA_N8N_SALES_OUTREACH_SECRET` (theo đúng pattern env var `N8N_BASE_URL`/`N8N_WEBHOOK_SECRET` đã có ở automations module, nhưng scoped riêng cho capability này theo đúng spec Tool Registry §16 — mỗi tool có config/permission riêng).
- `agents/domains/sales/action.py::dispatch_outreach`: bỏ receipt giả `"queued_to_n8n"`, gọi `dispatch_outbound_action` thật, map kết quả (success/failure) vào receipt, ghi `agent_events` với `tool_id="sales.communication.outreach_dispatch"` (dùng cột mới từ Phase 1a).
- `control_plane/execution.py:108-156`: xoá nhánh sample-data hardcode (`an@alphatech.example.com`) cho `step.domain == "sales"` — outreach drafts phải đến từ output thật của `SalesCommunicationCapability`, không phải dữ liệu giả cứng trong execution manager.

**Test:** `test_sales_outreach_dispatch.py` mới (mock HTTP layer, assert payload ký HMAC đúng, assert receipt phản ánh đúng kết quả thật/lỗi); cập nhật `test_n8n_execution_bridge.py` để cover `_send_signed_payload` dùng chung.

---

## Phase 6 — Domain agent parity: Marketing + Learning + Legal (Gap 8)

Theo pattern 6-file của Sales (`research/reasoning/data/communication/action/evaluation`).

**Marketing** (`agents/domains/marketing/`) — bọc logic có sẵn: `modules/marketing/services/analytics_engine.py` (`AnalyticsEngine`), `funnel_engine.py` (`FunnelEngine.build_funnel`), `scorecard_service.py` (`ScorecardService.build`), `skill_router.py` (`SkillRouter`).

**Learning** (`agents/domains/learning/`) — bọc `modules/learning/service.py` (`create_lesson`, `create_lesson_from_handoff`, `transition_lesson`, `list_lessons`), map trực tiếp vào spec §15.2/§38.

**Legal** (`agents/domains/legal/`) — net-new, vì `modules/legal/` hiện chỉ có CRUD (`LegalChecklistItem`/`LegalObligation`), không có logic phân tích:
- `research.py`/`data.py`: lấy context pháp lý từ DB hiện có (checklist/obligation rows) + knowledge base nếu có.
- `reasoning.py`: gọi `ModelGateway` (model_profile riêng, vd `legal_reasoning`) cho 5 capability theo spec §22 — `issue_classification`, `contract_clause_extraction`, `risk_summary`, `checklist_draft`, `expert_escalation_package`. Luôn kèm disclaimer + citation/evidence field bắt buộc (không có citation → fail schema validation, theo nguyên tắc §22 "Không cho optimizer học theo user accepted = legally correct" — áp dụng luôn cho reasoning thường, không chỉ optimizer).
- `communication.py`: soạn `expert_escalation_package` (draft-only).
- `action.py`: `checklist_draft` ghi vào **model CRUD có sẵn** (`modules/legal/models.py` qua service/router hiện tại), không tạo bảng riêng trùng lặp.
- `evaluation.py`: metric tối thiểu — schema validity, citation/evidence presence, hard-fail nếu thiếu evidence cho `risk_summary`.
- `control_plane/router.py` `DomainCapabilityRouter._ROUTES`: thêm route Marketing/Learning/Legal. **Legal bị chặn cứng ở L1_SUGGEST/L2_DRAFT** — không route nào cho Legal được gán L3/L3A (đúng spec §37: "Không cho Legal Agent tự ký hoặc nộp hồ sơ", quyết định pháp lý cuối luôn cần con người).

**Test:** `test_marketing_domain_wrapper.py`, `test_learning_domain_wrapper.py`, `test_legal_domain_wrapper.py` (mirror `test_finance_domain_wrapper.py`); riêng Legal có thêm assertion policy: không route Legal nào resolve ra `L3_EXECUTE`/`L3A_EXECUTE_WITH_APPROVAL`.

---

## Thứ tự thực hiện

Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6. Phase 1 bắt buộc trước vì Phase 4/5/6 đều phụ thuộc cột `agent_events` mới và state machine chuẩn. Phase 2/3 độc lập với nhau, làm trước Phase 4-6 vì cho một mặt bằng routing/context ổn định. Mỗi phase merge riêng, chạy full test suite (`pytest backend/app/tests/agents/` + `flutter test` cho phần frontend đổi) trước khi sang phase kế — đúng nguyên tắc spec §64.15 "Mỗi phase phải chạy được end-to-end trước khi sang phase tiếp theo."

## Verification

- Backend: `cd backend && pytest app/tests/agents/ -v` sau mỗi phase; riêng Phase 1 chạy thêm `pytest app/tests/agents/test_reliability_and_model_gateway.py app/tests/agents/test_governance_e2e.py -v` để đảm bảo không phá logic reliability/governance hiện có.
- Alembic: `alembic upgrade head` trên DB dev sau mỗi migration mới (v13_040, v13_041, v13_042), kiểm tra `alembic downgrade -1` chạy sạch (rollback path).
- Frontend: `flutter test` cho `control_plane_service_test.dart` + widget test mới (Phase 4).
- End-to-end thủ công sau Phase 5: tạo goal Sales → chạy plan → step outreach thật sự gọi webhook n8n test (hoặc mock server local) → xác nhận `agent_events` ghi đúng `tool_id`/`status`, Activity UI hiển thị đúng timeline retry nếu simulate lỗi transient.
- Chạy `rg -n --glob '!build/**' '(:8888|backend/server|javis/|web_socket_channel)' frontend/lib` cuối mỗi phase có đổi Flutter để đảm bảo không phạm runtime boundary rule.
