# COSA Agent Governance & Chief of Staff — Realization Plan

> **Source spec:** `COSA_DeepSeek_Harness_Integration_v13.1_v13.2(2).md` (repo root).
> **Source plan:** `docs/architecture/COSA_AGENT_AUTOMATION_RUNTIME_ADJUSTMENT_PLAN.md` (Phase 0-7
> roadmap; Phase 0/1 đã hoàn thiện và verify live thật, Phase 2 (Sales/Finance POC) đã sửa lỗi
> bịa số liệu).
> **Trạng thái:** Định hướng/roadmap cho phần **"chạy thật"** — tức là làm cho code đã tồn tại
> (viết bởi một tool khác, claim "complete Phases 0-6") thực sự hoạt động đúng như spec mô tả,
> không phải bản demo tĩnh.
> **Audit date:** 2026-08-14, re-verified cùng ngày trước khi viết plan này.

---

## Vì sao cần plan này

Audit trực tiếp code (không suy đoán từ commit message) phát hiện: khung sườn Phase 3-5
(governance, Chief of Staff, automation) **tồn tại và bám khá sát shape của spec**, nhưng có
ba lỗ hổng khiến nó không "chạy thật":

1. **Bảng governance/automation thiếu migration** — đã sửa (`v13_027`, commit `47bec64`).
2. **n8n callback nhận update dù signature sai/thiếu** — đã sửa (401 + replay window, commit
   `47bec64`).
3. **Ba lỗ hổng còn lại, plan này giải quyết:**
   - `ChiefOfStaffOrchestrator.orchestrate()` không gọi `AgentRuntime`/Harness ở đâu cả —
     import `agent_runtime_manager` nhưng chưa từng gọi. Diagnosis/priorities/action_plan là
     chuỗi tiếng Việt viết cứng, không phụ thuộc `goal` truyền vào.
   - `PolicyEngine.evaluate()` và `ApprovalService.create_approval()` không được gọi từ bất kỳ
     đường thực thi tool thật nào — chỉ tồn tại trong test và trong router list/approve/reject.
   - `POST /api/v1/automations/{key}/execute` nhận `approval_id` nhưng không verify nó thực sự
     `approved` trước khi dispatch ra n8n thật.

Nguyên nhân gốc chung của cả ba: **thiếu một "Tool Execution Gateway"** — điểm nghẽn duy nhất
nơi "agent muốn gọi tool X" phải đi qua trước khi tool X thực sự chạy. Đây chính là ô
"COSA Tool Gateway → Policy Engine → ALLOW/REQUIRE APPROVAL" ở sơ đồ §15 của spec, và nó chưa
tồn tại trong code — mọi nơi (Chief of Staff, sales_tools test) đang gọi thẳng Python function.

---

## Quyết định thiết kế cần chốt trước khi code

### 1. Chief of Staff lấy "reasoning" từ đâu

Spec §9 mô tả Chief of Staff như một agent thật: đọc goal, delegate, tổng hợp, phát hiện xung
đột. Có hai cách hợp lý để hiện thực hoá, khác nhau về khối lượng việc:

**Approach A — Full MCP Gateway (đúng nguyên văn spec §11/§12).**
Build một MCP server thật expose `tool_registry.py` ToolSpecs cho DeepSeek Harness subprocess
gọi trực tiếp (qua Cordis config `cordis.yml` trỏ vào MCP server này). Harness tự quyết định
gọi tool nào, COSA không lập trình sẵn trình tự delegate. Đây là cách "đúng" nhất theo kiến
trúc đích, nhưng là một mặt tích hợp hoàn toàn mới (MCP server, Cordis composition, xác minh
Harness thật sự gọi được tool qua đó) — rủi ro/khối lượng việc lớn, chưa có gì trong codebase
làm nền.

**Approach B — COSA điều phối, Harness/ModelGateway chỉ sinh văn bản (Recommended).**
Giữ nguyên việc COSA (Python) gọi trực tiếp `get_pipeline_summary`/`get_financial_summary` để
lấy dữ liệu thật (đã đúng, đã tenant-scoped) — đây **không phải** vấn đề, vấn đề là bước tổng
hợp/diagnosis phía sau bị viết cứng. Thay bước đó bằng một lời gọi thật tới `AgentRuntimeManager`
(hoặc thẳng `ModelGateway.get_client(PROFILE_BUSINESS_DEEP)`) với dữ liệu Sales/Finance thật làm
context, yêu cầu structured output theo schema §24 của spec. Không cần MCP server mới, không
cần Harness tự gọi tool — COSA vẫn là nơi duy nhất chạm business data (đúng nguyên tắc
"Agents may propose. COSA governs."). Đây là phần mở rộng tự nhiên của Phase 1 (AgentRuntime)
đã có, không phải execution engine thứ hai.

Approach A vẫn là điểm đến đúng đắn về lâu dài (đúng tinh thần "MCP Gateway" của spec), nhưng
nên là một phase riêng SAU KHI Approach B đã chứng minh giá trị — đúng thứ tự adjustment plan
gốc đã đề ra ("Phase 4 sau khi Sales + Finance agent đã qua eval ổn định").

**Quyết định plan này áp dụng: Approach B.** Ghi lại đây để phiên sau không làm lại quyết định.

### 2. PolicyEngine gate ở đâu

Vì Approach B không có Harness tự gọi tool, không cần một Tool Execution Gateway tổng quát
ngay. Chỉ cần: bất kỳ chỗ nào một *write* tool hoặc automation risk >= medium sắp thực thi,
phải đi qua `PolicyEngine.evaluate()` trước, và nếu kết quả là `REQUIRE_APPROVAL`, phải gọi
`ApprovalService.create_approval()` thật (ghi DB) thay vì trả một dict trang trí.

Hiện tại Chief of Staff chỉ **đọc** (`get_pipeline_summary`/`get_financial_summary` đều
read-only) — nên chưa có write nào cần chặn. Việc "gate" thật sự cần thiết đầu tiên là ở
`automations/execute` (mục 3 dưới), vì đó là nơi duy nhất hiện có thể gây side-effect thật ra
ngoài (n8n → email/Telegram/CRM).

### 3. Automation approval enforcement cần data thật

`AutomationDefinition.approval_mode` chỉ có ý nghĩa nếu bảng có dữ liệu — hiện DB trống
(catalog chỉ là fallback list cứng trong response, không phải nguồn thật). Cần seed
`automation_definitions` (migration additive) trước khi enforcement có gì để đọc.

---

## Phased implementation

Mỗi phase = một PR nhỏ, test-first, exit criteria rõ, rollback bằng cách không set config mới.

### Step 1 — Seed automation_definitions catalog

- Migration additive `v13_028_automation_catalog_seed.py`: insert các dòng
  `system.telegram_notification` (risk_level=low, approval_mode=none),
  `sales.followup_email` (risk_level=medium, approval_mode=required), theo đúng danh sách
  §74/§87 của spec — chỉ 2 dòng an toàn nhất trước, không seed finance/legal.
- Xoá fallback hardcode trong `automations/router.py::list_automation_definitions` sau khi có
  data thật (không giữ hai nguồn sự thật song song).
- Test: `GET /definitions` trả đúng 2 automation từ DB thật, không còn nhánh fallback.

### Step 2 — Gate `/automations/{key}/execute` bằng approval thật

Trong `backend/app/automations/router.py::execute_automation`:

1. Query `AutomationDefinition` theo `automation_key`. Nếu không tồn tại → 404 (không còn
   default-allow âm thầm).
2. Nếu `approval_mode != "none"`:
   - Bắt buộc `payload.approval_id` khác None.
   - Query `AgentApproval` scoped `(id=approval_id, workspace_id=current_member.workspace_id)`.
   - Approval phải tồn tại, `status == "approved"`, `tool_name`/`action_type` khớp
     `automation_key` (chống dùng nhầm approval của hành động khác), và chưa bị dùng lần nào
     (thêm cột `consumed_at`/kiểm tra qua `AutomationRun.approval_id` đã tồn tại chưa — chống
     replay một approval cho nhiều lần execute, đúng "idempotency" §49).
   - Nếu bất kỳ điều kiện nào fail → 403 với message rõ lý do.
3. Nếu pass, mới tạo `AutomationRun` và dispatch như hiện tại.

- Test: execute automation `approval_mode=required` không kèm `approval_id` → 403; kèm
  `approval_id` chưa approved → 403; kèm approval đã `approved` → 200 và thực sự dispatch;
  dùng lại approval đã dùng → 403 (chống double-execute).

### Step 3 — Chief of Staff dùng AgentRuntime thật cho bước tổng hợp (Approach B)

Trong `backend/app/agents/orchestration/chief_of_staff.py`:

1. Giữ nguyên bước gọi `get_pipeline_summary`/`get_financial_summary` (đã đúng).
2. Thay khối `diagnosis`/`priorities`/`action_plan` viết cứng bằng một lời gọi thật:
   - Dựng `AgentRunRequest` với `agent_key="chief_of_staff"`, `task=goal` (câu hỏi Founder thật),
     `context={"sales_snapshot": sales_data, "finance_snapshot": fin_data}`.
   - Gọi qua `agent_runtime_manager.get_runtime(...)` (mock trong test/CI mặc định, có thể chọn
     `deepseek_harness` qua flag `FLAG_AGENT_RUNTIME_DEEPSEEK` giống Phase 1) — **không** tự
     tạo runtime mới, dùng lại `AgentRuntimeManager` đã có.
   - Parse `structured_output` theo schema tối giản (`diagnosis`, `priorities: list[str]`,
     `action_plan: list[{week, tactic, owner}]`) — nếu invalid, áp dụng đúng §24: một lần
     repair, nếu vẫn fail thì trả `status="partial"` kèm raw text, không tự bịa dữ liệu như bản
     cũ đang làm.
3. `required_approvals`: với mỗi action trong `action_plan` có risk-worthy side effect
   (heuristic tối giản: owner khác `chief_of_staff` và tactic thuộc domain có write tool), gọi
   `ApprovalService.create_approval()` thật thay vì chỉ trả dict — để nó thực sự xuất hiện ở
   `GET /api/v1/agents/approvals`.
4. Ghi `AgentRun`/`AgentEventRecord` thật vào 2 bảng đã có migration ở Step trước của
   adjustment plan gốc (`agent_runs`, `agent_events`) thay vì chỉ emit qua
   `mission_control_bus` (SSE) — SSE là transport hiển thị real-time, không phải audit
   source; cần cả hai theo đúng phân biệt §16 của spec ("Harness session vs COSA Memory/Audit").

- Test: `orchestrate()` với `MockRuntime` (flag mặc định) trả `diagnosis` phụ thuộc thực sự vào
  `goal` (đổi goal → đổi output, chứng minh không còn hardcode); với goal chứa từ khoá
  risk-worthy → có ít nhất 1 `AgentApproval` thật được tạo trong DB; `agent_runs`/`agent_events`
  có bản ghi khớp `mission_id`.

### Step 4 — Hoàn thiện N8nAdapter (mức tối thiểu, không mở rộng scope)

- `get_status`: gọi thật `GET {base_url}/api/v1/executions/{id}` nếu `api_key` có cấu hình,
  map response thật thay vì luôn trả `"running"`. Nếu không có `api_key`, giữ nguyên trả
  `"running"` kèm `details` nói rõ "status polling requires n8n API key" — không giả vờ biết.
- `cancel`: gọi thật endpoint stop execution của n8n nếu có `api_key`; nếu không, raise lỗi rõ
  ràng thay vì `pass` âm thầm (một `cancel()` không làm gì mà không báo lỗi là nguy hiểm hơn
  một `cancel()` báo "not supported").

### Step 5 — Regression cho toàn bộ chuỗi Governance E2E

Một test tích hợp duy nhất đi hết chuỗi thật (Postgres thật, không mock DB):
`ChiefOfStaffOrchestrator.orchestrate()` → sinh `required_approvals` thật →
`ApprovalService.approve()` → `POST /automations/{key}/execute` với `approval_id` đó → 200.
Test này là exit criteria chính của cả plan — nếu nó pass, "chạy thật" mới thực sự đúng nghĩa.

---

## Không làm trong plan này (out of scope, cần plan riêng)

- Approach A (MCP Gateway thật cho Harness tự gọi tool) — theo dõi như một phase riêng sau khi
  Step 1-5 ở trên chạy ổn định, đúng khuyến nghị "Phase 4 sau khi Sales+Finance eval ổn định"
  của adjustment plan gốc.
- Marketing/Legal/Learning specialist agent — chưa có tool tương ứng, ngoài phạm vi.
- Licensing/entitlement (Phase 7 gốc) — vẫn ngoài phạm vi, cần spec sản phẩm/pháp lý riêng.
- Flutter Mission Control UI — cần normalized event backend ổn định trước (đã có
  `mission_control_bus` SSE nhưng chưa audit kỹ phần Flutter tiêu thụ nó).
- `hologram_hub`/`hub_chat_panel.dart` đang được một tool khác chỉnh sửa song song, không thuộc
  phạm vi backend agent/automation này.

---

## Guardrails áp dụng lại từ CLAUDE.md + spec

- Không tạo Tool Execution Gateway tổng quát nếu Approach B không cần nó — tránh xây execution
  engine thứ hai trước khi có nhu cầu thật.
- Mọi write tool/automation mới mặc định `approval_required=true` cho tới khi có policy cụ thể.
- `workspace_id` luôn inject từ `current_member`, không tin giá trị client truyền (Step 2, 3).
- Approval không được dùng lại hai lần cho hai lần execute khác nhau (Step 2 idempotency).
- Migration additive-only, Snowflake ID, backward-safe nếu flag tắt.

---

## Exit criteria tổng thể

- [ ] `automation_definitions` có data thật, `/definitions` không còn fallback cứng.
- [ ] `/automations/{key}/execute` từ chối khi thiếu/sai/tái sử dụng approval.
- [ ] `ChiefOfStaffOrchestrator.orchestrate()` với hai `goal` khác nhau cho `diagnosis` khác
      nhau (chứng minh không hardcode).
- [ ] Ít nhất một nhánh action_plan tạo `AgentApproval` thật, thấy được ở
      `GET /api/v1/agents/approvals`.
- [ ] `agent_runs`/`agent_events` có bản ghi thật sau mỗi lần orchestrate.
- [ ] Test E2E Step 5 pass với Postgres thật.
- [ ] Toàn bộ test suite hiện có (583 test) vẫn xanh.
