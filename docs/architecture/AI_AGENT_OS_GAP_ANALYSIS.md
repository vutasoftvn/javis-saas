# AI Agent OS — Gap Analysis: Blueprint vs Codebase

**Loại tài liệu:** Gap Analysis / Roadmap nguồn
**Ngày:** 2026-08-22
**Nguồn blueprint:** `markdown/AI_Agent_OS_Master_Architecture.md` (105 mục + Phụ lục A, ~5600 dòng)
**Nguồn ownership:** `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`
**Audit đi kèm (Giai đoạn 0, hoàn thành 2026-08-22):** `docs/architecture/AI_AGENT_OS_AUDIT_NOTES.md` — các mục đánh dấu **[Audit N.N — xác nhận]** bên dưới đã được cập nhật theo kết quả audit này, thay cho các câu "chưa xác nhận" ban đầu.

## Phát hiện trung tâm

`markdown/AI_Agent_OS_Master_Architecture.md` không chỉ là đề xuất trên giấy — nó đã được dùng làm spec để xây `agentos/`: code trong `agentos/` chứa comment trích thẳng số mục blueprint (`# blueprint §3.3/§20`, `# blueprint §26`, `# blueprint §34/§35/§37`, `# Blueprint §56`...). Nhưng có **3 hệ thống song song, chưa hợp nhất**, đúng loại rủi ro CLAUDE.md §14 cảnh báo (tương tự lịch sử phân mảnh Agent/AgentDefinition/AgentProfile/WorkforceMember):

| Hệ thống | Vai trò | Trạng thái | Nguồn xác thực |
|---|---|---|---|
| `agentos/` | Hiện thực hóa gần đúng blueprint (Python-native, đúng §5–§105 + Phụ lục A) | **Inert, parallel** — chưa wire vào production (ADR-AGENTOS-001) | COSA_CANONICAL_OWNERSHIP_MAP.md dòng 70 |
| `legacy/agent_runtime/workforce/agents/*` | ADK orchestration + DeepSeek Harness adapter + GovernanceKernel + TaskBoardService + ModelGateway | **Canonical production** — hệ thống CLAUDE.md §2/§6/§6a gọi là "current concrete instantiation" | COSA_CANONICAL_OWNERSHIP_MAP.md dòng 21–33 |
| `services/` (Encore) | Business OS: identity/operations/commercial/finance-legal, CRUD đầy đủ | **Pre-production** — 0 consumer gọi qua HTTP | COSA_CANONICAL_OWNERSHIP_MAP.md dòng 68–70 |

Mọi đề xuất hoàn thiện dưới đây phải tôn trọng bảng ownership này — không tạo thêm hệ thứ 4, không tự ý hợp nhất mà chưa qua ADR (CLAUDE.md §16 + ownership-map "Rules for new code").

---

## PHẦN A — Đối chiếu chi tiết theo 10 nhóm chức năng

### A1. Agent Core & Runtime (blueprint §5–§7, §55, §58–§60, §73, §89)

| Blueprint đòi hỏi | agentos/ (Python-native) | legacy/agent_runtime (production) |
|---|---|---|
| ContextBuilder | `agentos/core/context_builder.py` ✅ | context assembly rải trong orchestration nodes, chưa tách thành 1 class rõ ràng — cần audit |
| Planner | `agentos/core/planner.py` (MVP reactive/ReAct) ✅ | ADK planning node trong `orchestration/adk/nodes/` |
| Executor + tool loop | `agentos/core/executor.py` ✅ | `execution/service.py`, `execution/manager.py` |
| PolicyEngine (ALLOW/DENY/REQUIRE_APPROVAL) | `agentos/core/policy.py` ✅ đúng pattern §50 | `governance/policy_engine.py` (PermissionLevels L0_READ→L3_EXECUTE — vocabulary khác) + `cosa_core/governance/policy_engine.py` (bản thứ 3!) |
| TraceRecorder | `agentos/core/trace.py`, `trace_sink.py` (SqliteTraceSink) ✅ | OpenTelemetry qua `backend/core/telemetry.py` — 2 cơ chế trace khác nhau, không hợp nhất |
| Model abstraction (`ModelProvider` protocol) | `agentos/core/adapters/model_gateway.py` (DeepSeek/OpenAI/OpenRouter/Anthropic qua httpx) ✅ | `reliability/model_gateway.py` (ModelGateway + ModelProfileRegistry, LiteLLM) — 2 ModelGateway riêng biệt, tên trùng nhưng không cùng class |

**Kết luận A1:** Toàn bộ Agent Core do blueprint đặc tả đã có bản build 1:1 trong `agentos/core/`, nhưng production thật dùng kiến trúc khác (ADK + DSH). Không phải "thiếu code" — là **2 kiến trúc song song cùng giải 1 bài toán**.

### A2. Multi-Agent (blueprint §9–§10)

- Sequential: `agentos/agents/sequential.py` (`SequentialPipeline`).
- Parallel: `agentos/agents/parallel.py` (`ParallelFanOut`).
- Supervisor: `agentos/agents/supervisor.py` (`SupervisorAgent`, chọn specialist theo relevance score) + legacy ADK `orchestration/adk/nodes/specialist_delegation_node.py` (chạy production qua `TaskBoardService`).
- Debate/Critic: `agentos/agents/debate.py` (`DebateLoop`, generator↔critic tối đa `max_rounds`).
- **[Sửa lại 2026-08-22]** Bản phân tích trước ghi nhầm "Debate/Critic: không tìm thấy" — do 2 lượt Explore đầu chỉ liệt kê thư mục nông, chưa đọc hết `agentos/agents/`. Thực tế cả 4 pattern §9.2 (sequential/parallel/supervisor/debate) đã có trong `agentos/agents/`. Gap thật duy nhất còn lại của nhóm này (đã đóng ở Giai đoạn 3.1): `ParallelFanOut` chưa tích hợp vào `WorkflowEngine` — nay có `ParallelStep` trong `agentos/workflows/steps.py`.

### A3. Memory & Knowledge (blueprint §11–§15, §67)

- `agentos/memory/`: `store.py` (MemoryStore Protocol + InMemoryMemoryStore + PgVectorMemoryStore — đúng §12), `models.py` (MemoryItem đủ 5 kind: WORKING/EPISODIC/SEMANTIC/PROCEDURAL/ORGANIZATIONAL — đúng §11.1), `consolidation.py` (EpisodeConsolidator — đúng §14).
- **Gap:** không có Procedural memory consolidation thật (chỉ có model kind, chưa có pipeline chuyển "cách làm hiệu quả" → procedural memory).
- legacy: chỉ có `agent_runtime/agent_runtime/memory/models.py` tối giản — Memory là điểm `agentos/` vượt trội rõ rệt so với production.
- Knowledge Layer (§66, ingest→parse→chunk→embed→index): **[Audit 0.3 — xác nhận]** chưa implement ở đâu. `agentos/memory/retrieval.py` chỉ có term-overlap thuần túy (`score_relevance()`), không gọi embedding, không có vector DB; không tìm thấy bảng `knowledge_sources` trong bất kỳ migration nào.

### A4. Tool / MCP (blueprint §16–§17)

- `agentos/tools/registry.py` (ToolRegistry, gắn `permission_class`) + `encore_client.py` (gọi `services/` qua HTTP) ✅.
- `backend/core/tool_registry.py` + `tool_dispatch.py` — canonical production, GovernanceKernel resolve ToolSpec qua đây.
- MCP: `legacy/agent_runtime/workforce/tools/transports/mcp_adapter.py` (`MCPToolAdapter`, dòng 7-60, JSON-RPC qua httpx) là interface MCP thật trong production. **[Audit 0.5 — xác nhận]** `agentos/tools/` **không có** MCP adapter (grep rỗng) — feature gap thuần túy, không phải duplicate risk.
- Không phát hiện trùng lặp nghiêm trọng ở layer này vì `agentos/tools/` chỉ nói chuyện với `services/`, không đụng `backend/core/tool_registry.py`.

### A5. Skill Ecosystem (blueprint §18–§37 + toàn bộ Phụ lục A)

Phần blueprint đặc tả chi tiết nhất (63 mục Phụ lục A) và **hiện thực hóa đầy đủ nhất** trong `agentos/`:

- `agentos/skills/registry.py` (SkillRegistry, manifest.yaml discovery) ✅ đúng §20/§30.
- `agentos/skills/router.py` (scoring relevance/trust/quality) ✅ đúng §26.
- `agentos/skills/loader.py`, `instruction_loader.py` (progressive disclosure) ✅ đúng §24, Phụ lục A §5.2.
- `agentos/skills/manifest.py` (SkillManifest: metadata/capability/trust/permissions/risk) ✅ đúng §21, Phụ lục A §8.1.
- `agentos/skills/supply_chain/` (pipeline.py, artifact_store.py, pinning.py, scan.py, lifecycle.py) ✅ đúng §27–§29, Phụ lục A §13.
- `skillpacks/{tasks,okr,twelve-week-year,marketing/*,core/weekly-review}/` — skill thật (`manifest.yaml` + `SKILL.md`). **[Audit 0.4 — xác nhận, đã sửa lại kết luận 2026-08-22]** `SkillRegistry.discover()` (`agentos/skills/registry.py:35-47`) đọc trực tiếp filesystem và đánh dấu ACTIVE ngay, không gọi `supply_chain/pipeline.py`. **Đây KHÔNG phải lỗ hổng an toàn** — là hành vi cố tình đúng thiết kế: docstring của cả `SkillRegistry` lẫn `SupplyChainPipeline` đều ghi rõ pipeline chỉ áp dụng cho EXTERNAL skill, "internal skillpacks bypass this entirely". Mọi `skillpacks/*/manifest.yaml` thật đều khai `trust.tier: T0` (đã grep xác nhận), và theo đúng bảng trust tier blueprint §29 (T0 = internal = trusted), skill T0 không cần qua scan. `scan_manifest()` chỉ đánh giá rủi ro cho tier T3/T4 — wire pipeline vào cho skill T0 sẽ không đổi hành vi gì. Bản phân tích lần đầu đọc thiếu docstring/trust-tier context nên kết luận nhầm thành "lỗ hổng an toàn"; xem `docs/architecture/AI_AGENT_OS_AUDIT_NOTES.md` §0.4 để biết chi tiết correction.
- **Gap:** Skill Review Agent, Skill Curator Agent, Skill Eval Agent (Phụ lục A §45–§47) — không tìm thấy, blueprint tự nói "optional specialist" nên hợp lý.
- production (`legacy/`): không có khái niệm Skill/SKILL.md nào — muốn skill ecosystem chạy production phải đi qua `agentos/` hoặc port logic sang legacy.

### A6. Business OS / Encore (blueprint §38–§45)

`services/` có đủ 4 cluster: `identity` (auth/org/workspace/token), `operations` (task/okr/twelve-week-year/project/initiative + events task.completed/okr.progress_updated), `commercial` (lead/opportunity/account/contact/customer/billing/marketing), `finance-legal` (accounting-period/profile/regime/financial-transaction/legal-*). Khớp gần 1:1 danh sách domain blueprint §38 — chỉ thiếu **Notifications** như service riêng (có thể đã gộp nơi khác — audit).

**Gap lớn nhất của toàn bộ phân tích:** `services/` đã sẵn sàng schema+logic nhưng **0 consumer** — thiếu wiring, không thiếu code. `agentos/tools/encore_client.py` đã tồn tại và có thể gọi `services/`, nhưng chưa có integration test end-to-end xác nhận agent → services → caller chạy được.

### A7. Event & Workflow Engine (blueprint §46–§47)

- Event naming `entity.action` chuẩn hóa đúng ở `services/shared/events.ts` (Encore Topic, at-least-once) và `agentos/core/events.py` (EventEnvelope + InMemoryEventBus — chỉ single-process, chưa production-durable, comment "Phase 8 scope" trong code).
- `agentos/workflows/engine.py`: DeterministicStep/AgentStep/ApprovalGateStep, pause/resume qua approval — đúng khung §47.
- `legacy/backend/integrations/workflows` (canonical production, ownership map dòng 35–36) có WorkflowDefinition/Version/Run/Step/Approval + router — **workflow engine thứ 2** song song với `agentos/workflows/`.
- **[Audit 0.1 — xác nhận]** retry, compensation, parallel branch **thiếu ở cả 2 workflow engine**, không riêng `agentos/`. Điểm khác biệt thật duy nhất: chỉ `legacy/backend/integrations/workflows` có version history (`WorkflowVersion`, `version_no`); `agentos/workflows/` không có. Xem `docs/architecture/AI_AGENT_OS_AUDIT_NOTES.md` §0.1.

### A8. Governance & Permission (blueprint §48–§51, §85–§86, §96)

- `agentos/core/policy.py` + `approval.py`: PolicyEngine (ALLOW/DENY/REQUIRE_APPROVAL), PermissionClass đủ 11 giá trị đúng §30, ApprovalService với Approval model gần giống `apr_123` mẫu §49.
- **Thiếu:** RBAC, audit log persistent — cả blueprint (§48, §12) lẫn `agentos/` chưa có.
- production: `GovernanceKernel` (`legacy/agent_runtime/workforce/agents/governance/kernel.py`) canonical thật, nhưng dùng vocabulary khác (`PermissionLevels L0_READ→L3_EXECUTE`) — không tương thích trực tiếp với `PermissionClass` 11-giá-trị của `agentos/`. Điểm dễ gây nhầm lẫn nhất nếu 2 phía cùng sửa governance mà không biết nhau.

### A9. Evaluation & Observability & Cost (blueprint §51–§57)

- Trace: `agentos/core/trace.py` + `SqliteTraceSink` (tree qua parent_span_id, hiện flat theo comment "honest limitation") vs production OpenTelemetry (`backend/core/telemetry.py`) — 2 cơ chế khác nhau.
- Cost: `RunMetrics` (agentos/observability/metrics.py) mới có latency/span_count/tool_call_count — **không có token/cost tracking**, comment tự nhận "later hardening". Blueprint §56 yêu cầu token in/out, model cost, cost per outcome — chưa có ở bất kỳ đâu.
- Evaluation (§51–§54): **[Audit 0.2 — xác nhận]** eval harness cơ bản **đã có** — `agentos/evals/agent_eval.py` (`evaluate_agent_run()`) và `agentos/evals/workflow_eval.py` (`evaluate_workflow()`), có test tham chiếu trong `legacy/backend/tests/`. Còn thiếu: **[Sửa lại 2026-08-22]** Business Outcome Eval **đã có** (`agentos/evals/business_outcome_eval.py`, bỏ sót ở lần đọc trước) — chỉ Skill Eval và Model Eval còn thiếu (2/5 loại eval trong §51).

### A10. Self-Improvement (blueprint §34–§37, §90, §94–§97, Phụ lục A §20/§40–§52)

`agentos/improvement/`: `gap_detection.py` (đúng §35), `distillation.py` (`distill_skill()` đúng §37/Phụ lục A §41), `proposal.py` (đúng §35/§90), `hierarchy.py` (đúng §36), `approval_gate.py` (đúng §96). Phần **build đầy đủ nhất, trung thành nhất với blueprint**, nhưng vì `agentos/` chưa wire production nên vòng lặp self-improvement **chưa từng chạy trên dữ liệu thật**.

---

## PHẦN B — Ma trận trạng thái tổng hợp

| Nhóm | Đủ theo blueprint trong `agentos/`? | Có trong production (`legacy/`)? | Đã hợp nhất? | Rủi ro trùng kiến trúc |
|---|---|---|---|---|
| Agent Core/Runtime | ✅ | ✅ (khác thiết kế) | ❌ | Cao — 2 ModelGateway, 2 PolicyEngine tên khác nhau |
| Multi-Agent | ✅ đủ cả 4 pattern §9.2 (sequential/parallel/supervisor/debate) + `ParallelStep` đã nối vào workflow | ✅ (ADK, qua `TaskBoardService`) | ❌ | Trung bình |
| Memory | ✅ vượt trội, **nay có cả Procedural consolidation** | ⚠️ tối giản | ❌ | Thấp |
| Tool/MCP | ✅ (chỉ nói chuyện services/) | ✅ canonical | Không xung đột trực tiếp | Thấp |
| Skill Ecosystem | ✅ đầy đủ nhất; supply_chain cố tình chỉ áp dụng cho EXTERNAL skill (T0 nội bộ bypass đúng thiết kế — không phải gap) | ❌ không tồn tại | N/A | Thấp |
| Business OS (services/) | ✅ pilot HTTP thật cho `task.*` (Giai đoạn 2) | services/ commercial/finance-legal vẫn chưa có pilot tương tự | ❌ | Trung bình |
| Event/Workflow | ✅ retry/compensation/parallel/version-history đủ cả (Giai đoạn 3.1–3.3 + ADR-015) | `legacy/backend/integrations/workflows` không còn tính năng nào hơn `agentos/workflows/` | ❌ (2 engine song song, nhưng agentos/ đã đủ tính năng để cutover khi ADR-013 tới lượt) | Trung bình |
| Governance/Permission | ✅ khung + audit log bền vững (3.4) + **PermissionLevel/ExecutionMode đã port (ADR-014 bước 1)**; cutover thật (bước 2, per-tool risk_level) cố tình chưa làm; RBAC vẫn thiếu | ✅ vocabulary khác | ❌ | Trung bình (đã có primitives chung, chỉ còn thiếu wiring) |
| Eval/Observability/Cost | ✅ Agent + Workflow + Business Outcome Eval (`agentos/evals/`); **token/cost tracking thật (Giai đoạn 3.5)**; thiếu Skill Eval + Model Eval | OpenTelemetry riêng | ❌ | Trung bình |
| Self-Improvement | ✅ đầy đủ nhất, chưa chạy thật trên dữ liệu production | ❌ | N/A | Thấp |
| Knowledge Layer | ❌ **xác nhận chưa implement** (chỉ term-overlap, không embedding/vector DB) | ❌ | N/A | Thấp — chưa ai làm |
| Tool/MCP adapter | ❌ **xác nhận `agentos/tools/` chưa có MCP adapter** | ✅ `MCPToolAdapter` production | N/A | Thấp — feature gap, không trùng |

---

## PHẦN C — Roadmap giai đoạn (khung, chi tiết task ở Phần D)

Nguyên tắc: mọi giai đoạn bắt đầu bằng audit/ADR trước khi viết code — không tạo hệ thứ 4, không tự hợp nhất khi chưa có quyết định rõ ràng (CLAUDE.md §1, §14, §16).

- **Giai đoạn 0 — Audit** ✅ **hoàn thành 2026-08-22** — xem `AI_AGENT_OS_AUDIT_NOTES.md`. Kết quả: (1) cả 2 workflow engine đều thiếu retry/compensation/parallel, chỉ legacy có version history; (2) eval harness Agent/Workflow đã có trong `agentos/evals/`, thiếu Skill/Business Outcome/Model Eval; (3) Knowledge Layer xác nhận chưa implement; (4) skillpacks/ bỏ qua supply_chain pipeline — lỗ hổng an toàn cần ưu tiên; (5) `agentos/tools/` chưa có MCP adapter.
- **Giai đoạn 1 — ADR** ✅ **hoàn thành 2026-08-22**, user quyết:
  - `docs/architecture/adr/ADR-013-agentos-supersedes-legacy-agent-runtime.md` — `agentos/` là target, `legacy/agent_runtime` phased out dần (không xóa ngay, chỉ dừng nhận code mới, cutover từng capability khi có parity).
  - `docs/architecture/adr/ADR-014-permission-model-L0-L3-canonical.md` — vocabulary canonical là `PermissionLevel` (L0_READ/L1_SUGGEST/L2_DRAFT/L3A_EXECUTE_WITH_APPROVAL/L3_EXECUTE) từ `legacy/agent_runtime/cosa_core/governance/policy_engine.py`, port vào `agentos/core/policy.py` thay cho `PermissionClass` làm cơ chế quyết định chính; `PermissionClass` giữ lại làm tag phân loại tool.
  - `docs/architecture/adr/ADR-015-workflow-engine-agentos-canonical.md` — `agentos/workflows/` là canonical, port version-history từ `legacy/backend/integrations/workflows` (tính năng duy nhất bên đó có mà agentos thiếu); retry/compensation/parallel xây mới trực tiếp trong `agentos/workflows/` vì cả 2 bên đều thiếu.
- **Giai đoạn 2 — Pilot end-to-end** ✅ **hoàn thành 2026-08-22**: `task_create`/`task_list`/`task_update_status` verified qua real HTTP tới `services/` sống (không mock) — `tests/agentos/test_services_pilot_e2e.py` (3/3 pass, skip an toàn nếu server không chạy). Phát hiện + sửa gap thật khi làm: `task.created` event đã định nghĩa ở `shared/events.ts` nhưng chưa từng publish — nay `createTask` publish đúng 1 lần cho insert thật (dùng Postgres `xmax = 0` để không publish lại khi idempotency-key retry), verify bằng `vi.spyOn` trong `services/operations/task.test.ts` (117/117 pass, `tsc --noEmit` sạch). `tests/agentos` suite đầy đủ: 236/236 pass (không phá gì hiện có). Chi tiết: `COSA_CANONICAL_OWNERSHIP_MAP.md` mục "agentos/ + services/ migration status". Còn lại: commercial/finance-legal/identity (ngoài workspace-create) vẫn chưa có pilot HTTP tương tự — không tự nhận "Phase 1 parity" cho các cluster đó là đã verify sống.
- **Giai đoạn 3 — Lấp gap trong `agentos/`** ✅ **hoàn thành 2026-08-22** (259/259 test pass, không phá gì hiện có):
  - 3.1 `ParallelStep` (`agentos/workflows/steps.py`) tích hợp `ParallelFanOut`-style fan-out vào `WorkflowEngine`, merge kết quả nhiều nhánh vào 1 output key.
  - 3.2 `RetryStep` — retry step con tối đa N lần khi FAILED, cố tình từ chối bọc `ApprovalGateStep` (quyết định governance không phải lỗi để retry).
  - 3.3 `CompensatingStep` + `WorkflowEngine._run_compensations` — rollback best-effort theo thứ tự ngược khi workflow FAILED (kể cả khi approval bị denied lúc resume), lỗi compensate được ghi vào `state["_compensation_errors"]` chứ không chặn các rollback khác.
  - 3.4 `agentos/core/audit_sink.py` (`SqliteAuditSink`) — audit trail bền vững cho `PolicyEngine.evaluate()` và `ApprovalService.request_approval()`/`decide()`, `Executor` thread `run_id` xuống để truy vấn lịch sử approval của 1 run cụ thể qua `export_run()`.
  - 3.5 `TokenUsage` thật (không đoán) trong `ModelResponse`, populate từ response API thật của OpenAI-compatible/Anthropic provider; `RunMetrics` cộng dồn input/output tokens; `cost_usd` chỉ tính khi caller tự cung cấp `pricing_table` thật (không hardcode giá — xem `agentos/observability/pricing.py`).
  - 3.6 `ProceduralConsolidator` (`agentos/memory/consolidation.py`) — episodic lặp lại (theo `pattern_tag` tường minh, không giả vờ có semantic clustering vì Knowledge Layer chưa tồn tại) đủ ngưỡng `min_occurrences` thì tạo 1 `MemoryItem kind=PROCEDURAL`, không tạo trùng lặp khi gọi lại.
- **Giai đoạn 4 — Multi-agent còn thiếu**: ✅ **không còn việc phải làm** — xem sửa lại ở Phần A2, Debate/Critic đã tồn tại sẵn (`agentos/agents/debate.py`), không phải gap thật.
- **Giai đoạn 5 — Tài liệu hóa** ✅ **hoàn thành 2026-08-22**: 10 spec tại `docs/architecture/specs/01-...` đến `10-...` (theo đúng mục 104 của blueprint gốc), mỗi spec neo rõ áp dụng cho `agentos/` hay `legacy/agent_runtime` hay cả hai + trạng thái hiện tại + còn thiếu; `COSA_CANONICAL_OWNERSHIP_MAP.md` đã ghi nhận toàn bộ gap-closing work của Giai đoạn 3; `markdown/AI_Agent_OS_Master_Architecture.md` đã đánh dấu "Historical baseline" ở đầu file, trỏ về specs/ và gap analysis này.

Chi tiết task-level (file đụng tới, acceptance criteria, điều kiện chuyển giai đoạn) xem trong kế hoạch thực thi gốc đã lưu tại phiên làm việc — sẽ được tách thành các ADR/spec riêng ở Giai đoạn 1 và 5.
