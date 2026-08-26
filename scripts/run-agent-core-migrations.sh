#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MIGRATIONS_DIR="${REPO_ROOT}/packages/agent_core/migrations"

DATABASE_URL="${AGENT_CORE_DATABASE_URL:-${DATABASE_URL:-postgresql://javis_app:veqsedNwMeuecXLNdMs4WnRQF8YBUZD@127.0.0.1:5432/javis}}"
# Convert asyncpg/sqlalchemy url if needed
PLAIN_URL=$(echo "${DATABASE_URL}" | sed 's/postgresql+asyncpg:\/\//postgresql:\/\//g' | sed 's/@postgres:/@127.0.0.1:/g')

echo "Applying agent_core migrations to ${PLAIN_URL}..."

for sql_file in $(ls "${MIGRATIONS_DIR}"/*.sql | sort); do
    echo "Running migration: $(basename "${sql_file}")..."
    if command -v psql >/dev/null 2>&1; then
        psql "${PLAIN_URL}" -f "${sql_file}" >/dev/null
    elif docker ps --format '{{.Names}}' | grep -q cosa_postgres; then
        docker exec -i cosa_postgres psql -U javis -d javis < "${sql_file}" >/dev/null
    else
        echo "Warning: neither psql nor docker container cosa_postgres available."
    fi
done

echo "All agent_core migrations applied successfully."
