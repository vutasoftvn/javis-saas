"""Fixture khởi động Company service (Encore/TypeScript) THẬT cho
`tests/e2e/test_ai_compliance_company_http.py` (Task 10, plan
`2026-08-30-ai-compliance-production-hardening-reconciled.md`).

Audit đã xác nhận: bản trước dùng `httpx.MockTransport` tự viết + monkeypatch
`httpx.AsyncClient.__init__` toàn cục — đúng loại "fake snapshot client" mà
plan cấm, chỉ chuyển xuống 1 lớp sâu hơn. File này thay bằng: boot
`encore run` thật trên 1 cổng test riêng, áp migration company thật, seed dữ
liệu thật qua HTTP thật vào endpoint E2E-only
(`POST /finance-legal/ai-compliance/_e2e/seed`, tự nó gọi đúng service
function governance thật — xem
`services/company/finance-legal/services/ai-compliance-e2e-seed.service.ts`),
rồi để `AiComplianceClient` gọi HTTP thật vào Company service thật đó.

Nếu môi trường hiện tại thiếu `encore` CLI hoặc không kết nối được Postgres
test, test SKIP RÕ RÀNG kèm lý do — không bao giờ fallback âm thầm về mock.
"""

from __future__ import annotations

import contextlib
import os
import secrets
import shutil
import socket
import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass

import httpx
import pytest

from tests.e2e.stack.disposable_postgres import (
    DisposableCluster,
    apply_migrations,
    create_disposable_cluster,
    drop_disposable_cluster,
)

COMPANY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "services", "company")

# Cùng convention mật khẩu dev mặc định với `deploy/postgres/init/01-create-app-roles.sql`
# (fallback `${WORKSPACE_APP_PASSWORD:-change-me-workspace-app}`) và với job
# `services`/`ai-compliance-production-gate` trong `.github/workflows/quality.yml`.
_DEFAULT_DB_HOST = "127.0.0.1"
_DEFAULT_DB_PORT = "5432"
_DEFAULT_APP_PASSWORD = "change-me-workspace-app"
_DEFAULT_MIGRATOR_PASSWORD = "change-me-workspace-migrator"

_READY_TIMEOUT_SECONDS = 60.0


def _workspace_database_url() -> str:
    return os.environ.get(
        "WORKSPACE_DATABASE_URL",
        f"postgresql://workspace_app:{_DEFAULT_APP_PASSWORD}@{_DEFAULT_DB_HOST}:{_DEFAULT_DB_PORT}/workspace?sslmode=disable",
    )


def _workspace_migrator_database_url() -> str:
    return os.environ.get(
        "WORKSPACE_MIGRATOR_DATABASE_URL",
        f"postgresql://workspace_migrator:{_DEFAULT_MIGRATOR_PASSWORD}@{_DEFAULT_DB_HOST}:{_DEFAULT_DB_PORT}/workspace?sslmode=disable",
    )


def external_company_base_url() -> str | None:
    configured = os.environ.get("E2E_BASE_URL_COMPANY", "").strip()
    return configured.rstrip("/") or None


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _postgres_reachable(database_url: str) -> tuple[bool, str]:
    try:
        import psycopg2
    except ImportError:
        # psycopg2 không phải dependency Python chuẩn của repo — dùng `psql`
        # CLI (đã có sẵn trong deploy/CI) làm probe thay thế thay vì thêm
        # dependency chỉ để kiểm tra kết nối.
        psql = shutil.which("psql")
        if not psql:
            return False, "neither psycopg2 nor psql CLI is available to probe Postgres"
        try:
            result = subprocess.run(
                [psql, database_url, "-c", "select 1;"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except Exception as err:  # pragma: no cover - defensive
            return False, f"psql probe failed to run: {err}"
        if result.returncode != 0:
            return False, f"psql probe failed: {result.stderr.strip()}"
        return True, ""
    try:
        conn = psycopg2.connect(database_url, connect_timeout=5)
        conn.close()
        return True, ""
    except Exception as err:  # pragma: no cover - defensive
        return False, str(err)


@dataclass
class CompanyServiceHandle:
    base_url: str


def count_runtime_source_signals(
    workspace_id: str, source_kind: str, source_id: str, sequence: int
) -> int:
    """Đếm số hàng projection `operating.runtime_source_signals` cho một identity
    (workspace_id, source_kind, source_id, sequence) — dùng để chứng minh
    idempotency của POST /events/internal/agent-runtime-signal trên service thật:
    gửi 2 lần cùng identity phải chỉ tạo đúng 1 hàng (unique constraint trong
    migration 33)."""
    import psycopg2

    conn = psycopg2.connect(_workspace_database_url(), connect_timeout=5)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM operating.runtime_source_signals "
                "WHERE workspace_id = %s AND source_kind = %s AND source_id = %s AND sequence = %s",
                (int(workspace_id), source_kind, source_id, sequence),
            )
            row = cur.fetchone()
            return int(row[0]) if row else 0
    finally:
        conn.close()


def _wait_until_ready(base_url: str, proc: subprocess.Popen) -> None:
    deadline = time.monotonic() + _READY_TIMEOUT_SECONDS
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(
                f"`encore run` exited early with code {proc.returncode} before becoming ready — "
                "see captured stdout/stderr in the pytest failure output above"
            )
        try:
            resp = httpx.get(f"{base_url}/healthz", timeout=2.0)
            if resp.status_code in (200, 503):
                # 503 nghĩa là app đã lên nhưng DB probe riêng của healthz lỗi —
                # vẫn coi là "server thật đã sẵn sàng nhận request" cho mục
                # đích fixture này; DB reachability đã được verify riêng ở
                # bước _postgres_reachable trước khi spawn.
                return
        except httpx.HTTPError as err:
            last_error = err
        time.sleep(0.5)
    raise RuntimeError(
        f"Company service did not become ready within {_READY_TIMEOUT_SECONDS}s: {last_error}"
    )


@pytest.fixture(scope="session")
def real_company_service() -> Iterator[CompanyServiceHandle]:
    configured_base_url = external_company_base_url()
    if configured_base_url:
        try:
            response = httpx.get(f"{configured_base_url}/healthz", timeout=10.0)
        except httpx.HTTPError as err:
            pytest.fail(
                f"Configured E2E Company service is unreachable at {configured_base_url}: {err}"
            )
        if response.status_code != 200:
            pytest.fail(
                "Configured E2E Company service did not report ready health at "
                f"{configured_base_url}/healthz: {response.status_code} {response.text}"
            )
        yield CompanyServiceHandle(base_url=configured_base_url)
        return

    encore_bin = shutil.which("encore")
    if not encore_bin:
        pytest.fail(
            "`encore` CLI not found on PATH — cannot boot a real Company service for this E2E "
            "gate. Install via https://encore.dev/install.sh (see .github/workflows/quality.yml "
            "'Install Encore CLI' step) instead of falling back to a mock transport."
        )

    db_url = _workspace_database_url()
    reachable, reason = _postgres_reachable(db_url)
    if not reachable:
        pytest.fail(
            f"Postgres at {db_url!r} is not reachable ({reason}) — cannot seed/boot a real "
            "Company service for this E2E gate. Start it via `make services-docker-up` + "
            "`scripts/bootstrap-postgres-cluster.sh` (or the CI 'services'/"
            "'ai-compliance-production-gate' Postgres service container) instead of falling "
            "back to a mock transport."
        )

    migrator_url = _workspace_migrator_database_url()
    migrate = subprocess.run(
        ["node", "scripts/migrate.mjs"],
        cwd=COMPANY_DIR,
        env={**os.environ, "WORKSPACE_MIGRATOR_DATABASE_URL": migrator_url},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if migrate.returncode != 0:
        pytest.fail(
            "Applying real company migrations failed before the E2E gate could boot a real "
            f"Company service:\nstdout:\n{migrate.stdout}\nstderr:\n{migrate.stderr}"
        )

    port = _pick_free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = {
        **os.environ,
        "WORKSPACE_DATABASE_URL": db_url,
        # Chỉ bật seed endpoint E2E-only cho đúng process test này — xem
        # guard fail-closed 2 lớp trong ai-compliance-e2e-seed.handler.ts.
        "E2E_TEST_SEED_ENABLED": "1",
    }
    proc = subprocess.Popen(
        [encore_bin, "run", f"--port={port}"],
        cwd=COMPANY_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_until_ready(base_url, proc)
        yield CompanyServiceHandle(base_url=base_url)
    finally:
        # try/finally — dừng subprocess kể cả khi test/setup phía trên fail,
        # không để `encore run` treo lại chiếm cổng cho lần chạy sau.
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=15)
        remaining_output = ""
        if proc.stdout:
            with contextlib.suppress(Exception):
                remaining_output = proc.stdout.read() or ""
        if proc.returncode not in (0, None, -15, -9) and remaining_output:
            # Log ra để debug CI mà không làm fail test đã pass — chỉ in.
            print(f"[real_company_service] encore run output:\n{remaining_output}")


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
