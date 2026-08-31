# Frontend Legacy Boundary and Coverage Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Freeze the exact legacy `WorkspaceScopedService` callers and enforce a 46.0% Flutter line-coverage floor locally and in CI.

**Architecture:** Extend the existing Node frontend-boundary scanner with a repository-relative compatibility allowlist, while retaining the absolute feature-layer prohibition.  Add a dependency-free LCOV parser/checker with Node unit tests, then wire the same command into Make and GitHub Actions so local and CI enforcement use identical data and threshold.

**Tech Stack:** Node.js standard library, Node built-in test runner, Python pytest, Flutter test/LCOV, GNU Make, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-01-frontend-legacy-boundary-and-coverage-design.md`

## Global Constraints

- The only permitted direct imports of `workspace_scoped_service.dart` are the ten explicit files in the approved design.
- Any `features/*` import of the legacy service fails, regardless of allowlist edits.
- Preserve all application Dart behaviour: do not modify the compatibility class, its ten callers, endpoints, UI, tokens, backend, database, or deployment runtime.
- The coverage evaluator uses only Node built-ins and rejects malformed, missing, or zero-line LCOV reports.
- Initial global line-coverage floor is exactly **46.0%**, computed from LCOV `LH / LF` totals.
- Do not commit in this tranche: the current `main` checkout contains related P0/P1 modifications and the user has not authorized history changes.  Use `git diff --check` as the local review gate.

---

### Task 1: Freeze legacy WorkspaceScopedService imports

**Files:**

- Modify: `scripts/check_frontend_boundaries.mjs:12-121`
- Modify: `tests/quality/test_frontend_boundaries.py`

**Interfaces:**

- Consumes: `runCheck(targetDir: string): string[]`, exported by `scripts/check_frontend_boundaries.mjs`.
- Produces: scanner findings with either `NO_LEGACY_WORKSPACE_SCOPED_SERVICE` for feature code or `LEGACY_WORKSPACE_SCOPED_ALLOWLIST` for any non-feature caller outside the frozen inventory.

- [x] **Step 1: Add a failing scanner test for a non-allowlisted module import.**

  In `tests/quality/test_frontend_boundaries.py`, create a temporary `frontend/lib` tree containing both a known allowlisted path and a synthetic new module:

  ```python
  valid = lib_dir / "modules" / "tasks" / "services" / "task_service.dart"
  valid.parent.mkdir(parents=True)
  valid.write_text(
      "import 'package:frontend/core/network/workspace_scoped_service.dart';\n"
  )

  blocked = lib_dir / "modules" / "new_domain" / "services" / "new_service.dart"
  blocked.parent.mkdir(parents=True)
  blocked.write_text(
      "import 'package:frontend/core/network/workspace_scoped_service.dart';\n"
  )
  ```

  Execute the scanner subprocess and assert a non-zero exit plus
  `LEGACY_WORKSPACE_SCOPED_ALLOWLIST` in stderr.  Add a separate fixture file
  under `features/new_domain/` and assert it emits
  `NO_LEGACY_WORKSPACE_SCOPED_SERVICE`.

- [x] **Step 2: Run the focused test to prove it is red.**

  Run:

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/quality/test_frontend_boundaries.py -q
  ```

  Expected: FAIL because the existing scanner allows the synthetic
  `modules/new_domain` import.

- [x] **Step 3: Implement the exact caller freeze.**

  Add this repository-relative set near the scanner constants:

  ```js
  const legacyWorkspaceScopedImportAllowlist = new Set([
    'core/services/function_status_service.dart',
    'modules/approvals/services/approvals_service.dart',
    'modules/finance/services/finance_service.dart',
    'modules/legal/services/ai_compliance_service.dart',
    'modules/legal/services/legal_service.dart',
    'modules/sales/services/sales_service.dart',
    'modules/strategy/services/next_best_action_service.dart',
    'modules/strategy/services/outcomes_service.dart',
    'modules/tasks/services/task_service.dart',
    'modules/workflows/services/workflows_service.dart',
  ]);
  ```

  While examining every Dart import, identify
  `workspace_scoped_service.dart`.  For an import from `features/*`, record
  only `NO_LEGACY_WORKSPACE_SCOPED_SERVICE`; otherwise, record
  `LEGACY_WORKSPACE_SCOPED_ALLOWLIST` when `relFromLib` is absent from the set.
  Perform the check before resolving a package or relative import so both forms
  are covered.  Leave all non-legacy feature/private-import checks unchanged.

- [x] **Step 4: Run focused and repository boundary verification.**

  Run:

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/quality/test_frontend_boundaries.py -q
  make frontend-boundary-check
  ```

  Expected: pytest passes; the repository scan passes because it contains only
  the ten frozen direct imports.

- [x] **Step 5: Review this task without committing.**

  Run `git diff --check` and inspect only the two task files.  Do not stage or
  commit because the shared checkout contains pre-existing in-scope changes.

### Task 2: Add a testable LCOV coverage evaluator

**Files:**

- Create: `scripts/check_frontend_coverage.mjs`
- Create: `scripts/tests/check_frontend_coverage.test.mjs`

**Interfaces:**

- Produces: `parseLcov(lcov: string): { covered: number, found: number, percent: number }` and `evaluateCoverage(lcov: string, minimum: number): { covered: number, found: number, percent: number }`.
- CLI: `node scripts/check_frontend_coverage.mjs <lcov-path> --minimum=46` prints the measured totals and exits 0 only when `percent >= minimum`.

- [x] **Step 1: Write failing Node tests for the desired API.**

  Create `scripts/tests/check_frontend_coverage.test.mjs` using `node:test`
  and `node:assert/strict`.  Import the nonexistent evaluator and test the
  actual LCOV record format:

  ```js
  const passing = [
    'SF:lib/a.dart', 'LF:10', 'LH:5', 'end_of_record',
    'SF:lib/b.dart', 'LF:15', 'LH:9', 'end_of_record',
  ].join('\n');

  assert.deepEqual(parseLcov(passing), {
    covered: 14,
    found: 25,
    percent: 56,
  });
  assert.throws(() => evaluateCoverage(passing, 57), /below required 57%/);
  ```

  Add independent tests that reject a record lacking `LH`, a report without an
  `SF` source record, and `LH` greater than `LF`.  These inputs are real parser
  error cases; do not mock filesystem or child processes.

- [x] **Step 2: Run the Node test to prove it is red.**

  Run:

  ```bash
  node --test scripts/tests/check_frontend_coverage.test.mjs
  ```

  Expected: FAIL with `ERR_MODULE_NOT_FOUND` for
  `scripts/check_frontend_coverage.mjs`.

- [x] **Step 3: Implement only the parser and evaluator needed by the tests.**

  In `scripts/check_frontend_coverage.mjs`, parse `SF:`, `LF:`, `LH:`, and
  `end_of_record` line by line.  Require exactly one non-negative integer
  `LF` and `LH` for every source record, require `LH <= LF`, and require a
  positive total `LF`.  `evaluateCoverage` throws an `Error` containing
  `below required <minimum>%` when the computed percentage is less than the
  caller-supplied number.  The CLI reads its first positional file argument,
  accepts only `--minimum=<non-negative-number>`, prints
  `Frontend line coverage: <percent>% (<covered>/<found>)`, and assigns a
  non-zero exit code for invalid input or a below-floor result.

- [x] **Step 4: Run Node tests and the real baseline report.**

  Run:

  ```bash
  node --test scripts/tests/check_frontend_coverage.test.mjs
  node scripts/check_frontend_coverage.mjs frontend/coverage/lcov.info --minimum=46
  ```

  Expected: all evaluator tests pass; a fresh full report prints 46.45% and
  exits zero against the 46.0% floor.

- [x] **Step 5: Review this task without committing.**

  Run `git diff --check`.  Confirm the script imports only `node:fs`,
  `node:path`, and `node:url` as necessary; do not add an npm dependency or
  stage files.

### Task 3: Enforce the same coverage gate locally and in GitHub Actions

**Files:**

- Modify: `Makefile:7,70-74`
- Modify: `.github/workflows/quality.yml:17-28`
- Create: `tests/quality/test_frontend_coverage_gate.py`

**Interfaces:**

- Consumes: the Task 2 CLI and `frontend/coverage/lcov.info` generated by
  `flutter test --coverage`.
- Produces: `make frontend-coverage-check`, and the GitHub `frontend` job runs
  the exact `--minimum=46` evaluator before moving LCOV to its artifact path.

- [x] **Step 1: Write a failing local-gate behavior test.**

  Create `tests/quality/test_frontend_coverage_gate.py` that executes Make,
  rather than reading configuration source text.  Its only assertion is the
  actual dry-run recipe that a developer receives:

  ```python
  result = subprocess.run(
      ["make", "--dry-run", "frontend-coverage-check"],
      cwd=repo_root,
      capture_output=True,
      text=True,
  )

  assert result.returncode == 0, result.stderr
  assert "cd frontend && flutter test --coverage" in result.stdout
  assert (
      "node scripts/check_frontend_coverage.mjs "
      "frontend/coverage/lcov.info --minimum=46"
  ) in result.stdout
  ```

  This proves the consumer-visible Make invocation instead of asserting a
  particular source-file layout.  CI uses the same tested evaluator command;
  its insertion order is reviewed in the focused workflow diff and exercised
  by the GitHub `frontend` job on the next run.

- [x] **Step 2: Run the configuration test to prove it is red.**

  Run:

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/quality/test_frontend_coverage_gate.py -q
  ```

  Expected: FAIL because `frontend-coverage-check` is not a Make target.

- [x] **Step 3: Wire Make and CI to the evaluator.**

  Add `frontend-coverage-check` to `.PHONY` and define:

  ```make
  frontend-coverage-check:
	cd frontend && flutter test --coverage
	node scripts/check_frontend_coverage.mjs frontend/coverage/lcov.info --minimum=46
  ```

  In `.github/workflows/quality.yml`, insert exactly this step between the
  Flutter coverage step and the LCOV move:

  ```yaml
      - run: node scripts/check_frontend_coverage.mjs frontend/coverage/lcov.info --minimum=46
  ```

  Keep artifact names and upload configuration unchanged.

- [x] **Step 4: Run the wiring and full frontend verification.**

  Run:

  ```bash
  PYTHONPATH=$(pwd) .venv/bin/python -m pytest tests/quality/test_frontend_coverage_gate.py -q
  make frontend-coverage-check
  make frontend-test
  make frontend-analyze
  ```

  Expected: the local-gate behavior test passes, the evaluated coverage is at least
  46.0%, and existing Flutter test/analyzer suites report no failures.

- [x] **Step 5: Final local evidence review without committing.**

  Run:

  ```bash
  make frontend-boundary-check
  node --test scripts/tests/check_frontend_coverage.test.mjs
  git diff --check
  git status --short
  ```

  Record each command’s actual exit status and output summary in the final
  handoff.  Do not claim completion without fresh output from every command.

## Plan self-review

### Spec coverage

- Exact ten-caller freeze and absolute feature prohibition: Task 1.
- Dependency-free, malformed-report-safe LCOV evaluation at 46.0%: Task 2.
- Same Make/CI enforcement with evaluator before artifact move: Task 3.  The
  Make recipe is behavior-tested; the GitHub workflow is reviewed as deployment
  configuration and executes the identical, independently tested CLI.
- No application behaviour or large-service refactor: Global Constraints and
  task file limits.
- TDD red/green evidence and final verification: every task’s ordered steps.

### Placeholder scan

The plan has no `TODO`, `TBD`, “implement later”, or unspecified test step.
Every production change has an exact file, required interface, test shape, and
verification command.

### Type and command consistency

Task 2 defines the two evaluator exports used by its tests and defines the CLI
invoked by Task 3.  The only permitted command is consistently
`node scripts/check_frontend_coverage.mjs frontend/coverage/lcov.info --minimum=46`.
