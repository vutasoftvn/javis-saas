# AgentOS Authorization, Contract and Frontend Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close confirmed AgentOS workspace-authorization gaps, restore reliable release gates, and make unavailable Flutter backend features visible rather than silently empty.

**Architecture:** `get_authenticated_identity` remains the sole browser-facing authority for workspace membership. A small shared helper turns that identity into a workspace scope and mutation privilege; every affected AgentOS router consumes it rather than reading a client workspace ID. Quality tests seed the same runtime inventory as production. Flutter preserves its existing gateway client but exposes typed failures and removes its obsolete direct Extensions transport.

**Tech Stack:** Python 3.11/FastAPI/Pydantic/pytest, TypeScript/Encore/Vitest, Flutter/Dart/flutter_test, GitHub Actions, Caddy, PostgreSQL.

**Spec:** `docs/architecture/reports/2026-08-31-agentos-auth-contract-parity-audit.md`.

## Global Constraints

- Work directly on `main`; do not create a worktree.
- `workspace_id` comes only from `AuthenticatedIdentity` after Company membership verification. An input workspace ID may be validated for equality during a compatibility period, but never selected as scope.
- Do not weaken a quality gate, skip a failing test, use an in-memory production fallback, or replace a negative authorization test with a mock-only assertion.
- Resource lookup and mutation use the verified workspace; an out-of-scope resource returns 404 to avoid enumeration.
- No raw bearer token, exception string, prompt content or internal pinned-skill detail is sent in a conversation message, SSE event, metric, audit record or response body.
- Do not run migrations, full E2E or integration commands against a developer's active database during this work. Use the isolated unit commands listed below; staging validation needs separate authorization.
- This plan supplements, rather than edits or supersedes, `docs/superpowers/plans/2026-08-31-backend-frontend-security-quality-remediation.md`. Coordinate the single `.github/workflows/quality.yml` change with that plan's Task 6.

## Delivery order

| Wave | Deliverable | Release gate |
| --- | --- | --- |
| 1 | Shared AgentOS workspace/role guard and event-rule protection | Cross-workspace and unauthenticated tests fail closed |
| 2 | Event operations, autopilot and skill-registry protection | No browser route trusts a supplied workspace |
| 3 | Error, cache and readiness hardening | No internal exception egress; bounded cache; meaningful readiness |
| 4 | Runtime-seed test repair and enforced CI gates | `agent-test`, `apps-cosa-test`, contract freeze green |
| 5 | Honest Flutter unavailable states and Extensions retirement | Flutter reports a failed backend contract, never fake-empty data |

## File map

| Path | Responsibility after this plan |
| --- | --- |
| `apps/cosa/auth/dependency.py` | Identity-derived workspace comparison, privileged-role guard and bounded resolve cache. |
| `apps/cosa/api/event_rule_routes.py` | Authenticated, privileged event-rule create/enable; approval actor derived server-side. |
| `apps/cosa/api/event_operations_routes.py` | Scoped correlation/dead-letter read and privileged retry with real not-found semantics. |
| `apps/cosa/api/autopilot_metrics_routes.py` | Authenticated metrics scoped to identity; unavailable aggregates are explicitly null. |
| `apps/cosa/api/skill_registry_routes.py` | Cannot override workspace when listing/getting skills; privileged custom-skill mutation. |
| `apps/cosa/worker/handlers.py` | Client-safe unexpected-failure event and server-side diagnostic log. |
| `apps/cosa/api/app.py` | Distinct liveness/readiness routes based on concrete dependencies. |
| `tests/apps/cosa/test_event_rule_admin.py` | Event rule authentication, role and scope regressions. |
| `tests/apps/cosa/test_event_operations.py` | Event operations authentication, scope and retry regressions. |
| `tests/apps/cosa/test_autopilot_metrics.py` | Metrics authentication and scope regressions. |
| `tests/apps/cosa/test_skill_registry_routes.py` | Query-override and privilege regressions. |
| `tests/apps/cosa/test_pilot_capability_boundary.py` | Runtime capability registry assertion, not removed static constant. |
| `tests/apps/cosa/compliance/test_run_delegation.py` and `tests/apps/cosa/worker/test_handlers.py` | Runtime seed fixture matching production. |
| `tests/agent/registry/test_skill_resolution.py` | Built-in manifest seed using a real capability inventory. |
| `.github/workflows/quality.yml` | Mandatory isolated AgentOS unit test gate. |
| `frontend/lib/modules/strategy/services/strategy_service.dart` | Explicit `StrategyApiException` for unavailable/transport/malformed list results. |
| `frontend/lib/modules/settings/services/extensions_service.dart` | Deleted obsolete direct HTTP transport. |
| `frontend/lib/modules/settings/views/settings_extensions_page.dart` | Explicit unavailable state until a separately specified Extension contract exists. |

### Task 1: Add one reusable AgentOS workspace and privilege guard

**Files:**
- Modify: `apps/cosa/auth/dependency.py:25-215`
- Modify: `apps/cosa/auth/__init__.py:1-28`
- Create: `tests/apps/cosa/auth/test_workspace_access.py`

**Interfaces:**
- Produces: `resolve_identity_workspace(identity, requested_workspace_id: str | None = None) -> str`.
- Produces: `require_workspace_operator(identity) -> AuthenticatedIdentity`.
- Rule: an unequal supplied workspace raises 404; roles other than `founder`, `co-founder`, `admin` raise 403.

- [ ] **Step 1: Write the failing helper tests**

```python
def test_workspace_scope_cannot_be_overridden():
    identity = make_identity(workspace_id="ws-a", role_id="member")
    assert resolve_identity_workspace(identity) == "ws-a"
    with pytest.raises(HTTPException) as error:
        resolve_identity_workspace(identity, "ws-b")
    assert error.value.status_code == 404

def test_workspace_operator_requires_privileged_role():
    with pytest.raises(HTTPException) as error:
        require_workspace_operator(make_identity(role_id="member"))
    assert error.value.status_code == 403
```

- [ ] **Step 2: Run the focused test red**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/auth/test_workspace_access.py -q`

Expected: FAIL because neither shared helper exists.

- [ ] **Step 3: Implement the two helpers and export them**

```python
_WORKSPACE_OPERATOR_ROLES = frozenset({"founder", "co-founder", "admin"})

def resolve_identity_workspace(identity: AuthenticatedIdentity, requested_workspace_id: str | None = None) -> str:
    if requested_workspace_id is not None and requested_workspace_id != identity.workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    return identity.workspace_id

def require_workspace_operator(identity: AuthenticatedIdentity) -> AuthenticatedIdentity:
    if (identity.role_id or "").lower() not in _WORKSPACE_OPERATOR_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="workspace operator role required")
    return identity
```

Do not make the identity dependency optional in any new route. Export both helpers from `apps.cosa.auth` for router imports.

- [ ] **Step 4: Run focused tests and static checks**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/auth/test_workspace_access.py -q && make lint typecheck-py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/cosa/auth/dependency.py apps/cosa/auth/__init__.py tests/apps/cosa/auth/test_workspace_access.py
git commit -m "fix(agentos): centralize workspace authorization guards"
```

### Task 2: Protect Event Rule creation, listing and activation

**Files:**
- Modify: `apps/cosa/api/event_rule_routes.py:22-125`
- Modify: `tests/apps/cosa/test_event_rule_admin.py:1-140`

**Interfaces:**
- Consumes: `identity: AuthenticatedIdentity = Depends(get_authenticated_identity)`.
- Produces: `POST /agent/events/rules` and `POST /agent/events/rules/{rule_id}/enable` require an operator; `GET` requires membership.
- Request contract: `CreateRuleRequest` and `EnableRuleRequest` contain no `workspaceId` or `approvedBy`.

- [ ] **Step 1: Write hostile request tests before changing route models**

Use `override_authenticated_identity` in the existing fixture. Add all four tests:

```python
async def test_rule_routes_reject_missing_identity(unsecured_client):
    response = await unsecured_client.post("/agent/events/rules", json=valid_rule_payload())
    assert response.status_code == 401

async def test_member_cannot_create_or_enable_rule(member_client):
    assert (await member_client.post("/agent/events/rules", json=valid_rule_payload())).status_code == 403

async def test_list_uses_identity_workspace_not_query(operator_client):
    response = await operator_client.get("/agent/events/rules", params={"workspaceId": "other"})
    assert response.status_code == 404

async def test_write_approval_actor_is_derived(operator_client):
    response = await operator_client.post(f"/agent/events/rules/{write_rule_id}/enable", json={})
    assert response.json()["approvedBy"] == "operator-user"
```

- [ ] **Step 2: Run the focused router suite red**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/test_event_rule_admin.py -q`

Expected: FAIL: no-token creation succeeds, member role is not checked, and request JSON controls workspace/approver.

- [ ] **Step 3: Derive all mutable scope and approval data server-side**

Make route signatures explicit:

```python
async def create_rule(body: CreateRuleRequest, request: Request,
                      identity: AuthenticatedIdentity = Depends(get_authenticated_identity)):
    require_workspace_operator(identity)
    workspace_id = identity.workspace_id

async def list_rules(request: Request,
                     identity: AuthenticatedIdentity = Depends(get_authenticated_identity),
                     workspaceId: str | None = Query(None)):
    workspace_id = resolve_identity_workspace(identity, workspaceId)
```

Use the same identity workspace when fetching a rule; call `require_workspace_operator` before all enables, including `artifact_only`. For a gate requiring human approval, derive `approved_by = identity.platform_user_id`; never read `body.approvedBy`. Update the test helper payloads to omit removed fields and attach the authenticated identity override.

- [ ] **Step 4: Verify the focused route and event-policy suites**

Run:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/test_event_rule_admin.py tests/apps/cosa/events/test_trigger_evidence_wiring.py tests/apps/cosa/events/test_run_counter_and_auth.py -q
```

Expected: PASS; an authorized rule stays disabled until the existing evidence policy permits it.

- [ ] **Step 5: Commit**

```bash
git add apps/cosa/api/event_rule_routes.py tests/apps/cosa/test_event_rule_admin.py
git commit -m "fix(agentos): authorize event rule administration"
```

### Task 3: Scope Event Operations and make retry truthful

**Files:**
- Modify: `apps/cosa/api/event_operations_routes.py:1-144`
- Modify: `tests/apps/cosa/test_event_operations.py:1-160`

**Interfaces:**
- Consumes: verified identity, optional legacy `workspaceId` query only for equality verification.
- Produces: correlation/dead-letter reads scoped to identity; retry requires operator role and returns 404 when the scoped event does not exist.

- [ ] **Step 1: Replace plane-field authorization tests with request-identity tests**

Delete `caller_workspace_id` from the fake plane; it is not an HTTP security boundary. Add these cases using two app instances with separate `override_authenticated_identity` calls:

```python
async def test_missing_identity_cannot_read_correlation(unsecured_client, seeded_chain):
    assert (await unsecured_client.get(f"/agent/events/correlation/{seeded_chain.correlation_id}")).status_code == 401

async def test_workspace_b_gets_not_found_for_workspace_a_chain(client_b, seeded_chain):
    response = await client_b.get(f"/agent/events/correlation/{seeded_chain.correlation_id}")
    assert response.status_code == 404

async def test_member_cannot_retry_and_missing_event_is_not_success(member_client, operator_client):
    assert (await member_client.post("/agent/events/missing/retry")).status_code == 403
    assert (await operator_client.post("/agent/events/missing/retry")).status_code == 404
```

- [ ] **Step 2: Run it red**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/test_event_operations.py -q`

Expected: FAIL because the request has no identity and a missing event returns `{"status":"retried"}`.

- [ ] **Step 3: Replace all `workspaceId` ownership decisions**

Inject identity into the three endpoints, compute `workspace_id = resolve_identity_workspace(identity, workspaceId)`, and remove `caller_workspace_id` handling. For retry, invoke `require_workspace_operator(identity)` then raise `HTTPException(404, "event not found")` after the loop rather than returning a no-op success.

- [ ] **Step 4: Run focused verification**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/test_event_operations.py tests/apps/cosa/test_event_stream.py -q`

Expected: PASS; correlation chain output remains redacted and only the correct workspace receives it.

- [ ] **Step 5: Commit**

```bash
git add apps/cosa/api/event_operations_routes.py tests/apps/cosa/test_event_operations.py
git commit -m "fix(agentos): scope event operations to identity"
```

### Task 4: Protect Autopilot Metrics and stop reporting invented values

**Files:**
- Modify: `apps/cosa/api/autopilot_metrics_routes.py:7-60`
- Modify: `tests/apps/cosa/test_autopilot_metrics.py:1-80`

**Interfaces:**
- Produces: `GET /agent/autopilot/metrics` requires identity and scopes all run reads to `identity.workspace_id`.
- Produces: `approvalLatencyP95Sec`, `takeoverAfterAutopilotRate`, `unsafeProposalRate`, `policyViolationCount`, and `runDeadLetterCount` are nullable until a durable source exists; they are never fabricated as zero.

- [ ] **Step 1: Add failing authentication, isolation and null-semantics tests**

```python
async def test_metrics_require_identity(unsecured_client):
    assert (await unsecured_client.get("/agent/autopilot/metrics")).status_code == 401

async def test_metrics_ignore_cross_workspace_query(member_a_client):
    response = await member_a_client.get("/agent/autopilot/metrics?workspaceId=ws_metric_b")
    assert response.status_code == 404

async def test_unknown_aggregates_are_null(metrics_client):
    data = (await metrics_client.get("/agent/autopilot/metrics")).json()
    assert data["approvalLatencyP95Sec"] is None
```

- [ ] **Step 2: Run focused tests red**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/test_autopilot_metrics.py -q`

Expected: FAIL because the endpoint accepts the query scope and emits zeros.

- [ ] **Step 3: Change model semantics and route dependency**

```python
class AutopilotMetricsResponse(BaseModel):
    workspaceId: str
    runsDispatched: int
    runsCompleted: int
    runsHandedOff: int
    containmentRate: float
    approvalLatencyP95Sec: float | None = None
    takeoverAfterAutopilotRate: float | None = None
    unsafeProposalRate: float | None = None
    policyViolationCount: int | None = None
    runDeadLetterCount: int | None = None
```

Inject identity, validate any temporary query scope with the shared helper, and populate the response workspace from identity. Do not add a fake in-memory aggregate to fill the null fields.

- [ ] **Step 4: Run focused tests plus API type check**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/test_autopilot_metrics.py -q && make typecheck-py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/cosa/api/autopilot_metrics_routes.py tests/apps/cosa/test_autopilot_metrics.py
git commit -m "fix(agentos): authorize autopilot metrics"
```

### Task 5: Remove Skill Registry query override and enforce mutation privileges

**Files:**
- Modify: `apps/cosa/api/skill_registry_routes.py:159-748`
- Modify: `tests/apps/cosa/test_skill_registry_routes.py:1-220`
- Modify: `tests/apps/cosa/test_workspace_custom_skill_isolation.py:1-240`

**Interfaces:**
- Produces: list/get derive their workspace from identity; a legacy `workspace_id` only validates equality and returns 404 otherwise.
- Produces: candidate update and deprecation require the same operator role as promotion.

- [ ] **Step 1: Add negative tenant and role tests**

```python
def test_list_and_get_reject_workspace_query_override(setup_env):
    client = setup_env["client"]
    assert client.get("/agent/skills?workspace_id=ws-other").status_code == 404
    assert client.get("/agent/skills/private-skill?workspace_id=ws-other").status_code == 404

def test_member_cannot_update_or_deprecate_workspace_skill(member_env):
    assert member_env["client"].put("/agent/skills/private-skill", json={"instructions": "altered"}).status_code == 403
    assert member_env["client"].post("/agent/skills/private-skill/deprecate", json={"reason": "x"}).status_code == 403
```

- [ ] **Step 2: Run the focused test files red**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/test_skill_registry_routes.py tests/apps/cosa/test_workspace_custom_skill_isolation.py -q`

Expected: FAIL because list/get select `workspace_id` query and mutations accept any membership.

- [ ] **Step 3: Apply the shared guard to every affected route**

At `list_skills` and `get_skill`, replace fallback selection with:

```python
ws_id = resolve_identity_workspace(identity, workspace_id)
```

At `update_skill` and `deprecate_skill`, call `require_workspace_operator(identity)` before the candidate store lookup. Keep promote's existing approval behavior but replace its local role set with the shared helper so the policy has exactly one definition. Update tests so normal lifecycle actions use a founder identity and tests deliberately switch to member identity for rejection.

- [ ] **Step 4: Verify the registry suite**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/test_skill_registry_routes.py tests/apps/cosa/test_workspace_custom_skill_isolation.py tests/apps/cosa/api/test_skillpack_mapper.py -q`

Expected: PASS; built-in synchronization stays unaffected and candidate content cannot cross a workspace.

- [ ] **Step 5: Commit**

```bash
git add apps/cosa/api/skill_registry_routes.py tests/apps/cosa/test_skill_registry_routes.py tests/apps/cosa/test_workspace_custom_skill_isolation.py
git commit -m "fix(agentos): enforce skill workspace and operator scope"
```

### Task 6: Bound authorization cache, redact errors and expose honest readiness

**Files:**
- Modify: `apps/cosa/auth/dependency.py:121-154`
- Modify: `apps/cosa/worker/handlers.py:400-417`
- Modify: `apps/cosa/api/app.py:164-174`
- Modify: `tests/apps/cosa/auth/test_workspace_access.py`
- Modify: `tests/apps/cosa/worker/test_handlers.py`
- Modify: `tests/apps/cosa/test_app_lifecycle.py`

**Interfaces:**
- Produces: cache with `COSA_WORKSPACE_RESOLVE_CACHE_MAX_ENTRIES` default `10_000`, pruning expired entries then oldest entries before insert.
- Produces: `GET /live` means process is alive; `GET /ready` returns 503 if plane is absent or configured event dependencies are unavailable; `/healthz` delegates to readiness for deployment compatibility.
- Produces: unexpected worker failures publish `{ "error": "internal_error" }`; full exception is logged only with `run_id`.

- [ ] **Step 1: Add failing regression tests**

```python
async def test_workspace_cache_is_bounded(monkeypatch):
    monkeypatch.setattr(dependency, "_RESOLVE_CACHE_MAX_ENTRIES", 2)
    await resolve_three_distinct_workspace_contexts()
    assert len(dependency._resolve_cache) == 2

@pytest.mark.asyncio
async def test_unexpected_worker_error_is_not_sent_to_client(plane, stream_mgr):
    plane.kernel.run = AsyncMock(side_effect=RuntimeError("internal-pin-and-secret"))
    await execute_run_task(plane, stream_mgr, payload())
    assert "internal-pin-and-secret" not in await all_client_visible_text(plane)

def test_readiness_reports_missing_dependencies():
    app = create_cosa_app(plane=SimpleNamespace())
    with TestClient(app) as client:
        assert client.get("/ready").status_code == 503
```

- [ ] **Step 2: Run focused tests red**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/auth/test_workspace_access.py tests/apps/cosa/worker/test_handlers.py tests/apps/cosa/test_app_lifecycle.py -q`

Expected: FAIL for unlimited cache, raw exception egress and missing readiness route.

- [ ] **Step 3: Implement bounded cache, sanitized error and readiness**

Before cache insertion, remove expired entries and evict the entry with the oldest timestamp while `len(cache) >= max_entries`. In the worker's broad exception branch, use `logger.exception("agent run failed", extra={"run_id": run_id})`, append a stable Vietnamese client message without `exc`, and emit only `{"error": "internal_error"}`. `/ready` checks the plane and only dependencies actually configured for that deployment; it must not perform a network request on each probe.

- [ ] **Step 4: Run focused and broad AgentOS checks**

Run:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/apps/cosa/auth/test_workspace_access.py tests/apps/cosa/worker/test_handlers.py tests/apps/cosa/test_app_lifecycle.py -q
make lint typecheck-py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/cosa/auth/dependency.py apps/cosa/worker/handlers.py apps/cosa/api/app.py tests/apps/cosa
git commit -m "fix(agentos): bound auth state and redact runtime failures"
```

### Task 7: Repair runtime-seed regression tests and route inventory

**Files:**
- Modify: `tests/apps/cosa/test_pilot_capability_boundary.py:1-90`
- Modify: `tests/apps/cosa/compliance/test_run_delegation.py:1-390`
- Modify: `tests/apps/cosa/worker/test_handlers.py:1-150`
- Modify: `tests/agent/registry/test_skill_resolution.py:1-100`
- Modify: generated route inventory files reported by `make route-inventory`

**Interfaces:**
- Consumes: `seed_cosa_runtime_specs(spec_registry=..., capability_registry=...)` in every test that resolves pinned skills or executes a real run.
- Produces: capability assertions use `plane.capability_registry.list_specs()`; there is no import of a removed static capability constant.

- [ ] **Step 1: Make current regressions explicit**

Run:

```bash
make route-inventory-check
make agent-test
make apps-cosa-test
```

Expected: route snapshot failure; static constant import failure; and seed-related failures for pinned lifecycle skills.

- [ ] **Step 2: Replace static capability and partial-seed fixtures**

Delete the duplicate `REGISTERED_STATIC_CAPABILITY_IDS` test and its import; `test_pilot_capability_registration_boundaries` already makes the correct registry assertion. In the run/delegation and worker tests, replace:

```python
await seed_cosa_agent_specs(plane.spec_registry)
```

with:

```python
await seed_cosa_runtime_specs(
    spec_registry=plane.spec_registry,
    capability_registry=plane.capability_registry,
)
```

In `test_skill_resolution.py`, construct a real `CosaAgentPlane` and call the same runtime seed rather than passing a `MagicMock` capability registry to `sync_built_in_skills`.

- [ ] **Step 3: Update tests whose policy contracts intentionally changed**

For `commercial.experiment.write`, add a `metric_contract_id` or documented metric-contract reference to each successful test payload. Retain a negative test asserting the handler rejects a missing metric contract. Do not relax the production guard.

- [ ] **Step 4: Regenerate only intentional route artifacts**

Run: `make route-inventory`

Inspect the diff: it must include the new `/operations/projects` and Strategy list endpoints and removal of their obsolete `/strategy/projects` mapping, with no unrelated generated changes. Then run:

```bash
make route-inventory-check
make agent-test
make apps-cosa-test
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/apps/cosa tests/agent/registry/test_skill_resolution.py docs scripts
git commit -m "test: align runtime fixtures and route inventory"
```

### Task 8: Make the full AgentOS unit suite an enforced CI contract

**Files:**
- Modify: `.github/workflows/quality.yml:331-390`
- Modify: `Makefile:47-52,136-138` only if the CI command needs a named non-mutating target

**Interfaces:**
- Produces: a `quality-apps-cosa` CI job invoking `make apps-cosa-test` with isolated empty database environment, uploading its coverage artifact only after tests complete.

- [ ] **Step 1: Add the failing workflow-contract assertion**

Create `tests/quality/test_quality_workflow.py` that parses `.github/workflows/quality.yml` and asserts a job runs `make apps-cosa-test`:

```python
def test_quality_workflow_runs_full_apps_cosa_unit_suite():
    workflow = Path(".github/workflows/quality.yml").read_text()
    assert "make apps-cosa-test" in workflow
```

- [ ] **Step 2: Run it red**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/quality/test_quality_workflow.py -q`

Expected: FAIL because the current workflow only runs the agent unit subset.

- [ ] **Step 3: Add an isolated job, not a second partial command**

Copy Python setup/cache conventions from `quality-unit`, install `packages/agent/requirements.txt` and `apps/cosa/requirements.txt`, then execute:

```yaml
- name: AgentOS application unit tests
  run: make apps-cosa-test
```

Do not add PostgreSQL or an integration marker: this target intentionally clears database URLs and must remain deterministic. Upload an `apps-cosa-coverage.xml` artifact if coverage XML is generated; otherwise omit the artifact rather than uploading an empty placeholder.

- [ ] **Step 4: Verify workflow and local target**

Run:

```bash
PYTHONPATH=. .venv/bin/python -m pytest tests/quality/test_quality_workflow.py -q
make apps-cosa-test
make contract-freeze-check
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/quality.yml Makefile tests/quality/test_quality_workflow.py
git commit -m "ci: require AgentOS application unit tests"
```

### Task 9: Stop Strategy list failures from masquerading as empty data

**Files:**
- Modify: `frontend/lib/modules/strategy/services/strategy_service.dart:15-75` and every list caller in that file
- Modify: `frontend/test/strategy_service_test.dart:1-190`
- Create: `frontend/lib/modules/strategy/models/strategy_list_result.dart`
- Create: `frontend/test/modules/strategy/strategy_list_result_test.dart`

**Interfaces:**
- Produces: `StrategyListResult<T>` with `items`, `isUnavailable`, and `errorMessage`.
- Rule: HTTP 404 becomes unavailable only where the endpoint is known optional; 401/403/409/5xx, malformed JSON and transport failures preserve an actionable error. No catch-all returns `[]`.

- [ ] **Step 1: Add failing result-model and service tests**

```dart
test('getCanvases exposes unavailable instead of an empty success on 404', () async {
  ApiClient.client = MockClient((_) async => http.Response('missing', 404));
  final result = await StrategyService().getCanvasesResult();
  expect(result.items, isEmpty);
  expect(result.isUnavailable, isTrue);
});

test('getProjects preserves a network failure', () async {
  ApiClient.client = MockClient((_) async => throw const SocketException('offline'));
  final result = await StrategyService().getProjectsResult();
  expect(result.errorMessage, isNotEmpty);
});
```

- [ ] **Step 2: Run the tests red**

Run: `cd frontend && flutter test test/strategy_service_test.dart test/modules/strategy/strategy_list_result_test.dart`

Expected: FAIL because result methods/types do not exist and current methods return empty lists.

- [ ] **Step 3: Implement one typed list decoding path and migrate callers**

```dart
final class StrategyListResult<T> {
  const StrategyListResult.success(this.items) : isUnavailable = false, errorMessage = null;
  const StrategyListResult.unavailable() : items = const [], isUnavailable = true, errorMessage = null;
  const StrategyListResult.failure(this.errorMessage) : items = const [], isUnavailable = false;
  final List<T> items;
  final bool isUnavailable;
  final String? errorMessage;
}
```

Have `_decodeList` return `StrategyListResult<Map<String, dynamic>>`; only an explicitly optional 404 maps to `unavailable`. Update every `get*` list method currently catching and returning `[]`; then update its view/controller to render retry/unavailable copy rather than an empty-state success.

- [ ] **Step 4: Run focused Flutter verification**

Run:

```bash
cd frontend && flutter test test/strategy_service_test.dart test/modules/strategy && flutter analyze
```

Expected: PASS. A 500 and a disconnected client must be visually distinguishable from an empty successful response.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/modules/strategy frontend/test/strategy_service_test.dart frontend/test/modules/strategy
git commit -m "fix(frontend): expose strategy endpoint failures"
```

### Task 10: Retire the unauthenticated Extensions transport until its contract exists

**Files:**
- Delete: `frontend/lib/modules/settings/services/extensions_service.dart`
- Modify: `frontend/lib/modules/settings/views/settings_extensions_page.dart:1-150`
- Create: `frontend/test/modules/settings/settings_extensions_page_test.dart`

**Interfaces:**
- Produces: a read-only unavailable panel with no HTTP request and copy stating that workspace extensions are not yet available in this release.
- Rule: the frontend does not call `/api/v1/workspaces/{workspaceId}/extensions` until an approved Company/Control-Plane endpoint and DTO exist.

- [ ] **Step 1: Write the widget test**

```dart
testWidgets('extensions page makes no legacy network request and explains unavailability', (tester) async {
  ApiClient.client = MockClient((request) async => fail('Extensions page must not call ${request.url}'));
  await tester.pumpWidget(const MaterialApp(home: SettingsExtensionsPage()));
  await tester.pumpAndSettle();
  expect(find.textContaining('chưa khả dụng'), findsOneWidget);
});
```

- [ ] **Step 2: Run it red**

Run: `cd frontend && flutter test test/modules/settings/settings_extensions_page_test.dart`

Expected: FAIL because the page constructs `ExtensionsService` and invokes the legacy request.

- [ ] **Step 3: Remove the obsolete service and network lifecycle**

Delete the service. Replace loading, toggle mutation and retry code in the page with a stateless unavailable panel. Remove unused `http`, `baseUrl`, `workspaceId`, extension list and status-toggle imports. Do not substitute a mock list or an optimistic local toggle.

- [ ] **Step 4: Verify Flutter surface and search for forbidden route**

Run:

```bash
cd frontend && flutter test test/modules/settings/settings_extensions_page_test.dart && flutter analyze
! rg -n '/api/v1/workspaces/.*/extensions|ExtensionsService' lib test
```

Expected: PASS and no obsolete route remains.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/modules/settings/services/extensions_service.dart frontend/lib/modules/settings/views/settings_extensions_page.dart frontend/test/modules/settings/settings_extensions_page_test.dart
git commit -m "fix(frontend): disable unsupported extensions transport"
```

### Task 11: Publish endpoint ownership truth and release evidence

**Files:**
- Modify: `docs/implementation/frontend-endpoint-inventory-2026-08-28.md`
- Modify: `CLAUDE.md` only for confirmed broken normative links
- Modify: `docs/architecture/reports/2026-08-31-agentos-auth-contract-parity-audit.md`
- Create: `docs/operations/release-checklists/agentos-authorization-parity.md`

**Interfaces:**
- Produces: an endpoint inventory whose unsupported Strategy/Lenses/Validation entries are explicitly `UNAVAILABLE`, with owner and approved next-contract spec required before UI exposure.
- Produces: release checklist containing exact build SHA, gate output, two-workspace authorization evidence and staging approval placeholders that are not marked complete locally.

- [ ] **Step 1: Write the release checklist and update inventory status**

Use this non-negotiable checklist section:

```markdown
- [ ] `make contract-freeze-check`, `make agent-test`, `make apps-cosa-test`, Flutter tests and analyzer passed at SHA: ______.
- [ ] A no-token request returned 401 for Event Rule, Event Operations, Autopilot Metrics and Skill Registry.
- [ ] A workspace-B identity received 404 for a workspace-A rule, correlation chain, candidate skill and metrics query override.
- [ ] A member identity received 403 for rule create/enable, event retry, skill update and skill deprecation.
- [ ] Staging owner recorded date, environment, trace/correlation IDs and reviewer: ______.
```

Change stale endpoint mappings only after comparing them to the generated route inventory. Mark older reports that describe the deleted legacy backend as historical, not normative; do not rewrite historical conclusions.

- [ ] **Step 2: Verify documentation integrity**

Run: `make check-docs && git diff --check`

Expected: PASS.

- [ ] **Step 3: Run the final isolated release gate**

Run:

```bash
make lint typecheck-py boundary-check skillpacks-validate
make contract-freeze-check
make agent-test
make apps-cosa-test
cd frontend && flutter test && flutter analyze
cd ../landing && npm test -- --run && npm run lint && npm run build
```

Expected: every command PASS. Do not run database-mutating integration/E2E commands without a dedicated disposable environment.

- [ ] **Step 4: Commit the documentation-only release evidence**

```bash
git add docs/implementation/frontend-endpoint-inventory-2026-08-28.md docs/architecture/reports/2026-08-31-agentos-auth-contract-parity-audit.md docs/operations/release-checklists/agentos-authorization-parity.md CLAUDE.md
git commit -m "docs: record AgentOS authorization and parity release gates"
```

## Explicit follow-up plans

These are intentionally not implemented in this release-hardening plan because their missing business semantics cannot be safely inferred from the old Flutter routes:

1. **Strategy/Lenses contract parity:** an owner-approved spec for each canvas, lens and project lifecycle route; Company DTO, handler, Flutter model and migration change together.
2. **Validation Engine contract parity:** one separate plan defining persistence, authorization, lifecycle and DTOs for sessions, claims, risk matrix, hypotheses and interviews before exposing the current 15+ callers.
3. **Maintainability program:** feature-scoped GetX bindings, split large controller/service files by bounded context, gradual removal of `as any`, dependency upgrades and a production-backed Autopilot aggregate store.

## Plan self-review

- Authorization coverage: Tasks 1–5 protect every confirmed unauthenticated or cross-workspace AgentOS router and add hostile tests.
- Quality coverage: Tasks 7–8 repair current failures and ensure future app-suite failures block CI.
- Frontend coverage: Tasks 9–10 remove silent empty states and obsolete unauthenticated transport without inventing backend behavior.
- Operational coverage: Task 6 bounds state, redacts errors and differentiates liveness/readiness; Task 11 records release proof.
- Placeholder scan: no task depends on an unspecified implementation. The only deferred product work is explicitly excluded and requires a separate approved contract.
