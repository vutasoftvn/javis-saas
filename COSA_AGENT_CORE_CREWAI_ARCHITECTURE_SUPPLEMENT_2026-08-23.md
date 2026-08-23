# COSA Agent Core Platform — CrewAI Architecture Supplement

> **Revision:** Supplement A — 2026-08-23  
> **Status:** Architecture Addendum to `COSA_AGENT_CORE_PLATFORM_REARCHITECTURE_V3_2026-08-23.md`  
> **Repository:** `vutasoftvn/javis-saas`  
> **COSA baseline:** V3 architecture remains canonical  
> **External reference audited:** `crewAIInc/crewAI` current `main` line around CrewAI 1.15.x  
> **Purpose:** Incorporate lessons from the CrewAI architecture audit without changing the core ownership model already approved for COSA.

---

## 0. How to read this document

This document is **not V4** and does not replace V3.

V3 already made the correct foundational decisions:

1. COSA owns a reusable, framework-neutral Agent Core.
2. `ExecutionKernel` is replaceable.
3. OpenAI Agents Python is the primary execution kernel for the first production implementation.
4. Business side effects must pass through the COSA Capability / Tool Gateway.
5. Durable run state, approvals, events, memory, knowledge, artifacts, policy and audit belong to COSA.
6. Google ADK, DeepSeek Harness, CrewAI, OpenAI Agents SDK or any future framework must not become the architectural root of the platform.
7. The current `AgentRuntime` / custom `Executor` production path is transitional and should be retired.

The CrewAI audit does not invalidate these decisions.

It **adds four important refinements**:

```text
1. Flow-first, agent-second
2. Authoring DSL != Serializable Definition != Runtime
3. Pause / wait / feedback must be first-class durable data
4. Coordination should be an explicit platform capability,
   not an accidental property of an agent framework
```

The result is an extension of V3, not a framework switch.

---

# 1. Executive decision

## 1.1. Decision

**Do not adopt CrewAI as the root runtime or canonical platform abstraction of COSA.**

CrewAI may be used in three roles only:

```text
A. Architecture reference
B. Benchmark implementation
C. Optional Execution / Workflow adapter
```

subject to the same contracts and governance boundaries as every other runtime.

Canonical direction remains:

```text
Application Shells
        │
        ▼
COSA Agent Platform API
        │
        ▼
Reusable COSA Agent Core
        │
        ├─ Runs / Checkpoints / Interruptions
        ├─ AgentSpec / WorkflowSpec
        ├─ Context
        ├─ Capabilities
        ├─ Governance
        ├─ Connectors
        ├─ Memory / Knowledge
        ├─ Artifacts
        ├─ Events / Usage / Evals
        │
        ▼
Execution & Coordination Ports
        │
        ├─ OpenAI Agents Kernel      ← primary
        ├─ Deterministic Kernel      ← tests / deterministic workflows
        └─ CrewAI Adapter            ← optional, only if benchmark justifies it
```

## 1.2. Why CrewAI is not the platform root

CrewAI now contains much more than multi-agent role prompts. Its current architecture includes:

- Crews and agents;
- deterministic/event-driven Flows;
- flow state and persistence;
- pause/resume;
- async human feedback;
- memory;
- knowledge;
- model/provider abstraction;
- tools;
- tracing and telemetry;
- evaluation/training facilities;
- security and execution hooks.

This makes CrewAI a strong batteries-included application runtime.

It also means adopting it deeply would make COSA dependent on a framework that overlaps with areas COSA explicitly intends to own:

```text
run lifecycle
workflow runtime
memory
governance
observability
agent definitions
tool behavior
enterprise orchestration
```

That creates unnecessary framework gravity and weakens the reusable Agent Core goal.

---

# 2. What the CrewAI audit confirms about V3

## 2.1. V3 was correct to reject the “everything is an agent” architecture

CrewAI's evolution toward Flows confirms an important production lesson:

> Deterministic work should remain deterministic. Agents should be inserted where reasoning, ambiguity or adaptive tool selection are actually required.

COSA should therefore model:

```text
Workflow
 ├─ deterministic step
 ├─ connector action
 ├─ approval gate
 ├─ wait-for-event
 ├─ parallel branch
 ├─ agent reasoning step
 ├─ specialist delegation
 └─ artifact generation
```

instead of forcing every node through an autonomous agent loop.

## 2.2. V3 was correct to separate execution truth from business truth

CrewAI demonstrates useful runtime persistence and resume behavior, but COSA has stronger business requirements:

```text
Execution truth:
  model turns
  tool-call state
  framework checkpoint
  pending execution continuation

Business truth:
  principal
  tenant
  capability
  policy
  approval
  invocation identity
  audit record
  external side effect
```

These must remain separate.

The execution framework may tell COSA **where execution paused**.

Only COSA may decide **whether the requested business action is permitted**.

## 2.3. V3 was correct to keep canonical memory outside the execution kernel

CrewAI's unified memory is a useful reference implementation for:

- semantic + recency + importance scoring;
- consolidation;
- scopes;
- adaptive-depth recall.

But COSA Company OS additionally requires:

- tenant isolation;
- ACL-aware retrieval;
- organizational provenance;
- retention;
- sensitivity classification;
- supersession;
- auditability;
- cross-application reuse.

Therefore CrewAI Memory may inform algorithms, but cannot be the canonical organizational memory store.

---

# 3. New architectural principle: Flow-first, Agent-second

Add the following principle to V3:

> **COSA orchestrates work as a workflow graph. Agent reasoning is one kind of workflow step, not the container for the entire workflow.**

Target mental model:

```text
                     ┌───────────────────┐
                     │    WorkflowSpec   │
                     └─────────┬─────────┘
                               │ compile/resolve
                               ▼
                     ┌───────────────────┐
                     │ WorkflowDefinition│
                     │ versioned + serial│
                     └─────────┬─────────┘
                               │
                               ▼
                     ┌───────────────────┐
                     │ Coordination      │
                     │ Runtime           │
                     └─────────┬─────────┘
                               │
        ┌──────────────────────┼─────────────────────────┐
        ▼                      ▼                         ▼
 deterministic step       AgentStep                Wait/Approval
        │                      │                         │
        ▼                      ▼                         ▼
 Capability Gateway       ExecutionKernel          Durable state
```

This keeps autonomy bounded and observable.

---

# 4. Add `WorkflowSpec` as a first-class Core contract

V3 defines `AgentSpec`, but after the CrewAI review the platform also needs an explicit workflow contract.

## 4.1. `WorkflowSpec`

```python
@dataclass(frozen=True)
class WorkflowSpec:
    id: str
    version: str
    description: str
    input_schema: JsonSchema
    output_schema: JsonSchema | None
    state_schema: JsonSchema | None
    nodes: tuple[WorkflowNodeSpec, ...]
    edges: tuple[WorkflowEdgeSpec, ...]
    limits: RunLimits
    autonomy_policy: AutonomyPolicy
    failure_policy: WorkflowFailurePolicy
    metadata: Mapping[str, JsonValue]
```

## 4.2. Workflow node kinds

Minimum canonical node kinds:

```text
START
END

FUNCTION
CAPABILITY
AGENT
WORKFLOW

SEQUENTIAL
PARALLEL
JOIN
ROUTER

APPROVAL
HUMAN_INPUT
EXTERNAL_WAIT
SCHEDULE_WAIT

ARTIFACT
MEMORY_QUERY
MEMORY_WRITE
KNOWLEDGE_QUERY
```

These are **COSA semantics**.

An execution adapter may map them to CrewAI Flow, host-language orchestration, OpenAI agent-as-tool, a durable worker step, or another runtime.

## 4.3. Agent is one node kind

An `AGENT` node references an immutable `AgentSpec`:

```python
@dataclass(frozen=True)
class AgentNodeSpec:
    agent: AgentRef
    input_mapping: MappingSpec
    output_mapping: MappingSpec
    execution_requirements: KernelRequirements
```

This prevents a workflow definition from becoming coupled to a framework-specific `Agent`, `Crew`, `Task`, or decorator.

---

# 5. Add a serializable `WorkflowDefinition` layer

One of the best architectural patterns observed in modern CrewAI is the separation between:

```text
authoring syntax
definition
runtime
```

COSA should make this explicit.

## 5.1. Three layers

```text
Layer 1 — Authoring
YAML / Python builder / future visual builder
           │
           ▼
Layer 2 — WorkflowDefinition
canonical, versioned, serializable platform IR
           │
           ▼
Layer 3 — Runtime
CoordinationRuntime / ExecutionKernel adapters
```

## 5.2. Why this matters

Without an intermediate definition layer:

- decorators become runtime contracts;
- framework classes leak into persisted state;
- visual workflow builder becomes difficult;
- migrations become coupled to source code;
- versioning becomes unclear;
- workflow diffing and evals become harder;
- alternative runtimes cannot consume the same workflow.

## 5.3. Canonical rule

> Persist the COSA workflow definition, not the authoring mechanism.

For example:

```text
apps/cosa/workflows/monthly_business_review.yaml
                    │
                    ▼
WorkflowCompiler
                    │
                    ▼
WorkflowDefinition v3
                    │
         ┌──────────┴───────────┐
         ▼                      ▼
Native Coordination       CrewAI adapter
Runtime                    if enabled
```

---

# 6. Add `CoordinationRuntime`

V3 already moves orchestration away from `orchestration/adk/`.

This supplement makes the target contract explicit.

```python
class CoordinationRuntime(Protocol):
    async def start(
        self,
        definition: WorkflowDefinition,
        request: WorkflowRunRequest,
    ) -> WorkflowExecution: ...

    async def resume(
        self,
        state: WorkflowStateRef,
        decision: ResumeDecision,
    ) -> WorkflowExecution: ...

    async def cancel(self, run_id: RunId) -> None: ...
```

The default coordination implementation should be as deterministic as possible.

Agent autonomy is delegated downward through `ExecutionKernel`.

Target:

```text
CoordinationRuntime
    │
    ├─ sequential
    ├─ parallel
    ├─ join
    ├─ route
    ├─ wait
    ├─ approval
    ├─ retry
    ├─ compensation
    │
    └─ AGENT node
          │
          ▼
     ExecutionKernel
```

This means COSA no longer needs a monolithic “multi-agent runtime”.

---

# 7. Durable interruption becomes a first-class concept

V3 already defines approvals and checkpoints.

The CrewAI audit suggests generalizing this into one reusable interruption model.

## 7.1. `PendingInterruption`

```python
@dataclass(frozen=True)
class PendingInterruption:
    id: InterruptionId
    run_id: RunId
    kind: InterruptionKind
    checkpoint_ref: RunStateRef
    node_id: str | None
    call_id: str | None
    requested_at: datetime
    expires_at: datetime | None
    payload: SafeInterruptionPayload
    resume_contract: ResumeContract
```

## 7.2. Interruption kinds

```text
APPROVAL
HUMAN_INPUT
EXTERNAL_EVENT
CREDENTIAL_REQUIRED
SCHEDULE
RATE_LIMIT
MANUAL_RECOVERY
```

Approval is therefore a specialized business interruption, not the only reason a run can pause.

## 7.3. State transition

```text
RUNNING
   │
   ▼
interruption requested
   │
   ├─ persist exact execution/workflow state
   ├─ create interruption record
   ├─ emit event
   └─ transition run
          │
          ├─ WAITING_APPROVAL
          ├─ WAITING_INPUT
          ├─ WAITING_EXTERNAL
          └─ PAUSED
```

Resume:

```text
external decision/event
        │
        ▼
validate tenant + principal + interruption contract
        │
        ▼
load exact checkpoint
        │
        ▼
apply ResumeDecision
        │
        ▼
resume workflow/kernel
```

No prompt replay.

---

# 8. Approval remains stricter than generic human feedback

CrewAI's human-feedback model is useful for content review and routing.

COSA approval semantics must remain stronger.

## 8.1. Generic human feedback

Suitable for:

```text
approve draft
request revision
choose alternative
comment on plan
classify an ambiguous result
```

## 8.2. Governed business approval

Required for side effects such as:

```text
send email
publish content
modify CRM
pay invoice
delete record
create deployment
merge code
change access rights
sign or submit business data
```

A governed approval must bind to:

```text
approval_id
run_id
checkpoint_ref
tool_call_id / invocation_id
capability_id
payload_hash
safe_preview
principal / tenant
policy decision
```

An LLM-generated outcome like `"approved"` is **not** sufficient authorization.

---

# 9. Capability Gateway remains mandatory under every runtime

No CrewAI tool, OpenAI tool, MCP tool or future framework tool may bypass the gateway.

Canonical chain remains:

```text
Framework requests tool/action
          │
          ▼
Adapter converts request
          │
          ▼
COSA Capability Gateway
          │
          ├─ schema validation
          ├─ tenant scope
          ├─ policy
          ├─ approval
          ├─ credential resolution
          ├─ idempotency
          ├─ execution
          ├─ output validation
          ├─ audit
          └─ event / usage
```

Hard rule:

> Runtime-native tools are allowed only when they are wrapped into the COSA capability contract, or when they are explicitly classified as execution-internal and cannot create uncontrolled business side effects.

---

# 10. Optional `CrewAIExecutionAdapter`

CrewAI may be introduced only behind an adapter.

Suggested location:

```text
packages/agent_core/execution/
├── contracts.py
├── openai_agents/
├── deterministic/
└── crewai/
    ├── kernel.py
    ├── workflow_adapter.py
    ├── agent_adapter.py
    ├── capability_adapter.py
    ├── state_codec.py
    └── event_adapter.py
```

This directory should **not exist in the first production cutover unless the benchmark produces a concrete reason to keep it**.

## 10.1. Adapter responsibilities

The adapter may own:

- translation from `AgentSpec` to CrewAI agent configuration;
- translation from `WorkflowDefinition` to CrewAI Flow/Crew primitives;
- framework checkpoint encoding;
- framework streaming/event conversion;
- provider compatibility;
- framework-specific lifecycle cleanup.

The adapter may not own:

- tenant authorization;
- business approvals;
- credentials;
- canonical memory;
- canonical events;
- connector grants;
- business audit;
- artifact ownership;
- canonical Run records.

## 10.2. No direct CrewAI types in Core contracts

Forbidden:

```python
class RunRequest:
    crew: Crew
```

Forbidden:

```python
class AgentSpec:
    task: crewai.Task
```

Allowed only inside adapter package:

```python
def to_crewai_agent(spec: AgentSpec) -> CrewAIAgent:
    ...
```

---

# 11. Expand kernel capability negotiation

V3 already proposes kernel capability flags.

Add workflow- and interruption-related flags.

```python
@dataclass(frozen=True)
class KernelCapabilities:
    supports_resume: bool
    supports_nested_approvals: bool
    supports_streaming: bool
    supports_parallel_tools: bool
    supports_agent_as_tool: bool
    supports_handoffs: bool
    supports_mcp: bool
    supports_sandbox: bool
    supports_realtime: bool
    supports_server_conversations: bool

    supports_workflow_state: bool
    supports_external_wait: bool
    supports_async_human_input: bool
    supports_checkpoint_migration: bool
```

Agent and workflow resolution must fail before execution when requirements are unsupported.

No silent degradation for critical semantics.

---

# 12. Memory lessons adopted from CrewAI

COSA should adopt the following ideas at the algorithmic level.

## 12.1. Composite retrieval

A useful default scoring model:

```text
score =
  semantic_similarity * Wsemantic
+ lexical_relevance    * Wlexical
+ recency              * Wrecency
+ importance           * Wimportance
+ entity_relevance     * Wentity
+ source_confidence    * Wconfidence
```

Weights are policy/configuration, not hard-coded globally.

## 12.2. Consolidation

On long-term memory write:

```text
candidate
  │
  ▼
retrieve similar memories
  │
  ├─ duplicate      → update confirmation metadata
  ├─ refinement     → supersede / merge
  ├─ contradiction  → preserve lineage + resolve validity
  └─ novel          → insert
```

## 12.3. Scoped memory

Scope should be explicit and query-enforced:

```text
tenant
workspace
user
agent
workflow
business entity
project
```

Unlike a generic runtime memory, COSA's scope is also an authorization boundary.

## 12.4. Async writes need durability rules

Background memory extraction can be asynchronous.

But production behavior must distinguish:

```text
best-effort enrichment
vs
business-critical persistence
```

Best-effort memory failures may degrade gracefully.

Critical business state must never be hidden in a background memory thread.

---

# 13. Event Protocol additions

Add interruption and workflow event families.

```text
workflow.started
workflow.node.started
workflow.node.completed
workflow.node.failed
workflow.branch.started
workflow.branch.completed
workflow.completed
workflow.failed

interruption.created
interruption.resolved
interruption.expired

human_input.required
human_input.received

external_wait.created
external_wait.matched
external_wait.cancelled
```

Existing approval events remain:

```text
approval.required
approval.resolved
```

Adapters must translate framework events into this protocol.

UI, SSE and WebSocket clients must not depend on CrewAI/OpenAI SDK event classes.

---

# 14. Database additions

Extend the V3 durable schema with:

```text
agent_core.workflow_definitions
agent_core.workflow_runs
agent_core.workflow_node_runs
agent_core.interruptions
agent_core.external_event_waits
```

Suggested minimum interruption fields:

```text
id
run_id
workflow_node_id
kind
checkpoint_ref
call_id
status
safe_payload
resume_schema
requested_at
resolved_at
resolved_by
expires_at
```

`approvals` may either reference an interruption row or be implemented as the specialized record behind an approval interruption.

Recommended direction:

```text
interruptions        = execution pause abstraction
approvals            = business authorization abstraction
```

Do not collapse them into one table conceptually.

---

# 15. Target module boundary additions

Update the target package from V3 with:

```text
packages/agent_core/
│
├── workflows/
│   ├── spec.py
│   ├── definition.py
│   ├── compiler.py
│   ├── registry.py
│   ├── validation.py
│   └── versioning.py
│
├── coordination/
│   ├── contracts.py
│   ├── runtime.py
│   ├── sequential.py
│   ├── parallel.py
│   ├── routing.py
│   ├── delegation.py
│   └── synthesis.py
│
├── interruptions/
│   ├── models.py
│   ├── repository.py
│   ├── service.py
│   ├── resume.py
│   └── external_wait.py
│
└── execution/
    ├── contracts.py
    ├── openai_agents/
    ├── deterministic/
    └── crewai/              # optional, benchmark-gated
```

COSA application layer becomes:

```text
apps/cosa/
├── agents/
├── workflows/
├── capabilities/
├── context_sources/
├── memory/
└── composition.py
```

---

# 16. Workflow authoring policy

COSA should support multiple authoring surfaces while keeping one canonical IR.

Potential surfaces:

```text
YAML
Python builder
future visual builder
generated workflow templates
AI-assisted workflow authoring
```

All compile into:

```text
WorkflowDefinition
```

Rules:

1. Workflow ID and version are explicit.
2. Production workflow versions are immutable.
3. Definition is serializable without importing application runtime objects.
4. Every referenced AgentSpec / CapabilitySpec is version-resolved before run.
5. Validation checks unsupported cycles, missing joins, invalid routes and unsafe capability paths.
6. Definition checksum is stored on each run.
7. Runtime checkpoint stores definition version/checksum.

---

# 17. Workflow vs Agent vs Skill

Use the following decision rule.

## Use a Skill when

Only instructions/examples/procedure knowledge change.

```text
same authority
same tools
same lifecycle
same output type
```

## Use an Agent when

At least one meaningful execution boundary changes:

```text
context
tools
permissions
model policy
output contract
eval suite
ownership/lifecycle
```

## Use a Workflow when

The work has explicit coordination or lifecycle:

```text
ordered steps
parallel branches
approval
external wait
scheduled continuation
retry/compensation
multiple agents
artifact pipeline
```

This avoids both agent proliferation and giant procedural prompts.

---

# 18. CrewAI benchmark plan

CrewAI should be evaluated as a candidate adapter, not debated abstractly.

Run the following three spikes.

## Spike A — Research coordination

```text
Research request
   │
   ├─ market specialist
   ├─ technical specialist
   └─ risk specialist
          │
          ▼
       synthesis
```

Compare:

```text
COSA Coordination + OpenAI Agents
vs
CrewAI Flow + Crew adapter
```

Measure:

- code complexity;
- wall time;
- model calls;
- tokens/cost;
- trace clarity;
- failure handling;
- deterministic parallelism;
- output quality.

## Spike B — Exact governed approval

Scenario:

```text
agent proposes side-effect
       │
       ▼
Capability Gateway
       │
       ▼
WAITING_APPROVAL
       │
kill process
       │
restart
       │
approve
       │
resume exact invocation
```

Required result:

```text
0 duplicate side effects
same invocation identity
same payload digest
complete audit lineage
```

If a CrewAI path cannot satisfy this through COSA contracts, it is not eligible for governed side-effect workloads.

## Spike C — Long-running workflow

Scenario includes:

```text
agent work
→ external wait
→ resume on another worker
→ human feedback
→ artifact generation
→ completion
```

Test across process restart.

---

# 19. Benchmark acceptance gates

CrewAI adapter is retained only if it wins or materially simplifies at least one class of workload.

Minimum gates:

| Area | Gate |
|---|---|
| Correctness | no lower task completion than primary path |
| Governance | no policy / approval bypass |
| Durability | exact restart/resume |
| Idempotency | no duplicate side effects |
| Isolation | no tenant leakage |
| Events | full translation into Core protocol |
| Provider | DeepSeek/OpenAI capability tests pass for chosen workloads |
| Cost | acceptable model-call/token overhead |
| Complexity | measurable reduction in application orchestration code |
| Upgrade | pinned version + regression suite viable |

If it only reproduces features already provided by Core + primary kernel with more dependency surface, remove it.

---

# 20. DeepSeek and CrewAI

The CrewAI audit does not change the V3 position on DeepSeek.

DeepSeek remains a **model provider decision**, not a runtime architecture decision.

Preferred path:

```text
COSA ModelPort
      │
      ▼
DeepSeek model adapter
      │
      ▼
ExecutionKernel
```

A CrewAI adapter may use DeepSeek only through a tested provider path.

Required capability matrix:

```text
basic generation
structured output
tool calling
parallel tool calling
streaming
usage
error mapping
reasoning behavior
context limits
call identity stability
```

Do not introduce CrewAI simply to obtain model routing.

---

# 21. Revised migration plan

Keep V3 Phases 0–5.

Insert explicit workflow work before broad multi-agent expansion.

## Phase 0 — Freeze architecture drift

Unchanged.

Additional rule:

- no new CrewAI dependency in production path.

## Phase 1 — Durable Run Foundation

Unchanged.

Add generic `interruptions` schema if practical.

## Phase 2 — ExecutionKernel contract

Unchanged.

## Phase 2.5 — Workflow contracts

Create:

```text
WorkflowSpec
WorkflowDefinition
WorkflowCompiler
WorkflowRegistry
CoordinationRuntime
PendingInterruption
```

Initial runtime supports only:

```text
sequential
parallel
router
agent step
capability step
approval
```

## Phase 3 — OpenAI Agents Kernel MVP

Unchanged.

## Phase 4 — Exact HITL resume

Generalize approval checkpoint handling through `PendingInterruption`.

## Phase 5 — Streaming + cancellation

Add workflow/node events.

## Phase 6 — Specialist agents + deterministic coordination

Replace the earlier “multi-agent runtime” framing with:

```text
WorkflowDefinition
   +
CoordinationRuntime
   +
AgentSpec nodes
```

Retire `orchestration/adk`.

## Phase 6.5 — CrewAI benchmark spike

Implement adapter only in an experimental package/branch.

Do not make it default.

Decide:

```text
KEEP as optional adapter
or
REMOVE after extracting useful patterns
```

## Phase 7 onward

Connector Platform → Memory V2 → Artifacts/Sandbox → reusable package remain unchanged.

---

# 22. New anti-patterns

Add to V3 anti-pattern list:

- making CrewAI `Crew`, `Flow`, `Task` or `Agent` a Core domain type;
- storing framework workflow objects as canonical workflow definitions;
- using runtime-native memory as organizational truth;
- using free-form human feedback as business authorization;
- letting Flow/Crew tools bypass Capability Gateway;
- building orchestration only inside agent prompts;
- representing durable external waits as polling loops inside the LLM;
- coupling workflow definitions to decorators;
- silently degrading a workflow when a selected kernel lacks required semantics;
- adding multi-agent specialists where a deterministic workflow or Skill is sufficient.

---

# 23. Evals additions

Add workflow architecture evals.

## Workflow correctness

```text
correct branch selected
join waits for required branches
parallel failure semantics correct
retry limit respected
workflow output schema valid
```

## Interruption correctness

```text
pause persists
restart resumes
wrong interruption cannot resume run
expired interruption rejected
duplicate callback idempotent
```

## Agent coordination

```text
delegation justified
specialist output actually used
parallel work reduces latency when expected
no unnecessary model calls
synthesis preserves citations/provenance
```

## Framework adapter conformance

Every optional runtime runs the same contract suite:

```text
AgentSpec
WorkflowDefinition
Capability Gateway
Events
Interruptions
Usage
Cancellation
Checkpoint
```

---

# 24. Product implication for COSA Company OS

The new architecture allows COSA to model actual company work rather than only conversations.

Examples:

## Monthly business review

```text
schedule
  ↓
collect finance metrics ─┐
collect sales metrics ───┼─ parallel
collect ops metrics ─────┘
  ↓
CFO/strategy agent analysis
  ↓
artifact: business review
  ↓
founder approval
  ↓
publish / distribute
```

## Customer escalation

```text
CRM event
  ↓
context collection
  ↓
support specialist
  ↓
risk classifier
  ↓
low risk ──→ draft response
high risk ─→ human approval
  ↓
send through connector
  ↓
audit + memory candidate
```

## Strategic research

```text
goal
  ↓
router
  ├─ market research
  ├─ competitor research
  ├─ technical research
  └─ legal/risk research
  ↓
parallel agent nodes
  ↓
synthesis
  ↓
decision memo artifact
```

The user sees an AI Company OS.

Internally, COSA runs a governed workflow platform with selective agent autonomy.

---

# 25. Architectural decision matrix

| Concern | COSA Core | OpenAI Agents Kernel | CrewAI Adapter |
|---|---:|---:|---:|
| Tenant identity | **Owner** | No | No |
| AgentSpec | **Owner** | Adapted | Adapted |
| WorkflowSpec | **Owner** | Consumed indirectly | Adapted |
| Run lifecycle | **Owner** | Execution state | Execution state |
| Workflow coordination | **Owner** | Agent primitives | Optional implementation |
| Exact tool state | Persist adapter state | **Strong primitive** | Must prove |
| Approval business record | **Owner** | Interruption mechanics | Feedback/pause mechanics |
| Capability policy | **Owner** | No | No |
| Credentials | **Owner** | No | No |
| Tool side effects | **Gateway** | Wrapped | Wrapped |
| Idempotency | **Owner** | Supportive | Supportive |
| Canonical memory | **Owner** | No | No |
| Memory algorithms | **Owner** | External | Useful reference |
| Knowledge ACL | **Owner** | No | No |
| Event protocol | **Owner** | Adapted | Adapted |
| Audit | **Owner** | No | No |
| Artifacts | **Owner** | References | References |
| Model routing | **Owner** | Adapter | Adapter |
| Evals | **Owner** | Runtime inputs | Runtime inputs |

---

# 26. CrewAI concepts → COSA mapping

| CrewAI concept | COSA interpretation |
|---|---|
| `Agent` | adapter view of `AgentSpec` |
| `Crew` | one possible agent coordination implementation |
| `Task` | workflow/agent step input, not canonical Core task type |
| `Flow` | inspiration / adapter for `WorkflowDefinition` |
| Flow state | runtime state stored behind COSA checkpoint |
| Flow persistence | adapter persistence mechanism, never canonical RunRepository |
| Human feedback | `HUMAN_INPUT` interruption |
| Async feedback | durable interruption/resume pattern |
| Memory | algorithm/reference or adapter-local memory only |
| Tool | adapter view of `CapabilitySpec` |
| Process | coordination strategy |
| Manager agent | supervisor/delegation pattern |
| Event bus | translated into Core Event Protocol |
| LLM abstraction | provider compatibility input, not Core model policy |
| Knowledge | adapter-local reference; Core owns ACL/provenance truth |

---

# 27. Final architecture after supplement

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                         APPLICATION SHELLS                              │
│                                                                         │
│ COSA Company OS │ Personal Agent │ Dev Agent │ Vertical Apps           │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       COSA AGENT PLATFORM API                           │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       REUSABLE AGENT CORE                              │
│                                                                         │
│ AgentSpec          WorkflowSpec / Definition                           │
│ RunService         CoordinationRuntime                                 │
│ Checkpoints        PendingInterruptions                                │
│ ContextEngine      Capability Gateway                                  │
│ Governance         Connectors                                          │
│ Memory             Knowledge                                           │
│ Artifacts          Events / Audit / Usage / Evals                      │
└──────────────────┬─────────────────────────────┬────────────────────────┘
                   │                             │
          execution port                 capability port
                   │                             │
       ┌───────────┼────────────┐                ▼
       ▼           ▼            ▼        Policy → Approval
 OpenAI Agents  Deterministic  CrewAI     → Credential
 Kernel         Kernel         Adapter     → Idempotency
 primary        tests          optional    → Execution
                                            → Audit
                                            → Event

Model Port:
OpenAI / DeepSeek / Anthropic / future providers

Durable infrastructure:
Postgres or SQLite
Run / Checkpoint / Event / Interruption / Approval
Memory / Knowledge / Artifact stores
```

---

# 28. Final decision

The CrewAI audit strengthens rather than replaces the V3 direction.

The approved architecture should now be read as:

> **COSA is a durable, governed workflow-and-agent platform.**
>
> A workflow provides deterministic structure, lifecycle, waits and coordination.
>
> Agents provide bounded reasoning and adaptive execution inside that structure.
>
> Execution frameworks are replaceable implementations.
>
> COSA retains ownership of identity, policy, capabilities, approvals, durable state, memory, knowledge, artifacts, events, audit and product semantics.

CrewAI is valuable because it demonstrates that production agent systems naturally evolve toward:

```text
Flow
+ State
+ Persistence
+ HITL
+ Agents
+ Observability
```

COSA should adopt those lessons while keeping a stronger platform boundary:

```text
COSA Core
    >
any individual agent framework
```

That boundary is the strategic asset.

---

## Appendix A — Immediate backlog changes

Add the following items to the V3 backlog:

1. Define `WorkflowSpec`.
2. Define serializable `WorkflowDefinition`.
3. Implement `WorkflowCompiler`.
4. Define `CoordinationRuntime`.
5. Implement deterministic sequential/parallel/router primitives.
6. Add `PendingInterruption`.
7. Generalize approval resume on top of interruption/checkpoint semantics.
8. Add `workflow.*`, `interruption.*`, `human_input.*`, `external_wait.*` events.
9. Add interruption and workflow tables.
10. Move specialist coordination to workflow nodes + `AgentSpec`.
11. Build research workflow as first workflow vertical slice.
12. Build exact approval/restart vertical slice.
13. Run CrewAI benchmark only after the Core contracts exist.
14. Keep CrewAI only if measurable workload value exceeds dependency/upgrade cost.

---

## Appendix B — Suggested ADRs

### ADR — Workflow is a Core primitive

**Decision:** Add `WorkflowSpec` and `WorkflowDefinition` as framework-neutral Core contracts.

### ADR — Flow-first execution model

**Decision:** Deterministic workflow orchestration is preferred over autonomous multi-agent orchestration when the process is known.

### ADR — Durable interruption model

**Decision:** Approval, human input and external waits share a generalized checkpoint-backed interruption mechanism.

### ADR — CrewAI integration policy

**Decision:** CrewAI is benchmarked and may be supported as an optional adapter; it is not a Core dependency or architecture root.

### ADR — Framework-owned state is opaque adapter state

**Decision:** Framework checkpoints are versioned opaque state envelopes stored by COSA; Core does not reconstruct framework state machines.

---

## Appendix C — Source areas audited in CrewAI

The architectural conclusions in this supplement were informed by the current CrewAI source structure, especially:

```text
lib/crewai/src/crewai/flow/flow.py
lib/crewai/src/crewai/flow/runtime/
lib/crewai/src/crewai/flow/flow_definition.py
lib/crewai/src/crewai/flow/persistence/
lib/crewai/src/crewai/flow/human_feedback.py
lib/crewai/src/crewai/flow/async_feedback/
lib/crewai/src/crewai/crew.py
lib/crewai/src/crewai/memory/unified_memory.py
lib/crewai/src/crewai/llm.py
lib/crewai/src/crewai/llms/
lib/crewai/pyproject.toml
```

Key patterns adopted conceptually:

```text
authoring / definition / runtime separation
flow state
pause-resume
async human feedback
memory consolidation/scoring
event-driven runtime
flow-first application composition
```

Key areas intentionally not delegated to CrewAI:

```text
tenant identity
canonical run store
canonical workflow definition
governed approvals
capability authorization
credentials
idempotency
canonical memory
organizational knowledge ACL
audit
artifact ownership
```
