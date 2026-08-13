# Test Reliability Phase 1 Design

## Goal

Make the existing backend and realtime tests reproducible in CI and on a developer machine without allowing test results to depend on development database state.

## Scope

- Keep the backend integration suite on a dedicated Postgres database named `javis_test` in CI.
- Run Alembic upgrade and `alembic check` against that database before integration tests.
- Make the model-registry fallback test independent of persisted workspace secrets.
- Run the realtime-agent suite in GitHub Actions using its own dependency set.
- Publish machine-readable test artifacts: JUnit XML from Python suites and JSON from Flutter's native machine reporter.

## Non-goals

- No runtime/API behaviour changes.
- No changes to the legacy runtime boundary.
- No local development database migration or reset by automation.
- No end-to-end UI, tenant-isolation matrix, or coverage threshold in this phase; those are follow-up phases.

## Architecture

The CI Postgres service is initialized as `javis_test`, so migrations and tests never touch a developer or production database. The backend job runs all schema validation before tests. The model registry test explicitly disables the dynamic workspace-secret lookup, preserving the production lookup while making the test deterministic. The realtime worker remains a separately installed and tested deploy unit.

Because its tool bridge imports backend domain modules directly, the realtime deploy unit declares the backend packages required at import time (`pgvector`, `asyncpg`, and password hashing). Pytest remains a CI-only install.

## Acceptance criteria

1. The model-registry fallback test passes even when the connected database contains an OpenRouter workspace secret.
2. CI runs `alembic upgrade head` and `alembic check` against `javis_test`.
3. CI runs `services/realtime_agent/tests` with `services/realtime_agent/requirements.txt`.
4. Each CI test job writes and uploads a machine-readable result on every outcome.
5. `make migration-check` uses an explicit test URL when supplied and is part of `make verify` only when the caller opts into database integration.
