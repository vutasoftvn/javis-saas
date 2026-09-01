# Worker Readiness Compose Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the production COSA worker container unhealthy when its scheduler, lease store, or polling loop is unhealthy, without exposing a new public port.

**Architecture:** The worker already serves `/live` and `/ready`; production compose will bind that server to loopback and Docker will query `/ready` from inside the container. The image gains `curl` explicitly, and a static deployment test prevents the old process-only healthcheck from returning.

**Tech Stack:** Python 3.11, FastAPI, Uvicorn, Docker Compose, pytest.

**Spec:** `docs/superpowers/specs/2026-09-01-backend-quality-and-encore-guardrails-design.md`

## Global Constraints

- Do not publish a worker health port through Compose `ports`.
- Retain `/live`, `/ready`, and their no-secret response contract.
- `/ready` remains the readiness decision; `pgrep` is not an acceptable production healthcheck.
- Keep the worker container non-root, `no-new-privileges`, and `cap_drop: ALL`.

---

### Task 1: Add a deployment contract test for worker readiness

**Files:**
- Create: `tests/deploy/test_cosa_worker_compose_healthcheck.py`
- Test: `tests/apps/cosa/worker/test_health.py`

**Interfaces:**
- Consumes: `deploy/central_vps/docker-compose.prod.yaml` and the `/ready` behavior from `apps/cosa/worker/health.py`.
- Produces: a regression test that asserts the production worker uses loopback readiness rather than process liveness.

- [ ] **Step 1: Write the failing static compose test.**

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "deploy/central_vps/docker-compose.prod.yaml"

def worker_block() -> str:
    source = COMPOSE.read_text()
    return source.split("  cosa-worker:\n", 1)[1].split("\n  # --------------------------------------------------------------------------", 1)[0]

def test_cosa_worker_healthcheck_queries_loopback_ready_endpoint() -> None:
    block = worker_block()
    assert 'COSA_WORKER_HEALTH_HOST: "127.0.0.1"' in block
    assert 'COSA_WORKER_HEALTH_PORT: "8090"' in block
    assert "curl -fsS http://127.0.0.1:8090/ready" in block
    assert "pgrep -f" not in block
```

- [ ] **Step 2: Run the new test and confirm it fails against the process-only healthcheck.**

Run: `PYTHONPATH=. pytest tests/deploy/test_cosa_worker_compose_healthcheck.py -q`

Expected: FAIL because Compose has no worker health host/port and still contains
`pgrep -f`.

- [ ] **Step 3: Extend readiness unit coverage for the three failure signals.**

Keep or add one test each in `tests/apps/cosa/worker/test_health.py` that gets
HTTP 503 when `last_poll_ts` is missing/stale, scheduler health returns false,
and lease health returns false. Assert the response body only contains
`status`, `app`, `worker_id`, and boolean `checks`, never a URL, DSN or token.

- [ ] **Step 4: Run the health unit tests.**

Run: `PYTHONPATH=. pytest tests/apps/cosa/worker/test_health.py -q`

Expected: PASS.

### Task 2: Make the worker image capable of its declared healthcheck

**Files:**
- Modify: `apps/cosa/Dockerfile.worker:1-8`
- Test: `tests/deploy/test_cosa_worker_compose_healthcheck.py`

**Interfaces:**
- Consumes: `python:3.11-slim` and Docker's `CMD-SHELL` healthcheck execution.
- Produces: a non-root worker image containing `/usr/bin/curl` before the image switches to `USER app`.

- [ ] **Step 1: Add a failing assertion that Compose uses curl.**

The Task 1 test's `curl -fsS` assertion is the failing test for this image
dependency; it documents that the healthcheck executable is required.

- [ ] **Step 2: Install curl in the image before creating/running as `app`.**

```dockerfile
FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*
RUN groupadd -g 1001 app && useradd -u 1001 -g app -m -s /bin/sh app
```

- [ ] **Step 3: Build the worker image.**

Run: `docker build -f apps/cosa/Dockerfile.worker -t cosa-worker-readiness-test .`

Expected: PASS.

- [ ] **Step 4: Verify curl is available without elevating the image user.**

Run: `docker run --rm cosa-worker-readiness-test curl --version`

Expected: exit code `0` and a curl version string.

- [ ] **Step 5: Commit the image dependency.**

```bash
git add apps/cosa/Dockerfile.worker
git commit -m "build(worker): include readiness healthcheck client"
```

### Task 3: Wire Compose to internal `/ready`

**Files:**
- Modify: `deploy/central_vps/docker-compose.prod.yaml:251-278`
- Test: `tests/deploy/test_cosa_worker_compose_healthcheck.py`

**Interfaces:**
- Consumes: `COSA_WORKER_HEALTH_HOST`, `COSA_WORKER_HEALTH_PORT`, and `start_worker_health_server` defaults in `apps/cosa/worker/main.py`.
- Produces: an internal Docker healthcheck that exits non-zero on an HTTP 503 readiness response.

- [ ] **Step 1: Replace the stale comment and process probe with explicit loopback settings.**

```yaml
      COSA_WORKER_HEALTH_HOST: "127.0.0.1"
      COSA_WORKER_HEALTH_PORT: "8090"
    healthcheck:
      test: ["CMD-SHELL", "curl -fsS http://127.0.0.1:8090/ready || exit 1"]
      interval: 20s
      timeout: 5s
      retries: 3
      start_period: 30s
```

Place the two environment values in the existing `cosa-worker.environment` map.
Delete the comment that says the worker does not open HTTP and delete the
`pgrep` healthcheck command. Do not add a `ports:` section.

- [ ] **Step 2: Run the static deployment test.**

Run: `PYTHONPATH=. pytest tests/deploy/test_cosa_worker_compose_healthcheck.py -q`

Expected: PASS.

- [ ] **Step 3: Validate Compose interpolation and syntax with production env.**

Run: `cd deploy/central_vps && docker compose -f docker-compose.prod.yaml --env-file .env.prod config --quiet`

Expected: exit code `0`; do not print `.env.prod` values.

- [ ] **Step 4: Run all worker readiness checks.**

Run: `PYTHONPATH=. pytest tests/apps/cosa/worker/test_health.py tests/deploy/test_cosa_worker_compose_healthcheck.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the compose wiring and test.**

```bash
git add deploy/central_vps/docker-compose.prod.yaml tests/deploy/test_cosa_worker_compose_healthcheck.py \
  tests/apps/cosa/worker/test_health.py
git commit -m "fix(deploy): probe cosa worker readiness"
```

### Task 4: Prove container behavior in an isolated production-like run

**Files:**
- Modify: none.

**Interfaces:**
- Consumes: the built worker image and its Docker health status.
- Produces: evidence that a healthy process is not enough when `/ready` returns HTTP 503.

- [ ] **Step 1: Start the worker with a controlled unhealthy readiness dependency in the disposable test stack.**

Run: `docker compose -f deploy/central_vps/docker-compose.prod.yaml --env-file .env.prod up -d cosa-worker`

Expected: the worker process may start, but Docker marks the container unhealthy
if its scheduler/lease/polling readiness condition fails.

- [ ] **Step 2: Inspect only the health status.**

Run: `docker inspect --format '{{.State.Health.Status}}' cosa_prod_worker`

Expected: `unhealthy` for the controlled failure case, then `healthy` after
dependencies and a polling cycle are restored.

- [ ] **Step 3: Stop only the named disposable worker container after the test.**

Run: `docker compose -f deploy/central_vps/docker-compose.prod.yaml --env-file .env.prod stop cosa-worker`

Expected: the test service stops; no volume or database deletion occurs.
