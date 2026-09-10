# SP-A — Baseline completeness & harness health Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the schema objects the Founder Trial R1 `001` baseline squash dropped but running code still needs, add a regression guard, and prove the whole system green with `make verify-local`.

**Architecture:** Every restore is a **new, expand-only, idempotent** migration (`CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`, identity re-attach guarded by `attidentity='' AND NOT atthasdef`). The `001_*` baseline files are checksum-immutable and are never edited. DDL is reconstructed from the deleted migration content at git ref `81461673^` and verified against the current Drizzle schema by existing schema-shape tests. One consolidated `restore_baseline_gaps` migration per affected plane.

**Tech Stack:** PostgreSQL, Encore/TypeScript + Drizzle, Python/asyncpg, Node migration runners (`services/*/scripts/migrate.mjs`, `packages/agent/scripts/migrate.py`), pytest, vitest.

## Global Constraints

- Work directly on `main`; never create a git worktree.
- Recheck `git status --short` before each task; stage only the files that task lists.
- Migrations are **expand-only** (`make migration-compat-check` must pass): no `DROP TABLE`, `DROP COLUMN`, `RENAME`, `TRUNCATE`, `ALTER COLUMN ... SET NOT NULL` on an existing column. Destructive statements from the source migrations (`INSERT`/`UPDATE`/`DELETE`, `NOT VALID` + `VALIDATE CONSTRAINT`, backfill blocks) are **stripped** — a fresh baseline DB has no rows to migrate.
- Never edit any `001_founder_trial_mvp_baseline*` file (checksum-immutable — the runner FAILs HARD on a changed sha256).
- Migration numbers continue the sequence: cosa is at `004` → add `005`; `company/finance-legal` is at `001` → add `002`. Every restore migration ships a paired `.down.sql`.
- No legal / regulation **content seed** (regulation text, applicability rule predicates) — structure only. Confirmed scope decision.
- Do not restore `agent_artifact.workspace_artifacts` or any schema in `tests/quality/test_founder_trial_baseline_inventory.py::FORBIDDEN_SCHEMAS`.
- All identifiers at HTTP/DB boundaries stay strings; Snowflake bigint PKs are app-supplied (`generateSnowflake()`), so `id bigint` with **no** identity/default is correct for those tables — only re-attach identity where a `.generatedAlwaysAsIdentity()` Drizzle declaration or a `RETURNING sequence*`/`RETURNING id` insert (omitting the column) exists.
- Local Postgres must be reachable as `PGUSER=postgres` with `PGPASSWORD=$POSTGRES_PASSWORD` from `.env`. Test DBs `javis_{agent,cosa,workspace}_test` are provisioned by `bash scripts/provision-founder-trial-test-dbs.sh`.

---

## File map

| File | Responsibility |
|---|---|
| `services/company/finance-legal/migrations/002_restore_baseline_gaps.up.sql` (create) | Restore all `legal.*` table structures (regulation catalog + AI-compliance), flattened from deleted migrations 12/13/27/29/30/31. Structure only. |
| `services/company/finance-legal/migrations/002_restore_baseline_gaps.down.sql` (create) | `DROP TABLE IF EXISTS legal.<t> CASCADE` for every table this migration adds, child-first. |
| `services/cosa/migrations/005_restore_baseline_gaps.up.sql` (create) | Restore `control_plane.document_ingestions` + `control_plane.document_ingestion_audit_events`, flattened from deleted `15_document_ingestions`. |
| `services/cosa/migrations/005_restore_baseline_gaps.down.sql` (create) | `DROP TABLE IF EXISTS` both, child-first. |
| `tests/quality/test_baseline_identity_columns.py` (create) | Regression guard: every `generatedAlwaysAsIdentity()` / `RETURNING sequence*` column must have `GENERATED ... AS IDENTITY` in a baseline or restore migration. |
| `tests/e2e/test_founder_trial_baseline_reset.py` (modify) | Extend `_EXPECTED_LEDGER`; assert restored tables exist after `make test-db-reset`. |
| `deploy/schema/fingerprints.json` (modify, generated) | Regenerated golden — workspace group gains the `legal.*` tables, cosa gains the two `document_ingestion*` tables. |
| `docs/architecture/generated/company-usage-inventory.md` (modify, generated) | Regenerated — drift left by the Automation MVP effort. |
| `docs/superpowers/plans/2026-09-09-founder-trial-mvp-reset-baseline.md` (modify) | Doc-only: tick T1–T11 to match reality, note post-cutover baseline gaps. |

---

## Task 1: Restore the `legal` schema structure

**Files:**
- Create: `services/company/finance-legal/migrations/002_restore_baseline_gaps.up.sql`
- Create: `services/company/finance-legal/migrations/002_restore_baseline_gaps.down.sql`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: schema `legal` populated with ~23 tables matching `services/company/shared/db/schema/legal.ts`. Consumed by every later task (verify sweeps) and by `ai-compliance-access.service.ts`, `ai-compliance-snapshot.service.ts`, `ai-legal-applicability.service.ts` at runtime.

- [ ] **Step 1: Write the failing schema test**

The repo already ships schema-shape tests for `legal.*`. Prove they are red against a fresh baseline DB.

```bash
bash scripts/provision-founder-trial-test-dbs.sh
export WORKSPACE_TEST_MIGRATOR_DATABASE_URL='postgresql://workspace_migrator:change-me-workspace-migrator@127.0.0.1:5432/javis_workspace_test?sslmode=disable'
export AGENT_TEST_MIGRATOR_DATABASE_URL='postgresql+asyncpg://agent_migrator:change-me-agent-migrator@127.0.0.1:5432/javis_agent_test'
export COSA_TEST_MIGRATOR_DATABASE_URL='postgresql://cosa_migrator:change-me-cosa-migrator@127.0.0.1:5432/javis_cosa_test?sslmode=disable'
APP_ENV=test TEST_DATABASE_RESET=CONFIRM_FOUNDER_TRIAL_MVP_RESET node scripts/test-db-reset.mjs
export WORKSPACE_DATABASE_URL='postgresql://workspace_app:change-me-workspace-app@127.0.0.1:5432/javis_workspace_test?sslmode=disable'
cd services/company && npx vitest run finance-legal/tests/ai-compliance-schema.test.ts finance-legal/tests/ai-compliance-runtime-schema.test.ts finance-legal/tests/legal-applicability-integrity.test.ts
```

Expected: FAIL — `relation "legal.ai_system_catalog" does not exist` (and the other `legal.*` relations).

- [ ] **Step 2: Reconstruct the DDL**

Dump the six source migrations and build the restore file. Keep only `CREATE TABLE`, `CREATE INDEX`, `CREATE UNIQUE INDEX`, and `ALTER TABLE ... ADD COLUMN` / `ADD CONSTRAINT` statements. **Strip** every `INSERT`, `UPDATE`, `DELETE`, comment-only line noise, and every `NOT VALID` / `VALIDATE CONSTRAINT` pair (add those constraints as plain constraints — the DB is empty).

```bash
cd /Volumes/SSD/javis-saas
{
  echo "-- SP-A: restore the legal schema structure the 001 baseline squash dropped."
  echo "-- Flattened DDL from deleted migrations 12/13/27/29/30/31 (git ref 81461673^)."
  echo "-- Structure only — no regulation / rule content seed. Expand-only, idempotent."
  echo "CREATE SCHEMA IF NOT EXISTS legal;"
  echo
  for m in 12_legal_catalog 13_legal_applicability_obligations 27_ai_compliance_governance \
           29_ai_compliance_runtime_hardening 30_ai_legal_source_corrections 31_ai_legal_review_pending_correction; do
    echo "-- ===== from $m.up.sql ====="
    git show "81461673^:services/company/finance-legal/migrations/$m.up.sql"
    echo
  done
} > /tmp/legal_raw.sql
wc -l /tmp/legal_raw.sql
```

Now open `/tmp/legal_raw.sql` and produce `002_restore_baseline_gaps.up.sql` by hand-editing it down to DDL only:
1. Delete every `INSERT INTO legal.*` block (and its trailing `VALUES (...)` lines) — these are content seed.
2. Delete every `UPDATE legal.*` and `DELETE FROM legal.*` statement.
3. For each `ALTER TABLE ... ADD CONSTRAINT ... NOT VALID;` immediately followed by `ALTER TABLE ... VALIDATE CONSTRAINT ...;`, replace the pair with the single `ADD CONSTRAINT` line **without** `NOT VALID`.
4. Change every `ADD CONSTRAINT` to `ADD CONSTRAINT IF NOT EXISTS` is NOT valid Postgres — instead wrap each `ALTER TABLE ... ADD CONSTRAINT` in `DO $$ BEGIN ... EXCEPTION WHEN duplicate_object THEN NULL; END $$;` (matches the idiom in `services/company/operations/migrations/001_founder_trial_mvp_baseline.up.sql`).
5. Every `CREATE TABLE` must be `CREATE TABLE IF NOT EXISTS` (the sources already are — verify).
6. Ensure ordering: `regulation_sources` → `regulation_versions` → `legal_entity_profiles` / `legal_obligation_templates` → `applicability_rules` → `legal_obligation_instances` → `ai_system_catalog` → `ai_system_versions` → `workspace_ai_deployments` → `ai_system_capability_bindings` → `ai_risk_assessments` → (deferred FK `workspace_ai_deployments.current_assessment_id`) → `ai_compliance_evidence` → `ai_provider_profiles` → `ai_data_processing_profiles` → `data_processing_authorizations` → `data_subject_requests` → `ai_incidents` → `ai_incident_actions` → `ai_compliance_snapshots` → `ai_applicability_rules` → the migration-29 composite UNIQUE/FK ALTERs → the migration-29/30/31 `ADD COLUMN` statements.

Reference (migration 27 body is stable — reproduce it verbatim, it is 13 `CREATE TABLE` + indexes + one deferred FK):

```
-- The 27_ai_compliance_governance.up.sql content is 260 lines of pure DDL.
-- Copy it verbatim into the restore file (it is already CREATE TABLE IF NOT EXISTS).
```

Migration 29 adds, after the base tables (strip the backfill `UPDATE`s and the `NOT VALID`):

```sql
-- composite (workspace_id, id) UNIQUE on workspace-scoped parents
DO $$ BEGIN ALTER TABLE legal.workspace_ai_deployments ADD CONSTRAINT workspace_ai_deployments_workspace_id_id_key UNIQUE (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_risk_assessments      ADD CONSTRAINT ai_risk_assessments_workspace_id_id_key      UNIQUE (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_provider_profiles     ADD CONSTRAINT ai_provider_profiles_workspace_id_id_key     UNIQUE (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_incidents             ADD CONSTRAINT ai_incidents_workspace_id_id_key             UNIQUE (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_data_processing_profiles ADD CONSTRAINT ai_data_processing_profiles_workspace_id_id_key UNIQUE (workspace_id, id); EXCEPTION WHEN duplicate_object THEN NULL; END $$;
-- composite FKs (child.workspace_id, child.ref) -> parent(workspace_id, id)
DO $$ BEGIN ALTER TABLE legal.ai_risk_assessments        ADD CONSTRAINT ai_risk_assessments_workspace_deployment_fk        FOREIGN KEY (workspace_id, deployment_id) REFERENCES legal.workspace_ai_deployments(workspace_id, id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.workspace_ai_deployments   ADD CONSTRAINT workspace_ai_deployments_workspace_assessment_fk   FOREIGN KEY (workspace_id, current_assessment_id) REFERENCES legal.ai_risk_assessments(workspace_id, id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_compliance_evidence     ADD CONSTRAINT ai_compliance_evidence_workspace_assessment_fk     FOREIGN KEY (workspace_id, assessment_id) REFERENCES legal.ai_risk_assessments(workspace_id, id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_data_processing_profiles ADD CONSTRAINT ai_data_profiles_workspace_deployment_fk           FOREIGN KEY (workspace_id, deployment_id) REFERENCES legal.workspace_ai_deployments(workspace_id, id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_data_processing_profiles ADD CONSTRAINT ai_data_profiles_workspace_provider_fk             FOREIGN KEY (workspace_id, recipient_provider_profile_id) REFERENCES legal.ai_provider_profiles(workspace_id, id) ON DELETE RESTRICT; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_incidents               ADD CONSTRAINT ai_incidents_workspace_deployment_fk               FOREIGN KEY (workspace_id, deployment_id) REFERENCES legal.workspace_ai_deployments(workspace_id, id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_incident_actions        ADD CONSTRAINT ai_incident_actions_workspace_incident_fk          FOREIGN KEY (workspace_id, incident_id) REFERENCES legal.ai_incidents(workspace_id, id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_compliance_snapshots    ADD CONSTRAINT ai_compliance_snapshots_workspace_deployment_fk    FOREIGN KEY (workspace_id, deployment_id) REFERENCES legal.workspace_ai_deployments(workspace_id, id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_compliance_snapshots    ADD CONSTRAINT ai_compliance_snapshots_workspace_assessment_fk    FOREIGN KEY (workspace_id, assessment_id) REFERENCES legal.ai_risk_assessments(workspace_id, id) ON DELETE CASCADE; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
-- migration 29 §3 + 3e14fbd1: snapshot provenance columns
ALTER TABLE legal.ai_compliance_snapshots
  ADD COLUMN IF NOT EXISTS capability_binding_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS evidence_ids           JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS evidence_hashes        JSONB NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS provider_profile_id    BIGINT,
  ADD COLUMN IF NOT EXISTS data_profile_id        BIGINT,
  ADD COLUMN IF NOT EXISTS provenance_complete    BOOLEAN NOT NULL DEFAULT false;
DO $$ BEGIN ALTER TABLE legal.ai_compliance_snapshots ADD CONSTRAINT ai_compliance_snapshots_workspace_provider_fk     FOREIGN KEY (workspace_id, provider_profile_id) REFERENCES legal.ai_provider_profiles(workspace_id, id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN ALTER TABLE legal.ai_compliance_snapshots ADD CONSTRAINT ai_compliance_snapshots_workspace_data_profile_fk FOREIGN KEY (workspace_id, data_profile_id) REFERENCES legal.ai_data_processing_profiles(workspace_id, id) ON DELETE SET NULL; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
```

Migration 30 adds (strip the ~200-line seed and the `ai_applicability_rules` seed):

```sql
ALTER TABLE legal.regulation_versions
  ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'ACTIVE',
  ADD COLUMN IF NOT EXISTS content_hash text,
  ADD COLUMN IF NOT EXISTS correction_reason text,
  ADD COLUMN IF NOT EXISTS artifact_path text,
  ADD COLUMN IF NOT EXISTS reviewer_member_id bigint,
  ADD COLUMN IF NOT EXISTS reviewed_at timestamp with time zone;
ALTER TABLE legal.ai_compliance_evidence
  ADD COLUMN IF NOT EXISTS conclusion text NOT NULL DEFAULT 'COMPLIANT',
  ADD COLUMN IF NOT EXISTS source_version_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS rule_ids jsonb NOT NULL DEFAULT '[]'::jsonb;
CREATE TABLE IF NOT EXISTS legal.ai_applicability_rules (
  id bigint PRIMARY KEY,
  rule_id text NOT NULL UNIQUE,
  rule_version text NOT NULL DEFAULT '1.0.0',
  regulation_source_id bigint NOT NULL REFERENCES legal.regulation_sources(id) ON DELETE CASCADE,
  regulation_version_id bigint NOT NULL REFERENCES legal.regulation_versions(id) ON DELETE CASCADE,
  source_content_hash text NOT NULL,
  effective_from date NOT NULL,
  effective_to date,
  review_status text NOT NULL DEFAULT 'REVIEWED',
  layer text NOT NULL,
  effect text NOT NULL,
  reason_code text NOT NULL,
  description text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
```

Migration 31 adds:

```sql
ALTER TABLE legal.regulation_versions
  ADD COLUMN IF NOT EXISTS legal_review_confirmed boolean NOT NULL DEFAULT false;
```

If `git show 81461673^:.../30_*.up.sql` reveals more columns on `ai_applicability_rules` than shown above, or extra columns on any table, include them — the source file is authoritative, this plan reproduces the load-bearing parts.

- [ ] **Step 3: Write the `.down.sql`**

```sql
-- Rollback 002_restore_baseline_gaps.up.sql — child tables first.
DROP TABLE IF EXISTS legal.ai_applicability_rules CASCADE;
DROP TABLE IF EXISTS legal.ai_compliance_snapshots CASCADE;
DROP TABLE IF EXISTS legal.ai_incident_actions CASCADE;
DROP TABLE IF EXISTS legal.ai_incidents CASCADE;
DROP TABLE IF EXISTS legal.data_subject_requests CASCADE;
DROP TABLE IF EXISTS legal.data_processing_authorizations CASCADE;
DROP TABLE IF EXISTS legal.ai_data_processing_profiles CASCADE;
DROP TABLE IF EXISTS legal.ai_provider_profiles CASCADE;
DROP TABLE IF EXISTS legal.ai_compliance_evidence CASCADE;
DROP TABLE IF EXISTS legal.ai_risk_assessments CASCADE;
DROP TABLE IF EXISTS legal.ai_system_capability_bindings CASCADE;
DROP TABLE IF EXISTS legal.workspace_ai_deployments CASCADE;
DROP TABLE IF EXISTS legal.ai_system_versions CASCADE;
DROP TABLE IF EXISTS legal.ai_system_catalog CASCADE;
DROP TABLE IF EXISTS legal.legal_obligation_instances CASCADE;
DROP TABLE IF EXISTS legal.applicability_rules CASCADE;
DROP TABLE IF EXISTS legal.legal_obligation_templates CASCADE;
DROP TABLE IF EXISTS legal.legal_entity_profiles CASCADE;
DROP TABLE IF EXISTS legal.regulation_versions CASCADE;
DROP TABLE IF EXISTS legal.regulation_sources CASCADE;
```

- [ ] **Step 4: Apply and run the schema tests**

```bash
cd /Volumes/SSD/javis-saas
export WORKSPACE_MIGRATOR_DATABASE_URL='postgresql://workspace_migrator:change-me-workspace-migrator@127.0.0.1:5432/javis_workspace_test?sslmode=disable'
node services/company/scripts/migrate.mjs
export WORKSPACE_DATABASE_URL='postgresql://workspace_app:change-me-workspace-app@127.0.0.1:5432/javis_workspace_test?sslmode=disable'
cd services/company && npx vitest run finance-legal/tests/ai-compliance-schema.test.ts finance-legal/tests/ai-compliance-runtime-schema.test.ts finance-legal/tests/legal-applicability-integrity.test.ts finance-legal/tests/legal-applicability.test.ts
```

Expected: PASS. If a test reports a missing column/table, add it to the migration from the source file at `81461673^` and re-run. Also apply to the dev DB: `WORKSPACE_MIGRATOR_DATABASE_URL='postgresql://workspace_migrator:change-me-workspace-migrator@127.0.0.1:5432/workspace?sslmode=disable' node services/company/scripts/migrate.mjs`.

- [ ] **Step 5: Expand-only + typecheck**

```bash
cd /Volumes/SSD/javis-saas
node scripts/check-migration-backward-compat.mjs
cd services/company && npx tsc --noEmit
```

Expected: both pass (the migration has no `DROP`/`RENAME`/`SET NOT NULL`-on-existing; typecheck is unaffected but confirms nothing else broke).

- [ ] **Step 6: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/company/finance-legal/migrations/002_restore_baseline_gaps.up.sql \
        services/company/finance-legal/migrations/002_restore_baseline_gaps.down.sql
git commit -m "fix(db): restore the legal schema structure dropped by the R1 baseline squash

The 001 finance-legal baseline creates zero legal.* tables, but the AI-compliance
runtime path (ai-compliance-access / snapshot / legal-applicability services) and
18 finance-legal vitest suites need them. Flatten the DDL from deleted migrations
12/13/27/29/30/31 (git ref 81461673^) — structure only, no regulation/rule
content seed. Expand-only, idempotent.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: Restore `control_plane.document_ingestion*`

**Files:**
- Create: `services/cosa/migrations/005_restore_baseline_gaps.up.sql`
- Create: `services/cosa/migrations/005_restore_baseline_gaps.down.sql`

**Interfaces:**
- Consumes: nothing.
- Produces: `control_plane.document_ingestions` (text id) and `control_plane.document_ingestion_audit_events` (`id BIGINT GENERATED ALWAYS AS IDENTITY`, FK → `document_ingestions.id`). Consumed by knowledge-ingestion code and `make knowledge-ingestion-test` / `local-knowledge-e2e`.

- [ ] **Step 1: Prove it is missing**

```bash
cd /Volumes/SSD/javis-saas
export PGPASSWORD=change-me-cosa-migrator
psql -h 127.0.0.1 -U cosa_migrator -d javis_cosa_test -c "\d control_plane.document_ingestions"
```

Expected: `Did not find any relation named "control_plane.document_ingestions"`.

- [ ] **Step 2: Write the DDL**

Write `services/cosa/migrations/005_restore_baseline_gaps.up.sql` exactly as below. This is the deleted `15_document_ingestions.up.sql` (git ref `81461673^`) made idempotent, with the audit `id` changed from `BIGSERIAL` to `GENERATED ALWAYS AS IDENTITY` to match `control-plane-schema.ts:279` (`.generatedAlwaysAsIdentity()`) — the Drizzle schema is the tie-breaker per the SP-A design. Column sets verified against `control-plane-schema.ts:256-290`.

```sql
-- SP-A: restore control_plane.document_ingestion* dropped by the 001 cosa squash.
-- Flattened from deleted 15_document_ingestions.up.sql (git ref 81461673^),
-- matching control-plane-schema.ts. Expand-only, idempotent. Audit id is
-- GENERATED IDENTITY (Drizzle) not BIGSERIAL (old migration).
CREATE SCHEMA IF NOT EXISTS control_plane;

CREATE TABLE IF NOT EXISTS control_plane.document_ingestions (
  id                    TEXT PRIMARY KEY,
  workspace_id          TEXT NOT NULL,
  created_by            TEXT NOT NULL,
  original_filename     TEXT NOT NULL,
  declared_media_type   TEXT NOT NULL,
  detected_media_type   TEXT,
  size_bytes            BIGINT,
  source_sha256         TEXT,
  original_object_key   TEXT,
  state                 TEXT NOT NULL CHECK (state IN ('UPLOADING', 'QUARANTINED', 'QUEUED', 'VALIDATING', 'CONVERTING', 'REVIEW_PENDING', 'PUBLISHED', 'REJECTED', 'FAILED', 'EXPIRED')),
  idempotency_key       TEXT NOT NULL,
  knowledge_source_id   TEXT,
  converter_spec_id     TEXT,
  manifest_json         JSONB,
  failure_code          TEXT,
  claim_token           TEXT,
  created_at            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  UNIQUE (workspace_id, created_by, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_document_ingestions_workspace_state_created
  ON control_plane.document_ingestions (workspace_id, state, created_at DESC);

CREATE TABLE IF NOT EXISTS control_plane.document_ingestion_audit_events (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  ingestion_id  TEXT NOT NULL REFERENCES control_plane.document_ingestions(id) ON DELETE CASCADE,
  actor_kind    TEXT NOT NULL CHECK (actor_kind IN ('user', 'worker', 'system')),
  actor_id      TEXT NOT NULL,
  old_state     TEXT,
  new_state     TEXT NOT NULL,
  reason        TEXT,
  failure_code  TEXT,
  created_at    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_ingestion_audit_events_ingestion_created
  ON control_plane.document_ingestion_audit_events (ingestion_id, created_at DESC);
```

- [ ] **Step 3: Write the `.down.sql`**

```sql
DROP TABLE IF EXISTS control_plane.document_ingestion_audit_events;
DROP TABLE IF EXISTS control_plane.document_ingestions;
```

- [ ] **Step 4: Apply and verify shape**

```bash
cd /Volumes/SSD/javis-saas
export COSA_MIGRATOR_DATABASE_URL='postgresql://cosa_migrator:change-me-cosa-migrator@127.0.0.1:5432/javis_cosa_test?sslmode=disable'
node services/cosa/scripts/migrate.mjs
export PGPASSWORD=change-me-cosa-migrator
psql -h 127.0.0.1 -U cosa_migrator -d javis_cosa_test -c "\d control_plane.document_ingestion_audit_events" | grep -E "id|identity|ingestion_id"
node scripts/check-migration-backward-compat.mjs
```

Expected: `\d` shows `id | bigint | ... | generated always as identity`; compat check passes. Apply to dev cosa DB too (`COSA_MIGRATOR_DATABASE_URL=...@127.0.0.1:5432/cosa?sslmode=disable node services/cosa/scripts/migrate.mjs`).

- [ ] **Step 5: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add services/cosa/migrations/005_restore_baseline_gaps.up.sql \
        services/cosa/migrations/005_restore_baseline_gaps.down.sql
git commit -m "fix(db): restore control_plane.document_ingestion* dropped by the R1 squash

control-plane-schema.ts declares documentIngestions + documentIngestionAuditEvents
(audit id GENERATED IDENTITY) but the 001 cosa baseline never creates them;
knowledge-ingestion tests need them. Flatten from deleted 15_document_ingestions.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: IDENTITY-strip regression guard

**Files:**
- Create: `tests/quality/test_baseline_identity_columns.py`

**Interfaces:**
- Consumes: the restore migrations from Task 1–2 plus the already-committed `services/company/identity/migrations/002_*` and `packages/agent/migrations/004_*`.
- Produces: a CI-runnable guard (in `pyproject.toml` `testpaths` already includes `tests/quality` via `make ...` targets that name it explicitly; this file is run by `python -m pytest tests/quality/test_baseline_identity_columns.py`).

- [ ] **Step 1: Write the failing test**

```python
"""Guard: every DB-generated PK / sequence column must actually be GENERATED
AS IDENTITY in a migration. The Founder Trial R1 baseline squash (a pg_dump
--schema-only) stripped these clauses on several tables; this catches a
recurrence."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# (schema, table, column) that a repository INSERTs without the column,
# relying on the DB to fill it (RETURNING sequence* / RETURNING id).
DB_GENERATED_COLUMNS = [
    ("integration", "event_outbox", "id"),
    ("integration", "event_audit", "id"),
    ("control_plane", "document_ingestion_audit_events", "id"),
    ("agent", "run_events", "sequence_no"),
    ("agent", "runtime_signal_outbox", "sequence"),
    ("agent_conversation", "messages", "sequence_no"),
    ("agent_conversation", "run_stream_events", "sequence"),
]

MIGRATION_GLOBS = [
    "services/company/*/migrations/*.up.sql",
    "services/cosa/migrations/*.up.sql",
    "packages/agent/migrations/*.sql",
]


def _all_migration_sql() -> str:
    parts: list[str] = []
    for pat in MIGRATION_GLOBS:
        for p in sorted(ROOT.glob(pat)):
            if p.name.endswith(".down.sql"):
                continue
            parts.append(p.read_text(encoding="utf-8"))
    return "\n".join(parts)


def test_every_db_generated_column_has_an_identity_clause():
    sql = _all_migration_sql()
    missing: list[str] = []
    for _schema, table, column in DB_GENERATED_COLUMNS:
        # inline:  <column> BIGINT GENERATED ALWAYS AS IDENTITY
        inline = re.search(
            rf"\b{re.escape(column)}\s+(?:BIGINT|bigint)\s+GENERATED\s+ALWAYS\s+AS\s+IDENTITY",
            sql,
            re.IGNORECASE,
        )
        # altered: ALTER TABLE ... <table> ... ALTER COLUMN <column> ADD GENERATED ALWAYS AS IDENTITY
        altered = re.search(
            rf"ALTER\s+COLUMN\s+{re.escape(column)}\s+ADD\s+GENERATED\s+ALWAYS\s+AS\s+IDENTITY",
            sql,
            re.IGNORECASE,
        )
        if not (inline or altered):
            missing.append(f"{table}.{column}")
    assert not missing, (
        "DB-generated columns with no GENERATED IDENTITY clause in any migration: "
        + ", ".join(missing)
    )


def test_declared_generated_identity_sources_are_all_listed():
    """If a schema source adds a new .generatedAlwaysAsIdentity() column, this
    list must be updated — fail loudly so the guard above stays complete."""
    sources = list((ROOT / "services/company/shared/db/schema").glob("*.ts"))
    sources += list((ROOT / "services/cosa/storage").glob("*.ts"))
    declared = 0
    for s in sources:
        declared += len(re.findall(r"generatedAlwaysAsIdentity\(", s.read_text(encoding="utf-8")))
    # 2 in integration.ts + 1 in control-plane-schema.ts. Update DB_GENERATED_COLUMNS
    # (and this count) when a new one is added.
    assert declared == 3, (
        f"found {declared} generatedAlwaysAsIdentity() declarations; expected 3. "
        "Add the new column to DB_GENERATED_COLUMNS and bump this count."
    )
```

- [ ] **Step 2: Run it**

```bash
cd /Volumes/SSD/javis-saas
.venv/bin/python -m pytest tests/quality/test_baseline_identity_columns.py -q
```

Expected: PASS (Tasks 1–2 plus the already-committed identity/002 and agent/004 cover all seven columns). If `test_every_db_generated_column_has_an_identity_clause` FAILS, the Task 1/2 migration is missing an identity clause — fix that migration, not the test.

- [ ] **Step 3: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add tests/quality/test_baseline_identity_columns.py
git commit -m "test(db): guard against GENERATED IDENTITY clauses stripped from baselines

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: Regenerate drifted committed artifacts

**Files:**
- Modify: `deploy/schema/fingerprints.json` (generated)
- Modify: `docs/architecture/generated/company-usage-inventory.md` (generated)
- Modify: `tests/e2e/test_founder_trial_baseline_reset.py`

**Interfaces:**
- Consumes: the restore migrations from Tasks 1–2.
- Produces: golden fingerprint + usage inventory back in sync; `_EXPECTED_LEDGER` includes the two new migrations.

- [ ] **Step 1: Extend the ledger + existence assertions**

In `tests/e2e/test_founder_trial_baseline_reset.py`, add to `_EXPECTED_LEDGER`:

```python
    ("finance-legal", "002_restore_baseline_gaps.up.sql"),
    ("cosa", "005_restore_baseline_gaps.up.sql"),
```

- [ ] **Step 2: Regenerate the fingerprint**

```bash
cd /Volumes/SSD/javis-saas
export AGENT_MIGRATOR_DATABASE_URL='postgresql+asyncpg://agent_migrator:change-me-agent-migrator@127.0.0.1:5432/javis_agent_test'
export COSA_MIGRATOR_DATABASE_URL='postgresql://cosa_migrator:change-me-cosa-migrator@127.0.0.1:5432/javis_cosa_test?sslmode=disable'
export WORKSPACE_MIGRATOR_DATABASE_URL='postgresql://workspace_migrator:change-me-workspace-migrator@127.0.0.1:5432/javis_workspace_test?sslmode=disable'
node scripts/schema-fingerprint.mjs --write
node scripts/schema-fingerprint.mjs --check
```

Expected: `--check` passes; the workspace group gains the `legal.*` tables and the cosa group gains the two `document_ingestion*` tables. **Do not run `pytest tests/e2e/test_founder_trial_baseline_reset.py` before staging** — its `_fingerprint()` helper runs `git checkout deploy/schema/fingerprints.json` in a `finally` block and will revert the write.

- [ ] **Step 3: Regenerate the usage inventory**

```bash
cd /Volumes/SSD/javis-saas
make company-usage-inventory        # wraps: $(PYTHON) scripts/company_usage_inventory.py
$(PYTHON) scripts/company_usage_inventory.py --check   # or: sed -n 's/.*PYTHON *?= *//p' Makefile
```

Expected: the `--check` run exits 0 (inventory in sync).

- [ ] **Step 4: Verify the migration gates**

```bash
cd /Volumes/SSD/javis-saas
make migration-compat-check
node scripts/test-migration-rollback.mjs
```

Expected: both pass. Gate E rolls the two new `002`/`005` down and back up; the fingerprint check in its Phase 4 matches the regenerated golden.

- [ ] **Step 5: Run the baseline-reset test last, then commit**

```bash
cd /Volumes/SSD/javis-saas
export AGENT_TEST_MIGRATOR_DATABASE_URL="$AGENT_MIGRATOR_DATABASE_URL"
export COSA_TEST_MIGRATOR_DATABASE_URL="$COSA_MIGRATOR_DATABASE_URL"
export WORKSPACE_TEST_MIGRATOR_DATABASE_URL="$WORKSPACE_MIGRATOR_DATABASE_URL"
.venv/bin/python -m pytest tests/e2e/test_founder_trial_baseline_reset.py tests/quality/test_founder_trial_baseline_inventory.py -q
# the test reverts fingerprints.json in its teardown — restore the regenerated one:
node scripts/schema-fingerprint.mjs --write
git add deploy/schema/fingerprints.json docs/architecture/generated/company-usage-inventory.md tests/e2e/test_founder_trial_baseline_reset.py
git commit -m "chore(db): regenerate golden fingerprint + ledger + usage inventory for restored schema

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

Expected: tests pass (`_EXPECTED_LEDGER` now matches), then the fingerprint is rewritten and staged.

---

## Task 5: Full `make verify-local` sweep

**Files:** whichever the sweep surfaces — folded into `002_restore_baseline_gaps` (finance-legal or cosa) as `ADD COLUMN IF NOT EXISTS` / `CREATE TABLE IF NOT EXISTS`, never a new migration file.

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces: `make verify-local` green end to end.

- [ ] **Step 1: Run the aggregate gate**

```bash
cd /Volumes/SSD/javis-saas
set -a; source .env; set +a; export PGPASSWORD="$POSTGRES_PASSWORD" PGUSER=postgres
make verify-local 2>&1 | tee /tmp/verify-local.log
```

`verify-local = lint typecheck-py python-test-unit python-test-integration desktop-worker-test knowledge-ingestion-test boundary-check check-docs contract-freeze-check e2e-test e2e-cross-plane-smoke`.

- [ ] **Step 2: For each failure, root-cause before fixing**

Use `superpowers:systematic-debugging`. Expected failures and their handling:
- **`e2e-cross-plane-smoke` S2** (`test_s2_dispatch_worker_result`) — was red on `legal.ai_system_catalog` missing; must be green now. If it fails elsewhere, debug that specific point.
- **`e2e-test`** golden path — should be unaffected; if a scenario now reaches AI-compliance and fails on a missing `legal.*` column, add the column to `002_restore_baseline_gaps` from the source file at `81461673^`.
- **`knowledge-ingestion-test`** — should pass now that `document_ingestion*` exist.
- **`python-test-integration`** (`pytest tests/agent tests/apps/cosa tests/integration -m "integration and not live_provider and not durability"`) — if a test drives the AI-compliance HTTP path (`tests/e2e/test_ai_compliance_company_http.py`, `tests/apps/cosa/compliance/`) and needs regulation **content** (rows in `regulation_versions` / `applicability_rules`), add the **minimal** seed those tests require — copy only the specific `INSERT` rows the failing assertion needs from `81461673^:.../14_legal_seed_tt58_nq86.up.sql` or `.../30_*.up.sql`, into a new `services/company/finance-legal/migrations/003_seed_min_legal_for_tests.up.sql` (a separate file — seed is not structure). Document in the file header exactly which test forced each row.
- **`check-docs`** — if `scripts/check_doc_links.py` flags the new spec/plan, fix the link.

- [ ] **Step 3: Re-run until green**

```bash
cd /Volumes/SSD/javis-saas
set -a; source .env; set +a; export PGPASSWORD="$POSTGRES_PASSWORD" PGUSER=postgres
make verify-local
```

Expected: exits 0.

- [ ] **Step 4: Confirm no Automation regression**

```bash
cd /Volumes/SSD/javis-saas
set -a; source .env; set +a; export PGPASSWORD="$POSTGRES_PASSWORD" PGUSER=postgres
make automation-mvp-e2e
```

Expected: `6 passed`.

- [ ] **Step 5: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add -A
git status --short   # review: only migration files + any 003 seed, nothing stray
git commit -m "fix(db): close remaining baseline gaps surfaced by make verify-local

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

If `git status --short` shows nothing to commit (verify-local was already green after Task 4), skip the commit and note it.

---

## Task 6: Reconcile the Founder Trial reset plan (doc-only)

**Files:**
- Modify: `docs/superpowers/plans/2026-09-09-founder-trial-mvp-reset-baseline.md`

**Interfaces:**
- Consumes: git history + the verified state after Tasks 1–5.
- Produces: an accurate plan doc — no code change.

- [ ] **Step 1: Establish real status per task**

```bash
cd /Volumes/SSD/javis-saas
git log --oneline --all --grep="Task 1\|Task 2\|Task 3\|Task 4\|Task 5\|Task 6\|Task 7\|Task 8\|Task 9\|Task 10\|Task 11" -- docs/superpowers/plans/2026-09-09-founder-trial-mvp-reset-baseline.md 2>/dev/null | head
git log --oneline | grep -iE "founder trial|baseline|reset|cutover|R1 surface" | head -20
ls services/company/*/migrations/ packages/agent/migrations/ services/cosa/migrations/ | grep -E "001_founder_trial|baseline"
```

Cross-reference: Task 2 (contract) — `shared/contracts/mvp-surface.json` version `2026-09-09-founder-trial-r1` exists → done. Task 6 (capability manifest) — `services/cosa/services/surface-policy.ts` with the startup validator exists → done. Task 10 (baselines) — the six `001_founder_trial_mvp_baseline` files exist + `make test-db-reset` → done. Task 11 (fresh-DB HTTP) — `tests/e2e/test_founder_trial_http.py` + `test_founder_trial_full_stack.py` exist → done.

- [ ] **Step 2: Tick the boxes + add a post-cutover note**

For each of Tasks 1–11, change `- [ ]` to `- [x]` where the deliverable and its verification exist in the tree. For any step genuinely unfinished, leave `- [ ]` and add a one-line reason.

Append a section at the end of the plan:

```markdown
## Post-cutover baseline gaps (found 2026-09-10)

The 001 pg_dump squash dropped objects still needed by running code. Restored as
expand-only migrations, not by editing 001:

- `services/company/identity/migrations/002_restore_business_policy_tables.up.sql`
  — core.workspace_policy_versions + cutover markers; GENERATED IDENTITY on
  integration.event_outbox / event_audit. (commit a9709b70)
- `packages/agent/migrations/004_restore_baseline_identity_columns.sql`
  — GENERATED IDENTITY on run_events.sequence_no / runtime_signal_outbox.sequence
  / agent_conversation.messages.sequence_no / run_stream_events.sequence.
  (commit a9709b70)
- `services/cosa/migrations/004_seed_canonical_cosa_roles.up.sql`
  — cosa.roles was missing `member`; every /platform/auth/register 500'd.
  (commit a9709b70)
- `services/company/finance-legal/migrations/002_restore_baseline_gaps.up.sql`
  — the entire `legal` schema (regulation catalog + AI-compliance, ~23 tables).
  Structure only; regulation content seed deferred. (SP-A, this effort)
- `services/cosa/migrations/005_restore_baseline_gaps.up.sql`
  — control_plane.document_ingestions + document_ingestion_audit_events. (SP-A)

Regression guard: `tests/quality/test_baseline_identity_columns.py`.
```

- [ ] **Step 3: Commit**

```bash
cd /Volumes/SSD/javis-saas
git add docs/superpowers/plans/2026-09-09-founder-trial-mvp-reset-baseline.md
git commit -m "docs(plan): reconcile Founder Trial reset status + record post-cutover baseline gaps

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Final verification

```bash
cd /Volumes/SSD/javis-saas
set -a; source .env; set +a; export PGPASSWORD="$POSTGRES_PASSWORD" PGUSER=postgres
make migration-compat-check
node scripts/test-migration-rollback.mjs
node scripts/schema-fingerprint.mjs --check      # after re-writing golden if the baseline-reset test ran
.venv/bin/python -m pytest tests/quality/test_baseline_identity_columns.py -q
make verify-local
make automation-mvp-e2e
```

All must pass / exit 0. `make verify` (CI gate, adds Encore `services-test`) is a final sanity check, not an SP-A blocking condition.
