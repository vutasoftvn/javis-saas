# COSA: Google ADK Orchestrator + DeepSeek Harness + OPC OS (Database & Deployment)

**Status:** Đề xuất kiến trúc — đã đối chiếu với `OPC_OS_ADK_DeepSeek.md` (tài liệu tự viết của founder) và `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`
**Date:** 2026-08-20
**Revision 2026-08-21:** Đã đối chiếu với `markdown/A1.md` (bản review độc lập của chính proposal này) và verify chéo bằng 2 Explore agent import trực tiếp `google-adk` trong `backend/.venv` + đọc code thật (`TaskBoardService`, `worker_main.py`, `ModelGateway`, `COSA_CANONICAL_OWNERSHIP_MAP.md`, toàn bộ file model dùng Snowflake ID). Kết quả: A1.md đúng ở gần như mọi điểm tranh chấp — đã sửa trực tiếp các Quyết định bên dưới, đáng chú ý nhất là tiền đề sai về API ADK (Quyết định 1) và quyết định ID cuối cùng: **giữ thuần Snowflake ID cho toàn bộ dự án, bỏ hẳn UUIDv7** (Quyết định 5).
**Nguồn:** Khảo sát codebase (Explore + Plan agents, verify chéo bằng grep/Read trực tiếp, không suy đoán) + tra cứu bên ngoài (PostgreSQL 18 UUIDv7)
**Phạm vi tài liệu này:** Đề xuất kiến trúc + kế hoạch phân giai đoạn. Chưa thực thi code cho Quyết định 1-6; các sửa đổi CLAUDE.md ở Quyết định 7.3 đã được áp dụng cùng lúc với việc lưu tài liệu này.

## Context

Founder muốn dùng **Google ADK làm orchestrator** kết hợp **DeepSeek Harness** để tận dụng thế mạnh mỗi bên, mở rộng COSA thành "OPC OS" có thể có thêm **nhân viên là người thật** trong tương lai, và cần quyết định lại tầng **database** (Supabase/Insforge/Postgres, online/offline) + **triển khai** (desktop ưu tiên, VPS tự host).

Khảo sát kỹ codebase (3 agent Explore + 1 agent Plan, có xác minh chéo bằng grep) cho thấy **phần lớn hạ tầng cần thiết đã tồn tại và đang chạy thật** — không phải xây từ đầu:
- `ChiefOfStaffOrchestrator` đã là "Co-founder Orchestrator" sản xuất, có governance/budget/risk-gating đầy đủ.
- `DeepSeekHarnessAdapter` đã wrap SDK thật, chạy vòng lặp tool-calling có governance.
- `google-adk==2.7.0` đã được pin và cài, nhưng lần tích hợp trước (`agents/adk_runtime/`) là spike giả (hardcode Python, không gọi ADK thật) — đã bị đánh giá "dead code, nên xoá". Đây là bài học phải tránh lặp lại.
- Tầng đồng bộ trung tâm (`PlatformOutbox/Inbox`, `EntitlementManager`, `PlatformSyncWorker`) đã hoạt động **offline-first**, và **quan trọng**: nó nói chuyện qua HTTP nội bộ do COSA tự viết (`platform_router`), **không** gọi SDK Supabase hay Insforge trực tiếp — nghĩa là đổi vendor phía sau không đụng vào code đồng bộ này.
- **Phát hiện quan trọng** (đã verify bằng grep): production VPS (`deploy/central_vps/init_central_postgres.sql`) đã ghi rõ *"Pure PostgreSQL 16+ without Supabase dependencies"* — tức là hệ thống **hiện tại không thực sự chạy Supabase**, chỉ có Postgres thuần + JWT tự viết. `grep -rl supabase backend/app` trả về rỗng — không có SDK Supabase nào được gọi trong code. Thư mục `infra/supabase/` là một đặc tả song song, đang lệch (drift) với `deploy/central_vps/init_central_postgres.sql`.
- **Phát hiện quan trọng thứ 2**: cây `backend/agent_runtime/*` được tài liệu nội bộ gắn nhãn "frozen retirement candidate", nhưng thực tế `task_board.py` và `profiles/registry.py` (đường dẫn canonical, đang chạy sản xuất) vẫn `import` trực tiếp từ `agent_runtime.sessions.models` và `agent_runtime.profiles.definitions` — cây này **chưa thể xoá**, phải giữ nguyên trong mọi thay đổi.

Người dùng đã chốt 4 hướng kiến trúc, biết rõ đây là thay đổi lớn và rủi ro cao hơn "smallest safe change" mặc định của CLAUDE.md, và đã xác nhận cho phép điều chỉnh cấu trúc để ưu tiên dễ bảo trì/triển khai/đọc code hơn là giữ nhiều hệ thống song song. Vì vậy Quyết định 1 dưới đây **thay thế trực tiếp** `ChiefOfStaffOrchestrator` bằng `AdkCofounderWorkflow` (không giữ 2 orchestrator chạy song song, không feature-flag rollout dài hạn) — chỉ giữ lại đúng 1 lớp bảo vệ: bộ test bắt buộc xác nhận governance (audit row, risk-gate) không bị bypass trước khi merge, vì đó là nguyên nhân cụ thể khiến lần tích hợp ADK trước thất bại (nhìn an toàn trên giấy nhưng thực chất bỏ qua GovernanceKernel), không phải sự thận trọng thừa.

Người dùng cũng bổ sung 4 yêu cầu, đã được nghiên cứu/verify trực tiếp trên codebase và bằng tra cứu bên ngoài:
1. **ADK có nên dùng LiteLLM để kết nối model?** — Verify được: `ModelGateway.invoke()` (seam dự kiến dùng cho ADK) hiện **chưa có implementation thật nào trong production** — `invoker_fn` chỉ được truyền giá trị thật ở 1 file test (`backend/app/tests/agents/test_reliability_and_model_gateway.py`), production để mặc định (mock). Nhưng đã có `backend/app/workforce/ai/model_policy/gateway_lm.py::GatewayLM` — 1 `dspy.LM` subclass **đã dùng chung CircuitBreaker registry với ModelGateway**, và DSPy tự thân dùng LiteLLM làm tầng kết nối model (quy ước đặt tên `"provider/model"` trong file này chính là quy ước của LiteLLM). Tức là LiteLLM **đã ngầm là lựa chọn kết nối model của codebase**, chỉ chưa được nối đầy đủ vào `ModelGateway.invoke()`. → Trả lời: **Có**, nhưng ADK không dùng thẳng `google.adk.models.lite_llm.LiteLlm` (sẽ bypass governance) — LiteLLM chỉ là bộ kết nối ở tầng thấp nhất bên trong `invoker_fn` mà `CosaModelGatewayLlm` truyền vào `ModelGateway.invoke()`, hoàn thiện luôn phần còn thiếu của `ModelGateway` mà `gateway_lm.py` đã gợi ý sẵn.
2. **Database thống nhất PostgreSQL 17/18 dùng UUIDv7 cho cả online và offline** — đã tra cứu: PG18 (phát hành 09/2025) có hàm `uuidv7()` native, PG17 thì không (cần extension). Chi tiết thiết kế ở Quyết định 5.
3. **Cho phép "đập đi xây lại" codebase khi cần** — áp dụng có chọn lọc: dùng cho tầng ID/schema (Quyết định 5) vì đổi kiểu khoá chính vốn không thể làm kiểu strangler thuần; không áp dụng để bỏ yêu cầu test governance ở Quyết định 1 vì rủi ro cụ thể ở đó (ADK bypass governance) không biến mất chỉ vì được phép viết lại.
4. **ADK cần dùng được Tool/Skill hiện có, và cần phòng ngừa DeepSeek Harness thay đổi trong tương lai** — chi tiết ở cuối Quyết định 1.

Sau đó, người dùng cung cấp 1 tài liệu tự viết — `OPC_OS_ADK_DeepSeek.md` — và yêu cầu đối chiếu với `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` để chốt phương án tốt nhất. Kết quả đối chiếu:

- **Phần lớn nguyên tắc trong `OPC_OS_ADK_DeepSeek.md` khớp với Ownership Map và với những gì đã verify ở các Quyết định 1-3-5** — không cần sửa: ADK chỉ là orchestration, không sở hữu Permission/Approval/Budget/Task state (khớp nguyên tắc "OPC OS phải là System of Record" + Ownership Map dòng "Runtime governance ... No parallel driver"); DeepSeek Harness nằm dưới `AgentRuntime` (khớp dòng "Agent runtime implementation ... No parallel driver under agent_runtime"); ADK/DeepSeek/Chat dùng chung 1 "Governed Tool Broker" (khớp chính xác dòng "Workforce tools/transports ... tools/invocation is the real GovernanceKernel-routed dispatch path" — đây chính là `CosaGovernedTool` ở Quyết định 1); PostgreSQL là canonical database, SQLite chỉ cache (khớp CLAUDE.md §10); nguyên tắc "một aggregate chỉ có 1 authority tại 1 thời điểm" (Personal Mode: local = authority / Team Mode: cloud = authority, chuyển qua "Promote to Team Workspace") là 1 tinh chỉnh tốt — áp dụng bổ sung vào Quyết định 3.
- **Tài liệu giúp chốt dứt điểm câu hỏi InsForge ở Quyết định 2** — không cần spike InsForge làm thay thế Postgres cho control-plane nữa, vì lý lẽ "InsForge hấp dẫn nhưng OPC đã tự sở hữu phần lớn capability tương tự, nên dùng cho *generated apps* thay vì làm System of Record" khớp với việc production hiện không hề gọi SDK Supabase (đã verify).
- **Tài liệu ĐÚNG khi nói "codebase đã có nền tảng hybrid workforce" — nhưng thực tế phong phú và rối hơn tài liệu mô tả.** Đã verify: `WorkforceMember` (`backend/app/platform/organization/models.py`) và `Task.execution_mode/assignee_member_id/owner_member_id` (`backend/core/tasks/models.py`) đều **có thật**, đang chạy (mounted tại `/api/v1/organization` và `/api/v1/company-runtime` — module `platform/license/*` thực chất là "Company Runtime" bị đặt nhầm thư mục trong đợt tái cấu trúc 2026-08-18, có hẳn 8 ADR riêng: `COSA_V13_1_COMPANY_RUNTIME_IMPLEMENTATION_PLAN.md`). Nhưng: (a) 2 hệ thống này **hoàn toàn không kết nối** với pipeline canonical `workforce/agents/*`; (b) `execution_mode` hiện chỉ là dữ liệu đọc/ghi hiển thị, không có code nào rẽ nhánh dispatch thật; (c) tài liệu chỉ phát hiện xung đột tên `agents` vs `agent_definitions` (2 chiều) — thực tế xung đột là **4 chiều** (xem Quyết định 4), nghiêm trọng hơn nhiều.
- **`COSA_CANONICAL_OWNERSHIP_MAP.md` hoàn toàn im lặng về `platform/organization`, `platform/license`, và về việc `AgentDefinition` có phải canonical hay không** — lỗ hổng thật trong tài liệu authoritative. Khuyến nghị cập nhật Ownership Map với các dòng mới (Quyết định 4).
- Tài liệu không đề cập LiteLLM hay PG18/UUIDv7 — giữ nguyên như đã chốt ở Quyết định 1 và 5.

Cuối cùng, người dùng yêu cầu bổ sung việc dọn dẹp docs/code không dùng và tái cấu trúc `CLAUDE.md` theo kiến trúc/logic mới — Quyết định 7, dựa trên đúng quy trình retire mà `COSA_CANONICAL_OWNERSHIP_MAP.md` tự định nghĩa (không bịa quy trình mới).

---

## Quyết định 1 — Google ADK thay thế hoàn toàn ChiefOfStaffOrchestrator

**Nguyên tắc cốt lõi**: ADK thay tầng **orchestration/routing**, KHÔNG thay tầng **execution**. `DeepSeekHarnessAdapter` giữ nguyên 100%, tiếp tục là nơi thực thi tool-calling loop có governance. ADK không gọi thẳng runtime hay Harness — mọi việc giao cho DeepSeek đi qua hàng đợi durable đã có sẵn (`TaskBoardService` → `DelegationJob` → `delegation-worker`), không tạo đường thực thi song song mới bỏ qua `GovernanceKernel`.

### 3 điểm gọi cần thay (verified)
- `backend/app/workforce/agents/orchestration/router.py` (`POST /orchestrate`)
- `backend/app/workforce/orchestrator/cosa_cofounder_service.py:460,506` (`.orchestrate()`, `.confirm_mission()`) — đường dẫn sản xuất thật
- `backend/app/workforce/agents/orchestration/continuation.py:40` (`.resume_after_delegation()`)

### Thiết kế: thay thế qua 1 seam mỏng, không giữ 2 hệ thống song song production
Không tạo facade/protocol nặng, không feature flag theo workspace, không canary. 3 điểm gọi ở trên đổi sang gọi 1 seam ứng dụng rất mỏng — `orchestration/service.py` (`orchestrate_mission()`/`confirm_mission()`/`resume_mission()`) — để Founder OS/API/Worker **không biết gì về Google ADK**; seam này gọi `AdkCofounderWorkflow` bên trong. Lý do giữ seam thay vì import thẳng vào 3 nơi: nếu sau này đổi orchestration engine, chỉ package `orchestration` đổi, không phải sửa lại router/worker/service. Đây **không phải** dual-production hay feature flag dài hạn — vẫn chỉ 1 orchestrator chạy thật tại 1 thời điểm; rủi ro ADK bypass governance được chặn bằng **test bắt buộc**, không cần hạ tầng rollback phức tạp.
- Retire flag rác `FLAG_ADK_SALES_PILOT` (còn sót từ spike cũ, code đọc nó đã không còn tồn tại).

### API thật của google-adk 2.7.0 (đã verify bằng import trực tiếp trong `backend/.venv`, KHÔNG phải "không có Graph API" như bản proposal trước đây viết sai)
Verify lại (phiên 2026-08-21) cho thấy `google-adk==2.7.0` có sẵn một graph/workflow engine thật, không chỉ `BaseAgent`/`BaseLlm`/`BaseTool`:
- `google.adk.workflow._base_node.BaseNode`, `google.adk.workflow._workflow.Workflow(BaseNode)`, `google.adk.workflow._graph.Graph`/`Edge`, `google.adk.workflow._function_node.FunctionNode`, `google.adk.workflow._join_node.JoinNode` — có graph validation, concurrent scheduling, và replay/resume dựng lại state node từ session events (`workflow/utils/_replay_manager.py`, `_replay_interceptor.py`, `_rehydration_utils.py`).
- `google.adk.agents.base_agent.BaseAgent` **kế thừa `BaseNode`** — agent tự nó đã là 1 node trong graph, không phải khái niệm tách biệt khỏi workflow.
- `google.adk.models.base_llm.BaseLlm.generate_content_async` → seam để viết `CosaModelGatewayLlm` gọi `ModelGateway.invoke()` (giữ nguyên retry/circuit-breaker/cost-tracking).
- `google.adk.tools.base_tool.BaseTool.run_async` → seam cho tool, nhưng **không** gọi thẳng `GovernanceKernel`/domain logic — chỉ gọi vào các seam đã governed sẵn (xem dưới).
- `google.adk.tools.agent_tool.AgentTool` → model hoá `SPECIALIST_REGISTRY` (sales/finance/legal/marketing) thành sub-agent.

Vì vậy root orchestrator nên là **`AdkCofounderWorkflow`** dựng bằng `Workflow`/`Graph`/`FunctionNode` — không tự viết lại 1 `BaseAgent` trần với Python orchestration logic để tái tạo thứ ADK đã cung cấp sẵn. Cấu trúc node:

```text
AdkCofounderWorkflow
│
├── CreateMissionNode
├── BuildCompanyContextNode
├── RiskClassificationNode
├── PlanningNode
│
├── Specialist Delegation (Sales / Finance / Marketing / Legal)
├── Wait/Resume
├── SynthesisNode
├── ApprovalGateNode
├── ExecutionNode
└── QualityGateNode
```

Phần tất định (risk-tier R0-R4, budget/stuck/quality gate — giống cách `chief_of_staff.py` hiện không để LLM tự quyết action-plan) dùng `FunctionNode`; phần cần reasoning dùng LLM agent node; phần cần DeepSeek dùng **durable delegation** (mục dưới), không chạy Harness trực tiếp trong tiến trình ADK.

### Phân biệt rõ "Tool" và "Job" (không trộn 2 primitive)
- **`ToolInvocation`** — ngắn hạn, gọi API/DB/function trong cùng transaction context (vd `finance.get_summary`, `crm.find_customer`, `gmail.send`). Đi qua `CosaGovernedTool` → `ToolInvocationService`.
- **`DelegationJob`/`ExecutionJob`** — có thể chạy vài phút trở lên, durable, có retry/lease/cancel/resume (vd DeepSeek code repository work, research mission, sandbox execution). Đi qua `TaskBoardService`.

DeepSeek Harness thuộc nhóm thứ hai — nếu trộn 2 nhóm, ADK sẽ không phân biệt được "tool đang chờ 300ms" với "software engineer đang làm việc 20 phút".

### ADK giao việc cho DeepSeek qua hàng đợi durable đã có, không gọi Harness trực tiếp
Codebase đã có sẵn 1 execution pipeline durable tốt hơn việc ADK tự gọi runtime:

```text
RunStep → TaskBoardService.assign_step() → DelegationJob → PostgreSQL durable queue
   → delegation-worker → InProcessSubagentProvider → AgentRuntimeManager → DeepSeekHarnessAdapter
```

Đã verify `TaskBoardService.assign_step()` (`backend/app/workforce/agents/delegation/task_board.py:62-238`) tự làm đủ: row locking (`with_for_update`), tenant verification, idempotency (`idempotency_key = f"delegation:{step.id}:attempt:1"`), dependency check, delegation depth check (`assert_can_delegate`, `MAX_SUBRUN_DEPTH=1`), provider health check, `DelegationPolicyEngine.evaluate(...)`, tạo `ApprovalService` approval khi cần, và ghi `append_run_event`. Worker (`backend/app/workforce/agents/delegation/worker.py:640-642`, chạy ở process riêng qua `backend/app/worker_main.py`, **không** phải trong `backend/app/main.py` — đã verify `main.py` không start `AgentRuntimeManager`) mới gọi `agent_runtime_manager.start()`/`delegation_provider_manager.start()` rồi thực thi runtime; `InProcessSubagentProvider` dùng `get_runtime(..., allow_default=False)`.

Do đó node delegation trong `AdkCofounderWorkflow` chỉ **tạo `RunStep` + gọi `TaskBoardService.assign_step()`**, commit DB, rồi **pause** — dựa vào cơ chế replay/resume của `Workflow` đọc lại session events để khôi phục trạng thái node khi mission được resume. Không tự chạy `DeepSeekHarnessAdapter` trong tiến trình ADK. Lợi ích: process crash, VPS restart, hoặc DeepSeek mất mạng không làm mất mission.

### Exactly-once resume khi mission có nhiều specialist chạy song song
`continuation.py` hiện dùng advisory lock + materialized completion event để đảm bảo cross-worker exactly-once khi nhiều specialist step cùng chuyển terminal gần nhau. Chuyển sang ADK phải giữ đúng tính chất này — nếu không, 4 specialist hoàn tất gần nhau có thể khiến 4 worker cùng resume workflow 4 lần. Thêm **`MissionResumeJob`** durable:

```text
MissionResumeJob
────────────────
mission_run_id
workflow_session_id
reason
idempotency_key
status
lease
```

với constraint `UNIQUE(mission_run_id, checkpoint_key)` (hoặc tái dùng outbox abstraction hiện có nếu phù hợp) — chỉ 1 worker claim được resume cho mỗi checkpoint.

### File mới
- `backend/app/workforce/agents/orchestration/adk/workflow.py` — `AdkCofounderWorkflow` (Graph/Workflow/FunctionNode, thay cho 1 `BaseAgent` trần)
- `.../adk/model_adapter.py` — `CosaModelGatewayLlm(BaseLlm)` → `ModelGateway` (chỉ viết sau khi `ModelGateway` được refactor thành typed request/response, xem mục Model connectivity)
- `.../adk/specialist_tools.py` — mỗi `SPECIALIST_REGISTRY` entry → 1 node tạo `RunStep` + gọi `TaskBoardService.assign_step(...)` (tái dùng `SpecialistSpec`/`SPECIALIST_REGISTRY` từ `chief_of_staff.py` cho tới khi file đó bị xoá, tránh 2 nguồn sự thật)
- `.../adk/governed_tool.py` — `CosaGovernedTool(BaseTool)` cho nhóm `ToolInvocation` (xem dưới)
- `.../adk/session_bridge.py` — projector mỏng chuyển lifecycle event quan trọng của ADK sang `AgentRun`/`AgentEventRecord`/`mission_control_bus` hiện có — **không** phải 1 `BaseSessionService` tự viết đầy đủ (xem mục Session/Runtime bên dưới)
- `.../orchestration/service.py` — seam mỏng `orchestrate_mission()`/`confirm_mission()`/`resume_mission()` mà router/`cosa_cofounder_service`/`continuation` gọi vào

### Session/Runtime persistence — dùng ADK native `DatabaseSessionService`, không tự viết `BaseSessionService`
`Workflow` 2.7 rebuild trạng thái node khi resume bằng cách scan session events — `BaseSessionService` không chỉ log chat, nó còn quản lý session/state/event history/state delta/resume/replay/concurrency revision. Tự viết lại 1 `BaseSessionService` custom có nguy cơ phải tái tạo chính xác semantics đó (state delta, event ordering, stale session, interrupt, checkpoint) — rất dễ tạo bug khó thấy.

Vì vậy: dùng **`google.adk.sessions.database_session_service.DatabaseSessionService`** (native, đã verify tồn tại và import được trong `.venv`), đặt trong schema/database riêng (`adk_runtime` — tên bảng ADK khá generic: `sessions`, `events`, `app_states`, `user_states`, cần cô lập khỏi `public`). `session_bridge.py` chỉ là 1 projector mỏng ghi các lifecycle event quan trọng sang `AgentRun`/`AgentEventRecord` (canonical audit ledger hiện có) — không phải audit trail thứ 4 cạnh tranh, giống quan hệ "Redis queue state ≠ business database".

Thêm entity **`RuntimeSession`** để nối các loại session (ADK/DeepSeek/Sandbox/Human) dưới 1 Mission — field `AgentRun.runtime_session_id` hiện tại quá chật khi có nhiều runtime cùng lúc:

```text
runtime_sessions
─────────────────
id, workspace_id, mission_run_id, agent_run_id
runtime_type      ADK | DEEPSEEK_HARNESS | OPENSANDBOX | HUMAN
external_session_id, parent_session_id
status, checkpoint_ref, metadata_jsonb
created_at, updated_at, finished_at
```

### `ExecutionScope` phải dựng từ context tin cậy phía server
ADK direct tools đi qua `CosaGovernedTool` → `ToolInvocationService` → Governance → Native/MCP/Connector; DeepSeek cũng đi qua `dispatch_tool_call` → `ToolInvocationService` — cùng 1 cổng governance. Điểm bắt buộc: `ExecutionScope` (`workspace_id`, `member_id`, `permission_profile`) phải được tạo từ context tin cậy phía server, **tuyệt đối không** lấy từ dữ liệu mà LLM có thể tự sửa trong ADK session state — runtime không được tự quyết định quyền của chính mình.

### Model connectivity — refactor `ModelGateway` thành typed request/response TRƯỚC khi nối LiteLLM
Đã verify `ModelGateway.invoke()` hiện có bug thật, không chỉ là thiếu tính năng: `system_instruction` được nhận làm tham số nhưng **không bao giờ truyền vào `invoker_fn`** (chỉ dùng để ước lượng token), response content bị ép thành `content=str(raw_res)`, và token usage ước lượng bằng `len(prompt.split())`. Nếu nối `CosaModelGatewayLlm` thẳng vào contract hiện tại, multi-turn messages/system prompt/function calls/tool schema/structured output/usage token thật/finish reason đều sẽ bị mất hoặc méo.

Vì vậy, trước khi viết `CosaModelGatewayLlm`, refactor `ModelGateway` sang typed model:

```text
ModelRequest { messages, system_instruction, tools, response_schema, temperature, max_tokens, stream, metadata }
ModelResponse { content, tool_calls, usage, provider, model, finish_reason, metadata }
```

Tạo lớp `ModelProviderClient → LiteLLMProviderClient` ở tầng thấp hơn `ModelGateway` (`litellm==1.97.0` đã có sẵn trong `.venv` qua `google-adk`, chỉ cần ghim trực tiếp vào `backend/requirements.txt`). Cả `GatewayLM` (DSPy, đã verify chia sẻ đúng 1 `CircuitBreaker` registry với `ModelGateway` qua `ModelGateway.get_circuit_breaker(provider)`) và `CosaModelGatewayLlm` (ADK) cùng reuse `LiteLLMProviderClient` qua 1 hàm `cosa_litellm_invoker` (đặt ở `backend/app/workforce/agents/reliability/litellm_invoker.py` — file mới) — tránh 2 cách kết nối LiteLLM trôi dạt khác nhau.

### ADK dùng trực tiếp Tool/Skill đã có (không chỉ giao cả mission cho DeepSeek Harness)
- Tool: `CosaGovernedTool.run_async` gọi thẳng vào `backend/app/workforce/tools/invocation/service.py` (cùng pipeline `policy_gate.py`/`input_validation.py`/`output_safety.py` mà `dispatch_tool_call` của `DeepSeekHarnessAdapter` đang dùng).
- Skill: nạp qua `SkillRepository`/`skill_registry.py` thành system-instruction/context text đưa vào `LlmAgent` của ADK, dùng đúng nguồn markdown+schema hiện có (`backend/app/workforce/skills/*`). Cần xác nhận lại cơ chế nạp skill hiện tại của `DeepSeekHarnessAdapter` để đảm bảo ADK nạp đúng skill tương đương, không tự chế cơ chế mới.

### Phòng ngừa DeepSeek Harness thay đổi trong tương lai
- Code ADK không bao giờ `import DeepSeekHarnessAdapter` trực tiếp — luôn qua `agent_runtime_manager.get_runtime(profile.preferred_runtime or "deepseek_harness")` (field `preferred_runtime` đã có sẵn trong `AgentProfile`), và gọi `.health()` trước khi dispatch thay vì giả định harness luôn sẵn sàng.
- Coi `DeepSeekHarnessAdapter.resume() == NotImplementedError` là giới hạn đã biết — không thiết kế luồng ADK nào giả định resume giữa phiên hoạt động được, cho tới khi adapter hỗ trợ thật.
- Target dài hạn (không phải Phase 1): `AgentRuntime → DeepSeekRuntimeAdapter → HarnessClient {EmbeddedHarnessClient, SidecarHarnessClient}` — nếu DeepSeek đổi Python SDK/subprocess protocol/runtime khác, chỉ thay `HarnessClient`, ADK không biết gì về DeepSeek SDK.
- Hệ quả: thêm/thay 1 harness khác trong tương lai chỉ cần đăng ký adapter mới trong `AgentRuntimeManager` + đổi `preferred_runtime` ở profile liên quan — **không đổi code ADK**.

### Không đổi
`AgentRuntime` ABC, `AgentRuntimeManager`, nội bộ `DeepSeekHarnessAdapter`, `GovernanceKernel`, `ApprovalService`, `TaskBoardService`, `DelegationPolicyEngine`, `BudgetTracker`, `StuckDetector`, `QualityGateEvaluator`, `PromptRegistry`, và 2 import từ `agent_runtime.sessions.models` / `agent_runtime.profiles.definitions` (load-bearing, không xoá cây "frozen" trong phạm vi việc này).

### Phasing (thay thẳng qua 1 seam mỏng — không chạy song song dài hạn)
1. Refactor `ModelGateway` thành typed request/response + `LiteLLMProviderClient`. Viết đủ `AdkCofounderWorkflow` (model adapter, 4 specialist node theo `SPECIALIST_REGISTRY`, delegation node qua `TaskBoardService`, governed tool, session bridge + `RuntimeSession`) + **1 bộ test bắt buộc xanh trước khi merge**: gọi thử với vài fixture mission thật, xác nhận có audit row `AgentToolCall`/`AgentApproval` tạo qua `GovernanceKernel` (không bypass), risk-tier R0-R4 tự chặn/tự chạy đúng như `chief_of_staff.py` hiện tại, và `MissionResumeJob`/idempotency hoạt động đúng khi nhiều specialist hoàn tất gần nhau. Đây là bước lần trước KHÔNG làm — chính là lý do spike cũ chết mà không ai phát hiện.
2. Viết `orchestration/service.py` (seam mỏng), đổi 3 điểm gọi (`router.py`, `cosa_cofounder_service.py`, `continuation.py`) sang gọi seam thay vì `ChiefOfStaffOrchestrator` trực tiếp, chạy toàn bộ `backend/app/tests/agents/` đảm bảo không phá hành vi mission hiện có.
3. Sau khi cutover qua seam ổn định (không phải cùng lúc với bước 2), xoá `chief_of_staff.py`, cập nhật `COSA_CANONICAL_OWNERSHIP_MAP.md`/`MIGRATION_MAP.md`.

---

## Quyết định 2 — Central Control Plane: Postgres thuần, không spike InsForge

**Khung lại vấn đề**: vì production hiện KHÔNG thực sự dùng Supabase (chỉ Postgres thuần + JWT tự viết), câu hỏi thật không phải "Supabase hay Insforge" mà là **"cái gì nên đứng sau `platform_router`"**, và toàn bộ tầng đồng bộ local (`PlatformOutbox/Inbox`, `EntitlementManager`, `PlatformSyncWorker`) **không phụ thuộc** vào lựa chọn này vì nó chỉ gọi HTTP nội bộ do COSA tự viết.

### Việc cần làm trước, không phụ thuộc chọn vendor nào
`infra/supabase/migrations/001_initial_central_control_plane.sql` (366 dòng) và `deploy/central_vps/init_central_postgres.sql` (311 dòng) là **2 schema lệch nhau** cho cùng 1 khái niệm — phải hợp nhất thành 1 nguồn sự thật (khuyến nghị: đưa schema control-plane vào Alembic, giống cách schema local đã làm ở `backend/alembic/`, thay vì 2 file SQL tay).

**Đã verify (2026-08-21) 2 file này lệch nhau ngay cả về kiểu PK trung tâm**, không chỉ lệch cột: bảng `projects_registry` ở `deploy/central_vps/init_central_postgres.sql:114-129` dùng `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` + cột phụ `local_project_snowflake BIGINT`, trong khi cùng bảng đó ở `infra/supabase/migrations/001_initial_central_control_plane.sql:145-160` lại dùng `id BIGINT PRIMARY KEY DEFAULT public.generate_snowflake_id()` nhưng vẫn giữ cột `local_project_snowflake BIGINT` (vốn chỉ có ý nghĩa khi PK trung tâm là UUID) — một vết tích của drift. Theo quyết định "thuần Snowflake ID cho toàn bộ dự án" (Quyết định 5), khi hợp nhất 2 schema này **phải chốt PK trung tâm là BigInt Snowflake** (theo bản `infra/supabase/...`), xoá biến thể UUID ở `init_central_postgres.sql` và xoá cột `local_project_snowflake` dư thừa.

Cần phân biệt rõ **3 vai trò DB**, không chỉ local/cloud: (1) Personal Business DB (desktop/self-host founder, business truth ở Personal Mode), (2) Team Business DB (cloud/VPS, business truth khi workspace promote thành Team — xem single-authority ở Quyết định 3), (3) COSA Central Control Plane (account/license/entitlement/device/update). Database #2 và #3 **không nhất thiết là cùng một DB** — nếu không ghi rõ, "cloud Postgres" rất dễ trở thành 1 monolith trộn Founder finance/CRM/documents với license platform/billing COSA/device registration vào chung 1 security boundary.

### Insforge — KHÔNG dùng làm System of Record, chỉ là tool cho "generated apps" (đã chốt, không cần spike nữa)
Lý lẽ của `OPC_OS_ADK_DeepSeek.md` — "InsForge hấp dẫn vì agent-native, nhưng OPC đã tự sở hữu phần lớn capability tương tự (auth, storage, governance), dùng làm core backend ngay sẽ overlap lớn" — khớp với việc production hiện **không hề gọi SDK Supabase** (đã verify bằng grep) lẫn nguyên tắc CLAUDE.md §5/§6. Không có lý do kỹ thuật để đổi control-plane sang 1 BaaS mới khi Postgres thuần đang chạy tốt (~80MB RAM) và tầng đồng bộ local đã vendor-agnostic.

**Vị trí đúng của InsForge**: 1 tool tuỳ chọn cho DeepSeek Harness (hoặc 1 "Software Engineer Agent" specialist trong tương lai) dùng để dựng backend cho ứng dụng nội bộ do OPC sinh ra theo yêu cầu founder (vd "tạo mini CRM cho Sales") — hoàn toàn tách biệt khỏi quyết định control-plane. Không thiết kế/triển khai ngay; chỉ ghi nhận làm 1 tool candidate tương lai trong `tool_registry.py` khi có nhu cầu cụ thể, theo đúng seam đã có (Quyết định 1: `CosaGovernedTool`).

### Phasing
1. Hợp nhất 2 schema drift → 1 nguồn (Alembic hoặc chọn 1 file, sinh file kia).
2. Giữ nguyên Postgres thuần tự host làm control-plane persistence — không migration vendor nào cần làm.

### Không đổi
`PlatformOutbox/PlatformInbox/LocalEntitlementSnapshot` schema, cơ chế HMAC/signature của `EntitlementManager`, cơ chế outbox/backoff/idempotent ACK của `PlatformSyncWorker`.

---

## Quyết định 3 — Founder tự host full stack trên VPS riêng (bổ sung, không thay desktop-first)

Desktop (Flutter) vẫn là kênh chính; đây là **thêm 1 lựa chọn triển khai**, tái dùng ~90% những gì `docker-compose.yml` gốc đã có (postgres+minio+backend+worker+realtime) và pattern Caddy/TLS đã có sẵn ở `deploy/central_vps/Caddyfile`.

### Phát hiện phụ cần sửa kèm
`deploy/central_vps/docker-compose.yaml`'s `central_api` hiện build từ **cùng image monolith** với `brain-api` local (toàn bộ router workforce/founder_os/business) — chưa từng được thu hẹp về đúng control-plane. Sửa bằng biến `APP_ROLE` (`full` mặc định / `central_control_plane`), nhưng **không phải** bằng cách đọc `APP_ROLE` 1 lần rồi mount router có điều kiện trong `backend/app/main.py` hiện tại — đã verify `main.py` `import` cả 5 domain router (`founder_os`, `business`, `workforce`, `integrations`, `platform`) ở top-level **trước** khi gọi `include_router`, nên nếu chỉ bọc `include_router` trong `if APP_ROLE == ...`, tiến trình `central_control_plane` vẫn import toàn bộ dependency của business/workforce (không thu hẹp attack surface/dependency graph thật). Cần app factory thật: `app/bootstrap/create_app.py` (hàm `create_app(role)` import router có điều kiện, không import router không cần), 2 entrypoint `app/full_main.py`/`app/central_main.py`, deploy bằng `uvicorn app.full_main:app` hoặc `uvicorn app.central_main:app` tương ứng.

### File mới
- `deploy/self_host/docker-compose.yaml` — copy service từ root compose, chỉ `brain-api` lộ ra ngoài qua Caddy (TLS); `postgres`/`minio`/`agent-worker` giữ mạng nội bộ Docker, không public.
- `deploy/self_host/Caddyfile` — phỏng theo `deploy/central_vps/Caddyfile`, 1 domain → `brain-api:8000`.
- `deploy/self_host/README.md` — hướng dẫn 1 lệnh, nêu rõ cảnh báo đã biết: `docker-compose` chỉ đọc `.env` gốc, `backend/.env` KHÔNG được container đọc.
- `deploy/self_host/.env.example`
- `backend/app/bootstrap/create_app.py` — `create_app(role)`, import router có điều kiện theo `APP_ROLE`
- `backend/app/full_main.py`, `backend/app/central_main.py` — 2 entrypoint mỏng gọi `create_app("full"|"central_control_plane")`

### Sửa
- `deploy/central_vps/docker-compose.yaml` — set `APP_ROLE=central_control_plane`, đổi lệnh chạy sang `uvicorn app.central_main:app` (thu hẹp đúng phạm vi, sửa luôn lỗ hổng import-toàn-bộ có sẵn).

### Nguyên tắc single-authority (bổ sung từ `OPC_OS_ADK_DeepSeek.md`, áp dụng cho cả desktop lẫn self-host)
Không thiết kế active-active (ghi đồng thời cả local lẫn cloud cho cùng 1 aggregate dữ liệu business):
- **Personal Mode (desktop hoặc self-host 1 founder)**: Postgres local/self-host = authority cho dữ liệu business (Task/CRM/Finance/...); central control-plane chỉ là control plane cho licensing/entitlement — đúng như thiết kế `PlatformOutbox/Inbox` hiện có, KHÔNG mở rộng thành sync 2 chiều cho dữ liệu business.
- **Team Mode (nhiều Human Employee)**: khi cần cộng tác nhiều người, cloud Postgres trở thành authority cho dữ liệu business; desktop/self-host giữ vai trò cache/replica/executor cục bộ. Chuyển đổi qua 1 hành động tường minh kiểu "Promote to Team Workspace" — không tự động, không ngầm định.
- `deploy/self_host/` không được ngầm giả định business data sync 2 chiều với control-plane — nếu tương lai cần Team Mode, đó là 1 quyết định/migration riêng, có ADR riêng.

### Điểm thiết kế quan trọng
- **`desktop_worker/main.py` (loopback-only) KHÔNG chạy trong self-host mode** — có lỗ hổng đã biết (`subprocess(shell=True)` không sandbox) — tuyệt đối không expose ra ngoài; compose self-host không include service này.
- Đồng bộ entitlement/license giữ nguyên — self-host chỉ là đổi cách deploy, không đổi thiết kế đồng bộ.
- Giữ đúng nguyên tắc đã ghi ở `markdown/Structure.md:286` ("không multi-tenant SaaS vào local app") — self-host vẫn single-tenant mỗi deployment, giống desktop.

### Phasing
1. Compose + Caddyfile + README, verify tay trên 1 VPS thật.
2. `APP_ROLE` split, áp cho cả `deploy/central_vps/` (thu hẹp phạm vi VPS trung tâm của chính COSA).
3. (tuỳ chọn) script tự động hoá setup (sinh secret, chạy migration, in bước liên kết license).

---

## Quyết định 4 — Nhân viên người thật: hợp nhất định danh Agent + kích hoạt Hybrid Workforce đã có sẵn

### 4.1 — Phát hiện: schema hybrid-workforce đã tồn tại nhưng KHÔNG được nối vào dispatch thật (verified)
`Task` canonical (`backend/core/tasks/models.py`) đã có sẵn cả `assignee_id` (FK `users`), `assignee_member_id` + `owner_member_id` (FK `workforce_members`), và `execution_mode` (text tự do, giá trị dùng thật: `HUMAN`/`AGENT`/`HYBRID`) — tất cả cùng tồn tại, nullable/additive, gắn nhãn "Hybrid Workforce fields (mCOSA roadmap Phase 7, §150)". `WorkforceMember` (`backend/app/platform/organization/models.py`) đã có `member_type: HUMAN|AI_AGENT`, `human_user_id`, `agent_id`. Module ghi field này — `backend/app/platform/license/decomposition_service.py` — **thực chất là "Company Runtime"** (có kế hoạch triển khai gốc `docs/architecture/COSA_V13_1_COMPANY_RUNTIME_IMPLEMENTATION_PLAN.md` với 8 ADR, dự định nằm ở `app/modules/company_runtime/`, nhưng đợt tái cấu trúc 2026-08-18 đưa nhầm vào `platform/license/`) — nó phân rã 1 mission tuần thành các `Task` theo từng business function (LEGAL/MARKETING/SALES/TECH/FINANCE), gán `execution_mode` tương ứng, và `handoff_service.py` xử lý bàn giao **giữa các function** (không phải giữa các `WorkforceMember` cá nhân).

**Nhưng đây chỉ là schema + hiển thị, chưa phải dispatch thật**: `execution_mode`/`assignee_member_id` chỉ được đọc lại để trả JSON hoặc hiện nhãn "AI Specialist" trên dashboard (`founder_hub_service.py:77`) — **không có code nào rẽ nhánh** để: (a) khi `execution_mode="AGENT"` → dispatch thật vào pipeline canonical `workforce/agents/*`; (b) khi `="HUMAN"`/`"HYBRID"` → bắn notification/approval thật cho `WorkforceMember`. `grep` xác nhận `WorkforceMember`/`workforce_members` **0 lần** xuất hiện trong `workforce/agents/delegation/*` hay `workforce/agents/profiles/*` — 2 hệ thống (Company Runtime/Organization vs Agent Delegation canonical) đang chạy **hoàn toàn tách biệt**, dù cả 2 đều là API sống (`/api/v1/company-runtime`, `/api/v1/organization`).

### 4.2 — Fragmentation "Agent identity" là 4 chiều, không phải 2
`OPC_OS_ADK_DeepSeek.md` chỉ phát hiện xung đột `agents` vs `agent_definitions`. Thực tế verify được **4 khái niệm "ai/cái gì thực hiện công việc" hoàn toàn tách biệt, không FK chéo, không code path nối nhau**:

| # | Model | File | Bản chất | Ai dùng thật |
|---|---|---|---|---|
| 1 | `Agent` (table `agents`) | `backend/app/founder_os/tasks/models.py` | Định danh đơn giản (name/slug/system_prompt/provider/model) | FK target của `WorkforceMember.agent_id` — chỉ vậy |
| 2 | `AgentDefinition` (table `agent_definitions`) | `backend/app/workforce/models.py` | Registry "COSA Control Plane" đầy đủ: `key`, `role_title`, `department`, `agent_type`, `category`, `risk_level`, `capabilities_jsonb`, `model_config_jsonb`; có `AgentHierarchy` riêng cho org-chart | Không ai trong pipeline canonical join tới nó |
| 3 | `AgentProfile` | `backend/app/workforce/agents/profiles/schemas.py` | Pydantic **in-memory, không lưu DB**, `id` là string slug ("sales", "marketing", "cofounder") | **Đây là thứ THẬT SỰ chạy** — `AgentProfileRegistry`/`TaskBoardService`/pipeline delegation canonical dùng cái này |
| 4 | `WorkforceMember` | `backend/app/platform/organization/models.py` | Định danh nhân sự hỗn hợp (`human_user_id` HOẶC `agent_id`→#1); có `AgentRelation` riêng cho quan hệ cấp bậc — **trùng chức năng với `AgentHierarchy` ở #2** | Company Runtime/Organization module |

Không cái nào biết tới cái còn lại. Đây đúng là loại "duplicate architecture" CLAUDE.md §14 cấm, và `COSA_CANONICAL_OWNERSHIP_MAP.md` **hoàn toàn im lặng** về cả 4 (chỉ có dòng "Agent Profile Registry" nói về #3, không nhắc gì #1/#2/#4).

### 4.3 — Hướng hợp nhất đề xuất (PHẢI làm trước khi nối dispatch ở 4.4)
- Chọn `AgentDefinition` (#2, `workforce/models.py`) làm **canonical AI employee definition** — đúng hướng `OPC_OS_ADK_DeepSeek.md` đề xuất, và hợp lý nhất vì nó đã có `risk_level`/`capabilities_jsonb`/`model_config_jsonb`/`category` — gần khớp nhất với metadata tĩnh mà `AgentProfile` (#3) cần trước khi runtime nạp.
- Thêm field `profile_slug` trên `AgentDefinition` khớp đúng `AgentProfile.id` — cho phép **join được** giữa bản ghi DB (định danh, risk-level, trạng thái) và composition runtime (skills/tools/workflows) mà **không bắt buộc** `AgentProfile` phải chuyển hẳn xuống DB.
- `WorkforceMember.agent_id` đổi FK từ `agents.id` (#1) → `agent_definitions.id` (#2); xoá dần `Agent`/`agents` (#1) sau khi xác nhận không còn consumer nào khác — đúng quy tắc #6 của Ownership Map ("A directory name or old plan never proves a module is unused; consumer report plus tests are required before removal").
- **Sửa hướng cho `AgentRelation` (#4) vs `AgentHierarchy` (#2)**: không gộp `AgentRelation` vào `AgentHierarchy` để làm org-chart chung. OPC có cả quan hệ Human↔AI (Founder quản CFO Agent, Human CTO quản AI Software Engineer, AI Researcher report cho Human Product Lead) — org-chart doanh nghiệp thật không thể chỉ mô tả bằng quan hệ AI↔AI. Vì vậy:
  - Hierarchy **doanh nghiệp thật** (ai quản lý ai trong công ty, bất kể Human hay AI) chuyển xuống **`WorkforceMember`** qua entity mới **`WorkforceRelation`** — gộp các giá trị `relation` hiện có của `AgentRelation` (owner/manager/operator/reviewer/approver) vào đây, rồi deprecate `AgentRelation`.
  - `AgentHierarchy` (#2, workforce/models.py) nếu giữ thì chỉ còn là **template topology** — quan hệ AI↔AI ở mức định nghĩa/template (vd "Sales Agent template báo cáo cho CFO Agent template"), không phải org chart công ty thật.
  - Ví dụ: `AgentDefinition` (CFO Agent Template) → instantiate → `WorkforceMember` #200 ("CFO AI của MIVA") → `WorkforceRelation` `reports_to` → `WorkforceMember` #1 (Founder).
- **Định hướng dài hạn cho Permission (không bắt buộc làm ngay)**: `UnifiedPermission.principal` hiện là `USER`/`AGENT`. Vì `User` là authentication identity, `AgentDefinition` là template, còn `WorkforceMember` mới thật sự là "nhân viên nào trong công ty này" (1 người có thể thuộc nhiều workspace với role khác nhau; 1 `AgentDefinition` có thể instantiate thành nhiều AI employee ở nhiều công ty), nên dần chuyển principal sang `WORKFORCE_MEMBER`/`SERVICE`/`DEVICE`, bám theo employee instance thay vì template/user.
- **Bắt buộc**: thêm dòng mới vào `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` cho `platform/organization`, `platform/license` (đổi tên nội bộ thành `company_runtime` cho khớp thực tế — router đã tự gọi nó là `company_runtime` tại `platform/router.py:22`), và quyết định canonical ở trên.

### 4.4 — Nối `execution_mode` vào dispatch thật (chỉ làm SAU 4.3)
**Không merge `Task` vào `RunStep`** — đây là 2 khái niệm khác nhau, không phải 1 model đổi tên: `Task` là **business work item** ("Chuẩn bị Financial Forecast Q4"), `RunStep` là **execution step/attempt**. 1 Task có thể trải qua nhiều RunStep (vd `RunStep 1 → AI Finance analyse`, `RunStep 2 → Human CFO review`, `RunStep 3 → AI chỉnh lại`, `RunStep 4 → Founder approve`) — quan hệ 1-nhiều, không phải 1-1.
- `execution_mode="AGENT"`: cầu nối `Task` (core/tasks) → pipeline canonical (`TaskBoardService`/`RunStep`/`OutcomeRun`, founder_os/outcomes) qua mapping tường minh `Task → TaskExecution/task_id → RunStep(s)` — cần 1 adapter/service tạo `RunStep` tương ứng khi `Task.execution_mode="AGENT"` được kích hoạt, resolve agent qua `AgentDefinition.profile_slug` (đã hợp nhất ở 4.3).
- `execution_mode="HUMAN"`/`"HYBRID"`: bắn notification thật tới `WorkforceMember` qua `assignee_member_id` (kiểm tra cơ chế notification hiện có trước khi viết mới).
- Duyệt việc người-cho-người: tái dùng nguyên `ApprovalService.create_approval(resource_type="task", resource_id=task.id, ...)` — model đã hỗ trợ `resource_type` tuỳ ý.

### Không đổi
`TaskBoardService`, `DelegationPolicyEngine`, `RunStep`/`OutcomeRun`, cấu trúc `AgentProfile` (chỉ thêm liên kết qua `profile_slug`, không đổi shape). `handoff_service.py`/`decomposition_service.py` giữ nguyên logic phân rã theo function — chỉ đổi tên thư mục/khai báo, không đổi hành vi.

### Phasing
1. **Dọn nợ đặt tên**: đổi `platform/license` → phản ánh đúng `company_runtime` (thư mục hoặc ít nhất alias rõ ràng), cập nhật Ownership Map với các dòng mới cho `platform/organization`/`platform/license`/quyết định canonical identity. Việc này độc lập, làm trước, rủi ro thấp.
2. **Hợp nhất định danh** (4.3): `AgentDefinition.profile_slug`, đổi FK `WorkforceMember.agent_id`, xoá dần `Agent`/`agents`, thêm `WorkforceRelation` trên `WorkforceMember` (gộp giá trị `relation` của `AgentRelation` vào đó rồi deprecate `AgentRelation`; `AgentHierarchy` chỉ còn là template topology, không nhận `AgentRelation`).
3. **Nối dispatch AGENT** (4.4): `Task.execution_mode="AGENT"` → tạo `RunStep` thật qua `TaskBoardService`.
4. **Nối notification HUMAN/HYBRID** (4.4): bắn notification thật, không chỉ hiển thị nhãn.
5. (hoãn) Gán `RunStep` (mission-level) trực tiếp cho 1 `WorkforceMember` người cụ thể — chỉ làm khi có nhu cầu cụ thể, tái dùng đúng pattern provider-gate đã có ở `DelegationPolicyEngine`/`_APPROVAL_REQUIRED_PROVIDERS`.

---

## Quyết định 5 — Giữ nguyên Snowflake ID cho toàn bộ dự án (không migrate UUIDv7)

**Đã đổi hoàn toàn so với bản trước.** Bản proposal gốc (2026-08-20) đề xuất migrate toàn bộ PK từ Snowflake sang UUIDv7 trên PostgreSQL 18. Sau khi verify lại (2026-08-21, 1 Explore agent quét toàn bộ repo), quyết định cuối cùng là **không migrate** — dùng thuần Snowflake ID cho toàn bộ dự án.

### Đã verify: phạm vi thật lớn hơn nhiều so với ước tính ban đầu
- Bản gốc ước tính "~15 file model" dùng `SnowflakeIDMixin`. Verify lại cho thấy con số thật là **61 file model riêng biệt** sinh PK bằng Snowflake:
  - 19 file dùng `SnowflakeIDMixin` (`backend/app/db/snowflake_model.py`) — 66 class.
  - 42 file khác gọi `generate_snowflake_id()` **trực tiếp** làm `default` của cột PK (213 lượt), không qua mixin — gồm cả `Organization`/`Department`/`WorkforceMember` (`platform/organization/models.py`), `Task`/`TaskDependency` (`core/tasks/models.py`), và toàn bộ model mission/outcome/run-step (`founder_os/outcomes/models.py`) — kể cả sinh ID **inline trong service code** (`chief_of_staff.py:231,234`, `mission_control_bus.py:87`), không chỉ ở tầng ORM.
  - Đáng chú ý: 17 file dưới `backend/core/strategy/*.py` cũng sinh Snowflake ID trực tiếp nhưng không theo quy ước đặt tên `models.py` — loại file rất dễ bị bỏ sót khi ước lượng blast radius bằng cách grep tên file.
- Integer-ID không chỉ nằm trong schema — nó ăn sâu vào runtime/delegation qua nhiều lượt `int(request.workspace_id)`, `int(request.parent_run_id)`... ở `tool_bridge.py`, `governance/kernel.py`, `deepseek_harness.py`, `execution_router.py`, `orchestrator/service.py`.
- Không có thư viện sinh UUIDv7 nào (`uuid6`, `uuid-utils`) được cài trong `requirements.txt` hay `.venv` — sẽ là dependency hoàn toàn mới nếu triển khai.

### Quyết định cuối
- **Giữ nguyên `SnowflakeIDMixin` + pattern `default=generate_snowflake_id`** trên toàn bộ 61 file model hiện có, không đổi kiểu PK cho bất kỳ model nào.
- **Không** thêm cột `public_id UUIDv7` additive cho entity cross-boundary/public API — đây là phương án Hybrid từng được cân nhắc nhưng bị loại: quyết định cuối là thuần Snowflake, không giới thiệu UUIDv7 dưới bất kỳ hình thức nào ở giai đoạn này.
- **PG18 upgrade bị loại khỏi phạm vi tài liệu này** — lý do chính đáng duy nhất từng nêu (hàm `uuidv7()` native) không còn áp dụng khi không migrate ID. Nếu sau này có lý do PG18 độc lập (hiệu năng, tính năng khác của PG18), đó là 1 quyết định riêng, không thuộc phạm vi proposal này — không gộp chung với bất kỳ thay đổi ID nào.
- Áp dụng luôn cho schema trung tâm: khi hợp nhất `deploy/central_vps/init_central_postgres.sql` và `infra/supabase/migrations/...` (Quyết định 2), PK trung tâm chốt là **BigInt Snowflake**, không phải UUID.

### File / Phasing
Không có việc gì cần làm cho tầng ID trong phạm vi tài liệu này — không thêm dependency mới, không thêm Alembic migration đổi kiểu PK, không đổi `docker-compose.yml`/image Postgres vì lý do ID.

### Không đổi
Cơ chế Alembic hiện có, `base_class.py`, `SnowflakeIDMixin`/`backend/app/core/snowflake.py`/`generate_snowflake_id()` — toàn bộ giữ nguyên như đang chạy.

---

## Quyết định 6 — Dọn dẹp docs/code không dùng + tái cấu trúc CLAUDE.md

### 6.1 — Dọn dẹp code: đã có sẵn quy trình, chỉ cần áp dụng đúng lúc
`COSA_CANONICAL_OWNERSHIP_MAP.md` đã tự định nghĩa quy trình retire ("consumer report + tests required before removal", công cụ `scripts/report_harness_ownership.py` đã có sẵn) — không cần quy trình mới, chỉ áp dụng đúng cho 2 nhóm:

**Nhóm A — đã "Frozen retirement candidate"/"Audit required" từ trước, độc lập với các quyết định trên, có thể dọn ngay**:
- `backend/agent_runtime/{runtime,models,context,routing,trajectory}` (trừ `sessions.models`/`profiles.definitions` — load-bearing, xem Quyết định 1)
- `backend/tools`, `backend/skills`, `backend/workflows`, `backend/executors` (root scaffold)
- `backend/app/workforce/gateway` (`AgentGateway` stack — Ownership Map: "No new production code should depend on AgentGateway")
- `backend/app/integrations/channels/plugins/plugin_host.py` (stub, "Replace with Extension Registry facade")
- `backend/storage/sqlite` + `backend/agent_runtime/events/sessions` (SQLite session/event scaffold — "Select local-first authority before production promotion")

Với mỗi mục: chạy `scripts/report_harness_ownership.py`, xác nhận 0 consumer sản xuất còn lại, rồi mới xoá — không đoán từ tên thư mục.

**Nhóm B — chỉ "không dùng" SAU KHI thực thi Quyết định 1/2/4** (đã ghi trong từng phasing tương ứng, liệt kê lại đây cho gọn):
- `chief_of_staff.py`, flag `FLAG_ADK_SALES_PILOT` (sau Quyết định 1, sau khi cutover qua seam `orchestration/service.py` ổn định)
- `founder_os/tasks/models.py::Agent`/bảng `agents`, `AgentRelation` (sau Quyết định 4 bước 2)
- `infra/supabase/migrations/001_initial_central_control_plane.sql` (sau khi hợp nhất schema ở Quyết định 2 bước 1 — giữ 1 nguồn duy nhất, PK trung tâm chốt là BigInt Snowflake theo Quyết định 5)

(`SnowflakeIDMixin`/`backend/app/core/snowflake.py` **không** còn nằm trong danh sách retire — Quyết định 5 đã đổi thành giữ nguyên Snowflake ID cho toàn bộ dự án.)

### 6.2 — Dọn dẹp docs: audit có bằng chứng, không xoá theo phỏng đoán
Repo hiện có ~24 file `docs/architecture/*.md`, 5 file `docs/agent-platform/*.md`, ~32 ADR, 16 spec `markdown/*.md` — quá nhiều để khẳng định file nào chết mà không kiểm tra từng file. Chỉ có bằng chứng cụ thể cho các mục sau (phát hiện trong quá trình phân tích phiên này):
- `docs/agent-platform/ADK_INTEGRATION.md` — mô tả spike ADK giả (`agents/adk_runtime/`, đường dẫn xác nhận không còn tồn tại trên đĩa) đã bị 1 tài liệu khác (`COSA_Codebase_Audit_And_Decommissioning_Plan.md`) xếp loại "dead code POC, propose delete". Đã verify lại (2026-08-21): hiện **chưa có bất kỳ usage `google.adk` thật nào trong `backend/app`** — file này mô tả `app.agents.adk_runtime`/`SalesAdkPilotGraph` hoàn toàn chưa tồn tại trên đĩa, chỉ còn sót hằng số `FLAG_ADK_SALES_PILOT`. **Viết lại file này mô tả `AdkCofounderWorkflow` thật** (graph-based, theo Quyết định 1 đã sửa) thay vì xoá trắng — vẫn có giá trị lịch sử/ngữ cảnh nếu sửa đúng.
- `docs/agent-platform/GAP_ANALYSIS.md`, `MIGRATION_MAP.md` — **KHÔNG xoá, vẫn đang đúng và hữu ích** (đã dùng làm bằng chứng nhiều lần trong tài liệu này: 3 audit trail chưa hợp nhất, `AgentGateway` không dùng sản xuất, `context/builder.py` "audited but not enforced"). Cập nhật (không xoá) sau khi Quyết định 1 đóng được gap nào.
- `docs/architecture/COSA_HYBRID_LOCAL_POSTGRESQL_SUPABASE_INTEGRATION_PLAN.md`, `COSA_HYBRID_INTEGRATION_PHASE_1_PLAN.md` — mô tả tầm nhìn Supabase-cụ thể mà Quyết định 2 đã thay đổi (không còn nhắm Supabase, chỉ cần Postgres). Cần 1 ghi chú "superseded by tài liệu này" ở đầu file, không xoá thẳng (vẫn có lịch sử quyết định).

**Cho phần còn lại** (~20 file architecture khác, ADR, markdown specs): đề xuất chạy 1 audit pass riêng SAU KHI các quyết định chính triển khai xong (vì nhiều thứ chỉ thật sự "chết" như là HỆ QUẢ của các quyết định đó — audit trước sẽ cho kết luận sai) — dùng tiêu chí: (a) file có bị tài liệu/code nào khác còn tham chiếu không (`grep` tên file), (b) nội dung có mô tả 1 module đã bị Ownership Map đánh dấu "Frozen retirement candidate" hoặc đã xoá không. Không đưa vào phạm vi thực thi ngay của tài liệu này.

### 6.3 — Tái cấu trúc CLAUDE.md theo kiến trúc/logic mới (đã áp dụng cùng lúc lưu tài liệu này)
Giữ nguyên khung 18 mục hiện có, bổ sung các mục bị ảnh hưởng trực tiếp:
- **§2 (COSA Architecture)** — thêm dòng nêu rõ hiện trạng cụ thể: Co-founder Orchestrator = Google ADK; Agent Runtime thực thi = DeepSeek Harness qua `AgentRuntime` adapter; tra Ownership Map trước khi thêm code.
- **§5 (Business Core)** — thêm nguyên tắc: Workforce (người hay AI) phải đi qua 1 định danh hợp nhất (`WorkforceMember`).
- **Mục mới §6a (Google ADK Orchestrator)** — mirror cấu trúc §6 (DeepSeek Harness): ADK không bao giờ gọi thẳng model provider/tool/domain logic, luôn qua ModelGateway và GovernanceKernel/TaskBoardService.
- **§10 (Local First)** — thêm nguyên tắc single-authority (Personal Mode: local; Team Mode: cloud, chuyển đổi tường minh).
- **§14 (No Duplicate Architecture)** — thêm tham chiếu tới Ownership Map + case study fragmentation `Agent`/`AgentDefinition`/`AgentProfile`/`WorkforceMember`.

Các mục còn lại (1, 3, 4, 7, 8, 9, 11-13, 15-18, "Planning Before Execution") giữ nguyên.

### Phasing
1. Nhóm A (6.1) — dọn ngay, độc lập, không phụ thuộc quyết định nào khác.
2. CLAUDE.md (6.3) — đã áp dụng.
3. Nhóm B (6.1) + docs có bằng chứng (6.2 — 3 file đầu) — dọn theo đúng tiến độ từng quyết định tương ứng đã hoàn thành.
4. Audit pass diện rộng (6.2, phần còn lại) — làm sau cùng, sau khi các quyết định chính đã triển khai.

---

## Xác nhận giữ nguyên — lưu trữ file (không cần thiết kế lại)

- **Markdown/knowledge**: `markdown/` (spec gốc), `backend/skills/definitions/*.py` + `backend/skills/markdowns/*.md` qua `SkillRepository`, `docs/architecture/`, `docs/adr/` — pattern đã nhất quán, tiếp tục dùng.
- **Object storage**: `backend/app/integrations/storage/s3_client.py` (boto3 → MinIO, bucket `javis-vault`) — giữ nguyên cho cả desktop lẫn self-host (compose self-host có service `minio` riêng). Google Drive **chỉ thêm khi** có nhu cầu cụ thể từ nhân viên người thật — làm dưới dạng adapter mới cùng interface với `s3_client.py`, không dựng sẵn bây giờ.

---

## Rủi ro chính cần theo dõi

1. **ADK tự ý gọi tool bỏ qua risk-gate tất định** → phần risk-tier R0-R4/budget/stuck/quality gate trong `AdkCofounderWorkflow` phải dùng `FunctionNode` tất định (Python logic), không phải để 1 LLM agent node tự do chọn tool/quyết định risk.
2. **Test "trông an toàn" nhưng không phát hiện bypass** (đúng lỗi khiến spike ADK trước chết) → bộ test bắt buộc ở Quyết định 1 phải xác nhận có audit row `AgentToolCall`/`AgentApproval` thật, không chỉ so kết quả cuối cùng của mission.
3. **Xoá nhầm cây `agent_runtime/*`** trong lúc dọn dẹp ADK → 2 import load-bearing (`sessions.models`, `profiles.definitions`) phải giữ, ghi rõ vào ownership map.
4. **Schema drift Supabase-spec vs central_vps hiện có** → phải hợp nhất thành 1 nguồn trước khi thêm bảng/migration mới cho control-plane, không thì tiếp tục lệch thêm.
5. **`desktop_worker` bị lộ ra internet trong self-host** → không được include trong compose self-host dưới bất kỳ hình thức nào (đã có lỗ hổng `subprocess shell=True` chưa sandbox).
6. **ADK Workflow resume/replay không giữ đúng exactly-once semantics hiện có ở `continuation.py`** → nếu không có `MissionResumeJob`/idempotency key tương đương (Quyết định 1), nhiều specialist hoàn tất gần nhau có thể trigger resume mission nhiều lần.
7. **`ModelGateway.invoke()` không được sửa trước khi nối `CosaModelGatewayLlm`** → `system_instruction` sẽ âm thầm không tới được model (bug đã verify thật, không phải giả thuyết ở dòng `invoker_fn(provider, model, prompt)` hiện tại) — mission có thể chạy "được" nhưng sai hành vi vì thiếu system prompt.
8. **2 cơ chế gọi LiteLLM (DSPy `GatewayLM` và ADK `CosaModelGatewayLlm`) trôi dạt thành 2 cách kết nối khác nhau** → dùng chung 1 hàm `cosa_litellm_invoker`, không viết lại logic gọi LiteLLM ở 2 nơi.
9. **Nối dispatch `execution_mode` (Quyết định 4.4) trước khi hợp nhất định danh (4.3) xong** → sẽ tạo thêm 1 đường dispatch dùng định danh sai/cũ (`Agent`/`agents` sắp bị xoá) — bắt buộc làm đúng thứ tự 4.3 → 4.4, không đảo.
10. **Xoá `Agent`/`agents` (#1) hoặc `AgentRelation` (#4) khi vẫn còn consumer khác chưa phát hiện** → bắt buộc chạy consumer report (tương tự `scripts/report_harness_ownership.py` đã có cho agent_runtime) trước khi xoá, đúng quy tắc #6 Ownership Map.

## Verification / cách kiểm tra sau khi triển khai

- **Quyết định 1**: chạy bộ test bắt buộc (fixture mission thật qua `AdkCofounderWorkflow`), xác nhận `risk_level`/`required_approvals` đúng và có audit row `AgentToolCall`/`AgentApproval` thật (không bypass). Chạy toàn bộ `pytest` cho `backend/app/tests/agents/` hiện có để đảm bảo không phá vỡ hành vi mission cũ. Thêm: (a) test resume thật từ session events sau khi 1 `DelegationJob` chuyển terminal (không chỉ mock); (b) test nhiều specialist hoàn tất gần như đồng thời chỉ trigger đúng 1 lần resume mission (xác nhận `MissionResumeJob`/idempotency key hoạt động, giữ đúng exactly-once semantics của `continuation.py` cũ); (c) gọi `ModelGateway.invoke(..., system_instruction=..., invoker_fn=cosa_litellm_invoker)` sau khi refactor typed request/response, xác nhận `system_instruction` thực sự có mặt trong request gửi tới model — không chỉ dùng để đếm token như hiện tại.
- **Quyết định 2**: sau khi hợp nhất schema, chạy migration trên bản sao Postgres thuần self-host, xác nhận schema áp dụng sạch, không lỗi drift so với `deploy/central_vps/init_central_postgres.sql` cũ.
- **Quyết định 3**: từ máy khác, `curl https://<domain>/health` qua Caddy TLS; xác nhận `postgres`/`minio` không lộ port ra ngoài (`nmap`/`docker port`); xác nhận entitlement sync thật (kiểm tra `PlatformOutbox` được flush).
- **Quyết định 4**: (4.1-4.3) chạy `grep -rn "from app.founder_os.tasks.models import Agent"` để xác nhận danh sách đầy đủ consumer của `Agent`/`agents` trước khi xoá; test tạo `AgentDefinition` với `profile_slug` trỏ đúng 1 `AgentProfile.id` có thật, xác nhận `AgentProfileRegistry.get_profile(profile_slug)` resolve được. (4.4) tạo `Task execution_mode="AGENT"` → xác nhận có `RunStep` thật được tạo qua `TaskBoardService`, có audit row `GovernanceKernel`; tạo `Task execution_mode="HUMAN"` → xác nhận `WorkforceMember` tương ứng nhận notification thật (không chỉ đọc lại field); chạy `backend/app/tests/test_organization.py` + test suite tasks hiện có, đảm bảo không phá hành vi cũ của `decomposition_service.py`/`handoff_service.py`.
- **Model connectivity (LiteLLM)**: gọi `ModelGateway.invoke(..., invoker_fn=cosa_litellm_invoker)` với 1 provider thật (có API key test) → xác nhận nhận response thật, circuit breaker mở khi provider lỗi liên tục, và `GatewayLM` (DSPy) lẫn `CosaModelGatewayLlm` (ADK) cùng thấy breaker OPEN khi 1 trong 2 gây lỗi.
- CI hiện có (`.github/workflows/quality.yml`) phải xanh cho mọi phase (backend pytest+alembic, boundaries check) trước khi merge từng milestone.
