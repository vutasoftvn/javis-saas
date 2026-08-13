# COSA OS Functional Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make COSA OS operate through stable functional capabilities, with a reconciled Postgres schema and no release-labelled public feature vocabulary.

**Architecture:** Establish the Alembic metadata/schema contract first on a clean `javis_test` database. Migrate version-labelled feature flags through a single compatibility registry, then update callers to canonical functional keys. Public API paths remain stable; release wording is removed only from product-facing code and metadata.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, pytest, Flutter/Dart.

**Spec:** `docs/superpowers/specs/2026-08-13-functional-unification-design.md`

## Global Constraints

- Never rewrite existing Alembic revisions or delete production data to resolve drift.
- Use only Postgres, MinIO, and `backend/app/worker_main.py` for runtime state.
- Enforce workspace and brain tenancy server-side.
- Keep frontend communication limited to `/api/v1` on `backend/app`.
- Serialize Snowflake IDs as strings in REST responses.

---

### Task 1: Establish model registry completeness

**Files:**
- Modify: `backend/app/db/base.py`
- Modify: `backend/app/tests/test_migration_metadata.py`

**Interfaces:**
- Consumes: `app.db.base.Base.metadata` used by `backend/alembic/env.py`.
- Produces: one metadata registry containing every ORM table created by live migrations.

- [x] Write subprocess-backed regression assertions for every model module that owns a live table.
- [x] Add missing explicit model imports to `app.db.base`; do not rely on router/main import side effects.
- [x] Run `PYTHONPATH=backend .venv/bin/pytest backend/app/tests/test_migration_metadata.py -q`.

### Task 2: Reconcile schema drift by intent

**Files:**
- Modify: affected ORM modules under `backend/app/modules/`
- Create: one or more forward migrations under `backend/alembic/versions/`
- Modify: focused test files under `backend/app/tests/`

**Interfaces:**
- Consumes: `alembic check` operation list on a fresh `javis_test` schema.
- Produces: no autogenerate operations after `alembic upgrade head`.

- [x] Save the complete `alembic check` operation list as an engineering artifact before editing.
- [x] Classify each operation into model declaration error, missing forward migration, or intentional naming compatibility.
- [x] For each missing intentional change, add a forward migration with a matching regression test; for model errors, correct the declaration and test the intended schema shape.
- [x] Run `TEST_DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/javis_test make migration-check` after each coherent migration group.
- [x] Do not suppress Alembic comparison globally or add a destructive catch-all migration.

### Task 3: Create canonical functional flag registry

**Files:**
- Modify: `backend/app/core/feature_flags.py`
- Modify: flag-gated routers/services under `backend/app/modules/`
- Create: `backend/alembic/versions/<revision>_functional_feature_flags.py`
- Modify: `backend/app/tests/test_feature_flags.py`

**Interfaces:**
- Consumes: existing `is_enabled`, `require_flag`, and persisted `feature_flags` rows.
- Produces: `canonical_flag_key(key: str) -> str` and `LEGACY_FLAG_ALIASES: dict[str, str]`.

- [x] Write tests proving a canonical override wins, a legacy override is read only when canonical is absent, and unrelated keys are unchanged.
- [x] Add canonical flag constants for concrete gated capabilities and aliases for the documented legacy keys.
- [x] Add an idempotent data migration that copies explicit old-key overrides only where no canonical row exists.
- [x] Update each affected router/service to consult a canonical constant; preserve route paths and response schemas.
- [x] Run focused flag/router tests and schema check.

### Task 4: Remove release labels from public capability surfaces

**Files:**
- Modify: affected `backend/app/modules/**/*.py`
- Modify: affected `frontend/lib/**/*.dart`
- Modify: relevant tests under `backend/app/tests/` and `frontend/test/`

**Interfaces:**
- Consumes: canonical capability map from the approved spec.
- Produces: stable functional labels in product copy, client service names, and AI prompts.

- [ ] Build an allowlist for migration IDs, ADR filenames, historical documentation, and domain snapshot fields where version is semantically required.
- [ ] Replace release labels in user-visible strings, prompt identity copy, and public capability names with functional terminology.
- [ ] Keep immutable migration names, regulatory/template/workflow/document version fields, and historical ADR references unchanged.
- [ ] Add static regression checks that forbid V12/V13 labels in product-facing source locations while permitting the allowlist.
- [ ] Run Flutter tests and analyzer plus backend affected tests.

### Task 5: Add the tenant-isolation integration matrix

**Files:**
- Create: `backend/app/tests/test_tenant_isolation_matrix.py`
- Modify: only guards proven unsafe by a failing matrix case.

**Interfaces:**
- Consumes: reconciled `javis_test` schema and existing router/service tenancy guards.
- Produces: two-workspace regression coverage for Chat, Tasks, Realtime, Vault, and Strategy.

- [x] Seed two independent workspace/user/brain graphs in a rollback-only fixture.
- [x] Assert foreign Chat, Tasks, Vault, Strategy and Realtime operations are rejected and create no side effect.
- [x] Run `TEST_DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/javis_test make backend-integration-test` (562 passed).

### Task 6: Full verification and handoff

**Files:**
- Modify: this plan to record completed verification commands.

- [ ] Run `make boundary-check`.
- [ ] Run backend unit, integration, realtime-agent, Flutter test, and Flutter analyze commands.
- [ ] Confirm CI workflow YAML includes schema check, isolated database URL, and all test job artifacts.
- [ ] Record remaining intentionally preserved domain versions in the handoff.
