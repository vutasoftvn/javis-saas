# COSA OS Engineering Rules

This file is the shared instruction set for Antigravity and other coding
agents. Claude Code receives the equivalent rules from `CLAUDE.md`.

## Runtime boundary - non-negotiable

- `javis/` is the legacy COSA OS reference only. Do not import it, start it,
  proxy to it, copy its runtime state, or make it a production dependency.
- `backend/server/` is also legacy reference code. Do not add features to it
  and do not expose it to Flutter.
- `frontend/` communicates only with `backend/app` through versioned
  `/api/v1` endpoints. It must not contain references to `javis/`,
  `backend/server`, port `8888`, or legacy WebSocket endpoints.
- All migrated state belongs in the COSA OS runtime: Postgres through
  `backend/app/db`, MinIO for objects, and background work through
  `backend/app/worker_main.py`. Do not add SQLite state for new features.

## Migration method

1. Treat legacy code as behavior/reference material, not as a module to reuse.
2. Write a tenant-scoped API contract and test in `backend/app/tests`.
3. Implement the capability in `backend/app` using domain/service boundaries.
4. Change Flutter to call only that API.
5. Add a regression test, then remove the corresponding Flutter legacy client.
6. Confirm `frontend/lib` has no forbidden legacy runtime reference:

       rg -n --glob '!build/**' '(:8888|backend/server|javis/|web_socket_channel)' frontend/lib

## Security and quality

- Enforce `workspace_id` and `brain_id` tenancy server-side on every
  resource access; do not trust client-supplied IDs alone.
- Never commit or print secrets, runtime databases, logs, WAL/SHM files, or
  virtual environments.
- Use test-first development for behavioral changes. Run backend pytest and
  Flutter tests/analyze relevant to changed code before handoff.
- Update `DEPLOYMENT.md` whenever the runtime boundary or startup sequence
  changes.

## Current chat rule

Flutter Chat uses `/api/v1/chat` only. It creates sessions, sends user
messages, and reads replies from `brain-api`; AI adapters must be implemented
inside `backend/app`, never by reconnecting the client to legacy Javis.

## ID generation - Snowflake ID standard

- Always use 64-bit Snowflake ID (`SnowflakeIDMixin` from `app.db.snowflake_model` or `generate_snowflake_id()` / `generate_snowflake_str()` from `app.core.snowflake`) for entity primary keys and identifier generation across new models and features, optimizing B-tree indexing and time-ordered uniqueness.
- When serializing to REST JSON or communicating with Flutter Web/Mobile, serialize Snowflake IDs as strings (`id_str` or `str(id)`) to prevent 64-bit integer precision loss in JavaScript / JSON parsers.

## Git and workspace rules

- **NEVER use git worktree** (`git worktree add`, `.worktrees/`, etc.) under any circumstance. Always work directly in the primary workspace root (`/Volumes/SSD/javis-saas`) and perform commits directly on the target branch (e.g. `main`).

