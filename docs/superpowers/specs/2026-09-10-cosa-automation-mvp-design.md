# COSA Automation MVP — Design Specification

**Status:** IMPLEMENTED (2026-09-10) — Tasks 0–10 landed on `main`. WIRED across
Company / Control Plane / Agent Platform / Flutter; cross-plane E2E authored
(`make automation-mvp-e2e`). Not yet VERIFIED: the disposable-Postgres 3-plane
run is pending a healthy `real_cosa_stack` harness (the shared fixture 500s at
`/platform/auth/register` on the current dev machine, independent of this
work). Not PRODUCTION — rollout ships disabled per workspace.
**Date:** 2026-09-10
**Scope:** Automation definitions, invocation/run lifecycle, governance, blueprint library and Run Inspector.
**Out of scope:** Generic workflow platform, free-form YAML/DAG authoring, dynamic plugins, and a gRPC worker controller.

## 1. Purpose

COSA Automation turns durable agent execution into understandable, governed business automation. It is a curated library of business playbooks with immutable versions, typed configuration, durable execution evidence, and explicit human control of risky effects.

The design borrows Kestra 2.0's useful operating model—definition, revision, execution, task-level observability and context-aware UI—without making COSA a general infrastructure orchestrator. COSA retains local-first data boundaries and its existing business-governance model.

## 2. Goals and non-goals

### Goals

1. A founder configures and runs a curated automation without editing code, YAML, prompt, capability or secret.
2. Every run is attributable to one immutable revision, policy snapshot, trigger source, principal and execution manifest.
3. Run Inspector exposes real status, step evidence, approval, retry and failure data.
4. Every side effect remains capability-gated, tenant-scoped, idempotent and auditable across retry, cancellation and failover.
5. The feature reuses the existing RunRecord, checkpoint, event, tool-call ledger, approval ledger, scheduler, lease and runtime router.

### Non-goals

1. No generic visual programming product, free-form YAML, arbitrary script/HTTP task or user-installed plugin.
2. No outbound persistent gRPC Worker Controller in MVP; typed dispatch, scheduler, lease and runtime-node mechanisms remain the transport.
3. A workflow is not automatically an MCP tool.
4. An LLM cannot publish an automation, grant a capability, change a policy or approve an effect.
5. The MVP does not deliver an external message or change a financial/legal record.

## 3. Ownership and execution path

### 3.1 Plane ownership

| Concern | Authoritative owner | Responsibility |
|---|---|---|
| Blueprint, applicability, invocation and business outcome link | Company Business Plane | Business truth, membership/role and business-scope checks |
| Timer, dispatch delivery, worker lease and runtime-node routing | COSA Control Plane | Durable coordination with opaque references only |
| Manifest, run, checkpoint, tool call, approval and execution event | Agent Platform | Execute only through Capability Gateway and retain evidence |
| Library, configuration, Needs You and Run Inspector | Flutter Experience Plane | Present records; never infer a state from model text |

Cross-plane references are opaque IDs; there are no cross-database foreign keys. The Agent Platform never writes a business database directly. A business effect is always a server-authorized Company capability.

### 3.2 Execution path

~~~text
Flutter
  → Company Automation handler: authorize + validate business scope
  → AutomationInvocation persisted with idempotency key + Company outbox event
  → Control Plane: schedule/dispatch reference + lease/routing
  → Agent worker: resolve immutable ExecutionManifest and create/claim RunRecord
  → Capability Gateway: policy + connector grant + approval gate + effect
  → Agent evidence: checkpoint, event, tool-call and artifact reference
  → Company outcome projection and Flutter Run Inspector
~~~

The queue contains only workspace ID, invocation ID, definition revision/hash, trigger metadata and idempotency key. It contains no raw business content, vault object reference, upload ticket, credential, connector secret or unredacted prompt data.

## 4. Domain model

### 4.1 Definition and revision

AutomationDefinition is a named, workspace-applicable business playbook. It is not an AgentSpec and does not replace an AI employee, skillpack or business Task.

AutomationRevision is immutable. It records:

- definition ID, monotonically increasing revision number and definition hash;
- typed input/output and configuration-form schemas;
- deterministic step graph and permitted capability IDs;
- evidence contract, autonomy class and approval requirements;
- trigger and idempotency contracts;
- pinned AgentSpec/skill references when AI execution is required;
- creation/publish provenance and effective policy revision.

Lifecycle:

~~~text
DRAFT → PUBLISHED → SUSPENDED → RETIRED
~~~

Only PUBLISHED can invoke. Publishing creates a new revision and never changes a historical revision. SUSPENDED blocks new invocations without stopping history or a current run. RETIRED prevents future use but preserves audit evidence.

### 4.2 Invocation, manifest and run

AutomationInvocation is Company-owned business/audit intent. It records caller, source, business scope, validated input reference, idempotency key and requested revision. It gets one linked Agent Platform RunRecord after dispatch.

ExecutionManifest is resolved and pinned before execution. It contains the definition revision/hash, effective policy, AgentSpec/skill versions, capability set, route target, trigger source and redacted input snapshot. Retry/resume always use it; they never silently resolve newer dependencies.

RunRecord remains the execution substrate and retains checkpoints, events, tool calls and approvals. No automation-specific duplicate run table is introduced.

### 4.3 State

~~~text
REQUESTED → QUEUED → LEASED → RUNNING
                       ↘ WAITING_APPROVAL → RUNNING
RUNNING → COMPLETED | FAILED | CANCELLED | BLOCKED
~~~

BLOCKED has a structured actionable cause: unavailable runtime, missing evidence, denied policy or unavailable capability. Terminal state uses durable conditional transition so an old worker or stale lease cannot overwrite it.

## 5. Trigger, idempotency and recovery

Delivery is at-least-once. A capability effect is effectively-once only when its server handler enforces the invocation idempotency key.

| Source | Idempotency scope |
|---|---|
| Manual | workspace ID + definition revision + client request ID |
| Schedule | workspace ID + schedule ID + scheduled-for time |
| Business event | workspace ID + trigger ID + event ID |

The same key returns the original invocation/run. A deliberate manual rerun uses a new client request ID.

Existing heartbeat, visibility timeout, lease and fencing semantics reclaim a dead worker. Late completion from that worker is rejected. Only a capability with a registered idempotency contract may retry automatically. A non-idempotent external effect is BLOCKED, never retried blindly.

REMOTE_ACCESS never fails over to cloud. CLOUD_CONTINUITY can use isolated cloud execution only when the local lease has expired, required sync freshness is met, and the business domain does not require manual failover.

## 6. Governance and authorization

Authorization is action-specific at the service handler; a disabled Flutter button is not authorization.

| Action | Required authority |
|---|---|
| View library, run and evidence | Scoped automation read permission |
| Run published revision | Scoped automation.execute plus valid business scope |
| Configure workspace automation | Scoped configuration permission |
| Publish, suspend or retire | Automation publisher role plus policy validation |
| Approve a gated tool call | Reviewer role required by the exact approval rule |

Publish validation rejects invalid schemas, unregistered capability, forbidden trigger, missing evidence requirement, missing pinned dependency or policy violation. Policies first run report-only; a publish record stores the policy result used at publish time.

Approval binds the exact run ID, tool-call ID and checkpoint reference. Similar action names, another run, another checkpoint and already-decided approval are all rejected. Connector grants are checked immediately before secret resolution and before an external effect. Secrets never appear in a definition, event, checkpoint, log or Flutter payload.

## 7. Product scope and UI

### 7.1 Curated library

MVP system-published, read-first blueprints are:

1. operating.weekly-review: KPI/risk/decision digest with evidence; no mutation.
2. operations.task-follow-up: delayed/blocked work analysis and follow-up recommendation; no external send.
3. commercial.outbound-draft: evidence-backed outbound draft; no delivery.
4. strategy.initiative-health: Initiative/KR/Task deviation and missing-evidence analysis; no authoritative strategy mutation.

All configuration is a guided typed form. A user cannot configure a raw prompt, model provider, capability set, connector secret or arbitrary target.

### 7.2 Automation Library

The Library groups entries by domain and shows purpose, publication state, trigger, last execution, runtime availability and configuration state. Configure opens the typed form. Run now goes through the existing mutation gate and creates a Company invocation.

There is no free-form canvas, YAML editor, plugin picker or generic task palette.

### 7.3 Run Inspector and Needs You

Run Inspector is the primary operational UI. It projects the manifest and event stream as timeline/topology. Selecting a step shows state, timing, retry count, redacted typed input/output, policy decision, approval, artifact/evidence reference and actionable failure reason.

Needs You aggregates exact pending approvals, blocked runs, missing evidence and failed runs. Every item opens its authoritative record. UI must distinguish:

~~~text
forbidden ≠ unavailable ≠ offline ≠ pending ≠ empty ≠ failed
~~~

No badge or color fabricates a status; retry, approval, cancellation and degraded runtime each require their underlying record.

## 8. API and contract

The MVP provides registered, versioned operations to:

- list/read published definitions and configuration schema;
- create/list/read workspace-scoped invocations;
- run a published revision with client idempotency key;
- list/read linked runs, events, checkpoints, artifacts and approvals;
- cancel through durable state transition;
- configure, publish, suspend and retire under server authorization.

Flutter uses only these shared contract types and registered endpoints. Every endpoint appears in shared/contracts/mvp-surface.json. A surface without a real handler, authorization test and frontend contract test is not displayed as available.

Cross-plane dispatch is one typed, versioned envelope. Its producer, scheduler persistence and worker consumer have a single contract test. A mock-accepted payload rejected by the worker blocks release.

## 9. Rollout and migration

All persistence is expand-only and retains existing run/checkpoint/approval/business-audit history.

1. Add revision read model and contract validation behind a disabled feature flag.
2. Add Company invocation creation with idempotent outbox dispatch.
3. Bind manifest/run and reconcile through real scheduler/lease.
4. Ship read-only Library and Run Inspector using real endpoints.
5. Enable mutation and blueprints one at a time, starting read-only.
6. Keep commercial.outbound-draft draft-only until a separate send capability, connector grant and approval E2E test are accepted.

Legacy Workflow UI/API is neither removed nor claimed functional by this work. It is hidden from navigation or labeled unavailable until replaced by a registered, wired contract.

## 10. Acceptance evidence

Static checks, mocks, screenshots and widget tests do not prove this feature. Release evidence must show:

1. A foreign workspace cannot list, read, invoke, cancel or approve another workspace's chain.
2. A caller lacking execute, publish or suspend is rejected at the backend.
3. Duplicate manual, schedule and event delivery creates one invocation, run and effect.
4. A post-checkpoint worker crash is reclaimed; a stale worker cannot overwrite the newer attempt.
5. Cancel racing completion keeps the correct durable terminal state.
6. A mismatched or concurrent approval is rejected or creates exactly one decision.
7. New definition/policy/skill publication after enqueue does not change the running manifest.
8. Run Inspector uses real events/checkpoints and accurately distinguishes forbidden, offline, pending, empty and failed.
9. commercial.outbound-draft cannot deliver externally.
10. A disposable Postgres/process cross-plane test proves Company producer → scheduler → worker → capability → Company outcome, including negative tenancy and crash/retry.

Required gates include affected Encore typecheck/tests, company boundary, Encore handler boundary, frontend API contract, contract freeze, Agent Platform, Flutter and real cross-plane smoke checks. A skipped or credential-blocked process test is unavailable evidence, not a pass.

## 11. Explicit future boundaries

The following are separate future decisions and must not enter MVP: developer-authored automation source language, MCP publication policy, persistent worker-controller protocol, dynamic plugin UI, automated commercial delivery, and finance/legal automation with regulatory authority or manual failover requirements.
