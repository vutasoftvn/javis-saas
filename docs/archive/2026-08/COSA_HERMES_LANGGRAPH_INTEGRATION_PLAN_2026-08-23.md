# COSA — Hermes/LangGraph Supplement Integration Plan

> **Revision:** HLI1 — 2026-08-23
> **Status:** Approved
> **Vai trò:** Đây là **plan tích hợp**, hợp nhất `COSA_HERMES_LANGGRAPH_ARCHITECTURE_AND_IMPLEMENTATION_SUPPLEMENT_2026-08-23.md` vào roadmap 11-phase hiện có trong `COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md`. Không thay thế Master Architecture (M1) hay Promotion Plan; là **delta có thứ tự authority thấp hơn cả hai**, cùng cấp với supplement gốc nhưng sửa lại sequencing của nó.
> **File nguồn đã đối chiếu:** `COSA_HERMES_LANGGRAPH_ARCHITECTURE_AND_IMPLEMENTATION_SUPPLEMENT_2026-08-23.md`, `COSA_CANONICAL_MASTER_ARCHITECTURE_AND_IMPLEMENTATION_GUIDE_2026-08-23.md`, `COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md`.
> **Phương pháp:** 4 vòng research độc lập đối chiếu supplement với code thật (`packages/agent_core/`, `apps/cosa/`, `legacy/agent_runtime/`) trước khi viết plan này — không chấp nhận claim nào của supplement mà chưa verify bằng code.

---

## 0. Executive Decision

Supplement Hermes+LangGraph là một delta **hợp lệ về nội dung kỹ thuật** (contract nó mô tả khớp với code thật ~95%), nhưng **cấu trúc triển khai của nó sai**: nó tự tạo ra một roadmap song song (Phase A → Phase F, §43 của supplement) thay vì gắn vào roadmap 11-phase đã tồn tại. Điều này vi phạm trực tiếp hai rule trong `CLAUDE.md`:

- "Trước khi thêm code lớn vào `packages/agent_core/` hoặc `apps/cosa/`, đọc phase tương ứng trong Plan."
- "Không nhân bản kiến trúc — tìm trong repo trước khi thêm mới."

Plan này **giữ nguyên toàn bộ nội dung kỹ thuật hợp lệ của supplement** (context lifetime, curated memory, progressive skill disclosure, delegation authority attenuation, LangGraph superstep/reducer/pending-writes) nhưng **xóa bỏ hoàn toàn cấu trúc Phase A-F** và map từng hạng mục vào đúng vị trí trong Phase 0-11 hiện có, đồng thời sửa 6 lỗi sequencing/premise đã phát hiện qua verify:

| # | Vấn đề trong supplement gốc | Sửa trong plan này |
|---|---|---|
| 1 | Roadmap Phase A-F độc lập, không rõ authority so với Promotion Plan | Xóa bỏ; mọi hạng mục map vào Phase 0-11 |
| 2 | LangGraph spike (Phase B) đặt ngay sau "foundation truth", cạnh tranh với Phase 1 (harden WorkflowEngine) | Tách 2 gate: **technical spike ở Phase 3** (sau khi Phase 1 baseline xong) và **adoption decision ở Phase 6** (sau khi Capability Gateway + Approval thật đã có) |
| 3 | Context Architecture (§8) trình bày như "ADD" — greenfield, không audit legacy | Bắt buộc audit 4 file `legacy/agent_runtime/workforce/agents/context/` ở Phase 0; salvage invariant, không copy code, không port vào `packages/agent_core/` nguyên xi (vi phạm boundary agent_core không import business domain) |
| 4 | CapabilityReadiness (§18) xếp vào "Phase F" (item 26) — quá muộn so với vị trí thực sự cần trong Capability Gateway pipeline | Contract ở Phase 1, minimum enforcement ở Phase 4 (đúng vị trí trong pipeline thật), full implementation ở Phase 9 |
| 5 | Kernel gap (§0.1, §41) nêu vấn đề nhưng không có ADR, để ngỏ như câu hỏi mở | Promotion Plan **đã chốt** OpenAI Agents SDK là kernel target (dòng 195) — ADR-KERNEL chỉ ratify quyết định có sẵn + đặt exit criterion cho custom loop hiện tại, không mở lại 50/50 |
| 6 | Skill pinning ADR (§15, §25) chỉ trigger khi "child Run kế thừa skill của parent" | Mở rộng trigger: bất kỳ khi nào một Run có thể resolve Skill reference không cố định (floating) — kể cả cùng một Run qua pause/resume, không riêng delegation |

---

## 1. Bằng chứng verify (đối chiếu code thật)

### 1.1. Đúng như supplement mô tả

- `AgentSpec`, `WorkflowSpec`, `PinnedSpecIdentity`, `SpecResolutionManifest`, `CapabilitySpec` đã tồn tại đúng field như supplement mô tả (`packages/agent_core/contracts/spec.py`, `workflows/schema.py`, `governance/contracts.py`, `contracts/capability.py`).
- `coordination/delegate.py` (31 dòng) đúng là thin wrapper: `specialist_spec.to_pinned_identity()` → `RunRequest` → `kernel.run()`. Không có `DelegationEnvelope`, authority attenuation, skill inheritance.
- `workflows/engine.py` (282 dòng): custom DAG, `asyncio.gather` parallel waves, approval pause (`WAITING_APPROVAL` + `WaitDescriptor`), compensation (`on_failure` handlers), in-object checkpoints, step outcomes. Không phụ thuộc LangGraph.
- `MemoryKind` có `PROCEDURAL` cùng `WORKING/EPISODIC/SEMANTIC/ORGANIZATIONAL` (`memory/models.py`).
- `SkillSpec`, `ContextAssembler` chính thức, `packages/agent_core/context/`, `packages/agent_core/skills/`, `CapabilityReadiness` đều **chưa tồn tại** trong `packages/agent_core/` — xác nhận đúng gap.
- Governance/approval binding đúng invariant `run_id + tool_call_id + checkpoint_ref` (`capabilities/approval_service.py`).
- Stack: Python 3.9.6, FastAPI, async SQLAlchemy 2.0+ trên Postgres — tương thích kỹ thuật với LangGraph Postgres checkpointer nếu adopt.
- Không có ADR nào trước đó nhắc LangGraph/Hermes/SkillSpec/DelegationEnvelope — đây là lần đầu formalize.

### 1.2. Sai/thiếu so với supplement — đã sửa trong plan này

- **Kernel**: `packages/agent_core/kernel/openai_agents_kernel.py` (492 dòng) là **custom loop** — `KernelRunState` (fields `messages`, `pending_tool_calls`, `completed_tool_calls`), `while state.step_index < max_turns:` gọi `_call_model()` (dùng `openai` package trần, KHÔNG dùng `openai-agents` SDK) → parse tool_calls → policy → checkpoint → approval → execute. `requirements.txt` chỉ có `pydantic`, `openai`, `sqlalchemy`, `pyyaml` — không có `openai-agents`, `langgraph`, `langchain`. Trong khi đó, **Promotion Plan Phase 3 (dòng 195) đã chốt rõ**: "ExecutionKernel có 1 implementation thật dựa trên OpenAI Agents SDK." → Đây là gap thực thi (implementation chưa conform), không phải quyết định architecture còn treo.
- **Legacy context prior art bị bỏ sót**: `legacy/agent_runtime/workforce/agents/context/` có 4 file, không chỉ `assembler.py`:
  - `builder.py`: `ContextSection` (`data`/`source`/`fetched_at`/`status`/`error`), đánh giá governance **trước khi fetch** — invariant đáng giữ.
  - `compiler.py` (`ProgressiveContextCompiler`, `ContextBudget`): concept L0-L5 (Session/Company/Project/Domain/Skill/Artifacts). Verify thực tế: L0-L4 compile được, **L5 chưa thực sự implement** dù có placeholder; token estimate chỉ là `len(text)//4`; khi vượt budget chỉ đánh dấu `is_trimmed=True`, **không redistribute token thật**. → Prototype-grade, salvage ý tưởng chứ không salvage code.
  - `scope_resolver.py`: `ScopeSet`/`allowed_namespaces`/`token_budget`/`needs_heavy_priming`; invariant "No Job → No Heavy Priming" chỉ đúng có điều kiện (`not needs_job AND not needs_project`), không phải absolute.
  - `assembler.py` (`CofounderContextAssembler`): intent-based scoping (5 loại intent), graceful degradation qua từng field, reuse `SPECIALIST_REGISTRY.fetch_snapshot()`. Query trực tiếp SQLAlchemy business models (`Workspace`, `Project`, `TwelveWeekCycle`, `FounderDecision`, `ApprovalRequest`, `EvidenceItem`, `Outcome`) — nếu port nguyên vào `packages/agent_core/` sẽ vi phạm boundary "agent_core không import business domain".
- **Capability Gateway readiness**: pipeline thật (`capabilities/gateway.py`) là resolve capability → validate input → canonicalize+hash → build invocation identity & target snapshot (connector_id chỉ lấy trực tiếp `spec.connector_requirements.get("connector_id")`, KHÔNG có health-check) → idempotency → policy → governance accumulate → approval → execute handler. Không có bước readiness — cần chèn đúng vị trí giữa "build target snapshot" và "idempotency/policy", không phải để dồn về P2.

---

## 2. Nguyên tắc bao trùm

1. **Một roadmap duy nhất.** Không tồn tại Phase A-F. Mọi hạng mục Hermes/LangGraph gắn vào Phase 0-11 hiện có của Promotion Plan.
2. **LangGraph technical spike ≠ LangGraph adoption decision.** Hai gate tách biệt, cách nhau bởi Phase 4-5 (Capability Gateway, Durable Approval) để có boundary thật làm bằng chứng.
3. **Context = salvage, không phải greenfield, không phải copy nguyên xi.** Legacy 4 file là nguồn invariant để trích xuất ý tưởng, không phải code để port thẳng.
4. **Kernel ADR = ratify, không reopen.** Promotion Plan đã chọn OpenAI Agents SDK; ADR chỉ ghi nhận custom loop là tạm thời, đặt exit criterion.
5. **Skill pinning trigger mở rộng** ra mọi trường hợp floating Skill reference có thể resolve trong một Run, không riêng child-inheritance.
6. **Readiness ≠ Authorization**, luôn tách biệt, không có ordering tuyệt đối bắt buộc readiness luôn chạy trước governance — cần tránh leak thông tin connector cho principal chưa authorize.

---

## 3. Mapping Phase-by-Phase (thay thế hoàn toàn cấu trúc Phase A-F của supplement)

### Phase 0 — Inventory & Salvage (bổ sung)
- Audit đầy đủ 4 file `legacy/agent_runtime/workforce/agents/context/{assembler,builder,compiler,scope_resolver}.py`. Viết `docs/architecture/CONTEXT_ASSEMBLER_AUDIT.md`: invariant giữ (governance-before-fetch, progressive L0-L5 concept, ScopeSet/token_budget) vs phần KHÔNG production-ready (L5 rỗng, token estimate thô, rebalance giả, "No Job→No Heavy Priming" chỉ có điều kiện).
- Audit delegation pattern trong `agentos/orchestration/` (nếu tồn tại), đối chiếu Hermes §16.
- LangGraph: chỉ research/đọc source theo pin tại supplement §53. Không thêm dependency, không code.

**DoD Phase 0 (bổ sung):** `CONTEXT_ASSEMBLER_AUDIT.md` tồn tại và liệt kê rõ invariant giữ/bỏ.

### Phase 1 — Contracts + migrate WorkflowEngine (bổ sung tối thiểu)
- Tiếp tục migrate `agentos/workflows/*` (DAG, approval pause, compensation, YAML loader, retry, version pinning) đúng cam kết gốc của Plan — đây là baseline bắt buộc trước mọi LangGraph spike.
- Đóng băng **contract tối thiểu**, không viết implementation:
  - `ContextFragment`, `ContextSnapshot` (Protocol/BaseModel, framework-neutral, không import business domain) — chỉ nếu Phase 7 thực sự cần làm interface boundary; không bắt buộc dựng `packages/agent_core/context/` đầy đủ (tránh abstraction-first over-engineering).
  - `CapabilityReadiness` (`capability_id`, `ready`, `reason_code`, `observed_at`, `ttl`) — thêm vào `contracts/capability.py` hiện có.
  - Viết ADR-KERNEL (mục 4) trước khi Phase 3 bắt đầu code.

**DoD Phase 1 (bổ sung):** `ContextSnapshot`/`ContextFragment` construct được rỗng (unit test); `CapabilityReadiness` contract có test hợp lệ; ADR-KERNEL đã merge.

### Phase 2 — Durable Run substrate (không đổi)
- Không thêm cột/migration cho LangGraph checkpoint ở giai đoạn này — quá sớm khi chưa qua gate Phase 3/6. Nếu Phase 6 adopt LangGraph, migration riêng thêm lúc đó.

### Phase 3 — OpenAI Agents SDK Kernel + Coordination (gate kỹ thuật, KHÔNG quyết định adoption)
- **Kernel**: implement `ExecutionKernel` dựa trên `openai-agents` SDK thật, đúng DoD gốc của Plan. ADR-KERNEL phải ratify trước khi coding bắt đầu.
- **LangGraph technical spike** (chỉ sau khi Phase 1 baseline WorkflowEngine đã harden xong): branch riêng `experiment/langgraph-spike`, không merge main. Câu hỏi duy nhất: *LangGraph có fit kỹ thuật với WorkflowSpec/runtime model của COSA không?* — compile StateGraph từ WorkflowSpec, static DAG, parallel superstep, reducer, Postgres checkpointer, kill process → resume, pending-writes khi partial-success. Không test approval/governance thật ở đây (dùng approval giả lập) vì Phase 4/5 chưa xong.
- Coordination primitives: tiếp tục theo Plan gốc; chưa thêm `DelegationEnvelope` đầy đủ (đó là Phase 9).

**DoD Phase 3 (bổ sung):** `requirements.txt` có `openai-agents`, import xác nhận trong `kernel/`; nếu chạy spike — branch tồn tại kèm log kết quả DAG/checkpoint/resume/pending-writes.

### Phase 4 — Capability Gateway (bổ sung readiness minimum)
- Chèn bước readiness **minimum enforcement** vào đúng vị trí trong pipeline thật (giữa "build target snapshot" và "idempotency/policy"): nếu `MISSING_CREDENTIAL`/`CONNECTOR_OFFLINE` → block với lý do rõ ràng; không leak thông tin connector cho principal chưa được authorize (đánh giá static eligibility trước khi expose reason_code chi tiết).
- Readiness không thay governance — test bắt buộc: `ready=true` không đồng nghĩa `allowed=true` và ngược lại.
- **LangGraph ToolStep integration** (nếu spike Phase 3 tiếp diễn): chứng minh ToolStep node gọi đúng qua Capability Gateway, không bypass.

**DoD Phase 4 (bổ sung):** test case readiness OFFLINE + governance ALLOW → proceed có warning; readiness READY + governance DENY → blocked bởi governance.

### Phase 5 — Durable Approval (chứng minh LangGraph interrupt ↔ approval thật)
- Không đổi phần approval core.
- Nếu spike tiếp diễn: chứng minh `interrupt()` chỉ là control primitive; approval identity thật (`run_id+tool_call_id+checkpoint_ref`) vẫn do COSA governance quyết định, không bị LangGraph resume logic ghi đè.

### Phase 6 — Drift/security gate suite — **LangGraph adoption decision gate**
- Chạy đầy đủ acceptance matrix HL-01 → HL-18 (supplement §45) trên branch spike, dùng baseline thật từ Phase 4/5.
- Quyết định 1 trong 3, ghi vào ADR-LANGGRAPH:
  - **Adopt** — merge, engineering đầy đủ ở Phase 9.
  - **Reject** — đóng branch, áp dụng ý tưởng supersteps/reducer/pending-writes vào WorkflowEngine native ở Phase 9 (theo supplement §47).
  - **Defer** — ADR mở, re-evaluate ở Phase 10.
- Đây là **gate duy nhất** được phép quyết định adoption — không quyết định sớm hơn.

**DoD Phase 6 (bổ sung):** ADR-LANGGRAPH đóng với quyết định rõ ràng + bằng chứng HL-01→HL-18.

### Phase 7 — Compose apps/cosa (context adapter thật)
- `apps/cosa/composition/context_assembler.py`: implement dùng contract Phase 1, salvage invariant từ audit Phase 0 (governance-before-fetch, progressive disclosure concept), viết business adapter MỚI gọi qua Encore RPC tới `services/company` — không import trực tiếp SQLAlchemy business model như legacy làm.
- Đây là nơi đầu tiên chứng minh use case thật cho `ContextSnapshot`, tránh abstraction đóng băng ở Phase 1 mà không có consumer.

**DoD Phase 7 (bổ sung):** integration test — context assembly cho ít nhất 1 intent thật (vd. `founder_review`) trả về fragment đúng lifetime (STABLE/RUN/CURRENT), gọi qua Encore RPC, không import SQLAlchemy business model trực tiếp.

### Phase 8 — Text Chat vertical slice (conversation contract)
- Định nghĩa `ConversationHistoryPort` (contract only: `recent_messages`, `search_messages`, `get_thread_context`), stub implementation, tích hợp Flutter existing flow không phá vỡ.

### Phase 9 — P1 hardening (full implementation)
- Memory/Knowledge promote-after-audit (đã có trong Plan gốc).
- Context: full `ContextAssembler` production nếu Phase 7 đã chứng minh giá trị; hoàn thiện lexical/FTS search cho conversation (test: no cross-tenant leakage).
- Delegation: `DelegationEnvelope` đầy đủ (`delegation_id`, `parent_run_id`, `child_run_id`, `parent/child_spec_identity`, `goal`, `context_snapshot_ref`, `delegated_capability_ceiling`, `budget`, `depth`, `status`), authority attenuation invariant (`Authority(child) ⊆ Authority(parent) ∩ governance hiện tại ∩ connector grant hiện tại`), durable steer/cancel events (không phải mutate in-memory object).
- Readiness: full implementation (connector health, credential TTL, dependency readiness).
- SkillSpec: cho phép **publication** (DRAFT→PUBLISHED lifecycle, immutable version + `definition_hash`, progressive L0-L2 disclosure) nhưng **cấm runtime consumption qua floating reference** cho tới khi có ADR-SKILL-IDENTITY (mục 4).
- Hard non-approvable safety floor (`NON_APPROVABLE` policy level, dominate approval + autonomy).
- Nếu LangGraph adopt ở Phase 6: full integration engineering ở đây. Nếu reject: implement supersteps/reducer/pending-writes/state-vs-context separation vào WorkflowEngine native.

**DoD Phase 9 (bổ sung):** test authority attenuation (child capability không vượt trần); test skill publication v2 không ảnh hưởng Run đang chạy dùng v1; test hard-deny dominate approval + autonomy.

### Phase 10 — P2, trigger-based (không mandatory)
- **ADR-SKILL-IDENTITY**: quyết định cách AgentSpec/WorkflowSpec reference Skill (exact version/hash vs compiled-into-definition-hash vs mở rộng `PinnedSpecIdentity`) — trigger khi có use case thật cần Skill tham gia execution, không prebuild.
- Plugin trust/quarantine lifecycle (DISCOVERED→QUARANTINED→VERIFIED→INSTALLED→ACTIVE) — trigger khi plugin installation trở thành requirement thật.
- Rich delegation steer/stop UX, advanced LangGraph features (subgraph-as-child-Run, time-travel/fork) — trigger-based, chỉ khi Phase 6 đã Adopt.

### Phase 11 — Archive (mở rộng Definition of Done)
Giữ nguyên 15 tiêu chí gốc của Master doc §42, cộng thêm (chỉ áp dụng cho track đã kích hoạt thật):
16. Context assembly hoạt động cho ≥3 intent type qua use case thật.
17. Delegation authority attenuation test pass (không escalate).
18. Skill publication lifecycle test pass, không mutate live Run.
19. Conversation search không leak cross-tenant.
20. Hard non-approvable action không thể bypass.
21. (Nếu Adopt LangGraph ở Phase 6) HL-01 → HL-18 pass đầy đủ.

---

## 4. Hai ADR bắt buộc trước khi code Phase 3

**ADR-KERNEL** (ratify, không reopen):
> Decision: OpenAI Agents SDK chính thức là kernel implementation canonical (đã chốt tại Promotion Plan Phase 3, dòng 195). Custom loop hiện tại (`openai_agents_kernel.py`) là TẠM THỜI / non-conforming, không được nhận thêm trách nhiệm architecture mới trong lúc chờ thay thế. Exit criterion: thay thế bằng SDK thật trước khi Phase 3 DoD đóng. Fallback: chỉ mở lại quyết định nếu compatibility matrix chứng minh SDK có giới hạn chặn cứng — khi đó cần một ADR mới riêng, không tự động quay lại custom loop.

**ADR-LANGGRAPH** (mở tại Phase 3, đóng tại Phase 6):
> Ghi nhận kết quả spike kỹ thuật (Phase 3: DAG compile, checkpoint, resume, pending-writes) và quyết định adoption (Phase 6: Adopt / Reject / Defer), kèm lý do dựa trên acceptance matrix HL-01→HL-18.

**ADR-SKILL-IDENTITY** (trigger-based, Phase 10): quyết định cơ chế pin Skill khi có use case thật đầu tiên cần Skill tham gia execution (không riêng delegation).

---

## 5. Explicit Rejections (giữ nguyên lý do, không làm theo nguyên văn supplement)

- **REJECT** roadmap Phase A-F độc lập — không có authority rõ ràng so với Promotion Plan, vi phạm CLAUDE.md rule đọc-phase-trước-khi-code.
- **REJECT** tạo `packages/agent_core/context/` và `packages/agent_core/skills/` đầy đủ ngay Phase 1 — abstraction-first over-engineering, chờ Phase 7 chứng minh use case.
- **REJECT** port nguyên code `legacy/.../context/*.py` vào `packages/agent_core/` — vi phạm boundary agent_core-không-import-business-domain; code chưa production-grade (L5 rỗng, token estimate thô, rebalance giả).
- **REJECT** chạy LangGraph spike song song với Phase 1 harden WorkflowEngine — không có baseline để so sánh, vi phạm cam kết Plan gốc "migrate trực tiếp, không rewrite từ zero".
- **REJECT** quyết định LangGraph adoption ngay sau spike kỹ thuật Phase 3 — phải đợi Capability Gateway (Phase 4) + Durable Approval (Phase 5) chứng minh boundary integration thật, đúng như supplement §46 tự đòi hỏi nhưng đặt sai vị trí.
- **REJECT** mở ADR-KERNEL như câu hỏi 50/50 — Promotion Plan đã quyết định; ADR chỉ ratify + đặt exit criterion.
- **REJECT** giới hạn skill-pinning trigger vào riêng trường hợp child-inherit — mở rộng ra bất kỳ floating skill reference nào có thể bị resolve trong một Run (kể cả pause/resume cùng Run).
- **REJECT** đặt CapabilityReadiness làm mục P2 riêng biệt (Phase F cũ, item 26) — đúng vị trí là Phase 1 (contract) + Phase 4 (minimum enforcement, đúng chỗ trong pipeline) + Phase 9 (full).
- **REJECT** ordering tuyệt đối "readiness luôn chạy trước policy" — cần tránh leak thông tin connector cho principal chưa authorize; dùng static eligibility check trước khi expose readiness chi tiết.

Các REJECT khác từ supplement gốc (§48) vẫn giữ nguyên hiệu lực: Hermes `AIAgent` làm ExecutionKernel; LangChain `AgentExecutor` làm platform root; LangGraph state làm business state; LangGraph Store làm business database; LangGraph interrupt làm approval authority; direct LangGraph business writes; self-learning mutate trực tiếp published behavior; process-local delegation làm durable truth; sandbox isolation làm business authorization; framework leakage vào Flutter/business services.

---

## 6. Verification tổng thể

| Mốc | Kiểm tra |
|---|---|
| Sau Phase 0 | `docs/architecture/CONTEXT_ASSEMBLER_AUDIT.md` tồn tại, liệt kê invariant giữ/bỏ từ 4 file legacy |
| Sau Phase 1 | `ContextSnapshot`/`ContextFragment`/`CapabilityReadiness` construct hợp lệ qua unit test; ADR-KERNEL merged |
| Sau Phase 3 | `openai-agents` có trong `requirements.txt` và được import trong `kernel/`; (nếu spike) branch `experiment/langgraph-spike` có log DAG/checkpoint/resume/pending-writes |
| Sau Phase 4 | test readiness OFFLINE+ALLOW→proceed-with-warning; readiness READY+DENY→blocked-by-governance |
| Sau Phase 6 | ADR-LANGGRAPH đóng với quyết định rõ ràng + bằng chứng HL-01→HL-18 |
| Sau Phase 7 | integration test context assembly cho ≥1 intent thật, đúng lifetime, qua Encore RPC (không import SQLAlchemy business model trực tiếp) |
| Sau Phase 9 | test authority attenuation (HL-06/07), skill publication không ảnh hưởng Run đang chạy (HL-05), hard-deny dominate (HL-10) |
| Trước Phase 11 archive | review đủ 15+N tiêu chí DoD tùy track đã kích hoạt |

---

## 7. Nguồn tham chiếu

```text
COSA_HERMES_LANGGRAPH_ARCHITECTURE_AND_IMPLEMENTATION_SUPPLEMENT_2026-08-23.md
COSA_CANONICAL_MASTER_ARCHITECTURE_AND_IMPLEMENTATION_GUIDE_2026-08-23.md
COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md

packages/agent_core/contracts/spec.py
packages/agent_core/contracts/capability.py
packages/agent_core/coordination/delegate.py
packages/agent_core/workflows/engine.py
packages/agent_core/workflows/schema.py
packages/agent_core/memory/models.py
packages/agent_core/kernel/openai_agents_kernel.py
packages/agent_core/capabilities/gateway.py
packages/agent_core/capabilities/approval_service.py
packages/agent_core/governance/contracts.py

legacy/agent_runtime/workforce/agents/context/assembler.py
legacy/agent_runtime/workforce/agents/context/builder.py
legacy/agent_runtime/workforce/agents/context/compiler.py
legacy/agent_runtime/workforce/agents/context/scope_resolver.py
```
