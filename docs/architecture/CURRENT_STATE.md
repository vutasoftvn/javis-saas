# COSA OS current development state

## Runtime

Flutter communicates exclusively with `backend/app` at versioned `/api/v1` endpoints.
Compose runs Postgres/pgvector, MinIO, `brain-api`, and `agent-worker`. The API serves
HTTP and readiness only; chat, channels, scheduling, chunking, and Zalo QR jobs run in
`agent-worker`.

## State and tenancy

Postgres is created only by Alembic baseline `9a470e50097b_snowflake_runtime_baseline`.
Entity IDs and foreign keys are signed 64-bit Snowflake IDs. APIs serialize IDs as decimal
strings. Each resource access is scoped by authenticated workspace membership; brain IDs
are checked by their owning workspace.

## Supported development capabilities

- Auth, workspaces, brains, vault, chat, tasks, strategy, workflows, outcomes, devices,
  organization, integrations, and marketing through `backend/app`.
- Gmail OAuth and human-approved email flow.
- Zalo personal QR connector for controlled development: it creates a durable job scoped
  to workspace and creator, and is processed by `agent-worker` only.

## Experimental or external-risk capabilities

Personal Zalo automation must not be exposed beyond a controlled development deployment
without a separate legal, security, and account-risk decision. Provider-backed AI features
require their configured provider credentials.

## Developer verification

```bash
make boundary-check
make backend-test
make frontend-test
make frontend-analyze
docker compose down -v
docker compose up --build -d
docker compose exec brain-api alembic upgrade head
curl --fail http://127.0.0.1:8000/ready
```

The frontend legacy boundary must remain clean:

```bash
rg -n --glob '!build/**' '(:8888|backend/server|javis/)' frontend/lib
```

## Superseded material

`javis/`, `backend/server/`, and pre-baseline Alembic revisions are historical reference
only. Older roadmaps describing direct legacy runtime use or API startup DDL are historical
context, not implementation instructions.
