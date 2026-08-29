# Database Architecture & Operations Guide

## Canonical data planes

Development and production use three independent PostgreSQL databases. This is
an ownership boundary, not a split of one shared database into arbitrary
schemas.

| Database | Owner | Holds | Must not hold |
| --- | --- | --- | --- |
| `agent` | Agent runtime | runs, checkpoints, approvals, memory, knowledge, capability state | product/workspace business records |
| `cosa` | COSA control plane | platform identity, tenants, policies, connectors, entitlements | execution state or customer business data |
| `workspace` | Workspace application | identity, operating, commercial, finance, legal, validation records | platform policy or agent runtime state |

`services/company` remains the source-directory name while its database is
`workspace`; it is a gradual codebase rename, not a compatibility database.

## Credentials and permissions

Each plane has two distinct roles:

| Role suffix | Purpose | Permissions |
| --- | --- | --- |
| `_app` | long-running application services | only DML on the plane's migrated schemas |
| `_migrator` | one-shot migration process | owns the database and may perform DDL |

The six required URLs are:

```text
AGENT_DATABASE_URL
AGENT_MIGRATOR_DATABASE_URL
COSA_DATABASE_URL
COSA_MIGRATOR_DATABASE_URL
WORKSPACE_DATABASE_URL
WORKSPACE_MIGRATOR_DATABASE_URL
```

Keep all concrete values in the local `.env` or the deployment secret store.
Do not put connection strings or passwords in documentation, tests, or source
files. Runtime URLs use the `_app` roles; migration commands use only the
corresponding `_migrator` URL.

## Local development

1. Copy `.env.example` to `.env` and replace every `change-me-*` value.
2. Start the canonical cluster with `docker compose up -d postgres`.
3. Apply every plane in dependency-safe order with `make migrate-all`.
4. Verify the schema contract with `node scripts/schema-fingerprint.mjs --check`.

The local PostgreSQL port is exposed only on `127.0.0.1:5432`. Use the relevant
URL from `.env` with a database client; use an `_app` credential for ordinary
inspection and an `_migrator` credential only for schema administration.

## Migration contract

Migration runners are intentionally separate:

```text
packages/agent/scripts/migrate.py          -> AGENT_MIGRATOR_DATABASE_URL
services/cosa/scripts/migrate.mjs          -> COSA_MIGRATOR_DATABASE_URL
services/company/scripts/migrate.mjs       -> WORKSPACE_MIGRATOR_DATABASE_URL
```

They take an advisory lock, record applied migrations, and grant the required
DML privileges to the matching application role. Application code has no DDL
permission.

## Resetting a development cluster

There is an explicit, reviewed reset helper for this early development stage:

```bash
scripts/dev-reset-databases.sh --apply
```

It stops only the retired database containers and removes only their named
database volumes. It never uses Docker-wide prune commands. The command deletes
local database data; after it completes, regenerate or review `.env`, start
`postgres`, and run `make migrate-all`.

## Operational checks

```bash
make dev-preflight
make migrate-all
node scripts/schema-fingerprint.mjs --check
docker compose ps postgres
```

For a deployment, `make deploy` runs preflight, migrations, then application
deployment sequentially. Back up each of `agent`, `cosa`, and `workspace`
independently; restore and validate them independently as well.
