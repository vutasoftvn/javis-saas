# COSA Agent Harness Routing & Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add tenant-safe policy-controlled shadow routing, cost provenance and authorized replay/context diagnostics without changing a provider call until a workspace explicitly qualifies for active read-only routing.

**Architecture:** Keep model-route resolution in `apps/cosa/models`; add generic durable evidence contracts/repositories under `packages/agent`; compose a COSA-only harness evaluator before `run_core` creates a routed kernel. `OBSERVE` records a hypothetical decision while executing the existing baseline route. Flutter only renders registered, redacted API projections.

**Tech Stack:** Python 3.12, Pydantic, SQLAlchemy async/PostgreSQL/RLS, OpenAI Agents SDK/LiteLLM adapters, FastAPI, TypeScript/Encore contracts, Flutter/GetX.

**Spec:** `docs/superpowers/specs/2026-09-10-cosa-agent-harness-efficiency-safety-design.md`

## Global Constraints

- Business truth remains in `services/*`; Agent Platform never writes a business database directly.
- Migrations are expand-only; production has no implicit in-memory repository fallback.
- Model-policy precedence remains pinned run → agent profile → workspace → system default.
- A router selects only founder-approved workspace profiles and never exposes raw credential, prompt, Vault text or provider token.
- Default is `OFF`; only `OBSERVE` may be enabled before qualification. `ACTIVE_READ_ONLY` is feature-gated and excludes all effectful/regulatory task classes.
- Approval and retry semantics bind the current `run_id`, `tool_call_id`, `checkpoint_ref` and immutable manifest; cancellation remains terminal.
- Run IDs and Snowflake IDs stay strings through API/JSON/Flutter.

---

## File structure and dependency map

| Path | Responsibility |
|---|---|
| `packages/agent/migrations/006_agent_harness_observability.sql` | Expand-only evidence tables/indexes/RLS for policies, decisions, context plans and enriched usage. |
| `packages/agent/harness/contracts.py` | Stable Pydantic types, enum vocabulary and redaction-safe serialization. |
| `packages/agent/harness/repository.py` | Postgres/in-memory test repositories with workspace setting and conditional idempotent writes. |
| `apps/cosa/harness/policy.py` | COSA risk classification and deterministic eligibility decision. |
| `apps/cosa/harness/routing.py` | Candidate filtering/scoring and mode-specific route decision. |
| `apps/cosa/harness/context_plan.py` | Bounded context plan built from references/counters, not raw content. |
| `apps/cosa/worker/run_core.py` | Pins baseline/selected route, persists evidence, prevents active routing outside policy. |
| `apps/cosa/api/harness_schemas.py`, `apps/cosa/api/harness_routes.py` | Authenticated workspace-scoped settings and redacted diagnostic projection. |
| `apps/cosa/api/app.py`, `shared/contracts/mvp-surface.json` | Router registration and frontend contract inventory. |
| `frontend/lib/modules/agent_harness/**` | Settings, Run Inspector sections and API client/controller/view. |
| `tests/agent/harness/**`, `apps/cosa/tests/**`, `frontend/test/modules/agent_harness/**` | Unit, repository, API, worker and UI truthfulness evidence. |

Task 1 produces persistence/types. Tasks 2–4 consume them. Task 5 exposes only completed evidence. Task 6 renders those contracts. Task 7 is the required process-level qualification gate.

### Task 1: Add durable harness evidence contracts and schema

**Files:**
- Create: `packages/agent/migrations/006_agent_harness_observability.sql`
- Create: `packages/agent/harness/__init__.py`
- Create: `packages/agent/harness/contracts.py`
- Create: `packages/agent/harness/repository.py`
- Create: `tests/agent/harness/test_repository.py`

**Interfaces:**
- Produces `HarnessRoutingMode`, `HarnessPolicyRecord`, `RoutingDecisionRecord`, `ContextPlanRecord`, `CostSource`, and `PostgresHarnessRepository`.
- Consumed by `apps/cosa/harness/policy.py`, `apps/cosa/harness/routing.py`, `apps/cosa/worker/run_core.py` and API routes.

- [ ] **Step 1: Write failing repository/tenant tests**

```python
async def test_repository_scopes_decision_to_workspace(session_factory):
    repo = PostgresHarnessRepository(session_factory)
    await repo.create_policy(HarnessPolicyRecord(workspace_id="ws-a", revision=1, mode="OBSERVE"))
    await repo.record_routing_decision(_decision(workspace_id="ws-a", run_id="run-1"))
    assert await repo.get_routing_decision("ws-a", "run-1") is not None
    assert await repo.get_routing_decision("ws-b", "run-1") is None


async def test_decision_rejects_raw_prompt_and_credential_fields():
    with pytest.raises(ValidationError):
        RoutingDecisionRecord.model_validate({**_decision_dict(), "prompt": "secret"})
```

- [ ] **Step 2: Run the focused test to verify red**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/harness/test_repository.py -q`

Expected: FAIL because `agent.harness` and migration-backed repository do not exist.

- [ ] **Step 3: Implement contracts and the expand-only migration**

```python
class HarnessRoutingMode(StrEnum):
    OFF = "OFF"
    OBSERVE = "OBSERVE"
    ACTIVE_READ_ONLY = "ACTIVE_READ_ONLY"
    SUSPENDED = "SUSPENDED"


class RoutingDecisionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    decision_id: str
    workspace_id: str
    run_id: str
    manifest_hash: str
    policy_revision: int
    mode: HarnessRoutingMode
    baseline_profile_id: str
    selected_profile_id: str
    candidate_profile_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]
```

Create `agent.harness_policies`, `agent.routing_decisions` and `agent.context_plans` with `workspace_id`, immutable run binding, unique `(workspace_id, run_id)` routing decision, and indexes for workspace/time and run lookup. Alter `agent.run_cost_observations` additively for `cost_source`, `price_card_hash`, `routing_decision_id`, `attempt_no`, and `anomaly_code`; backfill only a non-sensitive default source for existing rows. Set the Agent DB workspace setting before every repository transaction and use `INSERT ... ON CONFLICT` only for idempotent identical receipts.

- [ ] **Step 4: Run repository/migration tests**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/agent/harness/test_repository.py -q`

Expected: PASS, including cross-workspace invisibility, immutable decision identity, decimal cost preservation and rejection of extra sensitive fields.

- [ ] **Step 5: Commit the atomic persistence change**

```bash
git add packages/agent/migrations/006_agent_harness_observability.sql packages/agent/harness tests/agent/harness/test_repository.py
git commit -m "feat: persist agent harness evidence"
```

### Task 2: Implement eligibility policy and shadow routing decision

**Files:**
- Create: `apps/cosa/harness/__init__.py`
- Create: `apps/cosa/harness/policy.py`
- Create: `apps/cosa/harness/routing.py`
- Create: `apps/cosa/tests/test_harness_policy.py`
- Create: `apps/cosa/tests/test_harness_routing.py`

**Interfaces:**
- Consumes `ResolvedModelRoute`, `WorkspaceModelPolicy`, `HarnessPolicyRecord`, and `RoutingDecisionRecord`.
- Produces `HarnessEligibilityDecision.evaluate(...)` and `RoutingDecisionService.decide(...)`.

- [ ] **Step 1: Write failing policy tests for hard exclusions**

```python
def test_effectful_or_regulated_run_is_never_eligible_for_active_route():
    result = evaluate_harness_eligibility(
        mode=HarnessRoutingMode.ACTIVE_READ_ONLY,
        task_class="finance",
        required_capability_ids=("financial.transaction.write",),
        has_required_approval=False,
    )
    assert result.eligible is False
    assert result.reason_codes == ("TASK_CLASS_EXCLUDED", "EFFECTFUL_CAPABILITY")


def test_observe_keeps_baseline_even_when_cheaper_candidate_scores_higher():
    decision = service.decide(_observe_input(primary="deepseek", fallbacks=("local",)))
    assert decision.selected_profile_id == "deepseek"
    assert decision.hypothetical_profile_id == "local"
```

- [ ] **Step 2: Run to verify red**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest apps/cosa/tests/test_harness_policy.py apps/cosa/tests/test_harness_routing.py -q`

Expected: FAIL because evaluator and routing service are absent.

- [ ] **Step 3: Implement deterministic candidate filtering and scoring**

Implement a server-owned `TaskRiskClass` enum and reject `finance`, `legal`, `identity`, `permission`, `deployment`, `external_delivery`, `regulated_record`, any non-read capability, all pending approvals, missing manifest/hash and unavailable candidate. Accept only ordered primary/fallback profiles returned from the existing workspace policy; do not enumerate a provider catalog. Score only `estimated_input_tokens`, `required_modality`, `context_window`, rolling health bucket, price-card version and budget headroom. Return reason codes, not raw feature values, in persisted decision.

```python
if inp.policy.mode is HarnessRoutingMode.OBSERVE:
    return decision.with_selected(inp.baseline.profile_id, hypothetical_profile_id=best.profile_id)
if not eligibility.eligible:
    return decision.with_baseline(reason_codes=eligibility.reason_codes)
```

- [ ] **Step 4: Run focused tests**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest apps/cosa/tests/test_harness_policy.py apps/cosa/tests/test_harness_routing.py -q`

Expected: PASS for mode behavior, policy ordered allowlist, health/budget filter, no-candidate fail-closed result and all hard exclusions.

- [ ] **Step 5: Commit the policy boundary**

```bash
git add apps/cosa/harness apps/cosa/tests/test_harness_policy.py apps/cosa/tests/test_harness_routing.py
git commit -m "feat: add policy-bound shadow routing"
```

### Task 3: Add context-plan and usage/cost provenance services

**Files:**
- Create: `apps/cosa/harness/context_plan.py`
- Create: `apps/cosa/harness/usage.py`
- Modify: `packages/agent/workforce/models.py`
- Modify: `packages/agent/workforce/repository.py`
- Create: `apps/cosa/tests/test_harness_context_plan.py`
- Create: `apps/cosa/tests/test_harness_usage.py`

**Interfaces:**
- Consumes run manifest references, provider usage result and `RoutingDecisionRecord`.
- Produces `build_context_plan(...) -> ContextPlanRecord` and `record_usage_observation(...)`.

- [ ] **Step 1: Write redaction and exact-once tests**

```python
def test_context_plan_contains_handles_and_hashes_not_document_text():
    plan = build_context_plan(_manifest_with_vault_ref("doc-1"), token_budget=2_000)
    serialized = plan.model_dump_json()
    assert "doc-1" in serialized
    assert "confidential paragraph" not in serialized


async def test_duplicate_provider_receipt_is_idempotent(repo):
    first = await record_usage_observation(repo, _usage(correlation_id="req-1"))
    second = await record_usage_observation(repo, _usage(correlation_id="req-1"))
    assert second.observation_id == first.observation_id
```

- [ ] **Step 2: Run to verify red**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest apps/cosa/tests/test_harness_context_plan.py apps/cosa/tests/test_harness_usage.py -q`

Expected: FAIL because context/usage services are absent.

- [ ] **Step 3: Implement bounded evidence-only plans**

Build context plans from source category, opaque reference, content hash, token estimate and include/exclude reason. Never serialize prompt text, Vault chunks, artifact content or chain-of-thought. Extend `RunCostObservationRecord` with cost source, price-card hash, routing decision and attempt fields; use `Decimal`, not float, through repository writes. Project a Control Plane aggregate only with an idempotency key `harness-cost:{workspace_id}:{run_id}:{attempt_no}:{provider_correlation_hash}`.

- [ ] **Step 4: Run tests**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest apps/cosa/tests/test_harness_context_plan.py apps/cosa/tests/test_harness_usage.py -q`

Expected: PASS for redaction, token-budget reason, billed/estimate/unavailable semantics, duplicate receipt and decimal precision.

- [ ] **Step 5: Commit usage/context evidence**

```bash
git add apps/cosa/harness/context_plan.py apps/cosa/harness/usage.py packages/agent/workforce apps/cosa/tests/test_harness_context_plan.py apps/cosa/tests/test_harness_usage.py
git commit -m "feat: record harness context and cost provenance"
```

### Task 4: Integrate the harness before provider execution

**Files:**
- Modify: `apps/cosa/composition/agent_plane.py`
- Modify: `apps/cosa/worker/run_core.py`
- Create: `apps/cosa/tests/test_harness_run_core.py`
- Modify: `apps/cosa/observability/metrics.py`

**Interfaces:**
- Consumes `HarnessPolicyEvaluator`, `RoutingDecisionService`, `ContextPlanService`, `PostgresHarnessRepository`.
- Produces a manifest-pinned selected route and structured metrics without changing existing `ModelRouteResolver` precedence.

- [ ] **Step 1: Write integration tests around `run_kernel`**

```python
async def test_observe_calls_only_baseline_and_persists_hypothetical_route(plane, request):
    await run_kernel(plane, _observe_prep(request), workspace_id="ws-1", run_id="run-1")
    assert plane.model_provider_factory.created_profiles == ["baseline"]
    assert (await plane.harness_repository.get_routing_decision("ws-1", "run-1")).hypothetical_profile_id == "cheap"


async def test_cancelled_run_never_starts_provider_fallback(plane, request):
    await plane.repository.mark_cancelled("run-1")
    with pytest.raises(RunCoreError, match="cancelled"):
        await run_kernel(plane, _active_prep(request), workspace_id="ws-1", run_id="run-1")
```

- [ ] **Step 2: Run to verify red**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest apps/cosa/tests/test_harness_run_core.py -q`

Expected: FAIL because `CosaAgentPlane` has no harness services and worker does not persist decisions.

- [ ] **Step 3: Compose and pin the harness**

Inject harness repository/services in `build_cosa_agent_plane()` with a real Postgres factory when `AGENT_DATABASE_URL` exists; test doubles must be explicit. In `run_core`, resolve normal model policy first, create policy/context/decision evidence, and then select a route. For `OBSERVE`, pass the baseline model client. For `ACTIVE_READ_ONLY`, write the selected route/fallback order into the execution manifest before provider invocation. Emit low-cardinality metrics by mode/outcome/reason only.

- [ ] **Step 4: Run focused worker tests**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest apps/cosa/tests/test_harness_run_core.py -q`

Expected: PASS for baseline preservation, active pinning, stale/cancel behavior and absent repository fail-fast.

- [ ] **Step 5: Commit integration**

```bash
git add apps/cosa/composition/agent_plane.py apps/cosa/worker/run_core.py apps/cosa/observability/metrics.py apps/cosa/tests/test_harness_run_core.py
git commit -m "feat: bind harness decisions to agent runs"
```

### Task 5: Expose redacted, authenticated settings and diagnostics APIs

**Files:**
- Create: `apps/cosa/api/harness_schemas.py`
- Create: `apps/cosa/api/harness_routes.py`
- Modify: `apps/cosa/api/app.py`
- Modify: `shared/contracts/mvp-surface.json`
- Create: `apps/cosa/tests/test_harness_routes.py`
- Create: `tests/contracts/test_harness_mvp_surface.py`

**Interfaces:**
- Produces workspace-scoped `get/updateHarnessPolicy`, `getRunHarnessDiagnostics` operations.
- Consumes authenticated identity, optimistic policy revision and Agent Platform repositories.

- [ ] **Step 1: Write backend negative authorization tests**

```python
async def test_foreign_workspace_diagnostics_returns_not_found(client, foreign_token):
    response = await client.get("/agent/harness/runs/run-1", headers=foreign_token)
    assert response.status_code == 404


async def test_policy_update_requires_matching_revision(client, operator_token):
    response = await client.put("/agent/harness/policy", json={"revision": 0, "mode": "OBSERVE"}, headers=operator_token)
    assert response.status_code == 409
```

- [ ] **Step 2: Run to verify red**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest apps/cosa/tests/test_harness_routes.py tests/contracts/test_harness_mvp_surface.py -q`

Expected: FAIL because endpoints and contract entries do not exist.

- [ ] **Step 3: Implement typed projections**

Use `get_authenticated_identity`, `resolve_identity_workspace`, explicit operator/configuration guard and repository-scoped lookup. Responses return route IDs/models, reason codes, cost source/decimal string, counters and references only. Do not return credentials, raw prompt, artifact/document content, local path or provider correlation value. Register all literal frontend paths in MVP surface; unknown query fields fail validation.

- [ ] **Step 4: Run API/contract tests**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest apps/cosa/tests/test_harness_routes.py tests/contracts/test_harness_mvp_surface.py -q && make frontend-api-contract-check`

Expected: PASS with unauthenticated/foreign/stale-revision/secret-redaction negatives.

- [ ] **Step 5: Commit API boundary**

```bash
git add apps/cosa/api/harness_schemas.py apps/cosa/api/harness_routes.py apps/cosa/api/app.py shared/contracts/mvp-surface.json apps/cosa/tests/test_harness_routes.py tests/contracts/test_harness_mvp_surface.py
git commit -m "feat: expose governed harness diagnostics"
```

### Task 6: Deliver truthful Flutter settings and Run Inspector sections

**Files:**
- Create: `frontend/lib/modules/agent_harness/models/harness_models.dart`
- Create: `frontend/lib/modules/agent_harness/services/harness_service.dart`
- Create: `frontend/lib/modules/agent_harness/controllers/harness_controller.dart`
- Create: `frontend/lib/modules/agent_harness/views/harness_settings_view.dart`
- Create: `frontend/lib/modules/agent_harness/views/widgets/run_harness_diagnostics.dart`
- Modify: `frontend/lib/core/routing/module_routes.dart`
- Create: `frontend/test/modules/agent_harness/harness_service_test.dart`
- Create: `frontend/test/modules/agent_harness/harness_view_truthfulness_test.dart`

**Interfaces:**
- Consumes registered API response models only.
- Produces a settings screen and inspector widget that never infer a successful route/cost/replay from missing fields.

- [ ] **Step 1: Write failing service/widget tests**

```dart
test('renders unavailable rather than enabled when diagnostics endpoint fails', () async {
  when(() => client.get(any())).thenThrow(ApiException.unavailable());
  await controller.loadRun('run-1');
  expect(controller.viewState.value, HarnessViewState.unavailable);
});

testWidgets('observe label never presents hypothetical route as executed', (tester) async {
  await tester.pumpWidget(subject(mode: RoutingMode.observe, selected: 'baseline', hypothetical: 'cheap'));
  expect(find.text('Baseline executed'), findsOneWidget);
  expect(find.text('Hypothetical candidate: cheap'), findsOneWidget);
});
```

- [ ] **Step 2: Run to verify red**

Run: `cd frontend && flutter test test/modules/agent_harness/harness_service_test.dart test/modules/agent_harness/harness_view_truthfulness_test.dart`

Expected: FAIL because feature module and models do not exist.

- [ ] **Step 3: Implement minimal registered client/UI**

Route all requests through `ApiClient`; retain workspace/token handling in that client. Serialize money as decimal string and IDs as string. Provide only mode selection permitted by backend response; show `OFF`, `OBSERVE`, `ACTIVE_READ_ONLY`, `SUSPENDED`, `notEligible`, `unavailable`, `forbidden`, `noData`, `pending` and `failed` distinctly. Do not render secret/profile edit controls or active-routing control when backend qualification is absent.

- [ ] **Step 4: Run focused Flutter checks**

Run: `cd frontend && flutter test test/modules/agent_harness/harness_service_test.dart test/modules/agent_harness/harness_view_truthfulness_test.dart && flutter analyze`

Expected: PASS with no raw endpoint literal outside contract conventions.

- [ ] **Step 5: Commit frontend slice**

```bash
git add frontend/lib/modules/agent_harness frontend/lib/core/routing/module_routes.dart frontend/test/modules/agent_harness
git commit -m "feat: show agent harness diagnostics"
```

### Task 7: Qualify observe mode and gate active read-only rollout

**Files:**
- Create: `tests/e2e/test_harness_observe_cross_plane.py`
- Create: `tests/e2e/test_harness_active_read_only_cross_plane.py`
- Modify: `Makefile`
- Create: `docs/architecture/generated/agent-harness-qualification.md`

**Interfaces:**
- Consumes real API/worker/provider fake harness and disposable Postgres stack.
- Produces `make agent-harness-e2e` and a generated qualification report with no production-enable side effect.

- [ ] **Step 1: Write red process tests**

```python
def test_observe_real_worker_executes_baseline_and_records_hypothesis(stack):
    run = stack.submit_read_only_run(mode="OBSERVE")
    assert stack.wait(run).provider_profile == "baseline"
    assert stack.routing_decision(run).hypothetical_profile_id == "cheap"


def test_active_read_only_rejects_finance_and_foreign_workspace(stack):
    assert stack.submit_finance_run(mode="ACTIVE_READ_ONLY").error_code == "TASK_CLASS_EXCLUDED"
    assert stack.get_diagnostics_as_foreign_workspace("run-1").status_code == 404
```

- [ ] **Step 2: Run to verify red**

Run: `source .venv/bin/activate && PYTHONPATH=. python -m pytest tests/e2e/test_harness_observe_cross_plane.py tests/e2e/test_harness_active_read_only_cross_plane.py -q`

Expected: FAIL before the disposable stack fixture and target exist.

- [ ] **Step 3: Wire a disposable-stack target and qualification artifact**

Use dedicated disposable Postgres credentials/DSN, real API/worker processes and a deterministic fake provider that records profile/attempts without prompt retention. The report must contain test case ID, run ID, profile decision, token/cost source, duration and pass/fail only. Make active qualification refuse to run unless explicit non-production workspace allowlist is set.

- [ ] **Step 4: Run evidence gates**

Run: `make agent-harness-e2e && make lint && make typecheck-py && make apps-cosa-test && make frontend-api-contract-check`

Expected: PASS. If the disposable environment is unavailable, record the exact environment blocker and do not enable `ACTIVE_READ_ONLY`.

- [ ] **Step 5: Commit qualification gate**

```bash
git add tests/e2e Makefile docs/architecture/generated/agent-harness-qualification.md
git commit -m "test: qualify agent harness routing rollout"
```
