# COSA Canonical Ownership Map

**Status:** Phase 0 baseline  
**Date:** 2026-08-20  
**Authority:** This map is the required ownership reference before adding Harness, extension, workflow, or runtime code.

## Classification vocabulary

- **Canonical production:** current application implementation for new production behavior.
- **Canonical persistence model:** SQLAlchemy metadata owner; not automatically the runtime implementation owner.
- **Migration facade:** compatibility import/re-export retained while consumers move.
- **Frozen retirement candidate:** no new production behavior; retain until consumer report, migration plan, tests, and removal review are complete.
- **Audit required:** evidence is insufficient to designate retirement.

## Ownership map

| Capability family | Canonical owner | Classification | Evidence | Allowed new code | Migration or retirement condition |
|---|---|---|---|---|---|
| Business domain models | backend/core | Canonical production | Recent core migration; compatibility imports still exist in app business/founder modules | Business entities and deterministic domain rules | Retire compatibility exports only after import scan and database metadata parity |
| Agent runtime implementation | backend/app/workforce/agents/runtime | Canonical production | Router, runtime manager, Chief of Staff, and DSH adapter import this path | Turn runtime, runtime request types, adapter contract | No parallel driver under agent_runtime |
| Runtime governance | backend/app/workforce/agents/governance | Canonical production | GovernanceKernel is used by runtime/execution paths and invariant tests | Policy, approval, audit decision behavior | Consolidate same-name policy helpers only with behavior-parity tests |
| Runtime capability gateway | backend/app/workforce/agents/capabilities | Canonical production | Execution service and capability routes import it | Capability grants, provider binding, connector authorization | Any merge with GovernanceKernel requires dedicated ADR and test plan |
| Model reliability gateway | backend/app/workforce/agents/reliability | Canonical production | Workforce AI policy imports ModelGateway and ModelProfileRegistry | Retry, circuit breaking, profile/model selection | Retire parallel agent_runtime model gateway after consumers migrate |
| DeepSeek Harness adapter | backend/app/workforce/agents/runtime/adapters/deepseek_harness.py | Canonical production adapter | Runtime manager registers deepseek_harness; orchestration resolves it | Version-pinned adapter compatibility only | Keep thin; do not import DSH internals into Business Core |
| Core tool registry | backend/app/core/tool_registry.py and tool_dispatch.py | Canonical production | GovernanceKernel resolves ToolSpec; chat/runtime dispatch uses it | Registered COSA business tool schemas and safe parameter injection | Do not create root tools registry consumers |
| Workforce tools/transports | backend/app/workforce/tools | Canonical production | Auto-registration, gateway, and MCP transport live here | Tool backends, connector transports, future extension adapters | Extension registry will own discovery metadata, not direct dispatch bypass |
| Workflow persistence/API | backend/app/integrations/workflows | Canonical production | db/base imports WorkflowDefinition/Version/Run/Step/Approval; router exposes graph_jsonb and runs | Graph compiler, version lifecycle, workflow execution API | Preserve tables/routes; evolve in place |
| Workflow frontend | frontend/lib/modules/workflows | Canonical production | Dashboard imports WorkflowsView; service calls workflows definitions/runs API | Workflow Library, Builder, Test/Publish, Run Inspector | Do not create a second workflow canvas module |
| Runtime persistence models | backend/agent_runtime/sessions/models.py; backend/agent_runtime/events/models.py; backend/agent_runtime/permissions/models.py; backend/agent_runtime/sandbox/models.py; backend/agent_runtime/memory/models.py | Canonical persistence model | backend/app/db/base.py imports all five modules; workforce compatibility models re-export them | SQLAlchemy table metadata and carefully reviewed persistence evolution | Any move requires Alembic/metadata parity test and explicit migration |
| agent_runtime runtime/models/context/routing/trajectory | backend/agent_runtime/runtime; backend/agent_runtime/models; backend/agent_runtime/context; backend/agent_runtime/routing; backend/agent_runtime/trajectory | Frozen retirement candidate | Imports are primarily phase unit/e2e tests; workforce contains production runtime equivalents | No new production behavior | Consumer report and targeted migration/retirement plan required |
| Root tools scaffold | backend/tools | Frozen retirement candidate | Root dispatcher/registry consume it; phase tests import it; production governance uses app core registry instead | No new product tool registrations | Migrate all consumers or explicitly adapt before removal |
| Root skills scaffold | backend/skills | Frozen retirement candidate | Root workflow engine and phase tests import it; workforce has skill lifecycle services | No new product skill lifecycle | Audit consumers and map to workforce protected-resource path |
| Root workflows scaffold | backend/workflows | Frozen retirement candidate | Root definitions/engine consume root tools/skills; integrations workflows owns production graph records/API | No new customer workflows | Graph compiler decision determines adapter or retirement |
| Root executors scaffold | backend/executors | Frozen retirement candidate | Plan1 identifies Claude Code executor as simulated; production execution manager has providers | No new executor integrations | Confirm no production callers and use workforce ExecutorProvider |
| Plugin host | backend/app/integrations/channels/plugins/plugin_host.py | Audit required / stub | load_plugins returns empty; execute_plugin returns placeholder result | No direct plugin execution | Replace with Extension Registry facade in Phase 2 |
| Tool Invocation Entrypoints | Chat tools, ToolBridge, Workflow Runner, MCP Bridge, DSH adapter | Canonical production | Execution entrypoints currently directly calling ToolSpec or providers | Direct execution without unified pipeline | Migrate to unified ToolInvocationService in Phase 3 |
| Postgres agent audit | workforce governance models and agent event bus | Canonical production projection | AgentToolCall and AgentEventRecord are production imports | Audit/compliance projection | Event authority decision deferred to Phase 6 |
| OpenTelemetry | backend/app/core/telemetry.py | Canonical telemetry projection | GovernanceKernel calls trace_span | Cross-service telemetry | Does not become session history authority |
| SQLite session/event scaffold | backend/storage/sqlite and backend/agent_runtime/events/sessions | Frozen retirement candidate / audit required | Phase tests use SQLiteEventStore; production session authority not selected | Test support only until Phase 6 decision | Select local-first authority before production promotion |
| Company portfolio scope | Workspace is the Company/tenant in Phase 1. OperatingUnit and Offering are Business Core entities. Initiative remains the existing operational record and Task remains the WorkItem engine. Project is a linked strategy record, not a replacement hierarchy level. | Canonical production/persistence anchors | Existing Workspace, Initiative, Task, and Project models | Extend the existing anchors in place; do not create a parallel Company table or split the Task engine | Any hierarchy change requires an explicit ownership and migration decision |

## Rules for new code

1. New production runtime behavior belongs under backend/app/workforce/agents/runtime.
2. New business tool schemas belong in backend/app/core/tool_registry.py; tool backend/transport implementations belong under backend/app/workforce/tools.
3. New workflow graph and run behavior extends backend/app/integrations/workflows; frontend workflow UI extends frontend/lib/modules/workflows.
4. New persistence tables/models must follow the current db/base metadata ownership until a migration ADR changes it.
5. Frozen retirement candidates may receive only compatibility, migration, or test changes approved by their owning migration plan.
6. A directory name or old plan never proves a module is unused. Consumer report plus tests are required before removal.

## Persistence-model retirement guard

The five agent_runtime persistence model families are canonical SQLAlchemy metadata
owners, not an endorsement of the adjacent agent_runtime runtime scaffold. Any move
or removal requires all of the following: an approved migration plan, Alembic and
SQLAlchemy metadata parity verification, import-consumer migration, and the full
regression suite. Compatibility re-export modules remain until their final consumer
has migrated.

## Workflow visual-builder migration base

The production workflow base is backend/app/integrations/workflows: its models
already persist workflow definitions, versions, graph_jsonb, runs, steps, and
approvals; its router already creates versions and triggers runs. The only workflow
frontend owner is frontend/lib/modules/workflows. Its current library and run-status
surface is intentionally retained as the base for Phase 4; it does not yet claim to
provide drag-and-drop graph authoring. Future compiler, draft, publish, and canvas
work extends these owners instead of creating a second workflow system.

## Evidence commands

~~~sh
rg -n "from agent_runtime|import agent_runtime|from tools|from skills|from workflows|from executors" backend --glob "*.py"
rg -n "agent_runtime_manager|DeepSeekHarnessAdapter|GovernanceKernel|WorkflowVersion" backend/app --glob "*.py"
rg -n "workflows" frontend/lib --glob "*.dart"
~~~

The report generated by scripts/report_harness_ownership.py is required before any frozen candidate is proposed for retirement.
