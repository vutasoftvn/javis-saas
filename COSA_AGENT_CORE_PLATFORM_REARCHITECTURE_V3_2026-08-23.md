# COSA Agent Core Platform — Re-architecture V3

> **Revision:** V3 — 2026-08-23  
> **Loại tài liệu:** Foundational Architecture + Runtime Redesign + Reusable Agent Platform Blueprint + Migration Handbook  
> **Repository:** `vutasoftvn/javis-saas`  
> **Code baseline đã đối chiếu:** `main@eedfbacb78de357b16983962bad5ff28a467e451`  
> **External runtime baseline đã phân tích:** `openai/openai-agents-python@233467994fac7e7dbd868931573cc9a4302c0a16`, package line `0.22.0` tại thời điểm audit  
> **Mục tiêu:** thiết kế lại COSA/Javis thành một nền tảng AI Agent thực sự mạnh, durable, composable, dễ kết nối vào công việc thật, đồng thời tách được một **Agent Core có thể tái sử dụng cho nhiều ứng dụng khác**.

---

## 0. Quyết định nền tảng

Tài liệu này **không tiếp tục giả định kiến trúc hiện tại là đúng**. Những phần của hệ thống hiện tại chỉ được giữ nếu chúng phục vụ target architecture tốt hơn việc thay thế.

Quyết định quan trọng nhất của V3:

> **COSA không nên được tổ chức quanh Google ADK, DeepSeek Harness, OpenAI Agents SDK, FastAPI, Encore, hay một model provider cụ thể. COSA phải có một Agent Core độc lập ở cấp kiến trúc; execution kernel là dependency có thể thay thế.**

Và:

> **Trong implementation trước mắt, OpenAI Agents Python là lựa chọn phù hợp nhất để làm execution kernel chính vì nó đã giải quyết sâu runner state machine, tool lifecycle, HITL interruption/resume, sessions, model abstraction, MCP, tracing và sandbox. Nhưng COSA tuyệt đối không để domain/core contracts phụ thuộc trực tiếp vào SDK này.**

Target tổng thể:

```text
┌────────────────────────────────────────────────────────────────────────────┐
│                          APPLICATION SHELLS                                │
│                                                                            │
│  COSA Company OS     Personal Assistant     Dev Agent      Vertical Apps   │
│  Flutter/Web/API     Slack/Email bot        Coding UI      CRM/Finance AI  │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │ stable Agent Platform API
                                ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                     REUSABLE COSA AGENT CORE                              │
│                                                                            │
│ Identity Envelope • Agent Spec • Capability Catalog • Context Engine       │
│ Policy • Approval • Tool Gateway • Connector Runtime • Memory • Knowledge  │
│ Run Store • Event Protocol • Artifacts • Evals • Observability • Billing   │
└───────────────────────────────┬────────────────────────────────────────────┘
                                │ execution port
                                ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                       EXECUTION KERNEL LAYER                               │
│                                                                            │
│   OpenAI Agents SDK (primary)       Native deterministic runtime (tests)   │
│   Future alternative runtimes through explicit adapter                    │
└─────────────────────┬───────────────────────┬──────────────────────────────┘
                      │                       │
                  Model Port              Sandbox Port
                      │                       │
         ┌────────────┼────────────┐          ├─ local/docker
         ▼            ▼            ▼          ├─ E2B/Daytona/etc.
      OpenAI       DeepSeek     Anthropic      └─ future providers

All business side effects
        │
        ▼
COSA Capability / Tool Gateway
        │
Policy → Approval → Execution → Audit → Event
```

---

# 1. Vì sao phải phá cấu trúc hiện tại

## 1.1. `AgentRuntime` đang có quá nhiều vai trò

`agentos/core/runtime.py` hiện vừa build context, quản lý `AgentRun`, tạo trace, chọn runtime qua metadata, phân nhánh multi-agent/DeepSeek/native Executor, xử lý approval exception và giữ mutable diagnostic state `last_run`, `last_trace`, `last_context`.

Đây là một **god-runtime** che ba concern khác nhau:

```text
Application orchestration
Execution engine selection
Run lifecycle persistence
```

Target phải tách thành:

```text
RunService
  │
  ├── AgentResolver
  ├── ContextEngine
  ├── ExecutionKernel
  ├── RunRepository
  ├── EventPublisher
  └── Governance hooks
```

`AgentRuntime` hiện tại nên được **retire**, không refactor thành một class to hơn.

## 1.2. `Executor` là mini agent framework tự viết

`agentos/core/executor.py` hiện sở hữu LLM → tool → LLM loop, `MAX_TOOL_ROUNDS`, policy decisions, approval interruption, tool execution, trace, audit và conversation replay.

Đây là loại code dễ kiểm soát ở Phase 1 nhưng nhanh chóng phức tạp khi thêm:

- parallel tool calls;
- nested agent calls;
- resume after restart;
- stable call identity;
- streaming model/tool events;
- retries;
- tool timeouts/recovery;
- provider fallback;
- MCP approvals;
- sandbox execution;
- durable long-running jobs.

OpenAI Agents SDK đã giải quyết chính lớp complexity này. COSA không có lợi thế cạnh tranh khi tự duy trì một agent loop riêng.

```text
agentos/core/executor.py
    CURRENT: custom execution loop
    TRANSITION: compatibility/fallback + deterministic tests
    TARGET: retire khỏi production path
```

## 1.3. `orchestration/adk` có tên sai với implementation

`agentos/orchestration/adk/orchestrator.py` hiện không dùng Google ADK runtime. Nó tự chạy specialists bằng `asyncio.gather()` rồi synthesis.

Do đó package name đang làm architecture bị méo.

**Target:**

```text
agent_core/coordination/
├── delegation.py
├── parallel.py
├── sequential.py
├── debate.py
├── supervisor.py
└── synthesis.py
```

Execution adapter map primitives này xuống Agent-as-Tool, Handoff hoặc host-language orchestration tùy runtime.

## 1.4. API hiện tại chưa phải durable agent API

`agentos/api/chat/routes.py` đã có conversation CRUD, SSE và approval endpoint, nhưng vẫn còn các điểm nền tảng:

### A. In-memory pending run

```python
_pending_runs: dict[str, dict[str, Any]] = {}
```

Process restart/deploy sẽ mất resume context.

### B. Approval hiện replay từ đầu

Sau approval, API gọi lại `_run_agent_task()` bằng cùng goal/run_id. Đây là **rerun**, không phải resume checkpoint chính xác.

Hậu quả:

- reasoning có thể đổi;
- tool call cũ có thể chạy lại;
- side effect có nguy cơ duplicate;
- audit lineage không chắc chắn;
- approval không bind vào exact execution state.

### C. `asyncio.create_task()` trong request process

Task không durable qua process crash, worker recycle, autoscaling, deploy hoặc container eviction.

### D. Request-scoped DB session bị đưa vào background task

HTTP request đã trả nhưng background task tiếp tục giữ object session từ dependency lifecycle. Đây là coupling không nên có.

### E. Cancel chưa cancel execution

Endpoint cancel hiện chủ yếu phát event; không có durable cancellation token/active execution handle.

### F. Streaming chưa thật

Khi complete, full output được emit như một `message.delta`; chưa phải model streaming semantic/token-level.

### G. Singleton mutable runtime

Global runtime giữ `last_context/last_run/last_trace`. Concurrent runs có thể ghi đè. API đọc citations từ `runtime.last_context`, nên có race condition tiềm ẩn.

**Kết luận:** API hiện tại là **TRANSITION**. Không thêm state mới vào module globals.

---

# 2. Mục tiêu sản phẩm: AI agent dùng được trong công việc thật

Một agent mạnh không được đo bằng số lượng agents hay độ dài prompt. Nó phải hoàn thành công việc có kiểm soát.

Target tối ưu cho 10 thuộc tính:

1. **Understand work context** — company/workspace/user/task/artifacts/history.
2. **Connect** — Gmail, Calendar, Drive, Slack, GitHub, CRM, finance, DB, browser, MCP.
3. **Act** — có action/tool layer chuẩn.
4. **Pause safely** — approval, external wait, credential, schedule.
5. **Resume exactly** — checkpoint durable, không replay mù.
6. **Use specialists** — delegation có cấu trúc.
7. **Remember** — working, episodic, semantic, procedural, organizational.
8. **Produce artifacts** — docs, files, code, reports, plans, structured records.
9. **Be evaluated** — quality, cost, latency, policy, reliability.
10. **Be embedded elsewhere** — core dùng lại được ngoài COSA.

---

# 3. Kiến trúc mới: Core trước, App sau

## 3.1. Tách `agent_core` khỏi `agentos`

Target repository:

```text
javis-saas/
├── apps/
│   ├── cosa/
│   │   ├── api/
│   │   ├── agent_profiles/
│   │   ├── company_tools/
│   │   ├── company_memory/
│   │   └── workflows/
│   ├── realtime_voice/
│   └── ...future apps
│
├── packages/
│   └── agent_core/
│       ├── api/
│       ├── agents/
│       ├── capabilities/
│       ├── connectors/
│       ├── context/
│       ├── coordination/
│       ├── execution/
│       ├── governance/
│       ├── memory/
│       ├── knowledge/
│       ├── runs/
│       ├── events/
│       ├── artifacts/
│       ├── models/
│       ├── sandbox/
│       ├── observability/
│       ├── evals/
│       └── testing/
│
├── services/
├── frontend/
├── skillpacks/
└── legacy/
```

Nếu chưa chuyển physical folder ngay, giữ `agentos/` tạm thời nhưng áp dụng logical boundaries này.

## 3.2. Core không được biết COSA business domains

`agent_core` không import operations, commercial, finance-legal, company strategy, Founder OS, COSA DB models hay Flutter schema.

Core chỉ biết:

```text
Principal
TenantScope
AgentSpec
Capability
Tool
Connector
ContextSource
MemoryStore
KnowledgeSource
Run
RunState
Artifact
Event
PolicyDecision
Approval
Model
ExecutionKernel
```

COSA app package register domain capabilities vào core.

---

# 4. Contract model mới

## 4.1. `RunRequest`

Không tiếp tục dùng `TaskContext.metadata` như untyped control bus.

Target:

```python
@dataclass(frozen=True)
class RunRequest:
    run_id: RunId
    conversation_id: ConversationId | None
    agent_id: AgentId
    input: RunInput
    principal: Principal
    scope: TenantScope
    limits: RunLimits
    execution: ExecutionPreferences
    context: ContextRequest
    correlation_id: str
```

## 4.2. `RunResult`

Không chỉ `(output, tool_calls_made)`.

```python
@dataclass
class RunResult:
    run_id: RunId
    status: RunStatus
    final_output: OutputEnvelope | None
    usage: Usage
    artifacts: list[ArtifactRef]
    citations: list[Citation]
    pending_actions: list[PendingAction]
    state_ref: RunStateRef | None
    error: RunError | None
```

## 4.3. `AgentSpec`

```python
@dataclass(frozen=True)
class AgentSpec:
    id: str
    version: str
    instructions: InstructionSource
    model_policy: ModelPolicy
    capabilities: tuple[CapabilityRef, ...]
    skills: tuple[SkillRef, ...]
    delegates: tuple[AgentRef, ...]
    memory_policy: MemoryPolicy
    context_policy: ContextPolicy
    autonomy_policy: AutonomyPolicy
    output_schema: OutputSchema | None
    limits: RunLimits
```

Agent profile immutable per run.

## 4.4. `ExecutionKernel`

```python
class ExecutionKernel(Protocol):
    async def run(self, spec: AgentSpec, request: RunRequest) -> RunExecution: ...
    async def resume(self, state: RunStateRef, decision: ResumeDecision) -> RunExecution: ...
    async def cancel(self, run_id: RunId) -> None: ...
```

Primary adapter:

```text
OpenAIAgentsExecutionKernel
```

Test adapter:

```text
DeterministicExecutionKernel
```

DeepSeek chỉ là runtime riêng nếu có capability độc đáo chứng minh được; nếu không, nó là model provider.

---

# 5. OpenAI Agents SDK sở hữu gì, Core sở hữu gì

## SDK nên sở hữu

- reasoning loop;
- turn state machine;
- function tool plumbing;
- handoffs;
- agent-as-tool;
- structured output;
- tool call identity;
- nested interruption propagation;
- RunState serialize/resume;
- session mechanics;
- SDK tracing lifecycle;
- sandbox mechanics;
- MCP protocol mechanics.

## COSA Agent Core phải sở hữu

- principal/tenant identity;
- authorization/policy;
- business approval records;
- capability registry;
- connector grants/credentials;
- tool business metadata;
- audit ledger;
- durable run repository;
- application event schema;
- memory semantics;
- knowledge policy;
- artifact ownership;
- cost budgets;
- model routing;
- eval policy;
- application AgentSpecs.

## Không duplicate state machines

Khi kernel có serialized resumable state, Core lưu state đó theo adapter-defined envelope; Core không tự reconstruct reasoning loop.

COSA Approval record là business representation; SDK RunState là execution truth.

---

# 6. Durable Run Architecture

## 6.1. Persist run trước execution

```text
POST message
    │
    ▼
create Run row (PENDING)
    │
    ▼
enqueue run command
    │
    ▼
worker leases Run
    │
    ▼
RUNNING
    │
    ├── COMPLETED
    ├── FAILED
    ├── CANCELLED
    ├── WAITING_APPROVAL
    ├── WAITING_EXTERNAL
    └── PAUSED
```

Không dùng module-level dictionary làm run registry.

## 6.2. Durable entities tối thiểu

```text
runs
run_checkpoints
run_events
run_usage
run_artifacts
run_tool_calls
approvals
conversations
messages
connector_grants
```

`run_checkpoints`:

```text
run_id
kernel_type
kernel_version
state_schema_version
opaque_state_blob / object_ref
created_at
checksum
```

## 6.3. Approval flow mới

```text
Tool asks approval
      │
      ▼
SDK interruption
      │
      ├─ serialize RunState
      ├─ persist checkpoint
      ├─ create business Approval
      ├─ emit approval.required
      └─ run -> WAITING_APPROVAL

Human decides
      │
      ▼
ApprovalService
      │
      ├─ verify principal/tenant
      ├─ mark decision
      └─ enqueue ResumeRun(run_id, approval_id)

Worker
      │
      ├─ load exact checkpoint
      ├─ apply approve/reject
      └─ kernel.resume(...)
```

Không rerun original prompt.

## 6.4. Idempotency

Mọi side effect có canonical invocation identity:

```text
(run_id, tool_call_id, capability_id, payload_hash)
```

Gateway reject duplicate completed invocation trừ khi capability khai báo retry-safe.

---

# 7. Worker architecture

## 7.1. API process tách khỏi execution

```text
FastAPI
    │
    ├─ validation/auth
    ├─ conversation write
    ├─ run creation
    └─ enqueue command

Durable queue
    │
    ▼
Agent Worker Pool
    │
    ├─ ExecutionKernel
    ├─ connector clients
    ├─ sandbox clients
    └─ event publisher
```

Phase đầu có thể dùng PostgreSQL-backed queue/lease để tránh thêm hạ tầng.

## 7.2. Lease

```text
leased_by
lease_expires_at
heartbeat_at
attempt
```

Worker chết thì worker khác recover từ checkpoint.

## 7.3. Cancellation

`cancel()` phải:

- mark cancellation requested;
- signal worker;
- cancel model stream nếu provider hỗ trợ;
- không bắt đầu tool call mới;
- tool dài check cancellation token khi có thể;
- emit terminal `run.cancelled` sau khi thực sự dừng.

---

# 8. Event Protocol là public contract

SSE/WebSocket/UI không phụ thuộc event nội bộ SDK.

Envelope:

```json
{
  "event_id": "...",
  "run_id": "...",
  "sequence": 42,
  "type": "tool.completed",
  "timestamp": "...",
  "correlation_id": "...",
  "payload": {}
}
```

Canonical families:

```text
run.created
run.started
run.paused
run.resumed
run.completed
run.failed
run.cancel.requested
run.cancelled

message.started
message.delta
message.completed

reasoning.status

agent.delegated
agent.started
agent.completed

tool.requested
tool.approval_required
tool.started
tool.progress
tool.completed
tool.failed

approval.required
approval.resolved

artifact.created
artifact.updated
citation.created
usage.updated
```

Adapter translate SDK stream events sang schema này.

Event store append-only, `sequence` monotonic per run.

---

# 9. Tool Gateway → Capability Runtime

## 9.1. Vấn đề registry hiện tại

`ToolRegistry` hiện đã có schema validation, timeout, aliases và risk metadata. Nhưng target cần vượt khỏi “Python handler registry”.

Capability có thể đến từ:

- local Python;
- Encore API;
- MCP;
- OAuth connector;
- remote HTTP;
- sandbox;
- another agent;
- workflow;
- knowledge;
- memory.

## 9.2. `CapabilitySpec`

```python
@dataclass(frozen=True)
class CapabilitySpec:
    id: str
    version: str
    kind: CapabilityKind
    description: str
    input_schema: JsonSchema
    output_schema: JsonSchema
    risk: RiskPolicy
    auth: AuthRequirement
    data_scope: DataScopePolicy
    approval: ApprovalPolicy
    retry: RetryPolicy
    timeout: TimeoutPolicy
    audit: AuditPolicy
    execution_ref: CapabilityExecutionRef
```

Kinds:

```text
FUNCTION
REMOTE_API
MCP_TOOL
CONNECTOR_ACTION
AGENT
WORKFLOW
SANDBOX
KNOWLEDGE_QUERY
MEMORY_ACTION
```

## 9.3. Execution chain

```text
Model requests capability
        │
        ▼
CapabilityResolver
        │
        ▼
Input validation
        │
        ▼
Policy evaluation
        │
        ├─ DENY
        ├─ REQUIRE_APPROVAL
        └─ ALLOW
              │
              ▼
Credential resolution
              │
              ▼
Idempotency check
              │
              ▼
Execution
              │
              ▼
Output validation
              │
              ▼
Audit + usage + event
```

Kernel không bypass chain này.

---

# 10. Connectors là first-class architecture

Work agent mạnh chủ yếu khác chatbot ở **connectivity**.

```text
agent_core/connectors/
├── contracts.py
├── registry.py
├── credentials.py
├── grants.py
├── oauth.py
├── mcp.py
├── webhooks.py
└── providers/
```

## 10.1. Connector contract

```python
class Connector(Protocol):
    manifest: ConnectorManifest

    async def capabilities(self, grant: ConnectorGrant) -> list[CapabilitySpec]: ...
    async def invoke(
        self,
        capability_id: str,
        args: dict,
        ctx: InvocationContext
    ) -> Any: ...
```

## 10.2. Credential isolation

Agent/model không nhận raw credential.

```text
Agent → capability request
            │
            ▼
Connector Runtime
            │
            ▼
Credential Vault / grant resolver
            │
            ▼
Provider API
```

## 10.3. MCP

MCP là integration protocol, không phải trust boundary.

```text
MCP discovery
    ↓
COSA capability normalization
    ↓
policy / approval / audit
    ↓
SDK MCP execution hoặc wrapped invocation
```

Không để MCP server tự quyết tenant permissions.

## 10.4. External event waits

Agent công việc cần có khả năng chờ email, approval, PR merged, payment, calendar time, CRM change.

Target cần durable `ExternalEventWait`, không polling trong LLM loop.

---

# 11. Model layer: bỏ tư duy “provider = runtime”

## 11.1. DeepSeek Harness

Current adapter flatten messages thành một prompt string, chạy sync Harness trong thread và parse text tìm tool call. Đây không phải integration lý tưởng cho modern tool runtime.

Ưu tiên:

```text
DeepSeek OpenAI-compatible API
        ↓
OpenAI-compatible Model adapter
        ↓
Agents SDK
```

Chỉ giữ Harness-specific model nếu nó tạo giá trị riêng rõ rệt.

## 11.2. `ModelPolicy`

```python
@dataclass(frozen=True)
class ModelPolicy:
    preferred: tuple[ModelRef, ...]
    fallback: tuple[ModelRef, ...]
    max_cost_usd: Decimal | None
    max_latency_ms: int | None
    required_capabilities: frozenset[ModelCapability]
    data_policy: ModelDataPolicy
```

Resolver theo task:

```text
classification → fast/cheap
deep reasoning → reasoning model
vision → multimodal
coding → coding-optimized
privacy → private/approved provider
```

## 11.3. Usage

Không đoán token. Provider trả usage thật hoặc `unknown`.

Aggregate:

```text
input_tokens
output_tokens
cached_tokens
model_calls
tool_calls
sandbox_compute
connector_calls
wall_time
estimated_provider_cost
```

---

# 12. Context Engine

Current `ContextBuilder` có hướng đúng nhưng cần trở thành pipeline có budget.

```text
ContextRequest
     │
     ▼
Context Sources (parallel)
 ├─ conversation
 ├─ working memory
 ├─ long-term memory
 ├─ knowledge
 ├─ company state
 ├─ user state
 ├─ connectors
 ├─ artifacts
 └─ task dependencies
     │
     ▼
Relevance ranking
     │
     ▼
Policy filtering
     │
     ▼
Token budget allocation
     │
     ▼
ContextPackage
```

`ContextPackage`:

```python
@dataclass
class ContextPackage:
    instructions: list[ContextBlock]
    memories: list[ContextBlock]
    knowledge: list[ContextBlock]
    conversation: list[ContextBlock]
    business_state: list[ContextBlock]
    artifacts: list[ArtifactRef]
    citations: list[Citation]
    provenance: list[Provenance]
    token_estimate: int
```

Mỗi block có source, sensitivity, timestamp, score, TTL.

Context source modes:

```text
OPTIONAL
REQUIRED
FAIL_CLOSED
```

Không silent-fallback cho dữ liệu bắt buộc trong task critical.

---

# 13. Memory architecture mới

Bốn lớp:

```text
L0 Execution State
   SDK RunState/checkpoints

L1 Conversation State
   messages/session history

L2 Agent/User Memory
   episodic + preferences + learned procedures

L3 Organizational Knowledge
   company facts, documents, entities, decisions
```

## 13.1. Current PostgresMemoryStore chưa semantic

Store hiện persist relational records và search theo scope/kind/time; semantic vector retrieval chưa được implement.

## 13.2. Write pipeline

Không lưu mọi message vào long-term memory.

```text
Observation
   ↓
Memory candidate extractor
   ↓
PII/secret/policy filter
   ↓
Dedup + contradiction
   ↓
importance + confidence
   ↓
Memory store
```

## 13.3. Memory record

```text
id
scope
kind
content
structured_payload
embedding
source_refs
confidence
importance
valid_from / valid_to
created_at
last_confirmed_at
supersedes
sensitivity
retention_policy
```

## 13.4. Retrieval

Hybrid:

```text
scope filter
+ semantic similarity
+ lexical
+ recency
+ importance
+ entity relevance
+ supersession rules
```

Memory cũng phải có provenance/citation.

---

# 14. Knowledge architecture

Knowledge khác memory.

```text
Source
  ↓
Ingest
  ↓
Parse
  ↓
Normalize
  ↓
Chunk
  ↓
Metadata + ACL
  ↓
Embed
  ↓
Index
  ↓
Retrieve
  ↓
Rerank
  ↓
Citation
```

Support:

- files;
- websites;
- Drive/Notion/Confluence;
- database snapshots;
- business records;
- connector sync;
- user attachments.

ACL phải nằm trong retrieval query path, không retrieve cross-tenant rồi lọc sau.

---

# 15. Agent specialization

## 15.1. Không tạo agent để “có multi-agent”

Một specialist mới chỉ tồn tại nếu có ít nhất một khác biệt rõ:

- context;
- tools;
- permissions;
- model;
- output contract;
- eval suite;
- lifecycle/ownership.

Nếu chỉ khác prompt nhỏ, dùng skill.

## 15.2. Agent-as-tool là default delegation

```text
Supervisor
 ├─ finance specialist
 ├─ sales specialist
 ├─ research specialist
 └─ operations specialist
```

Handoff chỉ khi control thực sự chuyển.

## 15.3. Parallelism explicit

Deterministic coordination layer quyết định parallelism khi phù hợp, không phụ thuộc hoàn toàn vào model.

## 15.4. Agent versioning

Mỗi production run lưu AgentSpec version.

---

# 16. Skills

Skillpack target:

```text
manifest.yaml
instructions.md
examples/
evals/
schemas/
optional capability declarations
```

Skill không có security authority.

```text
Agent selects Skill
       │
       ▼
Skill suggests capabilities
       │
       ▼
Capability + Policy quyết định actual access
```

---

# 17. Artifacts first-class

Work agent tạo/cập nhật objects, không chỉ chat.

Types:

```text
document
spreadsheet
presentation
code patch
report
plan
task list
dataset
image
file
external object reference
```

Artifact record:

```text
artifact_id
run_id
owner/scope
type
mime_type
storage_ref
version
provenance
created_by_agent
created_at
```

Tool output có thể trả `ArtifactRef`; UI render artifact độc lập message.

---

# 18. Governance redesign

## 18.1. Typed policy request

```python
@dataclass(frozen=True)
class PolicyRequest:
    principal: Principal
    tenant: TenantScope
    agent: AgentIdentity
    capability: CapabilitySpec
    arguments_summary: ArgumentClassification
    execution_mode: ExecutionMode
    data_scope: DataScope
    run: RunIdentity
```

## 18.2. Three-level governance

```text
Capability eligibility
        ↓
Policy authorization
        ↓
Per-invocation approval
```

## 18.3. Durable approvals

```text
approval_id
run_id
checkpoint_ref
tool_call_id
capability_id
requested_by
requested_for
argument_digest / safe_preview
status
reviewer
reason
created_at
decided_at
```

## 18.4. Audit != trace

Audit trả lời ai làm gì, tenant nào, policy nào, ai approve, external object nào thay đổi.

Trace phục vụ debugging/performance.

---

# 19. Observability

Ba lớp:

```text
Runtime traces
Product events
Audit ledger
```

Production tracing: sensitive model/tool payloads OFF mặc định.

Metrics tối thiểu:

```text
run_success_rate
run_latency_p50/p95/p99
model_latency
model_error_rate
tool_success_rate
tool_latency
approval_rate
approval_wait_time
resume_success_rate
cost_per_run
context_tokens
memory_hit_rate
knowledge_citation_rate
cancel_success_rate
```

---

# 20. Evals

Eval pyramid:

```text
Unit deterministic
  ↓
Tool contract eval
  ↓
Agent behavior eval
  ↓
Workflow eval
  ↓
Live provider regression
  ↓
Production sampled eval
```

Mỗi AgentSpec/Skill quan trọng có eval suite.

Metrics gồm:

- task completion;
- tool selection;
- policy compliance;
- hallucination;
- citation accuracy;
- number model calls;
- cost;
- approval correctness;
- no duplicate side effect;
- interruption recovery.

Model upgrade phải qua replay eval corpus.

---

# 21. Reusable packaging

Core phải install độc lập:

```text
pip install cosa-agent-core
```

hoặc workspace package trước.

Extras:

```text
cosa-agent-core[openai]
cosa-agent-core[postgres]
cosa-agent-core[redis]
cosa-agent-core[mcp]
cosa-agent-core[sandbox]
cosa-agent-core[otel]
```

Application usage:

```python
platform = AgentPlatform(
    execution_kernel=OpenAIAgentsKernel(...),
    run_store=PostgresRunStore(...),
    capability_registry=...,
    policy_engine=...,
)

platform.register_agent(my_agent_spec)
platform.register_connector(...)
```

---

# 22. Target module boundaries

```text
packages/agent_core/
│
├── api/
│   ├── application.py
│   ├── commands.py
│   └── queries.py
├── agents/
│   ├── spec.py
│   ├── registry.py
│   ├── resolver.py
│   └── versioning.py
├── runs/
│   ├── models.py
│   ├── repository.py
│   ├── service.py
│   ├── checkpoint.py
│   ├── cancellation.py
│   └── worker.py
├── execution/
│   ├── contracts.py
│   ├── openai_agents/
│   │   ├── kernel.py
│   │   ├── agent_adapter.py
│   │   ├── tool_adapter.py
│   │   ├── session_adapter.py
│   │   ├── state_codec.py
│   │   └── event_adapter.py
│   └── deterministic/
├── capabilities/
│   ├── spec.py
│   ├── registry.py
│   ├── resolver.py
│   ├── gateway.py
│   └── idempotency.py
├── connectors/
│   ├── contracts.py
│   ├── registry.py
│   ├── grants.py
│   ├── credentials.py
│   ├── mcp.py
│   └── webhooks.py
├── context/
│   ├── request.py
│   ├── package.py
│   ├── engine.py
│   ├── budget.py
│   ├── ranking.py
│   └── sources/
├── governance/
│   ├── policy.py
│   ├── approvals.py
│   ├── audit.py
│   └── sensitivity.py
├── memory/
│   ├── contracts.py
│   ├── models.py
│   ├── write_pipeline.py
│   ├── retrieval.py
│   └── providers/
├── knowledge/
│   ├── contracts.py
│   ├── ingestion.py
│   ├── retrieval.py
│   └── providers/
├── models/
│   ├── contracts.py
│   ├── policy.py
│   ├── routing.py
│   └── providers/
├── events/
│   ├── schema.py
│   ├── publisher.py
│   └── repository.py
├── artifacts/
│   ├── models.py
│   ├── repository.py
│   └── storage.py
├── sandbox/
│   ├── contracts.py
│   └── providers/
├── observability/
│   ├── tracing.py
│   ├── metrics.py
│   └── usage.py
├── evals/
│   ├── contracts.py
│   ├── runner.py
│   └── datasets.py
└── testing/
    ├── fake_kernel.py
    ├── fake_model.py
    ├── fake_capability.py
    └── fixtures.py
```

---

# 23. COSA application assembly

```text
apps/cosa/
├── api/
│   ├── conversations.py
│   ├── runs.py
│   ├── events.py
│   └── approvals.py
├── agents/
│   ├── cofounder.yaml
│   ├── finance.yaml
│   ├── sales.yaml
│   ├── strategy.yaml
│   └── operations.yaml
├── capabilities/
│   ├── encore/
│   ├── company_admin/
│   └── reporting/
├── context_sources/
│   ├── company.py
│   ├── workspace.py
│   └── business_services.py
├── memory/
│   └── company_memory_policy.py
└── composition.py
```

`services/` vẫn là business truth. Agent Core chỉ gọi qua typed APIs/capabilities.

---

# 24. Database ownership

Production schemas gợi ý:

```text
agent_core.runs
agent_core.run_checkpoints
agent_core.run_events
agent_core.run_tool_calls
agent_core.run_usage
agent_core.approvals
agent_core.artifacts
agent_core.connector_grants

agent_memory.*
agent_knowledge.*
cosa_chat.*
```

SQLite vẫn first-class cho local, desktop, offline, tests.

PostgreSQL dùng cho production multi-instance.

---

# 25. API redesign

```text
POST   /v1/conversations
GET    /v1/conversations
GET    /v1/conversations/{id}
PATCH  /v1/conversations/{id}

POST   /v1/conversations/{id}/messages
GET    /v1/runs/{run_id}
POST   /v1/runs/{run_id}/cancel
GET    /v1/runs/{run_id}/events

GET    /v1/approvals
POST   /v1/approvals/{id}/decision

GET    /v1/artifacts/{id}
GET    /v1/agents
GET    /v1/capabilities
GET    /v1/connectors
```

HTTP handler không:

- access runtime private fields;
- own pending dicts;
- start non-durable background tasks;
- giữ DB session theo worker lifecycle.

---

# 26. Security rules

1. Tenant scope nằm trong typed invocation context.
2. Tool/connector credentials không đi vào model context.
3. Cross-tenant retrieval impossible by query construction.
4. Sensitive tracing off mặc định production.
5. Every side effect có idempotency identity.
6. Approval bind exact tool call + argument digest.
7. Resume state checksum/versioned.
8. Sandbox mounts explicit allowlist.
9. Remote MCP server là untrusted source.
10. Tool output validate trước khi replay cho model.

---

# 27. Những phần current code nên KEEP

- `PolicyEngine` concepts;
- Tool risk/approval/audit metadata;
- `ToolSpecV2` schema/timeout direction;
- `AuditSink` semantic separation;
- `TraceRecorder` concepts;
- Agent profiles/skillpacks;
- Knowledge citations;
- Memory kinds;
- Business cluster tool adapters;
- event names hiện tại làm migration seed;
- adapter idea, nhưng contract nâng thành `ExecutionKernel`.

---

# 28. Những phần nên REPLACE

```text
AgentRuntime god object             → RunService + ExecutionKernel
Executor production loop           → OpenAI Agents SDK kernel
Planner FINISH/TOOL_CALL            → SDK state machine
orchestration/adk naming            → framework-neutral coordination
DeepSeekHarnessRuntimeAdapter       → model provider unless necessary
_pending_runs dict                  → durable RunRepository + checkpoint
asyncio.create_task HTTP execution  → durable worker queue
runtime.last_context                → per-run result/context record
runtime private profile registry    → AgentRegistry dependency
approval rerun-from-goal            → exact RunState resume
full-output message.delta           → actual stream events
fake cancel event                   → cancellation protocol
metadata control bus                → typed RunRequest/AgentSpec
```

---

# 29. Migration plan

## Phase 0 — Freeze architecture drift

- Không thêm runtime framework mới.
- Không thêm control state vào metadata nếu có thể typed.
- Không thêm module-level run state.
- Pin exact tested OpenAI Agents SDK release.
- ADR chốt `ExecutionKernel`.

## Phase 1 — Durable Run Foundation

Tạo:

```text
RunRepository
RunEventRepository
CheckpointRepository
ApprovalRepository
RunCommandQueue
```

API tạo run rồi enqueue; worker consume.

Chưa đổi Executor.

Exit:
- restart API không mất run;
- worker crash recover queued run;
- cancel có state thật.

## Phase 2 — ExecutionKernel contract

Wrap Executor thành `LegacyNativeKernel`.

`RunService` chỉ biết kernel.

Exit: API không import AgentRuntime/Executor trực tiếp.

## Phase 3 — OpenAI Agents Kernel MVP

Implement:

```text
OpenAIAgentsKernel
AgentSpec adapter
Capability → FunctionTool adapter
Core events adapter
Session/checkpoint adapter
```

Single-agent read-only tools trước.

## Phase 4 — HITL exact resume

- capability approval → SDK `needs_approval`;
- persist RunState;
- approval resumes exact state;
- duplicate side-effect tests.

Exit: kill process ở WAITING_APPROVAL, restart, approve, tiếp tục đúng checkpoint.

## Phase 5 — Streaming + cancellation

- SDK stream events → Core events;
- cancellation token;
- real model delta;
- tool lifecycle stream.

## Phase 6 — Agent specialization

- Co-founder + specialists thành AgentSpecs;
- agents-as-tools;
- deterministic parallel coordination;
- remove `orchestration/adk`.

## Phase 7 — Connector Platform + MCP

- ConnectorRegistry;
- ConnectorGrant;
- credential vault;
- MCP normalization;
- Gmail/Calendar/Drive/Slack/GitHub theo product priority.

## Phase 8 — Memory V2

- embeddings;
- hybrid retrieval;
- write pipeline;
- provenance;
- supersession;
- retention/privacy.

## Phase 9 — Artifacts + Sandbox

- ArtifactStore;
- sandbox port;
- coding/data/document agents;
- long-horizon tasks.

## Phase 10 — Extract reusable package

Move framework-neutral modules sang `packages/agent_core`.

COSA trở thành app assembly đầu tiên.

---

# 30. Testing requirements

## Kernel contract tests

```text
simple final output
single tool
multiple tools
invalid args
tool failure
timeout
approval pause
approval resume
rejection
cancellation
max limits
streaming
usage propagation
nested interruption
```

## Durability tests

```text
process dies before model call
after model output
after tool requested
after side effect before checkpoint
while waiting approval
resume on another worker
```

## Security tests

- tenant A không retrieve tenant B;
- approval payload X không authorize Y;
- denied capability không tới executor;
- credentials không xuất hiện trong prompt/event/trace;
- duplicate resume không duplicate side effect.

---

# 31. Performance/cost

Budget enforcement:

```text
max turns
max model calls
max tool calls
max wall time
max tokens
max estimated cost
max sandbox compute
max parallel delegates
```

Budgets là typed `RunLimits`.

Tool result lớn → artifact/object + summary/reference, không bơm raw data lớn vào model.

---

# 32. Runtime lock-in strategy

OpenAI Agents SDK là replaceable kernel nhưng không ép lowest-common-denominator.

Kernel capability flags:

```text
supports_resume
supports_nested_approvals
supports_streaming
supports_mcp
supports_sandbox
supports_realtime
supports_server_conversations
```

AgentSpec resolver validate requirements trước run.

---

# 33. Realtime/Voice

Voice là channel, không phải agent architecture riêng.

```text
Voice Session
   │
   ▼
RunService / Agent Core
   │
   ▼
same AgentSpec / capabilities / memory / policy
```

Text ↔ Voice dùng cùng conversation identity.

---

# 34. Self-improvement

Giữ concept self-improvement nhưng không cho tự sửa production config trực tiếp.

```text
evidence
  ↓
proposal
  ↓
candidate AgentSpec/Skill version
  ↓
offline eval
  ↓
review/approval
  ↓
canary
  ↓
promotion
```

Mọi promotion reversible.

---

# 35. Definition of “Agent thực sự mạnh”

Chỉ gọi mạnh hơn nếu có evidence:

```text
Task completion ↑
Tool success ↑
Correct approvals ↑
Hallucination ↓
Quality/cost ↑
Recovery success ↑
Connector coverage ↑
Memory relevance ↑
Citation correctness ↑
User intervention ↓ for low-risk work
```

Không dùng số agent/framework/prompt làm KPI.

---

# 36. Architecture decisions cuối cùng

## Python hay TypeScript cho Agent Core?

**Python.**

- current AgentOS đã Python;
- Agents Python SDK có runtime depth tốt;
- AI/embedding/sandbox ecosystem phù hợp;
- FastAPI/Pydantic/SQLAlchemy đủ;
- chuyển TS lúc này tạo thêm migration risk.

TypeScript/Encore tiếp tục Business/Control Plane.

## Google ADK?

Không giữ làm architecture pillar.

Nếu benchmark chứng minh có capability độc đáo thì dùng adapter phụ. Current `orchestration/adk` nên retire/rename.

## DeepSeek Harness?

Không coi là runtime root.

Dùng như model provider/experiment. Ưu tiên structured OpenAI-compatible integration.

## OpenAI Agents Python?

**Adopt làm primary execution kernel**, qua compatibility spike + eval gate.

- Không fork.
- Không import `run_internal`.
- Pin version.
- Wrap qua `ExecutionKernel`.
- Persist RunState như execution checkpoint.

## Database?

PostgreSQL production multi-instance; SQLite first-class local/offline/test.

---

# 37. Immediate implementation backlog

1. ADR `ExecutionKernel + durable run ownership`.
2. Typed `RunRequest`, `RunResult`, `AgentSpec`, `RunLimits`.
3. Persistent Run/Checkpoint/Event repositories.
4. API khỏi `asyncio.create_task()` → durable worker.
5. Xóa dependency vào `runtime.last_context`.
6. `_pending_runs` → DB state.
7. Wrap current Executor thành `LegacyNativeKernel`.
8. `OpenAIAgentsKernel` read-only pilot.
9. Capability → FunctionTool adapter với Policy/Audit.
10. Exact approval resume bằng RunState.
11. Model streaming → Core Event Protocol.
12. Cancellation thật.
13. Co-founder + 1 specialist → AgentSpec + agent-as-tool.
14. Benchmark/eval current vs new.
15. Nếu đạt gate, switch default.
16. Retire `orchestration/adk` + custom Planner/Executor production.
17. Connector Platform → Memory V2 → Artifacts/Sandbox.

---

# 38. Anti-patterns bị cấm từ V3

Không thêm mới:

- agent runtime loop khác;
- orchestration framework root khác;
- business DB access trực tiếp từ model;
- raw credential trong prompt;
- run state trong globals;
- approval state chỉ trong RAM;
- request-scoped DB session cho background run;
- `asyncio.create_task()` như durable queue;
- behavior flags mới trong metadata nếu typed được;
- agent mới chỉ vì chia prompt;
- long-term memory write every message;
- gọi vector DB là memory system nếu chưa có memory semantics;
- side effect tool không idempotency identity;
- SDK internal imports;
- sensitive trace payload mặc định production.

---

# 39. Success criteria cho reusable Agent Core

Core chỉ được xem là tách thành công khi có thể tạo app thứ hai, ví dụ **Internal Developer Agent**, với:

- AgentSpec riêng;
- GitHub connector;
- repo knowledge;
- coding sandbox;
- approval rules riêng;
- cùng RunService/Kernel/Event/Memory;
- **không import module COSA company/finance/sales/operations**.

Nếu không, core vẫn chỉ là COSA implementation đổi tên.

---

# 40. Canonical target summary

```text
                       ┌─────────────────────┐
                       │ Application Shells  │
                       └──────────┬──────────┘
                                  │
                       ┌──────────▼──────────┐
                       │   Agent Platform    │
                       │  Application API    │
                       └──────────┬──────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
         Run Service         Context Engine     Agent Registry
              │                   │                   │
              └─────────────┬─────┴─────┬─────────────┘
                            ▼           ▼
                    ExecutionKernel   Capability Gateway
                            │           │
                            │     Policy/Approval/Audit
                            │           │
          ┌─────────────────┴───┐       ├─ Connectors
          ▼                     ▼       ├─ MCP
 OpenAI Agents Kernel    Test/Other      ├─ Business APIs
          │                Kernels       ├─ Sandbox
          │                              └─ Agents/Workflows
          ├─ Models
          ├─ RunState
          ├─ Tools
          ├─ Handoffs/agents-as-tools
          ├─ Sessions
          └─ Sandbox/MCP mechanics

Shared durable infrastructure:
Postgres Run/Checkpoint/Event/Approval + Memory + Knowledge + Artifacts + OTel
```

**Target identity:**

> COSA/Javis không còn là “ứng dụng có chatbot + một số agent modules”. Nó trở thành một **Agent Platform** có execution kernel mạnh, durable work runtime, governed capability system, memory/knowledge/artifact layers và connector architecture; COSA Company OS chỉ là ứng dụng đầu tiên sử dụng platform đó.

---

## Appendix A — Mapping current → target

| Current | Target |
|---|---|
| `agentos/core/runtime.py` | `agent_core/runs/service.py` + kernel |
| `agentos/core/executor.py` | deterministic/legacy kernel hoặc retire |
| `agentos/core/planner.py` | SDK runtime |
| `agentos/core/adapters/contracts.py` | `execution/contracts.py` |
| `agentos/orchestration/adk/` | `coordination/` + agent composition |
| `agentos/core/model_provider.py` | richer `models/contracts.py` |
| `agentos/tools/registry.py` | `capabilities/registry.py` |
| `agentos/tools/clusters/*` | COSA app capability adapters |
| `agentos/core/policy.py` | `governance/policy.py` |
| `agentos/core/approval.py` | durable approvals |
| `agentos/core/audit_sink.py` | audit port/providers |
| `agentos/core/context_builder.py` | Context Engine |
| `agentos/memory/*` | Memory V2 |
| `agentos/knowledge/*` | Knowledge layer |
| `agentos/api/chat/routes.py` | thin HTTP adapter |
| `_pending_runs` | Run + Checkpoint repositories |
| `runtime.last_context` | per-run result/citations |
| `DeepSeekHarnessRuntimeAdapter` | normally Model provider |
| `AdkOrchestrator` | AgentSpecs + coordination |

---

## Appendix B — Compatibility policy

Trong migration:

- public HTTP breaking changes phải versioned;
- DB migrations forward-only;
- checkpoint schema versioned;
- AgentSpec version immutable sau production use;
- capability IDs stable, version explicit;
- kernel state version theo kernel + SDK;
- SDK exact-pinned;
- SDK upgrades qua eval + resume compatibility tests.

---

## Appendix C — Spike cần làm trước production cutover

1. DeepSeek OpenAI-compatible tool-call compatibility với Agents SDK.
2. Streaming + usage fields cho DeepSeek path.
3. RunState serialization size/storage cho COSA workloads.
4. Resume compatibility khi SDK minor upgrade.
5. Nested agent-as-tool approval propagation qua COSA policy bridge.
6. OTel bridge + sensitive-data behavior.
7. SQLAlchemy/Postgres Session adapter.
8. MCP wrapping để policy không bị bypass.
9. Sandbox threat model.
10. Benchmark current Executor vs Agents kernel cùng workload.

Nếu spike thất bại, không quay lại custom god-runtime. Điều chỉnh adapter boundary hoặc chọn kernel khác sau cùng contract.
