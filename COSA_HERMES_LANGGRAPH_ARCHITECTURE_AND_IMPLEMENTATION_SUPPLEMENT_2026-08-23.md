# COSA — Hermes + LangGraph Architecture & Implementation Supplement

> **Revision:** HL1 — 2026-08-23  
> **Status:** Proposed / Not Yet Implemented  
> **Scope:** Hermes-derived Agent Experience/Learning improvements + LangGraph-derived Workflow Runtime improvements  
> **Does not replace:** COSA Canonical Master Architecture, Promotion Implementation Plan, Governance Temporal Model, Paperclip Supplement, or newer ADRs  
> **COSA baseline audited:** `vutasoftvn/javis-saas@e76a26862bddf234c2854284889b0445efbfc150`  
> **Hermes architecture baseline audited:** `NousResearch/hermes-agent@933c209e96630a6026b0a18ecf6a86e65110f5b8`  
> **Hermes repository freshness rechecked:** head observed at `42e39d06469310c251dfa7078fdad6266f3c6d97` on 2026-08-23  
> **LangGraph baseline audited:** `langchain-ai/langgraph@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`, package line `langgraph==1.2.11`  
> **Purpose:** hợp nhất các bài học đáng giá từ Hermes Agent và LangGraph/LangChain ecosystem vào kiến trúc COSA hiện có mà không tạo một architecture root thứ hai.

---

# 0. Executive Decision

Hermes và LangGraph giải hai bài toán khác nhau nhưng bổ sung trực tiếp cho nhau:

```text
Hermes
  → Context
  → Memory
  → Session Recall
  → Skills
  → Learning
  → Delegation ergonomics
  → Tool/runtime readiness
  → Long-lived agent UX

LangGraph
  → Stateful workflow graph
  → Deterministic/parallel execution
  → Checkpointing
  → Pending writes
  → Interrupt/replay
  → Retry/timeout/error handling
  → Dynamic fan-out
  → Subgraphs
  → Fault tolerance
```

COSA không nên chọn một trong hai làm architecture root.

Target relationship:

```text
                           COSA Agent Platform
                                  │
                 ┌────────────────┴────────────────┐
                 │                                 │
                 ▼                                 ▼
        Agent Experience Plane             Workflow Runtime Plane
        inspired by Hermes                potentially backed by
                 │                            LangGraph
                 ▼                                 ▼
      Context / Memory / Skills        COSA WorkflowEngine contract
      Learning / Delegation UX                  │
                 │                              ▼
                 └──────────────┬────── LangGraph adapter
                                │
                                ▼
                         COSA Run Platform
                                │
                 ┌──────────────┴─────────────┐
                 │                            │
                 ▼                            ▼
         ExecutionKernel               Capability Gateway
       OpenAI Agents SDK*                    │
                                             ▼
                                 Governance / Approval / Audit
                                             │
                                             ▼
                                   Company Business Services
```

`*` Official OpenAI Agents SDK remains the intended kernel target. A custom OpenAI-compatible loop must not be mistaken for completion of that integration.

## 0.1. Final high-level recommendation

### Hermes

Use as **architectural prior art**, not runtime dependency.

### LangGraph

Treat as a **genuine candidate dependency for the implementation of COSA WorkflowEngine**, behind COSA-owned contracts.

### LangChain

Use selectively only where required by LangGraph or where individual integrations clearly help. Do **not** make generic LangChain chains/agents the COSA platform ontology.

---

# 1. Architectural Authority

When this supplement conflicts with other material, use:

```text
Approved newer ADR
    >
COSA Canonical Master Architecture
    >
Current code truth
    >
This supplement
    >
External Hermes/LangGraph behavior
```

External frameworks never own:

```text
Company business truth
WorkforceMember identity
Tenant/company authorization
COSA Run identity
PinnedSpecIdentity
Approval authority
CapabilitySpec
Connector grants
Temporal governance
Business idempotency contract
```

---

# 2. Current COSA Baseline

The relevant canonical code already exists under:

```text
packages/agent_core/
├── artifacts/
├── capabilities/
├── contracts/
├── coordination/
├── evals/
├── governance/
├── kernel/
├── knowledge/
├── memory/
├── plugins/
├── runs/
└── workflows/

apps/cosa/
```

Therefore this document is a **delta**, not a greenfield rewrite.

## 2.1. Existing useful foundations

COSA already has:

- `AgentSpec`;
- `PinnedSpecIdentity`;
- `SpecResolutionManifest`;
- durable Run direction;
- capability/governance contracts;
- WorkflowSpec + WorkflowEngine;
- coordination primitives;
- memory and knowledge packages;
- plugin manifest/registry beginnings;
- COSA application composition.

## 2.2. Confirmed gaps relevant to this supplement

At the audited baseline, searches found no canonical:

```text
SkillSpec
ContextAssembler
```

and existing delegation remains a thin wrapper:

```text
SpecialistDelegate
→ create RunRequest
→ pin child AgentSpec
→ kernel.run()
```

with no explicit durable delegation envelope, authority attenuation contract, or rich child-run control semantics.

## 2.3. Workflow runtime remains custom

Current `packages/agent_core/workflows/engine.py` implements:

- linear pipeline;
- static declarative DAG;
- `asyncio.gather` parallel waves;
- approval pause;
- compensation;
- in-object checkpoints;
- step outcomes.

This is a useful architecture asset but overlaps significantly with LangGraph's mature runtime machinery.

---

# 3. External System Classification

| External project | Primary value to COSA | Dependency candidate? | Architecture root? |
|---|---|---:|---:|
| Hermes Agent | Agent UX, context, memory, skills, learning, delegation | No | No |
| LangGraph | Workflow execution runtime, checkpoint/fault tolerance | **Yes, spike required** | No |
| LangChain Core | Runnable/integration substrate required by LangGraph | Incidental/selective | No |
| OpenAI Agents SDK | Agent execution kernel | Yes / intended | No |
| Paperclip | Durable control-plane prior art | No | No |

---

# 4. Combined Mental Model

Hermes and LangGraph together suggest a more complete Agent Platform model:

```text
                    PUBLISHED BEHAVIOR
            AgentSpec / WorkflowSpec / SkillSpec?
                        │
                        ▼
                Context Assembly
        ┌───────────────┼────────────────┐
        │               │                │
        ▼               ▼                ▼
 Conversation        Memory          Knowledge
  History                              Sources
        │               │                │
        └───────────────┼────────────────┘
                        ▼
                 Execution Layer
        ┌───────────────┴────────────────┐
        │                                │
        ▼                                ▼
 ExecutionKernel                   WorkflowEngine
 OpenAI Agents SDK              LangGraph candidate
        │                                │
        └──────────────┬─────────────────┘
                       ▼
               Capability Gateway
                       │
                       ▼
             Governance / Approval
                       │
                       ▼
                Business Services

                 OBSERVATION LOOP
                       │
                       ▼
                Learning Extractor
                       │
               ┌───────┴────────┐
               ▼                ▼
        MemoryCandidate     SkillCandidate
                                │
                           Eval / Review
                                │
                           Publish version
```

The critical boundary:

> **Execution consumes published, versioned behavior. Learning produces candidates.**

---

# 5. Hermes: What to Adopt

Hermes is strongest in the following areas:

1. Context lifetime layering.
2. Curated memory vs raw conversation history.
3. Searchable cross-session recall.
4. Progressive skill disclosure.
5. Closed learning loop.
6. Subagent context isolation.
7. Delegation authority reduction.
8. Child-agent steer/stop/status UX.
9. Tool readiness/discovery.
10. Plugin/skill trust and quarantine.
11. Provider/runtime resolution.
12. Hard security floors.

COSA should adopt the **semantics**, not Hermes' monolithic `AIAgent`.

---

# 6. LangGraph: What to Adopt or Evaluate

LangGraph is strongest in:

1. `StateGraph` state transition model.
2. reducer-based state merging.
3. Pregel superstep scheduling.
4. first-class checkpointing.
5. checkpoint pending writes.
6. interrupt/replay.
7. durable `task`.
8. retry/timeout/error policies.
9. dynamic `Send` fan-out.
10. subgraphs.
11. checkpoint namespaces.
12. replay/fork/time-travel operations.
13. separation of mutable State and run-scoped Context.
14. checkpoint conformance and Postgres/SQLite saver ecosystem.

Unlike Hermes, this is sufficiently close to COSA WorkflowEngine that it should be evaluated as a runtime dependency.

---

# 7. Important Semantic Difference: Hermes vs LangGraph

Hermes centers the **agent process**:

```text
Agent
→ prompt
→ tools
→ memory
→ skills
→ subagents
→ session
```

LangGraph centers **stateful computation**:

```text
State
→ ready nodes
→ parallel writes
→ reducer
→ checkpoint
→ next superstep
```

COSA should keep both concerns separate:

```text
Agent concerns
≠
Workflow state-machine concerns
```

Do not rebuild a Hermes-like god-loop and do not make LangGraph state the entire agent/company state.

---

# 8. ADD — Context Architecture

Hermes provides the strongest motivation for a formal Context Assembly layer.

LangGraph reinforces the design by distinguishing:

```text
mutable graph state
≠
runtime context
```

COSA should formalize three layers:

```text
1. Execution State
   mutable
   checkpointed
   workflow/run execution state

2. Run Context
   run-scoped
   non-model operational context
   tenant/principal/correlation/environment/leases

3. Prompt Context
   model-visible projection
   memory/history/knowledge/skills/current task information
```

## 8.1. Proposed package

```text
packages/agent_core/context/
├── __init__.py
├── contracts.py
├── assembler.py
├── budget.py
├── snapshots.py
└── provenance.py
```

## 8.2. Context lifetime

Suggested lifecycle:

```text
STABLE
RUN
CURRENT
EPHEMERAL
```

Examples:

| Fragment | Lifetime |
|---|---|
| Agent identity/instructions | STABLE |
| Company/project context for current Run | RUN |
| Current KPI snapshot | CURRENT |
| Approval answer / temporary user correction | EPHEMERAL |

## 8.3. ContextFragment

Conceptual contract:

```text
ContextFragment
    source_kind
    source_ref
    lifetime
    content
    token_estimate
    sensitivity
    provenance
    freshness
    cache_key?
```

## 8.4. ContextSnapshot

Kernel should receive a resolved `ContextSnapshot`, rather than independently querying:

```text
memory
knowledge
conversation
skills
company adapters
```

This prevents kernel growth into a Hermes-style god-runtime.

---

# 9. Memory, History, Knowledge, Business Truth

Hermes offers a valuable separation:

```text
Curated memory
≠
raw session history
```

COSA must go further:

```text
Working Context
≠
Curated Memory
≠
Conversation History
≠
Knowledge
≠
Business Truth
```

## 9.1. Curated Memory

Use for:

- preferences;
- durable lessons;
- stable environment facts;
- agent/user conventions;
- learned summaries.

Not for:

- invoice authoritative status;
- ledger values;
- CRM opportunity truth;
- authorization;
- company entitlements.

## 9.2. Conversation History

Product continuity layer:

```text
conversation
messages
attachments
run links
thread lineage
search
```

Preferred owner:

```text
apps/cosa/conversations/
```

Agent Core consumes via a port.

## 9.3. Knowledge

Referenceable sourced information:

```text
documents
policies
manuals
company references
uploaded files
citations
```

Owner:

```text
packages/agent_core/knowledge/
```

## 9.4. Business Truth

Always remains in:

```text
services/company/
services/cosa/
```

No external agent framework memory/store is authoritative.

---

# 10. Conversation Recall

Hermes uses full-text search over session history instead of forcing all history into vectors.

COSA should implement staged retrieval:

```text
1. structured filters
2. exact/lexical FTS
3. optional trigram/fuzzy search
4. semantic retrieval where needed
5. LLM synthesis only after retrieval
```

## 10.1. Proposed app owner

```text
apps/cosa/conversations/
├── models.py
├── repository.py
├── search.py
├── service.py
└── ports.py
```

## 10.2. Core port

Conceptual:

```python
class ConversationHistoryProvider(Protocol):
    async def recent_messages(...)
    async def search_messages(...)
    async def get_thread_context(...)
```

## 10.3. Invariant

```text
Conversation ID
≠
Run ID
≠
Workflow execution thread/checkpoint ID
```

Do not collapse these identities for convenience.

---

# 11. Skills — Proposed New Product Runtime Concept

`.agents/skills/` or developer-agent assets must not automatically become product runtime skills.

If implemented, create a canonical runtime concept:

```text
packages/agent_core/skills/
```

## 11.1. Proposed structure

```text
packages/agent_core/skills/
├── contracts.py
├── registry.py
├── loader.py
├── resolution.py
├── candidates.py
├── evaluation.py
└── publication.py
```

## 11.2. SkillSpec

Conceptual:

```text
SkillSpec
    id
    version
    definition_hash
    description
    instructions
    applicability
    required_capabilities
    required_knowledge
    references
    provenance
    publisher
    status
```

## 11.3. Lifecycle

```text
DRAFT
→ CANDIDATE
→ EVALUATED
→ APPROVED
→ PUBLISHED
→ RETIRED
```

Only published immutable versions enter canonical execution.

---

# 12. Progressive Skill Disclosure

Adopt Hermes' strongest skill UX pattern:

```text
L0
  skill index:
  id/name/description/tags

L1
  selected SkillSpec instructions

L2
  referenced examples/templates/assets
  loaded on demand
```

This avoids:

```text
100 skills
→ inject 100 full skill bodies into every prompt
```

and instead supports:

```text
cheap index
→ select relevant skill
→ load exact pinned version
```

---

# 13. Procedural Memory vs Skill

Existing COSA `MemoryKind.PROCEDURAL` should not silently become executable behavior.

Recommended meaning:

```text
PROCEDURAL MEMORY
=
learned procedural observation
or candidate lesson
```

Not:

```text
PROCEDURAL MEMORY
=
automatically executable workflow/skill
```

Promotion:

```text
Procedural Memory
       ↓
SkillCandidate
       ↓
evaluation
       ↓
immutable SkillSpec publication
```

Deterministic multi-step business procedure may instead become a WorkflowSpec.

---

# 14. Governed Learning Loop

Hermes demonstrates that long-lived agents benefit from:

```text
experience
→ lesson
→ memory / skill
→ future reuse
```

COSA should implement a governed version:

```text
Run/Workflow outcome
       ↓
Learning Extractor
       ↓
Candidate artifact
       ↓
provenance
       ↓
eval
       ↓
policy/human review
       ↓
publish immutable version
```

## 14.1. Candidate categories

```text
MemoryCandidate
SkillCandidate
WorkflowChangeCandidate
Prompt/AgentSpecChangeCandidate
```

## 14.2. No direct self-mutation

Forbidden:

```text
background learning process
→ edits published AgentSpec/WorkflowSpec/SkillSpec in place
```

Required:

```text
candidate
→ new immutable version
→ explicit publication
```

---

# 15. Behavioral Dependency Closure

Hermes reveals an extension of the existing spec-pinning problem.

Current L1:

```text
AgentSpec
WorkflowSpec
```

Future:

```text
AgentSpec@4
  depends on SkillSpec@7
```

Run pauses.

Skill v8 publishes.

Which version resumes?

This requires an ADR.

## 15.1. Proposed criterion

If changing an artifact can alter:

```text
control flow
tool selection
capability invocation semantics
approval-related behavior
```

without changing AgentSpec/WorkflowSpec, then the artifact is **execution-defining** and should be evaluated for pinning.

## 15.2. Do not change PinnedSpecIdentity immediately

Do not prematurely expand:

```text
spec_kind = agent | workflow | skill
```

until SkillSpec semantics exist and tests prove it is necessary.

But design Skill publication so future pinning is possible.

---

# 16. Delegation — Hermes Improvements to Existing COSA Coordination

Existing `SpecialistDelegate` is a good minimal primitive but needs stronger semantics.

Target:

```text
Parent Run
     │
     ├── DelegationEnvelope
     │
     ▼
Child Run
     ├── pinned child AgentSpec
     ├── independent checkpoint
     ├── events
     ├── tool calls
     ├── approvals
     └── budget
```

## 16.1. Authority attenuation

Canonical invariant:

```text
Authority(child)
⊆
Authority(parent)
```

Effective child authority:

```text
delegated capability ceiling
∩ child AgentSpec capability_refs
∩ current PrincipalAuthorization
∩ current TenantPolicy
∩ current ConnectorGrant
∩ current CapabilityGovernance
```

A specialist declaration can never expand authority above the parent delegation ceiling.

## 16.2. DelegationEnvelope

Conceptual:

```text
delegation_id
parent_run_id
child_run_id
parent_spec_identity
child_spec_identity
goal
context_snapshot_ref
delegated_capability_ceiling
budget
depth
model_policy_override?
status
created_at
```

## 16.3. Context isolation

Child should default to:

```text
explicit delegated task
selected context
selected skills
selected capabilities
```

not whole parent transcript.

## 16.4. Return boundary

Default return to parent:

```text
structured result
summary
artifacts
citations
status
```

not every child internal model/tool event.

Detailed child trace remains inspectable through observability.

---

# 17. Delegation Control UX

Hermes' `list / steer / stop` semantics are worth adopting.

Potential commands/events:

```text
delegation.created
delegation.started
delegation.steer_requested
delegation.cancel_requested
delegation.completed
delegation.failed
```

`steer` must be durable:

```text
control event
→ child Run input/control channel
```

not:

```text
mutate an in-memory Python object only
```

---

# 18. Capability Readiness

Hermes distinguishes registered tools from tools actually usable now.

COSA should add:

```text
CapabilityReadiness
```

Conceptual:

```text
capability_id
ready
reason_code
observed_at
ttl
connector_ref?
credential_ref?
```

Possible reason codes:

```text
READY
MISSING_CREDENTIAL
CONNECTOR_OFFLINE
TENANT_DISABLED
BACKEND_UNAVAILABLE
SCHEMA_MISMATCH
DEPENDENCY_MISSING
```

## 18.1. Readiness is not authorization

Never merge:

```text
ready = true
```

with:

```text
authorized = true
```

Final gate remains governance.

## 18.2. Technical caching only

Short-lived readiness caching can be acceptable for technical health.

Never reuse stale authorization.

---

# 19. Plugin / Extension Trust Lifecycle

Hermes' skill/plugin handling motivates stronger trust lifecycle.

Current COSA plugin primitives should evolve toward:

```text
DISCOVERED
→ QUARANTINED
→ SCANNED
→ VERIFIED
→ INSTALLED
→ TENANT_ENABLED
→ ACTIVE
```

with:

```text
REJECTED
DISABLED
REVOKED
```

as terminal/administrative states.

Plugin metadata should eventually include:

```text
identity
version
hash
publisher
source
declared capabilities
required permissions
connector requirements
scan result
installation provenance
trust/signing metadata
```

A plugin does not bypass:

```text
Capability Gateway
Governance
Run tool-call ledger
```

---

# 20. Hard Non-Approvable Safety Floor

Hermes has operations that remain blocked even when normal approval settings are permissive.

COSA should model:

```text
NON_APPROVABLE
```

or an equivalent hard-deny capability policy.

Ordering:

```text
Hard Deny
    >
Current Governance
    >
Approval Evidence
    >
Autonomy Level
```

Possible domain examples to consider:

```text
disable audit
export all secrets
delete entire tenant
mutate governance system
irreversibly transfer company ownership
```

Exact domain list requires separate policy ADR.

---

# 21. Sandbox Boundary

Hermes' execution backends are useful prior art:

```text
local
Docker
SSH
serverless sandbox
...
```

COSA may later adopt execution backend abstractions for code/terminal tasks.

But:

> **Sandbox isolation is not business authorization.**

All business side effects continue through Capability Gateway.

---

# 22. LangGraph State Model

LangGraph `StateGraph` gives each node:

```text
State → Partial<State>
```

and state keys may have reducers.

COSA should either adopt LangGraph or copy this invariant:

> Parallel workflow nodes produce isolated writes; a deterministic reducer composes them into the next state.

For:

```text
parallel research
parallel specialists
multi-source evidence
map/reduce
fan-out
```

avoid ambiguous shared dict mutation.

---

# 23. LangGraph Pregel Supersteps

LangGraph execution follows:

```text
PLAN
→ find ready actors

EXECUTE
→ run ready actors in parallel

UPDATE
→ commit channel writes

repeat
```

Writes from the current superstep are invisible to sibling nodes until the update phase.

This is a substantially more formal execution model than ad-hoc `asyncio.gather + state.update`.

---

# 24. LangGraph Checkpoint Model

LangGraph checkpointing tracks more than serialized state:

```text
checkpoint id
timestamp
channel values
channel versions
versions seen by nodes
updated channels
metadata
parent checkpoints
pending writes
```

COSA's canonical durability still owns:

```text
Run
checkpoint identity
spec manifest
events
tool-call ledger
approval
```

If adopted:

```text
LangGraph checkpoint
=
opaque workflow-runtime execution state
```

not the entire COSA Run truth.

---

# 25. Pending Writes — High-Value LangGraph Invariant

Suppose a parallel wave:

```text
A
B
C
```

A/B finish, C fails.

Target invariant:

```text
partial parallel success
→ successful branch results persist
→ recovery retries only unfinished/failed work
```

This is one of the highest-value reasons to evaluate LangGraph instead of extending current custom DAG execution indefinitely.

---

# 26. LangGraph Interrupt Semantics

LangGraph `interrupt()` does not restore the Python instruction pointer after the interrupt.

On resume, the containing node is replayed from its start, with interrupt value supplied from persisted resume state.

Correctness therefore depends on:

```text
deterministic replay
+
durable task boundaries
+
idempotent side effects
```

COSA must not weaken its own exact approval binding:

```text
run_id
tool_call_id
checkpoint_ref
payload identity
target identity
governance
```

LangGraph interrupt is workflow control machinery, not authorization.

---

# 27. Durable Tasks vs Capability Gateway

LangGraph durable tasks are useful for non-deterministic workflow operations.

But business writes must remain:

```text
LangGraph node/task
       ↓
Capability Gateway
       ↓
exact invocation ledger
       ↓
Governance
       ↓
Idempotency
       ↓
Business service
```

LangGraph durability does not automatically solve exactly-once external side effects.

---

# 28. Retry, Timeout and Error Handling

LangGraph offers first-class:

```text
RetryPolicy
TimeoutPolicy
error handlers
cache policy
```

COSA should avoid reimplementing equivalent scheduler machinery unless a COSA-specific requirement demands it.

COSA-specific compensation/Saga semantics remain platform-owned.

---

# 29. Dynamic Fan-Out

LangGraph `Send` supports runtime-dependent fan-out:

```text
collect N entities
→ create N tasks
→ aggregate results
```

Potential COSA uses:

- market evidence collection;
- specialist review;
- document processing;
- entity validation;
- dynamic delegation.

Do not modify WorkflowSpec to mimic every LangGraph primitive before the runtime spike proves value.

---

# 30. Subgraphs

LangGraph subgraphs can model:

```text
main workflow
├── finance subworkflow
├── legal subworkflow
└── strategy subworkflow
```

COSA must preserve:

```text
pinned WorkflowSpec
auditable subexecution identity
governance
capability ledger
```

Subgraph namespace alone is not a business audit identity.

---

# 31. State vs Runtime Context

LangGraph reinforces a three-layer COSA model:

```text
Execution State
  mutable/checkpointed

Run Context
  principal
  tenant/company
  environment
  correlation
  model routing
  execution metadata

Prompt Context
  model-visible fragments
```

Not all runtime context is model-visible.

---

# 32. LangGraph Checkpointer vs Store

LangGraph separates execution checkpoint state from long-term store data.

COSA should keep an even stronger decomposition:

```text
Run durability
Memory
Knowledge
Conversation
Business Truth
```

Do not make LangGraph Store canonical for all persistence.

---

# 33. Workflow Definition Pinning

This is a mandatory COSA override.

COSA invariant:

```text
Run started on WorkflowSpec v1
→ v2 published
→ old Run resumes v1
```

If LangGraph is adopted:

```text
COSA Run
→ PinnedSpecIdentity
→ load exact WorkflowSpec version/hash
→ compile exact graph
→ attach checkpoint
→ resume
```

Never compile latest workflow during resume.

---

# 34. `thread_id` Mapping

LangGraph `thread_id` is a checkpoint persistence key.

Do not map it automatically to `conversation_id`.

Preferred first spike:

```text
LangGraph thread_id
≈ COSA run_id
```

or an internal workflow execution id.

Keep:

```text
conversation_id
run_id
checkpoint_ref
workflow_spec_identity
```

separate.

---

# 35. Time Travel and Run Fork

LangGraph replay/fork is useful for debugging and operator repair.

COSA should expose it as an auditable Run Fork:

```text
Run R1
  checkpoint C4
       ↓
operator changes allowed input/state
       ↓
Run R2
  parent_run_id = R1
  fork_checkpoint_ref = C4
```

Never pretend business side effects committed before the fork did not happen.

---

# 36. LangGraph Adoption Boundary

Do not expose LangGraph directly to:

```text
Flutter
services/company
business policy code
```

Keep a platform-owned abstraction:

```text
WorkflowRuntime Protocol
        │
        ├── NativeWorkflowRuntime
        └── LangGraphWorkflowRuntime
```

or equivalent.

COSA WorkflowEngine remains the public platform abstraction.

---

# 37. Proposed Workflow Compiler

```text
WorkflowSpec
    ↓
WorkflowCompiler
    ↓
LangGraph StateGraph
    ↓
Compiled graph
```

Mapping:

```text
DETERMINISTIC
→ normal graph node

AGENT
→ node calling ExecutionKernel

TOOL_CALL
→ node calling Capability Gateway

APPROVAL_GATE
→ COSA approval/governance
  + LangGraph interrupt as optional control primitive

depends_on
→ graph edges/joins

parallel branches
→ parallel ready nodes

compensation
→ COSA-defined failure/compensation path
```

COSA `WorkflowSpec` stays canonical.

---

# 38. Persistence Options for LangGraph Spike

## Option A — Native LangGraph Postgres saver

```text
COSA canonical Run tables
+
LangGraph checkpoint tables
```

Recommended for the spike because it minimizes custom durability code.

## Option B — COSA custom `BaseCheckpointSaver`

Potential future optimization.

Do not start here because the saver contract includes:

```text
pending writes
parents
namespaces
history/list
fork/copy
prune
channel versions
```

A custom saver should only be built after LangGraph runtime fit is proven.

---

# 39. Combined Package Delta

```text
packages/agent_core/
├── context/                         # ADD
│   ├── contracts.py
│   ├── assembler.py
│   ├── budget.py
│   ├── snapshots.py
│   └── provenance.py
│
├── skills/                          # ADD
│   ├── contracts.py
│   ├── registry.py
│   ├── loader.py
│   ├── resolution.py
│   ├── candidates.py
│   ├── evaluation.py
│   └── publication.py
│
├── capabilities/
│   └── readiness.py                 # ADD
│
├── coordination/
│   ├── delegate.py                  # ADJUST
│   └── delegation_models.py         # ADD if justified
│
├── workflows/
│   ├── runtime.py                   # framework-neutral runtime protocol
│   ├── langgraph_runtime.py         # SPIKE
│   ├── langgraph_compiler.py        # SPIKE
│   └── ... existing
│
└── plugins/
    └── trust.py                     # ADD when installation becomes real

apps/cosa/
├── conversations/
└── skills/                          # optional COSA-specific definitions
```

Do not add duplicate roots such as:

```text
hermes_runtime/
langchain_agent/
langgraph_business_state/
session_db/
learning_runtime/
tool_registry_v2/
```

---

# 40. LangChain Usage Policy

LangGraph depends on LangChain Core.

That does not imply broad adoption of generic LangChain abstractions.

Allowed:

```text
LangGraph internal dependency
specific provider/document integrations
specific utility when clearly superior
```

Keep COSA canonical contracts framework-neutral:

```text
ExecutionKernel
WorkflowEngine
CapabilitySpec
RunRequest
RunResult
AgentSpec
WorkflowSpec
```

Do not replace them with:

```text
Chain
Runnable
AgentExecutor
```

as platform ontology.

---

# 41. Kernel Guardrail

A custom OpenAI-compatible loop should not be allowed to grow into a Hermes-style god-runtime.

Target:

```text
LangGraph Workflow node
→ ExecutionKernel
→ official OpenAI Agents SDK adapter
```

not:

```text
LangGraph
→ custom agent loop with memory/context/delegation/tool special cases
```

Context, memory, skills, workflow and governance remain separate owners.

---

# 42. AgentSpec Guardrail

Before adding Skills/Learning, align app-level AgentSpec vocabulary with canonical fields such as:

```text
capability_refs
```

Executable configuration should fail fast on unknown fields.

Silent contract drift becomes more dangerous once execution depends on:

```text
skills
context policies
coordination policies
capability lists
```

---

# 43. Implementation Sequence

## Phase A — Foundation truth

1. Align AgentSpec vocabulary/fail-fast validation.
2. Verify official OpenAI Agents SDK integration status.
3. Finish critical Run/Approval/Capability durability.
4. Freeze a framework-neutral WorkflowRuntime boundary.

## Phase B — LangGraph spike

5. Add isolated optional LangGraph dependency.
6. Compile a COSA WorkflowSpec into StateGraph.
7. Use native Postgres checkpointer.
8. Prove process restart/resume.
9. Prove old Run uses pinned WorkflowSpec after v2 publication.
10. Prove COSA approval and Capability Gateway integration.
11. Prove parallel pending-write recovery.
12. Compare complexity/performance/test burden against native runtime.

## Phase C — Hermes context/recall

13. Add Context Assembly.
14. Add ConversationHistoryProvider.
15. Add lexical/hybrid search.
16. Harden memory provenance/staleness.

## Phase D — Delegation

17. Add DelegationEnvelope.
18. Add parent-child durable Run relationship.
19. Enforce authority attenuation.
20. Add status/cancel/steer events.

## Phase E — Skills/Learning

21. Add SkillSpec.
22. Add progressive loading.
23. Add SkillCandidate.
24. Add eval/review/publication.
25. Decide Skill pinning ADR.

## Phase F — Extensibility

26. Add capability readiness.
27. Add plugin trust lifecycle.
28. Add hard non-approvable policy where needed.

---

# 44. LangGraph Spike Workflow

Use one graph that exercises real COSA boundaries:

```text
START
  │
  ▼
ReadBusinessContext
  │
  ├───────────────┐
  ▼               ▼
ResearchA      ResearchB
  │               │
  └───────┬───────┘
          ▼
      AgentStep
 OpenAI Agents Kernel
          │
          ▼
 GovernedWriteProposal
          │
          ▼
   Approval Boundary
          │
          ▼
   Capability Gateway
          │
          ▼
         END
```

The graph must be generated from COSA `WorkflowSpec`.

---

# 45. Acceptance Test Matrix

## HL-01 — Context lifetime

Stable fragments stay stable when CURRENT/EPHEMERAL facts change.

## HL-02 — Business truth beats stale memory

Business service result is authoritative.

## HL-03 — Conversation tenant isolation

No cross-tenant recall under lexical/semantic/hybrid search.

## HL-04 — Progressive skill disclosure

Only index is loaded globally; exact selected skill version loads on demand.

## HL-05 — Candidate does not mutate live skill

Candidate v2 cannot affect Runs until publication.

## HL-06 — Child authority attenuation

Child capability set cannot exceed parent delegation ceiling.

## HL-07 — Current revocation narrows child

Revoked connector/principal permission blocks later child execution.

## HL-08 — Child Run restart

Child resumes same pinned execution without duplicate side effects.

## HL-09 — Readiness vs authorization

Ready does not imply allowed; allowed does not imply technically ready.

## HL-10 — Hard deny dominates

Non-approvable action remains denied despite approval/autonomy.

## HL-11 — WorkflowSpec compiler

Same immutable WorkflowSpec compiles deterministically.

## HL-12 — Workflow version pinning with LangGraph

v1 paused Run resumes v1 after v2 publication.

## HL-13 — Parallel pending-write recovery

Successful sibling branch outputs survive crash/failure.

## HL-14 — Approval resume

COSA exact invocation identity and temporal governance remain authoritative.

## HL-15 — Side-effect crash window

Remote success before local commit does not produce duplicate side effect after replay.

## HL-16 — Thread identity

Two Runs in one Conversation do not accidentally share graph execution state.

## HL-17 — Run fork

Replay/fork produces explicit lineage instead of mutating original history.

## HL-18 — Checkpoint serialization security

Production checkpoint serialization rejects or controls unsafe arbitrary object reconstruction.

---

# 46. Decision Gate for LangGraph Adoption

Adopt LangGraph only if the spike proves:

### Functional

- WorkflowSpec maps cleanly.
- AgentStep uses ExecutionKernel.
- ToolStep uses Capability Gateway.
- Approval remains COSA-owned.
- Compensation remains expressible.

### Durability

- real process restart works;
- successful parallel writes are preserved;
- exact pinned WorkflowSpec reload works;
- subgraph semantics are understood.

### Security

- checkpoint serializer/config is acceptable;
- tenant/thread namespaces are isolated;
- no LangGraph Store business truth;
- no governance bypass.

### Operational

- Postgres saver lifecycle is manageable;
- run events can bridge into COSA observability;
- retention/pruning is understood.

### Complexity

The framework is adopted only if:

```text
custom code removed
+
failure semantics improved
+
tests simplified/strengthened
```

outweigh:

```text
framework coupling
+
extra persistence
+
integration complexity
```

---

# 47. If the LangGraph Spike Fails

Keep COSA-native WorkflowEngine, but promote these ideas:

```text
superstep execution
reducer-based writes
pending-write durability
State vs Context separation
dynamic fan-out
node retry/timeout/error policy
checkpoint ancestry
Run fork semantics
```

Hermes-derived work remains independent of LangGraph adoption.

---

# 48. Explicit Rejections

- **REJECT:** Hermes `AIAgent` as ExecutionKernel.
- **REJECT:** generic LangChain AgentExecutor as COSA platform root.
- **REJECT:** LangGraph state as company/business state.
- **REJECT:** LangGraph Store as canonical business database.
- **REJECT:** LangGraph interrupt as approval authority.
- **REJECT:** direct LangGraph business writes.
- **REJECT:** self-learning direct mutation of published behavior.
- **REJECT:** process-local delegation as durable truth.
- **REJECT:** sandbox isolation as business authorization.
- **REJECT:** framework leakage into Flutter/business services.

---

# 49. Priority

## P0

1. AgentSpec contract alignment.
2. Official OpenAI Agents SDK truth.
3. Critical durable Run/Approval/Capability path.
4. Framework-neutral WorkflowRuntime boundary.
5. LangGraph spike.

## P1

1. Context Assembly.
2. Conversation recall/search.
3. Memory provenance.
4. DelegationEnvelope.
5. Authority attenuation.
6. Durable child Runs.
7. Capability readiness.
8. LangGraph adoption decision.

## P2

1. SkillSpec.
2. Progressive skills.
3. Governed learning.
4. Skill pinning ADR.
5. Rich delegation steer/stop.
6. Plugin trust/quarantine.
7. Sandbox execution backends.
8. Advanced Run fork/time travel.

---

# 50. Target Architecture if LangGraph Passes

```text
                        apps/cosa
                           │
                           ▼
                   packages/agent_core
                           │
      ┌────────────────────┼───────────────────────┐
      │                    │                       │
      ▼                    ▼                       ▼
 Context/Skills       ExecutionKernel        WorkflowEngine
 Memory/Knowledge    OpenAI Agents SDK            │
 Conversation Port                                ▼
      │                                  LangGraphWorkflowRuntime
      │                                            │
      └────────────────┬───────────────────────────┘
                       ▼
                Capability Gateway
                       │
            Governance / Approval / Audit
                       │
                       ▼
                 services/company
```

LangGraph remains an implementation detail behind WorkflowEngine.

Hermes remains architectural prior art.

---

# 51. Target Architecture if LangGraph Does Not Pass

```text
WorkflowEngine
  COSA-native
```

enhanced with:

```text
supersteps
reducers
pending writes
state/context separation
dynamic fanout
strong checkpoint ancestry
fault tolerance
```

All Hermes-derived improvements still proceed independently.

---

# 52. Open ADRs

1. **LangGraph backend adoption.**
2. **Native PostgresSaver vs custom COSA saver.**
3. **Which Skills become execution-defining and pinned.**
4. **Which context fragments must be persisted for exact resume.**
5. **Conversation search backend.**
6. **Learning publication approval policy.**
7. **Delegation persistence representation.**
8. **Hard non-approvable policy representation.**
9. **Run fork API/storage semantics.**
10. **When LangGraph subgraph deserves a separately auditable child Run.**

---

# 53. Source Pins

## COSA

```text
vutasoftvn/javis-saas
e76a26862bddf234c2854284889b0445efbfc150
```

Key areas:

```text
packages/agent_core/contracts/spec.py
packages/agent_core/coordination/delegate.py
packages/agent_core/workflows/
packages/agent_core/memory/
packages/agent_core/plugins/
packages/agent_core/kernel/
apps/cosa/
```

## Hermes

Architecture audit:

```text
NousResearch/hermes-agent
933c209e96630a6026b0a18ecf6a86e65110f5b8
```

Freshness rechecked at repository head:

```text
42e39d06469310c251dfa7078fdad6266f3c6d97
```

## LangGraph

```text
langchain-ai/langgraph
f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f
langgraph 1.2.11
```

Key areas:

```text
libs/langgraph/langgraph/graph/state.py
libs/langgraph/langgraph/pregel/
libs/langgraph/langgraph/func/
libs/checkpoint/langgraph/checkpoint/
libs/checkpoint-postgres/
README.md
```

---

# 54. Final Disposition Matrix

| Concept | Source | COSA disposition |
|---|---|---|
| Context lifetime | Hermes | **ADD** |
| Curated memory | Hermes | **HARDEN** |
| Conversation FTS recall | Hermes | **ADD** |
| Progressive skills | Hermes | **ADD** |
| Learning loop | Hermes | **ADD governed lifecycle** |
| Delegation isolation | Hermes | **ADJUST** |
| Authority attenuation | Hermes | **ADD invariant** |
| Steer/stop | Hermes | **P2** |
| Capability readiness | Hermes | **ADD** |
| Plugin trust/quarantine | Hermes | **HARDEN** |
| Hard safety floor | Hermes | **ADD** |
| Hermes AIAgent loop | Hermes | **REJECT** |
| State reducers | LangGraph | **SPIKE/ADOPT** |
| Pregel supersteps | LangGraph | **SPIKE/ADOPT** |
| Pending writes | LangGraph | **HIGH-VALUE ADOPT** |
| Checkpointer | LangGraph | **SPIKE dependency** |
| Interrupt | LangGraph | **control mechanism only** |
| Durable task | LangGraph | **ADAPT under Capability Gateway** |
| Dynamic fan-out | LangGraph | **ADOPT if backend chosen** |
| Subgraphs | LangGraph | **ADOPT with COSA identity** |
| Time travel | LangGraph | **ADAPT as Run Fork** |
| LangGraph Store as business truth | LangGraph | **REJECT** |
| Graph migration for paused COSA Run | LangGraph | **OVERRIDE with pinned WorkflowSpec** |
| Generic LangChain ontology | LangChain | **REJECT** |

---

# 55. Closing Invariants

1. Business truth remains in Company/COSA services.
2. Execution consumes immutable published behavior.
3. Learning produces candidates, never in-place production mutation.
4. Memory is not conversation history, knowledge, or business truth.
5. Runtime context is not automatically model-visible.
6. Child authority never exceeds parent delegated authority.
7. Important delegated work is a durable Run.
8. Capability readiness is not authorization.
9. Hard deny may dominate approval and autonomy.
10. Workflow execution state is not Workflow definition.
11. WorkflowSpec remains pinned across pause/resume.
12. LangGraph interrupt does not replace COSA exact approval identity.
13. LangGraph checkpoint does not replace COSA Run/tool-call/approval truth.
14. Business side effects remain governed and idempotent even when nodes replay.
15. LangGraph may implement WorkflowEngine but not COSA ontology.
16. Hermes may inspire long-lived agent behavior but not become COSA kernel.
17. LangChain components are adopted tactically, not by default.

---

# 56. Final Recommendation

Proceed as two coordinated tracks:

```text
TRACK A — Hermes-derived Agent Maturity

Context
→ Conversation Recall
→ Memory hardening
→ Delegation authority
→ Skills
→ Governed Learning
```

```text
TRACK B — LangGraph Workflow Runtime Spike

WorkflowSpec compiler
→ StateGraph
→ Postgres checkpointer
→ restart
→ approval
→ spec pinning
→ pending writes
→ idempotent side effect
→ adoption decision
```

The desired result is not “COSA becomes Hermes” or “COSA becomes LangChain”.

It is:

> **COSA keeps its own durable Run, identity, governance, capability and business architecture; Hermes improves how agents remember, learn and delegate; LangGraph is evaluated to replace custom workflow execution machinery where it is already more mature.**
