# Rollback Procedure — Pre-Cutover (before Phase 10 legacy deletion)

**CẬP NHẬT 2026-08-25 (sau Phase 10): `legacy/backend` + `legacy/agent_runtime` đã bị XOÁ
HẲN** (người dùng xác nhận không dùng Google OAuth, quyết định xoá thay vì port — xem
`docs/architecture/LEGACY_BACKEND_CAPABILITY_AUDIT_2026-08-25.md` và ADR-012 "Correction #3").
**Scenario 1 dưới đây (revert về legacy services) KHÔNG còn khả thi** — `docker compose
--profile legacy up -d` sẽ fail ngay vì profile/service đó không còn tồn tại trong
`docker-compose.yml`. Rollback thật sự giờ CHỈ còn: `git checkout pre-cutover` (tag local,
tại thời điểm trước khi xoá legacy) hoặc revert từng commit Sub-project cụ thể. Scenario 2-4
(DB rollback, policy override, auth debug) vẫn còn giá trị tham khảo, giữ nguyên bên dưới.

**CẬP NHẬT 2026-08-27 (Task 4): Deploy pipeline tuần tự (sequential)** — `make deploy` 
giờ gọi `deploy-preflight` → `migrate-all` → `deploy-app` theo thứ tự này thay vì song 
song, ngay cả khi dùng `-j`. Xem `docs/operations/migrations.md` phần "Bootstrap và Deploy Flow" 
cho chi tiết.

**Status Date:** 2026-08-25 (viết trước Phase 10; xem cập nhật ở trên)
**Applies to:** State at commit tagged `pre-cutover` (before `legacy/` is deleted)  
**Confidence Level:** MEDIUM with significant known risk factor documented below

---

## Overview

This document describes how to revert to legacy services if the COSA phase deployment encounters critical issues. It is NOT a substitute for automated testing and gradual rollout, but a last-resort reference for operators.

**CRITICAL KNOWN LIMITATION:** The legacy `brain-api` service is currently non-operational due to a pre-existing code fragmentation issue from a 2026-08-22 restructure (runtime error: `ModuleNotFoundError: No module named 'full_main'`). Any rollback plan that assumes "switch back to legacy and it works" is unreliable in the current state.

---

## Pre-Cutover Rollback Scenarios

### Scenario 1: COSA Deployment Breaks at Startup

**If `cosa-api` or `cosa-worker` fail to start during `docker compose --profile cosa up`:**

#### 1.1 Revert docker-compose.yml Changes

```bash
# Check current state
docker ps
docker logs cosa-api  # or cosa-worker
docker logs cosa-api 2>&1 | head -50

# If unrecoverable, revert docker-compose.yml to before Phase 8:
git diff HEAD~1 docker-compose.yml  # Review what changed
git checkout HEAD~1 -- docker-compose.yml

# Redeploy legacy services only
docker compose down  # Stop all COSA services
docker compose --profile legacy up -d  # Start legacy brain-api, agent-worker, etc.
```

#### 1.2 Verify Legacy Services Start

```bash
# Check legacy API responds
curl -s http://localhost:8000/health || echo "brain-api not responding"

# Check logs
docker logs brain-api | tail -20
docker logs agent-worker | tail -20
```

**KNOWN ISSUE — Legacy `brain-api` may not start:**
```
ModuleNotFoundError: No module named 'full_main'
```
If this error appears:
- The legacy code is already broken (not caused by rollback procedure)
- Do NOT attempt to fix it during critical incident (too high risk)
- Instead: proceed to Scenario 2 (database rollback) or escalate to engineering team

---

### Scenario 2: Database Migration Rollback (Task 1 Changes)

**If COSA/Company/Agent-Core database migrations are causing data loss or blocking operations:**

#### 2.1 Backup Current State

```bash
# Before any destructive operation, capture current state
pg_dump -U postgres -h localhost cosa_postgres > /tmp/cosa_postgres_post_phase_1.sql
pg_dump -U postgres -h localhost company_postgres > /tmp/company_postgres_post_phase_1.sql
pg_dump -U postgres -h localhost agent_core_postgres > /tmp/agent_core_postgres_post_phase_1.sql

# Timestamp the backups
ls -lh /tmp/*_postgres_post_phase_1.sql
```

#### 2.2 Identify Migration to Revert

Each Phase 1 migration added new baseline tables; review which one is causing issues:

- **COSA**: `services/cosa/migrations/1_baseline_identity_and_agent_policy.up.sql`
- **Company**: `services/company/identity/migrations/1_baseline_workspace_user_workforce.up.sql`
- **Agent-Core**: `packages/agent_core/migrations/011_run_stream_events.sql` (Phase 5)

#### 2.3 Rollback (If .down.sql Exists)

```bash
# Check if down migration exists
ls -la services/cosa/migrations/*down.sql
ls -la services/company/identity/migrations/*down.sql

# If .down.sql exists, apply it
# (Exact command depends on migration runner; typically:)
node scripts/migrate.mjs --env production --down services/cosa
node scripts/migrate.mjs --env production --down services/company

# For agent-core (Python-based):
python -m packages.agent_core.scripts.migrate --down
```

**If .down.sql does NOT exist:**

Restart services with fresh database:

```bash
# Stop services
docker compose down

# Remove data volume (WARNING: destructive)
docker volume rm javis-saas_cosa_postgres
docker volume rm javis-saas_company_postgres
docker volume rm javis-saas_agent_core_postgres

# Restart with fresh databases
docker compose up -d postgres  # or bring up fresh DBs
# Services will re-run baseline migrations

# Restore legacy data if needed:
psql -U postgres -h localhost cosa_postgres < /path/to/legacy/cosa_backup.sql
```

---

### Scenario 3: Capability/Policy Layer Blocking Production Requests

**If COSA capability gateway or approval policies are blocking legitimate requests:**

#### 3.1 Temporary Policy Override (Emergency Only)

```python
# In apps/cosa/composition/agent_plane.py, if approval-gate is causing false positives:
# TEMPORARILY set all policies to ALLOW (EMERGENCY MEASURE ONLY)

policy_evaluator = lambda cap, payload, ctx: PolicyDecision(
    outcome=PolicyOutcome.ALLOW,
    reasons=("EMERGENCY OVERRIDE — restore original logic immediately")
)

# Restart worker
docker compose restart cosa-worker
```

**CRITICAL:** This is a one-time emergency band-aid only. Restore original policy logic immediately after incident and investigate root cause.

#### 3.2 Revert to Legacy Policy (if available)

Legacy policy configuration is in `legacy/backend/config/policies.yaml` (if it exists). To temporarily use it:

```bash
# Copy legacy policy config
cp legacy/backend/config/policies.yaml apps/cosa/policies/emergency_fallback.yaml

# Reference in code (temporary):
# snapshot = await plane.tenant_policy_client.get_snapshot(...)
# Apply legacy_fallback_policy as override for testing

# Restart
docker compose restart cosa-worker
```

---

### Scenario 4: Tenant Isolation Bypass or Auth Failure

**If authentication or tenant filtering is broken in COSA API:**

#### 4.1 Verify JWT/Identity Layer

```bash
# Check if API is rejecting all requests with 401
curl -v -H "Authorization: Bearer $TOKEN" http://localhost:8001/agent/conversations

# If getting 401 on valid token, check:
# - apps/cosa/auth/cosa_client.py (token validation)
# - apps/cosa/auth/jwt.py (JWT decode logic)
# - apps/cosa/api/routes.py (dependency injection of authenticated identity)

# Temporarily log token contents (DEBUG ONLY)
# In apps/cosa/auth/jwt.py:
# print(f"Token: {token}, Decoded: {decoded}")
```

#### 4.2 Fallback to Anonymous Mode (Testing Only)

```python
# In apps/cosa/api/test_main.py (or main.py for emergency):
# Remove @require_authenticated_identity dependency temporarily

@app.get("/agent/conversations")
async def list_conversations_unsafe():  # TEMPORARY — REMOVE AFTER INCIDENT
    # Return all conversations without auth check
    # This is INSECURE — do not leave deployed
    ...
```

**After incident, immediately restore authentication.**

---

## Database-Level Rollback (Nuclear Option)

**If all else fails, restore from pre-Phase-1 backup:**

```bash
# Assuming you have a pg_dump from before Phase 1 migration:
pg_restore -U postgres -h localhost -d cosa_postgres \
  < /archive/cosa_postgres_pre_phase_1.sql

pg_restore -U postgres -h localhost -d company_postgres \
  < /archive/company_postgres_pre_phase_1.sql

# Restart services
docker compose down
docker compose up -d
```

**Cost:** All data written during COSA phase is lost. Only use if migration irreversibly corrupted data.

---

## Re-Enabling COSA After Rollback

Once legacy is confirmed stable and issue is investigated:

1. **Identify root cause** — did COSA code fail, or was deployment assumption wrong?
2. **Fix in feature branch** — don't push directly to main
3. **Test with fresh COSA deployment** — kill cosa-api/cosa-worker, rebuild images, restart
4. **Gradual traffic shift** — if possible, route portion of traffic to COSA before full cutover
5. **Monitor metrics** — error rate, latency, approval decision distribution

---

## Known Issues & Gaps

| Issue | Risk | Mitigation |
|-------|------|-----------|
| Legacy `brain-api` is currently broken (missing `full_main` module) | HIGH | Do not attempt rollback to legacy API; focus on COSA stability instead. If COSA fails, escalate to engineering team. |
| No automated rollback tests (only manual procedure above) | MEDIUM | Before Phase 10 deletion, run a full rollback simulation in staging. |
| Database `.down.sql` files may not exist for all migrations | MEDIUM | Prepare `pg_dump` backups before deploying. Test restore procedure in staging. |
| Policy override is a band-aid, not a fix | MEDIUM | Use only for immediate stabilization; always restore original logic and investigate root cause. |
| No cross-service rollback coordination (COSA/Company/Agent-Core roll back independently) | MEDIUM | If data consistency depends on all three rolling back together, coordinate restores by timestamp. |

---

## Checklist: Before Phase 10 Deletion

Before `legacy/` is deleted, complete these steps to increase rollback confidence:

- [ ] **Backup:** Create production `pg_dump` backups of cosa/company/agent-core databases (timestamp them)
- [ ] **Test Rollback:** Simulate Scenario 1-4 above in staging environment; document time to recovery
- [ ] **Fix Legacy:** If legacy `brain-api` is needed as fallback, fix the `full_main` import error and test it starts cleanly (estimated effort: 2-4 hours — identify correct module path, update imports, verify Dockerfile/docker-compose integration)
- [ ] **Policy Cache:** Backup current COSA tenant policies (in case rollback to legacy + need policy state)
- [ ] **Circuit Breaker:** Add monitoring/alerting for COSA API error rates; define threshold for auto-rollback (e.g., if error rate > 5% for 5 min)
- [ ] **Document RTO/RPO:** For each scenario, note expected recovery time (RTO) and data loss (RPO)

---

## Contact & Escalation

If rollback does not restore service:

1. Check `docker logs` output of all services (capture full logs)
2. Verify database connectivity: `psql -U postgres -h localhost -l`
3. Review git history: `git log --oneline -20` (confirm what version is deployed)
4. Escalate to engineering team with:
   - Error message from logs
   - Docker ps output (what's running)
   - Database state (did migrations apply)
   - Steps taken so far

---

## Version Control

- **Tag:** `pre-cutover` (local, not pushed yet)
- **Document Updated:** 2026-08-25
- **Next Review:** After Phase 10 deletion (legacy cannot be rolled back to after deletion; this document becomes historical)
