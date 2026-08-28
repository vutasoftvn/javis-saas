#!/usr/bin/env bash
# check-backup-freshness.sh — dùng bởi `make deploy-preflight` (Part 2E.1).
#
# FAIL nếu:
#   - không đọc được manifest, HOẶC
#   - backup gần nhất > BACKUP_MAX_AGE_HOURS (mặc định 24h), HOẶC
#   - restore-test gần nhất > RESTORE_TEST_MAX_AGE_DAYS (mặc định 30 ngày)
#
# Nguồn manifest (ưu tiên theo thứ tự):
#   1. $BACKUP_MANIFEST_FILE (đường dẫn cục bộ)
#   2. $BACKUP_LOCAL_DIR/manifest.json  (mặc định /var/backups/cosa/manifest.json)
#
# Restore-test timestamp đọc từ $RESTORE_TEST_LOG_FILE (mặc định
# $BACKUP_LOCAL_DIR/last-restore-test.txt) — pg-restore rehearsal ghi ngày
# ISO-8601 vào file này (xem docs/operations/disaster-recovery.md).
#
# Bỏ qua kiểm tra (chỉ khi có lý do vận hành rõ ràng): DEPLOY_BACKUP_CONFIRMED=true
set -euo pipefail

BACKUP_LOCAL_DIR="${BACKUP_LOCAL_DIR:-/var/backups/cosa}"
MANIFEST="${BACKUP_MANIFEST_FILE:-${BACKUP_LOCAL_DIR}/manifest.json}"
RESTORE_LOG="${RESTORE_TEST_LOG_FILE:-${BACKUP_LOCAL_DIR}/last-restore-test.txt}"
MAX_AGE_HOURS="${BACKUP_MAX_AGE_HOURS:-24}"
RESTORE_MAX_AGE_DAYS="${RESTORE_TEST_MAX_AGE_DAYS:-30}"

if [ "${DEPLOY_BACKUP_CONFIRMED:-}" = "true" ]; then
  echo "⚠ DEPLOY_BACKUP_CONFIRMED=true — bỏ qua kiểm tra freshness (override thủ công)"
  exit 0
fi

epoch_now="$(date -u +%s)"

# --- 1. Backup freshness ---
if [ ! -f "$MANIFEST" ]; then
  echo "❌ không tìm thấy backup manifest: $MANIFEST" >&2
  echo "   chạy scripts/backup/pg-backup.sh trước, hoặc set DEPLOY_BACKUP_CONFIRMED=true nếu chủ đích bỏ qua" >&2
  exit 1
fi

last_backup="$(grep -o '"last_backup_utc"[[:space:]]*:[[:space:]]*"[^"]*"' "$MANIFEST" | sed 's/.*"\([^"]*\)"$/\1/')"
if [ -z "$last_backup" ]; then
  echo "❌ manifest không có last_backup_utc: $MANIFEST" >&2; exit 1
fi

# Parse timestamp → epoch. Chấp nhận cả ISO compact (20260828T031500Z) lẫn
# ISO extended (2026-08-28T03:15:00Z). GNU date (Linux/CI) xử lý cả hai qua
# `-d`; BSD date (macOS) cần format tường minh.
to_epoch() {
  local s="$1"
  date -u -d "$s" +%s 2>/dev/null && return 0
  for fmt in "%Y%m%dT%H%M%SZ" "%Y-%m-%dT%H:%M:%SZ" "%Y-%m-%d"; do
    date -u -j -f "$fmt" "$s" +%s 2>/dev/null && return 0
  done
  return 1
}
backup_epoch="$(to_epoch "$last_backup")" || { echo "❌ không parse được timestamp: $last_backup" >&2; exit 1; }
age_hours=$(( (epoch_now - backup_epoch) / 3600 ))

if [ "$age_hours" -gt "$MAX_AGE_HOURS" ]; then
  echo "❌ backup gần nhất $age_hours h trước (> ${MAX_AGE_HOURS}h): $last_backup" >&2
  exit 1
fi
echo "✓ backup gần nhất ${age_hours}h trước ($last_backup)"

# --- 2. Restore-test recency ---
if [ ! -f "$RESTORE_LOG" ]; then
  echo "❌ chưa có bằng chứng restore rehearsal: $RESTORE_LOG" >&2
  echo "   thực hiện restore rehearsal (docs/operations/disaster-recovery.md) và ghi ngày ISO vào file này" >&2
  exit 1
fi
last_restore="$(head -n1 "$RESTORE_LOG" | tr -d '[:space:]')"
restore_epoch="$(to_epoch "$last_restore")" || { echo "❌ không parse được restore-test date: $last_restore" >&2; exit 1; }
restore_age_days=$(( (epoch_now - restore_epoch) / 86400 ))

if [ "$restore_age_days" -gt "$RESTORE_MAX_AGE_DAYS" ]; then
  echo "❌ restore rehearsal gần nhất $restore_age_days ngày trước (> ${RESTORE_MAX_AGE_DAYS}): $last_restore" >&2
  exit 1
fi
echo "✓ restore rehearsal gần nhất ${restore_age_days} ngày trước ($last_restore)"
echo "✓ backup policy: freshness + restore-test recency OK"
