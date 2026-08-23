# COSA Agent Core Platform — CrewAI Architecture Supplement (V4-Aligned, Revised)

> **Revision:** Supplement A2 — 2026-08-23  
> **Supersedes:** `COSA_AGENT_CORE_CREWAI_ARCHITECTURE_SUPPLEMENT_2026-08-23.md`  
> **Canonical architecture input:** `COSA_AGENT_CORE_PLATFORM_REARCHITECTURE_V4_2026-08-23.md`  
> **Internal code audit baseline:** `vutasoftvn/javis-saas@main` around `b39246c`  
> **External CrewAI reference pin:** `crewAIInc/crewAI@f4731f5025f861c78e3af0487cc80bf5e7c64782`  
> **Purpose:** retain the useful lessons from the CrewAI audit while correcting the first Supplement's four architecture/documentation defects.

---

# 0. Status and authority

This document is an **addendum to V4**, not an independent architecture.

The precedence order for implementation is:

```text
V4 architecture decisions
        ↓
existing audited COSA assets / ADR invariants
        ↓
this CrewAI Supplement
        ↓
external CrewAI patterns
```

If this Supplement conflicts with V4, **V4 wins**.

If this Supplement proposes a new abstraction that overlaps an existing audited COSA abstraction, the default action is **do not create it** until an explicit audit/ADR proves that the existing abstraction cannot be promoted or hardened.

This rule is the main correction to Supplement A1.

---

# 1. Corrections to Supplement A1

Supplement A1 had four concrete defects.

## 1.1 It proposed workflow architecture before auditing `agentos/workflows/`

This was incorrect.

`agentos/workflows/` already contains:

```text
agentos/workflows/
├── approval_step.py
├── definition_registry.py
├── definitions/
├── engine.py
├── loader.py
├── models.py
├── schema.py
├── steps.py
└── tool_step.py
```

The current code already provides:

- `WorkflowSpec`;
- `WorkflowStepSpec`;
- YAML loading and validation;
- declarative DAG execution;
- parallel execution by dependency wave;
- retry;
- compensation;
- approval gates;
- governed tool-call steps;
- workflow runtime state;
- in-memory checkpoints;
- version history through `WorkflowDefinitionRegistry`;
- tests for checkpoint resume, DAG execution, YAML, governance, compensation and definition versioning.

Therefore the correct V4 action is:

> **PROMOTE/HARDEN the existing workflow architecture into VNext. Do not create a second WorkflowSpec / WorkflowDefinition / CoordinationRuntime subsystem beside it.**

## 1.2 It reused a migration-style phased roadmap

This contradicted V4.

V4 explicitly changed the problem class from:

```text
migration of a serving runtime
```

to:

```text
promotion of an inert prototype into the first canonical VNext
```

Therefore this Supplement contains **no migration phases** and no `Phase 2.5`, `Phase 6.5`, gradual compatibility cutover, dual-write or preservation of old runtime state.

It attaches CrewAI-derived actions to the **V4 11-step promotion lifecycle** and to V4's two vertical slices.

## 1.3 It invented a first-class `interruptions` schema before mapping to V4 Step 6

Supplement A1 proposed:

```text
agent_core.interruptions
agent_core.external_event_waits
```

too early.

V4 Step 6 already freezes the durable foundation as:

```text
agent_core.runs
agent_core.run_checkpoints
agent_core.run_events
agent_core.run_tool_calls
agent_core.approvals
```

and explicitly requires an approval record bound to:

```text
run_id
tool_call_id
checkpoint_ref
```

The corrected position is:

> **Do not add a canonical `interruptions` table in this Supplement.**
>
> First implement approval pause/resume as a semantic composition of the V4 Step 6 tables.
>
> Add a generalized interruption entity/table only later if a real external-wait/human-input use case proves that the five-table model is insufficient and an ADR approves the extension.

## 1.4 It listed CrewAI repository paths ambiguously

Paths such as:

```text
lib/crewai/src/crewai/flow/flow.py
```

are **not paths in `javis-saas`**.

All external references in this revision use the explicit syntax:

```text
EXTERNAL[crewAIInc/crewAI@<commit>]::<path>
```

Example:

```text
EXTERNAL[crewAIInc/crewAI@f4731f5]::lib/crewai/src/crewai/flow/flow.py
```

A coding agent must never interpret an `EXTERNAL[...]::` path as a local file to modify.

---

# 2. V4 remains the architecture root

The CrewAI audit does not change the core V4 decisions.

Keep:

```text
packages/agent_core/
apps/cosa/
```

from the beginning.

Keep:

```text
ExecutionKernel = probabilistic agent execution
WorkflowEngine  = deterministic workflow execution
Capability Layer = shared governed action layer
```

Keep OpenAI Agents SDK as the primary execution kernel.

Keep framework-neutral ownership of:

```text
identity
tenant scope
runs
checkpoints
events
capabilities
governance
approvals
connectors
credentials
idempotency
memory
knowledge
artifacts
audit
usage
evals
```

CrewAI remains:

```text
architecture reference
+ benchmark candidate
+ optional adapter only if it demonstrates value
```

It is not a new architecture root.

---

# 3. Internal workflow audit — what already exists

## 3.1 `WorkflowSpec` already exists

Internal source:

```text
INTERNAL[javis-saas]::agentos/workflows/schema.py
```

Current shape:

```python
class StepType(str, enum.Enum):
    TOOL_CALL = "tool_call"
    AGENT = "agent"
    DETERMINISTIC = "deterministic"
    APPROVAL_GATE = "approval_gate"

class WorkflowStepSpec(BaseModel):
    id: str
    name: Optional[str]
    type: StepType
    tool: Optional[str]
    inputs: dict[str, Any]
    depends_on: list[str]
    on_failure: Optional[str]
    compensate_with: Optional[str]
    output_key: Optional[str]
    agent_key: Optional[str]
    goal_key: Optional[str]
    action: Optional[str]
    subject_key: Optional[str]
    permission_level: Optional[str]

class WorkflowSpec(BaseModel):
    id: str
    name: str
    description: str
    version: str
    steps: list[WorkflowStepSpec]
```

### Decision

**PROMOTE**, do not duplicate.

VNext may evolve the field vocabulary to match V4 (`AutonomyLevel`, `CapabilitySpec`, stable references, schemas), but the concept itself is already present and proven.

Correct target is conceptually:

```text
agentos/workflows/schema.py::WorkflowSpec
        │
        │ promote semantics / rewrite imports / normalize V4 vocabulary
        ▼
packages/agent_core/workflows/spec.py::WorkflowSpec
```

This is a **promotion of an audited asset**, not creation of a new competing `WorkflowSpec`.

---

# 4. YAML authoring already exists

Internal source:

```text
INTERNAL[javis-saas]::agentos/workflows/loader.py
```

The loader already accepts:

```text
YAML path
YAML string
raw dict
```

and validates into `WorkflowSpec`.

There is also a real definition:

```text
INTERNAL[javis-saas]::agentos/workflows/definitions/strategy_gate_evaluation_flow.yaml
```

which already models:

```text
fetch evidence
    ↓
evaluate gate
    ↓
notify founder
    ↓ on_failure
compensate
```

### Decision

**PROMOTE/HARDEN** the existing YAML authoring path.

Do not add a second:

```text
WorkflowCompiler + new YAML DSL + new WorkflowDefinition IR
```

unless there is a proven capability gap.

A future visual builder may still target the promoted `WorkflowSpec` schema.

---

# 5. `WorkflowDefinition` already exists — but means something narrower

Internal source:

```text
INTERNAL[javis-saas]::agentos/workflows/definition_registry.py
```

Current `WorkflowDefinition` is:

```text
immutable version metadata
```

with:

```text
id
name
version_no
created_at
```

while executable Python step objects are produced from a version-specific `steps_factory`.

The registry guarantees:

```text
new version does not mutate old version
history preserved
current version resolves to latest
old version can be rebuilt
```

This is already a useful invariant.

## 5.1 Correction to A1

A1 incorrectly assumed the platform had no definition/version layer and proposed a new serializable `WorkflowDefinition` IR.

That would create semantic ambiguity:

```text
WorkflowSpec          ← declarative data already exists
WorkflowDefinition    ← version metadata already exists
New WorkflowDefinition ← proposed serialized graph
```

Three overlapping meanings are not acceptable.

## 5.2 VNext rule

During VNext promotion:

1. Keep immutable workflow-version semantics.
2. Keep declarative `WorkflowSpec`.
3. Decide deliberately whether version metadata and declarative spec should be represented:
   - as two linked records; or
   - as one versioned spec record.
4. **Do not create a third meaning called `WorkflowDefinition`.**

Recommended naming if separation remains:

```text
WorkflowSpec
WorkflowVersion
```

rather than overloading `WorkflowDefinition`.

This naming decision belongs in the VNext workflow contract work, not in the CrewAI supplement.

---

# 6. `WorkflowEngine` already matches the V4 ontology

Internal source:

```text
INTERNAL[javis-saas]::agentos/workflows/engine.py
```

It currently supports two modes:

```text
linear step pipeline
declarative DAG
```

The declarative path already:

- resolves dependencies;
- computes ready nodes;
- executes independent nodes concurrently;
- records step outcomes;
- pauses on approval;
- records checkpoints;
- executes compensation;
- resumes from a supplied workflow state.

The engine imports:

```text
ToolRegistry
PolicyEngine
ApprovalService
```

but does **not** depend on the custom `Executor` reasoning loop.

This matches V4's frozen ontology:

```text
ExecutionKernel                         WorkflowEngine
(probabilistic)                         (deterministic)
      │                                      │
      └────────── shared Capability Layer ───┘
```

### Decision

**PROMOTE NEAR-INTACT ARCHITECTURE.**

The VNext work is hardening and re-binding, not replacement.

---

# 7. Existing workflow primitives: disposition

| Existing asset | V4 disposition | Why |
|---|---|---|
| `WorkflowSpec` | **PROMOTE** | declarative schema already exists |
| `WorkflowStepSpec` | **PROMOTE + normalize** | align tool→capability and autonomy vocabulary |
| YAML loader | **PROMOTE** | proven authoring path |
| `WorkflowEngine` | **PROMOTE + durable backing** | correct deterministic runtime |
| `Workflow` runtime model | **PROMOTE semantics, replace storage ownership** | state machine useful; in-memory durability insufficient |
| `WorkflowDefinitionRegistry` | **PROMOTE versioning invariant** | immutable history already proven |
| `DeterministicStep` | **PROMOTE** | core flow-first primitive |
| `AgentStep` | **PROMOTE + ExecutionKernel binding** | should call VNext Agent Core, not old `Agent` shape |
| `ParallelStep` | **PROMOTE** | explicit deterministic parallelism |
| `RetryStep` | **PROMOTE + retry policy hardening** | already avoids retrying approval |
| `CompensatingStep` | **PROMOTE** | explicit compensation semantics |
| `ApprovalGateStep` | **PROMOTE semantics + V4 durable approval store** | current ApprovalService is memory-backed |
| `ToolCallStep` | **PROMOTE semantics + Capability Gateway** | governance path already exists, but VNext vocabulary changes |
| in-memory `Workflow.checkpoints` | **REPLACE** | V4 Step 6 durable run/checkpoint model |
| old `PermissionClass` usage | **RETIRE** | V4 keeps autonomy+risk model, not old 1D lookup |

---

# 8. What CrewAI actually contributes after this audit

Because COSA already has a workflow engine, CrewAI's value is narrower than Supplement A1 claimed.

Useful CrewAI patterns remain:

```text
A. strict separation of authoring surface, definition, runtime concerns
B. flow-first product composition
C. async pause/resume UX patterns
D. event-driven runtime instrumentation
E. scoped memory/consolidation ideas
F. optional crew/supervisor coordination patterns
```

But several items are **not new architecture requirements** for COSA:

```text
WorkflowSpec       → already exists
DAG execution      → already exists
Parallel flow      → already exists
Approval gate      → already exists
Checkpoint concept → already exists, durability is the gap
Compensation       → already exists
Version history    → already exists
YAML workflows     → already exists
```

Therefore CrewAI should primarily be used to:

```text
validate
benchmark
borrow implementation lessons
```

not to justify creating another subsystem.

---

# 9. External reference namespace — mandatory convention

Every CrewAI source reference must be written like this:

```text
EXTERNAL[crewAIInc/crewAI@f4731f5025f861c78e3af0487cc80bf5e7c64782]::<repo path>
```

Examples:

```text
EXTERNAL[crewAIInc/crewAI@f4731f5]::lib/crewai/src/crewai/flow/flow.py
EXTERNAL[crewAIInc/crewAI@f4731f5]::lib/crewai/src/crewai/flow/flow_definition.py
EXTERNAL[crewAIInc/crewAI@f4731f5]::lib/crewai/src/crewai/flow/runtime/
EXTERNAL[crewAIInc/crewAI@f4731f5]::lib/crewai/src/crewai/memory/unified_memory.py
```

Interpretation:

```text
EXTERNAL[...]::path
```

means:

> read-only source material from another repository.

It never means:

```text
file to create in javis-saas
file to import directly by COSA
canonical internal module
```

---

# 10. CrewAI pattern: DSL / Definition / Runtime — adjusted to existing COSA

The external CrewAI `flow.py` currently documents an explicit split:

```text
DSL
Flow Definition
Runtime
```

COSA should learn from the concern separation, but **not clone the names**.

COSA already has:

```text
YAML / loader
      │
      ▼
WorkflowSpec
      │
      ▼
WorkflowEngine
```

and separate version metadata:

```text
WorkflowDefinitionRegistry
```

So the actual VNext question is not “build these three layers”.

It is:

> **Can the promoted COSA workflow assets preserve a clean separation between authoring, versioned declarative data and runtime execution without adding duplicate domain types?**

The default answer should be yes.

---

# 11. Corrected interruption model: semantic view, not new schema root

## 11.1 V4 Step 6 is authoritative

V4 Step 6 freezes the durable base tables as:

```text
agent_core.runs
agent_core.run_checkpoints
agent_core.run_events
agent_core.run_tool_calls
agent_core.approvals
```

and freezes the critical approval binding:

```text
approval
  ├─ run_id
  ├─ tool_call_id
  └─ checkpoint_ref
```

The CrewAI supplement must fit inside this model.

## 11.2 Do not create `agent_core.interruptions` yet

The previous proposal:

```text
agent_core.interruptions
```

is removed from the target schema.

Likewise:

```text
agent_core.workflow_runs
agent_core.workflow_node_runs
agent_core.external_event_waits
```

are **not introduced by this Supplement**.

Any such table requires a separate V4-compatible ADR based on a demonstrated use case.

---

# 12. Mapping the old `PendingInterruption` idea to V4 Step 6

A1 proposed this conceptual object:

```python
PendingInterruption(
    id,
    run_id,
    kind,
    checkpoint_ref,
    node_id,
    call_id,
    requested_at,
    expires_at,
    payload,
    resume_contract,
)
```

The corrected mapping is:

| A1 conceptual field | V4 Step 6 owner | Decision |
|---|---|---|
| `run_id` | `agent_core.runs` and FK references | **KEEP exactly** |
| `checkpoint_ref` | `agent_core.run_checkpoints` | **KEEP exactly** |
| `call_id` for tool approval | `agent_core.run_tool_calls.tool_call_id` | **rename/map to `tool_call_id`** |
| approval identity | `agent_core.approvals` record identity | **use approval row, no generic interruption id needed** |
| approval type/kind | approval semantics + `run_events.type` | **do not add generic column yet** |
| `payload` | safe approval preview / tool-call record / event payload | **do not duplicate canonical args** |
| `resume_contract` | checkpoint codec + kernel resume contract | **execution contract, not new DB root** |
| `node_id` | not frozen by V4 Step 6 | **defer; do not invent canonical column in Supplement** |
| `expires_at` | not frozen by V4 Step 6 | **defer until timeout/expiry requirement is approved** |
| generic human/external wait kind | not frozen by V4 Step 6 | **future ADR, not Step-6 schema** |

The key correction is:

> The conceptual idea “a run can be paused” is useful.  
> The database abstraction `PendingInterruption` is **not yet justified**.

---

# 13. Mapping current `agentos/workflows.Workflow` to V4 Step 6

Current internal model:

```text
Workflow.id
Workflow.name
Workflow.status
Workflow.current_step_index
Workflow.completed_steps
Workflow.checkpoints
Workflow.step_outcomes
Workflow.state
Workflow.pending_approval_id
Workflow.failed_step_name
Workflow.had_approval_gate
Workflow.error
```

VNext mapping should be:

| Current workflow data | V4 durable owner | Promotion rule |
|---|---|---|
| `Workflow.id` | `agent_core.runs` identity | one workflow execution participates in the common Run lifecycle |
| `Workflow.status` | `agent_core.runs` status | do not maintain a second durable lifecycle source-of-truth |
| `Workflow.state` | `agent_core.run_checkpoints` payload/state | persist versioned checkpoint instead of process memory |
| `Workflow.checkpoints` | `agent_core.run_checkpoints` rows | replace dict with durable repository |
| `Workflow.completed_steps` | checkpoint state and/or `run_events` | no separate table introduced by this Supplement |
| `Workflow.step_outcomes` | checkpoint state + `run_events` | append observable lifecycle events |
| `pending_approval_id` | `agent_core.approvals` | approval row is canonical |
| approval pause position | `checkpoint_ref` | exact durable checkpoint |
| governed tool call | `agent_core.run_tool_calls` | canonical tool-call identity |
| `failed_step_name` | `run_events` + run terminal error contract | exact column layout belongs to Step 6 implementation spec |
| `error` | run terminal error + `run_events` | same rule |
| `had_approval_gate` | derivable from events/approvals | do not persist a redundant canonical boolean unless query needs prove it |

This follows a crucial V4 principle:

> **one durable run model**, not separate agent-run and workflow-run state machines unless evidence later requires that split.

---

# 14. Exact governed approval flow — V4-compatible

Target:

```text
WorkflowEngine or ExecutionKernel
        │
        ▼
Capability requests side effect
        │
        ▼
Capability Gateway
        │
        ▼
PolicyDecision = REQUIRE_APPROVAL
        │
        ├─ persist/update run_tool_calls record
        │      └─ stable tool_call_id
        │
        ├─ persist exact run checkpoint
        │      └─ checkpoint_ref
        │
        ├─ create approvals record
        │      ├─ run_id
        │      ├─ tool_call_id
        │      └─ checkpoint_ref
        │
        ├─ append approval.required / run.paused event
        │
        └─ run becomes waiting
```

Resume:

```text
approval decision
      │
      ▼
load approvals row
      │
      ├─ verify run_id
      ├─ verify tool_call_id
      └─ resolve checkpoint_ref
      │
      ▼
load exact run checkpoint
      │
      ▼
resume exact WorkflowEngine / ExecutionKernel state
      │
      ▼
Capability Gateway idempotency check
      │
      ▼
execute or reject exact invocation
```

This is the correct way to import the useful “pause as durable data” lesson from CrewAI without inventing a parallel persistence model.

---

# 15. Current workflow approval gap

The existing `ApprovalService` stores `Approval` objects in:

```text
self._approvals: dict[str, Approval]
```

although it can write audit events to an `AuditSink`.

Current approval fields already include useful source material:

```text
id
action
subject
requester
run_id
tool_name
checkpoint_index
correlation_id
status
reviewer
reason
created_at
decided_at
```

But V4 promotion must not simply persist this class unchanged.

The V4 target must instead bind the business approval to the durable Step 6 identity triple:

```text
run_id
tool_call_id
checkpoint_ref
```

In particular:

```text
checkpoint_index
```

is not an adequate substitute for:

```text
checkpoint_ref
```

because an index does not by itself identify the exact serialized execution state.

---

# 16. Current `ToolCallStep` — useful invariant and hardening gap

Current internal path:

```text
INTERNAL[javis-saas]::agentos/workflows/tool_step.py
```

Useful behavior already proven:

```text
tool lookup
→ input resolution
→ workspace/run context extraction
→ evaluate_access()
→ DENY / REQUIRE_APPROVAL / ALLOW
→ approval lookup/request
→ invoke tool
```

This is a valuable invariant.

VNext changes:

```text
ToolRegistry        → Capability Gateway / registry
ToolSpecV2          → CapabilitySpec
PermissionLevel     → AutonomyLevel
ToolRiskLevel       → CapabilityRisk
old PermissionClass → retired from VNext canonical path
in-memory Approval  → Step 6 durable approvals
run/action matching → stable tool_call_id + checkpoint_ref binding
```

Do not replace the workflow engine merely to get these semantics from CrewAI.

---

# 17. Current checkpoint resume — what is already proven

There is an existing test:

```text
INTERNAL[javis-saas]::tests/agentos/workflows/test_checkpoint_resume.py
```

that verifies a completed non-idempotent step is not rerun when a workflow resumes from an existing `Workflow` state with `completed_steps`.

This proves an important invariant:

> resume should continue from recorded progress, not replay completed side effects.

But it does **not** yet prove production durability because the test uses an in-memory copied `Workflow` object.

VNext must upgrade the same invariant to:

```text
persist checkpoint
kill process
reload from DB
resume on another process/worker
do not rerun completed side effect
```

The test intent should be promoted into the V4 vertical-slice acceptance suite.

---

# 18. CrewAI HITL lesson — narrowed correctly

CrewAI demonstrates good UX/runtime patterns around:

```text
pause
persist state
surface feedback request
resume
```

COSA should borrow the mental model.

But two forms must remain distinct:

## Content feedback

Examples:

```text
approve/revise a draft
choose option A/B
comment on analysis
request another research pass
```

This may eventually become a general human-input workflow primitive.

## Governed business authorization

Examples:

```text
send email
modify CRM
deploy
delete record
make payment
change access
publish externally
```

This must use V4 Step 6 durable approval semantics with:

```text
run_id
tool_call_id
checkpoint_ref
```

CrewAI feedback state is not authority.

---

# 19. Generic external waits — deferred extension, not current schema

A1 proposed:

```text
EXTERNAL_EVENT
CREDENTIAL_REQUIRED
SCHEDULE
RATE_LIMIT
MANUAL_RECOVERY
```

as first-class interruption kinds.

These may eventually be useful.

However V4 has not frozen a generic wait schema in Step 6.

Correct policy:

```text
approval pause         → implement now with V4 Step 6
workflow checkpoint    → implement now with V4 Step 6
external-event wait    → define requirement first
generic human input    → define requirement first
credential wait        → connector/auth design
schedule wait          → scheduler/workflow ADR
```

Do not let a CrewAI pattern prematurely dictate the database.

---

# 20. No new `CoordinationRuntime` root

A1 proposed:

```python
class CoordinationRuntime(Protocol):
    ...
```

as a new major runtime abstraction.

That is no longer recommended.

V4 already has the clearer separation:

```text
ExecutionKernel
WorkflowEngine
agent_core/coordination primitives
```

The existing workflow engine is the deterministic runtime.

`agent_core/coordination/` should contain reusable coordination strategies such as:

```text
delegation
parallel
sequential
debate
supervisor
synthesis
```

but should not become another top-level durable state machine competing with `WorkflowEngine`.

Use:

```text
WorkflowEngine = lifecycle + deterministic graph
coordination/  = reusable coordination behaviors/nodes
ExecutionKernel = probabilistic reasoning
```

---

# 21. CrewAI optional adapter — narrower contract

If CrewAI is benchmarked, its adapter should target the existing V4 seams.

Possible shape:

```text
packages/agent_core/
└── execution/
    └── crewai/        # experimental only
```

or, if it primarily executes workflows:

```text
packages/agent_core/
└── workflows/
    └── adapters/
        └── crewai/    # experimental only
```

The exact location depends on what the benchmark proves CrewAI is actually good at.

Do not create both by default.

The adapter may translate:

```text
AgentSpec
WorkflowSpec
Capability invocation
runtime state
events
```

but cannot own:

```text
Run repository
Checkpoint repository
Approval repository
Capability authorization
Credentials
Canonical memory
Audit
Tenant scope
```

---

# 22. V4 promotion lifecycle — CrewAI actions attached to existing steps

There are **no Supplement migration phases**.

Use the V4 lifecycle:

```text
1. Correct architecture truth
2. Freeze inert prototype
3. Define VNext contracts
4. Build clean reusable Agent Core
5. Integrate OpenAI Agents kernel
6. Add durable run/checkpoint/event model
7. Add governance/capability/connector/workflow layer
8. Compose COSA app on top
9. Run eval + integration + security gates
10. Wire first canonical integration entrypoint
11. Archive/delete inert prototype
```

CrewAI-related actions are only annotations to these steps.

---

# 23. V4 Step 1 — correct architecture truth

Add to architecture truth:

```text
agentos/workflows/ is an audited design asset
not a subsystem to be reinvented
```

Record:

```text
WorkflowSpec exists
WorkflowEngine exists
WorkflowDefinitionRegistry exists
approval gate exists
parallel/retry/compensation exist
YAML exists
checkpoint semantics exist
durability/API are the main gaps
```

Also record external-source notation:

```text
EXTERNAL[repo@commit]::path
```

so coding agents cannot confuse external CrewAI paths with internal files.

---

# 24. V4 Step 2 — freeze inert prototype

Freeze:

```text
agentos/core/runtime.py
agentos/core/executor.py
agentos/core/planner.py
agentos/orchestration/adk/
agentos/api/chat/routes.py
```

But do **not** freeze `agentos/workflows/` as useless prototype code.

Treat it as:

```text
promotion source
```

The distinction matters.

```text
runtime/executor prototype → reference/test only
workflows architecture     → promoted asset
```

---

# 25. V4 Steps 3–4 — define contracts/build core

Do not add a new workflow ontology from CrewAI.

Instead define the VNext workflow contract by **promoting the existing schema** and normalizing it to V4.

Required work:

```text
Tool step references CapabilitySpec
Agent step references AgentSpec / ExecutionKernel
PermissionLevel vocabulary becomes AutonomyLevel
risk remains CapabilityRisk
workflow identity/version contract becomes unambiguous
Principal derives from WorkforceMember projection
```

Open question to settle in the workflow contract:

```text
WorkflowSpec + WorkflowVersion
```

versus another clean naming scheme.

Do not use CrewAI's class names as COSA domain names.

---

# 26. V4 Step 5 — OpenAI Agents kernel

No change from V4.

CrewAI is not introduced here.

DeepSeek compatibility remains a model/kernel spike inside Vertical Slice 1.

CrewAI must not become a workaround for provider compatibility.

---

# 27. V4 Step 6 — durable run/checkpoint/event model

This is where the CrewAI pause/resume lesson matters most.

Implement:

```text
runs
run_checkpoints
run_events
run_tool_calls
approvals
```

with exact approval binding:

```text
run_id
tool_call_id
checkpoint_ref
```

Use the same durable checkpoint substrate for:

```text
OpenAI Agents RunState
WorkflowEngine state
```

through adapter-specific codecs/envelopes.

Do not introduce a second durable workflow checkpoint database.

---

# 28. V4 Step 7 — promote WorkflowEngine + capability layer

This is the main home for the workflow work.

Promote:

```text
DAG
ParallelStep
RetryStep
CompensatingStep
ApprovalGateStep
YAML loader
version history
```

Re-bind:

```text
ToolCallStep → Capability Gateway
AgentStep    → ExecutionKernel
ApprovalGate → durable approval repository
checkpoints  → run_checkpoints
```

Add the two V4-confirmed gaps:

```text
HTTP API
durable checkpoint store
```

Do not treat CrewAI as the implementation target.

---

# 29. V4 Step 8 — compose COSA app

Use real COSA workflows as validation.

Good candidates:

```text
strategy gate evaluation
monthly business review
customer escalation
founder decision workflow
research → synthesis → artifact
```

At least one workflow should contain:

```text
deterministic step
agent step
parallel branch
governed write
approval
resume
artifact
```

This proves the V4 architecture, not CrewAI.

---

# 30. V4 Step 9 — benchmark CrewAI here

CrewAI evaluation belongs under V4's:

```text
eval + integration + security gates
```

not as a separate migration phase.

Benchmark only after the VNext contracts are real enough to compare against.

Three benchmark workloads remain useful.

## A. Research coordination

Compare:

```text
promoted COSA WorkflowEngine + OpenAI Agents
vs
CrewAI Flow/Crew adapter
```

## B. Governed approval

Must preserve:

```text
run_id
tool_call_id
checkpoint_ref
no duplicate side effect
```

## C. Long-running pause/resume

Only after COSA defines a real non-approval waiting requirement.

Do not invent the requirement solely to test CrewAI.

---

# 31. CrewAI keep/remove gate

Retain an optional CrewAI adapter only if evidence shows a material advantage.

Examples of acceptable wins:

```text
substantially simpler hierarchical multi-agent coordination
better workflow authoring ergonomics without semantic loss
useful provider capability not available through the primary path
lower implementation/maintenance complexity for a bounded workload
```

Not enough:

```text
framework is popular
framework has many stars
same behavior can be reproduced
demo code is shorter but bypasses COSA governance
```

If it does not win a concrete workload:

```text
remove adapter
keep architectural lessons
```

---

# 32. V4 Step 10 — canonical integration entrypoint

Use V4 terminology exactly:

```text
canonical integration entrypoint
```

Do not say:

```text
production cutover
production migration
traffic migration
```

unless the product is actually in that state later.

The workflow supplement has no compatibility obligation to the inert `agentos` API.

---

# 33. V4 Step 11 — archive/delete inert prototype

When VNext is canonical and the required acceptance gates pass:

```text
archive/delete obsolete runtime prototype
```

For workflow code, this means:

```text
promoted implementation lives in packages/agent_core/
old agentos/workflows/ path can be retired
```

only after import consumers and tests have moved.

This is relocation/promotion cleanup, not preserving two workflow engines.

---

# 34. Vertical Slice 1 — read path

V4 defines:

```text
User message
→ new API
→ durable Run
→ OpenAI Agents kernel
→ one read-only business capability
→ streamed events
→ final message
→ trace/usage
```

CrewAI has no required role here.

Use this slice to prove:

```text
ExecutionKernel
RunRepository
Event protocol
Model capability matrix
Capability read path
```

---

# 35. Vertical Slice 2 — write + approval

V4 defines:

```text
write capability
→ policy
→ approval
→ persist exact RunState
→ process restart
→ approve
→ exact resume
→ idempotent side effect
```

Extend this slice with one WorkflowEngine case:

```text
workflow tool step
→ Capability Gateway
→ approval
→ persist workflow checkpoint
→ process restart
→ approve
→ workflow resumes
→ completed prior step not repeated
```

This directly promotes the invariant already tested in:

```text
tests/agentos/workflows/test_checkpoint_resume.py
```

into a durable VNext acceptance test.

---

# 36. Event protocol — no CrewAI-native contract leakage

CrewAI/OpenAI/native workflow events must translate into COSA events.

Workflow-oriented event families may include:

```text
workflow.started
workflow.step.started
workflow.step.completed
workflow.step.failed
workflow.completed
workflow.failed
```

Approval remains:

```text
approval.required
approval.resolved
```

Pause/resume can be represented through the canonical run lifecycle events already defined by the V4/V3 event contract.

Do not add a new `interruption.*` public family merely because CrewAI uses a feedback-pending object.

Add events only when product semantics require them.

---

# 37. Memory lessons remain algorithmic, not ownership-changing

The CrewAI unified-memory design still suggests useful ideas:

```text
semantic relevance
recency
importance
scope
consolidation
```

COSA may use a composite score such as:

```text
semantic
+ lexical
+ recency
+ importance
+ entity relevance
+ source confidence
```

But V4 ownership remains unchanged:

```text
COSA owns canonical memory semantics and tenant boundaries
```

CrewAI memory remains:

```text
reference
or adapter-local implementation
```

not organizational truth.

---

# 38. Security boundary remains unchanged

Under every framework:

```text
framework requests action
        │
        ▼
COSA Capability Gateway
        │
        ├─ schema validation
        ├─ tenant scope
        ├─ AutonomyLevel
        ├─ CapabilityRisk
        ├─ policy
        ├─ approval
        ├─ credential resolution
        ├─ idempotency
        ├─ execution
        ├─ output validation
        ├─ audit
        └─ event/usage
```

No CrewAI tool may bypass this chain.

No workflow step may bypass this chain.

---

# 39. Revised anti-patterns

The following are prohibited:

- creating a second `WorkflowSpec` without first auditing/promoting the existing one;
- creating a second durable workflow run store beside V4 `agent_core.runs`;
- creating a second workflow checkpoint store beside `agent_core.run_checkpoints`;
- adding `agent_core.interruptions` before a real use case and ADR justify it;
- treating generic human feedback as business authorization;
- storing approval only as a workflow flag or approval ID without exact checkpoint/tool-call binding;
- creating a second `CoordinationRuntime` state machine beside `WorkflowEngine`;
- using CrewAI `Flow`, `Crew`, `Task`, or `Agent` as COSA domain types;
- copying CrewAI source paths into the internal target module map;
- saying "migration phase" where V4 means promotion/build step;
- preserving compatibility with inert prototype code without a demonstrated consumer;
- replacing an audited `agentos/workflows/` invariant merely because an external framework offers a similar feature.

---

# 40. Internal vs external source map

## Internal COSA sources audited

```text
INTERNAL[javis-saas]::agentos/workflows/__init__.py
INTERNAL[javis-saas]::agentos/workflows/schema.py
INTERNAL[javis-saas]::agentos/workflows/loader.py
INTERNAL[javis-saas]::agentos/workflows/models.py
INTERNAL[javis-saas]::agentos/workflows/engine.py
INTERNAL[javis-saas]::agentos/workflows/steps.py
INTERNAL[javis-saas]::agentos/workflows/tool_step.py
INTERNAL[javis-saas]::agentos/workflows/approval_step.py
INTERNAL[javis-saas]::agentos/workflows/definition_registry.py
INTERNAL[javis-saas]::agentos/workflows/definitions/strategy_gate_evaluation_flow.yaml

INTERNAL[javis-saas]::agentos/core/approval.py

INTERNAL[javis-saas]::tests/agentos/workflows/test_checkpoint_resume.py
INTERNAL[javis-saas]::tests/agentos/workflows/test_dag_engine.py
INTERNAL[javis-saas]::tests/agentos/workflows/test_declarative_yaml.py
INTERNAL[javis-saas]::tests/agentos/workflows/test_definition_registry.py
INTERNAL[javis-saas]::tests/agentos/workflows/test_workflow_compensation.py
INTERNAL[javis-saas]::tests/agentos/workflows/test_workflow_governance.py
```

## External CrewAI reference sources

These are **not in javis-saas**:

```text
EXTERNAL[crewAIInc/crewAI@f4731f5025f861c78e3af0487cc80bf5e7c64782]
    ::lib/crewai/src/crewai/flow/flow.py

EXTERNAL[crewAIInc/crewAI@f4731f5025f861c78e3af0487cc80bf5e7c64782]
    ::lib/crewai/src/crewai/flow/flow_definition.py

EXTERNAL[crewAIInc/crewAI@f4731f5025f861c78e3af0487cc80bf5e7c64782]
    ::lib/crewai/src/crewai/flow/runtime/

EXTERNAL[crewAIInc/crewAI@f4731f5025f861c78e3af0487cc80bf5e7c64782]
    ::lib/crewai/src/crewai/memory/unified_memory.py
```

Rule for coding agents:

> Never create, edit or import from an `EXTERNAL[...]::` path as if it were part of the local repository. It is evidence/reference only.

---

# 41. Corrected architecture summary

```text
APPLICATIONS
    │
    ▼
COSA Agent Platform API
    │
    ▼
packages/agent_core/
    │
    ├─ RunService
    ├─ AgentSpec
    ├─ WorkflowSpec          ← promoted from agentos/workflows
    ├─ WorkflowEngine        ← promoted deterministic runtime
    ├─ ExecutionKernel       ← OpenAI Agents primary
    ├─ Capability Gateway
    ├─ Governance
    ├─ Connectors
    ├─ Context
    ├─ Memory / Knowledge
    ├─ Artifacts
    ├─ Events / Audit / Usage / Evals
    │
    ▼
V4 Step 6 durable substrate
    ├─ runs
    ├─ run_checkpoints
    ├─ run_events
    ├─ run_tool_calls
    └─ approvals
          │
          └─ approval binds:
             run_id
             tool_call_id
             checkpoint_ref
```

Optional external runtime:

```text
CrewAI adapter
```

exists only after a benchmark demonstrates a concrete advantage.

---

# 42. Final decision

The CrewAI audit still provides useful lessons, but the internal workflow audit changes the interpretation materially.

The correct conclusion is not:

> “CrewAI shows COSA needs WorkflowSpec, WorkflowDefinition and a workflow runtime.”

The correct conclusion is:

> **COSA already built most of the correct deterministic workflow architecture in `agentos/workflows/`. V4 should promote that asset into VNext, harden its durability and governance bindings, and use CrewAI only as an external reference/benchmark for specific missing patterns.**

The strongest CrewAI lesson that remains is architectural discipline:

```text
authoring concerns
≠ definition/version concerns
≠ runtime concerns
```

But COSA should apply that discipline to its **existing** workflow assets rather than recreate them.

For durable pauses, V4 Step 6 is the source of truth:

```text
run
+ exact checkpoint
+ stable tool call
+ approval record
+ event lineage
```

A generalized interruption abstraction is deferred until a real requirement proves it is necessary.

And for planning terminology:

```text
prototype → VNext → gates → canonical integration entrypoint
```

is **promotion**, not migration.

---

## Appendix A — Change log from Supplement A1

| A1 | A2 correction |
|---|---|
| proposed new `WorkflowSpec` | removed; existing `agentos/workflows/schema.py::WorkflowSpec` is promoted |
| proposed new serializable `WorkflowDefinition` | removed as default; existing version semantics audited first |
| proposed new `CoordinationRuntime` | removed as top-level runtime; use WorkflowEngine + coordination primitives |
| proposed `interruptions` table | removed from Step-6 target |
| proposed `workflow_runs` tables | removed from Supplement target |
| migration-style phases | replaced with V4 11-step promotion lifecycle |
| CrewAI paths shown without repo prefix | all paths explicitly marked `EXTERNAL[repo@commit]::` |
| CrewAI used as reason for workflow architecture | CrewAI reduced to reference/benchmark because COSA already has workflow architecture |
| approval pause generalized immediately | approval first mapped to `runs/checkpoints/tool_calls/approvals/events` |
| workflow checkpoint treated as separate subsystem | mapped to common V4 `run_checkpoints` durable substrate |

---

## Appendix B — Promotion checklist for `agentos/workflows/`

Before moving workflow architecture into `packages/agent_core/`, verify each item:

```text
[ ] WorkflowSpec field mapping to V4 CapabilitySpec/AgentSpec
[ ] PermissionLevel → AutonomyLevel vocabulary
[ ] ToolRiskLevel → CapabilityRisk
[ ] no PermissionClass dependency in VNext canonical path
[ ] ToolCallStep calls Capability Gateway
[ ] AgentStep calls ExecutionKernel
[ ] ApprovalGateStep uses durable ApprovalRepository
[ ] approval binds run_id/tool_call_id/checkpoint_ref
[ ] Workflow state serializable
[ ] Workflow checkpoint persisted in run_checkpoints
[ ] process-kill/restart resume test
[ ] completed non-idempotent step is not rerun
[ ] event translation to Core Event Protocol
[ ] immutable workflow version semantics retained
[ ] YAML definition validation retained
[ ] compensation semantics retained
[ ] parallel-wave semantics retained
[ ] no old runtime.py/executor.py import introduced
[ ] tests promoted with behavior, not blindly copied paths
```

---

## Appendix C — CrewAI benchmark gate

Only implement/retain a CrewAI adapter if:

```text
[ ] same COSA governance path
[ ] same durable Run ownership
[ ] same checkpoint repository
[ ] same approval binding
[ ] same idempotency guarantees
[ ] same event protocol
[ ] tenant isolation preserved
[ ] exact restart/resume works
[ ] measurable complexity or capability win
[ ] dependency/upgrade cost acceptable
```

Otherwise:

```text
extract lessons
delete adapter
keep VNext architecture framework-neutral
```
