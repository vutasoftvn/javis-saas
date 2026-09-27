#!/bin/bash
# SessionStart hook cho Claude Code on the web: cài dependency để lint/test chạy
# được (review 2026-09-27, G-15). Idempotent; chỉ chạy trong môi trường remote.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$ROOT"
log() { echo "[session-start] $*" >&2; }

# ── Python: 1 venv cho packages/agent + apps/cosa + dev tools ───────────────
if [ ! -x .venv/bin/python ]; then
  log "tạo .venv"
  python3 -m venv .venv
fi
log "pip install (apps/cosa, packages/agent, dev)"
.venv/bin/pip install -q --disable-pip-version-check \
  -r apps/cosa/requirements.txt -r packages/agent/requirements.txt \
  -r requirements-dev.txt pytest pytest-asyncio

# ── Node: 2 app Encore độc lập ──────────────────────────────────────────────
for app in services/company services/cosa; do
  log "npm install ($app)"
  (cd "$app" && npm install --no-audit --no-fund --loglevel=error)
done

# ── Flutter SDK (frontend-test/analyze) ─────────────────────────────────────
FLUTTER_DIR=/opt/flutter-sdk/flutter
if [ ! -x "$FLUTTER_DIR/bin/flutter" ]; then
  log "tải Flutter SDK stable"
  mkdir -p /opt/flutter-sdk
  archive=$(curl -fsS https://storage.googleapis.com/flutter_infra_release/releases/releases_linux.json \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(next(r['archive'] for r in d['releases'] if r['hash']==d['current_release']['stable']))")
  curl -fsS "https://storage.googleapis.com/flutter_infra_release/releases/$archive" | tar -xJ -C /opt/flutter-sdk
  git config --global --add safe.directory '*'
fi
echo "export PATH=\"$FLUTTER_DIR/bin:\$PATH\"" >> "${CLAUDE_ENV_FILE:-/dev/null}"
(cd frontend && "$FLUTTER_DIR/bin/flutter" pub get >/dev/null)

# ── Postgres 16 + pgvector: DB test đã migrate (parity/durability tests) ────
if command -v pg_ctl >/dev/null 2>&1 || [ -x /usr/lib/postgresql/16/bin/pg_ctl ]; then
  if [ ! -f /usr/share/postgresql/16/extension/vector.control ]; then
    log "cài pgvector"
    apt-get install -y -q postgresql-16-pgvector >/dev/null 2>&1 || log "không cài được pgvector (bỏ qua)"
  fi
  PGDATA_DIR=/var/tmp/cosa-pg
  PG_BIN=/usr/lib/postgresql/16/bin
  if [ ! -d "$PGDATA_DIR/data" ]; then
    mkdir -p "$PGDATA_DIR" && chown postgres "$PGDATA_DIR"
    su postgres -c "$PG_BIN/initdb -D $PGDATA_DIR/data -A trust -U postgres >/dev/null"
  fi
  if ! su postgres -c "$PG_BIN/pg_ctl -D $PGDATA_DIR/data status" >/dev/null 2>&1; then
    su postgres -c "$PG_BIN/pg_ctl -D $PGDATA_DIR/data -l $PGDATA_DIR/log -o '-p 55432 -k $PGDATA_DIR' start" >/dev/null
    sleep 2
  fi
  for db in agent_test company_test; do
    psql -q -h 127.0.0.1 -p 55432 -U postgres -tc "SELECT 1 FROM pg_database WHERE datname='$db'" | grep -q 1 \
      || psql -q -h 127.0.0.1 -p 55432 -U postgres -c "CREATE DATABASE $db"
  done
  for role in agent_app agent_migrator workspace_app workspace_migrator cosa_app; do
    psql -q -h 127.0.0.1 -p 55432 -U postgres -tc "SELECT 1 FROM pg_roles WHERE rolname='$role'" | grep -q 1 \
      || psql -q -h 127.0.0.1 -p 55432 -U postgres -c "CREATE ROLE $role LOGIN" >/dev/null
  done
  log "migrate Agent Core + Company vào DB test"
  AGENT_MIGRATOR_DATABASE_URL=postgresql://postgres@127.0.0.1:55432/agent_test \
    PYTHONPATH=. .venv/bin/python -m packages.agent.scripts.migrate >/dev/null 2>&1 \
    || log "migrate agent thất bại (bỏ qua)"
  (cd services/company && WORKSPACE_MIGRATOR_DATABASE_URL=postgresql://postgres@127.0.0.1:55432/company_test \
    node scripts/migrate.mjs >/dev/null 2>&1) || log "migrate company thất bại (bỏ qua)"
  echo 'export AGENT_TEST_DATABASE_URL=postgresql+asyncpg://postgres@127.0.0.1:55432/agent_test' >> "${CLAUDE_ENV_FILE:-/dev/null}"
fi

# ── Encore CLI (services-test-*, e2e): thường bị proxy chặn github.com ─────
if ! command -v encore >/dev/null 2>&1; then
  if curl -fsSL https://encore.dev/install.sh -o /tmp/encore-install.sh 2>/dev/null; then
    bash /tmp/encore-install.sh >/dev/null 2>&1 && \
      echo 'export PATH="$HOME/.encore/bin:$PATH"' >> "${CLAUDE_ENV_FILE:-/dev/null}" || \
      log "cài encore thất bại — services-test-*/e2e-test chỉ chạy trên CI"
  else
    log "không tải được encore (proxy) — services-test-*/e2e-test chỉ chạy trên CI"
  fi
fi

echo 'export PYTHONPATH="."' >> "${CLAUDE_ENV_FILE:-/dev/null}"
log "xong"
