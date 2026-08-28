#!/usr/bin/env bash

# scripts/load-dev-env.sh
# Standard environment loader for local development and CI preflight.
# Usage:
#   source scripts/load-dev-env.sh
#   or ./scripts/load-dev-env.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

find_env_file() {
    if [ -f "$REPO_ROOT/.env" ]; then
        echo "$REPO_ROOT/.env"
    elif [ -f "$REPO_ROOT/services/.env" ]; then
        echo "$REPO_ROOT/services/.env"
    else
        echo ""
    fi
}

ENV_FILE="$(find_env_file)"

if [ -n "$ENV_FILE" ]; then
    echo "Loading environment from $ENV_FILE..."
    while IFS='=' read -r key value || [ -n "$key" ]; do
        # Ignore comments and empty lines
        [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
        # Strip potential leading/trailing whitespace
        key="$(echo "$key" | xargs)"
        value="$(echo "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
        # Only export if not already set by outer shell
        if [ -z "${!key+x}" ]; then
            export "$key=$value"
        fi
    done < <(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$ENV_FILE")
else
    echo "⚠️ No .env file found at repo root or services/.env" >&2
fi

# Check required database URLs
check_database_urls() {
    local has_error=0
    
    if [ -z "$COSA_DATABASE_URL" ] && [ -z "$CONTROL_PLANE_DATABASE_URL" ]; then
        echo "❌ COSA_DATABASE_URL (or CONTROL_PLANE_DATABASE_URL) is required for local dev" >&2
        has_error=1
    elif [[ "$COSA_DATABASE_URL" =~ USER:PASSWORD ]] || [[ "$CONTROL_PLANE_DATABASE_URL" =~ USER:PASSWORD ]]; then
        echo "⚠️ WARNING: COSA_DATABASE_URL contains placeholder 'USER:PASSWORD'. Please configure valid credentials in .env" >&2
    fi

    if [ -z "$COMPANY_DATABASE_URL" ] && [ -z "$DATABASE_URL" ]; then
        echo "❌ COMPANY_DATABASE_URL (or DATABASE_URL) is required for local dev" >&2
        has_error=1
    elif [[ "$COMPANY_DATABASE_URL" =~ USER:PASSWORD ]]; then
        echo "⚠️ WARNING: COMPANY_DATABASE_URL contains placeholder 'USER:PASSWORD'. Please configure valid credentials in .env" >&2
    fi

    return $has_error
}

check_database_urls
