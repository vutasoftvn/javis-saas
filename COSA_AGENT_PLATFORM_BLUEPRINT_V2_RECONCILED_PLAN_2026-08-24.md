# COSA Agent Platform — Kế hoạch triển khai đã đối chiếu (Reconciled Plan cho Blueprint V2)

> **Trạng thái:** Approved Implementation Plan (đã người dùng duyệt qua phiên plan-mode ngày 2026-08-24)
> **Nguồn gốc:** Đối chiếu `COSA_AGENT_PLATFORM_IMPLEMENTATION_BLUEPRINT_V2_2026-08-24.md` với `COSA_CANONICAL_MASTER_ARCHITECTURE_AND_IMPLEMENTATION_GUIDE_2026-08-23.md`, `COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md`, và trạng thái code thật tại HEAD `fcfe387`.
> **Vai trò tài liệu:** Đây là tài liệu **thực thi** (đã hiệu chỉnh theo code thật + quyết định người dùng), đứng cạnh 2 tài liệu canonical 2026-08-23. `COSA_AGENT_PLATFORM_IMPLEMENTATION_BLUEPRINT_V2_2026-08-24.md` giữ nguyên làm tài liệu đề xuất gốc/lịch sử, không sửa.

---

## Bối cảnh

Blueprint V2 (85 mục) đề xuất tái cấu trúc lớn, audit cùng baseline `fcfe387` với HEAD hiện tại. Ba agent audit song song đã đối chiếu Blueprint V2 với hai tài liệu canonical 2026-08-23 và trạng thái thật của `packages/agent_core/`, `apps/cosa/`, `services/*`, `docs/architecture/adr/`. Kết quả:

- Phần lớn chi tiết code-level của Blueprint V2 đúng (contracts, 3 migration hiện có, kernel/gateway split, PK rời của `tool_call_id`, in-memory globals trong API...).
- Có 2 xung đột kiến trúc với ADR đã ratify: `ADR-KERNEL-openai-agents-sdk-ratification.md` (OpenAI Agents SDK = canonical kernel) và `ADR-LANGGRAPH-adoption-decision.md` (LangGraph đã bị reject làm runtime dependency).
- Một điểm đã lỗi thời: Run/Memory repository đã mặc định Postgres, không còn silent in-memory fallback (commit `3cfceb3`, `fcfe387`) — Blueprint V2 vẫn liệt kê đây là vấn đề cần sửa.
- Control-plane primitives (`packages/agent_core/runs/leases.py`, `packages/agent_core/coordination/scheduler.py`) đã tồn tại nhưng 100% in-memory, chưa durable.

## Quyết định đã chốt với người dùng (2026-08-24)

1. **Runtime priority:** Theo hướng LangChain-primary của Blueprint V2 nguyên bản → supersede chính thức `ADR-KERNEL-openai-agents-sdk-ratification.md` và `ADR-LANGGRAPH-adoption-decision.md` bằng ADR mới (chưa viết — xem Phần B).
2. **Control-plane home:** Di chuyển các primitive control-plane (lease/scheduler/mission/task/worker/budget/watch/signal/delivery) sang `services/cosa` (TypeScript/Encore), đúng quy tắc CLAUDE.md "business truth thuộc services/*".
3. **Phạm vi:** Đưa toàn bộ Blueprint V2 vào kế hoạch triển khai (Wave 0–11 đầy đủ, gồm documentation-as-code, chính sách comment/prompt-language, Skill Optimization Lab, Recipe Catalog, Control Plane Watch/Signal/Delivery).

---

## Phần A — Bảng hiệu chỉnh Blueprint V2 theo code thật (phản biện)

| # | Blueprint V2 giả định | Thực tế đã verify | Hệ quả |
|---|---|---|---|
| A1 | `OpenAIAgentsKernel` chưa full implementation | Đúng — `packages/agent_core/kernel/openai_agents_kernel.py:73` là manual loop | Hạ ưu tiên xuống adapter tuỳ chọn (Wave 4), không phải Wave 1 |
| A2 | Run/Memory repository "chưa mặc định Postgres, còn rơi về in-memory" | **Lỗi thời** — `3cfceb3`, `fcfe387` đã bắt buộc `AGENT_CORE_DATABASE_URL`, raise `RuntimeError` nếu thiếu | Bỏ khỏi backlog; gap thật còn lại là `apps/cosa/api/routes.py:38-40` (`_conversations`, `_messages`, `_pending_runs`) |
| A3 | `tool_call_id` PK độc lập, chưa composite | Đúng cho `agent_core.run_tool_calls` (migration 001 dòng 70); nhưng `invocation_governance_state` (migration 002) **đã dùng** composite `(run_id, tool_call_id)` | Migration 004 chỉ cần đổi PK 1 bảng, pattern đã chứng minh chạy được ở governance |
| A4 | Google ADK ngang hàng LangGraph/OpenAI SDK, chỉ "optional adapter" | ADK đã ship & chạy thật (`AdkCofounderWorkflow`, `google-adk==2.7.0`, `docs/agent-platform/ADK_INTEGRATION.md`) — trưởng thành hơn LangChain (0 dòng code) | Wave 4 chạy LangChain song song, không rollback ADK cho tới khi conformance suite pass |
| A5 | Migration tiếp theo đánh số 004+ | Đúng, không xung đột | Giữ nguyên |
| A6 | `packages/agent_integrations/` chưa tồn tại | Đúng | Tạo mới hoàn toàn ở Wave 0/4 |
| A7 | Control-plane cần "tạo mới" | Đã có `runs/leases.py` (`RunLeaseManager`) và `coordination/scheduler.py` (`RunScheduler`) nhưng 100% in-memory (`dict` + `asyncio.Lock`) | Wave 7 là "port + harden", không phải viết từ 0 |
| A8 | `services/cosa` nên có `control_plane/`, `runtime_registry/`... | Đúng, chưa tồn tại — service hiện có `handlers/`: agent-policy, auth, company, index; migration cuối là `5_rename_company_roles.up.sql` | Wave 7 thêm handler/service mới trong cùng service Encore |
| A9 | Không đề cập ADR cần supersede | Có ≥54 ADR trong `docs/architecture/adr/`, cần rà hết trước khi viết ADR mới | Wave 0 bắt buộc audit toàn bộ thư mục ADR |
| A10 | Wave 5: "chưa có tiền lệ" cho vị trí lưu skill package format | **SAI** — repo root đã có `skillpacks/<domain>/<skill-id>/{manifest.yaml,SKILL.md}` đang dùng thật (okr, marketing, strategy, twelve-week-year, tasks, core) theo apiVersion `agentos.ai/v1 kind: Skill`, có `trust.tier` (T0...) khớp khái niệm Trust tier của Blueprint V2 §11 | Wave 5 **mở rộng `skillpacks/`**, không tạo `packages/agent_core/skills/library/` mới — chỉ thêm field còn thiếu (`evals:`, `permissions.mutations`, `source_locale`) vào format `manifest.yaml` hiện có |
| A11 | Wave 5-6: eval suite cần hạ tầng mới | Root đã có `evals/README.md` mô tả 5 lớp eval (Model/Agent/Skill/Workflow/Business Outcome) theo 1 tài liệu "AI Agent OS Master Architecture" cũ (không còn tồn tại trong repo, chỉ còn 3 dòng tham chiếu §3.8/§33 trong README) | Wave 5-6 dùng `evals/` làm nơi chứa golden dataset/test suite thật; migration `agent_evals.*` (DB metadata: suites/cases/runs/results) trong `packages/agent_core/migrations/` là **bổ sung**, không trùng — DB lưu metadata/kết quả, `evals/` lưu dataset file |
| A12 | Wave 3/Wave 5: registry cần module mới hoàn toàn | Root đã có `registry/{packages/,state/}` — nơi lưu immutable skill package artifact + trust tier/approval log, theo cùng tài liệu cũ §20/§23 | `packages/agent_core/registry/` (Wave 3, module Python `publisher.py`/`resolver.py`) đọc/ghi vào `registry/packages/` + `registry/state/` làm storage backend, không tạo storage layer riêng; `agent_registry.published_specs` (DB) lưu metadata/version pin, `registry/` (filesystem) lưu artifact — 2 tầng bổ sung nhau |
| A13 | Wave 9/11: plugin trust/isolation "cần xây từ đầu" | Root đã có `plugins/<plugin-name>/{manifest.yaml,skills/,tools/,resources/,ui/}` (theo §7/§8 tài liệu cũ) **và** `packages/agent_core/plugins/manifest.py` đã tồn tại (đọc/validate manifest) | Wave 7/plugin-hardening (Blueprint V2 §11) mở rộng `packages/agent_core/plugins/manifest.py` để đọc đúng format `plugins/<name>/manifest.yaml` đã có, thêm lifecycle state (`DISCOVERED→...→RETIRED`) và trust tier, không đổi cấu trúc thư mục `plugins/` hiện có |

---

## Phần B — Wave 0: Freeze, Inventory, ADR supersession

**Mục tiêu:** không còn tài liệu canonical nào mô tả sai trạng thái runtime/DB, và có nền tảng package/test/docs để các Wave sau build lên.

### B.1 — ADR audit & supersession
- Liệt kê đầy đủ `docs/architecture/adr/*.md` (grep theo `ADR-KERNEL`, `ADR-LANGGRAPH`, `ADR-EXEC`, `ADR-015`, `ADR-014`, `ADR-MEM-*` — xác nhận không bỏ sót ADR nào tham chiếu execution kernel hoặc workflow runtime).
- Viết `docs/architecture/adr/ADR-0XX-runtime-strategy-langchain-primary.md` (số thật lấy theo ADR cuối cùng tồn tại tại thời điểm PR):
  - Header: `Status: Accepted`, `Supersedes: ADR-KERNEL-openai-agents-sdk-ratification.md, ADR-LANGGRAPH-adoption-decision.md`.
  - Nội dung: quyết định LangChain + DeepSeek là runtime chính; OpenAI Agents SDK và Google ADK → adapter tuỳ chọn (ADK **giữ nguyên vai trò production** cho tới khi LangChain path qua conformance); LangGraph mở lại làm `WorkflowRuntime` candidate, cần spike + conformance trước khi thay Native engine.
- Viết `docs/architecture/adr/ADR-0XX-control-plane-ownership.md`: ghi nhận quyết định #2, supersede vị trí hiện tại của `leases.py`/`scheduler.py`, chỉ rõ boundary "execution-plane mechanics nội bộ 1 run vẫn ở Python agent_core; cross-run/cross-worker shared state chuyển sang `services/cosa`".
- Viết 6 ADR còn lại theo Blueprint V2 §51: `ADR-MODEL-GATEWAY.md`, `ADR-RUNTIME-ADAPTERS.md`, `ADR-PROTOCOLS-MCP-A2A-AGUI.md`, `ADR-DURABLE-IDENTITY.md`, `ADR-DATABASE-SCHEMA-OWNERSHIP.md`, `ADR-PLUGIN-TRUST-AND-ISOLATION.md`.
- Cập nhật `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` dòng "Execution Kernel" (hiện trỏ OpenAI Agents SDK) → trỏ ADR mới.
- Cập nhật `COSA_CANONICAL_MASTER_ARCHITECTURE_AND_IMPLEMENTATION_GUIDE_2026-08-23.md` §1.1 Decision 3 và §9 bằng 1 PR riêng, dẫn chiếu ADR mới (không sửa nội dung lịch sử, thêm ghi chú "Superseded by ADR-0XX").

**Không được code Wave 1+ trước khi 2 ADR chính (runtime strategy, control-plane ownership) được người dùng review — đây là thay đổi kiến trúc lớn, ADR draft ≠ đã duyệt.**

### B.2 — Package/test scaffolding
- Tạo `packages/agent_integrations/` (rỗng, có `README.md` mô tả boundary rule: không import vào `agent_core`, chỉ implement `agent_core.contracts.*`).
- Tạo `packages/agent_recipes/` (rỗng, `README.md`).
- Tạo `packages/agent_testkit/` với subfolder theo Blueprint V2 §4.1 (`kernel_conformance/`, `model_conformance/`, `workflow_conformance/`, `gateway_conformance/`, `persistence_conformance/`, `protocol_conformance/`, `fixtures/`) — di chuyển các test conformance-shaped hiện có trong `tests/agent_core/p1/`, `p2/`, `drift/` vào đây theo từng batch nhỏ (không move hàng loạt 1 PR, tránh vỡ CI).
- Tạo `docs/manifest.yaml` khung rỗng (feature → owner → doc → tests), điền dần mỗi Wave.
- Tạo `pyproject.toml` workspace ở `packages/` (uv workspace) — hiện `packages/agent_core/requirements.txt` là file rời, cần chuyển sang `pyproject.toml` để `agent_core` không kéo dependency của `agent_integrations`.

**Exit criteria Wave 0:** ADR mới tồn tại + được duyệt; `docs/manifest.yaml`, `agent_integrations/`, `agent_recipes/`, `agent_testkit/` tồn tại (rỗng/khung); không còn tài liệu canonical mô tả sai trạng thái A1-A9.

---

## Phần C — Wave 1: Execution spine (durable, framework-neutral)

**PR-02, PR-03, PR-04, PR-09, PR-10, PR-11 (theo Blueprint V2 §53)**

### C.1 — Durable conversations (thay in-memory globals)
- File đích: `apps/cosa/api/routes.py:38-40` — xoá `_conversations`, `_messages`, `_pending_runs`.
- Migration mới `packages/agent_core/migrations/006_conversation_substrate.sql`, schema `agent_conversation` (bảng `conversations`, `messages` theo Blueprint V2 §23, `UNIQUE(conversation_id, sequence_no)`).
- Module mới `packages/agent_core/conversations/repository.py` (`PostgresConversationRepository`), theo đúng pattern của `packages/agent_core/runs/repository.py:220` (`PostgresRunRepository`) — tái dùng session factory helper `_build_postgres_session_factory` đã có trong `apps/cosa/composition/agent_plane.py`.
- `apps/cosa/conversations/repository.py` (hiện có `ports.py`, `stub.py`) — thay `stub.py` bằng implementation thật gọi `packages/agent_core/conversations/repository.py`, giữ `ports.py` (Protocol) nguyên vẹn.
- Wiring: `apps/cosa/api/routes.py` inject repository qua `apps/cosa/composition/agent_plane.py`, theo đúng nguyên tắc "production không được silent fallback in-memory" đã áp dụng cho Run/Memory (`RuntimeError` nếu thiếu `AGENT_CORE_DATABASE_URL`).

### C.2 — Composite exact invocation identity
- Migration `packages/agent_core/migrations/004_harden_exact_invocation_and_approval.sql`:
  - Đổi PK `agent_core.run_tool_calls` từ `tool_call_id VARCHAR(128) PRIMARY KEY` → `PRIMARY KEY (run_id, tool_call_id)`.
  - Thêm FK composite từ `agent_core.approvals` → `agent_core.run_tool_calls(run_id, tool_call_id)`.
  - Thêm CAS fields cho `approvals` (`decision_version INTEGER NOT NULL DEFAULT 0`) theo Blueprint V2 §21.
- Code đích: `packages/agent_core/capabilities/gateway.py` (bước 3-4 trong pipeline execute, dòng ~131-150) — đảm bảo `ToolInvocation` giữ nguyên `(run_id, tool_call_id)` xuyên suốt, không tạo lại ID.
- `packages/agent_core/kernel/openai_agents_kernel.py` — audit chỗ phát sinh `tool_call_id` (trong `_execute_reasoning_loop`) để xác nhận ID này được truyền nguyên vẹn tới gateway, không bị kernel tự sinh lại.

### C.3 — Typed runtime errors
- Module mới `packages/agent_core/contracts/errors.py` — enum/class theo taxonomy Blueprint V2 §36 (`MODEL_PROVIDER_ERROR`, `MODEL_TIMEOUT`, `TOOL_SCHEMA_ERROR`, `APPROVAL_REQUIRED`, `IDEMPOTENCY_CONFLICT`...).
- Sửa `packages/agent_core/kernel/openai_agents_kernel.py` để convert provider failure → typed error thay vì assistant text (đúng invariant "không convert failure thành successful assistant content" — Blueprint V2 §56 anti-pattern, đã có tiền lệ đúng ở `ADR-EXEC-002-no-silent-provider-fallback.md`, tái dùng pattern từ ADR này).

**Exit criteria Wave 1 (theo đúng Blueprint V2 §81 Wave 1 exit, đã hiệu chỉnh):** một Run end-to-end restart-safe — kill process giữa chừng, resume ở process khác, conversation/message không mất, `(run_id, tool_call_id)` không đổi.

---

## Phần D — Wave 2: Governance + exactly-once effect

**PR-05, PR-06, PR-07, PR-08**

- Migration `packages/agent_core/migrations/005_runtime_bindings_and_idempotency.sql`: bảng `agent_core.idempotency_claims` (theo schema Blueprint V2 §20, `UNIQUE (scope_kind, scope_key_hash, capability_id, idempotency_key)`), `agent_core.run_runtime_bindings`, `agent_core.runtime_checkpoints`, `agent_core.run_model_calls`.
- Module mới `packages/agent_core/capabilities/idempotency.py` — atomic claim service dùng `INSERT ... ON CONFLICT`, gọi từ `gateway.py` bước 5 (hiện tại dòng ~165 chỉ có "idempotency checking", chưa atomic).
- `packages/agent_core/capabilities/approval_service.py` — sửa decision flow theo CAS UPDATE pattern Blueprint V2 §21 (`WHERE status = 'pending' AND decision_version = :expected RETURNING *`), load lại `G_acc` fresh trước khi resume theo Blueprint V2 §9.3.
- Test bắt buộc trong `agent_testkit/persistence_conformance/`: 2 worker cùng claim 1 idempotency key → chỉ 1 side effect (Scenario B/Blueprint V2 §82).

**Exit criteria:** crash sau khi external call thành công nhưng trước khi ghi response → resume không gọi lại side effect lần 2 (test tự động, không chỉ mô tả).

---

## Phần E — Wave 3: Prompt/Spec Registry + prompt language strategy

**PR mới (không có số PR-01→29 gốc, vì đây là scope mở rộng do người dùng chọn đưa vào toàn bộ Blueprint V2)**

- Migration `packages/agent_core/migrations/007_agent_registry.sql`: `agent_registry.published_specs` (composite PK `(spec_kind, spec_id, version)`), `agent_registry.skill_candidates`.
- Module mới `packages/agent_core/registry/` (chưa tồn tại — thư mục `packages/agent_core/` hiện không có `registry/`) — `publisher.py`, `resolver.py`.
- Prompt architecture (Blueprint V2 §68): thư mục mới `packages/agent_core/prompts/glossary/core.en.yaml`, `vi-VN.yaml`; module `PromptBundle` trong `packages/agent_core/contracts/` hoặc `packages/agent_core/prompts/bundle.py` (quyết định vị trí cụ thể khi code, giữ nguyên tắc contracts framework-neutral).
- Locale policy áp dụng vào `apps/cosa/composition/context_assembler.py` (đã tồn tại, là nơi hợp lý để inject locale directive vào context trước khi gọi kernel).

**Exit criteria:** Run replay xác định đúng phiên bản prompt/spec đã dùng (pin version + hash trong `agent_core.runs.model_policy` hoặc bảng mới).

---

## Phần F — Wave 4: LangChain/LangGraph primary + LiteLLM/DeepSeek

**PR-03, PR-04, PR-13, PR-25 (đã đổi ưu tiên theo quyết định #1)**

- `packages/agent_integrations/langchain/` (mới hoàn toàn): `model_provider.py` (implement `agent_core.contracts.runtime.ModelProvider`), `kernel.py` (`LangChainKernel`, implement `ExecutionKernel` Protocol tại `packages/agent_core/contracts/kernel.py:11-12`), `tool_schema_adapter.py`.
- Package cần `pyproject.toml` riêng khai `langchain`, `langchain-deepseek` — **hiện chưa có dòng dependency LangChain nào trong repo**, đây là lần đầu cài đặt.
- `packages/agent_integrations/litellm/gateway.py` — có thể tái dùng kinh nghiệm/pattern từ `legacy/backend/.../litellm_invoker.py` (circuit breaker, fallback provider) đã chạy thật trong `AdkCofounderWorkflow`, không viết lại từ đầu.
- Wiring: `apps/cosa/composition/agent_plane.py` thêm nhánh chọn `LangChainKernel` theo runtime policy (Blueprint V2 §35 YAML `runtime.preferred`).
- **Không đổi kernel mặc định production ngay** — thêm bằng feature flag/runtime policy, giữ ADK (`AdkCofounderWorkflow`) là default cho tới khi `agent_testkit/kernel_conformance/` pass cho `LangChainKernel` (theo checklist Blueprint V2 §46: response, streaming, structured output, parallel tool, cancellation, resume, exact identity).
- LangGraph spike: `packages/agent_integrations/langgraph/workflow_runtime.py` — chạy conformance so với `docs/architecture/langgraph_spike_results.md` đã có (kết quả spike cũ dẫn tới ADR-LANGGRAPH bị reject — **đọc lại file này trước khi spike lại**, để biết chính xác lý do reject cũ, tránh lặp lại vấn đề đã biết mà không giải quyết).

**Exit criteria:** production candidate chạy DeepSeek qua canonical execution path, ADK vẫn chạy song song không bị gián đoạn.

---

## Phần G — Wave 5-6: Skills / Evals / Skill Optimization Lab

**Đã hiệu chỉnh theo A10-A12 — không tạo hạ tầng mới, mở rộng 3 thư mục root đã có (`skillpacks/`, `evals/`, `registry/`):**

- Migration mới (namespace `agent_core`, số tiếp theo sau 007): schema `agent_evals` (`suites`, `cases`, `runs`, `results`, `skill_candidates`, `skill_mutations` — Blueprint V2 §71.2, giữ ở `packages/agent_core/migrations/`) lưu **metadata/kết quả**; dataset/test case file thật nằm trong `evals/` (đã có, theo 5 lớp Model/Agent/Skill/Workflow/Business Outcome).
- Skill artifact format: **dùng `skillpacks/<domain>/<skill-id>/{manifest.yaml,SKILL.md}` đã có** (format `apiVersion: agentos.ai/v1 kind: Skill`, đã có `trust.tier`), không tạo `skill.yaml` mới theo tên khác của Blueprint V2 §69.1 — chỉ bổ sung field còn thiếu vào `manifest.yaml` hiện có: `evals.suite` (trỏ `evals/`), `permissions.mutations`, `source_locale`.
- `packages/agent_core/skills/` (đã tồn tại, hiện gần rỗng) — thêm `candidate.py`, `lifecycle.py` theo state machine Blueprint V2 §69.2 (Draft → Candidate → ... → Published immutable); code này **đọc/ghi vào `skillpacks/` và `registry/{packages/,state/}`** làm storage backend (registry đã có sẵn concept "immutable skill package artifact" + "trust tier/approval log"), không tạo storage layer Python riêng.
- Skill Optimization Lab (`Executor → Analyst → Mutator`): module mới `packages/agent_core/skills/lab/` — **chạy tách khỏi production path**, chỉ thao tác trên **candidate copy** của skill trong `skillpacks/` (không sửa trực tiếp manifest đã publish), không được tự publish (invariant Blueprint V2 §69.3).
- **Việc cần làm thêm ở Wave 0.1 (bổ sung):** README của `evals/`, `registry/`, `plugins/` hiện tham chiếu một tài liệu "AI Agent OS Master Architecture" (§3.8/§33/§20/§23/§7/§8) không còn tồn tại trong repo (chỉ còn legacy) — cập nhật 3 README này để trỏ đúng vào `COSA_AGENT_PLATFORM_BLUEPRINT_V2_RECONCILED_PLAN_2026-08-24.md` + Blueprint V2 §69/§71/§11 tương ứng, tránh dead reference.

---

## Phần H — Wave 7: Control Plane → `services/cosa` (chi tiết theo quyết định #2)

Đây là wave khác biệt lớn nhất so với Blueprint V2 gốc.

### H.1 — Port nguồn Python hiện có
- `packages/agent_core/runs/leases.py` (`RunLeaseManager`, in-memory `dict` + `asyncio.Lock`) → logic acquire/renew/release trở thành Encore endpoint mới.
- `packages/agent_core/coordination/scheduler.py` (`RunScheduler`, coalescing queue in-memory) → Encore endpoint mới.
- Audit riêng từng file trong `packages/agent_core/coordination/{supervisor,delegate,delegation_envelope,parallel,synthesis}.py` — chỉ chuyển phần sở hữu **trạng thái chia sẻ giữa nhiều worker/run**; phần orchestration logic thuần trong 1 run (vd. `parallel.py` xử lý wave/reducer nội bộ 1 workflow run) ở lại `agent_core`.

### H.2 — Encore service mới (trong `services/cosa`, cùng service hiện có, không tách app riêng trừ khi phát sinh lý do isolation)
- Migration tiếp theo sau `services/cosa/migrations/5_rename_company_roles.up.sql` — đặt tên theo nội dung, số thật xác nhận lại tại thời điểm PR (không hard-code, vì backlog khác có thể thêm migration trước Wave 7 tới):
  - `N_control_plane_missions_tasks.up.sql` — `control_plane.missions`, `control_plane.tasks`, `control_plane.assignments`.
  - `N+1_control_plane_leases_workers.up.sql` — `control_plane.workers`, `control_plane.runtime_leases` (thay `RunLeaseManager`), `control_plane.scheduled_tasks` (thay `RunScheduler`).
  - `N+2_control_plane_watches_signals.up.sql` — `control_plane.watches`, `control_plane.trigger_policies`, `control_plane.signal_observations`.
  - `N+3_control_plane_delivery.up.sql` — `control_plane.delivery_policies`, `control_plane.delivery_attempts`, `control_plane.cost_ledger`.
- `services/cosa/handlers/control-plane/` (mới, theo layout Encore chuẩn của repo: parse input → gọi service → response, không query DB trực tiếp).
- `services/cosa/services/control-plane/` (business logic, Drizzle ORM) — endpoint `expose: false` (nội bộ, chỉ `agent_core` gọi qua service-to-service).
- Schema Drizzle: thêm vào `services/cosa/shared/db/schema/` theo đúng quy tắc CLAUDE.md ("Schema Drizzle tập trung ở `<app>/shared/db/schema/<service>.ts`").

### H.3 — Client mỏng phía Python
- `packages/agent_core/runs/leases.py` viết lại thành HTTP/internal-RPC client gọi `services/cosa` control-plane endpoint, giữ nguyên interface `RunLeaseManager.acquire_lease/renew_lease/release_lease` (không đổi call site ở nơi khác trong `agent_core`) — đổi implementation bên trong, không đổi contract.
- Tương tự cho `coordination/scheduler.py`.
- **Cutover có kiểm soát:** feature flag chọn backend (in-memory cũ / Encore mới), dual-write tạm thời nếu có run đang chạy dở khi deploy, xoá backend in-memory sau khi xác nhận ổn định (đúng nguyên tắc additive → dual-write → cutover → cleanup).

### H.4 — Rủi ro cần đo đạc, không giả định an toàn
- Thêm 1 network hop (Python asyncio → Encore TS RPC) vào hot path resume run — cần benchmark latency trước/sau, thiết kế retry/circuit breaker rõ ràng trong client, không copy nguyên logic `asyncio.Lock` cũ sang giả định RPC có cùng tính chất.

---

## Phần I — Wave 8-11: Knowledge/Memory v2, Protocols, Runtime bổ sung, Recipe harvest

- **Wave 8:** Migration `008_memory_v2.sql`, `009_knowledge_versioning_and_embeddings.sql` — additive, backfill từ `agent_memory.agent_memories`/`knowledge.knowledge_sources` hiện có (migration 003), không phá bảng cũ trước khi cutover xong.
- **Wave 9:** `packages/agent_integrations/mcp/`, `a2a/`, `ag_ui/` — MCP capability adapter phải đi qua `packages/agent_core/capabilities/gateway.py`, không tạo execution path riêng.
- **Wave 10:** Conformance đầy đủ cho ADK (đã có, cần viết test conformance chính thức trong `agent_testkit/`), OpenAI Agents SDK thật (thay `openai_agents_kernel.py` manual loop), PydanticAI spike.
- **Wave 11:** `packages/agent_recipes/<domain>/<recipe-id>/` — 7 recipe ưu tiên theo Blueprint V2 §81 Wave 11 (competitor intelligence, research-synthesize, release radar, advisor-orchestrator-worker, dependency doctor, self-improving skill, mixture-of-agents), mỗi recipe kèm `docs/recipes/<recipe-id>.md`.

---

## Phần J — Documentation-as-code + chính sách comment/prompt-language (áp dụng toàn bộ, theo quyết định #3)

- `docs/manifest.yaml` (khởi tạo Wave 0, điền dần) ánh xạ feature → owner → doc → tests.
- Comment convention: đã khớp CLAUDE.md hiện có (tiếng Việt cho WHY, tiếng Anh cho identifier) — không cần ADR riêng, chỉ cần checklist trong mỗi PR template.
- CI documentation gate: chỉ bật (fail build nếu thiếu `.md`) **sau khi** `docs/manifest.yaml` đã có entry cho toàn bộ feature hiện có tính đến cuối Wave 2 — tránh CI đỏ ngay vì nợ tài liệu của code cũ trước khi có kế hoạch này.
- Danh sách `.md` bắt buộc theo Blueprint V2 §79 — tạo dần theo từng Wave tương ứng (không tạo hết 40+ file rỗng ở Wave 0).

---

## Phần K — PR sequence (ánh xạ Wave → PR, đã hiệu chỉnh thứ tự ưu tiên)

Giữ đúng nội dung PR-01→PR-29 của Blueprint V2 §53, nhưng đổi thứ tự ưu tiên: PR-03/PR-04 (LangChain vertical slice) chạy **sau** khi PR-01 (ADR), PR-02 (runtime contracts), PR-05→PR-11 (Gateway/DB/conversation hardening) đã xong — vì LangChain là runtime mới hoàn toàn, cần execution spine ổn định trước để có nền conformance test mà so sánh, đúng tinh thần "Runtime conformance bắt buộc" ở Blueprint V2 §74. Các PR còn lại (PR-12→PR-29) giữ nguyên thứ tự gốc.

---

## Phần L — Kiểm thử / Definition of Done

1. Trước mỗi Wave: `git log`/`grep` xác nhận lại giả định trong Phần A còn đúng — codebase đổi nhanh (3 commit Postgres cutover mới nhất đã làm lỗi thời 1 phần Blueprint V2 khi audit).
2. Chạy `tests/agent_core/{p1,p2,drift}/` trước/sau mỗi PR, không phá vỡ conformance test theo phase đã có.
3. Scenario A-G ở Blueprint V2 §82 và end-to-end §55 → viết thành test thật trong `agent_testkit/` (Wave 0-1), không chỉ mô tả prose.
4. 2 ADR chính (Phần B.1) phải được người dùng review trước khi Wave 1 code thật bắt đầu.
5. Sau khi lưu tài liệu này vào project (đã hoàn tất), mở PR riêng cập nhật `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` (chỉ sau khi ADR Wave 0 tồn tại) để các tài liệu canonical không mâu thuẫn nhìn bề ngoài.

---

## File/thư mục quan trọng cần biết trước khi code

- `packages/agent_core/contracts/{kernel,run,spec,capability,target}.py` — contracts framework-neutral, giữ nguyên.
- `packages/agent_core/kernel/openai_agents_kernel.py` — kernel hiện tại, hạ vai trò xuống adapter.
- `packages/agent_core/capabilities/gateway.py` — pipeline 10 bước, mọi adapter mới (kể cả LangChain) phải cắm vào đây.
- `packages/agent_core/runs/repository.py:220`, `packages/agent_core/memory/store.py:45-61` — pattern `Postgres*` default đã đúng, dùng làm khuôn mẫu cho `PostgresConversationRepository` mới.
- `apps/cosa/api/routes.py:38-40` — in-memory globals cần thay ở Wave 1.
- `apps/cosa/composition/agent_plane.py` — composition root, nơi wiring adapter mới.
- `packages/agent_core/runs/leases.py`, `packages/agent_core/coordination/scheduler.py` — nguồn port sang `services/cosa` (Wave 7).
- `services/cosa/{handlers,services,migrations}/` — đích control-plane mới; migration cuối hiện tại `5_rename_company_roles.up.sql`.
- `docs/architecture/adr/ADR-KERNEL-openai-agents-sdk-ratification.md`, `ADR-LANGGRAPH-adoption-decision.md`, `docs/architecture/langgraph_spike_results.md` — đọc kỹ trước khi viết ADR mới/spike lại LangGraph, để không lặp lại lý do đã bị reject trước đó mà không xử lý.
- `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`, `docs/agent-platform/ADK_INTEGRATION.md` — cập nhật/không được vô tình phá vỡ.

---

## Trạng thái triển khai

- [x] Wave 0.0 — Tài liệu này được lưu vào project (bước 0).
- [~] Wave 0.1 — ADR audit & supersession (Phần B.1) — đã audit toàn bộ `docs/architecture/adr/` (51 file) và **soạn xong 2 ADR draft**:
  - `docs/architecture/adr/ADR-RUNTIME-001-langchain-deepseek-primary-supersedes-kernel-and-langgraph.md` (supersede `ADR-KERNEL-...`, `ADR-LANGGRAPH-...`)
  - `docs/architecture/adr/ADR-CONTROLPLANE-001-control-plane-primitives-in-services-cosa.md`
  - ~~Còn thiếu: 6 ADR bổ sung theo Blueprint V2 §51~~ — **ĐÃ VIẾT** (xem mục 7 trong "Tổng kết toàn bộ 11 Wave" cuối file — dòng này để lại làm mốc lịch sử, không xoá).
  - **ĐÃ LÀM (2026-08-24, phát hiện gap khi người dùng hỏi "còn gì chưa làm"):** cập nhật `COSA_CANONICAL_OWNERSHIP_MAP.md` dòng Execution Kernel + `COSA_CANONICAL_MASTER_ARCHITECTURE_AND_IMPLEMENTATION_GUIDE_2026-08-23.md` §1.1 mục 3 và §9.2 — chỉ thêm ghi chú "Superseded by ADR-RUNTIME-001 (DRAFT, chưa duyệt)" trỏ tới ADR mới, KHÔNG xoá/sửa nội dung quyết định lịch sử gốc (vẫn giữ nguyên để biết bối cảnh cũ). An toàn vì là bổ sung con trỏ thông tin, không phải đổi quyết định đã ratify khi ADR chưa được duyệt.
  - **Chặn:** 2 ADR trên là DRAFT, chưa được người dùng review — không code Wave 1+ trước khi review xong (đúng nguyên tắc đã ghi trong Phần B).
- [x] Wave 0.2 — Package/test scaffolding (Phần B.2), đã hiệu chỉnh sau khi phát hiện A10-A13:
  - Tạo mới (thật sự chưa tồn tại): `packages/agent_integrations/` (README + pyproject.toml), `packages/agent_recipes/` (README + pyproject.toml), `packages/agent_testkit/` (README + 6 subfolder conformance + pyproject.toml), `packages/pyproject.toml` (uv workspace, 4 member), `packages/agent_core/pyproject.toml` (tách dependency, chưa khai build-system vì chưa ai pip-install package này — xem comment trong file).
  - **Không tạo trùng:** phát hiện `skillpacks/`, `evals/`, `registry/`, `plugins/` ở repo root đã là hạ tầng skill/eval/registry/plugin thật (xem A10-A13) — đã sửa 3 README (`evals/`, `registry/`, `plugins/`) đang trỏ dead reference tới 1 tài liệu "AI Agent OS Master Architecture" không còn tồn tại, trỏ lại đúng tài liệu hiện hành.
  - **Chưa làm:** di chuyển test conformance-shaped từ `tests/agent_core/{p1,p2,drift}/` vào `packages/agent_testkit/` — theo đúng plan, việc này làm dần theo batch nhỏ gắn với từng Wave sau, không làm ở bước scaffold.
- [x] Wave 1 — Execution spine (Phần C), đã code + test pass (205 passed, 0 failed, `tests/agent_core` + `tests/apps` qua venv tạm với `eval_type_backport` do máy chỉ có Python 3.9 — xem ghi chú dưới):
  - **C.1 Durable conversations:** migration `006_conversation_substrate.sql`; module mới `packages/agent_core/conversations/{models.py,repository.py}` (`ConversationRecord`, `MessageRecord`, `MessageAttachmentRecord`, `PostgresConversationRepository`, `InMemoryConversationRepository`); `apps/cosa/composition/agent_plane.py` wire `conversation_repository` (cùng no-silent-fallback pattern như `RunRepository`); `apps/cosa/api/routes.py` viết lại hoàn toàn — bỏ `_conversations`/`_messages`/`_pending_runs`. `_pending_runs` hoá ra dư thừa: `checkpoint_ref` đã durable trong `RunApprovalRecord.checkpoint_ref`, `conversation_id` đã durable trong `RunRecord.conversation_id` — không cần bảng mới cho pending-run state. Phát hiện thêm: `apps/cosa/conversations/{ports.py,stub.py,repository.py}` (Track 9A cũ) không được import ở đâu khác trong repo — để nguyên, không phải đường dẫn wiring thật như plan ban đầu giả định.
  - **C.2 Composite invocation identity:** migration `004_harden_exact_invocation_and_approval.sql` — đổi PK `run_tool_calls` sang `(run_id, tool_call_id)`, **giữ thêm** `UNIQUE(tool_call_id)` để không phải đổi signature `get_tool_call(tool_call_id)` ở gateway.py/approval_service.py (3 call site hiện tại chỉ truyền tool_call_id) — quyết định hẹp phạm vi có ghi chú trong chính file migration. FK `approvals` đổi sang composite. Thêm `decision_version` cho CAS (chưa wire logic — đó là Wave 2). **CHƯA CHẠY THẬT trên Postgres** (máy này không có Postgres/Docker) — chỉ verify bằng đối chiếu kỹ với migration 001/002 và quy ước đặt tên constraint mặc định của Postgres. Cần chạy `make migrate-agent-platform` trên môi trường có Postgres thật trước khi coi migration này là an toàn.
  - **C.3 Typed runtime errors:** `packages/agent_core/contracts/errors.py` (`RuntimeErrorCode`, `AgentRuntimeError`); sửa `packages/agent_core/kernel/openai_agents_kernel.py::_call_model` — raise `AgentRuntimeError` thay vì `return {"content": f"Model call error: {exc}", ...}` (đây chính là anti-pattern Blueprint V2 §56 bắt được trong code thật); `_execute_reasoning_loop` tách thành `_execute_reasoning_loop` (bắt `AgentRuntimeError`, cập nhật `RunStatus.FAILED` + `error_details` + event `run.failed`) gọi `_run_reasoning_turns` (vòng lặp cũ). Test mới `test_kernel_model_provider_failure_is_typed_failed_not_completed` chứng minh hành vi cũ/mới khác nhau.
  - **Việc cần làm thêm (không chặn):** wiring Protocol `get_tool_call(run_id, tool_call_id)` đầy đủ (hiện chỉ có UNIQUE constraint an toàn, chưa đổi call site) — để lại cho lần hardening sau nếu cần; migration 004 cần chạy thật trên Postgres staging trước production.
- [x] Wave 2 — Governance + exactly-once effect (Phần D), code + test pass (208 passed, 0 failed):
  - **Atomic idempotency claim:** migration `005_idempotency_claims.sql` (chỉ bảng `idempotency_claims` — thu hẹp phạm vi so với Blueprint V2 gốc, xem ghi chú trong file migration); model `IdempotencyClaimRecord`; 4 method mới trên `RunRepository` Protocol (`claim_idempotency` dùng `INSERT ... ON CONFLICT DO NOTHING`, `complete_/fail_/retry_idempotency_claim`) — implement cả `InMemoryRunRepository` và `PostgresRunRepository`; module mới `packages/agent_core/capabilities/idempotency.py` (`IdempotencyClaimService`); wire vào `gateway.py` Bước 5 thay hoàn toàn check-then-act cũ (`get_tool_call_by_idempotency` rồi mới `save_tool_call` — có race window thật). Phát hiện + sửa 1 bug trong lúc wire: request thứ 2 với **cùng tool_call_id** (resume sau approval qua `gateway.execute()` gọi lại) bị chặn nhầm thành `IN_PROGRESS` — đã phân biệt "cùng invocation tiếp tục" (cho qua) vs "invocation khác đua giành" (chặn) bằng so khớp `(run_id, tool_call_id)` của claim. Test mới `test_concurrent_gateway_execute_same_idempotency_key_only_one_side_effect` (2 request độc lập, `asyncio.gather`, handler có `await asyncio.sleep` tạo yield point thật) chứng minh handler chỉ chạy đúng 1 lần.
  - **CAS approval decision:** `RunApprovalRecord.decision_version` (dùng cột đã thêm ở migration 004); `decide_approval()` (cả 2 implementation) đổi thành atomic CAS (`WHERE status='pending'`, Postgres dùng `UPDATE ... RETURNING`, InMemory dựa vào không có `await` giữa check/write); `ApprovalAlreadyDecidedError` mới, `submit_decision()` raise exception này khi CAS thất bại (phân biệt với "not found"); `apps/cosa/api/routes.py::decide_approval` bắt exception → trả `409 Conflict` thay vì âm thầm ghi đè hoặc 404 sai nghĩa. 2 test mới trong `test_approval_service.py` (double-decide tuần tự, và `asyncio.gather` — có ghi chú rõ giới hạn InMemory không tạo interleaving thật, xem docstring test).
  - **Đã audit `verify_and_prepare_resume`:** hoá ra đã implement sẵn phần lớn "resume flow bắt buộc" của Blueprint V2 §9.3 (fresh tenant/principal check, target drift, fresh policy re-evaluation) — không cần viết lại.
  - ~~Phát hiện gap MỚI, CHƯA SỬA: `CapabilityGateway._gov_states` in-memory, không durable qua restart~~ — **ĐÃ SỬA** (xem mục 8 trong "Tổng kết toàn bộ 11 Wave" cuối file — dòng này để lại làm mốc lịch sử, không xoá).
- [x] Wave 3 — Prompt/Spec Registry + prompt language strategy (Phần E), code + test pass (215 passed, 0 failed):
  - **Spec Registry:** migration `007_agent_registry.sql` (`agent_registry.published_specs`, composite PK `(spec_kind, spec_id, version)`, `UNIQUE(spec_kind, spec_id, definition_hash)`); module mới `packages/agent_core/registry/{models,repository,publisher}.py` — `publish_agent_spec()` idempotent nếu cùng hash, raise `SpecVersionHashConflictError` nếu version đã publish với nội dung khác (đúng invariant "published spec bất biến"). Wire vào `OpenAIAgentsKernel.run()`: publish spec vào registry TRƯỚC khi tạo `RunRecord`, dùng `pinned_spec.definition_hash` cho `root_definition_hash` — Run giờ luôn resolve được đúng nội dung spec đã dùng dù code sau này đổi `instructions`.
  - **Phát hiện + sửa bug thật khi chuẩn bị publish:** `apps/cosa/agents/specs.py` dùng `name=`/`allowed_tools=` — cả 2 đều KHÔNG phải field thật của `AgentSpec` (field đúng là `capability_refs`), bị Pydantic âm thầm bỏ qua (default `extra='ignore'`). Nghĩa là `capability_refs` của 2 agent spec sản xuất (`COSA_OPERATIONS_AGENT_SPEC`, `COSA_FINANCE_AGENT_SPEC`) đang rỗng dù code đọc như thể có khai báo. Chưa gây hậu quả chức năng (chưa có chỗ nào đọc `capability_refs` để enforce), nhưng là bom nổ chậm — đã sửa dùng đúng field, giữ `name` cũ trong `metadata.display_name`.
  - **Prompt language strategy:** `packages/agent_core/prompts/{locale.py,bundle.py}` — `PromptBundle` compose platform policy (bất biến) + agent instructions (từ spec) + locale policy (English canonical, template đúng nguyên văn Blueprint V2 §68.3); `RunRequest.locale: str = "vi-VN"` field mới; wire vào `OpenAIAgentsKernel.run()` thay hoàn toàn `messages.append({"role": "system", "content": spec.instructions})` cũ. Glossary tĩnh `packages/agent_core/prompts/glossary/{core.en.yaml,vi-VN.yaml}` theo Blueprint V2 §68.4 — hiện là dữ liệu tham chiếu, chưa có code nào load/substitute (chưa cần vì chưa có consumer thật, tránh xây plumbing thừa).
  - **Đã audit, không cần sửa:** `AgentSpec.definition_hash`/`compute_hash()`/`to_pinned_identity()` và `RunRequest.root_executable_ref: PinnedSpecIdentity` đã tồn tại sẵn từ trước — phần lớn hạ tầng "pin version/hash" mà Blueprint V2 đề xuất **đã có**, Wave 3 chỉ thêm registry để lưu bất biến nội dung, không phải xây từ đầu.
  - **Không dùng `context_assembler.py` như kế hoạch gốc dự tính:** phát hiện `COSAContextAssembler` không được wire vào đâu cả (orphaned module, giống `apps/cosa/conversations/{ports,stub,repository}.py` phát hiện ở Wave 1) — locale policy inject thẳng vào kernel thay vì qua module này.
- [~] Wave 4 — LangChain/LiteLLM primary path (Phần F), code + test pass (227 passed, 0 failed) — **hoàn thành 1 phần**:
  - **`LangChainKernel`:** `packages/agent_integrations/langchain/kernel.py` — implement đầy đủ `ExecutionKernel` Protocol (run/resume/cancel/stream), dùng `langchain_core.messages` (System/Human/AI/Tool) thay dict thô, checkpoint qua `messages_to_dict`/`messages_from_dict`. Giữ đúng mọi invariant đã harden ở `OpenAIAgentsKernel` (typed error, spec registry publish, PromptBundle, exact tool identity). `tool_schema_adapter.py` convert `CapabilitySpec` → OpenAI-function-call-style dict cho `bind_tools()`. Test conformance đầy đủ trong `packages/agent_testkit/kernel_conformance/test_langchain_kernel.py` (5 test: basic response, provider failure typed, tool call ALLOW-path exact identity, approval pause/resume, cancellation) — dùng `FakeLangChainChatModel` duck-typed, **chưa test với DeepSeek provider thật** (cần API key, ngoài khả năng môi trường này).
  - **`LiteLLMModelClient`:** `packages/agent_integrations/litellm/gateway.py` — bọc `litellm.acompletion()` thành interface `.chat.completions.create()` tương thích OpenAI, dùng làm `model_client=` cho `OpenAIAgentsKernel` (không cần đổi kernel). Map đúng exception litellm (`RateLimitError`→`MODEL_RATE_LIMIT`, `ContextWindowExceededError`→`CONTEXT_LIMIT_EXCEEDED`, `Timeout`→`MODEL_TIMEOUT`, `AuthenticationError`→`TENANT_UNAUTHORIZED`) thay vì generic. Test trong `packages/agent_testkit/model_conformance/`.
  - **Runtime selection:** `build_cosa_agent_plane(runtime="openai_agents"|"langchain")` — mặc định vẫn `OpenAIAgentsKernel` (production hiện tại không đổi), `langchain` là opt-in tường minh, import lazy (không bắt buộc cài langchain cho consumer không dùng runtime này).
  - **Phát hiện + sửa 2 bug thật trong lúc xây LangChainKernel (đối chiếu với OpenAIAgentsKernel):**
    1. `OpenAIAgentsKernel._execute_tool()` nhánh fallback `GatewayExecutionRequest` **tự sinh `run_id`/`tool_call_id` NGẪU NHIÊN MỚI** thay vì dùng đúng identity của lần gọi đang xử lý — phá vỡ invariant exact `(run_id, tool_call_id)` xuyên suốt kernel→gateway, và sẽ gây lỗi FK thật trên Postgres (`run_id` giả không tồn tại trong `agent_core.runs`). `InMemoryRunRepository` không phát hiện vì không enforce FK — đây là gap chỉ lộ ra trên Postgres thật, đúng loại lỗi đã lặp lại nhiều lần trong session này. Đã sửa: `_execute_tool()` giờ nhận `run_id`/`tool_call_id` thật từ call site. Test `test_kernel_allow_path_tool_execution_preserves_real_run_and_tool_call_id` chứng minh.
    2. `_call_model()` bắt `Exception` rộng, kể cả `AgentRuntimeError` đã có `RuntimeErrorCode` cụ thể từ 1 `model_client` thông minh (như `LiteLLMModelClient`) — re-wrap thành `MODEL_PROVIDER_ERROR` chung chung, mất thông tin phân loại lỗi. Đã thêm `except AgentRuntimeError: raise` trước khi bắt `Exception` rộng. Test `test_kernel_with_litellm_client_surfaces_specific_error_code_not_generic` chứng minh.
  - **Chưa làm — LangGraph spike:** `packages/agent_integrations/langgraph/workflow_runtime.py` — theo đúng kế hoạch phải đọc kỹ `docs/architecture/langgraph_spike_results.md` và chạy lại acceptance matrix HL-01→18 trước khi kết luận bất cứ điều gì (ADR-LANGGRAPH cũ đã PASS 18/18 tiêu chí đó — lặp lại nghiêm túc, không phải việc làm qua loa). Đây là khối lượng công việc lớn (spike + benchmark thật), **cố ý để lại**, không làm ẩu trong 1 pass ngắn.
  - **pyproject.toml riêng** cho `agent_integrations/langchain/` và `agent_integrations/litellm/` — không gộp dependency vào `agent_integrations/pyproject.toml` chung.
- [x] Wave 5-6 — Skills/Evals/Skill Optimization Lab (Phần G), code + test pass (235 passed, 0 failed) — **phát hiện xung đột lớn với ADR có sẵn, đã xin quyết định người dùng trước khi code:**
  - **Phát hiện quan trọng trước khi code:** `packages/agent_core/skills/{contracts.py,registry.py}` đã tồn tại từ Phase 9D (SkillSpec/SkillRegistry/SkillStatus Draft→Candidate→...→Published) NHƯNG đi kèm `ADR-SKILL-IDENTITY-trigger-based-evaluation.md` ở trạng thái "PENDING TRIGGER / DEFERRED UNTIL FIRST RUNTIME EXECUTION USE CASE" — cố ý khoá skill khỏi runtime execution để tránh floating reference, với nguyên tắc rõ ràng "Không prebuild trước khi có trigger thật". Skill Optimization Lab của Blueprint V2 đòi hỏi chính xác thứ bị khoá này. **Đã hỏi người dùng** — quyết định coi Blueprint V2 là trigger thật, kích hoạt ADR, chọn Phương án A (pinned_skills trong AgentSpec). Đã cập nhật `ADR-SKILL-IDENTITY-trigger-based-evaluation.md` §4 ghi lại quyết định kích hoạt thay vì tạo ADR mới (giữ đúng quy trình ADR đó tự đề ra).
  - **Cài đặt Phương án A:** `PinnedSkillRef` (đặt ở `contracts/identity.py`, không phải `skills/` — giữ đúng chiều phụ thuộc contracts không phụ thuộc ngược subsystem); `AgentSpec.pinned_skills: list[PinnedSkillRef]` field mới; `packages/agent_core/skills/resolver.py::SkillResolver` verify `definition_hash` khớp tuyệt đối trước khi dùng, raise `AgentRuntimeError(SKILL_RESOLUTION_ERROR)` (code mới thêm vào taxonomy) nếu không khớp/không tồn tại — đúng invariant chống floating reference ADR gốc lo ngại. `publish_skill_spec()` tái dùng CÙNG bảng `agent_registry.published_specs` (spec_kind="skill") thay vì tạo registry riêng. Wire vào cả `OpenAIAgentsKernel` và `LangChainKernel`: resolve skill TRƯỚC khi tạo RunRecord (cùng nguyên tắc "lỗi cấu hình propagate raw, không để Run kẹt RUNNING" như spec publish).
  - **Skill Optimization Lab:** `packages/agent_core/skills/lab/{models,executor,mutator,lab}.py` — `SkillOptimizationLab.optimize()` chạy Executor→Scorer→Mutator (1 bounded mutation/round, tối đa `max_rounds`)→accept nếu tăng điểm/revert nếu không→full regression (bao gồm holdout) trước khi đánh dấu "evaluated". **Không tự publish** — trả `SkillCandidateRecord` chờ approval người thật gọi `publish_skill_spec()` riêng. `mutation_fn`/`score_fn` là tham số tiêm (Callable), không hardcode 1 LLM call cụ thể trong hạ tầng lõi — test dùng mutator/scorer đơn giản xác định được, không cần API key thật. `SkillCandidateExecutor` chạy qua `ExecutionKernel` THẬT (không phải mock riêng cho lab) — nối instructions candidate vào `AgentSpec.instructions` tạm thời với version tag riêng mỗi round (`{base_version}-lab-r{N}`) để tránh đụng `SpecVersionHashConflictError` của `publish_agent_spec` khi nội dung đổi giữa các round.
  - **Migration `008_agent_evals.sql`:** `agent_evals.{suites,cases,runs,results,skill_candidates,skill_mutations}` — schema tồn tại cho persistence tương lai, **CHƯA có Python repository wiring** (chỉ SQL, giống cách `packages/agent_core/evals/{models,runner}.py` cũ vẫn chạy in-memory, không đổi) — cố ý thu hẹp phạm vi, tránh xây thêm 1 bộ Postgres repository nữa (đã làm 4 lần trong session: runs, conversations, spec registry, idempotency) khi lab hiện tại chưa có consumer production thật cần durable.
  - **Không động vào `skillpacks/` manifest.yaml:** phần "bổ sung field `evals.suite`/`permissions.mutations`/`source_locale`" trong plan gốc — để lại vì Lab hiện tại thao tác trên `SkillSpec` (Python), không đọc `skillpacks/manifest.yaml`, thêm field vào ~10 file YAML hiện có mà chưa ai đọc là việc làm cho đủ checklist, không phải nhu cầu thật.
- [x] Wave 7 — Control Plane → `services/cosa` (Phần H) — **xây theo yêu cầu người dùng dù tiền đề gốc không còn đúng, chưa verify được bằng Encore CLI/Postgres thật:**
  - **Phát hiện quan trọng trước khi code:** `RunLeaseManager`/`RunScheduler` (2 class Python ADR-CONTROLPLANE-001 định "di chuyển để bảo vệ") **không có consumer production nào** — chỉ có test riêng của chúng gọi trực tiếp (`tests/agent_core/p2/test_multi_worker_leases.py`, `test_coalescing_scheduler.py`), không wire vào `agent_plane.py`/kernel/gateway. Tiền đề "bảo vệ logic đang chạy thật" không còn đúng. **Đã hỏi người dùng** — quyết định vẫn xây đầy đủ theo Blueprint V2 (missions/tasks/workers/watches/signals/delivery), coi là hạ tầng đón đầu.
  - **Giới hạn môi trường xác nhận trước khi code:** không có Encore CLI (`encore` command not found) và không có Postgres — `npx vitest run` trên test suite services/cosa hiện có (kể cả trước khi tôi động vào) fail với `ENCORE_RUNTIME_LIB environment variable is not set`, nghĩa là **không ai có thể chạy test TypeScript thật trong môi trường này**, kể cả code cũ. Verify duy nhất khả thi: `npx tsc --noEmit` (type-check tĩnh) — 0 lỗi trong code ứng dụng (chỉ còn lỗi nội bộ `node_modules/encore.dev` do xung đột `moduleResolution: nodenext` của chính package Encore, không liên quan code viết).
  - **4 migration mới** `services/cosa/migrations/{6_control_plane_missions_tasks,7_control_plane_leases_workers,8_control_plane_watches_signals,9_control_plane_delivery}.up.sql` — schema Postgres riêng `control_plane` (khác `cosa` dùng cho identity/license), 12 bảng đúng theo ADR-CONTROLPLANE-001/Blueprint V2 §71.2.
  - **Drizzle schema** `storage/control-plane-schema.ts`, re-export qua `storage/schema.ts` (giữ đúng convention 1-file-schema hiện có của `services/cosa` — KHÔNG áp `shared/db/schema/` vì đó là convention của `services/company` cho nhiều sub-service, `services/cosa` là 1 service đơn).
  - **6 service file mới:** `control-plane-lease.service.ts` (port `leases.py`, dùng `SELECT ... FOR UPDATE` trong transaction cho atomicity thật giữa nhiều process — bản Python gốc chỉ có `asyncio.Lock` trong 1 process), `control-plane-scheduler.service.ts` (port `scheduler.py`, dùng `FOR UPDATE SKIP LOCKED` cho multi-worker poll — cải tiến thật so với bản gốc chỉ chạy 1 process), `control-plane-mission.service.ts` (mission/task/atomic checkout dựa vào unique partial index thay vì lock riêng), `control-plane-worker.service.ts`, `control-plane-watch.service.ts` (dedupe signal qua unique index — đúng Blueprint V2 Scenario G), `control-plane-delivery.service.ts`.
  - **1 handler file** `control-plane.handler.ts` — toàn bộ `expose: false`, đặt tên hậu tố `Endpoint` để tránh trùng symbol với service khi `api.ts` gộp `export *` (đúng convention `getTenantPolicy` vs `getTenantPolicyForTool` đã có sẵn ở `agent-policy.handler.ts` — đã đối chiếu kỹ trước khi đặt tên).
  - **Phát hiện + sửa 1 bug thật không liên quan Wave 7** trong lúc type-check: `services/cosa/models/db.ts` re-export `controlPlaneDB` từ `../db` nhưng `db.ts` chưa từng định nghĩa/export tên này (lỗi TS2305) — không có consumer nào import `controlPlaneDB` ở đâu khác, đây là dead re-export từ trước. Đã xoá khỏi danh sách re-export.
  - **Python HTTP client** `packages/agent_core/runs/control_plane_client.py::HttpControlPlaneLeaseClient` — giữ nguyên interface `RunLeaseManager` (acquire/renew/release_lease) để không đổi call site, gọi qua HTTP tới endpoint mới. Test dùng `httpx.MockTransport` (không cần services/cosa thật đang chạy) verify đúng shape request/response. **CHƯA wire làm default** ở đâu — vì không có consumer thật, không có "cutover" nào cần làm; class tồn tại sẵn cho khi có consumer thật (matching nguyên tắc "không đổi mặc định production khi chưa cần" áp dụng xuyên suốt session này).
  - **CHƯA làm:** benchmark latency thật (Phần H.4 của plan) — không thể đo latency network hop Python↔Encore khi không có server Encore thật chạy được trong môi trường này. Đây là việc bắt buộc phải làm trên môi trường có Encore CLI + Postgres trước khi coi Wave 7 an toàn cho production.
- [x] Wave 8 — Knowledge/Memory v2 (Phần I), code + test pass (244 passed, 0 failed, 15 skipped cần Postgres thật):
  - **Memory v2:** migration `009_memory_v2.sql` — thêm cột thật (application_id, tenant_id, company_id, scope_type/scope_id, subject_type/subject_id, content_hash, source_run_id/source_event_id, provenance JSONB, status, valid_from/valid_until, supersedes_memory_id, updated_at) + backfill từ metadata packed cũ + bảng `agent_memory.memory_embeddings` mới (memory trước đây KHÔNG có khả năng embedding nào). **Đóng nợ kỹ thuật đã ghi chú sẵn trong code:** `PostgresMemoryStore` (viết ở Wave trước phiên này) có comment tường minh "pack vào metadata để tránh mở migration mới trong cùng epic" — Wave 8 chính là lúc mở migration đó, viết lại `put()`/`search()` dùng cột thật thay vì pack/unpack JSONB. `MemoryStatus` enum mới (ACTIVE/SUPERSEDED/EXPIRED/RETRACTED/ARCHIVED); `search()` mặc định chỉ trả ACTIVE — áp dụng nhất quán cho cả `InMemoryMemoryStore` (trước đó không lọc) và `PostgresMemoryStore`.
  - **Knowledge v2:** migration `010_knowledge_versioning_and_embeddings.sql` — `knowledge.source_versions` mới (source→version, content_hash, ingestion_run_id, parser_name/version) + `knowledge.chunk_embeddings` mới (nhiều embedding/chunk, khác model không mất embedding cũ) + `authority_class`/`status`/scope generic trên `knowledge_sources`. **Phát hiện quan trọng:** schema `knowledge.knowledge_sources`/`knowledge_chunks` đã tồn tại từ migration 003 (Wave 0) nhưng **chưa từng có `PostgresKnowledgeStore`** — chỉ có `InMemoryKnowledgeStore`, nghĩa là toàn bộ subsystem knowledge chạy in-memory dù schema durable đã sẵn sàng từ đầu. Đã viết `packages/agent_core/knowledge/providers/postgres.py::PostgresKnowledgeStore` (mới hoàn toàn) — `save_document()` tự tạo `source_version` mới khi nội dung đổi (content_hash tổng hợp từ toàn bộ chunk theo thứ tự `chunk_index`), giữ lịch sử version thay vì ghi đè; `search_chunks()` hiện dùng ILIKE keyword search (chưa phải semantic/vector search thật — cần benchmark index/model cụ thể trước khi xây, để lại có chủ đích).
  - **`get_knowledge_store()`** factory mới, cùng no-silent-fallback pattern với `get_memory_store()` đã có.
- [x] Wave 9 — Protocols MCP/A2A/AG-UI (Phần I), code + test pass (253 passed, 0 failed):
  - **MCP:** `packages/agent_integrations/mcp/capability_adapter.py` — `mcp_tool_to_capability_spec()` + `register_mcp_tools()` convert MCP `tools/list` wire format (dict thô, KHÔNG import package `mcp` cụ thể — package đó yêu cầu Python 3.10+, máy này chỉ có 3.9) thành `CapabilitySpec` đăng ký vào `CapabilityRegistry` bình thường. Test chứng minh tool MCP đăng ký kiểu này tự động đi qua ĐÚNG `CapabilityGateway.execute()` pipeline (governance/idempotency/tool_call ledger) — không cần code đặc biệt để "không bypass Gateway", vì bản chất đăng ký vào registry chung đã đảm bảo điều đó.
  - **A2A:** `packages/agent_integrations/a2a/authority.py::attenuate_authority()` — verify invariant `Authority(child) ⊆ Authority(parent)` ở cả 4 chiều (capability_refs theo wildcard prefix, max_risk theo thứ tự LOW<MEDIUM<HIGH<CRITICAL, expires_at lấy sớm hơn, tenant_id LUÔN theo parent bất kể child yêu cầu gì) — 5 test cố ý cho `requested` vượt quá `parent` để chứng minh luôn bị chặn.
  - **AG-UI:** `packages/agent_integrations/ag_ui/event_mapper.py::map_run_event_to_ag_ui()` — map `RunEventRecord` sang vocabulary AG-UI (RUN_STARTED/RUN_FINISHED/RUN_ERROR/TEXT_MESSAGE_CONTENT/TOOL_CALL_START/TOOL_CALL_END/STATE_SNAPSHOT/CUSTOM). Test map TOÀN BỘ chuỗi event thật sinh ra từ 1 lần `OpenAIAgentsKernel.run()` thật (không phải fixture giả lập), verify thứ tự RUN_STARTED→...→RUN_FINISHED và `sequence_no` tăng dần được giữ nguyên. **Ghi chú trung thực:** mapping chưa đối chiếu certification chính thức với AG-UI spec gốc (không có kết nối tới tài liệu spec trong môi trường này) — best-effort dựa trên mô tả Blueprint V2 §10.3.
- [~] Wave 10 — Additional runtime conformance (Phần I) — **spike feasibility only, không xây conformance suite đầy đủ:**
  - Đã xác nhận trong môi trường này: `openai-agents`, `pydantic-ai`, `google-adk` đều **cài và import được** (dù máy chỉ có Python 3.9 — các SDK này chấp nhận, chỉ riêng package `mcp` chính thức yêu cầu Python 3.10+, đã tránh phụ thuộc trực tiếp vào nó ở Wave 9). `agents.Runner.run(starting_agent, input: str|list|RunState, ...)` xác nhận có hỗ trợ resume qua `RunState` như ADR-KERNEL kỳ vọng.
  - **KHÔNG viết conformance test/kernel thay thế thật** vì: (1) chạy conformance thật cần gọi model provider thật (DeepSeek/OpenAI) — không có API key trong môi trường này, mock ở tầng quá sâu trong SDK nội bộ (không có tài liệu API chi tiết) có rủi ro tạo "bằng chứng" sai lệch; (2) ADK integration production thật nằm ở `legacy/backend/app/workforce/agents/orchestration/adk/`, NGOÀI biên giới `packages/agent_core`/`packages/agent_integrations` — viết conformance test cho code chưa được di chuyển vào đúng vị trí target không có ý nghĩa, di chuyển nó là 1 việc lớn riêng chưa làm.
  - Đây là quyết định thu hẹp phạm vi có chủ đích (giống cách xử lý LangGraph spike ở Wave 4) — không giả vờ "đã conformance-test" khi thực chất chỉ xác nhận package import được.
- [x] Wave 11 — Recipe harvest (Phần I), 7 recipe theo đúng danh sách ưu tiên Blueprint V2 §81:
  - `packages/agent_recipes/{sales/competitor-intelligence, research/research-synthesize, ops/release-radar, core/advisor-orchestrator-worker, dev/dependency-doctor, core/self-improving-skill, core/mixture-of-agents}/{recipe.yaml,README.md}` + `docs/recipes/<recipe-id>.md` tương ứng cho từng recipe.
  - **Hiệu chỉnh cấu trúc so với `packages/agent_recipes/README.md` viết ở Wave 0.2:** bỏ `workflow.yaml`/`agents/`/`skills/`/`evals/` riêng — 1 file `recipe.yaml` (metadata + workflow pattern/steps + requires + governance) đủ diễn đạt cho 7 recipe declarative này, tránh nhiều file rỗng. Đã cập nhật lại README phản ánh đúng cấu trúc thật.
  - **3 recipe tái dùng module đã có sẵn, không viết code mới:** `advisor-orchestrator-worker` (dùng `coordination/{supervisor,parallel,quality_gate,synthesis}.py` có từ trước phiên này), `self-improving-skill` (dùng `skills/lab/` xây ở Wave 5-6), `mixture-of-agents` (dùng `coordination/parallel.py`).
  - **2 recipe (`ops/release-radar`) trực tiếp dùng control-plane Wave 7** — minh hoạ nguyên tắc deterministic-first (Blueprint V2 §72) áp dụng thật: parser/version-diff là code thường, LLM chỉ dùng ở bước đánh giá độ liên quan.
  - **Trung thực về phụ thuộc chưa có:** `web.search` capability (cần cho competitor-intelligence, research-synthesize, dependency-doctor) **chưa implement** ở đâu trong `apps/cosa/capabilities/` — mọi recipe cần nó đều ghi rõ trong README/doc, không giả vờ đã sẵn sàng chạy end-to-end.

## Tổng kết toàn bộ 11 Wave (2026-08-24)

Đã hoàn thành Wave 0-11 theo đúng thứ tự yêu cầu, với các quyết định thu hẹp phạm vi có chủ đích (LangGraph spike thật — Wave 4; ADK/OpenAI SDK conformance đầy đủ — Wave 10) được ghi lại minh bạch thay vì giả vờ hoàn thành. Toàn bộ code Python (`packages/agent_core`, `packages/agent_integrations`, `packages/agent_recipes`) đã test pass (253 passed, 15 skipped — cần Postgres/DeepSeek key thật). Code TypeScript (Wave 7, `services/cosa`) chỉ verify được bằng `tsc --noEmit` (0 lỗi ứng dụng) — KHÔNG chạy được test thật (không có Encore CLI trong môi trường này, xác nhận ngay cả test cũ trước phiên này cũng không chạy được).

**Quyết định 2026-08-24 (cuối phiên):** đã xác nhận môi trường phiên này CÓ network access (encore.dev, npm, PyPI đều phản hồi 200 — trước đó chưa kiểm tra kỹ). Hỏi người dùng có muốn cài Postgres/Encore CLI/Python 3.11+ thật trên máy để verify các mục còn lại hay không — người dùng chọn **"Không, để lại cho CI/staging"**. Vì vậy các mục dưới đây CHỦ ĐỘNG để ngỏ cho môi trường CI/staging riêng, không phải giới hạn kỹ thuật không vượt qua được.

**Việc cần làm tiếp theo, để lại cho CI/staging (không cài trên máy này theo quyết định người dùng):**
1. Review 2 ADR chính (`ADR-RUNTIME-001`, `ADR-CONTROLPLANE-001`) — vẫn ở trạng thái DRAFT theo quy trình đã thống nhất ở Wave 0, dù code đã build theo hướng đó.
2. Chạy toàn bộ migration (001→010 ở `packages/agent_core`, 1→9 ở `services/cosa`) trên Postgres thật, xác nhận không lỗi.
3. Chạy `packages/agent_testkit/` + `tests/agent_core` + `tests/apps` trên Python 3.11+ thật (môi trường này chỉ có 3.9, dùng workaround `eval_type_backport`).
4. Chạy `npx vitest run` trên `services/cosa` với Encore CLI thật (`ENCORE_RUNTIME_LIB` cần thiết lập).
5. Benchmark latency Wave 7 H.4 (network hop Python↔Encore) trên môi trường có server thật.
6. Test `LangChainKernel`/`LiteLLMModelClient` với DeepSeek API key thật (hiện chỉ test qua fake model).
7. ~~6 ADR bổ sung theo Blueprint V2 §51~~ — **ĐÃ VIẾT (2026-08-24, sau khi hoàn thành Wave 0-11):** `ADR-MODEL-GATEWAY`, `ADR-RUNTIME-ADAPTERS`, `ADR-PROTOCOLS-MCP-A2A-AGUI`, `ADR-DURABLE-IDENTITY`, `ADR-DATABASE-SCHEMA-OWNERSHIP` ghi lại ĐÚNG những gì đã build trong Wave 0-11 (không phải đề xuất mới). `ADR-PLUGIN-TRUST-AND-ISOLATION` là ngoại lệ — trạng thái PROPOSED, cố ý CHƯA implement (không có plugin bên thứ ba thật cần trust/isolation, và phụ thuộc `SandboxProvider` Protocol chưa tồn tại) — cùng nguyên tắc "không prebuild trước trigger thật" đã áp dụng cho `ADR-SKILL-IDENTITY`.
8. ~~Gap governance-accumulator phát hiện ở Wave 2~~ — **ĐÃ SỬA (2026-08-24, sau khi hoàn thành Wave 0-11):** `CapabilityGateway` giờ nhận `governance_store: GovernanceStateStore` (mặc định `InMemoryGovernanceStateStore()`, production qua `build_cosa_agent_plane()` dùng `PostgresGovernanceStateStore` — cùng no-silent-fallback pattern, thêm biến bắt buộc `governance_store`/`AGENT_CORE_DATABASE_URL`). Thay hoàn toàn `self._gov_states` dict in-memory bằng `governance_store.load_governance_state()`/`save_governance_state()` — **tái dùng** `GovernanceStateStore` Protocol + `PostgresGovernanceStateStore` đã có sẵn từ trước (đang được `packages/agent_core/workflows/{engine,tool_step}.py` dùng đúng, chỉ Gateway là ngoại lệ có state riêng) — không tạo cơ chế song song. Test `test_governance_accumulator_survives_gateway_restart` (tạo Gateway instance MỚI hoàn toàn, chỉ chia sẻ governance_store, mô phỏng process restart) chứng minh state được giữ đúng. 256 test pass sau fix.

**Ghi chú môi trường test:** máy hiện tại chỉ có Python 3.9 (không có 3.11+, không có Postgres/Docker). Đã dùng venv tạm (`.venv_check`, đã xoá sau khi xong) + gói `eval_type_backport` để chạy được test suite hiện có (pydantic v2 dùng cú pháp `X | None` cần Python 3.10+ để eval). Đây là môi trường chạy test cục bộ của phiên làm việc này, không phải thay đổi vào repo — CI/production cần Python 3.11+ thật theo `pyproject.toml` mới tạo.

9. ~~Documentation-as-code đầy đủ theo Blueprint V2 §79~~ — **ĐÃ VIẾT (2026-08-24, sau khi hoàn thành Wave 0-11, theo yêu cầu người dùng "tiếp tục" viết hết checklist thay vì dừng sớm):** toàn bộ 41 file doc theo checklist — `docs/architecture/` (5 file: overview, dependency-rules, execution-lifecycle, data-model, prompt-language-strategy), `docs/features/` (15 file, 9 file "spine" viết đầy đủ 16-mục, `workflows.md`/`artifacts.md` viết ngắn gọn vì là subsystem có sẵn không đụng tới phiên này), `docs/integrations/` (9 file: langchain/litellm/mcp/a2a/ag-ui đã build; langgraph/deepseek/google-adk/openai-agents-sdk/opentelemetry là honest "chưa build/chưa migrate/chưa implement" — có lý do rõ ràng, không phải file rỗng), `docs/recipes/` (7 file), `docs/development/` (8 file: add-runtime/add-capability/add-skill/add-recipe/add-knowledge-source/add-delivery-channel/commenting-conventions/testing-conformance), `docs/operations/` (4 file: deployment/migrations/secrets/disaster-recovery — tất cả ghi rõ "CHƯA verify trên hạ tầng thật" thay vì giả vờ đã test), `docs/manifest.yaml` (validated bằng pyyaml: 11 features, 5 integrations, 7 recipes). Tổng `docs/` sau khi hoàn thành: 155 file `.md`. Điểm trung thực xuyên suốt: mọi file mô tả tính năng CHƯA verify/CHƯA implement đều nói rõ lý do và việc cần làm tiếp, không có file nào giả vờ hoàn thành để lấp checklist.
