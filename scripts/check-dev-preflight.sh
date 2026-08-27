#!/usr/bin/env bash

# Preflight check for dev stack configuration.
# Validates required environment variables, Docker Compose configuration,
# service health, and JWT token claims without ever printing the token.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Các biến required (trừ DEEPSEEK_API_KEY có thể omit ở deterministic-test mode)
REQUIRED_VARS=(
    "AGENT_CORE_DATABASE_URL"
    "COSA_DATABASE_URL"
    "COMPANY_DATABASE_URL"
    "COSA_CONTROL_PLANE_URL"
    "COMPANY_SERVICE_URL"
    "PLATFORM_JWT_SECRET"
    "WORKER_SERVICE_JWT_SECRET"
    "COSA_WORKER_SERVICE_TOKEN"
)

# Kiểm tra biến environment bắt buộc
check_required_vars() {
    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            echo "❌ Missing required environment variable: $var" >&2
            return 1
        fi
    done

    # DEEPSEEK_API_KEY bắt buộc ngoại trừ khi ở deterministic-test mode
    if [ -z "$DEEPSEEK_API_KEY" ] && [ "$DETERMINISTIC_TEST_MODE" != "true" ]; then
        echo "❌ Missing required environment variable: DEEPSEEK_API_KEY" >&2
        return 1
    fi

    echo "✓ All required environment variables present"
}

# Kiểm tra Docker Compose files (syntax/integrity)
check_compose_config() {
    if ! docker compose config -q 2>/dev/null; then
        echo "❌ docker-compose.yml configuration invalid" >&2
        return 1
    fi
    echo "✓ docker-compose.yml valid"

    if ! docker compose -f services/docker-compose.yml config -q 2>/dev/null; then
        echo "❌ services/docker-compose.yml configuration invalid" >&2
        return 1
    fi
    echo "✓ services/docker-compose.yml valid"
}

# Kiểm tra HTTP readiness của 1 service
check_http_endpoint() {
    local url="$1"
    local endpoint="$2"
    local service_name="$3"

    local full_url="${url}${endpoint}"

    # Retry logic: 5 attempts với 1 second delay
    for attempt in {1..5}; do
        if curl -fsS "$full_url" >/dev/null 2>&1; then
            echo "✓ $service_name reachable at $url"
            return 0
        fi
        if [ $attempt -lt 5 ]; then
            sleep 1
        fi
    done

    echo "❌ $service_name not reachable at $url" >&2
    return 1
}

# Decode JWT token claims để kiểm tra audience, role, và expiry
# Không bao giờ in ra token.
check_jwt_token() {
    local token="$1"
    local token_name="$2"

    # Giải mã JWT token: Base64 decode phần payload (field 2, cách dấu chấm)
    # JWT format: header.payload.signature
    # Chúng ta chỉ decode payload, không verify signature (chỉ cần check claims cấu trúc)

    if [ -z "$token" ]; then
        echo "❌ Token is empty: $token_name" >&2
        return 1
    fi

    # Split token by dots
    IFS='.' read -r header payload signature <<< "$token"

    if [ -z "$payload" ]; then
        echo "❌ Invalid token format: $token_name" >&2
        return 1
    fi

    # Pad Base64 string if necessary (JWT might omit padding)
    padding=$((${#payload} % 4))
    if [ $padding -ne 0 ]; then
        payload="${payload}$(printf '%*s' $((4 - padding)) | tr ' ' '=')"
    fi

    # Decode payload from Base64
    local payload_json
    if ! payload_json=$(echo "$payload" | base64 -d 2>/dev/null); then
        echo "❌ Token decode failed: $token_name" >&2
        return 1
    fi

    # Kiểm tra các claims cần thiết (không in token, chỉ verify claims exist)
    if ! echo "$payload_json" | grep -q '"aud"' 2>/dev/null; then
        echo "❌ Token missing 'aud' claim: $token_name" >&2
        return 1
    fi

    if ! echo "$payload_json" | grep -q '"role"' 2>/dev/null; then
        echo "❌ Token missing 'role' claim: $token_name" >&2
        return 1
    fi

    if ! echo "$payload_json" | grep -q '"exp"' 2>/dev/null; then
        echo "❌ Token missing 'exp' claim: $token_name" >&2
        return 1
    fi

    echo "✓ $token_name claims valid (aud, role, exp present)"
}

# Main preflight checks
main() {
    echo "Checking development stack configuration..."

    cd "$REPO_ROOT"

    check_required_vars || return 1
    echo ""

    check_compose_config || return 1
    echo ""

    echo "Checking service health endpoints..."
    check_http_endpoint "$COSA_CONTROL_PLANE_URL" "/healthz" "COSA Control Plane" || return 1
    check_http_endpoint "$COMPANY_SERVICE_URL" "/healthz" "Company Service" || return 1
    check_http_endpoint "http://127.0.0.1:8000" "/healthz" "COSA FastAPI" || return 1
    echo ""

    echo "Checking worker service token..."
    check_jwt_token "$COSA_WORKER_SERVICE_TOKEN" "COSA_WORKER_SERVICE_TOKEN" || return 1
    echo ""

    echo "✓ All preflight checks passed"
}

main "$@"
