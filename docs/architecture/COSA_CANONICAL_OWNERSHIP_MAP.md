# COSA Canonical Ownership Map

**Status:** Phase C durable-delegation baseline

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
| Durable multi-agent delegation | `backend/app/workforce/agents/delegation` (`TaskBoardService`, `DelegationProviderManager`) | Canonical production coordination | `RunStep` assignments, append-only `DelegationJob` attempts, ordered `RunEvent`s, worker leases and CoS continuation all route through this package | Assignment policy, tenant-safe task-board operations, provider routing, leases, retry/cancel and continuation triggers | Do not create a second task board, delegation policy vocabulary, or event log; providers implement the canonical delegation contract |
| Long-running work providers | `backend/app/workforce/agents/execution/long_running` (`LongRunningWorkProviderManager`) | Canonical production execution seam | Device, n8n and explicitly configured sandbox executors are bridged into `DelegationProviderManager` | Honest start/poll/cancel/health adapters for external or long-lived work | Provider names are explicit and fail closed; sandbox never selects the default mock implicitly |
| Agent Profile Registry | backend/app/workforce/agents/profiles/schemas.py and registry.py | Canonical production | Composition consumes `AgentProfile`; `TaskBoardService` resolves governed assignments through the self-populating `AgentProfileRegistry` singleton backed by the 12 `agent_runtime.profiles.definitions` role definitions | New/updated AgentProfile fields (e.g. permission_profile, preferred_runtime) and profile lookup | agent_runtime.profiles is NOT part of the frozen agent_runtime.{runtime,models,context,routing,trajectory} candidates -- exclude it when scanning for retirement |
| Runtime governance | backend/app/workforce/agents/governance | Canonical production | GovernanceKernel is used by runtime/execution paths and invariant tests | Policy, approval, audit decision behavior | Consolidate same-name policy helpers only with behavior-parity tests |
| Runtime capability gateway | backend/app/workforce/agents/capabilities | Canonical production | Execution service and capability routes import it | Capability grants, provider binding, connector authorization | Any merge with GovernanceKernel requires dedicated ADR and test plan |
| Model reliability gateway | backend/app/workforce/agents/reliability | Canonical production | Workforce AI policy imports ModelGateway and ModelProfileRegistry | Retry, circuit breaking, profile/model selection | Retire parallel agent_runtime model gateway after consumers migrate |
| DeepSeek Harness adapter | backend/app/workforce/agents/runtime/adapters/deepseek_harness.py | Canonical production adapter | Runtime manager registers deepseek_harness; orchestration resolves it | Version-pinned adapter compatibility only | Keep thin; do not import DSH internals into Business Core |
| Core tool registry | backend/app/core/tool_registry.py and tool_dispatch.py | Canonical production | GovernanceKernel resolves ToolSpec; chat/runtime dispatch uses it | Registered COSA business tool schemas and safe parameter injection | Do not create root tools registry consumers |
| Extension metadata and connector registration | backend/app/workforce/extensions/tool_registration.py, backed by registry.py and eligibility.py | Canonical production | Eligible workspace discovery snapshots are mapped to canonical connector `ToolSpec`s; invocation re-resolves the endpoint snapshot from the request scope before MCP dispatch | Extension metadata-to-`ToolSpec` mapping and request-scoped connector registration | Keep `app.core.tool_registry` and `GovernanceKernel` as the registry and policy authorities; do not route extensions through `AgentGateway` |
| Workforce tools/transports | backend/app/workforce/tools (tools/invocation pipeline, tools/transports) | Canonical production | tools/invocation is the real GovernanceKernel-routed dispatch path (backend/app/core/tool_dispatch.py imports invoke_tool_legacy from tools/invocation/service.py); tools/transports/mcp_adapter.py's MCPToolAdapter.execute() is the confirmed real interface behind the Task 3 ProviderProtocolError fix | Tool backends, connector transports, future extension adapters | Extension registry will own discovery metadata, not direct dispatch bypass |
| Workforce Agent Gateway stack | backend/app/workforce/gateway (AgentGateway, RiskPolicyEvaluator, gateway/approval.py::ApprovalService) and auto_register.py's register_all_domain_tools | Audit required / not a production dependency | `AgentGateway(...)` is instantiated only in agent-platform tests; production extension modules neither import nor instantiate it. Canonical extension registration now lives in workforce/extensions/tool_registration.py, and auto_register.py no longer contains an extension-registration path | No new production code should depend on AgentGateway | Preserve only for compatibility tests while consumer/retirement evidence is completed; production tools and extensions use the canonical registry, invocation service, and GovernanceKernel |
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
| Company Runtime (thư mục hiện tại là platform/license) | backend/app/platform/license | Canonical production | Router tự gọi nó là `company_runtime` tại `backend/app/platform/router.py:22`; `decomposition_service.py`/`handoff_service.py` phân rã mission tuần thành Task theo function (LEGAL/MARKETING/SALES/TECH/FINANCE) và xử lý handoff giữa các function; mounted tại `/api/v1/company-runtime` | Per-function Task/Outcome decomposition, handoff, blocker, review, checkpoint | Đổi tên thư mục là 1 việc riêng (rủi ro thấp, độc lập) chưa làm trong lần cập nhật này — coi đường dẫn này là Company Runtime bất kể tên thư mục |
| Hybrid Workforce identity (Organization) | backend/app/platform/organization (`WorkforceMember`, `WorkforceRelation`) | Canonical production | Mounted tại `/api/v1/organization`; `hire_ai_employee()` là writer sản xuất duy nhất của `WorkforceMember` | Định danh nhân sự hỗn hợp Human+AI, org-chart thật qua `WorkforceRelation` | `WorkforceMember.agent_id` (cũ, FK `agents.id`) đang được thay bằng `agent_definition_id` (FK `agent_definitions.id`) — code mới phải dùng `agent_definition_id` |
| AI employee canonical identity | backend/app/workforce/models.py::AgentDefinition | Canonical persistence model | Được chọn làm canonical AI employee record (quyết định hợp nhất định danh 2026-08-21) thay vì `Agent` (founder_os/tasks/models.py) hay `AgentProfile` không-persist; join sang `AgentProfile` qua field `profile_slug` | `profile_slug`, các field risk/capabilities/model_config hiện có | `AgentHierarchy` (cùng file) chỉ là template topology AI-AI, KHÔNG phải org-chart công ty thật — org-chart thật là `WorkforceRelation` |
| Legacy Agent identity | backend/app/founder_os/tasks/models.py::Agent (table agents) | Audit required (không phải "chỉ dùng làm FK target" như từng ghi nhận) | Có CRUD API độc lập đang chạy thật tại `/api/v1/agents` (`backend/app/founder_os/tasks/agents_router.py`, tích hợp `protected_resource_service` cho prompt-revision), hoàn toàn tách biệt khỏi `WorkforceMember`; `hire_ai_employee()` đã ngừng ghi mới vào bảng này từ quyết định hợp nhất định danh 2026-08-21 (xác nhận bằng scripts/report_identity_consumers.py: platform/organization/service.py không còn xuất hiện trong báo cáo sau khi Task 5 merge; agents_router.py và db/base.py vẫn là consumer hợp lệ, không xoá) | Chỉ sửa lỗi cho `/api/v1/agents` CRUD hiện có | Xoá hẳn cần 1 quyết định riêng (di chuyển `/api/v1/agents` sang dùng `AgentDefinition`, hoặc chính thức giữ `Agent` như 1 resource riêng nhẹ) — không xoá dựa trên map này |
| Task-to-agent dispatch (song song, chưa hợp nhất) | backend/app/workforce/dispatcher (`AgentTaskDispatcher`, mounted tại `POST /api/v1/workforce/tasks/{task_id}/dispatch`) | Audit required | Có đủ governance (budget/risk/approval/cost-ledger/work-product) nhưng resolve agent qua `AgentDefinition.key` trực tiếp và KHÔNG đọc `Task.execution_mode`/`assignee_member_id` — là 1 đường dispatch Task→Agent thứ 2, độc lập, song song với pipeline `TaskBoardService`/`RunStep` mà `execution_mode="AGENT"` dùng (phát hiện mới, 2026-08-21, không có trong đề xuất gốc) | Không có cho tới khi được đối chiếu | 2 pipeline dispatch Task→Agent sống song song là cùng loại rủi ro fragmentation với định danh Agent — cần 1 quyết định riêng để hợp nhất/giữ tách biệt rõ ràng |
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

## Hybrid Workforce identity canonicalization (2026-08-21)

`AgentDefinition` is the canonical AI employee record; `AgentProfile`
(`workforce/agents/profiles/schemas.py`) stays in-memory/non-persisted and is
joined via `AgentDefinition.profile_slug`; `WorkforceMember` is the unified
Human+AI employee identity; `WorkforceRelation` is the real company org chart
(Human<->AI hierarchy), while `AgentHierarchy` stays AI-template-only topology.
`Agent` (`founder_os/tasks/models.py`, table `agents`) and `AgentRelation`
(`platform/organization/models.py`) are not deleted -- see the Ownership map
rows above and CLAUDE.md §14.

Long-term direction (not implemented yet, no task tracks this): `UnifiedPermission.principal`
(`workforce/models.py`) is currently `USER`/`AGENT`. Since `User` is an authentication
identity and `AgentDefinition` is a template (one definition can be instantiated into
many `WorkforceMember`s across workspaces), `principal` should eventually move toward
`WORKFORCE_MEMBER`/`SERVICE`/`DEVICE`, tracking the actual employee instance instead of
the template or the login identity. This is a documented future direction, not a
required migration.

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
