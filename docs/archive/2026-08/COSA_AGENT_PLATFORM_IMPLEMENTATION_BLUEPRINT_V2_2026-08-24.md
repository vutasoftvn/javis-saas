# COSA Agent Platform — Kế hoạch tái cấu trúc kiến trúc & database

> **Trạng thái:** Proposed Architecture / Restructuring Blueprint  
> **Ngày:** 2026-08-24  
> **Repository baseline đã audit:** `vutasoftvn/javis-saas@fcfe3877977c0d8be16078a1406aca8bd764cecc`  
> **Mục tiêu:** Tái cấu trúc Javis/COSA thành một **Agent Platform Core tái sử dụng được cho nhiều ứng dụng**, không khóa vào LangChain, Google ADK, OpenAI Agents SDK, DeepSeek Harness hoặc bất kỳ runtime/framework đơn lẻ nào.  
> **Phạm vi:** Python Agent Core, runtime integrations, workflow, capability/governance, durable execution, memory/knowledge/skills, control plane, protocol interoperability, observability, deployment, CI/CD và PostgreSQL schema/migration.

---

## 0. Executive Decision

COSA cần chuyển từ mô hình:

```text
COSA
  └── một "canonical framework runtime"
      └── model/tool/workflow/approval...
```

sang:

```text
COSA Agent Core
  ├── Contracts
  ├── Exact execution identity
  ├── Durable run/event/checkpoint substrate
  ├── Capability execution authority
  ├── Governance / Approval / Idempotency
  ├── Workflow contracts
  ├── Memory / Knowledge / Skills
  ├── Runtime / Provider protocols
  └── Protocol interoperability

        ↓ adapters

  LangChain / LangGraph / Google ADK
  OpenAI Agents SDK / PydanticAI
  DeepSeek Harness / remote runtimes
  LiteLLM / MCP / A2A / AG-UI
```

### Quyết định công nghệ

| Công nghệ | Quyết định | Vai trò |
|---|---|---|
| LangChain | **ADOPT** | Primary model/tool integration layer; ưu tiên DeepSeek |
| LangGraph | **SPIKE / OPTIONAL** | `WorkflowRuntime` implementation sau conformance benchmark |
| Google ADK 2.x | **OPTIONAL ADAPTER** | Graph/workflow/runtime/A2A implementation, nhất là Google/Gemini |
| OpenAI Agents SDK | **OPTIONAL ADAPTER** | OpenAI-native agent/handoff/realtime runtime |
| DeepSeek Harness | **HARVEST + EXPERIMENTAL REMOTE ADAPTER** | Plugin/event/session architecture; không làm canonical core |
| Hermes Agent | **HARVEST PATTERNS** | Skills, learning loop, memory/session UX, sandbox/messaging |
| Paperclip | **HARVEST CONTROL-PLANE PATTERNS** | Missions/tasks/workers/heartbeat/lease/budget |
| LiteLLM | **ADOPT INFRASTRUCTURE** | Model gateway, routing, budget/cost/fallback |
| MCP | **ADOPT STANDARD** | Agent ↔ tools/data |
| A2A | **ADOPT STANDARD** | Agent ↔ agent |
| AG-UI | **ALIGN / ADOPT** | Agent ↔ UI event contract |
| OpenTelemetry GenAI | **ADOPT STANDARD** | Tracing/metrics/events |
| DSPy | **OFFLINE ONLY** | Optimization/evals/spec generation |
| PydanticAI | **SPIKE** | Typed alternate kernel/reference implementation |
| OpenSandbox/Daytona/Modal/Docker | **ADAPTERS** | Sandbox/execution providers |

### Nguyên tắc khóa kiến trúc

> **One canonical run identity. One capability gateway. One governance authority. One durable event history. Multiple interchangeable runtimes.**

Không framework nào được quyền sở hữu hoặc định nghĩa lại:

- `run_id`;
- `(run_id, tool_call_id)`;
- tenant/principal authority;
- approval semantics;
- idempotency semantics;
- business capability identity;
- durable business/audit ledger;
- published `AgentSpec` / `WorkflowSpec` / `SkillSpec`;
- business truth.

---

# 1. Bối cảnh và kết quả audit hiện tại

## 1.1. Những phần đã đúng hướng và nên giữ

Codebase hiện tại đã có nhiều tài sản tốt, không nên rewrite:

```text
packages/agent_core/
├── contracts/
├── runs/
├── capabilities/
├── governance/
├── workflows/
├── coordination/
├── memory/
├── knowledge/
├── skills/
├── plugins/
├── artifacts/
└── evals/
```

`ExecutionKernel` hiện đã là một Python `Protocol`, nghĩa là về mặt contract hệ thống **không bắt buộc phải phụ thuộc OpenAI Agents SDK**. Đây là nền tảng đúng để chuyển sang multi-runtime.

`AgentSpec`, `RunRequest`, `RunResult`, `CapabilitySpec`, `ExecutionTargetSnapshot` cũng đã là typed Pydantic contracts và phần lớn không gắn framework.

Durable substrate hiện có:

- `agent_core.runs`;
- `agent_core.run_checkpoints`;
- `agent_core.run_events`;
- `agent_core.run_tool_calls`;
- `agent_core.approvals`.

Governance temporal model hiện có:

- `agent_core_governance.spec_resolution_manifest_entries`;
- `agent_core_governance.invocation_governance_state`;
- `agent_core_governance.invocation_governance_history`;
- `agent_core_governance.approval_evidence`.

Memory/knowledge hiện có:

- `agent_memory.agent_memories`;
- `knowledge.knowledge_sources`;
- `knowledge.knowledge_chunks`.

Các schema nghiệp vụ thuộc `services/company/*` và control plane thuộc `services/cosa/*` đã có boundary đúng: **agent core không được query trực tiếp business schema**.

## 1.2. Những vấn đề cần sửa trước khi mở rộng framework

### A. Canonical documentation đang gắn core vào OpenAI Agents SDK

Ownership map hiện mô tả `Execution Kernel = OpenAI Agents SDK` trong khi chính `ExecutionKernel` contract là framework-neutral.

**Điều chỉnh:** canonical owner phải là `ExecutionKernel Protocol`; OpenAI Agents SDK chỉ là một implementation.

### B. `OpenAIAgentsKernel` hiện tại không phải implementation đầy đủ của OpenAI Agents SDK

Implementation hiện có là manual OpenAI-compatible chat/tool loop.

**Điều chỉnh:** hoặc rename thành `OpenAICompatibleChatKernel`, hoặc thay bằng implementation OpenAI Agents SDK thật. Không để tên class/tài liệu tạo cảm giác SDK integration đã hoàn tất.

### C. Tool execution authority đang bị phân tán

Kernel và `CapabilityGateway` đều tham gia policy/approval/tool execution.

**Điều chỉnh:** mọi side effect chỉ được phép đi qua:

```text
Runtime
  ↓
ToolInvocation
  ↓
CapabilityGateway
  ↓
readiness → governance → approval → idempotency → execute → audit
```

Runtime chỉ được phát sinh **intent** gọi capability.

### D. Exact invocation identity cần được chuẩn hóa

Canonical identity phải là `(run_id, tool_call_id)`, không phải một `tool_call_id` độc lập và không được tạo lại ID khi chuyển từ kernel sang gateway.

### E. API shell vẫn còn state in-memory

Conversations/messages/pending run in-memory không phù hợp multi-replica/restart-safe architecture.

### F. Runtime/model failure không được biến thành assistant text

Provider timeout, malformed response, tool schema mismatch, context overflow phải là typed runtime failure, không phải assistant content rồi đánh dấu Run hoàn tất.

### G. CI/deployment path phải phản ánh canonical architecture mới

CI phải test `packages/agent_core`, `packages/agent_integrations`, `apps/cosa`, không tiếp tục dựa vào path legacy.

---

# 2. Mục tiêu tái cấu trúc

## 2.1. Product goals

Core mới phải dùng được cho:

- COSA Startup OS;
- Sales Agent;
- Marketing Agent;
- Legal/Finance Agent;
- Developer/Coding Agent;
- Personal Agent;
- SaaS vertical khác;
- CLI/Desktop agent;
- remote worker agents;
- embedded single-process app;
- multi-service enterprise deployment.

Một application mới không cần fork `agent_core`. Application chỉ cần chọn runtime adapter, cung cấp identity/tenant resolver, đăng ký capabilities, chọn memory/knowledge policy, cung cấp app composition và expose API/UI protocol.

## 2.2. Non-goals

Không thực hiện:

- rewrite toàn bộ Python sang TypeScript;
- đưa LangChain ontology vào core;
- đưa Google ADK session model vào core;
- đưa OpenAI Agents RunState vào canonical database;
- đưa DeepSeek Harness session log thành canonical source of truth;
- copy Paperclip/Hermes code wholesale;
- giao business authorization cho model/framework;
- lưu private chain-of-thought.

---

# 3. Kiến trúc đích

```text
┌──────────────────────────────────────────────────────────────┐
│                       APPLICATIONS                           │
│ COSA OS │ Sales │ Legal │ Dev Agent │ Personal │ Other SaaS │
└──────────────────────────────┬───────────────────────────────┘
                               │
                    REST / SSE / AG-UI
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                   APPLICATION COMPOSITION                    │
│ Auth/Tenant │ Conversation │ App capabilities │ UI mapping  │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│                        AGENT CORE                            │
│ Contracts / Specs / Registry                                │
│ Run / Checkpoint / Event / Wait                             │
│ Capability Gateway                                           │
│ Governance / Approval / Idempotency                         │
│ Workflow contracts                                           │
│ Memory / Knowledge / Skills                                 │
│ Coordination / Delegation                                    │
│ Protocol contracts                                           │
│ Observability contracts                                      │
└─────────────┬──────────────────┬─────────────────────────────┘
              │                  │
       Runtime adapters      External protocols
              │                  │
   ┌──────────┼──────────┐   ┌───┼─────────────┐
   │          │          │   │   │             │
LangChain   ADK       OpenAI MCP A2A          AG-UI
LangGraph   Pydantic  SDK
DeepSeek Harness(remote)
              │
┌─────────────▼────────────────────────────────────────────────┐
│                 MODEL / EXECUTION PLANE                     │
│ LiteLLM → DeepSeek / OpenAI / Gemini / Claude / Local       │
│ SandboxProvider → Docker / OpenSandbox / Daytona / Modal    │
└──────────────────────────────────────────────────────────────┘

                CONTROL PLANE — services/cosa

 Mission / Task / Assignment / Worker / Heartbeat / Lease
 Schedule / Budget / Cost / Watchdog / Runtime Slot / Artifact
```

---

# 4. Repo structure đích

## 4.1. Python reusable packages

```text
packages/
├── agent_core/
│   ├── pyproject.toml
│   └── agent_core/
│       ├── contracts/
│       │   ├── agent.py
│       │   ├── run.py
│       │   ├── runtime.py
│       │   ├── model.py
│       │   ├── capability.py
│       │   ├── workflow.py
│       │   ├── identity.py
│       │   ├── context.py
│       │   ├── events.py
│       │   └── waits.py
│       ├── runtime/
│       │   ├── kernel.py
│       │   ├── model_provider.py
│       │   ├── workflow_runtime.py
│       │   ├── sandbox_provider.py
│       │   └── transport.py
│       ├── runs/
│       ├── capabilities/
│       ├── governance/
│       ├── workflows/
│       ├── coordination/
│       ├── conversations/
│       ├── memory/
│       ├── knowledge/
│       ├── skills/
│       ├── registry/
│       ├── plugins/
│       ├── artifacts/
│       ├── evals/
│       ├── protocols/
│       │   ├── mcp/
│       │   ├── a2a/
│       │   └── ag_ui/
│       ├── observability/
│       └── persistence/
│
├── agent_integrations/
│   ├── langchain/
│   ├── langgraph/
│   ├── google_adk/
│   ├── openai_agents/
│   ├── pydantic_ai/
│   ├── deepseek_harness/
│   ├── litellm/
│   ├── mcp/
│   ├── a2a/
│   ├── ag_ui/
│   ├── otel/
│   └── sandboxes/
│
└── agent_testkit/
    ├── kernel_conformance/
    ├── model_conformance/
    ├── workflow_conformance/
    ├── gateway_conformance/
    ├── persistence_conformance/
    ├── protocol_conformance/
    └── fixtures/
```

### Lý do tách `agent_integrations`

Không lặp lại mô hình legacy, nơi một environment chứa đồng thời Google ADK, DeepSeek Harness SDK, LiteLLM, DSPy, OpenSandbox, OpenAI client và các dependency transitively xung đột.

`agent_core` phải boot/test mà **không cần cài bất kỳ runtime framework nào**.

## 4.2. Application layer

```text
apps/
└── cosa/
    ├── api/
    ├── composition/
    ├── conversations/
    ├── auth/
    ├── capabilities/
    ├── protocol_adapters/
    ├── runtime_selection/
    └── config/
```

`apps/cosa` là composition root của ứng dụng COSA, không phải reusable core.

## 4.3. Business and control-plane services

Giữ:

```text
services/
├── company/
│   ├── identity/
│   ├── operations/
│   ├── commercial/
│   └── finance-legal/
└── cosa/
    ├── control_plane/
    ├── runtime_registry/
    ├── scheduling/
    ├── budgets/
    └── artifacts/
```

Python Agent Core không được import TypeScript service code và không query trực tiếp schema nghiệp vụ.

---

# 5. Core runtime contracts

## 5.1. `ExecutionKernel`

```python
class ExecutionKernel(Protocol):
    async def run(self, request, spec, context) -> RunResult: ...
    async def resume(self, request, context) -> RunResult: ...
    async def cancel(self, run_id, reason=None) -> CancelResult: ...
    async def stream(self, request, spec, context) -> AsyncIterator[RuntimeEvent]: ...
```

Kernel **không được** trực tiếp query business DB, tự quyết approval, bypass `CapabilityGateway`, hoặc tự tạo `run_id` mới khi đã có canonical ID.

## 5.2. `ModelProvider`

```python
class ModelProvider(Protocol):
    async def generate(self, request: ModelRequest) -> ModelResponse: ...
    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelEvent]: ...
    async def capabilities(self, model_ref: str) -> ModelCapabilities: ...
```

`ModelCapabilities` mô tả: tool calling, parallel tool calls, structured output, streaming, reasoning, vision/audio, context window, usage và provider request id.

## 5.3. `WorkflowRuntime`

```python
class WorkflowRuntime(Protocol):
    async def start(...)
    async def resume(...)
    async def cancel(...)
    async def inspect(...)
```

Implementations:

```text
NativeWorkflowRuntime
LangGraphWorkflowRuntime
GoogleADKWorkflowRuntime
```

Canonical `WorkflowSpec` thuộc COSA.

## 5.4. `SandboxProvider`

```python
class SandboxProvider(Protocol):
    async def create(...)
    async def execute(...)
    async def upload(...)
    async def download(...)
    async def terminate(...)
```

Implementations: Local, Docker, OpenSandbox, Daytona, Modal, Remote.

## 5.5. Runtime binding

```text
COSA run_id             = canonical
LangGraph thread_id     = runtime binding
ADK session_id          = runtime binding
OpenAI SDK state/ref    = runtime binding
Harness session_id      = runtime binding
```

Một conversation có thể có nhiều run.

---

# 6. Runtime integrations

## 6.1. LangChain — primary model integration

Tạo `packages/agent_integrations/langchain/` với model provider, kernel, tool schema adapter, structured output và normalized events.

DeepSeek policy:

```text
deepseek-chat
  → normal agent
  → tool calling
  → structured output
  → streaming

deepseek-reasoner
  → planner/research/critic
  → no direct mutating capability execution
```

LangChain không sở hữu tool authorization, approval, idempotency, tenant isolation hay canonical checkpoint.

## 6.2. LangGraph — optional workflow runtime

Không đưa LangGraph Store/checkpointer thành canonical source of truth. Framework checkpoint chỉ là runtime implementation state.

Phải pass crash/restart, pending writes, exact invocation, approval freshness, version pinning, replay và fork lineage.

## 6.3. Google ADK

Phục hồi pattern tốt từ legacy ADK:

```text
ADK Tool
  ↓
CosaGovernedToolAdapter
  ↓
CapabilityGateway
```

và:

```text
ADK model
  ↓
CosaModelProviderAdapter
  ↓
COSA ModelProvider / LiteLLM
```

Tạo integration riêng, không phục hồi business objects cũ nguyên trạng.

## 6.4. OpenAI Agents SDK

Tạo SDK implementation thật trong optional package. Nếu giữ manual OpenAI-compatible loop thì rename thành `OpenAICompatibleChatKernel`.

## 6.5. DeepSeek Harness

Vì Harness còn developer preview và kiến trúc chính là TypeScript/Cordis, ưu tiên **out-of-process adapter**:

```text
COSA
  ↓ gRPC/HTTP/JSON-RPC/A2A
DeepSeek Harness Worker
```

Harvest: typed events, scoped plugin lifecycle, reversible registration, durable session facts, live interception events, plugin composition/profile bundles.

## 6.6. Hermes

Không dependency runtime. Harvest cross-session recall, procedural skill lifecycle, agent learning loop, progressive skill loading, subagent isolation, scheduled automation UX, multi-channel gateway và sandbox abstraction.

Learning loop:

```text
Experience → SkillCandidate → Evidence → Eval → Approval → Immutable SkillSpec → Publish
```

## 6.7. Paperclip

Không import vào Agent Core. Harvest vào `services/cosa`: Mission, Task, Assignment, Worker, Heartbeat, Lease, Schedule, Watchdog, RuntimeAdapter, Budget, Cost attribution, Artifact timeline.

---

# 7. Model Gateway

LiteLLM nên là model infrastructure layer:

```text
ExecutionKernel → ModelProvider → LiteLLM Gateway → DeepSeek/OpenAI/Gemini/Claude/Local
```

Centralize provider auth, routing, budgets, quotas, cost, fallback, circuit breaker, retry và rate limiting.

Không tạo nested retry chaos. Failure owner:

| Failure | Owner |
|---|---|
| provider HTTP/5xx | LiteLLM |
| tool validation | Agent Core |
| workflow retry | WorkflowRuntime |
| business retry | CapabilityGateway |
| whole-run retry | Control Plane |

---

# 8. Capability Gateway — sole side-effect authority

## 8.1. Canonical `ToolInvocation`

```python
class ToolInvocation(BaseModel):
    run_id: str
    tool_call_id: str
    checkpoint_ref: str | None
    tenant_id: str | None
    principal_id: str
    capability_id: str
    arguments: dict
    payload_hash: str
    target_snapshot: ExecutionTargetSnapshot
    idempotency_key: str | None
    runtime_ref: RuntimeInvocationRef | None
```

Runtime adapters chỉ tạo intent, không execute handler.

## 8.2. Execution pipeline

```text
resolve capability
→ validate schema
→ resolve execution target
→ exact invocation identity
→ readiness
→ fresh principal/tenant gate
→ durable governance accumulator
→ fresh policy observation
→ approval evidence validation
→ atomic idempotency claim
→ execute
→ persist result
→ audit/event
```

Required invariant:

```text
InvocationIdentity before approval
== InvocationIdentity after resume
== InvocationIdentity at side effect
```

---

# 9. Governance và Approval

## 9.1. Run-level current gate

Fresh/current, không monotonic: tenant active, principal active, membership, workspace access, safety switches.

## 9.2. Invocation-level accumulator

Monotonic theo `(run_id, tool_call_id)`. Observation mới không được làm policy accumulated yếu đi.

## 9.3. Resume flow bắt buộc

```text
submit approval decision
→ load exact invocation
→ fresh tenant/principal state
→ fresh execution target
→ load durable G_acc
→ fresh policy observation
→ G_acc' = G_acc ∧ observation
→ validate approval evidence against G_acc'
→ resume SAME invocation
```

Không dùng generic `{"approved": true}` làm authority.

---

# 10. Protocol architecture

## 10.1. MCP

MCP là tool/data transport, không phải authorization system:

```text
MCP Server → MCP Capability Adapter → CapabilityGateway → COSA Governance
```

MCP discovery convert thành `CapabilitySpec`; execution không bypass Gateway.

## 10.2. A2A

Dùng cho remote agent interoperability. Remote child authority phải attenuate:

```text
Authority(child) ⊆ Authority(parent)
```

## 10.3. AG-UI

Normalize runtime events thành common vocabulary: run lifecycle, text delta, model request, tool requested/waiting/started/completed, state snapshot/delta, artifact, error, completion.

Flutter/Web/Desktop consume cùng mapping; SSE có thể tiếp tục là transport ban đầu.

---

# 11. Plugin architecture

Plugin system hiện tại cần nâng lên registry có lifecycle.

## Trust tiers

- Tier 0: core built-in, in-process.
- Tier 1: signed internal plugin, pinned version.
- Tier 2: third-party isolated qua process/container/MCP/A2A/sandbox.

Plugin metadata: plugin id/version/hash/publisher/signature/required core version/capabilities/permissions/dependencies/trust tier/isolation/entrypoints/healthcheck.

Lifecycle:

```text
DISCOVERED → INSTALLED → VERIFIED → ENABLED → DEGRADED/DISABLED → RETIRED
```

---

# 12. Memory architecture

Memory không được là business truth.

Classes: WORKING, EPISODIC, SEMANTIC, PROCEDURAL, ORGANIZATIONAL.

Nếu memory và Company Service mâu thuẫn thì Company Service thắng.

Memory lifecycle:

```text
create → score → retrieve → reinforce → supersede → expire → archive
```

Promoted procedural memory có thể thành `SkillCandidate`, không tự thành published Skill.

---

# 13. Knowledge/RAG architecture

Knowledge tách:

```text
source → version → chunks → embeddings
```

Required: source versioning, content hash, ingestion provenance, embedding model/version, chunking strategy/version, authority class, tenant/scope, retire/rebuild.

---

# 14. Observability

Canonical telemetry = OpenTelemetry.

Required spans/events:

```text
agent.run
agent.model.request
agent.workflow.step
agent.capability.invoke
agent.governance.evaluate
agent.approval.wait
agent.memory.retrieve
agent.knowledge.search
agent.delegation
agent.sandbox.execute
```

Required attributes: run/conversation/tenant/application/spec/runtime/model/capability/tool_call/workflow/status/latency/tokens/cost.

Không export secrets, raw credentials, private chain-of-thought hoặc unrestricted business payload. Dùng redaction trước exporter.

---

# 15. Database target architecture

## 15.1. Schema ownership

```text
agent_core
agent_core_governance
agent_conversation
agent_registry
agent_memory
knowledge
control_plane
business schemas...
```

| Schema | Owner |
|---|---|
| `agent_core` | `packages/agent_core/runs` |
| `agent_core_governance` | `packages/agent_core/governance` |
| `agent_conversation` | `packages/agent_core/conversations` |
| `agent_registry` | `packages/agent_core/registry` |
| `agent_memory` | `packages/agent_core/memory` |
| `knowledge` | `packages/agent_core/knowledge` |
| `control_plane` | `services/cosa` |
| business schemas | `services/company` |

`agent_core` không có quyền SQL trực tiếp vào business schemas.

---

# 16. Database: `agent_core.runs`

Existing row chứa `company_id/workspace_id`, useful cho COSA nhưng làm core mang app semantics. Giữ compatibility columns ở migration đầu, nhưng thêm generic scope.

Target conceptual schema:

```sql
CREATE TABLE agent_core.runs (
    run_id              UUID PRIMARY KEY,
    application_id      TEXT NOT NULL,
    tenant_id           TEXT,
    scope_type          TEXT,
    scope_id            TEXT,
    principal_id        TEXT NOT NULL,
    conversation_id     UUID,
    parent_run_id       UUID,
    root_run_id         UUID,
    executable_kind     TEXT NOT NULL,
    executable_id       TEXT NOT NULL,
    executable_version  TEXT NOT NULL,
    definition_hash     TEXT NOT NULL,
    runtime_name        TEXT NOT NULL,
    status              TEXT NOT NULL,
    execution_mode      TEXT NOT NULL,
    correlation_id      TEXT,
    request_key         TEXT,
    input_payload       JSONB NOT NULL,
    model_policy        JSONB NOT NULL DEFAULT '{}',
    final_output        JSONB,
    usage               JSONB NOT NULL DEFAULT '{}',
    error_details       JSONB,
    created_at          TIMESTAMPTZ NOT NULL,
    updated_at          TIMESTAMPTZ NOT NULL,
    completed_at        TIMESTAMPTZ
);
```

Indexes: `(application_id, tenant_id, status, created_at DESC)`, `(conversation_id, created_at)`, `parent_run_id`, `correlation_id`.

Run deduplication và side-effect idempotency là hai bài toán khác nhau.

---

# 17. Database: runtime bindings/checkpoints

## `agent_core.run_runtime_bindings`

```sql
CREATE TABLE agent_core.run_runtime_bindings (
    run_id              UUID NOT NULL REFERENCES agent_core.runs(run_id),
    runtime_name        TEXT NOT NULL,
    runtime_version     TEXT,
    binding_kind        TEXT NOT NULL,
    external_id         TEXT,
    state_ref           TEXT,
    metadata            JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, runtime_name, binding_kind)
);
```

Examples: `langgraph/thread`, `google_adk/session`, `openai_agents/session`, `deepseek_harness/session`.

## Canonical checkpoint

`agent_core.run_checkpoints` chỉ chứa state thuộc COSA.

## Runtime checkpoint

```sql
CREATE TABLE agent_core.runtime_checkpoints (
    run_id              UUID NOT NULL,
    checkpoint_ref      UUID NOT NULL,
    runtime_name        TEXT NOT NULL,
    serializer          TEXT NOT NULL,
    serializer_version  TEXT,
    state_json          JSONB,
    state_blob_ref      TEXT,
    external_ref        TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, checkpoint_ref, runtime_name)
);
```

Framework state là implementation detail, không phải canonical state.

---

# 18. Database: event ledger

`agent_core.run_events` append-only.

Target fields:

```text
event_id UUIDv7
run_id
event_offset BIGINT
event_type
event_version
actor_type
actor_id
payload
correlation_id
causation_event_id
created_at
```

Rules: không update/delete normal operation, payload redacted, schema versioned, SSE replay từ durable ledger.

Indexes: `(run_id,event_offset)`, `(run_id,created_at)`, `(event_type,created_at)`, `correlation_id`.

---

# 19. Database: exact tool invocation

Hiện `tool_call_id` là PK độc lập. Target:

```sql
PRIMARY KEY (run_id, tool_call_id)
```

Conceptual table:

```sql
CREATE TABLE agent_core.run_tool_calls (
    run_id                  UUID NOT NULL,
    tool_call_id            TEXT NOT NULL,
    checkpoint_ref          UUID,
    capability_id           TEXT NOT NULL,
    capability_version      TEXT,
    capability_hash         TEXT,
    payload_hash            TEXT NOT NULL,
    input_payload           JSONB NOT NULL,
    execution_target_hash   TEXT,
    execution_target        JSONB NOT NULL,
    status                  TEXT NOT NULL,
    attempt_no              INTEGER NOT NULL DEFAULT 0,
    runtime_name            TEXT,
    runtime_tool_call_ref   TEXT,
    output_payload          JSONB,
    result_hash             TEXT,
    error_code              TEXT,
    error_message           TEXT,
    created_at              TIMESTAMPTZ NOT NULL,
    started_at              TIMESTAMPTZ,
    completed_at            TIMESTAMPTZ,
    PRIMARY KEY (run_id, tool_call_id)
);
```

---

# 20. Database: atomic idempotency

Non-unique index hiện tại không đủ. Tạo claim table để support idempotency vượt qua run boundary khi capability cần.

```sql
CREATE TABLE agent_core.idempotency_claims (
    claim_id            UUID PRIMARY KEY,
    tenant_id           TEXT,
    capability_id       TEXT NOT NULL,
    scope_kind          TEXT NOT NULL,
    scope_key_hash      TEXT NOT NULL,
    idempotency_key     TEXT NOT NULL,
    payload_hash        TEXT NOT NULL,
    run_id              UUID NOT NULL,
    tool_call_id        TEXT NOT NULL,
    status              TEXT NOT NULL,
    lease_owner         TEXT,
    lease_until         TIMESTAMPTZ,
    result_hash         TEXT,
    result_payload      JSONB,
    created_at          TIMESTAMPTZ NOT NULL,
    updated_at          TIMESTAMPTZ NOT NULL,
    UNIQUE (scope_kind, scope_key_hash, capability_id, idempotency_key)
);
```

`scope_kind`: RUN, TENANT, WORKSPACE, BUSINESS_ENTITY, GLOBAL.

Atomic claim dùng `INSERT ... ON CONFLICT ...`. Nếu conflict: cùng payload+completed trả kết quả cũ; running thì attach/wait; khác payload thì conflict; lease retryable hết hạn thì CAS takeover.

---

# 21. Database: Approval

Composite invocation FK:

```sql
FOREIGN KEY (run_id, tool_call_id)
REFERENCES agent_core.run_tool_calls(run_id, tool_call_id)
```

Target fields: approval id, exact invocation, checkpoint, requirement hash/content, status, requested/decided principals, reason, evidence ref, decision version, timestamps/expiry.

Atomic decision:

```sql
UPDATE agent_core.approvals
SET status = :decision,
    decided_by = :reviewer,
    decided_at = now(),
    decision_version = decision_version + 1
WHERE approval_id = :id
  AND status = 'pending'
  AND (expires_at IS NULL OR expires_at > now())
RETURNING *;
```

Không có row returned = stale/conflict/expired.

---

# 22. Database: governance

Giữ schema `agent_core_governance` để tránh rename không cần thiết.

Migration 002 hiện còn giả định repo chưa có runs/tool tables; migration mới phải thêm FK.

`spec_resolution_manifest_entries` thêm FK run và có thể mở rộng `spec_kind`: agent/workflow/skill/plugin/capability.

`invocation_governance_state` và history dùng composite FK `(run_id,tool_call_id)`.

Governance history fields nên có: observation id, decision, requirement, source, policy ref/version, observed principal-state hash, observed target hash, timestamp.

Approval evidence target:

```text
evidence_id
run_id
tool_call_id
approval_id
requirement_hash
approver_principal
scope
decision
decided_at
valid_until
evidence_payload
```

---

# 23. Database: conversations

Tạo schema `agent_conversation`.

## `conversations`

```text
conversation_id UUID PK
application_id
tenant_id
scope_type
scope_id
created_by
title
status
metadata
created_at
updated_at
archived_at
```

## `messages`

```text
message_id UUID PK
conversation_id FK
sequence_no
role
author_type
author_id
content_parts JSONB
run_id nullable
reply_to_message_id
created_at
```

`UNIQUE(conversation_id, sequence_no)`.

Không lưu private chain-of-thought. `content_parts` có thể chứa text/image/file/artifact/tool_summary/citation.

Bỏ production globals `_conversations`, `_messages`, `_pending_runs`.

---

# 24. Database: model calls

Tạo `agent_core.run_model_calls` phục vụ cost/reliability/debug/conformance:

```text
model_call_id
run_id
step_ref
runtime_name
provider
model
provider_request_id
request_hash
response_hash
status
error_code
input_tokens
output_tokens
cache_tokens
reasoning_tokens
cost_amount
cost_currency
started_at
completed_at
latency_ms
metadata
```

Không bắt buộc persist raw prompt/response. Nếu cần debug raw payload: opt-in, encrypt, redact, TTL và tenant policy.

---

# 25. Database: registry/spec publication

Tạo schema `agent_registry`.

## `published_specs`

```text
spec_kind
spec_id
version
definition_hash
content JSONB
status
publisher
created_at
published_at
retired_at

PRIMARY KEY(spec_kind, spec_id, version)
UNIQUE(spec_kind, spec_id, definition_hash)
```

`spec_kind`: agent/workflow/skill/capability/plugin.

Published version immutable; thay đổi phải tạo version mới.

Optional `spec_channels`: stable/beta/canary. Run luôn pin version/hash tại start.

## Skill candidate lifecycle

`agent_registry.skill_candidates` chứa candidate, parent run, proposed spec, evidence, eval suite/score, status, reviewer/timestamps.

Flow: CANDIDATE → EVALUATED → APPROVED → PUBLISHED.

---

# 26. Database: memory v2

Memory hiện scope chủ yếu bằng `workspace_id`. Reusable core cần generic tenant/scope.

Target `agent_memory.memories`:

```text
memory_id UUID PK
application_id
tenant_id
scope_type
scope_id
agent_key
subject_type
subject_id
kind
content
content_hash
importance
source_run_id
source_event_id
provenance JSONB
status
valid_from
valid_until
supersedes_memory_id
tags
metadata
created_at
updated_at
```

Status: ACTIVE, SUPERSEDED, EXPIRED, RETRACTED, ARCHIVED.

Tách `agent_memory.memory_embeddings`:

```text
memory_id
embedding_model
embedding_version
dimensions
embedding
created_at
UNIQUE(memory_id, embedding_model, embedding_version)
```

---

# 27. Database: knowledge v2

## `knowledge.sources`

Fields: source id, application/tenant/scope, source type/URI/title, authority class, status, metadata, timestamps.

Authority class: REFERENCE, POLICY, BUSINESS_SNAPSHOT, USER_CONTENT, EXTERNAL. BUSINESS_SNAPSHOT không thay thế live business query.

## `knowledge.source_versions`

Fields: source version id, source id, version, content hash, ingestion run, parser name/version, created timestamp.

## `knowledge.chunks`

Fields: chunk id, source version, chunk index, content/hash, chunker name/version, metadata, created timestamp.

## `knowledge.chunk_embeddings`

Fields: chunk id, embedding model/version, dimensions, embedding, created timestamp; unique theo chunk+model+version.

Vector strategy: ban đầu chốt 1 canonical embedding dimension per deployment. Nếu multi-dimension thì tạo partial/expression HNSW index theo model/dimension.

---

# 28. Database: control plane

Schema do `services/cosa` sở hữu.

Core tables:

```text
control_plane.missions
control_plane.tasks
control_plane.assignments
control_plane.workers
control_plane.runtime_slots
control_plane.schedules
control_plane.cost_ledger
```

`missions`: tenant, creator, goal, status, priority, budget, deadline, root run.

`tasks`: mission, parent task, description, status, priority, requirements.

`assignments`: task, worker, status, lease, attempt, timestamps; atomic checkout.

`workers`: runtime kind, endpoint, capabilities, health, concurrency, trust, heartbeat.

`runtime_slots`: worker/runtime/state/current run/lease.

`cost_ledger`: tenant/mission/run/provider/model/tokens/cost/time.

---

# 29. Tenant isolation và RLS

API resolve:

```text
Bearer token → Authenticated Principal → TenantScope
```

`X-Workspace-Id` / `X-Company-Id` chỉ là requested scope hint.

PostgreSQL RLS dùng làm defense-in-depth sau khi repositories đã tenant-aware. Không bật RLS nửa vời.

---

# 30. Identifier policy

IDs mới nên application-side UUIDv7: run/event/checkpoint/approval/mission/task/message.

Không cần migration tức thì cho toàn bộ legacy VARCHAR IDs.

External SDK IDs không làm primary key; lưu trong runtime binding/provider request ref.

---

# 31. Migration plan

Không rewrite schema một lần.

## DB-0 — Baseline freeze

- backup;
- checksum migrations;
- schema fingerprint;
- fresh bootstrap Postgres;
- verify 001→003;
- rollback/runbook.

## DB-1 — Harden durable substrate

`004_harden_exact_invocation_and_approval.sql`

- composite invocation identity;
- approval composite FK;
- CAS fields;
- status checks;
- tenant indexes;
- fix stale governance assumptions.

## DB-2 — Atomic idempotency + runtime bindings

`005_runtime_bindings_and_idempotency.sql`

Tạo runtime bindings, runtime checkpoints, idempotency claims, model calls.

## DB-3 — Conversation durability

`006_conversation_substrate.sql`: conversations/messages.

## DB-4 — Registry/spec publication

`007_agent_registry.sql`.

## DB-5 — Memory v2

`008_memory_v2.sql`: additive generic scope/provenance/lifecycle, backfill từ workspace.

## DB-6 — Knowledge v2

`009_knowledge_versioning_and_embeddings.sql`.

## DB-7 — Governance integrity

`010_governance_integrity.sql`: FKs, exact evidence binding, policy provenance.

## DB-8 — RLS

`011_tenant_rls.sql` chỉ activate sau tenant-aware repositories.

### Compatibility strategy

Mỗi migration: additive → dual read/write nếu cần → backfill idempotent → validate → cutover → drop legacy sau.

---

# 32. Persistence repository redesign

Request-facing repository/service phải nhận `TenantScope`:

```python
@dataclass(frozen=True)
class TenantScope:
    application_id: str
    tenant_id: str | None
    scope_type: str | None
    scope_id: str | None
```

Thay request-facing `get_run(run_id)` bằng `get_run(scope, run_id)`.

---

# 33. Conversation + run relationship

```text
Conversation
 ├── message
 ├── message → Run A → model calls/tool calls/checkpoints
 ├── message → Run B
 └── message
```

Không dùng conversation làm run identity.

---

# 34. Workflow redesign

Giữ `WorkflowSpec` canonical.

Native engine phải sửa parallel semantics: mỗi wave dùng immutable snapshot, mỗi branch trả updates riêng, reducer merge sau barrier. Không truyền shared mutable state cho parallel tasks.

Chạy conformance cho Native/LangGraph/Google ADK. Adopt runtime nếu custom code removed + failure semantics improved + tests/ops tốt hơn framework coupling + duplicate persistence + serialization risk.

---

# 35. Runtime selection

`AgentSpec.model_policy` không hard-code framework. Runtime policy nằm ở application/deployment composition.

```yaml
runtime:
  preferred: langchain
  allowed: [langchain, openai_agents, google_adk]
model:
  preferred: deepseek-chat
  fallbacks: [openai:*, gemini:*]
```

Published AgentSpec có thể declare requirements (tool calling, structured output, parallel tools...). Resolver chọn runtime/model phù hợp.

---

# 36. Error taxonomy

Chuẩn hóa typed errors:

```text
MODEL_PROVIDER_ERROR
MODEL_TIMEOUT
MODEL_RATE_LIMIT
MODEL_INVALID_RESPONSE
CONTEXT_LIMIT_EXCEEDED
TOOL_SCHEMA_ERROR
CAPABILITY_NOT_FOUND
CAPABILITY_NOT_READY
CAPABILITY_DENIED
APPROVAL_REQUIRED
APPROVAL_EXPIRED
TARGET_DRIFT
IDEMPOTENCY_CONFLICT
WORKFLOW_STEP_FAILED
WORKFLOW_DEADLOCK
RUNTIME_CHECKPOINT_ERROR
TENANT_UNAUTHORIZED
PRINCIPAL_REVOKED
```

Không parse exception string để điều khiển workflow.

---

# 37. Events taxonomy

Canonical events versioned:

```text
run.created.v1
run.started.v1
run.status_changed.v1
model.request_started.v1
model.request_completed.v1
model.request_failed.v1
tool.requested.v1
tool.governance_observed.v1
tool.waiting_approval.v1
tool.execution_started.v1
tool.execution_completed.v1
tool.execution_failed.v1
approval.requested.v1
approval.decided.v1
approval.expired.v1
workflow.step_started.v1
workflow.step_completed.v1
workflow.step_failed.v1
memory.retrieved.v1
memory.created.v1
artifact.created.v1
```

AG-UI mapping nằm ngoài canonical DB model.

---

# 38. Event streaming

Server flow:

```text
client cursor
→ query durable run_events after cursor
→ replay
→ subscribe live notifier
→ stream new events
```

Postgres LISTEN/NOTIFY có thể làm wake-up, nhưng DB là source of truth. Không dùng queue in-memory làm history.

---

# 39. Control-plane execution model

Paperclip-inspired:

```text
Trigger → Mission → Tasks → Atomic assignment → Worker lease → RunRequest
→ Agent runtime → RunResult/artifacts/usage → Task/Mission state
```

Worker mất heartbeat → lease hết hạn → task retryable → worker mới claim. Side effects vẫn protected bởi Gateway idempotency.

---

# 40. Sandbox strategy

Coding/bash/file tools không chạy trực tiếp trong Agent API production process.

| Capability | Default |
|---|---|
| pure read internal RPC | no sandbox |
| Python analysis | sandbox |
| shell | sandbox mandatory |
| arbitrary package install | sandbox mandatory |
| file mutation | scoped sandbox |
| browser automation | isolated worker |
| untrusted plugin | isolated worker |

---

# 41. Security

Production boot fail nếu thiếu JWT signing config, DB credentials, model gateway credentials hoặc encryption key.

Plugin chỉ nhận credential reference, không raw global secrets.

Capability grants scope theo tenant/principal/capability/target/expiry.

Mutating/financial/external capability phải audit request identity, policy observation, approval evidence, idempotency claim, target snapshot và result.

---

# 42. Python packaging

Khuyến nghị `pyproject.toml` + `uv` workspace.

Packages:

```text
agent-core
agent-integration-langchain
agent-integration-google-adk
agent-integration-openai-agents
agent-integration-pydantic-ai
agent-testkit
```

Core dependencies tối thiểu; không có Google ADK/OpenAI Agents/LangGraph/Harness trong base install.

---

# 43. Deployment topology

Minimum:

```text
postgres
company-service :4000
cosa-control    :4001
agent-api       :8000
model-gateway   :4002
flutter/web
```

Primary Agent API image cài agent-core + langchain + litellm + otel integrations.

Optional workers: ADK, OpenAI agent, DeepSeek Harness, coding sandbox. Không bắt main API image cài mọi framework.

---

# 44. Configuration layering

```text
core defaults
→ deployment config
→ application config
→ tenant policy
→ agent spec
→ limited run override
```

Secrets không nằm trong AgentSpec.

---

# 45. CI/CD target

Core CI: tests/agent_core, typing/lint, migration bootstrap, import-boundary checks, không cài external runtimes.

Integration matrix: langchain, google_adk, openai_agents, pydantic_ai, deepseek_harness — mỗi job chỉ cài integration cần test.

DB CI: fresh Postgres → all migrations → schema assertions → repository integration tests → migration checksum immutability.

---

# 46. Conformance suite

Kernel: response, streaming, structured output, single/parallel tool, cancellation, provider failure, timeout, resume.

Identity: exact `(run_id,tool_call_id)`, checkpoint, target drift.

Approval: approve/deny/expiry/principal revoked/policy stricter before resume.

Persistence: process A pause → kill → process B resume → same invocation → no duplicate side effect.

Multi-worker: two workers claim same idempotency → exactly one side effect.

Protocol: MCP mapping, A2A authority attenuation, AG-UI event mapping.

---

# 47. Evaluation strategy

Mỗi runtime chạy cùng dataset và đo: task success, tool correctness, policy compliance, approval correctness, recovery, latency, token/cost, runtime errors, adapter LOC, dependency count, cold start, memory usage.

Không chọn framework bằng popularity.

---

# 48. DSPy role

DSPy chỉ offline:

```text
dataset → optimizer → candidate spec/instructions → eval → gate → immutable new version
```

Không mutate production prompt trực tiếp.

---

# 49. File-level refactoring plan

## Giữ và harden

```text
packages/agent_core/contracts/*
packages/agent_core/runs/*
packages/agent_core/governance/*
packages/agent_core/capabilities/*
packages/agent_core/memory/*
packages/agent_core/knowledge/*
packages/agent_core/skills/*
packages/agent_core/evals/*
```

## Refactor

`packages/agent_core/kernel/openai_agents_kernel.py`: tách manual loop; rename nếu giữ; move OpenAI-specific code sang integration; thêm LangChain primary adapter.

`capabilities/gateway.py`: sole authority, durable governance injection, atomic idempotency, exact ToolInvocation.

`approval_service.py`: fresh-governance conjunction, exact invocation, target drift, evidence validation.

`workflows/engine.py`: behind WorkflowRuntime; reducer/snapshot parallel semantics.

`plugins/*`: persistent registry, lifecycle, trust tier, signing, isolation.

`apps/cosa/composition/*`: inject TenantResolver, ModelProvider, ExecutionKernel, WorkflowRuntime, Gateway, repositories, event publisher. Không hidden production mock.

`apps/cosa/api/*`: authenticated TenantContext, no global state, durable conversation, durable replay, typed errors.

`services/cosa/*`: thêm control-plane primitives.

---

# 50. Legacy salvage plan

`legacy/*` read-only; không phục hồi nguyên application.

| Legacy asset | Action |
|---|---|
| Google ADK | port adapter patterns |
| LiteLLM | restore model gateway concepts |
| DSPy | offline optimization |
| OpenSandbox | SandboxProvider adapter |
| DeepSeek Harness adapter | rewrite under integration boundary |
| old mission/task | compare với new control plane |
| old runtime session | lessons → runtime bindings |

---

# 51. Documentation/ADR changes

Tạo `ADR-AGENT-CORE-FRAMEWORK-NEUTRAL.md` với decision: `ExecutionKernel Protocol = canonical`, framework runtime = adapter.

Supersede phần docs tuyên bố OpenAI Agents SDK là architecture owner, không xóa lịch sử.

Tạo thêm:

```text
ADR-MODEL-GATEWAY.md
ADR-RUNTIME-ADAPTERS.md
ADR-PROTOCOLS-MCP-A2A-AGUI.md
ADR-DURABLE-IDENTITY.md
ADR-DATABASE-SCHEMA-OWNERSHIP.md
ADR-PLUGIN-TRUST-AND-ISOLATION.md
```

---

# 52. Implementation milestones

## Milestone 0 — Architecture freeze

Approve ADR, freeze ownership, boundary tests, không thêm framework dependency vào core.

## Milestone 1 — Canonical execution path closure

Framework-neutral interfaces, LangChain+DeepSeek primary adapter, sole Gateway, exact invocation, typed errors, authenticated tenant.

## Milestone 2 — Database hardening

Composite identity, atomic idempotency, approval CAS, runtime bindings, model calls, durable conversations, governance FKs.

## Milestone 3 — Protocol layer

MCP, A2A, AG-UI mapping, OTel.

## Milestone 4 — Control plane

Missions/tasks/workers/heartbeat/lease/schedules/budget/cost.

## Milestone 5 — Knowledge/Memory/Skills v2

Generic scope, provenance, knowledge versioning, separate embeddings, skill candidate/eval/publish.

## Milestone 6 — Multi-runtime conformance

OpenAI, ADK, PydanticAI, Harness remote, LangGraph workflow spike.

## Milestone 7 — Plugin/sandbox hardening

Trust tiers, signing, isolation, sandbox providers.

---

# 53. PR sequence đề xuất

```text
PR-01  ADR framework-neutral core + boundary tests
PR-02  runtime contracts + normalized events
PR-03  LangChain/DeepSeek ModelProvider
PR-04  LangChainKernel minimal read-only vertical slice
PR-05  ToolInvocation + Gateway sole authority
PR-06  exact invocation DB migration
PR-07  idempotency claim service
PR-08  approval CAS + fresh governance resume
PR-09  authenticated TenantScope in Agent API
PR-10  durable conversations/messages
PR-11  durable SSE replay
PR-12  runtime bindings/model call ledger
PR-13  LiteLLM gateway integration
PR-14  MCP capability adapter
PR-15  A2A agent transport
PR-16  AG-UI event adapter
PR-17  OTel semantic tracing
PR-18  control-plane mission/task/worker
PR-19  memory v2
PR-20  knowledge v2
PR-21  skill learning/publish pipeline
PR-22  Google ADK adapter
PR-23  OpenAI Agents SDK adapter
PR-24  PydanticAI conformance spike
PR-25  LangGraph workflow conformance spike
PR-26  DeepSeek Harness remote worker
PR-27  plugin trust/isolation
PR-28  legacy dependency cleanup
PR-29  deployment/CI canonical cutover
```

Không gộp tất cả vào mega-PR.

---

# 54. Definition of Done cho reusable core

Agent Core chỉ được xem là reusable khi có ít nhất **hai application composition độc lập** chạy cùng package mà không fork core, ví dụ COSA Startup OS và Developer Agent.

Cả hai share Run substrate, Gateway, Governance, Runtime contracts, Memory contracts, Protocol contracts; nhưng có different capabilities, tenant resolver, UI, workflows và runtime policy.

---

# 55. End-to-end acceptance scenario bắt buộc

```text
1. User Flutter đăng nhập.
2. API resolve Principal + TenantScope.
3. Tạo conversation/message durable.
4. Tạo Run với immutable AgentSpec identity.
5. Runtime resolver chọn LangChainKernel + DeepSeek.
6. Model phát sinh mutating tool call.
7. ToolInvocation giữ exact run/tool identity.
8. CapabilityGateway: readiness + fresh gate + governance + idempotency.
9. Policy yêu cầu approval.
10. Persist checkpoint + invocation + approval + event.
11. Process A bị kill.
12. Process B nhận approval.
13. Fresh tenant/principal/target/policy evaluate lại.
14. Same exact invocation resume.
15. Atomic idempotency claim.
16. Side effect xảy ra đúng một lần.
17. Durable run event được ghi.
18. Flutter reconnect bằng Last-Event-ID.
19. Server replay từ PostgreSQL.
20. Run completed.
21. OTel trace nối model → tool → approval → RPC.
```

Chạy lại với hai replicas cạnh tranh. **Pass condition: đúng một business side effect.**

---

# 56. Anti-patterns bị cấm

```text
❌ Framework SDK object làm canonical domain model
❌ LangGraph thread_id làm run_id
❌ ADK session làm conversation
❌ MCP tool execute bypass Gateway
❌ A2A child inherit toàn quyền parent
❌ business DB query trực tiếp từ agent_core
❌ in-memory approval/resume production path
❌ tool_call_id regenerate giữa runtime và gateway
❌ non-atomic idempotency check-then-act
❌ model error converted to successful assistant content
❌ plugin third-party arbitrary import vào main process
❌ every framework installed in one production image
❌ memory treated as authoritative business state
❌ published spec edited in place
❌ private chain-of-thought persisted/logged
```

---

# 57. Target technology stack

Core Python: Python 3.12+, Pydantic, PostgreSQL, psycopg/asyncpg abstraction, OpenTelemetry API, JSON Schema.

Primary runtime: LangChain + `langchain-deepseek` + DeepSeek.

Model infrastructure: LiteLLM.

Optional: LangGraph, Google ADK, OpenAI Agents SDK, PydanticAI, DeepSeek Harness remote/SDK.

Protocols: MCP, A2A, AG-UI, OpenTelemetry.

Business services: Encore.ts, TypeScript, Drizzle.

UI: Flutter.

Không có lý do kiến trúc đủ mạnh để rewrite toàn hệ thống sang TypeScript.

---

# 58. Database checklist trước production

- [ ] exact `(run_id, tool_call_id)` DB constraint;
- [ ] idempotency unique atomic claim;
- [ ] approval CAS;
- [ ] governance FKs;
- [ ] tenant-aware repositories;
- [ ] conversation/message durable;
- [ ] SSE durable replay;
- [ ] runtime binding table;
- [ ] model call usage ledger;
- [ ] no raw CoT;
- [ ] redaction policy;
- [ ] migration checksums;
- [ ] fresh-bootstrap CI;
- [ ] backup/restore tested;
- [ ] failover/restart test;
- [ ] RLS decision documented;
- [ ] retention policy;
- [ ] vector index strategy;
- [ ] append-only event retention/archive policy.

---

# 59. Operational retention

| Data | Retention |
|---|---|
| run events | 90–365 days hot, archive later |
| audit/approval | compliance policy, thường dài hơn |
| raw model debug payload | disabled hoặc short TTL |
| usage/cost | long-term aggregate |
| checkpoints | active run + configured history |
| transient runtime blobs | terminal run + safety window |
| memories | lifecycle policy |
| knowledge versions | source lifecycle |
| traces | ngắn hơn audit ledger |

Audit ledger và telemetry không phải một thứ.

---

# 60. Performance considerations

Chỉ partition khi có evidence. Future candidates: `run_events` và `model_calls` theo tháng; không partition sớm runs/approvals.

Python/Encore dùng pool riêng; không connection per token/event.

Token deltas có thể stream live mà không persist từng token; durable ledger nên lưu semantic chunks/final messages/events quan trọng.

---

# 61. Disaster recovery

Minimum: Postgres PITR, daily backup, migration checksum archive, artifact backup, runtime-state rebuild rules.

Framework runtime state classification:

```text
REQUIRED_FOR_RESUME
RECONSTRUCTABLE
EPHEMERAL
```

Không backup mọi transient object vô hạn.

---

# 62. Final architectural position

COSA nên trở thành:

> **Một reusable agent operating substrate có protocol/invariant do COSA sở hữu, thay vì một application được xây “bên trong” một agent framework.**

Công nghệ bên ngoài dùng theo thế mạnh:

```text
LangChain        → model/tool integration
LangGraph / ADK  → workflow runtime candidates
OpenAI Agents    → OpenAI-native runtime
DeepSeek Harness → composable plugin/session patterns + experimental runtime
Hermes           → memory/skill/learning UX patterns
Paperclip        → control-plane operational patterns
LiteLLM          → model infrastructure
MCP              → tool/data interoperability
A2A              → agent interoperability
AG-UI            → UI interoperability
OpenTelemetry    → observability interoperability
DSPy             → offline optimization
```

COSA sở hữu identity, run, checkpoint, event, capability, governance, approval, idempotency, published spec, memory semantics và business authority boundary.

---

# 63. Quyết định triển khai ưu tiên

Nếu chỉ được làm 5 việc tiếp theo:

1. **ADR + package boundary:** framework-neutral Agent Core.
2. **LangChain/DeepSeek primary vertical slice:** bỏ production mock/manual ambiguity.
3. **CapabilityGateway closure:** exact identity + governance + approval + atomic idempotency.
4. **Database durability closure:** conversation + runtime bindings + SSE replay.
5. **Conformance testkit:** runtime tương lai phải chứng minh compatibility trước khi adopt.

Sau 5 bước này mới mở rộng ADK/OpenAI/LangGraph/Harness.

---

# Appendix A — Mapping hiện tại → target

| Hiện tại | Target |
|---|---|
| `contracts/kernel.py` | giữ, mở rộng framework-neutral |
| `kernel/openai_agents_kernel.py` | move/rename; optional integration |
| `workflows/engine.py` | `NativeWorkflowRuntime` |
| `capabilities/gateway.py` | sole execution authority |
| `governance/*` | durable canonical authority |
| `runs/*` | canonical durable run substrate |
| `plugins/manifest.py` | plugin registry/lifecycle v2 |
| `skills/*` | skill publish/learning pipeline |
| `memory/*` | generic scoped memory v2 |
| `knowledge/*` | versioned knowledge/embedding v2 |
| `apps/cosa/api` | authenticated, durable API |
| `apps/cosa/composition` | composition root / DI |
| `services/company` | business truth owner |
| `services/cosa` | control plane |
| legacy ADK | salvage adapter patterns |
| legacy LiteLLM | restore model gateway concepts |
| legacy DSPy | offline optimization |
| legacy OpenSandbox | SandboxProvider adapter |
| legacy Harness adapter | rewrite as isolated integration |

---

# Appendix B — Proposed migration filenames

```text
004_harden_exact_invocation_and_approval.sql
005_runtime_bindings_and_idempotency.sql
006_conversation_substrate.sql
007_agent_registry.sql
008_memory_v2.sql
009_knowledge_versioning_and_embeddings.sql
010_governance_integrity.sql
011_tenant_rls.sql
```

---

# Appendix C — Architecture decision summary

```text
Core framework-neutral?                 YES
LangChain in core?                      NO
LangChain primary integration?          YES
LangGraph canonical workflow?           NOT YET
Google ADK canonical runtime?            NO
Google ADK adapter?                      YES
OpenAI SDK canonical runtime?            NO
OpenAI SDK adapter?                      YES
DeepSeek Harness in-process canonical?   NO
Harness remote adapter?                  EXPERIMENTAL
Hermes dependency?                       NO
Harvest Hermes patterns?                 YES
Paperclip dependency?                    NO
Harvest Paperclip control plane?         YES
LiteLLM central gateway?                 YES
MCP support?                             YES
A2A support?                             YES
AG-UI alignment?                         YES
OTel canonical telemetry?                YES
DSPy runtime dependency?                 NO
DSPy offline optimizer?                  YES
```

---

# Appendix D — Evidence base trong repository

Tài liệu được xây từ audit trực tiếp các phần:

```text
docs/architecture/COSA_CANONICAL_OWNERSHIP_MAP.md
docs/architecture/langgraph_spike_results.md
docs/architecture/adr/ADR-LANGGRAPH-adoption-decision.md
docs/agent-platform/ADK_INTEGRATION.md
packages/agent_core/contracts/*
packages/agent_core/kernel/*
packages/agent_core/capabilities/*
packages/agent_core/governance/*
packages/agent_core/runs/*
packages/agent_core/workflows/*
packages/agent_core/memory/*
packages/agent_core/knowledge/*
packages/agent_core/skills/*
packages/agent_core/plugins/*
packages/agent_core/migrations/001_canonical_agent_core_schema.sql
packages/agent_core/migrations/002_governance_temporal_model.sql
packages/agent_core/migrations/003_agent_memory_and_knowledge.sql
apps/cosa/*
services/company/*
services/cosa/*
legacy/backend/requirements.txt
legacy/agent_runtime/*
legacy/agent_runtime_archive/*
```

External prior art: LangChain/LangGraph, Google ADK, OpenAI Agents SDK, DeepSeek Harness/Cordis, Hermes Agent, Paperclip, LiteLLM, MCP, A2A, AG-UI, OpenTelemetry GenAI, DSPy, PydanticAI.

---

**Recommended document authority after approval:**

```text
Approved ADRs
    >
COSA Agent Core Restructuring Blueprint
    >
Application-specific architecture docs
    >
Current implementation details
    >
External framework behavior
```


---

# 64. Blueprint v2 — thống nhất sau audit `awesome-llm-apps`

> Phần này **supersede** các điểm chưa đầy đủ của blueprint v1 khi có xung đột. Các invariant về run identity, CapabilityGateway, governance, durable event history và framework-neutral core ở phần trước vẫn giữ nguyên.

## 64.1. Kết luận nền tảng cuối cùng

COSA không nên trở thành một “agent framework mới” cạnh tranh với LangChain/ADK/OpenAI Agents SDK. COSA phải là **Agent Platform Core + Application Platform** sở hữu business semantics, còn framework bên ngoài là execution adapters.

Kiến trúc thống nhất:

```text
COSA Applications
  ├── Startup OS
  ├── Sales / CRM
  ├── Marketing
  ├── Finance / Legal
  ├── Developer Agent
  └── vertical SaaS khác
          │
          ▼
Application Composition
  ├── auth / tenant / principal
  ├── conversation
  ├── UI / AG-UI mapping
  └── application capabilities
          │
          ▼
COSA Agent Platform Core
  ├── Contracts + Registry
  ├── Execution + Durable Runs
  ├── Workflow Patterns
  ├── Capability Gateway
  ├── Governance / Approval / Idempotency
  ├── Memory / Knowledge
  ├── Skills / Evals / Optimization Lab
  ├── Control Plane / Watch / Signal / Delivery
  ├── Artifact System
  ├── Protocols: MCP / A2A / AG-UI
  └── Observability
          │
          ├──────── runtime adapters ────────┐
          ▼                                  ▼
   LangChain/LangGraph                 Google ADK
   OpenAI Agents SDK                   PydanticAI spike
   DeepSeek Harness adapter            Remote workers
          │
          ▼
      Model Gateway
  LiteLLM / provider adapters
          │
  DeepSeek / Gemini / OpenAI / others
```

### Vai trò công nghệ cuối cùng

| Thành phần | Trạng thái | Vai trò trong COSA |
|---|---|---|
| Python | **Canonical backend language** | Agent Core, orchestration, AI ecosystem |
| FastAPI | **ADOPT** | API/SSE/control endpoints |
| Pydantic | **ADOPT** | Canonical contracts/spec schemas |
| PostgreSQL | **ADOPT** | Durable source of truth |
| pgvector | **ADOPT where justified** | embeddings/search, không thay business DB |
| Redis | **OPTIONAL infra** | ephemeral cache/locks/pubsub; không canonical truth |
| LangChain | **ADOPT** | model/tool/provider integration utilities |
| LangGraph | **PRIMARY workflow candidate** | durable graph runtime sau conformance; không sở hữu core semantics |
| Google ADK | **ADAPTER** | Gemini/Google-native teams/workflows; self-improving lab reference |
| OpenAI Agents SDK | **ADAPTER** | OpenAI-native handoff/realtime/tooling |
| DeepSeek Harness | **HARVEST + adapter** | DeepSeek-specific runtime/session/event patterns |
| Hermes | **HARVEST** | skills, learning, sandbox/session UX |
| Paperclip | **HARVEST** | control-plane: mission/task/worker/lease/budget |
| awesome-llm-apps | **HARVEST CORPUS** | recipes, skills, eval patterns, always-on, MCP, RAG use cases |
| LiteLLM | **MODEL GATEWAY** | routing/fallback/cost/provider abstraction |
| MCP | **STANDARD** | external tools/data transport, behind CapabilityGateway |
| A2A | **STANDARD** | external agent interoperability |
| AG-UI | **ALIGN** | normalized agent-to-UI events |
| OpenTelemetry | **STANDARD** | trace/metric/log correlation |
| DSPy | **OFFLINE LAB** | prompt/spec optimization, not online authority |

## 64.2. Quy tắc “framework-neutral nhưng opinionated”

Framework-neutral không có nghĩa là mọi thứ đều abstract vô hạn. COSA phải opinionated ở các điểm sau:

1. `run_id` và `tool_call_id` do COSA sở hữu.
2. mọi side effect đi qua `CapabilityGateway`.
3. published specs immutable.
4. database là durable truth; framework checkpoint chỉ là runtime state.
5. runtime/model error là typed error.
6. authorization không giao cho prompt/model.
7. deterministic work ưu tiên deterministic code.
8. agent reasoning chỉ dùng khi thực sự cần reasoning.
9. mọi feature production phải có docs, tests, telemetry và extension contract.
10. application code không import trực tiếp implementation internals của runtime adapter.

---

# 65. Cấu trúc repository đích

Đề xuất chuẩn hóa monorepo như sau:

```text
javis-saas/
├── apps/
│   ├── cosa_api/
│   ├── cosa_worker/
│   ├── cosa_scheduler/
│   └── cosa_flutter/
│
├── packages/
│   ├── agent_core/
│   │   ├── README.md
│   │   ├── contracts/
│   │   ├── identity/
│   │   ├── registry/
│   │   ├── runs/
│   │   ├── events/
│   │   ├── capabilities/
│   │   ├── governance/
│   │   ├── approvals/
│   │   ├── idempotency/
│   │   ├── workflows/
│   │   ├── coordination/
│   │   ├── memory/
│   │   ├── knowledge/
│   │   ├── skills/
│   │   ├── evals/
│   │   ├── artifacts/
│   │   ├── control_plane/
│   │   ├── protocols/
│   │   ├── observability/
│   │   └── errors/
│   │
│   ├── agent_integrations/
│   │   ├── langchain/
│   │   ├── langgraph/
│   │   ├── google_adk/
│   │   ├── openai_agents/
│   │   ├── deepseek/
│   │   ├── litellm/
│   │   ├── mcp/
│   │   ├── a2a/
│   │   ├── ag_ui/
│   │   └── sandbox/
│   │
│   ├── agent_recipes/
│   │   ├── README.md
│   │   ├── patterns/
│   │   ├── startup/
│   │   ├── sales/
│   │   ├── marketing/
│   │   ├── finance/
│   │   └── developer/
│   │
│   └── shared/
│
├── services/
│   ├── company/
│   └── cosa/
│
├── migrations/
├── docs/
│   ├── architecture/
│   ├── features/
│   ├── integrations/
│   ├── recipes/
│   ├── operations/
│   ├── development/
│   └── adr/
│
└── tests/
    ├── conformance/
    ├── integration/
    ├── e2e/
    └── fixtures/
```

### Dependency direction bắt buộc

```text
apps
  ↓
application services
  ↓
agent_core contracts/services
  ↑
agent_integrations implement protocols

agent_core  X→ framework SDK
agent_core  X→ app business tables directly
runtime adapter X→ bypass CapabilityGateway
```

`agent_recipes` chỉ tham chiếu public contracts/specs; recipe không được trở thành authorization boundary.

---

# 66. Chuẩn tài liệu: mỗi chức năng phải có `.md`

Đây là yêu cầu bắt buộc, không phải tùy chọn.

## 66.1. Documentation-as-code contract

Mỗi feature/package production phải có ít nhất một tài liệu:

```text
docs/features/<feature-id>.md
```

Mỗi integration:

```text
docs/integrations/<integration-id>.md
```

Mỗi reusable recipe:

```text
docs/recipes/<recipe-id>.md
```

Ngoài ra thư mục implementation nên có `README.md` ngắn trỏ về canonical document.

Ví dụ:

```text
packages/agent_core/capabilities/README.md
docs/features/capability-gateway.md

packages/agent_core/skills/README.md
docs/features/skill-registry.md
docs/features/skill-optimization.md

packages/agent_integrations/google_adk/README.md
docs/integrations/google-adk.md
```

## 66.2. Template bắt buộc cho feature document

Mỗi file phải có:

```markdown
# <Feature name>

## 1. Mục đích
## 2. Khi nào sử dụng
## 3. Không dùng cho việc gì
## 4. Kiến trúc và luồng dữ liệu
## 5. Public contracts/API
## 6. Database/schema liên quan
## 7. Cấu hình
## 8. Ví dụ sử dụng
## 9. Cách bổ sung implementation mới
## 10. Security/governance
## 11. Error handling
## 12. Observability
## 13. Testing
## 14. Migration/backward compatibility
## 15. Troubleshooting
## 16. Definition of Done
```

Đặc biệt mục **“Cách bổ sung implementation mới”** phải nêu rõ extension point, file cần tạo, interface phải implement, test conformance phải chạy và docs cần cập nhật.

## 66.3. Documentation gate trong CI

CI phải fail nếu:

- thêm package/feature public mới nhưng không có docs;
- thêm runtime/provider/capability type mới nhưng không có extension guide;
- thay đổi public contract mà không cập nhật docs/changelog;
- code example trong docs không còn chạy nếu example thuộc nhóm executable docs.

Nên có `docs/manifest.yaml` ánh xạ feature → code owner → canonical doc → tests.

---

# 67. Chính sách comment trong code: tiếng Việt cho dev, identifier tiếng Anh

## 67.1. Quyết định

**Code identifiers, types, API names, DB columns và machine-readable schemas dùng tiếng Anh.  
Comment/docstring giải thích nghiệp vụ và quyết định khó dùng tiếng Việt.**

Ví dụ tốt:

```python
class CapabilityGateway:
    """Cổng thực thi capability duy nhất của COSA.

    Mọi side effect phải đi qua gateway này để bảo đảm governance,
    approval, idempotency và audit dùng cùng một semantics.
    """

    async def invoke(self, request: CapabilityInvocation) -> CapabilityResult:
        # Không tạo lại tool_call_id tại đây.
        # ID này phải được giữ nguyên từ runtime intent đến durable ledger.
        ...
```

Không nên:

```python
def thuc_hien_cong_cu(...):
    ...
```

vì làm giảm interoperability với ecosystem Python và tài liệu upstream.

## 67.2. Không comment mọi dòng

Yêu cầu “comment tiếng Việt” phải được hiểu là **comment nơi dev cần hiểu WHY**, không tạo noise.

Phải comment:

- invariant;
- security boundary;
- transaction boundary;
- non-obvious retry/idempotency behavior;
- framework workaround;
- temporal/governance semantics;
- migration compatibility;
- lý do không dùng cách đơn giản hơn.

Không cần comment:

```python
# Tăng biến đếm lên 1
count += 1
```

## 67.3. Docstring public API

Public class/function/protocol quan trọng phải có docstring tiếng Việt, nhưng thuật ngữ canonical giữ tiếng Anh:

```python
async def resume_run(...):
    """Resume một durable Run từ checkpoint đã commit.

    Không được replay side effect đã có idempotency record thành công.
    """
```

---

# 68. Prompt architecture và chiến lược ngôn ngữ

## 68.1. Quyết định: English canonical prompts + locale-aware output

Không nên duy trì hai bộ prompt logic Việt/Anh độc lập. Điều đó gây prompt drift và khó eval.

COSA nên dùng:

```text
Canonical system/developer prompt: English
Structured contracts/schema: English
Tool/capability names: English
Internal taxonomy: English

User input: any language
User-facing answer: locale-aware
Vietnam default: vi-VN
```

Lý do không chỉ là “model hiểu tiếng Anh tốt hơn”. Quan trọng hơn là ecosystem examples, tool schemas, technical vocabulary, eval datasets và framework instructions chủ yếu dùng English; một canonical language giảm divergence.

## 68.2. Prompt composition

Không lưu một giant prompt. Compose từ typed sections:

```text
PromptBundle
├── platform_policy.en.md
├── agent_role.en.md
├── domain_context.<locale-or-neutral>.md
├── skill_instructions.en.md
├── capability_instructions.en.md
├── output_policy.en.md
└── locale_policy.en.md
```

Runtime render:

```text
platform policy
+ immutable AgentSpec instructions
+ selected SkillSpec
+ capability/tool contracts
+ tenant/app context
+ locale/output policy
+ current user message
```

## 68.3. Locale policy

Canonical English instruction:

```text
The user's preferred locale is {{locale}}.
Respond in that locale unless the user explicitly requests another language.
Preserve official product names, code identifiers, API names, schema fields,
and technical terms when translation would reduce precision.
```

Default application configuration:

```yaml
default_locale: vi-VN
fallback_locale: en-US
prompt_source_locale: en
```

Nếu user viết tiếng Anh hoặc yêu cầu tiếng Anh, output đổi theo request.

## 68.4. Domain terminology dictionary

Cần có glossary versioned:

```text
prompts/glossary/
├── core.en.yaml
├── vi-VN.yaml
└── domain/
```

Ví dụ `vi-VN.yaml` ánh xạ cách hiển thị, không đổi internal identifier:

```yaml
run:
  preferred: "lượt chạy"
  keep_english_when_technical: true
capability:
  preferred: "capability"
approval:
  preferred: "phê duyệt"
```

## 68.5. Prompt versioning

Mọi published prompt phải có:

```text
prompt_id
version
source_locale
content_hash
created_at
published_at
eval_suite_id
```

Run phải pin prompt/spec version để replay/audit.

## 68.6. Không lưu private chain-of-thought

Prompt có thể yêu cầu structured rationale ngắn hoặc evidence, nhưng không thiết kế database để lưu hidden chain-of-thought. Lưu:

- decision;
- evidence references;
- tool results;
- concise explanation;
- scores;
- structured intermediate artifacts khi business cần.

---

# 69. Skill Platform — nâng cấp từ `awesome-llm-apps` + Hermes

## 69.1. Skill artifact chuẩn COSA

```text
skills/<skill-id>/
├── SKILL.md
├── skill.yaml
├── prompts/
│   └── instructions.en.md
├── references/
├── scripts/
├── assets/
├── evals/
│   ├── cases.yaml
│   └── rubric.yaml
└── README.md
```

`skill.yaml` machine-readable:

```yaml
kind: skill
id: competitor-intelligence
version: 1.0.0
source_locale: en
requires:
  capabilities:
    - web.search
    - company.read
permissions:
  network: restricted
  mutations: none
inputs:
  schema_ref: CompetitorIntelligenceInput
outputs:
  schema_ref: CompetitorIntelligenceReport
evals:
  suite: competitor-intelligence-v1
```

`SKILL.md` là hướng dẫn cho agent/human; `skill.yaml` là contract cho machine.

## 69.2. Skill lifecycle

```text
Draft
  ↓
Candidate
  ↓
Static validation
  ↓
Baseline eval
  ↓
Optimization Lab (optional)
  ↓
Regression + safety eval
  ↓
Human/governance approval
  ↓
Published immutable SkillSpec
  ↓
Deprecated/retired
```

Published version không mutate.

## 69.3. Self-improving Skill Lab

Harvest pattern `Executor → Analyst → Mutator`, nhưng tách khỏi production:

```text
Candidate Skill
   ↓
Executor
   ↓
Scorer
   ↓
Analyst
   ↓
Mutator (ONE bounded mutation)
   ↓
Challenger eval
   ↓
improved?
 ├─ no → revert
 └─ yes → candidate revision
   ↓
full regression
   ↓
approval
```

Bắt buộc:

- optimization chạy trên candidate copy;
- mỗi mutation có diff;
- không tự publish;
- không tự đổi skill của Run đang active;
- eval suite có holdout cases để giảm overfit;
- cost/token budget;
- max rounds;
- audit trail.

## 69.4. Skill extension guide

`docs/features/skills.md` phải hướng dẫn:

1. tạo folder;
2. khai báo `skill.yaml`;
3. viết canonical English prompt;
4. thêm Vietnamese usage docs;
5. khai báo capabilities;
6. thêm eval cases;
7. chạy `skill validate`;
8. chạy eval;
9. publish candidate;
10. promote immutable version.

---

# 70. Recipe Catalog — biến `awesome-llm-apps` thành pattern corpus

Không copy nguyên app. Chuẩn hóa recipe:

```text
agent_recipes/<domain>/<recipe-id>/
├── recipe.yaml
├── workflow.yaml
├── agents/
├── skills/
├── evals/
└── README.md
```

Recipe có thể instantiate thành AgentSpec/WorkflowSpec, nhưng không có authority riêng.

Các workflow pattern canonical:

- `single-agent`;
- `router`;
- `sequential`;
- `parallel`;
- `map-reduce`;
- `supervisor-worker`;
- `critic-revise`;
- `debate`;
- `mixture-of-agents`;
- `research-synthesize`;
- `watch-rank-deliver`;
- `human-approval-resume`.

Không hard-code pattern vào một SDK. Mỗi runtime adapter map pattern sang primitive phù hợp và phải qua conformance tests.

---

# 71. Control Plane — Paperclip + Always-on Agent thống nhất

## 71.1. Primitive

```text
Mission
Task
Worker
Lease
Budget
WatchSpec
TriggerPolicy
SignalObservation
DeliveryPolicy
DeliveryAttempt
```

Luồng proactive:

```text
Schedule/Event
    ↓
WatchSpec
    ↓
deterministic collector
    ↓
SignalObservation
    ↓
dedupe/filter/rank
    ↓
TriggerPolicy
    ↓
Agent Run
    ↓
Artifact
    ↓
DeliveryPolicy
    ↓
Flutter / email / Slack / webhook
```

## 71.2. Database bổ sung

Bổ sung migration sau các migration v1:

```text
012_control_plane_watches.sql
013_signal_observations.sql
014_delivery_policies.sql
015_recipe_registry.sql
016_prompt_registry.sql
017_skill_eval_lifecycle.sql
```

Bảng đề xuất:

```text
control_plane.watches
control_plane.trigger_policies
control_plane.signal_observations
control_plane.delivery_policies
control_plane.delivery_attempts

agent_registry.recipes
agent_registry.prompt_versions

agent_evals.suites
agent_evals.cases
agent_evals.runs
agent_evals.results
agent_evals.skill_candidates
agent_evals.skill_mutations
```

## 71.3. Scheduler

Scheduler chỉ quyết định “đến lúc xem xét chạy”; execution vẫn tạo canonical Run. Không để cron job gọi capability side effect trực tiếp.

---

# 72. Deterministic-first architecture

Pattern từ Release Radar phải trở thành coding rule.

Ưu tiên:

```text
deterministic acquisition
→ deterministic parsing/normalization
→ LLM reasoning/ranking only if needed
→ typed artifact
→ deterministic delivery
```

Ví dụ dependency release radar:

```text
requirements/package.json parser
→ normalized dependency records
→ GitHub release collector
→ deterministic version delta
→ LLM relevance/risk summary
→ delivery
```

Không dùng LLM để parse thứ mà parser chắc chắn hơn, rẻ hơn và test được.

Mỗi feature doc phải có mục:

```text
## Deterministic vs Agentic Boundary
```

và giải thích phần nào bắt buộc code thường, phần nào cho model.

---

# 73. Capability architecture hoàn chỉnh

Capability là business/external action contract, không phải SDK tool object.

```text
CapabilitySpec
├── id
├── version
├── input_schema
├── output_schema
├── side_effect_class
├── permission_requirements
├── approval_policy
├── idempotency_policy
├── timeout/retry policy
└── implementation binding
```

Execution:

```text
Runtime tool intent
→ normalize ToolInvocation
→ preserve (run_id, tool_call_id)
→ CapabilityGateway
→ readiness
→ current run-level governance
→ invocation accumulator
→ authorization
→ approval
→ idempotency reservation
→ implementation
→ durable result/audit
→ normalized runtime result
```

MCP capability cũng đi qua đường này. MCP là transport/discovery, không phải authority.

---

# 74. Runtime strategy: ưu tiên triển khai thực tế

## Phase 1 canonical production path

Ưu tiên:

```text
LangChain model/tool integration
+ COSA native execution contracts
+ LangGraph WorkflowRuntime candidate
+ LiteLLM gateway
+ DeepSeek primary model
```

Lý do: phù hợp Python codebase và DeepSeek, ecosystem rộng, dễ tạo provider abstraction.

## Phase 2 adapters

Sau khi conformance suite ổn:

```text
Google ADK adapter
OpenAI Agents SDK adapter
```

ADK đặc biệt hữu ích cho:

- Gemini-native workflow;
- multi-agent experimentation;
- Skill Optimization Lab.

OpenAI Agents SDK hữu ích cho:

- OpenAI-native tool/handoff;
- realtime/voice use cases nếu cần.

## DeepSeek Harness

Không để DeepSeek Harness làm canonical persistence/governance. Chỉ:

- remote runtime adapter;
- event/session pattern source;
- DeepSeek-specific experiments.

## Runtime conformance bắt buộc

Mọi runtime phải chứng minh:

- preserves run/tool-call identity;
- tool intents đi qua CapabilityGateway;
- structured output;
- streaming normalization;
- pause/approval/resume;
- timeout/cancel;
- typed errors;
- checkpoint/recovery;
- no duplicate side effect after retry;
- event ordering/correlation;
- tenant context propagation.

---

# 75. Memory và Knowledge

Tách rõ:

```text
Conversation history ≠ Memory ≠ Knowledge ≠ Business truth
```

Memory types:

- episodic;
- semantic preference;
- working summary;
- entity memory;
- procedural references.

Knowledge:

```text
KnowledgeSource
→ SourceVersion
→ Chunk
→ Embedding
→ Retrieval evidence
```

Source adapters có thể gồm file/PDF/GitHub/Gmail/web/YouTube/Arxiv/business service, nhưng business truth vẫn được lấy qua capability/service contract khi cần current state.

Memory write phải có policy; không tự động biến mọi model statement thành fact.

---

# 76. Artifact-first output

Không coi assistant text là output duy nhất.

Canonical Artifact:

```text
Artifact
├── markdown
├── structured_data
├── table
├── chart_spec
├── form
├── approval_request
├── task_plan
├── report
├── file_reference
└── generative_ui_descriptor
```

Flutter nhận normalized RuntimeEvent/Artifact, không nhận raw LangGraph/ADK/OpenAI event.

AG-UI adapter map canonical events ra UI protocol.

---

# 77. Security và secrets

Không copy demo pattern truyền API key tùy ý từ frontend vào process environment.

Production:

```text
Tenant/User
→ CredentialRef
→ Secret Broker
→ scoped provider credential
→ Model/Capability adapter
```

Yêu cầu:

- secrets không vào prompt;
- secrets không log;
- provider keys server-side;
- per-tenant policy/budget;
- network egress policy cho sandbox;
- capability allowlist;
- mutation approval;
- audit;
- RLS/tenant isolation.

BYOK nếu có phải là product feature riêng với encrypted storage và rotation.

---

# 78. Observability và evals là first-class

Mọi Run phải correlate:

```text
trace_id
run_id
conversation_id
tenant_id
principal_id
workflow_id/version
agent_spec_id/version
prompt_version
skill versions
model calls
tool_call_ids
approval ids
artifact ids
```

Metrics tối thiểu:

- run latency/success;
- model latency/token/cost;
- capability latency/error;
- approval wait;
- retries;
- duplicate prevention;
- retrieval quality;
- eval score;
- skill regression;
- delivery success.

Không log chain-of-thought.

---

# 79. Bộ tài liệu bắt buộc cần tạo trong repo

Claude Code phải tạo/cập nhật tối thiểu:

```text
docs/architecture/overview.md
docs/architecture/dependency-rules.md
docs/architecture/execution-lifecycle.md
docs/architecture/data-model.md
docs/architecture/prompt-language-strategy.md

docs/features/run-engine.md
docs/features/capability-gateway.md
docs/features/governance.md
docs/features/approvals.md
docs/features/idempotency.md
docs/features/workflows.md
docs/features/memory.md
docs/features/knowledge.md
docs/features/skills.md
docs/features/skill-optimization.md
docs/features/evals.md
docs/features/artifacts.md
docs/features/control-plane.md
docs/features/watch-signal-delivery.md
docs/features/recipe-catalog.md

docs/integrations/langchain.md
docs/integrations/langgraph.md
docs/integrations/litellm.md
docs/integrations/deepseek.md
docs/integrations/google-adk.md
docs/integrations/openai-agents-sdk.md
docs/integrations/mcp.md
docs/integrations/a2a.md
docs/integrations/ag-ui.md
docs/integrations/opentelemetry.md

docs/development/add-runtime.md
docs/development/add-capability.md
docs/development/add-skill.md
docs/development/add-recipe.md
docs/development/add-knowledge-source.md
docs/development/add-delivery-channel.md
docs/development/commenting-conventions.md
docs/development/testing-conformance.md

docs/operations/deployment.md
docs/operations/migrations.md
docs/operations/secrets.md
docs/operations/disaster-recovery.md
```

Mỗi file phải có phần usage + extension guide.

---

# 80. Quy tắc cho Claude Code khi triển khai

## 80.1. Không big-bang rewrite

Mỗi PR phải:

1. giữ system runnable;
2. additive trước;
3. backfill;
4. dual-read/dual-write nếu cần;
5. cutover;
6. cleanup sau.

## 80.2. Trước khi sửa

Claude Code phải:

- đọc canonical docs;
- xác định ownership;
- tìm tests hiện có;
- tìm migration/schema liên quan;
- không giả định file path từ blueprint nếu codebase đã thay đổi;
- ghi lại mismatch giữa blueprint và current code.

## 80.3. Khi tạo code

Bắt buộc:

- identifiers English;
- comments/docstrings nghiệp vụ quan trọng bằng tiếng Việt;
- typed Pydantic contracts;
- no raw dict across core boundaries nếu đã có contract;
- no framework object leaking into core;
- no direct DB access từ runtime adapter tới business schemas;
- no direct side effect outside CapabilityGateway;
- no silent exception → assistant text;
- no in-memory canonical state cho production;
- test failure paths, không chỉ happy path.

## 80.4. Khi thêm feature

Definition of Done:

```text
[ ] public contract
[ ] implementation
[ ] persistence/migration nếu cần
[ ] security/governance
[ ] telemetry
[ ] unit tests
[ ] integration tests
[ ] conformance tests nếu là adapter
[ ] feature .md
[ ] extension guide
[ ] Vietnamese explanatory comments/docstrings
[ ] changelog/ADR nếu thay architecture
```

---

# 81. Implementation plan v2 cho Claude Code

## Wave 0 — Freeze và inventory

- snapshot current repo/DB;
- cập nhật ownership map;
- tạo docs manifest;
- rename misleading runtime classes nếu có;
- tạo architecture tests cho dependency direction.

## Wave 1 — Execution spine

- canonical IDs;
- Run repository;
- Event ledger;
- ToolInvocation;
- CapabilityGateway single authority;
- typed runtime errors;
- durable conversations.

**Exit:** một end-to-end Run restart-safe.

## Wave 2 — Governance + exactly-once effect

- approval state machine;
- invocation governance accumulator;
- current run-level gate;
- atomic idempotency reservation/result;
- retry/recovery tests.

**Exit:** crash sau external success nhưng trước response không tạo side effect lần hai.

## Wave 3 — Prompt/Spec Registry

- immutable AgentSpec/WorkflowSpec/PromptVersion;
- English canonical prompt source;
- locale policy `vi-VN`;
- prompt hashes/version pinning;
- glossary.

**Exit:** Run replay xác định đúng prompt/spec versions.

## Wave 4 — LangChain/LangGraph + LiteLLM/DeepSeek

- LangChain integration;
- LiteLLM gateway;
- DeepSeek provider config;
- LangGraph WorkflowRuntime spike;
- conformance benchmark.

**Exit:** production candidate chạy DeepSeek qua canonical execution path.

## Wave 5 — Skills/Evals

- skill package format;
- registry;
- eval suites;
- candidate lifecycle;
- publish immutable versions;
- skill docs/tooling.

## Wave 6 — Skill Optimization Lab

- Executor;
- scorer;
- Analyst;
- Mutator;
- bounded mutation;
- holdout/regression;
- approval promotion.

Google ADK có thể được dùng ở lab qua adapter, nhưng candidate/publish state thuộc COSA.

## Wave 7 — Control Plane

- mission/task/worker/lease/budget;
- watches/triggers/signals;
- scheduler;
- delivery policy;
- proactive Run creation.

## Wave 8 — Knowledge/Memory v2

- source versions;
- adapters;
- retrieval evidence;
- memory write policies;
- migration from legacy memory.

## Wave 9 — Protocols

- MCP behind gateway;
- A2A;
- AG-UI;
- normalized artifacts/events.

## Wave 10 — Additional runtimes

- Google ADK conformance;
- OpenAI Agents SDK conformance;
- DeepSeek Harness remote adapter if still justified.

## Wave 11 — Recipe harvest

Harvest selected `awesome-llm-apps` ideas into COSA specs, ưu tiên:

1. competitor intelligence;
2. research-synthesize;
3. release radar/watch-rank-deliver;
4. advisor-orchestrator-worker;
5. dependency doctor;
6. self-improving skill;
7. mixture-of-agents.

Không copy demo architecture; translate thành recipe/skill/capability/eval.

---

# 82. Acceptance tests cấp nền tảng

Trước production, bắt buộc có automated scenarios:

### Scenario A — side-effect crash recovery

```text
Run
→ tool intent
→ approval
→ reserve idempotency
→ external API succeeds
→ process crashes
→ restart
→ resume
→ external API NOT called again
→ result reconciled
```

### Scenario B — approval pause/resume

Run pause ở approval phải resume trên replica khác với cùng `(run_id, tool_call_id)`.

### Scenario C — prompt reproducibility

Run lưu/pin exact AgentSpec + SkillSpec + PromptVersion + WorkflowSpec.

### Scenario D — multilingual

Cùng canonical English prompt:

- Vietnamese user → high-quality Vietnamese answer;
- English user → English answer;
- code/schema identifiers không bị dịch sai;
- eval so sánh quality giữa locales.

### Scenario E — runtime parity

Cùng một canonical workflow chạy ít nhất native/LangGraph và một adapter khác, semantics governance/capability không đổi.

### Scenario F — skill promotion

Candidate mutation tốt hơn baseline nhưng fail holdout → không được publish.

### Scenario G — watch delivery

Duplicate signal không tạo duplicate proactive Run/delivery.

---

# 83. Quyết định cuối về ngôn ngữ prompt

Đề xuất chính thức:

> **English is the canonical instruction language; Vietnamese is the default product interaction locale.**

Không dịch runtime prompt sang tiếng Việt theo kiểu toàn bộ hệ thống trước mỗi call. Thay vào đó, prompt English chứa locale directive rõ ràng và inject Vietnamese domain/business context khi dữ liệu nguồn là tiếng Việt.

Đối với một số domain Việt Nam (pháp luật, thuế, địa danh, tên biểu mẫu, thuật ngữ hành chính), giữ source text tiếng Việt trong context/reference để tránh mất nghĩa. Agent vẫn được điều khiển bằng canonical English instructions.

Đánh giá prompt phải chạy ít nhất hai track:

```text
EN reasoning/contract compliance eval
VI user-facing quality/terminology eval
```

Nếu sau benchmark một skill cụ thể chứng minh prompt Vietnamese tốt hơn đáng kể, có thể publish locale-specific override:

```text
skill_prompt.en.md      # canonical
skill_prompt.vi-VN.md   # optional evaluated override
```

nhưng override phải versioned, eval độc lập và không trở thành mặc định toàn platform chỉ dựa trên cảm giác.

---

# 84. Claude Code execution brief

Có thể giao trực tiếp phần này cho Claude Code:

```text
Implement the COSA Agent Platform restructuring incrementally.

Primary invariants:
1. COSA owns canonical run identity and durable history.
2. Every side effect goes through CapabilityGateway.
3. Governance, approval and idempotency are framework-independent.
4. Published AgentSpec/WorkflowSpec/SkillSpec/PromptVersion are immutable.
5. Framework SDK objects must not leak into agent_core public contracts.
6. PostgreSQL is durable truth; runtime checkpoints are implementation state.
7. Use deterministic code before LLM reasoning whenever possible.
8. Canonical prompt instructions are English; default user locale is vi-VN.
9. Code identifiers are English. Add Vietnamese comments/docstrings for non-obvious business, security, transaction, retry and architecture semantics.
10. Every public feature/integration must have a Markdown usage and extension guide.

Do not perform a big-bang rewrite. Audit the current repository before each wave and adapt paths to the real codebase. Preserve compatibility using additive migrations, backfills and controlled cutovers.

Implement in Waves 0–11 described in this blueprint. For every wave:
- update canonical docs first or in the same PR;
- implement typed contracts;
- add migrations where required;
- add unit/integration/failure-path tests;
- add telemetry;
- update docs/manifest.yaml;
- report any blueprint/current-code mismatch instead of silently inventing architecture.

Never bypass CapabilityGateway for production mutations.
Never regenerate tool_call_id after a runtime has emitted it.
Never convert provider/runtime failure into successful assistant text.
Never store private chain-of-thought.
Never let a self-improving agent mutate a published skill in place.
```

---

# 85. Final architecture checkpoint

Sau tất cả các phân tích LangChain, Google ADK, OpenAI Agents SDK, DeepSeek Harness, Hermes, Paperclip và `awesome-llm-apps`, cấu trúc nên chốt như sau:

```text
COSA = reusable Agent Platform Core
     + runtime adapters
     + capability/governance authority
     + durable execution
     + skill/eval platform
     + memory/knowledge
     + control plane
     + protocol interoperability
     + recipe corpus
     + application composition
```

Không chọn một framework làm “COSA Core”.

**LangChain/LangGraph là đường triển khai ưu tiên**, Google ADK và OpenAI Agents SDK là adapter mạnh cho use case phù hợp; DeepSeek là model/provider ưu tiên nhưng không được định nghĩa kiến trúc core. Paperclip đóng góp control-plane pattern; Hermes đóng góp skill/learning/sandbox pattern; `awesome-llm-apps` đóng góp recipe/skill/eval/always-on corpus.

Điểm phân biệt COSA với một collection demo là các invariant production: **tenant isolation, durable state, immutable specs, exact invocation identity, centralized capability authority, governance, approval, idempotency, eval/promotion, observability và documentation-as-code.**

Đây là baseline đề xuất để Claude Code triển khai. Mọi thay đổi kiến trúc sau baseline phải đi qua ADR và cập nhật tài liệu canonical tương ứng.
