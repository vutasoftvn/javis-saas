# COSA × DeepSeek Harness — Reference Alignment & Runtime Composition

**Status:** Proposed architecture and migration decision  
**Date:** 2026-08-20  
**Scope:** COSA Agent Runtime, tool execution, skills, workflows, extensions, sessions and runtime adapters  
**Decision owner:** COSA architecture / platform  
**Source references:** [DeepSeek Harness architecture](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md), [tool system](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/tools.md), [tool pipeline](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/tool-execution-pipeline.md), [capability seams](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/capability-seams.md), [skills](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md).

> This document **adjusts and connects** existing COSA plans. It does not replace
> `markdown/Structure.md`, `CLAUDE.md`,
> `docs/architecture/COSA_HARNESS_ENGINEERING_INTEGRATION_PLAN.md`, or
> `docs/agent-platform/*`.

## 1. Executive decision

COSA will **inherit and use DeepSeek Harness** in two deliberately different ways:

1. **Reference architecture.** COSA adopts the useful Harness patterns: composable
   capabilities, a durable session/event log, a single guarded tool pipeline,
   provider seams, scoped capability sets, and replayable UI projections.
2. **Optional runtime implementation.** DeepSeek Harness can run behind a COSA
   adapter for suitable workloads—initially coding, research, and controlled
   agentic sessions—without becoming COSA's business core or policy authority.

The system will not fork Harness, embed Harness internals throughout COSA, or copy
Cordis verbatim into Python. The compatibility boundary is explicit:

```text
COSA Business Core
        │
        ▼
COSA Runtime Kernel contracts
        │
        ├── NativeCosaRuntime
        ├── DeepSeekHarnessAdapter ──> dsh / Cordis plugin tree
        └── future runtime adapters
```

This preserves two important properties at once:

- COSA can benefit directly from the Harness ecosystem and its actively maintained
  tools/providers.
- COSA retains deterministic tenancy, business authorization, approval, audit, and
  data boundaries even when a third-party runtime is swapped or unavailable.

DeepSeek Harness is declared by its maintainers as developer preview and subject to
compatibility-breaking changes. Therefore its public adapter boundary, not its
internal package graph, is the dependency boundary for COSA.

## 2. Why this adjustment is necessary

### 2.1 Existing COSA direction is correct

`CLAUDE.md` already defines COSA as a Founder/Company Operating System with a
composable Agent Harness. It also requires:

- one runtime abstraction, composed from profile, model, context, skills, tools,
  workflows, permissions, and runtime;
- business entities that do not depend on DeepSeek, Claude, OpenAI, or Harness;
- deterministic permissions and approvals rather than prompt-only controls;
- local-first data and traceable execution.

Those decisions match the useful parts of Harness and remain mandatory.

### 2.2 The immediate risk is architectural duplication

The current repository contains both:

- a production-oriented platform under `backend/app/workforce/agents/`, including
  governance, capabilities, execution, runtime management, approval, and event
  publishing; and
- a newer `backend/agent_runtime/` contract-oriented package, containing profiles,
  intent/context resolution, session/event primitives, model providers, permissions,
  sandbox records, and an abstract `BaseAgentRuntime`.

The second package is the correct destination for stable runtime contracts, but it
must not become a copied second implementation. At this audit date,
`BaseAgentRuntime` defines a protocol but not a concrete production turn driver.
Several consumers still use the workforce platform directly. A third, generic
plugin framework at this point would make the situation worse.

### 2.3 The correction in one sentence

**Converge every execution path on one COSA Runtime Kernel and one Tool Invocation
Pipeline before introducing a general plugin lifecycle.**

## 3. Terminology and ownership

The following terms are intentionally non-overlapping. A proposed feature must be
classified before implementation.

| Term | Definition | Owns execution? | Typical COSA form |
|---|---|---:|---|
| Business capability | Deterministic domain behavior and data | Yes, under Business Core | service/repository/domain command |
| Profile | A role-specific composition of allowed capabilities | No | `AgentProfile` |
| Skill | Versioned method/instructions for doing work | No | Markdown + manifest + resolver |
| Tool | Typed, model-callable or operator-callable capability | Yes | `ToolDefinition`/`ToolSpec` |
| Workflow | Repeatable deterministic multi-step process | Coordinates | workflow definition/engine |
| Connector | Provider for an external system | Yes, through a tool/backend | Gmail, CRM, n8n, MCP |
| Executor | Controlled environment that performs work | Yes | OpenSandbox, Codex, Claude Code, n8n |
| Plugin | Deployable package that contributes one or more capabilities | Indirectly | COSA extension package or DSH plugin |
| Runtime | Drives a session/turn/model/tool loop | Coordinates | Native COSA or DSH adapter |

Rules:

1. A new business role does not automatically create a new runtime.
2. A skill is not executable code and cannot bypass tool policy.
3. A tool is not automatically a plugin; most first-party tools are normal COSA
   registrations.
4. A plugin cannot own or weaken COSA's tenant boundary, approval decision, or
   authoritative business write.
5. Codex and Claude Code are executors, not COSA's business agent runtime.

## 4. What COSA inherits from DeepSeek Harness

### 4.1 Capability seams, not framework cloning

Harness describes a capability seam as three roles:

```text
Service Definition (interface)
        ← implemented by — Service Provider
        ← used by — Consumer
```

COSA adopts this pattern as Python protocols/ABCs and dependency wiring. It does
not require a Cordis-compatible runtime in the COSA server. The provider may be a
native implementation, a remote service, or a Harness-backed implementation.

Initial COSA seams:

| COSA seam | Definition | Initial providers | Consumers |
|---|---|---|---|
| `ModelProvider` | structured model request/stream | OpenAI, DeepSeek, Anthropic | runtime turn driver |
| `ToolBackend` | execute a resolved tool invocation | native, connector, automation | tool pipeline |
| `SandboxProvider` | isolated process/filesystem/network execution | OpenSandbox | code/shell tools |
| `ExecutorProvider` | long-running delegated work | Codex, Claude Code, n8n | workflows/jobs |
| `KnowledgeProvider` | scoped retrieval | local files, DB, vector/RAG | context engine |
| `EventStore` | append/read immutable runtime events | SQLite local, PostgreSQL projection | sessions, UI, audit |
| `RuntimeAdapter` | session/turn lifecycle | native COSA, DeepSeek Harness | orchestrator |

Every new seam requires all three parts: interface, at least one provider, and a
consumer. It also requires a provider contract test. A provider-specific import in
Business Core is a failed seam.

### 4.2 Durable events as the model-visible source of truth

Harness's key invariant is: **anything visible to a model must be reconstructable
from the session log**. COSA adopts the invariant with a privacy limitation: logs
record messages, selected context references, tool calls, results, approvals, state
transitions, and artifacts—but never private chain-of-thought.

`backend/agent_runtime/events/` and its SQLite append-only store are the starting
point. The design separates:

```text
Runtime event stream (append-only, replayable)
        │
        ├── Session/history projection for the model
        ├── Hologram/task/approval read models for UI
        ├── PostgreSQL audit and operational projections
        └── telemetry/metrics exporters
```

The event stream does not replace business tables. `Task`, `Project`, `CRM`,
`Approval`, and financial records remain their own authoritative domain models.

### 4.3 One guarded tool pipeline

Harness separates extensible pre/post hooks from final monotonic guards. COSA
inherits this safety property: a downstream extension may make an action more
restrictive, but may never turn a denial into an allow.

Target pipeline:

```text
Tool call request
  → resolve registered definition and server-derived identity
  → validate and canonicalize arguments
  → pre-policy hooks (allow | deny | request approval)
  → monotonic governance / tenancy / budget guards
  → approval resolution, if needed
  → execution wrappers (timeout, retry, tracing, sandbox routing)
  → backend dispatch
  → validate canonical result
  → post-execution redaction/enrichment/verification
  → append immutable result event + audit projection
  → return model/UI-safe result
```

All entrypoints must use it:

- text chat;
- realtime/voice;
- native agent runtime;
- DeepSeek Harness adapter;
- scheduled workflow or n8n callback;
- coding executors;
- internal operator quick actions.

No direct Python invocation is permitted for a registered tool when that invocation
crosses a policy, tenant, or audit boundary.

### 4.4 Scoped composition

Harness lets an agent see a different capability set without changing global
registration. COSA maps this to `AgentProfile` plus a server-derived runtime scope:

```text
RuntimeScope =
  workspace + user/principal + session + profile + intent + stage + grants
```

The capability resolver may only reduce the tool set from the profile's eligible
set. A model suggestion never grants a tool. Greetings and ordinary conversation
receive zero operational tools unless an explicit workflow/session state requires
one.

## 5. Target COSA Runtime Kernel

### 5.1 Logical architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│ COSA Application / UI                                             │
│ Chat · Voice · Tasks · Hologram Hub · Admin                       │
└──────────────────────────────┬──────────────────────────────────┘
                               │ authenticated command/message
┌──────────────────────────────▼──────────────────────────────────┐
│ COSA Runtime Kernel                                               │
│ SessionManager · TurnDriver · ContextEngine · CapabilityResolver │
│ EventStore · ToolInvocationPipeline · ApprovalCoordinator        │
└───────┬──────────────────────┬──────────────────────┬───────────┘
        │                      │                      │
        ▼                      ▼                      ▼
  RuntimeAdapter          Capability seams       Domain facades
  Native / DSH            models/tools/...       Business Core
        │                      │
        ▼                      ▼
 DeepSeek Harness       Sandbox / connectors / executors
 Cordis plugin tree     OpenSandbox / n8n / Codex / Claude Code
```

### 5.2 Runtime interface adjustment

`BaseAgentRuntime` remains the only COSA runtime abstraction. It should evolve to
own turn processing only, not business authorization or direct domain queries.

Required responsibilities:

- start/resume/cancel a session;
- consume a resolved `RuntimeScope` and visible capability set;
- stream typed runtime events;
- request tool execution from `ToolInvocationPipeline`;
- stop at approval/cancellation/limit boundaries;
- expose deterministic recovery metadata.

It must not:

- create a tenant scope from model arguments;
- call a business repository directly;
- decide its own policy outcome;
- bypass the event store;
- retain secrets outside the secret broker.

### 5.3 Canonical turn model

```text
turn/start
  → claim user message or workflow continuation
  → resolve intent, profile, context references, visible tools/skills
  → append admitted input/context-reference events
  → model request / stream
  → zero or more tool calls through ToolInvocationPipeline
  → append assistant result / state transition
  → either next step, WAITING_APPROVAL, PAUSED, BLOCKED, or terminal state
turn/end
```

The Durable Event Types need a stable vocabulary, for example:

```text
turn.started | message.admitted | context.selected | model.requested
model.chunk | model.completed | tool.requested | tool.authorized
tool.approval_requested | tool.started | tool.completed | tool.failed
artifact.created | verification.completed | turn.paused | turn.completed
turn.failed | turn.cancelled
```

Names can evolve, but each event must have: correlation ID, causation ID, session,
workspace/principal scope, timestamp, safe payload, and schema version.

## 6. Tool definition and invocation contract

### 6.1 Evolve `ToolSpec`; do not replace all registrations at once

`backend/app/core/tool_registry.py` already has valuable metadata: chat schema,
risk level, permission level, approval, idempotency, agent allowlist, stage
availability, mutating/external flags, and execution backend. It becomes the
migration base for `ToolDefinition v2`.

New fields should be added compatibly:

| Contract | Requirement |
|---|---|
| Input schema | Explicit JSON schema, validated before execution |
| Output schema | Explicit canonical JSON schema, validated before return |
| Definition ID/version | Stable identity for audit and replay |
| Execution context | Immutable server-derived workspace, principal, session, run, correlation, cancellation signal |
| Side-effect class | `read`, `draft`, `internal_write`, `external_write`, `destructive` |
| Scheduling hints | timeout, retry policy, idempotency, concurrency safety |
| Presentation | Pure call/result rendering metadata; never controls policy |
| Backend binding | native / connector / automation / sandbox / executor |

Only `name`, `description`, and input parameters are projected into a model request.
Policy metadata, callbacks, timeouts, credentials, output internals, and backend
configuration are server-only.

### 6.2 Authority model

The policy decision is centralized and explicit:

```text
ALLOW
ALLOW_IN_SANDBOX
REQUIRE_APPROVAL
DENY
```

`GovernanceKernel` is the orchestration chokepoint. Existing policy engines and
capability gateway logic must be mapped into it rather than duplicated. The class
currently named `OrchestratorPolicyEngine` remains distinct and must retain a name
that cannot be confused with governance policy.

Approval grants are:

- scoped to an exact invocation or explicit bounded grant;
- attributable to a human principal;
- durable/audited;
- invalidated on changed tool/version/arguments where appropriate;
- never inferred from chat text.

### 6.3 Result safety

A tool result is not automatically safe to return to the model or UI. The pipeline
must distinguish:

- canonical result retained for authorized audit/use;
- redacted model-visible projection;
- UI presentation projection;
- artifact reference for large/private output.

This prevents a connector, sandbox, or plugin from leaking secrets by simply
returning them in a nominally successful tool result.

## 7. Skills, workflows, and context

### 7.1 Skills

Use the existing Markdown skill direction (`backend/skills/`) and protected-resource
versioning. A skill manifest should include:

```yaml
id: market-research
version: 1
purpose: Research a market with cited evidence
allowed_profiles: [cofounder, marketing, research]
required_tools: [web.search, knowledge.retrieve]
risk: read_only
context_budget: 4000
```

The body remains human-reviewable instructions. The resolver selects it based on
profile and intent, then adds a version/reference event before it becomes
model-visible. The skill cannot register executable code or self-grant tools.

### 7.2 Workflows

Workflows model deterministic business process and must be independently resumable.
They may call a runtime for reasoning steps, but their transitions and approvals are
not hidden in prompts.

```text
Workflow definition
  → create WorkItem/ExecutionJob
  → start/continue a runtime step
  → tool and approval events
  → verify result
  → update business state through domain command
```

The workflow engine, task lifecycle, and mission/outcome records remain COSA-owned.
Harness may be an executor within one runtime step, never the authority for the
business workflow.

### 7.3 Context and memory

The Context Engine returns references and bounded content from explicit scopes:

```text
conversation | session | user | company | project | domain | working memory
```

Each source must carry freshness, authority, sensitivity, and token/cost budget.
Lazy loading by intent is retained. Context selection is logged; raw private source
contents need not be duplicated in the event log when an immutable reference and
authorized retrieval path suffice.

## 8. DeepSeek Harness compatibility and adapter design

### 8.1 What the adapter may delegate

For a compatible DSH profile, COSA can delegate:

- model conversation/streaming;
- Harness-native coding tools such as shell, terminal, filesystem and subagents;
- session continuation/forking where COSA owns the external session mapping;
- optional Harness UI/session projections for an isolated developer experience.

### 8.2 What COSA retains

The adapter must retain control of:

- authenticated principal and workspace scope;
- tenant isolation and business data access;
- tool eligibility, policy, approval, budget, and audit;
- secret resolution;
- business workflow/work-item transitions;
- canonical COSA event emission and artifact ownership.

### 8.3 Two integration modes

| Mode | Use case | Tool authority |
|---|---|---|
| **COSA-governed DSH** | business/research/coding task initiated in COSA | COSA registers/bridges approved tools; all business operations route through COSA pipeline |
| **Isolated DSH workspace** | developer-facing coding environment | Harness controls its native local tools inside a sandboxed workspace; COSA sees only governed executor/job/artifact boundaries |

Do not mix the modes silently. A DSH plugin with shell or filesystem access cannot
receive direct production business credentials merely because a COSA session initiated
it.

### 8.4 DSH plugin inheritance policy

Harness plugins are acceptable dependency units for the adapter layer. Examples:

- model adapters;
- web/search adapters;
- sandboxed shell/terminal tools;
- subagent implementations;
- session persistence adapters;
- code-oriented workflows.

Before enabling a DSH plugin in a COSA-managed workload, review:

1. permissions and filesystem/network behavior;
2. whether it invokes external side effects;
3. secret source and redaction behavior;
4. event/audit correlation bridge;
5. cancellation, timeout, and cleanup guarantees;
6. version pinning and compatibility test coverage.

No DSH dynamic plugin authored by an LLM or tenant user is enabled in COSA production
in the initial architecture. That capability may be reconsidered only after extension
signing, sandbox isolation, review/approval, quotas, and reversible lifecycle controls
are implemented.

## 9. COSA extension-package model

### 9.1 Start narrow

An initial COSA extension is a reviewed, deploy-time package. It may contribute a
provider, tool definitions, skill files, workflow definitions, UI projection, or
configuration schema. It cannot override Runtime Kernel invariants.

Suggested manifest:

```yaml
id: cosa.connector.hubspot
version: 1.0.0
kind: connector
trust_level: first_party
provides:
  - tool_backend: hubspot
  - tools: [crm.search_contacts, crm.create_draft]
requires:
  permissions: [crm.read, crm.write]
  secrets: [hubspot.oauth]
  sandbox: none
compatibility:
  cosa_runtime: ">=1"
```

### 9.2 Lifecycle

```text
discover → validate → install → configure → enable
       → invoke through governance → observe/audit
       → disable → uninstall
```

Enablement is workspace-scoped only where the extension is tenant-safe. A plugin
version change must be visible in tool and runtime events. Disabling a plugin blocks
new work but preserves audit and artifacts for old runs.

### 9.3 Explicit non-goals

This phase does not add:

- an arbitrary third-party plugin marketplace;
- runtime Python code upload from users or models;
- per-tenant arbitrary server-side process execution;
- a universal DSL meant to replace normal first-party code;
- plugin-owned database migrations without platform review.

## 10. Migration plan

### Phase 0 — Freeze boundaries and inventory

**Goal:** stop duplication before adding behavior.

- Declare `backend/agent_runtime/` the home for new runtime contracts.
- Declare `backend/app/workforce/agents/` the current implementation location until
  each capability is migrated through a tested adapter/facade.
- Inventory every production tool entrypoint and classify direct calls.
- Publish the canonical ownership map for policy, approval, event, session, and
  model-routing components.
- Do not add a generic plugin registry in this phase.

**Exit criteria:** one documented owner for each contract; no new runtime feature is
implemented twice in workforce and agent_runtime.

### Phase 1 — Tool Invocation Pipeline

**Goal:** a single safe execution chokepoint.

- Introduce `ToolInvocation`, immutable `ToolExecutionContext`, and normalized
  `ToolResult` contracts beside compatible `ToolSpec` support.
- Route chat and agent-runtime paths through the same pipeline.
- Make GovernanceKernel's decision enforced—not merely audit-logged—at each callsite.
- Add input/output validation, cancellation propagation, correlation IDs, and
  structured error codes.
- Record a durable event for every authorization and result transition.

**Exit criteria:** test proves `DENY` executes no body, `REQUIRE_APPROVAL` pauses and
resumes only after a valid grant, and no production entrypoint bypasses the pipeline.

### Phase 2 — Native Runtime Kernel turn driver

**Goal:** turn `BaseAgentRuntime` from an interface into a production path.

- Implement a native driver using SessionManager, ContextEngine, CapabilityResolver,
  ModelGateway, EventStore, and Tool Invocation Pipeline.
- Migrate one low-risk read-only profile end-to-end.
- Emit the canonical turn and tool events and render an existing UI projection.
- Add resume/cancel/retry semantics before multi-agent capabilities.

**Exit criteria:** a real COSA session can replay its model-visible history and tool
results after restart without accessing provider-specific state.

### Phase 3 — DeepSeek Harness Adapter compatibility

**Goal:** use Harness as a real selectable runtime, safely.

- Define a version-pinned adapter capability contract.
- Map COSA session/run/correlation IDs to Harness sessions.
- Bridge COSA-approved tool calls to the COSA pipeline; do not expose privileged
  business tools directly to DSH plugins.
- Support an isolated DSH coding workspace through OpenSandbox/executor boundaries.
- Create compatibility tests against a pinned DSH release and fixture session logs.

**Exit criteria:** a COSA-governed DSH run can use approved read-only COSA tools,
receive a deterministic denial/approval outcome, and produce COSA audit events.

### Phase 4 — Profiles, skills, and workflow composition

**Goal:** make role composition the only way to vary behavior.

- Finalize profile manifests/presets and validate referenced tools/skills/workflows
  during boot/CI.
- Version skills through protected resources and log activated versions.
- Bind deterministic workflow transitions to WorkItems/ExecutionJobs.
- Add stage-aware and workspace-aware tool eligibility as a monotonic filter.

**Exit criteria:** a new role can be added by profile/skill/workflow composition
without a new runtime loop or copied prompt/tool code.

### Phase 5 — Extension packages and projections

**Goal:** safely add first-party extension lifecycle and operational UI.

- Add reviewed extension manifests, enablement, health checks, and version audit.
- Add Agent/Task/Approval projections from canonical runtime events to Hologram Hub.
- Offer only first-party or explicitly reviewed connector packages.

**Exit criteria:** enable/disable of a connector changes eligible capability sets
without changing Business Core or losing historical traceability.

### Deferred — Dynamic plugins and agent teams

Reconsider only after the preceding phases demonstrate demand and the following are
available: signed packages, sandbox isolation, resource quotas, approval UX, source
review, rollback, tenant-safe secrets, and production observability.

## 11. Test and verification strategy

| Layer | Required verification |
|---|---|
| Contract | Provider contract tests for every seam |
| Tool schema | valid/invalid input and output, server-only metadata not model-visible |
| Governance | deny/allow/approval/sandbox decisions and no-body-on-deny proof |
| Tenancy | model-supplied identifiers cannot escape server-derived scope |
| Runtime | replay, cancellation, resume, bounded tool rounds, error recovery |
| Adapter | pinned DSH compatibility fixtures and no privileged-tool bypass |
| Extension | manifest validation, lifecycle reversal, disabled-plugin refusal |
| UI | event projection of pending approval, blocked, paused, complete, failed states |

Architectural invariant tests should be retained and expanded rather than relying on
review convention alone.

## 12. Decisions required before implementation

1. Confirm the canonical runtime event schema and the durable store authority:
   SQLite local-first with PostgreSQL projection, or PostgreSQL primary plus local
   session cache. This is a deployment/data-retention decision.
2. Confirm whether DSH integration begins with **COSA-governed DSH** or an
   **isolated coding workspace**. The first gives business-tool value; the latter is
   lower integration risk.
3. Confirm a single governance ownership model before Phase 1 changes call sites.
   The target is GovernanceKernel as the execution decision chokepoint.
4. Confirm which existing `backend/agent_runtime/` changes are authoritative and
   which are scaffolding before further migration.

## 13. Acceptance criteria for the architecture

The adjustment is successful when all are true:

- COSA can run a session through NativeCosaRuntime or DeepSeekHarnessAdapter without
  a Business Core import of provider/Harness internals.
- Every tool invocation has an immutable server-derived scope and passes one
  authorization/approval/audit pipeline.
- Model-visible context and tool results are reconstructable from durable COSA events.
- Profiles compose skills, tools, workflows, context, and permissions; no duplicate
  per-role agent loops are introduced.
- DSH tools/plugins are usable through a version-pinned, capability-reviewed adapter.
- A DSH plugin cannot directly obtain COSA business credentials or bypass COSA policy.
- Extension lifecycle is reviewed, reversible, observable, and tenant-safe.

## 14. Relationship to existing documents

| Existing document | Relationship |
|---|---|
| `CLAUDE.md` | Normative architecture constraints; this document operationalizes them |
| `markdown/Structure.md` | Target harness architecture; this document adds the DSH compatibility boundary and migration rules |
| `COSA_HARNESS_ENGINEERING_INTEGRATION_PLAN.md` | Preserve its anti-duplication and governance-gap findings; Phase 1 here supplies the unified pipeline direction |
| `COSA_AGENT_RUNTIME_TOOL_CALLING_GAP_PLAN.md` | Its tool-calling concern becomes a Phase 1/3 implementation slice, but direct SDK assumptions must be revalidated against current DSH APIs |
| `docs/agent-platform/CURRENT_ARCHITECTURE.md` | Current-state evidence; update after each completed migration phase |
| `docs/agent-platform/GAP_ANALYSIS.md` | Tracks concrete bypasses/fragmentation that Phase 0–1 must close |

## Appendix A — Mapping Harness concepts to COSA

| Harness concept | COSA equivalent | Adoption decision |
|---|---|---|
| Cordis plugin context | Python contracts + dependency wiring | adopt principle, not framework |
| `ctx.llm` | ModelProvider / ModelGateway | converge existing providers |
| `ctx.tools` | Tool Registry + Tool Invocation Pipeline | strengthen and centralize |
| `tools/pre-execute` | pre-policy hooks | adopt |
| monotonic `ToolGuard` | GovernanceKernel final guards | adopt |
| `tools/execute` wrappers | timeout/retry/tracing/sandbox routing | adopt |
| `tools/post-execute` | redaction/verification/result enrichment | adopt |
| session event log | AgentEvent + session/trajectory store | converge and formalize |
| agent-scoped registrations | RuntimeScope + profile capability resolver | adopt |
| plugin bundle/profile | COSA extension package/profile manifests | later, narrowed scope |
| dynamic plugins | user/model-generated runtime code | defer |
| subagent provider seam | ExecutorProvider / RuntimeAdapter | later, controlled |

## Appendix B — Implementation guardrails

- Never couple a domain model or business service to a DeepSeek Harness type.
- Never trust a model-provided workspace, user, run, or approval identifier.
- Never let a Skill grant a tool or permission.
- Never expose provider secret/configuration in model-visible schemas or events.
- Never mark a governance check complete unless its decision is enforced.
- Never migrate by copying a runtime path; introduce a facade/adapter, migrate a
  consumer, test it, then retire the old path deliberately.
- Never enable a DSH plugin in a COSA business session without explicit capability,
  sandbox, secret, and audit review.
