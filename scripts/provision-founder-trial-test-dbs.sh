#!/usr/bin/env bash
# One-off: create the three disposable Startup Core test databases used ONLY by
# `make test-db-reset`.
#
# Safe to re-run: it drops and recreates the three javis_*_test databases. It
# NEVER touches the real agent / cosa / workspace databases.
#
# Prereq: the dev Postgres cluster is up (docker: cosa_postgres on 127.0.0.1:5432)
# and `.env` holds the real POSTGRES_PASSWORD + *_MIGRATOR_PASSWORD / *_APP_PASSWORD.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
set -a; source .env; set +a

export PGPASSWORD="${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD in .env}"
PSQL=(psql -h 127.0.0.1 -p 5432 -U "${POSTGRES_USER:-postgres}" -v ON_ERROR_STOP=1)

provision() {
  local db="$1" migrator="$2" app="$3"
  echo "→ (re)creating $db  (owner=$migrator)"
  "${PSQL[@]}" -d postgres -c "DROP DATABASE IF EXISTS ${db};"
  "${PSQL[@]}" -d postgres -c "CREATE DATABASE ${db} OWNER ${migrator};"
  "${PSQL[@]}" -d "${db}" -c "GRANT ALL ON DATABASE ${db} TO ${migrator};"
  "${PSQL[@]}" -d "${db}" -c "GRANT CONNECT ON DATABASE ${db} TO ${app};"
  "${PSQL[@]}" -d "${db}" -c "REVOKE CREATE ON SCHEMA public FROM PUBLIC;"
}

provision javis_agent_test     agent_migrator     agent_app
provision javis_cosa_test      cosa_migrator      cosa_app
provision javis_workspace_test workspace_migrator workspace_app

# Agent plane keeps pgvector installed in public (the reset preserves it).
"${PSQL[@]}" -d javis_agent_test -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo
echo "Done. Now add these to .env (or your shell) before 'make test-db-reset':"
cat <<EOF

AGENT_TEST_MIGRATOR_DATABASE_URL=postgresql+asyncpg://agent_migrator:${AGENT_MIGRATOR_PASSWORD}@127.0.0.1:5432/javis_agent_test
AGENT_TEST_DATABASE_URL=postgresql+asyncpg://agent_app:${AGENT_APP_PASSWORD}@127.0.0.1:5432/javis_agent_test
COSA_TEST_MIGRATOR_DATABASE_URL=postgresql://cosa_migrator:${COSA_MIGRATOR_PASSWORD}@127.0.0.1:5432/javis_cosa_test?sslmode=disable
COSA_TEST_DATABASE_URL=postgresql://cosa_app:${COSA_APP_PASSWORD}@127.0.0.1:5432/javis_cosa_test?sslmode=disable
WORKSPACE_TEST_MIGRATOR_DATABASE_URL=postgresql://workspace_migrator:${WORKSPACE_MIGRATOR_PASSWORD}@127.0.0.1:5432/javis_workspace_test?sslmode=disable
WORKSPACE_TEST_DATABASE_URL=postgresql://workspace_app:${WORKSPACE_APP_PASSWORD}@127.0.0.1:5432/javis_workspace_test?sslmode=disable
EOF
