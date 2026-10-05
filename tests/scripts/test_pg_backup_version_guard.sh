#!/usr/bin/env bash
# Test guard phiên bản pg_dump của scripts/backup/pg-backup.sh bằng stub pg_dump/psql/aws trong PATH.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
STUBS="$WORK/bin"; mkdir -p "$STUBS"

cat > "$STUBS/pg_dump" <<'S'
#!/usr/bin/env bash
if [ "${1:-}" = "--version" ]; then echo "pg_dump (PostgreSQL) ${STUB_CLIENT_VERSION:-18.6}"; exit 0; fi
echo "FAKE-DUMP"
S
cat > "$STUBS/psql" <<'S'
#!/usr/bin/env bash
if [ -n "${STUB_PSQL_FAIL:-}" ]; then exit 2; fi
echo " ${STUB_SERVER_NUM:-180006} "
S
printf '#!/usr/bin/env bash\nexit 0\n' > "$STUBS/aws"
printf '#!/usr/bin/env bash\nshasum -a 256 "$@"\n' > "$STUBS/sha256sum"
chmod +x "$STUBS"/*

fail=0
run_case() {  # name expected_rc expected_substring
  local name="$1" want_rc="$2" want_msg="$3" out rc
  out="$(PATH="$STUBS:$PATH" BACKUP_LOCAL_DIR="$WORK/data" BACKUP_S3_BUCKET=s3://x \
         BACKUP_DATABASES="agent=postgres://u@h/agent" bash "$ROOT/scripts/backup/pg-backup.sh" 2>&1)"; rc=$?
  if [ "$rc" -eq "$want_rc" ] && grep -qF -- "$want_msg" <<<"$out"; then
    echo "PASS: $name (rc=$rc)"
  else
    echo "FAIL: $name (rc=$rc, want $want_rc / '$want_msg')"; echo "$out" | sed 's/^/    /'; fail=1
  fi
}

STUB_CLIENT_VERSION=16.4 STUB_SERVER_NUM=180006 run_case "client 16 vs server 18 bị chặn" 1 "pg_dump 16 older than server 18"
STUB_CLIENT_VERSION=18.6 STUB_SERVER_NUM=180006 run_case "client 18 vs server 18 chạy được" 0 "pg_dump 18 >= server 18 OK"
STUB_CLIENT_VERSION=18.6 STUB_SERVER_NUM=160015 run_case "client 18 vs server 16 chạy được" 0 "pg_dump 18 >= server 16 OK"
STUB_CLIENT_VERSION=18.6 STUB_PSQL_FAIL=1 run_case "không đọc được server version thì fail" 1 "cannot read server version"
exit $fail
