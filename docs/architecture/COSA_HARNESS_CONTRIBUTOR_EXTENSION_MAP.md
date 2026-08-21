# COSA Harness Contributor Extension Map

**Purpose:** This is the single routing map for adding Harness capability without creating duplicate architecture.

## Core rule

Do not add production runtime behavior to backend/agent_runtime/runtime. That tree is a frozen retirement candidate until a dedicated migration plan moves a production consumer.

Do not add a second workflow UI outside frontend/lib/modules/workflows. The existing module is the sole frontend base for Workflow Library, Builder, Test and Publish, and Run Inspector.

GovernanceKernel is the final production policy decision point for registered operational tool calls. A plugin, workflow node, adapter, connector, executor, or UI client must not bypass it.

## Extension-point map

| Requested capability | Canonical extension point | Required safety boundary | Prohibited duplicate |
|---|---|---|---|
| Model provider | backend/workforce/adapters and workforce agents reliability model gateway | Provider interface, model policy, telemetry | backend/agent_runtime/models provider scaffold |
| Runtime adapter | backend/workforce/agents/runtime/adapters | Runtime manager, session/run scope, cancellation | Business Core import of vendor/DSH runtime |
| COSA business tool | backend/core/tool_registry.py with backend/workforce/tools backend | Tool schema, ExecutionScope, GovernanceKernel, audit | backend/tools registry |
| MCP or external connector | backend/workforce/tools/transports through Extension Registry | Tool Invocation Pipeline, secret broker, policy | direct PluginHost execution or direct HTTP call from UI |
| Skill | backend/workforce skill lifecycle and protected-resource path | Version, human approval, profile eligibility | backend/skills repository |
| Executor | backend/workforce/agents/execution manager/provider | Sandbox, secret broker, policy, artifact/event result | backend/executors stub |
| Workflow graph/compiler | backend/integrations/workflows | Graph validation, immutable version, scope, policy | backend/workflows engine as new product workflow authority |
| Workflow node/UI | backend/integrations/workflows plus frontend/lib/modules/workflows | Node schema, compiler binding, backend authorization | second workflow canvas/module |
| Policy or approval | workforce agents governance GovernanceKernel and ApprovalService | Deterministic allow, deny, approval decision | inline policy in tool, model prompt, plugin, or Flutter UI |
| Event projection | canonical event authority selected in Phase 6; current audit uses governance/event bus | Correlation, redaction, replay constraints | unrelated local event log |
| DSH capability | workforce runtime DeepSeekHarnessAdapter | Version pin, Tool Invocation Pipeline, sandbox mode | DSH internals imported by Business Core |

## Runtime lifecycle

The production runtime owns the following ordering:

~~~text
admitted input
  -> intent/context/profile capability resolution
  -> model/runtime step
  -> governed tool invocation
  -> approval or executor continuation
  -> verified result and event/audit projection
  -> terminal, paused, blocked, or resumable state
~~~

A new capability attaches to an extension point in the table. It must not create a second turn loop, tool registry, workflow engine, or permission implementation.

## Visual workflow contract

The Flutter Workflow Builder edits drafts only. The backend remains authoritative for:

1. graph schema and node definition lookup;
2. typed edge validation;
3. scope, permission, secret, risk, and extension eligibility;
4. immutable published versions;
5. execution, pause/resume, approval, audit, events, and artifacts.

The UI may explain an unavailable node but can never enable it locally.

## Required checks for every extension

1. Interface, provider, consumer, and provider contract test exist.
2. Manifest declares version, trust level, required permissions, secret references, scopes, and health behavior.
3. Model-visible schema excludes credentials, policy callbacks, and backend internals.
4. Tool/provider invocation reaches GovernanceKernel and the canonical dispatch pipeline.
5. External or mutating actions are independently auditable and approval-aware.
6. Disable behavior blocks new work while preserving historical runs/artifacts.

