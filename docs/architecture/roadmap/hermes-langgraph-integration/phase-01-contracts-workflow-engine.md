# Phase 1 — VNext Contracts + Migrate Workflow Engine

> Nguồn gốc: `COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md` §"Phase 1" (Step 3). Bổ sung Hermes/LangGraph theo `COSA_HERMES_LANGGRAPH_INTEGRATION_PLAN_2026-08-23.md` §3, §4.

## Mục tiêu

Có bộ contract nền tảng (`packages/agent_core/contracts/`) và `packages/agent_core/workflows/` chạy được với logic thật đã migrate từ `agentos/workflows/*`, không phải viết lại từ đầu. Đây là **baseline bắt buộc** phải xong trước khi bất kỳ LangGraph spike nào chạy (Phase 3).

## Điều kiện tiên quyết

Phase 0 DoD đã đạt — bảng salvage đã chốt, đặc biệt dòng `agentos/workflows/*` = PROMOTE CODE mạnh, và `docs/architecture/CONTEXT_ASSEMBLER_AUDIT.md` đã tồn tại.

## Việc cụ thể (gốc)

1. Tạo `packages/agent_core/contracts/` với các module con:
   - `run.py`: `RunRequest`, `RunResult` — field tối thiểu: `principal`, tenant/company/workspace scope, conversation/session ref, root executable ref, input, execution mode, model policy, correlation id, idempotency key, metadata (`RunRequest`); `run_id`, status, final_output, artifacts, usage, events cursor/ref, interruptions/waits, errors (`RunResult`).
   - `spec.py`: `AgentSpec` với `definition_hash` bắt buộc — field: `id`, `version`, `instructions`, `model_policy`, `autonomy_level`, `capability_refs`, `memory_policy`, `knowledge_policy`, `coordination_policy`, `limits`, `metadata`.
   - `identity.py`: `PinnedSpecIdentity` (import lại từ `governance/contracts.py`, không định nghĩa trùng), `InvocationIdentity` mới: `run_id + tool_call_id + capability_id + payload_hash`, mở rộng optional connector/connection identity, idempotency key, checkpoint_ref.
   - `target.py`: `ExecutionTargetSnapshot`: `capability_id`, `connector_id`, connection/account id, endpoint/resource identity, schema_hash/version, credential/grant version, capability risk at request time, handler/catalog version.
   - `wait.py`: `WaitDescriptor`: kind, reason, owner/responder, resume_trigger, checkpoint_ref, related approval/event/dependency ref, created_at, optional expiry.
   - `kernel.py`: `ExecutionKernel` Protocol — chỉ method signature (`run`, `resume`, `cancel`, `stream`), chưa implement.
   - `capability.py`: `CapabilitySpec`: `id`, description, input schema, output schema, risk, approval policy, idempotency semantics, audit policy, eligibility, connector requirements.
2. Migrate `agentos/workflows/schema.py`, `loader.py`, `engine.py`, `definition_registry.py`, `tool_step.py` sang `packages/agent_core/workflows/` — copy logic, không viết lại DAG/retry/compensation/version-pinning. Thêm field bắt buộc `failure/compensation policy`, `input/output schemas` nếu chưa có trong schema gốc.
3. Đổi vocabulary khi promote code governance/policy: `PermissionLevel`→`AutonomyLevel`, `ToolRiskLevel`→`CapabilityRisk`, `ToolPermission`→gộp vào `PrincipalAuthorization` nếu semantics tương đương. Retire `PermissionClass`. Rename chỉ áp dụng trong `packages/agent_core/`, không đổi ngược vào `agentos/`.
4. Viết `docs/architecture/agentos_salvage_inventory.md` mục "Phase 1 completed": đánh dấu module đã migrate xong, kèm commit hash.

## Test bắt buộc (gốc)

- Schema validation cho từng contract (Pydantic validate cả input hợp lệ và không hợp lệ).
- `definition_hash` determinism test: cùng input → cùng hash, input khác 1 field → hash khác.
- Toàn bộ test suite cũ của `agentos/workflows/*` chạy pass trên code đã migrate ở vị trí mới.

## Bổ sung Hermes/LangGraph

**Nguyên tắc:** đóng băng **contract tối thiểu**, không viết implementation — tránh abstraction-first over-engineering trước khi Phase 7 chứng minh use case thật.

1. **`ContextFragment`, `ContextSnapshot`** (Protocol/BaseModel, framework-neutral, KHÔNG import business domain) — chỉ tạo nếu Phase 7 thực sự cần làm interface boundary. Không bắt buộc dựng toàn bộ `packages/agent_core/context/` ở Phase 1.
   ```text
   ContextFragment: source_kind, source_ref, lifetime (STABLE|RUN|CURRENT|EPHEMERAL), content,
                     token_estimate, sensitivity, provenance, freshness, cache_key?
   ContextSnapshot:  run_id, principal_id, tenant_id, assembled_at, fragments: list[ContextFragment],
                      budget_tokens_remaining, memory_access_enabled
   ```
2. **`CapabilityReadiness`** (nhỏ, thêm trực tiếp vào `contracts/capability.py` hiện có, không cần file riêng):
   ```text
   CapabilityReadiness: capability_id, ready, reason_code (READY|MISSING_CREDENTIAL|CONNECTOR_OFFLINE|
                         TENANT_DISABLED|BACKEND_UNAVAILABLE|SCHEMA_MISMATCH|DEPENDENCY_MISSING),
                         observed_at, ttl, connector_ref?, credential_ref?
   ```
   Đây không phải mục P2 tách biệt (như supplement gốc §18/§43 xếp vào "Phase F") — đúng vị trí là ngay trong `CapabilitySpec` vì Phase 4 (Capability Gateway) cần nó ở giữa pipeline thật (xem `phase-04-capability-gateway.md`).
3. **ADR-KERNEL** — viết và merge trước khi Phase 3 bắt đầu code:
   > Decision: OpenAI Agents SDK chính thức là kernel implementation canonical (đã chốt tại chính Phase 3 của Promotion Plan gốc — dòng "ExecutionKernel có 1 implementation thật dựa trên OpenAI Agents SDK"). Custom loop hiện tại (`packages/agent_core/kernel/openai_agents_kernel.py`, dùng package `openai` trần, không dùng `openai-agents`) là TẠM THỜI / non-conforming, không được nhận thêm trách nhiệm architecture mới trong lúc chờ thay thế. Exit criterion: thay thế bằng SDK thật trước khi Phase 3 DoD đóng. Fallback: chỉ mở lại quyết định nếu compatibility matrix (Phase 3, mục 6) chứng minh SDK có giới hạn chặn cứng — cần một ADR mới riêng, không tự động quay lại custom loop.

   Lưu ADR tại `docs/architecture/adr/ADR-KERNEL-openai-agents-sdk-ratification.md` (đặt tên theo convention ADR hiện có trong repo, `docs/architecture/adr/`).

## Definition of Done — Phase 1

**Gốc:**
- `packages/agent_core/contracts/` tồn tại đủ 7 module trên, type hint đầy đủ, docstring theo CLAUDE.md (tiếng Việt cho phần giải thích ý nghĩa).
- `packages/agent_core/workflows/` chạy được toàn bộ test đã migrate từ `agentos/workflows/tests`, pass 100%.
- Không còn `packages/agent_core/*` import gì từ `agentos/*` (`grep -r "from agentos" packages/agent_core/` → rỗng).
- Vocabulary rename áp dụng nhất quán trong `packages/agent_core/governance/`, có test xác nhận enum mới hoạt động đúng với accumulator/policy logic hiện có.

**Bổ sung:**
- `ContextSnapshot`/`ContextFragment` construct được rỗng (unit test), không cần implementation.
- `CapabilityReadiness` contract có unit test construct hợp lệ.
- ADR-KERNEL đã viết, merge, và trỏ đúng dòng trong Promotion Plan gốc làm căn cứ ratify.

## Rủi ro/lưu ý

**Gốc:** Rename vocabulary có phạm vi rộng nếu làm ẩu — giới hạn chặt trong package mới, không codemod ngược. Migrate workflow engine dễ bị cám dỗ "tiện thể refactor luôn" — chống lại, chỉ đổi phần cần cho contract mới.

**Bổ sung:** Không tạo `packages/agent_core/context/` hay `packages/agent_core/skills/` đầy đủ ở phase này dù supplement gốc đề xuất — đó là lỗi abstraction-first đã bị reject trong Integration Plan §5. ADR-KERNEL phải ratify quyết định có sẵn, không mở lại như câu hỏi 50/50.
