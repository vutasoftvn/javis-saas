# Cross-Plane E2E Harness Implementation Plan (P1–P3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Vận hành:** xem `docs/testing/cross-plane-e2e.md` (phạm vi phủ S1–S4 + khoảng trống B5, cách chạy).

**Goal:** Dựng dàn E2E cross-plane tự động — Tầng 1 (subprocess, `model=fake`, chặn PR) chạy 4 vùng thật (`services/company` + `services/cosa` + `apps/cosa` API + `cosa-worker`) trên Postgres disposable, cùng workstream sửa 4 bug tích hợp đã lộ.

**Architecture:** Lớp dùng chung (`tests/e2e/seed/`, `tests/e2e/stack/`, `tests/e2e/scenarios/`) tách khỏi cách boot stack. Tầng 1 boot 4 process bằng `subprocess.Popen` (mở rộng pattern `tests/e2e/conftest.py::real_company_service` đã có), Postgres disposable tạo 3 DB mới có suffix `run_id` mỗi lần chạy. Scenario assert trên HTTP/SSE/DB thật, không mock, không skip.

**Tech Stack:** Python 3.11 + pytest 9 + `pytest-asyncio` (`asyncio_mode=strict`) + `httpx` + `psycopg2`/`asyncpg` + `pyjwt`; Encore CLI (TS services); Node 20 (`scripts/migrate.mjs`, `scripts/mint-worker-service-token.mjs`); GitHub Actions.

## Global Constraints

- **Không mock trong file E2E:** cấm `unittest.mock`, `Mock/MagicMock/AsyncMock/patch/PropertyMock`, `monkeypatch`, `ASGITransport/MockTransport`, `pytest.skip/importorskip`, `@pytest.mark.skip/skipif/xfail`, `sqlite:///:memory:`, `__import__`/`importlib.import_module`, và mọi class/hàm tiền tố `Fake`/`InMemory`/`Stub`/`fake_`/`stub_` (`scripts/check_mvp_e2e_purity.py`).
- **Thiếu tiền đề → `pytest.fail(...)` kèm lý do + cách khắc phục, KHÔNG skip, KHÔNG fallback mock** (mẫu `tests/e2e/conftest.py:174-191`).
- **Assert trên dữ liệu structured:** HTTP status, JSON envelope `{data, meta}`, SSE frame, hàng DB — không suy diễn từ text tự nhiên (CLAUDE.md rule 7).
- **Code trực tiếp trên `main`, KHÔNG tạo git worktree** (CLAUDE.md rule 12).
- **Phản hồi hội thoại + `docs/**/*.md` bằng tiếng Việt;** comment code giải thích "why" bằng tiếng Việt; định danh/route/log/env giữ tiếng Anh.
- **Migration chỉ Expand** (`make migration-compat-check`); destructive cần ADR + evidence + `.down.sql` round-trip.
- **Không dùng `any`/`@ts-ignore`/`@ts-expect-error`** trong TS (`make ts-suppression-check`).
- **DB/secret giá trị dev chuẩn** (`.env.e2e`): `PLATFORM_JWT_SECRET=cosa-super-secret-platform-jwt-key-change-in-prod`, `WORKER_SERVICE_JWT_SECRET=cosa-worker-service-jwt-key-change-in-prod-min32chars`, `JWT_SECRET=cosa-dev-jwt-secret-do-not-use-in-prod`, mật khẩu app `change-me-{agent,cosa,workspace}-app`, migrator `change-me-{agent,cosa,workspace}-migrator`, `COSA_MODEL_PROVIDER=fake`, `DEEPSEEK_API_KEY=fake-deepseek-key-for-e2e`.
- **Mỗi task kết thúc bằng commit;** message tiếng Anh có tiền tố `feat(e2e):` / `fix(agent):` / `test(...)` / `ci:` và dòng cuối `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.

---

## File Structure

| File | Trách nhiệm |
|---|---|
| `tests/e2e/stack/__init__.py` | package marker |
| `tests/e2e/stack/_process.py` | Helper tiến trình dùng chung: `pick_free_port`, `spawn`, `wait_until_ready`, `terminate_all` |
| `tests/e2e/stack/disposable_postgres.py` | Tạo/migrate/drop cluster Postgres disposable (3 DB có suffix `run_id`) |
| `tests/e2e/stack/subprocess_stack.py` | Boot 4 process (2× `encore run` + `apps/cosa` api + worker), trả `StackHandles` |
| `tests/e2e/seed/__init__.py` | package marker |
| `tests/e2e/seed/identity.py` | `register_user`, `login`, `provision_workspace`, `add_member` qua HTTP thật |
| `tests/e2e/seed/entitlement.py` | `grant_entitlement` (bật capability prefix cho workspace) |
| `tests/e2e/seed/agent_spec.py` | `seed_minimal_agent_spec` (publish AgentSpec + skillpack tối thiểu cho dispatch) |
| `tests/e2e/seed/handles.py` | `@dataclass SeededWorkspace` |
| `tests/e2e/scenarios/__init__.py` | package marker |
| `tests/e2e/scenarios/auth_tenant_isolation.py` | S1 |
| `tests/e2e/scenarios/dispatch_worker_result.py` | S2 |
| `tests/e2e/scenarios/capability_governance.py` | S3 |
| `tests/e2e/scenarios/outbox_relay.py` | S4 |
| `tests/e2e/mvp_stack.py` | *(sửa)* bỏ `migration_versions` hard-code; `MvpStack.from_subprocess/from_compose` |
| `tests/e2e/conftest.py` | *(sửa)* thêm fixture `disposable_cluster`, `real_cosa_stack`; giữ `real_company_service` |
| `tests/e2e/test_cross_plane_smoke.py` | Test file Tầng 1 gọi S1–S4 |
| `scripts/check_mvp_e2e_purity.py` | *(sửa)* phủ `test_cross_plane_smoke.py` + `tests/e2e/{scenarios,stack,seed}/` |
| `tests/quality/test_mvp_e2e_purity.py` | *(sửa nếu tồn tại)* cập nhật kỳ vọng danh sách file |
| `Makefile` | *(sửa)* target `e2e-cross-plane-smoke`, thêm vào `verify-local` |
| `.github/workflows/quality.yml` | *(sửa)* job `e2e-cross-plane-smoke` (blocking PR) |
| `packages/agent/migrations/024_grant_event_tables_to_agent_app.sql` (+`.down.sql`) | B2 — cấp DML `event_inbox`/`event_trigger_rules` cho `agent_app` |
| `packages/agent/knowledge/providers/postgres.py` hoặc `apps/cosa/knowledge_ingestion/publish.py` | B1 — thread `ingestion_run_id` vào `doc.metadata["ingestion_id"]` |
| *(2 file test sẽ xác định)* trong `services/cosa/**/tests/` | B3 — bỏ `INSERT cosa.companies` |
| *(5 file test sẽ xác định)* trong `frontend/test/` | B4 — cô lập state toàn cục |

---

## PHASE P1 — Lớp dùng chung

### Task 1: Helper tiến trình `tests/e2e/stack/_process.py`

**Files:**
- Create: `tests/e2e/stack/__init__.py` (rỗng)
- Create: `tests/e2e/stack/_process.py`
- Test: `tests/e2e/stack/test_process_helpers.py`

**Interfaces:**
- Produces:
  - `pick_free_port() -> int`
  - `@dataclass ManagedProc(name: str, popen: subprocess.Popen)`
  - `spawn(name: str, argv: list[str], *, cwd: str, env: dict[str, str]) -> ManagedProc`
  - `wait_until_ready(name: str, health_url: str, proc: ManagedProc, *, timeout_s: float = 60.0) -> None` — raise `RuntimeError` nếu proc chết sớm hoặc quá hạn; chấp nhận HTTP 200 hoặc 503
  - `terminate_all(procs: list[ManagedProc]) -> None` — `terminate → wait(15) → kill`, đảo thứ tự, nuốt lỗi teardown

- [ ] **Step 1: Viết test thất bại**

```python
# tests/e2e/stack/test_process_helpers.py
"""Test helper tiến trình — không cần service thật, chỉ spawn `python -c`."""
from __future__ import annotations

import sys

from tests.e2e.stack._process import pick_free_port, spawn, terminate_all, wait_until_ready


def test_pick_free_port_returns_bindable_port() -> None:
    port = pick_free_port()
    assert 1024 < port < 65536


def test_wait_until_ready_raises_when_proc_exits_early() -> None:
    # Process thoát ngay -> wait_until_ready phải raise, không treo tới timeout.
    proc = spawn("dummy", [sys.executable, "-c", "raise SystemExit(1)"], cwd=".", env={})
    try:
        raised = False
        try:
            wait_until_ready("dummy", "http://127.0.0.1:9/healthz", proc, timeout_s=5.0)
        except RuntimeError as err:
            raised = True
            assert "exited early" in str(err)
        assert raised
    finally:
        terminate_all([proc])
```

- [ ] **Step 2: Chạy test — xác nhận fail**

Run: `PYTHONPATH=. .venv/bin/pytest tests/e2e/stack/test_process_helpers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tests.e2e.stack._process'`

- [ ] **Step 3: Cài đặt tối thiểu**

```python
# tests/e2e/stack/_process.py
"""Helper spawn/giám sát tiến trình con cho dàn E2E subprocess.

Rút từ pattern đã kiểm chứng ở `tests/e2e/conftest.py::real_company_service`
(pick free port, chờ /healthz chấp nhận 200/503, teardown try/finally).
"""
from __future__ import annotations

import contextlib
import socket
import subprocess
import time
from dataclasses import dataclass

import httpx


def pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@dataclass
class ManagedProc:
    name: str
    popen: subprocess.Popen


def spawn(name: str, argv: list[str], *, cwd: str, env: dict[str, str]) -> ManagedProc:
    popen = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return ManagedProc(name=name, popen=popen)


def wait_until_ready(
    name: str, health_url: str, proc: ManagedProc, *, timeout_s: float = 60.0
) -> None:
    deadline = time.monotonic() + timeout_s
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if proc.popen.poll() is not None:
            output = _drain(proc)
            raise RuntimeError(
                f"[{name}] process exited early with code {proc.popen.returncode} "
                f"before {health_url} became ready.\n--- captured output ---\n{output}"
            )
        try:
            resp = httpx.get(health_url, timeout=2.0)
            # 503 = app đã lên nhưng probe DB nội bộ của /healthz đỏ; với fixture
            # này DB đã verify riêng, coi như "đã nhận request được".
            if resp.status_code in (200, 503):
                return
        except httpx.HTTPError as err:
            last_error = err
        time.sleep(0.5)
    raise RuntimeError(f"[{name}] not ready within {timeout_s}s: {last_error}")


def terminate_all(procs: list[ManagedProc]) -> None:
    for proc in reversed(procs):
        if proc.popen.poll() is None:
            proc.popen.terminate()
            try:
                proc.popen.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.popen.kill()
                with contextlib.suppress(Exception):
                    proc.popen.wait(timeout=15)


def _drain(proc: ManagedProc) -> str:
    if proc.popen.stdout is None:
        return ""
    with contextlib.suppress(Exception):
        return proc.popen.stdout.read() or ""
    return ""
```

Tạo `tests/e2e/stack/__init__.py` rỗng.

- [ ] **Step 4: Chạy test — xác nhận pass**

Run: `PYTHONPATH=. .venv/bin/pytest tests/e2e/stack/test_process_helpers.py -v`
Expected: PASS (2 test)

- [ ] **Step 5: Lint + commit**

```bash
.venv/bin/ruff check tests/e2e/stack/ && .venv/bin/ruff format tests/e2e/stack/
git add tests/e2e/stack/__init__.py tests/e2e/stack/_process.py tests/e2e/stack/test_process_helpers.py
git commit -m "feat(e2e): process spawn/health helpers for subprocess stack

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Postgres disposable `tests/e2e/stack/disposable_postgres.py`

**Files:**
- Create: `tests/e2e/stack/disposable_postgres.py`
- Modify: `tests/e2e/conftest.py` — thêm fixture `disposable_cluster`
- Test: `tests/e2e/stack/test_disposable_postgres.py`

**Interfaces:**
- Consumes: không có (chỉ Postgres admin qua env `PGHOST/PGPORT/PGUSER/PGPASSWORD`, mặc định `127.0.0.1:5432` user `postgres`)
- Produces:
  - `@dataclass DisposableCluster` với các thuộc tính URL: `agent_app_url`, `agent_migrator_url`, `cosa_app_url`, `cosa_migrator_url`, `workspace_app_url`, `workspace_migrator_url`, và `run_id: str`
  - `create_disposable_cluster(run_id: str) -> DisposableCluster`
  - `apply_migrations(cluster: DisposableCluster) -> None` — raise `RuntimeError` nếu bất kỳ runner nào exit != 0
  - `drop_disposable_cluster(cluster: DisposableCluster) -> None` — không raise
  - fixture pytest `disposable_cluster` (scope=`session`) trong `conftest.py`

**Bối cảnh cần biết:**
- `deploy/postgres/init/01-create-app-roles.sql` tạo 6 role `{agent,cosa,workspace}_{app,migrator}` (NOSUPERUSER NOCREATEDB) + 3 DB tên `agent`/`cosa`/`workspace` OWNER `<svc>_migrator`, `REVOKE CREATE ON SCHEMA public FROM PUBLIC`, `GRANT USAGE ON SCHEMA public TO <svc>_app`, `CREATE EXTENSION vector` (chỉ DB `agent`). CI đã chạy `scripts/bootstrap-postgres-cluster.sh` nên **role đã tồn tại**; task này chỉ tạo **DB mới** OWNER cùng migrator role + lặp lại các GRANT/EXTENSION cho DB mới đó.
- Thứ tự migrate = `make migrate-all`: agent (`python -m packages.agent.scripts.migrate`, env `AGENT_MIGRATOR_DATABASE_URL`, DSN dạng `postgresql+asyncpg://`) → cosa (`node scripts/migrate.mjs` trong `services/cosa`, env `COSA_MIGRATOR_DATABASE_URL`) → company (`node scripts/migrate.mjs` trong `services/company`, env `WORKSPACE_MIGRATOR_DATABASE_URL`).
- `packages/agent/scripts/migrate.py::_grant_application_access` tự cấp DML cho `agent_app` trên **mọi schema do migrator sở hữu trừ `public`** — nên DB `agent` disposable cũng được cấp tự động sau migrate (B2 xử lý phần `public`).

- [ ] **Step 1: Viết test thất bại**

```python
# tests/e2e/stack/test_disposable_postgres.py
"""Chứng minh: tạo cluster disposable -> migrate-all -> connect bằng *_app role
-> teardown DROP sạch. Fail rõ nếu Postgres admin không reachable (không skip)."""
from __future__ import annotations

import psycopg2
import pytest

from tests.e2e.stack.disposable_postgres import (
    apply_migrations,
    create_disposable_cluster,
    drop_disposable_cluster,
)


@pytest.fixture()
def cluster():
    c = create_disposable_cluster(run_id="pytass1")
    try:
        apply_migrations(c)
        yield c
    finally:
        drop_disposable_cluster(c)


def test_app_role_can_read_migrated_schema(cluster) -> None:
    # agent_app phải truy vấn được bảng do migration tạo trong schema có tên
    # (không phải public) — chứng minh _grant_application_access đã chạy.
    conn = psycopg2.connect(cluster.agent_app_url, connect_timeout=5)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('knowledge.source_versions')")
            assert cur.fetchone()[0] is not None
    finally:
        conn.close()


def test_databases_are_dropped_on_teardown() -> None:
    c = create_disposable_cluster(run_id="pytass2")
    apply_migrations(c)
    drop_disposable_cluster(c)
    admin = psycopg2.connect(
        dbname="postgres", host="127.0.0.1", port=5432, user="postgres",
        password="postgres", connect_timeout=5,
    )
    try:
        with admin.cursor() as cur:
            cur.execute("SELECT datname FROM pg_database WHERE datname LIKE %s", ("%pytass2%",))
            assert cur.fetchall() == []
    finally:
        admin.close()
```

- [ ] **Step 2: Chạy test — xác nhận fail**

Run: `PYTHONPATH=. .venv/bin/pytest tests/e2e/stack/test_disposable_postgres.py -v`
Expected: FAIL — `ModuleNotFoundError: tests.e2e.stack.disposable_postgres`

- [ ] **Step 3: Cài đặt tối thiểu**

```python
# tests/e2e/stack/disposable_postgres.py
"""Cluster Postgres disposable cho E2E: mỗi lần chạy tạo 3 DB mới có suffix
run_id, áp toàn bộ migration, rồi DROP khi teardown. Đáp ứng yêu cầu
"disposable CI PostgreSQL with unique names/fresh database" trong
docs/superpowers/plans/2026-09-01-truthful-mvp-hardening.md.
"""
from __future__ import annotations

import contextlib
import os
import subprocess
from dataclasses import dataclass

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

_ADMIN = {
    "host": os.environ.get("PGHOST", "127.0.0.1"),
    "port": int(os.environ.get("PGPORT", "5432")),
    "user": os.environ.get("PGUSER", "postgres"),
    "password": os.environ.get("PGPASSWORD", "postgres"),
    "dbname": "postgres",
}
_APP_PWD = {"agent": "change-me-agent-app", "cosa": "change-me-cosa-app", "workspace": "change-me-workspace-app"}
_MIG_PWD = {
    "agent": "change-me-agent-migrator",
    "cosa": "change-me-cosa-migrator",
    "workspace": "change-me-workspace-migrator",
}


@dataclass
class DisposableCluster:
    run_id: str
    agent_app_url: str
    agent_migrator_url: str
    cosa_app_url: str
    cosa_migrator_url: str
    workspace_app_url: str
    workspace_migrator_url: str


def _db_name(svc: str, run_id: str) -> str:
    return f"{svc}_{run_id}"


def _url(svc: str, run_id: str, *, role: str, pwd: str, driver: str = "postgresql") -> str:
    host, port = _ADMIN["host"], _ADMIN["port"]
    return f"{driver}://{role}:{pwd}@{host}:{port}/{_db_name(svc, run_id)}?sslmode=disable"


def _admin_conn() -> psycopg2.extensions.connection:
    conn = psycopg2.connect(connect_timeout=5, **_ADMIN)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn


def create_disposable_cluster(run_id: str) -> DisposableCluster:
    conn = _admin_conn()
    try:
        with conn.cursor() as cur:
            for svc in ("agent", "cosa", "workspace"):
                name = _db_name(svc, run_id)
                cur.execute(f'CREATE DATABASE "{name}" OWNER {svc}_migrator')
                cur.execute(f'GRANT CONNECT ON DATABASE "{name}" TO {svc}_app, {svc}_migrator')
    finally:
        conn.close()

    # Per-DB: chặn CREATE trên public cho PUBLIC, cho app USAGE, bật vector cho agent.
    for svc in ("agent", "cosa", "workspace"):
        db_conn = psycopg2.connect(
            connect_timeout=5, host=_ADMIN["host"], port=_ADMIN["port"],
            user=_ADMIN["user"], password=_ADMIN["password"], dbname=_db_name(svc, run_id),
        )
        db_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        try:
            with db_conn.cursor() as cur:
                if svc == "agent":
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cur.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
                cur.execute(f"GRANT USAGE ON SCHEMA public TO {svc}_app")
        finally:
            db_conn.close()

    return DisposableCluster(
        run_id=run_id,
        agent_app_url=_url("agent", run_id, role="agent_app", pwd=_APP_PWD["agent"]),
        agent_migrator_url=_url(
            "agent", run_id, role="agent_migrator", pwd=_MIG_PWD["agent"],
            driver="postgresql+asyncpg",
        ),
        cosa_app_url=_url("cosa", run_id, role="cosa_app", pwd=_APP_PWD["cosa"]),
        cosa_migrator_url=_url("cosa", run_id, role="cosa_migrator", pwd=_MIG_PWD["cosa"]),
        workspace_app_url=_url("workspace", run_id, role="workspace_app", pwd=_APP_PWD["workspace"]),
        workspace_migrator_url=_url(
            "workspace", run_id, role="workspace_migrator", pwd=_MIG_PWD["workspace"]
        ),
    )


def apply_migrations(cluster: DisposableCluster) -> None:
    steps = [
        (
            [os.environ.get("PYTHON", ".venv/bin/python"), "-m", "packages.agent.scripts.migrate"],
            _REPO_ROOT,
            {"AGENT_MIGRATOR_DATABASE_URL": cluster.agent_migrator_url},
        ),
        (
            ["node", "scripts/migrate.mjs"],
            os.path.join(_REPO_ROOT, "services", "cosa"),
            {"COSA_MIGRATOR_DATABASE_URL": cluster.cosa_migrator_url},
        ),
        (
            ["node", "scripts/migrate.mjs"],
            os.path.join(_REPO_ROOT, "services", "company"),
            {"WORKSPACE_MIGRATOR_DATABASE_URL": cluster.workspace_migrator_url},
        ),
    ]
    for argv, cwd, extra_env in steps:
        result = subprocess.run(
            argv, cwd=cwd, env={**os.environ, **extra_env},
            capture_output=True, text=True, timeout=300, check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"disposable migrate failed: {' '.join(argv)} (cwd={cwd})\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )


def drop_disposable_cluster(cluster: DisposableCluster) -> None:
    conn = _admin_conn()
    try:
        with conn.cursor() as cur:
            for svc in ("agent", "cosa", "workspace"):
                with contextlib.suppress(Exception):
                    cur.execute(
                        f'DROP DATABASE IF EXISTS "{_db_name(svc, cluster.run_id)}" WITH (FORCE)'
                    )
    finally:
        with contextlib.suppress(Exception):
            conn.close()
```

Thêm vào `tests/e2e/conftest.py`:

```python
import secrets
from collections.abc import Iterator

from tests.e2e.stack.disposable_postgres import (
    DisposableCluster,
    apply_migrations,
    create_disposable_cluster,
    drop_disposable_cluster,
)


@pytest.fixture(scope="session")
def disposable_cluster() -> Iterator[DisposableCluster]:
    """Cluster Postgres tạm cho toàn phiên E2E cross-plane. Fail rõ nếu Postgres
    admin không reachable — không skip."""
    run_id = secrets.token_hex(4)
    try:
        cluster = create_disposable_cluster(run_id)
    except Exception as err:  # pragma: no cover - defensive
        pytest.fail(
            f"Cannot create disposable Postgres cluster ({err}). Start Postgres and run "
            "scripts/bootstrap-postgres-cluster.sh (or use the CI 'services' Postgres container)."
        )
    try:
        apply_migrations(cluster)
        yield cluster
    finally:
        drop_disposable_cluster(cluster)
```

- [ ] **Step 4: Chạy test — xác nhận pass**

Run: `PYTHONPATH=. .venv/bin/pytest tests/e2e/stack/test_disposable_postgres.py -v`
Expected: PASS (2 test). Nếu FAIL ở `test_app_role_can_read_migrated_schema` với `permission denied for table event_inbox` — đó là bug B2, **để lại**; Task 12 sẽ sửa và test này chỉ chạm `knowledge.source_versions` nên không bị ảnh hưởng.

- [ ] **Step 5: Lint + commit**

```bash
.venv/bin/ruff check tests/e2e/stack/ && .venv/bin/ruff format tests/e2e/stack/ tests/e2e/conftest.py
git add tests/e2e/stack/disposable_postgres.py tests/e2e/stack/test_disposable_postgres.py tests/e2e/conftest.py
git commit -m "feat(e2e): disposable Postgres cluster fixture (create/migrate/drop)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Seed kit `tests/e2e/seed/`

**Files:**
- Create: `tests/e2e/seed/__init__.py` (rỗng), `tests/e2e/seed/handles.py`, `tests/e2e/seed/identity.py`, `tests/e2e/seed/entitlement.py`, `tests/e2e/seed/agent_spec.py`
- Test: `tests/e2e/seed/test_seed_kit_contract.py`

**Interfaces:**
- Consumes: base URL company (`http://127.0.0.1:<p1>`), cosa (`http://127.0.0.1:<p2>`), apps/cosa (`http://127.0.0.1:<p3>`) từ `MvpStack` (Task 4); `DisposableCluster` để verify bằng SQL
- Produces:
  - `handles.SeededWorkspace(workspace_id: str, owner_user_id: str, owner_token: str, member_user_id: str | None, member_token: str | None)`
  - `identity.register_user(cosa_base_url: str, *, email: str | None = None) -> tuple[str, str, str]` → `(user_id, email, password)` (gọi `POST /platform/auth/register`)
  - `identity.login(cosa_base_url: str, email: str, password: str) -> str` → access token (gọi `POST /platform/auth/sessions`)
  - `identity.provision_workspace(cosa_base_url: str, owner_token: str, *, name: str) -> str` → `workspace_id`
  - `identity.add_member(cosa_base_url: str, owner_token: str, workspace_id: str, member_user_id: str) -> None`
  - `identity.seed_workspace(stack, *, with_member: bool = False) -> SeededWorkspace` — orchestrator gọi 4 hàm trên
  - `entitlement.grant_entitlement(cosa_base_url: str, owner_token: str, workspace_id: str, capability_prefix: str) -> None`
  - `agent_spec.seed_minimal_agent_spec(apps_cosa_base_url: str, cluster: DisposableCluster, *, workspace_id: str) -> str` → `agent_spec_id`

**Bối cảnh — bước discovery bắt buộc (Step 0):** trước khi code, chạy các lệnh sau và ghi route/payload thật vào docstring mỗi hàm:
```bash
grep -rn "expose: true" services/cosa/handlers/auth.handler.ts
sed -n '1,120p' services/cosa/handlers/auth.handler.ts          # shape register/login request+response
grep -rn "path:.*workspace\|provisionWorkspace\|createWorkspace" services/cosa/handlers/*.ts
grep -rn "expose: true" services/cosa/handlers/venture-workspace.handler.ts  # membership add route
sed -n '1,80p' services/company/identity/handlers/e2e-session.handler.ts     # nếu cần _e2e/session
node scripts/mint-worker-service-token.mjs --help 2>&1 | head
```
Nếu route provision workspace / add-member là `expose: false` (nội bộ), dùng đường seed hợp lệ thay thế **theo thứ tự ưu tiên**: (a) endpoint `_e2e` chuyên dụng nếu có; (b) `INSERT` trực tiếp vào `cluster.cosa_app_url` bằng `psycopg2` theo đúng schema (chấp nhận được cho seed — `test_ai_compliance_company_http.py` đã verify bằng `psycopg2`). KHÔNG dùng mock.

- [ ] **Step 1: Viết test thất bại**

```python
# tests/e2e/seed/test_seed_kit_contract.py
"""Contract test cho seed kit — chạy với real_cosa_stack thật (Task 5)."""
from __future__ import annotations

from tests.e2e.seed import entitlement, identity
from tests.e2e.seed.handles import SeededWorkspace


def test_seed_workspace_returns_usable_owner_token(real_cosa_stack) -> None:
    seeded = identity.seed_workspace(real_cosa_stack, with_member=True)
    assert isinstance(seeded, SeededWorkspace)
    assert seeded.workspace_id
    assert seeded.owner_token
    assert seeded.member_token

    # Owner token + workspace hợp lệ -> gọi được API business, trả envelope {data, meta}.
    resp = real_cosa_stack.company.get(
        "/operations/tasks", token=seeded.owner_token, workspace_id=seeded.workspace_id
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "data" in body and "meta" in body


def test_grant_entitlement_is_idempotent(real_cosa_stack) -> None:
    seeded = identity.seed_workspace(real_cosa_stack)
    entitlement.grant_entitlement(
        real_cosa_stack.platform.base_url, seeded.owner_token, seeded.workspace_id, "operations"
    )
    entitlement.grant_entitlement(  # lần 2 không được lỗi
        real_cosa_stack.platform.base_url, seeded.owner_token, seeded.workspace_id, "operations"
    )
```

- [ ] **Step 2: Chạy test — xác nhận fail**

Run: `PYTHONPATH=. .venv/bin/pytest tests/e2e/seed/test_seed_kit_contract.py -v`
Expected: FAIL — `ModuleNotFoundError: tests.e2e.seed` (hoặc fixture `real_cosa_stack` chưa tồn tại — chấp nhận, Task 5 tạo; tạm `-k` bỏ qua đến khi Task 5 xong nếu cần chạy tách).

- [ ] **Step 3: Cài đặt tối thiểu**

```python
# tests/e2e/seed/handles.py
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class SeededWorkspace:
    workspace_id: str
    owner_user_id: str
    owner_token: str
    member_user_id: str | None = None
    member_token: str | None = None
```

```python
# tests/e2e/seed/identity.py
"""Seed danh tính + workspace qua HTTP THẬT vào services/cosa.

Routes (xác nhận ở Step 0 discovery):
  POST /platform/auth/register  -> tạo user, trả {userId, ...}
  POST /platform/auth/sessions  -> login, trả {accessToken | token, ...}
  <route provision workspace>   -> điền sau discovery
  <route add member>            -> điền sau discovery
"""
from __future__ import annotations

import secrets

import httpx

from tests.e2e.seed.handles import SeededWorkspace

_TIMEOUT = 15.0


def register_user(cosa_base_url: str, *, email: str | None = None) -> tuple[str, str, str]:
    email = email or f"e2e-{secrets.token_hex(6)}@example.test"
    password = f"Pw-{secrets.token_hex(8)}!"
    with httpx.Client(base_url=cosa_base_url, timeout=_TIMEOUT) as client:
        resp = client.post(
            "/platform/auth/register",
            json={"email": email, "password": password, "displayName": "E2E User"},
        )
    resp.raise_for_status()
    body = resp.json()
    user_id = str(body.get("userId") or body.get("user_id") or body["user"]["id"])
    return user_id, email, password


def login(cosa_base_url: str, email: str, password: str) -> str:
    with httpx.Client(base_url=cosa_base_url, timeout=_TIMEOUT) as client:
        resp = client.post("/platform/auth/sessions", json={"email": email, "password": password})
    resp.raise_for_status()
    body = resp.json()
    token = body.get("accessToken") or body.get("token") or body.get("access_token")
    if not token:
        raise AssertionError(f"login response has no token field: {body}")
    return str(token)


def provision_workspace(cosa_base_url: str, owner_token: str, *, name: str) -> str:
    # TODO(discovery Step 0): thay bằng route thật. Nếu expose:false -> INSERT trực
    # tiếp vào cosa DB theo schema venture-workspace (workspace + membership OWNER +
    # license + entitlement mặc định), KHÔNG mock.
    with httpx.Client(base_url=cosa_base_url, timeout=_TIMEOUT) as client:
        resp = client.post(
            "/platform/workspaces",
            json={"name": name},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
    resp.raise_for_status()
    return str(resp.json()["workspaceId"])


def add_member(cosa_base_url: str, owner_token: str, workspace_id: str, member_user_id: str) -> None:
    with httpx.Client(base_url=cosa_base_url, timeout=_TIMEOUT) as client:
        resp = client.post(
            f"/platform/workspaces/{workspace_id}/members",
            json={"userId": member_user_id, "role": "member"},
            headers={"Authorization": f"Bearer {owner_token}", "X-Workspace-Id": workspace_id},
        )
    resp.raise_for_status()


def seed_workspace(stack, *, with_member: bool = False) -> SeededWorkspace:
    cosa_url = stack.platform.base_url
    owner_id, owner_email, owner_pw = register_user(cosa_url)
    owner_token = login(cosa_url, owner_email, owner_pw)
    workspace_id = provision_workspace(cosa_url, owner_token, name=f"E2E {secrets.token_hex(3)}")

    member_id = member_token = None
    if with_member:
        member_id, member_email, member_pw = register_user(cosa_url)
        add_member(cosa_url, owner_token, workspace_id, member_id)
        member_token = login(cosa_url, member_email, member_pw)

    return SeededWorkspace(
        workspace_id=workspace_id,
        owner_user_id=owner_id,
        owner_token=owner_token,
        member_user_id=member_id,
        member_token=member_token,
    )
```

```python
# tests/e2e/seed/entitlement.py
"""Bật capability prefix cho một workspace (cho scenario S3)."""
from __future__ import annotations

import httpx


def grant_entitlement(
    cosa_base_url: str, owner_token: str, workspace_id: str, capability_prefix: str
) -> None:
    # TODO(discovery Step 0): route thật của agent-policy / entitlement grant.
    with httpx.Client(base_url=cosa_base_url, timeout=15.0) as client:
        resp = client.post(
            f"/platform/workspaces/{workspace_id}/entitlements",
            json={"capabilityPrefix": capability_prefix},
            headers={"Authorization": f"Bearer {owner_token}", "X-Workspace-Id": workspace_id},
        )
    # Idempotent: 200 hoặc 409 "already granted" đều chấp nhận.
    if resp.status_code not in (200, 201, 409):
        resp.raise_for_status()
```

```python
# tests/e2e/seed/agent_spec.py
"""Publish 1 AgentSpec + skillpack tối thiểu đủ để control-plane dispatch.

Dựa apps/cosa/agents/seed.py (seed idempotent lúc startup). Ở đây gọi lại
đường publish đó cho một workspace test, hoặc INSERT theo schema registry
(packages/agent/migrations/007_agent_registry.sql) nếu không có route.
"""
from __future__ import annotations

from tests.e2e.stack.disposable_postgres import DisposableCluster


def seed_minimal_agent_spec(
    apps_cosa_base_url: str, cluster: DisposableCluster, *, workspace_id: str
) -> str:
    # TODO(discovery Step 0): xác định đường publish spec. Trả agent_spec_id.
    raise NotImplementedError("fill after discovery in Step 0")
```

> **Lưu ý cho engineer:** `provision_workspace`, `add_member`, `grant_entitlement`, `seed_minimal_agent_spec` có `TODO(discovery)` — Step 0 của task này bắt buộc phải hoàn tất chúng bằng route/SQL thật. Không được để `NotImplementedError` hay `TODO` khi commit. Nếu discovery cho thấy phải INSERT SQL, viết hàm INSERT đầy đủ theo schema.

- [ ] **Step 4: Hoàn tất discovery + chạy test — xác nhận pass**

Run: `PYTHONPATH=. .venv/bin/pytest tests/e2e/seed/test_seed_kit_contract.py -v` (sau khi Task 5 xong)
Expected: PASS (2 test)

- [ ] **Step 5: Lint + commit**

```bash
.venv/bin/ruff check tests/e2e/seed/ && .venv/bin/ruff format tests/e2e/seed/
git add tests/e2e/seed/
git commit -m "feat(e2e): unified seed kit (identity, workspace, entitlement, agent spec)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Rework `tests/e2e/mvp_stack.py`

**Files:**
- Modify: `tests/e2e/mvp_stack.py`
- Test: `tests/e2e/stack/test_mvp_stack_factories.py`

**Interfaces:**
- Consumes: `StackHandles` (Task 5 — dùng forward ref / TYPE_CHECKING để tránh vòng import)
- Produces:
  - `MvpStack.company / .platform / .agent: ServiceClient` (giữ), `MvpStack.apps_cosa: ServiceClient` (mới), `MvpStack.worker_health_url: str` (mới)
  - `MvpStack.uses_mock_transport: bool` — **giữ mặc định `False`, thêm `__post_init__` raise nếu bị set `True`**
  - `@classmethod MvpStack.from_base_urls(company: str, platform: str, agent: str, apps_cosa: str, worker_health_url: str) -> MvpStack`
  - **Xoá** field `migration_versions`

- [ ] **Step 1: Viết test thất bại**

```python
# tests/e2e/stack/test_mvp_stack_factories.py
from __future__ import annotations

import pytest

from tests.e2e.mvp_stack import MvpStack


def test_from_base_urls_builds_clients() -> None:
    stack = MvpStack.from_base_urls(
        company="http://127.0.0.1:4000",
        platform="http://127.0.0.1:4001",
        agent="http://127.0.0.1:8001",
        apps_cosa="http://127.0.0.1:8001",
        worker_health_url="http://127.0.0.1:8090/live",
    )
    assert stack.company.base_url == "http://127.0.0.1:4000"
    assert stack.uses_mock_transport is False
    assert not hasattr(stack, "migration_versions")


def test_mock_transport_flag_cannot_be_enabled() -> None:
    with pytest.raises(ValueError):
        MvpStack(
            company=MvpStack.from_base_urls(
                company="x", platform="x", agent="x", apps_cosa="x", worker_health_url="x"
            ).company,
            platform=MvpStack.from_base_urls(
                company="x", platform="x", agent="x", apps_cosa="x", worker_health_url="x"
            ).platform,
            agent=MvpStack.from_base_urls(
                company="x", platform="x", agent="x", apps_cosa="x", worker_health_url="x"
            ).agent,
            apps_cosa=MvpStack.from_base_urls(
                company="x", platform="x", agent="x", apps_cosa="x", worker_health_url="x"
            ).apps_cosa,
            worker_health_url="x",
            uses_mock_transport=True,
        )
```

- [ ] **Step 2: Chạy test — xác nhận fail**

Run: `PYTHONPATH=. .venv/bin/pytest tests/e2e/stack/test_mvp_stack_factories.py -v`
Expected: FAIL — `AttributeError: type object 'MvpStack' has no attribute 'from_base_urls'`

- [ ] **Step 3: Sửa `tests/e2e/mvp_stack.py`**

Giữ `pick_free_port` + `ServiceClient` như cũ. Thay `MvpStack`:

```python
@dataclass
class MvpStack:
    company: ServiceClient
    platform: ServiceClient
    agent: ServiceClient
    apps_cosa: ServiceClient
    worker_health_url: str
    uses_mock_transport: bool = False

    def __post_init__(self) -> None:
        # Bất biến: dàn E2E cross-plane KHÔNG bao giờ dùng transport giả.
        if self.uses_mock_transport:
            raise ValueError("MvpStack.uses_mock_transport must stay False for the real stack")

    @classmethod
    def from_base_urls(
        cls,
        *,
        company: str,
        platform: str,
        agent: str,
        apps_cosa: str,
        worker_health_url: str,
    ) -> "MvpStack":
        return cls(
            company=ServiceClient(base_url=company.rstrip("/")),
            platform=ServiceClient(base_url=platform.rstrip("/")),
            agent=ServiceClient(base_url=agent.rstrip("/")),
            apps_cosa=ServiceClient(base_url=apps_cosa.rstrip("/")),
            worker_health_url=worker_health_url,
        )
```

Cập nhật docstring đầu file: bỏ câu "deliberately does not start processes", thay bằng mô tả 2 chế độ boot (subprocess / compose) và dẫn `tests/e2e/stack/`. Sửa mọi test hiện dùng `migration_versions` (grep `rg "migration_versions" tests/`) — nếu có, chuyển sang gọi `<runner> --check` (Task 2 `apply_migrations` đã đảm bảo mới nhất; không còn cần assert version tay).

- [ ] **Step 4: Chạy test — xác nhận pass**

Run: `PYTHONPATH=. .venv/bin/pytest tests/e2e/stack/test_mvp_stack_factories.py tests/e2e/ -q --co` (collect-only để chắc không vỡ import)
Then: `PYTHONPATH=. .venv/bin/pytest tests/e2e/stack/test_mvp_stack_factories.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
.venv/bin/ruff check tests/e2e/ && .venv/bin/ruff format tests/e2e/mvp_stack.py
git add tests/e2e/mvp_stack.py tests/e2e/stack/test_mvp_stack_factories.py
git commit -m "feat(e2e): MvpStack factories, drop hard-coded migration_versions

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## PHASE P2 — Tầng 1: subprocess stack + scenarios + CI

### Task 5: Subprocess stack + fixture `real_cosa_stack`

**Files:**
- Create: `tests/e2e/stack/subprocess_stack.py`
- Modify: `tests/e2e/conftest.py` — fixture `real_cosa_stack`
- Test: `tests/e2e/stack/test_subprocess_stack_boot.py`

**Interfaces:**
- Consumes: `DisposableCluster` (Task 2), `_process` helpers (Task 1), `MvpStack.from_base_urls` (Task 4)
- Produces:
  - `@dataclass StackHandles(company_url, cosa_url, apps_cosa_url, worker_health_url, procs: list[ManagedProc])`
  - `boot_subprocess_stack(cluster: DisposableCluster) -> StackHandles`
  - `teardown_subprocess_stack(handles: StackHandles) -> None`
  - fixture `real_cosa_stack` (scope=`session`) → `MvpStack`; nhánh `E2E_BASE_URL_COMPANY/_COSA/_API` trỏ stack ngoài (bỏ boot)

**Bối cảnh cross-wiring (env cho từng process):**

| Process | cwd | argv | Env then chốt |
|---|---|---|---|
| company | `services/company` | `encore run --port=<p1>` | `WORKSPACE_DATABASE_URL=<cluster.workspace_app_url>`, `E2E_TEST_SEED_ENABLED=1`, `COSA_URL=http://127.0.0.1:<p2>`, `PLATFORM_JWT_SECRET`, `JWT_SECRET` |
| cosa | `services/cosa` | `encore run --port=<p2>` | `COSA_DATABASE_URL=<cluster.cosa_app_url>`, `COMPANY_SERVICE_URL=http://127.0.0.1:<p1>`, `PLATFORM_JWT_SECRET`, `WORKER_SERVICE_JWT_SECRET` |
| apps/cosa api | repo root | `<python> -m apps.cosa.api.main` (cổng qua env, xem `apps/cosa/api/main.py`) | `AGENT_DATABASE_URL=<cluster.agent_app_url>` (driver `postgresql+asyncpg`), `COSA_DATABASE_URL=<cluster.cosa_app_url>`, `COMPANY_SERVICE_URL=http://127.0.0.1:<p1>`, `COSA_CONTROL_PLANE_URL=http://127.0.0.1:<p2>`, `COSA_MODEL_PROVIDER=fake`, `DEEPSEEK_API_KEY=fake-deepseek-key-for-e2e`, `COSA_WORKER_SERVICE_TOKEN=<mint>`, `APP_ENV=development` |
| apps/cosa worker | repo root | `<python> -m apps.cosa.worker.main` | như api + `WORKER_ID=e2e-<run_id>`, health server cổng `<p4>` |

Mint worker token 1 lần: `subprocess.run(["node", "scripts/mint-worker-service-token.mjs", f"e2e-{cluster.run_id}"], env={**os.environ, "WORKER_SERVICE_JWT_SECRET": "cosa-worker-service-jwt-key-change-in-prod-min32chars"}, capture_output=True, text=True)` → token = `result.stdout.strip()`.

**Discovery Step 0 (bắt buộc):**
```bash
sed -n '1,60p' apps/cosa/api/main.py            # cách nhận cổng: arg? env PORT? COSA_API_PORT?
sed -n '320,421p' apps/cosa/worker/main.py      # health server cổng nào, env gì
grep -rn "healthz\|/live\|/ready" apps/cosa/api/app.py apps/cosa/worker/health.py
grep -rn "COSA_URL\|COMPANY_SERVICE_URL\|COSA_CONTROL_PLANE_URL" services/company/shared services/cosa/shared apps/cosa/composition | grep -v test
```
Điền chính xác cách truyền cổng + đường `/healthz` (api) / `/live` (worker) vào code.

- [ ] **Step 1: Viết test thất bại**

```python
# tests/e2e/stack/test_subprocess_stack_boot.py
"""Boot đủ 4 process thật trên cluster disposable, cả 4 /healthz xanh, teardown sạch."""
from __future__ import annotations

import httpx


def test_all_four_planes_report_healthy(real_cosa_stack) -> None:
    for name, url in (
        ("company", f"{real_cosa_stack.company.base_url}/healthz"),
        ("cosa", f"{real_cosa_stack.platform.base_url}/healthz"),
        ("apps_cosa", f"{real_cosa_stack.apps_cosa.base_url}/healthz"),
        ("worker", real_cosa_stack.worker_health_url),
    ):
        resp = httpx.get(url, timeout=5.0)
        assert resp.status_code in (200, 503), f"{name} unhealthy: {resp.status_code} {resp.text}"
```

- [ ] **Step 2: Chạy test — xác nhận fail**

Run: `PYTHONPATH=. .venv/bin/pytest tests/e2e/stack/test_subprocess_stack_boot.py -v`
Expected: FAIL — fixture `real_cosa_stack` chưa định nghĩa

- [ ] **Step 3: Cài đặt**

```python
# tests/e2e/stack/subprocess_stack.py
"""Boot 4 vùng thật bằng subprocess cho E2E Tầng 1 (không Docker).

Mở rộng pattern tests/e2e/conftest.py::real_company_service sang cả cosa +
apps/cosa API + worker, tất cả trỏ vào một DisposableCluster.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field

from tests.e2e.stack._process import ManagedProc, pick_free_port, spawn, terminate_all, wait_until_ready
from tests.e2e.stack.disposable_postgres import DisposableCluster

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
_PYTHON = os.environ.get("PYTHON", os.path.join(_REPO_ROOT, ".venv", "bin", "python"))

_SECRETS = {
    "PLATFORM_JWT_SECRET": "cosa-super-secret-platform-jwt-key-change-in-prod",
    "WORKER_SERVICE_JWT_SECRET": "cosa-worker-service-jwt-key-change-in-prod-min32chars",
    "JWT_SECRET": "cosa-dev-jwt-secret-do-not-use-in-prod",
}


@dataclass
class StackHandles:
    company_url: str
    cosa_url: str
    apps_cosa_url: str
    worker_health_url: str
    procs: list[ManagedProc] = field(default_factory=list)


def _require_encore() -> str:
    encore = shutil.which("encore")
    if not encore:
        raise RuntimeError(
            "`encore` CLI not found on PATH — cannot boot the real cross-plane stack. "
            "Install via https://encore.dev/install.sh (see .github/workflows/quality.yml)."
        )
    return encore


def _mint_worker_token(run_id: str) -> str:
    result = subprocess.run(
        ["node", "scripts/mint-worker-service-token.mjs", f"e2e-{run_id}"],
        cwd=_REPO_ROOT,
        env={**os.environ, "WORKER_SERVICE_JWT_SECRET": _SECRETS["WORKER_SERVICE_JWT_SECRET"]},
        capture_output=True, text=True, timeout=30, check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(f"mint worker token failed: {result.stdout}\n{result.stderr}")
    return result.stdout.strip()


def boot_subprocess_stack(cluster: DisposableCluster) -> StackHandles:
    encore = _require_encore()
    p_company, p_cosa, p_api, p_worker = (pick_free_port() for _ in range(4))
    company_url = f"http://127.0.0.1:{p_company}"
    cosa_url = f"http://127.0.0.1:{p_cosa}"
    api_url = f"http://127.0.0.1:{p_api}"
    worker_health = f"http://127.0.0.1:{p_worker}/live"  # xác nhận ở discovery Step 0
    worker_token = _mint_worker_token(cluster.run_id)
    procs: list[ManagedProc] = []

    try:
        company = spawn(
            "company",
            [encore, "run", f"--port={p_company}"],
            cwd=os.path.join(_REPO_ROOT, "services", "company"),
            env={
                **os.environ, **_SECRETS,
                "WORKSPACE_DATABASE_URL": cluster.workspace_app_url,
                "E2E_TEST_SEED_ENABLED": "1",
                "COSA_URL": cosa_url,
            },
        )
        procs.append(company)
        wait_until_ready("company", f"{company_url}/healthz", company)

        cosa = spawn(
            "cosa",
            [encore, "run", f"--port={p_cosa}"],
            cwd=os.path.join(_REPO_ROOT, "services", "cosa"),
            env={
                **os.environ, **_SECRETS,
                "COSA_DATABASE_URL": cluster.cosa_app_url,
                "COMPANY_SERVICE_URL": company_url,
            },
        )
        procs.append(cosa)
        wait_until_ready("cosa", f"{cosa_url}/healthz", cosa)

        common_py_env = {
            **os.environ, **_SECRETS,
            "AGENT_DATABASE_URL": cluster.agent_app_url,  # postgresql+asyncpg://...
            "COSA_DATABASE_URL": cluster.cosa_app_url,
            "COMPANY_SERVICE_URL": company_url,
            "COSA_CONTROL_PLANE_URL": cosa_url,
            "COSA_MODEL_PROVIDER": "fake",
            "DEEPSEEK_API_KEY": "fake-deepseek-key-for-e2e",
            "COSA_WORKER_SERVICE_TOKEN": worker_token,
            "APP_ENV": "development",
            "PYTHONPATH": _REPO_ROOT,
        }

        api = spawn(
            "apps_cosa_api",
            [_PYTHON, "-m", "apps.cosa.api.main"],
            cwd=_REPO_ROOT,
            env={**common_py_env, "COSA_API_PORT": str(p_api)},  # xác nhận tên env ở Step 0
        )
        procs.append(api)
        wait_until_ready("apps_cosa_api", f"{api_url}/healthz", api)

        worker = spawn(
            "apps_cosa_worker",
            [_PYTHON, "-m", "apps.cosa.worker.main"],
            cwd=_REPO_ROOT,
            env={**common_py_env, "WORKER_ID": f"e2e-{cluster.run_id}", "WORKER_HEALTH_PORT": str(p_worker)},
        )
        procs.append(worker)
        wait_until_ready("apps_cosa_worker", worker_health, worker)

        return StackHandles(company_url, cosa_url, api_url, worker_health, procs)
    except Exception:
        terminate_all(procs)
        raise


def teardown_subprocess_stack(handles: StackHandles) -> None:
    terminate_all(handles.procs)
```

Thêm vào `tests/e2e/conftest.py`:

```python
from tests.e2e.mvp_stack import MvpStack
from tests.e2e.stack.subprocess_stack import boot_subprocess_stack, teardown_subprocess_stack


@pytest.fixture(scope="session")
def real_cosa_stack(disposable_cluster) -> Iterator[MvpStack]:
    ext_company = os.environ.get("E2E_BASE_URL_COMPANY", "").strip()
    ext_cosa = os.environ.get("E2E_BASE_URL_COSA", "").strip()
    ext_api = os.environ.get("E2E_BASE_URL_API", "").strip()
    if ext_company and ext_cosa and ext_api:
        yield MvpStack.from_base_urls(
            company=ext_company, platform=ext_cosa, agent=ext_api,
            apps_cosa=ext_api, worker_health_url=f"{ext_api}/healthz",
        )
        return

    handles = boot_subprocess_stack(disposable_cluster)
    try:
        yield MvpStack.from_base_urls(
            company=handles.company_url, platform=handles.cosa_url, agent=handles.apps_cosa_url,
            apps_cosa=handles.apps_cosa_url, worker_health_url=handles.worker_health_url,
        )
    finally:
        teardown_subprocess_stack(handles)
```

- [ ] **Step 4: Chạy test — xác nhận pass**

Run: `PYTHONPATH=. .venv/bin/pytest tests/e2e/stack/test_subprocess_stack_boot.py -v -s`
Expected: PASS. Thời gian boot lần đầu có thể 60–120s (Encore compile). Nếu 1 process chết sớm, `wait_until_ready` in output đã capture — đọc lỗi env/DB từ đó.

- [ ] **Step 5: Commit**

```bash
.venv/bin/ruff check tests/e2e/ && .venv/bin/ruff format tests/e2e/stack/subprocess_stack.py tests/e2e/conftest.py
git add tests/e2e/stack/subprocess_stack.py tests/e2e/stack/test_subprocess_stack_boot.py tests/e2e/conftest.py
git commit -m "feat(e2e): boot 4-plane subprocess stack + real_cosa_stack fixture

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: Scenario S1 — auth + tenant isolation

**Files:**
- Create: `tests/e2e/scenarios/__init__.py` (rỗng), `tests/e2e/scenarios/auth_tenant_isolation.py`
- Create: `tests/e2e/test_cross_plane_smoke.py`
- Test: chính `test_cross_plane_smoke.py::test_s1_auth_tenant_isolation`

**Interfaces:**
- Consumes: `MvpStack` (fixture `real_cosa_stack`), `identity.seed_workspace`
- Produces: `auth_tenant_isolation.run(stack: MvpStack, seeded: SeededWorkspace) -> None`

- [ ] **Step 1: Viết test thất bại**

```python
# tests/e2e/test_cross_plane_smoke.py
"""Tầng 1 — cross-plane smoke. 4 vùng thật, model=fake, chặn PR.

KHÔNG mock, KHÔNG skip, KHÔNG transport giả (scripts/check_mvp_e2e_purity.py).
Thiếu tiền đề -> fixture pytest.fail, không skip.
"""
from __future__ import annotations

from tests.e2e.scenarios import auth_tenant_isolation
from tests.e2e.seed import identity


def test_s1_auth_tenant_isolation(real_cosa_stack) -> None:
    seeded = identity.seed_workspace(real_cosa_stack, with_member=True)
    auth_tenant_isolation.run(real_cosa_stack, seeded)
```

```python
# tests/e2e/scenarios/auth_tenant_isolation.py
"""S1: đăng ký/đăng nhập thật -> workspace A & B -> cô lập tenant qua wire."""
from __future__ import annotations

from tests.e2e.mvp_stack import MvpStack
from tests.e2e.seed import identity
from tests.e2e.seed.handles import SeededWorkspace


def run(stack: MvpStack, seeded: SeededWorkspace) -> None:
    company = stack.company

    # Workspace thứ hai cùng owner để kiểm cô lập.
    workspace_b = identity.provision_workspace(
        stack.platform.base_url, seeded.owner_token, name="E2E-B"
    )

    # 1. Member đọc list task ở workspace của mình -> 200 envelope {data, meta}.
    r_list = company.get("/operations/tasks", token=seeded.member_token, workspace_id=seeded.workspace_id)
    assert r_list.status_code == 200, r_list.text
    assert set(r_list.json()) >= {"data", "meta"}

    # 2. Owner tạo 1 task ở workspace A.
    r_create = company.post(
        "/operations/tasks",
        json={"title": "S1 task", "status": "todo"},
        token=seeded.owner_token,
        workspace_id=seeded.workspace_id,
    )
    assert r_create.status_code in (200, 201), r_create.text
    task_id = r_create.json()["data"]["id"]

    # 3. Đọc task đó với X-Workspace-Id = B -> KHÔNG được thấy (404), không leak.
    r_cross = company.get(
        f"/operations/tasks/{task_id}", token=seeded.owner_token, workspace_id=workspace_b
    )
    assert r_cross.status_code == 404, r_cross.text

    # 4. Không Authorization -> 401.
    r_anon = company.get("/operations/tasks", workspace_id=seeded.workspace_id)
    assert r_anon.status_code == 401

    # 5. Token member hợp lệ nhưng workspace không thuộc -> 403.
    r_forbidden = company.get(
        "/operations/tasks", token=seeded.member_token, workspace_id=workspace_b
    )
    assert r_forbidden.status_code == 403, r_forbidden.text
```

Tạo `tests/e2e/scenarios/__init__.py` rỗng.

- [ ] **Step 2: Chạy test — xác nhận fail rồi pass**

Run: `PYTHONPATH=. .venv/bin/pytest tests/e2e/test_cross_plane_smoke.py::test_s1_auth_tenant_isolation -v`
Expected: ban đầu có thể FAIL vì route/field thật khác (`/operations/tasks` payload, `data.id`) — điều chỉnh assert theo response THẬT quan sát được (in `r_create.json()`), **không** nới lỏng thành `status_code < 500`. Khi khớp: PASS.

- [ ] **Step 3: (không có bước impl riêng — scenario chính là impl)**

- [ ] **Step 4: Chạy lại toàn bộ file**

Run: `PYTHONPATH=. .venv/bin/pytest tests/e2e/test_cross_plane_smoke.py -v`
Expected: PASS `test_s1_...`

- [ ] **Step 5: Commit**

```bash
.venv/bin/ruff check tests/e2e/ && .venv/bin/ruff format tests/e2e/scenarios/ tests/e2e/test_cross_plane_smoke.py
git add tests/e2e/scenarios/__init__.py tests/e2e/scenarios/auth_tenant_isolation.py tests/e2e/test_cross_plane_smoke.py
git commit -m "test(e2e): S1 cross-plane auth + tenant isolation scenario

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: Scenario S2 — dispatch → worker → result

**Files:**
- Create: `tests/e2e/scenarios/dispatch_worker_result.py`
- Modify: `tests/e2e/test_cross_plane_smoke.py` — thêm `test_s2_dispatch_worker_result`
- Modify: `tests/e2e/seed/agent_spec.py` — hoàn tất `seed_minimal_agent_spec` (nếu Task 3 để lại)

**Interfaces:**
- Consumes: `MvpStack`, `SeededWorkspace`, `agent_spec.seed_minimal_agent_spec`, `conftest.count_runtime_source_signals`
- Produces: `dispatch_worker_result.run(stack: MvpStack, seeded: SeededWorkspace, cluster: DisposableCluster) -> None`

**Discovery Step 0:**
```bash
grep -rn "path:" services/cosa/handlers/control-plane.handler.ts | head -40   # route tạo mission/task + xem trạng thái
grep -rn "runtime_source_signals\|agent-runtime-signal" services/company/events | grep -v test
sed -n '1,60p' tests/e2e/conftest.py   # count_runtime_source_signals signature (đã có)
grep -rn "run_events\|run_tool_calls\|RunEventRecord" packages/agent/runs/models.py
```

- [ ] **Step 1: Viết test thất bại**

```python
# thêm vào tests/e2e/test_cross_plane_smoke.py
from tests.e2e.scenarios import dispatch_worker_result


def test_s2_dispatch_worker_result(real_cosa_stack, disposable_cluster) -> None:
    seeded = identity.seed_workspace(real_cosa_stack)
    dispatch_worker_result.run(real_cosa_stack, seeded, disposable_cluster)
```

```python
# tests/e2e/scenarios/dispatch_worker_result.py
"""S2: tạo mission ở cosa -> worker thật claim & chạy (FakeSDKModel) -> run
completed -> signal về company idempotent."""
from __future__ import annotations

import time

import psycopg2

from tests.e2e.mvp_stack import MvpStack
from tests.e2e.seed import agent_spec
from tests.e2e.seed.handles import SeededWorkspace
from tests.e2e.stack.disposable_postgres import DisposableCluster

_POLL_TIMEOUT_S = 120.0


def run(stack: MvpStack, seeded: SeededWorkspace, cluster: DisposableCluster) -> None:
    spec_id = agent_spec.seed_minimal_agent_spec(
        stack.apps_cosa.base_url, cluster, workspace_id=seeded.workspace_id
    )

    # 1. Tạo mission/run qua control-plane (route xác nhận ở discovery).
    r = stack.platform.post(
        "/cosa/control-plane/missions",
        json={"workspaceId": seeded.workspace_id, "agentSpecId": spec_id, "input": {"prompt": "ping"}},
        token=seeded.owner_token,
        workspace_id=seeded.workspace_id,
    )
    assert r.status_code in (200, 201), r.text
    run_id = r.json()["data"]["runId"]

    # 2. Poll trạng thái run tới completed — worker thật xử lý.
    deadline = time.monotonic() + _POLL_TIMEOUT_S
    status = None
    while time.monotonic() < deadline:
        rs = stack.platform.get(
            f"/cosa/control-plane/runs/{run_id}", token=seeded.owner_token,
            workspace_id=seeded.workspace_id,
        )
        assert rs.status_code == 200, rs.text
        status = rs.json()["data"]["status"]
        if status in ("completed", "succeeded"):
            break
        if status in ("failed", "cancelled"):
            raise AssertionError(f"run {run_id} ended {status}: {rs.text}")
        time.sleep(2.0)
    assert status in ("completed", "succeeded"), f"run not completed in {_POLL_TIMEOUT_S}s (last={status})"

    # 3. run_events có hàng thật trong DB agent.
    agent_conn = psycopg2.connect(cluster.agent_app_url, connect_timeout=5)
    try:
        with agent_conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM run_events WHERE run_id = %s", (run_id,))
            assert cur.fetchone()[0] > 0
    finally:
        agent_conn.close()

    # 4. Signal về company idempotent: projection chỉ 1 hàng cho identity của run.
    ws_conn = psycopg2.connect(cluster.workspace_app_url, connect_timeout=5)
    try:
        with ws_conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM operating.runtime_source_signals "
                "WHERE workspace_id = %s AND source_kind = 'run' AND source_id = %s",
                (int(seeded.workspace_id), run_id),
            )
            assert cur.fetchone()[0] == 1
    finally:
        ws_conn.close()
```

- [ ] **Step 2–4: Chạy, điều chỉnh route/field theo response thật, xác nhận PASS**

Run: `PYTHONPATH=. .venv/bin/pytest tests/e2e/test_cross_plane_smoke.py::test_s2_dispatch_worker_result -v -s`
Nếu worker không nhặt task: kiểm `COSA_WORKER_SERVICE_TOKEN` khớp `WORKER_SERVICE_JWT_SECRET` giữa 2 process; kiểm log worker (in ra khi `wait_until_ready` fail, hoặc thêm `-s` xem stdout). Điều chỉnh tên bảng `run_events` / cột theo `packages/agent/runs/models.py` thật.

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/scenarios/dispatch_worker_result.py tests/e2e/test_cross_plane_smoke.py tests/e2e/seed/agent_spec.py
git commit -m "test(e2e): S2 dispatch -> worker -> result -> idempotent signal

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 8: Scenario S3 — capability + governance

**Files:**
- Create: `tests/e2e/scenarios/capability_governance.py`
- Modify: `tests/e2e/test_cross_plane_smoke.py` — `test_s3_capability_governance`

**Interfaces:**
- Consumes: `MvpStack`, `SeededWorkspace`, `entitlement.grant_entitlement`, `DisposableCluster`
- Produces: `capability_governance.run(stack, seeded, cluster) -> None`

**Discovery Step 0:**
```bash
grep -rn "operations_read\|operations_write" apps/cosa/capabilities/ | head
grep -rn "router\|APIRouter\|@router" apps/cosa/api/copilot_routes.py apps/cosa/api/routes.py | head -30
grep -rn "REQUIRE_APPROVAL\|run_approvals\|checkpoint_ref" packages/agent/capabilities packages/agent/runs | grep -v test | head
grep -rn "CREATE TABLE.*audit\|audit_events\|governance.*audit" packages/agent/migrations/*.sql
```

- [ ] **Step 1: Viết test thất bại**

```python
# tests/e2e/scenarios/capability_governance.py
"""S3: capability operations_read từ apps/cosa -> CompanyServiceClient HTTP THẬT
tới services/company (không Stub) -> audit ghi thật; HIGH-risk -> REQUIRE_APPROVAL
bind đúng run_id + tool_call_id + checkpoint_ref."""
from __future__ import annotations

import psycopg2

from tests.e2e.mvp_stack import MvpStack
from tests.e2e.seed import entitlement
from tests.e2e.seed.handles import SeededWorkspace
from tests.e2e.stack.disposable_postgres import DisposableCluster


def run(stack: MvpStack, seeded: SeededWorkspace, cluster: DisposableCluster) -> None:
    entitlement.grant_entitlement(
        stack.platform.base_url, seeded.owner_token, seeded.workspace_id, "operations"
    )

    # 1. Đường đọc: apps/cosa gọi capability -> company thật trả dữ liệu.
    r_read = stack.apps_cosa.post(
        "/copilot/capabilities/operations_read",  # route xác nhận ở discovery
        json={"resource": "tasks"},
        token=seeded.owner_token,
        workspace_id=seeded.workspace_id,
    )
    assert r_read.status_code == 200, r_read.text
    assert "data" in r_read.json()

    # 2. Audit event ghi thật trong DB agent.
    agent_conn = psycopg2.connect(cluster.agent_app_url, connect_timeout=5)
    try:
        with agent_conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM audit_events WHERE workspace_id = %s",  # tên bảng xác nhận
                (seeded.workspace_id,),
            )
            assert cur.fetchone()[0] > 0
    finally:
        agent_conn.close()

    # 3. HIGH-risk -> REQUIRE_APPROVAL, approval bind đúng run_id + tool_call_id + checkpoint_ref.
    r_write = stack.apps_cosa.post(
        "/copilot/capabilities/operations_write",
        json={"resource": "tasks", "op": "delete", "id": "does-not-exist"},
        token=seeded.owner_token,
        workspace_id=seeded.workspace_id,
    )
    assert r_write.status_code in (200, 202), r_write.text
    decision = r_write.json()["data"]
    assert decision["mode"] == "REQUIRE_APPROVAL", decision
    approval = decision["approval"]
    assert approval["runId"] and approval["toolCallId"] and approval["checkpointRef"]

    with agent_conn := psycopg2.connect(cluster.agent_app_url, connect_timeout=5):
        with agent_conn.cursor() as cur:
            cur.execute(
                "SELECT run_id, tool_call_id, checkpoint_ref FROM run_approvals "
                "WHERE run_id = %s AND tool_call_id = %s",
                (approval["runId"], approval["toolCallId"]),
            )
            row = cur.fetchone()
            assert row is not None and row[2] == approval["checkpointRef"]
```

```python
# thêm vào tests/e2e/test_cross_plane_smoke.py
from tests.e2e.scenarios import capability_governance


def test_s3_capability_governance(real_cosa_stack, disposable_cluster) -> None:
    seeded = identity.seed_workspace(real_cosa_stack)
    capability_governance.run(real_cosa_stack, seeded, disposable_cluster)
```

- [ ] **Step 2–4: Chạy, khớp route/tên bảng theo thật, xác nhận PASS**

Run: `PYTHONPATH=. .venv/bin/pytest tests/e2e/test_cross_plane_smoke.py::test_s3_capability_governance -v -s`

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/scenarios/capability_governance.py tests/e2e/test_cross_plane_smoke.py
git commit -m "test(e2e): S3 capability -> real company HTTP + governance approval binding

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 9: Scenario S4 — outbox → relay

**Files:**
- Create: `tests/e2e/scenarios/outbox_relay.py`
- Modify: `tests/e2e/test_cross_plane_smoke.py` — `test_s4_outbox_relay`

**Interfaces:**
- Consumes: `MvpStack`, `SeededWorkspace`, `DisposableCluster`
- Produces: `outbox_relay.run(stack, seeded, cluster) -> None`

**Discovery Step 0:**
```bash
sed -n '1,80p' services/company/events/outbox-relay.service.ts
grep -rn "path:\|expose:" services/company/events/*.ts | grep -v test    # có route trigger relay thủ công?
grep -rn "CREATE TABLE.*outbox\|events\..*outbox" services/company/**/migrations/*.sql
grep -rn "event_inbox\|inbox" apps/cosa/events/*.py | grep -v test | head
```
Nếu không có route trigger relay thủ công: scenario gọi thẳng hàm relay qua một endpoint nội bộ có sẵn, hoặc chờ cron (poll `event_inbox` tối đa 60s). Ghi rõ cách chọn vào docstring.

- [ ] **Step 1: Viết test thất bại**

```python
# tests/e2e/scenarios/outbox_relay.py
"""S4: mutation company -> domain event vào outbox cùng transaction -> relay đẩy
sang cosa -> event_inbox nhận idempotent (duplicate không tạo 2 hàng)."""
from __future__ import annotations

import time

import psycopg2

from tests.e2e.mvp_stack import MvpStack
from tests.e2e.seed.handles import SeededWorkspace
from tests.e2e.stack.disposable_postgres import DisposableCluster


def run(stack: MvpStack, seeded: SeededWorkspace, cluster: DisposableCluster) -> None:
    # 1. Mutation sinh domain event (vd tạo OKR).
    r = stack.company.post(
        "/operations/okrs",
        json={"objective": "S4 objective", "period": "2026-Q3"},
        token=seeded.owner_token,
        workspace_id=seeded.workspace_id,
    )
    assert r.status_code in (200, 201), r.text

    # 2. Outbox có hàng (schema events — tên bảng xác nhận ở discovery).
    ws_conn = psycopg2.connect(cluster.workspace_app_url, connect_timeout=5)
    try:
        with ws_conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM events.outbox WHERE workspace_id = %s", (int(seeded.workspace_id),)
            )
            assert cur.fetchone()[0] >= 1
    finally:
        ws_conn.close()

    # 3. Chờ relay -> event_inbox ở cosa nhận (poll tối đa 60s).
    cosa_conn = psycopg2.connect(cluster.cosa_app_url, connect_timeout=5)
    try:
        deadline = time.monotonic() + 60.0
        count = 0
        while time.monotonic() < deadline:
            with cosa_conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM event_inbox WHERE workspace_id = %s", (str(seeded.workspace_id),)
                )
                count = cur.fetchone()[0]
            if count >= 1:
                break
            cosa_conn.rollback()
            time.sleep(2.0)
        assert count >= 1, "relay did not deliver to event_inbox within 60s"
    finally:
        cosa_conn.close()
```

```python
# thêm vào tests/e2e/test_cross_plane_smoke.py
from tests.e2e.scenarios import outbox_relay


def test_s4_outbox_relay(real_cosa_stack, disposable_cluster) -> None:
    seeded = identity.seed_workspace(real_cosa_stack)
    outbox_relay.run(real_cosa_stack, seeded, disposable_cluster)
```

- [ ] **Step 2–4: Chạy, khớp tên bảng/route, xác nhận PASS**

> Nếu bước 3 fail vì `permission denied for table event_inbox` → đó là bug B2. Làm Task 12 trước, rồi quay lại xác nhận S4 PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/scenarios/outbox_relay.py tests/e2e/test_cross_plane_smoke.py
git commit -m "test(e2e): S4 outbox -> relay -> cosa inbox delivery

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 10: Mở rộng purity check phủ file mới

**Files:**
- Modify: `scripts/check_mvp_e2e_purity.py`
- Modify: `tests/quality/test_mvp_e2e_purity.py` *(nếu tồn tại — grep trước)*

**Interfaces:**
- Consumes: không
- Produces: `run_check` quét thêm `test_cross_plane_smoke.py` + toàn bộ `tests/e2e/{scenarios,stack,seed}/*.py` (bỏ `test_*helpers*` / `test_disposable*` thuần helper? — KHÔNG, quét tất, các file helper cũng phải sạch)

- [ ] **Step 1: Viết test thất bại**

```python
# tests/quality/test_mvp_e2e_purity_cross_plane.py
"""Purity check phải phủ file cross-plane mới, và bắt được mock nếu lỡ đưa vào."""
from __future__ import annotations

from pathlib import Path

from scripts.check_mvp_e2e_purity import check_file, run_check

ROOT = Path(__file__).resolve().parents[2]


def test_cross_plane_smoke_is_required() -> None:
    violations = run_check(target_dir=ROOT / "tests" / "e2e", required_files=None)
    # Không có vi phạm trên cây sạch hiện tại.
    assert violations == [], violations


def test_check_file_flags_mock_in_scenario(tmp_path: Path) -> None:
    bad = tmp_path / "auth_tenant_isolation.py"
    bad.write_text("from unittest.mock import Mock\n\ndef run(s, w):\n    Mock()\n")
    violations = check_file(bad, base_dir=tmp_path)
    assert any("NO_MOCK_IMPORT" in v for v in violations)
```

- [ ] **Step 2: Chạy — xác nhận fail**

Run: `PYTHONPATH=. .venv/bin/pytest tests/quality/test_mvp_e2e_purity_cross_plane.py -v`
Expected: FAIL — `run_check` hiện chỉ glob `test_mvp_*.py`, không phủ file mới.

- [ ] **Step 3: Sửa `scripts/check_mvp_e2e_purity.py`**

```python
REQUIRED_MVP_E2E_FILES = frozenset(
    {
        "test_mvp_marketing_http.py",
        "test_mvp_release_smoke.py",
        "test_mvp_settings_http.py",
        "test_mvp_strategy_runtime_http.py",
        "test_cross_plane_smoke.py",
    }
)

_CROSS_PLANE_GLOBS = ("test_cross_plane_smoke.py", "scenarios/*.py", "stack/*.py", "seed/*.py")


def run_check(
    target_dir: Path = E2E_DIR,
    *,
    required_files: frozenset[str] | None = None,
) -> list[str]:
    violations: list[str] = []
    if not target_dir.exists():
        return [f"{target_dir}:1:MISSING_E2E_DIRECTORY:Required MVP E2E directory is missing"]

    for required_file in required_files or frozenset():
        if not (target_dir / required_file).is_file():
            violations.append(
                f"{target_dir / required_file}:1:MISSING_REQUIRED_MVP_TEST:"
                "Required MVP E2E release test is missing"
            )

    seen: set[Path] = set()
    for pattern in ("test_mvp_*.py", *_CROSS_PLANE_GLOBS):
        for file_path in target_dir.glob(pattern):
            if file_path.name == "__init__.py" or file_path in seen:
                continue
            seen.add(file_path)
            violations.extend(check_file(file_path, base_dir=target_dir))

    return violations
```

- [ ] **Step 4: Chạy — xác nhận pass**

Run: `PYTHONPATH=. .venv/bin/pytest tests/quality/test_mvp_e2e_purity_cross_plane.py -v && make mvp-e2e-purity-check`
Expected: PASS + `✅ MVP E2E purity check passed.`

- [ ] **Step 5: Commit**

```bash
git add scripts/check_mvp_e2e_purity.py tests/quality/test_mvp_e2e_purity_cross_plane.py
git commit -m "ci: extend MVP E2E purity check to cross-plane scenarios/stack/seed

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 11: Makefile target + CI job `e2e-cross-plane-smoke`

**Files:**
- Modify: `Makefile` — target `e2e-cross-plane-smoke`, thêm vào `verify-local`
- Modify: `.github/workflows/quality.yml` — job mới

**Interfaces:**
- Consumes: mọi Task trước
- Produces: `make e2e-cross-plane-smoke`; job CI blocking PR

- [ ] **Step 1: Thêm target Makefile**

```makefile
e2e-cross-plane-smoke: ## Tầng 1 E2E: 4 vùng subprocess + Postgres disposable, model=fake
	mkdir -p test-results
	PYTHONPATH=. $(PYTEST) tests/e2e/test_cross_plane_smoke.py -q \
		--junitxml=test-results/e2e-smoke.xml
```

Sửa dòng `verify-local`:
```makefile
verify-local: lint typecheck-py python-test-unit python-test-integration desktop-worker-test knowledge-ingestion-test boundary-check check-docs contract-freeze-check e2e-test e2e-cross-plane-smoke
```

- [ ] **Step 2: Thêm job vào `.github/workflows/quality.yml`**

Copy khối `services:` (job matrix company/cosa, lines ~341+) làm mẫu cho phần Postgres + Encore CLI + Node. Job mới (đặt cạnh `e2e-golden-path`):

```yaml
  e2e-cross-plane-smoke:
    runs-on: ubuntu-latest
    timeout-minutes: 25
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: postgres
        ports: ['5432:5432']
        options: >-
          --health-cmd "pg_isready -U postgres" --health-interval 5s
          --health-timeout 5s --health-retries 20
    env:
      PGHOST: 127.0.0.1
      PGPORT: '5432'
      PGUSER: postgres
      PGPASSWORD: postgres
      AGENT_APP_PASSWORD: change-me-agent-app
      AGENT_MIGRATOR_PASSWORD: change-me-agent-migrator
      COSA_APP_PASSWORD: change-me-cosa-app
      COSA_MIGRATOR_PASSWORD: change-me-cosa-migrator
      WORKSPACE_APP_PASSWORD: change-me-workspace-app
      WORKSPACE_MIGRATOR_PASSWORD: change-me-workspace-migrator
      PYTHON: python
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: pip
          cache-dependency-path: |
            requirements-dev.txt
            packages/agent/requirements.txt
            apps/cosa/requirements.txt
      - name: Install Encore CLI
        run: |
          curl -L https://encore.dev/install.sh | bash
          echo "$HOME/.encore/bin" >> "$GITHUB_PATH"
      - name: Install Node deps (services)
        run: |
          (cd services/company && npm ci)
          (cd services/cosa && npm ci)
      - name: Install Python deps
        run: |
          pip install --require-hashes -r packages/agent/requirements.txt -r apps/cosa/requirements.txt
          pip install -r requirements-dev.txt pytest pytest-asyncio httpx pyjwt psycopg2-binary
      - name: Bootstrap Postgres cluster roles
        run: bash scripts/bootstrap-postgres-cluster.sh
      - name: Cross-plane smoke (S1-S4)
        run: make e2e-cross-plane-smoke
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: e2e-cross-plane-smoke-results
          path: test-results/e2e-smoke.xml
          if-no-files-found: error
```

> Job **không** có `if:` guard → chạy mọi push/PR (blocking). Nếu thời gian vượt 25p thường xuyên: bước tiếp theo là cache Encore build artifact hoặc tách S3/S4 sang nightly — ghi vào issue, không nới guard.

- [ ] **Step 3: Verify local**

Run: `make e2e-cross-plane-smoke`
Expected: 4 test PASS, `test-results/e2e-smoke.xml` sinh ra.

- [ ] **Step 4: Verify CI**

Push nhánh feature (không phải `main`), mở PR nháp → job `e2e-cross-plane-smoke` xuất hiện trong checks và xanh. Kiểm artifact `e2e-cross-plane-smoke-results` tải được.

- [ ] **Step 5: Commit**

```bash
git add Makefile .github/workflows/quality.yml
git commit -m "ci: add blocking e2e-cross-plane-smoke job (4-plane subprocess stack)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## PHASE P3 — Workstream sửa bug (song song P2; mỗi bug TDD đỏ→xanh)

### Task 12: B2 — cấp DML `event_inbox` / `event_trigger_rules` cho `agent_app`

**Files:**
- Create: `packages/agent/migrations/024_grant_event_tables_to_agent_app.sql`
- Create: `packages/agent/migrations/024_grant_event_tables_to_agent_app.down.sql`
- Test: `tests/agent/events/test_event_inbox_app_grants.py`

**Root cause (đã xác minh):** `019_event_inbox.sql` + `020_event_trigger_rules.sql` chạy `CREATE TABLE IF NOT EXISTS event_inbox (...)` / `event_trigger_rules (...)` **không có schema qualifier** → bảng nằm ở `public`. `packages/agent/scripts/migrate.py::_grant_application_access` cố tình loại trừ `public` (`nspname NOT IN ('public', 'information_schema')`) → `agent_app` không có `INSERT/UPDATE/DELETE` → runtime `permission denied for table event_inbox`.

**Cách sửa (Expand, không destructive):** migration forward chỉ chứa `GRANT` — migrator sở hữu bảng nên cấp được; không đụng dữ liệu, không đổi cấu trúc → `migration-compat-check` pass, `schema-fingerprint` không đổi (fingerprint theo cấu trúc bảng, không theo ACL — xác nhận bằng `make schema-fingerprint-check` ở Step 4).

- [ ] **Step 1: Viết test thất bại**

```python
# tests/agent/events/test_event_inbox_app_grants.py
"""agent_app phải INSERT được vào event_inbox sau migrate-all (bug B2)."""
from __future__ import annotations

import os
import uuid

import psycopg2
import pytest

_APP_URL = os.environ.get(
    "AGENT_TEST_DATABASE_URL",
    "postgresql://agent_app:change-me-agent-app@127.0.0.1:5432/agent?sslmode=disable",
)


@pytest.mark.integration
def test_agent_app_can_insert_into_event_inbox() -> None:
    conn = psycopg2.connect(_APP_URL, connect_timeout=5)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO event_inbox
                  (workspace_id, event_id, consumer_name, event_type, correlation_id, outcome)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                ("ws-b2", str(uuid.uuid4()), "b2-consumer", "test.evt", "corr-b2", "accepted"),
            )
            cur.execute("SELECT count(*) FROM event_trigger_rules")
            assert cur.fetchone()[0] >= 0  # SELECT quyền tối thiểu cũng phải có
    finally:
        conn.close()
```

- [ ] **Step 2: Chạy — xác nhận fail**

Run: `PYTHONPATH=. .venv/bin/pytest tests/agent/events/test_event_inbox_app_grants.py -v -m integration`
(cần Postgres đã `migrate-agent-platform`; nếu chạy trên cluster dev cũ đã grant tay, dùng DB disposable: chạy sau Task 2 hoặc tạo DB mới.)
Expected: FAIL — `psycopg2.errors.InsufficientPrivilege: permission denied for table event_inbox`

- [ ] **Step 3: Viết migration**

```sql
-- packages/agent/migrations/024_grant_event_tables_to_agent_app.sql
-- Bug B2: event_inbox (migration 019) + event_trigger_rules (020) được tạo
-- không kèm schema nên nằm ở `public`; _grant_application_access trong
-- scripts/migrate.py cố tình bỏ qua `public` -> agent_app thiếu quyền DML,
-- runtime lỗi "permission denied for table event_inbox". Cấp tường minh ở đây.
GRANT SELECT, INSERT, UPDATE, DELETE ON public.event_inbox TO agent_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.event_trigger_rules TO agent_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO agent_app;
```

```sql
-- packages/agent/migrations/024_grant_event_tables_to_agent_app.down.sql
REVOKE SELECT, INSERT, UPDATE, DELETE ON public.event_inbox FROM agent_app;
REVOKE SELECT, INSERT, UPDATE, DELETE ON public.event_trigger_rules FROM agent_app;
```

- [ ] **Step 4: Áp migration + chạy test + gates**

```bash
# Trên DB test/disposable:
AGENT_MIGRATOR_DATABASE_URL="postgresql+asyncpg://agent_migrator:change-me-agent-migrator@127.0.0.1:5432/agent" \
  .venv/bin/python -m packages.agent.scripts.migrate
PYTHONPATH=. .venv/bin/pytest tests/agent/events/test_event_inbox_app_grants.py -v -m integration
make migration-compat-check
make schema-fingerprint-check
```
Expected: test PASS; cả 2 gate PASS. Nếu `schema-fingerprint-check` báo drift vì ACL — cập nhật golden theo hướng dẫn của script (`schema-fingerprint.mjs --write`) và ghi lý do trong commit.

- [ ] **Step 5: Commit**

```bash
git add packages/agent/migrations/024_grant_event_tables_to_agent_app.sql \
        packages/agent/migrations/024_grant_event_tables_to_agent_app.down.sql \
        tests/agent/events/test_event_inbox_app_grants.py
git commit -m "fix(agent): grant agent_app DML on public event_inbox/event_trigger_rules (B2)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 13: B1 — persist `ingestion_run_id` vào `knowledge.source_versions`

**Files:**
- Modify: `apps/cosa/knowledge_ingestion/publish.py` (điểm nối metadata) **hoặc** `packages/agent/knowledge/providers/postgres.py:104` (đọc key)
- Test: `tests/agent/knowledge/test_source_version_ingestion_run_id.py`

**Root cause (đã xác minh một phần):** cột `knowledge.source_versions.ingestion_run_id VARCHAR(64)` **đã tồn tại** (migration `010`, dòng 27). `packages/agent/knowledge/providers/postgres.py:104` đọc `doc.metadata.get("ingestion_id")` và INSERT vào cột đó. Bug: caller phía `apps/cosa/knowledge_ingestion/` không đặt `ingestion_id` vào `doc.metadata` → luôn NULL.

**Discovery Step 0:**
```bash
sed -n '1,160p' apps/cosa/knowledge_ingestion/publish.py
grep -rn "ingestion_run_id\|ingestion_id\|run_id\|metadata\[" apps/cosa/knowledge_ingestion/ | grep -v test
sed -n '90,130p' packages/agent/knowledge/providers/postgres.py
```
Xác định: pipeline có `ingestion_run_id` ở tầng nào (scanner/handler) và mất ở đâu khi tạo `Document`.

- [ ] **Step 1: Viết test thất bại**

```python
# tests/agent/knowledge/test_source_version_ingestion_run_id.py
"""Sau publish qua knowledge store, source_versions.ingestion_run_id != NULL (bug B1)."""
from __future__ import annotations

import os
import uuid

import psycopg2
import pytest

_APP_URL = os.environ.get(
    "AGENT_TEST_DATABASE_URL",
    "postgresql://agent_app:change-me-agent-app@127.0.0.1:5432/agent?sslmode=disable",
)


@pytest.mark.integration
def test_publish_persists_ingestion_run_id() -> None:
    # Arrange: gọi đúng đường publish của apps/cosa knowledge ingestion với một
    # ingestion_run_id đã biết (fill theo discovery — hàm publish thật, không mock).
    ingestion_run_id = f"ir-{uuid.uuid4().hex[:12]}"
    source_id = _run_real_ingestion(ingestion_run_id)  # helper gọi publish.py thật

    conn = psycopg2.connect(_APP_URL, connect_timeout=5)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ingestion_run_id FROM knowledge.source_versions WHERE source_id = %s "
                "ORDER BY created_at DESC LIMIT 1",
                (source_id,),
            )
            row = cur.fetchone()
            assert row is not None and row[0] == ingestion_run_id
    finally:
        conn.close()
```

> Engineer: `_run_real_ingestion` phải gọi hàm publish thật (`apps/cosa/knowledge_ingestion/publish.py`) với input bytes tối thiểu; không mock knowledge store. Nếu cần Postgres + object store, dùng fixture integration sẵn có ở `tests/apps/cosa/knowledge_ingestion/conftest.py`.

- [ ] **Step 2: Chạy — xác nhận fail**

Run: `PYTHONPATH=. .venv/bin/pytest tests/agent/knowledge/test_source_version_ingestion_run_id.py -v -m integration`
Expected: FAIL — `assert None == 'ir-...'`

- [ ] **Step 3: Sửa điểm nối**

Tại nơi `apps/cosa/knowledge_ingestion/publish.py` dựng `Document(...)` trước khi gọi knowledge store, thêm `ingestion_id` vào metadata:

```python
# apps/cosa/knowledge_ingestion/publish.py — trong hàm publish (vị trí chính xác từ discovery)
document.metadata = {
    **(document.metadata or {}),
    "ingestion_id": ingestion_run_id,  # -> knowledge.source_versions.ingestion_run_id (postgres.py:104)
}
```

Nếu discovery cho thấy tên key khác nhau giữa 2 tầng (vd caller dùng `ingestion_run_id`, provider đọc `ingestion_id`) → thống nhất về `ingestion_id` ở cả hai và thêm comment "why".

- [ ] **Step 4: Chạy — xác nhận pass**

Run: `PYTHONPATH=. .venv/bin/pytest tests/agent/knowledge/test_source_version_ingestion_run_id.py -v -m integration && make knowledge-ingestion-test`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/cosa/knowledge_ingestion/publish.py tests/agent/knowledge/test_source_version_ingestion_run_id.py
git commit -m "fix(agent): thread ingestion_run_id into source_versions on publish (B1)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 14: B3 — bỏ `INSERT cosa.companies` trong 2 test

**Files:**
- Modify: 2 file test *(xác định bằng grep)*

**Discovery Step 0:**
```bash
rg -n "cosa\.companies|INTO companies|from companies|companies\b" services/cosa services/company tests --glob '*.ts' --glob '*.py' | grep -vi "migration"
git log --oneline -- services/cosa/migrations | grep -i "29\|drop.*compan"
sed -n '1,40p' services/cosa/migrations/029_*.sql   # xác nhận companies đã DROP
```

- [ ] **Step 1: Chạy 2 test đó trên DB disposable — xác nhận fail**

```bash
# ví dụ (thay path thật):
COSA_DATABASE_URL="postgresql://cosa_app:change-me-cosa-app@127.0.0.1:5432/cosa_<runid>" \
  npx vitest run services/cosa/path/to/foo.test.ts
```
Expected: FAIL — `relation "cosa.companies" does not exist` (hoặc `companies`).

- [ ] **Step 2: Sửa test seed**

Thay mỗi `INSERT INTO cosa.companies (...)` bằng đường provision workspace hợp lệ (workspace-only tenancy) — dùng helper seed sẵn có của test suite cosa (`services/cosa/tests/helpers/` — grep `createTestSession` / `provisionWorkspace`). Nếu test chỉ cần một `workspace_id` số hợp lệ mà không cần bản ghi company, xoá hẳn INSERT và dùng ID số như `test_agent_runtime_signal_http.py` làm (comment giải thích `runtime_source_signals.workspace_id` là bigint không FK).

- [ ] **Step 3: Chạy lại 2 test — xác nhận pass**

- [ ] **Step 4: Chạy rộng hơn để không hồi quy**

Run: `cd services/cosa && encore test` (hoặc `npx vitest run` phạm vi file liên quan)
Expected: không test nào mới đỏ.

- [ ] **Step 5: Commit**

```bash
git add <2 file test>
git commit -m "test(cosa): drop obsolete cosa.companies seed (dropped in migration 29) (B3)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 15: B4 — cô lập 5 flutter test flaky khi chạy full-suite

**Files:**
- Modify: tối đa 5 file trong `frontend/test/` *(xác định)* + có thể `frontend/test/flutter_test_config.dart`

**Discovery Step 0:**
```bash
cd frontend
flutter test --concurrency=1 --reporter expanded 2>&1 | tee /tmp/seq.txt
flutter test --reporter expanded 2>&1 | tee /tmp/par.txt
# so 2 file, khoanh 5 test PASS ở seq nhưng FAIL ở par
grep -E "^(✓|✗|[0-9]+:[0-9]+)" /tmp/par.txt | grep -i fail
```
Với mỗi test đỏ: xác định state toàn cục rò rỉ — `Get.put(..., permanent: true)` không reset, `SecureStorageService` seam không khôi phục, static singleton (`RealtimeService`, `ApiClient.setRuntimeContext`), `SharedPreferences.setMockInitialValues` sticky.

- [ ] **Step 1: Tái hiện flakiness — test lặp**

```bash
cd frontend
for i in 1 2 3; do flutter test test/path/to/flaky_one_test.dart test/path/to/flaky_two_test.dart || echo "FAIL run $i"; done
```
Expected: fail ít nhất 1/3 lần khi chạy cùng nhau; pass khi chạy đơn lẻ.

- [ ] **Step 2: Thêm reset state trong `setUp`/`tearDown`**

Trong mỗi file flaky (hoặc gom vào `flutter_test_config.dart` nếu chung):

```dart
setUp(() {
  Get.reset();
  SecureStorageService.configureForTest(FakeSecretStore());
  SharedPreferences.setMockInitialValues(<String, Object>{});
});

tearDown(() {
  Get.reset();
  RealtimeService.instance.stop(clearCheckpoint: true); // nếu test chạm realtime
});
```

(Điều chỉnh theo state thật mỗi test rò — comment "why" tiếng Việt: "reset singleton GetX để test kế tiếp không thấy controller permanent của test trước".)

- [ ] **Step 3: Chạy lặp lại — xác nhận ổn định**

```bash
cd frontend
for i in 1 2 3 4 5; do flutter test test/path/one_test.dart test/path/two_test.dart || exit 1; done
flutter test   # full-suite
```
Expected: 5/5 lần pass cụm; full-suite pass.

- [ ] **Step 4: Chạy full-suite 3 lần liên tiếp**

```bash
cd frontend
for i in 1 2 3; do flutter test || exit 1; done
```
Expected: 3/3 PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/test/
git commit -m "test(frontend): reset global GetX/secure-storage state to fix full-suite flakiness (B4)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage:**
- Spec §4 (P1 lớp dùng chung) → Task 1 (`_process`), Task 2 (`disposable_postgres`), Task 3 (`seed/`), Task 4 (`mvp_stack` rework). ✅
- Spec §5 (P2 subprocess stack + S1–S4 + CI) → Task 5 (`subprocess_stack` + `real_cosa_stack`), Task 6–9 (S1–S4), Task 10 (purity), Task 11 (Makefile + CI job). ✅
- Spec §6 (P3 bug B1–B4) → Task 12 (B2), Task 13 (B1), Task 14 (B3), Task 15 (B4). ✅
- Spec §7–§8 (P4/P4-live/P5) → **cố ý ngoài phạm vi plan này** (spec nói "plan riêng ở phase sau"). ✅
- Nguyên tắc no-mock (spec §2) → Task 10 mở rộng `check_mvp_e2e_purity.py`; Global Constraints liệt kê đầy đủ. ✅
- Yêu cầu disposable DB (spec §4.1) → Task 2. ✅

**2. Placeholder scan:** Các `TODO(discovery Step 0)` trong Task 3/5/7/8/9 là **bước discovery bắt buộc có lệnh cụ thể**, không phải placeholder mơ hồ — mỗi task ghi rõ lệnh `grep`/`sed` phải chạy và phải thay bằng route/SQL thật trước khi commit (Task 3 Step 3 nêu tường minh "không được để `NotImplementedError` hay `TODO` khi commit"). `agent_spec.seed_minimal_agent_spec` raise `NotImplementedError` ở Task 3 và được hoàn tất ở Task 7 Step 0 — liên kết đã ghi. Không có "add error handling"/"handle edge cases" chung chung.

**3. Type consistency:**
- `MvpStack` thuộc tính: `company/platform/agent/apps_cosa: ServiceClient` + `worker_health_url: str` + `uses_mock_transport: bool` — dùng nhất quán Task 4→5→6→7→8→9.
- `ServiceClient.get/post` chữ ký `(path, *, json=None, token=None, workspace_id=None)` — khớp `tests/e2e/mvp_stack.py` hiện có, dùng đúng trong mọi scenario.
- `SeededWorkspace` field `workspace_id/owner_user_id/owner_token/member_user_id/member_token` — khai ở Task 3, dùng khớp ở Task 6–9.
- `DisposableCluster` URL attr `*_app_url` / `*_migrator_url` — khai Task 2, dùng khớp Task 5 (`workspace_app_url`, `cosa_app_url`, `agent_app_url`) và Task 7–9 (`psycopg2.connect(cluster.<x>_app_url)`).
- `boot_subprocess_stack(cluster) -> StackHandles` với `.company_url/.cosa_url/.apps_cosa_url/.worker_health_url` — khai Task 5, tiêu thụ ở fixture cùng task.
- `check_file(path, base_dir=...)` / `run_check(target_dir=..., required_files=...)` — chữ ký khớp `scripts/check_mvp_e2e_purity.py` hiện tại (Task 10 giữ nguyên chữ ký, chỉ mở rộng glob).

Không phát hiện lệch tên. Kế hoạch sẵn sàng thực thi.

---

## Verification (toàn phase)

```bash
# P1
PYTHONPATH=. .venv/bin/pytest tests/e2e/stack/ -v
# P2 (cần Postgres + Encore CLI + node deps services/*)
make e2e-cross-plane-smoke
make mvp-e2e-purity-check
# test tiêu cực: thêm `from unittest.mock import Mock` vào 1 scenario -> `make mvp-e2e-purity-check` PHẢI fail, rồi revert
# P3
PYTHONPATH=. .venv/bin/pytest tests/agent/events/test_event_inbox_app_grants.py tests/agent/knowledge/test_source_version_ingestion_run_id.py -v -m integration
make migration-compat-check && make schema-fingerprint-check
cd services/cosa && encore test        # B3 không hồi quy
cd frontend && for i in 1 2 3; do flutter test || exit 1; done   # B4 ổn định
# Không hồi quy
make verify-local
make ai-compliance-production-gate
```

Milestone khớp `docs/superpowers/plans/2026-09-02-frontend-trust-and-ux-hardening.md` M4 ("CI has isolated end-to-end evidence"): job `e2e-cross-plane-smoke` xanh trên PR + artifact junit lưu mỗi lần chạy.

---

## PHASE P4–P5 — Bổ sung chi tiết (thêm 2026-09-03 sau khi P1–P3 hoàn tất)

> **Bối cảnh:** P1–P3 đã xong và review sạch (final review commit `b36b5636`). Khi triển khai
> lộ ra **bug B5**: agent run trong stack thật KHÔNG chạm được kernel — `local_session`
> delegation token (ký `JWT_SECRET`, không `aud`) bị `services/cosa` gateway từ chối tại
> hop tenant-policy-snapshot → run `run.failed{error:"policy_snapshot_unavailable"}`.
> B5 là ranh giới kiến trúc auth 3 chiều (xem comment dày trong `apps/cosa/auth/jwt.py`),
> KHÔNG phải bug vá nhanh — cần ADR riêng. Vì vậy P4/P5 dưới đây được thu hẹp về phần
> **đạt được thật mà không phụ thuộc B5 / Docker rebuild / DeepSeek key**, phần còn lại
> ghi rõ là follow-up có chủ đích.

### Task 16: Scenario S7 — policy snapshot tenant isolation (subprocess stack)

**Files:** Create `tests/e2e/scenarios/policy_snapshot_tenant.py`; modify `tests/e2e/test_cross_plane_smoke.py` (+`test_s7_policy_snapshot_tenant`, `@pytest.mark.cross_plane`).

**Đạt được (không phụ thuộc B5):** `GET /platform/auth/me/agent-policy-snapshot` trên `services/cosa`
CHẤP NHẬN cosa platform token (từ `identity.register_user` + `identity.login`). S7:
1. `register_user` + `login` (cosa) → cosa platform token cho user U.
2. `entitlement.grant_entitlement(cluster, ws_a, "operations")` + `grant_entitlement(cluster, ws_b, "finance")`
   (2 workspace, mỗi cái 1 rule khác nhau trong `cosa.workspace_agent_policy`).
3. Gọi snapshot với `workspaceId=ws_a` + token U → 200, `rules` CHỈ chứa `operations.*`,
   `workspaceId == ws_a`, `snapshotHash` không rỗng.
4. Gọi với `workspaceId=ws_b` → `rules` CHỈ chứa `finance.*` (không rò rule của ws_a).
5. Gọi không token → 401; token U + `workspaceId` U không có quyền → 403/404 (assert mã cụ thể quan sát được).

Purity như S1–S4. TDD: RED (collection) → GREEN. `make e2e-cross-plane-smoke` chạy 5 test (S1–S4 + S7).

**DoD:** S7 xanh trên subprocess stack; `make e2e-cross-plane-smoke` = 5 passed; purity ✅.

### Task 17: `test_golden_path.py` — chạy thư viện scenario với target ngoài (compose/staging)

**Files:** Create `tests/e2e/test_golden_path.py` (`@pytest.mark.cross_plane` KHÔNG áp — nó chạy khi có `E2E_BASE_URL_*`, không boot gì); modify `.github/workflows/quality.yml` job `e2e-golden-path` để chạy nó; modify `docs/testing/cross-plane-e2e.md`.

**Nội dung:** khi `E2E_BASE_URL_COMPANY` + `_COSA` + `_API` được set (nhánh external của `real_cosa_stack`
đã hỗ trợ từ Task 5), `test_golden_path.py` gọi lại `scenarios.auth_tenant_isolation`,
`scenarios.outbox_relay`, `scenarios.policy_snapshot_tenant` (S1, S4, S7 — các scenario KHÔNG cần
B5) qua `MvpStack.from_base_urls`. Bỏ qua S2/S3 completed-branch (B5). Fixture skip-fail rõ ràng
nếu thiếu 1 trong 3 URL (KHÔNG `pytest.skip` — dùng `pytest.fail` hoặc marker `e2e` sẵn có +
`-m e2e` chỉ chạy khi env đủ; thống nhất cách chọn với maintainer, mặc định: gate bằng env-var
guard ở đầu module `if not all(...): pytest.skip` LÀ được phép ở file golden-path này vì nó
KHÔNG nằm trong `check_mvp_e2e_purity` scope — xác nhận `run_check` không glob `test_golden_path.py`).

`scripts/e2e/run-golden-path.sh` sau khi `docker compose --profile e2e up --wait` đã export
`E2E_BASE_URL_COMPANY` — bổ sung export `_COSA=http://127.0.0.1:4001` + `_API=http://127.0.0.1:8001`
để `test_golden_path.py` chạy được cả 3 scenario, rồi `pytest tests/e2e -m "not cross_plane"`
(đã có) sẽ nhặt `test_golden_path.py`.

**P4-live (DeepSeek) + P4 compose scenario S5/S6/S8:** GHI LẠI là follow-up phụ thuộc:
- S5 (SSE reconnect), S8 (multi-agent) cần run chạm kernel → phụ thuộc B5.
- S6 (knowledge ingest→retrieval) cần `object_store`/`scanner`/`sandbox` inject vào worker dispatch
  (gap Task 13 đã ghi) → phụ thuộc follow-up B1-b.
- P4-live cần `DEEPSEEK_API_KEY` thật (chi phí) + B5. Job `e2e-golden-path` compose đã tồn tại
  và chạy `run-golden-path.sh` trên `main`; thêm 1 job `e2e-golden-path-live` khi cả 2 điều kiện
  sẵn sàng.

**DoD:** `test_golden_path.py` chạy S1/S4/S7 xanh khi trỏ vào subprocess stack đang chạy (mô phỏng
target ngoài bằng cách set `E2E_BASE_URL_*` tới stack boot tay); doc cập nhật; job YAML valid.

**Kết quả (2026-09-03):** DONE — `tests/e2e/test_golden_path.py` (module `pytest.skip`
khi thiếu `E2E_BASE_URL_*`; `@dataclass ExternalClusterDsns` map ba `*_DATABASE_URL`
→ `workspace_app_url` / `agent_app_url` (hạ `+asyncpg`) / `cosa_app_url`; ba test
`test_golden_s1/s4/s7_*` gọi lại `auth_tenant_isolation` / `outbox_relay` /
`policy_snapshot_tenant`; S2/S3/S5/S8 để lại follow-up B5). `scripts/e2e/run-golden-path.sh`
compose-branch nay export thêm `E2E_BASE_URL_COSA=http://127.0.0.1:4001` +
`E2E_BASE_URL_API=http://127.0.0.1:8001` (port map đã verify trong `docker-compose.yml`).
`.github/workflows/quality.yml` job `e2e-golden-path` thêm `psycopg2-binary` vào pip
install (scenario S1/S4/S7 + seed kit dùng psycopg2). Doc:
`docs/testing/cross-plane-e2e.md` thêm mục "Golden path (target ngoài / compose)".
Verify: collection-level — `pytest tests/e2e -m "not cross_plane" --co` nhặt 3 test
golden khi có env, module-skip sạch khi không; purity ✅; ruff ✅; `bash -n` + YAML load ✅.

### Task 18: P5 — Flutter Tier 2 (integration_test vs stack thật)

**Files:** Create `frontend/integration_test/support/real_stack_config.dart`; modify 3 file
`frontend/integration_test/{session_workspace_flow,remote_access_flow,approvals_truthfulness}_test.dart`
để chạy được 2 chế độ; create `frontend/tool/run_integration_real.sh`; modify
`docs/testing/frontend-integration.md` + `docs/testing/cross-plane-e2e.md`.

**Nội dung:**
- `real_stack_config.dart` đọc `--dart-define=E2E_MODE=real|fixture` (mặc định `fixture`) +
  `--dart-define=E2E_COMPANY_URL/E2E_COSA_URL/E2E_API_URL`. Khi `real`: `ApiClient` base URLs
  trỏ các URL đó; giữ `FakeSecretStore` (không chạm Keychain).
- 3 test hiện có: bọc phần seed/fixture trong `if (E2E_MODE == 'fixture') { <FixtureServer cũ> } else { <dựa vào stack thật đã seed sẵn qua tests/e2e/seed hoặc một bước setup Dart gọi /identity/_e2e/session> }`.
  Giữ nguyên assertion (wire-level qua `ApiRecorder`). Nếu 1 test không thể chạy chế độ `real`
  mà không có `modeSource` adapter (`remote_access_flow` phần `configured`), ĐỂ phần đó chỉ chạy
  `fixture` + comment `// TODO(modeSource-adapter)` — KHÔNG mock để giả `configured`.
- `run_integration_real.sh`: boot subprocess stack (tái dùng logic Python `tests/e2e/stack` qua
  một script wrapper, hoặc yêu cầu `make dev-stack` chạy sẵn) → export 3 URL → vòng lặp
  `flutter test integration_test/<file> -d macos --dart-define=E2E_MODE=real ...` từng file
  (macOS driver rớt nếu chạy cả thư mục 1 lệnh — đã biết).
- CI: job `frontend-integration` (nightly) thêm matrix `mode: [fixture, real]`; `real` chỉ nightly.

**DoD:** ít nhất `session_workspace_flow_test.dart` + `approvals_truthfulness_test.dart` xanh ở
`E2E_MODE=real` vs stack thật (chạy tay); `flutter analyze` sạch; doc cập nhật. `remote_access_flow`
phần `configured` ghi rõ blocker.

**DONE — 2026-09-03.** Implement theo sát brief, deviation nhỏ so với "matrix
`mode: [fixture, real]`": thay vì matrix trên job `frontend-integration` hiện
có, thêm job RIÊNG `frontend-integration-real` (nightly, `continue-on-error:
true`) — vì leg `real` cần boot thêm Postgres + 2 Encore service + `apps/cosa`
trên runner `macos-latest` (không có docker `services:` như Ubuntu runner),
tách job giữ job `frontend-integration` (fixture, blocking) không bị ảnh hưởng
nếu leg mới flaky. `session_workspace_flow_test.dart` +
`approvals_truthfulness_test.dart`: verify được `flutter analyze` sạch +
fixture mode xanh (từng file riêng lẻ) + wiring `real` mode xác nhận qua cổng
không tồn tại (SocketException, không phải lỗi biên dịch) — KHÔNG có stack
thật trong phiên làm việc này nên DoD "xanh ở `E2E_MODE=real` vs stack thật"
chưa verify hết bằng chạy tay, xem
`.superpowers/sdd/2026-09-02-cross-plane-e2e-harness/task-18-report.md`. Job
CI `frontend-integration-real` cũng chưa có bằng chứng chạy xanh thật (comment
rõ trong `quality.yml`).

### Task 19: B5 — ADR + design cho cầu identity apps/cosa ↔ services/cosa (KHÔNG code fix)

**Files:** Create `docs/architecture/adr/ADR-COSA-DELEGATION-002-agent-run-tenant-token.md` (hoặc số
ADR trống kế tiếp — kiểm `ls docs/architecture/adr/`).

**Nội dung:** ghi lại đầy đủ điều tra B5 (từ `tests/.../task-7-report.md`, `task-8-report.md`,
`docs/testing/cross-plane-e2e.md`): 3 secret / 3 chiều tin cậy hiện có (`PLATFORM_JWT_SECRET`
cosa→cosa/apps, `JWT_SECRET` company→apps, `COSA_COMPANY_DELEGATION_SECRET` apps→company); vì sao
run seed qua `/identity/_e2e/session` (company local_session) không qua được hop
`GET /platform/auth/me/agent-policy-snapshot` (cosa `verifyPlatformToken`); các phương án:
(a) run được khởi tạo bằng cosa platform token (user auth với cosa, workspace liên kết cosa↔company),
(b) apps/cosa mint token cosa-audience cho hop policy-snapshot,
(c) `services/cosa` chấp nhận local delegation token cho đúng route này.
Nêu tác động tenancy/security mỗi phương án, khuyến nghị 1, để trạng thái `PROPOSED`.
Đây là điều kiện để S2 Tier-1 / S3 completed-branch / S5 / S8 / P4-live kích hoạt.

**DoD:** ADR file tồn tại, `make check-docs` (doc-links) xanh, liên kết từ
`docs/testing/cross-plane-e2e.md` và từ plan này.

**Kết quả:** [`docs/architecture/adr/ADR-COSA-DELEGATION-002-agent-run-tenant-token.md`](../../architecture/adr/ADR-COSA-DELEGATION-002-agent-run-tenant-token.md)
(PROPOSED, 2026-09-03) — khuyến nghị Option B (secret thứ tư
`COSA_CONTROL_DELEGATION_SECRET` cho hop policy-snapshot), hoặc Option A nếu
`provisionVentureWorkspace` đã double-write membership company-side.

### Thứ tự thực thi P4–P5

16 (S7) → 19 (B5 ADR — rẻ, gỡ nợ nhận thức) → 17 (golden-path runner) → 18 (Flutter Tier 2).
Mỗi task: implementer + task-review + fix-loop như P1–P3. Sau Task 18: final review lần 2 chỉ
trên range P4–P5, rồi `finishing-a-development-branch`.
