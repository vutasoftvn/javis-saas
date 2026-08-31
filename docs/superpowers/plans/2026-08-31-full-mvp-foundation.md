# Full MVP Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every MVP frontend/backend capability explicit, typed, failure-preserving and mechanically checked before domain routes are migrated.

**Architecture:** `shared/contracts/mvp-surface.json` is the single editable capability manifest. A small generator produces read-only language metadata for TypeScript, Python and Dart; a check script proves frontend references, server routes, source kinds and test-only fixture boundaries. Company and Agent response helpers expose the same successful envelope, while Flutter turns all non-2xx/network/parse outcomes into `ApiFailure` rather than empty success values.

**Tech Stack:** JSON/Node.js generation; Python repository checks; TypeScript Encore; Python FastAPI/Pydantic; Flutter/Dart `http`; Vitest, pytest and Flutter test.

**Spec:** `docs/superpowers/specs/2026-08-31-full-mvp-contract-first-truth-only-design.md`

## Global Constraints

- `shared/contracts/mvp-surface.json` is the source of truth. Generated files are never hand-edited.
- A capability is enabled only when its route, owner, schema, Flutter consumer, source kind, backend test, Flutter test and real integration test are present.
- `populated` and `empty` are the only successful `data_state` values. `unavailable` and `not_connected` are failures, not empty lists.
- Test fakes are allowed only in test files and must not be imported by `frontend/lib`, `services/**`, `apps/cosa/**` or `packages/agent/**` runtime code.
- Production/staging keeps explicit URLs and secrets fail-closed. A development loopback default may remain only behind `ENVIRONMENT=development`; it does not create fallback data.
- Preserve Snowflake IDs as strings at HTTP and Dart boundaries.

---

## File map

| File | Responsibility |
|---|---|
| `shared/contracts/mvp-surface.json` | Editable IDs, route/method/owner/schema/source/test declarations for every enabled MVP capability |
| `shared/contracts/mvp-response.schema.json` | Language-neutral success/error envelope definitions |
| `scripts/gen-mvp-contracts.mjs` | Generates language route metadata from the manifest |
| `scripts/mvp_surface_check.py` | Checks manifest completeness, generated output, route implementation, enabled client calls and forbidden runtime fixture imports |
| `services/company/shared/contracts/mvp-surface.generated.ts` | Generated Company route metadata |
| `services/company/shared/contracts/mvp-response.ts` | Company `MvpSuccess`, source and response helper types |
| `apps/cosa/api/mvp_contracts_generated.py` | Generated Agent route metadata |
| `apps/cosa/api/mvp_response.py` | Agent Pydantic success/error envelope helpers |
| `frontend/lib/core/network/mvp_endpoints.g.dart` | Generated `MvpEndpoint` metadata used by all new clients |
| `frontend/lib/core/network/api_result.dart` | `ApiResult`, `ApiFailureDetail`, `ApiResponseMeta` and decoding rules |
| `frontend/lib/core/network/mvp_request_client.dart` | Typed authenticated requests using an `MvpEndpoint` without legacy normalization |
| `frontend/lib/core/network/api_client.dart` | Low-level HTTP, auth headers, documented plane selection and development-only configuration validation |
| `frontend/lib/core/network/workspace_scoped_service.dart` | Deprecated compatibility base; no new MVP service may inherit it after this plan |
| `frontend/test/core/network/api_result_test.dart` | Failure and success-envelope decoding tests |
| `frontend/test/core/network/mvp_request_client_test.dart` | Contracted request/header/plane tests using a test-only fake transport |
| `tests/quality/test_mvp_surface_check.py` | Pytest coverage of check-script failures |
| `Makefile` | `mvp-contracts-gen`, `mvp-contracts-check` and `mvp-surface-check` targets |

## Task 1: Define and generate the MVP capability manifest

**Files:**

- Create: `shared/contracts/mvp-surface.json`
- Create: `shared/contracts/mvp-response.schema.json`
- Create: `scripts/gen-mvp-contracts.mjs`
- Create: `services/company/shared/contracts/mvp-surface.generated.ts`
- Create: `apps/cosa/api/mvp_contracts_generated.py`
- Create: `frontend/lib/core/network/mvp_endpoints.g.dart`
- Test: `tests/quality/test_mvp_surface_check.py`
- Modify: `Makefile`

**Interfaces:**

- Produces `MvpCapability` fields: `id`, `enabled`, `owner`, `plane`, `method`, `path`, `schema`, `source_kind`, `requires_workspace`, `frontend_symbol`, `backend_test`, `flutter_test`, and `integration_test`.
- Produces `MvpEndpoint.byId(String id)` in Dart, `MVP_CAPABILITIES` in TypeScript, and `MVP_CAPABILITIES` in Python.
- Later plans consume capability IDs exactly; no client writes a raw string route for an enabled MVP surface.

- [ ] **Step 1: Write the manifest-validation tests first.**

  Create test cases that pass a complete minimal capability and reject the truth-policy violations below:

  ```python
  def test_enabled_capability_requires_real_source_and_all_proofs(tmp_path: Path) -> None:
      manifest = {"version": "2026-08-31", "capabilities": [{
          "id": "strategy.canvas.list", "enabled": True,
          "owner": "company-operations", "plane": "company",
          "method": "GET", "path": "/operations/strategy/canvases",
          "schema": "strategy.canvas.list.v1", "source_kind": "company_db",
          "requires_workspace": True, "frontend_symbol": "StrategyClient.listCanvases",
          "backend_test": "services/company/operations/tests/mvp-canvas-runtime.test.ts",
          "flutter_test": "frontend/test/strategy_mvp_service_test.dart",
          "integration_test": "tests/e2e/test_mvp_strategy_runtime_http.py",
      }]}
      assert validate_manifest(manifest) == []

  def test_enabled_capability_rejects_runtime_fixture_source() -> None:
      errors = validate_manifest({"version": "2026-08-31", "capabilities": [{
          "id": "bad", "enabled": True, "owner": "company-operations", "plane": "company",
          "method": "GET", "path": "/operations/bad", "schema": "bad.v1",
          "source_kind": "fixture", "requires_workspace": True, "frontend_symbol": "Bad.client",
          "backend_test": "a", "flutter_test": "b", "integration_test": "c",
      }]})
      assert "source_kind" in "\n".join(errors)
  ```

- [ ] **Step 2: Run the focused test and verify the absent checker fails.**

  Run: `PYTHONPATH=$(pwd) python3 -m pytest tests/quality/test_mvp_surface_check.py -q`

  Expected: FAIL because `scripts.mvp_surface_check.validate_manifest` does not exist.

- [ ] **Step 3: Create the manifest and response schema with exact allowed values.**

  Put the following schema rules in `shared/contracts/mvp-response.schema.json`; use this shape in both server helpers and Dart decoding:

  ```json
  {
    "$id": "javis.mvp.response.v1",
    "success": {
      "required": ["data", "meta"],
      "meta": {
        "required": ["data_state", "observed_at", "sources"],
        "data_state": ["populated", "empty"]
      }
    },
    "failure_codes": ["unauthenticated", "forbidden", "not_found", "invalid_request", "conflict", "unavailable", "not_connected", "rate_limited", "malformed_response", "unknown"]
  }
  ```

  Add all final capability groups to the manifest: Strategy/Execution, Workspace Runtime, Workforce, Vault/Knowledge, Marketing, and Settings. Set `enabled` to `false` until the matching sub-plan's backend and Flutter tests exist; the final plan flips every listed group to `true` only after verification. Do not create an entry with `source_kind: fixture`, `mock`, `demo`, `synthetic`, or `unknown`.

- [ ] **Step 4: Implement deterministic generation and run it.**

  `scripts/gen-mvp-contracts.mjs` must sort by `id`, reject duplicate `id`/`method path`, and emit only route metadata. Its generated Dart shape is:

  ```dart
  enum MvpEndpoint {
    strategyCanvasList(
      id: 'strategy.canvas.list',
      plane: ApiPlane.company,
      method: 'GET',
      path: '/operations/strategy/canvases',
      requiresWorkspace: true,
    );

    const MvpEndpoint({required this.id, required this.plane, required this.method,
      required this.path, required this.requiresWorkspace});
    final String id;
    final ApiPlane plane;
    final String method;
    final String path;
    final bool requiresWorkspace;
  }
  ```

  Run: `node scripts/gen-mvp-contracts.mjs`

  Expected: the three generated files are created/updated in stable sorted order.

- [ ] **Step 5: Add Make targets and prove stale generated output fails.**

  Add these targets without removing the existing enum contract targets:

  ```make
  mvp-contracts-gen:
	$(NODE) scripts/gen-mvp-contracts.mjs

  mvp-contracts-check:
	$(NODE) scripts/gen-mvp-contracts.mjs --check

  mvp-surface-check:
	$(PYTHON) scripts/mvp_surface_check.py --check
  ```

  Run: `make mvp-contracts-check`

  Expected: PASS after generation; edit one generated route locally, run again, and expect a non-zero stale-generated-output error before restoring via the generator.

- [ ] **Step 6: Commit the manifest spine.**

  ```bash
  git add shared/contracts/mvp-surface.json shared/contracts/mvp-response.schema.json \
    scripts/gen-mvp-contracts.mjs services/company/shared/contracts/mvp-surface.generated.ts \
    apps/cosa/api/mvp_contracts_generated.py frontend/lib/core/network/mvp_endpoints.g.dart \
    tests/quality/test_mvp_surface_check.py Makefile
  git commit -m "feat: add mvp contract manifest"
  ```

## Task 2: Add honest success/failure envelopes in Company and Agent Platform

**Files:**

- Create: `services/company/shared/contracts/mvp-response.ts`
- Create: `apps/cosa/api/mvp_response.py`
- Modify: `services/company/operations/handlers/index.ts`
- Modify: `services/company/commercial/handlers/index.ts`
- Modify: `apps/cosa/api/routes.py`
- Test: `services/company/operations/tests/mvp-response.test.ts`
- Test: `tests/apps/cosa/test_mvp_response.py`

**Interfaces:**

- Produces `mvpList<T>(items, sources, observedAt)` and `mvpItem<T>(item, sources, observedAt)` in Company.
- Produces `MvpSuccess[T]`, `mvp_list()` and `mvp_item()` in Agent Platform.
- Domain routes from later plans return `MvpSuccess<T>` for 2xx requests and their framework-native typed error for non-2xx requests.

- [ ] **Step 1: Write the response helper tests.**

  ```ts
  it("marks an authorized zero-row query empty without hiding its source", () => {
    expect(mvpList([], [{ kind: "company_db", ref: "operating.tasks" }], observedAt)).toEqual({
      data: [],
      meta: { dataState: "empty", observedAt: observedAt.toISOString(), sources: [{ kind: "company_db", ref: "operating.tasks" }] },
    });
  });
  ```

  ```python
  def test_mvp_list_never_accepts_unavailable_as_success() -> None:
      with pytest.raises(ValueError, match="data_state"):
          MvpResponseMeta(data_state="unavailable", observed_at=datetime.now(UTC), sources=[])
  ```

- [ ] **Step 2: Run the focused tests and verify they fail.**

  Run:

  ```bash
  cd services/company && npx vitest run operations/tests/mvp-response.test.ts
  PYTHONPATH=$(pwd) python3 -m pytest tests/apps/cosa/test_mvp_response.py -q
  ```

  Expected: failures caused by the missing helper modules.

- [ ] **Step 3: Implement the helpers without an error-to-empty branch.**

  Use these TypeScript types exactly:

  ```ts
  export type MvpDataState = "populated" | "empty";
  export interface MvpSourceRef { kind: "company_db" | "agent_db" | "object_store" | "control_plane" | "external_connector"; ref: string; observedAt?: string; }
  export interface MvpResponseMeta { dataState: MvpDataState; observedAt: string; sources: readonly MvpSourceRef[]; }
  export interface MvpSuccess<T> { data: T; meta: MvpResponseMeta; }
  ```

  `mvpList` derives `dataState` from `items.length`; `mvpItem` always returns `populated`. Neither function catches an exception, receives an HTTP response, or accepts a status code. Let `APIError`/`HTTPException` propagate intact.

- [ ] **Step 4: Assert serialization parity.**

  Add matching TypeScript/Python assertions for `data/meta`, camelCase Company fields and snake_case Agent fields only where the endpoint schema declares them. Keep `data_state`/`observed_at` transport naming consistent with each plane and let the Flutter endpoint decoder normalize the documented variation.

  Run the two focused suites again. Expected: PASS.

- [ ] **Step 5: Commit the envelope helpers.**

  ```bash
  git add services/company/shared/contracts/mvp-response.ts apps/cosa/api/mvp_response.py \
    services/company/operations/tests/mvp-response.test.ts tests/apps/cosa/test_mvp_response.py
  git commit -m "feat: add truthful mvp response envelopes"
  ```

## Task 3: Build Flutter's typed, failure-preserving request path

**Files:**

- Create: `frontend/lib/core/network/api_result.dart`
- Create: `frontend/lib/core/network/mvp_request_client.dart`
- Modify: `frontend/lib/core/network/api_client.dart`
- Modify: `frontend/lib/core/network/workspace_scoped_service.dart`
- Test: `frontend/test/core/network/api_result_test.dart`
- Test: `frontend/test/core/network/mvp_request_client_test.dart`

**Interfaces:**

- Produces `Future<ApiResult<T>> MvpRequestClient.request<T>(MvpEndpoint endpoint, {Map<String, String> query, Object? body, required T Function(Object?) decode})`.
- Produces `ApiFailureDetail(code, statusCode, message, retryAfter, endpointId)`.
- Later Flutter domain clients call `MvpRequestClient`; they do not call `WorkspaceScopedService.getJson` or construct direct legacy routes.

- [ ] **Step 1: Write failing tests for real empty, 403 and malformed JSON.**

  ```dart
  test('403 remains forbidden rather than an empty success', () async {
    final result = await client.request<List<String>>(
      MvpEndpoint.strategyCanvasList,
      decode: (json) => (json as List<Object?>).cast<String>(),
    );
    expect(result, isA<ApiFailure<List<String>>>());
    expect((result as ApiFailure<List<String>>).failure.code, 'forbidden');
  });

  test('a successful empty envelope remains empty with metadata', () async {
    final result = await client.request<List<String>>(
      MvpEndpoint.strategyCanvasList,
      decode: (json) => (json as List<Object?>).cast<String>(),
    );
    expect((result as ApiSuccess<List<String>>).meta.dataState, ApiDataState.empty);
  });
  ```

- [ ] **Step 2: Run the Dart tests and verify the imports fail.**

  Run: `cd frontend && flutter test test/core/network/api_result_test.dart test/core/network/mvp_request_client_test.dart`

  Expected: FAIL because `api_result.dart` and `mvp_request_client.dart` do not exist.

- [ ] **Step 3: Implement `ApiResult` and request decoding.**

  `ApiResult` is a sealed hierarchy and must preserve all failures. Map response status exactly as follows:

  ```dart
  const statusToFailure = <int, ApiFailureCode>{
    401: ApiFailureCode.unauthenticated,
    403: ApiFailureCode.forbidden,
    404: ApiFailureCode.notFound,
    409: ApiFailureCode.conflict,
    429: ApiFailureCode.rateLimited,
  };
  ```

  Map other 4xx to `invalidRequest`, 5xx/socket/timeout to `unavailable`, missing configured external provider to `notConnected` only when that code is returned by the documented contract, and invalid success JSON to `malformedResponse`. Decode a 2xx payload only if it has both `data` and `meta`; reject `meta.data_state` other than `populated`/`empty`.

- [ ] **Step 4: Restrict `ApiClient` to transport and documented plane selection.**

  Add a request helper accepting `MvpEndpoint`; select origin from `endpoint.plane` rather than `normalizeEndpoint`. Send `Authorization` and `X-Workspace-Id` for `requiresWorkspace` endpoints, with the workspace value read once from secure storage. If the workspace is missing, return `ApiFailureCode.unauthenticated`/`invalidRequest` according to the session contract; never substitute `'1'`.

  Keep `normalizeEndpoint` only for unmigrated non-MVP callers during the programme. Mark it deprecated and add a final scan in Task 5; no `MvpRequestClient` call may invoke it. Remove `WorkspaceScopedService` success-null behavior by making its public methods return `ApiResult<dynamic>`; later plans migrate and delete its remaining consumers.

- [ ] **Step 5: Re-run focused tests, then static analysis.**

  Run:

  ```bash
  cd frontend && flutter test test/core/network/api_result_test.dart test/core/network/mvp_request_client_test.dart
  cd frontend && flutter analyze
  ```

  Expected: PASS; test-only fake transport appears only under `frontend/test/`.

- [ ] **Step 6: Commit the typed transport.**

  ```bash
  git add frontend/lib/core/network frontend/test/core/network
  git commit -m "feat: preserve mvp api failures in flutter"
  ```

## Task 4: Make capability/route/truth checks enforceable in CI

**Files:**

- Create: `scripts/mvp_surface_check.py`
- Modify: `tests/quality/test_mvp_surface_check.py`
- Modify: `Makefile`
- Modify: `scripts/route_inventory.py`
- Modify: `docs/architecture/generated/route-inventory.allowlist.json`

**Interfaces:**

- Produces `python3 scripts/mvp_surface_check.py --check [--ledger]`.
- Consumes manifest entries, generated endpoint output, Company Encore route inventory, FastAPI app routes and Dart `MvpEndpoint` references.
- A legacy allowlist entry may remain only for a disabled capability and must name a removal plan; final enabled MVP leaves no such entry.

- [ ] **Step 1: Add failing checker tests for each prohibited condition.**

  ```python
  @pytest.mark.parametrize("runtime_import", [
      'from tests.fixtures.canvas import CANVAS',
      "import '../test/fixtures/workforce.dart'",
      'from __fixtures__.marketing import sample',
  ])
  def test_runtime_fixture_import_is_rejected(runtime_import: str, tmp_path: Path) -> None:
      runtime_file = tmp_path / "runtime.py"
      runtime_file.write_text(runtime_import)
      assert "runtime fixture import" in "\n".join(find_runtime_fixture_imports(tmp_path))
  ```

- [ ] **Step 2: Run the checker test and verify it fails before implementation.**

  Run: `PYTHONPATH=$(pwd) python3 -m pytest tests/quality/test_mvp_surface_check.py -q`

  Expected: FAIL for missing `find_runtime_fixture_imports`, route resolver and generated-file validation.

- [ ] **Step 3: Implement narrow, reviewable checks.**

  The checker must:

  ```python
  ALLOWED_SOURCE_KINDS = {"company_db", "agent_db", "object_store", "control_plane", "external_connector"}
  RUNTIME_ROOTS = ("frontend/lib", "services/company", "services/cosa", "apps/cosa", "packages/agent")
  TEST_IMPORT_MARKERS = ("/test/", "/tests/", "fixtures", "__fixtures__", "mock_data", "demo_data")
  ```

  Check imports/path references, not arbitrary strings such as `Mock` in a comment. Parse the checked-in manifest; compare each enabled `method/path` against the actual Encore/FastAPI route set; compare `frontend_symbol` against a generated endpoint reference; reject duplicate routes and incomplete proof fields. Do not treat the old broad route inventory's two-segment match as final parity for an enabled MVP route.

- [ ] **Step 4: Connect the check to existing generated inventory.**

  Extend `scripts/route_inventory.py` to add a `MVP capability` column for calls made through `MvpEndpoint` and preserve the existing historical inventory. Do not delete the known-broken allowlist manually. Remove an allowlist item only in the same commit that changes its Flutter caller, backend route and generated snapshot.

- [ ] **Step 5: Run all Foundation gates.**

  Run:

  ```bash
  make mvp-contracts-check
  make mvp-surface-check
  make route-inventory
  make company-usage-inventory
  make contract-freeze-check
  ```

  Expected: generated files are synchronized. At this phase, disabled future capabilities are reported as planned, not incorrectly passed as enabled.

- [ ] **Step 6: Commit CI enforcement.**

  ```bash
  git add scripts/mvp_surface_check.py scripts/route_inventory.py tests/quality/test_mvp_surface_check.py \
    Makefile docs/architecture/generated
  git commit -m "test: enforce mvp route and truth contracts"
  ```

## Task 5: Prepare safe domain-client cutover rules

**Files:**

- Modify: `frontend/lib/core/network/workspace_scoped_service.dart`
- Modify: `frontend/lib/core/network/api_client.dart`
- Create: `frontend/test/core/network/legacy_route_guard_test.dart`
- Modify: `scripts/mvp_surface_check.py`

**Interfaces:**

- Consumes every domain plan's `MvpEndpoint` client migration.
- Produces a final rule: enabled MVP files have no direct raw `ApiClient` route literal and no `?? '1'`, `?? 0`, `return []` on HTTP failure, or fallback endpoint invocation.

- [ ] **Step 1: Write a guard test against the confirmed regressions.**

  Scan the enabled MVP client files and assert the following expressions are absent after their migration:

  ```text
  stringWorkspaceId() ?? '1'
  projectId?.toString() ?? '1'
  int.tryParse(weeklyCommitmentId) ?? 0
  if (response.statusCode == 404) return []
  final fallbackResp = await ApiClient.get(
  ```

- [ ] **Step 2: Run it to observe current failure.**

  Run: `cd frontend && flutter test test/core/network/legacy_route_guard_test.dart`

  Expected: FAIL while legacy Strategy, Workforce, Vault and Runtime clients still contain these patterns.

- [ ] **Step 3: Restrict the guard to manifest-enabled source files.**

  Read the generated manifest metadata to determine `frontend_symbol` source file. The test must not block test fixtures or disabled migration work. Each domain plan flips its capability on and removes the matching direct literal/fallback in the same pull request.

- [ ] **Step 4: Run the guard after each domain cutover.**

  Run: `cd frontend && flutter test test/core/network/legacy_route_guard_test.dart`

  Expected: the focused test remains green for every currently enabled capability; a newly enabled raw legacy call fails before review.

- [ ] **Step 5: Commit the guard after the first migrated domain.**

  ```bash
  git add frontend/lib/core/network frontend/test/core/network scripts/mvp_surface_check.py
  git commit -m "test: block legacy fallbacks in enabled mvp clients"
  ```

## Foundation completion gate

Run:

```bash
make mvp-contracts-check
make mvp-surface-check
make contract-freeze-check
cd frontend && flutter test test/core/network && flutter analyze
git diff --check
```

Do not start an enabled domain route without a manifest entry and the typed Flutter request path. Do not enable a domain capability until its subsequent plan has supplied the owner route, its genuine source, the specified backend/Flutter/integration tests and its ledger row.
