#!/usr/bin/env bash
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$REPO_ROOT/tmp/pids"

echo "Stopping dev services..."
if [ -d "$PID_DIR" ]; then
  for pid_file in "$PID_DIR"/*.pid; do
    if [ -f "$pid_file" ]; then
      pid=$(cat "$pid_file")
      echo "Stopping $(basename "$pid_file" .pid) (PID $pid)..."
      kill -TERM "$pid" 2>/dev/null || true
      rm -f "$pid_file"
    fi
  done
fi

for port in 4000 4001 8000; do
  lsof -ti :$port | xargs kill -9 2>/dev/null || true
done
pkill -f "apps.cosa.worker.main" 2>/dev/null || true

echo "✓ All dev services stopped"
