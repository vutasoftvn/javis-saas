# Strategy Canvas Facade Design

**Status:** Proposed — awaiting review before implementation planning

**Date:** 2026-09-01

## Goal

Move the active Strategy Canvas CRUD path from raw `ApiClient` calls to the
typed MVP transport without changing the current Foundation tab or Hologram
activation behaviour.  The migration establishes the first real
`features/strategy` vertical slice and leaves Canvas detail, revision, AI
generation, review, and foundation-save workflows for a later slice.

## Evidence

- `FoundationController` owns the visible Foundation tab.  It calls
  `StrategyService` for listing, creating, updating, deleting, and selecting
  canvases.
- `HubStageMixin.completeCompanyActivation` creates a Canvas through the same
  `StrategyService` before running its existing revision/foundation workflow.
- Today `CanvasService` performs Canvas CRUD through raw `/strategy/canvases`
  routes and `StrategyService` exposes raw maps to both callers.
- The canonical Company endpoints already exist under
  `/operations/strategy/canvases`, are declared in
  `shared/contracts/mvp-surface.json`, and have Company, Flutter, and real E2E
  proof.  `MvpRequestClient` preserves typed `ApiSuccess`/`ApiFailure`,
  workspace context, and generated endpoint ownership.
- `FoundationController.selectCanvas` requires revision-rich detail that is not
  returned by the canonical Canvas summary endpoint.  It cannot be moved to
  the CRUD facade without expanding the Company contract.

## Considered approaches

### A. Rewrite FoundationController to a new facade immediately

This would make all controller state typed, but it also requires replacing the
revision/foundation detail shape in the same change.  It combines an endpoint
contract expansion with a UI state rewrite.  **Rejected for this tranche**.

### B. Add a typed Canvas facade and retain a compatibility adapter

The feature owns typed Canvas summaries and canonical CRUD requests.
`CanvasService` delegates only CRUD to that facade and translates at the legacy
boundary to the existing `StrategyListResult<Map<String, dynamic>>` and
exception contracts.  The Foundation tab and Hub therefore use the new
transport transitively while their visible behaviour remains stable.
**Selected.**

### C. Keep raw routes until all Canvas workflows can move together

This avoids an adapter but leaves the most established vertical contract path
unmigrated and postpones proof that the feature boundary works.  **Rejected.**

## Architecture

```text
FoundationController / HubStageMixin
                 │ existing StrategyService API
                 ▼
           CanvasService compatibility adapter
                 │ CanvasFacade (public feature API)
                 ▼
    features/strategy/data/CanvasRemoteRepository
                 │ MvpRequestClient + generated MvpEndpoint
                 ▼
     Company /operations/strategy/canvases
```

### Feature surface

Create a focused public feature API under `frontend/lib/features/strategy`:

```text
domain/canvas_summary.dart              immutable typed CanvasSummary
application/canvas_repository.dart      interface for list/get/create/update/delete
data/canvas_remote_repository.dart      strict MvpRequestClient decoder
canvas_facade.dart                      public CanvasFacade operations
public.dart                             exports only domain + facade contracts
```

`CanvasSummary` keeps Snowflake IDs as `String` and represents optional
description/current revision/member fields as nullable.  Its decoder requires
the non-optional fields supplied by the Company contract; malformed success
data throws during decoding so `MvpRequestClient` returns `ApiFailure` with
`malformedResponse`.  It never substitutes blank IDs, names, timestamps, or
workspace IDs.

The public facade exposes only these typed operations:

```dart
abstract interface class CanvasFacade {
  Future<ApiResult<List<CanvasSummary>>> list();
  Future<ApiResult<CanvasSummary>> get(String canvasId);
  Future<ApiResult<CanvasSummary>> create(CreateCanvasCommand command);
  Future<ApiResult<CanvasSummary>> update(UpdateCanvasCommand command);
  Future<ApiResult<void>> delete(String canvasId);
}
```

Every operation uses the matching generated endpoint.  Repository/data code
does not import `StrategyService`, `CanvasService`, `GetX`, secure storage, or
raw route literals.  Authentication and workspace context are resolved only by
`MvpRequestClient`.

### Compatibility boundary

`CanvasService` receives a `CanvasFacade` dependency, defaulting to the
feature implementation.  Its existing CRUD method signatures remain stable:

- successful lists map `CanvasSummary` values to the old map shape and return
  `StrategyListResult.success`, including a genuine empty list;
- `ApiFailure` maps to `StrategyListResult.failure` using the owner error
  message, never to a silent empty collection;
- create/update map a successful summary to the legacy map shape; failures
  become `StrategyApiException` so existing callers preserve their failure
  paths; and
- delete returns only on `ApiSuccess<void>`; failures become the same typed
  exception.

This adapter means `FoundationController` and `HubStageMixin` retain their
current public calls.  A successful create still exposes a top-level `id`, so
the Hub can continue immediately to its existing revision API.

`getCanvasDetail`, revision operations, AI generation, review, and
foundation-save remain in `CanvasService` on their present path.  In
particular, `selectCanvas` continues to use the revision-rich legacy detail
response.  No new UI state, placeholder, fallback data, or endpoint is
invented in this tranche.

`StrategyMvpClient` keeps its externally visible API for existing tests and
future callers, but its Canvas summary methods delegate through the new public
facade rather than retaining a duplicate decoder/transport implementation.
Its non-Canvas methods are not changed.

## Tests and acceptance criteria

Tests are written first and prove observable behaviour:

1. The remote repository sends list/create/get/update/delete to their generated
   MVP endpoints with MvpRequestClient authentication/workspace semantics.
2. A populated summary preserves string IDs and optional values; a valid empty
   list remains `ApiSuccess` with `dataState.empty`; malformed summary data,
   401, and 5xx remain `ApiFailure`, never `[]` or a default summary.
3. Facade tests prove result propagation with a repository fake; no test uses a
   fake as real E2E evidence.
4. Adapter tests prove Foundation/Hub-compatible map outputs, truthful list
   errors, and command failures.  Existing Canvas Service/Strategy tests are
   updated to inject the adapter dependency rather than intercept raw CRUD
   routes.
5. The generated contract's existing Company test and real E2E Canvas test
   remain green.  The frontend boundary scan proves feature code does not
   import legacy transport.

Acceptance requires focused Dart tests, existing strategy tests, Company Canvas
contract/runtime tests, the real Canvas E2E, `make frontend-analyze`,
`make frontend-boundary-check`, and a scan that finds no raw transport, token,
or `WorkspaceScopedService` import below `features/strategy`.

## Non-goals and follow-up

- Removing `WorkspaceScopedService` or any of its ten frozen callers.
- Migrating revision/AI/foundation detail workflows, which require a typed
  revision-detail contract first.
- Rewriting Foundation tab widgets/controllers, replacing GetX, or changing
  the Hologram activation sequence.
- Modifying Company endpoints, database schema, E2E harness topology, or
  backend ownership.

After this slice, the next Strategy decision is whether to define a typed
revision-detail contract or migrate a different legacy domain.  `CanvasService`
is deleted only when all of its remaining advanced callers have a proven typed
replacement.
