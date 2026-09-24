# Governed Advisor Overlay and Truthful Hub Implementation Plan

> **For agentic workers:** Execute tasks in order. Each behavior change starts with a failing test and ends with the stated verification. Do not commit unless the user separately asks for a commit.

**Goal:** Make advisor overlays and Hub actions production-verifiable by pinning immutable advisor definitions to Project deployments and removing simulated actions.

**Architecture:** Company frames a Project deployment pin plus an advisor overlay pin obtained from COSA Control Plane. COSA resolves both exact identities, executes the overlay through the common compliance/model-routing path, and records both identities. Flutter uses only canonical APIs for chat and task creation.

**Tech Stack:** Encore TypeScript, FastAPI/Python, PostgreSQL, OpenAI Agents SDK adapter, Flutter/GetX, pytest, Vitest, flutter_test.

**Spec:** `docs/superpowers/specs/2026-09-20-governed-advisor-overlay-and-truthful-hub-design.md`

## Global Constraints

- Company owns Workspace, Project, deployment authority, business writes, and transactional outbox.
- Every business run has explicit `workspace_id` and `project_id`.
- Every AgentSpec, skill, and overlay resolves by exact id, version, and hash.
- Advisor overlays are L1 and cannot expand their required profile's capabilities.
- No UI action claims success before a canonical API returns success.
- Preserve existing user changes in the three E2E files already modified in this workspace.
- Do not commit or push without a separate user request.

## Review Focus

- A workspace office active in another Project must not permit advisory execution without a deployment in the framed Project; Task 4 tests this.
- A persisted overlay hash differing from registry content must fail before the model call; Task 5 tests this.
- An AGENT workflow step must fail against a real two-argument kernel if it lacks a resolved full spec; Task 8 tests this.
- A direct chat failure must not insert a fabricated assistant response; Task 11 tests this.
- Task creation retry must not duplicate a task; Task 12 tests idempotency propagation.

---

## File structure

| Area | Files | Responsibility |
|---|---|---|
| Shared contracts | `shared/contracts/executive-advisor-overlays.json`, generator outputs | Built-in role-to-overlay exact identity contract. |
| COSA control plane | `services/cosa/*advisor-overlay*` | Service-authenticated read-only overlay identity lookup. |
| Company | executive deliberation service, handler, tests | Resolve/persist/emit both Project deployment and overlay pins. |
| Agent registry/runtime | catalog, specs, seed, executive-board runtime | Seed all overlays, resolve exact pins, enforce scope closure. |
| Workflow | `agent_step.py`, composition, tests | Resolve full spec and call conforming kernel. |
| Hub | direct chat sheet/controller, task service, tests | Real Project-scoped chat and task creation, no simulated execution. |

### Task 1: Define the shared advisor overlay identity contract

**Files:**
- Create: `shared/contracts/executive-advisor-overlays.json`
- Create: `scripts/gen-executive-advisor-overlays.mjs`
- Create: generated TypeScript/Python contract outputs using repository generator conventions
- Test: `tests/contracts/test_executive_advisor_overlay_contract.py`

**Interfaces:**
- Produces `AdvisorOverlayDefinition { roleKey, overlaySpecId, overlaySpecVersion, overlayDefinitionHash, requiredProfileKey, skillPins }`.
- Consumed by Company framing and COSA seed validation.

- [ ] Write a failing contract test that requires one overlay per executive role and rejects duplicate role keys.
- [ ] Run `PYTHONPATH=. .venv/bin/pytest tests/contracts/test_executive_advisor_overlay_contract.py -q`; expect failure because the contract does not exist.
- [ ] Add the JSON source and generator. Generate immutable TypeScript and Python artifacts; do not hand-edit generated files.
- [ ] Extend the test to assert the generated role-key set equals `EXECUTIVE_ROLE_KEYS`.
- [ ] Re-run the focused test; expect pass.

### Task 2: Complete and seed advisor overlay AgentSpecs

**Files:**
- Modify: `apps/cosa/agents/specs.py`
- Modify: `apps/cosa/agents/catalog.py`
- Modify: `apps/cosa/agents/seed.py`
- Test: `tests/agent/executive_board/test_overlay_catalog.py`

**Interfaces:**
- Produces one published `AgentSpec` overlay for all fifteen role keys.
- Existing executive specs are retained as overlay definitions where ids match.

- [ ] Write a failing test that maps every overlay contract id/version/hash to a seeded AgentSpec and verifies L1 autonomy.
- [ ] Run `PYTHONPATH=. .venv/bin/pytest tests/agent/executive_board/test_overlay_catalog.py -q`; expect missing Chief of Staff, CFO, CMO, COO, and CCO overlays.
- [ ] Add the five missing overlay AgentSpecs with exact prompt and skill pins; expose all fifteen entries in the catalog as `deployment_kind="executive"` overlay assets.
- [ ] Seed prompts, model policies, skills, and overlay specs in deterministic order.
- [ ] Re-run the focused test and `make skillpacks-validate`; expect pass.

### Task 3: Enforce overlay/profile capability closure

**Files:**
- Modify: `apps/cosa/agents/capability_readiness.py`
- Create: `apps/cosa/agents/advisor_overlay_validation.py`
- Test: `tests/apps/cosa/agents/test_advisor_overlay_validation.py`

**Interfaces:**
- Produces `validate_advisor_overlay(overlay: AgentSpec, profile: AgentSpec) -> list[str]`.
- Rejects overlay capabilities outside the required profile and missing skill manifests.

- [ ] Write failing tests for an overlay with an extra capability, an overlay with higher autonomy, a missing skill manifest, and a valid contained overlay.
- [ ] Run `PYTHONPATH=. .venv/bin/pytest tests/apps/cosa/agents/test_advisor_overlay_validation.py -q`; expect failure because the validator is absent.
- [ ] Implement subset validation and make `check_agent_spec_readiness` report skill tools that are absent from the owning AgentSpec capability refs.
- [ ] Invoke the validator from runtime seed verification so startup fails before polling.
- [ ] Re-run focused tests and `make apps-cosa-test`; report any unrelated failure separately.

### Task 4: Persist deployment and overlay pins in Company frames

**Files:**
- Modify: `services/company/operations/services/executive-deliberation.service.ts`
- Modify: `services/company/operations/handlers/executive-deliberation.handler.ts`
- Modify: Company DTO/contract generator files as required
- Test: `services/company/operations/tests/executive-deliberation.service.test.ts`

**Interfaces:**
- Replaces `SelectedRolePin` with `SelectedAdvisorExecutionPin` containing `deployment` and `overlay` subobjects.
- Consumes a read-only COSA overlay identity client.

- [ ] Write failing service tests asserting frame persistence includes exact deployment and overlay fields and that a Project without the required deployment fails even when the Workspace office is active.
- [ ] Run `cd services/company && encore test operations/tests/executive-deliberation.service.test.ts`; expect failure because only the old flat pin exists.
- [ ] Implement exact Project deployment pinning first, then resolve overlay identity through the new internal client before creating the frame/outbox event.
- [ ] Make the outbox payload include both subobjects; reject unavailable or mismatched overlay identity before write.
- [ ] Re-run the focused Company test and generated-contract check.

### Task 5: Add the COSA Control Plane overlay identity endpoint

**Files:**
- Create: `services/cosa/*advisor-overlay*.ts`
- Modify: `services/company/shared/*` internal client wiring
- Test: `services/cosa/tests/advisor-overlay*.test.ts`
- Test: `services/company/operations/tests/executive-deliberation.service.test.ts`

**Interfaces:**
- `GET internal overlay identity(roleKey)` returns an exact published overlay identity and skill hashes.
- Caller is service-authenticated; browser access is rejected.

- [ ] Write a failing COSA test for a valid role, unknown role, and a role whose registry record hash differs from the generated contract.
- [ ] Run the focused COSA test; expect endpoint/module absence.
- [ ] Implement read-only lookup using the seeded registry/catalog, service authentication, and structured failure codes.
- [ ] Wire Company client handling so lookup/network failure prevents framing without partial persistence.
- [ ] Re-run COSA and Company focused tests; expect pass.

### Task 6: Execute advisor overlays through the COSA run path

**Files:**
- Modify: `packages/agent/executive_board/models.py`
- Modify: `packages/agent/executive_board/runner.py`
- Modify: `apps/cosa/worker/executive_board_handler.py`
- Modify: `apps/cosa/worker/run_core.py`
- Test: `tests/agent/executive_board/test_runner.py`
- Test: `tests/apps/cosa/worker/test_executive_board_handler.py`

**Interfaces:**
- `AdvisorOverlayPin` and `ProjectDeploymentPin` replace the flat `RolePin`.
- Worker resolves exact overlay and deployment AgentSpecs and provides both pins in run metadata.

- [ ] Write failing tests proving the runner rejects an overlay hash mismatch before model invocation and records both identities on the request.
- [ ] Run the focused Python tests; expect failure because the runner synthesizes `executive.board.<role>`.
- [ ] Move Company-dependent run preparation into `apps/cosa`; keep the generic board package responsible for schema/evidence validation only.
- [ ] Resolve the overlay exact hash from registry, verify its scope against the deployment spec, use it as the root executable, and run through compliance/model-route preparation.
- [ ] Remove default pin values in the handler; malformed outbox payload must become a structured failure.
- [ ] Re-run focused tests and all `tests/agent/executive_board` tests.

### Task 7: Make callback and replay identity-safe

**Files:**
- Modify: `services/company/operations/services/executive-deliberation.service.ts`
- Modify: `apps/cosa/company/executive_board_client.py`
- Test: `services/company/operations/tests/executive-deliberation.service.test.ts`
- Test: `tests/apps/cosa/worker/test_executive_board_handler.py`

**Interfaces:**
- Callback includes frame version, role key, deployment pin hash, and overlay pin hash.
- Company accepts a callback only when every identity equals the persisted frame.

- [ ] Write failing tests for stale frame callback, overlay hash drift, deployment hash drift, and duplicate identical callback.
- [ ] Run focused tests; expect current callback contract lacks both pin identities.
- [ ] Extend callback DTO and persistence comparison. Make duplicate equal callbacks idempotent and conflicting callbacks fail without overwriting analysis.
- [ ] Re-run focused tests.

### Task 8: Repair AGENT workflow kernel execution

**Files:**
- Modify: `packages/agent/workflows/agent_step.py`
- Modify: `apps/cosa/composition/agent_plane.py`
- Modify: `apps/cosa/composition/workflow_orchestration.py`
- Test: `tests/agent/workflows/test_agent_step.py`
- Test: `tests/apps/cosa/worker/test_governed_workflow_run.py`

**Interfaces:**
- `AgentWorkflowStep` receives an exact-spec resolver and invokes `kernel.run(request, spec)`.

- [ ] Replace the one-argument fake kernel in the unit test with a conforming two-argument fake and write a failing test that asserts the resolved AgentSpec is passed.
- [ ] Run `PYTHONPATH=. .venv/bin/pytest tests/agent/workflows/test_agent_step.py -q`; expect failure at the existing one-argument call.
- [ ] Resolve the full AgentSpec from the registry using the live authority identity and exact manifest pin; fail closed on missing content or hash mismatch.
- [ ] Inject the resolver through composition rather than importing Company code into `packages/agent`.
- [ ] Re-run workflow unit tests and governed workflow worker tests, including approval/resume.

### Task 9: Make built-in skillpack publication atomic

**Files:**
- Modify: `apps/cosa/agents/skillpack_seed.py`
- Modify: `packages/agent/registry/repository.py` and Postgres implementation if batch support is absent
- Test: `tests/apps/cosa/agents/test_skillpack_seed.py`

**Interfaces:**
- `publish_skill_batch(records)` exposes all records or none.

- [ ] Write a failing test that makes the second manifest publish fail and asserts the first manifest is not visible afterward.
- [ ] Run the focused seed test; expect partial records under current sequential publish.
- [ ] Parse and validate all manifests first; add transactional/staged batch publication for the registry implementation.
- [ ] Re-run seed tests and skillpack validation.

### Task 10: Replace Hub specialist chat simulation with Project-scoped API chat

**Files:**
- Modify: `frontend/lib/modules/hologram_hub/widgets/agent_direct_chat_sheet.dart`
- Modify: `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart`
- Create: `frontend/lib/modules/hologram_hub/controllers/direct_agent_chat_controller.dart`
- Test: `frontend/test/modules/hologram_hub/direct_agent_chat_controller_test.dart`

**Interfaces:**
- Controller accepts `projectId`, `profileKey`, `AgentChatService`, and an SSE stream factory.
- It creates/reuses a Project conversation and returns durable run state; it never returns a local fabricated assistant answer.

- [ ] Write failing controller tests for message request fields `project_id`, `active_agent_profile`, and `data_access`, plus a network failure that leaves no assistant response.
- [ ] Run `cd frontend && flutter test test/modules/hologram_hub/direct_agent_chat_controller_test.dart`; expect missing controller.
- [ ] Implement controller using `AgentChatService.createConversation`, `sendMessage`, and run event streaming. Pass active Project and profile from Hub.
- [ ] Remove `AgentsService.testRunAgent`, `_generateSpecialistResponse`, and all local fallback success text from this sheet.
- [ ] Re-run focused Flutter tests and existing Hologram Hub tests.

### Task 11: Create Company tasks only after API success

**Files:**
- Modify: `frontend/lib/modules/hologram_hub/controllers/direct_agent_chat_controller.dart`
- Modify: `frontend/lib/modules/hologram_hub/widgets/agent_direct_chat_sheet.dart`
- Modify: `frontend/lib/modules/tasks/services/task_service.dart`
- Test: `frontend/test/modules/hologram_hub/direct_agent_chat_controller_test.dart`

**Interfaces:**
- `createTaskFromResponse(projectId, conversationId, messageId, title, body)` returns the persisted task id.

- [ ] Write failing tests for API success, API failure, absent Project, and retry with a stable idempotency key.
- [ ] Run focused Flutter test; expect no such method and current toast-only behavior.
- [ ] Call `/operations/tasks` through `TaskService.createTypedTask` with required `projectId` and a stable idempotency key; expose the returned task id.
- [ ] Render success only after result; retain the response and render retryable error on failure.
- [ ] Re-run focused Flutter tests.

### Task 12: Remove non-real Hub test execution and untruthful navigation

**Files:**
- Modify: `frontend/lib/modules/hologram_hub/views/hologram_hub_view.dart`
- Modify: `frontend/lib/modules/agents/views/widgets/agent_test_run_drawer.dart`
- Modify: `frontend/lib/core/routing/module_routes.dart`
- Test: `frontend/test/modules/hologram_hub/hologram_hub_view_test.dart`
- Test: `frontend/test/core/routing/module_routes_test.dart`

**Interfaces:**
- Hub has no test-run CTA until a durable sandbox execution endpoint exists.
- Non-live modules are visibly unavailable and excluded from actionable navigation.

- [ ] Write failing widget tests that reject the test-run success toast and verify planned module entries cannot expose an execution CTA.
- [ ] Run focused Flutter tests; expect current simulated action.
- [ ] Remove the test-run drawer from Hub and route planned navigation through an explicit unavailable presentation without action buttons.
- [ ] Re-run focused tests and `make frontend-test`.

### Task 13: Update and add process E2E evidence

**Files:**
- Modify: `tests/e2e/test_executive_advisory_board.py`
- Modify: role-profile E2E files using deprecated Project activation
- Modify: `tests/e2e/test_ai_compliance_company_http.py`
- Create: `tests/e2e/test_advisor_overlay_process_e2e.py`
- Create: `tests/e2e/test_hub_real_action_process_e2e.py`

**Interfaces:**
- E2E uses Workspace role activation, Project deployment, exact overlay pin, and explicit Project-scoped conversations.

- [ ] Write failing process tests for successful advisor frame/run/callback, cross-project denial, overlay drift, paused deployment before resume, API chat, and task creation.
- [ ] Configure disposable PostgreSQL credentials from the actual dev environment; do not treat an authentication setup failure as a code failure.
- [ ] Update stale endpoint and DTO assertions to current Workspace-office and Project-deployment APIs.
- [ ] Run focused E2E tests, then `make e2e-test` and `make e2e-cross-plane-smoke`.
- [ ] Record separately any environment-blocked PostgreSQL result and the exact configuration needed to unblock it.

## Final verification

- [ ] `make lint`
- [ ] `make typecheck-py`
- [ ] `make agent-test`
- [ ] `make apps-cosa-test`
- [ ] `make services-test-company`
- [ ] `make services-test-cosa`
- [ ] `make frontend-test`
- [ ] `make e2e-test`
- [ ] `make e2e-cross-plane-smoke`
- [ ] Inspect `git diff` and `git status --short`; preserve unrelated changes and report all environment-blocked checks separately.

## Self-review

The plan covers every acceptance criterion in the linked spec: exact frame
pins (Tasks 1-5), runtime execution and callback safety (Tasks 6-7), workflow
execution correctness (Task 8), registry atomicity (Task 9), truthful Hub
actions (Tasks 10-12), and process evidence (Task 13). It contains no
floating asset resolution or fake-success behavior. Execution is intentionally
not started by this planning artifact.
