#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

PYTEST_BIN="${PYTEST_BIN:-}"
if [ -z "$PYTEST_BIN" ]; then
  if [ -x "$REPO_ROOT/.venv/bin/pytest" ]; then
    PYTEST_BIN="$REPO_ROOT/.venv/bin/pytest"
  else
    PYTEST_BIN="pytest"
  fi
fi

# Check if targeting external environment (staging / prod smoke)
if [ -n "${E2E_BASE_URL_API:-}" ] || [ -n "${E2E_BASE_URL_COSA:-}" ] || [ -n "${E2E_BASE_URL_COMPANY:-}" ]; then
  echo "🚀 Running E2E Golden Path against external target:"
  echo "   E2E_BASE_URL_API:     ${E2E_BASE_URL_API:-default}"
  echo "   E2E_BASE_URL_COSA:    ${E2E_BASE_URL_COSA:-default}"
  echo "   E2E_BASE_URL_COMPANY: ${E2E_BASE_URL_COMPANY:-default}"
  mkdir -p test-results
  PYTHONPATH=. "$PYTEST_BIN" tests/e2e -m "not cross_plane" -q --junitxml=test-results/e2e.xml "$@"
  exit 0
fi

echo "🚀 Starting E2E Docker Compose stack (--profile e2e)..."
if [ -f .env.e2e ]; then
  set -a
  # shellcheck disable=SC1091
  source .env.e2e
  set +a
fi

# The Docker profile starts Company on the host loopback port. The pytest
# fixture must use that process rather than silently starting a second local
# service or skipping when the Encore CLI is absent on the host.
#
# Ba biến E2E_BASE_URL_* dưới đây là điều kiện chạy `tests/e2e/test_golden_path.py`
# (S1/S4/S7 vs target ngoài). `docker-compose.yml` map: services-company→4000,
# services-cosa→4001, cosa-api→8001 (host 8001 → container 8000).
export E2E_BASE_URL_COMPANY="${E2E_BASE_URL_COMPANY:-http://127.0.0.1:4000}"
export E2E_BASE_URL_COSA="${E2E_BASE_URL_COSA:-http://127.0.0.1:4001}"
export E2E_BASE_URL_API="${E2E_BASE_URL_API:-http://127.0.0.1:8001}"
# `source .env.e2e` (set -a ở trên) đã export AGENT_DATABASE_URL /
# COSA_DATABASE_URL / WORKSPACE_DATABASE_URL — `test_golden_path.py`
# (`ExternalClusterDsns.from_env`) cần chúng cho assert DB của S1/S4/S7.
export E2E_TEST_SEED_ENABLED=1

docker compose --profile e2e up -d --build --wait
trap 'echo "🧹 Tearing down E2E stack..."; docker compose --profile e2e down -v' EXIT

mkdir -p test-results
echo "🧪 Running E2E Golden Path test suite..."
PYTHONPATH=. "$PYTEST_BIN" tests/e2e -m "not cross_plane" -q --junitxml=test-results/e2e.xml "$@"
