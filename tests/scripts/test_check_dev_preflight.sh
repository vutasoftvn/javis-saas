#!/usr/bin/env bash

# Test suite for scripts/check-dev-preflight.sh
# Verifies that preflight checks fail appropriately when contracts are missing.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PREFLIGHT_SCRIPT="$SCRIPT_DIR/scripts/check-dev-preflight.sh"

# Bảng test: kiểm tra chọn các biến thiếu theo từng trường hợp
test_missing_env_var() {
    local var_name="$1"
    local test_name="test_missing_$var_name"

    echo "Running: $test_name"
    # Xóa tạm thời một biến rồi chạy preflight; phải trả về non-zero
    if env -u "$var_name" bash "$PREFLIGHT_SCRIPT" >/dev/null 2>&1; then
        echo "FAIL: $test_name — expected non-zero exit"
        return 1
    fi
    echo "PASS: $test_name"
}

# Test mỗi required biến một cách độc lập
echo "=== Testing required environment variables ==="
test_missing_env_var "AGENT_CORE_DATABASE_URL"
test_missing_env_var "COSA_DATABASE_URL"
test_missing_env_var "COMPANY_DATABASE_URL"
test_missing_env_var "COSA_CONTROL_PLANE_URL"
test_missing_env_var "COMPANY_SERVICE_URL"
test_missing_env_var "PLATFORM_JWT_SECRET"
test_missing_env_var "WORKER_SERVICE_JWT_SECRET"
test_missing_env_var "COSA_WORKER_SERVICE_TOKEN"

echo "=== Testing with non-listening service URL ==="
# Export valid values for all required vars, but point COSA_CONTROL_PLANE_URL to non-listening endpoint
export AGENT_CORE_DATABASE_URL="postgresql+asyncpg://user:pass@127.0.0.1:5432/db"
export COSA_DATABASE_URL="postgresql://user:pass@127.0.0.1:5432/db"
export COMPANY_DATABASE_URL="postgresql://user:pass@127.0.0.1:5433/db"
export COSA_CONTROL_PLANE_URL="http://127.0.0.1:54321"  # Intentionally non-listening
export COMPANY_SERVICE_URL="http://127.0.0.1:54322"       # Intentionally non-listening
export PLATFORM_JWT_SECRET="test-secret"
export WORKER_SERVICE_JWT_SECRET="test-secret"
export COSA_WORKER_SERVICE_TOKEN="test-token"

if bash "$PREFLIGHT_SCRIPT" >/dev/null 2>&1; then
    echo "FAIL: Expected non-zero exit when services are unreachable"
    exit 1
fi
echo "PASS: Correctly rejected unreachable services"

echo "=== All tests passed ==="
