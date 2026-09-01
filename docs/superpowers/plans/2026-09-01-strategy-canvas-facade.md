# Strategy Canvas Facade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the active Strategy Canvas CRUD path to the typed Company MVP transport while preserving the Foundation and Hologram callers' current contracts and behaviour.

**Architecture:** Add a small `features/strategy` vertical slice: strict Canvas domain objects, a repository that uses `MvpRequestClient` and generated endpoints, and a public facade. `CanvasService` becomes the one explicit adapter from that typed feature to legacy maps and `StrategyListResult`; detail/revision/AI/Foundation methods remain on the proven legacy path. `StrategyMvpClient` delegates its Canvas summary methods to the facade but retains its public return types for compatibility.

**Tech Stack:** Flutter/Dart 3.12, `flutter_test`, `http` `MockClient`, existing `MvpRequestClient`, generated MVP endpoints, Node.js boundary scanner, Company Vitest, Python real HTTP E2E.

**Spec:** `docs/superpowers/specs/2026-09-01-strategy-canvas-facade-design.md`

## Global Constraints

- All Canvas CRUD requests use only `MvpEndpoint.strategyCanvasCreate`, `strategyCanvasList`, `strategyCanvasGet`, `strategyCanvasUpdate`, and `strategyCanvasDelete` via `MvpRequestClient`.
- Canvas IDs, workspace IDs, names, and timestamps are required non-empty strings; no decoder may replace a missing value with an empty string.
- `description`, `currentRevisionId`, and `createdByMemberId` remain nullable and must be either a string or `null` when present.
- Preserve `StrategyService`, `CanvasService`, `FoundationController`, and `HubStageMixin` method signatures and their legacy maps; a create result must still contain top-level `id`.
- Keep `getCanvasDetail`, revision actions, AI generation, review, and Foundation persistence on their present legacy routes in this slice.
- Feature code below `frontend/lib/features/strategy` may not import `ApiClient`, `SecureStorageService`, or `WorkspaceScopedService`; it receives transport/context only through `MvpRequestClient`.
- Do not change Company routes, Company data contracts, schema/migrations, Hologram activation order, or UI state in this plan.
- No fake repository test is evidence for live endpoint availability; keep the existing Company runtime and real HTTP E2E checks as release evidence.
- Commit only the files named by the completed task after its focused tests pass; push only after the full verification task passes.

---

### Task 1: Define strict Canvas feature contracts

**Files:**
- Create: `frontend/lib/features/strategy/domain/canvas_summary.dart`
- Create: `frontend/lib/features/strategy/domain/canvas_commands.dart`
- Create: `frontend/lib/features/strategy/application/canvas_repository.dart`
- Create: `frontend/test/features/strategy/domain/canvas_summary_test.dart`

**Interfaces:**
- Produces `CanvasSummary.fromJson(Map<String, dynamic>)`, `CanvasSummary.toLegacyMap()`, `CreateCanvasCommand`, and `UpdateCanvasCommand`.
- Produces `CanvasRepository` with `list`, `get`, `create`, `update`, and `delete` operations returning `ApiResult` values.
- Consumes only `package:frontend/core/network/api_result.dart`; these contracts do not perform I/O.

- [ ] **Step 1: Write failing decoder and command tests.**

  In `frontend/test/features/strategy/domain/canvas_summary_test.dart`, define one full Company response fixture and assert the intended typed and compatibility shapes:

  ```dart
  final json = {
    'id': '9223372036854775807',
    'workspaceId': 'ws_1001',
    'name': 'Lean Canvas',
    'description': null,
    'currentRevisionId': 'rev_1',
    'createdByMemberId': null,
    'createdAt': '2026-09-01T10:00:00.000Z',
    'updatedAt': '2026-09-01T11:00:00.000Z',
  };

  final canvas = CanvasSummary.fromJson(json);
  expect(canvas.id, '9223372036854775807');
  expect(canvas.description, isNull);
  expect(canvas.toLegacyMap()['id'], canvas.id);
  expect(CreateCanvasCommand(name: 'Lean', description: 'Model').toJson(), {
    'name': 'Lean', 'description': 'Model',
  });
  ```

  Add independent tests that `CanvasSummary.fromJson` throws `FormatException`
  for a missing `id`, an empty `workspaceId`, a numeric `id`, and a non-string
  non-null `description`.  Add a test that `UpdateCanvasCommand` serializes
  `id`, emits only non-null update fields, and rejects an empty ID in its
  constructor.

- [ ] **Step 2: Run the focused test and confirm it fails because the feature contracts do not exist.**

  Run:

  ```bash
  cd frontend && flutter test test/features/strategy/domain/canvas_summary_test.dart
  ```

  Expected: compilation failure for the missing feature imports.

- [ ] **Step 3: Add immutable domain objects and the repository port.**

  Create `CanvasSummary` as a `final class` with the eight Company fields and
  private helpers like the following; `requiredString` rejects non-strings and
  blank strings, while `optionalString` accepts only `null` or a string:

  ```dart
  static String _requiredString(Map<String, dynamic> json, String key) {
    final value = json[key];
    if (value is! String || value.trim().isEmpty) {
      throw FormatException('Canvas $key must be a non-empty string');
    }
    return value;
  }

  static String? _optionalString(Map<String, dynamic> json, String key) {
    final value = json[key];
    if (value == null) return null;
    if (value is! String) throw FormatException('Canvas $key must be a string or null');
    return value;
  }
  ```

  `toLegacyMap()` returns the existing camel-case map keys (`id`, `workspaceId`,
  `name`, `description`, `currentRevisionId`, `createdByMemberId`, `createdAt`,
  `updatedAt`) without wrapper maps or invented defaults.  Put commands in
  `canvas_commands.dart`: `CreateCanvasCommand` has `name` and nullable
  `description`; `UpdateCanvasCommand` has non-empty `id`, nullable `name`, and
  nullable `description`. Both `toJson()` methods omit null values, and both
  reject blank provided names.

  Define the port in `application/canvas_repository.dart`:

  ```dart
  abstract interface class CanvasRepository {
    Future<ApiResult<List<CanvasSummary>>> list();
    Future<ApiResult<CanvasSummary>> get(String canvasId);
    Future<ApiResult<CanvasSummary>> create(CreateCanvasCommand command);
    Future<ApiResult<CanvasSummary>> update(UpdateCanvasCommand command);
    Future<ApiResult<void>> delete(String canvasId);
  }
  ```

- [ ] **Step 4: Run the domain test and format the new Dart files.**

  Run:

  ```bash
  cd frontend && dart format lib/features/strategy/domain lib/features/strategy/application test/features/strategy/domain
  cd frontend && flutter test test/features/strategy/domain/canvas_summary_test.dart
  ```

  Expected: all strict-decoder and command cases pass.

- [ ] **Step 5: Commit the independently tested contracts.**

  Run:

  ```bash
  git add frontend/lib/features/strategy/domain/canvas_summary.dart frontend/lib/features/strategy/domain/canvas_commands.dart frontend/lib/features/strategy/application/canvas_repository.dart frontend/test/features/strategy/domain/canvas_summary_test.dart
  git commit -m "feat(strategy): add typed canvas contracts"
  ```

### Task 2: Implement canonical Canvas repository transport

**Files:**
- Create: `frontend/lib/features/strategy/data/canvas_remote_repository.dart`
- Create: `frontend/test/features/strategy/data/canvas_remote_repository_test.dart`

**Interfaces:**
- Consumes `CanvasRepository`, `CanvasSummary`, Canvas commands,
  `MvpRequestClient`, and generated `MvpEndpoint` constants from Task 1.
- Produces `CanvasRemoteRepository({MvpRequestClient? client, http.Client? httpClient})` that implements the repository port.
- The constructor must permit a test-created `MvpRequestClient`, so tests never modify global `ApiClient.client`.

- [ ] **Step 1: Write failing transport tests for all CRUD routes and failure truthfulness.**

  In `frontend/test/features/strategy/data/canvas_remote_repository_test.dart`, use
  `MockClient` plus a local `ApiAuthResolver` fake returning `token-1` and
  `ws_1001`.  Build the repository with `CanvasRemoteRepository(client:
  MvpRequestClient(httpClient: mockHttp, authResolver: fakeAuth))`.

  Add a table-style test that invokes list, create, get, update, and delete and
  asserts the captured requests are exactly:

  ```dart
  expect(seen, [
    ('GET', '/operations/strategy/canvases'),
    ('POST', '/operations/strategy/canvases'),
    ('GET', '/operations/strategy/canvases/canvas%201'),
    ('PUT', '/operations/strategy/canvases/canvas%201'),
    ('DELETE', '/operations/strategy/canvases/canvas%201'),
  ]);
  expect(request.headers['authorization'], 'Bearer token-1');
  expect(request.headers['x-workspace-id'], 'ws_1001');
  ```

  Return a canonical envelope for each success. Assert POST/PUT JSON payloads
  contain `name` and `description` only when supplied. Add separate tests that:

  - a `data: []` envelope with `dataState: empty` remains an
    `ApiSuccess<List<CanvasSummary>>` with `meta.dataState == ApiDataState.empty`;
  - a 401 is `ApiFailure` with `ApiFailureCode.unauthenticated`;
  - a 503 is `ApiFailure` with `ApiFailureCode.unavailable`; and
  - an otherwise successful envelope containing a Canvas without `id` is an
    `ApiFailure` with `ApiFailureCode.malformedResponse`.

- [ ] **Step 2: Run the focused test and confirm it fails before the repository exists.**

  Run:

  ```bash
  cd frontend && flutter test test/features/strategy/data/canvas_remote_repository_test.dart
  ```

  Expected: compilation failure for `CanvasRemoteRepository`.

- [ ] **Step 3: Implement the repository with generated endpoints only.**

  Create the repository with a stored `MvpRequestClient`. Each method must call
  `_client.request` once with its corresponding `MvpEndpoint`. The list decoder
  must accept only a JSON `List`; every list element must be a
  `Map<String, dynamic>` and is decoded by `CanvasSummary.fromJson`:

  ```dart
  Future<ApiResult<List<CanvasSummary>>> list() => _client.request(
    MvpEndpoint.strategyCanvasList,
    decode: (value) {
      if (value is! List) throw FormatException('Canvas list data must be a list');
      return value.map((item) {
        if (item is! Map<String, dynamic>) {
          throw FormatException('Canvas list item must be an object');
        }
        return CanvasSummary.fromJson(item);
      }).toList(growable: false);
    },
  );
  ```

  `get` and `delete` pass `pathParams: {'id': canvasId}`. `create` passes
  `body: command.toJson()`. `update` passes its `id` as a path parameter and
  `body: command.toJson()` with the ID excluded from the body. Decode all item
  endpoints through a private `_decodeCanvas(Object?)` that rejects a non-map.
  Decode delete with `decode: (_) {}`. Do not import `ApiClient`, secure
  storage, legacy service types, raw paths, GetX, or UI packages.

- [ ] **Step 4: Run the repository test and static analysis.**

  Run:

  ```bash
  cd frontend && dart format lib/features/strategy/data test/features/strategy/data
  cd frontend && flutter test test/features/strategy/domain/canvas_summary_test.dart test/features/strategy/data/canvas_remote_repository_test.dart
  cd frontend && flutter analyze lib/features/strategy test/features/strategy
  ```

  Expected: all route, header, empty-list, and failure mapping assertions pass;
  the feature has no analyzer diagnostics.

- [ ] **Step 5: Commit the typed remote boundary.**

  Run:

  ```bash
  git add frontend/lib/features/strategy/data/canvas_remote_repository.dart frontend/test/features/strategy/data/canvas_remote_repository_test.dart
  git commit -m "feat(strategy): add canonical canvas repository"
  ```

### Task 3: Publish a Canvas facade without duplicating transport logic

**Files:**
- Create: `frontend/lib/features/strategy/canvas_facade.dart`
- Modify: `frontend/lib/features/strategy/public.dart:1-2`
- Create: `frontend/test/features/strategy/canvas_facade_test.dart`

**Interfaces:**
- Consumes the repository port from Task 1 and its default remote implementation from Task 2.
- Produces `CanvasFacade` and `MvpCanvasFacade` as the only Canvas API exported to code outside `features/strategy`.
- `MvpCanvasFacade({CanvasRepository? repository, MvpRequestClient? client})` builds `CanvasRemoteRepository(client: client)` only when no repository is injected.

- [ ] **Step 1: Write a failing facade propagation test using a repository fake.**

  In `frontend/test/features/strategy/canvas_facade_test.dart`, create an in-file
  `FakeCanvasRepository implements CanvasRepository`. Configure it to return
  `ApiSuccess` containing a known `CanvasSummary`, a known empty list with
  `ApiDataState.empty`, and an `ApiFailure` with `ApiFailureCode.conflict`.
  Assert that `MvpCanvasFacade` calls the exact port methods and returns the
  original `ApiSuccess` metadata and `ApiFailureDetail`, rather than replacing
  either result. This test must not use HTTP or claim runtime endpoint proof.

- [ ] **Step 2: Run the focused test and confirm it fails before the facade exists.**

  Run:

  ```bash
  cd frontend && flutter test test/features/strategy/canvas_facade_test.dart
  ```

  Expected: compilation failure for the missing facade symbols.

- [ ] **Step 3: Add the public facade and precise exports.**

  In `canvas_facade.dart`, define this contract and a thin delegating default
  implementation:

  ```dart
  abstract interface class CanvasFacade {
    Future<ApiResult<List<CanvasSummary>>> list();
    Future<ApiResult<CanvasSummary>> get(String canvasId);
    Future<ApiResult<CanvasSummary>> create(CreateCanvasCommand command);
    Future<ApiResult<CanvasSummary>> update(UpdateCanvasCommand command);
    Future<ApiResult<void>> delete(String canvasId);
  }

  final class MvpCanvasFacade implements CanvasFacade {
    MvpCanvasFacade({CanvasRepository? repository, MvpRequestClient? client})
        : _repository = repository ?? CanvasRemoteRepository(client: client);
    final CanvasRepository _repository;
    // Every CanvasFacade member delegates one-for-one to _repository.
  }
  ```

  Preserve the current shared export in `public.dart`, then export only
  `domain/canvas_summary.dart`, `domain/canvas_commands.dart`, and
  `canvas_facade.dart`. Do not export the repository port or data class to
  module callers. External code must import
  `package:frontend/features/strategy/public.dart`, never an internal file.

- [ ] **Step 4: Run feature tests and public-import analysis.**

  Run:

  ```bash
  cd frontend && dart format lib/features/strategy/canvas_facade.dart lib/features/strategy/public.dart test/features/strategy/canvas_facade_test.dart
  cd frontend && flutter test test/features/strategy
  cd frontend && flutter analyze lib/features/strategy test/features/strategy
  ```

  Expected: facade preserves success metadata/failure details and its public
  API analyzes cleanly.

- [ ] **Step 5: Commit the public feature API.**

  Run:

  ```bash
  git add frontend/lib/features/strategy/canvas_facade.dart frontend/lib/features/strategy/public.dart frontend/test/features/strategy/canvas_facade_test.dart
  git commit -m "feat(strategy): expose canvas facade"
  ```

### Task 4: Migrate legacy Canvas CRUD callers through the compatibility adapter

**Files:**
- Modify: `frontend/lib/modules/strategy/services/canvas_service.dart:1-57`
- Modify: `frontend/lib/modules/strategy/services/strategy_mvp_client.dart:1-75`
- Modify: `frontend/test/strategy_service_test.dart:1-131`
- Modify: `frontend/test/strategy_mvp_service_test.dart:1-96`

**Interfaces:**
- Consumes `CanvasFacade` only through `package:frontend/features/strategy/public.dart`.
- Produces unchanged `CanvasService.getCanvases`, `createCanvas`, `updateCanvas`, and `deleteCanvas` signatures for `StrategyService`, Foundation, and Hub.
- Produces unchanged `StrategyMvpClient` Canvas method return types:
  `ApiResult<List<MvpCanvas>>`, `ApiResult<MvpCanvas>`, and `ApiResult<void>`.

- [ ] **Step 1: Rewrite legacy tests to assert the preserved public contracts through a fake facade.**

  In `frontend/test/strategy_service_test.dart`, remove only tests that intercept
  raw `/strategy/canvases` requests. Add a `FakeCanvasFacade` in the test file
  and construct the real facade chain as:

  ```dart
  final service = StrategyService(
    canvasService: CanvasService(canvasFacade: fakeCanvasFacade),
  );
  ```

  Assert that a successful list maps a typed summary to a legacy map with a
  top-level `id` and `name`; a typed empty success remains a non-failure empty
  `StrategyListResult`; list 503 becomes a non-empty `errorMessage`; and create,
  update, and delete failures throw `StrategyApiException` whose `statusCode`
  is the `ApiFailureDetail.statusCode` (or `0` when absent) and whose message is
  the owner failure message. Retain the existing detail/revision raw-route test
  unchanged to prove those methods were not moved.

  In `frontend/test/strategy_mvp_service_test.dart`, inject the same type of
  facade into `StrategyMvpClient`. Keep its existing assertions for empty,
  populated, and 503 results, and add one assertion that converting a
  `CanvasSummary` preserves every MvpCanvas field rather than using
  `MvpCanvas.fromJson` defaults.

- [ ] **Step 2: Run the two test files and confirm Canvas expectations fail against the old raw implementation.**

  Run:

  ```bash
  cd frontend && flutter test test/strategy_service_test.dart test/strategy_mvp_service_test.dart
  ```

  Expected: failures because `CanvasService` and `StrategyMvpClient` do not yet
  accept or delegate to `CanvasFacade`.

- [ ] **Step 3: Adapt exactly the four CRUD methods in CanvasService.**

  Give `CanvasService` an optional `CanvasFacade` constructor dependency
  defaulting to `MvpCanvasFacade()`. Replace only `getCanvases`, `createCanvas`,
  `updateCanvas`, and `deleteCanvas`:

  ```dart
  StrategyListResult<Map<String, dynamic>> _asLegacyList(
    ApiResult<List<CanvasSummary>> result,
  ) => result.when(
    success: (items, _) => StrategyListResult.success(
      items.map((item) => item.toLegacyMap()).toList(growable: false),
    ),
    failure: (failure) => StrategyListResult.failure(failure.message),
  );

  Never throw from list on an ApiFailure; create/update/delete call
  `result.when` and throw `StrategyApiException(failure.statusCode ?? 0,
  failure.message)` only from their failure branch. Successful create/update
  return `CanvasSummary.toLegacyMap()`, and successful delete returns normally.
  Remove the raw `ApiClient` dependency only if no remaining Canvas method
  needs it; retain the legacy raw import for detail/revision/AI/Foundation
  operations. Do not alter any other method or its route literal.

- [ ] **Step 4: Delegate StrategyMvpClient Canvas methods through the facade while preserving old types.**

  Add optional `CanvasFacade? canvasFacade` to the existing constructor. Its
  default is `MvpCanvasFacade(client: _client)`, so injected request clients use
  the same transport instance. Replace the five Canvas CRUD bodies with facade
  calls and a private result mapper:

  ```dart
  ApiResult<R> _mapCanvasResult<T, R>(ApiResult<T> result, R Function(T) map) {
    return result.when(
      success: (data, meta) => ApiSuccess(data: map(data), meta: meta),
      failure: ApiFailure.new,
    );
  }
  ```

  Map each `CanvasSummary` to `MvpCanvas` by passing all eight fields directly
  to its constructor. Map a list element-by-element. `listCanvases`,
  `createCanvas`, `getCanvas`, and `updateCanvas` use this mapper; delete
  returns `await _canvasFacade.delete(id)` directly. Keep all revision, OKR,
  and twelve-week methods and their `_client` request logic unchanged.

- [ ] **Step 5: Run focused regression checks and review the compatibility diff.**

  Run:

  ```bash
  cd frontend && dart format lib/modules/strategy/services/canvas_service.dart lib/modules/strategy/services/strategy_mvp_client.dart test/strategy_service_test.dart test/strategy_mvp_service_test.dart
  cd frontend && flutter test test/features/strategy test/strategy_service_test.dart test/strategy_mvp_service_test.dart
  cd frontend && flutter analyze lib/features/strategy lib/modules/strategy/services/canvas_service.dart lib/modules/strategy/services/strategy_mvp_client.dart
  git diff --check
  ```

  Expected: typed transport tests and legacy caller contract tests all pass;
  no change occurs in FoundationController or HubStageMixin.

- [ ] **Step 6: Commit the compatibility migration.**

  Run:

  ```bash
  git add frontend/lib/modules/strategy/services/canvas_service.dart frontend/lib/modules/strategy/services/strategy_mvp_client.dart frontend/test/strategy_service_test.dart frontend/test/strategy_mvp_service_test.dart
  git commit -m "refactor(strategy): route canvas crud through facade"
  ```

### Task 5: Enforce the feature boundary and prove release-level behaviour

**Files:**
- Modify: `scripts/check_frontend_boundaries.mjs:34-104`
- Modify: `tests/quality/test_frontend_boundaries.py:5-63`

**Interfaces:**
- Consumes the scanner's existing `runCheck(targetDir)` result and all Dart
  imports below `frontend/lib`.
- Produces `NO_STRATEGY_FEATURE_RAW_TRANSPORT` for an import of
  `api_client.dart`, `secure_storage_service.dart`, or
  `workspace_scoped_service.dart` from `features/strategy/**`.
- Leaves all existing frozen-legacy and cross-feature import rules unchanged.

- [ ] **Step 1: Add failing scanner fixtures for forbidden Strategy feature imports.**

  Extend `test_frontend_boundary_scanner_detects_violations` in
  `tests/quality/test_frontend_boundaries.py` with three files under
  `features/strategy/` importing the three prohibited paths using
  `package:frontend/...` syntax. Assert the scanner exits non-zero and includes
  `NO_STRATEGY_FEATURE_RAW_TRANSPORT` for each file. Keep the existing
  `NO_LEGACY_WORKSPACE_SCOPED_SERVICE` assertion as well, because a strategy
  feature's workspace-scoped import violates both the feature-wide and
  strategy-specific policy.

- [ ] **Step 2: Run the boundary test and confirm it fails before the new strategy rule exists.**

  Run:

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/quality/test_frontend_boundaries.py -q
  ```

  Expected: the new test fails because the scanner has no raw-transport
  violation for `ApiClient` or `SecureStorageService`.

- [ ] **Step 3: Add a narrow, import-based Strategy feature rule.**

  After resolving a Dart import to its repository-relative target, detect a
  current feature value of `strategy` and an exact target ending in one of:

  ```js
  const strategyForbiddenTargets = new Set([
    'core/network/api_client.dart',
    'core/services/secure_storage_service.dart',
    'core/network/workspace_scoped_service.dart',
  ]);
  ```

  Record `NO_STRATEGY_FEATURE_RAW_TRANSPORT` with the explanation
  `Strategy feature code must use MvpRequestClient through its typed facade`.
  Continue running the pre-existing workspace-scoped rule; do not suppress it
  and do not broaden the new restriction to unrelated feature folders.

- [ ] **Step 4: Run full local frontend and contract verification.**

  Run these commands in order:

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/quality/test_frontend_boundaries.py -q
  make frontend-boundary-check
  cd frontend && flutter test test/features/strategy test/strategy_service_test.dart test/strategy_mvp_service_test.dart
  make frontend-analyze
  cd services/company && pnpm vitest run identity/tests/e2e-session.test.ts operations/tests/mvp-canvas-runtime.test.ts
  PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/e2e/test_mvp_strategy_runtime_http.py -q
  git diff --check
  git status --short
  ```

  Expected: the scanner catches synthetic violations and passes the repository;
  focused Flutter tests and analysis pass; the Company Canvas contract test
  passes; and the real HTTP E2E creates, reads, revisions, and isolates a
  Canvas without a mock transport. If the real E2E fixture reports that Encore
  or Postgres is unavailable, start the documented local Company prerequisites
  or provide `E2E_COMPANY_BASE_URL`; do not replace that check with a mock.

- [ ] **Step 5: Commit, push, and record exact verification evidence.**

  Run:

  ```bash
  git add scripts/check_frontend_boundaries.mjs tests/quality/test_frontend_boundaries.py
  git commit -m "test(strategy): guard canvas feature transport boundary"
  git push origin main
  git status --short
  ```

  Expected: the working tree is clean after the push. In the handoff, report
  the commit IDs and actual exit result for every command in Step 4; do not
  claim the live E2E passed without its fresh output.

## Plan self-review

### Spec coverage

- Strict typed summary, command objects, Snowflake string preservation, and
  malformed-response behaviour: Tasks 1 and 2.
- Generated endpoint CRUD, authenticated workspace transport, 401/503/error
  truthfulness, and valid empty lists: Task 2.
- Public facade and no duplicated Canvas decoder/transport in `StrategyMvpClient`:
  Tasks 3 and 4.
- Compatibility for Foundation and Hub, including top-level `id`, list failure
  semantics, and exceptions on mutation failure: Task 4.
- Detail/revision/AI/Foundation non-goals and unchanged UI callers: Global
  Constraints and Task 4's scoped file list.
- Feature no-raw-transport rule plus company runtime and real HTTP E2E proof:
  Task 5.

### Placeholder scan

The plan contains concrete paths, names, command lines, response assertions,
and code for every change. It contains no deferred or unspecified work items.

### Type consistency

`CanvasSummary`, `CreateCanvasCommand`, `UpdateCanvasCommand`,
`CanvasRepository`, `CanvasFacade`, and `MvpCanvasFacade` are introduced in
Task 1 or Task 3 before Tasks 2 and 4 consume them. `CanvasService` retains
legacy maps; `StrategyMvpClient` retains `MvpCanvas` return types.
