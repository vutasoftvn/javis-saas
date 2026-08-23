# COSA Agent Core Platform — Paperclip Control-Plane Architecture Supplement (V4-Aligned)

> **Revision:** Supplement P1 — 2026-08-23  
> **Document type:** Architecture addendum / delta; **not** a replacement for V4  
> **Canonical architecture input:** `COSA_AGENT_CORE_PLATFORM_REARCHITECTURE_V4_2026-08-23.md`  
> **Peer supplement:** `COSA_AGENT_CORE_CREWAI_ARCHITECTURE_SUPPLEMENT_V4_ALIGNED_REVISED_2026-08-23.md`  
> **Internal code baseline:** `vutasoftvn/javis-saas@b39246ccea5b92543678f20d1d2ed2cb64de33b2`  
> **External Paperclip audit pin:** `paperclipai/paperclip@05b35d4669cebea2e1d0bad194caf883b43d8550`  
> **Purpose:** incorporate only the Paperclip control-plane invariants that materially improve COSA V4, while preserving V4's execution-kernel, workflow, identity, business-plane and promotion decisions.

---

# 0. Status, authority, and scope

This document is a **supplement to V4**. It does not define a new architecture root and it does not authorize a Paperclip integration.

Implementation precedence remains:

```text
COSA V4 canonical decisions
        ↓
existing COSA ADRs + audited internal invariants
        ↓
this Paperclip Supplement
        ↓
external Paperclip implementation patterns
```

If this Supplement conflicts with V4, **V4 wins**.

If a Paperclip concept overlaps an existing COSA abstraction, the default is:

```text
ADAPT THE INVARIANT
not
COPY THE EXTERNAL SUBSYSTEM
```

Because Paperclip is an external repository, the verb **PROMOTE** is reserved for COSA's own audited code. Paperclip code is never promoted into VNext; at most its invariant is adapted.

This Supplement therefore **does not**:

- replace OpenAI Agents SDK;
- replace `ExecutionKernel`;
- replace the existing `agentos/workflows/` architecture;
- introduce a Paperclip server beside Encore;
- introduce Paperclip's `Company` / `Issue` / `Board` domain model into COSA;
- convert Agent Core to TypeScript;
- add a generic `interruptions` table;
- add a second durable workflow runtime;
- turn `services/` into an agent framework;
- copy Paperclip's heartbeat terminology into the COSA public ontology.

It only strengthens V4 where Paperclip has proven operational patterns that COSA should not rediscover through production incidents.

---

# 1. Why Paperclip matters to V4 — and where it does not

Paperclip is not primarily an agent reasoning framework. Its own implementation behaves as an **organizational control plane** around heterogeneous agent runtimes and adapters.

That makes it a strong external reference for:

```text
work ownership
run dispatch
run liveness
recovery
scheduling
idempotency
approval binding
tool target integrity
budget hard-stops
auditability
low-trust coordination
operator control
```

It is **not** the strongest reference for:

```text
kernel-level ReAct semantics
serializable model reasoning state
OpenAI Agents SDK RunState
COSA deterministic DAG workflow semantics
COSA WorkforceMember identity
COSA business truth
semantic memory architecture
```

The architectural implication is simple:

```text
Paperclip lessons improve the layers AROUND Agent Core.
They do not replace Agent Core.
```

V4's root ontology remains:

```text
                     COSA business/control plane
                              services/
                                  │
                                  │ policy, identity, business truth,
                                  │ approvals, work context
                                  ▼
                         apps/cosa/ composition
                                  │
                                  ▼
                    packages/agent_core/ (Python)
                 ┌────────────────┴────────────────┐
                 │                                 │
         ExecutionKernel                    WorkflowEngine
         probabilistic                      deterministic
                 │                                 │
                 └──────── Capability Layer ───────┘
                                  │
                           governed effects
```

Paperclip is prior art mainly for the **durable/control-plane semantics surrounding this graph**.

---

# 2. Source notation and audit baseline

To avoid the ambiguity corrected in the CrewAI Supplement, all Paperclip source paths use:

```text
EXTERNAL[paperclipai/paperclip@05b35d4]::<repo-path>
```

Examples:

```text
EXTERNAL[paperclipai/paperclip@05b35d4]::doc/execution-semantics.md
EXTERNAL[paperclipai/paperclip@05b35d4]::packages/db/src/schema/routines.ts
EXTERNAL[paperclipai/paperclip@05b35d4]::packages/db/src/schema/tool_access.ts
EXTERNAL[paperclipai/paperclip@05b35d4]::server/src/services/tool-gateway.ts
```

Internal COSA paths use:

```text
INTERNAL[vutasoftvn/javis-saas@b39246c]::<repo-path>
```

The current COSA baseline already reflects the 2026-08-23 service split:

```text
services/
├── company/
│   ├── commercial/
│   ├── finance-legal/
│   ├── identity/
│   └── operations/
│       └── strategy/
└── cosa/
```

This matters because the Paperclip audit must **not** cause another top-level control-plane product to be created. The correct action is to clarify ownership across the boundaries COSA already has.

---

# 3. Paperclip findings — disposition for COSA

| Paperclip pattern | Evidence / meaning | COSA disposition |
|---|---|---|
| Control plane wraps heterogeneous agents | adapters + heartbeat execution, not one universal reasoning loop | **ADAPT principle** — confirms Python Agent Core + external control plane split |
| `checkoutRunId` ≠ `executionRunId` | ownership right is distinct from live execution path | **ADAPT invariant** — logical run/ownership must not be confused with worker attempt/lease |
| DB-backed wake requests + coalescing | duplicate triggers are merged and idempotency-aware | **DEFER physical queue; ADAPT contract now** — useful when autonomous schedules/events become first-class |
| Routable `blocked` state | waiting requires blocker/approval/owner-action path | **ADOPT invariant now** for all durable wait states |
| `routine_revisions` + `routine_runs.routineRevisionId` | immutable definition revision pinned to execution | **ADOPT invariant now** as `PinnedSpecIdentity` |
| Agent task sessions + config fingerprints | session reuse/reset on config drift | **ADAPT selectively** — useful provider-session hygiene, not canonical checkpoint semantics |
| Tool invocation ledger | exact invocation + payload hash + idempotency + result | **ADOPT now** inside V4 `run_tool_calls` |
| Signed approval arguments | approval is bound to exact canonical args | **ADOPT now** |
| Approval target snapshot | catalog/schema/risk/credential/target drift invalidates approval | **ADOPT now** and strengthen with current-governance re-evaluation |
| Exact-once accepted-plan decomposition | durable fingerprint prevents duplicate fan-out | **ADOPT invariant now** for workflow/delegation expansion |
| Recovery restores liveness without silent takeover | exhausted recovery escalates instead of changing owner | **ADOPT invariant now** |
| Budget hard-stop controls execution | spend limit can pause/cancel work | **ADAPT** into ambient current governance |
| Low-trust direct-parent/lateral boundaries | prevents prompt-injection propagation across organizational trust boundaries | **ADAPT P1** for delegated/reviewer agents |
| Pipelines | business stage state machine | **DO NOT COPY** into `WorkflowEngine` |
| Paperclip plugin runtime | extension mechanism, currently with documented same-origin/cloud limitations | **DEFER**; no need for VNext core |
| Paperclip memory/knowledge | still less mature than its control-plane subsystems | **DO NOT USE as primary memory reference** |

The key point is that Paperclip contributes **operational invariants**, not a new COSA domain model.

---

# 4. The architectural improvement: make COSA explicitly three-plane

V4 already implies this separation. The Paperclip audit makes it useful to state it explicitly so future implementation does not collapse responsibilities again.

```text
┌──────────────────────────────────────────────────────────────────┐
│ 1. BUSINESS PLANE — TypeScript / Encore                          │
│                                                                  │
│ services/company/*                                               │
│   identity       → WorkforceMember truth                         │
│   operations     → strategy/work/business lifecycle              │
│   commercial     → commercial truth                              │
│   finance-legal  → financial/legal truth                         │
│                                                                  │
│ services/cosa/*                                                  │
│   COSA-facing API/control composition                            │
│   approval decision endpoints                                    │
│   run command/query projection                                   │
│   policy/business context bridge                                 │
└──────────────────────────────┬───────────────────────────────────┘
                               │ typed API/contracts
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│ 2. AGENT PLATFORM PLANE — Python                                 │
│                                                                  │
│ packages/agent_core/*                                            │
│   contracts / execution / durability / capability / governance   │
│   workflows / coordination / connectors / memory / knowledge     │
│                                                                  │
│ apps/cosa/*                                                      │
│   COSA-specific AgentSpec / WorkflowSpec / context / evals        │
└──────────────────────────────┬───────────────────────────────────┘
                               │ adapter / provider protocol
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│ 3. EXECUTION PROVIDER PLANE                                      │
│                                                                  │
│ OpenAI Agents SDK / DeepSeek route / MCP / connector transports   │
│ external APIs / model providers / runtime services               │
└──────────────────────────────────────────────────────────────────┘
```

## 4.1 Why this is better than importing Paperclip wholesale

Paperclip owns `Company`, agents, issues/tasks, board governance and run control in one product.

COSA already has stronger domain ownership boundaries in `services/company/*` plus a dedicated Agent Core target. Importing Paperclip would create competing canonical truths:

```text
Paperclip Company     vs COSA company/workspace
Paperclip Agent       vs WorkforceMember/AgentSpec
Paperclip Issue       vs COSA strategy/work objects
Paperclip Approval    vs COSA governance approval
Paperclip Run         vs agent_core Run
Paperclip Budget      vs COSA finance/operations policy
```

The improved COSA architecture therefore adopts **separation and invariants**, not entities.

---

# 5. Canonical ownership matrix after this Supplement

| Concern | Canonical owner | Agent Core role | What must NOT happen |
|---|---|---|---|
| Workforce identity | `services/company/identity` | `Principal` projection only | new Agent/User identity database in Agent Core |
| Business strategy/work | `services/company/operations` | consume typed context + emit outcomes | create Paperclip-like `issues` as parallel business truth |
| COSA API/control | `services/cosa` | command/query target | put Encore business API logic inside kernel |
| Agent definitions | `apps/cosa/agents` + framework-neutral spec contract | resolve + pin immutable spec snapshot | old run resolving mutable `latest` silently |
| Workflow definitions | `apps/cosa/workflows` + promoted `WorkflowSpec` | deterministic runtime | second WorkflowSpec/FlowDefinition subsystem |
| Run execution truth | `packages/agent_core` durable store | canonical | TS and Python directly dual-writing run rows |
| Checkpoint truth | `packages/agent_core` | canonical exact state codec | using provider session ID as checkpoint |
| Tool invocation truth | `agent_core.run_tool_calls` | canonical | approval by generic tool name only |
| Approval execution binding | `agent_core.approvals` | bind exact run/tool-call/checkpoint | unbound approval replay |
| Approval actor authorization | business/governance policy from `services/` | verify via policy interface | trusting arbitrary user/agent decision payload |
| Capability policy evaluation | COSA-owned policy semantics exposed through Agent Core governance interface | execution gate | vendor framework owning policy truth |
| Budget/business hard-stop | business/finance policy | current ambient execution gate | snapshot budget permission once and ignore later hard-stop |
| Audit | linked business audit + execution event ledger | execution events | one giant generic log with no typed correlation |
| Provider session | adapter/provider | optimization only | treating session reuse as exact durable resume |
| Recovery | Agent Core for execution continuity; services for business ownership decisions | retry/reload/escalate | silent reassignment/takeover |

The critical rule is **single-writer canonical ownership** for execution records. `services/cosa` may command/query Agent Core, but it should not become a second writer of `agent_core.runs` / checkpoints / tool calls.

---

# 6. V4 Step 3 delta — add four contracts, not four subsystems

Paperclip justifies four contract-level additions to V4. None requires a new service or database table.

## 6.1 `PinnedSpecIdentity`

Paperclip's strongest definition-versioning pattern is its routine model:

```text
logical routine
    ↓ publish
immutable routine revision
    ↓
routine run pins revision id
```

COSA should apply the same invariant to both agents and workflows.

Suggested framework-neutral contract:

```python
@dataclass(frozen=True)
class PinnedSpecIdentity:
    kind: Literal["agent", "workflow"]
    spec_id: str
    version: str
    content_hash: str
    source_revision: str | None = None
```

The exact storage backend is intentionally not frozen here.

For file-backed specs in `apps/cosa/`:

```text
version         = explicit spec version or Git/blob revision
content_hash    = canonical normalized spec hash
source_revision = Git commit/blob SHA when available
```

At run creation, persist enough resolved snapshot information that an old run never needs to reinterpret `latest` after code/spec drift.

### Required invariant

```text
Run created against AgentSpec A@v7
        ↓
pause / restart / approval wait / deploy
        ↓
resume
        ↓
still A@v7
```

Never:

```text
resume → resolve AgentSpec.current → accidentally A@v8
```

## 6.2 `InvocationIdentity`

Paperclip's tool ledger reinforces the V4 requirement that approval bind to an exact tool call.

Suggested semantic identity:

```python
@dataclass(frozen=True)
class InvocationIdentity:
    run_id: str
    tool_call_id: str
    capability_id: str
    payload_hash: str
```

This is the minimum identity for a governed side effect.

## 6.3 `ExecutionTargetSnapshot`

Payload identity alone is insufficient.

An approval may be for the same arguments while the actual execution target changed underneath it.

Paperclip defends against this by snapshotting target details such as catalog/schema/risk/credential versions and refusing execution when the live target differs.

COSA should adapt this as a framework-neutral structure:

```python
@dataclass(frozen=True)
class ExecutionTargetSnapshot:
    capability_id: str
    capability_version: str | None
    input_schema_hash: str | None
    connector_id: str | None
    connection_id: str | None
    provider_type: str | None
    upstream_action: str | None
    risk: CapabilityRisk
    credential_version_refs: tuple[str, ...]
    implementation_hash: str | None
```

Not all fields are mandatory for all capability kinds.

The invariant is:

```text
approved invocation
        +
same payload
        but
changed target / schema / risk / credential binding
        ↓
old approval is stale
```

## 6.4 `WaitDescriptor`

Paperclip's `blocked` semantics are valuable because they reject prose-only waiting.

COSA should define a **typed wait descriptor**, but keep it as checkpoint/event state rather than a new interruption table.

Suggested shape:

```python
@dataclass(frozen=True)
class WaitDescriptor:
    kind: Literal[
        "approval",
        "dependency",
        "external_event",
        "timer",
        "human_input",
    ]
    checkpoint_ref: str
    owner_principal_id: str | None
    trigger_ref: str | None
    expires_at: datetime | None
```

For V4 v1, only `approval` must be implemented end-to-end.

The other kinds are contract vocabulary for future use and **must not create tables until a real use case exists**.

### Required invariant

Every non-terminal waiting Run must answer:

```text
What is it waiting for?
Who/what can unblock it?
Which durable event/ref proves it?
Which exact checkpoint will resume?
```

If those answers cannot be produced from durable state, the Run is stranded, not legitimately waiting.

---

# 7. V4 Step 6 delta — strengthen the five-table durable substrate, do not add a sixth root table

V4 freezes:

```text
agent_core.runs
agent_core.run_checkpoints
agent_core.run_events
agent_core.run_tool_calls
agent_core.approvals
```

Paperclip does **not** justify replacing this model. It justifies enriching its invariants.

## 7.1 `agent_core.runs`

The Run is a **logical execution identity**, not a process and not a provider session.

Recommended semantics/fields to ensure in the target schema:

```text
id
tenant/workspace scope
principal/workforce projection
status
created_at / started_at / completed_at
parent_run_id or correlation lineage when needed
pinned_agent_spec
pinned_workflow_spec (optional)
current_checkpoint_ref
wait_state summary (optional/derived)
lease_owner / lease_expires_at / lease_epoch   # if distributed workers are enabled
```

### Paperclip lesson adapted correctly

Paperclip distinguishes task checkout ownership from the live run path.

COSA should **not** copy `checkoutRunId` and `executionRunId` literally.

Instead distinguish:

```text
Run                     = logical durable execution
ExecutionLease          = which worker currently owns execution rights
WorkerAttempt           = a physical dispatch/retry attempt
ProviderSession         = optional provider continuity state
Checkpoint              = canonical exact resume state
```

These are different concepts.

### Important v1 constraint

Do **not** add `run_attempts` as a sixth canonical table in V4 v1.

If worker-attempt history is initially only needed for operations, represent it through:

- lease fields on `runs`;
- typed `run_events` such as `attempt.started`, `attempt.lost`, `attempt.reacquired`;
- checkpoint generation.

If real multi-worker operations later require first-class attempt querying, add `run_attempts` only through a dedicated ADR.

## 7.2 `agent_core.run_checkpoints`

Paperclip's session continuity must not be confused with checkpoint durability.

The checkpoint contract should explicitly distinguish:

```text
KernelCheckpointState
    - OpenAI Agents SDK serialized RunState

WorkflowCheckpointState
    - WorkflowEngine deterministic state

ProviderSessionState
    - Claude/Codex/provider session continuation metadata
    - optional optimization
    - not authoritative resume truth
```

Recommended metadata:

```text
checkpoint_ref
run_id
generation
codec
codec_version
state_hash
state_payload / state_ref
pinned_spec_identity
wait_descriptor (when paused)
created_at
```

### Non-negotiable invariant

```text
provider session exists
```

does **not** imply:

```text
exact durable checkpoint exists
```

Vertical Slice 2 must prove process restart + exact state reload independently of any lucky provider-side session continuation.

## 7.3 `agent_core.run_events`

Paperclip's ordered run-event ledger is useful prior art.

COSA event semantics should support:

```text
monotonic per-run sequence
run.created
run.started
checkpoint.persisted
run.paused
approval.requested
approval.resolved
capability.authorized
capability.started
capability.completed
capability.failed
attempt.started
attempt.lost
attempt.reacquired
run.resumed
run.completed
run.failed
```

Events are for observability and reconstruction evidence; they do not replace the checkpoint state itself.

## 7.4 `agent_core.run_tool_calls`

This table should be strengthened from a simple tool-call log into the canonical **invocation ledger**.

Recommended minimum semantics:

```text
run_id
tool_call_id                    # stable SDK/native call identity
capability_id
capability_version              # when known
payload_hash
idempotency_key
risk_at_request
input_schema_hash               # when known
target_snapshot_hash
target_snapshot_safe_json       # redacted / no raw secrets
policy_decision_at_request
status
result_hash / result summary
started_at / completed_at
```

Paperclip demonstrates why `catalogVersionHash` / `schemaHash`-style fields are operationally valuable: an approval should not silently survive a changed implementation target.

This does **not** require COSA to build a full capability-version registry in v1. Hashes and version refs are enough to establish identity.

## 7.5 `agent_core.approvals`

Keep V4's canonical triple:

```text
run_id
tool_call_id
checkpoint_ref
```

Strengthen the record with evidence sufficient to prove what was actually approved:

```text
invocation_payload_hash
target_snapshot_hash
requested_risk
requested_at
expires_at
requested_by / decided_by
decision
decision_note
approval_requirement/evidence metadata
```

No raw credential material should be stored in the approval snapshot.

---

# 8. Approval semantics — combine Paperclip target integrity with COSA temporal governance

This is the highest-value architectural improvement from the Paperclip audit.

Paperclip has strong protection for:

```text
"Did the thing being executed change after the human reviewed it?"
```

COSA additionally needs to protect:

```text
"Did the rules that permit execution change after the human reviewed it?"
```

These are distinct.

## 8.1 Layer A — invocation integrity

Before executing an approved side effect, verify:

```text
same run_id
same tool_call_id
same capability_id
same payload_hash
same checkpoint_ref
```

## 8.2 Layer B — target integrity

Re-resolve the live execution target and compare it to the approved snapshot.

Examples of drift that must stale the approval:

```text
capability version changed
connector target changed
input schema changed
risk changed MEDIUM → CRITICAL
credential binding/version changed
upstream action changed
provider route materially changed
```

If the target changed, do not execute under the old approval.

Emit a typed result such as:

```text
approval.stale_target
```

and require a new review/policy decision.

## 8.3 Layer C — current temporal governance

Even with identical target and payload, current policy can become stricter while the Run is paused.

Example:

```text
t0: policy requires Founder approval
    Founder approves

t1: policy changes to Founder + Security approval

t2: Run resumes
```

A target-snapshot comparison alone does not necessarily detect this.

Therefore resume must re-evaluate current governance.

Conceptually:

```text
historical evidence accumulator
        ∧
current policy requirements
        ∧
current ambient hard-stops
        ↓
effective execution authorization
```

A practical decision algorithm is:

```text
1. Validate exact invocation identity.
2. Validate approved target snapshot against current target.
3. Re-evaluate current governance for the same invocation.
4. If current policy = DENY → deny.
5. If current policy requires evidence not present in the durable approval/evidence set → pause again.
6. If budget/tenant/kill-switch/current hard-stop denies → deny/pause regardless of historical approval.
7. Only then execute idempotently.
```

This gives COSA both:

```text
Invocation Target Integrity
+
Temporal Governance Integrity
```

Paperclip is strong prior art for the first. COSA should deliberately implement both.

---

# 9. Idempotency — bind side effects to the invocation ledger, not to workflow prose

Paperclip's invocation model correctly treats idempotency as part of execution identity.

COSA should require every side-effecting `CapabilitySpec` to declare its idempotency behavior.

Minimum model:

```python
class IdempotencyPolicy(Enum):
    REQUIRED = "required"
    PROVIDER_NATIVE = "provider_native"
    COSA_DERIVED = "cosa_derived"
    NOT_SUPPORTED = "not_supported"
```

For COSA-derived keys, a safe starting point is a hash over stable execution identity, for example:

```text
run_id
+ tool_call_id
+ capability_id
+ payload_hash
```

Provider-specific APIs may require a dedicated idempotency key format, but the mapping must remain durable in `run_tool_calls`.

### Required invariant

```text
process dies after external side effect succeeded
but before local completion event persisted
        ↓
resume/retry
        ↓
must not duplicate the side effect
```

Vertical Slice 2 should test exactly this failure window.

---

# 10. WorkflowEngine delta — exact-once expansion, not a new workflow architecture

The CrewAI Supplement already corrected the workflow mistake: COSA has an audited internal WorkflowEngine source and must promote it rather than create a duplicate runtime.

Paperclip adds one especially valuable invariant: **fan-out must have a durable identity**.

Paperclip's accepted-plan decomposition uses a fingerprint based on the source issue and accepted plan revision so retries cannot create duplicate child trees.

COSA should generalize this into an `ExpansionFingerprint` contract for operations that create durable children/delegations.

Examples:

```text
Workflow parallel expansion
Supervisor delegation
Plan → child work decomposition
Compensation fan-out
Batch connector writes
```

Suggested semantic identity:

```python
@dataclass(frozen=True)
class ExpansionFingerprint:
    parent_run_id: str
    operation_id: str
    source_revision: str | None
    input_hash: str
```

The exact fingerprint may be domain-specialized when the business artifact has a stronger immutable revision identity.

## 10.1 Execution rule

Before child creation/fan-out:

```text
persist claim/fingerprint + intended operation state
```

As children are created:

```text
persist partial result into checkpoint/event/business relation
```

On retry:

```text
reuse existing claim and existing children
```

Never:

```text
re-read an old approval/plan and treat it as fresh permission to fan-out again
```

## 10.2 Where to store it in v1

Do not add a generic `expansions` table yet.

Use:

- WorkflowEngine checkpoint state;
- `run_events` for durable evidence;
- canonical business child relation in `services/company/operations` where appropriate.

A dedicated table becomes justified only if cross-run querying/repair requires it.

---

# 11. Waiting semantics — no prose-only pause

This is one of the most transferable Paperclip lessons.

COSA already needs approval pause/resume. The architecture should make the general rule explicit:

> A Run is only legitimately waiting if a durable path exists that can move it forward.

## 11.1 Healthy wait examples

```text
WAITING_APPROVAL
    approval row exists
    owner/approver is resolvable
    checkpoint_ref exists

WAITING_DEPENDENCY
    durable dependency ref exists
    completion event can wake/re-evaluate

WAITING_EXTERNAL_EVENT
    durable subscription/correlation exists

WAITING_TIMER
    durable scheduled trigger exists
```

## 11.2 Unhealthy wait

```text
status = waiting
reason = "Need someone to review this"
```

with no approval/dependency/owner/trigger is a stranded Run.

## 11.3 V4 v1 action

Implement only:

```text
WAITING_APPROVAL
```

end-to-end in Step 6.

But design status/checkpoint/event contracts so future wait kinds have a typed home instead of reopening the entire persistence architecture.

---

# 12. Run liveness and worker ownership — adapt the invariant, not Paperclip's heartbeat model

Paperclip's distinction between checkout ownership and live execution is useful, but COSA should not convert itself into a heartbeat-oriented runtime.

COSA's desired semantics are:

```text
Run = stable logical execution identity
```

A Run can survive:

```text
process restart
worker crash
approval pause
worker replacement
deployment restart
```

without becoming a new Run.

## 12.1 `ExecutionLease`

Introduce a semantic execution lease:

```python
@dataclass(frozen=True)
class ExecutionLease:
    run_id: str
    owner_id: str
    epoch: int
    expires_at: datetime
```

The physical implementation may be row fields, Postgres locking, or another safe lease primitive.

The lease must support:

```text
acquire
renew
compare-and-release
expire
reacquire after worker loss
```

### Required invariant

A stale worker from epoch N must never be allowed to finalize or execute side effects after epoch N+1 acquired the Run.

This is the direct COSA adaptation of Paperclip's careful compare-and-clear execution lock handling.

## 12.2 `WorkerAttempt`

Treat worker attempt as observability metadata, not canonical Run identity in v1.

This prevents the common mistake:

```text
retry == new Run
```

when the desired semantics are actually:

```text
same Run + new execution attempt + same pinned spec + checkpoint resume
```

---

# 13. Recovery semantics — restore liveness, never silently rewrite authority

Paperclip's recent recovery direction is particularly compatible with COSA's `WorkforceMember` and governance model.

Recovery is allowed to:

```text
reacquire a lost Run lease
reload an exact checkpoint
retry a safe provider call
resume the same owner/AgentSpec
schedule a bounded retry
surface a recovery action
escalate to a human/governance owner
```

Recovery is **not** allowed to:

```text
silently replace the WorkforceMember owner
silently promote autonomy level
silently choose a manager/CEO as executor
silently bypass an approval requirement
silently choose a more powerful capability
```

## 13.1 Suggested recovery classification

No new subsystem is required, but use typed reasons from the beginning:

```text
PROCESS_LOST
LEASE_EXPIRED
PROVIDER_QUOTA
PROVIDER_TRANSIENT
CHECKPOINT_CORRUPT
CONFIGURATION_INCOMPLETE
CREDENTIAL_UNAVAILABLE
TARGET_DRIFT
APPROVAL_STALE
OUTPUT_STALLED          # only if COSA later has a reliable signal
UNKNOWN
```

A recovery decision should be deterministic enough to audit:

```text
retry_same_owner
wait
reacquire
require_human_action
fail_terminal
```

## 13.2 Configuration incomplete is not a model failure

Paperclip's pre-dispatch validation lesson is strong:

If required secrets/workspace/configuration are known to be missing before dispatch, do not start a Run that is guaranteed to fail and then classify it as an agent failure.

COSA should separate:

```text
PRE_DISPATCH_GATE_FAILURE
```

from:

```text
RUN_EXECUTION_FAILURE
```

This improves liveness, eval quality and operator diagnosis.

---

# 14. Scheduling and wake coalescing — contract now, persistence later

Paperclip proves that autonomous systems eventually need durable trigger semantics.

But COSA V4 does not need a Paperclip-style heartbeat scheduler to prove the first canonical Agent Core.

Therefore:

## P0/V4 v1

Keep execution entry explicit:

```text
API / workflow / approved command
        ↓
RunRequest
        ↓
Run
```

Define trigger metadata on `RunRequest`:

```python
@dataclass(frozen=True)
class RunTrigger:
    source: Literal["api", "workflow", "schedule", "event", "recovery"]
    source_ref: str | None
    idempotency_key: str | None
    coalesce_key: str | None
```

## P1 when autonomous recurring/event work is real

Add a durable control-plane trigger/wake queue in the **Encore/control plane**, not inside model/kernel code.

Required semantics:

```text
idempotent enqueue
coalesce duplicate triggers
bounded retries
scheduled retry time
actor/source attribution
link to created run
```

Do not add this table merely because Paperclip has one.

---

# 15. Business work ownership — learn from Paperclip without creating `issues`

Paperclip's work model is mature, but COSA must keep its own business ontology.

The useful invariant is:

```text
structure
≠
dependency
≠
ownership
≠
execution
```

COSA should apply this to whatever canonical work objects exist or emerge under `services/company/operations`.

For example, do not overload a parent-child strategy/mission relation to mean execution dependency.

Keep explicit concepts such as:

```text
parent/child        = structural decomposition
blocked_by          = execution dependency
owner               = WorkforceMember accountable for the work
run_id              = current/related agent execution, not business ownership
```

This avoids a future class of bugs where deleting/retrying a Run accidentally changes business ownership or where a hierarchy is treated as an execution DAG without explicit blockers.

### Important scope rule

This Supplement does **not** mandate a new generic `Task` or `Issue` aggregate. If `services/company/operations` already has a domain-specific object that carries this meaning, extend that object rather than create a duplicate.

---

# 16. Budget and global stop conditions — treat as ambient current governance

Paperclip makes budgets operational: hard limits can pause work, not merely produce dashboard warnings.

COSA should use the same principle while preserving business ownership in `services/`.

Examples of **ambient current governance**:

```text
company paused
workspace disabled
budget hard-stop reached
agent/workforce member disabled
connector revoked
credential revoked
emergency kill switch
```

These must be re-evaluated at execution time and resume time.

A historical approval must never override a current hard-stop.

Recommended rule:

```text
Historical approval = evidence
Current ambient governance = authority
```

Therefore:

```text
approved yesterday
+
budget hard-stop today
=
DO NOT EXECUTE today
```

No duplicate budget accounting should be created in Agent Core. Agent Core queries/receives the current decision through the governance boundary.

---

# 17. Low-trust delegation — adopt provenance boundaries, not Paperclip's exact courier UX

Paperclip contains a useful security insight: agent-to-agent communication can propagate prompt injection across trust boundaries.

COSA should make delegated work carry explicit provenance/trust metadata.

Suggested concepts:

```text
source_trust_level
source_principal_id
source_run_id
source_artifact_refs
sanitization_policy
allowed_report_channels
```

## 17.1 Default rule

A low-trust child/reviewer should not obtain arbitrary write access into a higher-trust parent's mutable context merely because it is part of the same coordination graph.

Prefer:

```text
explicit child Run/work item
self-contained delegated context
structured result/artifact
parent synthesis under parent's trust boundary
```

rather than unrestricted shared transcript mutation.

## 17.2 P1, not Step-6 blocker

This is security architecture worth retaining, but it should not expand V4's first read/write vertical slices unless the first COSA AgentSpec already delegates to low-trust reviewer agents.

---

# 18. Provider sessions — useful optimization, explicitly non-canonical

Paperclip's `agent_task_sessions` and effective-config fingerprints provide a good pattern for CLI-provider continuity.

COSA may eventually need a provider/session envelope such as:

```python
@dataclass
class ProviderSessionState:
    provider: str
    session_id: str | None
    display_id: str | None
    config_fingerprint: str
    last_run_id: str
```

Use it for:

```text
Claude/Codex session reuse
provider-side cache/context continuity
session reset when model/config changes
operational diagnostics
```

Do not use it for:

```text
approval checkpoint identity
workflow checkpoint identity
exact OpenAI Agents SDK RunState resume
```

This distinction should appear in code names and schema documentation so future developers do not accidentally implement "durability" by persisting only a provider session ID.

---

# 19. Capability Layer — proposed stronger target after Paperclip audit

V4 already promotes `ToolSpecV2` invariants into a generalized `CapabilitySpec`.

Paperclip suggests strengthening the execution path around that spec.

Target flow:

```text
ExecutionKernel / WorkflowEngine
             │
             ▼
     Capability Gateway
             │
             ├── resolve CapabilitySpec
             ├── resolve current target
             ├── validate tenant/workforce scope
             ├── evaluate current governance
             ├── create/reuse run_tool_call ledger row
             ├── require approval if needed
             ├── persist exact checkpoint if pausing
             ├── enforce idempotency
             ├── execute provider/connector/MCP target
             └── persist result + audit events
```

## 19.1 What the Gateway must own

```text
canonical invocation identity
policy gate ordering
approval binding
idempotency mediation
target snapshot generation
execution audit emission
```

## 19.2 What the Gateway must not own

```text
business truth
WorkforceMember database
provider-specific reasoning loop
workflow DAG definition
COSA startup methodology
```

---

# 20. Proposed repository structure — delta only

This is **not a command to reorganize the whole repository**. It is the target placement for the new contracts/modules justified by V4 + this Supplement.

```text
packages/
└── agent_core/
    ├── contracts/
    │   ├── run.py
    │   ├── specs.py
    │   ├── identity.py          # Principal projection contract
    │   ├── invocation.py       # InvocationIdentity
    │   ├── target.py           # ExecutionTargetSnapshot
    │   └── wait.py             # WaitDescriptor
    │
    ├── execution/
    │   ├── kernel.py
    │   ├── openai_agents.py
    │   ├── model_policy.py
    │   └── provider_session.py  # optional optimization contract
    │
    ├── durability/
    │   ├── runs.py
    │   ├── checkpoints.py
    │   ├── events.py
    │   ├── tool_calls.py
    │   ├── approvals.py
    │   ├── leases.py
    │   └── codecs/
    │       ├── openai_run_state.py
    │       └── workflow_state.py
    │
    ├── capabilities/
    │   ├── spec.py
    │   ├── registry.py
    │   ├── gateway.py
    │   ├── idempotency.py
    │   └── target_snapshot.py
    │
    ├── governance/
    │   ├── engine.py
    │   ├── decisions.py
    │   └── evidence.py
    │
    ├── workflows/
    │   ├── spec.py              # promoted from existing WorkflowSpec semantics
    │   ├── engine.py
    │   ├── loader.py
    │   └── steps/
    │
    ├── coordination/
    │   ├── delegation.py
    │   ├── parallel.py
    │   ├── sequential.py
    │   ├── debate.py
    │   ├── supervisor.py
    │   └── expansion.py         # ExpansionFingerprint helper, not a runtime root
    │
    ├── recovery/
    │   ├── classifier.py
    │   └── policy.py
    │
    ├── connectors/
    ├── memory/
    ├── knowledge/
    ├── artifacts/
    └── evals/

apps/
└── cosa/
    ├── agents/
    │   ├── cofounder.yaml
    │   ├── finance.yaml
    │   └── ...
    ├── workflows/
    ├── context/
    ├── api/
    └── evals/

services/
├── company/
│   ├── identity/                # canonical WorkforceMember
│   ├── operations/
│   │   └── strategy/            # already exists at current baseline
│   ├── commercial/
│   └── finance-legal/
│
└── cosa/
    ├── handlers/                # existing surface
    ├── models/                  # existing surface
    └── agent-control/           # ADD ONLY when implementation needs it
        ├── run-client.ts        # commands/queries Agent Core, does not write its DB directly
        ├── approval-handler.ts
        ├── policy-context.ts
        └── event-projection.ts
```

## 20.1 Important: `services/cosa/agent-control/` is optional placement, not a required new service

Do not create it merely to satisfy the diagram.

If the existing handler/service layout can cleanly host these responsibilities, keep the current structure.

The architectural requirement is ownership, not folder aesthetics:

```text
services/cosa commands Agent Core
Agent Core owns execution rows
```

not:

```text
services/cosa and Python both mutate agent_core tables
```

---

# 21. What should be added to the V4 Step-6 schema now vs later

## Add/ensure now — P0

Within the existing five-table model:

```text
runs:
  pinned spec identity/snapshot
  current checkpoint ref
  safe lease semantics when concurrent workers are enabled

run_checkpoints:
  codec + codec version
  state hash
  pinned spec identity
  typed wait descriptor metadata

run_events:
  monotonic sequence
  typed attempt/pause/resume/capability events

run_tool_calls:
  stable tool_call_id
  capability_id/version
  payload_hash
  idempotency_key
  risk_at_request
  schema/implementation/target snapshot hashes

approvals:
  run_id/tool_call_id/checkpoint_ref
  invocation hash
  target snapshot hash
  expiry + decision evidence
```

## Do not add now — unless a concrete use case proves need

```text
interruptions
external_event_waits
run_attempts
expansions
wake_requests
pipeline_revisions
plugin_runtime tables copied from Paperclip
```

This keeps V4's durable model compact while retaining clear extension points.

---

# 22. V4 lifecycle annotations — Paperclip lessons mapped to the existing 11 steps

No new phase framework is introduced.

## Step 1 — Correct architecture truth

Add to architecture/ownership documentation:

- Paperclip is **external control-plane prior art**, not an implementation dependency.
- current Javis baseline is `b39246c`, with `services/company/*` and `services/cosa` split already present;
- `services/company/operations/strategy` already exists — do not invent a second strategy bounded context;
- define the three-plane ownership model in this Supplement.

## Step 2 — Freeze inert prototype

No Paperclip-derived implementation work belongs here.

Do not retrofit wake queues, leases or target snapshots into frozen `agentos/core/runtime.py`.

## Step 3 — Define VNext contracts

Add:

```text
PinnedSpecIdentity
InvocationIdentity
ExecutionTargetSnapshot
WaitDescriptor
RunTrigger metadata
ExecutionLease semantic contract
ExpansionFingerprint
```

Only contracts that are used by the first slices should be implemented immediately.

## Step 4 — Build clean reusable Agent Core

Implement:

- clear logical Run vs worker lease vs provider session distinction;
- checkpoint codecs;
- recovery policy interface;
- exact-once coordination helper where needed.

Do not build a heartbeat scheduler.

## Step 5 — Integrate OpenAI Agents kernel

The critical Paperclip-related rule is negative:

> Provider/session continuation is not a substitute for serializable OpenAI Agents SDK `RunState`.

Compatibility matrix must still test exact RunState resume and approval interruption.

## Step 6 — Durable run/checkpoint/event model

This is where most Paperclip-derived value lands:

- invocation ledger;
- approval target snapshot;
- idempotency mapping;
- typed waits;
- execution lease safety;
- ordered run events;
- pinned spec identity.

Do not add new root tables.

## Step 7 — Governance/capability/connector/workflow layer

Add:

- target integrity check at approved execution;
- current-governance re-evaluation at resume;
- ambient hard-stop checks;
- capability implementation/schema/version hashes when available;
- exact-once workflow/delegation expansion.

Keep existing WorkflowEngine promotion plan unchanged.

## Step 8 — Compose COSA app on top

Map business semantics rather than Paperclip entities:

- business work remains in `services/company/operations`;
- owner resolves to `WorkforceMember`;
- parent structure is not automatically dependency;
- delegated child work has explicit provenance and result channels;
- schedules/triggers are added only for real COSA use cases.

## Step 9 — Eval + integration + security gates

Add the acceptance matrix in §24.

Paperclip-specific benchmarks are unnecessary; test the adapted invariants against COSA contracts.

## Step 10 — Wire first canonical integration entrypoint

The canonical entrypoint must create/query Runs through one Agent Core API path.

No direct dual-write from Flutter/Encore into Agent Core persistence.

## Step 11 — Archive/delete inert prototype

Archive the old in-memory approval/replay/session semantics once the new invariant tests pass.

Do not keep a compatibility layer merely because Paperclip uses adapters for external runtimes; COSA's old prototype is not an external provider that needs permanent support.

---

# 23. Vertical Slice 1 — read path, strengthened but not enlarged unnecessarily

V4 Slice 1 remains:

```text
user
→ new API
→ durable Run
→ OpenAI Agents kernel
→ read-only capability
→ streamed events
→ final
→ trace/usage
```

Add these assertions:

1. `Run` pins exact `AgentSpec` identity at creation.
2. `run_events` are monotonically ordered per Run.
3. read-only tool call creates a `run_tool_calls` ledger entry with stable `tool_call_id` and payload hash.
4. provider session metadata, if present, is not required to reconstruct the final result.
5. changing `AgentSpec.current` during the test does not alter the already-created Run's pinned identity.
6. capability target/schema/version metadata is recorded when the adapter exposes it.
7. tenant/workforce context is resolved from canonical services identity, not invented inside Agent Core.

This slice should still remain cheap and fast.

---

# 24. Vertical Slice 2 — write + approval, expanded into the real durability/security gate

V4 Slice 2 remains the decisive proof:

```text
write capability
→ policy
→ approval required
→ exact checkpoint persist
→ process restart
→ approve
→ exact resume
→ idempotent side effect
```

The Paperclip audit justifies making the acceptance test stricter.

## 24.1 Required acceptance matrix

| Scenario | Expected result |
|---|---|
| same invocation, same target, same policy, approved | resume and execute once |
| payload changed after approval | stale/invalid approval; no execute |
| capability/tool_call identity changed | stale/invalid approval |
| target connector changed | stale target; fresh review |
| capability version changed | stale target or policy re-evaluation |
| input schema hash changed | stale target |
| risk MEDIUM → CRITICAL | old approval not sufficient |
| credential binding/version changed | stale target or fresh authorization |
| policy becomes stricter while paused | pause again / require missing current evidence |
| policy becomes DENY while paused | deny on resume |
| company/workspace hard-stop while paused | deny/pause regardless of approval |
| process dies before approval | reload checkpoint on another process/worker |
| process dies after side effect but before local completion persist | retry does not duplicate side effect |
| two workers race to resume same Run | one lease epoch wins; stale worker cannot execute/finalize |
| AgentSpec current changes while paused | resumed Run still uses pinned old spec |
| provider session unavailable after restart | exact checkpoint resume still works |

If these pass, COSA has a materially stronger execution contract than simply copying Paperclip's approval flow.

---

# 25. Additional tests for WorkflowEngine / coordination

## 25.1 Exact-once fan-out test

```text
1. Start workflow/delegation expansion.
2. Persist expansion fingerprint.
3. Create child A and child B.
4. Crash before child C / before parent checkpoint finalize.
5. Restart process.
6. Resume same checkpoint.
7. Reuse A and B.
8. Create only missing C.
9. Final result contains exactly A/B/C once.
```

## 25.2 Routable wait test

Any workflow step returning a waiting status without a valid `WaitDescriptor` must fail validation or become an explicit error, not remain silently waiting.

## 25.3 Stale lease test

Worker A loses lease, Worker B acquires next epoch, then A returns late.

A must not be able to:

```text
write checkpoint
execute capability
mark Run completed
release B's lease
```

## 25.4 Recovery authority test

When recovery exhausts retries, it may create/escalate a recovery action but must not silently change `Principal`/`WorkforceMember` ownership.

---

# 26. P0 / P1 / P2 priorities after the Paperclip audit

## P0 — incorporate into VNext contracts / first two slices

1. **Pinned spec identity** for AgentSpec and WorkflowSpec.
2. **Exact invocation ledger** in `run_tool_calls`.
3. **Approval target snapshot** with capability/schema/risk/connector identity.
4. **Current-governance re-evaluation** on approved resume.
5. **Idempotency key persistence** for side-effecting capability calls.
6. **Typed wait descriptor** for approval pause.
7. **Checkpoint vs provider-session separation**.
8. **Logical Run vs execution lease/attempt separation**.
9. **Exact-once expansion fingerprint** for any first-slice fan-out/delegation path.
10. Security/durability tests in §24–25.

## P1 — implement when COSA app behavior needs them

1. bounded recovery classifier/policy;
2. pre-dispatch configuration-incomplete gates;
3. budget/current hard-stop integration;
4. low-trust delegation provenance/report-channel rules;
5. durable schedule/event trigger queue with coalescing;
6. provider-session config fingerprints for CLI/session-based adapters;
7. operator-facing run liveness/recovery projections.

## P2 — defer until scale/use-case proves value

1. first-class `run_attempts` table;
2. generalized `interruptions` table;
3. generalized external-event wait registry;
4. work queues inspired by Paperclip;
5. plugin marketplace/runtime architecture;
6. generalized capability implementation registry beyond version/hash refs;
7. complex automatic organizational self-healing/reassignment policy.

---

# 27. Explicit rejections — what should NOT enter COSA because of this audit

## 27.1 Do not run Paperclip beside COSA

Rejected topology:

```text
Flutter
  ↓
Encore
  ↓
Paperclip server
  ↓
Python Agent Core
```

This creates a double control plane and competing canonical entities.

## 27.2 Do not replace Agent Core with TypeScript

Paperclip's TypeScript implementation is evidence that a strong control plane can be TypeScript; it is not evidence that COSA's reasoning/execution kernel should move from Python.

V4's Python Agent Core remains the better fit for OpenAI Agents SDK and current COSA assets.

## 27.3 Do not copy Paperclip `Issue` as COSA's universal task model

COSA business semantics already belong to its own service bounded contexts.

Adopt:

```text
structure vs dependency vs ownership vs execution
```

not the entity name.

## 27.4 Do not copy Paperclip pipelines into WorkflowEngine

Paperclip pipelines are business stage/case state machines.

COSA's audited `agentos/workflows/` remains the source for deterministic DAG workflow semantics.

## 27.5 Do not treat heartbeat/session persistence as exact resume

The V4 Step-6 checkpoint remains authoritative.

## 27.6 Do not create all Paperclip operational tables preemptively

The point of the audit is to learn invariants, not to reproduce its schema count.

---

# 28. Architecture rules to add to the implementation checklist

A coding agent implementing VNext should be able to answer **yes** to all of these before merge:

1. Does every Run pin exact spec identity/snapshot?
2. Can an old Run resume without resolving mutable `latest`?
3. Is a provider session explicitly non-canonical?
4. Does every side-effecting call have stable `tool_call_id` and payload hash?
5. Is every approval bound to `run_id/tool_call_id/checkpoint_ref`?
6. Does approval also bind a safe execution-target snapshot/hash?
7. Is target drift checked before executing an approved action?
8. Is current governance re-evaluated after a pause?
9. Can current budget/kill-switch/tenant policy stop a historically approved action?
10. Is idempotency persisted before/with dispatch of a side effect?
11. Can process restart resume from the exact checkpoint on a different worker?
12. Can two workers race without double execution?
13. Does every wait state have a durable routable trigger/owner/ref?
14. Does recovery preserve authority/ownership unless an explicit approved policy changes it?
15. Is fan-out/delegation retry exact-once relative to a durable fingerprint?
16. Are business ownership and execution Run identity separate?
17. Does Agent Core avoid owning WorkforceMember/business truth?
18. Does Encore avoid directly dual-writing Agent Core execution tables?
19. Are external Paperclip paths clearly marked `EXTERNAL[...]::`?
20. Did the implementation adapt an invariant rather than copy an external subsystem?

---

# 29. Recommended ADR consequences

This Supplement itself does not create ADRs, but the following decisions are important enough that implementation should eventually freeze them in existing/new ADRs as appropriate.

## ADR candidate A — Durable Run identity and pinned spec semantics

Freeze:

```text
Run is logical identity
specs are immutable/pinned for a Run
provider sessions are non-canonical
```

## ADR candidate B — Approval = invocation evidence + target integrity + current governance

Freeze:

```text
run_id/tool_call_id/checkpoint_ref
payload hash
target snapshot
current policy re-evaluation
ambient hard-stop precedence
```

## ADR candidate C — Execution lease semantics

Freeze compare-and-lease/epoch behavior before multi-worker execution is enabled.

## ADR candidate D — Waiting-state contract

Freeze the rule that a waiting Run must have a durable routable path.

Do not create these ADRs merely to increase document count; create them when the corresponding implementation PR begins or when the existing ADR set needs an explicit amendment.

---

# 30. Relationship to the CrewAI Supplement

The two external audits now serve different purposes.

```text
CrewAI Supplement
    → Flow authoring/runtime separation
    → HITL patterns
    → optional adapter benchmark
    → reinforced internal WorkflowEngine audit

Paperclip Supplement
    → durable control-plane semantics
    → run ownership/liveness
    → invocation/approval target identity
    → exact-once side effects/fan-out
    → recovery
    → scheduling/waiting
    → operational governance
```

Neither becomes an architecture root.

The common rule is:

```text
COSA owns its contracts and durable truth.
External frameworks are references/adapters, never owners.
```

---

# 31. External Paperclip source map used for this Supplement

The following are read-only external references.

## Product/control-plane positioning

```text
EXTERNAL[paperclipai/paperclip@05b35d4]::README.md
EXTERNAL[paperclipai/paperclip@05b35d4]::DESIGN.md
```

Useful for:

- control-plane positioning;
- operator model;
- run/budget/approval/audit orientation.

## Execution / work semantics

```text
EXTERNAL[paperclipai/paperclip@05b35d4]::doc/execution-semantics.md
EXTERNAL[paperclipai/paperclip@05b35d4]::doc/spec/agent-runs.md
```

Useful for:

- ownership vs execution distinction;
- routable blocked/waiting semantics;
- accepted-plan exact-once decomposition;
- crash/stale-lock semantics.

## Heartbeat/session durability

```text
EXTERNAL[paperclipai/paperclip@05b35d4]::packages/db/src/schema/heartbeat_runs.ts
EXTERNAL[paperclipai/paperclip@05b35d4]::packages/db/src/schema/heartbeat_run_events.ts
EXTERNAL[paperclipai/paperclip@05b35d4]::packages/db/src/schema/agent_task_sessions.ts
EXTERNAL[paperclipai/paperclip@05b35d4]::server/src/services/heartbeat.ts
```

Useful for:

- event ledger;
- liveness/retry/session continuity;
- config/session freshness.

Caution: these are **not** equivalent to OpenAI Agents SDK exact RunState checkpoints.

## Revision-pinned routines

```text
EXTERNAL[paperclipai/paperclip@05b35d4]::packages/db/src/schema/routines.ts
EXTERNAL[paperclipai/paperclip@05b35d4]::server/src/services/routines.ts
```

Useful for:

- immutable revision snapshot;
- run pins exact revision;
- trigger idempotency/coalescing.

## Tool/capability governance

```text
EXTERNAL[paperclipai/paperclip@05b35d4]::packages/db/src/schema/tool_access.ts
EXTERNAL[paperclipai/paperclip@05b35d4]::server/src/services/tool-access-policy.ts
EXTERNAL[paperclipai/paperclip@05b35d4]::server/src/services/tool-gateway.ts
EXTERNAL[paperclipai/paperclip@05b35d4]::server/src/routes/tool-gateway.ts
```

Useful for:

- invocation ledger;
- risk/schema/catalog identity;
- approval action request;
- signed canonical arguments;
- target drift detection;
- idempotency;
- MCP gateway policy enforcement.

## Recovery and budgets

```text
EXTERNAL[paperclipai/paperclip@05b35d4]::server/src/services/recovery/service.ts
EXTERNAL[paperclipai/paperclip@05b35d4]::server/src/services/budgets.ts
```

Useful for:

- liveness/recovery reason classification;
- no-silent-takeover direction;
- hard-stop execution behavior.

## Plugin caveats

```text
EXTERNAL[paperclipai/paperclip@05b35d4]::doc/plugins/PLUGIN_SPEC.md
```

Useful mainly as a warning not to confuse target plugin architecture with currently isolated/cloud-ready implementation.

## Evaluation evidence

```text
EXTERNAL[paperclipai/paperclip@05b35d4]::evals/promptfoo/mcp-gateway-gap-memo.md
EXTERNAL[paperclipai/paperclip@05b35d4]::server/src/__tests__/tool-gateway.test.ts
EXTERNAL[paperclipai/paperclip@05b35d4]::server/src/__tests__/tool-gateway-service.test.ts
EXTERNAL[paperclipai/paperclip@05b35d4]::server/src/__tests__/tool-access-service.test.ts
EXTERNAL[paperclipai/paperclip@05b35d4]::server/src/__tests__/execution-lock-orphan-cleanup.test.ts
```

Useful for:

- expected agent response to approval/deny/rate-limit/credential/target drift;
- mechanical service enforcement;
- stale execution lock recovery.

---

# 32. Internal COSA source map relevant to this Supplement

Current baseline:

```text
INTERNAL[vutasoftvn/javis-saas@b39246c]::services/company/identity/
INTERNAL[vutasoftvn/javis-saas@b39246c]::services/company/operations/
INTERNAL[vutasoftvn/javis-saas@b39246c]::services/company/operations/strategy/
INTERNAL[vutasoftvn/javis-saas@b39246c]::services/cosa/
INTERNAL[vutasoftvn/javis-saas@b39246c]::services/cosa/handlers/agent-policy.handler.ts
```

Promotion sources already audited in the CrewAI/V4 work:

```text
INTERNAL[vutasoftvn/javis-saas@b39246c]::agentos/workflows/schema.py
INTERNAL[vutasoftvn/javis-saas@b39246c]::agentos/workflows/engine.py
INTERNAL[vutasoftvn/javis-saas@b39246c]::agentos/workflows/steps.py
INTERNAL[vutasoftvn/javis-saas@b39246c]::agentos/workflows/tool_step.py
INTERNAL[vutasoftvn/javis-saas@b39246c]::agentos/workflows/approval_step.py
INTERNAL[vutasoftvn/javis-saas@b39246c]::agentos/core/policy.py
INTERNAL[vutasoftvn/javis-saas@b39246c]::agentos/tools/spec.py
```

These internal sources remain higher-authority implementation inputs than analogous Paperclip abstractions.

---

# 33. Consolidated target architecture after V4 + CrewAI A2 + Paperclip P1

The architecture should now be read as:

```text
┌──────────────────────────────────────────────────────────────────────┐
│ COSA BUSINESS / CONTROL PLANE — TypeScript / Encore                 │
│                                                                      │
│ WorkforceMember | strategy/work | finance | commercial | policies    │
│ approval decision endpoints | business hard-stops | API projections  │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                │ typed contracts / commands / queries
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ COSA AGENT APPLICATION — apps/cosa                                  │
│                                                                      │
│ AgentSpec snapshots | WorkflowSpec | company context | eval suites    │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ REUSABLE AGENT CORE — packages/agent_core                           │
│                                                                      │
│ contracts                                                            │
│   ├─ PinnedSpecIdentity                                              │
│   ├─ InvocationIdentity                                              │
│   ├─ ExecutionTargetSnapshot                                         │
│   └─ WaitDescriptor                                                  │
│                                                                      │
│ ExecutionKernel                 WorkflowEngine                       │
│        │                              │                               │
│        └──────────────┬───────────────┘                               │
│                       ▼                                               │
│                Capability Gateway                                    │
│        target integrity + governance + idempotency                   │
│                       │                                               │
│                       ▼                                               │
│ Durable Run substrate                                                 │
│ runs | checkpoints | events | tool_calls | approvals                  │
│     + lease semantics + exact checkpoint codecs                      │
│                                                                      │
│ coordination | recovery | connectors | memory | knowledge | artifacts│
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ PROVIDERS / EFFECTS                                                  │
│                                                                      │
│ OpenAI Agents SDK | DeepSeek route | MCP | Gmail | GitHub | Calendar │
│ other connectors / external business systems                         │
└──────────────────────────────────────────────────────────────────────┘
```

The most important new invariant is the chain around a write:

```text
Pinned Run
  ↓
Exact tool call identity
  ↓
Current capability resolution
  ↓
Current governance
  ↓
Persist invocation ledger
  ↓
Persist exact checkpoint if approval required
  ↓
Approval bound to invocation + target snapshot + checkpoint
  ↓
Process may die
  ↓
Reload exact checkpoint
  ↓
Re-check invocation identity
  ↓
Re-check target integrity
  ↓
Re-check current governance / hard-stops
  ↓
Execute idempotently exactly once
  ↓
Persist result + events
```

This is the control-plane quality bar COSA should target.

---

# 34. Final decision

The Paperclip audit **does justify changing the detail of COSA V4**, but not its root direction.

Keep V4 unchanged at the strategic level:

```text
promotion, not migration
Python Agent Core
OpenAI Agents SDK primary kernel
WorkflowEngine promoted from existing agentos/workflows
Capability/Governance owned by COSA
WorkforceMember canonical identity
business truth in services/
five-table durable Step-6 substrate
```

Strengthen V4 with these Paperclip-derived invariants:

```text
1. immutable/pinned AgentSpec + WorkflowSpec identity per Run
2. logical Run separated from worker attempt/provider session
3. routable durable waiting state
4. exact invocation ledger for every side effect
5. approval binds payload + target snapshot + checkpoint
6. target/schema/risk/credential drift invalidates stale approval
7. current governance/hard-stops are re-evaluated on resume
8. idempotency protects the external side-effect failure window
9. fan-out/delegation has exact-once durable fingerprint
10. recovery restores liveness but cannot silently rewrite authority
11. business structure/dependency/ownership/execution remain separate
12. future trigger queues coalesce/idempotently dispatch work, but are not a v1 kernel feature
13. low-trust delegated work carries provenance and bounded report channels
```

The net effect is **not more architecture**. It is a sharper set of invariants inside the V4 architecture that already exists.

If only three Paperclip lessons are implemented immediately, they should be:

```text
A. PinnedSpecIdentity
B. invocation + approval target integrity + current-governance resume check
C. exact checkpoint + idempotent side-effect restart test
```

Those three close the highest-risk gaps before COSA's first canonical VNext entrypoint is wired.
