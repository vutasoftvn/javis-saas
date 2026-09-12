#!/usr/bin/env bash
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

source "$REPO_ROOT/scripts/load-dev-env.sh"

LOG_DIR="$REPO_ROOT/tmp/logs"
PID_DIR="$REPO_ROOT/tmp/pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

# Clean up any stale port bindings / workers
for port in 4000 4001 8000; do
  lsof -ti :$port | xargs kill -9 2>/dev/null || true
done
pkill -f "apps.cosa.worker.main" 2>/dev/null || true

echo "Starting Company Service (Encore, port 4000)..."
(cd "$REPO_ROOT/services/company" && encore run --port=4000 > "$LOG_DIR/company.log" 2>&1) &
echo $! > "$PID_DIR/company.pid"

echo "Starting COSA Control Plane (Encore, port 4001)..."
(cd "$REPO_ROOT/services/cosa" && encore run --port=4001 > "$LOG_DIR/cosa.log" 2>&1) &
echo $! > "$PID_DIR/cosa.pid"

echo "Starting COSA FastAPI (port 8000)..."
(PYTHONPATH="$REPO_ROOT:$REPO_ROOT/packages:$REPO_ROOT/apps" "$REPO_ROOT/.venv/bin/python" -m uvicorn apps.cosa.api.main:app --host 127.0.0.1 --port 8000 > "$LOG_DIR/fastapi.log" 2>&1) &
echo $! > "$PID_DIR/fastapi.pid"

echo "Starting COSA Worker..."
(PYTHONPATH="$REPO_ROOT:$REPO_ROOT/packages:$REPO_ROOT/apps" "$REPO_ROOT/.venv/bin/python" -m apps.cosa.worker.main > "$LOG_DIR/worker.log" 2>&1) &
echo $! > "$PID_DIR/worker.pid"

echo "Waiting for services to become healthy..."
attempt=0
while [ $attempt -lt 60 ]; do
  if curl -fsS http://127.0.0.1:4000/healthz >/dev/null 2>&1 && \
     curl -fsS http://127.0.0.1:4001/healthz >/dev/null 2>&1 && \
     curl -fsS http://127.0.0.1:8000/healthz >/dev/null 2>&1; then
    echo "✓ All services healthy!"
    break
  fi
  attempt=$((attempt + 1))
  sleep 1
done

if [ $attempt -ge 60 ]; then
  echo "✗ Services failed to become healthy within 60 seconds."
  echo "--- company.log (last 20 lines) ---"
  tail -n 20 "$LOG_DIR/company.log"
  echo "--- cosa.log (last 20 lines) ---"
  tail -n 20 "$LOG_DIR/cosa.log"
  echo "--- fastapi.log (last 20 lines) ---"
  tail -n 20 "$LOG_DIR/fastapi.log"
  echo "--- worker.log (last 20 lines) ---"
  tail -n 20 "$LOG_DIR/worker.log"
  exit 1
fi
