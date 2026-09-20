# Runtime Truth and Release Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Khôi phục tính đúng đắn của Project scope, Agent registry và release evidence để COSA chỉ chạy/hiển thị/truy vết dữ liệu có authority và provenance thực.

**Architecture:** Sửa P0 ở durable boundary trước: schedule legacy không được suy diễn Project; scheduled conversation/message phải inherit Project snapshot. Sau đó thay các danh sách AgentSpec phân tán bằng một source-owned catalog để startup registry fail-closed. Các release gates, UI DTO và capability status được sửa sau khi runtime scope/identity ổn định; Knowledge/Vault không được enable trong plan này.

**Tech Stack:** TypeScript/Encore + Drizzle, Python/FastAPI + pytest, Flutter/Dart, PostgreSQL, Make, JSON contract manifest.

**Spec:** `docs/superpowers/specs/2026-09-19-runtime-truth-and-release-recovery-design.md`

## Global Constraints

- Company Service là business truth; Agent Platform không được ghi business DB trực tiếp hoặc bypass Capability Gateway/Governance/Audit.
- Mọi business run mới require `workspace_id` và `project_id`; local active Project chỉ là UX, không phải authority.
- Legacy schedule thiếu Project phải `paused`/`needs_rebind`; tuyệt đối không chọn `projects[0]` hoặc suy diễn Project từ prompt/title/timestamp.
- `ProjectAgentRunAuthority` giữ trước compliance/kernel; fixture phải dựng authority hợp lệ, không nới production guard.
- Agent startup resolve exact version/hash của Prompt, ModelPolicy, AgentSpec và PinnedSkill; không fallback sang local Python object.
- Built-in asset vẫn clone-only; không mở API tự sửa/xóa built-in hay tự tăng authority.
- Money/invalid timestamps từ backend không được materialize thành `0.0`/`DateTime.now()`.
- Không claim semantic retrieval/Vault retrieval production-ready; `/agent/vault/retrieval/query` tiếp tục explicit unavailable cho đến workstream riêng.
- Không tạo worktree; làm trực tiếp `main`, preserve user changes, không commit/push nếu user chưa yêu cầu.

## Review Focus

- Legacy row có `project_id=NULL` khi Company API lỗi phải vẫn không thể dispatch, thay vì được auto-bound hay re-enabled.
- Payload mang Project B cho execution snapshot Project A phải fail trước conversation, compliance và kernel.
- Retry/restart phải dùng cùng Project snapshot và không tạo duplicate conversation/activity khác Project.
- `founder_assistant` (default Flutter profile) và CTO phải resolve registry identity thật ở cả API/worker startup.
- Flutter nhận money/date thiếu hoặc malformed phải render unavailable/invalid, không hiển thị 0 hay ngày hiện tại.

---

## File structure và dependency graph

```text
Task 1  Schedule legacy remediation repository/script
   └─> Task 2  Scheduled conversation/message scope propagation
        └─> Task 3  Process E2E scope/restart proof

Task 4  Canonical Agent catalog + exact registry startup validation
   └─> Task 5  Repair authority-aware test fixtures

Task 6  MVP manifest proof contract
Task 7  Frontend lifecycle boundary + scanner scope
Task 8  Workforce surface decision + truthful DTOs
   └─> Task 9  Full release gates and rollout evidence
```

| Area | Existing files | New files |
|---|---|---|
| Schedule scope | `services/cosa/scripts/backfill-schedule-project-ids.ts`, `services/cosa/services/schedule/schedule.repository.ts`, `services/cosa/services/workspace-schedule.service.ts`, `apps/cosa/worker/handlers.py` | `tests/e2e/test_schedule_project_scope_process.py` |
| Conversation persistence | `packages/agent/conversations/models.py`, `packages/agent/conversations/repository.py` | none |
| Agent registry | `apps/cosa/agents/specs.py`, `agent_profile_specs.py`, `seed.py` | `apps/cosa/agents/catalog.py` |
| Gate evidence | `shared/contracts/mvp-surface.json`, `scripts/mvp_surface_check.py`, `scripts/check_frontend_boundaries.mjs` | none |
| Experience truth | `frontend/lib/core/lifecycle/lifecycle_service.dart`, `frontend/lib/data/models/*.dart`, Founder Hub view/controller/service | `frontend/test/data/models/finance_legal_models_test.dart`, `frontend/test/data/models/commercial_models_test.dart` |

## Task 1: Fail-close legacy schedule remediation

**Files:**
- Modify: `services/cosa/scripts/backfill-schedule-project-ids.ts:1-76`
- Modify: `services/cosa/services/schedule/schedule.repository.ts:98-117`
- Modify: `services/cosa/services/workspace-schedule.service.ts:156-211`
- Modify: `services/cosa/tests/backfill-schedule-project-ids.test.ts:1-156`
- Modify: `services/cosa/tests/workspace-schedule.test.ts`

**Consumes:** Nullable legacy `workspace_schedule_definitions.project_id` from migration `005_add_schedule_project_scope.up.sql`.

**Produces:** A remediation function that never mutates `projectId` for a NULL legacy row, pauses it with a machine-readable reason, and returns an auditable summary.

- [ ] **Step 1: Write failing tests for the legacy state machine.**

  Replace the first-project test with the following test cases:

  ```ts
  it("pauses an unscoped legacy schedule without calling Company project list", async () => {
    const result = await backfillLegacyScheduleProjectIds("http://fake-company", "test-token");
    expect(fetchMock).not.toHaveBeenCalled();
    expect(result.pausedDefinitionIds).toEqual([id]);
    expect(row.projectId).toBeNull();
    expect(row.state).toBe("paused");
    expect(row.isLegacyUnscoped).toBe(true);
  });

  it("does not dispatch a paused or legacy-unscoped definition", async () => {
    await dispatchDueWorkspaceSchedules(now);
    expect(scheduleTask).not.toHaveBeenCalled();
  });
  ```

- [ ] **Step 2: Run focused red tests.**

  Run: `cd services/cosa && npx vitest run tests/backfill-schedule-project-ids.test.ts tests/workspace-schedule.test.ts`

  Expected: FAIL because current script calls `GET /operations/projects` and writes the first returned id.

- [ ] **Step 3: Define explicit remediation result and implement the minimum safe behavior.**

  Change `BackfillResult` to:

  ```ts
  interface BackfillResult {
    pausedDefinitionIds: string[];
    alreadyBoundDefinitionIds: string[];
    skippedDefinitionIds: string[];
  }
  ```

  For every row selected by `isNull(projectId)`, atomically set `state: "paused"`, `isLegacyUnscoped: true`, `updatedAt: new Date()`. Do not invoke Company, do not set `projectId`, and do not include prompt content in logs. Log only definition id/workspace id and reason `PROJECT_CONTEXT_REQUIRED`.

  In `findDueScheduleDefinitions`, require all three conditions: `state == "enabled"`, `projectId IS NOT NULL`, and `isLegacyUnscoped == false`. This avoids minting a known-doomed execution. Keep the worker fail-closed check as defense in depth.

- [ ] **Step 4: Add an explicit Founder rebind service contract.**

  Add a `rebindLegacyWorkspaceSchedule({ scheduleId, workspaceId, projectId, principalId })` service function in `workspace-schedule.service.ts`. It must:

  ```ts
  // preconditions
  // schedule belongs to workspace
  // projectId is non-empty and separately verified by the caller's Company boundary
  // schedule is paused + isLegacyUnscoped=true
  // result: projectId set, isLegacyUnscoped=false, state="enabled"
  ```

  Do not reuse normal create semantics and do not accept an implicit Project. Add repository support with `WHERE id AND workspace_id AND is_legacy_unscoped=true` to prevent stale rebind overwrites.

- [ ] **Step 5: Run focused green tests and service type checks.**

  Run: `cd services/cosa && npx vitest run tests/backfill-schedule-project-ids.test.ts tests/workspace-schedule.test.ts tests/schedule-schema.test.ts && npm run typecheck`

  Expected: PASS; no test expects `projects[0]`; new rows stay scope-explicit.

- [ ] **Step 6: Commit boundary.**

  Commit only schedule remediation code/tests with: `fix(schedules): fail closed for legacy project scope`.

## Task 2: Persist schedule conversation and messages as Project-scoped

**Files:**
- Modify: `apps/cosa/worker/handlers.py:107-123,1095-1222`
- Modify: `packages/agent/conversations/models.py:16-79`
- Modify: `packages/agent/conversations/repository.py:125-140,307-340`
- Modify: `tests/apps/cosa/test_scheduled_session_worker.py`
- Modify: `tests/agent/conversations/test_project_scoped_repository.py`

**Consumes:** `ScheduleExecution.project_id_snapshot` created by Task 1 and existing `ConversationScopeState` validation.

**Produces:** A scheduled run whose conversation, initial message, assistant messages and activity events all carry the same Project id.

- [ ] **Step 1: Write red tests for scoped persistence.**

  Add tests asserting:

  ```python
  conversation = await plane.conversation_repository.get_conversation(conversation_id)
  assert conversation.project_id == PROJECT_A
  assert conversation.scope_state == "PROJECT_SCOPED"
  assert conversation.active_agent_profile == "operations"

  messages = await plane.conversation_repository.list_messages(conversation_id)
  assert {message.project_id for message in messages} == {PROJECT_A}
  ```

  Add a model/repository negative case: a `MessageRecord(project_id=PROJECT_B)` cannot be persisted into a `PROJECT_SCOPED` conversation for Project A. The repository must reject before commit; in-memory and PostgreSQL implementations must agree.

- [ ] **Step 2: Run the red test.**

  Run: `PYTHONPATH=. .venv/bin/python -m pytest -q tests/apps/cosa/test_scheduled_session_worker.py tests/agent/conversations/test_repository.py`

  Expected: FAIL because scheduled conversation and `MessageRecord` are currently constructed without Project metadata.

- [ ] **Step 3: Make Project scope an explicit append contract.**

  Change `_append_message` to receive `project_id: str | None`. For a project-scoped run, every call site in `execute_run_task`/resume path passes the payload Project. At repository level, load the conversation and enforce:

  ```python
  if conversation.scope_state == "PROJECT_SCOPED" and message.project_id != conversation.project_id:
      raise ValueError("message_project_scope_mismatch")
  ```

  Keep legacy conversations readable: `LEGACY_UNSCOPED` accepts only `message.project_id is None`. Do not infer a Project for historical messages.

- [ ] **Step 4: Scope scheduled creation before calling `execute_run_task`.**

  In `execute_scheduled_session_task`, create:

  ```python
  ConversationRecord(
      conversation_id=conversation_id,
      workspace_id=workspace_id,
      project_id=project_id,
      scope_state="PROJECT_SCOPED",
      created_by_principal="service:scheduler",
      active_agent_profile=agent_profile,
      title=f"Scheduled execution: {prompt_template[:30]}",
  )
  ```

  Construct initial `MessageRecord(..., project_id=project_id)`. Ensure completion reporting preserves the same conversation id after failures but never reports it as successful when the worker returns a failed `RunTaskResult`.

- [ ] **Step 5: Add failure-order tests.**

  Test missing snapshot and forged snapshot behavior:

  ```python
  assert no_conversation_created
  assert no_message_created
  assert completion.state == "failed"
  assert completion.error == "PROJECT_CONTEXT_REQUIRED"
  ```

  For a payload Project B conflicting with snapshot A, assert `PROJECT_CONTEXT_MISMATCH`, no kernel call, no compliance call, and no activity in B.

- [ ] **Step 6: Run green tests and lint.**

  Run: `make lint && PYTHONPATH=. .venv/bin/python -m pytest -q tests/apps/cosa/test_scheduled_session_worker.py tests/agent/conversations/test_repository.py tests/apps/cosa/project_activity/test_worker_wiring.py`

  Expected: PASS; all messages for a scheduled Project A run have Project A.

- [ ] **Step 7: Commit boundary.**

  Commit: `fix(agent): preserve project scope in scheduled conversations`.

## Task 3: Prove scope persistence across real process restart

**Files:**
- Modify: `tests/e2e/scenarios/schedule_project_scope.py`
- Modify: `tests/e2e/test_cross_plane_smoke.py:100-105`

**Consumes:** Tasks 1–2; disposable three-database test environment.

**Produces:** Process-level proof that PostgreSQL durable schedule execution preserves scope/idempotency through worker restart.

- [ ] **Step 1: Write the red process E2E test.**

  Extend existing S10 in `tests/e2e/scenarios/schedule_project_scope.py`: create Workspace A with Projects A1/A2 and Workspace B with Project B1, create a schedule scoped to A1, wait until the execution's scoped conversation exists, call `restart_api_and_worker(handles, cluster)` from `tests/e2e/stack/subprocess_stack.py`, then wait for the recovered execution and assert:

  ```python
  assert conversation.workspace_id == workspace_a
  assert conversation.project_id == project_a1
  assert conversation.scope_state == "PROJECT_SCOPED"
  assert all(message.project_id == project_a1 for message in messages)
  assert await list_activity(workspace_a, project_a2) == []
  assert await list_activity(workspace_b, project_b1) == []
  assert count_runs_for_execution(execution_id) == 1
  ```

- [ ] **Step 2: Run it in the disposable environment.**

  Run: `PYTHONPATH=. .venv/bin/python -m pytest -q tests/e2e/test_cross_plane_smoke.py::test_s10_schedule_project_scope -m cross_plane`

  Expected before Tasks 1–2: FAIL on unscoped conversation/message or duplicate/retry behavior. If infrastructure is unavailable, record `UNVERIFIED_ENVIRONMENT` rather than a code pass/fail.

- [ ] **Step 3: Implement only missing test harness plumbing.**

  Use process start/stop facilities already used by cross-plane smoke. Do not replace a process restart with a second in-process object. Use fixed, test-only database names and cleanup hooks supplied by the existing harness.

- [ ] **Step 4: Run focused E2E to green.**

  Run: the focused process test, then `make e2e-cross-plane-smoke`.

  Expected: PASS with proof from a new worker process and PostgreSQL queries.

- [ ] **Step 5: Commit boundary.**

  Commit: `test(e2e): prove schedule project scope across restart`.

## Task 4: Establish one canonical Agent runtime catalog

**Files:**
- Create: `apps/cosa/agents/catalog.py`
- Modify: `apps/cosa/agents/specs.py:1-60,1029-1064`
- Modify: `apps/cosa/agents/agent_profile_specs.py:1-77`
- Modify: `apps/cosa/agents/seed.py:15-168`
- Modify: `tests/apps/cosa/agents/test_seed.py`
- Modify: `tests/apps/cosa/worker/test_handlers.py:181-202`

**Consumes:** Existing `AgentSpec`, `PromptSpec`, `COSA_DEFAULT_MODEL_POLICY`, `seed_builtin_skillpacks`, and `SpecResolver` exact-hash contract.

**Produces:** Single-source catalog that controls profile routing, Prompt/Agent seed order, deployed validation and test parametrization.

- [ ] **Step 1: Write failing catalog invariants.**

  Add a test that imports catalog and asserts:

  ```python
  assert "founder_assistant" in PUBLIC_PROFILE_KEYS
  assert catalog_by_profile["founder_assistant"].agent_spec.id == "cosa.agents.founder_assistant"
  assert catalog_by_profile["cto"].agent_spec.id == "cosa.executive.cto"
  assert {entry.agent_spec.id for entry in deployed_entries} <= seeded_agent_ids
  assert {entry.prompt_spec.id for entry in deployed_entries} <= seeded_prompt_ids
  ```

  Add a startup test that `seed_cosa_runtime_specs` succeeds and `resolve_spec` succeeds for every public profile. Add a negative test deleting a catalog entry's prompt/spec record and asserting startup/readiness failure.

- [ ] **Step 2: Run focused red tests.**

  Run: `PYTHONPATH=. .venv/bin/python -m pytest -q tests/apps/cosa/agents/test_seed.py tests/apps/cosa/worker/test_handlers.py -k 'seed or correct_spec'`

  Expected: FAIL because `founder_assistant` and CTO are in deployed/profile sets but absent from `seed_cosa_agent_specs`.

- [ ] **Step 3: Add typed catalog module.**

  Implement immutable `RuntimeAgentCatalogEntry` with `profile_key`, `agent_spec`, `prompt_spec`, `availability` (`public`, `deployed_not_public`, `declared_only`) and `deployment_kind`. Make duplicate profile key/id validation happen at module construction. Catalog exposes exactly:

  ```python
  def public_profile_specs() -> dict[str, AgentSpec]: ...
  def seeded_entries() -> tuple[RuntimeAgentCatalogEntry, ...]: ...
  def deployed_entries() -> tuple[RuntimeAgentCatalogEntry, ...]: ...
  ```

  Keep `COSA_DEPLOYED_AGENT_SPECS` as a compatibility view derived from `deployed_entries()`, not a second literal list.

- [ ] **Step 4: Convert routing and seeding.**

  `agent_profile_specs.py` derives the mapping from catalog. `seed.py` publishes `prompt_spec` for every seeded entry, then model policy once, then every corresponding `agent_spec`; it must include `founder_assistant` and CTO. `seed_cosa_runtime_specs` verifies every deployed entry's AgentSpec record and pinned skills, not only skill pins.

  Preserve special profiles only if their availability is explicit. A `declared_only` entry cannot be in the public profile map or startup deployed validation.

- [ ] **Step 5: Run green tests and type/lint gates.**

  Run: `make lint typecheck-py && PYTHONPATH=. .venv/bin/python -m pytest -q tests/apps/cosa/agents/test_seed.py tests/apps/cosa/worker/test_handlers.py`

  Expected: PASS; a manually removed registry dependency fails closed, while every actual public profile resolves.

- [ ] **Step 6: Commit boundary.**

  Commit: `fix(agent): derive runtime seed from canonical catalog`.

## Task 5: Repair authority-aware test fixtures without weakening guards

**Files:**
- Modify: `tests/apps/cosa/compliance/test_run_delegation.py`
- Modify: `tests/apps/cosa/project_activity/test_worker_wiring.py`
- Modify: `tests/apps/cosa/test_founder_knowledge_context.py`
- Modify: `tests/apps/cosa/test_scheduled_session_worker.py`
- Modify: `tests/apps/cosa/test_vertical_slice_1_read_path.py`
- Modify: `tests/apps/cosa/test_workspace_execution_e2e.py`
- Modify: shared helper only if existing helper ownership is clear; otherwise create `tests/apps/cosa/helpers/project_team_authority.py`.

**Consumes:** Catalog from Task 4 and real `ProjectAgentRunAuthority` contract.

**Produces:** Tests that reach their intended compliance/kernel/activity branch only after valid authority, plus negative tests that prove fail-closed behavior.

- [ ] **Step 1: Create a single valid authority fixture factory.**

  ```python
  def valid_run_authority(*, workspace_id: str, project_id: str, profile_key: str) -> ProjectAgentRunAuthority:
      spec = public_profile_specs()[profile_key]
      return ProjectAgentRunAuthority(
          projectId=project_id,
          workspaceId=workspace_id,
          profileKey=profile_key,
          assignmentVersion=1,
          agentWorkforceMemberId="mem_test_agent",
          spec=SpecRef(id=spec.id, version=spec.version, definitionHash=spec.compute_hash()),
      )
  ```

- [ ] **Step 2: Replace ad-hoc Company mocks in success-path tests.**

  Attach `AsyncMock(spec=ProjectTeamClient)` to each plane and return the factory result. Ensure data-governance/Company mocks remain isolated from Project Team mock so HTTP interception cannot accidentally return `{"tasks": []}` for authority.

- [ ] **Step 3: Keep/add negative cases.**

  Add explicit tests for missing Project, Company unavailable, cross-Project response and spec-hash mismatch. Each asserts `run.failed` code, zero compliance resolver calls and zero kernel calls.

- [ ] **Step 4: Run red-to-green focused suite.**

  Run: `PYTHONPATH=. .venv/bin/python -m pytest -q tests/apps/cosa/compliance/test_run_delegation.py tests/apps/cosa/project_activity/test_worker_wiring.py tests/apps/cosa/test_founder_knowledge_context.py tests/apps/cosa/test_vertical_slice_1_read_path.py tests/apps/cosa/test_workspace_execution_e2e.py`

  Expected: Success-path tests reach their asserted branch; negative tests preserve guard ordering.

- [ ] **Step 5: Commit boundary.**

  Commit: `test(agent): construct valid project team authority fixtures`.

## Task 6: Make `mvp-surface` evidence executable

**Files:**
- Modify: `scripts/mvp_surface_check.py`
- Modify: `tests/quality/test_mvp_surface_check.py`
- Modify: `shared/contracts/mvp-surface.json`
- Create/modify the exact missing Flutter/integration tests selected per capability; do not add empty test shells.

**Consumes:** Current list of 21 enabled capabilities with absent `flutter_test`/`integration_test` fields.

**Produces:** A manifest where every enabled user-facing capability points to existing, meaningful test evidence.

- [ ] **Step 1: Add red checker tests for missing and nonexistent proof paths.**

  ```python
  errors = validate_manifest({"capabilities": [{
      "id": "x", "enabled": True, ...,
      "flutter_test": "frontend/test/missing_test.dart",
      "integration_test": "tests/e2e/missing.py",
  }]})
  assert "does not exist" in "\n".join(errors)
  ```

  Add one test for an enabled route with empty `integration_test` and one disabled route permitted to omit UI proof.

- [ ] **Step 2: Run red checker tests.**

  Run: `PYTHONPATH=. .venv/bin/python -m pytest -q tests/quality/test_mvp_surface_check.py && make mvp-surface-check`

  Expected: current manifest fails with the 21 missing fields.

- [ ] **Step 3: Decide each of the 21 capability states from actual code.**

  For each ID, inspect endpoint handler plus Flutter caller. Apply exactly one outcome:

  - enabled + add existing test paths only after writing behavior tests;
  - disabled + remove/block Flutter call;
  - internal + remove from public MVP surface.

  Record decisions as manifest fields/commit context, not comments that silently bypass validation. Priority set: executive workspace role mutation, lifecycle transition/history, task delete, old OKR routes, twelve-week cycle and execution-cycle view.

- [ ] **Step 4: Implement path existence validation and manifest updates.**

  Resolve proof paths against repository root, reject path traversal and directories, and keep test files under owned `frontend/test`, `tests/e2e`, or service test roots. Do not parse test source heuristically; existence plus explicit manifest ownership is the gate.

- [ ] **Step 5: Run green proof gates.**

  Run: `make mvp-contracts-check mvp-surface-check frontend-api-contract-check`

  Expected: PASS; no enabled capability has missing/nonexistent proof fields.

- [ ] **Step 6: Commit boundary.**

  Commit: `fix(contracts): require executable MVP proof paths`.

## Task 7: Remove legacy frontend boundary dependency and worktree false-reds

**Files:**
- Modify: `frontend/lib/core/lifecycle/lifecycle_service.dart`
- Modify: `frontend/test/core/lifecycle/lifecycle_service_test.dart`
- Modify: `scripts/check_frontend_boundaries.mjs`
- Modify: `tests/apps/cosa/test_services_boundary_audit.py`

**Consumes:** Generated `MvpEndpoint` paths and `MvpRequestClient` behavior.

**Produces:** Lifecycle routes use current typed client; release source scanner only scans release-owned roots.

- [ ] **Step 1: Write Dart red tests for typed lifecycle requests.**

  Cover workspace/project `getHistory` and `transition`, asserting the `MvpEndpoint` used, required path params, body `{toStage, expectedStageVersion, rationale?}`, successful decode, and non-200 failure. The test must not inherit `WorkspaceScopedService`.

- [ ] **Step 2: Implement lifecycle client migration.**

  Remove the `workspace_scoped_service.dart` import/inheritance. Inject `MvpRequestClient`, use generated lifecycle endpoints, and retain typed response parsing. Preserve caller API only where tests prove current widgets use it.

- [ ] **Step 3: Write scanner red test.**

  Extend boundary audit fixture to create `.kilo/worktrees/example/Makefile` containing `legacy/` and assert it does not appear in deployment findings; create a root `Makefile` fixture with `legacy/` and assert it still does.

- [ ] **Step 4: Restrict scanner traversal.**

  In `test_services_boundary_audit.py`, add `.kilo`, `.claude`, `.agents`, managed worktree roots and build/cache roots to excluded directory parts. Do not add any worktree path to `_DEPLOYMENT_LEGACY_ALLOWLIST`.

- [ ] **Step 5: Run green tests/gates.**

  Run: `cd frontend && flutter test test/core/lifecycle/lifecycle_service_test.dart && cd .. && make frontend-boundary-check && PYTHONPATH=. .venv/bin/python -m pytest -q tests/apps/cosa/test_services_boundary_audit.py`

  Expected: PASS without expanding `legacyWorkspaceScopedImportAllowlist`.

- [ ] **Step 6: Commit boundary.**

  Commit: `refactor(frontend): move lifecycle requests to MVP client`.

## Task 8: Reconcile Skill catalog and Workforce test truth

**Files:**
- Modify: `tests/apps/cosa/test_lifecycle_tranche_c_acceptance.py`
- Modify: `apps/cosa/agents/skillpack_seed.py` only if the runtime bundle needs an explicit catalog filter.
- Modify: `tests/apps/cosa/test_workforce_routes.py`
- Modify: workforce source/seed fixture only if roster changes are unintended after source review.

**Consumes:** Repository `skillpacks/**/manifest.yaml`, deployment root resolution, and actual seeded Workforce roster.

**Produces:** Deterministic catalog assertion and workforce dashboard expectation derived from business truth rather than a stale literal.

- [ ] **Step 1: Write red catalog identity test.**

  Parse all deployment-root manifests through the same parser used by `seed_builtin_skillpacks`, derive tuples `(skill_id, version, definition_hash)`, then compare exact set with sync API response. Assert duplicates are rejected and IDs are sorted deterministically.

- [ ] **Step 2: Replace hard-coded `TRANCHE_C_CANONICAL_COUNT`.**

  Do not assert a count as the source of truth. Assert set equality and use count only as diagnostic:

  ```python
  assert synced_identity_set == deployment_identity_set
  assert len(synced_identity_set) == len(deployment_identity_set)
  ```

  If a subset is intended, implement one explicit manifest/config filter used by both seed and test; review every excluded id/version/hash.

- [ ] **Step 3: Diagnose Workforce roster arithmetic before changing expected count.**

  In the route test, enumerate the initial roster source and created assignment. Assert the response count equals the actual distinct active roster records, and assert each expected id appears once. If eight is intended, replace `6` with derived identity assertion; if not, fix duplicate seed/aggregation source and add idempotency test.

- [ ] **Step 4: Run focused green tests.**

  Run: `PYTHONPATH=. .venv/bin/python -m pytest -q tests/apps/cosa/test_lifecycle_tranche_c_acceptance.py tests/apps/cosa/test_workforce_routes.py && make skillpacks-validate`

  Expected: identity catalog equality and truthful roster aggregation.

- [ ] **Step 5: Commit boundary.**

  Commit: `test(catalog): derive skill and workforce inventory from runtime truth`.

## Task 9: Make Founder Hub and financial/commercial DTOs truthful

**Files:**
- Modify: `frontend/lib/modules/hologram_hub/controllers/founder_command_center_controller.dart`
- Modify: affected Founder Hub view/widgets under `frontend/lib/modules/hologram_hub/`
- Modify: `frontend/lib/data/models/finance_legal_models.dart`
- Modify: `frontend/lib/data/models/commercial_models.dart`
- Create: `frontend/lib/data/models/source_value_state.dart`
- Modify: `frontend/test/founder_command_center_chat_test.dart`
- Modify: `frontend/test/modules/hologram_hub/ai_workforce_tab_test.dart`
- Create: `frontend/test/data/models/finance_legal_models_test.dart`
- Create: `frontend/test/data/models/commercial_models_test.dart`

**Consumes:** `MvpRequestClient.unavailable`, current Hub state enums, backend decimal-string contracts.

**Produces:** No legacy actionable workforce UI; no lossy numeric/date defaults.

- [ ] **Step 1: Select and test the approved Workforce product outcome.**

  This plan implements the safe default: hide/remove legacy Workforce and pending approval panels/actions that call `WorkforceMvpService` unavailable methods. Add widget tests asserting the Hub does not render a mutation CTA for unavailable workforce data and does render a neutral explanation only where the product still needs a placeholder.

  Do not implement a new Workforce API in this task. That is a separately approved cross-plane product slice.

- [ ] **Step 2: Write red model tests for malformed source data.**

  ```dart
  test('financial transaction preserves missing amount as unavailable') {
    final model = FinancialTransactionModel.fromJson({'id': 'tx-1', 'transactionDate': 'bad'});
    expect(model.amountState, SourceValueState.unavailable);
    expect(model.amount, isNull);
    expect(model.transactionDateState, SourceValueState.invalid);
    expect(model.transactionDate, isNull);
  });
  ```

  Add equivalent cases for finance snapshots, accounting periods, leads and opportunities. Add exact decimal string test (`"0.10"` remains `"0.10"`, never a binary `double`).

- [ ] **Step 3: Introduce provenance-aware value types.**

  `SourceValueState` has only `present`, `unavailable`, `invalid`. Add `MonetaryAmount { String decimal; String currency; }`. Update DTO fields used by UI to nullable `DateTime?` / `MonetaryAmount?` plus state. Do not silently change API write payload semantics; adapt views/services at compile errors and render explicit unavailable/invalid copy.

- [ ] **Step 4: Run red-to-green Flutter tests.**

  Run: `cd frontend && flutter test test/founder_command_center_chat_test.dart test/modules/hologram_hub/ai_workforce_tab_test.dart test/modules/finance test/modules/commercial && flutter analyze`

  Expected: no unavailable workforce CTA; no model turns malformed source into zero/current date; analyzer clean.

- [ ] **Step 5: Commit boundary.**

  Commit: `fix(frontend): preserve unavailable finance and workforce states`.

## Task 10: Preserve Knowledge/Vault unavailable boundary and complete release verification

**Files:**
- Modify only tests/manifest/UI status files if any currently label semantic/Vault retrieval as enabled.
- Do not modify `apps/cosa/api/vault_routes.py` to enable retrieval in this plan.
- Modify: `docs/superpowers/specs/2026-09-19-runtime-truth-and-release-recovery-design.md` only if implementation reveals a source-backed deviation; otherwise leave proposed design immutable.

**Consumes:** Current 501 route and lexical/default retrieval contract.

**Produces:** Release evidence that scopes out unimplemented Knowledge/Vault functionality rather than masking it.

- [ ] **Step 1: Add/verify explicit unavailable tests.**

  Assert `/agent/vault/retrieval/query` returns 501 without path/secret leakage. Assert semantic settings without a production provider resolve lexical or return explicit unavailable, never hashing vectors presented as semantic results.

- [ ] **Step 2: Run all scoped verification.**

  Run in order:

  ```bash
  make contracts-check mvp-contracts-check mvp-surface-check
  make frontend-boundary-check company-boundary-check encore-handler-boundary-check
  make ts-suppression-check route-auth-allowlist-check frontend-api-contract-check
  make skillpacks-validate migration-compat-check contract-freeze-check
  make lint typecheck-py
  make apps-cosa-test services-test frontend-test frontend-analyze
  make e2e-cross-plane-smoke
  ```

  Mark a process/database command `UNVERIFIED_ENVIRONMENT` only when its required disposable infrastructure cannot start; do not claim it passed from unit coverage.

- [ ] **Step 3: Run final scope-specific evidence.**

  Run the Task 3 process test with two Workspaces/two Projects, capture test output plus migration checksum status, and verify `git diff --check`.

- [ ] **Step 4: Final review checklist.**

  Confirm each acceptance item in the spec maps to a green test/evidence artifact. Confirm no code path chooses first Project, no public profile lacks a seeded exact identity, no enabled manifest entry lacks proof paths, and no UI default fabricates financial/commercial facts.

- [ ] **Step 5: Commit boundary.**

  If and only if all scoped tests are green, commit release-proof-only changes with: `test(release): verify runtime truth recovery gates`.

## Rollout order and rollback gates

1. Deploy Task 1 safe pause behavior before any rebind UI/API. It only disables ambiguous legacy schedules.
2. Deploy Tasks 2 and 4 together only after process E2E and startup registry tests pass; both affect durable runtime identity/scope.
3. Deploy Tasks 5–8 only after gates are green; none may weaken authority to compensate for tests.
4. Deploy Task 9 separately as Flutter release after backend contracts stay stable.
5. Keep Knowledge/Vault retrieval unavailable through this release.

Rollback binary code if startup validation breaks unexpectedly. Do not rollback by nulling Project IDs, deleting conversations/messages, re-enabling legacy schedules, or restoring auto-first-Project selection. Paused schedule remediation records are durable operational evidence.

## Plan self-review

- **Spec coverage:** Tasks 1–3 cover schedule/conversation/restart; Tasks 4–5 cover Agent identity and authority; Tasks 6–8 cover evidence gates/catalog; Task 9 covers UI truth; Task 10 preserves Knowledge/Vault boundary and runs release proof.
- **Placeholders:** No `TBD`, `TODO`, generic error-handling instruction, or implicit test instruction remains.
- **Type consistency:** `project_id`, `projectIdSnapshot`, `RuntimeAgentCatalogEntry`, `ProjectAgentRunAuthority`, `SourceValueState`, and `MonetaryAmount` are introduced before later task use.
- **Review focus coverage:** Legacy failure is Task 1; forged/restart scope is Tasks 2–3; public profile startup is Task 4; malformed UI data is Task 9.
