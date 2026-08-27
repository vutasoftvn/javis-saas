# COSA Operating Handbook (Runbook)

**Purpose:** Definitive sequence for development, testing, and production deployment gates. This document supersedes ad-hoc deployment procedures and must be followed for any release.

**Last Updated:** 2026-08-27 (Task 6: Development & Test Readiness)

---

## Quick Start: Full Development & Test Gate

```bash
# 1. Load environment
cp .env.example .env
export $(grep -v '^#' .env | xargs)

# 2. Run full deterministic gate (must pass before any commit)
make dev-infra       # Start PostgreSQL, MinIO, LiveKit (Docker)
make dev-migrate     # Apply all migrations in order
make dev-preflight   # Validate configuration and service health
make boundary-check  # Tenant isolation verification
make python-test-unit
make python-test-integration
make services-test
make desktop-worker-test
make realtime-agent-test
make frontend-test
make frontend-analyze

# 3. Service health endpoints (no auth required)
curl http://localhost:4000/healthz  # Company Service
curl http://localhost:4001/healthz  # COSA Control Plane
```

---

## Prerequisites

### Required Services
- **Docker & Docker Compose:** 29.6.2+
- **PostgreSQL:** 16+ (via container or native)
- **Node.js:** 20+ LTS
- **Python:** 3.11+
- **Flutter:** 3.5+ (for frontend testing)

### Required Environment Variables

Before running any gate, set these variables in `.env` (or load from secrets manager):

```bash
# Database URLs (use localhost when running app on host; use 'postgres' service name for Docker-internal)
DATABASE_URL=postgresql://javis_app:change-me-javis-app@localhost:5432/javis
CONTROL_PLANE_DATABASE_URL=postgresql://cosa_control_plane_app:change-me-control-plane-app@postgres:5432/cosa_control_plane

# Service URLs (host-reachable from Docker containers)
COSA_CONTROL_PLANE_URL=http://casa-control-plane:4001
COMPANY_SERVICE_URL=http://company-service:4000

# Secrets (required for real runs, optional in test mode)
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_DEFAULT_MODEL=deepseek-chat

# JWT & Authentication
PLATFORM_JWT_SECRET=cosa-super-secret-platform-jwt-key-change-in-prod
WORKER_SERVICE_JWT_SECRET=worker-secret-change-in-prod
COSA_WORKER_SERVICE_TOKEN=worker-token-change-in-prod
```

**Validation:** `make dev-preflight` will fail immediately if any required variable is missing or unreachable.

---

## Deterministic Test Gates (Canonical Order)

Each gate must exit with code 0 before proceeding to the next. Do not run in parallel (`make -j`).

### Gate 1: Infrastructure Ready (`make dev-infra`)

Start all required Docker containers. Must complete successfully before migrations.

**What it does:**
- Starts PostgreSQL 16 (ports 5432 for COSA, 5433 for Company)
- Starts MinIO S3-compatible storage (port 9000/9001)
- Starts LiveKit WebRTC server (port 7880/7885)

**Exit criteria:** All containers running, health check `curl localhost:9400` returns 200 (Encore proxy).

**Rollback:** `make dev-infra-down` or `docker compose down` (preserves volumes).

### Gate 2: Database Migrations (`make dev-migrate`)

Apply schema migrations in strict order: Agent Core → COSA Control Plane → Company Services.

**Order matters:**
1. **Agent Core** (`packages/agent_core/scripts/migrate.mjs`): policy, runs, messages, knowledge, evals schemas.
2. **COSA Control Plane** (`services/cosa/scripts/migrate.mjs`): control plane, identity, worker lease schemas.
3. **Company** (`services/company/scripts/migrate.mjs`): commercial, finance-legal, identity, operations schemas.

**Exit criteria:** All migrations applied, no errors logged. Verify schema fingerprint (currently manual check; see Phase 1 of `docs/implementation/production-runtime-closure.md`).

**Rollback:** 
- **Data loss:** backups required before any production migration. Contact DBA.
- **Dev retry:** `docker volume rm javis-postgres-agent`, `docker volume rm javis-postgres-cosa`, `docker volume rm javis-postgres-company`, then re-run `make dev-infra dev-migrate`.

### Gate 3: Configuration Validation (`make dev-preflight`)

Verify configuration and service health after infrastructure and migrations are complete. **Must run after dev-infra and dev-migrate.**

**What it does:**
- Parses `.env` or environment
- Validates all required variables are set and non-empty
- Attempts health connection to each service URL (COSA, Company, Postgres)
- Checks Docker daemon availability
- Verifies migration state (no stale locks)

**Exit criteria:** All checks pass; health endpoints return 200 (see "Health Endpoints" section below).

**Fail-fast:** Missing any variable → immediate exit 1 (no retry, no defaults).

### Gate 4: Tenant Isolation (`make boundary-check`)

Verify no conversation, run, approval, or event can cross company/workspace scope.

**What it tests:**
- Two separate companies cannot see each other's workspaces.
- Workspace A in Company 1 cannot list/read runs from Workspace B in Company 2.
- Cross-tenant token injection rejected at handler level.
- Event streams are workspace-scoped (no leakage in SSE reconnect).

**Exit criteria:** All tests pass.

### Gate 5-9: Unit, Integration, and Service Tests

Run test suites in any order after Gate 4 completes.

**Gate 5: Agent Core Unit Tests** (`make python-test-unit`)
- Tests deterministic services, scheduling, policy evaluation.
- Does not require live provider (uses mocks).
- Expected: 40+ tests pass.

**Gate 6: Agent Core Integration Tests** (`make python-test-integration`)
- Tests durable queue, message streaming, approval workflows.
- Requires Docker (uses disposable Postgres instance).
- Expected: 30+ tests pass.

**Gate 7: Services Tests** (`make services-test`)
- Runs `encore test` for Company and COSA services.
- Includes newly added health endpoint tests.
- Expected: 181+ tests pass (41 test files).

**Gate 8: Desktop Worker Tests** (`make desktop-worker-test`)
- Tests local capability handlers (git, filesystem, shell with approval).
- Does not require live provider.
- Expected: 19+ tests pass.

**Gate 9: Realtime Agent Tests** (`make realtime-agent-test`)
- Tests voice/realtime agent isolation and event streaming.
- Expected: 15+ tests pass.

### Gate 10-11: Frontend Tests & Analysis

**Gate 10: Frontend Unit & Widget Tests** (`make frontend-test`)
- Flutter analyzer, widget tests, integration test matrix.
- Expected: 130+ tests pass, zero diagnostics.

**Gate 11: Frontend Analyzer** (`make frontend-analyze`)
- Runs Flutter static analyzer for memory leaks, deprecated APIs.
- Expected: zero diagnostics.

---

## Health Endpoints (Unauthenticated)

Two mandatory health endpoints provide readiness signals for load balancers and monitoring systems.

### Endpoint 1: Company Service (`GET /healthz`)

**Location:** `services/company/identity/handlers/health.handler.ts`

**Response (HTTP 200):**
```json
{
  "app": "company",
  "status": "ok",
  "version": "1.0.0"
}
```

**Status codes:**
- `"ok"` — database `SELECT 1` succeeded; service is ready.
- `"error"` — database connection failed; load balancer should skip this instance.

**Security properties:**
- No DSN, hostname, or credentials in response.
- Response body limited to app name, status, version.
- Performs bounded DB connectivity check (single SELECT query, 5s timeout).
- Never returns migrations state, schema version, or internal topology.

### Endpoint 2: COSA Control Plane (`GET /healthz`)

**Location:** `services/cosa/handlers/health.handler.ts`

**Response (HTTP 200):**
```json
{
  "app": "cosa",
  "status": "ok",
  "version": "1.0.0"
}
```

**Same properties as Company Service health endpoint.**

---

## Production Deployment Gate Sequence

For staging/production deployments, follow this sequence without modification:

```bash
# Step 1: Validate before touching production database
make deploy-preflight

# Step 2: Apply database migrations (one-way operation — backup first!)
make migrate-all

# Step 3: Build and restart application instances
make deploy-app

# Or: one-command shortcut (runs all three in sequence)
make deploy
```

**Blocked deploy condition:**
If any health endpoint returns `status: "error"` or is unreachable after startup, deployment must halt. Do not allow traffic until health endpoints return `status: "ok"`.

---

## Rollback Path

### Scenario 1: Database Migration Failed

**Action:** Restore from backup, do not retry same migration.

1. Stop application instances: `make services-docker-down`
2. Restore database backup: (manual via your backup tool — consult DBA)
3. Verify restore: `psql $COSA_DATABASE_URL -c "SELECT COUNT(*) FROM schema_migrations"`
4. Investigate failure in `docs/implementation/production-runtime-closure.md` (Phase 3, Gate F).
5. If migration has a bug, fix in source, create new migration file (do not re-run failed one).

### Scenario 2: Application Health Endpoint Fails

**Action:** Immediate traffic halt, do not proceed to next instances.

1. Check logs: `docker logs cosa-api` or `docker logs company-api`
2. Verify database connectivity: `psql $COSA_DATABASE_URL -c "SELECT 1"`
3. If database is unreachable, restore from backup.
4. If database is reachable but app won't connect, check:
   - `COSA_DATABASE_URL` / `COMPANY_DATABASE_URL` matches running Postgres instance
   - App has permission to access database
   - Firewall/network policy not blocking app→DB connection
5. Restart app instance: `docker restart cosa-api` (or re-run `make deploy-app` for full rebuild).

### Scenario 3: Test Suite Failure After Code Change

**Action:** Revert code change, re-run gates, investigate root cause.

1. `git revert HEAD` (or `git checkout HEAD~1` if not yet committed)
2. Re-run failed gate: `make <gate-name>`
3. If gate still fails: database state may be corrupted; perform restore.
4. If gate passes with reverted code: your change introduced failure — do not merge.

### Scenario 4: Stale Worker Task (Process Crash Recovery)

**Action:** Scheduler sweeper will automatically reclaim stuck tasks.

- Visibility timeout: 5 minutes (configurable in `services/cosa/storage/schema.ts`)
- Sweeper job: runs every 1 minute (cron in `services/cosa/control-plane.cron.ts`)
- Effect: if worker crashes, task status changes from `processing` → `scheduled` after 5 minutes; next available worker picks it up

**Verify:** Check `control_plane.scheduled_tasks` table:
```sql
SELECT id, status, claimed_at, visibility_timeout_at FROM scheduled_tasks 
WHERE visibility_timeout_at < NOW() AND status = 'processing'
LIMIT 1;
-- Should be empty (swept by cron)
```

---

## Test Tiers & Isolation

| Tier | Name | Infrastructure | Provides | Blocked By |
|------|------|-----------------|----------|-----------|
| 1 | Unit (Deterministic) | None | Policy, scheduling, data structures | Code quality |
| 2 | Integration (Postgres) | Docker Postgres | Durable queue, SSE, approval workflows | Database schema |
| 3 | Service (Encore) | Docker Postgres + Encore | API handlers, tenant isolation, health endpoints | Service auth |
| 4 | E2E (Full Stack) | All services + FastAPI + Flutter | End-to-end text/voice flows | Live provider credentials |
| 5 | Conformance (Provider) | All + DeepSeek/OpenAI API | Model correctness, policy evaluation | Authorization & rate limits |

**Live-provider conformance is isolated:** marked with `@pytest.mark.live_provider`, runs only with `DEEPSEEK_API_KEY` in environment. Do not run against shared credentials; use disposable test account per run.

---

## Deployment Topology (Canonical)

```
Host (macOS/Linux/K8s)        Docker Containers / Cloud Services
═══════════════════════════════════════════════════════════════════
Company Service (4000)  ←→    PostgreSQL 5433 (Company DB)
                        ←→    Secrets Manager (COMPANY_DATABASE_URL)

COSA Control Plane      ←→    PostgreSQL 5432 (COSA DB)
(4001)                  ←→    Secrets Manager (COSA_DATABASE_URL)

FastAPI Worker          ←→    PostgreSQL 5432 (Agent Core DB)
(8000)                  ←→    MinIO (9000)
                        ←→    Secrets Manager (AGENT_CORE_DATABASE_URL)

Flutter Frontend        ←→    Company Service (4000)
(macOS/iOS/Android/Web)       COSA Control Plane (4001)
                        ←→    Secrets Manager (Auth tokens, workspace IDs)
```

**Network contract:**
- All database URLs must be host-reachable (no Docker-internal dns if app runs on host).
- All service URLs must be container-reachable (use Docker service DNS if containers cross-talk).
- No localhost fallbacks; explicit configuration for every link.

---

## Observability & Troubleshooting

### Health Check Flow

1. Load balancer or operator: `curl $COMPANY_SERVICE_URL/healthz`
2. Handler (`services/company/identity/handlers/health.handler.ts`):
   - Calls `checkHealth()` service function
   - Service opens DB connection, runs `SELECT 1`
   - Returns `{status: "ok", ...}` or `{status: "error", ...}`
3. If any health endpoint returns error, remove instance from load balancer

### Service Logs

Capture logs during test gate runs:
```bash
# All container logs
docker compose -f services/docker-compose.yml logs -f

# Specific service
docker logs casa-api
docker logs company-api

# Database schema verification (after migrations complete)
psql $COSA_DATABASE_URL -c "\dt public.*"
```

### Common Issues

**Issue:** `make dev-preflight` fails with "database unreachable"
- **Cause:** `COSA_DATABASE_URL` or `COMPANY_DATABASE_URL` points to non-existent host/port
- **Fix:** Update `.env`, verify Docker container is running (`docker ps`)

**Issue:** Migration applies but schema is incomplete
- **Cause:** Migration file has typo or was interrupted
- **Fix:** Check logs for SQL errors; restore backup; verify migration file syntax before re-run

**Issue:** Health endpoint returns error after restart
- **Cause:** Database connection pool exhausted or database restarted but app didn't re-connect
- **Fix:** Restart app: `docker restart cosa-api company-api`; verify database is accepting connections: `psql $COSA_DATABASE_URL -c "SELECT version()"`

---

## Sign-Off & Deployment Approval

Before deploying to production:

- [ ] All test gates (1-11) passed locally against staging database
- [ ] Health endpoints return `status: "ok"` for all instances
- [ ] No sensitive data (API keys, DSNs, credentials) in logs or response bodies
- [ ] Database backup completed
- [ ] Rollback procedure tested (at least data restore path)
- [ ] Stakeholders notified of scheduled maintenance window

**After deployment:**

- [ ] Verify health endpoints again on production instances
- [ ] Monitor application logs for 30 minutes (first-run errors, rate limiting)
- [ ] Check key user flows (text agent request, approval workflow, workspace switching)
- [ ] Confirm monitoring dashboards showing traffic

---

## References

- Architecture: `docs/architecture/COSA_CANONICAL_MASTER_ARCHITECTURE_AND_IMPLEMENTATION_GUIDE_2026-08-23.md`
- Migrations: `docs/operations/migrations.md`
- Runtime Closure: `docs/implementation/production-runtime-closure.md`
- ADRs: `docs/architecture/adr/` (especially `ADR-RUNTIME-002`, `ADR-CONTROLPLANE-001`)
- Original Plan: `COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md`
