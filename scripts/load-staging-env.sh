#!/usr/bin/env bash
# scripts/load-staging-env.sh
# Standard environment loader for Staging deployment and preflight verification (Part 1E §1E.4).
# Usage:
#   source scripts/load-staging-env.sh
#   or ./scripts/load-staging-env.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

find_env_file() {
    if [ -f "$REPO_ROOT/.env.staging" ]; then
        echo "$REPO_ROOT/.env.staging"
    elif [ -f "$REPO_ROOT/.env.staging.local" ]; then
        echo "$REPO_ROOT/.env.staging.local"
    elif [ -f "$REPO_ROOT/services/.env.staging" ]; then
        echo "$REPO_ROOT/services/.env.staging"
    else
        echo ""
    fi
}

ENV_FILE="$(find_env_file)"

if [ -n "$ENV_FILE" ]; then
    echo "Loading staging environment from $ENV_FILE..."
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
    echo "ℹ️ No .env.staging file found at repo root. Using existing shell environment variables." >&2
fi

# Check required database URLs and keys
check_staging_env() {
    local has_error=0

    if [ -z "$COSA_DATABASE_URL" ] && [ -z "$CONTROL_PLANE_DATABASE_URL" ]; then
        echo "❌ COSA_DATABASE_URL (or CONTROL_PLANE_DATABASE_URL) is required for staging" >&2
        has_error=1
    elif [[ "$COSA_DATABASE_URL" =~ staging_password ]] || [[ "$CONTROL_PLANE_DATABASE_URL" =~ staging_password ]]; then
        echo "⚠️ WARNING: COSA_DATABASE_URL contains placeholder credentials from example template." >&2
    fi

    if [ -z "$COMPANY_DATABASE_URL" ] && [ -z "$DATABASE_URL" ]; then
        echo "❌ COMPANY_DATABASE_URL (or DATABASE_URL) is required for staging" >&2
        has_error=1
    fi

    if [ -z "$PLATFORM_JWT_SECRET" ]; then
        echo "❌ PLATFORM_JWT_SECRET is required for staging" >&2
        has_error=1
    fi

    if [ -z "$WORKER_SERVICE_JWT_SECRET" ]; then
        echo "❌ WORKER_SERVICE_JWT_SECRET is required for staging" >&2
        has_error=1
    fi

    return $has_error
}

check_staging_env
