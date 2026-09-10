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

## Task 5: Full `make verify-local` sweep — SUPERSEDED (partially executed)

> **2026-09-10 — scope revised.** Task 5's first pass proved the SP-A spec's
> "two gaps" premise wrong: the R1 squash (`81461673`) dropped **five** gap
> classes, plus a CRITICAL bug landed in a Phase-3 migration. `make verify-local`
> has never been green since the squash; the previously-"green" targets rode
> leftover pre-squash state in the dev DB.
>
> **Landed and kept** (legitimate side-fixes, out of the blocked scope):
> - `404920f3` — pre-existing ruff debt (from `8dc6b72e`) that blocked `make lint`.
> - `6c2a1513` — two durability tests: signer used `os.environ["WORKER_SERVICE_JWT_SECRET"]`
>   while the spawned `services/cosa` verified with the module constant; and
>   `test_crash_recovery_subprocess.py` didn't pin `COSA_EXECUTION_PLANE_URL`
>   (the primary key `resolve_execution_plane_url()` reads) so the worker polled
>   the dead dev port. Both fixed to use the value the service-under-test uses.
>
> **User decisions (2026-09-10):** restore the RETAINED-scope gaps (A/B/C below);
> **quarantine** the DELIBERATELY-DESCOPED subsystems' tests (D — Vault/RAG, eval
> promotion, agent memory/artifact are `PLANNED` per reset spec §7.3 line 66/187,
> not R1); **reset the dev `workspace` DB** to clear the checksum drift.
>
> The `make verify-local` gate itself moves to **Task 5F**. Tasks 5A–5E do the
> restores/quarantine/reset that make it reachable.

---

## Task 5A: Fix the `agent.runtime_signal_outbox.sequence` identity bug

**Files:**
- Create: `packages/agent/migrations/005_fix_runtime_signal_outbox_sequence.sql`
- Create: `packages/agent/migrations/005_fix_runtime_signal_outbox_sequence.down.sql`
- Modify: `tests/quality/test_baseline_identity_columns.py` (the `DB_GENERATED_COLUMNS` list: 7 → 6 tuples)
- Modify: `tests/e2e/test_founder_trial_baseline_reset.py` (`_EXPECTED_LEDGER` += the new agent migration)
- Modify: `deploy/schema/fingerprints.json` (regenerated — the `agent` group's `runtime_signal_outbox.sequence` column loses its identity attribute)

**Interfaces:**
- Consumes: the committed `packages/agent/migrations/004_restore_baseline_identity_columns.sql` (which introduced the bug) and Task 3's guard test.
- Produces: `enqueue_runtime_signal` works on a fresh baseline DB → the agent-run → runtime-signal-outbox → Company projection path is unblocked; cross-plane smoke S2 can reach a real `run.completed`.

**Root cause (already diagnosed, controller-verified):** `004_restore_baseline_identity_columns.sql` lists `('agent','runtime_signal_outbox','sequence')` alongside genuine auto-sequence columns and re-attaches `GENERATED ALWAYS AS IDENTITY` to it. But `packages/agent/workforce/repository.py::enqueue_runtime_signal` (line ~782) inserts `sequence` **explicitly** — it is a caller-supplied natural-key component (`ON CONFLICT (workspace_id, source_kind, source_id, sequence)`), and the worker passes `sequence=1`. Pre-squash DDL (`git show 81461673^:packages/agent/migrations/022_workforce_assignments_and_runtime_outbox.sql`) and the current baseline `001_founder_trial_mvp_baseline.sql:265` both declare it `sequence BIGINT NOT NULL` — never identity. Every `enqueue_runtime_signal` on a baseline-migrated DB dies with `cannot insert a non-DEFAULT value into column "sequence"`, swallowed by the worker's broad `except Exception` in `apps/cosa/worker/handlers.py`. This is cross-plane smoke S2's real blocker; commit `9edb3db1`'s "fake provider ran out of turns" attribution was wrong.

- [ ] **Step 1: Reproduce (RED)**

```bash
cd /Volumes/SSD/javis-saas
bash scripts/provision-founder-trial-test-dbs.sh
export AGENT_MIGRATOR_DATABASE_URL='postgresql+asyncpg://agent_migrator:change-me-agent-migrator@127.0.0.1:5432/javis_agent_test'
# reset+apply agent plane only is fine here; or the full 3-var test-db-reset
PGPASSWORD=change-me-agent-migrator psql -h 127.0.0.1 -U agent_migrator -d javis_agent_test -c \
  "INSERT INTO agent.runtime_signal_outbox (outbox_id, workspace_id, source_kind, source_id, sequence, state, observed_at, correlation_id, payload_hash, state_delivery) VALUES (gen_random_uuid(), 'ws_x', 'run', 'r1', 1, 'COMPLETED', now(), 'c', 'h', 'PENDING');"
```
Expected: `ERROR: cannot insert a non-DEFAULT value into column "sequence"` … `Column "sequence" is an identity column defined as GENERATED ALWAYS.`

- [ ] **Step 2: Write the fix migration**

`packages/agent/migrations/005_fix_runtime_signal_outbox_sequence.sql`:

```sql
-- SP-A Task 5A: migration 004 wrongly attached GENERATED ALWAYS AS IDENTITY to
-- agent.runtime_signal_outbox.sequence. That column is a caller-supplied natural-key
-- component (enqueue_runtime_signal inserts it explicitly; pre-squash 022_* and the
-- current baseline 001 both declare it plain `sequence BIGINT NOT NULL`). Detach the
-- identity so explicit inserts work again. 004 is checksum-immutable — do NOT edit it.
-- Non-destructive: the column keeps its data, type (bigint) and NOT NULL; only the
-- auto-generation is removed. Idempotent.
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'agent' AND c.relname = 'runtime_signal_outbox'
      AND a.attname = 'sequence' AND a.attidentity <> ''
  ) THEN
    EXECUTE 'ALTER TABLE agent.runtime_signal_outbox ALTER COLUMN sequence DROP IDENTITY IF EXISTS';
  END IF;
END $$;
```

`.down.sql` (best-effort inverse; the "correct" state has no identity, so down re-adds it to match what `004` left):

```sql
-- Inverse of 005: re-attach the (incorrect, per 004) identity. Only for rollback symmetry.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_attribute a
    JOIN pg_class c ON c.oid = a.attrelid
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'agent' AND c.relname = 'runtime_signal_outbox'
      AND a.attname = 'sequence' AND a.attidentity <> ''
  ) THEN
    EXECUTE 'ALTER TABLE agent.runtime_signal_outbox ALTER COLUMN sequence ADD GENERATED ALWAYS AS IDENTITY';
  END IF;
END $$;
```

`ALTER COLUMN ... DROP IDENTITY` is not in `check-migration-backward-compat.mjs`'s `DESTRUCTIVE_PATTERNS` (DROP TABLE/COLUMN/SCHEMA, RENAME, TRUNCATE) — the gate passes.

- [ ] **Step 3: Apply + GREEN**

```bash
cd /Volumes/SSD/javis-saas
python packages/agent/scripts/migrate.py   # or the repo's agent migrate entrypoint; AGENT_MIGRATOR_DATABASE_URL set
# re-run the Step 1 INSERT → now succeeds
PGPASSWORD=change-me-agent-migrator psql -h 127.0.0.1 -U agent_migrator -d javis_agent_test -c "\d agent.runtime_signal_outbox" | grep sequence
# → `sequence | bigint | not null` (no "generated always as identity")
node scripts/check-migration-backward-compat.mjs   # pass
```
Apply to the dev `agent` DB too (`AGENT_MIGRATOR_DATABASE_URL=...@127.0.0.1:5432/agent`).

- [ ] **Step 4: Fix Task 3's guard test**

In `tests/quality/test_baseline_identity_columns.py`, remove the tuple `("agent", "runtime_signal_outbox", "sequence")` from `DB_GENERATED_COLUMNS` (7 → 6) and update the module docstring / any comment that claimed this column is DB-generated (it isn't — that claim was inherited from `004`'s wrong comment). The declaration-count test (`declared == 3`) is unaffected — `runtime_signal_outbox.sequence` was never a `.generatedAlwaysAsIdentity()` Drizzle column. Run:
```bash
.venv/bin/python -m pytest tests/quality/test_baseline_identity_columns.py -q   # 2 passed
```

- [ ] **Step 5: Ledger + fingerprint**

```bash
cd /Volumes/SSD/javis-saas
# _EXPECTED_LEDGER += ("agent", "005_fix_runtime_signal_outbox_sequence.sql")
export AGENT_MIGRATOR_DATABASE_URL='postgresql+asyncpg://agent_migrator:change-me-agent-migrator@127.0.0.1:5432/javis_agent_test'
export COSA_MIGRATOR_DATABASE_URL='postgresql://cosa_migrator:change-me-cosa-migrator@127.0.0.1:5432/javis_cosa_test?sslmode=disable'
export WORKSPACE_MIGRATOR_DATABASE_URL='postgresql://workspace_migrator:change-me-workspace-migrator@127.0.0.1:5432/javis_workspace_test?sslmode=disable'
# re-apply all planes to the test DBs first (3-var test-db-reset.mjs), then:
node scripts/schema-fingerprint.mjs --write && node scripts/schema-fingerprint.mjs --check
node scripts/test-migration-rollback.mjs   # Gate E: 005 down→up roundtrip
# run the ledger pytest LAST (reverts fingerprints.json in teardown), then re-write:
env -u AGENT_MIGRATOR_DATABASE_URL -u COSA_MIGRATOR_DATABASE_URL -u WORKSPACE_MIGRATOR_DATABASE_URL \
  AGENT_TEST_MIGRATOR_DATABASE_URL='postgresql+asyncpg://agent_migrator:change-me-agent-migrator@127.0.0.1:5432/javis_agent_test' \
  COSA_TEST_MIGRATOR_DATABASE_URL='postgresql://cosa_migrator:change-me-cosa-migrator@127.0.0.1:5432/javis_cosa_test?sslmode=disable' \
  WORKSPACE_TEST_MIGRATOR_DATABASE_URL='postgresql://workspace_migrator:change-me-workspace-migrator@127.0.0.1:5432/javis_workspace_test?sslmode=disable' \
  .venv/bin/python -m pytest tests/e2e/test_founder_trial_baseline_reset.py -q
node scripts/schema-fingerprint.mjs --write && node scripts/schema-fingerprint.mjs --check
```

- [ ] **Step 6: Prove it end to end**

```bash
cd /Volumes/SSD/javis-saas
set -a; source .env; set +a; export PGPASSWORD="$POSTGRES_PASSWORD" PGUSER=postgres
.venv/bin/python -m pytest tests/e2e/test_cross_plane_smoke.py -m cross_plane -q
```
Expected: S2 (`test_s2_dispatch_worker_result`) now finds `agent.runtime_signal_outbox` populated `[(1, 'COMPLETED')]`. If S2's assertion was softened by `9edb3db1` to "durable facts, not stream terminal", tighten it back to also assert the stream terminal is `run.completed` (the bug that forced the softening is now fixed) — but only if S2 genuinely reaches that state; otherwise leave the durable-fact assertion and note why in the report.

- [ ] **Step 7: Commit**

```bash
git add packages/agent/migrations/005_fix_runtime_signal_outbox_sequence.sql \
        packages/agent/migrations/005_fix_runtime_signal_outbox_sequence.down.sql \
        tests/quality/test_baseline_identity_columns.py \
        tests/e2e/test_founder_trial_baseline_reset.py \
        deploy/schema/fingerprints.json
git commit -m "fix(db): detach the wrongly-attached IDENTITY from agent.runtime_signal_outbox.sequence

Migration 004 mis-classified this caller-supplied natural-key column as an
auto-sequence and re-attached GENERATED ALWAYS AS IDENTITY. Every
enqueue_runtime_signal on a baseline-migrated DB then failed with
'cannot insert a non-DEFAULT value', swallowed by the worker's broad except,
so no runtime signal / Company projection was ever written. New migration 005
drops the identity; 004 stays untouched (checksum-immutable). Guard test's
tracked-column list corrected 7->6.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 5B: Restore the `operating.*` baseline gap

**Files:**
- Create: `services/company/operations/migrations/004_restore_baseline_gaps.up.sql`
- Create: `services/company/operations/migrations/004_restore_baseline_gaps.down.sql`

**Interfaces:**
- Consumes: nothing.
- Produces: every `operating.*` / `strategy.*` table declared in `services/company/shared/db/schema/operations.ts` + `strategy.ts` but absent from `services/company/operations/migrations/001_founder_trial_mvp_baseline.up.sql` now exists. `operating` and `strategy` are RETAINED R1 schemas (`test_founder_trial_baseline_inventory.py::RETAINED_SCHEMAS["company-operations"]`).

`operations` migrations currently: `001_founder_trial_mvp_baseline.up.sql` + `003_cosa_automation_mvp.up.sql`. Add `004_restore_baseline_gaps.up.sql` + `.down.sql`.

**Controller research (2026-09-10) — the gap set and its exact source migrations:**

| Drizzle decl (missing from `001`) | Source migration at `81461673^` |
|---|---|
| `operations.ts:585` `operating.task_projects` | `services/company/operations/migrations/14_project_link_tables.up.sql` |
| `operations.ts:684` `operating.runtime_source_signals` | `services/company/operations/migrations/33_mvp_strategy_canvas_runtime.up.sql` |
| `operations.ts:698` `operating.runtime_snoozes` | `33_mvp_strategy_canvas_runtime.up.sql` |
| `strategy.ts:462` `strategy.canvases` | `33_mvp_strategy_canvas_runtime.up.sql` |
| `strategy.ts:475` `strategy.canvas_revisions` | `33_mvp_strategy_canvas_runtime.up.sql` |
| `strategy.okr_objective_projects` (verify it's in `strategy.ts`) | `14_project_link_tables.up.sql` |

`14_project_link_tables.up.sql` is 2 tables (`operating.task_projects`, `strategy.okr_objective_projects`) with composite FKs into `operating.tasks` / `strategy.projects` / `strategy.okr_objectives` (+ 2 indexes each). `33_mvp_strategy_canvas_runtime.up.sql` is `strategy.canvases`, `strategy.canvas_revisions` (composite FK + CHECKs), `operating.runtime_source_signals` (`UNIQUE (workspace_id, source_kind, source_id, sequence)`), `operating.runtime_snoozes` (+ indexes).

- [ ] **Step 1: Confirm the exact missing set**

```bash
cd /Volumes/SSD/javis-saas
# Drizzle-declared operating.*/strategy.* table names:
grep -oE '(operating|strategy)Schema\.table\("(\w+)"' services/company/shared/db/schema/operations.ts services/company/shared/db/schema/strategy.ts | sed -E 's/.*"(\w+)"/\1/' | sort -u
# baseline 001 creates:
grep -oE 'CREATE TABLE (IF NOT EXISTS )?(operating|strategy)\.\w+' services/company/operations/migrations/001_founder_trial_mvp_baseline.up.sql | sed -E 's/.*(operating|strategy)\./\1./' | sort -u
```
The difference is your table list. Cross-check it against the controller table above; if the diff turns up MORE missing tables than listed, restore those too (same gap class). If it turns up FEWER (e.g. `okr_objective_projects` is actually in `001`), restore only what's genuinely missing. Also probe the migrated test DB: `PGPASSWORD=change-me-workspace-migrator psql -h 127.0.0.1 -U workspace_migrator -d javis_workspace_test -c "\dt operating.* strategy.*"`.

- [ ] **Step 2: Reconstruct DDL into `004_restore_baseline_gaps.up.sql`**

```bash
git show 81461673^:services/company/operations/migrations/14_project_link_tables.up.sql
git show 81461673^:services/company/operations/migrations/33_mvp_strategy_canvas_runtime.up.sql
```
Reproduce the `CREATE TABLE` / `CREATE INDEX` verbatim BUT: every `CREATE TABLE` → `CREATE TABLE IF NOT EXISTS` (some already are), every `CREATE INDEX` → `CREATE INDEX IF NOT EXISTS`, and wrap any bare `ALTER TABLE ... ADD CONSTRAINT` (there are none in these two, the FKs are inline) in `DO $$ ... EXCEPTION WHEN duplicate_object THEN NULL; END $$;`. Strip nothing else — these two files are pure DDL (no INSERT/UPDATE). Order: parent tables before children (`strategy.canvases` before `strategy.canvas_revisions`; `task_projects`/`okr_objective_projects` need `operating.tasks`, `strategy.projects`, `strategy.okr_objectives` which `001` already created). Cross-check every column + constraint name against `operations.ts` / `strategy.ts` — **Drizzle wins on disagreement**; note any deviation in the report. `id BIGINT PRIMARY KEY` no identity (Snowflake, app-supplied) unless the `.ts` says `.generatedAlwaysAsIdentity()`.

- [ ] **Step 3: `.down.sql`** — `DROP TABLE IF EXISTS <schema>.<t> CASCADE;` for each table added, child-first (`canvas_revisions` before `canvases`; the link tables before nothing in particular). Do not drop schemas.

- [ ] **Step 4: Apply + verify**

```bash
cd /Volumes/SSD/javis-saas
export WORKSPACE_MIGRATOR_DATABASE_URL='postgresql://workspace_migrator:change-me-workspace-migrator@127.0.0.1:5432/javis_workspace_test?sslmode=disable'
node services/company/scripts/migrate.mjs
node scripts/check-migration-backward-compat.mjs
cd services/company && npx tsc --noEmit
# run the e2e-test suites that were failing on these relations, isolated to the test DB:
cd /Volumes/SSD/javis-saas && WORKSPACE_DATABASE_URL='postgresql://workspace_app:change-me-workspace-app@127.0.0.1:5432/javis_workspace_test?sslmode=disable' \
  .venv/bin/python -m pytest tests/e2e -k "operating or runtime_source or task_project" -q
```
Apply to dev `workspace` DB too (after Task 5E resets it) or note it's deferred to 5E.

- [ ] **Step 5: Commit** — `git add services/company/operations/migrations/004_restore_baseline_gaps.{up,down}.sql`; message `fix(db): restore operating.* tables dropped by the R1 baseline squash`; `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.

---

## Task 5C: Restore `finance.accounting_fiscal_profiles`

**Files:**
- Create: `services/company/finance-legal/migrations/003_restore_finance_baseline_gaps.up.sql`
- Create: `services/company/finance-legal/migrations/003_restore_finance_baseline_gaps.down.sql`

**Interfaces:**
- Consumes: nothing (independent of Task 1's `002` legal restore).
- Produces: `finance.accounting_fiscal_profiles` (+ any sibling `finance.*` table the finance-legal vitest / e2e sweep proves missing) exists, matching `services/company/shared/db/schema/finance.ts`. `finance` is a RETAINED R1 schema.

`finance-legal` migrations after Task 1: `001_*` + `002_restore_baseline_gaps` (legal). This is `003`, **finance** structure only — keep it separate from the legal `002` (different schema, different concern).

- [ ] **Step 1: Enumerate** — `grep -oE '\.table\("(\w+)"' services/company/shared/db/schema/finance.ts | sort -u` vs `grep -oE 'CREATE TABLE (IF NOT EXISTS )?finance\.\w+' services/company/finance-legal/migrations/001_founder_trial_mvp_baseline.up.sql | sort -u`. The Task 1 report + Task 5 report both named `finance.accounting_fiscal_profiles`; confirm whether anything else is missing.

- [ ] **Step 2: Reconstruct DDL** — `git show 81461673 --stat -- services/company/finance-legal/migrations/ | grep -iE "fiscal|accounting|profile"`, then `git show 81461673^:services/company/finance-legal/migrations/<file>` for the `CREATE TABLE finance.accounting_fiscal_profiles` DDL. `CREATE TABLE IF NOT EXISTS`, cross-check columns against `finance.ts` (Drizzle wins), strip seed/backfill.

- [ ] **Step 3: `.down.sql`** — `DROP TABLE IF EXISTS finance.<t> CASCADE;` child-first.

- [ ] **Step 4: Apply + verify**

```bash
cd /Volumes/SSD/javis-saas
export WORKSPACE_MIGRATOR_DATABASE_URL='postgresql://workspace_migrator:change-me-workspace-migrator@127.0.0.1:5432/javis_workspace_test?sslmode=disable'
node services/company/scripts/migrate.mjs
node scripts/check-migration-backward-compat.mjs
cd services/company && WORKSPACE_DATABASE_URL='postgresql://workspace_app:change-me-workspace-app@127.0.0.1:5432/javis_workspace_test?sslmode=disable' \
  npx vitest run finance-legal/tests/legal-applicability-integrity.test.ts finance-legal/tests/legal-applicability.test.ts
```
Expected: the 3 finance-legal suites that were red on `relation "finance.accounting_fiscal_profiles" does not exist` (Task 1 report) go green (they may still need a row or two of legal content seed — if so, that seed is Task 5C-local: add a `003_seed...` only if a specific assertion needs it, and document which).

- [ ] **Step 5: Commit** — `git add services/company/finance-legal/migrations/003_restore_finance_baseline_gaps.{up,down}.sql`; message `fix(db): restore finance.accounting_fiscal_profiles dropped by the R1 baseline squash`; `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.

---

## Task 5D: Quarantine the descoped agent-plane test suites

**Files:**
- Modify: the failing test modules under `tests/agent/**` (44 `python-test-unit` failures) and `tests/**` for `knowledge-ingestion-test` (14 failures) — add module-level skip markers.
- Modify (if needed): `Makefile` `python-test-unit` `--cov-fail-under=80` and/or a coverage `omit` list.

**Interfaces:**
- Consumes: the Task 5 report's failure inventory (relations `vault.*`, `knowledge.*`, `agent_memory.*`, `agent_evals.*`, `agent_artifact.*`, `agent.workforce_schedules`, `agent.local_ingestion_attempts`).
- Produces: `make python-test-unit` and `make knowledge-ingestion-test` green — the descoped-subsystem tests skip with a traceable reason instead of erroring.

**Rationale:** Vault/RAG, eval promotion, agent memory and artifact are `PLANNED`, not Founder Trial R1 — `docs/superpowers/specs/2026-09-09-founder-trial-mvp-reset-baseline-design.md` line 66 ("Vault/RAG … PLANNED — no live route/module") and line 187, and `tests/quality/test_founder_trial_baseline_inventory.py::FORBIDDEN_SCHEMAS`. Their schemas were intentionally dropped. Restoring them would reopen an architecture decision (forbidden by CLAUDE.md). The tests are stale; quarantine them.

- [ ] **Step 1: Inventory the exact failing modules**

```bash
cd /Volumes/SSD/javis-saas
set -a; source .env; set +a; export PGPASSWORD="$POSTGRES_PASSWORD" PGUSER=postgres
bash scripts/provision-founder-trial-test-dbs.sh
# reset+apply test DBs (3-var test-db-reset.mjs)
make python-test-unit 2>&1 | grep -E "^FAILED|^ERROR" | sed 's/::.*//' | sort -u > /tmp/pu-fails.txt
make knowledge-ingestion-test 2>&1 | grep -E "^FAILED|^ERROR" | sed 's/::.*//' | sort -u > /tmp/ki-fails.txt
cat /tmp/pu-fails.txt /tmp/ki-fails.txt
# For each file, confirm it references a FORBIDDEN/PLANNED schema:
while read f; do echo "== $f =="; grep -oE '(vault|knowledge|agent_memory|agent_evals|agent_artifact|workforce_schedules|local_ingestion)[._]' "$f" | sort -u; done < /tmp/pu-fails.txt
```
If a failing module does **not** reference any descoped schema, it is NOT a 5D case — STOP and report it (it may be a real regression or a different gap).

- [ ] **Step 2: Add the skip marker**

At the top of each confirmed-descoped test module (after imports), add:

```python
import pytest

pytestmark = pytest.mark.skip(
    reason="Subsystem PLANNED, not in Founder Trial R1 — reset spec "
    "docs/superpowers/specs/2026-09-09-founder-trial-mvp-reset-baseline-design.md §7.3. "
    "Schema (vault/knowledge/agent_memory/agent_evals/agent_artifact) intentionally "
    "dropped from the 001 baseline; re-enable when the subsystem is promoted to R1."
)
```

Prefer a module-level `pytestmark`; only skip individual functions if a module mixes descoped and in-scope tests (check — most won't). Do **not** delete the tests.

- [ ] **Step 3: Coverage floor**

Re-run `make python-test-unit`. If `--cov-fail-under=80` now fails because the skipped modules dropped the measured coverage, either (a) add the descoped `packages/agent` subpackages (`packages/agent/vault`, `.../knowledge`, `.../memory`, `.../evals`, `.../artifacts`) to a coverage `omit` in `pyproject.toml`/`.coveragerc` so the ratio reflects only R1 code, or (b) lower the floor with a comment citing this task. Prefer (a). Document the before/after coverage number.

- [ ] **Step 4: Verify + commit**

```bash
cd /Volumes/SSD/javis-saas
set -a; source .env; set +a; export PGPASSWORD="$POSTGRES_PASSWORD" PGUSER=postgres
make python-test-unit          # green (N skipped)
make knowledge-ingestion-test  # green (M skipped)
git add -A && git status --short   # test modules + maybe pyproject.toml/.coveragerc + Makefile
git commit -m "test: quarantine descoped Vault/RAG + eval-promotion + agent-memory suites

These test PLANNED subsystems whose schemas were intentionally dropped from the
Founder Trial R1 baseline (reset spec §7.3). Skip with a spec reference rather
than restore the schemas (which would reopen the R1 descoping decision).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 5E: Reset the dev `workspace` DB + apply all restore migrations to the dev DBs

**Files:** none (operational).

**Interfaces:**
- Consumes: Tasks 1, 2, 5A, 5B, 5C committed.
- Produces: the dev `workspace` / `agent` / `cosa` DBs match the committed migration tree — clears the `identity/002_restore_business_policy_tables.up.sql` checksum drift a concurrent session left, so `make e2e-test` (which uses ambient env) can run.

**Rationale:** the Founder Trial baseline is a test-reset-only product (reset spec §7.3 — "marking an unknown existing database as current is incompatible with a test-reset-only product"). User approved the destructive reset.

- [ ] **Step 1: Confirm the drift is still there and snapshot what's in the dev DB**

```bash
cd /Volumes/SSD/javis-saas
set -a; source .env; set +a
PGPASSWORD="$POSTGRES_PASSWORD" psql -h 127.0.0.1 -U postgres -d workspace -c \
  "SELECT name, substr(checksum,1,12), applied_at FROM schema_migrations WHERE name LIKE '%002_restore_business_policy%';"
PGPASSWORD="$POSTGRES_PASSWORD" psql -h 127.0.0.1 -U postgres -d workspace -c "\dn"   # note any non-R1 schemas present
```

- [ ] **Step 2: Reset + re-migrate the dev DBs from the committed tree**

```bash
cd /Volumes/SSD/javis-saas
set -a; source .env; set +a; export PGPASSWORD="$POSTGRES_PASSWORD" PGUSER=postgres
# the dev-DB variant of the founder-trial reset — same script, dev URLs:
APP_ENV=development DATABASE_RESET=CONFIRM_FOUNDER_TRIAL_MVP_RESET node scripts/test-db-reset.mjs   # if it supports a dev mode
# OR, if that script is test-only: drop+recreate the app schemas in dev `workspace`/`agent`/`cosa`
#   and re-run the plane migrators:
#   node services/company/scripts/migrate.mjs   (WORKSPACE_MIGRATOR_DATABASE_URL=...@/workspace)
#   node services/cosa/scripts/migrate.mjs      (COSA_MIGRATOR_DATABASE_URL=...@/cosa)
#   python packages/agent/scripts/migrate.py    (AGENT_MIGRATOR_DATABASE_URL=...@/agent)
```
Investigate the exact repo idiom first (`grep -rn "DATABASE_RESET\|test-db-reset" scripts/ Makefile package.json`); use whatever the repo provides for a dev reset. If none exists, the minimal safe path is: `DROP SCHEMA ... CASCADE` for each app schema in the dev DB + `CREATE SCHEMA` + re-run the migrator (the migrator recreates everything from `001` + restores).

- [ ] **Step 3: Verify**

```bash
cd /Volumes/SSD/javis-saas
set -a; source .env; set +a; export PGPASSWORD="$POSTGRES_PASSWORD" PGUSER=postgres
node services/company/scripts/migrate.mjs   # "nothing to apply, already up to date"
node scripts/schema-fingerprint.mjs --check # against dev DBs — MATCH
```

- [ ] **Step 4: No commit** (operational). Record the before/after `schema_migrations` state and `\dn` in the report.

---

## Task 5F: Full `make verify-local` sweep (final gate)

**Files:** whichever the sweep still surfaces — a genuine `legal.*`/`control_plane.*`/`operating.*`/`finance.*` structural gap folds into that plane's `restore_baseline_gaps` migration (all new & unreleased). No test weakening, no `type: ignore`, no `001_*` edit, no secret reuse.

**Interfaces:**
- Consumes: Tasks 1–4, 5A–5E, plus Task 6's doc-link fixes.
- Produces: `make verify-local` green end to end; `make automation-mvp-e2e` 6/6.

- [ ] **Step 1: Run the aggregate gate**

```bash
cd /Volumes/SSD/javis-saas
set -a; source .env; set +a; export PGPASSWORD="$POSTGRES_PASSWORD" PGUSER=postgres
make verify-local 2>&1 | tee /tmp/verify-local.log
```

`verify-local = lint typecheck-py python-test-unit python-test-integration desktop-worker-test knowledge-ingestion-test boundary-check check-docs contract-freeze-check e2e-test e2e-cross-plane-smoke`.

- [ ] **Step 2: For each failure, root-cause before fixing**

Use `superpowers:systematic-debugging`. After Tasks 5A–5E the expected state per sub-target:
- **`lint`, `typecheck-py`, `boundary-check`, `contract-freeze-check`, `desktop-worker-test`** — green (unchanged / fixed by `404920f3`).
- **`python-test-unit`, `knowledge-ingestion-test`** — green with the 5D skips. If a NON-descoped module still fails, that's a new finding — debug it, don't skip it.
- **`python-test-integration`** — green (fixed by `6c2a1513`). If a test drives the AI-compliance HTTP path and needs regulation **content** rows, add the **minimal** seed into a new `services/company/finance-legal/migrations/00X_seed_min_legal_for_tests.up.sql` (separate file — seed is not structure), header naming each test that forced each row.
- **`check-docs`** — Task 6 fixes the 15 pre-existing broken links; if any remain, they belong to Task 6, not here.
- **`e2e-test`** — after 5E reset the dev DB and 5B/5C restored `operating.*`/`finance.*`, the golden path should boot. A remaining missing `<retained-schema>.*` column folds into that plane's `restore_baseline_gaps` migration from `81461673^`.
- **`e2e-cross-plane-smoke`** — after 5A, S2 must reach a real `run.completed` with `runtime_signal_outbox` populated. Other scenarios were already green.

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
- Modify: whichever doc files carry the 15 broken relative links `check-docs` flags (all pre-existing, in `docs/archive/2026-08/`, `docs/architecture/overview/07-*`, `09-*`, and an old `.superpowers/sdd/2026-08-30-*/task-1-report.md`).

**Interfaces:**
- Consumes: git history + the verified state after Tasks 1–5F.
- Produces: an accurate plan doc + `make check-docs` green — no runtime code change.

- [ ] **Step 0: Fix the 15 broken doc links**

```bash
cd /Volumes/SSD/javis-saas
make check-docs 2>&1 | grep -E "broken|->" > /tmp/broken-links.txt
cat /tmp/broken-links.txt
```

For each: the target was `git rm`'d by `81461673` or an earlier cleanup. Fix by (a) repointing to the surviving replacement doc if there is an obvious one, else (b) unlinking — convert `[text](dead-path)` to plain `text` — and, if the sentence only exists to point at the dead file, delete the sentence. Do **not** recreate deleted files. Re-run `make check-docs` → green. Keep these edits in their own commit, separate from the reset-plan reconcile.

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
  Structure only; regulation content seed deferred. (SP-A)
- `services/cosa/migrations/005_restore_baseline_gaps.up.sql`
  — control_plane.document_ingestions + document_ingestion_audit_events. (SP-A)
- `packages/agent/migrations/005_fix_runtime_signal_outbox_sequence.sql`
  — detaches the IDENTITY that migration 004 wrongly attached to
  agent.runtime_signal_outbox.sequence (a caller-supplied natural-key column);
  every enqueue_runtime_signal was failing on a fresh baseline DB. (SP-A Task 5A)
- `services/company/operations/migrations/004_restore_baseline_gaps.up.sql`
  — operating.runtime_source_signals / operating.task_projects (retained R1
  schema). (SP-A Task 5B)
- `services/company/finance-legal/migrations/003_restore_finance_baseline_gaps.up.sql`
  — finance.accounting_fiscal_profiles (retained R1 schema). (SP-A Task 5C)

Deliberately NOT restored (PLANNED, not R1 — reset spec §7.3): schemas
`vault`, `knowledge`, `agent_memory`, `agent_evals`, `agent_artifact`. Their
stale test suites are skipped with a spec reference (SP-A Task 5D), not
re-enabled.

Regression guard: `tests/quality/test_baseline_identity_columns.py` (tracks 6
DB-generated columns after Task 5A corrected the `runtime_signal_outbox.sequence`
entry).
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
