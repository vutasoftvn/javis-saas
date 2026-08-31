# Frontend Legacy Boundary and Coverage Gate Design

**Status:** Implemented — locally verified; GitHub Actions pending its next run

**Date:** 2026-09-01

## Goal

Turn two confirmed frontend-quality gaps into deterministic, low-risk release
gates without changing product behaviour:

1. prevent new code from taking a dependency on the legacy
   `WorkspaceScopedService`; and
2. fail CI when Flutter line coverage falls below a reproducible initial floor.

This is a foundation tranche for the approved modular-MVP migration.  It does
not claim that all legacy services are migrated, nor does it split the large
Strategy, Marketing, or Agent Platform services in the same change.

## Evidence and current state

- A fresh full `flutter test --coverage` run records **7,661 / 16,492 lines =
  46.45%**.  The previous 48.20% figure came from an ignored local LCOV
  artifact and was not a reproducible baseline.  The GitHub quality job already
  runs `flutter test --coverage` and uploads the LCOV file, but it does not
  evaluate a threshold.
- The current scanner rejects `WorkspaceScopedService` only inside
  `frontend/lib/features/*`.  It does not stop a new `modules/*` caller from
  being added.
- `WorkspaceScopedService` has ten direct imports that must remain working
  until their individual vertical slices migrate:

  - `core/services/function_status_service.dart`
  - `modules/approvals/services/approvals_service.dart`
  - `modules/finance/services/finance_service.dart`
  - `modules/legal/services/ai_compliance_service.dart`
  - `modules/legal/services/legal_service.dart`
  - `modules/sales/services/sales_service.dart`
  - `modules/strategy/services/next_best_action_service.dart`
  - `modules/strategy/services/outcomes_service.dart`
  - `modules/tasks/services/task_service.dart`
  - `modules/workflows/services/workflows_service.dart`

  `MissionControlService` and `CompanyWorkspaceView` import other classes named
  `WorkspaceService`; they are not callers of this legacy network base class.

- The approved modular-MVP design already defines
  `WorkspaceScopedService` as a compatibility layer and assigns final deletion
  to the master decommission task.  This design enforces that decision rather
  than overriding it.

## Considered approaches

### A. Delete the legacy base class now

This would force a broad migration of ten independent product domains.  It
would change transport, authentication, decoding, and visible behaviour at the
same time, without focused acceptance tests for each.  **Rejected**: too much
regression risk and contrary to the approved strangler migration.

### B. Permit legacy use everywhere and rely on review discipline

This keeps the application compiling, but permits each new module or feature
to add another caller.  The eventual deletion task would then have unbounded
scope.  **Rejected**: it does not create an enforceable boundary.

### C. Freeze the exact legacy caller inventory and add a coverage ratchet

Treat the ten current imports as an explicit compatibility allowlist.  The
frontend scanner fails any additional import, including a new import under
`modules/*`; existing `features/*` remains absolutely forbidden.  Add a
dependency-free LCOV evaluator with a conservative 46.0% initial line-coverage
floor.  **Selected**: it protects architecture and quality now while leaving
behavioural migrations small and independently testable.

## Design

### 1. Legacy transport boundary

`scripts/check_frontend_boundaries.mjs` becomes the single source of truth for
the legacy caller freeze:

- It keeps an exact, repository-relative allowlist of the ten files above.
- Any Dart import resolving to `workspace_scoped_service.dart` outside that
  allowlist fails with `LEGACY_WORKSPACE_SCOPED_ALLOWLIST`.
- An import from `features/*` fails regardless of any future allowlist edit
  with `NO_LEGACY_WORKSPACE_SCOPED_SERVICE`.
- The check applies to both `package:frontend/...` and relative Dart imports.
- The compatibility class and typedef remain unchanged in this tranche.  No
  runtime request, response, token, workspace-scoping, or UI behaviour changes.

The test suite must prove all three cases: an allowlisted legacy caller passes,
a synthetic new legacy-module caller fails, and a synthetic feature caller
fails.  It must also prove the repository scan is green, so the allowlist
cannot silently drift.

When a feature is migrated to its typed `MvpRequestClient` facade, its old
allowlist entry is removed in the same change.  Only the master task may delete
`workspace_scoped_service.dart`, after this inventory is empty and every
replacement has focused contract and UI-state proof.

### 2. Coverage quality gate

Add `scripts/check_frontend_coverage.mjs`, a small Node script using only the
standard library.  Given an LCOV file and a required minimum, it:

- sums `LH` and `LF` records across source files;
- rejects a missing, malformed, or zero-instrumented-line report;
- emits the measured line count and percentage; and
- exits non-zero when the percentage is below the requested floor.

The first floor is **46.0% line coverage**, deliberately below the measured
46.45% baseline to tolerate a small, explainable toolchain variation while
preventing regressions.  It is not a proxy for risk coverage and is not a
claim that 48% is sufficient.  The ratchet policy is:

1. never lower the floor without an approved incident/rebaseline note;
2. raise it after a committed, reproducible coverage increase; and
3. introduce per-feature risk-module floors only with the relevant migration
   slice, where their test ownership is known.

The local command `make frontend-coverage-check` runs Flutter tests with
coverage and then evaluates `frontend/coverage/lcov.info`.  The GitHub
`frontend` job evaluates the same generated report before moving it to the
test-results artifact directory.  Thus local and CI enforcement use the same
parser, data format, and threshold.

The evaluator has focused Node tests for valid passing data, below-floor data,
missing required records, and a malformed/no-source report.  The test fixtures
are intentionally tiny; no generated LCOV artifact is committed or used as a
baseline source of truth.

### 3. Deferred structural decomposition

The following hotspots remain explicitly out of scope for this safety tranche:

| Hotspot | Future decomposition boundary |
|---|---|
| `StrategyService` | Canvas, OKR, Planning, Portfolio, Lifecycle repositories |
| `MarketingController` / `MarketingService` | Context, Campaign/Asset, Experiment/Learning, Measurement slices |
| `AgentPlatformService` | Workforce, Runs, Approvals, Schedules, Telemetry repositories |

They are already specified in
`docs/superpowers/specs/2026-08-31-maintainable-modular-truthful-mvp-design.md`
and `docs/superpowers/plans/2026-08-31-maintainable-mvp-frontend.md`.
Each will be executed as a separately approved, test-first vertical slice.  The
new freeze makes their completion measurable: each removes one legacy caller
and may raise the coverage floor only after tests land.

## Files and verification

Implementation is constrained to:

- modify `scripts/check_frontend_boundaries.mjs`;
- create `scripts/check_frontend_coverage.mjs` and focused Node tests/fixtures;
- modify `Makefile` to expose `frontend-coverage-check`;
- modify `.github/workflows/quality.yml` to run the coverage evaluator; and
- add/adjust boundary tests for the frozen import inventory.

No application Dart service, widget, API contract, backend, database, or
deployment runtime file is changed.

The implementation acceptance gate is:

```bash
make frontend-boundary-check
make frontend-coverage-check
make frontend-test
make frontend-analyze
node --test <coverage-evaluator-test-path>
git diff --check
```

The full test run is expected to regenerate `frontend/coverage/lcov.info`.
That generated file is a local verification artifact and is not intentionally
added to version control.

## Risks and rollback

- A scanner false positive blocks a pull request but has no runtime impact.  It
  is resolved by correcting an intentionally migrated caller or, if genuinely
  legacy, adding the exact file after review; broad directory exemptions are
  prohibited.
- A coverage failure is a quality failure rather than a deployment outage.  A
  valid increase or toolchain rebaseline updates the documented floor through
  review; CI must not be disabled to pass it.
- Since this tranche changes only quality tooling, reverting its small set of
  scripts/workflow lines restores the previous delivery behaviour without data
  migration or user-visible rollback.

## Non-goals

- Removing `WorkspaceScopedService` or changing the ten legacy callers.
- Treating coverage percentage as complete functional, security, or E2E proof.
- Refactoring a large service merely to reduce its line count.
- Raising the coverage floor above data produced by the current deterministic
  Flutter test collection.
