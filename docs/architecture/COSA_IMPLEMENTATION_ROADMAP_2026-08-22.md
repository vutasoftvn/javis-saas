# COSA — Đối chiếu tài liệu kiến trúc & Kế hoạch triển khai hoàn chỉnh

## Context

`COSA_CANONICAL_ARCHITECTURE_FUNCTIONAL_IMPLEMENTATION_GUIDE_REVISED_CHAT_2026-08-22.md` (2874 dòng, tại root repo) là tài liệu kiến trúc mới nhất, tự nhận là authority cao nhất sau ADR. Yêu cầu của user: đối chiếu tài liệu này với codebase thật, phản biện nếu cần để thống nhất, sau đó viết plan triển khai **theo đúng thứ tự các mục trong tài liệu** (§4.1 → §18), không sắp xếp lại theo mức độ rủi ro/độ sẵn sàng.

Đã dùng 3 Explore agent song song để kiểm chứng từng phần tài liệu với code thật (`agentos/`, `services/`, `docs/architecture/`, `skillpacks/`), và 1 Plan agent để dựng roadmap chi tiết từ các phát hiện đó. Kết luận đối chiếu:

- **Tài liệu về cơ bản khớp với code và với 2 tài liệu cùng ngày khác** (`COSA_ARCHITECTURE_REVIEW_2026-08-22.md`, `COSA_ARCHITECTURE_ADJUSTMENT_ADDENDUM_2026-08-22.md`) — không có mâu thuẫn cần phản biện lớn. `COSA_CANONICAL_OWNERSHIP_MAP.md` và extraction plan cũ **đã được sửa (chưa commit)** để khớp tài liệu mới — việc "supersede" mà tài liệu mô tả thực chất đã đang được thực thi trong working tree.
- **Đề xuất `backend/cosa_core/` bị bác bỏ đúng đắn** — lý do chính xác là nó sẽ tạo ra Control Plane thứ hai (Python) trùng với `services/control-plane` + `services/identity` hiện có bằng TypeScript, không chỉ vì `backend/` không còn tồn tại.
- Hai gap P0/quan trọng nhất tài liệu nêu ra (**trace redaction §7.4**, **composition root §9.2**) **đã có code sửa sẵn nhưng chưa commit** trong `agentos/core/{redaction.py,trace_sink.py,factory.py,runtime.py,adapters/contracts.py}` — cần land trước tiên vì mọi việc downstream phụ thuộc vào ContextBuilder/ToolRegistry/trace sink ổn định.
- Gap lớn nhất về mặt tính năng: **Strategy & Startup Methodology domain (§4.3)** — tài liệu gọi đây là "bổ sung quan trọng nhất từ Founder OS" nhưng 10/12 entity (assumptions, experiments, evidence, gate_evaluations, decision_records, next_action_candidates...) hoàn toàn chưa tồn tại trong schema/migration.
- Vi phạm boundary đã xác nhận: `services/realtime_agent/voice_tools.py` vẫn `sys.path.insert` sang `legacy/backend/` và gọi `SessionLocal()` trực tiếp — đúng chiều bị cấm ở §3.1.
- `agentos/api/` (Text Chat API §17.1) và `agentos/orchestration/adk/` (§9.3) hoàn toàn chưa tồn tại — đây là phần greenfield lớn nhất.

Kế hoạch dưới đây bám theo thứ tự tài liệu như user yêu cầu, đánh dấu CURRENT/TRANSITION/TARGET theo đúng 3 trạng thái tài liệu quy định (§0.2), và liệt kê file path thật để có thể thực thi trực tiếp.

---

## Deliverable & thứ tự xuất bản tài liệu (làm trước Phase 0a)

1. Lưu bản kế hoạch này (sau khi đã tích hợp toàn bộ phản biện ở trên) vào repo tại `docs/architecture/COSA_IMPLEMENTATION_ROADMAP_2026-08-22.md`, dẫn chiếu từ `COSA_CANONICAL_OWNERSHIP_MAP.md` như "Active implementation plan" theo đúng thứ tự ưu tiên tài liệu ở §0.1 của guide gốc.
2. Sau khi roadmap tổng đã nằm trong repo, viết **plan chi tiết riêng cho từng phase** (mỗi phase 1 file, dưới `docs/architecture/roadmap/phase-0-land-wip.md`, `phase-1-tenant-rbac.md`, `phase-2-strategy-domain.md`, ... `phase-12-hardening.md`) — mỗi file chi tiết hoá: danh sách task cụ thể, file/migration sẽ tạo, test cần viết, và tiêu chí acceptance ở mức implement-ready (không chỉ mục tiêu như roadmap tổng). Việc này làm tuần tự, ưu tiên viết chi tiết Phase 0-2 trước (đang chặn mọi việc khác), các phase sau viết chi tiết ngay trước khi bắt tay thực thi (tránh chi tiết hoá quá sớm rồi lại phải sửa khi hiểu biết thay đổi).
3. Không bắt đầu code Phase 0a/0b (commit WIP) trước khi bước 1-2 hoàn tất, để đảm bảo có tài liệu tham chiếu chung trước khi chỉnh sửa.

---

## Phase 0 — Land WIP đã có sẵn + P0 fix (chặn mọi phase sau)

### 0a. Trace redaction (§7.4 — P0 security)
- **CURRENT (trước fix):** `agentos/core/trace_sink.py` ghi raw JSON payload không redact.
- **TRANSITION (đã code, chưa commit):** `agentos/core/redaction.py` (exact-key match, case/separator-insensitive, đệ quy, non-mutating) đã được wire vào `trace_sink.py` (`redact_payload(event.payload)`), có test đầy đủ (`tests/agentos/test_redaction.py`, `tests/agentos/test_trace_sink.py`).
- **Việc cần làm:** review kỹ diff, xác nhận coverage đủ pattern nhạy cảm, `git add` + commit riêng cho fix P0 này.
- **Acceptance:** mọi payload trace đi qua `redact_payload()` trước khi persist; test suite pass; không còn field như `api_key`, `password`, `authorization` xuất hiện raw trong SQLite trace.

### 0b. Composition root (§9.2)
- **CURRENT (trước fix):** `build_default_runtime()` tạo `ToolRegistry()` rỗng, `AgentRuntime` build `ContextBuilder(tool_registry)` thiếu memory/skills/knowledge.
- **TRANSITION (đã code, chưa commit):** `build_cosa_agent_plane()` mới trong `agentos/core/factory.py` wire đủ `registry.register_cluster_tools()`, memory_retriever, skill_router, skill_instruction_loader vào `AgentRuntime`; `runtime.py` đã nhận và forward các tham số này; `agentos/core/adapters/contracts.py` định nghĩa `AgentRuntimeAdapter` Protocol. Có test `test_factory_composition.py`, `test_runtime_adapter_contract.py`, `test_runtime_convergence.py`.
- **Việc cần làm:** xác nhận `build_cosa_agent_plane()` là entrypoint production duy nhất (grep toàn repo xem còn ai gọi `build_default_runtime()` không), commit.
- **Acceptance:** không còn code path production nào gọi hàm cũ; test composition pass; governance/approval hoạt động độc lập với model provider (theo `test_runtime_convergence.py`).

### 0c. `agentos/improvement/` — đã điều tra, quyết định: **KEEP**
- Không phải dead code — là implementation có chủ đích của **Phase 10 Self-Improvement loop** (commit gốc `f722f6a — feat(agentos): implement Phase 10 self-improvement loop`, có implementation plan riêng từ trước). Gồm `gap_detection.py, proposal.py, approval_gate.py, hierarchy.py, distillation.py`, có test suite full lifecycle: failure/eval history → `GapDetector` → skill candidate → `SupplyChainPipeline` → human `ApprovalService` → promotion → ACTIVE. Sau restructure module được chuyển chủ động từ `backend/agentos/...` lên root `agentos/...`.
- Phần thiếu thật: `GapDetector` hiện nhận `CapabilityOutcome` do caller đưa vào — chưa wire với eval history thật (production wiring gap, không phải thiết kế sai).
- **Việc cần làm:** thêm `agentos/improvement/README.md` ghi rõ ownership = `agentos/improvement/`, operational status = `IMPLEMENTED / TESTED / NOT YET WIRED TO PRODUCTION EVAL PIPELINE`; đưa vào `COSA_CANONICAL_OWNERSHIP_MAP.md`. Việc wire vào eval pipeline thật để làm ở Phase 10 (Observability & Eval taxonomy), không phải Phase 0.

---

## Phase 1 — Platform, Identity, TenantContext, RBAC nền tảng (§4.1, §4.2, §8, §5.1)

### 1a. Unified TenantContext (§4.2)
- **CURRENT:** thông tin rải rác ở `services/identity/services/workspace.service.ts`, `auth.service.ts`; mỗi handler tự resolve company/workspace/role.
- **TARGET:** một type `TenantContext { company_id, workspace_id, user_id, workforce_member_id?, membership_role, permissions, correlation_id }` tại `services/shared/types/tenant_context.ts`, có resolver dùng chung ở control-plane + identity, mọi handler lấy context qua đây thay vì tự đoán.
- **Acceptance:** test đổi company/workspace context cập nhật đúng; correlation_id sinh/forward xuyên suốt request; không handler nào tự suy company/workspace từ nguồn khác nhau.

### 1b. WorkforceMember — chỉ verify, không xây lại
- **CURRENT (đã xác nhận đầy đủ):** model hợp nhất tại `services/identity/services/organization.service.ts`, schema `identityWorkforceMembers` (`services/shared/db/schema/identity.ts`), migration `2_create_workforce.up.sql`. Cảnh báo "4 duplicate models" (2026-08-20) đã được giải quyết — **không tạo model mới**.

### 1c. RBAC decision function bước đầu (§8.5)
- **CURRENT (đã kiểm tra code thật):** `agentos/core/policy.py::PolicyEngine.evaluate_for_agent()` hiện **chỉ** làm `AgentPermissionLevel × ToolRisk × ToolPermission` — **chưa có RBAC (role) trong công thức**, và hard-code mọi risk `critical` thành `REQUIRE_APPROVAL` bất kể role/level. Control Plane (`services/control-plane`, migration 1) hiện chỉ seed role `founder, co-founder, user` ở company scope — **chưa có `auditor`**.
- **TARGET (scope Phase 1):** một policy kernel tất định đúng nghĩa intersection (không phải `max(restrictiveness)` độc lập từng bảng — cách đó khiến `critical` luôn thắng và Founder+L3 không bao giờ `ALLOW`):

```python
class ToolRiskLevel(str, Enum):
    LOW = "low"; MEDIUM = "medium"; HIGH = "high"; CRITICAL = "critical"

class ToolPermission(str, Enum):
    READ_ONLY = "read_only"; SCOPED_WRITE = "scoped_write"; ADMIN_WRITE = "admin_write"

def evaluate_access(*, role: str, agent_permission_level: PermissionLevel,
                     tool_risk_level: ToolRiskLevel, tool_permission: ToolPermission) -> PolicyDecision: ...
```

  Ma trận tối thiểu Phase 1 (role × risk, sau đó AgentPermissionLevel siết tiếp trong ceiling mà role cho phép):

  | Role | Read | Write low/medium | High | Critical |
  |---|---:|---:|---:|---:|
  | founder | ALLOW | ALLOW | ALLOW với L3 | ALLOW với L3, approval nếu <L3 |
  | co-founder | ALLOW | theo agent level | REQUIRE_APPROVAL | REQUIRE_APPROVAL |
  | user (Member) | ALLOW | theo agent level | REQUIRE_APPROVAL | REQUIRE_APPROVAL |
  | auditor | ALLOW | DENY | DENY | DENY |

  `Founder+CRITICAL+L3` = explicit privileged execution → `ALLOW`. `user+CRITICAL+L2` = role không deny tuyệt đối nhưng autonomy chưa đủ → `REQUIRE_APPROVAL`. `auditor+non-read` = RBAC hard deny → `DENY`.

- **Ownership role — bắt buộc:** AgentOS **không** tự sở hữu danh sách role. Role canonical vẫn thuộc `services/control-plane` (bảng `cosa.roles`/`company_roles`); AgentOS chỉ nhận `role` đã normalize qua `TenantContext` (Phase 1a). Thêm role `auditor` bằng **migration mới** (`3_add_auditor_role.up.sql` hoặc tương tự), **không sửa migration 1 đã phát hành**. Test dùng đúng id canonical hiện có (`user`), không dùng nhãn `Member` tự chế để tránh semantic drift giữa Agent Plane (Python) và Control Plane (TypeScript).
- **Trình tự thực hiện (3 bước, không làm gộp):**
  1. Pure RBAC decision kernel (`evaluate_access`) + unit test theo ma trận trên.
  2. Mở rộng `ToolSpec` thêm `risk_level`, `tool_permission` (tiền đề cho ToolSpecV2 ở Phase 3a) — `PERMISSION_CLASS_RISK_MAPPING` hiện tại chỉ dùng làm fallback migration, không phải source-of-truth lâu dài.
  3. Cutover Executor sang gọi `evaluate_access()` thật, xoá đường hard-code `critical→REQUIRE_APPROVAL`.
- **Acceptance:**
```python
evaluate_access(role="founder", tool_risk_level=CRITICAL, agent_permission_level=L3_EXECUTE, tool_permission=ADMIN_WRITE) == ALLOW
evaluate_access(role="user", tool_risk_level=CRITICAL, agent_permission_level=L2_DRAFT, tool_permission=ADMIN_WRITE) == REQUIRE_APPROVAL
evaluate_access(role="auditor", tool_risk_level=LOW, agent_permission_level=L3_EXECUTE, tool_permission=SCOPED_WRITE) == DENY
```

---

## Phase 2 — Strategy & Startup Co-Founder Methodology domain (§4.3, §5.2) — gap lớn nhất

> Theo chỉ đạo của user, không dựa vào các ADR/tài liệu cũ (`ADR-007`, `ADR-008`, `COSA_STARTUP_METHODOLOGY_INTEGRATION_ANALYSIS.md`...) làm ràng buộc — các đề xuất/kết luận trong đó không được coi là authority cho kế hoạch này. Chỉ dựa trên codebase thật đã audit ở `services/` và guide kiến trúc mới. Nếu khi thực thi phát hiện code Python cũ trong `legacy/` đang thực sự được gọi bởi thành phần production (ví dụ chat/voice), xử lý đúng nguyên tắc chung của roadmap: `legacy/` không nhận feature mới, và bất kỳ dependency thật nào vào `legacy/` phải được thay bằng gọi qua Agent API/Tool Gateway (Phase 3b/4) — không port nguyên code cũ, viết lại sạch trên schema/service mới.

### 2a. Tạo `services/operations/strategy/` (logical bounded context)
- **CURRENT:** `operations/` phẳng, chỉ có `projects/portfolios/initiatives` (migration `6_create_projects_portfolios.up.sql`).
- **TARGET:** subdirectory theo layering chuẩn §20 (`handlers/services/models/migrations/tests`), không tách thành microservice riêng (theo §18.2 gate — không đủ điều kiện tách service).

### 2b. Schema/migration cho 10 entity còn thiếu
`stage_policies, stage_transitions, assumptions, experiments, evidence, interviews, discovery_signals, gate_evaluations, decision_records, next_action_candidates, next_action_rankings` — thiết kế mới, thêm vào `services/shared/db/schema/strategy.ts` (giữ nguyên convention centralized schema đang dùng). Tất cả có `company_id/workspace_id` scope + `deleted_at` soft-delete (nối tiếp pattern migration `2_align_schema.up.sql`).

### 2c. Business logic tất định (§5.2)
Stage assessment, assumption ranking, experiment proposal, evidence scoring, gate evaluation, decision recording, **Next Best Action candidate scoring tất định** (stage, assumption chưa giải quyết, evidence strength, blocked tasks, OKR gap, cash/runway, founder attention budget) — viết mới trong TypeScript service layer. LLM chỉ được dùng để **explain/critique/rerank**, không được tự đặt priority — ràng buộc cứng theo §5.2.

### 2d. API handlers + event
Endpoint CRUD + `GET /operations/strategy/projects/{id}/next-best-actions`, tenant-scoped, emit domain event (`ExperimentCreated`, `GateEvaluated`, ...).

### 2e. Verify Execution & Planning (§4.4) đã đủ
Đã xác nhận tồn tại: tasks, task_dependencies, task_schedules, OKR cycles/objectives/key_results, 12-week cycles, weekly plans/commitments, portfolios. Chỉ cần smoke test chuỗi project → initiative → OKR → 12WY → weekly plan.

---

## Phase 3 — Governance & Tool system nâng cấp (§8 hoàn thiện, §10 ToolSpecV2, §2.6 fix boundary)

### 3a. ToolSpecV2 (§10.3)
`ToolSpec` hiện tại chỉ có name/description/handler/permission_class. Định nghĩa `ToolSpecV2` (Pydantic) với input/output schema, risk_level, write_scope, idempotent, reversible, approval_policy, audit_policy, timeout, tags — migrate tool hiện có sang schema mới.

### 3b. Sửa vi phạm boundary `services/realtime_agent/voice_tools.py` (§2.6 — đã xác nhận vi phạm)
- Xoá `sys.path.insert(...,"backend")` và các import `db.session.SessionLocal`, `founder_os.strategy.tools`, `platform_core.vault.vault_tools` từ `legacy/backend/`.
- Viết lại mọi voice tool thành adapter HTTP mỏng gọi Agent API (Phase 4 phải làm Agent API trước hoặc song song).
- **Acceptance:** `voice_tools.py` không còn import nào từ `legacy/`; toàn bộ gọi qua Agent API.

### 3c. Tool registry + naming convention (§10.4-10.5)
Chuẩn hoá tên `<domain>.<resource>.<action>`; đảm bảo đăng ký tool chỉ qua một composition path (Phase 0b đã dọn phần lớn việc này).

### 3d. Audit sink + correlation id (§20.1-20.3, §12 Sessions & Trace)
Audit record đầy đủ: caller, tool, input (redacted), approval status, outcome, correlation_id xuyên suốt.

---

## Phase 4 — Agent Chat API & Text Chat MVP (§17.1, §4.8, §5.3)

> **Đã double-check kỹ:** `agentos/api/` **không tồn tại** (top-level `agentos/` hiện chỉ có `agents, core, evals, improvement, knowledge, memory, observability, skills, tools, workflows`), và `services/` cũng không giấu một Agent API nào khác (chỉ có `control-plane, identity, operations, commercial, finance-legal` + Python `realtime_agent`). Vì vậy đúng nghĩa **CURRENT = 0% implemented** cho HTTP/SSE entrypoint của AgentOS hiện tại.
>
> Nhưng đây **không phải bài toán thiết kế từ số 0 về mặt ý tưởng** — `legacy/agent_runtime/workforce/{api/,chat/}` có implementation tương đối trưởng thành: `ai_api.py`, `ai_router.py`, `chat_execution_service.py`, `chat_stream_bus.py`, `conversation_gate.py`. `ai_router.py` đã có abstraction sạch (`ChatTurn`, `ToolCall`, `AIEvent`, `ChatProvider`, streaming contract `delta/completed/failed/tool_call`). `chat_stream_bus.py` đã giải quyết khá kỹ luồng worker→API→Flutter: Postgres `LISTEN/NOTIFY`, delta kèm offset, DB là source of truth (notify chỉ best-effort), phát hiện missing chunk và resync — đây là **behavioral invariant đáng giữ** cho Text Chat mới, không nên tự nghĩ lại từ đầu.
>
> Đồng thời **không được port nguyên code** — `ai_api.py` phụ thuộc trực tiếp `fastapi`, `sqlalchemy.orm.Session`, `db.session.get_db`, `db.models.WorkspaceMember`, `core.auth.get_current_workspace_member`: dính chặt DB/auth/package graph legacy, không phù hợp làm API layer của AgentOS mới (vi phạm §3.1 nếu port thẳng).
>
> **Kết luận dùng cho Phase 4:** *"Greenfield API surface trên AgentOS kernel hiện có, được dẫn dắt bởi một legacy chat/API implementation phải migrate chọn lọc chứ không resurrect nguyên khối."*
> - **Reuse (ý tưởng/behavior, viết lại trên AgentOS kernel mới):** ChatTurn/event-stream concept, semantics delta/completed/failed/tool_call, streaming offset + resync behavior, async provider streaming contract, bài học tách worker/API, bài học conversation gating (`conversation_gate.py`).
> - **Không reuse trực tiếp:** SQLAlchemy models, `db.session`, `core.auth`, `WorkspaceMember` legacy, business DB access trực tiếp, hay bất kỳ registry/tool-execution stack trùng với AgentOS hiện tại.

### 4a. Route + event contract (§17.1.1-17.1.2)
`POST /agent/conversations`, `GET/PATCH .../{id}`, `POST .../messages`, `POST /agent/runs/{run_id}/cancel`, `POST /agent/approvals/{approval_id}/decision`, `GET /agent/runs/{run_id}/events` (SSE). Event types: `run.started, message.delta, tool.started/completed, approval.required/resolved, citation, run.completed/...`. Sequence monotonic trong 1 run để client resume/dedupe — tham khảo trực tiếp offset/resync design của `chat_stream_bus.py` (legacy) khi thiết kế resume logic, nhưng implement mới trong `agentos/api/`, wire vào composition root (`build_cosa_agent_plane()`) và governance hiện tại, không import code legacy.

### 4b. Conversation/Message/Attachment/RunEvent persistence (§7.2)
Postgres-backed (không SQLite cho server mode). Schema mới `agentos` hoặc `services/shared/db/schema/conversations.ts` tùy quyết định ownership — theo tài liệu, Agent Plane sở hữu conversation store, cần ADR ngắn xác nhận nơi đặt DB (Python service riêng hay chung Postgres cluster).

### 4c. Wire ContextBuilder đủ 5 lớp context (§5.3)
recent turns + memory + knowledge + skill instructions + business snapshot qua read tool.

### 4d. Flutter Chat UI MVP (§2.1, §17.1.3) — chưa audit, cần khảo sát `frontend/` trước khi ước lượng effort chính xác.

---

## Phase 5 — Skill system & Agent Profile (§11, §12)

- Skillpacks hiện có (`okr, tasks, core/weekly-review, marketing/*`) **đã compliant** với §11.1-11.3 — chỉ cần formalize registry loader + routing test, không viết lại.
- Viết cohort skill Strategy mới (`strategy.stage-assessment`, `strategy.assumption-discovery`, `strategy.experiment-design`, `strategy.evidence-synthesis`, `strategy.gate-evaluation`, `strategy.decision-capture`, `strategy.next-best-action`) gắn với tool Phase 2.
- Agent Profile schema (`agentos/profiles/`) theo mẫu §12.2, map sang WorkforceMember khi agent được "hire".

---

## Phase 6 — Text ↔ Voice continuity (§17.2, §17.3, §5.5)

- Voice session nhận `conversation_id`, transcript persist vào cùng Message model (Phase 4b).
- Hoàn tất việc port `voice_tools.py` sang gọi Agent API (tiếp nối Phase 3b).

---

## Phase 7 — Memory & Knowledge (§14, §15)

> **Đã spike và xác nhận trạng thái thật (không còn là giả định):** Memory và Knowledge **lệch trình độ hoàn thiện đáng kể** — không nên gộp chung một task "Implement Memory & Knowledge". Knowledge đã có pipeline chunk→embed→retrieve chạy thật (tested), Memory mới ở mức prototype (persistence lexical, không có vector, có nguy cơ silent data loss).

### CURRENT thật (đã verify code, không phải suy đoán)

**Memory** (`agentos/memory/{consolidation,models,pgvector_store,retrieval,retriever,store}.py`):
- `MemoryStore` protocol + `InMemoryMemoryStore` (có test) đã implement.
- `MemoryRetriever` có thể inject vào `ContextBuilder`, nhưng ranking chỉ là `0.7×relevance + 0.3×importance`, và `score_relevance()` tokenize bằng regex `[a-z0-9]+` — **không xử lý tiếng Việt có dấu**, và **không có recency factor** dù docstring có nhắc.
- `PgVectorMemoryStore` **tên gây hiểu nhầm**: bảng `agent_memories` không có cột `embedding`, search chỉ `WHERE workspace_id=... ORDER BY created_at DESC` — đây là Postgres persistence adapter thường, **không phải vector/semantic memory**. Không có `tests/agentos/memory/test_pgvector_store.py`.
- **Bug nghiêm trọng cần fix cùng phase:** nếu không truyền `db_session_factory`, `put()` return im lặng, `search()` trả `[]`, `delete()` no-op im lặng → **silent data loss khi cấu hình sai**. Vi phạm thẳng §14.3 ("không silent no-op") — phải sửa thành raise lỗi cấu hình khi khởi động (`UnavailableMemoryBackend` hoặc tương đương), không phải "giả vờ thành công".
- `agentos/memory/providers/` (target §14.1) **không tồn tại** — đây là structural refactor cần làm, không phải đã có sẵn khác tên.
- `build_default_runtime()`/`build_cosa_agent_plane()` hiện **chưa wire MemoryRetriever vào production composition** dù hook đã tồn tại ở ContextBuilder.

**Knowledge** (`agentos/knowledge/`):
- Pipeline `chunk → embed → store → semantic retrieval` **là implementation thật, đã unit-test full path** (`KnowledgeIngestPipeline`, `StubEmbeddingProvider`/`OpenAICompatibleEmbeddingProvider` gọi thật `POST /embeddings` qua httpx, `InMemoryKnowledgeStore` cosine search) — không phải scaffold, claim "đã implement" trong tài liệu gốc là đúng cho phần này.
- Chunking hiện là MVP theo character count (`DEFAULT_CHUNK_SIZE=800`, `overlap=100`) — không heading/token/document-structure-aware. Đủ dùng cho MVP, không cần nâng cấp ngay trong Phase 7.
- `PgVectorKnowledgeStore` **có SQL semantic vector thật** (`embedding <=> :query_embedding`, similarity = `1 - distance`) — nhưng **chỉ test bằng fake session**, chưa từng chạy với Postgres/pgvector extension thật, chưa có migration cho `knowledge_sources`/`knowledge_chunks`, chưa test workspace isolation ở tầng DB. Docstring code tự thừa nhận DB ownership (chung `services/` Postgres hay Postgres riêng cho AgentOS) **cố tình chưa quyết**.
- **Parser hoàn toàn chưa có** — pipeline nhận thẳng `raw_text: str`, PDF/DOCX/HTML→text phải làm bên ngoài. Chưa phải flow "file → RAG" end-to-end.
- `ContextBuilder` hiện chỉ biết `memory_snippets/skill_instructions/tool_names`, **chưa có `knowledge_snippets`/citations** — Knowledge tồn tại như subsystem độc lập nhưng AgentRuntime chưa consume nó. Chưa thể gọi COSA hiện tại là "RAG-enabled" ở production path.
- Hardening cần thêm cùng phase: `KnowledgeIngestPipeline` dùng `zip(texts, embeddings)` — nếu provider trả thiếu embedding sẽ silently truncate, cần validate `len(embeddings)==len(texts)` trước khi lưu; `KnowledgeChunk` nên lưu thêm `embedding_model/embedding_dimensions/embedding_version/content_hash` để re-index an toàn khi đổi model.

### Chia lại Phase 7 thành 4 workstream (không gộp chung)

**7A — Storage ownership (làm trước tiên, chặn 7C/7D):** chốt dùng chung 1 PostgreSQL cluster hiện có, tách schema ownership: `services/*` sở hữu business schema, `agentos/memory` sở hữu schema `agent_memory`, `agentos/knowledge` sở hữu schema `knowledge` (không cần Postgres server thứ hai). Viết migration cho `knowledge_sources`, `knowledge_chunks`, `agent_memories` (đã có) + bổ sung cột nếu cần.

**7B — Memory provider architecture:** refactor thành `agentos/memory/providers/{in_memory,postgres,tencent_agent_memory}.py`; nâng contract từ CRUD thô lên semantic hơn (`remember/recall/forget/consolidate`) trên nền `MemoryStore` low-level hiện có; fix bug silent no-op (mục CURRENT ở trên); đổi tên `PgVectorMemoryStore`→`PostgresMemoryStore` trừ khi thực sự thêm vector semantics thật; thêm test `test_postgres_memory_store.py` với DB thật hoặc testcontainer.

**7C — Knowledge productionization:** viết migration thật cho `knowledge_sources/knowledge_chunks`, chạy integration test với pgvector extension thật (không chỉ fake session), thêm parser tối thiểu (plain text + markdown trước, PDF/DOCX sau nếu cần), validate `len(embeddings)==len(texts)`, bổ sung metadata versioning cho re-index.

**7D — Agent integration:** wire `MemoryRetriever` + `KnowledgeRetriever` vào `build_cosa_agent_plane()` (nối tiếp Phase 0b) và mở rộng `ContextBuilder` thêm `knowledge_snippets`/citations — đây là điều kiện để Phase 4 (Text Chat) thực sự trả lời có citation như §17.1 yêu cầu.

**Acceptance chung Phase 7:** không component nào silent-fail khi thiếu dependency; `agentos/memory/providers/` tồn tại đúng cấu trúc target; pgvector Knowledge có ít nhất 1 integration test chạy Postgres thật; `ContextBuilder` trả về `knowledge_snippets` có citation khi có Knowledge source liên quan.

---

## Phase 8 — Workflow engine: pause/resume & deterministic procedure (§13.2, §5.3)

- Approval pause/resume **resume cùng run**, không tạo run mới (đúng yêu cầu §5.3 "không tạo một run mới làm mất causal chain").
- Sequential/parallel step + compensation cho Deterministic Agent Workflow.

---

## Phase 9 — ADK Orchestration port (§9.3, §2.4)

- **Nguyên tắc bắt buộc:** port hành vi/invariant từ `legacy/agent_runtime/workforce/agents/orchestration/adk/` (workflow.py, specialist_delegation.py, governed_tool.py, nodes/*) vào `agentos/orchestration/adk/`, **không `mv` nguyên dependency graph legacy**.
- Không direct DB access từ ADK node — mọi side effect qua Tool Gateway đã chuẩn hoá ở Phase 3.
- Composition root route: multi-agent mission → ADK; đơn giản → native Executor; specialist execution → DSH RuntimeAdapter (tất cả đều implement `AgentRuntimeAdapter` Protocol từ Phase 0b).
- Cần pin `google-adk` + `deepseek-harness-sdk` version cụ thể vào `agentos/requirements.txt` khi bắt đầu phase này (hiện chưa pin, đúng như tài liệu nói).

---

## Phase 10 — RBAC hoàn thiện, Connector pattern, Observability (§8.5 đầy đủ, §16, §20)

- Mở rộng decision function: thêm `TenantPolicy, ExecutionMode, DataScope` vào intersection.
- Connector pattern chuẩn (§16.1-16.3): transport/auth tách khỏi Tool adapter, secret ở vault không ở memory, OAuth ownership giữa `services/identity` và integration layer cần 1 ADR ngắn (tài liệu chưa chốt).
- Eval taxonomy (§20.4-20.5) + OpenTelemetry distributed trace thay SQLite làm authority.

---

## Phase 11 — Business Feature decision tree & smoke test cross-domain (§18)

- Viết `docs/architecture/COSA_FEATURE_IMPLEMENTATION_TREE.md` chốt decision tree §18.1 làm checklist bắt buộc cho mọi PR tính năng mới.
- Smoke test end-to-end: luồng Strategy (§5.2 đầy đủ từ founder hỏi → NBA → Initiative) và luồng Commercial linkage (Experiment ↔ Lead ↔ Evidence, §4.5).

---

## Phase 12 — Production hardening

- Security review theo checklist §3.1 (forbidden directions) + §7.4 (redaction coverage) + §14.3 (no silent no-op).
- Performance baseline cho chat latency, tool latency, retrieval latency.
- Docs vận hành cuối: runbook, "adding business feature" guide, dọn README (chỉ hướng dẫn khởi động, không chứa architecture — đúng §0.1).

---

## KHÔNG được làm (§3.1 forbidden directions + §0.3 superseded — nhắc lại để tránh tái phạm)

1. Không tái tạo `backend/cosa_core/` — đã bị bác bỏ đúng vì tạo Control Plane Python trùng lặp.
2. Voice không được import `legacy/` business modules (đang vi phạm — fix ở Phase 3b).
3. Frontend không gọi thẳng DB nội bộ.
4. Tool handler không được viết business logic/SQL trực tiếp — luôn qua Services API.
5. ADK/DSH không được bypass Tool Gateway/governance/audit.
6. Memory provider không được silent no-op khi backend unavailable.
7. Text Chat và Voice dùng chung một bộ Tool/Skill/Governance — không tạo `chat_tools.py` riêng biệt business logic.
8. Business rule/priority không được nhét vào prompt — logic tất định nằm ở code, LLM chỉ explain/critique/rerank.
9. SQLite không phải business truth (CRM, accounting, membership, legal) — chỉ trace/cache/checkpoint.
10. Không tạo `ToolRegistry()` rỗng rải rác — chỉ một composition path canonical (`build_cosa_agent_plane()`).

---

## Dependency & thứ tự thực thi

Phase 0 chặn tất cả. Phase 1 (TenantContext/RBAC) chặn Phase 2/3/4. Phase 2 (Strategy schema) chặn Phase 5b (strategy skills) và Phase 11 (smoke test). Phase 3b (voice boundary fix) chặn Phase 6. Phase 4 (Agent API) chặn Phase 5, 6, 8. Phase 9 (ADK) phụ thuộc Phase 1, 3, 8. Các phase 7, 10 có thể chạy song song sau Phase 4.

## Xác minh cuối mỗi milestone

Chạy `pytest tests/agentos` + `vitest` trong `services/` sau mỗi milestone; với milestone chạm domain Strategy, thêm integration test chuỗi project→assumption→experiment→evidence→gate→decision; với milestone chạm Agent API/Chat, test thủ công qua Flutter/`curl` SSE stream để xác nhận sequence event đúng thứ tự và resume được sau reconnect.
