# Runtime and E2E Truthfulness Remediation Plan

> **For agentic workers:** Required skills: `superpowers:test-driven-development`, `superpowers:systematic-debugging`, and `superpowers:verification-before-completion`.

**Goal:** Correct the Workspace Runtime task projection and make the required E2E suite truthful about whether it exercises a running service stack.

**Architecture:** Company remains the owner of Operations task state. Workspace Runtime is a read projection: active, assigned tasks appear in “Needs you”; a task dependency is a blocker only while its prerequisite task remains unresolved. The Python E2E directory contains release evidence only. In-process applications built with fake models, in-memory repositories, test transports, or overrides move to the integration test layer.

**Tech Stack:** TypeScript, Encore, Drizzle, Vitest, Python, pytest, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-08-31-maintainable-modular-truthful-mvp-design.md`

## Guardrails

- Do not modify any applied migration or alter migration history/checksums.
- Preserve the Company/Control/Agent ownership boundary; this plan makes no direct cross-plane database call.
- Start every production behavior change with a focused failing test.
- A skipped or in-process test cannot be used as E2E release evidence.
- Preserve existing test coverage by reclassifying fake/in-process scenarios as integration tests rather than weakening their assertions.

## Delivery order

### 1. Lock the Workspace Runtime contract with failing tests

Files:

- Modify: `services/company/operations/tests/mvp-canvas-runtime.test.ts`

Add one authenticated scenario that proves:

1. an assigned `todo`, `in_progress`, or `waiting_approval` task appears in Needs You;
2. the canonical lower-case priority values map correctly to severity;
3. a dependent task is a blocker while its prerequisite is active;
4. the same dependency disappears when its prerequisite is `done` or `cancelled`.

Run the targeted Vitest file and observe it fail under the current projection.

### 2. Correct the Company projection

Files:

- Modify: `services/company/operations/services/workspace-runtime.service.ts`

Use the canonical task vocabulary. Join the prerequisite task separately from the dependent task, scope both to the workspace, and filter out resolved/deleted prerequisites. Retain the existing response contract and source references. Run the focused test, then the Company TypeScript typecheck and test suite.

### 3. Separate E2E release evidence from in-process integration

Files:

- Move: `tests/e2e/test_mvp_vault_http.py` → `tests/integration/test_mvp_vault_in_process.py`
- Move: `tests/e2e/test_mvp_workforce_http.py` → `tests/integration/test_mvp_workforce_in_process.py`
- Remove: `tests/e2e/test_golden_path.py`

Mark the moved tests as integration and rename their test descriptions to avoid an E2E claim. The removed Golden Path file is already broken because its fake fixture graph was deliberately deleted; Git history retains it. Its scenarios are not restored as false E2E evidence.

### 4. Harden the E2E purity gate and make stack selection explicit

Files:

- Modify: `scripts/check_mvp_e2e_purity.py`
- Modify: `tests/quality/test_mvp_e2e_purity.py`
- Modify: `tests/e2e/conftest.py`
- Modify: `scripts/e2e/run-golden-path.sh`

The AST guard rejects in-process transports, `Fake*`, `InMemory*`, test identity overrides, runtime `pytest.skip`, and fake/stub clients in `test_mvp_*.py`. It also checks required MVP files exist. Add focused scanner tests for every new class of violation.

When an explicit `E2E_BASE_URL_COMPANY` is supplied, the E2E fixture must use that already-running service after a health probe; otherwise it may boot Company locally. Missing required infrastructure fails the E2E fixture rather than skipping it. The Docker runner exports the Company base URL from the Compose stack.

### 5. Verify and document the remaining migration release blocker

Run:

```bash
cd services/company && npx tsc --noEmit && npx vitest run
PYTHONPATH=. python -m pytest tests/quality/test_mvp_e2e_purity.py -q
make mvp-e2e-purity-check
make e2e-test
make migration-compat-check
```

Report the exact migration compatibility violations separately. Do not replace them with a code exemption: an operator must decide the recovery/rollback runbook and confirm data backup/PITR before a safe forward-only migration or explicitly approved cutover can be designed.
