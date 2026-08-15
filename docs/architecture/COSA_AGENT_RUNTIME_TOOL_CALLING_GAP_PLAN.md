# COSA Agent Runtime — Tool-Calling Gap + Follow-up Plan

> **Source spec:** `myiris.md` (repo root) — spec đề xuất tích hợp DeepSeek Harness
> (Agent Runtime) + n8n (Automation Runtime) vào COSA v13.1/v13.2, nội dung gần như
> trùng với `COSA_DeepSeek_Harness_Integration_v13.1_v13.2(2).md` đã được audit trong
> `COSA_AGENT_AUTOMATION_RUNTIME_ADJUSTMENT_PLAN.md` (cùng thư mục).
>
> **Quan hệ với các plan đã có:** `COSA_AGENT_AUTOMATION_RUNTIME_ADJUSTMENT_PLAN.md`
> (Phase 0-6) và `COSA_AGENT_GOVERNANCE_REALIZATION_PLAN.md` đã được thực thi — xác
> nhận qua git log (`0817ee0 feat(agents-automation): complete Phases 0 to 6` và các
> commit theo sau tới `7dc3c52`). Tài liệu này **không lặp lại** phần đã audit trong hai
> plan trên; nó bắt đầu từ trạng thái code *sau* Phase 6 và chỉ ra gap còn sót lại mà
> hai plan trước chưa xử lý triệt để — cụ thể là vòng lặp tool-calling thật bên trong
> `DeepSeekHarnessAdapter`.
>
> **Audit date:** 2026-08-15. Đối chiếu trực tiếp `myiris.md` với `backend/app/agents/`,
> `backend/app/automations/`, `backend/app/core/tool_registry.py`,
> `backend/app/modules/chat/company_tools.py`.
>
> **Trạng thái:** Roadmap đã đối chiếu đầy đủ (Phần A); Phần B (4 slice) đủ chi tiết để
> bắt tay code, theo đúng CLAUDE.md ("test-first development for behavioral changes")
> và chỉ thị #14 của `myiris.md` ("Tạo tests trước khi bật write-capability").

---

## Phần A — Roadmap: đối chiếu myiris.md với trạng thái hiện tại

### A.1 Đã triển khai đầy đủ (giữ nguyên, không xây lại)

| myiris.md đề xuất | Trạng thái | Vị trí |
|---|---|---|
| §4 AgentRuntime abstraction | ✅ Có | `backend/app/agents/runtime/base.py`, `manager.py`, `types.py` |
| §5 DeepSeek Harness Adapter | ✅ Có (thật, không phải mock) | `backend/app/agents/runtime/adapters/deepseek_harness.py` — wrap `deepseek-harness-sdk==0.1.0rc6` qua JSON-RPC subprocess, có streaming/timeout/cancel |
| §6 Feature flags | ✅ Có (DB row, không phải env var — đã được lưu ý trong ADR-V13-1-004/008) | `backend/app/core/feature_flags.py`: `FLAG_AGENT_RUNTIME`, `FLAG_AGENT_RUNTIME_DEEPSEEK`, `FLAG_AGENT_EXECUTION`, `FLAG_AGENT_EXECUTION_SANDBOX`, `FLAG_AGENT_EXECUTION_BROWSER` |
| §9 Chief of Staff Agent | ✅ Có | `backend/app/agents/orchestration/chief_of_staff.py` |
| §13 Policy Engine L0-L3 | ✅ Có, đúng 4 mức | `backend/app/agents/governance/policy_engine.py` |
| §14 Approval Gateway | ✅ Có, lưu Postgres | `backend/app/agents/governance/approval_service.py`, model `AgentApproval` |
| §18 Runtime Trace & Audit | ✅ Có (agent_runs, agent_events, agent_tool_calls) | `backend/app/agents/governance/models.py` — `AgentRun`, `AgentEventRecord`, `AgentToolCall` (SnowflakeIDMixin) |
| §19 Security & Sandbox (execution) | ✅ Có — nhánh riêng theo doc OpenSandbox (`COSA_OPENSANDBOX_EXECUTION_RUNTIME_PLAN.md`) | `backend/app/agents/execution/` — `ExecutionProvider`, `OpenSandboxExecutor`, policies, artifacts, migration `v13_031_execution_runtime.py` |
| §11 COSA MCP Gateway (tương đương) | ✅ Có nhưng namespace phẳng, không theo `cosa.<domain>.<verb>` | `backend/app/core/tool_registry.py` — `ToolSpec` với risk_level/permission_level/requires_approval/allowed_agent_keys |
| §16 Agent Session vs Business Memory | ✅ Có phân tách | module `agent_memory` riêng (MEM-0/MEM-1), tách khỏi `AgentEventRecord` |
| Automation Runtime (n8n) — §16-26 phần automation | ✅ Có | `backend/app/automations/runtime/base.py` (`AutomationProvider`), `adapters/n8n.py` (HMAC-signed webhook + callback), `router.py`, mounted `/api/v1/automations` |
| §50 Tenant isolation | ✅ Có, đúng nguyên tắc "không tin company_id do model tự truyền" | `backend/app/core/tenancy.py` — pattern `get_*_scoped(db, id, workspace_id)`, 404 khi mismatch |
| Idempotency (§49) cho execution jobs | ✅ Có | `execution_jobs` table có field `idempotency` |

**Kết luận A.1:** Không viết lại các phần này. Rủi ro lớn nhất là **triển khai trùng**
(vd. tạo lại `AgentRuntime`/`ApprovalService` mới) — mọi việc mới phải import và mở
rộng các module trên.

### A.2 Có nhưng thiếu (partial) — mở rộng khi có nhu cầu thật, không ưu tiên ngay

| myiris.md đề xuất | Thiếu gì | Ghi chú |
|---|---|---|
| §11.2-11.3 Namespace `cosa.<domain>.<verb>` | Namespace hiện tại phẳng: `sales`, `finance`, `strategy`, `execution` (OKR/12WY gộp vào `strategy`) | Đổi tên rủi ro phá vỡ mọi `allowed_agent_keys` hiện có — khuyến nghị **không đổi** namespace hiện tại, chỉ áp namespace mới cho tool mới nếu cần |
| §12 Bộ MCP tools tối thiểu | **Marketing: 0 tool đã đăng ký** | Sales/Finance/Strategy(OKR) đã có tool đọc cơ bản; hoãn Marketing tới khi có agent Marketing thật |
| Automation Catalog (§10, §31.3) | Chỉ có 2 automation_key: `system.telegram_notification`, `sales.followup_email` (seed `v13_028`) | Đủ cho POC hiện tại |
| §23 Concurrency & resource controls | Chỉ có `timeout_seconds` per-run; chưa có `max_concurrent_runs`, subagent depth limit | Rủi ro thấp ở quy mô per-customer deployment hiện tại |
| §38 Observability metrics | Chưa có (không `prometheus`/`Counter` nào cho agent_runs) | Không phải blocker cho functionality |
| DEPLOYMENT.md | Có ranh giới cho OpenSandbox (ADR-EXEC-003) nhưng **chưa có** ranh giới cho Agent Runtime (Harness) | Cần bổ sung theo CLAUDE.md — làm cùng Slice 1 dưới đây |

### A.3 Gap nghiêm trọng — chặn giá trị thực của toàn hệ thống

**#1 — DeepSeekHarnessAdapter chưa gọi tool thật (blocker lớn nhất, chưa được hai plan
trước xử lý).** `backend/app/agents/runtime/adapters/deepseek_harness.py:207` hardcode
`tool_calls=[]`. Không có import `tool_registry` ở bất kỳ đâu trong `agents/runtime/`.
Agent chạy qua Harness runtime hiện tại chỉ *chat/reasoning*, không tự gọi được
`cosa.sales.pipeline_summary` hay bất kỳ tool nào đã đăng ký — trái mục tiêu cốt lõi
của myiris.md §2 (Harness chịu trách nhiệm "tool execution lifecycle"). Chief of Staff
hiện "delegate" bằng cách **gọi thẳng hàm Python** (`sales_tools.get_pipeline_summary(...)`)
chứ không qua một agentic tool-use loop thật — Harness gần như chỉ là LLM wrapper.

**#2 — Agent Registry (§7) chưa tồn tại.** `agent_key` như `sales_specialist`,
`finance_specialist` chỉ là chuỗi rải rác trong `allowed_agent_keys=[...]` của từng
tool — không có nơi định nghĩa tập trung tool/write_tools/requires_approval/
permission_profile theo agent.

**#3 — Context Builder (§17) chưa tồn tại.** `chief_of_staff.py:175-179` dựng context
bằng dict tay, không có freshness/confidence/source, không có OKR/company context.

**#4 — agent_proposals → OKR/12WY bridge (§30) chưa tồn tại.** Không có bảng
`AgentProposal`. Khuyến nghị của Chief of Staff dừng ở
`ApprovalService.create_approval(...)` cho `automation_dispatch` — không có đường đi
từ "agent đề xuất" → "founder duyệt" → "tạo OKR/task thật".

---

## Phần B — Kế hoạch triển khai (4 slice, theo thứ tự phụ thuộc)

Theo đúng myiris.md §65/§66 (giữ PR nhỏ, không gộp): triển khai và test từng slice độc
lập, theo đúng thứ tự dưới đây vì slice sau phụ thuộc slice trước.

### Slice 1 — Wire tool-calling thật vào DeepSeekHarnessAdapter (ưu tiên cao nhất)

**Vấn đề mở cần xác nhận trước khi code:** SDK `deepseek-harness-sdk==0.1.0rc6`
(Developer Preview) — cần kiểm tra API thật trong
`backend/.venv/lib/python3.11/site-packages/deepseek_harness/` xem có cơ chế "custom
tool registration" cấp session hay không, hay chỉ có plugin nội bộ `bash-local`/
`fs-local`. Nếu SDK không hỗ trợ đăng ký tool tùy biến trực tiếp, dùng
**application-level ReAct loop** (vòng lặp do COSA tự điều khiển, không phụ thuộc
tool-calling native của SDK) — an toàn hơn vì mọi tool-call vẫn đi qua
PolicyEngine/tenancy của COSA thay vì để SDK tự thực thi.

**Thiết kế:**
1. Tách `_parse_structured_output` từ `chief_of_staff.py` ra
   `backend/app/agents/runtime/json_output.py` dùng chung.
2. Tạo `backend/app/core/tool_dispatch.py` — generalize logic đã có trong
   `backend/app/modules/chat/company_tools.py::execute_tool` (dùng
   `get_tool_by_flat_name`, `_coerce` để loại `_INJECTED_PARAMS = ("db", "workspace_id",
   "user_id", "chat_session_id")` khỏi input do model sinh ra, rồi inject giá trị
   **server-derived, không tin model**) để cả chat và agent runtime dùng chung một
   điểm thực thi tool an toàn — tránh hai cài đặt song song lệch nhau.
3. Tạo `backend/app/agents/runtime/tool_bridge.py::dispatch_tool_call(db, request:
   AgentRunRequest, tool_flat_name, args)`:
   - Lookup `ToolSpec` qua `get_tool_by_flat_name`.
   - Chạy qua `PolicyEngine.evaluate(...)` — DENY chặn, REQUIRE_APPROVAL tạo
     `ApprovalService.create_approval(...)` và trả `awaiting_approval` (không thực
     thi), ALLOW mới chạy.
   - `workspace_id`/`company_id`/`user_id`/`agent_key` lấy từ `AgentRunRequest` (đã có
     sẵn trong `runtime/types.py`, do caller — không phải model — set), đúng nguyên
     tắc tenancy.py.
   - Ghi `AgentToolCall` row (bảng đã tồn tại) với input/output/latency/status.
4. Trong `deepseek_harness.py::_execute_harness`, thay lệnh gọi `harness.run()` đơn lẻ
   bằng vòng lặp có giới hạn (tối đa 6 turn): liệt kê schema tool được whitelist cho
   `request.agent_key` (từ `tool_registry.available_tools(...)` lọc theo
   `allowed_agent_keys`), yêu cầu model trả `{"tool_call": {...}}` hoặc
   `{"final": "..."}`; khi có `tool_call` → gọi `tool_bridge.dispatch_tool_call` →
   tiếp tục cùng session (`harness.start_session`/`Session.run`) với kết quả tool; tích
   lũy vào `AgentRunResult.tool_calls` thay vì `[]` ở dòng 207.
5. Áp dụng tương tự cho `stream()` (dòng 250-327), phát `tool_call_started`/
   `tool_call_completed` events.
6. Thêm flag mới `FLAG_AGENT_RUNTIME_TOOLS` trong `feature_flags.py`, mặc định `False`.

**Vấn đề bảo mật cần xác nhận trước khi bật production:** plugin `bash-local`/
`fs-local` của Harness runtime hiện chỉ sandbox theo `cwd` (`DSH_CWD`), không sandbox
network — cần xác nhận subprocess Harness không thể gọi thẳng vào COSA internal service
(bypass `tool_bridge`/PolicyEngine).

**Files:** `backend/app/agents/runtime/adapters/deepseek_harness.py`,
`backend/app/agents/runtime/tool_bridge.py` (mới),
`backend/app/agents/runtime/json_output.py` (mới),
`backend/app/core/tool_dispatch.py` (mới), `backend/app/core/feature_flags.py`.

**Tests:** `backend/app/tests/agents/test_deepseek_harness_tool_bridge.py` (mock SDK,
assert 3 nhánh PolicyEngine + `AgentToolCall` được ghi), mở rộng theo pattern
real-Postgres của `test_governance_e2e.py`.

**DEPLOYMENT.md:** thêm mục ranh giới cho Agent Runtime/tool execution tương tự mục
đã có cho OpenSandbox (ADR-EXEC-003).

---

### Slice 2 — Agent Registry (data-driven presets)

**Quyết định thiết kế:** dùng Python dataclass module, **không** dùng YAML. Lý do:
feature flags trong codebase này là DB row vì cần operator bật/tắt runtime; agent
preset ngược lại là *code* cần type-check và validate tại CI (bắt lỗi gõ sai tên tool
ngay khi build) — giống cách `execution/tools.py` đã hardcode `allowed_agent_keys`
bằng Python thay vì file data. YAML sẽ cần thêm một lớp validate riêng mà không có
lợi ích tương ứng ở quy mô hiện tại.

**Files:**
- `backend/app/agents/registry/__init__.py`, `backend/app/agents/registry/presets.py`
  — `@dataclass(frozen=True) class AgentPreset(agent_key, tool_flat_names,
  write_tools, requires_approval, permission_profile)` và `AGENT_PRESETS: dict[str,
  AgentPreset]` cho `chief_of_staff`, `sales_specialist`, `finance_specialist`,
  `data_analyst`, `researcher` (tổng hợp từ literal rải rác hiện có trong
  `execution/tools.py` và các tool khác).
- Sửa `chief_of_staff.py::_resolve_runtime` để đọc `permission_profile` từ preset
  thay vì literal `"chief_of_staff_suggest"` hardcode.
- Slice 1's tool-whitelisting (bước 4) đọc `get_preset(agent_key).tool_flat_names`
  thay vì hardcode.

**Tests:** `backend/app/tests/agents/test_agent_registry.py` — assert mọi
`tool_flat_names` trong mỗi preset resolve được qua `get_tool_by_flat_name` (bắt lỗi
drift khi tool bị đổi tên/xoá).

---

### Slice 3 — Context Builder

**Files:**
- `backend/app/agents/context/__init__.py`,
  `backend/app/agents/context/builder.py::build_agent_context(db, workspace_id,
  company_id) -> AgentContext` (Pydantic model, mỗi section có `data`, `source`,
  `fetched_at`).
- Gọi **trực tiếp các hàm tool đã đăng ký** (`sales_tools.get_pipeline_summary`,
  `finance_tools.get_financial_summary`, `strategy.tools.list_okrs`/`list_projects` —
  đã được `chief_of_staff.py` import sẵn) thay vì gọi lại domain service — giữ một
  nguồn sự thật duy nhất.
- Thay dict tay ở `chief_of_staff.py:175-179` bằng
  `build_agent_context(...).model_dump()`.

**Tests:** `backend/app/tests/agents/test_context_builder.py` — assert có freshness
timestamp, và section thiếu/lỗi không làm sập toàn bộ context (graceful degrade, theo
đúng pattern `.get(..., {})` đã dùng ở `chief_of_staff.py:286`).

---

### Slice 4 — agent_proposals → OKR/12WY bridge

**Model mới** `backend/app/agents/proposals/models.py::AgentProposal` (SnowflakeIDMixin,
theo đúng mẫu `AgentApproval` trong `governance/models.py`): `workspace_id`,
`company_id`, `run_id` (FK `agent_runs.id`), `proposal_type` (`okr_objective` |
`strategy_task`), `payload` (jsonb), `status` (`pending|approved|rejected|applied`),
timestamps.

**Migration:** `backend/alembic/versions/v13_034_agent_proposals.py` (migration mới
nhất hiện tại là `v13_033_execution_coding.py`).

**Service** `backend/app/agents/proposals/service.py::AgentProposalService.apply(db,
workspace_id, proposal_id, reviewed_by)`:
- `proposal_type == "okr_objective"` → gọi thẳng
  `okrs_router.create_okr_objective(workspace_id, OkrObjectiveCreate(**payload),
  member, db)` (`backend/app/modules/strategy/okrs_router.py:192`) — hàm này chỉ dùng
  `workspace_id`/`data`/`db`, tham số `member` không được dùng trong thân hàm nên gọi
  trực tiếp ngoài FastAPI DI là an toàn.
- `proposal_type == "strategy_task"` → gọi `tasks/router.py::create_task(...)`
  (`backend/app/modules/tasks/router.py:84`) — hàm này **có** dùng `member.user_id`
  làm assignee mặc định (dòng 92), nên phải truy vấn `WorkspaceMember` thật theo
  `run.user_id` trước khi gọi, không truyền `None`.
- Tái sử dụng logic tạo OKR/task có sẵn, không viết lại business logic.

**Router:** `backend/app/agents/proposals/router.py` — `POST
/agent-proposals/{id}/apply`, mount trong `main.py` cạnh `mission_control_router`
hiện có (dòng ~63).

**Wiring Chief of Staff:** `_create_approvals_for_action_plan`
(`chief_of_staff.py:313-339`) hiện chỉ tạo `AgentApproval` cho `automation_dispatch`;
thêm nhánh tạo `AgentProposal` khi action item có `proposal_type`.

**Tests:** `backend/app/tests/agents/test_agent_proposal_bridge.py` theo pattern
real-Postgres của `test_governance_e2e.py` (`RUN_DB_INTEGRATION=1`) — tạo proposal →
apply → assert có `OkrObjective`/`Task` row thật, đúng workspace scope.

---

## Ngoài phạm vi slice này (ghi nhận nhưng không làm ngay)

Theo đúng roadmap A.2, các mục sau **không** đưa vào 4 slice trên vì rủi ro/độ ưu tiên
thấp hơn giá trị mang lại ở quy mô hiện tại — chỉ làm khi có nhu cầu thật:
- Đổi tool namespace sang `cosa.<domain>.<verb>` (rủi ro phá `allowed_agent_keys`
  hiện có).
- Bổ sung Marketing tools.
- Mở rộng Automation Catalog quá 2 key hiện có.
- Concurrency/resource controls (`max_concurrent_runs`, subagent depth).
- Observability metrics (Prometheus).
- Flutter Mission Control UI mới (`hologram_hub` hiện tại là hub thoại/chat cũ, không
  liên quan `/api/v1/agents/*` — cần quyết định riêng: mở rộng `hologram_hub` hay tạo
  module mới theo `lib/features/agent_mission_control/` như myiris.md §25.3).
- Licensing/entitlement server (myiris.md §45.3) — ngoài phạm vi agent runtime.

---

## Kiểm chứng (Verification)

Sau mỗi slice:
1. `cd backend && pytest app/tests/agents/ -v` (unit + integration mới).
2. Chạy `test_governance_e2e.py` để đảm bảo không phá luồng governance hiện có.
3. Với Slice 1: bật `FLAG_AGENT_RUNTIME_TOOLS` trên 1 workspace test, gọi
   `/api/v1/agents/mission-control/orchestrate` với câu hỏi cần tool Sales (vd.
   "pipeline hôm nay thế nào") và xác nhận `AgentRunResult.tool_calls` không rỗng + có
   `AgentToolCall` row thật trong DB — bằng chứng gap #1 đã được vá.
4. Với Slice 4: gọi flow tạo proposal → approve → apply, xác nhận OKR/task thật xuất
   hiện đúng workspace, và **company khác không thấy được** (kiểm tra tenancy).
5. Cập nhật `DEPLOYMENT.md` — thêm mục ranh giới runtime cho Agent Runtime (Harness)
   tương tự mục đã có cho OpenSandbox (ADR-EXEC-003), theo đúng yêu cầu CLAUDE.md.
