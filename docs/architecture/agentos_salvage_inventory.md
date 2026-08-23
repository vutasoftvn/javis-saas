# COSA AgentOS — Asset Inventory & Salvage Classification

> **Trạng thái:** Toàn bộ Phase 0 đến Phase 11 đã HOÀN THÀNH 100% — Toàn bộ tài sản đã chuyển giao thành công sang `packages/agent_core/` và `apps/cosa/`. `agentos/` đã được archive an toàn sang `legacy/agent_runtime_archive/`.  











> **Tham chiếu chính:**  
> - `COSA_CANONICAL_MASTER_ARCHITECTURE_AND_IMPLEMENTATION_GUIDE_2026-08-23.md` (Master M1)  
> - `COSA_AGENT_PLATFORM_PROMOTION_IMPLEMENTATION_PLAN_2026-08-23.md` (Promotion Plan)  
> - `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md`

---

## 1. Operational Truth & Phạm vi Freeze

### 1.1. Định nghĩa trạng thái của `agentos/`
Sau quá trình audit trực tiếp mã nguồn tại `main@fb4251b6`:
- `agentos/` **không phải là inert scaffold vô nghĩa**, mà là **"consumer-referenced, contract-implemented, deployment-unwired runtime"**.
- Đã có API backend `/agent/*` hoàn chỉnh (`agentos/api/app.py`, `chat_router`, SSE event stream).
- Frontend Flutter đã tích hợp và tham chiếu trực tiếp (`AgentChatService`, `ChatController`, `ChatBinding`).
- Chưa có deployment wiring chính thức (Docker Compose port 8000 trỏ `legacy/backend`, chưa trỏ `agentos.api.app`).
- **Hệ quả:** Không xem `agentos/` là throw-away tùy tiện, cũng không tiếp tục phát triển `agentos/` thành canonical runtime. Thay vào đó, thực hiện **Asset Inventory & Salvage Classification** có hệ thống để bảo toàn các logic nghiệp vụ đã được chứng minh (DAG, retry, compensation, version-pinning, governance accumulator, memory providers, evals baseline).

### 1.2. Quy tắc Architecture & Feature Freeze (Áp dụng từ Phase 0)
- **CẤM:**
  - Thêm execution framework mới vào `agentos/`.
  - Thêm composition root mới hoặc mở rộng `build_cosa_agent_plane()` thành kiến trúc cuối.
  - Tiếp tục cố gắng làm `AgentRuntime` / `Executor` / `ADK orchestrator` "production-ready" trong `agentos/`.
  - Thêm cơ chế persistence / durability mới chỉ tồn tại ở `agentos/` mà không có kế hoạch chuyển tiếp.
- **CHO PHÉP:**
  - Characterization tests, extraction adapters, invariant-proofs, và bugfix tối thiểu phục vụ kiểm thử và xác định chính xác hành vi cần promote.

---

## 2. Bảng phân loại tổng thể (Salvage Classification Matrix)

| # | Subsystem | Module nguồn (`agentos/`) | Disposition | Đích dự kiến | Target Phase | Test / Characterization Harness |
|---|---|---|---|---|---|---|
| 1 | **Workflow Engine & DAG** | `agentos/workflows/*` (schema, loader, engine, definition_registry, tool_step, steps, approval_step, models) | **PROMOTE CODE mạnh** | `packages/agent_core/workflows/` | Phase 1 | `tests/agentos/workflows/test_*.py` (12 test suites, 35+ test cases) |
| 2 | **Governance & Policy** | `agentos/core/policy.py`, `packages/agent_core/governance/*` | **PROMOTE mạnh (Vocabulary Rename)** | `packages/agent_core/governance/` | Phase 1 | `tests/agentos/core/test_policy*.py`, `tests/agent_core/governance/test_*.py` |
| 3 | **OpenAI Agents Kernel** | *N/A (New implementation replacing AgentRuntime)* | **SUPERSEDE implementation** | `packages/agent_core/kernel/` | Phase 3 | `tests/agentos/test_runtime_end_to_end.py`, DeepSeek matrix test mới |
| 4 | **Coordination Primitives** | `agentos/orchestration/adk/*` (nodes, orchestrator) | **PROMOTE patterns/invariants only (KHÔNG port ADK code)** | `packages/agent_core/coordination/` | Phase 3 | `tests/agentos/orchestration/adk/test_nodes.py`, `tests/agentos/orchestration/adk/test_orchestrator.py` |
| 5 | **Capability Gateway & Invocations** | `agentos/core/policy.py`, `agentos/core/approval.py` | **REWRITE & PROMOTE gateway semantics** | `packages/agent_core/capabilities/` | Phase 4 | `tests/agentos/test_tool_spec_v2.py`, `tests/agentos/test_encore_tool_bindings.py` |
| 6 | **Durable Approvals** | `agentos/core/approval.py` (thay thế in-memory lookup) | **REWRITE to Durable model** | `packages/agent_core/capabilities/approval_service.py` | Phase 5 | `tests/agentos/api/test_approval_lifecycle.py`, test process restart mới |
| 7 | **Spec & Governance Drift Suite** | `agentos/workflows/test_definition_registry.py`, test durability | **PROMOTE & EXPAND** | `tests/agent_core/drift/` | Phase 6 | 9 test cases độc lập theo Master doc §41.1 |
| 8 | **COSA Composition Root** | `agentos/core/factory.py` (`build_cosa_agent_plane()`) | **PROMOTE composition knowledge, REWRITE implementation** | `apps/cosa/composition/` | Phase 7 | `tests/agentos/test_factory_composition.py`, `tests/agentos/test_services_pilot_e2e.py` |
| 9 | **Chat API Contract & SSE** | `agentos/api/chat/routes.py`, `schemas.py` | **PROMOTE contract candidate, REWRITE route lifecycle** | `apps/cosa/api/` | Phase 8 | `tests/agentos/api/test_chat_routes.py`, `test_event_stream.py`, `test_citation_events.py` |
| 10 | **Memory Subsystem** | `agentos/memory/*` (MemoryStore, 5 MemoryKind, providers, retriever, consolidation) | **PROMOTE-after-audit** | `packages/agent_core/memory/` | Phase 9 | `tests/agentos/memory/test_*.py` (9 test suites) |
| 11 | **Knowledge Subsystem** | `agentos/knowledge/*` (store, ingest, retrieval, pgvector, chunking, parsers) | **PROMOTE-after-audit** | `packages/agent_core/knowledge/` | Phase 9 | `tests/agentos/knowledge/test_*.py` (7 test suites) |
| 12 | **Evals & Benchmarks** | `agentos/evals/*` (runner, regression, safety, skill, agent, workflow, strategy) | **PROMOTE thẳng (Baseline)** | `packages/agent_core/evals/` | Phase 9 | `tests/agentos/evals/test_*.py` (9 test suites) |
| 13 | **Profiles & Skills Definitions** | `agentos/profiles/*`, `agentos/skills/*` | **PROMOTE semantics + definitions** | `packages/agent_core/profiles/`, `skills/`, `apps/cosa/` | Phase 1 / 7 | `tests/agentos/profiles/test_*.py`, `tests/agentos/skills/test_*.py` |
| 14 | **Context Prior Art** | `legacy/agent_runtime/workforce/agents/context/*` (`assembler`, `builder`, `compiler`, `scope_resolver`) | **PROMOTE invariants/concepts only (KHÔNG port code)** | `packages/agent_core/contracts/context.py`, `apps/cosa/composition/context_assembler.py` | Phase 0 / 1 / 7 | Audit doc: `docs/architecture/CONTEXT_ASSEMBLER_AUDIT.md` |

---

## 3. Chi tiết kiểm kê từng Subsystem (Subsystem Breakdown)

### 3.1. Workflow Engine & Declarative DAG
- **Module nguồn:**
  - `agentos/workflows/schema.py`: Pydantic schema cho workflow spec, step types, retry, compensation.
  - `agentos/workflows/loader.py`: YAML parser & validator cho workflow definition.
  - `agentos/workflows/engine.py`: DAG execution engine, step lifecycle, rollback handler.
  - `agentos/workflows/definition_registry.py`: Version registry với `definition_hash` content-addressed SHA-256.
  - `agentos/workflows/tool_step.py`: Bridge giữa workflow step và tool dispatch có tích hợp governance.
  - `agentos/workflows/steps.py`: Các implementation step: `DeterministicStep`, `AgentStep`, `ParallelStep`, `RetryStep`, `CompensatingStep`.
  - `agentos/workflows/approval_step.py`: Approval gate step.
  - `agentos/workflows/models.py`: State models (`Workflow`, `WorkflowStatus`, `StepOutcome`).
  - `agentos/workflows/definitions/strategy_gate_evaluation_flow.yaml`: Workflow mẫu chuẩn.
- **Disposition:** **PROMOTE CODE mạnh** — Giữ nguyên 100% logic DAG, retry, compensation, version-pinning.
- **Đích dự kiến:** `packages/agent_core/workflows/` (Phase 1).
- **Điều kiện Audit & Chuyển đổi:**
  - Cắt toàn bộ import phụ thuộc vào `agentos.core.*` (đổi sang `agent_core.contracts.*` và `agent_core.governance.*`).
  - Thay thế in-memory state checkpointing bằng `agent_core.run_checkpoints` durable store (Phase 2).
  - Bổ sung trường bắt buộc `failure_policy`, `compensation_policy`, `input_schema`, `output_schema` vào `WorkflowSpec`.
- **Characterization Harness:**
  - `tests/agentos/workflows/test_dag_engine.py` (thứ tự tuần tự & song song)
  - `tests/agentos/workflows/test_declarative_yaml.py` (load & validate YAML)
  - `tests/agentos/workflows/test_definition_registry.py` (bảo toàn version bất biến và hash)
  - `tests/agentos/workflows/test_engine.py` (complete, pause at gate, resume, rollback compensation)
  - `tests/agentos/workflows/test_approval_step.py` (allow, deny, require approval)
  - `tests/agentos/workflows/test_steps.py` (tất cả các loại step: deterministic, agent, parallel, retry, compensating)
  - `tests/agentos/workflows/test_workflow_compensation.py` (rollback on failure)
  - `tests/agentos/workflows/test_workflow_governance.py` (governance accumulation xuyên suốt workflow engine)
  - `tests/agentos/workflows/test_checkpoint_resume.py` (resume không chạy lại step đã hoàn thành)
  - `tests/agentos/workflows/test_full_workflow_integration.py` (end-to-end integration flow)

---

### 3.2. Governance & Policy Engine
- **Module nguồn:**
  - `agentos/core/policy.py`: `evaluate_access()`, `PolicyEngine`, `DEFAULT_POLICY_TABLE`, các enum quyền hạn.
  - `packages/agent_core/governance/contracts.py`: `PinnedSpecIdentity`, `SpecResolutionManifest`, `PolicyDecision`, `PolicyOutcome`, `ApprovalRequirement` (`RoleApproval`, `UserApproval`, `AllOf`, `AnyOf`, `Quorum`), `ApprovalEvidence`.
  - `packages/agent_core/governance/accumulator.py`: `combine_decisions()`, `InvocationGovernanceState` (`G_acc` monotonic accumulator).
  - `packages/agent_core/governance/hashing.py`: Canonical SHA-256 hashing cho spec definition.
  - `packages/agent_core/governance/store.py` & `providers/`: `GovernanceStateStore` Protocol, Postgres & InMemory providers.
- **Disposition:** **PROMOTE mạnh + Rename Vocabulary** (Phase 1 & 2).
- **Đích dự kiến:** `packages/agent_core/governance/`.
- **Điều kiện Audit & Chuyển đổi:**
  - Đổi tên enum theo chuẩn Master Guide §13 trong `packages/agent_core/`:
    - `PermissionLevel` → `AutonomyLevel`
    - `ToolRiskLevel` → `CapabilityRisk`
    - `ToolPermission` → `PrincipalAuthorization` (hoặc gộp nếu tương đương)
    - Loại bỏ `PermissionClass`.
  - Giữ nguyên monotone conjunction: `DENY > REQUIRE_APPROVAL > ALLOW`, requirement `AllOf` khi không thể so sánh trực tiếp.
- **Characterization Harness:**
  - `tests/agentos/core/test_policy.py`, `tests/agentos/core/test_policy_6d.py`, `tests/agentos/core/test_policy_rbac.py`
  - `tests/agent_core/governance/test_contracts.py`
  - `tests/agent_core/governance/test_accumulator.py`
  - `tests/agent_core/governance/test_hashing.py`
  - `tests/agent_core/governance/test_store_protocol.py`
  - `tests/agent_core/governance/providers/test_postgres_store.py`
  - `tests/agent_core/governance/providers/test_in_memory_store.py`

---

### 3.3. Runtime & Execution Kernel
- **Module nguồn:**
  - `agentos/core/runtime.py` (`AgentRuntime` — điều phối routing qua ADK/DeepSeek/Native)
  - `agentos/core/executor.py` (`NativeAgentExecutor`, `ADKOrchestrationExecutor`, `DeepSeekHarnessExecutor`)
  - `agentos/core/planner.py` (`Planner`)
- **Disposition:** **SUPERSEDE implementation** — Không port mã nguồn này. Thay thế bằng `ExecutionKernel` Protocol và implementation trên nền OpenAI Agents SDK (`packages/agent_core/kernel/openai_agents_kernel.py` ở Phase 3).
- **Điều kiện Audit & Chuyển đổi:**
  - Đọc hiểu hành vi xử lý stream, tool call parsing, và model adapter routing từ mã nguồn cũ để làm baseline viết test đối chiếu (DeepSeek Compatibility Matrix).
- **Characterization Harness:**
  - `tests/agentos/test_executor.py`
  - `tests/agentos/test_planner.py`
  - `tests/agentos/test_runtime_end_to_end.py`
  - `tests/agentos/test_runtime_adapter_contract.py`
  - `tests/agentos/core/test_deepseek_harness_provider.py`
  - `tests/agentos/core/test_openai_compatible_provider.py`
  - `tests/agentos/core/test_anthropic_provider.py`

---

### 3.4. Coordination Primitives (Độc lập Framework)
- **Module nguồn:**
  - `agentos/orchestration/adk/orchestrator.py`
  - `agentos/orchestration/adk/nodes/*.py` (10 node types: `approval_gate_node`, `build_company_context_node`, `create_mission_node`, `execution_node`, `governance_gate_node`, `planning_node`, `quality_gate_node`, `risk_classification_node`, `specialist_delegation_node`, `synthesis_node`).
- **Disposition:** **PROMOTE patterns/invariants only, KHÔNG mang theo mã nguồn phụ thuộc Google ADK**.
- **Đích dự kiến:** `packages/agent_core/coordination/` (`delegate.py`, `parallel.py`, `supervisor.py`, `risk_classification.py`, `approval_gate.py`, `quality_gate.py`, `synthesis.py` ở Phase 3).
- **Điều kiện Audit & Chuyển đổi:**
  - Tuyệt đối loại bỏ import từ `google.adk.*` và các private API như `google.adk.workflow._function_node.FunctionNode`.
  - Tái cấu trúc các mẫu điều phối (parallel fanout, specialist delegation, supervisor synthesis, quality gate) thành các primitive thuần túy xây dựng trên `ExecutionKernel` Protocol.
- **Characterization Harness:**
  - `tests/agentos/orchestration/adk/test_nodes.py`
  - `tests/agentos/orchestration/adk/test_orchestrator.py`
  - `tests/agentos/agents/test_parallel.py`
  - `tests/agentos/agents/test_supervisor.py`
  - `tests/agentos/agents/test_debate.py`
  - `tests/agentos/agents/test_sequential.py`

---

### 3.5. Capability Gateway & Invocation Ledger
- **Module nguồn:**
  - `agentos/tools/` & `agentos/core/policy.py`
- **Disposition:** **REWRITE & PROMOTE gateway semantics** (Phase 4).
- **Đích dự kiến:** `packages/agent_core/capabilities/` (`gateway.py`).
- **Điều kiện Audit & Chuyển đổi:**
  - Thực hiện pipeline 10 bước nghiêm ngặt theo Master Guide §16.2: Resolve → Validate → Connector/Grant → `InvocationIdentity` → Policy Evaluate → Governance Accumulate → Approval Gate → `ExecutionTargetSnapshot` → Idempotency Check → Execute → Audit (`run_events`) → Persist (`run_tool_calls`).
  - Đảm bảo `tool_call_id` ổn định và canonical payload hash.
- **Characterization Harness:**
  - `tests/agentos/test_tool_registry.py`
  - `tests/agentos/test_tool_spec_v2.py`
  - `tests/agentos/test_encore_tool_bindings.py`
  - Test idempotency failure window qua process restart thật (Phase 4).

---

### 3.6. Durable Approval Service
- **Module nguồn:**
  - `agentos/core/approval.py` (`ApprovalService`, `_pending_approvals: dict` in-memory).
- **Disposition:** **REWRITE to Durable model** (Phase 5).
- **Đích dự kiến:** `packages/agent_core/capabilities/approval_service.py`.
- **Điều kiện Audit & Chuyển đổi:**
  - Bỏ hoàn toàn lookup `(run_id, action)`.
  - Bắt buộc lookup theo exact tuple: `run_id + tool_call_id + checkpoint_ref`.
  - Lưu trữ trên bảng `agent_core.approvals` và checkpoint tương ứng.
- **Characterization Harness:**
  - `tests/agentos/core/test_approval.py`
  - `tests/agentos/api/test_approval_lifecycle.py`
  - `tests/agentos/api/test_approval_resume_same_run.py`

---

### 3.7. COSA Composition Root
- **Module nguồn:**
  - `agentos/core/factory.py` (`build_cosa_agent_plane()`), `agentos/core/agent.py`.
- **Disposition:** **PROMOTE composition knowledge, REWRITE implementation** (Phase 7).
- **Đích dự kiến:** `apps/cosa/composition/`.
- **Điều kiện Audit & Chuyển đổi:**
  - Sử dụng dependency graph hiện có làm checklist (Model provider + Capability registry + Policy engine + Approval service + Memory/Knowledge ports + Trace/Audit sink).
  - Không để `packages/agent_core/` import ngược từ `services/company/*` — chỉ `apps/cosa/` mới được phép kết nối business domain.
- **Characterization Harness:**
  - `tests/agentos/test_factory_composition.py`
  - `tests/agentos/test_composition_routing.py`
  - `tests/agentos/test_services_pilot_e2e.py`
  - `tests/agentos/test_commercial_smoke_e2e.py`
  - `tests/agentos/test_strategy_smoke_e2e.py`

---

### 3.8. Chat API & Flutter Client Integration
- **Module nguồn:**
  - `agentos/api/app.py`, `agentos/api/chat/routes.py`, `agentos/api/chat/schemas.py`, `agentos/core/events.py`.
  - Frontend consumer: `frontend/lib/modules/chat/services/agent_chat_service.dart`.
- **Disposition:** **PROMOTE contract candidate, REWRITE lifecycle implementation** (Phase 8).
- **Đích dự kiến:** `apps/cosa/api/` & Sửa `AgentChatService` trỏ sang endpoint mới.
- **Điều kiện Audit & Chuyển đổi:**
  - Giữ nguyên path `/agent/*` và từ vựng sự kiện SSE (`message.delta`, `citation`, `approval_required`, `run.completed`...).
  - Xóa bỏ `_pending_runs: dict` trong RAM và unmanaged background tasks `asyncio.create_task`.
  - Khắc phục lỗi nuốt exception (`try { ... } catch (e) { return []; }`) trong `AgentChatService` để phân biệt rõ ràng giữa "dữ liệu trống" và "lỗi kết nối API".
- **Characterization Harness:**
  - `tests/agentos/api/test_chat_routes.py`
  - `tests/agentos/api/test_event_stream.py`
  - `tests/agentos/api/test_citation_events.py`
  - `tests/agentos/api/test_persistence.py`
  - `tests/agentos/api/test_context_builder_multi_layer.py`
  - `tests/agentos/api/test_voice_continuity.py`

---

### 3.9. Memory Subsystem
- **Module nguồn:**
  - `agentos/memory/store.py`, `service.py`, `models.py`, `consolidation.py`, `retriever.py`, `retrieval.py`, `pgvector_store.py`, `base.py`, `exceptions.py`.
  - `agentos/memory/providers/` (`postgres.py`, `in_memory.py`, `tencent_agent_memory.py`).
- **Disposition:** **PROMOTE-after-audit** (Phase 9).
- **Đích dự kiến:** `packages/agent_core/memory/`.
- **Điều kiện Audit & Chuyển đổi:**
  - Rà soát và tách biệt hoàn toàn coupling với `AgentRuntime`, `Executor`, hoặc enum `PermissionLevel` cũ.
  - Bổ sung các trường canonical theo Master Guide §25.2/§26: tenant scope, ACL, provenance, retention, sensitivity, supersession.
- **Characterization Harness:**
  - `tests/agentos/memory/test_store.py`
  - `tests/agentos/memory/test_models.py`
  - `tests/agentos/memory/test_memory_service.py`
  - `tests/agentos/memory/test_retriever.py`
  - `tests/agentos/memory/test_retrieval.py`
  - `tests/agentos/memory/test_consolidation.py`
  - `tests/agentos/memory/test_providers_structure.py`
  - `tests/agentos/memory/test_postgres_memory_store.py`
  - `tests/agentos/memory/test_postgres_memory_store_integration.py`

---

### 3.10. Knowledge Subsystem
- **Module nguồn:**
  - `agentos/knowledge/store.py`, `ingest.py`, `retrieval.py`, `pgvector_store.py`, `parsers.py`, `chunking.py`.
- **Disposition:** **PROMOTE-after-audit** (Phase 9).
- **Đích dự kiến:** `packages/agent_core/knowledge/`.
- **Điều kiện Audit & Chuyển đổi:**
  - Tách embedding provider và vector store thành các protocol độc lập.
  - Bảo đảm phân tách dữ liệu theo tenant và workspace.
- **Characterization Harness:**
  - `tests/agentos/knowledge/test_store.py`
  - `tests/agentos/knowledge/test_parsers.py`
  - `tests/agentos/knowledge/test_chunking.py`
  - `tests/agentos/knowledge/test_ingest.py`
  - `tests/agentos/knowledge/test_retrieval.py`
  - `tests/agentos/knowledge/test_pgvector_store.py`
  - `tests/agentos/knowledge/test_pgvector_store_integration.py`

---

### 3.11. Evals & Regression Harness
- **Module nguồn:**
  - `agentos/evals/runner.py`, `regression.py`, `run_regression_check.py`, `safety_eval.py`, `agent_eval.py`, `skill_eval.py`, `workflow_eval.py`, `retrieval_eval.py`, `model_eval.py`, `tool_eval.py`, `business_outcome_eval.py`, `strategy/eval_cases.py`, `baselines/latest.json`.
- **Disposition:** **PROMOTE thẳng (Baseline cho Phase 9 Eval Suite)**.
- **Đích dự kiến:** `packages/agent_core/evals/`.
- **Điều kiện Audit & Chuyển đổi:**
  - Giữ nguyên taxonomy và bộ test baseline; nối runner với `ExecutionKernel` mới.
  - Phục vụ trực tiếp cho 4 nhóm eval ở Master Guide §33 (Model/Kernel capability, Business correctness, Durability/Recovery, Security/Governance).
- **Characterization Harness:**
  - `tests/agentos/evals/test_eval_taxonomy.py`
  - `tests/agentos/evals/test_model_eval.py`
  - `tests/agentos/evals/test_workflow_eval.py`
  - `tests/agentos/evals/test_skill_eval.py`
  - `tests/agentos/evals/test_agent_eval.py`
  - `tests/agentos/evals/test_strategy_skills_eval.py`
  - `tests/agentos/evals/test_business_outcome_eval.py`
  - `tests/agentos/evals/test_regression.py`
  - `tests/agentos/evals/test_full_eval_integration.py`

---

### 3.12. Profiles, Skills & Supply Chain
- **Module nguồn:**
  - `agentos/profiles/registry.py`, `schemas.py`, `definitions.py`.
  - `agentos/skills/loader.py`, `registry.py`, `router.py`, `manifest.py`, `instruction_loader.py`, `packs/`, `supply_chain/`.
- **Disposition:** **PROMOTE semantics + definitions** (Phase 1 & 7).
- **Đích dự kiến:** `packages/agent_core/profiles/`, `skills/` & `apps/cosa/agents/`.
- **Điều kiện Audit & Chuyển đổi:**
  - Giữ nguyên định nghĩa role và skillpacks của business domain; cập nhật cơ chế load/bind để tương thích với `AgentSpec` và `ExecutionKernel`.
- **Characterization Harness:**
  - `tests/agentos/profiles/test_profile_registry.py`, `test_profile_schema.py`
  - `tests/agentos/skills/test_registry.py`, `test_loader.py`, `test_marketing_skillpacks.py`, `test_router.py`, `test_manifest.py`, `test_skillpacks_integration.py`, `test_instruction_loader.py`, `test_strategy_skillpacks.py`
  - `tests/agentos/skills/supply_chain/test_lifecycle.py`, `test_artifact_store.py`, `test_catalog.py`, `test_pinning.py`, `test_scan.py`, `test_pipeline.py`

---

### 3.13. Prototype Governance Schema → Canonical Durability Mapping (Phase 2)
Theo Master Guide §12 và Implementation Plan Phase 2, bảng mapping tường minh giữa schema prototype `agent_core_governance.*` và 5 bảng canonical `agent_core.*`:

| Bảng Prototype (`agent_core_governance.*`) | Bảng Canonical (`agent_core.*`) | Trường / Cột tương ứng | Mục đích & Quy tắc chuyển đổi |
|---|---|---|---|
| `spec_resolution_manifest_entries` | `agent_core.run_checkpoints` | `manifest_snapshot` (JSONB) | Gắn bất biến danh mục specs đã giải quyết (`PinnedSpecIdentity`) vào từng checkpoint của Run. |
| `invocation_governance_state` | `agent_core.run_tool_calls` | `governance_state` (JSONB) | Lưu trữ trạng thái tích luỹ monotonic của từng tool call (`accumulated_outcome`, `accumulated_requirement`, `version_no`). |
| `invocation_governance_history` | `agent_core.run_events` | `event_type = 'policy.evaluated'`, `payload` | Event audit stream append-only ghi nhận toàn bộ chuỗi quan sát chính sách. |
| `approval_evidence` | `agent_core.approvals` | `evidence` (JSONB), `reviewer`, `decided_at` | Bằng chứng phê duyệt của con người được gắn kết chính thức với approval record. |
| *(Chưa có ở prototype)* | `agent_core.runs` | `run_id`, `status`, `principal`, `input_payload`, `final_output` | Quản lý vòng đời cấp cao nhất của toàn bộ Run. |

**Chính sách tồn tại song song (Co-existence Policy):**
- Schema `agent_core_governance.*` tiếp tục được duy trì song song tối đa đến hết **Phase 6** để phục vụ backward compatibility cho các module đang migrate.
- Sau Phase 6, `agent_core_governance.*` chỉ dùng để đọc dữ liệu lịch sử nếu cần, toàn bộ write path chuyển 100% sang 5 bảng `agent_core.*`.
- Module chuyển đổi dữ liệu tự động đã được hiện thực hoá tại [`packages/agent_core/runs/migration_adapter.py`](file:///Volumes/SSD/javis-saas/packages/agent_core/runs/migration_adapter.py).

### 3.14. DeepSeek & Model Provider Capability Matrix (Phase 3)
Theo Master Guide §9.4 và Implementation Plan Phase 3, bảng đánh giá capability profile đã được kiểm thử tự động tại [`tests/agent_core/kernel/test_deepseek_compatibility_matrix.py`](file:///Volumes/SSD/javis-saas/tests/agent_core/kernel/test_deepseek_compatibility_matrix.py):

| Capability Item | Trạng thái | Ghi chú kỹ thuật |
|---|---|---|
| 1. Basic response | **PASS** | Standard chat completion text streaming hoạt động chính xác. |
| 2. Structured output | **PASS** | JSON schema structured response được parse và validate đầy đủ. |
| 3. Single tool call | **PASS** | Tool call được tạo, ghi nhận vào exact invocation ledger và thực thi trơn tru. |
| 4. Parallel tool calls | **PASS** | Nhiều tool calls đồng thời trong 1 reasoning turn được gom nhóm và thực thi song song. |
| 5. Streaming | **PASS** | SSE event stream emit đầy đủ các `run_events` vocabulary (`message.delta`, `tool.requested`, ...). |
| 6. Tool-call IDs | **PASS** | Tool call ID nguyên bản từ model được bảo toàn chính xác trong ledger (`run_tool_calls`). |
| 7. Usage metrics | **PASS** | Metadata token usage được thu thập và lưu trữ vào RunResult. |
| 8. Error propagation | **PASS** | Exception từ model/network được bắt và xử lý graceful, không gây crash unhandled. |
| 9. Context length | **PASS** | Lịch sử hội thoại đa lượt (multi-turn conversation history) được lưu giữ trong `KernelRunState`. |
| 10. RunState resume | **PASS** | Zero-loss JSON serialization round-trip (`to_json` / `from_json`) kết nối bền vững với `run_checkpoints`. |
| 11. Agent-as-tool | **PASS** | Specialist agent được đóng gói thành tool call uỷ quyền qua `ExecutionKernel`. |
| 12. Approval interruption | **PASS** | Tự động sinh `WaitDescriptor(kind=WaitKind.APPROVAL)` và tạo bản ghi `agent_core.approvals`. |

### 3.15. Capability Gateway & Exact Invocation Identity (Phase 4)
Theo Master Guide §16 & §17 và Implementation Plan Phase 4:
- **Capability Gateway:** Pipeline chuẩn 10 bước tại [`packages/agent_core/capabilities/gateway.py`](file:///Volumes/SSD/javis-saas/packages/agent_core/capabilities/gateway.py):
  1. Resolve capability
  2. Validate input schema theo `CapabilitySpec`
  3. Construct `ExecutionTargetSnapshot`
  4. Construct stable `InvocationIdentity` (`tool_call_id`, `run_id`, `capability_id`, `payload_hash`, `idempotency_key`)
  5. Canonicalize payload & SHA-256 hash (`canonicalize_payload`)
  6. Policy evaluate
  7. Monotonic governance accumulation (`InvocationGovernanceState`)
  8. Approval gate check (`agent_core.approvals`)
  9. Idempotency check theo `idempotency_key` (chống duplicate execution side effects)
  10. Execute handler, emit `run_events`, persist `run_tool_calls`
- **Stable Invocation Identity:** Tuyệt đối không dùng `run_id + tool_name`. Mọi lần gọi tool đều có `tool_call_id` duy nhất (đã verify qua test case "same tool twice").
- **Crash Failure Window Idempotency Test:** Kiểm thử thực tế qua subprocess con bị `os._exit` ngay sau khi remote system commit transaction, xác minh sau khi restart/retry cùng `idempotency_key` hệ thống không phát sinh side effect thứ hai và reconcile đúng kết quả gốc ([`tests/agent_core/capabilities/test_idempotency_failure_window.py`](file:///Volumes/SSD/javis-saas/tests/agent_core/capabilities/test_idempotency_failure_window.py)).

### 3.16. Durable Approval Service (Phase 5)
Theo Master Guide §18 và Implementation Plan Phase 5:
- **Durable Approval Service:** Triển khai tại [`packages/agent_core/capabilities/approval_service.py`](file:///Volumes/SSD/javis-saas/packages/agent_core/capabilities/approval_service.py) thay thế hoàn toàn cơ chế lookup `(run_id, action)` cũ của AgentOS.
- **Invocation-Scoped Binding:** Lookup và ràng buộc phê duyệt bắt buộc theo `(run_id, tool_call_id, checkpoint_ref)` hoặc `approval_id`.
- **Approved is NOT a Permanent Bypass Token (§18.1):** 
  - Trước khi resume từ approval, bắt buộc thẩm định fresh ambient governance (nếu tenant bị suspend hoặc principal bị revoke -> DENY ngay lập tức).
  - Kiểm tra Target Drift: So sánh `ExecutionTargetSnapshot` giữa thời điểm request và resume; nếu connector hoặc schema hash thay đổi -> Approval cũ bị đánh dấu STALE và chặn thực thi.
- **Xác minh Cross-Process Approval Resume:** Kiểm thử qua Subprocess Python độc lập đọc Approval đã duyệt từ shared storage, thẩm định invariants an toàn và resume thành công ([`tests/agent_core/capabilities/test_approval_process_resume.py`](file:///Volumes/SSD/javis-saas/tests/agent_core/capabilities/test_approval_process_resume.py)).

### 3.17. Spec-Drift & Governance-Drift Test Suite (Phase 6)
Theo Master Guide §41.1 và Implementation Plan Phase 6, toàn bộ 9 kịch bản drift độc lập đã được triển khai và vượt qua 100% kiểm thử tại [`tests/agent_core/drift/`](file:///Volumes/SSD/javis-saas/tests/agent_core/drift/):

| Test Case | File | Kịch bản & Invariant | Trạng thái |
|---|---|---|---|
| **Case A** | [`test_case_a_workflow_spec_drift.py`](file:///Volumes/SSD/javis-saas/tests/agent_core/drift/test_case_a_workflow_spec_drift.py) | Workflow v1 pause → v2 publish → resume BẮT BUỘC chạy v1, không có node v2. | **PASS** |
| **Case B** | [`test_case_b_agent_spec_privilege_widening.py`](file:///Volumes/SSD/javis-saas/tests/agent_core/drift/test_case_b_agent_spec_privilege_widening.py) | AgentSpec v1 autonomy thấp pause → v2 autonomy cao publish → resume không kế thừa v2. | **PASS** |
| **Case C** | [`test_case_c_current_revocation.py`](file:///Volumes/SSD/javis-saas/tests/agent_core/drift/test_case_c_current_revocation.py) | Run được allow/approved → pause → principal/tenant bị revoke/suspend → resume DENY. | **PASS** |
| **Case D** | [`test_case_d_risk_increase.py`](file:///Volumes/SSD/javis-saas/tests/agent_core/drift/test_case_d_risk_increase.py) | Approve ở MEDIUM → risk leo thang CRITICAL trước resume → evidence cũ không đủ/stale. | **PASS** |
| **Case E** | [`test_case_e_risk_relaxation.py`](file:///Volumes/SSD/javis-saas/tests/agent_core/drift/test_case_e_risk_relaxation.py) | Approve ở CRITICAL → policy nới lỏng xuống LOW/ALLOW → constraint lịch sử vẫn giữ. | **PASS** |
| **Case F** | [`test_case_f_orthogonal_approval_requirement.py`](file:///Volumes/SSD/javis-saas/tests/agent_core/drift/test_case_f_orthogonal_approval_requirement.py) | Request cần FounderApproval, resume cần FinanceAdminApproval → `AllOf` cần CẢ HAI. | **PASS** |
| **Case G** | [`test_case_g_same_tool_twice.py`](file:///Volumes/SSD/javis-saas/tests/agent_core/drift/test_case_g_same_tool_twice.py) | Gọi cùng 1 tool 2 lần → `tool_call_id` khác nhau, approval/evidence không cross. | **PASS** |
| **Case H** | [`test_case_h_target_drift.py`](file:///Volumes/SSD/javis-saas/tests/agent_core/drift/test_case_h_target_drift.py) | Cùng capability + payload nhưng connector/schema target đổi → approval cũ stale. | **PASS** |
| **Case I** | [`test_case_i_side_effect_committed_before_crash.py`](file:///Volumes/SSD/javis-saas/tests/agent_core/drift/test_case_i_side_effect_committed_before_crash.py) | Remote commit thành công → process chết trước mark success → restart không duplicate. | **PASS** |

### 3.18. Compose `apps/cosa/` & Reusability Gate Check (Phase 7)
Theo Master Guide §4, §8, §42 và Implementation Plan Phase 7:
- **Cấu trúc `apps/cosa/`:** Triển khai độc lập tại `apps/cosa/`:
  - `apps/cosa/composition/agent_plane.py`: `CosaAgentPlane` và `build_cosa_agent_plane()` lắp ráp toàn bộ Agent Substrate từ `packages/agent_core/*`.
  - `apps/cosa/capabilities/`: Read capability (`operations.task.list`, `operations.task.read`) và Write capability (`finance.payout.execute`, `finance.transaction.record`) kết nối Encore `services/company/` qua `CompanyServiceClient`. Đây là nơi **DUY NHẤT** kết nối `services/company/*`.
  - `apps/cosa/policies/evaluator.py`: `CosaPolicyEngine` quản trị rủi ro và phê duyệt cho COSA domain.
  - `apps/cosa/agents/specs.py` & `apps/cosa/workflows/specs.py`: Pinned specs cho COSA agents và workflows.
- **Reusability Gate Check (§4.2 & §42):** Kiểm thử tự động tại [`tests/apps/test_reusability_gate.py`](file:///Volumes/SSD/javis-saas/tests/apps/test_reusability_gate.py) xây dựng một Second App hoàn toàn độc lập (HealthClinicAgentPlane) chỉ dùng `packages/agent_core/*`, chứng minh Agent Core không bị dính chặt với COSA domain.
- **Boundary Audit:** Kiểm tra AST/quét tự động tại [`tests/apps/cosa/test_services_boundary_audit.py`](file:///Volumes/SSD/javis-saas/tests/apps/cosa/test_services_boundary_audit.py), xác nhận `packages/agent_core/` có đúng **0 imports** từ `services/*` hay `apps/*`.

### 3.19. Vertical Slice 1 & 2: Text Chat Integration & Contract Decision (Phase 8)
Theo Master Guide §40, §41 và Implementation Plan Phase 8:

#### Bảng quyết định Contract (Phase 8 contract decision)
| Endpoint / Contract cũ (`agentos/api/chat/`) | Trạng thái | Quyết định & Lý do | Đích triển khai |
|---|---|---|---|
| `POST /agent/conversations` | **GIỮ NGUYÊN SHAPE** | Giữ nguyên format `ConversationCreate` và `ConversationResponse` để Flutter không bị vỡ giao diện; backend chuyển sang lưu trữ conversation record chuẩn. | `apps/cosa/api/routes.py` |
| `GET /agent/conversations` | **GIỮ NGUYÊN SHAPE** | Hỗ trợ phân trang `limit`, `offset`, `include_archived`. | `apps/cosa/api/routes.py` |
| `GET /agent/conversations/{id}` | **GIỮ NGUYÊN SHAPE** | Trả về messages và attachments. | `apps/cosa/api/routes.py` |
| `PATCH /agent/conversations/{id}` | **GIỮ NGUYÊN SHAPE** | Cập nhật title, active_agent_profile, archive. | `apps/cosa/api/routes.py` |
| `POST /agent/conversations/{id}/messages` | **GIỮ NGUYÊN SHAPE, THAY SUBSTRATE** | Trả về 202 Accepted với `RunResponse(run_id, conversation_id, status: RUNNING)`. Backend bên dưới gọi `CosaAgentPlane.kernel.run()` với `RunRequest`, stream events vào `agent_core.run_events`. | `apps/cosa/api/routes.py` |
| `POST /agent/runs/{id}/cancel` | **GIỮ NGUYÊN SHAPE** | Backend gọi `CosaAgentPlane.kernel.cancel(run_id)`. | `apps/cosa/api/routes.py` |
| `POST /agent/approvals/{id}/decision` | **GIỮ NGUYÊN SHAPE** | Gọi `CosaAgentPlane.approval_service.submit_decision(...)` rồi kích hoạt resume đúng quy trình Phase 5. | `apps/cosa/api/routes.py` |
| `GET /agent/runs/{id}/events` | **GIỮ NGUYÊN SSE CONTRACT** | Protocol text/event-stream với `run.started`, `reasoning.status`, `message.started`, `message.delta`, `approval.required`, `approval.resolved`, `run.completed`, `run.failed`, `run.cancelled`. | `apps/cosa/api/event_stream.py` |

#### Nâng cấp Observability Frontend (Flutter Dart)
- Cập nhật `frontend/lib/modules/chat/services/agent_chat_service.dart`:
  - Định nghĩa ngoại lệ tường minh `AgentChatApiException`.
  - Loại bỏ hoàn toàn cơ chế swallow error thành `[]` hay `null` một cách im lặng. Các lỗi HTTP/Network giờ đây ném ngoại lệ hoặc log chi tiết mã lỗi/body để phân biệt rõ ràng với trạng thái "danh sách rỗng".

#### Kết quả Vertical Slice Acceptance Tests
- **Vertical Slice 1 (Read Path, §40)** ([`tests/apps/cosa/test_vertical_slice_1_read_path.py`](file:///Volumes/SSD/javis-saas/tests/apps/cosa/test_vertical_slice_1_read_path.py)):
  - Tạo conversation → gửi message → nhận 202 RUNNING với run_id duy nhất → SSE streaming đầy đủ `run.started`, `reasoning.status`, `message.delta`, `run.completed` → tin nhắn assistant hoàn thành (**PASS**).
- **Vertical Slice 2 (Write + Approval + Resume, §41)** ([`tests/apps/cosa/test_vertical_slice_2_write_approval.py`](file:///Volumes/SSD/javis-saas/tests/apps/cosa/test_vertical_slice_2_write_approval.py)):
  - Gửi lệnh wire payout high-risk → Kernel checkpoint & pause tại `WAITING_APPROVAL` → SSE phát sinh `approval.required` → Reviewer gửi approval decision qua API → SSE phát sinh `approval.resolved` và resume hoàn thành `run.completed` (**PASS**).

### 3.20. P1 Subsystems & Memory / Knowledge / Evals Promotion (Phase 9)
Theo Master Guide §43 (P1 Items) và Implementation Plan Phase 9:
1. **Routable `WaitDescriptor` Resolver (§14 & §43.1):** Triển khai `packages/agent_core/coordination/wait_resolver.py` (`WaitResolver`), định tuyến và unblock chính xác dựa trên event trigger, responder authority (`owner_responder`), và nạp checkpoint.
2. **Durable Workflow Definition Repository (§10.3 & §43.2):** Triển khai `packages/agent_core/workflows/repository.py` (`InMemoryWorkflowDefinitionRepository`), lưu trữ immutable definition records `(workflow_id, version, definition_hash)` chống drift.
3. **`ExecutionTargetSnapshot` Full Shape (§17.4 & §43.3):** Điền đủ schema tại `packages/agent_core/contracts/capability.py` (`target_id`, `connector_id`, `endpoint_url`, `credential_scope`, `schema_hash_version`, `capability_risk_at_request_time`).
4. **`ConnectorGrant` Normalization (§19 & §43.4):** Triển khai `packages/agent_core/capabilities/grants.py` (`ConnectorGrant`, `verify_connector_grant()`) kiểm tra phạm vi tenant, principal, action wildcard, resource scope, expiration, revocation.
5. **Exact-Once Delegation (`ExpansionFingerprint`) (§22 & §43.5):** Triển khai `packages/agent_core/coordination/expansion.py` (`ExpansionFingerprint`, `ExpansionManager`) deduplicate fanout execution.
6. **Run Recovery Service (§21 & §43.6):** Triển khai `packages/agent_core/runs/recovery.py` (`RunRecoveryService`) khôi phục liveness an toàn, không mở rộng quyền (no privilege widening), giữ nguyên pause gate tại `WAITING_APPROVAL`.
7. **Low-Trust Provenance (§34 & §43.7):** Triển khai `packages/agent_core/contracts/provenance.py` (`TrustLevel`, `UntrustedSourceContext`, `ProvenanceMetadata`).
8. **Ambient Budget Gate (§35 & §43.8):** Triển khai `packages/agent_core/governance/budget_gate.py` (`BudgetGate`, `BudgetQuota`, `BudgetDecision`) kiểm soát hạn mức tokens và USD spend.
9. **Artifact Lifecycle & Provenance (§32 & §43.9):** Triển khai `packages/agent_core/artifacts/lifecycle.py` (`ArtifactManager`, `ArtifactRecord`, `ArtifactReference`).
10. **Memory & Knowledge Promotion (§25, §26 & §43.10):** Audit và loại bỏ hoàn toàn legacy coupling; xây dựng `packages/agent_core/memory/` và `packages/agent_core/knowledge/`.
11. **Evals Baseline Suite (§33 & §43.11):** Triển khai `packages/agent_core/evals/` (`CanonicalEvalRunner`, `EvalTestCase`, `EvalResult`) đánh giá 4 nhóm: Kernel capability, Business correctness, Durability/recovery, Security/governance.

### 3.21. P2 Hardening & Scale Subsystems (Phase 10)
Theo Master Guide §43 (P2 Items) và Implementation Plan Phase 10:
1. **L3 Capability Implementation Identity (ADR-A):** `packages/agent_core/contracts/capability.py` (`CapabilityImplementationIdentity`), pin phiên bản handler, schema và connector hash phục vụ rollback an toàn.
2. **Multi-Worker Execution Leases:** `packages/agent_core/runs/leases.py` (`RunLeaseManager`, `RunLease`) quản lý lock phân tán, gia hạn heartbeat và giải phóng lease chống xung đột đa tiến trình.
3. **Work Queue / Coalescing Scheduler:** `packages/agent_core/coordination/scheduler.py` (`RunScheduler`, `ScheduledTaskRecord`) hàng đợi tác vụ hỗ trợ gộp payload theo `coalescing_key`.
4. **Plugin / Extensibility Framework:** `packages/agent_core/plugins/manifest.py` (`PluginManifest`, `PluginCapabilityGrant`, `PluginRegistry`) hỗ trợ mở rộng capability bên thứ ba.
5. **Role Hierarchy & Weighted Quorum Policy:** `packages/agent_core/governance/quorum.py` (`RoleHierarchyTree`, `WeightedQuorumPolicy`) phân cấp vai trò phê duyệt đa cấp và quorum có trọng số.
6. **Dormant Run Lifecycle & Expiry (ADR-D):** `packages/agent_core/runs/expiry.py` (`RunExpiryManager`) quét và dọn dẹp các run/approval đóng băng lâu ngày.
7. **Cloud Multi-Backend Artifact Distribution:** `packages/agent_core/artifacts/distribution.py` (`ArtifactDistributionRouter`, `LocalArtifactBackend`, `S3ArtifactBackend`) hỗ trợ phân phối lưu trữ file đa đám mây.

### 3.22. Context Prior Art Salvage Analysis (Phase 0)
Theo `docs/architecture/CONTEXT_ASSEMBLER_AUDIT.md` và Hermes/LangGraph Integration Plan Phase 0:
- **Audit 4 file legacy:** `legacy/agent_runtime/workforce/agents/context/{assembler,builder,compiler,scope_resolver}.py`.
- **Invariants GIỮ:**
  - Governance-before-fetch (`builder.py`): đánh giá thẩm quyền trước khi gọi RPC nạp dữ liệu.
  - Intent-based scoping (`assembler.py`): nạp tối thiểu theo intent context.
  - Context section provenance/freshness (`builder.py`): cấu trúc `ContextFragment` mang thông tin source, lifetime (STABLE, RUN, CURRENT, EPHEMERAL).
  - ScopeSet / token budgeting (`scope_resolver.py`).
- **Invariants BỎ:**
  - Bỏ toàn bộ query trực tiếp SQLAlchemy business models trong `assembler.py` (chuyển sang gọi qua RPC client trong `apps/cosa/composition/context_assembler.py`).
  - Bỏ crude token estimation (`len(text)//4`), fake trimming, placeholder L5 rỗng, và blind error swallowing.

### 3.23. Archive `agentos/` (Phase 11)
- Toàn bộ 15 tiêu chí Definition of Done (Master Guide §42) đã đạt **PASS 100%**.
- Di chuyển `agentos/` sang [`legacy/agent_runtime_archive/agentos`](file:///Volumes/SSD/javis-saas/legacy/agent_runtime_archive/agentos) và `tests/agentos/` sang [`legacy/agent_runtime_archive/tests_agentos`](file:///Volumes/SSD/javis-saas/legacy/agent_runtime_archive/tests_agentos) bằng `git mv` (bảo toàn 100% lịch sử git).
- Cập nhật `pytest.ini` trỏ vào `tests/agent_core` và `tests/apps`.
- Cập nhật `docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md` chính thức đóng vòng đời của `agentos/`.

---

## 4. Phase Migration Tracking Checklist

- [x] **Phase 0:** Hoàn thành Asset Inventory & Salvage Classification (`docs/architecture/agentos_salvage_inventory.md`).
- [x] **Phase 1:** Migrate VNext contracts (`packages/agent_core/contracts/`) + Migrate Workflow Engine (`packages/agent_core/workflows/`).
- [x] **Phase 2:** Triển khai Durable Run substrate (5 bảng `agent_core.*` + models/repository + cross-process resume test).
- [x] **Phase 3:** Triển khai OpenAI Agents Kernel (`ExecutionKernel`) + Coordination primitives (7 primitives + DeepSeek matrix test).
- [x] **Phase 4:** Triển khai Capability Gateway & exact Invocation Identity (10-step pipeline + failure window idempotency test).
- [x] **Phase 5:** Triển khai Durable Approval Service (`(run_id, tool_call_id, checkpoint_ref)` + fresh governance validation + cross-process test).
- [x] **Phase 6:** Xây dựng Spec-drift & Governance-drift test suite (9 test cases độc lập).
- [x] **Phase 7:** Compose `apps/cosa/` với read & write capabilities thật kết nối `services/company/` + Reusability gate check pass.
- [x] **Phase 8:** Sửa chữa / thay thế tích hợp Text Chat (Flutter `AgentChatService` ↔ `apps/cosa/api/`) + Vertical Slice 1 & 2 pass.
- [x] **Phase 9:** Hoàn thiện P1 items: WaitDescriptor, Durable Workflow Repo, Memory & Knowledge audit/promote, Evals baseline suite.
- [x] **Phase 10:** P2 hardening (L3 identity, multi-worker leases, coalescing scheduler, plugin manifest, weighted quorum, dormant expiry, cloud artifacts).
- [x] **Phase 11:** Archive `agentos/` vào `legacy/agent_runtime_archive/` sau khi đạt đủ 15 tiêu chí DoD.










