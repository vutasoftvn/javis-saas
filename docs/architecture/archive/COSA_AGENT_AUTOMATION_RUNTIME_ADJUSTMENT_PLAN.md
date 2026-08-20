# COSA Agent Runtime & Automation Runtime — Adjustment Plan

> **Source spec:** `COSA_DeepSeek_Harness_Integration_v13.1_v13.2(2).md` (repo root,
> ~4850 dòng). Spec đề xuất tích hợp DeepSeek Harness làm **Agent Runtime** và n8n làm
> **Automation Runtime** vào COSA v13.1/v13.2, cộng một phần bổ sung (BỔ SUNG) về
> Companion/Realtime Voice + ModelGateway. Spec tự khẳng định: không tạo product
> version mới, mọi mốc H0–H7/R0–R12 chỉ là technical phase trên nền v13.1/v13.2.
>
> **Audit date:** 2026-08-14. Plan này được viết sau khi đọc toàn bộ spec gốc và đối
> chiếu trực tiếp với `backend/app/`, `frontend/lib/`, `services/realtime_agent/`,
> theo đúng cách các plan khác trong thư mục này (`MCOSA_V13_IMPLEMENTATION_PLAN.md`,
> `COSA_V13_1_COMPANY_RUNTIME_IMPLEMENTATION_PLAN.md`,
> `COSA_V13_2_REVENUE_SALES_IMPLEMENTATION_PLAN.md`) đã đối chiếu spec của chúng.
>
> **Trạng thái:** Định hướng/roadmap. Phase 0 và Phase 1 đủ chi tiết để bắt tay code
> ngay; Phase 2 trở đi cần một plan/design pass riêng trước khi viết code, theo đúng
> "Migration method" của `CLAUDE.md` và chỉ thị #14 của spec gốc ("Tạo tests trước khi
> bật write-capability").

---

## Context

Spec gốc chia làm ba lớp:

1. **Agent Runtime** — DeepSeek Harness xử lý reasoning/planning/subagent/tool
   lifecycle cho các "business agent" (Chief of Staff, Sales, Finance, Marketing,
   Legal, Learning), đứng sau một abstraction `AgentRuntime` để có thể thay thế.
2. **Automation Runtime** — n8n xử lý trigger/schedule/webhook/external SaaS
   integration, đứng sau một abstraction `AutomationProvider`, chạy trên hạ tầng
   khách hàng tự quản lý (không phải SaaS dùng chung).
3. **BỔ SUNG (Companion/Realtime/ModelGateway)** — tách `RealtimeProvider` (LiveKit +
   Gemini Live cho voice) khỏi `ModelProvider`/`ModelGateway` (APIAI.vn/OpenRouter/
   direct cho reasoning text), thêm Talk→Work Intent Router và background mission.

Cả ba lớp đều nhấn mạnh một nguyên tắc xuyên suốt: **COSA giữ business truth, governance,
approval, memory; Harness/n8n/model provider chỉ là replaceable infrastructure**, không
được để business domain (`finance`, `sales`, `okr`...) import thẳng SDK vendor.

### Phát hiện quan trọng nhất

**Đây không phải một bản build từ số 0.** Phần lớn "abstraction layer" mà spec đề xuất
đã tồn tại trong codebase dưới tên khác, xây trong quá trình migrate `javis/` sang
`backend/app/` và các đợt V13.1/V13.2 trước đó:

- Cái tương đương **ModelGateway** đã chạy thật trong production path của chat
  (`ai_router.py` + `providers.py`), không phải khái niệm mới.
- Cái tương đương **MCP tool gateway** đã tồn tại thu nhỏ (`tool_registry.py`), chỉ
  thiếu governance metadata (risk/permission/approval/idempotency).
- **Feature flag** đã có, nhưng là DB-backed/workspace-scoped, không phải biến môi
  trường như spec viết literal — nghĩa là phần "Feature flags" (Section 6, Section 93)
  của spec phải được dịch lại sang convention thật, không copy nguyên văn.
- **Approval gate** đã có hai bản thu nhỏ thật sự chạy (`WorkflowApproval`,
  `EmailApproval`).
- **Evidence/structured-output/proposal** đã có một substrate riêng
  (`ai_team`/`outcomes`/`learning`/`tasks`, mô hình 5 AI Function) gần với những gì
  Section 24/30/53 của spec mô tả.
- **LiveKit voice + Companion HUD** đã chạy đầy đủ (`modules/realtime`,
  `services/realtime_agent/`, `frontend/lib/modules/hologram_hub/`) — phần BỔ SUNG của
  spec phần lớn là *formalize* cái đã có, không phải xây mới.
- **Background execution** đã có một worker asyncio tự chế
  (`backend/app/worker_main.py`, claim-and-poll qua Postgres LISTEN/NOTIFY, không
  Celery/arq).

Phần **thật sự greenfield**: DeepSeek Harness (chưa có dòng code nào import SDK này),
n8n/`AutomationProvider` (chưa có gì), governance chính quy dạng `agent_runs`/
`agent_events`/`agent_tool_calls`/Policy Engine L0–L3, Chief of Staff orchestration đa
agent, và toàn bộ licensing/entitlement (Section 81, BỔ SUNG §9).

Nguyên tắc điều chỉnh cho toàn bộ roadmap dưới đây: **mở rộng abstraction đã có nơi nó
đã thỏa mãn ý định của spec; chỉ tạo mới nơi thật sự chưa có gì; không bao giờ dựng một
"execution engine" thứ hai** — đúng tinh thần mà các plan V13 trước đã áp dụng và đúng
ranh giới runtime của `CLAUDE.md`.

---

## Domain Mapping — Spec Concept vs Codebase Reality

| Spec concept (section) | Trạng thái | Tương đương trong codebase | Quyết định |
|---|---|---|---|
| ModelGateway / model routing (§10, §46, BỔ SUNG §7) | EXISTS | `backend/app/modules/chat/ai_router.py` (`ChatProvider`, `AIRouter`) + `providers.py` (registry deepseek/openai/openrouter/anthropic/gemini) + `app/integrations/*_client.py` | **EXTEND** — thêm `ApiAIVnProvider`, khái niệm "profile" (chat_fast/business_deep...), không tạo module `ModelGateway` song song |
| COSA MCP Gateway / tool contract (§11, §12) | PARTIAL | `backend/app/core/tool_registry.py` (`ToolSpec`, namespace, `flag_key`, `chat_schema`, `flat_name`) | **EXTEND** — thêm `risk_level`, `permission_level`, `requires_approval`, `idempotency`, `allowed_agent_keys` vào `ToolSpec` |
| Feature flags (§6, §93) | EXISTS (khác cơ chế) | `backend/app/core/feature_flags.py` — DB-backed, workspace-scoped (`FeatureFlag` model), constant `FLAG_..._V13_x` | **DÙNG CONVENTION THẬT** — bỏ ý tưởng env var `COSA_AGENT_RUNTIME=...` của spec, đặt flag mới theo mẫu `FLAG_AGENT_RUNTIME_...`/`FLAG_AUTOMATION_...` |
| Approval Gateway (§14, §54) | PARTIAL | `WorkflowApproval` (`modules/workflows`) + `EmailApproval` (`modules/integrations/email_approval_router.py`) | **GENERALIZE** thay vì viết `approvals/` từ đầu ở Phase 3 |
| Agent hierarchy / structured output / evidence (§8, §24, §53) | PARTIAL | `modules/ai_team` (5 AI Function: LEGAL/MARKETING/SALES/TECH/FINANCE), `modules/outcomes` (Outcome/Artifact), `modules/learning` (Lesson), `modules/tasks` | **REUSE làm evidence substrate** — Harness (nếu bật) nên ghi kết quả vào đây, không tạo kho evidence song song |
| `agent_proposals` (§30) | PARTIAL | `Task` state machine + `WorkflowApproval` đã có khái niệm "đề xuất chờ duyệt rồi mới tạo task/objective" | **EXTEND/QUYẾT ĐỊNH RIÊNG** ở Phase 2 — có thể chỉ cần thêm cột liên kết `agent_run_id` vào `Task`/`Outcome` thay vì bảng mới |
| LiveKit voice transport (§27) | EXISTS | `modules/realtime` (token/session) + `services/realtime_agent/` (LiveKit-agents service riêng) | **GIỮ NGUYÊN**, không thay bằng Harness (đúng chỉ thị #12 của spec) |
| Companion Mode / HUD (BỔ SUNG §6) | EXISTS | `frontend/lib/modules/hologram_hub/` (`hud_card`, `system_health_panel`, `needs_you_panel`, `quick_commands_bar`...) | **EXTEND** — Mission/mission-count/pending-approval hiển thị thêm trong HUD sẵn có, không tạo Companion Mode mới |
| Intent/Action Registry (BỔ SUNG §4) | PARTIAL | `modules/company_runtime/tools.py` (`runtime_classify_intent`, LiveKit tool registration theo ADR-V13-005) | **EXTEND** thành Talk→Work router ở Phase 6 |
| Mission Control event stream (§26, §92, BỔ SUNG §16) | PARTIAL (transport có sẵn) | `modules/chat/chat_stream_bus.py` — SSE qua Postgres LISTEN/NOTIFY, Flutter đã có client SSE tay (`chat_service.dart:streamSession`) | **TÁI DÙNG transport**, chỉ thêm normalized event schema mới, không dựng WebSocket/SSE mới |
| Background job execution (§48, mọi automation/agent job) | EXISTS | `backend/app/worker_main.py` — asyncio claim-and-poll qua Postgres, `chat_loop`/`channel_worker_loop`/`_background_loop` | **CẮM VÀO WORKER HIỆN CÓ**, không thêm Celery/arq/RQ |
| Tenant isolation pattern (§50) | EXISTS | `backend/app/db/repositories/vault_repo.py` — `get_<entity>_scoped(db, id, workspace_id)`; `get_current_workspace_member` (`app/core/auth.py`) | **COPY PATTERN NÀY** cho mọi MCP tool/agent-runtime endpoint mới |
| Snowflake ID (CLAUDE.md) | EXISTS | `backend/app/db/snowflake_model.py` (`SnowflakeIDMixin`), `app/core/snowflake.py` | **DÙNG NGUYÊN** cho mọi bảng mới (`agent_runs`, `automation_runs`...) |
| `AgentRuntime` abstraction (§4, §5) | GREENFIELD | — | **NEW**, Phase 1 |
| DeepSeek Harness adapter thật (§5, §69) | GREENFIELD | — | **NEW**, Phase 1, cần pin version SDK |
| `AutomationProvider` + N8nAdapter (§31, §73–§99) | GREENFIELD | — | **NEW**, Phase 5 |
| Policy Engine / L0–L3 chính quy (§13, §15) | GREENFIELD (chỉ có approval rời rạc) | — | **NEW**, Phase 3, dựa trên permission profile YAML như spec đề xuất |
| `agent_runs`/`agent_events`/`agent_tool_calls` (§18) | GREENFIELD | — | **NEW migration**, additive, Phase 1/3 |
| Chief of Staff orchestration (§9) | GREENFIELD | — | **NEW**, Phase 4, sau khi Sales/Finance agent ổn định |
| `RealtimeProvider` abstraction chính quy (BỔ SUNG §2) | PARTIAL (LiveKit+Gemini đã chạy nhưng không có interface tách rời) | `modules/realtime/*`, `services/realtime_agent/` | **FORMALIZE** thành interface ở Phase 6, không đổi hành vi hiện tại |
| Licensing/entitlement (§81, BỔ SUNG §9) | GREENFIELD | — | **OUT OF SCOPE roadmap này** — Phase 7, cần spec riêng |
| `modules/integrations/mcp/{mcp_hub,mcp_catalog,mcp_client}.py` | **DEAD CODE, KHÔNG PHẢI FOUNDATION** | Chép nguyên từ `javis/`, import module không tồn tại (`config`, `mcp_store`, `skill_router`, `claude_cli`, `plugins_host`), không có `__init__.py`, `main.py` không import | **REMOVE/QUARANTINE**, Phase 0 |
| `Agent` DB model (chat persona) | EXISTS, TÊN TRÙNG VỚI SPEC | `db/models.py:Agent` (name/slug/system_prompt/provider/model), `modules/tasks/agents_router.py`, `frontend/lib/modules/agents/` | **KHÔNG ĐỤNG** — spec's "Agent Registry" (§7, runtime definition với tools/permission_profile) phải dùng tên khác, xem "Quyết định đặt tên" bên dưới |

---

## Adjustment Principles

Áp dụng lại các nguyên tắc trong `CLAUDE.md` + chỉ thị #1–26 của spec gốc, cụ thể hoá
cho roadmap này:

1. Không import `deepseek_harness`/n8n SDK ngoài `backend/app/agents/runtime/adapters/`
   và `backend/app/automations/runtime/adapters/`. Domain (`finance`, `sales`, `okr`...)
   không bao giờ thấy vendor SDK.
2. Mọi flag mới đi qua `app/core/feature_flags.py` (DB-backed, workspace-scoped) —
   không thêm cơ chế flag thứ hai bằng env var.
3. Mọi bảng mới dùng `SnowflakeIDMixin`, migration additive-only (không sửa bảng
   business hiện có), backward-safe nếu Harness/n8n bị tắt.
4. Mọi write tool mới mặc định `approval_required=true` cho đến khi có policy cụ thể
   (chỉ thị #15 của spec).
5. Không cấp shell/filesystem toàn hệ thống cho agent mặc định; sandbox theo
   `/data/cosa/agent-workspaces/{company_id}/{run_id}/` nếu cần filesystem.
6. Background execution luôn cắm vào `worker_main.py`, không đưa thêm queue
   technology.
7. Mọi endpoint/tool mới copy pattern tenant-scope của `vault_repo.py` — không tin
   `company_id`/`workspace_id` do model tự truyền trong tool-call payload.
8. n8n không bao giờ có credential/quyền ghi trực tiếp vào Postgres business của
   COSA; chỉ gọi qua FastAPI `/api/v1` hoặc MCP tool đã policy-kiểm soát.
9. Không bundle n8n binary/source vào installer COSA; không host n8n dùng chung nhiều
   khách hàng theo mặc định.

---

## Phased Roadmap

Mỗi phase = một PR review được, test-first, có exit criteria rõ ràng, có đường rollback
(tắt flag → hành vi cũ). Phase 0–1 đủ chi tiết để thực thi ngay; Phase 2 trở đi chỉ nêu
mục tiêu/phạm vi/phụ thuộc, cần một plan riêng trước khi code.

### Phase 0 — Hygiene (làm trước tiên, rất nhỏ)

**Mục tiêu:** loại bỏ rủi ro có sẵn trước khi bắt đầu, không phụ thuộc gì ở các phase
sau.

- Xử lý `backend/app/modules/integrations/mcp/{mcp_hub.py, mcp_catalog.py,
  mcp_client.py}` — dead code chép từ `javis/`, vi phạm ranh giới runtime của
  `CLAUDE.md`. Vì file này chưa từng được import bởi `main.py`, xoá nó không có blast
  radius runtime; chỉ cần xác nhận không có script/test nào tham chiếu trước khi xoá,
  hoặc — nếu muốn giữ làm tài liệu tham khảo — di chuyển ra ngoài `backend/app/` (vd.
  vào `docs/reference/` không phải Python package) kèm ghi chú rõ "không phải code
  chạy được".
- Không có migration, không có flag, không đổi hành vi runtime.

**Exit criteria:** `rg -n "mcp_hub|mcp_catalog|mcp_client" backend/app --type py`
không còn hit nào bên ngoài chỗ đã dọn; test suite hiện tại vẫn xanh.

### Phase 1 — AgentRuntime Spike (≈ spec H0 + Claude Code execution Step 1–3)

**Mục tiêu:** chứng minh FastAPI gọi được DeepSeek Harness an toàn, sau một
abstraction trung lập, hoàn toàn tắt theo mặc định.

Phạm vi cụ thể:

- `backend/app/agents/runtime/`:
  - `types.py` — `AgentRunRequest`/`AgentRunResult`/`AgentEvent` (theo §4.2/§4.3 của
    spec, `company_id`/`workspace_id`/`user_id` bắt buộc, không truyền raw DB object).
  - `base.py` — `AgentRuntime` ABC (`run`, `stream`, `resume`, `cancel`, `get_trace`,
    `health`; `fork()` optional).
  - `manager.py` — `AgentRuntimeManager`, khởi động/dừng trong `lifespan` của
    `backend/app/main.py` cạnh MinIO bootstrap và `cross_process_event_listener` đã có,
    không để request tự spawn runtime.
  - `errors.py` — mã lỗi chuẩn hoá (`AGENT_RUNTIME_UNAVAILABLE`,
    `AGENT_RUNTIME_TIMEOUT`, `AGENT_TOOL_ERROR`..., theo §22 của spec) — không bao giờ
    để raw exception của Harness lộ ra response.
  - `adapters/mock.py` — `MockRuntime`, dùng làm test path mặc định.
  - `adapters/deepseek_harness.py` — `DeepSeekHarnessAdapter` bọc
    `deepseek-harness-sdk` (đã pin version cụ thể trong `requirements.txt`/lockfile,
    theo lựa chọn của người dùng: cài SDK thật ngay, không chỉ Mock). Chỉ implement
    `run`/`health`/`cancel` cơ bản ở phase này; `stream`/`resume`/`fork` có thể
    `NotImplementedError` nếu SDK thật chưa ổn định cho các method đó — kiểm tra API
    thực tế của bản pin trước khi code method signature (đúng cảnh báo §69 của spec:
    Harness đang Developer Preview, API có thể đổi).
- Feature flag mới trong `app/core/feature_flags.py`, theo convention `FLAG_..._V13_x`
  đã có, ví dụ `FLAG_AGENT_RUNTIME_DEEPSEEK`, mặc định **tắt**, workspace-scoped.
- Một `runtime_test_agent` duy nhất — read-only, không business tool, chỉ để chứng
  minh vòng đời run/health/timeout/cancel.
- Endpoint nội bộ kiểu `GET /api/v1/agents/runtime/health` (theo convention router
  `/api/v1/<module>` hiện có trong `main.py`, không tạo tiền tố `/internal/` mới nếu
  repo chưa có convention đó — kiểm tra lại các router hiện có trước khi đặt path).
- `tests/agents/runtime_contract/` (theo §21 của spec) — cùng một bộ test chạy lần
  lượt với `MockRuntime` và `DeepSeekHarnessAdapter`: `test_run.py`, `test_cancel.py`,
  `test_timeout.py`, `test_runtime_crash.py`, `test_trace.py` tối thiểu cho phase này.
- **Đặt tên**: không dùng chữ "Agent" trần cho khái niệm registry runtime mới, để
  tránh trùng bảng `Agent` (chat persona) đã có ở `db/models.py`. Xem "Quyết định đặt
  tên" bên dưới trước khi đặt tên module/bảng chính thức.

**Exit criteria (copy §41 H0 của spec):** FastAPI boot/stop sạch; một run thành công
qua `MockRuntime` và một run thành công qua `DeepSeekHarnessAdapter` thật (network/API
key thật, có thể dùng key sandbox); timeout hoạt động; Harness crash không kéo FastAPI
sập; flag tắt → app hoạt động bình thường không đổi gì.

### Phase 2 — MCP Read-only Tools + Sales/Finance Agent POC (≈ spec H1)

**Mục tiêu:** một agent thật (Sales, rồi Finance) trả lời câu hỏi read-only bằng tool
gọi vào domain service thật, có tenant isolation và trace.

Phạm vi (cần plan riêng trước khi code):

- Mở rộng `ToolSpec` trong `tool_registry.py` thêm `risk_level`, `permission_level`,
  `requires_approval`, `idempotency`, `allowed_agent_keys` — additive, không phá vỡ
  chữ ký hiện có (`@register(namespace, name, flag_key, chat_schema)`).
- Tool read-only đầu tiên bọc quanh service Sales/Finance hiện có (`modules/sales`,
  `modules/finance`), dùng scoped-getter pattern của `vault_repo.py` — inject
  `workspace_id` từ execution context đã xác thực, không tin giá trị model tự truyền
  (đúng §50 của spec).
- Chốt quyết định đặt tên "agent runtime definition" (xem mục Quyết định bên dưới) và
  viết một ADR ngắn (theo convention `docs/adr/ADR-...md` đã có trong repo) trước khi
  tạo bảng/registry chính thức.
- `agent_eval_cases`/fixture tối thiểu cho Sales (theo §39 của spec): không đề xuất
  lead đã closed/lost sai, evidence map được tới tool output, không hallucinate số
  liệu.

### Phase 3 — Governance (≈ spec H2)

**Mục tiêu:** mọi write tool đi qua policy + approval, có audit đầy đủ.

- `agent_runs`/`agent_events`/`agent_tool_calls` — migration additive, Snowflake PK,
  theo schema §18 của spec (rút gọn nếu cần, không bắt buộc copy hết field).
- Generalize `WorkflowApproval`/`EmailApproval` thay vì viết `approvals/` domain mới
  từ đầu — đánh giá xem hai model này có thể hợp nhất thành một bảng
  `Approval` generic (action_type/tool_name/risk_level/status) mà cả hai use case cũ
  lẫn agent tool call mới đều dùng được, hay giữ riêng và thêm bảng thứ ba
  `AgentToolApproval` — đây là quyết định thiết kế cần một plan riêng, không quyết ở
  đây.
- Policy Engine tối giản: đọc permission profile (YAML hoặc bảng DB tương đương mẫu
  §55–§57 của spec), input là `(company, agent, tool, resource, risk)`, output
  `allow|deny|require_approval` — không cần engine tổng quát, chỉ cần đủ cho 4 mức
  L0–L3.
- Chỉ mở một số internal low-risk write đầu tiên (vd. `create_activity` trong Sales),
  không mở write tool tài chính/pháp lý/gửi email hàng loạt ở phase này.

### Phase 4 — Chief of Staff + Mission Control (≈ spec H3)

**Mục tiêu:** một câu hỏi cấp Founder tự động delegate sang nhiều specialist agent, kết
quả tổng hợp hiển thị real-time.

- Chief of Staff orchestration + subagent delegation trong `AgentRuntime`, chỉ bật sau
  khi Sales + Finance agent (Phase 2) đã qua eval ổn định (đúng thứ tự spec đề xuất ở
  §8).
- Mission Control event: tái dùng transport SSE/Postgres NOTIFY đã có
  (`chat_stream_bus.py` là mẫu tham khảo trực tiếp), chỉ định nghĩa event schema mới
  (`run_started`, `tool_completed`...) theo §18.1/§26 của spec — không dựng WebSocket
  hay transport mới.
- Flutter: module mới dưới `frontend/lib/modules/` (vd. `mission_control/`) theo đúng
  convention `{bindings,controllers,views,data}` + đăng ký `GetPage` trong
  `app_pages.dart`/`app_routes.dart` — không đưa `get_it` hay pattern DI khác vào.
  Có thể tận dụng lại các widget HUD đã có trong `hologram_hub/` thay vì vẽ mới hoàn
  toàn.

### Phase 5 — AutomationProvider / n8n (độc lập, có thể chạy song song Phase 2/3)

**Mục tiêu:** một automation an toàn nhất (Telegram notification) chạy end-to-end qua
n8n của khách hàng, không đụng business DB trực tiếp.

- `backend/app/automations/runtime/{base.py,manager.py,types.py,adapters/
  {mock.py,n8n.py}}` theo contract §73.1 của spec
  (`health/execute/get_status/cancel/list_capabilities`).
- `automation_definitions`/`automation_runs`/`automation_events`/
  `automation_callbacks` — migration additive, Snowflake PK, không dùng execution DB
  của n8n làm audit source.
- Automation Catalog dùng key ổn định COSA (`system.telegram_notification` là điểm
  khởi đầu, thấp rủi ro nhất theo §87 của spec) — mapping `automation_key →
  provider_workflow_ref` là config cài đặt theo khách hàng, không hard-code/không
  commit vào repo.
- Callback có signature + chống replay (§77, §85 của spec).
- `infra/n8n/` chỉ chứa README + script/docs deploy trên hạ tầng khách hàng (pull
  official image), **không** bundle binary/source n8n — đúng chỉ thị #20 của spec và
  `CLAUDE.md`.

### Phase 6 — Companion / ModelGateway Formalization (BỔ SUNG của spec)

**Mục tiêu:** chính quy hoá cái đã chạy (LiveKit+Gemini, provider routing) thành
interface thay thế được, không đổi hành vi hiện tại của người dùng cuối.

- Mở rộng `ai_router.py`/`providers.py` thành `ModelGateway` có khái niệm "profile"
  (`chat_fast`, `business_deep`, `structured_extract`...) map tới provider/model cụ
  thể qua config, không hard-code model ID trong code domain.
- Thêm `ApiAIVnProvider` vào registry hiện có trong `providers.py`, theo cùng pattern
  các provider khác (`DeepSeekClient`, `GeminiClient`...).
- Bọc `RealtimeProvider` (interface, §BỔ SUNG 2) quanh tích hợp LiveKit+Gemini đã chạy
  ở `modules/realtime` — refactor có kiểm soát, không thay đổi UX voice hiện tại.
- Talk→Work Intent Router mở rộng `modules/company_runtime/tools.py`
  (`runtime_classify_intent` đã có) để phân luồng TALK (trả lời ngay qua Realtime) vs
  WORK (tạo agent mission chạy nền qua `AgentRuntime` từ Phase 1/4).
- Background mission state (`waiting_user`, `waiting_approval`...) nên map vào state
  machine `Task` đã có nếu ngữ nghĩa tương thích, thay vì một enum mission độc lập —
  cần xác nhận cụ thể trong plan riêng của phase này.

### Phase 7 — Licensing/Entitlement (ngoài phạm vi roadmap này)

Hoàn toàn greenfield ở cả backend lẫn frontend (không có hit nào cho
`license`/`entitlement`/`device_activation`). Cố ý để ngoài roadmap này — cần một spec
sản phẩm/pháp lý riêng (đúng §70 "License note" của spec gốc: đây là kiến trúc kỹ
thuật, không phải tư vấn pháp lý) trước khi lên kế hoạch kỹ thuật.

---

## Quyết định cần chốt trước khi code Phase 1

Không phải ADR đầy đủ — liệt kê để phiên làm việc tiếp theo biết cần quyết định gì
trước khi viết code, và vì sao mỗi quyết định lệch khỏi văn bản spec gốc:

1. **Tên gọi "agent runtime definition"** — không dùng "Agent" trần vì đã có bảng
   `Agent` (chat persona, `db/models.py`) expose qua `tasks/agents_router.py` +
   `frontend/lib/modules/agents/`. Đề xuất: gọi khái niệm mới trong spec §7 (agent
   definition với `runtime`/`tools`/`permission_profile`) là ví dụ
   `AgentRuntimeProfile` hoặc `RuntimeAgentDefinition` trong code/migration, giữ
   "Agent" cho đúng nghĩa hiện tại (chat persona). Cần chốt tên chính thức bằng một ADR
   ngắn trước khi tạo bảng.
2. **Feature flag DB-backed, không phải env var** — spec Section 6/93 viết
   `COSA_AGENT_RUNTIME=legacy|deepseek_harness|mock`, `COSA_DSH_ENABLED=false` như biến
   môi trường. Repo hiện dùng `FeatureFlag` model workspace-scoped
   (`app/core/feature_flags.py`). Roadmap dùng convention thật của repo cho mọi
   toggle logic nghiệp vụ; biến môi trường chỉ dùng cho thứ phải quyết định *trước khi*
   kết nối được DB (vd. có khởi động subprocess runtime hay không ở tầng process).
3. **Dọn `mcp_hub.py` trước** (Phase 0) — để không ai nhầm đây là MCP gateway đang
   sống khi bắt đầu Phase 1/2.
4. **SDK thật ngay từ Phase 1** — theo lựa chọn của người dùng, không chỉ dừng ở
   `MockRuntime`. Nhưng `MockRuntime` vẫn phải là default test path (CI không nên phụ
   thuộc mạng ngoài/API key thật); contract suite (§21) phải pass với cả hai runtime.
5. **Background run cắm vào `worker_main.py`** — không thêm Celery/arq/RQ dù spec
   Section 48 mô tả một hàng đợi tổng quát; pattern claim-and-poll qua Postgres đã có
   sẵn và đúng "không dựng execution engine thứ hai".
6. **`agent_proposals` có thể không cần bảng riêng ngay** — vì `Task`/`WorkflowApproval`
   đã gần đủ ngữ nghĩa "đề xuất chờ duyệt rồi mới thành business entity" (§30 của spec).
   Quyết định mở bảng mới hay mở rộng bảng cũ thuộc phạm vi Phase 2/3, không chốt ở
   Phase 1.

---

## Sequencing & Dependencies

```text
Phase 0 (hygiene)
   │
   ▼
Phase 1 (AgentRuntime spike) ──────────┐
   │                                   │
   ▼                                   ▼
Phase 2 (MCP read-only + Sales/Finance POC)   Phase 5 (AutomationProvider/n8n)
   │                                          — độc lập với Phase 1-4, có thể
   ▼                                          chạy song song sau Phase 0
Phase 3 (Governance)
   │
   ▼
Phase 4 (Chief of Staff + Mission Control)

Phase 6 (Companion/ModelGateway formalization)
   — chạm chung file với Phase 2 (ai_router.py/providers.py mở rộng cho MCP tool
     chat_schema); nên làm sau Phase 2 để tránh conflict, nhưng không phụ thuộc cứng
     vào Phase 3/4/5.

Phase 7 (Licensing) — hoàn toàn tách rời, không phụ thuộc phase nào ở trên.
```

Ưu tiên theo giá trị/rủi ro: Phase 0 → Phase 1 → Phase 2 trước tiên (chứng minh runtime
+ một agent hữu ích thật). Phase 5 (n8n) có thể bắt đầu song song ngay sau Phase 0 vì
hoàn toàn độc lập kỹ thuật với Agent Runtime — chỉ cần Policy/Approval tối giản của
Phase 3 trước khi cho phép automation có side-effect ngoài whitelist hệ thống
(`system.telegram_notification` không cần approval, các automation khác thì cần).

---

## Guardrails không được vi phạm (carried từ CLAUDE.md + chỉ thị spec)

- Không đổi version sản phẩm khỏi v13.1/v13.2 vì roadmap này.
- Không fork DeepSeek Harness; không sửa source upstream.
- `finance`/`sales`/`okr`/`marketing`... không bao giờ import thẳng SDK Harness/n8n.
- DeepSeek Harness phải disable hoàn toàn được bằng flag mà COSA vẫn boot bình thường.
- Không cấp quyền filesystem/shell toàn hệ thống cho agent mặc định.
- Không cho agent tự thực hiện hành động tài chính/pháp lý/gửi thông điệp ra
  ngoài/thay đổi dữ liệu quan trọng nếu chưa qua approval.
- Mọi task agent có trace tối thiểu: user request, runtime, model, tool call, tool
  result, approval, final result, error.
- Không dùng Harness session/event log làm business memory chính.
- Không thay LiveKit bằng Harness.
- n8n không được host dùng chung nhiều khách hàng theo mặc định; không bundle
  binary/source vào installer; không embed n8n editor vào Flutter; không cho n8n ghi
  thẳng Postgres business.
- `frontend/lib` tiếp tục không được reference `:8888`, `backend/server`, `javis/`,
  `web_socket_channel` (đã verify sạch ở thời điểm audit — giữ nguyên).

---

## Traceability — Spec section → Phase

| Spec section(s) | Phase |
|---|---|
| §4, §5, §6, §21, §22, §41(H0), §62 Step 1-3, §65 | Phase 1 |
| §11, §12, §13(một phần), §39, §41(H1), §66, §28, §29 | Phase 2 |
| §14, §15, §18, §36, §41(H2), §55-§57, §67 | Phase 3 |
| §8, §9, §26, §41(H3), §68, §33 | Phase 4 |
| §31, §32, §73–§99 | Phase 5 |
| BỔ SUNG §1–§20 | Phase 6 |
| §81, §45.3, BỔ SUNG §9 | Phase 7 (ngoài phạm vi) |
| §0, §1–§3, §19, §20, §37, §42, §43, §60, §61, §64 (nguyên tắc/ranh giới) | Áp dụng xuyên suốt mọi phase |

---

## Verification (cho chính tài liệu này)

Đây là tài liệu định hướng, không có code để chạy test. Đã xác minh trước khi viết:

- Mọi đường dẫn trong bảng Domain Mapping được đọc trực tiếp hoặc qua Explore agent
  trong phiên audit 2026-08-14 (không suy đoán).
- Format khớp với các plan khác trong `docs/architecture/` (header trỏ spec gốc, mục
  Context nêu phát hiện đối chiếu, bảng mapping, roadmap theo phase).
- Không đề xuất điều gì vi phạm `CLAUDE.md`: không import `javis/`, không thêm SQLite,
  không cấp quyền filesystem/shell mặc định, mọi write tool mới mặc định
  `approval_required=true`.

Khi bắt đầu code Phase 1, cần chạy lại `rg -n --glob '!build/**'
'(:8888|backend/server|javis/|web_socket_channel)' frontend/lib` và test suite backend
hiện có để xác nhận baseline vẫn xanh trước khi thêm code mới.
