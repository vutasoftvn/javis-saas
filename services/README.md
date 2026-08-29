# COSA Services

This directory contains the TypeScript service applications. Its historic
`company/` source directory now serves the **workspace** business data plane;
the directory name does not change the canonical database name.

## Service boundaries

| Component | Responsibility | Database |
| --- | --- | --- |
| `cosa/` | platform identity, tenants, policy, licensing, connectors | `cosa` |
| `company/identity/` | workspace members, organizations, local identity | `workspace` |
| `company/operations/` | tasks, initiatives, OKRs and planning | `workspace` |
| `company/commercial/` | CRM, customer engagement, sales and marketing | `workspace` |
| `company/finance-legal/` | accounting, finance and legal records | `workspace` |
| `realtime_agent/` | realtime voice agent integration | `workspace` when business data is required |

The separate Python `agent` package owns durable execution state in the `agent`
database. A service may call it through its supported interfaces, but it must not
write Agent tables directly.

## Database configuration

The root compose stack supplies one PostgreSQL cluster with three independent
databases: `agent`, `cosa`, and `workspace`. Configure URLs in the repository
root `.env`:

```text
COSA_DATABASE_URL=...cosa_app.../cosa
COSA_MIGRATOR_DATABASE_URL=...cosa_migrator.../cosa
WORKSPACE_DATABASE_URL=...workspace_app.../workspace
WORKSPACE_MIGRATOR_DATABASE_URL=...workspace_migrator.../workspace
```

Applications use `_app` roles and migrations use `_migrator` roles. Never use a
migrator URL for a long-running service, or commit concrete credentials.

## Local workflow

```bash
cp .env.example .env
# Fill all change-me values in .env.
docker compose up -d postgres
make migrate-all

cd services/cosa && npm run typecheck
cd services/company && npm run typecheck
```

The canonical host port is `127.0.0.1:5432`; Docker services use
`postgres:5432` internally. Run `make dev-preflight` before starting the full
stack and `node scripts/schema-fingerprint.mjs --check` after migrations.

## Native Encore development

The project may still be run with Encore from `services/cosa` or
`services/company`. Provide the same canonical URLs as environment variables;
do not create or depend on legacy `company`, `control_plane`, or per-service
development databases.
