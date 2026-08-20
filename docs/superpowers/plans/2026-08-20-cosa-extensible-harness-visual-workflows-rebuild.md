# COSA Extensible Harness and Visual Workflow Builder — Rebuild Master Plan

> For agentic workers: execute phase by phase; each phase must pass its acceptance criteria before the next phase starts.

**Status:** Proposed rebuild plan
**Date:** 2026-08-20
**Goal:** Rebuild COSA as a multi-product, multi-service Founder/Company OS with a governed extensible Harness and a visual workflow builder.

**Architecture:** Business Core owns company data and deterministic business rules. Harness owns AI session/turn execution, extension discovery, capability composition, policy, approval, and events. Flutter authors workflow graphs, while the backend validates, versions, compiles, and executes immutable published graphs. DeepSeek Harness is a version-pinned adapter/provider, never the business core.

**Source architecture:** docs/architecture/COSA_DEEPSEEK_HARNESS_REFERENCE_ALIGNMENT_AND_RUNTIME_COMPOSITION.md and markdown/plan1.md.

## Non-negotiable decisions

- COSA is a Founder/Company OS, not a generic agent platform.
- One Company can have multiple Operating Units, Offerings (product, service, hybrid), Initiatives, and WorkItems.
- Business Core never imports DeepSeek Harness or a model-provider implementation.
- A plugin can add capability but cannot create a privileged execution path.
- Every action goes through one server-derived scope, policy, approval, audit, and event path.
- Workflow graphs are visual in the UI but deterministic, validated, versioned, and server-executed.
- The existing integrations/workflows graph/version/run records are the migration base; no second workflow database model is created.
- Do not extend backend/agent_runtime as a parallel production runtime until canonical ownership is decided. Preserve persistence models already imported from app/db/base.py.
- DeepSeek Harness stays optional and version-pinned; arbitrary DSH dynamic plugins never receive COSA business credentials.
- The previous Tool Invocation Pipeline plan is not an implementation starting point. Its useful pipeline design is applied only after Phase 0 determines the canonical production path.

---

## Product domain and execution scope

~~~
Company
  shared functions: finance, legal, knowledge, governance, people
  OperatingUnit (brand, business line, subsidiary)
    Offering (product, service, hybrid)
      Initiative (project, campaign, client delivery)
        WorkItem (task, approval, execution job)
  Founder Control Plane: portfolio health, capital allocation, risk, priorities
~~~

All execution uses a server-derived scope:

~~~
ExecutionScope =
  workspace_id + company_id
  + operating_unit_id?
  + offering_id?
  + initiative_id?
  + principal + profile + session + grants
~~~

A client request, model output, graph, or extension manifest cannot widen this scope.

## Target Harness structure

~~~
COSA Harness
  runtime       session, turn, cancellation, continuation
  context       bounded, attributable context assembly
  profiles      role/capability visibility
  skills        versioned instructions and method packs
  tools         schema registry and one invocation pipeline
  policy        deterministic authorization and approval
  workflows     graph compiler, runner, schedule/event triggers
  events        append-only facts and UI projections
  extensions    manifests, lifecycle, provider contracts
  seams         model, connector, executor, sandbox, knowledge, event store
  adapters      native, DSH, MCP, n8n, Codex, Claude Code
~~~

## Target visual workflow product

~~~
Workflow Library
  -> Draft Builder
  -> Validate and risk preview
  -> Test run
  -> Publish immutable version
  -> Run Inspector and Hologram projection
~~~

The node palette receives metadata from the Extension Registry after scope, profile, permission, extension enablement, and secret readiness have been evaluated.

| Node family | Examples | Execution owner |
|---|---|---|
| Trigger | manual, schedule, webhook, business event | workflow runtime |
| Reasoning | profile, skills, bounded context | runtime adapter |
| Tool | CRM query, finance read, create draft | tool invocation pipeline |
| Decision | deterministic predicate, branch | graph compiler |
| Approval | founder or role approval | approval service |
| Wait | timer, event, dependency | workflow runtime |
| Executor | n8n, OpenSandbox, Codex, Claude Code | executor provider |
| Subworkflow | published workflow version | workflow runtime |
| Outcome | WorkItem or artifact mutation | Business Core command |

Every node type declares input/output JSON schema, risk, required permissions/secrets, supported scopes, optional UI renderer, and a backend compiler/executor binding.

---

# Phase 0 — Canonical ownership and safe rebuild boundary

**Goal:** Stop parallel architecture before adding capability.

## Backend tasks

1. Produce a checked-in ownership inventory for every runtime, model provider, tool registry, skill registry, workflow engine, executor, event store, and adapter.
2. Classify every component: canonical production, canonical persistence model, migration facade, test-only scaffold, or retirement candidate.
3. Preserve migrated persistence models in agent_runtime sessions, events, permissions, sandbox, and memory model modules because app/db/base.py imports them.
4. Freeze new code in duplicate scaffolds: agent_runtime runtime/models/context/routing, root tools, root skills, and root executors, until the audit decides their status.
5. Identify the canonical production implementation under app/workforce for each capability. Create a narrow facade only when a consumer cannot move immediately.
6. Add architecture invariant tests: Business Core cannot import provider/Harness implementation; no new second registry for an existing capability.

## Frontend tasks

1. Inventory workflows, skills, approvals, agents, task, and Hologram modules.
2. Declare frontend/lib/modules/workflows as the sole workflow UI ownership point.
3. Record all routes/services that the current workflow UI calls.

## Acceptance criteria

- One ownership map names one canonical production implementation per capability.
- Import scan has no unexplained production consumers of retirement candidates.
- Baseline tests run before files move; no mass delete based only on similar names.
- Subsequent implementation plans target only canonical paths.

# Phase 1 — Company portfolio scope

**Goal:** Make Company, Operating Unit, Offering, and Initiative the shared scope vocabulary.

## Backend tasks

1. Audit Company, Project, Task, CRM, and finance models against the target hierarchy.
2. Add only missing entities/foreign keys with backwards-compatible migrations.
3. Create ExecutionScope in the canonical Harness area: workspace/company; optional unit/offering/initiative; principal; profile; session; grants.
4. Add server-side hierarchy resolvers that validate parent-child relationships.
5. Add auditable scope snapshots/references to workflow definition, version, run, approval, and artifact records.
6. Add authorized portfolio-filter APIs.

## Frontend tasks

1. Add an application-shell scope switcher for Company, Unit, Offering, Initiative.
2. Add scope breadcrumb/chips to workflows, tasks, Hologram, and run inspection.
3. Founder views show permitted aggregate data; lower roles receive backend-filtered scope only.

## Acceptance criteria

- A run in Offering A cannot access Offering B after request-field tampering.
- Every workflow run stores the scope snapshot present at start.
- UI scope selection never grants access without server authorization.

# Phase 2 — Governed capability seams and extension registry

**Goal:** Add plugins/tools/skills/connectors/executors without changing Harness Core.

## Backend tasks

1. Define each seam as interface, provider, consumer, and shared contract test:
   ModelProvider, ToolBackend, ConnectorProvider, ExecutorProvider, SandboxProvider, KnowledgeProvider, EventStore, RuntimeAdapter.
2. Define ExtensionManifest and ExtensionRegistration:
   ID, version, compatibility range, trust level, owner, provided capability IDs, permissions, secret references, supported scopes, health check, disable behavior.
3. Build an Extension Registry that validates and enables/disables metadata; it must never call extension code directly.
4. Replace PluginHost stub with a facade to this registry.
5. Implement MCP as ConnectorProvider: initialize, tools/list, schema conversion, governed registration, and tools/call routed through the common tool pipeline.
6. Support reviewed first-party extension packages only. Do not allow user/model-supplied server code.

## Frontend tasks

1. Add Settings Extension pages: installed versions, health, disabled reason, permission request, secret readiness, provided tools/skills/nodes.
2. Make enable/disable server-authorized actions.
3. Feed eligible extension node metadata into the workflow palette.

## Acceptance criteria

- A mocked MCP server is discovered with initialize and tools/list.
- Its tools disappear when extension disabled or secret unavailable.
- Its call uses the same deny/approval/audit gateway as native tools.
- Disabling blocks new calls and preserves historical run/artifact records.

# Phase 3 — Unified Tool Invocation Pipeline

**Goal:** One authority for every operational action.

## Backend tasks

1. Evolve canonical ToolDefinition: stable ID/version, input/output schema, side-effect class, timeout/retry/idempotency/concurrency hints, required scope/permission/secret/backend.
2. Implement exactly one pipeline in the canonical workforce runtime/tool path:
   resolve -> validate input -> pre-policy -> monotonic guards -> approval -> execution wrappers -> backend dispatch -> output validation -> redaction/verification -> event/audit projection.
3. GovernanceKernel remains final policy authority. Retire duplicate policy names only after parity tests.
4. Ignore model-supplied identifiers and approval fields; use ExecutionScope.
5. Migrate chat, voice, workflow runner, MCP, n8n callbacks, coding executors, and DSH adapter one at a time.
6. Add cancellation, correlation/causation IDs, JSON-safe canonical output, and structured errors.

## Frontend tasks

1. Shared cards render risk, approval, execution status, safe output preview, and artifact links.
2. Reuse them in Workflow Builder test view, Run Inspector, Hologram Hub, and approval screens.
3. Never render secret-bearing raw input/output.

## Acceptance criteria

- DENY and REQUIRE_APPROVAL execute no body code.
- Every migrated entrypoint produces correlation ID, audit projection, and runtime event.
- Invalid/non-JSON-safe output cannot reach model or UI.
- Tool/node schema is filtered by scope before it becomes model- or UI-visible.

# Phase 4 — Visual graph compiler and deterministic workflow runtime

**Goal:** Turn existing WorkflowDefinition, WorkflowVersion.graph_jsonb, WorkflowRun, WorkflowStep, and WorkflowApproval into a validated visual workflow platform.

## Backend tasks

1. Preserve existing workflow models/routes as the migration base.
2. Version the graph wire format: nodes with type/version/config; typed ports; edges; entry nodes; scope requirements; pinned capability dependencies.
3. Build WorkflowNodeDefinition registry from core and Extension Registry.
4. Compile/validate:
   - exactly one valid entry;
   - all terminal paths reachable;
   - no unbounded cycle;
   - compatible edge schemas;
   - enabled/eligible pinned tool/skill/extension versions;
   - satisfiable secret/permission/risk requirements;
   - approval policy before high/external side effect;
   - acyclic, version-pinned subworkflow references.
5. Add draft, validated, published, archived version states. Published graph JSON and dependency versions are immutable.
6. Replace the current single start-step initialization with graph traversal that persists node attempts, pauses at approval/wait, resumes idempotently, emits events, and stores artifact references.
7. Keep n8n as ExecutorProvider; it cannot become the workflow authority.

## Frontend tasks

1. Workflow Library: scope-aware list, owner, state, version, last run, extension health.
2. Workflow Builder:
   - drag/drop palette grouped by node family and extension;
   - pan/zoom and typed port connections;
   - node inspector;
   - scope selector;
   - node/edge validation errors;
   - autosaved drafts with revision-conflict handling.
3. Test and Publish: validation report, permission/secret/risk summary, dry-run inputs, version note, publish confirmation.
4. Run Inspector: graph with live node status, timeline, approval, retry, artifacts, failure details, and server-authorized pause/cancel/retry.

## Acceptance criteria

- A user creates a low-risk read-only graph by drag/drop, validates, publishes, runs, and inspects it.
- Backend rejects an invalid edge or missing extension/secret; UI pinpoints the node/edge.
- High-risk/external tool cannot execute without policy/approval.
- A published run reproduces graph, scope, and dependency versions at start.

# Phase 5 — Profiles, skills, and visual composition

**Goal:** Roles are composed, not independently coded agents.

## Backend tasks

1. Re-home only the valuable AgentProfile definitions after Phase-0 ownership decision.
2. Profile manifest controls visible tools, eligible skills, workflow permissions, model policy, scope ceiling, approval baseline.
3. Add session-scoped overrides that only reduce capability visibility or add context references.
4. Version Skill manifests/bodies through protected resources and record activated version/source references.
5. Provide profile composition endpoint for UI preview/compiler validation.

## Frontend tasks

1. Profile composition screen: read-only for ordinary users; authorized versioned editing for administrators.
2. Reasoning node config: profile, eligible skills, bounded context, visible tool summary.
3. Explain unavailable capabilities: scope, profile, permission, disabled extension, missing secret, or flag.

## Acceptance criteria

- New role = profile composition, never a copied turn loop.
- API and UI reject tools/skills outside profile eligibility.
- Session override cannot bypass GovernanceKernel.

# Phase 6 — Runtime events, Hologram projections, and local-first sessions

**Goal:** Replayable operational visibility without competing event systems.

## Backend tasks

1. Define canonical event vocabulary, schema version, correlation/causation/scope fields.
2. Treat existing Postgres audit and OpenTelemetry as projections/telemetry rather than new competing session authorities.
3. Decide deployment mode: SQLite append-only session log with Postgres audit projection, or Postgres primary log with SQLite offline/cache projection.
4. Implement the selected model end-to-end for one workflow path before broad migration.
5. Project events into Task, Approval, Workflow Run, Agent/Executor health, and Artifact read models.

## Frontend tasks

1. Hologram and Run Inspector read projections, not inferred raw logs.
2. Add Agent/Task cards with scope, current node, progress, risk, approval, verification, artifacts.
3. Reconnect by event cursor and never display private reasoning.

## Acceptance criteria

- Paused run resumes exact workflow version and scope.
- Reconnect displays deterministic event-derived state.
- Audit, trace, and session correlate without duplicating secrets.

# Phase 7 — DeepSeek Harness and executor integration

**Goal:** Reuse Harness, Codex, Claude Code, and n8n after COSA governance is stable.

## Backend tasks

1. Version-pin DeepSeek Harness and document supported capabilities.
2. Implement DeepSeekHarnessAdapter against canonical RuntimeAdapter and Tool Pipeline contracts.
3. Support two explicit modes:
   - COSA-governed DSH: only approved COSA tools are bridged through pipeline;
   - isolated DSH coding workspace: native DSH tools stay inside OpenSandbox/executor boundary.
4. Add session mapping, cancellation, timeout, artifact ingestion, compatibility fixtures.
5. Treat Codex, Claude Code, and n8n as ExecutorProviders using same scope, policy, approval, event, artifact contracts.
6. Keep arbitrary dynamic DSH plugin execution disabled.

## Frontend tasks

1. Show selected runtime/executor per node/run.
2. Show isolation and permission summary before coding execution.
3. Render executor outputs as governed artifacts, not unrestricted transcripts.

## Acceptance criteria

- Same registered tool gets equivalent COSA deny/approval/audit behavior via Native and DSH runtime.
- Coding executor cannot access production credential outside sandbox/secret broker.
- DSH updates are covered by pinned compatibility fixtures.

# Phase 8 — Migration, retirement, and operating model

**Goal:** Remove old paths only after users, data, and tests have moved.

1. Migrate one offering and one low-risk workflow first.
2. Dual-read only for data projection migration; never dual-execute external actions.
3. Mark replaced APIs/modules deprecated with owner/removal date.
4. Delete candidates only after import scan, production metrics, and regression suite prove zero consumers.
5. Publish a contributor cookbook: add tool, skill, node, MCP/connector, executor, DSH adapter capability, UI renderer.
6. Create an ADR for every seam/node family.

## Acceptance criteria

- One documented/test-enforced path remains per core capability.
- No production consumer remains on a retired registry/scaffold.
- First-party extension adds tool, skill, workflow node, and UI renderer without Harness Core edit.
- Workflow author composes it visually within scope/governance constraints.

---

## Milestones

| Milestone | Phases | Demonstrable outcome |
|---|---|---|
| M0 Foundation | 0–1 | Canonical ownership and multi-offering scope |
| M1 Extensible governance | 2–3 | MCP/extension tool through one policy gateway |
| M2 Visual automation | 4 | Drag/drop workflow build, validate, publish, run, inspect |
| M3 Composed workforce | 5–6 | Profiles/skills and event-derived operational UI |
| M4 Harness ecosystem | 7–8 | DSH/Codex/n8n safely integrated; duplicates retired |

## Test strategy

- Unit: graph validation, port schema compatibility, profile resolver, manifest validation, policy outcomes.
- Contract: all seam providers against shared contract tests.
- Integration: MCP discovery/call, workflow publish/run/resume, approval pause/resume, executor artifact ingestion.
- Security: scope tampering, disabled extension, missing secret, denial/approval non-execution, output redaction.
- Flutter: workflow library, graph-edit, validation, scope switcher, run inspector controllers/services.
- End-to-end: multi-offering company builds a governed workflow with extension tool and approval, then sees lifecycle in Hologram Hub.

## Risks and controls

| Risk | Control |
|---|---|
| Rewrite grows indefinitely | Phase gates; enhance existing workflow records/UI rather than create duplicates |
| Duplicate core remains | Phase-0 ownership map plus import/invariant tests |
| UI bypasses policy | Graph compiler/runtime are authoritative; UI only authors graph |
| Plugin becomes arbitrary code execution | Reviewed manifests only; dynamic plugins deferred |
| DSH developer-preview churn | Pin version, adapter seam, fixtures, no provider imports in Business Core |
| Event stores diverge | Select authority in Phase 6; audit/OTel projections |
| Multi-offering data leak | Server-derived ExecutionScope and hierarchy validation |

## Explicitly deferred

- User/model-authored runtime plugins.
- Arbitrary JavaScript/Python workflow node code.
- Model-authored dynamic workflow scripts as default mode.
- Plugin marketplace.
- General subagent team framework beyond governed executors.

## First execution slice

Begin with Phase 0 only. Its output is an ownership map and invariant tests, not a new tool pipeline, adapter, or UI canvas. That prevents investment in paths that the rebuild will retire.
