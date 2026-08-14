# Worker Heartbeat Design

## Goal

Make development readiness and workspace diagnostics distinguish a running
`agent-worker` from an API stack that merely has healthy Postgres and MinIO.

## Scope

This change adds a runtime-global heartbeat record, writes it from
`backend/app/worker_main.py`, and consumes it from `/ready` and the existing
admin diagnostics endpoint. It does not create tenant data, add client-side
state, or treat a worker heartbeat as proof that a provider API is available.

## Data model and migration

Migration `v13_030_worker_heartbeat` follows
`v13_029_chat_session_purpose`. It creates `runtime_heartbeats` with a
Snowflake `id`, unique component name, and `last_seen_at` timestamp. The
record represents deployment-level runtime state, so it has no workspace or
brain foreign key.

## Worker contract

`agent-worker` starts an asynchronous heartbeat loop alongside its existing
chat and background loops. It upserts the `agent-worker` record immediately,
then every five seconds. A transient database failure is logged and retried;
it must not terminate message processing.

## API contract

`GET /ready` adds `checks.worker`. It reports `ok` only when the worker
heartbeat is no older than 15 seconds; missing, stale, or unreadable state
marks readiness as `not_ready` with HTTP 503. The existing `/live` endpoint
remains process-only and unchanged.

`GET /api/v1/admin/{workspace_id}/diagnostics` uses the same health function:
worker status is `healthy` only for a fresh heartbeat, `degraded` otherwise.
The endpoint retains its workspace authorization and all existing connector
and usage fields.

## Verification

Tests cover heartbeat freshness boundaries, readiness success and stale
failure, diagnostics worker status, worker-loop startup wiring, model
registration for Alembic, and migration metadata. A Compose smoke test checks
that `migrate` exits successfully and `/ready` includes a fresh worker check.

