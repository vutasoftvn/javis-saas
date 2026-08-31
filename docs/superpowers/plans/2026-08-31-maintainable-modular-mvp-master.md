# Maintainable Modular Truthful MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the implemented MVP buildable, truthful, modular, and demonstrably maintainable without adding a deployable service or changing business ownership.

**Architecture:** Use a contract-first strangler migration. Keep Flutter, Control Plane, Company, and Agent Platform as the four deployment planes; introduce typed feature boundaries inside each plane, migrate one vertical slice at a time, then remove a legacy path only after its callers and proof are gone.

**Tech Stack:** Flutter/Dart/GetX/http, TypeScript/Encore/Drizzle/PostgreSQL, Python/FastAPI/Pydantic/SQLAlchemy, MinIO, pytest, Vitest, Flutter test, GitHub Actions, Node scripts.

**Spec:** `docs/superpowers/specs/2026-08-31-maintainable-modular-truthful-mvp-design.md`

## Global Constraints

- Do not create a new deployable microservice, rename the repository root, replace GetX, or move all Flutter files in one change.
- Runtime may read only owned storage or a configured connector. It must not create demo, placeholder, fake health, synthetic metric, fake role, default provider, or customer data.
- A success is exactly `populated` or `empty`. All other conditions are `ApiFailure` or the source-specific explicit state; never convert them to `null`, `[]`, `{}`, `false`, zero, `HEALTHY`, `connected`, or `verified`.
- `system_derived` presentation labels are allowed only when explicitly marked as such and may not impersonate source content.
- Browser workspace IDs do not authorize access. Every owner verifies actor, membership, and workspace server-side.
- Snowflake IDs are strings beyond the database boundary. Do not parse an ID to Dart `int`, JavaScript `number`, or `double`.
- Do not hand-edit generated MVP contract files. Edit `shared/contracts/mvp-surface.json`, run `make mvp-contracts-gen`, then commit generated output together.
- Existing migrations are immutable. New migrations are additive, include a down migration, and pass apply/rollback/reapply on an isolated database.
- `tests/e2e/test_mvp_*.py` may not import or use `ASGITransport`, `MockTransport`, `AsyncMock`, `FakeSDKModel`, `InMemory`, fake policy clients, monkeypatched transport, or required-test `pytest.skip`.
- A task stops and records a blocker if it needs a new product capability, a new deployable service, an altered applied migration, fabricated data, or an unapproved route.
- Angravity completes only the current unchecked task. It may not edit files outside that task's **Files** list except a generated file explicitly named by that task.

---

## Executor protocol for Angravity

1. Read this master plan, the linked spec, and the selected child plan before opening an editor.
2. Run `git status --short`; if it is non-empty, identify every overlapping file and stop for owner direction rather than overwrite another change.
3. Execute tasks in the dependency order below. A later task cannot be started because a related file looks easy.
4. For every task: write the named failing test, run its exact failing command, make only the named minimal change, run the exact passing command, run the task quality command, update the acceptance ledger, and commit only the files listed by the task.
5. Record an actual test skip as `UNVERIFIED`, never as `PASS`. Do not weaken a test, add a fallback, or replace a real dependency with a mock to obtain green output.
6. After each commit, run `git status --short` and `git show --stat --oneline HEAD`; if an unexpected file is included, stop before the next task.

## Programme map and dependency order

| Order | Child plan | Primary deliverable | May run after | Must finish before |
|---:|---|---|---|---|
| 0 | `2026-08-31-maintainable-mvp-foundation.md` | Green quality baseline, strict transport parsing/auth, architecture guards and ledger | immediately | all other workstreams |
| 1 | `2026-08-31-maintainable-mvp-company.md` | Typed Company Operations/Commercial application boundaries and truthful Runtime projection | Foundation Tasks 1–4 | related Flutter migration and Company real E2E |
| 2 | `2026-08-31-maintainable-mvp-agent-control-e2e.md` | Split Agent routers/repos, real Vault/Settings behavior, real cross-plane E2E stack | Foundation Tasks 1–4 | Workforce/Vault/Settings UI migration and release gate |
| 3 | `2026-08-31-maintainable-mvp-frontend.md` | Feature repositories and presentation boundaries, migrated visible callers, Hub facade | Foundation Tasks 1–4; matching owner routes | legacy-client removal |
| 4 | master Task 3 | Final legacy removal and release evidence | all child plans | release decision |

Company and Agent/Control work may run in parallel after Foundation because they own disjoint directories. Frontend may migrate only a capability whose owner route, response schema, source state, and backend tests are green. Hologram Hub migration is last because it consumes the feature facades.

## Fixed ownership and public boundaries

| Plane | Owner | May expose | Must not own |
|---|---|---|---|
| `services/cosa` | membership, identity, policy, connectors, nodes, Settings audit | redacted platform status | Company business state or Agent work records |
| `services/company` | Operations, Strategy, Commercial, Finance/Legal | business commands and read models | mutable Agent assignment/run/document/skill records |
| `packages/agent` | reusable runs, governance, workforce, vault, skills | typed ports and adapters | Company imports, Company DB writes, browser HTTP routing |
| `apps/cosa` | Agent composition and FastAPI adapters | Agent routes and worker orchestration | duplicated Agent domain persistence policy |
| Flutter `features/*` | view/domain contracts and remote repositories | typed user interactions | raw transport, cross-feature implementation imports |
| Flutter `surfaces/hologram_hub` | composition of public facades | hub-specific UI state | direct feature service/repository/controller access |

## Shared interfaces introduced by Foundation

All child plans consume these exact public signatures; none may define a competing equivalent.

```dart
abstract interface class ApiAuthResolver {
  Future<String?> tokenFor(ApiPlane plane);
  Future<String?> workspaceId();
}

abstract interface class HubOverviewQuery {
  Future<ApiResult<HubOverview>> load();
}

abstract interface class HubCommandFacade {
  Future<ApiResult<void>> execute(HubCommand command);
}
```

```ts
export interface RuntimeObservation {
  readonly sourceKind: "company" | "agent";
  readonly status: "healthy" | "degraded" | "unavailable" | "not_observed";
  readonly observedAt: Date | null;
  readonly evidenceRef: string | null;
}
```

```python
@runtime_checkable
class WorkforceRepository(Protocol):
    async def list_assignments(self, workspace_id: str, *, status: str | None = None) -> list[WorkforceAssignmentRecord]: ...

@runtime_checkable
class VaultRepository(Protocol):
    async def create_draft(self, workspace_id: str, title: str, *, kind: str, created_by: str) -> VaultDocumentRecord: ...
```

## Cross-plan acceptance ledger

### Task 1: Establish evidence rows before code moves

**Files:**

- Modify: `docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md`
- Modify: `shared/contracts/mvp-surface.json`
- Modify: `scripts/mvp_surface_check.py`
- Test: `tests/quality/test_mvp_surface_check.py`

**Interfaces:**

- Consumes `capabilities[]` from `shared/contracts/mvp-surface.json`.
- Produces one ledger row per enabled capability with `owner`, `source_kind`, `flutter_repository`, `backend_test`, `real_e2e_test`, `legacy_callers`, `status`, and `evidence_commit`.

- [ ] **Step 1: Write the failing ledger-completeness test.**

  ```python
  def test_enabled_capability_requires_real_e2e_and_legacy_state(tmp_path: Path) -> None:
      manifest = {"capabilities": [{"id": "strategy.canvas.list", "enabled": True}]}
      ledger = "| capability_id | owner | real_e2e_test | legacy_callers | status |\n| strategy.canvas.list | company |  |  | READY |"
      assert validate_manifest_ledger(manifest, ledger) == [
          "strategy.canvas.list: real_e2e_test is required",
          "strategy.canvas.list: legacy_callers is required",
      ]
  ```

- [ ] **Step 2: Run the test and verify it fails.**

  Run: `PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/quality/test_mvp_surface_check.py::test_enabled_capability_requires_real_e2e_and_legacy_state -q`

  Expected: FAIL because the validator does not require these fields.

- [ ] **Step 3: Add exact ledger validation and real rows.**

  Add `real_e2e_test`, `legacy_callers`, and `evidence_commit` to the validator's required fields. Set every current MVP row to `BLOCKED` until its listed command completes; do not mark a row `READY` merely because a unit test passes.

- [ ] **Step 4: Run the check and commit.**

  Run: `make mvp-surface-check`

  Expected: PASS only after every enabled capability has a non-empty evidence path and explicit legacy state.

  ```bash
  git add docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md shared/contracts/mvp-surface.json scripts/mvp_surface_check.py tests/quality/test_mvp_surface_check.py
  git commit -m "test: require mvp evidence ledger fields"
  ```

### Task 2: Enforce final release completeness

**Files:**

- Modify: `scripts/mvp_surface_check.py`
- Modify: `Makefile`
- Modify: `.github/workflows/quality.yml`
- Test: `tests/quality/test_mvp_surface_check.py`

**Interfaces:**

- Produces `make maintainable-mvp-release-check`.
- Consumes all acceptance-ledger rows and fails unless each enabled capability is `VERIFIED` with an immutable commit hash.

- [ ] **Step 1: Write the failing release-state test.**

  ```python
  def test_release_check_rejects_blocked_enabled_capability() -> None:
      ledger = [{"capability_id": "vault.document.list", "enabled": True, "status": "BLOCKED", "evidence_commit": ""}]
      assert release_errors(ledger) == ["vault.document.list: expected VERIFIED with evidence_commit"]
  ```

- [ ] **Step 2: Run it and verify it fails.**

  Run: `PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/quality/test_mvp_surface_check.py::test_release_check_rejects_blocked_enabled_capability -q`

  Expected: FAIL because release-state validation is absent.

- [ ] **Step 3: Add the Make and CI gate.**

  Implement `maintainable-mvp-release-check` as the composition of `lint`, `typecheck-py`, Company/COSA TypeScript type checks, `frontend-analyze`, generated-contract checks, frontend boundary check, E2E purity check, and real MVP E2E. The CI job must run the same target against isolated dependencies.

- [ ] **Step 4: Verify the gate rejects an incomplete ledger and commit.**

  Run: `make maintainable-mvp-release-check`

  Expected: FAIL while any enabled row remains `BLOCKED`; preserve this result as release evidence, then allow it to pass only in the final task.

  ```bash
  git add scripts/mvp_surface_check.py Makefile .github/workflows/quality.yml tests/quality/test_mvp_surface_check.py
  git commit -m "ci: gate release on verified mvp evidence"
  ```

### Task 3: Final decommission and release decision

**Files:**

- Modify: `docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md`
- Modify: `docs/operations/release-security-checklist.md`
- Modify: `docs/operations/deployment.md`
- Delete only after caller scan is empty: `frontend/lib/core/network/workspace_scoped_service.dart`
- Test: `tests/quality/test_mvp_surface_check.py`

**Interfaces:**

- Consumes all child-plan commits and their evidence rows.
- Produces a release checklist that states `VERIFIED` only for commands actually run against authorized infrastructure.

- [ ] **Step 1: Run the legacy caller scan before deletion.**

  Run: `rg -n "WorkspaceScopedService|WorkspaceService|getJson\(|postJson\(|putJson\(|patchJson\(" frontend/lib`

  Expected: no production caller; test fixtures may mention the removed type only after their tests are deleted in the same commit.

- [ ] **Step 2: Run the full release target.**

  Run: `make maintainable-mvp-release-check`

  Expected: PASS with no skipped required MVP E2E, no ghost enabled route, and all ledger rows `VERIFIED`.

- [ ] **Step 3: Record only observed evidence.**

  In the release checklist, write command, UTC timestamp, commit hash, environment, and result for every verified check. Keep edge/WAF as `UNVERIFIED` unless `scripts/verify_edge_rate_limit.sh` returned an observed HTTP 429 against an authorized target.

- [ ] **Step 4: Commit the release evidence.**

  ```bash
  git add docs/superpowers/plans/2026-08-31-full-mvp-acceptance-ledger.md docs/operations/release-security-checklist.md docs/operations/deployment.md frontend/lib/core/network/workspace_scoped_service.dart tests/quality/test_mvp_surface_check.py
  git commit -m "chore: retire legacy mvp transport and record evidence"
  ```

## Master verification commands

Run these only after their dependent tasks are complete:

```bash
make lint
make typecheck-py
cd services/company && npx tsc --noEmit
cd services/cosa && npx tsc --noEmit
make frontend-analyze
make mvp-contracts-check mvp-surface-check route-inventory-check
make frontend-boundary-check mvp-e2e-purity-check
make maintainable-mvp-release-check
```
