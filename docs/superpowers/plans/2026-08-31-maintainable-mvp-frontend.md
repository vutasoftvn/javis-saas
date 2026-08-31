# Maintainable MVP Flutter Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move active MVP callers from raw, cross-module Flutter services to typed feature repositories and public facades, make errors/empty/source states visible instead of fabricated, and make Hologram Hub a pure composition surface.

**Architecture:** Strangle one feature vertical slice at a time. Existing `frontend/lib/modules/*` views/controllers remain stable while their active data dependency changes to a feature public facade. New `frontend/lib/features/<feature>` modules contain typed domain models, repository interfaces, remote implementations using Foundation `MvpRequestClient`, state presenters, and a single `public.dart` facade. Cross-feature calls and Hub imports target only those facades. `WorkspaceScopedService` remains only until the master final-decommission task proves all callers are gone.

**Tech Stack:** Flutter/Dart, GetX, HTTP, Flutter test, existing generated MVP endpoint contract, Node boundary scanner.

**Spec:** `docs/superpowers/specs/2026-08-31-maintainable-modular-truthful-mvp-design.md`

**Depends on:** Foundation Tasks 1–4; matching Company or Agent/Control owner task for each backend capability; Agent/Control Task 6 before marking frontend capability real-E2E verified.

## Global Constraints

- Read and obey the master and Foundation plans. All remote calls use Foundation `ApiAuthResolver`, `ApiPlane`, `ApiResult<T>`, and generated `MvpEndpoint`; do not introduce direct `http.*` or `SecureStorageService.read('auth_token')` in a feature.
- New active feature code may not use `dynamic`, `Map<String, dynamic>` as a domain model, `as` casts on network values, raw URL literals, `Get.find` in a repository, or default text/value/date for an absent source fact.
- `ApiSuccess` may represent only `populated` or `empty`. UI renders `ApiFailure`, `not_observed`, unavailable connector, and authorization failure explicitly; it must not replace them with blank analytics, demo cards, a zero metric, or a green status.
- Preserve Snowflake IDs as `String`, including navigation arguments, model keys, JSON fields, and request path parameters.
- A `public.dart` facade may export domain contracts, presentation models, and facade interfaces only. It must not export controllers, widgets, data classes, remote repositories, bindings, or `GetX` implementation details.
- Hologram Hub cannot import feature implementation folders (`data`, `services`, `repositories`, `controllers`, `bindings`, `views`, `widgets`). It imports facades from `features/*/public.dart` and receives them by typed constructor/binding injection.
- Do not delete or mass-move a legacy module in this plan. Retire it only under master Task 3 after all caller scans and acceptance-ledger evidence are green.

## Standard feature shape and result presentation

Each new slice follows this structure. Reuse existing models only by moving/wrapping them behind this contract; do not duplicate divergent model classes.

```text
frontend/lib/features/<capability>/
  domain/<capability>.dart                 # immutable typed facts/value objects
  application/<capability>_repository.dart # interface; no Flutter/GetX imports
  data/<capability>_remote_repository.dart # MvpRequestClient and strict decoder
  presentation/<capability>_state.dart     # loading/success/empty/failure/not-observed state
  <capability>_facade.dart                 # public query/command boundary
  public.dart                              # permitted import surface
```

Every slice exposes query/command methods returning `Future<ApiResult<T>>`; controllers convert them to presentation state. Tests use a local fake repository only in `test/`, while remote-repository tests use `http.MockClient` solely for Flutter transport contract tests, never for real E2E.

## Task 1: Add shared Flutter feature conventions and strict feature-boundary tests

**Files:**

- Create: `frontend/lib/features/_shared/presentation/async_feature_state.dart`
- Create: `frontend/lib/features/_shared/public.dart`
- Create: `frontend/lib/features/strategy/public.dart`
- Create: `frontend/lib/features/marketing/public.dart`
- Create: `frontend/lib/features/workforce/public.dart`
- Create: `frontend/lib/features/vault/public.dart`
- Create: `frontend/lib/features/settings/public.dart`
- Create: `frontend/lib/features/workspace_runtime/public.dart`
- Modify: `scripts/check_frontend_boundaries.mjs`
- Modify: `tests/quality/test_frontend_boundaries.py`
- Test: `frontend/test/features/shared/async_feature_state_test.dart`
- Test: `frontend/test/features/public_surface_test.dart`

**Interfaces:**

```dart
sealed class AsyncFeatureState<T> {
  const AsyncFeatureState();
}
final class FeatureLoading<T> extends AsyncFeatureState<T> { const FeatureLoading(); }
final class FeatureData<T> extends AsyncFeatureState<T> {
  const FeatureData(this.value, this.meta);
  final T value;
  final ApiResponseMeta meta;
}
final class FeatureFailure<T> extends AsyncFeatureState<T> {
  const FeatureFailure(this.failure);
  final ApiFailureDetail failure;
}
final class FeatureNotObserved<T> extends AsyncFeatureState<T> {
  const FeatureNotObserved(this.reason, this.sourceKind);
  final String reason;
  final String sourceKind;
}
```

- [ ] **Step 1: Write failing state/policy tests.**

  Cover success-populated, success-empty, transport failure, and explicit not-observed. Assert none becomes another state or creates an observed timestamp. Add public-surface tests that only permit the intended facade/domain exports and fail if an implementation import is exported.

  Run:

  ```bash
  cd frontend && flutter test test/features/shared/async_feature_state_test.dart test/features/public_surface_test.dart
  PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/quality/test_frontend_boundaries.py -q
  ```

  Expected: FAIL before shared state/facade files and stricter scanner rules exist.

- [ ] **Step 2: Implement shared state and empty public surfaces.**

  Map Foundation `ApiResult` explicitly. `FeatureNotObserved` is constructed only from a declared backend source state, never inferred from a `null` field. Public facades may initially export no capability API besides package documentation/type placeholder; do not create fake implementations to make imports compile.

- [ ] **Step 3: Strengthen scanner for the new architecture.**

  Add failures for:

  - `features/*` importing `modules/*/services`, `modules/*/controllers`, or another feature’s `data`/`presentation` implementation;
  - domain/application layers importing Flutter widgets, GetX, HTTP, secure storage, or raw route paths;
  - public facades exporting implementation folders;
  - Hologram Hub importing implementation folders.

  Leave legacy-module violations reported as inventory warnings until a slice is migrated. The scanner must fail new source in `features/` immediately; it must not grandfather future violations.

- [ ] **Step 4: Verify and commit.**

  Run:

  ```bash
  cd frontend && flutter test test/features/shared/async_feature_state_test.dart test/features/public_surface_test.dart
  make frontend-boundary-check
  make frontend-analyze
  ```

  Expected: PASS.

  ```bash
  git add frontend/lib/features/_shared frontend/lib/features/strategy/public.dart frontend/lib/features/marketing/public.dart frontend/lib/features/workforce/public.dart frontend/lib/features/vault/public.dart frontend/lib/features/settings/public.dart frontend/lib/features/workspace_runtime/public.dart scripts/check_frontend_boundaries.mjs tests/quality/test_frontend_boundaries.py frontend/test/features/shared/async_feature_state_test.dart frontend/test/features/public_surface_test.dart
  git commit -m "feat(frontend): establish typed feature boundaries"
  ```

## Task 2: Migrate Strategy Canvas active reads/commands behind a feature facade

**Files:**

- Create: `frontend/lib/features/strategy/domain/canvas.dart`
- Create: `frontend/lib/features/strategy/application/canvas_repository.dart`
- Create: `frontend/lib/features/strategy/data/canvas_remote_repository.dart`
- Create: `frontend/lib/features/strategy/presentation/canvas_state.dart`
- Create: `frontend/lib/features/strategy/canvas_facade.dart`
- Modify: `frontend/lib/features/strategy/public.dart`
- Modify: `frontend/lib/modules/strategy/services/strategy_mvp_client.dart`
- Modify: `frontend/lib/modules/strategy/services/strategy_service.dart`
- Modify: active Strategy controller/view/binding files found by Step 1
- Test: `frontend/test/features/strategy/canvas_remote_repository_test.dart`
- Test: `frontend/test/features/strategy/canvas_facade_test.dart`
- Test: existing active Strategy widget/controller tests found by Step 1

**Interfaces:**

```dart
abstract interface class CanvasRepository {
  Future<ApiResult<CanvasSnapshot>> load({required String workspaceId});
  Future<ApiResult<CanvasSnapshot>> save(CanvasCommand command);
}

abstract interface class CanvasFacade {
  Future<ApiResult<CanvasSnapshot>> load();
  Future<ApiResult<CanvasSnapshot>> execute(CanvasCommand command);
}
```

`CanvasSnapshot` is an immutable, typed translation of the current owner response. IDs remain strings. Optional source facts remain nullable; no field gets a UI placeholder at decoding time.

- [ ] **Step 1: Identify only visible Canvas callers and freeze their behavior.**

  Run:

  ```bash
  rg -n "StrategyMvpClient|CanvasService|/.*canvas|MvpEndpoint" frontend/lib/modules/strategy frontend/lib/modules/hologram_hub -g '*.dart'
  rg -n "strategy\.canvas" shared/contracts/mvp-surface.json docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  ```

  List every active caller in `legacy_callers` before editing. Choose the first UI journey that users can reach; do not migrate all of the 1,878-line legacy service.

- [ ] **Step 2: Write red remote-repository and facade tests.**

  Remote test covers correct generated endpoint/path/workspace header, strict populated envelope, real empty envelope, malformed response failure, 401, and 5xx. Facade test covers the same result propagation with a test repository. Controller/widget test covers visible loading, empty, failure, and no-observation handling rather than an empty screen or fabricated values.

  Run:

  ```bash
  cd frontend && flutter test test/features/strategy/canvas_remote_repository_test.dart test/features/strategy/canvas_facade_test.dart
  ```

  Expected: FAIL before feature modules exist.

- [ ] **Step 3: Build the slice and adapt legacy caller through facade.**

  Decode only through Foundation `MvpRequestClient`. Inject repository/facade in binding/composition; no `Get.find` in domain/data. `StrategyMvpClient` becomes a deprecated facade adapter or is removed from the migrated journey, but `strategy_service.dart` must not acquire new raw route calls. Map feature state to existing views while preserving the same user action and navigation.

- [ ] **Step 4: Prove no raw transport is added and record real-E2E dependency.**

  Run:

  ```bash
  cd frontend && flutter test test/features/strategy/canvas_remote_repository_test.dart test/features/strategy/canvas_facade_test.dart
  make frontend-analyze
  make frontend-boundary-check
  rg -n "http\.|SecureStorageService|auth_token|WorkspaceScopedService" frontend/lib/features/strategy
  ```

  Expected: tests/checks pass; the scan returns no direct transport/token/legacy service use. Reference the matching Company Canvas contract and real E2E test in the ledger, but do not mark verified until Agent Task 6 executed it.

- [ ] **Step 5: Commit.**

  ```bash
  git add frontend/lib/features/strategy frontend/lib/modules/strategy frontend/test/features/strategy docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "refactor(frontend): move canvas to typed feature facade"
  ```

## Task 3: Migrate Marketing and Workspace Runtime as separate truthful feature slices

**Files:**

- Create: `frontend/lib/features/marketing/domain/marketing_context.dart`
- Create: `frontend/lib/features/marketing/application/marketing_repository.dart`
- Create: `frontend/lib/features/marketing/data/marketing_remote_repository.dart`
- Create: `frontend/lib/features/marketing/presentation/marketing_state.dart`
- Create: `frontend/lib/features/marketing/marketing_facade.dart`
- Modify: `frontend/lib/features/marketing/public.dart`
- Modify: `frontend/lib/modules/marketing/services/marketing_mvp_service.dart`
- Modify: active Marketing controller/view/binding files found by Step 1
- Create: `frontend/lib/features/workspace_runtime/domain/runtime_overview.dart`
- Create: `frontend/lib/features/workspace_runtime/application/runtime_repository.dart`
- Create: `frontend/lib/features/workspace_runtime/data/runtime_remote_repository.dart`
- Create: `frontend/lib/features/workspace_runtime/presentation/runtime_state.dart`
- Create: `frontend/lib/features/workspace_runtime/runtime_facade.dart`
- Modify: `frontend/lib/features/workspace_runtime/public.dart`
- Modify: `frontend/lib/modules/workspace_runtime/services/workspace_runtime_mvp_client.dart`
- Modify: active Runtime controller/view/binding files found by Step 1
- Test: `frontend/test/features/marketing/marketing_remote_repository_test.dart`
- Test: `frontend/test/features/marketing/marketing_facade_test.dart`
- Test: `frontend/test/features/workspace_runtime/runtime_remote_repository_test.dart`
- Test: `frontend/test/features/workspace_runtime/runtime_facade_test.dart`
- Test: existing active Marketing/Runtime widget/controller tests found by Step 1

**Interfaces:**

```dart
abstract interface class MarketingFacade {
  Future<ApiResult<MarketingContext>> loadContext();
  Future<ApiResult<MarketingContext>> saveContext(MarketingContextCommand command);
}

abstract interface class RuntimeFacade {
  Future<ApiResult<RuntimeOverview>> loadOverview();
}
```

`RuntimeOverview` represents each source as its stated status and optional observation evidence. It has no `isHealthy` bool that can turn `not_observed` into green.

- [ ] **Step 1: Write red Marketing repository/facade tests first.**

  Cover populated/empty/error response separation, string IDs, exact form payload, invalid field decode failure, and UI failure/error presentation. Do not manufacture campaign statistics in models.

  Run: `cd frontend && flutter test test/features/marketing/marketing_remote_repository_test.dart test/features/marketing/marketing_facade_test.dart`

  Expected: FAIL before the feature exists.

- [ ] **Step 2: Migrate the Marketing visible path and verify against owner contract.**

  Implement typed decoder/repository/facade, inject it into only the selected active Marketing journey, and leave the remaining legacy service untouched except to delegate that migrated call. Verify with the matching Company `mvp-marketing` contract test before continuing.

- [ ] **Step 3: Write red Runtime observation-state tests.**

  Tests must render all four owner states: `healthy`, `degraded`, `unavailable`, `not_observed`. `not_observed` uses absence wording and no date; it must not render green, `0`, an empty status card, or current time. Test system-derived title carries an explicit UI affordance/label rather than being displayed as source text.

  Run: `cd frontend && flutter test test/features/workspace_runtime/runtime_remote_repository_test.dart test/features/workspace_runtime/runtime_facade_test.dart`

  Expected: FAIL before typed Runtime slice exists.

- [ ] **Step 4: Migrate Runtime active path only after Company Task 3 is green.**

  Use Company response fields verbatim through strict decoding. Bind state to the Runtime view with explicit cards/errors. Remove no legacy response semantics to make a test pass.

- [ ] **Step 5: Run cross-slice verification and commit in two commits.**

  Marketing commit:

  ```bash
  cd frontend && flutter test test/features/marketing/marketing_remote_repository_test.dart test/features/marketing/marketing_facade_test.dart
  make frontend-analyze frontend-boundary-check
  git add frontend/lib/features/marketing frontend/lib/modules/marketing frontend/test/features/marketing docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "refactor(frontend): move marketing to typed feature facade"
  ```

  Runtime commit:

  ```bash
  cd frontend && flutter test test/features/workspace_runtime/runtime_remote_repository_test.dart test/features/workspace_runtime/runtime_facade_test.dart
  make frontend-analyze frontend-boundary-check
  git add frontend/lib/features/workspace_runtime frontend/lib/modules/workspace_runtime frontend/test/features/workspace_runtime docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "refactor(frontend): render runtime observation truthfully"
  ```

## Task 4: Migrate Workforce, Vault, and Settings after their real owner behavior exists

**Files:**

- Create: `frontend/lib/features/workforce/domain/workforce.dart`
- Create: `frontend/lib/features/workforce/application/workforce_repository.dart`
- Create: `frontend/lib/features/workforce/data/workforce_remote_repository.dart`
- Create: `frontend/lib/features/workforce/presentation/workforce_state.dart`
- Create: `frontend/lib/features/workforce/workforce_facade.dart`
- Modify: `frontend/lib/features/workforce/public.dart`
- Modify: `frontend/lib/modules/agents/services/workforce_service.dart`
- Modify: active workforce caller/binding/controller/view files found by Step 1
- Create: `frontend/lib/features/vault/domain/vault_document.dart`
- Create: `frontend/lib/features/vault/application/vault_repository.dart`
- Create: `frontend/lib/features/vault/data/vault_remote_repository.dart`
- Create: `frontend/lib/features/vault/presentation/vault_state.dart`
- Create: `frontend/lib/features/vault/vault_facade.dart`
- Modify: `frontend/lib/features/vault/public.dart`
- Modify: `frontend/lib/modules/vault/services/vault_mvp_service.dart`
- Modify: active vault caller/binding/controller/view files found by Step 1
- Create: `frontend/lib/features/settings/domain/skill_setting.dart`
- Create: `frontend/lib/features/settings/application/settings_repository.dart`
- Create: `frontend/lib/features/settings/data/settings_remote_repository.dart`
- Create: `frontend/lib/features/settings/presentation/settings_state.dart`
- Create: `frontend/lib/features/settings/settings_facade.dart`
- Modify: `frontend/lib/features/settings/public.dart`
- Modify: `frontend/lib/modules/settings/services/settings_mvp_service.dart`
- Modify: active Settings caller/binding/controller/view files found by Step 1
- Test: `frontend/test/features/workforce/workforce_remote_repository_test.dart`
- Test: `frontend/test/features/vault/vault_remote_repository_test.dart`
- Test: `frontend/test/features/settings/settings_remote_repository_test.dart`
- Test: facade/UI state tests in each same feature directory

**Interfaces:**

```dart
abstract interface class WorkforceFacade {
  Future<ApiResult<List<WorkforceAssignment>>> list({String? status});
  Future<ApiResult<WorkforceAssignment>> assign(AssignWorkforceCommand command);
}

abstract interface class VaultFacade {
  Future<ApiResult<VaultDocument>> requestUpload(VaultUploadRequest request);
  Future<ApiResult<VaultDocument>> confirmUpload(VaultUploadConfirmation confirmation);
  Future<ApiResult<List<VaultDocument>>> list();
}

abstract interface class SettingsFacade {
  Future<ApiResult<List<SkillSetting>>> list();
  Future<ApiResult<SkillSetting>> save(SkillSettingCommand command);
}
```

- [ ] **Step 1: Gate each slice on its owner behavior and ledger evidence.**

  Before implementing, check these conditions and stop the respective slice if false:

  | Slice | Required owner plan | Required backend truth test |
  |---|---|---|
  | Workforce | Agent/Control Task 2 | `tests/apps/cosa/test_workforce_routes.py` + Postgres adapter test |
  | Vault | Agent/Control Task 4 | Vault lifecycle/object-store test with MinIO |
  | Settings | Agent/Control Task 3 | Settings registry/persistence test |

  Confirm the acceptance ledger has owner, source kind, remote repository name, backend test, real E2E test path, and legacy caller inventory. If not, fill facts only; keep `BLOCKED`.

- [ ] **Step 2: Write red slice tests with truthful state cases.**

  Workforce: populated, empty, membership error, persistence outage. Vault: draft/uploading/stored/processing/indexed/failed as returned by owner; no optimistic `INDEXED`. Settings: `not_configured`, registry unavailable, unknown skill, persisted setting; no default provider/version/title. Each test asserts malformed server data produces `ApiFailure`.

  Run:

  ```bash
  cd frontend && flutter test test/features/workforce test/features/vault test/features/settings
  ```

  Expected: FAIL before implementations.

- [ ] **Step 3: Implement in dependency order, one feature per commit.**

  Implement Workforce first, Settings second, Vault last. For Vault, browser upload bytes to the ticket URL is an external object-storage operation: show actual progress/failure and call confirmation only after the browser upload response succeeds. Do not create a local document/version or show `INDEXED` optimistically. Each migrated legacy service delegates to the facade or is removed only for the migrated caller.

- [ ] **Step 4: Run every slice’s test/analyze/boundary suite.**

  Run after each feature:

  ```bash
  cd frontend && flutter test test/features/<feature>
  make frontend-analyze frontend-boundary-check
  rg -n "http\.|SecureStorageService|auth_token|WorkspaceScopedService|DateTime\.now" frontend/lib/features/<feature>
  ```

  Expected: all checks pass; the scan has no prohibited direct transport, token, legacy fallback, or observation fabrication.

- [ ] **Step 5: Commit three bounded slices.**

  ```bash
  git add frontend/lib/features/workforce frontend/lib/modules/agents frontend/test/features/workforce docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "refactor(frontend): move workforce to typed feature facade"
  ```

  ```bash
  git add frontend/lib/features/settings frontend/lib/modules/settings frontend/test/features/settings docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "refactor(frontend): move settings to typed feature facade"
  ```

  ```bash
  git add frontend/lib/features/vault frontend/lib/modules/vault frontend/test/features/vault docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "refactor(frontend): move vault lifecycle to typed feature facade"
  ```

## Task 5: Make Hologram Hub depend exclusively on feature facades

**Files:**

- Create: `frontend/lib/surfaces/hologram_hub/domain/hub_overview.dart`
- Create: `frontend/lib/surfaces/hologram_hub/application/hub_overview_query.dart`
- Create: `frontend/lib/surfaces/hologram_hub/application/hub_command_facade.dart`
- Create: `frontend/lib/surfaces/hologram_hub/presentation/hub_state.dart`
- Create: `frontend/lib/surfaces/hologram_hub/hologram_hub_facade.dart`
- Create: `frontend/lib/surfaces/hologram_hub/public.dart`
- Modify: all active `frontend/lib/modules/hologram_hub/**/*.dart` caller/binding/controller/view files found by Step 1
- Modify: central Flutter route/binding registration files found by Step 1
- Modify: `scripts/check_frontend_boundaries.mjs`
- Test: `frontend/test/surfaces/hologram_hub/hologram_hub_facade_test.dart`
- Test: `frontend/test/surfaces/hologram_hub/hologram_hub_view_test.dart`
- Test: `tests/quality/test_frontend_boundaries.py`

**Interfaces:**

These complete the master’s exact shared interface definitions:

```dart
final class HubOverview {
  const HubOverview({required this.sections});
  final List<HubSection> sections;
}

sealed class HubCommand {
  const HubCommand();
}

abstract interface class HubOverviewQuery {
  Future<ApiResult<HubOverview>> load();
}

abstract interface class HubCommandFacade {
  Future<ApiResult<void>> execute(HubCommand command);
}
```

`HubSection` carries typed feature state/failure attribution. The Hub does not combine raw maps, call endpoints, or decide a source has data because a feature failed.

- [ ] **Step 1: Inventory Hub imports and label every target.**

  Run:

  ```bash
  rg -n "^import .*modules/(strategy|marketing|agents|vault|settings|workspace_runtime)/" frontend/lib/modules/hologram_hub -g '*.dart'
  rg -n "http\.|MvpRequestClient|WorkspaceScopedService|StrategyService|MarketingService|WorkforceService|VaultMvpService|SettingsMvpService" frontend/lib/modules/hologram_hub -g '*.dart'
  ```

  Categorize every import as public model/facade, feature implementation, or unrelated legacy UI. Record count and paths in ledger. Do not blindly replace imports with barrel files until the feature facade actually provides the needed capability.

- [ ] **Step 2: Write red composition tests.**

  `HologramHubFacade` test supplies fake *facades*, never raw repositories, and proves partial data plus one `ApiFailure` renders a hub overview with clear per-section failure—not sample/empty content. Test commands delegate only to supplied `HubCommandFacade`. View test proves a `not_observed` Runtime section does not show green/now status.

  Run: `cd frontend && flutter test test/surfaces/hologram_hub/hologram_hub_facade_test.dart test/surfaces/hologram_hub/hologram_hub_view_test.dart`

  Expected: FAIL before the surface exists.

- [ ] **Step 3: Introduce Hub surface and migrate imports one feature at a time.**

  Start with Canvas, Marketing, Runtime, Workforce, Settings, then Vault. Each feature facade is injected by a binding/composition root. Any hub-specific DTO belongs under `surfaces/hologram_hub`; it may refer to public domain contracts but cannot reconstruct source data. Adapt existing Hub widgets/controllers progressively; do not move 102 files in one commit.

- [ ] **Step 4: Turn Hub implementation-import finding into a hard failure.**

  After every active Hub caller is migrated, modify the boundary scanner/test so any `modules/hologram_hub` or `surfaces/hologram_hub` import of a feature implementation fails. It must allow only `features/<name>/public.dart` from the migrated feature. Leave unrelated legacy Hub UI imports out of scope only if not a feature implementation; list them in ledger.

- [ ] **Step 5: Verify and commit.**

  Run:

  ```bash
  cd frontend && flutter test test/surfaces/hologram_hub/hologram_hub_facade_test.dart test/surfaces/hologram_hub/hologram_hub_view_test.dart
  make frontend-analyze frontend-boundary-check
  rg -n "^import .*modules/(strategy|marketing|agents|vault|settings|workspace_runtime)/(services|controllers|bindings|views|data|repositories)/" frontend/lib/modules/hologram_hub frontend/lib/surfaces/hologram_hub -g '*.dart'
  ```

  Expected: tests/checks pass; final scan has no direct feature-implementation import.

  ```bash
  git add frontend/lib/surfaces/hologram_hub frontend/lib/modules/hologram_hub scripts/check_frontend_boundaries.mjs tests/quality/test_frontend_boundaries.py frontend/test/surfaces/hologram_hub docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "refactor(frontend): compose hologram hub from feature facades"
  ```

## Task 6: Migrate remaining visible raw service routes and prepare legacy removal

**Files:**

- Modify: remaining active caller files returned by Step 1 scans
- Modify: `frontend/lib/modules/strategy/services/strategy_service.dart`
- Modify: `frontend/lib/modules/marketing/services/marketing_service.dart`
- Modify: `frontend/lib/core/network/workspace_scoped_service.dart` only to remove moved callers; do not delete in this task
- Modify: `docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md`
- Test: focused replacement feature/controller/widget tests

- [ ] **Step 1: Produce a complete raw-call inventory.**

  Run:

  ```bash
  rg -n "WorkspaceScopedService|WorkspaceService|getJson\(|postJson\(|putJson\(|patchJson\(|deleteJson\(|http\.(get|post|put|patch|delete)" frontend/lib/modules frontend/lib/surfaces -g '*.dart'
  rg -n "Map<String, dynamic>|\bdynamic\b" frontend/lib/modules/strategy frontend/lib/modules/marketing frontend/lib/modules/hologram_hub -g '*.dart'
  ```

  Put each active route caller in the acceptance ledger with capability owner and destination facade. Classify unreachable/dead code with evidence rather than assuming it is inactive.

- [ ] **Step 2: Migrate in owner-route batches, never by mechanical replace.**

  Batches are: Strategy Canvas, Strategy other visible MVP route, Marketing MVP, Runtime, Workforce, Settings, Vault, then Hub. Before each caller change write a test that asserts typed facade behavior. If an endpoint lacks a generated contract/owner test/real E2E path, stop that caller and leave it `BLOCKED`; do not wrap the raw call in a new repository.

- [ ] **Step 3: Keep source complexity shrinking, not relocating.**

  For every extracted legacy service method, delete the corresponding raw route/decoder/map cast after the facade caller is proven. Do not create a “new legacy” bridge that returns `Map<String, dynamic>`. Split a large old service only when its active callers have been migrated; name remaining legacy sections and their owner in the ledger.

- [ ] **Step 4: Verify direct callers are gone from migrated capability paths.**

  Run:

  ```bash
  make frontend-boundary-check
  make frontend-analyze
  rg -n "WorkspaceScopedService|WorkspaceService|getJson\(|postJson\(|putJson\(|patchJson\(|deleteJson\(" frontend/lib/features frontend/lib/surfaces -g '*.dart'
  ```

  Expected: no matches in new features/surfaces. Legacy `modules/*` matches are permitted only while explicitly recorded; no match may be marked resolved merely because UI tests do not cover it.

- [ ] **Step 5: Commit each route-owner batch and record evidence.**

  One commit per ownership batch, for example:

  ```bash
  git add frontend/lib/features/strategy frontend/lib/modules/strategy frontend/test/features/strategy docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "refactor(frontend): retire migrated strategy raw callers"
  ```

  Do not delete `workspace_scoped_service.dart` here. Master Task 3 owns final deletion after its caller scan is empty.

## Task 7: Final frontend handoff to master release gate

**Files:**

- Modify: `docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md`
- Test: focused feature tests only; no status-only code

- [ ] **Step 1: Run all migrated feature tests and static checks.**

  Run:

  ```bash
  cd frontend && flutter test test/features test/surfaces/hologram_hub
  make frontend-analyze frontend-boundary-check
  ```

  Expected: PASS. A flaky or skipped test is not evidence.

- [ ] **Step 2: Verify truthful parsing and no raw new architecture.**

  Run:

  ```bash
  rg -n "DateTime\.now\(|\?\? .*Unknown|\?\? .*0|\?\? .*Healthy|Map<String, dynamic>|\bdynamic\b" frontend/lib/features frontend/lib/surfaces -g '*.dart'
  rg -n "WorkspaceScopedService|WorkspaceService|getJson\(|postJson\(|putJson\(|patchJson\(|deleteJson\(" frontend/lib/features frontend/lib/surfaces -g '*.dart'
  ```

  Expected: review every match. A match is allowed only for non-source UI layout/defaulting that cannot represent business/source facts; record its file/line/reason in ledger. Any data/transport match is a failure.

- [ ] **Step 3: Update only evidence that actually exists and commit.**

  For each capability, enter exact Flutter repository, backend contract test, real E2E test name, caller state, status, commit. `VERIFIED` requires the real-stack command from Agent/Control Task 6; local Flutter test alone is `READY` at most.

  ```bash
  git add docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md
  git commit -m "docs: record frontend mvp migration evidence"
  ```
