#!/usr/bin/env bash
set -euo pipefail

if [ -z "${AGENT_MIGRATOR_DATABASE_URL:-}" ]; then
    echo "AGENT_MIGRATOR_DATABASE_URL is required" >&2
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

exec python3 -m packages.agent.scripts.migrate "$@"
