# Stage-Adaptive AI Operating System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Evolve COSA into a Project-scoped, stage-adaptive AI Operating System that measures AI business value, data readiness, safety, quality, adoption and cost before allowing an initiative to scale.

**Architecture:** Extend the existing Company-owned `strategy.initiatives` aggregate instead of creating a parallel AI-use-case silo. Company owns initiative lifecycle, owners, value/budget/decision records and APIs; Agent Platform owns pinned execution, usage, evaluation and retrieval enforcement; COSA binds the two through exact IDs, outbox events and fail-closed policy snapshots. Delivery is tranche-gated: Discovery/Pilot first, then Validate, then selected Scale; knowledge ingestion and higher autonomy remain separately gated.

**Tech Stack:** Encore.ts + TypeScript + Drizzle + PostgreSQL; Python/FastAPI + SQLAlchemy/Pydantic/OpenAI Agents SDK; Flutter/GetX; `shared/contracts/mvp-surface.json`; disposable PostgreSQL/process E2E.

**Spec:** `docs/superpowers/specs/2026-09-28-stage-adaptive-ai-operating-system-design.md`

## Global Constraints

- Preserve Core as final identity/organization authority, Company as business truth, and `ProjectAgentRunAuthority` as pre-kernel authority.
- All new business records require exact `workspace_id` and `project_id`; never infer a Project, owner, Key Result or Initiative from list order, active UI state or prompt text.
- Reuse and extend `strategy.initiatives`; do not introduce a competing `ai_initiatives` aggregate.
- Release migrations are expand-only. Foreign-key columns get indexes; composite indexes follow actual equality/range read paths; no external HTTP/model call inside a DB transaction.
- Money/cost/value amounts travel as decimal strings plus currency or as `numeric`, never `double`/`float` business values.
- Every state transition needs authenticated actor, `expectedRevision`, idempotency key, reason code and append-only decision/event evidence.
- Agent runs can use less autonomy than an Initiative, never more. T3/external and A3 delegated execution stay unavailable under this plan.
- UI must render `blocked`, `paused`, `unavailable`, `missing` and `invalid` explicitly; never fabricate a success, zero value or current timestamp.
- Static/unit evidence does not prove cross-plane authority or recovery. `SCALED` requires disposable PostgreSQL/process E2E.

## Review Focus

- A legacy Initiative with a missing Project/KR must remain remediation-visible and cannot be promoted; Task 2 adds migration and service tests.
- A caller attempting to promote an Initiative from another Workspace or with a stale revision must receive a typed denial; Task 4 adds authorization/CAS tests.
- A changed AgentSpec/model/knowledge pin must invalidate a prior evaluation; Task 7 adds pin-drift tests.
- A run missing durable Initiative attribution must remain `unattributed`, never be auto-linked from prompt/profile; Task 6 adds ledger tests.
- A revoked owner/delegation or budget hard breach must block future execution without deleting history; Tasks 5 and 8 add negative/restart tests.

---

## File structure and delivery tranches

| Tranche | Deliverable | Primary locations |
|---|---|---|
| T0 | Contract inventory and existing Initiative safety repair | `shared/contracts/`, `services/company/operations/` |
| T1 | AI Initiative foundation, lifecycle, value/data contracts | Company schema, migration, service, handlers, tests |
| T2 | Usage attribution, FinOps and promotion-policy bridge | `packages/agent/migrations/`, `apps/cosa/models/`, `apps/cosa/worker/` |
| T3 | Evaluation suites, release gates, portfolio API/UI | `apps/cosa/assets/`, Company APIs, Flutter project module |
| T4 | Operational review, staged knowledge enablement and E2E | observability, knowledge/Vault, `tests/e2e/` |

Tasks 1–5 ship a working `DISCOVER → PILOT → VALIDATE` slice. Tasks 6–10
ship selected `SCALE_CANDIDATE → SCALED` controls. Tasks 11–13 are separate
enablement gates and must not block non-retrieval initiatives.

### Task 1: Freeze the public contract and inventory existing Initiative behavior

**Files:**
- Modify: `shared/contracts/mvp-surface.json`
- Modify: `scripts/gen-mvp-contracts.mjs`
- Create: `docs/architecture/generated/ai-initiative-capability-inventory.json` (generator-owned)
- Create: `scripts/check-ai-initiative-contract.mjs`
- Test: `tests/contracts/test_ai_initiative_contract.py`

**Interfaces:**
- Consumes: current `project.initiative.write`, Company route inventory and capability matrix.
- Produces: contract IDs `ai.initiative.read`, `ai.initiative.write`, `ai.initiative.transition`, `ai.initiative.portfolio.read`, each with source, owner, auth and evidence fields.

- [ ] **Step 1: Write failing contract tests for the four AI Initiative endpoint IDs and for generated Dart endpoints.**

```python
def test_ai_initiative_contract_routes_have_existing_backend_and_flutter_evidence():
    assert_contract_has_existing_evidence("ai.initiative.transition")
```

- [ ] **Step 2: Run the contract test to verify it fails because the contract IDs do not exist.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/contracts/test_ai_initiative_contract.py -q`

Expected: FAIL naming the missing endpoint ID.

- [ ] **Step 3: Add the contract records and generator validation.**

Require `workspace_id`, explicit `project_id`, typed idempotency header/body where applicable, and source-backed test paths. The generator must derive the inventory; do not hand-edit generated output.

- [ ] **Step 4: Generate contracts and run contract checks.**

Run: `node scripts/gen-mvp-contracts.mjs && node scripts/gen-mvp-contracts.mjs --check && source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/contracts/test_ai_initiative_contract.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the contract slice.**

```bash
git add shared/contracts/mvp-surface.json scripts/gen-mvp-contracts.mjs scripts/check-ai-initiative-contract.mjs tests/contracts/test_ai_initiative_contract.py frontend/lib/core/network/mvp_endpoints.g.dart docs/architecture/generated/ai-initiative-capability-inventory.json
git commit -m "feat(contract): define AI initiative endpoints"
```

### Task 2: Make the existing Initiative aggregate explicitly Project-scoped and migration-safe

**Files:**
- Create: `services/company/operations/migrations/034_ai_initiative_foundation.up.sql`
- Create: `services/company/operations/migrations/034_ai_initiative_foundation.down.sql`
- Modify: `services/company/shared/db/schema/operations.ts:6-30`
- Modify: `services/company/operations/services/initiative.service.ts`
- Test: `services/company/operations/tests/initiative-ai-foundation.test.ts`
- Test: `services/company/operations/tests/initiative-workspace-integrity.test.ts`

**Interfaces:**
- Consumes: existing `strategy.initiatives`, `strategy.initiative_key_results`, `strategy.projects`, `key_results`.
- Produces: `AiInitiative` read type; no create/update path can choose a first Project or first Key Result.

- [ ] **Step 0: Audit existing callers of `createInitiativeAuthorized` before removing the first-Project/first-KR fallback.**

Grep every caller across `services/company` (internal service-to-service calls), `shared/contracts/mvp-surface.json`-generated handlers, and `frontend/lib` (any initiative-creation form/service) for calls that omit `projectId` or `keyResultIds` and currently rely on the fallback at `initiative.service.ts:233-258`. Record findings (caller path, whether it omits either field) directly in this task's PR description or a scratch note — do not skip this because "MVP likely has no such caller." If a real caller is found, Step 4 must add an explicit `projectId`/`keyResultIds` argument at that call site as part of this task, not defer it.

- [ ] **Step 1: Write failing service tests for explicit Project/KR, same-Workspace ownership, and legacy remediation.**

```ts
it("rejects create when projectId or keyResultIds are absent instead of selecting a first row", async () => {
  await expect(createInitiativeService(validWithoutProject, token)).rejects.toThrow("projectId is required");
});

it("marks preexisting incomplete rows NEEDS_REBIND and excludes them from promotion", async () => {
  expect(await getInitiativeGateStatus(legacyId, workspaceId)).toContainEqual("PROJECT_CONTEXT_REQUIRED");
});
```

- [ ] **Step 2: Run the targeted tests to verify the current fallback behavior fails the new expectations.**

Run: `cd services/company && encore test ./operations/tests/initiative-ai-foundation.test.ts ./operations/tests/initiative-workspace-integrity.test.ts`

Expected: FAIL because the service currently resolves a first Project/Key Result.

- [ ] **Step 3: Write migration `034_ai_initiative_foundation.up.sql`.**

Add `initiative_kind`, `lifecycle_state`, `risk_tier`, `autonomy_tier`, `technical_owner_member_id`, `risk_owner_member_id`, `legacy_remediation_state`, and `versioned` timestamps to `strategy.initiatives`; retain existing rows and map them to `DISCOVER` or `NEEDS_REBIND` only from durable columns. Add check constraints through guarded `DO` blocks, indexes on `(workspace_id, project_id, lifecycle_state, updated_at DESC)` and every new FK column. Do not delete, fabricate owner/KR, or call services in the migration.

- [ ] **Step 4: Implement explicit-create and truthful read behavior in `initiative.service.ts`.**

Define `createAiInitiativeInWorkspace(ctx, params)` with required `projectId`, `keyResultIds`, `businessOwnerMemberId`, `initiativeKind`, `riskTier`, and `autonomyTier`. Replace first-row fallback with `APIError.invalidArgument`; resolve Project/KR/member in the same Workspace before insert. Preserve old generic fields for compatibility but return `legacyRemediationState` and never allow legacy rows past `DISCOVER`.

- [ ] **Step 5: Run migration compatibility and service tests.**

Run: `make migration-compat-check && make services-test-company`

Expected: migration compatibility passes; Initiative targeted tests pass.

- [ ] **Step 6: Commit the foundation slice.**

```bash
git add services/company/operations/migrations/034_ai_initiative_foundation.* services/company/shared/db/schema/operations.ts services/company/operations/services/initiative.service.ts services/company/operations/tests/initiative-ai-foundation.test.ts services/company/operations/tests/initiative-workspace-integrity.test.ts
git commit -m "feat(operations): harden AI initiative foundation"
```

### Task 3: Persist append-only value, data-readiness, budget and decision evidence

**Files:**
- Create: `services/company/operations/migrations/035_ai_initiative_evidence.up.sql`
- Create: `services/company/operations/migrations/035_ai_initiative_evidence.down.sql`
- Modify: `services/company/shared/db/schema/operations.ts`
- Create: `services/company/operations/services/ai-initiative-evidence.service.ts`
- Test: `services/company/operations/tests/ai-initiative-evidence.service.test.ts`

**Interfaces:**
- Consumes: `AiInitiative` from Task 2 and existing metric contracts/decision records.
- Produces: `AiValueContract`, `AiDataReadinessAssessment`, `AiBudgetPolicy`, `AiInitiativeDecision`, and `AiValueMeasurement` repository/service methods.

- [ ] **Step 1: Write failing tests for revision append-only behavior and decimal/missing-state preservation.**

```ts
it("rejects VALIDATE evidence without a baseline source reference", async () => {
  await expect(recordValueContract(noBaselineRef)).rejects.toThrow("baseline_source_ref is required");
});

it("stores 12.3400 as a decimal string and never returns 0 for an unavailable measurement", async () => {
  expect(result.latestMeasurement.state).toBe("UNAVAILABLE");
});
```

- [ ] **Step 2: Run the new tests and verify they fail because evidence tables/services do not exist.**

Run: `cd services/company && encore test ./operations/tests/ai-initiative-evidence.service.test.ts`

Expected: FAIL with missing exports/tables.

- [ ] **Step 3: Add migration `035_ai_initiative_evidence.up.sql`.**

Create append-only tables under `strategy`: `ai_initiative_value_contracts`, `ai_initiative_data_readiness_assessments`, `ai_initiative_budget_policies`, `ai_initiative_decisions`, `ai_initiative_value_measurements`. Use `numeric` for amounts, `TEXT`/enum-like check constraints for states, opaque source/evidence refs, and indexes matching `(workspace_id, project_id, initiative_id, created_at DESC)`. Add indexes for all FKs; use partial unique indexes only for one active revision/policy.

- [ ] **Step 4: Implement `AiInitiativeEvidenceService`.**

Expose `recordValueContract`, `recordDataReadinessAssessment`, `setBudgetPolicy`, `recordMeasurement`, and `listEvidence`. Each verifies Initiative/Project/owner scope, creates a new revision rather than updating old evidence, and returns explicit `PRESENT | UNAVAILABLE | INVALID` value state.

- [ ] **Step 5: Run focused service and schema gates.**

Run: `cd services/company && encore test ./operations/tests/ai-initiative-evidence.service.test.ts && npm run typecheck`

Expected: PASS.

- [ ] **Step 6: Commit the evidence slice.**

```bash
git add services/company/operations/migrations/035_ai_initiative_evidence.* services/company/shared/db/schema/operations.ts services/company/operations/services/ai-initiative-evidence.service.ts services/company/operations/tests/ai-initiative-evidence.service.test.ts
git commit -m "feat(operations): persist AI initiative evidence"
```

### Task 4: Implement stage/risk/autonomy transition policy in Company

**Files:**
- Create: `services/company/operations/services/ai-initiative-promotion-policy.ts`
- Create: `services/company/operations/services/ai-initiative-transition.service.ts`
- Create: `services/company/operations/handlers/ai-initiative.handler.ts`
- Modify: `services/company/operations/handlers/index.ts`
- Modify: `services/company/operations/api.ts`
- Test: `services/company/operations/tests/ai-initiative-transition.service.test.ts`
- Test: `services/company/operations/tests/ai-initiative.handler.test.ts`

**Interfaces:**
- Consumes: Task 2 aggregate, Task 3 evidence APIs, `ProjectLifecycleStage`, `TenantContext` and Company decision records.
- Produces: `transitionAiInitiative(params: TransitionAiInitiativeParams, ctx: TenantContext): Promise<AiInitiativeTransitionResult>`.

- [ ] **Step 1: Write transition matrix tests for every valid state edge and important denial.**

```ts
it("allows PILOT to VALIDATE only with baseline, metric, owner, risk and data assessment", async () => {
  await expect(transitionAiInitiative(validPilotToValidate, ctx)).resolves.toMatchObject({ lifecycleState: "VALIDATE" });
});

it("rejects cross-Project evidence and a stale expectedRevision", async () => {
  await expect(transitionAiInitiative(staleOrForeignEvidence, ctx)).rejects.toThrow("Revision conflict");
});

it("rejects DISCOVER to PILOT when approvalStatus is not APPROVED", async () => {
  await expect(transitionAiInitiative(discoverToPilotWithDraftApproval, ctx)).rejects.toThrow("approvalStatus must be APPROVED");
});
```

- [ ] **Step 2: Run the tests and verify they fail because no transition service exists.**

Run: `cd services/company && encore test ./operations/tests/ai-initiative-transition.service.test.ts ./operations/tests/ai-initiative.handler.test.ts`

Expected: FAIL with missing service/route.

- [ ] **Step 3: Implement `evaluateAiInitiativePromotionGates`.**

Signature: `evaluateAiInitiativePromotionGates(input: AiInitiativeGateInput): readonly AiInitiativeGateStatus[]`. Make it a pure function mapping Project stage, lifecycle edge, risk/autonomy tier and evidence identities to required gate codes; do not query DB or call COSA. For the `DISCOVER -> PILOT` edge, `input` must include the initiative's current `approvalStatus`; require `APPROVED` and return a blocking `APPROVAL_STATUS_REQUIRED` gate code otherwise, per spec §6.2/§7.2.

- [ ] **Step 4: Implement `transitionAiInitiative`.**

Use one short Company DB transaction to CAS `revision`, append an `ai_initiative_decisions` record and outbox event. Validate authorization and any COSA-facing pin/evaluation references before the transaction; do not hold DB locks during HTTP calls. Reject A3/T3 requested autonomy with `unsupported_autonomy_tier`.

- [ ] **Step 5: Expose typed transition/read endpoints and register endpoint contracts.**

The handler requires Authorization, `X-Workspace-Id`, explicit `projectId`, `expectedRevision`, idempotency key and reason code. It maps errors to `APIError` classes and returns gate status/read model; it does not import schema/Drizzle.

- [ ] **Step 6: Run Company boundary, handler and test gates.**

Run: `make company-boundary-check && make encore-handler-boundary-check && make ts-suppression-check && cd services/company && encore test ./operations/tests/ai-initiative-transition.service.test.ts ./operations/tests/ai-initiative.handler.test.ts`

Expected: PASS.

- [ ] **Step 7: Commit the transition slice.**

```bash
git add services/company/operations/services/ai-initiative-promotion-policy.ts services/company/operations/services/ai-initiative-transition.service.ts services/company/operations/handlers/ai-initiative.handler.ts services/company/operations/handlers/index.ts services/company/operations/api.ts services/company/operations/tests/ai-initiative-transition.service.test.ts services/company/operations/tests/ai-initiative.handler.test.ts
git commit -m "feat(operations): gate AI initiative promotion"
```

### Task 5: Add durable AI Initiative usage attribution and Project budget enforcement

**Files:**
- Create: `packages/agent/migrations/018_ai_initiative_usage_attribution.sql`
- Create: `packages/agent/migrations/018_ai_initiative_usage_attribution.down.sql`
- Modify: `apps/cosa/models/usage.py`
- Modify: `apps/cosa/worker/run_core.py:376-440`
- Modify: `apps/cosa/composition/agent_plane.py`
- Test: `tests/apps/cosa/models/test_usage_ledger.py`
- Test: `tests/apps/cosa/worker/test_run_core_usage_attribution.py`

**Interfaces:**
- Consumes: durable `initiative_id`, budget-policy snapshot and Project authority injected by Company/COSA command path.
- Produces: `UsageEntry.initiative_id`, `UsageLedger.total_cost_for_initiative(...)`, `InitiativeBudgetDecision` with `WARN | REQUIRE_APPROVAL | PAUSE_INITIATIVE`.

- [ ] **Step 1: Write failing attribution and budget tests.**

```python
async def test_usage_without_durable_initiative_id_is_recorded_unattributed_not_guessed():
    entry = await ledger.record(usage_entry(initiative_id=None))
    assert entry.initiative_id is None

async def test_hard_budget_breach_prevents_model_client_creation_and_emits_pause_code():
    with pytest.raises(UsageBudgetExceeded, match="initiative_budget_paused"):
        await prepare_run(over_budget_initiative)
```

- [ ] **Step 2: Run tests to verify the `initiative_id` interface is absent.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/models/test_usage_ledger.py tests/apps/cosa/worker/test_run_core_usage_attribution.py -q`

Expected: FAIL with unknown `initiative_id`/budget policy API.

- [ ] **Step 3: Add migration 018 and ledger queries.**

Add nullable `initiative_id` to `models.run_usage`, an `(workspace_id, project_id, initiative_id, created_at DESC)` index, and a conservative down migration that refuses rollback when attributed rows exist. Extend SQL INSERT/select parameters and in-memory filtering. Do not store monetary value as float.

- [ ] **Step 4: Thread only durable attribution into `run_core.py`.**

Resolve Initiative from persisted run/command metadata created by Company; reject a mismatched workspace/project. For legacy or non-Initiative runs write null. Call budget check before model construction and persist an event/reason code when deny/pause occurs; do not use raw client metadata.

- [ ] **Step 5: Run Python tests, migration checks and focused worker test.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/models/test_usage_ledger.py tests/apps/cosa/worker/test_run_core_usage_attribution.py -q && make migration-compat-check`

Expected: PASS.

- [ ] **Step 6: Commit the attribution slice.**

```bash
git add packages/agent/migrations/018_ai_initiative_usage_attribution.* apps/cosa/models/usage.py apps/cosa/worker/run_core.py apps/cosa/composition/agent_plane.py tests/apps/cosa/models/test_usage_ledger.py tests/apps/cosa/worker/test_run_core_usage_attribution.py
git commit -m "feat(agent): attribute usage to AI initiatives"
```

### Task 6: Implement Company-to-COSA promotion snapshots and outbox delivery

**Files:**
- Create: `services/company/operations/services/ai-initiative-cosa.client.ts`
- Modify: `services/company/operations/services/ai-initiative-transition.service.ts`
- Modify: `services/company/shared/events/outbox.repository.ts` (existing Company outbox publisher; also review `services/company/events/outbox-relay.service.ts` for delivery wiring)
- Create: `apps/cosa/api/ai_initiative_internal_routes.py`
- Modify: `apps/cosa/api/app.py`
- Test: `services/company/operations/tests/ai-initiative-cosa.client.test.ts`
- Test: `tests/apps/cosa/api/test_ai_initiative_internal_routes.py`

**Interfaces:**
- Consumes: Company transition decision and exact deployment/evaluation/budget references.
- Produces: service-authenticated `AiInitiativePromotionSnapshot` and idempotent `ai.initiative.promoted.v1` inbox/outbox envelope.

- [ ] **Step 1: Write failing cross-plane contract tests for a valid snapshot, retry and mismatch denial.**

```ts
it("persists the outbox event before publishing a SCALE_CANDIDATE decision", async () => {
  expect(await outboxFor(decision.id)).toMatchObject({ eventType: "ai.initiative.promoted.v1" });
});
```

```python
def test_internal_promotion_snapshot_rejects_foreign_project_or_hash_drift(client):
    assert client.post("/internal/ai-initiatives/snapshots", json=foreign_snapshot).status_code == 403
```

- [ ] **Step 2: Run each targeted test and verify it fails before the internal interface exists.**

Run: `cd services/company && encore test ./operations/tests/ai-initiative-cosa.client.test.ts`

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/api/test_ai_initiative_internal_routes.py -q`

Expected: FAIL.

- [ ] **Step 3: Define `AiInitiativePromotionSnapshot` as a shared typed wire contract.**

Include Initiative id/revision, Workspace/Project, lifecycle/autonomy/risk, policy decision id/hash, value/data/budget/evaluation revisions and exact Agent/Workflow/Model/Knowledge pins. No raw evidence body, secrets, prompts or user token travels in the event.

- [ ] **Step 4: Implement Company outbox and COSA idempotent inbox handling.**

Company builds the snapshot after Company authorization and before short transaction commit; delivery retries only the callback. COSA validates service token, scope and immutable pins, stores consumed event ID/hash, and fails closed on mismatch. Do not synchronously execute an Agent from the callback.

- [ ] **Step 5: Run Company/Agent boundary gates and contract tests.**

Run: `make company-boundary-check && make contract-freeze-check && cd services/company && encore test ./operations/tests/ai-initiative-cosa.client.test.ts && source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/api/test_ai_initiative_internal_routes.py -q`

Expected: PASS.

- [ ] **Step 6: Commit the cross-plane snapshot slice.**

```bash
git add services/company/operations/services/ai-initiative-cosa.client.ts services/company/operations/services/ai-initiative-transition.service.ts apps/cosa/api/ai_initiative_internal_routes.py apps/cosa/api/app.py services/company/operations/tests/ai-initiative-cosa.client.test.ts tests/apps/cosa/api/test_ai_initiative_internal_routes.py
git commit -m "feat(cosa): consume governed initiative promotion snapshots"
```

### Task 7: Publish immutable evaluation suites and enforce pin invalidation

**Files:**
- Create: `packages/agent/evaluations/initiative_suite.py`
- Create: `packages/agent/evaluations/repository.py`
- Create: `apps/cosa/assets/initiative_evaluation_service.py`
- Modify: `apps/cosa/assets/internal_routes.py`
- Modify: `apps/cosa/assets/evaluation_service.py`
- Test: `tests/agent/evaluations/test_initiative_suite.py`
- Test: `tests/apps/cosa/assets/test_initiative_evaluation_service.py`

**Interfaces:**
- Consumes: Task 6 promotion snapshot and existing asset registry/evaluation records.
- Produces: `AiEvaluationSuite`, `InitiativeEvaluationResult`, `assert_evaluation_current(snapshot, result)`.

- [ ] **Step 1: Write failing tests for immutable publish and material pin drift.**

```python
def test_agent_spec_hash_change_invalidates_a_passing_initiative_evaluation():
    assert assert_evaluation_current(changed_snapshot, passing_result).code == "evaluation_pin_drift"
```

- [ ] **Step 2: Run tests to verify the suite contracts do not exist.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/evaluations/test_initiative_suite.py tests/apps/cosa/assets/test_initiative_evaluation_service.py -q`

Expected: FAIL.

- [ ] **Step 3: Implement immutable `AiEvaluationSuite` and result contracts.**

Required pin set is AgentSpec/prompt/model route/workflow/capability list/knowledge snapshot plus suite hash. Cases reference authorized fixtures only. Result categories are structural, functional, groundedness, policy safety, cost and latency; unspecified categories remain `NOT_REQUIRED`, never pass by default.

- [ ] **Step 4: Extend evaluation service without weakening existing asset checks.**

Run structural closure first; add functional/groundedness/safety adapters as explicit dependencies. Persist evaluator version and suite/result hashes. Production must return `503` when persistent evaluation storage is absent, matching existing production behavior.

- [ ] **Step 5: Run focused evaluation tests and apps-cosa suite.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/evaluations/test_initiative_suite.py tests/apps/cosa/assets/test_initiative_evaluation_service.py -q && make apps-cosa-test`

Expected: PASS.

- [ ] **Step 6: Commit the evaluation slice.**

```bash
git add packages/agent/evaluations apps/cosa/assets/initiative_evaluation_service.py apps/cosa/assets/internal_routes.py apps/cosa/assets/evaluation_service.py tests/agent/evaluations tests/apps/cosa/assets/test_initiative_evaluation_service.py
git commit -m "feat(agent): add immutable initiative evaluation suites"
```

### Task 8: Gate execution and resume by effective Initiative policy

**Files:**
- Modify: `apps/cosa/worker/handlers.py`
- Modify: `apps/cosa/worker/run_core.py`
- Create: `apps/cosa/governance/initiative_policy.py`
- Modify: `apps/cosa/observability/logging.py`
- Test: `tests/apps/cosa/worker/test_initiative_policy_gate.py`
- Test: `tests/apps/cosa/worker/test_handlers.py`

**Interfaces:**
- Consumes: validated Task 6 snapshot and Task 7 current evaluation result.
- Produces: `assert_initiative_run_allowed(snapshot, run_request) -> InitiativeRunPolicyDecision` and structured machine codes.

- [ ] **Step 1: Write failing tests for lower-autonomy success, higher-autonomy denial, revoked snapshot and resume recheck.**

```python
async def test_resume_fails_closed_when_current_initiative_snapshot_is_revoked():
    result = await resume_waiting_approval(revoked_initiative_run)
    assert result.error == "initiative_policy_revoked_on_resume"
```

- [ ] **Step 2: Run the focused worker tests and verify Initiative policy is not yet enforced.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/worker/test_initiative_policy_gate.py tests/apps/cosa/worker/test_handlers.py -q`

Expected: FAIL.

- [ ] **Step 3: Implement the pure policy evaluator.**

Check scope, lifecycle (`SCALE_CANDIDATE`/`SCALED` only for protected runs), risk/autonomy ceiling, budget status, current evaluation and exact pin identity. Existing `ProjectAgentRunAuthority`, tenant policy and capability approvals run first and remain mandatory.

- [ ] **Step 4: Thread decision into initial execution and approval resume.**

Attach only IDs/hashes/tier fields to allowlisted logs and durable run metadata. On denial emit `run.failed` with a classified code, do not leak raw policy/evidence. On resume fetch current authorized snapshot and deny if revoked/drifted; never reuse an old approval to bypass policy change.

- [ ] **Step 5: Run focused and negative authority tests.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/worker/test_initiative_policy_gate.py tests/apps/cosa/worker/test_handlers.py tests/apps/cosa/models/test_usage_ledger.py -q`

Expected: PASS.

- [ ] **Step 6: Commit the policy enforcement slice.**

```bash
git add apps/cosa/governance/initiative_policy.py apps/cosa/worker/handlers.py apps/cosa/worker/run_core.py apps/cosa/observability/logging.py tests/apps/cosa/worker/test_initiative_policy_gate.py tests/apps/cosa/worker/test_handlers.py
git commit -m "feat(cosa): enforce initiative execution policy"
```

### Task 9: Build the Company portfolio read model and truthful Flutter surface

**Files:**
- Create: `services/company/operations/services/ai-initiative-portfolio.service.ts`
- Create: `services/company/operations/handlers/ai-initiative-portfolio.handler.ts`
- Modify: `services/company/operations/api.ts`
- Create: `frontend/lib/modules/projects/models/ai_initiative_portfolio.dart`
- Create: `frontend/lib/modules/projects/services/ai_initiative_portfolio_service.dart`
- Create: `frontend/lib/modules/projects/controllers/ai_initiative_portfolio_controller.dart`
- Create: `frontend/lib/modules/projects/views/widgets/ai_initiative_portfolio_card.dart`
- Test: `services/company/operations/tests/ai-initiative-portfolio.service.test.ts`
- Test: `frontend/test/modules/projects/ai_initiative_portfolio_controller_test.dart`
- Test: `frontend/test/modules/projects/widgets/ai_initiative_portfolio_card_test.dart`

**Interfaces:**
- Consumes: Tasks 2–5 Company evidence/read models and generated `MvpEndpoint.aiInitiativePortfolioRead`.
- Produces: `getAiInitiativePortfolio(ctx, projectId)` and Flutter states `loading | ready | blocked | unavailable | error`.

- [ ] **Step 1: Write failing backend and Flutter tests for portfolio states.**

```dart
testWidgets('renders Chưa có baseline instead of 0 and blocks scale CTA', (tester) async {
  await tester.pumpWidget(cardFor(missingBaselineInitiative));
  expect(find.text('Chưa có baseline'), findsOneWidget);
  expect(find.byKey(const Key('scale_initiative')), findsNothing);
});
```

- [ ] **Step 2: Run targeted tests and verify the read model/UI are absent.**

Run: `cd services/company && encore test ./operations/tests/ai-initiative-portfolio.service.test.ts`

Run: `cd frontend && flutter test test/modules/projects/ai_initiative_portfolio_controller_test.dart test/modules/projects/widgets/ai_initiative_portfolio_card_test.dart`

Expected: FAIL.

- [ ] **Step 3: Implement a scoped portfolio query and typed API response.**

Join only Initiative evidence, usage aggregates and decision refs within the requested Workspace/Project. Return source states and next required gate; avoid N+1 queries by loading evidence groups with composite filters. Do not aggregate cross-Project data in this first surface.

- [ ] **Step 4: Implement Flutter service/controller/card through `MvpRequestClient`.**

Generate/consume typed endpoint; show latest decision, baseline/target/outcome, cost/adoption/quality/data gate states, and only CTA actions authorized by returned state. No direct literal route or optimistic success.

- [ ] **Step 5: Run UI/API contract and focused tests.**

Run: `make frontend-api-contract-check && cd services/company && encore test ./operations/tests/ai-initiative-portfolio.service.test.ts && cd ../../frontend && flutter test test/modules/projects/ai_initiative_portfolio_controller_test.dart test/modules/projects/widgets/ai_initiative_portfolio_card_test.dart`

Expected: PASS.

- [ ] **Step 6: Commit the portfolio slice.**

```bash
git add services/company/operations/services/ai-initiative-portfolio.service.ts services/company/operations/handlers/ai-initiative-portfolio.handler.ts services/company/operations/api.ts services/company/operations/tests/ai-initiative-portfolio.service.test.ts frontend/lib/modules/projects frontend/test/modules/projects
git commit -m "feat(projects): show governed AI initiative portfolio"
```

### Task 10: Add portfolio review cadence, observability and pause/remediation operations

**Files:**
- Create: `services/company/operations/services/ai-initiative-review.service.ts`
- Create: `services/company/operations/handlers/ai-initiative-review.handler.ts`
- Create: `apps/cosa/observability/initiative_metrics.py`
- Modify: `apps/cosa/observability/metrics.py`
- Modify: `apps/cosa/observability/logging.py`
- Test: `services/company/operations/tests/ai-initiative-review.service.test.ts`
- Test: `tests/apps/cosa/observability/test_initiative_metrics.py`

**Interfaces:**
- Consumes: Initiative/windowed evidence and usage from prior tasks.
- Produces: `recordAiInitiativeReview`, `pauseAiInitiative`, and redacted metrics keyed by Initiative lifecycle/risk/autonomy.

- [ ] **Step 1: Write failing tests for periodic review, pause idempotency and redaction.**

```python
def test_initiative_metric_labels_exclude_prompt_document_and_tool_payload():
    assert set(metric.labels) <= {"initiative_id", "workspace_id", "state", "risk_tier", "autonomy_tier"}
```

- [ ] **Step 2: Run tests to verify review/metrics interfaces are missing.**

Run: `cd services/company && encore test ./operations/tests/ai-initiative-review.service.test.ts`

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/observability/test_initiative_metrics.py -q`

Expected: FAIL.

- [ ] **Step 3: Implement review/decision service and pause command.**

Review computes a bounded-window snapshot from declared metrics/evidence and emits recommendation only. An authorized human owner makes pause/retire/reduce-autonomy decision. A pause immediately blocks new runs via Task 8 policy; it preserves completed runs, usage and audit evidence.

- [ ] **Step 4: Add allowlisted metrics/log fields and alerts.**

Use `initiative_id`, revision, suite ref, budget ref, risk/autonomy, gate result and duration only. Keep prompt/document/tool payload out of labels/log metadata. Add no global quality SLO; metrics are Initiative-scoped.

- [ ] **Step 5: Run tests and narrow quality gates.**

Run: `cd services/company && encore test ./operations/tests/ai-initiative-review.service.test.ts && source ../../.venv/bin/activate && PYTHONPATH=../.. python -m pytest ../../tests/apps/cosa/observability/test_initiative_metrics.py -q`

Expected: PASS.

- [ ] **Step 6: Commit review/observability.**

```bash
git add services/company/operations/services/ai-initiative-review.service.ts services/company/operations/handlers/ai-initiative-review.handler.ts apps/cosa/observability/initiative_metrics.py apps/cosa/observability/metrics.py apps/cosa/observability/logging.py services/company/operations/tests/ai-initiative-review.service.test.ts tests/apps/cosa/observability/test_initiative_metrics.py
git commit -m "feat(operations): review and observe AI initiatives"
```

### Task 11: Make data-readiness enforceable without falsely enabling enterprise knowledge

**Files:**
- Create: `apps/cosa/knowledge/initiative_readiness.py`
- Modify: `apps/cosa/capabilities/enterprise_knowledge_read.py`
- Modify: `apps/cosa/api/vault_routes.py`
- Modify: `packages/agent/knowledge/retrieval.py`
- Test: `tests/apps/cosa/knowledge/test_initiative_readiness.py`
- Test: `tests/apps/cosa/test_vault_document_routes.py`
- Test: `tests/agent/knowledge/test_retrieval_evals.py`

**Interfaces:**
- Consumes: Task 3 data-readiness assessment and Task 6 authoritative promotion snapshot.
- Produces: `assert_initiative_knowledge_allowed(snapshot, request) -> KnowledgeReadinessDecision`.

- [ ] **Step 1: Write failing tests for `NOT_READY`, `CONDITIONAL`, `READY`, tenant isolation and semantic-not-wired behavior.**

```python
async def test_ready_assessment_does_not_enable_semantic_mode_without_pinned_provider_and_eval():
    result = await retrieve_for_initiative(ready_but_unwired_semantic)
    assert result.code == "semantic_retrieval_not_ready"
```

- [ ] **Step 2: Run the knowledge tests to verify the Initiative gate is absent.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/knowledge/test_initiative_readiness.py tests/apps/cosa/test_vault_document_routes.py tests/agent/knowledge/test_retrieval_evals.py -q`

Expected: FAIL.

- [ ] **Step 3: Implement readiness intersection and keep unavailable routes truthful.**

Intersect Initiative snapshot, Workspace/Project scope, source entitlement, source freshness/quality evidence, retrieval mode and evaluation pin. `NOT_READY` denies; `CONDITIONAL` permits only declared lower autonomy; vault routes keep explicit `501` until their existing production dependencies are actually wired.

- [ ] **Step 4: Make retrieval return explicit readiness causes.**

Lexical fallback remains allowed only after authorization. Semantic requires an exact embedding provider/version/dimension plus current evaluation result. Do not accept a caller-provided embedding as proof of production readiness.

- [ ] **Step 5: Run readiness, Vault and retrieval tests.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/knowledge/test_initiative_readiness.py tests/apps/cosa/test_vault_document_routes.py tests/agent/knowledge/test_retrieval_evals.py -q`

Expected: PASS.

- [ ] **Step 6: Commit the readiness gate.**

```bash
git add apps/cosa/knowledge/initiative_readiness.py apps/cosa/capabilities/enterprise_knowledge_read.py apps/cosa/api/vault_routes.py packages/agent/knowledge/retrieval.py tests/apps/cosa/knowledge/test_initiative_readiness.py tests/apps/cosa/test_vault_document_routes.py tests/agent/knowledge/test_retrieval_evals.py
git commit -m "feat(knowledge): gate retrieval by initiative readiness"
```

### Task 12: Ship Vault ingestion and semantic retrieval only as a separately approved capability gate

**Files:**
- Modify: `apps/cosa/knowledge_ingestion/dependencies.py`
- Modify: `apps/cosa/knowledge_ingestion/handler.py`
- Modify: `apps/cosa/api/vault_routes.py`
- Modify: `packages/agent/knowledge/embedding.py`
- Modify: `packages/agent/knowledge/providers/postgres.py`
- Test: `tests/apps/cosa/knowledge_ingestion/test_end_to_end.py`
- Test: `tests/integration/test_mvp_vault_in_process.py`
- Test: `tests/e2e/test_local_knowledge_workspace.py`

**Interfaces:**
- Consumes: Task 11 readiness gate.
- Produces: production-wired lexical ingestion/retrieval first; semantic provider is a later explicit sub-gate.

- [ ] **Step 1: Write failing process-oriented tests for ingest, authorization, citation, revocation, restart and purge/legal-hold behavior.**

```python
def test_revoked_source_is_not_retrievable_after_worker_restart(disposable_stack):
    assert search(disposable_stack, revoked_document_query).citations == []
```

- [ ] **Step 2: Run the tests in the disposable stack and record environmental blockers separately.**

Run: `make e2e-cross-plane-smoke`

Expected: FAIL until ingestion dependencies and durable wiring are implemented; database/environment errors are reported as unverified, not product passes.

- [ ] **Step 3: Wire lexical ingestion end-to-end before exposing Vault routes.**

Use existing quarantine/object-store/publish components, durable source version IDs, workspace authorization and citation provenance. Enable only when persistent dependencies are configured; otherwise retain `501`/`503` truthful states.

- [ ] **Step 4: Design and implement semantic provider as a follow-up only after lexical E2E passes.**

Pin provider/model/version/dimension/residency in an immutable configuration, add migration only if schema requires it, and require evaluation before semantic mode. This sub-step requires a separate ADR approval for provider/data residency selection; do not silently choose one.

- [ ] **Step 5: Run ingestion/retrieval integration and E2E gates.**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/apps/cosa/knowledge_ingestion/test_end_to_end.py tests/integration/test_mvp_vault_in_process.py -q && make e2e-cross-plane-smoke`

Expected: lexical path PASS; semantic result reported only after its approved sub-gate.

- [ ] **Step 6: Commit lexical and semantic work separately.**

```bash
git add apps/cosa/knowledge_ingestion apps/cosa/api/vault_routes.py packages/agent/knowledge tests/apps/cosa/knowledge_ingestion tests/integration/test_mvp_vault_in_process.py tests/e2e/test_local_knowledge_workspace.py
git commit -m "feat(knowledge): wire governed Vault ingestion"
```

### Task 13: Prove the first scaled Initiative through a four-plane recovery E2E

**Files:**
- Create: `tests/e2e/test_ai_initiative_operating_system.py`
- Modify: `tests/e2e/conftest.py` or existing disposable-stack helpers
- Modify: `Makefile`
- Modify: `docs/architecture/generated/ai-initiative-capability-inventory.json` (generated only)

**Interfaces:**
- Consumes: all prior tranches.
- Produces: one repeatable source of release evidence for `SCALED` eligibility.

- [ ] **Step 1: Write the E2E happy-path and negative-case skeleton first.**

```python
def test_scaled_initiative_survives_restart_and_preserves_scope_budget_and_audit(disposable_stack):
    initiative = create_validated_initiative(disposable_stack)
    promote_to_scaled(initiative)
    run = execute_authorized_run(initiative)
    restart_api_and_worker(disposable_stack)
    assert read_portfolio(initiative).usage.run_id == run.id

def test_foreign_project_revoked_owner_and_budget_breach_cannot_execute(disposable_stack):
    ...
```

- [ ] **Step 2: Run the new test and verify it fails until all cross-plane wiring is complete.**

Run: `make e2e-ai-initiative-operating-system`

Expected: FAIL initially; failure must identify the missing durable contract, not be hidden by mocks.

- [ ] **Step 3: Add a Make target that provisions disposable PostgreSQL and starts Company, COSA control plane, API and worker.**

The target must reuse existing stack helpers, set test-only secrets, tear down processes, and never point at developer/production DB URLs.

- [ ] **Step 4: Implement the full proof matrix.**

Cover: valid `DISCOVER → PILOT → VALIDATE → SCALE_CANDIDATE → SCALED`; Project/Workspace denial; stale revision/idempotent retry; evaluation pin drift; budget pause; approval/resume with revocation; restart/recovery; redacted audit correlation; legacy unattributed run remains explicit.

- [ ] **Step 5: Run release gates from repository root.**

Run: `make migration-compat-check && make boundary-check && make frontend-api-contract-check && make e2e-ai-initiative-operating-system`

Expected: PASS only with disposable PostgreSQL/process evidence. If infrastructure blocks execution, report exactly which proof remains unverified.

- [ ] **Step 6: Commit E2E evidence harness.**

```bash
git add tests/e2e/test_ai_initiative_operating_system.py tests/e2e/conftest.py Makefile docs/architecture/generated/ai-initiative-capability-inventory.json
git commit -m "test(e2e): prove governed AI initiative lifecycle"
```

## Final verification and rollout checklist

- [ ] Run `node scripts/gen-mvp-contracts.mjs --check` and `make frontend-api-contract-check`.
- [ ] Run Company typecheck/tests, `make apps-cosa-test`, targeted Agent tests, boundary/suppression/migration gates, and `git diff --check`.
- [ ] Run `make e2e-ai-initiative-operating-system` against disposable PostgreSQL; separately record a blocked environment if it cannot run.
- [ ] Release only T1/T2 first with `DISCOVER → PILOT → VALIDATE`; hold `SCALED` endpoints behind policy until Task 13 evidence is green.
- [ ] Enable budget policies in `WARN`, observe bounded windows, then require explicit owner decision before `REQUIRE_APPROVAL` or `PAUSE_INITIATIVE`.
- [ ] Do not enable Vault/semantic retrieval or A3/T3 from this plan unless Task 12's separate gates and ADR are approved.
