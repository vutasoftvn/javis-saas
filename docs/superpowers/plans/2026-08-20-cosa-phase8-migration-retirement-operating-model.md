# COSA Phase 8 Migration, Retirement and Operating Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans task-by-task.

**Goal:** Retire duplicate/scaffold paths only after users, data, providers and tests have migrated to the governed Harness operating model.

**Architecture:** Migration proceeds by one Offering and one low-risk workflow at a time. Canonical paths from Phase 0–7 are authoritative. Compatibility facades may dual-read projections during data migration but never dual-execute an external side effect. Retirement requires evidence: import scan, runtime usage/metrics window, data migration verification and regression suite.

**Tech Stack:** Python scripts/pytest, Alembic, SQLAlchemy, OpenTelemetry/metrics, FastAPI deprecation headers, Flutter, markdown ADR/cookbook.

**Spec:** Master rebuild plan Phase 8 and Phase 0 ownership map; Phase 1–7 completion documents.

## Global Constraints

- Never delete a module/table because its name looks duplicate; require direct consumer evidence.
- Never dual-execute external tool/provider/workflow actions.
- Backfill is idempotent, scoped, checkpointed, observable and reversible where data semantics permit.
- Every deprecated API/module has canonical replacement, owner, announced date and removal date.
- Production credentials, private reasoning and historical audit/event records are preserved or redacted according to retention policy.
- A module with persistence metadata imports is not retired until Alembic/SQLAlchemy parity and consumer migration tests pass.

## Tasks

### Task 1: Freeze retirement candidates and create evidence ledger

- [ ] Update ownership map with candidate, canonical replacement, verified consumers, metrics key, owner, earliest removal release/date.
- [ ] Create `scripts/report_retirement_readiness.py` and tests scanning imports, route mounts, migrations and frontend references.
- [ ] Run report in CI; commit `docs: track harness retirement readiness`.

### Task 2: Select and migrate one low-risk pilot slice

- [ ] Select one Offering and one read-only workflow through an ADR; define success/rollback criteria.
- [ ] RED integration tests for old-to-new projection read compatibility and exactly-once workflow/tool effect.
- [ ] Implement idempotent scoped migration command with dry-run, checkpoint, counts and audit event.
- [ ] Run pilot and commit `feat: migrate governed harness pilot slice`.

### Task 3: Add compatibility facades and deprecation contracts

- [ ] For each verified legacy consumer, create a narrow facade forwarding to canonical service without copying behavior.
- [ ] Add HTTP `Deprecation`, `Sunset`, replacement-link headers and structured warning events to deprecated APIs.
- [ ] RED tests assert facade has no direct provider/tool body call and emits deprecation telemetry.
- [ ] GREEN tests; commit `refactor: deprecate legacy harness entrypoints`.

### Task 4: Migrate consumers family by family

- [ ] Sequence: tool callers, skills/profiles, workflow callers, executors/adapters, UI services, then persistence metadata imports.
- [ ] For each family, add consumer migration test, move one caller, run focused suite and commit independently.
- [ ] Record remaining consumer count in retirement ledger; do not start next deletion candidate until count is zero.

### Task 5: Validate data and projection parity

- [ ] Create parity verifier comparing canonical/legacy read projections by workspace/offering, including counts, identifiers, scope snapshots and immutable artifact hashes.
- [ ] RED tests for mismatch report and dry-run exit code.
- [ ] Run verifier in CI and release checklist; commit `test: verify migration projection parity`.

### Task 6: Retire dead code and schemas safely

- [ ] Require report: zero production imports/routes, zero metrics usage through deprecation window, parity pass and full suite pass.
- [ ] Delete one candidate family per commit, including stale tests/docs/config only for that family.
- [ ] For tables, first remove writers/readers, retain read-only export during retention window, then create reviewed Alembic drop migration.
- [ ] Run full verification after each deletion; commit `refactor: retire <candidate>`.

### Task 7: Publish contributor cookbook and seam ADRs

- [ ] Create recipes: add native tool, skill, workflow node/UI renderer, MCP connector, executor, DSH capability, profile and event projection.
- [ ] Every recipe specifies module boundary, manifest, scope/policy/approval, tests, versioning, health/disable and observability.
- [ ] Add ADR for each seam/node family; commit `docs: publish harness contributor cookbook`.

### Task 8: Final operating-model acceptance

- [ ] End-to-end test: multi-offering company composes an approved first-party extension tool into a visual workflow, executes with approval, and sees event/artifact lifecycle in Hologram.
- [ ] Verify one documented/test-enforced canonical path remains for each runtime, registry, policy, workflow and executor capability.
- [ ] Run backend full suite, Flutter tests/analyze, import/retirement report and migration parity report.
- [ ] Write `docs/architecture/COSA_PHASE8_RETIREMENT_COMPLETION.md`; tag accepted release; commit `docs: complete harness migration and retirement`.

## Acceptance checklist

- [ ] No production consumer remains on retired registry/scaffold paths.
- [ ] Every deletion has evidence, rollback/export plan and green regression suite.
- [ ] First-party extension can add tool, skill, workflow node and UI renderer without Harness Core edit.
- [ ] Multi-offering workflow stays scope/governance constrained end-to-end.
