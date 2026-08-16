# COSA — Kế hoạch tích hợp Master Agentic Runtime & Governance Spec (C1/C2) vào codebase hiện tại

**Trạng thái:** Roadmap tích hợp đã được duyệt
**Nguồn:** Phân tích `C1-COSA_Master_Agentic_Runtime_Governance_Integration_Spec_VI.md` + `C2-COSA_Master_Agentic_Runtime_Governance_Integration_Spec.md` đối chiếu với `backend/app` và `frontend/lib` hiện tại
**Đối tượng:** Claude Code / đội phát triển COSA
**Ngày lập:** 2026-08-16

---

## 0. Context

`C1` (tiếng Việt) và `C2` (tiếng Anh) là **cùng một đặc tả kiến trúc** — COSA Founder Agentic Operating System — mô tả một runtime thống nhất:

```text
Conversation Guard → Intent Router → Verb Router → Domain/Specialist Router
→ Mission Orchestrator → Agent Kernel → Governance Kernel
→ Tool/MCP/n8n → Reality Verifier → Outcome Certificate → Brain
```

Tài liệu này cũng chính là spec đã thay thế 8 file markdown gốc bị xoá ở commit `68b719d` (DSPy, DeepSeek Harness, Harness Engineering, JaredRhod RBAC, Modular Landing CRM, OpenSandbox, V13.1/V13.2) — nghĩa là phần lớn nội dung của C1/C2 **đã được lên kế hoạch và một phần đã triển khai** trong platform upgrade gần nhất.

Khảo sát trực tiếp `backend/app` (đọc code, không suy đoán) cho thấy: **đây không phải là một kiến trúc mới cần xây từ đầu — đây là một bài toán hợp nhất (consolidation)**, đúng tinh thần "Migration method" của `CLAUDE.md` và mục "Migration From Current COSA" của chính spec ("Do not rewrite the whole application"). Khoảng 70% các khối trong sơ đồ target đã tồn tại dưới tên gọi khác, đang chạy production, có test. Phần việc thật sự là:

1. Hợp nhất các hệ thống song song đang trùng lặp.
2. Lấp các khoảng trống thật (budget enforcement, stuck detector, reality verifier).
3. Áp dụng invariant/quality-gate như automated test.
4. Dọn UX Hub/nav theo đúng mẫu "Founder không thấy chi tiết kỹ thuật".

### Quyết định đã chốt

- Phạm vi roadmap: đầy đủ P0 → P5 (không chỉ P0).
- Strategy module: thêm feature flag đúng kiến trúc (`FLAG_STRATEGY_MODULE_V13_2` hoặc tương đương) nhưng **mặc định BẬT** — không phá UX/tab Project Funding hiện tại; Founder/Admin có thể tắt thủ công sau nếu cần.

---

## 1. Bản đồ hiện trạng → spec (bằng chứng từ code, không phải suy đoán)

| Khối trong spec | Đã tồn tại ở đâu | Ghi chú |
|---|---|---|
| Conversation Guard + Intent Router | `modules/chat/conversation_gate.py` (`resolve()` → `GateDecision`) gọi `modules/company_runtime/intent_classifier.py::WorkIntentClassifier` làm lớp nền | Đã đúng invariant "NO INTENT = NO TOOL" — có `SOCIAL_GREETING_PATTERNS` chặn tool trên câu chào |
| Verb Router | Ẩn trong `WorkIntentClassifier` (CHAT/QUICK_TASK/COMPANY_WORK/CYCLE_CHANGE/STRATEGIC/APPROVAL) + `AgentPlanStep.policy_level` (L0_READ…L3_EXECUTE) | Chưa map trực tiếp sang verb chuẩn CONVERSE/SHAPE/INVESTIGATE/JUDGE/EXECUTE/FINISH/LEARN của spec |
| Specialist Router / Domain Agent | `agents/domains/{sales,finance,legal,marketing,learning}/{reasoning,research,data,action,evaluation,communication}.py` | Đã verb-decomposed gần đúng spec §7/§57 |
| Agent Registry | `agents/registry/presets.py` (`AGENT_PRESETS`: chief_of_staff, sales_specialist, finance_specialist, data_analyst, researcher, coding_agent) | Tương đương Agent Contract §8, thiếu YAML hoá + versioning |
| Mission Orchestrator | `agents/orchestration/chief_of_staff.py` (`ChiefOfStaffOrchestrator.orchestrate`) | Có goal→delegate→synthesize→action_plan→approval, nhưng **không dùng bảng `outcomes`** |
| Mission Ledger #1 | `modules/outcomes/models.py`: `Outcome, OutcomeRun, RunStep, RunEvent, Artifact` — được ~15 module khác dùng (company_runtime, tasks, tech, devices, strategy, ai_team...) | Đây là ledger đang hoạt động rộng nhất |
| Mission Ledger #2 | `agents/control_plane/models.py`: `AgentGoal→AgentPlan→AgentPlanStep`; `agents/governance/models.py`: `AgentRun, AgentEventRecord, AgentToolCall, AgentApproval` | Dùng bởi `chief_of_staff.py` |
| Governance (Policy/Approval) | `agents/governance/policy_engine.py` (`PolicyEngine.evaluate` → ALLOW/DENY/REQUIRE_APPROVAL theo L0–L3), `approval_service.py`, `states.py` | Rất sát spec §36/§37, chỉ thiếu facade gộp chung |
| Secret Broker | `agents/execution/credential_broker.py::CredentialBroker` | Đúng mẫu §44/§39 |
| Tool Registry | `core/tool_registry.py` (`ToolSpec`, `@register`, risk_level/permission_level/requires_approval) | Đúng mẫu §34/§26, thiếu 1-2 field (`mutating`, `external`) |
| Event Bus | 3 hệ song song: `core/events.py::EventBroker` (Postgres LISTEN/NOTIFY, cross-process), `modules/chat/chat_stream_bus.py` (chat SSE), `agents/orchestration/mission_control_bus.py` (**in-memory `asyncio.Queue`, KHÔNG cross-process**) | `mission_control_bus` sẽ mất event nếu chạy nhiều worker — rủi ro thật |
| n8n / Automation | `automations/runtime/adapters/n8n.py` + `automations/runtime/manager.py` | Đúng mẫu §40/§66 |
| DSPy / Prompt optimization | `ai/programs/`, `ai/evaluation/evaluators.py`, `ai/optimization/artifacts.py`, đã có test `test_dspy_*` | Nền cho P5 đã có |
| Feature Flags | `core/feature_flags.py` (~60 flag `FLAG_*_V13...`), `modules/platform/models.py::FeatureFlag`, gate trên `dashboard_view.dart` nav qua `flagKey` | Đúng mẫu §50, Strategy nav (index 3) hiện **không có flagKey** |
| Hologram Hub / CEO Command Center | `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart` đã có Company Pulse, TodayPriorityList, ActiveMissionsTracker, QuickApprovalQueue, HubChatPanel, KpiStrip | Đã đúng mẫu §53, chỉ cần nối vào Mission Ledger hợp nhất |
| Reality Verifier / Outcome Certificate / Evidence Manager | **Không tồn tại.** `agents/learning/verifier.py::Verifier` chỉ so `expected` vs `actual` dict cho learning candidate, không verify trạng thái hệ thống thật | **Gap thật, cần code mới** |
| Mission Budget enforcement | **Không tồn tại.** `estimated_cost`/`input_tokens` được ghi nhận nhưng không có `max_cost_usd`/`max_steps`/`BUDGET_EXCEEDED` ở đâu cả (grep toàn repo = 0 kết quả) | **Gap thật** |
| Stuck Detector | **Không tồn tại** (grep "stuck" = 0 kết quả ngoài test) | **Gap thật** |

---

## 2. P0 — Runtime Foundation (chi tiết, có thể thực thi ngay)

### P0.1 Đóng băng tăng trưởng bề mặt

Tạm dừng thêm module/agent/dashboard card mới cho đến khi P0.2–P0.7 xong. `policy_funding` (đang uncommitted) được coi là ngoại lệ đã lỡ scaffold — cho hoàn thiện nốt, không mở thêm vertical mới sau đó.

### P0.2 Hợp nhất Conversation Guard + Intent + Verb Router

- Chọn `modules/chat/conversation_gate.py` làm **canonical single source** (đã wired vào `chat_execution_service.py`, đã có test, đã đúng invariant NO INTENT = NO TOOL).
- `agents/control_plane/intent.py::IntentClassifier` (CHAT/QUERY/COMMAND/GOAL/EVENT): audit xem còn được gọi từ đâu ngoài `conversation_gate`/`WorkIntentClassifier`. Nếu không có caller sản xuất nào khác — xoá hoặc gộp logic hữu ích (nếu có) vào `conversation_gate.py`, không giữ 2 lớp phân loại độc lập.
- Thêm một tầng map tường minh `GateIntent → canonical verb` (CONVERSE/SHAPE/INVESTIGATE/JUDGE/EXECUTE/FINISH/LEARN) ngay trong `conversation_gate.py` hoặc file mới `modules/chat/verb_router.py`, để mọi nơi downstream (orchestrator, policy engine, mission ledger) dùng chung 7 verb chuẩn thay vì tái dùng `GateIntent`/`WorkIntentClassifier` intent string rải rác.
- Test bắt buộc (theo mục "Mandatory Acceptance Tests" của spec): `"chào"` → verb CONVERSE, `should_route=False`, không tool nào được gọi, không mission nào được tạo.

### P0.3 Hợp nhất Mission Ledger (việc rủi ro/giá trị cao nhất)

Không viết lại `outcomes/*` (15 module phụ thuộc) và không viết lại `agents/control_plane` + `agents/governance` (đã có test, đã chạy production qua `chief_of_staff.py`). Thay vào đó:

- Thêm cột cầu nối nullable: `AgentRun.outcome_run_id` (FK → `outcome_runs.id`) và ngược lại `OutcomeRun.agent_run_id` (FK → `agent_runs.id`) để một mission có thể được truy vấn từ cả hai phía mà không cần merge bảng.
- `ChiefOfStaffOrchestrator.orchestrate()` (`agents/orchestration/chief_of_staff.py`): khi tạo `AgentRun`, tạo song song một `Outcome`/`OutcomeRun` tương ứng (hoặc field `mission_type`/`title` nếu chưa có) — để mọi mission, dù khởi tạo từ orchestrator agent hay từ company_runtime, đều xuất hiện thống nhất trong `outcomes`/`outcome_runs` — đây chính là "Mission Ledger" nhìn từ phía UI (Hologram Hub, Mission Inspector).
- Coi `RunEvent` (`outcomes` module) + `AgentEventRecord` (`agents/governance`) là 2 luồng event bổ sung nhau (một cho work-item lifecycle, một cho agent execution chi tiết) — không hợp nhất bảng, nhưng cả hai phải publish qua cùng một Event Bus (xem P0.4).
- Không tạo bảng `missions`, `mission_steps`, `mission_events` mới như literal trong spec — đó là trùng lặp không cần thiết với những gì đã có.

### P0.4 Event Bus hợp nhất

- Chọn `core/events.py::EventBroker` (Postgres LISTEN/NOTIFY, cross-process) làm canonical, theo đúng mẫu đã dùng cho `modules/chat/chat_stream_bus.py`.
- Sửa `agents/orchestration/mission_control_bus.py::MissionControlBus.emit_event` để publish qua `EventBroker` thay vì chỉ giữ trong `asyncio.Queue` nội bộ process — nếu không, mission events sẽ **không tới được** client khi backend chạy nhiều worker (`worker_main.py` + web process tách biệt là kịch bản hiện tại). Giữ nguyên interface `subscribe()`/`emit_event()` để không phải sửa call site trong `chief_of_staff.py`.
- Chuẩn hoá event type theo danh sách spec mục "Recommended events" (`MISSION_STARTED`, `MISSION_WAITING_APPROVAL`, `TOOL_REQUESTED`, `VERIFICATION_PASSED`...) làm alias/constant, map từ các `event_type` string tự do hiện có (`mission_started`, `subagent_delegated`...).

### P0.5 Governance Kernel facade + Tool Sentinel

- Tạo `agents/governance/kernel.py` là facade mỏng gộp `PolicyEngine.evaluate` + `ApprovalService` + `CredentialBroker` + audit (ghi `AgentEventRecord`/`AgentToolCall`) thành một entrypoint duy nhất `GovernanceKernel.check_tool_call(...)` mà mọi tool-dispatch path (`core/tool_dispatch.py`) phải đi qua trước khi gọi `ToolSpec.callable`. Không viết lại policy/approval/secret-broker logic đã có — chỉ gộp lại thành một cửa vào.
- Thêm 2 field còn thiếu vào `ToolSpec` (`core/tool_registry.py`): `mutating: bool` và `external: bool` — cần cho Reality Verifier (P0.7) biết tool nào cần verify trạng thái thật, và cho `policy.external_action` kiểu spec mục 40/41.
- Inspector chain: `PermissionInspector`/`ScopeInspector` đã có (qua `PolicyEngine`); `SecretInspector` đã có (không đưa secret vào context — `CredentialBroker`); còn thiếu `EgressInspector`, `InjectionInspector`, `RepetitionInspector` — có thể gộp `RepetitionInspector` chung với Stuck Detector (P0.6) thay vì viết riêng.

### P0.6 Mission Budget + Stuck Detector (gap thật, code mới)

- `agents/governance/budget.py` (mới): `MissionBudget` dataclass (`max_steps`, `max_wall_time_seconds`, `max_api_cost_usd`, `max_tool_calls`) + `BudgetTracker.check(agent_run)` đọc tổng `estimated_cost`/số `AgentToolCall` hiện có cho `run_id`, trả `BUDGET_EXCEEDED` nếu vượt. Gọi trong vòng lặp của `chief_of_staff.py` và bất kỳ orchestrator loop nào khác trước mỗi bước.
- `agents/governance/stuck_detector.py` (mới): phát hiện `SAME_ACTION_LOOP`/`SAME_ERROR_LOOP`/`TOOL_PING_PONG` bằng cách quét `AgentToolCall` gần nhất theo `run_id` (đã có đủ dữ liệu: `tool_name`, `status`, `started_at`). Policy: lặp 2 → log observe, lặp 3 → cảnh báo + đổi chiến lược, lặp 5 → chuyển `AgentRun.status = "failed"` với `error_code="STUCK_LOOP"`.
- Thêm cột `budget_jsonb` vào `AgentRun` (hoặc bảng `agent_run_budgets` riêng nếu muốn tách theo mẫu spec `mission_budgets`) để lưu ngưỡng đã cấu hình cho từng run.

### P0.7 Evidence Manager + Reality Verifier + Outcome Certificate (gap thật, code mới)

- Mở rộng `modules/outcomes/models.py`: thêm `verification_status` (`VERIFIED|PARTIAL|FAILED|UNKNOWN`) và `verification_jsonb` vào `OutcomeRun` (không cần bảng riêng `mission_verifications` nếu volume thấp — additive column rẻ hơn).
- `agents/verification/reality_verifier.py` (mới, theo domain, tái dùng session Postgres/service đã có):
  - CRM: sau `crm.upsert_contact` → query lại bằng `modules/sales` service để xác nhận row tồn tại đúng field.
  - Email: sau `email.send` → xác nhận có provider message ID trả về (không chỉ "success" string).
  - Deploy: xác nhận commit hash + HTTP endpoint (tái dùng `modules/platform/deployment_models.py::Deployment` đã có).
  - Finance: xác nhận ledger state qua `modules/finance`/`tt58_engine.py` invariants.
- `Artifact.type = "external_action_receipt"` (đã có sẵn trong enum comment của `outcomes/models.py:83`) chính là chỗ lưu Outcome Certificate — không cần bảng mới, ghi JSON certificate (`verdict`, `evidence`, `unresolved`) vào `Artifact` gắn với `outcome_id`.
- Test bắt buộc theo spec: tool trả "success" nhưng DB không đổi ⇒ `verification_status` phải là `FAILED`/`UNKNOWN`, không bao giờ `VERIFIED`.

### P0.8 Migration & Test

- Mọi model mới/cột mới phải add vào `backend/app/db/base.py` để Alembic thấy được (đúng rule `CLAUDE.md`), dùng `SnowflakeIDMixin`/`generate_snowflake_id()` cho khoá chính mới.
- Test-first theo `backend/app/tests/`: viết test cho từng "Mandatory Acceptance Test" trong spec (chào → CONVERSE không tool; sales prospecting → INVESTIGATE background; gửi email → WAITING_APPROVAL; verify giả lập DB không đổi → FAILED không VERIFIED) trước khi sửa code, đúng "test-first development" đã ghi trong `CLAUDE.md`.

---

## 3. P1 — Founder Command Center

Phần lớn UI đã tồn tại (`hologram_hub_view.dart`), việc còn lại chủ yếu là **nối dây**, không phải xây mới:

- `ActiveMissionsTracker` (frontend) đọc dữ liệu qua API mới cần thêm: `GET /api/v1/missions` tổng hợp từ `outcomes`+`agent_runs` đã hợp nhất ở P0.3, thay vì chỉ đọc `outcomes` như hiện tại.
- Mission Inspector (mở rộng): hiển thị Budget (`$0.12/$0.30`), Loop Health, Evidence count, Verification status — lấy trực tiếp từ các trường mới ở P0.6/P0.7.
- Thêm feature flag mới cho Strategy: `FLAG_STRATEGY_MODULE_V13_2 = "strategy_module"` trong `core/feature_flags.py`, set **default `enabled=true`** (theo quyết định đã chốt), gắn `flagKey: 'strategy_module'` vào `_NavItem` "Chiến lược" (index 3) trong `dashboard_view.dart` — cho phép Admin tắt thủ công qua Feature Flags admin UI đã có sẵn, không ẩn ngay lập tức.
- `QuickApprovalQueue`/`HubChatPanel` giữ nguyên, chỉ đổi nguồn event sang Event Bus hợp nhất (P0.4).

## 4. P2 — Revenue Engine end-to-end

`modules/sales` (CRM core) + `revenue_router.py`/`revenue_engine_service.py` + `agents/domains/sales/*` đã phủ gần hết chuỗi Market Research→ICP→Prospect→Qualification→CRM. Việc còn thiếu để "end-to-end" đúng nghĩa spec:

- Outreach Draft → Governance → Approval → Send → Outbox: kiểm tra `modules/integrations/models.py::Outbox`/`EmailApproval` đã có model, cần audit xem `agents/domains/sales/communication.py` đã thật sự đi qua `GovernanceKernel` (P0.5) trước khi gọi provider gửi email hay chưa; nếu chưa, đây là vi phạm invariant "NO EXTERNAL ACTION WITHOUT GOVERNANCE" cần vá ngay.
- Gắn Reality Verifier (P0.7) cho `email.send` và `crm.upsert_lead` trong luồng sales — đây chính là vertical chứng minh toàn bộ kiến trúc theo spec mục 56.

## 5. P3 — Automation & Channels

- `automations/runtime/adapters/n8n.py` đã đúng vị trí (n8n = executor, không phải "brain"). Việc cần làm: đảm bảo **mọi** dispatch tới `N8nAdapter` đi qua `GovernanceKernel.check_tool_call` trước — audit các call site hiện có (`agents/execution/n8n_bridge.py`) để chắc không có đường tắt bỏ qua approval.
- Ưu tiên kênh theo đúng thứ tự spec: Telegram → Email → Zalo (Zalo dùng connector không chính thức, không nên là kênh critical duy nhất) — kiểm tra `modules/integrations/models.py::ZaloQrSession` hiện có redundancy fallback chưa.

## 6. P4 — Company Operations

- Finance Lite/TT58 (`modules/finance/tt58_router.py`, `tt58_engine.py`), Legal (`modules/legal`) đã tồn tại và khớp mẫu spec §59/§60 khá sát — không cần xây lại.
- Việc cần thêm: Quality Gate cross-cutting (§45) — hiện mỗi domain tự judge theo cách riêng; nên có 1 interface chung `agents/governance/quality_gate.py` mà `agents/domains/{finance,legal,sales,marketing}/evaluation.py` implement, để Mission không thể FINISH nếu Quality Gate fail — tái dùng logic evaluation.py sẵn có, chỉ thêm 1 lớp interface thống nhất, không viết lại từng domain.
- Gắn Reality Verifier cho action tài chính rủi ro cao (đúng invariant "AI must not autonomously... finalize high-risk entries").

## 7. P5 — Intelligence & Self-improvement

- `ai/programs/`, `ai/evaluation/evaluators.py`, `ai/optimization/artifacts.py` đã là nền DSPy — chỉ cần thêm **Prompt Registry chính thức có version** (`prompts/cosa/*.md` theo mẫu spec mục 30, hiện `prompts/cosa/` đã tồn tại nhưng cần audit xem có version field/eval-gate trước khi promote hay chưa) và cấm DSPy tự động promote production prompt (invariant "NO AGENT SELF-PROMOTION OF PROMPTS/SKILLS") — kiểm tra `ai/optimization/artifacts.py` hiện có gate Admin-approval hay tự động ghi đè.
- Skill Registry lifecycle (`candidate → evaluation → admin approval → active → deprecated`): kiểm tra `modules/marketing/models.py::SkillRegistry` (đã tồn tại cho marketing) có thể tổng quát hoá thành Skill Registry toàn hệ thống, dùng chung cho mọi domain thay vì chỉ marketing.
- Technology Radar (mục 49): trang Admin mới, đơn giản (bảng YAML/DB `status: ADOPT/TRIAL/ASSESS/WATCH/REJECT`) — việc nhỏ, làm sau cùng.

---

## 8. Invariant cần biến thành automated test (áp dụng xuyên suốt P0–P5)

Danh sách "Architectural Invariants" (mục cuối C2) nên có 1 file test riêng `backend/app/tests/test_architectural_invariants.py`, mỗi invariant 1 test, chạy trong CI:

```text
NO INTENT = NO TOOL
NO EXTERNAL ACTION WITHOUT GOVERNANCE
NO HIGH-RISK ACTION WITHOUT POLICY
NO APPROVAL WAIT WITHOUT TIMEOUT
NO VERIFIED STATUS WITHOUT REALITY CHECK
NO SECRET IN MODEL CONTEXT
NO AGENT SELF-PROMOTION OF PROMPTS/SKILLS
NO UNBOUNDED WORKER SPAWNING
NO UNBOUNDED COST
NO HIDDEN STATE TRANSITION
NO FINISH WITHOUT EVIDENCE WHEN REQUIRED
```

---

## 9. Thứ tự thực hiện đề xuất

Bám sát mục "Recommended Immediate Implementation Order" của C2, đã điều chỉnh theo hiện trạng:

1. Audit call site còn dùng `agents/control_plane/intent.py` → quyết định xoá hay gộp (P0.2)
2. Thêm mapping verb chuẩn trong `conversation_gate.py` (P0.2)
3. Thêm cột cầu nối `AgentRun.outcome_run_id` / `OutcomeRun.agent_run_id`, sửa `chief_of_staff.py` tạo cả hai (P0.3)
4. Sửa `mission_control_bus.py` publish qua `EventBroker` (P0.4)
5. Viết `agents/governance/kernel.py` facade (P0.5)
6. Thêm `mutating`/`external` vào `ToolSpec` (P0.5)
7. Viết `agents/governance/budget.py` + `stuck_detector.py`, wire vào `chief_of_staff.py` (P0.6)
8. Viết `agents/verification/reality_verifier.py`, mở rộng `OutcomeRun.verification_status` (P0.7)
9. Test invariant tổng hợp (`test_architectural_invariants.py`)
10. P1: API `GET /api/v1/missions` hợp nhất, feature flag Strategy (default ON), Mission Inspector mở rộng
11. P2: audit + vá đường tắt approval trong sales outreach, gắn Reality Verifier
12. P3–P5: theo thứ tự liệt kê ở trên, sau khi P0–P2 ổn định

---

## 10. Xác minh

- Backend: `cd backend && pytest app/tests/test_architectural_invariants.py app/tests/test_dspy_*.py -v` sau mỗi mốc P0; chạy toàn bộ `pytest` trước khi coi P0 "done".
- Alembic: `alembic upgrade head` chạy sạch sau khi thêm cột/bảng mới vào `db/base.py`.
- Frontend: `flutter analyze` + `flutter test` cho các file bị đổi (`dashboard_view.dart`, `hologram_hub_view.dart`); test thủ công trên `flutter run` — gõ "chào" trong chat phải không kích hoạt tool nào (kiểm tra qua Mission Inspector là không có `AgentRun`/`Outcome` nào được tạo).
- Kiểm tra rule `CLAUDE.md`: `rg -n --glob '!build/**' '(:8888|backend/server|javis/|web_socket_channel)' frontend/lib` phải rỗng sau mọi thay đổi frontend.

---

**Hết tài liệu.**
