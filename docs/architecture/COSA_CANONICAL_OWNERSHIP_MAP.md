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
| Business domain models | backend/business_core | Canonical production | Recent core migration; compatibility imports still exist in app business/founder modules | Business entities and deterministic domain rules | Retire compatibility exports only after import scan and database metadata parity |
| Co-Founder Mission Orchestrator | `backend/workforce/agents/orchestration` (`AdkCofounderWorkflow`, `orchestration/service.py`, `SpecialistRegistry`, `MissionResumeJobService`, `RuntimeSession`) | Canonical production | All mission orchestration, founder review/confirmation, and specialist delegation resumes route through `orchestration_service.orchestrate_mission`, `confirm_mission`, and `resume_mission`. Legacy `chief_of_staff.py` is fully retired. | ADK workflow nodes, deterministic gates (R0-R4), quality gates, durable task board delegation, session lifecycle | Do not create a parallel orchestrator loop; `chief_of_staff.py` is permanently deleted (2026-08-21) |
| Agent runtime implementation | backend/workforce/agents/runtime | Canonical production | Router, runtime manager, ADK workflow orchestrator, and DSH adapter import this path | Turn runtime, runtime request types, adapter contract | No parallel driver under agent_runtime |

| Durable multi-agent delegation | `backend/workforce/agents/delegation` (`TaskBoardService`, `DelegationProviderManager`) | Canonical production coordination | `RunStep` assignments, append-only `DelegationJob` attempts, ordered `RunEvent`s, worker leases and CoS continuation all route through this package | Assignment policy, tenant-safe task-board operations, provider routing, leases, retry/cancel and continuation triggers | Do not create a second task board, delegation policy vocabulary, or event log; providers implement the canonical delegation contract |
| Long-running work providers | `backend/workforce/agents/execution/long_running` (`LongRunningWorkProviderManager`) | Canonical production execution seam | Device, n8n and explicitly configured sandbox executors are bridged into `DelegationProviderManager` | Honest start/poll/cancel/health adapters for external or long-lived work | Provider names are explicit and fail closed; sandbox never selects the default mock implicitly |
| Agent Profile Registry | backend/workforce/agents/profiles/schemas.py and registry.py | Canonical production | Composition consumes `AgentProfile`; `TaskBoardService` resolves governed assignments through the self-populating `AgentProfileRegistry` singleton backed by the 12 `agent_runtime.profiles.definitions` role definitions | New/updated AgentProfile fields (e.g. permission_profile, preferred_runtime) and profile lookup | agent_runtime.profiles is NOT part of the frozen agent_runtime.{runtime,models,context,routing,trajectory} candidates -- exclude it when scanning for retirement |
| Runtime governance | backend/workforce/agents/governance | Canonical production | GovernanceKernel is used by runtime/execution paths and invariant tests | Policy, approval, audit decision behavior | Consolidate same-name policy helpers only with behavior-parity tests |
| Runtime capability gateway | backend/workforce/agents/capabilities | Canonical production | Execution service and capability routes import it | Capability grants, provider binding, connector authorization | Any merge with GovernanceKernel requires dedicated ADR and test plan |
| Model reliability gateway | backend/workforce/agents/reliability | Canonical production | Workforce AI policy imports ModelGateway and ModelProfileRegistry | Retry, circuit breaking, profile/model selection | Retire parallel agent_runtime model gateway after consumers migrate |
| DeepSeek Harness adapter | backend/workforce/agents/runtime/adapters/deepseek_harness.py | Canonical production adapter | Runtime manager registers deepseek_harness; orchestration resolves it | Version-pinned adapter compatibility only | Keep thin; do not import DSH internals into Business Core |
| Core tool registry | backend/core/tool_registry.py and tool_dispatch.py | Canonical production | GovernanceKernel resolves ToolSpec; chat/runtime dispatch uses it | Registered COSA business tool schemas and safe parameter injection | Do not create root tools registry consumers |
| Extension metadata and connector registration | backend/workforce/extensions/tool_registration.py, backed by registry.py and eligibility.py | Canonical production | Eligible workspace discovery snapshots are mapped to canonical connector `ToolSpec`s; invocation re-resolves the endpoint snapshot from the request scope before MCP dispatch | Extension metadata-to-`ToolSpec` mapping and request-scoped connector registration | Keep `app.core.tool_registry` and `GovernanceKernel` as the registry and policy authorities; do not route extensions through `AgentGateway` |
| Workforce tools/transports | backend/workforce/tools (tools/invocation pipeline, tools/transports) | Canonical production | tools/invocation is the real GovernanceKernel-routed dispatch path (backend/core/tool_dispatch.py imports invoke_tool_legacy from tools/invocation/service.py); tools/transports/mcp_adapter.py's MCPToolAdapter.execute() is the confirmed real interface behind the Task 3 ProviderProtocolError fix | Tool backends, connector transports, future extension adapters | Extension registry will own discovery metadata, not direct dispatch bypass |
| Workforce Agent Gateway stack | backend/workforce/gateway (AgentGateway, RiskPolicyEvaluator, gateway/approval.py::ApprovalService) and auto_register.py's register_all_domain_tools | Audit required / not a production dependency | `AgentGateway(...)` is instantiated only in agent-platform tests; production extension modules neither import nor instantiate it. Canonical extension registration now lives in workforce/extensions/tool_registration.py, and auto_register.py no longer contains an extension-registration path | No new production code should depend on AgentGateway | Preserve only for compatibility tests while consumer/retirement evidence is completed; production tools and extensions use the canonical registry, invocation service, and GovernanceKernel |
| Workflow persistence/API | backend/integrations/workflows | Canonical production | db/base imports WorkflowDefinition/Version/Run/Step/Approval; router exposes graph_jsonb and runs | Graph compiler, version lifecycle, workflow execution API | Preserve tables/routes; evolve in place |
| Workflow frontend | frontend/lib/modules/workflows | Canonical production | Dashboard imports WorkflowsView; service calls workflows definitions/runs API | Workflow Library, Builder, Test/Publish, Run Inspector | Do not create a second workflow canvas module |
| Runtime persistence models | backend/agent_runtime/sessions/models.py; backend/agent_runtime/events/models.py; backend/agent_runtime/permissions/models.py; backend/agent_runtime/sandbox/models.py; backend/agent_runtime/memory/models.py | Canonical persistence model | backend/db/base.py imports all five modules; workforce compatibility models re-export them | SQLAlchemy table metadata and carefully reviewed persistence evolution | Any move requires Alembic/metadata parity test and explicit migration |
| agent_runtime runtime/models/context/routing/trajectory | backend/agent_runtime/runtime; backend/agent_runtime/models; backend/agent_runtime/context; backend/agent_runtime/routing; backend/agent_runtime/trajectory | Removed (Quyết định 6.1 Nhóm A) | 0 production consumers; deleted 2026-08-21. (`sessions/models.py` and `profiles/` definitions are retained as canonical persistence/definitions) | None | Removed |
| Root tools scaffold | backend/tools | Removed (Quyết định 6.1 Nhóm A) | 0 production consumers; deleted 2026-08-21 | None | Removed |
| Root skills scaffold | backend/skills | Removed (Quyết định 6.1 Nhóm A) | 0 production consumers; deleted 2026-08-21 | None | Removed |
| Root workflows scaffold | backend/workflows | Removed (Quyết định 6.1 Nhóm A) | 0 production consumers; deleted 2026-08-21 | None | Removed |
| Root executors scaffold | backend/executors | Removed (Quyết định 6.1 Nhóm A) | 0 production consumers; deleted 2026-08-21 | None | Removed |
| Plugin host | backend/integrations/channels/plugins/plugin_host.py | Audit completed / Frozen candidate | 0 production consumers (only test_plugin_host_facade.py) | No direct plugin execution | Candidate for retirement |
| Tool Invocation Entrypoints | Chat tools, ToolBridge, Workflow Runner, MCP Bridge, DSH adapter | Canonical production | Execution entrypoints currently directly calling ToolSpec or providers | Direct execution without unified pipeline | Migrate to unified ToolInvocationService in Phase 3 |
| Postgres agent audit | workforce governance models and agent event bus | Canonical production projection | AgentToolCall and AgentEventRecord are production imports | Audit/compliance projection | Event authority decision deferred to Phase 6 |
| OpenTelemetry | backend/core/telemetry.py | Canonical telemetry projection | GovernanceKernel calls trace_span | Cross-service telemetry | Does not become session history authority |
| SQLite session/event scaffold | backend/storage/sqlite and backend/agent_runtime/events/sessions | Frozen retirement candidate / Audit completed | 0 production consumers; local-first authority selection deferred | Test support only | Candidate for cleanup |
| Company Runtime (thư mục hiện tại là platform/license) | backend/platform_core/license | Canonical production | Router tự gọi nó là `company_runtime` tại `backend/platform_core/router.py:22`; `decomposition_service.py`/`handoff_service.py` phân rã mission tuần thành Task theo function (LEGAL/MARKETING/SALES/TECH/FINANCE) và xử lý handoff giữa các function | Per-function Task/Outcome decomposition, handoff, blocker, review, checkpoint | Đổi tên thư mục là 1 việc riêng (rủi ro thấp, độc lập) chưa làm trong lần cập nhật này — coi đường dẫn này là Company Runtime bất kể tên thư mục |
| Hybrid Workforce identity (Organization) | backend/platform_core/organization (`WorkforceMember`, `WorkforceRelation`) | Canonical production | Mounted tại `/api/v1/organization`; `hire_ai_employee()` là writer sản xuất duy nhất của `WorkforceMember` | Định danh nhân sự hỗn hợp Human+AI, org-chart thật qua `WorkforceRelation` | `WorkforceMember.agent_id` (cũ, FK `agents.id`) đang được thay bằng `agent_definition_id` (FK `agent_definitions.id`) — code mới phải dùng `agent_definition_id` |
| AI employee canonical identity | backend/workforce/models.py::AgentDefinition | Canonical persistence model | Được chọn làm canonical AI employee record (quyết định hợp nhất định danh 2026-08-21) thay vì `Agent` (founder_os/tasks/models.py) hay `AgentProfile` không-persist; join sang `AgentProfile` qua field `profile_slug` | `profile_slug`, các field risk/capabilities/model_config hiện có | `AgentHierarchy` (cùng file) chỉ là template topology AI-AI, KHÔNG phải org-chart công ty thật — org-chart thật là `WorkforceRelation` |
| Legacy Agent identity | backend/founder_os/tasks/models.py::Agent (table agents) | Audit completed / Legacy surface | Có CRUD API độc lập đang chạy tại `/api/v1/agents` (`backend/founder_os/tasks/agents_router.py`, tích hợp `protected_resource_service` cho prompt-revision); đã thêm docstring cảnh báo kiến trúc; `hire_ai_employee()` đã ngừng ghi mới vào bảng này | Chỉ sửa lỗi cho `/api/v1/agents` CRUD hiện có | Giữ như 1 legacy/admin prompt revision resource |
| Task-to-agent dispatch (song song, chưa hợp nhất) | backend/workforce/dispatcher (`AgentTaskDispatcher`, mounted tại `POST /api/v1/workforce/tasks/{task_id}/dispatch`) | Audit completed / Dedicated path | Sử dụng cho routine/admin automation với `AgentDefinition.key` trực tiếp; pipeline canonical `dispatch_agent_task()` dùng cho `Task.execution_mode="AGENT"` qua `TaskBoardService`/`RunStep`. Hai đường dispatch được phân định ranh giới: (1) Business Work Items đi qua `dispatch_agent_task()`, (2) Direct Agent Execution/Routines đi qua `AgentTaskDispatcher`. Ranh giới này giờ được ghi ngay trong docstring của cả 2 class/hàm (2026-08-21, Task 4 của completion plan), không chỉ ở đây. | Không mở rộng thêm dispatch path thứ 3 | Giữ 2 path với ranh giới rõ ràng hoặc lên kế hoạch redirect routines sang TaskBoardService |
| ~~Task-to-agent dispatch #3 (dead)~~ | ~~backend/founder_os/tasks/task_dispatcher.py (`dispatch_pending_tasks`)~~ | **Removed 2026-08-21** | Phát hiện khi audit Task 4: đây thực ra là 1 no-op — `worker_main.py`'s background loop gọi nó mỗi vòng, nhưng thân hàm chỉ query `Task(status="todo")` rồi log, phần cập nhật status/thực thi thật đã bị comment out từ đầu ("Actual execution logic would be deferred to workflow_runtime", chưa từng viết). Consumer report: chỉ 1 call site (`worker_main.py`), không ai khác import. Đã xóa file + bỏ call site; không phải 1 trong 2 đường dispatch thật ở trên. | — | Đã xóa, không cần theo dõi thêm |
| Company portfolio scope | Workspace is the Company/tenant in Phase 1. OperatingUnit and Offering are Business Core entities. Initiative remains the existing operational record and Task remains the WorkItem engine. Project is a linked strategy record, not a replacement hierarchy level. | Canonical production/persistence anchors | Existing Workspace, Initiative, Task, and Project models | Extend the existing anchors in place; do not create a parallel Company table or split the Task engine | Any hierarchy change requires an explicit ownership and migration decision |

## Newly-tracked capability families (2026-08-22, see ADR-012)

These five families existed only in `legacy/backend` with no ownership row, which let `agentos/`+`services/` drift ahead in some areas (Business Core, Task/OKR/CRM/Finance) while staying silently absent in others. Recorded here so a future contributor does not fork a second implementation without checking first (CLAUDE.md §14).

| Capability family | Canonical owner today | Classification | Evidence | Migration condition |
|---|---|---|---|---|
| LLM Chat Gateway (multi-provider) | `agentos/core/adapters/model_gateway.py` (DeepSeek/OpenAI/OpenRouter/Anthropic) | Canonical production for `agentos/` | Self-contained `httpx`-based providers, no `legacy/backend` dependency — built 2026-08-22 after `legacy/backend` was frozen-in-place (ADR-012 "Decision on Correction #2" superseded the original "call legacy/backend over HTTP" plan, since that HTTP target does not run). `legacy/backend/integrations/llm_providers/*` remains as an unused historical reference — do not import it. | Add a provider by extending `model_gateway.py`'s `build_model_provider()`; Gemini/Kira/apiai_vn not yet ported (no test coverage written for them, add when needed) |
| OAuth / external account linking | `legacy/backend/integrations/channels/google/*` | Canonical production | Token encryption via `MASTER_SECRET_KEY`; OAuth flow tested (`test_google_oauth.py`) | Stays in `legacy/backend`; `services/identity` calls it internally when needed — do not rewrite OAuth flow inside `services/` or `agentos/` |
| Automation / n8n workflow bridge | `legacy/backend/integrations/workflows/n8n_gateway_service.py` | Canonical production | HMAC-SHA256 signed webhook dispatch already running | Expose as an `agentos/tools/clusters/automation_tools.py` HTTP-wrapper Tool (same pattern as `operations_tools.py`), gated by `PermissionClass.EXTERNAL_WRITE` |
| Sandboxed code execution | `legacy/backend` + `opensandbox` container (`COSA_EXECUTION_PROVIDER`) | Canonical production | Root `docker-compose.yml` `opensandbox` service, port 8080 | Expose as an `agentos/tools/clusters/sandbox_tools.py` Tool gated by `PermissionClass.EXECUTE_CODE` (must go through the now-wired PolicyEngine/ApprovalService in `agentos/core/executor.py`) |
| Extensions / Plugin API | `legacy/backend` (consumed by `frontend/lib/modules/settings/views/settings_extensions_page.dart` at `:8000`) | Audit required / no owner in `services/` yet | No `services/` cluster exposes an equivalent route | Do not point the frontend extensions page at `:4000` until a `services/` (or `agentos/` tool) owner exists — see ADR-012 |

## `agentos/` + `services/` migration status (2026-08-22, see ADR-012)

`agentos/` was introduced by ADR-AGENTOS-001 as an explicitly **inert, parallel** runtime — not wired into any production entrypoint. `services/` (Encore) has Phase 1 schema/logic parity for `identity`/`operations`/`commercial`/`finance-legal`.

**Update (2026-08-22, Giai đoạn 2 pilot, see `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md`):** `services/` now has its first verified real consumer. `agentos/tools/registry.py` (`register_cluster_tools`) + `agentos/tools/encore_client.py`, invoked through the `task_create`/`task_list`/`task_update_status` tool bindings, were exercised against a live `encore run` instance of `services/` over real HTTP (not a mocked `EncoreClient`) — workspace creation, task creation with idempotency-key retry, and status transition to `done` all round-tripped through Postgres correctly. Integration test: `tests/agentos/test_services_pilot_e2e.py` (skips automatically if no live Encore server is reachable at `:4000` — does not block CI without the dev stack running). While wiring this pilot, a real gap was found and fixed: `shared/events.ts` defined `TASK_CREATED = "task.created"` but nothing ever published it — `createTask` (`services/operations/task.ts`) now publishes it on a genuine insert only (guarded via Postgres `xmax = 0`, so an idempotency-key retry does not re-publish), verified via `vi.spyOn` in `services/operations/task.test.ts` (full `services/` suite 117/117 pass, `tsc --noEmit` clean). This is **still not full production parity** — `services/` is still not called from `legacy/agent_runtime`, `frontend/`, or `realtime_agent`. **Update (2026-08-22, same day, 3 pilot extension rounds):** the pilot now covers every remaining tool binding across all 4 clusters — `services/operations` (all 8: task/okr/12wy/initiative), `services/commercial` (lead/account/contact/opportunity), `services/finance-legal` (transaction/accounting-period/obligation/checklist), `services/identity` (`workspace_get`) — 15/15 pass, `tests/agentos/test_services_pilot_e2e.py`. While extending to identity/commercial, found and fixed **4 more broken tool bindings** (same class as the OKR/12WY bug above, confirmed via real HTTP 404s): `workspace_list`, `organization_get`, `workforce_member_list`, `opportunity_list` all called routes that don't exist in `services/` — removed (not redirected, no real route to point to), see ADR-012 "Follow-up: 3 broken identity/commercial list-style tools found." `commercial.sales_leads` has no `idempotency_key` and no domain event yet — deliberately not added, since inventing lead-lifecycle event semantics is a business decision, not a mechanical gap fix. `customer`/`billing`/`marketing` domains have no tool bindings at all yet (not a pilot gap — nothing to verify). `legacy/agent_runtime`, `frontend/`, `realtime_agent` still don't call `services/` — this pilot proves technical capability, not production traffic.

`legacy/backend` (`brain-api`/`agent-worker` via the root `docker-compose.yml`) is **frozen-in-place** (user-confirmed decision, 2026-08-22, see ADR-012 "Correction #2"): the restructure commit `5c5bc85` split it across 6 sibling `legacy/*` directories (`backend`, `agent_runtime`, `platform`, `business`, `domains`, `entrypoints`) without updating the Docker build, so it is known-broken today and is **not** being resurrected. `migrate`/`migrate-control-plane`/`brain-api`/`agent-worker` are gated behind `docker compose --profile legacy` so they no longer start by default. Effort instead goes into extracting the specific pieces `agentos/` needs (LLM Gateway, OAuth, n8n, Sandbox) as adapters — see ADR-012 Decision. Per ADR-013, `legacy/agent_runtime`'s orchestration/governance/delegation/reliability capabilities are also targeted for eventual replacement by `agentos/`, on the same "prove parity before cutover" basis — not yet started beyond this Giai đoạn 2 pilot.

## Rules for new code

1. New production runtime behavior belongs under backend/workforce/agents/runtime.
2. New business tool schemas belong in backend/core/tool_registry.py; tool backend/transport implementations belong under backend/workforce/tools.
3. New workflow graph and run behavior extends backend/integrations/workflows; frontend workflow UI extends frontend/lib/modules/workflows.
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

The production workflow base is backend/integrations/workflows: its models
already persist workflow definitions, versions, graph_jsonb, runs, steps, and
approvals; its router already creates versions and triggers runs. The only workflow
frontend owner is frontend/lib/modules/workflows. Its current library and run-status
surface is intentionally retained as the base for Phase 4; it does not yet claim to
provide drag-and-drop graph authoring. Future compiler, draft, publish, and canvas
work extends these owners instead of creating a second workflow system.

## Related gap analysis and direction ADRs (2026-08-22)

`docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` cross-references `markdown/AI_Agent_OS_Master_Architecture.md` against this ownership map, section by section, to identify where `agentos/` duplicates or diverges from the `legacy/agent_runtime` production runtime documented below. Read it before adding new code to `agentos/`, `agentos/skills/`, `agentos/workflows/`, or `agentos/core/policy.py`.

Three ADRs (user-confirmed, same day) set direction that **supersedes several rows below** even though those rows have not yet been rewritten (the underlying code/parity work has not landed — see each ADR's Consequences before treating a row as already migrated):

- `docs/architecture/adr/ADR-013-agentos-supersedes-legacy-agent-runtime.md` — `agentos/` is the target agent-runtime architecture; `legacy/agent_runtime/workforce/agents/{orchestration,delegation,governance,reliability}` are phased out over time, not deleted immediately. New agent-runtime code goes in `agentos/`, not `legacy/agent_runtime`.
- `docs/architecture/adr/ADR-014-permission-model-L0-L3-canonical.md` — `PermissionLevel` (L0-L3A-L3, from `legacy/agent_runtime/cosa_core/governance/policy_engine.py`) is the canonical governance vocabulary, to be ported into `agentos/core/policy.py`, replacing `PermissionClass` as the decision mechanism.
- `docs/architecture/adr/ADR-015-workflow-engine-agentos-canonical.md` — `agentos/workflows/` is the canonical workflow engine; `legacy/backend/integrations/workflows`'s version-history feature is the one gap to port over.

Rows below for "Co-Founder Mission Orchestrator", "Durable multi-agent delegation", "Runtime governance", and "Workflow persistence/API" still describe **today's actual production dependency** (per this map's evidence-based classification rules) — do not treat them as retired until the corresponding ADR's migration work has landed and this map has been updated to match, per this map's own "Rules for new code" §6 ("a directory name or old plan never proves a module is unused").

**Update (2026-08-22, gap analysis Giai đoạn 3 gap-closing work landed in `agentos/`):** `agentos/workflows/` gained `ParallelStep`/`RetryStep`/`CompensatingStep` (parallel fan-out, retry, best-effort rollback on failure); `agentos/core/audit_sink.py` (`SqliteAuditSink`) gives `PolicyEngine`/`ApprovalService` a persistent, run_id-queryable audit trail (previously in-memory only); `agentos/core/model_provider.py`'s `ModelResponse` now carries real `TokenUsage` from provider API responses, summed into `agentos/observability/metrics.py`'s `RunMetrics` (cost_usd only when the caller supplies real pricing — never guessed); `agentos/memory/consolidation.py` gained `ProceduralConsolidator`. None of this changes the classification above — `agentos/` is still not wired into any production entrypoint (ADR-AGENTOS-001 still holds), this is gap-closing toward the ADR-013 target, not a cutover. See `docs/architecture/specs/` (10 specs, one per layer, each noting current status and what's still missing) for the itemized breakdown, and `docs/architecture/AI_AGENT_OS_GAP_ANALYSIS.md` for full detail.

## Evidence commands

~~~sh
rg -n "from agent_runtime|import agent_runtime|from tools|from skills|from workflows|from executors" backend --glob "*.py"
rg -n "agent_runtime_manager|DeepSeekHarnessAdapter|GovernanceKernel|WorkflowVersion" backend --glob "*.py"
rg -n "workflows" frontend/lib --glob "*.dart"
~~~

The report generated by scripts/report_harness_ownership.py is required before any frozen candidate is proposed for retirement.
