# Founder-Configurable Role, Agent, Skill & Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cho Founder tạo hoặc clone agent, skill và workflow có governance, sau đó triển khai chúng vào Project và thực thi bằng manifest hash-pinned, approval, audit, evaluation và improvement bền vững.

**Architecture:** Company Business Plane là command/authority owner cho Workspace role, AI workforce member và Project deployment. Agent Platform giữ custom AgentSpec/SkillSpec/WorkflowSpec, evaluation, registry, execution manifest và run persistence; Company giao tiếp qua signed outbox/internal event và chỉ project dữ liệu thật cho UI. Flutter chỉ author Draft, deploy vào Project và quan sát data server, không chứa authority hay graph validation.

**Tech Stack:** TypeScript/Encore + Drizzle/PostgreSQL (`services/company`), Python/FastAPI + SQLAlchemy/Pydantic (`packages/agent`, `apps/cosa`), signed cross-plane outbox, OpenAI Agents SDK runtime, Flutter/GetX + generated MVP contracts, pytest/Vitest/Flutter test, disposable PostgreSQL/process E2E.

**Spec:** `docs/superpowers/specs/2026-09-13-founder-configurable-agent-skill-workflow-design.md`

## Global Constraints

- Built-in Role/AgentSpec/SkillSpec/WorkflowTemplate là Platform-owned, read-only; Founder chỉ `clone`, không `PATCH`/delete trực tiếp.
- Agent, skill và workflow là Workspace asset; Project chỉ giữ binding/deployment và chỉ có quyền thu hẹp data, budget, policy và capability.
- Mọi business run mới bắt buộc có `workspace_id` và `project_id`; active Project local của Flutter không là authorization.
- Company là nguồn sự thật cho Founder command, business permission, AI WorkforceMember và deployment. Agent Platform không đọc/ghi Company DB trực tiếp.
- Agent Platform là owner cho spec body/version/hash, evaluation, run manifest, checkpoint, usage và feedback; Company chỉ giữ opaque reference/hashes cùng audit business.
- `DENY` thắng; Control Plane chỉ siết chặt; high-risk effect cần live one-time ticket bind `(run_id, tool_call_id, checkpoint_ref, capability_id, authorizationEpoch)`.
- Published version immutable; `PINNED` là binding/run snapshot chứ không là trạng thái toàn cục của asset.
- Migration chỉ additive. Không xóa `project_agent_assignments` hay dữ liệu Executive Board trong release này; dùng dual-read/shadow và rollback qua feature flag.
- Down migration chỉ dùng cho database disposable chưa có record; production rollback tắt feature flag và giữ nguyên asset, manifest, run và audit record để forensic/replay.
- Không cho custom prompt/skill/workflow mang raw secret, connector credential, raw shell, arbitrary network, generic code execution hay capability chưa đăng ký.
- `shared/contracts/mvp-surface.json` là nguồn route/capability; sau mỗi route change chạy `node scripts/gen-mvp-contracts.mjs`, `make contract-freeze-check` và `make frontend-api-contract-check`.
- Không hiển thị node workflow nào publishable nếu chưa có executor thật và conformance test. Không dùng no-op fallback để giả vờ workflow đã chạy.

---

## File Structure and Boundaries

| Boundary | Files | Responsibility |
|---|---|---|
| Company data/commands | `services/company/operations/migrations/013_founder_configurable_assets.*.sql`, `services/company/shared/db/schema/operations.ts`, `services/company/operations/services/founder-asset*.ts`, `services/company/operations/handlers/founder-asset*.ts` | Founder authority, operating role, workforce identity, Project deployment, business audit/outbox. |
| Shared public surface | `shared/contracts/mvp-surface.json`, generated contract files, `frontend/lib/core/network/mvp_endpoints.g.dart` | Typed public Company routes; no literal Flutter URLs. |
| Agent asset registry | `packages/agent/migrations/009_founder_configurable_assets.*.sql`, `packages/agent/assets/*`, `apps/cosa/assets/*` | Workspace/project-sandbox asset bodies, clone lineage, immutable publish/evaluation and scoped resolution. |
| Workflow runtime | `packages/agent/workflows/*`, `packages/agent/runs/*`, `apps/cosa/composition/*`, `apps/cosa/worker/*`, `apps/cosa/events/*` | Durable workflow definitions/manifests/steps, typed validation, real executors, scheduled dispatch and resume. |
| Cross-plane projection | `services/company/events/outbox-relay.service.ts`, `apps/cosa/events/router.py`, `apps/cosa/company/*` | Signed commands/callbacks, idempotency, opaque references and live authority refresh. |
| Flutter | `frontend/lib/modules/founder_workforce/*`, `frontend/lib/modules/hologram_hub/*`, `frontend/test/modules/founder_workforce/*` | Library, Project deployment, draft builder, truthful timeline; server owns all validation. |
| Verification | `services/company/operations/tests/founder-asset*.test.ts`, `tests/agent/assets/*`, `tests/agent/workflows/*`, `tests/apps/cosa/assets/*`, `tests/e2e/test_founder_configurable_workflow.py`, Flutter tests | Red/green unit, contract, migration, process E2E and UI truth evidence. |

## Delivery Sequence

1. Add authoritative data and command boundaries before exposing authoring UI.
2. Add scoped asset repository, clone/evaluation/publish and cross-plane callbacks.
3. Separate Workspace assets from legacy Project profiles with shadow reads.
4. Make workflow persistence and every V1 executor real before enabling canvas publish.
5. Add typed API/Flutter library, deployment, builder and run timeline in that order.
6. Cut over only after disposable-Postgres/process E2E proves revoke, replay, isolation and truthful UI behavior.

---

### Task 1: Add Company-owned operating-role and Project-deployment storage

**Files:**
- Create: `services/company/operations/migrations/013_founder_configurable_assets.up.sql`
- Create: `services/company/operations/migrations/013_founder_configurable_assets.down.sql`
- Modify: `services/company/shared/db/schema/operations.ts`
- Modify: `services/company/operations/models/db.ts`
- Test: `services/company/operations/tests/founder-asset-schema.test.ts`

**Interfaces:**
- Produces Company records `workspace_operating_roles`, `workspace_agents`, `role_agent_bindings`, `project_role_deployments`, `project_agent_deployments`, `project_workflow_bindings`, and append-only `founder_asset_events`.
- Consumed by Tasks 2, 3, 6, 10 and 13. Opaque `agent_asset_id`, `workflow_asset_id`, version and hash refer to Agent Platform data; no cross-database FK is created.

- [ ] **Step 1: Write schema tests for invariants before creating tables**

```ts
it("keeps one workspace agent deployment per project and agent", async () => {
  await insertProjectAgentDeployment({ workspaceId: ws, projectId: projectA, workspaceAgentId: agent });
  await expect(insertProjectAgentDeployment({ workspaceId: ws, projectId: projectA, workspaceAgentId: agent }))
    .rejects.toThrow(/unique/i);
});

it("rejects a deployment whose project belongs to another workspace", async () => {
  await expect(insertProjectRoleDeployment({ workspaceId: wsA, projectId: projectInWsB, roleId }))
    .rejects.toThrow(/fk_project.*workspace/i);
});
```

- [ ] **Step 2: Run the focused test and confirm it fails because the schema/table helpers do not exist**

Run: `cd services/company && encore test --prepare tests/founder-asset-schema.test.ts`
Expected: FAIL with missing table/schema helper.

- [ ] **Step 3: Add the additive Company migration**

Create enum values `DRAFT`, `ACTIVE`, `PAUSED`, `RETIRED`, `SANDBOX` only where state is a deployment state. Add the following minimum columns:

```sql
CREATE TABLE operating.workspace_agents (
  id bigint PRIMARY KEY,
  workspace_id bigint NOT NULL,
  agent_asset_id text NOT NULL,
  agent_asset_version text NOT NULL,
  agent_definition_hash text NOT NULL,
  workforce_member_id bigint NOT NULL,
  state text NOT NULL,
  origin_kind text NOT NULL,
  created_by bigint NOT NULL,
  version integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (workspace_id, agent_asset_id),
  FOREIGN KEY (workforce_member_id) REFERENCES core.workforce_members(id)
);
```

Use composite Project/workspace foreign keys on all deployment tables, unique `(workspace_id, project_id, workspace_agent_id)` for agent deployments and `(workspace_id, project_id, workflow_asset_id)` for workflow bindings. `founder_asset_events` contains actor, command, target kind/ref, before/after hashes, reason, correlation ID and occurred time. The down migration aborts when any new table contains rows and drops only the new tables/enums in reverse dependency order in a disposable empty database; it must not touch legacy tables.

- [ ] **Step 4: Map the new tables in Drizzle with exact bigint/string discipline**

Add each table to `operations.ts` with references and indexes matching SQL. API DTO conversion must use `.toString()` at boundaries; never serialize a JavaScript `bigint` directly.

- [ ] **Step 5: Run focused schema/migration checks**

Run: `cd services/company && encore test --prepare tests/founder-asset-schema.test.ts`
Expected: PASS.

Run: `make services-migrate-company` against disposable PostgreSQL, then apply the down migration in an isolated database.
Expected: new tables appear after up; only new tables disappear after down; legacy `project_agent_assignments` remains.

- [ ] **Step 6: Commit the independent storage boundary**

```bash
git add services/company/operations/migrations/013_founder_configurable_assets.up.sql \
  services/company/operations/migrations/013_founder_configurable_assets.down.sql \
  services/company/shared/db/schema/operations.ts \
  services/company/operations/models/db.ts \
  services/company/operations/tests/founder-asset-schema.test.ts
git commit -m "feat(company): add governed agent deployment storage"
```

### Task 2: Implement Founder-only operating-role and deployment commands

**Files:**
- Create: `services/company/operations/services/founder-asset-deployment.service.ts`
- Create: `services/company/operations/handlers/founder-asset-deployment.handler.ts`
- Modify: `services/company/operations/handlers/index.ts`
- Modify: `services/company/operations/api.ts`
- Test: `services/company/operations/tests/founder-asset-deployment.service.test.ts`
- Test: `services/company/operations/tests/founder-asset-deployment.handler.test.ts`

**Interfaces:**
- Consumes Task 1 tables and the existing Company founder-human authority guard.
- Produces `createOperatingRole`, `bindRoleAgent`, `deployRoleToProject`, `deployAgentToProject`, `bindWorkflowToProject`, `pauseProjectDeployment` and `getProjectDeploymentAuthority`.
- Tasks 3, 10 and 13 use these commands; all mutating calls require `expectedVersion`, `reason` and `idempotencyKey`.

- [ ] **Step 1: Write failing authorization and CAS tests**

```ts
it("allows only a HUMAN founder to deploy a role", async () => {
  await expect(deployRoleToProject(aiAgentContext, input)).rejects.toMatchObject({ code: "permission_denied" });
  await expect(deployRoleToProject(founderContext, input)).resolves.toMatchObject({ state: "ACTIVE" });
});

it("does not append an event on stale expectedVersion", async () => {
  await expect(pauseProjectDeployment(founderContext, { ...input, expectedVersion: 0 }))
    .rejects.toMatchObject({ code: "aborted" });
  expect(await listFounderAssetEvents(input.workspaceId)).toHaveLength(0);
});
```

- [ ] **Step 2: Run the focused service test and confirm it fails**

Run: `cd services/company && encore test --prepare tests/founder-asset-deployment.service.test.ts`
Expected: FAIL because the service exports do not exist.

- [ ] **Step 3: Implement command transaction and audit rules**

Use a single Company transaction for authorization, project/workspace membership validation, optimistic version compare-and-set, state mutation and `founder_asset_events` insert. `bindRoleAgent` accepts only an active WorkspaceAgent from the same workspace. `deployAgentToProject` verifies the requested agent is in the deployed role or has an explicitly recorded shared binding. `getProjectDeploymentAuthority` returns role, workspace-agent, exact agent spec identity, workflow identity, state and policy/budget references; it never returns prompt, secrets or raw skill text.

- [ ] **Step 4: Add thin Encore handlers and public route-free exports**

Handlers only normalize request, call the service and map `APIError`; they do not import Drizzle. Keep public endpoint declarations for Task 13, but export typed service interfaces now:

```ts
export interface ProjectDeploymentAuthority {
  readonly workspaceAgentId: string;
  readonly workforceMemberId: string;
  readonly agentSpec: { id: string; version: string; definitionHash: string };
  readonly roleIds: readonly string[];
  readonly projectId: string;
  readonly state: "ACTIVE" | "PAUSED" | "RETIRED";
}
```

- [ ] **Step 5: Run service and handler tests**

Run: `cd services/company && encore test --prepare tests/founder-asset-deployment.service.test.ts tests/founder-asset-deployment.handler.test.ts`
Expected: PASS, including foreign-project, AI-actor, duplicate binding and stale-version negatives.

- [ ] **Step 6: Commit the Company command boundary**

```bash
git add services/company/operations/services/founder-asset-deployment.service.ts \
  services/company/operations/handlers/founder-asset-deployment.handler.ts \
  services/company/operations/handlers/index.ts services/company/operations/api.ts \
  services/company/operations/tests/founder-asset-deployment.service.test.ts \
  services/company/operations/tests/founder-asset-deployment.handler.test.ts
git commit -m "feat(company): govern role and agent deployments"
```

### Task 3: Add scoped custom-asset persistence in Agent Platform

**Files:**
- Create: `packages/agent/migrations/009_founder_configurable_assets.sql`
- Create: `packages/agent/migrations/009_founder_configurable_assets.down.sql`
- Create: `packages/agent/assets/contracts.py`
- Create: `packages/agent/assets/repository.py`
- Create: `packages/agent/assets/service.py`
- Create: `tests/agent/assets/test_repository.py`
- Create: `tests/agent/assets/test_service.py`
- Modify: `packages/agent/assets/__init__.py`
- Modify: `packages/agent/migrations/README.md`

**Interfaces:**
- Produces `WorkspaceAsset`, `WorkspaceAssetVersion`, `AssetEvaluation`, `AssetScope`, `AssetOrigin`, `AssetLifecycle`, `WorkspaceAssetRepository` and `PostgresWorkspaceAssetRepository`.
- Company references `{asset_id, version, definition_hash}` only. Task 4 uses command methods; Tasks 5, 7 and 8 resolve exact records.

- [ ] **Step 1: Write failing repository tests for tenant isolation and immutable versions**

```python
async def test_workspace_asset_version_cannot_be_read_from_another_workspace(repo):
    saved = await repo.create_draft(workspace_id="ws-a", draft=agent_draft())
    assert await repo.get_version("ws-b", saved.asset_id, saved.version) is None

async def test_published_version_rejects_in_place_content_change(repo):
    published = await repo.publish(workspace_id="ws-a", asset_id="agent-a", expected_hash=HASH)
    with pytest.raises(AssetImmutableError):
        await repo.replace_draft_content("ws-a", published.asset_id, published.version, {"instructions": "changed"})
```

- [ ] **Step 2: Run tests and confirm the package is absent**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/assets -q`
Expected: FAIL during collection because `agent.assets` is missing.

- [ ] **Step 3: Create the Agent Platform migration and contracts**

Create `agent.workspace_assets`, `agent.workspace_asset_versions`, `agent.asset_evaluations` and `agent.asset_events`. Each table has `workspace_id`; versions additionally have `asset_id`, semantic version, `definition_hash`, `content_json`, `lifecycle`, `scope_kind`, nullable `project_id`, origin `{kind,id,version,hash}`, creator, and timestamps. Enforce `(workspace_id, asset_id, version)` and `(workspace_id, asset_id, definition_hash)` uniqueness. Enforce `scope_kind='PROJECT_SANDBOX'` implies non-null `project_id`; workspace assets require null `project_id`.

Define only three custom asset kinds: `AGENT`, `SKILL`, `WORKFLOW`. Built-ins remain in `agent_registry.published_specs`; a custom clone stores the origin identity but never mutates that table's built-in row.

The down migration aborts if any of these new asset tables contains records. It is permitted only for an empty disposable database and never removes a built-in or legacy asset table.

- [ ] **Step 4: Implement repository with fail-closed scope checks**

```python
class WorkspaceAssetRepository(Protocol):
    async def create_draft(self, workspace_id: str, draft: WorkspaceAssetDraft) -> WorkspaceAssetVersion: ...
    async def clone_to_draft(self, workspace_id: str, source: PinnedAssetIdentity, target_scope: AssetScope) -> WorkspaceAssetVersion: ...
    async def get_version(self, workspace_id: str, asset_id: str, version: str) -> WorkspaceAssetVersion | None: ...
    async def publish(self, workspace_id: str, asset_id: str, expected_hash: str) -> WorkspaceAssetVersion: ...
```

`clone_to_draft` loads source by exact kind/id/version/hash, refuses cross-workspace source, copies content into a new draft and records origin. `publish` only accepts an evaluated/reviewed draft and inserts a new immutable record; it never updates a previous published row.

- [ ] **Step 5: Run in-memory and PostgreSQL repository tests**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/assets/test_repository.py tests/agent/assets/test_service.py -q`
Expected: PASS.

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/assets -q`
Expected: PASS against disposable PostgreSQL; skip only when the variable is absent.

- [ ] **Step 6: Commit scoped asset persistence**

```bash
git add packages/agent/migrations/009_founder_configurable_assets.sql \
  packages/agent/migrations/009_founder_configurable_assets.down.sql \
  packages/agent/migrations/README.md packages/agent/assets tests/agent/assets
git commit -m "feat(agent): persist founder configurable assets"
```

### Task 4: Implement clone-only authoring, evaluation and publisher controls

**Files:**
- Create: `apps/cosa/assets/authoring_service.py`
- Create: `apps/cosa/assets/evaluation_service.py`
- Create: `apps/cosa/assets/internal_routes.py`
- Create: `apps/cosa/assets/schemas.py`
- Modify: `apps/cosa/api/app.py`
- Modify: `apps/cosa/composition/agent_plane.py`
- Modify: `packages/agent/skills/improvement_repository.py`
- Test: `tests/apps/cosa/assets/test_authoring_service.py`
- Test: `tests/apps/cosa/assets/test_internal_routes.py`
- Test: `tests/agent/assets/test_publish_lifecycle.py`

**Interfaces:**
- Consumes Task 3 repository and the existing `publish_agent_spec`/`publish_skill_spec` only for platform-built-in publication.
- Produces `AuthoringCommand`, `AssetEvaluationResult`, `publish_workspace_asset`, and internal event receiver requiring the Company service token/signature for Agent/Skill assets.
- Task 10 completes workflow-specific publish validation; Task 5 uses evaluation output; Task 13 receives Company projections.

- [ ] **Step 1: Write failing built-in mutation and lifecycle tests**

```python
async def test_builtin_edit_is_rejected_and_clone_preserves_origin(service):
    with pytest.raises(BuiltinAssetReadOnlyError):
        await service.edit("ws-1", builtin_identity, {"instructions": "mutate"})
    clone = await service.clone("ws-1", builtin_identity, AssetScope.workspace())
    assert clone.origin.definition_hash == builtin_identity.definition_hash

async def test_publish_requires_passing_evaluation_and_founder_command(service):
    draft = await service.create_agent_draft("ws-1", agent_payload())
    with pytest.raises(AssetNotEvaluatedError):
        await service.publish("ws-1", draft.asset_id, draft.definition_hash)
```

- [ ] **Step 2: Run the tests and confirm missing services fail**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/assets/test_authoring_service.py -q`
Expected: FAIL because `apps.cosa.assets` does not exist.

- [ ] **Step 3: Implement strict authoring validation**

Validate agent content with `AgentSpec`, skill content with `SkillSpec`, and workflow draft structure with the existing `WorkflowSpec` DAG validator. Reject unknown capability IDs, raw URLs/shell fields, non-pinned dependencies, source scope mismatch, and a publish command without a Company-issued command reference. For Project sandbox assets reject any non-empty `capability_refs`, `tool_contract_refs` or external trigger. Until Tasks 9–10 install context-aware workflow validation and registered executors, a workflow command may create/edit/evaluate a Draft but returns `WORKFLOW_PUBLISH_DISABLED` for publication.

- [ ] **Step 4: Implement evaluation and review transition**

Persist separate evaluation records with structural result, negative policy cases, scenario suite result, evidence refs, cost/latency summary and evaluator version. The only valid transition is:

```text
DRAFT → CANDIDATE → EVALUATING → REVIEW_REQUIRED → PUBLISHED
```

`RETIRED` may follow `PUBLISHED`; a run pinned before retirement remains resolvable. An LLM improvement may create `CANDIDATE`, but only a signed Company Founder command moves an Agent/Skill from `REVIEW_REQUIRED` to `PUBLISHED`. Task 10 adds the same transition for Workflow after it verifies executor readiness and Project binding contracts.

- [ ] **Step 5: Expose only internal Company-to-Agent routes**

Register `/agent/internal/founder-assets/commands` and `/agent/internal/founder-assets/:asset_id/status`. Verify the service token and signed envelope before parsing the command. Do not expose a browser route in `apps/cosa`; public authoring routes are Company routes in Task 13.

- [ ] **Step 6: Run authoring, lifecycle and boundary tests**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/assets tests/agent/assets/test_publish_lifecycle.py -q`
Expected: PASS, including edit-built-in denial, clone lineage, stale hash, failed evaluation and cross-workspace cases.

- [ ] **Step 7: Commit authoring lifecycle controls**

```bash
git add apps/cosa/assets apps/cosa/api/app.py apps/cosa/composition/agent_plane.py \
  packages/agent/skills/improvement_repository.py tests/apps/cosa/assets \
  tests/agent/assets/test_publish_lifecycle.py
git commit -m "feat(agent): govern asset clone evaluation and publish"
```

### Task 5: Extend skill observation and improvement with Project/run manifest provenance

**Files:**
- Modify: `packages/agent/skills/improvement_repository.py`
- Modify: `packages/agent/skills/candidate_store.py`
- Modify: `packages/agent/skills/contracts.py`
- Modify: `apps/cosa/skills/improvement_service.py`
- Create: `packages/agent/migrations/010_founder_asset_provenance.sql`
- Create: `packages/agent/migrations/010_founder_asset_provenance.down.sql`
- Test: `tests/agent/skills/test_project_provenance.py`
- Test: `tests/e2e/test_skill_improvement_process_recovery.py`

**Interfaces:**
- Consumes existing `SkillUsageObservation` and Task 4 asset identity.
- Produces exact `{workspace_id, project_id, run_id, manifest_hash, skill_id, version, definition_hash}` observation identity and candidate lineage.
- Task 12 projects this data into the run timeline.

- [ ] **Step 1: Write failing feedback-isolation tests**

```python
async def test_feedback_requires_exact_project_run_and_manifest_observation(repo):
    await repo.record_resolved_skill_use(observation(project_id="p-1", manifest_hash="m-1"))
    with pytest.raises(ValueError, match="No observation"):
        await repo.record_feedback_and_maybe_enqueue(feedback(project_id="p-2", manifest_hash="m-1"), policy())
```

- [ ] **Step 2: Run the focused test and confirm the new fields are unsupported**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/skills/test_project_provenance.py -q`
Expected: FAIL because `SkillUsageObservation` lacks `project_id`/`manifest_hash`.

- [ ] **Step 3: Add provenance columns and immutable feedback lookup**

Add nullable-forward-compatible columns to existing observation, aggregate, request and outbox records, then require non-null values for new configured-workflow writes in service code. The unique observation claim becomes `(run_id, skill_id, skill_version, definition_hash)` plus assertions that workspace/project/manifest match the stored row. Do not overwrite older observations.

- [ ] **Step 4: Preserve candidate-only improvement behavior**

When aggregate feedback crosses policy thresholds, create a new Task 4 `CANDIDATE` with `origin` set to the observed pinned skill. Do not alter `AgentSkillBinding`, Project binding, published registry content or an active run.

- [ ] **Step 5: Run recovery tests**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/skills/test_project_provenance.py tests/e2e/test_skill_improvement_process_recovery.py -q`
Expected: PASS; retry/restart produces one candidate and no duplicate feedback/outbox event.

- [ ] **Step 6: Commit provenance-aware skill improvement**

```bash
git add packages/agent/skills packages/agent/migrations/010_founder_asset_provenance.sql \
  packages/agent/migrations/010_founder_asset_provenance.down.sql \
  apps/cosa/skills/improvement_service.py tests/agent/skills \
  tests/e2e/test_skill_improvement_process_recovery.py
git commit -m "feat(skills): bind improvement evidence to project manifests"
```

### Task 6: Bridge Company commands to Agent authoring through signed outbox callbacks

**Files:**
- Create: `services/company/operations/services/founder-asset-authoring.service.ts`
- Create: `services/company/operations/handlers/founder-asset-authoring.handler.ts`
- Modify: `services/company/events/outbox-relay.service.ts`
- Modify: `services/company/operations/handlers/index.ts`
- Modify: `apps/cosa/events/router.py`
- Create: `apps/cosa/events/founder_asset_events.py`
- Test: `services/company/operations/tests/founder-asset-authoring.service.test.ts`
- Test: `tests/apps/cosa/events/test_founder_asset_events.py`

**Interfaces:**
- Consumes Company founder-human authorization and Tasks 1–4.
- Produces signed events `founder.asset.commanded.v1` and `founder.asset.status.v1`, each with correlation/idempotency IDs and opaque asset refs.
- Tasks 7 and 13 consume Company read projection; no browser calls Agent Platform directly.

- [ ] **Step 1: Write failing outbox idempotency and callback tests**

```ts
it("records one Company command and one outbox row for an idempotency key", async () => {
  await requestAssetClone(founderCtx, cloneInput);
  await requestAssetClone(founderCtx, cloneInput);
  expect(await pendingOutbox("founder.asset.commanded.v1")).toHaveLength(1);
});
```

```python
async def test_replayed_signed_command_does_not_create_second_asset(router, envelope):
    first = await router.handle(envelope)
    second = await router.handle(envelope)
    assert second.status == "duplicate"
```

- [ ] **Step 2: Run tests and confirm routing is absent**

Run: `cd services/company && encore test --prepare tests/founder-asset-authoring.service.test.ts`
Expected: FAIL because `requestAssetClone` is missing.

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/events/test_founder_asset_events.py -q`
Expected: FAIL because event routing is missing.

- [ ] **Step 3: Implement Company command receipt and event payload**

The Company command transaction verifies a HUMAN founder, writes `founder_asset_events`, generates a stable `command_id`, then writes the existing signed outbox. Payload is camelCase at Company boundary and converted once in `founder_asset_events.py`; it contains no body secret or raw prompt:

```json
{
  "commandId": "opaque",
  "workspaceId": "...",
  "projectId": "... or null",
  "assetKind": "AGENT|SKILL|WORKFLOW",
  "operation": "CREATE|CLONE|EDIT_DRAFT|EVALUATE|PUBLISH|RETIRE",
  "assetRef": {"assetId": "...", "version": "...", "definitionHash": "..."},
  "expectedVersion": 3,
  "idempotencyKey": "..."
}
```

- [ ] **Step 4: Implement Agent receiver and status callback**

Verify the existing signature before dispatch. Persist incoming command idempotently before work, invoke Task 4 authoring service, then emit `founder.asset.status.v1` with lifecycle, hashes, evaluation summary and safe reason code. Company callback validates workspace, command ID and expected state before updating its projection and appending an audit event.

- [ ] **Step 5: Run both-plane contract tests**

Run: `cd services/company && encore test --prepare tests/founder-asset-authoring.service.test.ts`
Expected: PASS.

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/events/test_founder_asset_events.py -q`
Expected: PASS, including bad signature, foreign workspace, stale callback and duplicate delivery.

- [ ] **Step 6: Commit the cross-plane authoring bridge**

```bash
git add services/company/operations/services/founder-asset-authoring.service.ts \
  services/company/operations/handlers/founder-asset-authoring.handler.ts \
  services/company/events/outbox-relay.service.ts services/company/operations/handlers/index.ts \
  apps/cosa/events/router.py apps/cosa/events/founder_asset_events.py \
  services/company/operations/tests/founder-asset-authoring.service.test.ts \
  tests/apps/cosa/events/test_founder_asset_events.py
git commit -m "feat: relay founder asset commands across planes"
```

### Task 7: Create WorkspaceAgent identity and compatibility path for legacy project profiles

**Files:**
- Modify: `services/company/operations/services/ai-member.service.ts`
- Modify: `services/company/operations/services/project-startup-team.service.ts`
- Modify: `services/company/operations/services/executive-role-activation.service.ts`
- Create: `services/company/operations/services/founder-agent-compatibility.service.ts`
- Test: `services/company/operations/tests/founder-agent-compatibility.service.test.ts`
- Test: `services/company/operations/tests/project-startup-team.service.test.ts`

**Interfaces:**
- Consumes Company deployment tables and an exact published Agent Platform identity from Task 6.
- Produces `ensureAiWorkforceMemberForAsset`, `resolveProjectAgentAuthorityV2`, and a feature-gated dual-read adapter.
- Existing Startup Team/Executive Board callers remain compatible until Task 18 cutover.

- [ ] **Step 1: Write failing custom-agent workforce tests**

```ts
it("creates one AI workforce member for a published custom agent asset", async () => {
  const first = await ensureAiWorkforceMemberForAsset(tx, ws, customSpec);
  const second = await ensureAiWorkforceMemberForAsset(tx, ws, customSpec);
  expect(second).toEqual(first);
});

it("uses V2 deployment authority only when the feature is enabled", async () => {
  expect(await resolveProjectAgentAuthorityV2(ctx, legacyProfile)).toMatchObject({ source: "legacy" });
});
```

- [ ] **Step 2: Run tests and verify the generic asset identity path is absent**

Run: `cd services/company && encore test --prepare tests/founder-agent-compatibility.service.test.ts`
Expected: FAIL because `ensureAiWorkforceMemberForAsset` is absent.

- [ ] **Step 3: Generalize AI workforce-member creation without weakening existing mappings**

Add `ensureAiWorkforceMemberForAsset(tx, workspaceId, {specId, specVersion, definitionHash, title})`. It queries the exact workspace/spec/hash tuple and creates an `AI_AGENT` only when absent. Retain `ensureAiWorkforceMember` and `AGENT_PROFILE_SPEC_*` as built-in compatibility wrappers; do not replace their hash pins or use a string fallback.

- [ ] **Step 4: Add feature-gated dual read**

`resolveProjectAgentAuthorityV2` first reads an active `project_agent_deployments` row and validates its workspace agent/version hash. While `FOUNDER_CONFIGURABLE_ASSETS_MODE=SHADOW`, it compares that result with `project_agent_assignments`, logs a redacted mismatch event and executes legacy behavior. `ENFORCED` uses V2 only after Task 18 evidence. The Executive Board must still require an active underlying deployment; it must not turn a custom role into authority.

- [ ] **Step 5: Run compatibility and executive regression tests**

Run: `cd services/company && encore test --prepare tests/founder-agent-compatibility.service.test.ts tests/project-startup-team.service.test.ts tests/executive-role-activation.service.test.ts`
Expected: PASS; no existing profile behavior changes in `SHADOW`.

- [ ] **Step 6: Commit compatibility support**

```bash
git add services/company/operations/services/ai-member.service.ts \
  services/company/operations/services/project-startup-team.service.ts \
  services/company/operations/services/executive-role-activation.service.ts \
  services/company/operations/services/founder-agent-compatibility.service.ts \
  services/company/operations/tests/founder-agent-compatibility.service.test.ts \
  services/company/operations/tests/project-startup-team.service.test.ts
git commit -m "feat(company): bridge workspace agents to project profiles"
```

### Task 8: Persist workflow definitions, bindings and execution manifests durably

**Files:**
- Create: `packages/agent/workflows/postgres_repository.py`
- Create: `packages/agent/workflows/manifest.py`
- Modify: `packages/agent/workflows/repository.py`
- Modify: `packages/agent/workflows/models.py`
- Modify: `packages/agent/runs/models.py`
- Modify: `packages/agent/runs/repository.py`
- Create: `packages/agent/migrations/011_workflow_manifest_persistence.sql`
- Create: `packages/agent/migrations/011_workflow_manifest_persistence.down.sql`
- Test: `tests/agent/workflows/test_postgres_repository.py`
- Test: `tests/agent/workflows/test_manifest.py`

**Interfaces:**
- Produces `PostgresWorkflowDefinitionRepository`, `GovernedWorkflowRunManifest`, `WorkflowRunRecord`, and durable step records keyed by `run_id`.
- Tasks 9–12 depend on exact workflow version/hash and manifest retrieval across restart.

- [ ] **Step 1: Write failing restart and immutable-version tests**

```python
async def test_postgres_workflow_definition_survives_repository_restart(factory):
    first = PostgresWorkflowDefinitionRepository(factory)
    saved = await first.save_definition(workflow_spec().with_hash())
    second = PostgresWorkflowDefinitionRepository(factory)
    assert (await second.get_by_hash(saved.definition_hash)).spec_data == saved.spec_data

async def test_manifest_is_insert_once_and_contains_project_scope(repo):
    manifest = await repo.create_manifest(make_manifest(project_id="p-1"))
    assert manifest.project_id == "p-1"
    with pytest.raises(ManifestConflictError):
        await repo.create_manifest(make_manifest(run_id=manifest.run_id, project_id="p-2"))
```

- [ ] **Step 2: Run tests and confirm no Postgres repository exists**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/workflows/test_postgres_repository.py tests/agent/workflows/test_manifest.py -q`
Expected: FAIL because `PostgresWorkflowDefinitionRepository` and manifest contract are absent.

- [ ] **Step 3: Add durable tables and repository implementation**

Add `agent.workflow_definitions`, `agent.workflow_execution_manifests` and `agent.workflow_step_records`. Definition keys are `(workspace_id, workflow_asset_id, version)` with definition hash unique per asset/workspace. Manifest contains project ID, role/project agent deployment opaque IDs, exact agent/skill/workflow pins, policy epoch/hash, capability allowlist, budget, trigger/correlation ID and redacted evidence refs. Step records store status, checkpoint ref, input/output hashes and safe error code; they do not store raw prompt/secret.

- [ ] **Step 4: Make `WorkflowDefinitionRepository` production-safe**

Keep `InMemoryWorkflowDefinitionRepository` for unit tests only. Composition must receive `PostgresWorkflowDefinitionRepository` when a database session exists; production startup fails closed if configured workflow authoring/run is enabled without it.

- [ ] **Step 5: Run durable repository tests**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/workflows/test_postgres_repository.py tests/agent/workflows/test_manifest.py -q`
Expected: PASS against disposable PostgreSQL; a process/repository restart reads the same definition and manifest hash.

- [ ] **Step 6: Commit durable workflow persistence**

```bash
git add packages/agent/workflows packages/agent/runs \
  packages/agent/migrations/011_workflow_manifest_persistence.sql \
  packages/agent/migrations/011_workflow_manifest_persistence.down.sql \
  tests/agent/workflows/test_postgres_repository.py tests/agent/workflows/test_manifest.py
git commit -m "feat(workflows): persist definitions and execution manifests"
```

### Task 9: Make workflow validation typed and reject all unimplemented node semantics

**Files:**
- Modify: `packages/agent/workflows/schema.py`
- Create: `packages/agent/workflows/validation.py`
- Modify: `packages/agent/workflows/engine.py`
- Test: `tests/agent/workflows/test_schema.py`
- Test: `tests/agent/workflows/test_validation.py`
- Test: `tests/agent/workflows/test_engine.py`

**Interfaces:**
- Produces `WorkflowPublishValidator.validate(spec, context)` and `UnsupportedWorkflowStepError`.
- Task 10 registers concrete builders; Task 16 consumes validation results for the canvas.

- [ ] **Step 1: Write failing invalid-graph and unsupported-node tests**

```python
def test_agent_step_requires_project_agent_deployment_pin():
    with pytest.raises(ValueError, match="project_agent_deployment_id"):
        WorkflowSpec.model_validate(agent_step_without_deployment())

async def test_engine_rejects_unregistered_step_type_instead_of_noop():
    with pytest.raises(UnsupportedWorkflowStepError):
        await WorkflowEngine().execute_spec(unimplemented_router_spec(), {})
```

- [ ] **Step 2: Run tests and confirm current fallback behavior fails the expectation**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/workflows/test_validation.py tests/agent/workflows/test_engine.py -q`
Expected: FAIL because unsupported step types currently compile to an empty deterministic step.

- [ ] **Step 3: Define V1 publishable node contracts**

V1 node types are `AGENT`, `TOOL_CALL`, `APPROVAL_GATE`, `DETERMINISTIC` with a registered deterministic handler, `RETRY` with max attempts/backoff, and compensation via existing `on_failure`. Parallelism is encoded by independent DAG dependencies and join output schema; no free-form router or loop is publishable. `AGENT` requires `project_agent_deployment_id`, exact agent identity and typed input/output schema. `TOOL_CALL` requires catalog capability, project scope, idempotency key template and risk class. `APPROVAL_GATE` requires a structured subject and checkpoint binding.

- [ ] **Step 4: Implement two-level validation**

`WorkflowSpec` validates structure: IDs, dependency graph, unique ports, schema-compatible edges, bounded retry and compensation. `WorkflowPublishValidator` validates context: referenced deployment/workflow assets exist in the same workspace/project, are published/active, skills are exact-pinned, capability is allowlisted, and every effect has an approval or policy-approved low-risk decision. Reject any node for which no executor has registered an implementation identity. Keep the Task 4 `WORKFLOW_PUBLISH_DISABLED` response until Task 10 registers every V1 executor and wires this validator into authoring publication.

- [ ] **Step 5: Remove the no-op fallback**

Replace the final `else` in `WorkflowEngine.build_steps_from_spec()` with `UnsupportedWorkflowStepError(step_spec.id, step_spec.type)`. `DETERMINISTIC` must resolve a whitelisted handler ID rather than execute a generic no-op.

- [ ] **Step 6: Run workflow unit tests**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/workflows/test_schema.py tests/agent/workflows/test_validation.py tests/agent/workflows/test_engine.py -q`
Expected: PASS; invalid graph and unavailable node fail before a run is created.

- [ ] **Step 7: Commit typed workflow validation**

```bash
git add packages/agent/workflows/schema.py packages/agent/workflows/validation.py \
  packages/agent/workflows/engine.py tests/agent/workflows/test_schema.py \
  tests/agent/workflows/test_validation.py tests/agent/workflows/test_engine.py
git commit -m "feat(workflows): validate publishable node semantics"
```

### Task 10: Implement real Agent, capability, approval and retry workflow executors

**Files:**
- Create: `packages/agent/workflows/agent_step.py`
- Create: `packages/agent/workflows/retry_step.py`
- Create: `packages/agent/workflows/deterministic_handlers.py`
- Modify: `packages/agent/workflows/engine.py`
- Modify: `apps/cosa/assets/authoring_service.py`
- Modify: `apps/cosa/assets/evaluation_service.py`
- Modify: `apps/cosa/composition/workflow_orchestration.py`
- Modify: `apps/cosa/composition/agent_plane.py`
- Test: `tests/agent/workflows/test_agent_step.py`
- Test: `tests/agent/workflows/test_retry_step.py`
- Test: `tests/agent/workflows/test_executor_registration.py`

**Interfaces:**
- Consumes Task 8 manifest repository and Task 9 validated specs.
- Produces registered executor map for all V1 node types. Agent tasks call the normal kernel/run path using exact spec/skill pins; effects continue through `CapabilityGateway`.
- Task 11 dispatches these executors from Worker.

- [ ] **Step 1: Write failing executor tests**

```python
async def test_agent_step_uses_manifest_pinned_spec_and_project_deployment(fake_kernel):
    outcome = await AgentWorkflowStep(resolver, fake_kernel).run(state_for_manifest())
    assert fake_kernel.request.root_executable_ref.definition_hash == AGENT_HASH
    assert fake_kernel.request.workspace_id == "ws-1"
    assert fake_kernel.request.metadata["project_id"] == "p-1"

async def test_retry_stops_at_declared_limit():
    step = RetryWorkflowStep(failing_handler, max_attempts=2)
    assert (await step.run({})).status == StepStatus.FAILED
    assert failing_handler.calls == 2
```

- [ ] **Step 2: Run tests and confirm executor classes are absent**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/workflows/test_agent_step.py tests/agent/workflows/test_retry_step.py -q`
Expected: FAIL during import.

- [ ] **Step 3: Implement AgentWorkflowStep**

Resolve the manifest's `project_agent_deployment_id` against a live Company authority endpoint before kernel invocation. Verify returned workspace/project, deployment state and exact `{spec_id, version, definition_hash}` match the manifest. Resolve skills through the scoped resolver; on a retired/mismatched dependency fail with a safe reason before model invocation. Use the existing kernel factory and RunRecord rather than creating a second model execution path.

- [ ] **Step 4: Implement explicit registered handlers**

`GatewayToolCallStep` remains the sole effect executor. `ApprovalGateStep` receives manifest hash and checkpoint reference. `RetryWorkflowStep` persists attempt count in the workflow state/checkpoint and enforces bounded exponential backoff. Deterministic handlers are registered by stable ID, receive typed JSON values and cannot execute IO.

- [ ] **Step 5: Register builders in composition and test unknown builder rejection**

`WorkflowOrchestration.execute_manifest()` obtains builders from the explicit registry; it must never create `{step.id: generic_builder}` for all input steps. Startup exposes health/readiness of each registered executor for the palette service. Once every V1 executor is registered, call `WorkflowPublishValidator` from Task 9 inside the Task 4 authoring service and permit only a validated `REVIEW_REQUIRED` workflow to move to `PUBLISHED` under a signed Founder command.

- [ ] **Step 6: Run executor tests**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/workflows/test_agent_step.py tests/agent/workflows/test_retry_step.py tests/agent/workflows/test_executor_registration.py -q`
Expected: PASS; no executor means validation failure, not a completed no-op run.

- [ ] **Step 7: Commit concrete V1 executors**

```bash
git add packages/agent/workflows apps/cosa/assets/authoring_service.py \
  apps/cosa/assets/evaluation_service.py apps/cosa/composition/agent_plane.py \
  apps/cosa/composition/workflow_orchestration.py tests/agent/workflows/test_agent_step.py \
  tests/agent/workflows/test_retry_step.py tests/agent/workflows/test_executor_registration.py
git commit -m "feat(workflows): execute pinned agent workflow steps"
```

### Task 11: Dispatch governed workflow runs through scheduler, resume and live authority

**Files:**
- Create: `apps/cosa/worker/governed_workflow_run.py`
- Modify: `apps/cosa/worker/main.py`
- Modify: `apps/cosa/events/router.py`
- Modify: `apps/cosa/company/executive_board_client.py` or create `apps/cosa/company/project_deployment_client.py`
- Modify: `packages/agent/runs/models.py`
- Test: `tests/apps/cosa/worker/test_governed_workflow_run.py`
- Test: `tests/apps/cosa/events/test_governed_workflow_trigger.py`
- Test: `tests/e2e/test_unified_approval_process_recovery.py`

**Interfaces:**
- Consumes manifest/executors from Tasks 8–10 and Company deployment authority from Task 2.
- Produces task type `governed_workflow_run`, durable checkpoint/resume behavior and Project Activity-compatible event records.
- Task 15 reads run events; Task 18 runs process E2E.

- [ ] **Step 1: Write failing worker dispatch tests**

```python
async def test_worker_dispatches_governed_workflow_task_to_real_handler(plane, claimed_task):
    result = await dispatch_claimed_task(plane, claimed_task("governed_workflow_run"))
    assert result["status"] == "completed"

async def test_revoked_project_agent_blocks_effect_after_resume(plane, manifest):
    await pause_project_deployment(manifest.project_agent_deployment_id)
    assert (await execute_governed_workflow_run(plane, manifest)).status == "failed"
```

- [ ] **Step 2: Run tests and confirm the task type is unknown**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/worker/test_governed_workflow_run.py -q`
Expected: FAIL because `governed_workflow_run` is not dispatched.

- [ ] **Step 3: Implement event-to-scheduler path**

The signed Company event contains `workspace_id`, `project_id`, workflow binding ID, manifest reference, correlation ID and idempotency key. Router verifies signature/scope, creates one scheduler task using a coalescing key based on run ID, and records ignored/disabled outcomes truthfully. `worker/main.py` explicitly dispatches only `governed_workflow_run` to the new handler.

- [ ] **Step 4: Build/load manifest exactly once and re-authorize at every effect**

At start, create a `RunRecord` and insert the manifest once. At resume, load that same manifest; never resolve latest asset. Before `AgentWorkflowStep`, approval continuation and `GatewayToolCallStep`, fetch live Company deployment/grant/policy epoch. A mismatch, pause/revoke, missing project or expired ticket fails closed and appends a safe run event.

- [ ] **Step 5: Run worker/recovery tests**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/worker/test_governed_workflow_run.py tests/apps/cosa/events/test_governed_workflow_trigger.py tests/e2e/test_unified_approval_process_recovery.py -q`
Expected: PASS; duplicate trigger makes one run, restart resumes pinned state and revoked deployment blocks the pending effect.

- [ ] **Step 6: Commit governed worker dispatch**

```bash
git add apps/cosa/worker/governed_workflow_run.py apps/cosa/worker/main.py \
  apps/cosa/events/router.py apps/cosa/company packages/agent/runs/models.py \
  tests/apps/cosa/worker/test_governed_workflow_run.py \
  tests/apps/cosa/events/test_governed_workflow_trigger.py \
  tests/e2e/test_unified_approval_process_recovery.py
git commit -m "feat(worker): dispatch governed workflow manifests"
```

### Task 12: Add Company read projections and typed public Founder commands

**Files:**
- Create: `services/company/operations/services/founder-asset-query.service.ts`
- Create: `services/company/operations/handlers/founder-asset.handler.ts`
- Modify: `services/company/operations/handlers/index.ts`
- Modify: `services/company/operations/api.ts`
- Modify: `shared/contracts/mvp-surface.json`
- Modify: `services/company/shared/contracts/mvp-surface.generated.ts`
- Modify: `apps/cosa/api/mvp_contracts_generated.py`
- Modify: `frontend/lib/core/network/mvp_endpoints.g.dart`
- Test: `services/company/operations/tests/founder-asset.handler.test.ts`
- Test: `shared/contracts/tests/mvp-surface.test.mjs`

**Interfaces:**
- Produces Founder-facing Company endpoints: library, clone/create/edit draft/evaluate/publish, Project deploy/pause/bind, workflow validate/run and Project timeline read.
- Frontend Tasks 13–16 use only generated `MvpEndpoint` members.

- [ ] **Step 1: Write failing endpoint contract tests**

```ts
it("does not expose direct built-in edit route", () => {
  expect(MVP_SURFACE.routes).not.toContainEqual(expect.objectContaining({ path: expect.stringContaining("/builtins/:id") }));
});

it("requires projectId for workflow run command", async () => {
  await expect(startWorkflow({ workflowAssetId: "wf-1" })).rejects.toMatchObject({ code: "invalid_argument" });
});
```

- [ ] **Step 2: Run contract tests and confirm endpoint identifiers are absent**

Run: `node --test shared/contracts/tests/mvp-surface.test.mjs`
Expected: FAIL because founder asset endpoint IDs are absent.

- [ ] **Step 3: Define typed route inventory and request/response DTOs**

Add only these public routes, all under Company `operations` and all requiring `X-Workspace-Id` plus authenticated principal:

```text
GET  /operations/founder-assets
POST /operations/founder-assets/drafts
POST /operations/founder-assets/:assetId/clones
PATCH /operations/founder-assets/:assetId/drafts/:version
POST /operations/founder-assets/:assetId/drafts/:version/evaluations
POST /operations/founder-assets/:assetId/drafts/:version/publications
GET  /operations/projects/:projectId/founder-deployments
POST /operations/projects/:projectId/founder-deployments
POST /operations/projects/:projectId/workflow-bindings/:bindingId/runs
GET  /operations/projects/:projectId/agent-timeline
```

The response exposes origin/version/hash, lifecycle, evaluation summary, safe reason, deployments and redacted evidence references. It never returns raw secret, full model context or unredacted skill body outside Founder-authorized draft editor.

- [ ] **Step 4: Implement handlers as Company commands/query projections**

Create/clone/edit/evaluate/publish create or query Task 6 command/status projections; they do not invoke Agent Platform via browser request. Commands require `expectedVersion`, `reason` and `idempotencyKey`. Queries derive workspace from auth context, validate Project belongs to it, then return `MvpSuccess` source refs.

- [ ] **Step 5: Regenerate contracts and run Company/frontend boundary checks**

Run: `node scripts/gen-mvp-contracts.mjs`
Expected: generated TypeScript/Dart endpoint files include exactly the new IDs.

Run: `node --test shared/contracts/tests/mvp-surface.test.mjs && make contract-freeze-check && make frontend-api-contract-check`
Expected: PASS.

- [ ] **Step 6: Commit public command/read surface**

```bash
git add services/company/operations/services/founder-asset-query.service.ts \
  services/company/operations/handlers/founder-asset.handler.ts \
  services/company/operations/handlers/index.ts services/company/operations/api.ts \
  shared/contracts/mvp-surface.json services/company/shared/contracts/mvp-surface.generated.ts \
  apps/cosa/api/mvp_contracts_generated.py \
  frontend/lib/core/network/mvp_endpoints.g.dart \
  services/company/operations/tests/founder-asset.handler.test.ts \
  shared/contracts/tests/mvp-surface.test.mjs
git commit -m "feat(api): expose governed founder asset commands"
```

### Task 13: Build Flutter Founder Asset Library and clone-only editor

**Files:**
- Create: `frontend/lib/modules/founder_workforce/models/founder_asset_models.dart`
- Create: `frontend/lib/modules/founder_workforce/services/founder_asset_service.dart`
- Create: `frontend/lib/modules/founder_workforce/controllers/founder_asset_library_controller.dart`
- Create: `frontend/lib/modules/founder_workforce/views/founder_asset_library_view.dart`
- Create: `frontend/test/modules/founder_workforce/founder_asset_service_test.dart`
- Create: `frontend/test/modules/founder_workforce/founder_asset_library_view_test.dart`
- Modify: `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart`

**Interfaces:**
- Consumes Task 12 `MvpEndpoint` commands only via `MvpRequestClient`.
- Produces a Founder-only asset library showing built-in/clone/custom origin, exact version/hash/lifecycle and safe command errors.
- Task 14 links Project deployment; Task 15 opens workflow draft builder.

- [ ] **Step 1: Write failing service and widget tests**

```dart
test('clone sends only the generated endpoint and expected version', () async {
  await service.cloneAsset(assetId: 'builtin.finance', expectedVersion: 3, reason: 'project variant');
  expect(fakeClient.lastEndpoint, MvpEndpoint.founderAssetClone);
});

testWidgets('built-in card has Clone and never Edit/Delete actions', (tester) async {
  await tester.pumpWidget(testApp(asset: builtinAsset));
  expect(find.text('Clone'), findsOneWidget);
  expect(find.text('Chỉnh sửa'), findsNothing);
});
```

- [ ] **Step 2: Run tests and confirm module absence**

Run: `cd frontend && flutter test test/modules/founder_workforce/founder_asset_service_test.dart test/modules/founder_workforce/founder_asset_library_view_test.dart`
Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement models and service with no raw URL construction**

Decode `originKind`, origin identity, lifecycle, evaluation summary and safe status. Service calls `MvpRequestClient.request` and passes project ID only when server says the target is a sandbox/Project operation. Do not cache authority locally or infer that a built-in became editable after a failed request.

- [ ] **Step 4: Implement truthful clone-only UX**

Built-in cards show `Built-in · read-only`, pin/version/hash, dependency/evaluation status and a `Clone` action. Custom Draft cards show edit/evaluate/publish only when server lifecycle permits. A failed command renders the exact safe error from API and refreshes the authoritative list; it does not optimistically change lifecycle.

- [ ] **Step 5: Run Flutter tests and analyzer**

Run: `cd frontend && flutter test test/modules/founder_workforce/founder_asset_service_test.dart test/modules/founder_workforce/founder_asset_library_view_test.dart`
Expected: PASS.

Run: `flutter analyze --no-pub`
Expected: no new diagnostics.

- [ ] **Step 6: Commit the asset library**

```bash
git add frontend/lib/modules/founder_workforce frontend/test/modules/founder_workforce \
  frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart
git commit -m "feat(frontend): add founder asset clone library"
```

### Task 14: Build Project deployment and sandbox configuration experience

**Files:**
- Create: `frontend/lib/modules/founder_workforce/controllers/project_deployment_controller.dart`
- Create: `frontend/lib/modules/founder_workforce/views/project_deployment_view.dart`
- Create: `frontend/test/modules/founder_workforce/project_deployment_view_test.dart`
- Modify: `frontend/lib/modules/founder_workforce/services/founder_asset_service.dart`
- Modify: `frontend/lib/modules/founder_workforce/models/founder_asset_models.dart`

**Interfaces:**
- Consumes Task 12 Project deployment command/read endpoints.
- Produces an explicit Project-bound deployment screen; it cannot invoke a workflow/run without Project context.
- Task 15 uses active deployment IDs only as form inputs, never as client authority.

- [ ] **Step 1: Write failing Project-context tests**

```dart
testWidgets('run controls remain unavailable without selected Project', (tester) async {
  await tester.pumpWidget(testApp(projectId: null));
  expect(find.text('Chọn Project để triển khai'), findsOneWidget);
  expect(find.byKey(const Key('start-workflow')), findsNothing);
});

test('pause sends project deployment expected version', () async {
  await controller.pause(deploymentId: 'dep-1', expectedVersion: 4, reason: 'scope changed');
  expect(fakeClient.lastBody['expectedVersion'], 4);
});
```

- [ ] **Step 2: Run the widget test and confirm controller/view absence**

Run: `cd frontend && flutter test test/modules/founder_workforce/project_deployment_view_test.dart`
Expected: FAIL during import.

- [ ] **Step 3: Implement deployment controller and view**

Show Role → Agent → Workflow bindings, effective capability summary, knowledge/evidence refs, budget, lifecycle and last server event. Actions are deploy, bind, pause and open Draft sandbox; each requires server-supplied current version and a non-empty Founder reason. Never offer a capability checkbox that can widen Company policy.

- [ ] **Step 4: Add sandbox boundary messaging**

Project sandbox creates only `PROJECT_SANDBOX` asset drafts. The UI labels it `Không có side effect`, hides external capability controls and explains that promotion requires evaluation/review before Workspace reuse.

- [ ] **Step 5: Run tests and analyzer**

Run: `cd frontend && flutter test test/modules/founder_workforce/project_deployment_view_test.dart`
Expected: PASS, including missing Project, pause conflict and sandbox message.

Run: `flutter analyze --no-pub`
Expected: no new diagnostics.

- [ ] **Step 6: Commit Project deployment UI**

```bash
git add frontend/lib/modules/founder_workforce frontend/test/modules/founder_workforce/project_deployment_view_test.dart
git commit -m "feat(frontend): configure project agent deployments"
```

### Task 15: Deliver the guarded workflow canvas in Draft-only mode

**Files:**
- Create: `frontend/lib/modules/founder_workforce/models/workflow_graph_models.dart`
- Create: `frontend/lib/modules/founder_workforce/controllers/workflow_builder_controller.dart`
- Create: `frontend/lib/modules/founder_workforce/views/workflow_builder_view.dart`
- Create: `frontend/lib/modules/founder_workforce/views/workflow_node_inspector.dart`
- Create: `frontend/test/modules/founder_workforce/workflow_builder_controller_test.dart`
- Create: `frontend/test/modules/founder_workforce/workflow_builder_view_test.dart`
- Modify: `frontend/lib/modules/founder_workforce/services/founder_asset_service.dart`

**Interfaces:**
- Consumes Task 9 validation result and Task 12 draft/evaluate/publish routes.
- Produces a graph editor for Draft JSON only. Server returns authoritative diagnostics; client-side rules are usability hints, not publish authority.

- [ ] **Step 1: Write failing graph editor tests**

```dart
test('rejects a local edge when port schemas differ', () {
  final result = controller.connect('agent.output', 'approval.subject');
  expect(result.localErrorCode, 'PORT_SCHEMA_MISMATCH');
});

testWidgets('unavailable node cannot be dragged into the graph', (tester) async {
  await tester.pumpWidget(testBuilder(nodeCatalog: [unavailableAgentNode]));
  expect(find.byKey(const Key('palette-node-agent-unavailable')), findsOneWidget);
  expect(tester.getSemantics(find.byKey(const Key('palette-node-agent-unavailable'))).hasAction(SemanticsAction.tap), isFalse);
});
```

- [ ] **Step 2: Run tests and confirm builder files are absent**

Run: `cd frontend && flutter test test/modules/founder_workforce/workflow_builder_controller_test.dart test/modules/founder_workforce/workflow_builder_view_test.dart`
Expected: FAIL during import.

- [ ] **Step 3: Implement graph model and palette restrictions**

Represent nodes, typed ports, edges and graph revision as pure DTOs. Palette shows only Task 10 registered executor identities from server: Agent Task, Capability, Approval, Deterministic transform, Retry and compensation. Parallel execution derives from independent dependencies; do not add an arbitrary loop/router/custom-code node. The client blocks obvious cycles/type mismatch but always submits graph revision to server validation.

- [ ] **Step 4: Implement Draft save, simulation and publish gates**

Save uses optimistic `expectedVersion`; conflict reloads server draft rather than merge blindly. Simulation displays structured validation/evaluation results, selected Project deployments, missing grants and approval requirements. Publish is disabled until server returns `REVIEW_REQUIRED` with passing evaluation and explicit Founder command confirmation.

- [ ] **Step 5: Run widget tests and analyzer**

Run: `cd frontend && flutter test test/modules/founder_workforce/workflow_builder_controller_test.dart test/modules/founder_workforce/workflow_builder_view_test.dart`
Expected: PASS; unavailable or invalid graph never appears publishable.

Run: `flutter analyze --no-pub`
Expected: no new diagnostics.

- [ ] **Step 6: Commit guarded Draft canvas**

```bash
git add frontend/lib/modules/founder_workforce frontend/test/modules/founder_workforce/workflow_builder_controller_test.dart \
  frontend/test/modules/founder_workforce/workflow_builder_view_test.dart
git commit -m "feat(frontend): author governed workflow drafts"
```

### Task 16: Add Project run timeline, feedback and improvement visibility

**Files:**
- Create: `frontend/lib/modules/founder_workforce/controllers/agent_timeline_controller.dart`
- Create: `frontend/lib/modules/founder_workforce/views/agent_timeline_view.dart`
- Create: `frontend/test/modules/founder_workforce/agent_timeline_view_test.dart`
- Modify: `services/company/operations/services/founder-asset-query.service.ts`
- Modify: `apps/cosa/project_activity/service.py` or the existing Project Activity projector
- Modify: `packages/agent/project_activity/models.py`
- Test: `tests/apps/cosa/project_activity/test_founder_asset_projection.py`

**Interfaces:**
- Consumes run/manifests/skill observation events from Tasks 5 and 11.
- Produces durable redacted Project activity and feedback controls, keyed by real run and version/hash.
- Task 18 validates Last-Event-ID/replay and no mock state.

- [ ] **Step 1: Write failing projection and widget tests**

```python
async def test_skill_feedback_projection_has_exact_run_project_and_hash(projector):
    event = await projector.project(skill_observation_event())
    assert event.project_id == "p-1"
    assert event.payload["definition_hash"] == SKILL_HASH
```

```dart
testWidgets('timeline renders a server paused state without claiming completion', (tester) async {
  await tester.pumpWidget(testTimeline(events: [waitingApprovalEvent]));
  expect(find.text('Đang chờ phê duyệt'), findsOneWidget);
  expect(find.text('Hoàn tất'), findsNothing);
});
```

- [ ] **Step 2: Run tests and confirm founder-asset events have no projection**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/project_activity/test_founder_asset_projection.py -q`
Expected: FAIL because the projector does not recognize the event.

Run: `cd frontend && flutter test test/modules/founder_workforce/agent_timeline_view_test.dart`
Expected: FAIL during import.

- [ ] **Step 3: Project only redacted durable events**

Project `asset.cloned`, `evaluation.completed`, `workflow.validated`, `workflow.run.started`, step/checkpoint/approval/tool result, run terminal state, feedback and improvement candidate events. Each projection references opaque asset/run IDs, version/hash and safe reason; never copies prompt, raw evidence, secret, connector response or internal policy payload.

- [ ] **Step 4: Implement feedback UI**

Feedback requires selected exact run/skill version/hash from the timeline. It submits a rating/reason/evidence reference and renders returned candidate status. It cannot “apply improvement”; only the Library can later show Founder-reviewed publish action.

- [ ] **Step 5: Run projection and Flutter tests**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/project_activity/test_founder_asset_projection.py -q`
Expected: PASS.

Run: `cd frontend && flutter test test/modules/founder_workforce/agent_timeline_view_test.dart`
Expected: PASS.

- [ ] **Step 6: Commit truthful timeline and feedback**

```bash
git add apps/cosa/project_activity packages/agent/project_activity \
  services/company/operations/services/founder-asset-query.service.ts \
  frontend/lib/modules/founder_workforce frontend/test/modules/founder_workforce/agent_timeline_view_test.dart \
  tests/apps/cosa/project_activity/test_founder_asset_projection.py
git commit -m "feat: show governed workflow timeline and feedback"
```

### Task 17: Add Hướng 3 readiness gate without enabling unrestricted canvas

**Files:**
- Create: `apps/cosa/workflows/readiness.py`
- Create: `apps/cosa/api/workflow_readiness_routes.py`
- Modify: `apps/cosa/api/app.py`
- Modify: `frontend/lib/modules/founder_workforce/services/founder_asset_service.dart`
- Modify: `frontend/lib/modules/founder_workforce/views/workflow_builder_view.dart`
- Test: `tests/apps/cosa/workflows/test_readiness.py`
- Test: `frontend/test/modules/founder_workforce/workflow_builder_view_test.dart`

**Interfaces:**
- Produces server-authoritative executor/readiness catalog: `AVAILABLE`, `UNAVAILABLE`, `SHADOW_ONLY` with a safe reason and required evidence.
- Hướng 3 canvas remains limited to catalog entries from this service; no client-defined node/tool exists.

- [ ] **Step 1: Write failing readiness tests**

```python
def test_agent_node_is_unavailable_without_durable_repository_and_executor():
    decision = WorkflowNodeReadiness.evaluate(deps_without_repository())
    assert decision.state == "UNAVAILABLE"
    assert decision.reason_code == "DURABLE_WORKFLOW_REPOSITORY_REQUIRED"
```

- [ ] **Step 2: Run test and confirm no readiness service exists**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/workflows/test_readiness.py -q`
Expected: FAIL during import.

- [ ] **Step 3: Implement readiness aggregation**

For each node type, require durable repository, registered executor, schema validator, dependency health, policy/approval support and its conformance test marker. Return `SHADOW_ONLY` for new nodes until Task 18 process proof marks them enabled by explicit workspace feature flag. Return `UNAVAILABLE` instead of a node that completes as no-op.

- [ ] **Step 4: Wire UI strictly to the readiness catalog**

The Flutter builder renders disabled entries with server reason; it has no local override, hidden developer mode or raw JSON action to create an unavailable node.

- [ ] **Step 5: Run readiness/unit/widget tests**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/workflows/test_readiness.py -q`
Expected: PASS.

Run: `cd frontend && flutter test test/modules/founder_workforce/workflow_builder_view_test.dart`
Expected: PASS.

- [ ] **Step 6: Commit Hướng 3 gate**

```bash
git add apps/cosa/workflows/readiness.py apps/cosa/api/workflow_readiness_routes.py apps/cosa/api/app.py \
  frontend/lib/modules/founder_workforce/services/founder_asset_service.dart \
  frontend/lib/modules/founder_workforce/views/workflow_builder_view.dart \
  tests/apps/cosa/workflows/test_readiness.py frontend/test/modules/founder_workforce/workflow_builder_view_test.dart
git commit -m "feat(workflows): gate founder canvas nodes by runtime readiness"
```

### Task 18: Run cutover evidence, enable controlled V1, and document rollback

**Files:**
- Create: `tests/e2e/test_founder_configurable_workflow.py`
- Create: `tests/e2e/test_founder_asset_cross_plane_process.py`
- Create: `docs/runbooks/founder-configurable-workflow-cutover.md`
- Modify: `docs/architecture/generated/company-usage-inventory.md` via its generator only
- Modify: `docs/superpowers/specs/2026-09-13-founder-configurable-agent-skill-workflow-design.md`
- Modify: `docs/superpowers/plans/2026-09-13-founder-configurable-agent-skill-workflow.md`

**Interfaces:**
- Consumes all previous tasks.
- Produces reproducible release evidence and a deliberate `SHADOW → ENFORCED` flag transition. No code path may declare production-ready before this task passes.

- [ ] **Step 1: Write disposable-PostgreSQL/process E2E cases**

```python
def test_clone_publish_deploy_run_revoke_blocks_pending_effect(process_stack):
    asset = process_stack.founder.clone_and_publish_builtin_skill()
    deployment = process_stack.founder.deploy(asset, project_id="p-1")
    run = process_stack.founder.start_workflow(deployment)
    process_stack.founder.pause(deployment)
    assert process_stack.await_terminal(run).safe_reason_code == "PROJECT_AGENT_DEPLOYMENT_PAUSED"

def test_project_sandbox_cannot_effect_or_leak_to_another_project(process_stack):
    draft = process_stack.founder.create_sandbox_skill(project_id="p-1")
    assert process_stack.start_sandbox(draft).status == "forbidden"
    assert process_stack.get_asset(workspace="ws", project_id="p-2", asset_id=draft.id).status_code == 404
```

- [ ] **Step 2: Run E2E red and verify missing required behavior**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/e2e/test_founder_configurable_workflow.py tests/e2e/test_founder_asset_cross_plane_process.py -q`
Expected: FAIL until all earlier tasks are complete.

- [ ] **Step 3: Execute full quality gates after E2E passes**

Run: `make lint typecheck-py boundary-check skillpacks-validate contract-freeze-check frontend-api-contract-check`
Expected: PASS.

Run: `make agent-test apps-cosa-test services-test frontend-test frontend-analyze check-docs`
Expected: PASS. If `check-docs` reports a pre-existing broken link, record exact path and create a separate repair commit; do not hide it with an allowlist.

Run: `make e2e-cross-plane-smoke` plus the two new process E2E files against disposable PostgreSQL.
Expected: PASS for clone-only denial, cross-workspace/project isolation, hash drift, stale CAS, duplicate delivery, restart/resume, approval mismatch, revoke after dispatch, no direct Company DB write and Flutter truthful errors.

- [ ] **Step 4: Write cutover and rollback runbook**

The runbook defines: backup/schema fingerprint; migration order Agent Platform → COSA → Company; default `FOUNDER_CONFIGURABLE_ASSETS_MODE=SHADOW`; required mismatch dashboards; Founder pilot Workspace allowlist; explicit change to `ENFORCED`; and rollback to `SHADOW`/disable flag without deleting published assets, audit, run, approval or manifest records. A rollback never re-enables legacy authority if a live high-risk approval/ticket fails.

- [ ] **Step 5: Regenerate derived inventory and update evidence status**

Run the official generator for `company-usage-inventory.md`; do not hand-edit it. Update the design/plan status only with command outputs and commit IDs. Mark any unavailable Hướng 3 node as `UNAVAILABLE` rather than implemented.

- [ ] **Step 6: Commit release evidence separately**

```bash
git add tests/e2e/test_founder_configurable_workflow.py \
  tests/e2e/test_founder_asset_cross_plane_process.py \
  docs/runbooks/founder-configurable-workflow-cutover.md \
  docs/architecture/generated/company-usage-inventory.md \
  docs/superpowers/specs/2026-09-13-founder-configurable-agent-skill-workflow-design.md \
  docs/superpowers/plans/2026-09-13-founder-configurable-agent-skill-workflow.md
git commit -m "test: prove founder configurable workflow cutover"
```

## Plan Self-Review

| Spec requirement | Implementing tasks |
|---|---|
| Built-ins read-only; Founder clone/edit/publish only | 3, 4, 6, 12, 13, 18 |
| Workspace role/agent/skill/workflow; Project deployment | 1, 2, 3, 7, 12, 14 |
| Exact hash/version, no floating references | 3, 4, 5, 8, 10, 11, 18 |
| Skill log/evaluate/improve, no auto-apply | 4, 5, 16, 18 |
| Typed flow with real execution | 8, 9, 10, 11 |
| Drag/drop founder canvas with server governance | 9, 12, 15, 17 |
| Capability/approval/live authorization | 2, 9, 10, 11, 18 |
| Durable audit/timeline | 1, 5, 8, 11, 16, 18 |
| Hướng 3 only after runtime evidence | 17, 18 |
| Additive migration, dual-read, rollback | 1, 7, 18 |

No task edits built-in content, sends direct browser requests to Agent Platform, creates a raw capability path, or claims a node runs before a real executor and process evidence exist.
