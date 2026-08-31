# Maintainable MVP Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a green, contract-strict baseline which makes fabricated client states, raw feature transport, architecture regressions, and impure “real E2E” tests fail in CI.

**Architecture:** Preserve the four deployment planes. Foundation supplies the shared Dart transport seam, exact failure semantics, generated-contract hygiene, and static policy checks consumed by the Company, Agent/Control, and Flutter migrations. It does not introduce a service or change an owner route.

**Tech Stack:** Flutter/Dart/GetX/http, TypeScript/Encore, Python/FastAPI/Pydantic/SQLAlchemy, pytest, Flutter test, Node/Python check scripts, Make, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-31-maintainable-modular-truthful-mvp-design.md`

## Global Constraints

- Read and obey `docs/superpowers/plans/2026-08-31-maintainable-modular-mvp-master.md`; its constraints and executor protocol apply to every task below.
- Do not hand-edit `apps/cosa/api/mvp_contracts_generated.py` or `frontend/lib/core/network/mvp_contracts_generated.dart`; edit `shared/contracts/mvp-surface.json` then run the generator.
- A malformed response, missing required field, invalid `observed_at`, unknown enum, non-2xx response, or unavailable token is an explicit typed failure. It must not become a current timestamp, empty collection, false, zero, or a success-shaped model.
- No test in this plan may make a runtime client return sample data. Fixtures are allowed only inside tests and must be visibly named fixture data.
- Do not start a child-plan task before its named Foundation dependency is committed and the working tree is clean.

## Completion definition

The following commands pass before a consumer plan starts, except `make maintainable-mvp-release-check`, which intentionally remains blocked until the final master task:

```bash
make lint
make typecheck-py
cd services/company && npx tsc --noEmit
cd services/cosa && npx tsc --noEmit
make frontend-analyze
make mvp-contracts-check mvp-surface-check route-inventory-check
make frontend-boundary-check mvp-e2e-purity-check
```

## Task 1: Repair the current quality baseline without weakening checks

**Files:**

- Modify: `scripts/gen-mvp-contracts.mjs`
- Generated: `apps/cosa/api/mvp_contracts_generated.py`
- Generated: `frontend/lib/core/network/mvp_contracts_generated.dart`
- Modify: `apps/cosa/api/mvp_response.py`
- Modify: `apps/cosa/api/settings_routes.py`
- Modify: `apps/cosa/api/vault_routes.py`
- Modify: `apps/cosa/api/workforce_routes.py`
- Modify: `packages/agent/vault/repository.py`
- Modify: `packages/agent/workforce/repository.py`
- Modify: `services/company/commercial/services/marketing-mvp.service.ts`
- Modify: `services/company/operations/services/workspace-runtime.service.ts`
- Modify: `services/company/operations/handlers/workspace-runtime.handler.ts`
- Modify: `services/company/operations/handlers/okr.handler.ts`
- Modify: `services/company/operations/services/canvas.service.ts`
- Modify: the directly failing test files named by the TypeScript compiler, only if their asserted contract is stale
- Modify: `pyproject.toml`
- Create: `tests/quality/test_generated_mvp_contracts.py`

**Interfaces:**

- The generator is the only writer of MVP contract artifacts.
- Python source must have one canonical package identity: `agent.*`, never both `agent.*` and `packages.agent.*` for the same module.
- `TenantContext` uses its declared member identifier consistently; no call site may invent `memberId` when the contract exposes `workforceMemberId`.

- [ ] **Step 1: Capture all current failures, including filenames and line numbers.**

  Run:

  ```bash
  make lint
  make typecheck-py
  cd services/company && npx tsc --noEmit
  cd services/cosa && npx tsc --noEmit
  make frontend-analyze
  ```

  Expected: current known failures are captured before editing; do not suppress a linter/type checker or lower its rule level.

- [ ] **Step 2: Write a generator idempotence test before changing output style.**

  Test that invoking `make mvp-contracts-gen` twice leaves no diff and generated Python uses ruff-compatible imports/types. The test must execute the generator in a temporary copied checkout or compare deterministic generated text; it must not rewrite the developer checkout while asserting.

  Run: `PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/quality/test_generated_mvp_contracts.py -q`

  Expected: FAIL if the generator still emits lint-invalid Python or non-deterministic content.

- [ ] **Step 3: Make the smallest source corrections indicated by the captured diagnostics.**

  Apply these exact categories of correction:

  1. Make generated Python imports, `Final`/`Literal` declarations, ordering, and blank lines ruff compliant in `scripts/gen-mvp-contracts.mjs`; then run `make mvp-contracts-gen`.
  2. Replace the mixed `packages.agent.vault.models` import with the canonical `agent.vault.models` identity and configure mypy package bases/path so it discovers each module once. Do not silence `duplicate module` with `ignore_missing_imports`.
  3. Correct only mechanical Python lint faults in the named route/repository files: imports, exception chaining, unused symbols, line style, and annotations. Semantic Settings/Vault behavior remains for the Agent/Control plan, but this task must not leave a catch-and-return-empty fallback.
  4. Correct Company compiler errors at their source: guard potentially missing dynamic-SQL values, preserve nullable/number distinctions, use `workforceMemberId`, add fields only where the owned task schema actually has them, and update stale tests to the handler’s real input contract. Do not widen a type to `any` or add an unchecked cast.
  5. Fix the two Flutter analysis warnings in the identified Settings MVP service with explicit typed handling; do not discard values merely to silence analysis.


- [ ] **Step 4: Run the currently available baseline commands and commit the mechanically verifiable repair.**

  Run the first six Completion definition commands through `make mvp-contracts-check mvp-surface-check route-inventory-check`. `frontend-boundary-check` and `mvp-e2e-purity-check` are created in Task 3 and are first required in Task 4.

  Expected: all pass. If a command identifies a behavioral issue rather than a mechanical typing/lint error, stop and put that change in its owner child plan rather than hide it here.

  ```bash
  git add scripts/gen-mvp-contracts.mjs apps/cosa/api/mvp_contracts_generated.py frontend/lib/core/network/mvp_contracts_generated.dart apps/cosa/api/mvp_response.py apps/cosa/api/settings_routes.py apps/cosa/api/vault_routes.py apps/cosa/api/workforce_routes.py packages/agent/vault/repository.py packages/agent/workforce/repository.py services/company/commercial/services/marketing-mvp.service.ts services/company/operations/services/workspace-runtime.service.ts services/company/operations/handlers/workspace-runtime.handler.ts services/company/operations/handlers/okr.handler.ts services/company/operations/services/canvas.service.ts tests/quality/test_generated_mvp_contracts.py pyproject.toml frontend/lib/modules/settings/services/settings_mvp_service.dart
  git commit -m "fix: establish maintainable mvp quality baseline"
  ```


## Task 2: Create strict plane-aware Flutter transport primitives

**Files:**

- Create: `frontend/lib/core/network/api_auth_resolver.dart`
- Modify: `frontend/lib/core/network/api_result.dart`
- Modify: `frontend/lib/core/network/api_client.dart`
- Modify: `frontend/lib/core/network/mvp_request_client.dart`
- Test: `frontend/test/core/network/api_auth_resolver_test.dart`
- Test: `frontend/test/core/network/api_result_test.dart`
- Test: `frontend/test/core/network/mvp_request_client_test.dart`

**Interfaces:**

```dart
enum ApiPlane { platform, company, agent }

abstract interface class ApiAuthResolver {
  Future<String?> tokenFor(ApiPlane plane);
  Future<String?> workspaceId();
}

sealed class ApiResult<T> {
  const ApiResult();
}
final class ApiSuccess<T> extends ApiResult<T> {
  const ApiSuccess(this.value, this.meta);
  final T value;
  final ApiResponseMeta meta;
}
final class ApiFailure<T> extends ApiResult<T> {
  const ApiFailure(this.failure);
  final ApiFailureDetail failure;
}
```

- [ ] **Step 1: Write failing token-plane tests.**

  Cover these cases with a fake secure store confined to the test:

  - Platform resolves only the existing platform access-token key.
  - Company resolves only the local Company-session key.
  - Agent resolves the configured Agent-plane credential path, or returns an `ApiFailure` at request construction if that plane has no credential contract.
  - A missing token does not fall back to a token belonging to another plane.
  - Workspace ID is passed as an identifier string unchanged.

  Run: `cd frontend && flutter test test/core/network/api_auth_resolver_test.dart`

  Expected: FAIL because `MvpRequestClient` currently reads generic `auth_token` and has no plane discriminator.

- [ ] **Step 2: Write failing strict-decoding tests.**

  Test that `observed_at` is required where the endpoint schema declares it, accepts only valid ISO-8601 timestamps, and does not call `DateTime.now()` for invalid/missing input. A source reference must reject a missing/invalid kind, reference, or observation timestamp rather than defaulting to `unknown`/empty text. Test a non-2xx result, invalid JSON envelope, malformed body, and source state `not_observed` each produce a distinguishable `ApiFailure` or explicitly declared source state.

  Run:

  ```bash
  cd frontend && flutter test test/core/network/api_result_test.dart test/core/network/mvp_request_client_test.dart
  ```

  Expected: FAIL because the current client converts failures to nullable success-looking values and `ApiResponseMeta.fromJson` creates a current timestamp.

- [ ] **Step 3: Implement the shared seam, retaining compatibility only at its outer edge.**

  1. Extract existing endpoint-token knowledge from `ApiClient._tokenForEndpoint` into `ApiAuthResolver`; delete duplicate token-key selection from callers.
  2. Make `MvpRequestClient` require `ApiPlane`, `ApiAuthResolver`, and a decoder returning `ApiResult<T>`.
  3. Parse all envelope metadata strictly. `observedAt` is nullable only for endpoint contracts explicitly declaring non-observation; absence is not substituted with local time.
  4. Preserve body/status/request-id in `ApiFailureDetail` for UI display and telemetry, redacting tokens and sensitive request bodies.
  5. Do not let `getJson`, `postJson`, or any new helper return `null`/`false` for transport failure.

- [ ] **Step 4: Run focused tests and static analysis, then commit.**

  Run:

  ```bash
  cd frontend && flutter test test/core/network/api_auth_resolver_test.dart test/core/network/api_result_test.dart test/core/network/mvp_request_client_test.dart
  make frontend-analyze
  ```

  Expected: PASS. The test suite must contain both an absence-of-fallback assertion and a cross-plane-token rejection assertion.

  ```bash
  git add frontend/lib/core/network/api_auth_resolver.dart frontend/lib/core/network/api_result.dart frontend/lib/core/network/api_client.dart frontend/lib/core/network/mvp_request_client.dart frontend/test/core/network/api_auth_resolver_test.dart frontend/test/core/network/api_result_test.dart frontend/test/core/network/mvp_request_client_test.dart
  git commit -m "feat(frontend): add strict plane-aware mvp transport"
  ```

## Task 3: Add enforceable source-boundary and E2E-purity guards

**Files:**

- Create: `scripts/check_frontend_boundaries.mjs`
- Create: `scripts/check_mvp_e2e_purity.py`
- Modify: `Makefile`
- Modify: `.github/workflows/quality.yml`
- Test: `tests/quality/test_frontend_boundaries.py`
- Test: `tests/quality/test_mvp_e2e_purity.py`
- Generated: `docs/architecture/generated/route-inventory.md` only through `make route-inventory`

**Interfaces:**

- `make frontend-boundary-check` checks only production Dart beneath `frontend/lib`.
- `make mvp-e2e-purity-check` checks only `tests/e2e/test_mvp_*.py` and their shared MVP fixtures.
- Both scripts print `path:line:rule:explanation` and exit non-zero on every violation; they do not auto-fix source.

- [ ] **Step 1: Write red tests for each prohibited construct.**

  Frontend fixture cases must detect: a feature importing another feature’s `services/`, `repositories/`, `controllers/`, or `data/` implementation; a Hologram Hub file importing any feature implementation; and a `modules/*` visible caller importing `WorkspaceScopedService` after its migration. Allow imports of a feature’s declared `public.dart` facade only.

  E2E fixture cases must detect every prohibited symbol from the master plan, including aliased imports and `pytest.mark.skip`; a normal `httpx.AsyncClient` targeting a configured real URL must remain allowed.

  Run:

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/quality/test_frontend_boundaries.py tests/quality/test_mvp_e2e_purity.py -q
  ```

  Expected: FAIL before scanner implementation.

- [ ] **Step 2: Implement AST-aware-enough deterministic scanners.**

  The Dart scanner must resolve relative and package imports to a normalized project path before applying its boundary matrix. The Python scanner must use `ast`, inspect imports, qualified symbol names, decorators, and calls; no `rg`-only false assurance. Treat unsupported dynamic import as a violation in required E2E tests.

- [ ] **Step 3: Wire non-optional Make and CI gates.**

  Add these targets:

  ```make
  frontend-boundary-check:
	 node scripts/check_frontend_boundaries.mjs

  mvp-e2e-purity-check:
	 PYTHONPATH=$(CURDIR) .venv/bin/python scripts/check_mvp_e2e_purity.py
  ```

  Add both to the existing quality workflow before any release job. CI must execute source scans even if integration infrastructure is unavailable.

- [ ] **Step 4: Demonstrate detection, then the clean repository, and commit.**

  Run fixture tests, then:

  ```bash
  make frontend-boundary-check mvp-e2e-purity-check
  make route-inventory-check
  ```

  Expected: PASS against current source. If it fails on a current violation, record it in the relevant child-plan task and do not weaken the scanner.

  ```bash
  git add scripts/check_frontend_boundaries.mjs scripts/check_mvp_e2e_purity.py Makefile .github/workflows/quality.yml tests/quality/test_frontend_boundaries.py tests/quality/test_mvp_e2e_purity.py docs/architecture/generated/route-inventory.md
  git commit -m "test: enforce mvp boundaries and e2e purity"
  ```

## Task 4: Set and prove the shared baseline handoff

**Files:**

- Modify: `docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md`
- Generated: `docs/architecture/generated/route-inventory.md` only through `make route-inventory`
- Test: existing quality tests only; do not create a status-only test

- [ ] **Step 1: Run every Foundation command from a clean checkout.**

  Run the Completion definition commands exactly, recording command output, commit hash, UTC time, and environment in the ledger’s Foundation row.

  Expected: every quality/static command passes. A skipped live E2E is not part of this Foundation claim and remains `BLOCKED`.

- [ ] **Step 2: Verify the handoff surface.**

  Run:

  ```bash
  rg -n "DateTime\.now\(\).*observed|auth_token|WorkspaceScopedService" frontend/lib/core/network
  rg -n "packages\.agent\.vault" apps packages
  git diff --check HEAD~1..HEAD
  ```

  Expected: no fabricated observation timestamp, no generic token lookup in `MvpRequestClient`, no duplicate vault package identity, and no whitespace errors.

- [ ] **Step 3: Commit evidence only if all static checks passed.**

  ```bash
  git add docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md docs/architecture/generated/route-inventory.md
  git commit -m "docs: record maintainable mvp foundation evidence"
  ```

  If any command fails, do not commit a success row. Open the owning task with the exact command failure instead.
