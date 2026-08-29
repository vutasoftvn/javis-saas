#!/usr/bin/env bash
# Initialize the three canonical databases on an already-running PostgreSQL
# cluster. Docker Compose runs the same SQL on first boot; this helper makes
# the exact contract reusable in CI and when repairing an empty dev cluster.
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

: "${PGHOST:?PGHOST is required}"
: "${PGPORT:=5432}"
: "${PGUSER:?PGUSER is required}"
: "${PGDATABASE:=postgres}"
: "${PGPASSWORD:?PGPASSWORD is required}"

export AGENT_APP_PASSWORD="${AGENT_APP_PASSWORD:?AGENT_APP_PASSWORD is required}"
export AGENT_MIGRATOR_PASSWORD="${AGENT_MIGRATOR_PASSWORD:?AGENT_MIGRATOR_PASSWORD is required}"
export COSA_APP_PASSWORD="${COSA_APP_PASSWORD:?COSA_APP_PASSWORD is required}"
export COSA_MIGRATOR_PASSWORD="${COSA_MIGRATOR_PASSWORD:?COSA_MIGRATOR_PASSWORD is required}"
export WORKSPACE_APP_PASSWORD="${WORKSPACE_APP_PASSWORD:?WORKSPACE_APP_PASSWORD is required}"
export WORKSPACE_MIGRATOR_PASSWORD="${WORKSPACE_MIGRATOR_PASSWORD:?WORKSPACE_MIGRATOR_PASSWORD is required}"

exec psql -v ON_ERROR_STOP=1 -f "$repo_root/deploy/postgres/init/01-create-app-roles.sql"
