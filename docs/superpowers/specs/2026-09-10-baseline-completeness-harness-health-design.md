# SP-A — Baseline completeness & harness health

**Status:** Approved design
**Date:** 2026-09-10
**Scope:** Restore the schema objects the Founder Trial R1 `001` baseline squash
dropped but running code still needs, add a regression guard, and prove the
whole system green with `make verify-local`.
**Out of scope:** New features, frontend work, per-workspace rollout mechanics,
known technical debt (TT58 accounting, model routing, Persistent AI Workforce).
Those are sub-projects SP-B / SP-C / SP-D.

## 1. Why

The Founder Trial R1 baseline (`001_founder_trial_mvp_baseline`, a `pg_dump
--schema-only` filtered to a retained allowlist) is internally incomplete. The
COSA Automation MVP effort already found and fixed three gap classes
(`cosa.roles` missing `member`, `core.workspace_policy_versions` dropped,
`GENERATED ALWAYS AS IDENTITY` stripped from four agent sequence columns and two
`integration` tables — commits `a9709b70`). Two gaps remain and block a trial:

- **AI-compliance schema** — 14 `legal.*` tables (deleted migration
  `27_ai_compliance_governance` + follow-ups) are gone. `ai-compliance-access.service.ts`
  reads five of them on the `resolve-data-use` / `runtime/snapshots/resolve`
  path, which gates **every** agent run. `test_cross_plane_smoke.py::test_s2`
  currently fails at `ai-compliance _e2e/seed` with
  `relation "legal.ai_system_catalog" does not exist`.
- **Document-ingestion tables** — `control_plane.document_ingestions` and
  `control_plane.document_ingestion_audit_events` (declared in
  `control-plane-schema.ts`, the audit table with a `GENERATED IDENTITY` id) are
  missing from the cosa baseline; knowledge-ingestion tests need them.

`make verify-local` is red today because `e2e-cross-plane-smoke` (S2) is red.

## 2. Principles

SP-A adds no features. Every restore is a **new, expand-only, idempotent
migration** — `CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`, and
identity re-attach guarded by `attidentity = '' AND NOT atthasdef`. The `001_*`
files are checksum-immutable and are never edited. No row or table is deleted.

DDL source of truth: the Drizzle schema
(`services/company/shared/db/schema/*.ts`, `services/cosa/storage/*.ts`)
cross-checked against the deleted migration content
(`git show <deleted-commit>^:<path>`). Where the two disagree, the Drizzle
schema wins (it is what the running ORM expects).

Migration numbers continue the existing sequence: cosa is at `004` → add `005`;
`company/finance-legal` is at `001` → add `002`. **One consolidated
`restore_baseline_gaps` migration per affected plane** (not one per concern).
The `company/identity/002_*` and `packages/agent/004_*` restores from the
Automation MVP effort are the same family and stay untouched.

## 3. Gaps

### G1 — AI-compliance `legal.*` schema (14 tables)

Flattened final state of the deleted `27_ai_compliance_governance.up.sql` (260
lines) plus its follow-ups: `51d806cc` (ownership FK on
`workspace_ai_deployments`), `48383fc1` (verified-source columns + rule seed),
`3e14fbd1` (snapshot provenance columns), `4dc246a8` (reviewer-claim fix).

Tables: `ai_system_catalog`, `ai_system_versions`, `workspace_ai_deployments`,
`ai_system_capability_bindings`, `ai_risk_assessments`, `ai_compliance_evidence`,
`ai_provider_profiles`, `ai_data_processing_profiles`,
`data_processing_authorizations`, `data_subject_requests`, `ai_incidents`,
`ai_incident_actions`, `ai_compliance_snapshots` (+ provenance columns).

Restore into `services/company/finance-legal/migrations/002_restore_baseline_gaps.up.sql`,
matching `shared/db/schema/legal.ts` (24 exports; the 14 AI-compliance tables
plus already-present legal-catalog tables). The `48383fc1` "verified legal
sources" seed rows are included **only if** an on-request runtime handler
(`resolve-data-use`, snapshot resolve) fails without them; a seed that only
feeds the Legal Center UI is deferred to SP-B. This is decided during
implementation by reading the handler code, not guessed.

### G2 — `control_plane.document_ingestion*` (2 tables)

Flattened from the deleted `15_document_ingestions` migration into
`services/cosa/migrations/005_restore_baseline_gaps.up.sql`. `document_ingestions`
(text id, workspace-scoped) and `document_ingestion_audit_events`
(`id BIGINT GENERATED ALWAYS AS IDENTITY`, FK → `document_ingestions.id`),
matching `control-plane-schema.ts`.

### G3 — IDENTITY-strip regression guard

The known identity columns are now covered (agent `004`, identity `002`, and
G2's audit table). Add `tests/quality/test_baseline_identity_columns.py`: scan
every schema source for `generatedAlwaysAsIdentity()` and every repository for
`RETURNING sequence` / `RETURNING id` on an insert that omits the column, then
assert the corresponding baseline **or restore** migration declares
`GENERATED ... AS IDENTITY` for that column. Fail closed on any new bare column.

### G4 — Regenerate drifted committed artifacts

`docs/architecture/generated/company-usage-inventory.md` is stale (Automation
MVP drift). After G1/G2 land: regenerate it, regenerate the golden schema
fingerprint (`schema-fingerprint.mjs --write` — workspace group gains 14 tables,
cosa gains 2), extend `_EXPECTED_LEDGER` in
`tests/e2e/test_founder_trial_baseline_reset.py` with the two new migrations,
and re-run `mvp-contracts-check`. Commit the regenerated files with the
migration that caused the drift.

### G5 — Full `make verify-local`

Run it end to end. Each new failure is investigated with
`superpowers:systematic-debugging` (root cause before fix), and any further
small gap it surfaces is folded into the relevant `restore_baseline_gaps`
migration — no new migration files. Expected clean afterwards: cross-plane smoke
S1–S7, `e2e-test` golden path, `knowledge-ingestion-test`.

### G6 — Reconcile Founder Trial reset plan (doc-only)

`docs/superpowers/plans/2026-09-09-founder-trial-mvp-reset-baseline.md` still
shows every step `[ ]` although the baseline was cut over (`24a6908b`). Tick the
boxes to match reality, call out anything genuinely unfinished, and add a
"baseline gaps found post-cutover" note pointing at the SP-A restore migrations.
No code change.

## 4. Sequence

```
Step 1  G1 + G2 — write both restore migrations (+ .down.sql), apply to the
        disposable test DBs and the dev DBs, verify \d matches Drizzle.
Step 2  G4 — regenerate golden fingerprint + usage inventory; extend the ledger.
Step 3  G3 — add the IDENTITY regression guard test.
Step 4  G5 — run make verify-local; systematic-debug every new failure.
Step 5  G6 — reconcile the Founder Trial reset plan checkboxes.
Step 6  Re-run make verify-local; confirm green. Re-run make automation-mvp-e2e
        (must stay 6/6).
```

Each step is an independent unit with its own verification and its own commit.

## 5. Verification — definition of done

| Check | Command | Expected |
|---|---|---|
| Expand-only | `make migration-compat-check` | pass |
| Rollback roundtrip | `node scripts/test-migration-rollback.mjs` | pass (two new down.sql) |
| Schema vs golden | `node scripts/schema-fingerprint.mjs --check` | pass after regen |
| Baseline-reset ledger | `pytest tests/e2e/test_founder_trial_baseline_reset.py` | pass |
| IDENTITY guard | `pytest tests/quality/test_baseline_identity_columns.py` | pass (new) |
| **Aggregate gate** | `make verify-local` | **fully green** |
| No Automation regression | `make automation-mvp-e2e` | 6/6 |

No PRODUCTION claim. `make verify` (the CI gate, which adds Encore
`services-test`) is run as a final sanity but is not an SP-A blocking condition
— it belongs to CI.

## 6. Testing

- `test_founder_trial_baseline_reset.py`: extend `_EXPECTED_LEDGER`; after
  `make test-db-reset`, assert `legal.ai_system_catalog` and
  `control_plane.document_ingestions` exist.
- New `tests/quality/test_baseline_identity_columns.py` (G3).
- `test_cross_plane_smoke.py::test_s2_dispatch_worker_result` (existing) must
  pass — proof that `_e2e/seed` + `resolve-data-use` + a real agent run work.
- No per-table tests for `legal.*` — those tables already have Drizzle
  definitions and `finance-legal/tests/` coverage; SP-A only guarantees they
  *exist* so that coverage can run.
