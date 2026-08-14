# Dev Runtime Reliability Design

## Goal

Make a fresh COSA OS development environment boot deterministically and expose
actionable readiness diagnostics to Flutter Web, mobile, and developers.

## Scope

This increment changes deployment orchestration, API cross-origin behavior,
provider configuration signaling, readiness reporting, regression tests, and
the local development runbook. It does not add business-domain features,
persist new client-side state, change legacy runtime boundaries, or expose AI
provider secrets to `brain-api` or Flutter.

## Runtime startup

Docker Compose will have a one-shot `migrate` service that runs `alembic
upgrade head` against Postgres. `brain-api` and `agent-worker` will depend on
its successful completion, in addition to Postgres and MinIO health. A fresh
`docker compose up --build -d` therefore reaches a migrated schema before
either process serves domain routes.

The existing development API command remains reload-enabled. The migration
container is intentionally not reload-enabled and is rerun by Compose when
explicitly recreated after a migration change.

## CORS contract

`brain-api` will install FastAPI `CORSMiddleware`. `CORS_ALLOWED_ORIGINS` is a
comma-separated allowlist; in development its default permits Flutter Web's
local origins. No wildcard origin is used, because authenticated requests use
the Authorization header. Empty/invalid entries are ignored. The response to a
valid preflight contains the configured request origin and permits the standard
HTTP methods and headers used by Flutter.

## Provider configuration boundary

`OPENROUTER_API_KEY` is supplied to `agent-worker` only. `brain-api` receives
only `PROVIDER_CONFIGURED_OPENROUTER=${OPENROUTER_API_KEY:+1}`, matching the
existing no-secret model-picker design. It must never set that configured flag
unconditionally. A model is selectable only when the API flag is set, while
real invocation remains possible only in the worker that owns the key.

## Readiness contract

`GET /ready` retains its existing database and MinIO checks and adds an Alembic
revision check. It returns 503 if the database is not at Alembic head. It does
not claim that an independently running worker is healthy unless a durable
worker heartbeat exists; worker-heartbeat storage is deliberately out of scope
for this increment. Operational worker status remains visible through Compose
and logs.

## Verification

Backend tests cover: allowed CORS preflight; disallowed origin behavior; and
the migration-head readiness failure/success paths without a real database.
Compose configuration is tested as text-level regression where feasible.
Flutter analyzer has zero diagnostics and all Flutter tests pass. The complete
backend suite, boundary check, and a real Compose `/ready` check pass.

## Documentation

`DEPLOYMENT.md` describes the `migrate` service as the canonical boot path,
removes obsolete `create_all()` recovery guidance, and documents the web CORS
environment variable. `.env.example` declares the non-secret CORS setting.

