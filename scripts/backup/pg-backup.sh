#!/usr/bin/env bash
# ============================================================================
# pg-backup.sh — Backup logic DB của COSA sang object store (Part 2E.1)
# ============================================================================
# Cho từng logical DB: pg_dump -Fc (custom format) → gzip → checksum SHA-256 →
# upload object store → cập nhật manifest. Retention: daily × N_DAILY, weekly
# × N_WEEKLY (chủ nhật). Manifest JSON dùng bởi scripts/backup/check-backup-
# freshness.sh (deploy-preflight).
#
# KHÔNG thay cho WAL archiving / PITR — nếu Postgres prod bật `archive_mode`,
# ghi rõ RPO trong docs/operations/disaster-recovery.md. Nếu chỉ có script
# này: RPO = khoảng cách 2 lần chạy (mặc định 24h).
#
# ENV bắt buộc:
#   BACKUP_DATABASES        vd. "agent=postgres://...  cosa=postgres://... company=postgres://..."
#                           (cặp <name>=<dsn> phân tách bằng khoảng trắng)
#   BACKUP_S3_BUCKET        vd. "s3://cosa-backups"  (dùng aws-cli) HOẶC
#   BACKUP_MC_TARGET        vd. "minio/cosa-backups" (dùng mc)
# ENV tuỳ chọn:
#   BACKUP_LOCAL_DIR        (mặc định /var/backups/cosa)
#   BACKUP_RETENTION_DAILY  (mặc định 14)
#   BACKUP_RETENTION_WEEKLY (mặc định 8)
#   BACKUP_GPG_RECIPIENT    nếu set → mã hoá dump bằng gpg trước upload
# ============================================================================
set -euo pipefail

BACKUP_LOCAL_DIR="${BACKUP_LOCAL_DIR:-/var/backups/cosa}"
RETENTION_DAILY="${BACKUP_RETENTION_DAILY:-14}"
RETENTION_WEEKLY="${BACKUP_RETENTION_WEEKLY:-8}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
DAY_OF_WEEK="$(date -u +%u)"   # 1=Mon .. 7=Sun
TIER="daily"; [ "$DAY_OF_WEEK" = "7" ] && TIER="weekly"
RUN_DIR="${BACKUP_LOCAL_DIR}/${TIER}/${TS}"
MANIFEST="${BACKUP_LOCAL_DIR}/manifest.json"

: "${BACKUP_DATABASES:?BACKUP_DATABASES required (\"name=dsn ...\")}"
if [ -z "${BACKUP_S3_BUCKET:-}" ] && [ -z "${BACKUP_MC_TARGET:-}" ]; then
  echo "❌ cần BACKUP_S3_BUCKET hoặc BACKUP_MC_TARGET" >&2; exit 1
fi

mkdir -p "$RUN_DIR"
echo "[backup] run $TS tier=$TIER dir=$RUN_DIR"

declare -a ENTRIES=()

upload() {  # $1 = local file, $2 = remote relative path
  local src="$1" rel="$2"
  if [ -n "${BACKUP_S3_BUCKET:-}" ]; then
    aws s3 cp "$src" "${BACKUP_S3_BUCKET%/}/${rel}" --only-show-errors
  else
    mc cp "$src" "${BACKUP_MC_TARGET%/}/${rel}"
  fi
}

for pair in $BACKUP_DATABASES; do
  name="${pair%%=*}"; dsn="${pair#*=}"
  out="${RUN_DIR}/${name}.dump.gz"
  echo "[backup] pg_dump ${name}..."
  pg_dump --format=custom --no-owner --no-privileges --dbname="$dsn" | gzip -9 > "$out"

  if [ -n "${BACKUP_GPG_RECIPIENT:-}" ]; then
    gpg --yes --batch --encrypt --recipient "$BACKUP_GPG_RECIPIENT" "$out"
    rm -f "$out"; out="${out}.gpg"
  fi

  sha="$(sha256sum "$out" | awk '{print $1}')"
  size="$(wc -c < "$out")"
  echo "$sha  $(basename "$out")" >> "${RUN_DIR}/SHA256SUMS"
  rel="${TIER}/${TS}/$(basename "$out")"
  upload "$out" "$rel"
  ENTRIES+=("{\"db\":\"${name}\",\"object\":\"${rel}\",\"sha256\":\"${sha}\",\"bytes\":${size}}")
done

upload "${RUN_DIR}/SHA256SUMS" "${TIER}/${TS}/SHA256SUMS"

# ---- Manifest (atomic write) ----
tmp_manifest="$(mktemp)"
cat > "$tmp_manifest" <<JSON
{
  "last_backup_utc": "${TS}",
  "tier": "${TIER}",
  "artifacts": [$(IFS=,; echo "${ENTRIES[*]}")],
  "retention": {"daily": ${RETENTION_DAILY}, "weekly": ${RETENTION_WEEKLY}}
}
JSON
mv "$tmp_manifest" "$MANIFEST"
upload "$MANIFEST" "manifest.json"
echo "[backup] manifest → ${MANIFEST}"

# ---- Retention (local + xoá theo tier) ----
prune() {  # $1 = tier dir, $2 = keep count
  local dir="$1" keep="$2"
  [ -d "$dir" ] || return 0
  ls -1dt "$dir"/*/ 2>/dev/null | tail -n "+$((keep + 1))" | while read -r old; do
    echo "[backup] prune $old"; rm -rf "$old"
  done
}
prune "${BACKUP_LOCAL_DIR}/daily" "$RETENTION_DAILY"
prune "${BACKUP_LOCAL_DIR}/weekly" "$RETENTION_WEEKLY"

echo "[backup] ✓ done ${TS}"
