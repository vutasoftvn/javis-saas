#!/usr/bin/env bash
set -euo pipefail

# Verify Edge Rate Limiting (429 response) against an authorized safe endpoint.
# Non-destructive: sends bounded requests only if explicitly provided target URL.

if [[ -z "${EDGE_VERIFY_URL:-}" ]]; then
  echo "Error: EDGE_VERIFY_URL is required" >&2
  exit 1
fi

AUTH_HEADER=()
if [[ -n "${EDGE_VERIFY_AUTHORIZATION:-}" ]]; then
  AUTH_HEADER=(-H "Authorization: ${EDGE_VERIFY_AUTHORIZATION}")
fi

MAX_REQUESTS=${EDGE_VERIFY_BURST:-50}
OBSERVED_429=0
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "[${TIMESTAMP}] Probing rate limiter on: ${EDGE_VERIFY_URL} (burst count: ${MAX_REQUESTS})"

for ((i=1; i<=MAX_REQUESTS; i++)); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${AUTH_HEADER[@]}" "${EDGE_VERIFY_URL}")
  if [[ "$STATUS" == "429" ]]; then
    OBSERVED_429=1
    echo "[${TIMESTAMP}] Observed HTTP 429 after $i requests"
    break
  fi
done

if [[ "$OBSERVED_429" -eq 1 ]]; then
  echo "[${TIMESTAMP}] SUCCESS: Edge rate limiting verified."
  exit 0
else
  echo "[${TIMESTAMP}] FAILED: Did not observe HTTP 429 within ${MAX_REQUESTS} requests."
  exit 2
fi
