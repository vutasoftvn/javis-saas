# COSA Agent Platform — Promotion Implementation Plan

> **Companion to:** `COSA_CANONICAL_MASTER_ARCHITECTURE_AND_IMPLEMENTATION_GUIDE_2026-08-23.md` (Master M1)
> **Status:** Operationalized plan + audit addendum, sau 2 vòng phản biện với người dùng
> **Không thay thế Master M1** — chỉ tường minh hóa trình tự thực thi, bổ sung correction đã được xác nhận

## Context

`COSA_CANONICAL_MASTER_ARCHITECTURE_AND_IMPLEMENTATION_GUIDE_2026-08-23.md` (Master M1) là bản hợp nhất kiến trúc COSA sau khi audit lại code tại `main@fb4251b6`. Tài liệu tự nhận là **audited, không phải wishlist** — mọi claim đều gắn nhãn PROVEN CURRENT / PARTIAL PROTOTYPE / TARGET CONTRACT / DEFERRED. Yêu cầu của người dùng: đọc kỹ tài liệu này + code thật, phản biện, rồi hợp nhất thành plan triển khai.

### Kết quả kiểm chứng (4 agent audit song song, đọc code trực tiếp)

Đã verify độc lập — không suy diễn từ tài liệu:

| Vùng | Kết quả |
|---|---|
| `agentos/core/runtime.py` routing (ADK / DeepSeek Harness / Native Executor) | **CONFIRMED** khớp 100% |
| `agentos/core/policy.py::evaluate_access()` | **CONFIRMED tồn tại**, nhưng dùng tên enum `PermissionLevel`/`ToolRiskLevel`/`ToolPermission` — không phải `AutonomyLevel`/`CapabilityRisk`/`PrincipalAuthorization`. Đây chính xác là điều Master doc §13 đề xuất đổi tên (target, chưa phải hiện trạng) — không phải sai lệch, mà là việc cần làm |
| `agentos/core/approval.py` in-memory dict | **CONFIRMED**, không persist |
| `agentos/workflows/*` (schema, loader, engine, definition_registry) | **CONFIRMED** — registry đã lưu `WorkflowSpec` thật + `definition_hash`; `Workflow.checkpoints` vẫn in-memory Pydantic dict |
| `agentos/memory/*` (MemoryStore, 5 MemoryKind) | **CONFIRMED** |
| `agentos/requirements.txt` (google-adk, deepseek-harness-sdk, KHÔNG có openai-agents) | **CONFIRMED** |
| `agentos/migrations/002_governance_temporal_model.sql` (5 bảng governance) | **CONFIRMED** |
| `packages/agent_core/` chỉ có `governance/` | **CONFIRMED**, chưa có runs/kernel/workflows/capabilities/... |
| `services/cosa` + `services/company` hai Encore app độc lập, `pg.Pool`+`createDrizzleClient` | **CONFIRMED** |
| `services/company/operations/strategy` (Project→Stage→...→NBA, S0–S5) | **CONFIRMED** |
| `apps/cosa/` chưa tồn tại | **CONFIRMED** |
| Test "governance state survives restart" (commit 198031a) | **CONFIRMED nhưng yếu hơn tên gọi** — không kill process thật, chỉ tạo `PostgresGovernanceStateStore` instance thứ hai cùng process. File test tự ghi rõ giới hạn này. Khớp với chính đánh giá của Master doc §2.10/§10.4 rằng đây chưa phải durability đầy đủ — **không phải mâu thuẫn, là gap đã được biết** |
| Test workflow-version pinning (commit 358da14) | **CONFIRMED nhưng yếu hơn tên gọi** — pin trong cùng process, chưa qua durable repository/process kill. Cũng đã được chính Master doc §10.4 nêu là bước tiếp theo cần làm |
| OpenAI Agents SDK chưa dùng ở đâu trong repo | **CONFIRMED** |

### Hai điểm phản biện — đã tinh chỉnh sau vòng phản biện thứ hai của người dùng

**1. "Không có production traffic" đúng, nhưng "agentos inert" là diễn giải quá xa.**

Operational truth chính xác hơn:

| Trục | Trạng thái |
|---|---|
| Backend API implemented (`agentos/api/app.py`, `chat_router`, `/agent/conversations`, messages/runs/approvals/SSE) | **Yes** |
| Frontend consumer implemented (`AgentChatService`, `ChatController.onInit()` gọi `loadConversations()`, `ChatBinding` register cả hai vào GetX) | **Yes** |
| Frontend↔API contract path aligned (`/agent/*`) | **Yes** |
| Deployment wiring cho AgentOS API | **No** (`docker-compose.yml` port 8000 là `legacy/backend` brain-api sau profile `legacy`, không phải `agentos.api.app`) |
| Default reachable / verified successful traffic | **No** |
| Product integration intent | **Rõ ràng Yes** |

Gọi đúng trạng thái này là **"consumer-referenced, contract-implemented, deployment-unwired runtime"**, không phải `inert`. Hệ quả: Step 10 không phải "wire first-ever consumer" mà là **"repair/replace an existing but broken client↔agent integration path"** — contract `/agent/*`, SSE event vocabulary, conversation semantics, approval UX flow là **observable product intent cần audit trước khi thay**, dù không bắt buộc backward-compatible vì chưa từng serving thành công.

Chi tiết quan sát thêm: `AgentChatService.getConversations()` catch mọi exception rồi trả `[]` — nghĩa là backend chết hiện ra với người dùng như "không có conversation" chứ không phải lỗi rõ ràng. Rule cần nhớ: **absence of reported traffic/error không đồng nghĩa absence of attempted traffic.**

**2. "Freeze agentos" cần định nghĩa lại — architecture freeze + feature freeze, KHÔNG PHẢI code freeze tuyệt đối.**

Commit `e28d396` (+22k dòng, "implement COSA roadmap phases 0-6": Strategy domain, governance, chat API, profiles, voice continuity) và `eedfbac` (+8.5k dòng: ADK orchestration nodes, DeepSeek harness adapter, tenant policy client, workflow YAML/tool-step, Postgres/pgvector memory/knowledge, eval harness — "wired through the existing runtime/factory composition") không phải scaffolding. `build_cosa_agent_plane()` tự ghi docstring "Production composition root" và thật sự compose model provider, ToolRegistry, MemoryRetriever, KnowledgeRetriever, skills, profiles, PolicyEngine, ApprovalService, trace/audit vào `AgentRuntime`.

Câu gốc của Master doc — *"Serving = No → không port implementation, không cần preserve behavior"* — là logical leap quá mạnh. `Serving = No` chỉ chứng minh **freedom to break implementation** (không cần migration compatibility/zero-downtime/preserve persisted state). Nó **không** chứng minh **freedom to ignore implementation** (behavior không cần audit, contract không tồn tại, tests không cần preserve, recent work có thể bỏ).

**Quyết định đã chốt (thay thế quyết định "freeze toàn bộ" trước đó):**
- **KHÔNG** đảo ngược hướng kiến trúc — `packages/agent_core/` + `apps/cosa/` + OpenAI Agents SDK vẫn là target đúng, `agentos` KHÔNG được tiếp tục nâng thành canonical.
- **NHƯNG** trước khi build VNext, phải làm **asset inventory & salvage classification** theo subsystem (xem Phase 0 dưới) — không throw-away toàn bộ, không port nguyên xi toàn bộ.
- Phạm vi plan: toàn bộ roadmap 11 bước, cả P0/P1/P2.
- Canonical entrypoint đầu tiên (Step 10): Text Chat (Flutter) — nhưng đóng vai "repair broken integration", không phải greenfield.

### Authority

Plan này **không thay thế** Master doc — nó operationalize Master doc thành trình tự thực thi cụ thể, có target file/dir, migration, test. Khi có xung đột, thứ tự authority của Master doc §0.1 vẫn áp dụng (ADR mới hơn > quyết định V4 freeze > code truth > Master doc > supplement cũ).

---

## Nguyên tắc thực thi xuyên suốt (không lặp lại ở từng phase)

- **Vertical slice, không layer-by-layer.** Mỗi phase dưới đây build đủ dọc một use case thật, không hoàn thiện toàn bộ một layer rồi mới sang layer khác.
- **`packages/agent_core/` không được import bất cứ gì từ `services/company/*`.** `apps/cosa/` là nơi duy nhất compose.
- **Không tạo bảng/schema thứ hai cho cùng semantics đã có ở `agent_core_governance.*`** — Phase 2 phải map rõ 1-1 (Master doc §12), không giữ song song vô thời hạn.
- **Mỗi phase kết thúc bằng một test chứng minh được** (không chỉ "logic đúng trong cùng process" — học từ gap đã phát hiện ở trên).
- **`agentos/` chỉ nhận bugfix/test nhỏ phục vụ audit** trong suốt quá trình; không thêm feature.

---

## Cách đọc phần Phase dưới đây

Mỗi Phase có cùng cấu trúc: **Mục tiêu** (một câu) → **Điều kiện tiên quyết** → **Việc cụ thể** (numbered, có file/dir) → **Definition of Done** (điều kiện kiểm tra được, không mơ hồ) → **Rủi ro/lưu ý**. Phase không có DoD rõ thì không được coi là xong.

---

## Phase 0 — Architecture freeze + Asset Inventory & Salvage Classification (Step 1–2, đã revise sau phản biện)

**Định nghĩa freeze cho giai đoạn này (khác Master doc gốc):**

Cấm từ thời điểm này:
- thêm execution framework mới vào `agentos`;
- thêm composition root mới hoặc tiếp tục mở rộng `build_cosa_agent_plane()` thành kiến trúc cuối;
- tiếp tục làm `AgentRuntime`/`Executor`/`ADK orchestrator` "production-ready" hơn;
- thêm durable architecture mới mà chỉ tồn tại ở `agentos` (không có kế hoạch promote).

Vẫn cho phép ở `agentos/`:
- characterization test, extraction adapter, invariant-proof, bugfix cần thiết để xác định chính xác thứ sẽ promote.

**Bảng phân loại salvage theo subsystem (chốt trước khi sang Phase 1):**

| Subsystem | Disposition | Việc cụ thể |
|---|---|---|
| `AgentRuntime` / `Executor` / `Planner` | **SUPERSEDE implementation** | Runtime ownership chuyển hẳn sang OpenAI Agents SDK kernel (Phase 3). Không port code, chỉ đọc để hiểu hành vi hiện có khi viết characterization test |
| `build_cosa_agent_plane()` | **PROMOTE composition knowledge, REWRITE implementation** | Dependency graph (model provider + ToolRegistry + MemoryRetriever + KnowledgeRetriever + skills + profiles + PolicyEngine + ApprovalService + trace/audit) có giá trị làm checklist cho `apps/cosa/composition/`; code thật viết lại |
| `agentos/orchestration/adk/*` (nodes, orchestrator) | **PROMOTE patterns/invariants only, KHÔNG port framework code** | Semantics đáng giữ: delegate / parallel / supervisor / risk classification / approval gate / quality gate / synthesis → đưa vào `packages/agent_core/coordination/` như primitive framework-neutral. Code hiện tại import thẳng private API (`google.adk.workflow._function_node.FunctionNode`) — không mang theo |
| `agentos/workflows/*` (schema, loader, engine, definition_registry, tool_step) | **PROMOTE CODE mạnh** | DAG, approval pause, compensation, YAML loader, retry, version pinning là tài sản thật, không rewrite từ zero — migrate trực tiếp vào `packages/agent_core/workflows/`, giữ nguyên logic, chỉ thay storage/durability (Phase 2) |
| Governance/policy semantics (`agentos/core/policy.py::evaluate_access`, temporal accumulator) | **PROMOTE mạnh** | Đã bắt đầu đúng hướng ở `packages/agent_core/governance/` — tiếp tục theo Phase 1 |
| Memory contracts/providers (`agentos/memory/*`) | **PROMOTE-after-audit** | Protocol/provider separation + Postgres implementation đã tách khá độc lập runtime kernel — audit coupling trước khi copy sang `packages/agent_core/memory/` (Phase 9) |
| Knowledge ingest/retrieval/chunking (pgvector) | **PROMOTE-after-audit** | Tương tự memory — audit rồi promote ở Phase 9 |
| Evals/regression harness | **PROMOTE** | Không viết lại từ zero — đây là promotion-gate asset, dùng làm baseline cho Phase 9 eval suite |
| Agent profiles/skills | **PROMOTE semantics + definitions** | Framework-neutral hơn runtime, giữ định nghĩa, viết lại phần load/bind vào kernel mới |
| `/agent/*` HTTP schema + SSE event vocabulary | **PROMOTE thành contract candidate** | Flutter đã consume trực tiếp — dùng làm input khi thiết kế `apps/cosa/api/` (Phase 7–8), không thiết kế lại tùy tiện rồi để Flutter vỡ |
| FastAPI chat route **implementation** (`agentos/api/chat/routes.py`) | **REWRITE** | `_pending_runs: dict` giữ resume state trong RAM (mất khi process chết); `asyncio.create_task(...)` truyền thẳng `db: Session` của request vào background task; `cancel_run()` chỉ emit event `run.cancelled`, không thật sự cancel kernel đang chạy. Giữ contract, bỏ toàn bộ lifecycle implementation này |
| In-memory approval/run/event state | **RETIRE** | Trái thẳng Step 6 durable model — không mang theo dưới bất kỳ hình thức nào |
| Google ADK làm architecture root | **SUPERSEDE** | Coordination primitives cứu được (xem trên), ownership/ADK-as-root thì không |

**Việc cụ thể trong Phase 0:**
1. Với mỗi dòng PROMOTE CODE / PROMOTE-after-audit ở trên: viết 1 file inventory ngắn (`docs/architecture/agentos_salvage_inventory.md`) liệt kê module nguồn → đích dự kiến trong `packages/agent_core/` → điều kiện audit (nếu có) → test hiện có nào sẽ trở thành characterization harness.
2. Cập nhật `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` để phản ánh đúng bảng phân loại trên — không còn ghi "agentos hoàn toàn inert/disposable".
3. Xóa/archive các file supplement đã bị Master doc hợp nhất (đã thấy `git status` hiện có 8 file supplement ở trạng thái `D` — xác nhận với người dùng trước khi commit xóa, vì đây là hành động phá hủy).
4. Không sửa `agentos/core/runtime.py`, `executor.py`, ADK orchestrator ngoài bugfix/characterization-test tối thiểu — nhưng khác Phase 0 bản gốc, việc **thêm test đặc tả hành vi** (không phải feature) được khuyến khích, vì các test này sẽ trở thành baseline cho Phase 1–4.

**Definition of Done — Phase 0:**
- `docs/architecture/agentos_salvage_inventory.md` tồn tại, mỗi dòng PROMOTE trong bảng trên có ít nhất 1 mục tương ứng (module nguồn, đích, điều kiện audit, test/characterization harness liên quan).
- `COSA_CANONICAL_OWNERSHIP_MAP.md` không còn câu nào mô tả agentos là "inert, không cần preserve behavior" mà không có qualifier đúng theo bảng operational-truth ở phần Context.
- Không có commit mới nào trong `agentos/` thêm feature (chỉ bugfix/characterization test) kể từ mốc Phase 0 — kiểm bằng đọc lại `git log --oneline -- agentos/` định kỳ trong các phase sau.
- Quyết định về 8 file supplement `D` trong `git status` đã được người dùng xác nhận rõ ràng (giữ nguyên trong staging area hay commit xóa) — không tự ý commit.

**Rủi ro/lưu ý:** Đây là phase thuần tài liệu + inventory, không đổi hành vi runtime nào — rủi ro thấp, nhưng là gate bắt buộc: Phase 1 không nên bắt đầu migrate code khi bảng salvage chưa chốt, vì mọi phase sau đều tham chiếu đích migrate từ bảng này.

---

## Phase 1 — VNext contracts + migrate Workflow Engine (Step 3)

**Mục tiêu:** có bộ contract nền tảng (`packages/agent_core/contracts/`) và `packages/agent_core/workflows/` chạy được với logic thật đã migrate từ `agentos/workflows/*`, không phải viết lại từ đầu.

**Điều kiện tiên quyết:** Phase 0 DoD đã đạt — bảng salvage đã chốt, đặc biệt dòng `agentos/workflows/*` = PROMOTE CODE mạnh.

**Việc cụ thể:**
1. Tạo `packages/agent_core/contracts/` với các module con theo từng contract (khuyến nghị 1 file/contract để review dễ, không bắt buộc):
   - `run.py`: `RunRequest`, `RunResult` (Master doc §6.5–6.6) — field tối thiểu: `principal`, `tenant/company/workspace scope`, `conversation/session ref`, `root executable ref`, `input`, `execution mode`, `model policy`, `correlation id`, `idempotency key`, `metadata` cho `RunRequest`; `run_id`, `status`, `final_output`, `artifacts`, `usage`, `events cursor/ref`, `interruptions/waits`, `errors` cho `RunResult`.
   - `spec.py`: `AgentSpec` với `definition_hash` bắt buộc (§6.1), field: `id`, `version`, `instructions`, `model_policy`, `autonomy_level`, `capability_refs`, `memory_policy`, `knowledge_policy`, `coordination_policy`, `limits`, `metadata`.
   - `identity.py`: `PinnedSpecIdentity` (đã có ở `governance/contracts.py` — import lại, không định nghĩa trùng), `InvocationIdentity` mới (L2, §7): `run_id + tool_call_id + capability_id + payload_hash`, mở rộng optional `connector/connection identity`, `idempotency key`, `checkpoint_ref`.
   - `target.py`: `ExecutionTargetSnapshot` (§8): `capability_id`, `connector_id`, `connection/account id`, `endpoint/resource identity`, `schema_hash/version`, `credential/grant version`, `capability risk at request time`, `handler/catalog version`.
   - `wait.py`: `WaitDescriptor` (§19): `kind`, `reason`, `owner/responder`, `resume_trigger`, `checkpoint_ref`, `related_approval/event/dependency ref`, `created_at`, `optional expiry`.
   - `kernel.py`: `ExecutionKernel` Protocol (§9.1) — chỉ method signature (`run`, `resume`, `cancel`, `stream`), chưa implement.
   - `capability.py`: `CapabilitySpec` (§16.1): `id`, `description`, `input schema`, `output schema`, `risk`, `approval policy`, `idempotency semantics`, `audit policy`, `eligibility`, `connector requirements`.
2. Migrate `agentos/workflows/schema.py`, `loader.py`, `engine.py`, `definition_registry.py`, `tool_step.py` sang `packages/agent_core/workflows/` — copy logic, không viết lại DAG/retry/compensation/version-pinning. Đổi import để dùng `WorkflowSpec` mở rộng: thêm field bắt buộc `failure/compensation policy`, `input/output schemas` nếu chưa có trong schema gốc.
3. Đổi vocabulary khi promote code liên quan governance/policy sang `packages/agent_core/governance/`: `PermissionLevel`→`AutonomyLevel`, `ToolRiskLevel`→`CapabilityRisk`, `ToolPermission`→gộp vào `PrincipalAuthorization` nếu semantics tương đương (kiểm tra kỹ trước khi gộp — nếu semantics khác, giữ tách). Retire `PermissionClass` khỏi vocabulary mới. Rename này CHỈ áp dụng trong `packages/agent_core/`, không đổi ngược vào `agentos/` (frozen).
4. Viết `docs/architecture/agentos_salvage_inventory.md` mục "Phase 1 completed": đánh dấu các module đã migrate xong, kèm commit hash.

**Test bắt buộc:**
- Schema validation cho từng contract (Pydantic validate cả input hợp lệ và không hợp lệ).
- `definition_hash` determinism test: cùng input → cùng hash, input khác 1 field → hash khác.
- Toàn bộ test suite cũ của `agentos/workflows/*` (schema/loader/engine/definition_registry) chạy pass trên code đã migrate ở vị trí mới — không được để mất coverage khi di chuyển.

**Definition of Done — Phase 1:**
- `packages/agent_core/contracts/` tồn tại đủ 7 module trên, có type hint đầy đủ, có docstring theo Quy tắc #19 CLAUDE.md (tiếng Việt cho phần giải thích ý nghĩa).
- `packages/agent_core/workflows/` chạy được toàn bộ test đã migrate từ `agentos/workflows/tests`, pass 100%.
- Không còn `packages/agent_core/*` import gì từ `agentos/*` (kiểm bằng `grep -r "from agentos" packages/agent_core/` → rỗng).
- Vocabulary rename đã áp dụng nhất quán trong `packages/agent_core/governance/`, có test xác nhận enum mới hoạt động đúng với accumulator/policy logic hiện có.

**Rủi ro/lưu ý:** Rename vocabulary có phạm vi rộng nếu làm ẩu — giới hạn chặt trong package mới, không codemod ngược. Việc migrate workflow engine dễ bị cám dỗ "tiện thể refactor luôn" — chống lại, chỉ đổi phần cần cho contract mới, giữ nguyên phần logic đã proven.

---

## Phase 2 — Durable Run substrate (Step 6, P0.2–P0.3)

**Mục tiêu:** 5 bảng canonical `agent_core.*` tồn tại, có model/repository trong `packages/agent_core/runs/`, và test resume xuyên qua process thật (không phải giả lập cùng process).

**Điều kiện tiên quyết:** Phase 1 xong (cần `contracts/` để định nghĩa row shape khớp `RunRequest`/`RunResult`/`InvocationIdentity`).

**Việc cụ thể:**
1. Viết migration SQL mới (không đụng `agentos/migrations/002_governance_temporal_model.sql` — đó là frozen) tạo schema `agent_core` với 5 bảng theo Master doc §11.2–11.6:
   - `agent_core.runs`: `run_id`, tenant/company/workspace scope, `principal`, root executable, `status`, correlation, created/updated, terminal result/error refs.
   - `agent_core.run_checkpoints`: `checkpoint_ref`, `run_id`, `sequence`, serialized kernel/workflow state, `SpecResolutionManifest` snapshot/ref, resume metadata, `created_at`.
   - `agent_core.run_events`: append-only, event type theo vocabulary §11.4 (`run.started`, `message.delta`, `tool.requested`, `policy.evaluated`, `approval.required`, `approval.decided`, `tool.started`, `tool.completed`, `checkpoint.created`, `run.waiting`, `run.resumed`, `run.completed`, `run.failed`).
   - `agent_core.run_tool_calls`: exact invocation ledger — `run_id`, `tool_call_id`, `capability_id`, `payload_hash`, payload/summary safe representation, `status`, `idempotency_key`, `checkpoint_ref`, result hash/ref, `error`, timestamps; recommended thêm `execution_target_snapshot`, policy observation refs, connector identity, risk at request.
   - `agent_core.approvals`: `approval_id`, `run_id`, `tool_call_id`, `checkpoint_ref`, `status`, `requirement`, reviewer/evidence refs, created/decided, expiry, reason.
2. Viết `packages/agent_core/runs/models.py` (ORM/dataclass mapping 5 bảng) và `packages/agent_core/runs/repository.py` (CRUD + query theo `run_id`, theo `tool_call_id`, không theo `(run_id, action)`).
3. Viết mapping tường minh (bảng markdown trong `docs/architecture/agentos_salvage_inventory.md` mục Phase 2) từ 4 bảng prototype `agent_core_governance.*` sang 5 bảng canonical mới, theo Master doc §12 — quyết định rõ: giữ song song bao lâu (khuyến nghị: tối đa hết Phase 6, sau đó `agent_core_governance.*` chỉ còn đọc lịch sử, không ghi mới).
4. Viết test resume qua process thật: script test spawn subprocess Python riêng (không dùng threading/asyncio task giả lập), subprocess mới đọc `run_checkpoints` từ Postgres bằng `run_id` truyền qua argv/env, resume, và assert kết quả đúng.

**Definition of Done — Phase 2:**
- 5 bảng tồn tại trong Postgres dev environment, có migration file review được.
- `packages/agent_core/runs/repository.py` có test coverage cho: tạo run, ghi checkpoint tuần tự, đọc run_tool_calls theo `tool_call_id` (không phải `(run_id, action)`), ghi/đọc approval theo `checkpoint_ref`.
- **Test process-thật pass**: subprocess con độc lập đọc checkpoint và resume đúng — đây là điều kiện bắt buộc để khép gap "Serving = No test yếu hơn tên gọi" đã phát hiện trong audit. Không coi Phase 2 xong nếu chỉ có test tạo instance thứ hai cùng process.
- Mapping tài liệu từ `agent_core_governance.*` → `agent_core.*` đã viết, có ít nhất 1 script/test đọc dữ liệu cũ và insert tương đương vào bảng mới (không cần chạy production migration thật, nhưng phải chứng minh mapping đúng).

**Rủi ro/lưu ý:** Đây là phase rủi ro kỹ thuật cao nhất về durability — process-thật test cần môi trường CI/dev hỗ trợ subprocess + Postgres thật, không chỉ SQLite/mock.

---

## Phase 3 — OpenAI Agents Kernel + Coordination primitives (Step 5, P0.4)

**Mục tiêu:** `ExecutionKernel` có 1 implementation thật dựa trên OpenAI Agents SDK, và `packages/agent_core/coordination/` có các primitive framework-neutral rút từ hành vi ADK orchestrator cũ (không phải code cũ).

**Điều kiện tiên quyết:** Phase 1 (contracts, đặc biệt `ExecutionKernel` protocol) và Phase 2 (nơi lưu checkpoint) đã xong.

**Việc cụ thể:**
1. Thêm `openai-agents` vào dependency riêng của `packages/agent_core` (file requirements/pyproject riêng cho package này — không đụng `agentos/requirements.txt`).
2. Viết `packages/agent_core/kernel/openai_agents_kernel.py` implement `ExecutionKernel` protocol: `run()`, `resume()`, `cancel()`, `stream()`.
3. Viết `RunState` serialization adapter: SDK `RunState.to_json()/from_json()` ↔ cột serialized state trong `agent_core.run_checkpoints`.
4. Implement streaming event mapping sang `agent_core.run_events` vocabulary đã định nghĩa ở Phase 2 (`message.delta`, `tool.requested`, ...).
5. Implement interruption/approval surfacing: khi SDK báo tool-call cần approval, map sang `WaitDescriptor` + tạo row `agent_core.approvals` (chuẩn bị cho Phase 5, ở đây chỉ cần kernel phát đúng signal).
6. Viết DeepSeek compatibility matrix test (§9.4) — 1 test file chạy qua từng capability: basic response, structured output, single tool call, parallel tool calls, streaming, tool-call IDs, usage, error propagation, context length, RunState resume, agent-as-tool, approval interruption. Output là bảng capability profile (pass/partial/fail per item), không phải 1 assertion pass/fail duy nhất.
7. Viết `packages/agent_core/coordination/` — đọc lại characterization test của `agentos/orchestration/adk/*` đã viết ở Phase 0 (nếu có) để hiểu behavior, sau đó viết mới các primitive: `delegate.py`, `parallel.py`, `supervisor.py`, `risk_classification.py`, `approval_gate.py`, `quality_gate.py`, `synthesis.py` — mỗi primitive dùng `ExecutionKernel` protocol của Phase 1, KHÔNG import `google.adk.*`.

**Test bắt buộc:**
- DeepSeek matrix test (mục 6) chạy được và log ra capability profile.
- Mỗi primitive coordination có ít nhất 1 test đối chiếu hành vi với characterization test cũ của ADK orchestrator (Phase 0) — không cần giống 100% code, nhưng phải giữ đúng invariant (vd. parallel thật sự chạy song song, supervisor thật sự tổng hợp kết quả specialist).

**Definition of Done — Phase 3:**
- `OpenAIAgentsKernel` chạy được 1 Run thật end-to-end (input → tool call → output) trong môi trường dev, ghi đúng vào `agent_core.run_events`.
- Capability matrix profile đã document cho ít nhất DeepSeek (route chính hiện có).
- `packages/agent_core/coordination/` không có import nào từ `google.adk` hay `agentos.*` (kiểm bằng grep).
- Không còn dùng `google.adk.workflow._function_node.FunctionNode` hoặc bất kỳ private API tương tự nào trong code mới.

**Rủi ro/lưu ý:** SDK OpenAI Agents có thể có giới hạn/khác biệt hành vi với DeepSeek qua proxy — capability matrix là để phát hiện sớm, không phải rào cản chặn tiến độ; ghi nhận rõ item nào PARTIAL/FAIL và quyết định có chấp nhận được không.

---

## Phase 4 — Capability Layer & invocation identity (Step 7, P0.5–P0.9)

**Mục tiêu:** Capability Gateway thật, invocation identity ổn định, và test chứng minh idempotency qua kịch bản crash thật.

**Điều kiện tiên quyết:** Phase 2 (bảng `run_tool_calls`) và Phase 3 (kernel phát tool-call events) đã xong.

**Việc cụ thể:**
1. Viết `packages/agent_core/capabilities/gateway.py` implement pipeline đầy đủ theo §16.2: resolve capability → validate input (theo `CapabilitySpec` từ Phase 1) → resolve connector/grant → construct `InvocationIdentity` ổn định → policy evaluate (gọi `governance/`) → accumulate governance (accumulator đã có) → approval gate (check `agent_core.approvals`) → construct `ExecutionTargetSnapshot` → idempotency check (theo `idempotency_key`) → execute → audit (ghi `run_events`) → persist (`run_tool_calls`).
2. Stable `tool_call_id`: nếu SDK cung cấp call ID ổn định từ Phase 3, dùng trực tiếp; nếu không, sinh UUID nội bộ và map rõ external↔internal trong `run_tool_calls`.
3. Payload canonicalization: viết hàm canonicalize input (sort keys, normalize types) trước khi hash — dùng cho cả `payload_hash` lẫn idempotency key.
4. Viết idempotency failure-window test (§17.3): 
   - bước 1: gọi capability write giả lập (vd. mock external API ghi vào file/DB phụ để giả lập "remote system") 
   - bước 2: remote system "commit" thành công 
   - bước 3: kill process COSA (thật, qua subprocess) TRƯỚC khi mark `run_tool_calls.status = completed` 
   - bước 4: restart/retry cùng `idempotency_key` 
   - bước 5: assert không có side effect thứ hai ở remote system, và COSA reconcile được kết quả gốc.

**Definition of Done — Phase 4:**
- `CapabilityGateway` chạy được ít nhất 1 capability giả lập (mock, chưa cần nối `services/company` — việc đó là Phase 7) qua đủ pipeline 10 bước.
- `tool_call_id` không bao giờ trùng giữa 2 lần gọi khác nhau trong cùng Run (test case "same tool twice" — tiền đề cho Phase 6 case G).
- Idempotency failure-window test pass — đây là điều kiện bắt buộc theo Master doc §17.3, mạnh hơn "không rerun step trong object hiện có".

**Rủi ro/lưu ý:** Kịch bản "kill process giữa lúc side-effect đã commit nhưng local chưa mark success" khó mô phỏng đúng — cần thiết kế test có điểm dừng xác định (vd. `os.kill` sau khi mock remote ghi file nhưng trước khi COSA update DB), không dùng sleep đoán thời điểm.

---

## Phase 5 — Durable approval (P0.7)

**Mục tiêu:** Approval sống được qua restart, bind đúng invocation cụ thể chứ không phải action name.

**Điều kiện tiên quyết:** Phase 2 (bảng `approvals`), Phase 4 (invocation identity + gateway).

**Việc cụ thể:**
1. Viết `packages/agent_core/capabilities/approval_service.py` thay thế hoàn toàn cách lookup `(run_id, action)` của `agentos/core/approval.py` — lookup bắt buộc qua `run_id + tool_call_id + checkpoint_ref`.
2. Implement lifecycle đầy đủ theo §18:
   - kernel/workflow đề xuất exact invocation → ghi `run_tool_calls` row → fresh policy evaluation → cập nhật `InvocationG_acc` → nếu `REQUIRE_APPROVAL` → persist checkpoint chính xác → tạo `approvals` row bind `run_id/tool_call_id/checkpoint_ref/requirement` → set trạng thái `WAITING_APPROVAL`.
   - reviewer: load approval → trình bày đúng target/payload/risk/context (dùng `ExecutionTargetSnapshot` từ Phase 4) → ghi `ApprovalEvidence`.
   - resume: load run + approval + invocation + checkpoint → verify identity → verify approval evidence → verify target snapshot/drift → fresh current governance → conjoin → verify effective requirement → idempotency check → resume checkpoint → execute nếu allowed.
3. Đảm bảo APPROVED không phải bypass vĩnh viễn (§18.1) — mọi resume phải re-evaluate governance hiện tại trước khi dùng evidence cũ.

**Definition of Done — Phase 5:**
- Test: 2 lời gọi cùng 1 tool trong cùng Run (vd. `send_email` gọi 2 lần) có 2 approval độc lập, evidence không cross lẫn nhau (case G ở Phase 6, làm trước ở đây để verify approval service).
- Test: sau khi approve rồi tenant bị suspend trước khi resume → resume phải DENY, không dùng lại evidence cũ mù quáng (case C, làm trước ở đây).
- Approval survive qua test process-thật tương tự Phase 2 (kill process giữa lúc WAITING_APPROVAL, subprocess mới load lại đúng approval).

**Rủi ro/lưu ý:** Phase này phụ thuộc chặt vào chất lượng `ExecutionTargetSnapshot` và accumulator từ các phase trước — nếu phát hiện thiếu field khi implement, quay lại bổ sung Phase 1/4 thay vì patch tạm ở đây.

---

## Phase 6 — Spec-drift & governance-drift test suite (P0.10)

**Mục tiêu:** 9 case bắt buộc ở Master doc §41.1 đều có test độc lập, pass.

**Điều kiện tiên quyết:** Phase 1 (spec pinning), Phase 2 (durable run), Phase 5 (approval) đã xong — case này lắp ráp lại toàn bộ hệ thống đã build.

**Việc cụ thể — mỗi case là 1 file test riêng, không gộp chung:**
- **A. Workflow spec drift:** v1 pause → publish v2 → restart → resume → phải chạy v1, không có node của v2.
- **B. AgentSpec privilege widening:** v1 autonomy thấp → pause → publish v2 autonomy cao → resume → Run cũ không kế thừa v2.
- **C. Current revocation:** Run được allow → pause → principal/connector bị revoke → resume → DENY thắng.
- **D. Risk increase:** approve ở MEDIUM → risk tăng lên CRITICAL trước khi resume → evidence cũ không đủ/stale.
- **E. Risk/policy relaxation:** approve ở CRITICAL/FounderApproval → policy sau đó nới lỏng xuống LOW/ALLOW → resume → constraint lịch sử vẫn giữ (không tự động nới theo policy mới).
- **F. Orthogonal approval requirement:** request cần FounderApproval, hiện tại cần FinanceAdminApproval → resume → cần CẢ HAI trừ khi có role semantics chứng minh khác.
- **G. Same tool twice:** gọi `send_email` 2 lần → `tool_call_id` khác nhau, approval/evidence không cross.
- **H. Target drift:** cùng capability + payload nhưng connector/account/schema/credential thay đổi → approval cũ stale.
- **I. Side-effect committed before crash:** remote system commit thành công → process chết trước khi mark success → restart → không duplicate (tái sử dụng test từ Phase 4).

**Definition of Done — Phase 6:**
- 9 file test, mỗi file pass độc lập, không phụ thuộc thứ tự chạy lẫn nhau.
- CI (nếu có) chạy được cả 9 case trong một suite riêng gọi là "governance drift suite" — dễ chạy lại khi thay đổi accumulator/policy logic sau này.

**Rủi ro/lưu ý:** Đây là nơi dễ phát hiện thiếu sót từ các phase trước (vd. `ExecutionTargetSnapshot` thiếu field cần cho case H) — chấp nhận quay lại phase trước bổ sung, không patch tắt case test.

---

## Phase 7 — Compose `apps/cosa/` (Step 8, P0.11)

**Mục tiêu:** Có composition boundary thật, gọi được ít nhất 1 read + 1 write capability thật vào `services/company/`.

**Điều kiện tiên quyết:** Phase 1–6 đã xong (đủ contracts, kernel, capability gateway, approval, drift tests).

**Việc cụ thể:**
1. Tạo cấu trúc `apps/cosa/{api,composition,policies,capabilities,agents,workflows}/` theo Master doc §4.
2. `apps/cosa/composition/`: dùng bảng dependency graph đã ghi lại từ `build_cosa_agent_plane()` ở Phase 0 (PROMOTE composition knowledge) làm checklist — implement lại composition root: model provider, capability registry, memory/knowledge port (stub tạm nếu Phase 9 chưa xong), policy engine, approval service, trace/audit, tất cả từ `packages/agent_core/*` đã build.
3. `apps/cosa/capabilities/`: implement 1 read-only capability thật gọi `services/company/operations` hoặc `services/company/operations/strategy` (vd. `operations.task.read` hoặc `strategy.gate.read`) qua Encore RPC/HTTP client hiện có — đây là nơi DUY NHẤT được phép import `services/company/*`.
4. Implement 1 write capability thật có approval gate risk MEDIUM+ (vd. một action trong `finance-legal` phù hợp) — dùng đầy đủ pipeline Phase 4–5.
5. Reusability gate check (§4.2): viết 1 script/test riêng compose "app thứ hai" giả lập, chỉ dùng `RunService`/`ExecutionKernel`/`WorkflowEngine`/Capability contract/Events/Governance/Memory-Knowledge ports từ `packages/agent_core/`, KHÔNG import gì từ `services/company`. Nếu import bị cần thì boundary chưa đạt — sửa lại `packages/agent_core/` trước khi tuyên bố Phase 7 xong.

**Definition of Done — Phase 7:**
- `apps/cosa/` chạy được 1 read capability + 1 write capability thật (không mock) chống lại `services/company/` dev instance.
- Reusability gate check script pass — chứng minh được `packages/agent_core/` độc lập COSA business domain.
- `grep -r "services.company" packages/agent_core/` → rỗng.

**Rủi ro/lưu ý:** Đây là phase dễ bị cám dỗ import tắt cho nhanh — giữ kỷ luật boundary vì đây là gate cuối cùng chứng minh Agent Core "tái sử dụng được" theo đúng North Star của CLAUDE.md mục 18.

---

## Phase 8 — Vertical Slice 1 + 2: repair/replace Text Chat integration (Step 10, reframed)

**Mục tiêu:** Flutter Text Chat nói chuyện được với `apps/cosa/api` thật, qua đúng 2 vertical slice acceptance criteria của Master doc.

**Điều kiện tiên quyết:** Phase 7 xong (có `apps/cosa/api` với ít nhất 1 read + 1 write capability).

**Việc cụ thể — thứ tự bắt buộc:**
1. **Audit contract cũ trước khi đổi:** đọc đầy đủ `/agent/*` HTTP schema (`agentos/api/chat/routes.py`, `schemas.py`) + SSE event vocabulary + toàn bộ `AgentChatService` (Dart) — liệt kê từng endpoint, field, event type đang được Flutter dùng thật (không phải suy đoán từ tên).
2. Viết bảng quyết định: mỗi endpoint/field cũ → giữ nguyên / đổi có lý do / bỏ có lý do — lưu vào `docs/architecture/agentos_salvage_inventory.md` mục "Phase 8 contract decision".
3. Implement `apps/cosa/api/` theo quyết định ở bước 2, dùng contract `RunRequest`/`RunResult`/events từ Phase 1–2, không phải tự nghĩ ra shape mới tùy tiện.
4. **Bổ sung observability tường minh trước khi rewire:** sửa hoặc bọc thêm layer trong `AgentChatService.getConversations()` (và các method khác đang catch-and-swallow) để lỗi network/backend không còn tự động biến thành `[]` — hoặc ít nhất thêm log/metric rõ ràng phân biệt "không có data" và "gọi API thất bại". Đây là điều kiện để test end-to-end đáng tin.
5. Sửa `frontend/lib/modules/chat/services/agent_chat_service.dart` trỏ `agentOsBaseUrl` sang endpoint mới của `apps/cosa/api`.
6. Vertical Slice 1 (Read Path, §40): chạy end-to-end Flutter → Agent API → durable Run → pinned AgentSpec → OpenAIAgentsKernel → DeepSeek route → read-only Capability (từ Phase 7) → `services/company` → streamed events → final answer + usage/trace. Acceptance criteria dùng nguyên văn §40 (unique run id, spec manifest persisted, tool call id stable, read-only policy ALLOW, streaming thật, trace/usage persisted, cancel works, provider error map predictably, không import business DB từ Agent Core).
7. Vertical Slice 2 (Write + Approval + Restart, §41): full canonical test, dùng write capability từ Phase 7, qua approval flow Phase 5.

**Definition of Done — Phase 8:**
- Integration test end-to-end thật (không mock backend) chạy Flutter test hoặc ít nhất HTTP-level test giả lập đúng request Flutter gửi, xác nhận toàn bộ acceptance criteria §40 và §41.
- Bảng quyết định contract cũ→mới đã có, không có endpoint nào bị đổi "âm thầm" mà không ghi lý do.
- `AgentChatService` không còn silent-swallow lỗi thành `[]` mà không phân biệt được với "thật sự trống".

**Rủi ro/lưu ý:** Đây là phase đầu tiên chạm UI thật — cần user xác nhận trước khi merge/deploy vì ảnh hưởng trải nghiệm người dùng cuối, dù hiện tại chưa ai dùng thật (theo audit).

---

## Phase 9 — P1: WaitDescriptor, durable workflow repo, ExecutionTargetSnapshot đầy đủ, memory/knowledge, evals

**Mục tiêu:** Đóng các gap còn lại theo P1 của Master doc §43, và hoàn tất promote-after-audit cho memory/knowledge/evals.

**Điều kiện tiên quyết:** Phase 8 xong — có 1 canonical entrypoint sống để các P1 item này có chỗ dùng thật, tránh xây "cho có".

**Việc cụ thể theo thứ tự Master doc §43 P1:**
1. `WaitDescriptor` routable thật (không chỉ contract Phase 1) — có API cho phép resolve "ai/cái gì unblock, event nào, resume checkpoint nào" thành hành động thật.
2. Durable workflow definition repository — đóng gap §10.3: registry hiện tại (Phase 1 đã migrate) cần thêm persisted immutable definition repository, cross-process load exact definition.
3. `ExecutionTargetSnapshot` full shape (Phase 1 mới có schema, đây là điền đủ field thật từ connector/credential system).
4. `ConnectorGrant` normalization — scope theo tenant/company, principal/agent, account, capability/actions, resource scope, expiry/revocation.
5. Exact-once delegation/fanout: `ExpansionFingerprint` (§22) — `source_run_id`, `source_node/decision/spec revision`, `expansion semantic key`; đảm bảo không tạo sibling tree thứ hai cho cùng fingerprint.
6. Recovery service (§21): chỉ restore liveness (requeue, restore lease, retry same owner, restore provider session, load checkpoint, resume, reconcile idempotent side effect, surface operator action) — KHÔNG được tự ý gán quyền cao hơn/switch agent/rewrite ownership/skip approval/resolve spec mới nhất.
7. Low-trust delegation provenance (§34): gắn trust metadata lên external ticket/uploaded doc/web result/review output/agent delegation result/connector content.
8. Budget/run-level gate (§35): budget threshold → deny/pause protected execution mới, optionally cancel safe-to-cancel work; budget là ambient/current, không phải invocation historical accumulator.
9. Artifact lifecycle (§32): artifact provenance (run_id, source inputs, spec identity, creator principal/agent, timestamp, version/hash), `RunResult` chỉ reference artifact record, không nhét payload vào event stream.
10. **Memory/Knowledge PROMOTE-after-audit:** trước khi copy `agentos/memory/*` và knowledge ingest/retrieval/chunking (pgvector) vào `packages/agent_core/{memory,knowledge}/`, audit từng module tìm coupling ngầm vào `AgentRuntime`/`Executor`/`PermissionLevel` cũ — cắt coupling trước khi copy. Bổ sung field canonical còn thiếu theo §25.2/§26 (tenant scope, ACL, provenance, retention, sensitivity, supersession...).
11. **Evals PROMOTE thẳng:** lấy evals/regression harness hiện có trong `agentos/` làm baseline test suite cho 4 nhóm eval ở §33 (model/kernel capability, business correctness, durability/recovery, security/governance) — không viết lại từ đầu, chỉ bổ sung case còn thiếu.

**Definition of Done — Phase 9:**
- Mỗi mục 1–9 có ít nhất 1 test/case chứng minh, tham chiếu đúng section Master doc tương ứng.
- Memory/Knowledge đã promote vào `packages/agent_core/` và pass toàn bộ test cũ (đã migrate) + audit coupling document hóa trong `agentos_salvage_inventory.md`.
- 4 nhóm eval ở §33 chạy được như 1 suite, dùng baseline từ `agentos/` evals cũ.

**Rủi ro/lưu ý:** Phạm vi P1 rộng — nên làm tuần tự theo đúng thứ tự liệt kê, không song song hóa nhiều mục cùng lúc vì một số mục phụ thuộc lẫn nhau (vd. budget gate cần recovery service đã có khái niệm "safe-to-cancel").

---

## Phase 10 — P2 hardening/scale (chỉ khi sản phẩm thật sự cần)

**Mục tiêu:** Không prebuild — chỉ trigger từng mục khi có nhu cầu sản phẩm cụ thể, tránh over-engineering.

**Điều kiện tiên quyết:** Phase 9 xong; và với TỪNG mục dưới đây, phải có lý do cụ thể (feature request, incident, scale limit thật) trước khi bắt đầu — không làm "vì roadmap nói vậy".

**Danh sách (mỗi mục là 1 quyết định độc lập, không phải trình tự bắt buộc):**
1. L3 Capability Implementation Identity (ADR-A, hiện DEFERRED) — chỉ pin handler/schema/connector implementation version nếu có case cụ thể cần rollback an toàn.
2. Multi-worker execution leases — chỉ khi có distributed workers thật (nhiều process/machine cùng xử lý Run).
3. Work queue/coalescing scheduler — chỉ khi sản phẩm cần recurring/background work thật.
4. Plugin/extensibility framework — chỉ khi có use case cụ thể cần third-party/community extension.
5. Role hierarchy/quorum policy mở rộng — chỉ khi `AllOf`/`AnyOf`/`Quorum` hiện có (Phase 1) không đủ biểu diễn nhu cầu approval thật.
6. Dormant Run TTL/expiry UX (ADR-D) — chỉ khi có Run thật tồn đọng lâu cần chính sách rõ ràng.
7. Multi-region/cloud artifact distribution — chỉ khi cần thật.

**Definition of Done — Phase 10:** Không áp dụng theo nghĩa "hoàn thành toàn bộ" — mỗi mục có DoD riêng khi được trigger, viết bổ sung vào tài liệu này tại thời điểm đó (ghi rõ lý do trigger + ADR liên quan).

---

## Phase 11 — Archive `agentos/` (Step 11)

**Mục tiêu:** Gỡ bỏ hoàn toàn phụ thuộc vào `agentos/` runtime cũ, chỉ giữ làm lịch sử tham khảo.

**Điều kiện tiên quyết:** Promotion Definition of Done (Master doc §42) pass toàn bộ 15 tiêu chí — liệt kê lại để tick từng cái:
1. `packages/agent_core` owns clean contracts.
2. OpenAI Agents kernel pass model compatibility matrix.
3. Durable Run/Checkpoint/Event/ToolCall/Approval hoạt động qua restart (process thật).
4. AgentSpec/WorkflowSpec pinned bằng immutable identity.
5. Exact invocation identity tồn tại.
6. Write side effects idempotent (đã test failure window).
7. Approval sống qua restart.
8. Current governance có thể narrow nhưng không bao giờ widen invocation cũ.
9. Waiting states có routable descriptor.
10. WorkflowEngine resume durable.
11. Capability calls chạm `services/company` thật.
12. Text Chat integration dùng API mới.
13. Security/eval gates pass.
14. Không còn production path nào cần `AgentRuntime` cũ.
15. App thứ hai reuse được Agent Core mà không import COSA business.

**Việc cụ thể khi đủ điều kiện:**
1. Xác nhận với người dùng trước khi archive/xóa (hành động phá hủy) — liệt kê rõ những gì sẽ archive vs xóa hẳn.
2. Di chuyển `agentos/` sang `legacy/agent_runtime_archive/` hoặc archive branch riêng (không xóa thẳng — giữ lịch sử git đã có).
3. Gỡ mọi reference còn sót trong docs/README trỏ về `agentos/` như nguồn hiện hành.
4. Cập nhật `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` lần cuối để đóng vòng đời `agentos/`.

**Definition of Done — Phase 11:** Cả 15 tiêu chí §42 đã tick, có evidence (test/log/doc) cho từng tiêu chí, và người dùng đã xác nhận archive.

---

## Verification chung cho toàn bộ plan

- Mỗi phase có test riêng (nêu ở trên); không phase nào coi là "done" chỉ vì logic chạy trong cùng process — bài học trực tiếp từ 2 gap durability đã phát hiện trong audit.
- Trước khi tuyên bố promotion hoàn tất: chạy đủ 4 nhóm eval ở §33 (model/kernel capability, business correctness, durability/recovery, security/governance).
- Checklist cuối cùng: đối chiếu nguyên văn 15 điều ở §42 (Promotion Definition of Done) và 20 invariant ở §47 (Closing Architecture Invariants) — không tuyên bố xong nếu còn điều nào chưa verify được bằng test/evidence cụ thể.

## File/dir tham chiếu chính

```
packages/agent_core/
├── governance/          # đã có — KEEP/HARDEN, đổi tên vocabulary ở đây (Phase 1)
├── contracts/            # MỚI — Phase 1
├── workflows/             # MIGRATE CODE từ agentos/workflows/* — Phase 1 (PROMOTE CODE, không rewrite)
├── kernel/                # MỚI — Phase 3
├── coordination/          # MỚI — Phase 3, invariant rút từ agentos/orchestration/adk/* (không port code)
├── capabilities/          # MỚI — Phase 4
├── runs/                  # MỚI — Phase 2 (models/repository cho 5 bảng)
├── memory/, knowledge/    # Phase 9 — PROMOTE-after-audit từ agentos/memory, agentos knowledge
└── artifacts/, evals/     # Phase 9 — evals PROMOTE thẳng làm baseline

apps/cosa/
├── api/, composition/, policies/, capabilities/, agents/, workflows/   # MỚI — Phase 7, dùng /agent/* contract đã audit làm input thiết kế

agentos/                   # ARCHITECTURE+FEATURE FROZEN kể từ Phase 0 — không code freeze tuyệt đối:
                            # cho phép characterization test/bugfix phục vụ promotion; cấm feature/framework mới
docs/architecture/agentos_salvage_inventory.md   # MỚI — Phase 0, bảng module nguồn→đích→điều kiện audit
services/company/, services/cosa/   # KHÔNG đổi cấu trúc, chỉ thêm capability endpoint khi Phase 7 cần
frontend/lib/modules/chat/services/agent_chat_service.dart   # SỬA ở Phase 8 — repair contract đã audit, không phải greenfield
```
