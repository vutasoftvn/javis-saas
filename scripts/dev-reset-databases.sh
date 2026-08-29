#!/usr/bin/env bash
# Reset only the legacy local PostgreSQL volumes that predate the canonical
# agent/cosa/workspace topology. This is intentionally opt-in: run with
# --apply only after confirming that development data may be discarded.
set -euo pipefail

readonly database_containers=(
  "cosa_postgres"
  "company_db"
  "cosa_db"
)

readonly database_volumes=(
  "javis-saas_postgres_data"
  "company_company_db_data"
  "cosa_central_pgdata"
  "cosa_central_central_pgdata"
)

if [[ "${1:-}" != "--apply" || "$#" -ne 1 ]]; then
  echo "Dry run only. This script stops these database containers:"
  printf '  - %s\n' "${database_containers[@]}"
  echo "It then removes only these PostgreSQL volumes:"
  printf '  - %s\n' "${database_volumes[@]}"
  echo "Re-run as: scripts/dev-reset-databases.sh --apply"
  exit 0
fi

for container in "${database_containers[@]}"; do
  if docker inspect "$container" >/dev/null 2>&1; then
    docker stop "$container" >/dev/null
    echo "Stopped database container: $container"
    docker rm "$container" >/dev/null
    echo "Removed database container: $container"
  fi
done

for volume in "${database_volumes[@]}"; do
  if docker volume inspect "$volume" >/dev/null 2>&1; then
    docker volume rm "$volume" >/dev/null
    echo "Removed database volume: $volume"
  fi
done

echo "Legacy development databases have been reset. Start the canonical cluster with: docker compose up -d postgres"
