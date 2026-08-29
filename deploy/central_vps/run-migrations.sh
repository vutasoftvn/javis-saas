#!/usr/bin/env bash
# One-shot migrate runner cho docker-compose.prod.yaml (Part 2D / Gate G).
#
# Chạy đúng thứ tự: Agent Core → COSA Control Plane → Company, giống hệt
# `make migrate-all` nhưng không cần `make`/venv (chạy trong container
# Dockerfile.migrate có sẵn python3 + node). Exit != 0 nếu bất kỳ bước nào
# lỗi → compose `service_completed_successfully` sẽ chặn app khởi động.
set -euo pipefail

echo "[migrate] Agent Core (python)..."
python3 -m packages.agent.scripts.migrate

echo "[migrate] COSA Control Plane (node)..."
( cd services/cosa && node scripts/migrate.mjs )

echo "[migrate] Company (node)..."
( cd services/company && node scripts/migrate.mjs )

if [ "${MIGRATE_VERIFY_FINGERPRINT:-true}" = "true" ]; then
  echo "[migrate] Schema fingerprint check vs golden..."
  node scripts/schema-fingerprint.mjs --check
fi

echo "[migrate] ✓ hoàn tất"
