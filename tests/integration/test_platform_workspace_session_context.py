"""E2E HTTP integration coverage cho `GET /platform/workspaces/:workspaceId/session-context`
(Task 3 — Frontend Trust and UX Hardening, plan
`docs/superpowers/plans/2026-09-02-frontend-trust-and-ux-hardening.md`).

Endpoint này PHẢI là nguồn sự thật duy nhất, server-authoritative cho
workspace/role/runtimeMode/presence — test ở đây gọi HTTP THẬT vào một
instance `encore run` thật của `services/cosa` (không gọi hàm TypeScript trực
tiếp trong process Python, không mock transport), cùng pattern với
`tests/e2e/conftest.py::real_company_service` nhưng nhắm vào `services/cosa`
(một Encore app RIÊNG, có `encore.app` của chính nó — không cùng app với
`services/company`).

Nếu môi trường hiện tại thiếu `encore` CLI hoặc không kết nối được Postgres
test cho cosa, test FAIL rõ ràng kèm lý do — không bao giờ fallback âm thầm
về mock/skip im lặng.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import socket
import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass

import httpx
import pytest

COSA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "services", "cosa")

_DEFAULT_DB_HOST = "127.0.0.1"
_DEFAULT_DB_PORT = "5432"
_DEFAULT_COSA_APP_PASSWORD = "change-me-cosa-app"

_READY_TIMEOUT_SECONDS = 60.0


def _cosa_database_url() -> str:
    return os.environ.get(
        "COSA_DATABASE_URL",
        f"postgresql://cosa_app:{_DEFAULT_COSA_APP_PASSWORD}@{_DEFAULT_DB_HOST}:{_DEFAULT_DB_PORT}/cosa?sslmode=disable",
    )


def _external_cosa_base_url() -> str | None:
    configured = os.environ.get("E2E_BASE_URL_COSA", "").strip()
    return configured.rstrip("/") or None


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _postgres_reachable(database_url: str) -> tuple[bool, str]:
    try:
        import psycopg2
    except ImportError:
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
class CosaServiceHandle:
    base_url: str


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
                return
        except httpx.HTTPError as err:
            last_error = err
        time.sleep(0.5)
    raise RuntimeError(f"Cosa service did not become ready within {_READY_TIMEOUT_SECONDS}s: {last_error}")


@pytest.fixture(scope="module")
def real_cosa_service() -> Iterator[CosaServiceHandle]:
    configured_base_url = _external_cosa_base_url()
    if configured_base_url:
        try:
            response = httpx.get(f"{configured_base_url}/healthz", timeout=10.0)
        except httpx.HTTPError as err:
            pytest.fail(f"Configured E2E Cosa service is unreachable at {configured_base_url}: {err}")
        if response.status_code != 200:
            pytest.fail(
                "Configured E2E Cosa service did not report ready health at "
                f"{configured_base_url}/healthz: {response.status_code} {response.text}"
            )
        yield CosaServiceHandle(base_url=configured_base_url)
        return

    encore_bin = shutil.which("encore")
    if not encore_bin:
        pytest.fail(
            "`encore` CLI not found on PATH — cannot boot a real Cosa service for this "
            "integration gate. Install via https://encore.dev/install.sh instead of falling "
            "back to a mock transport."
        )

    db_url = _cosa_database_url()
    reachable, reason = _postgres_reachable(db_url)
    if not reachable:
        pytest.fail(
            f"Postgres at {db_url!r} is not reachable ({reason}) — cannot boot a real Cosa "
            "service for this integration gate. Start it via `make services-docker-up` (or the "
            "CI Postgres service container) instead of falling back to a mock transport."
        )

    port = _pick_free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = {**os.environ, "COSA_DATABASE_URL": db_url}
    proc = subprocess.Popen(
        [encore_bin, "run", f"--port={port}"],
        cwd=COSA_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        _wait_until_ready(base_url, proc)
        yield CosaServiceHandle(base_url=base_url)
    finally:
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
            print(f"[real_cosa_service] encore run output:\n{remaining_output}")


def _register(client: httpx.Client, email: str, workspace_name: str) -> tuple[str, str]:
    """Đăng ký user + venture workspace THẬT qua HTTP thật, trả về (access_token, workspace_id)."""
    res = client.post(
        "/platform/auth/register",
        json={"email": email, "password": "SecurePassword123", "workspace_name": workspace_name},
    )
    assert res.status_code == 200, f"registration failed ({res.status_code}): {res.text}"
    data = res.json()
    return data["access_token"], str(data["platform_workspace_id"])


def test_session_context_returns_only_the_authenticated_member_workspace(real_cosa_service) -> None:
    client = httpx.Client(base_url=real_cosa_service.base_url, timeout=10.0)
    token, workspace_id = _register(client, f"session-ctx-a-{time.time()}@example.com", "Session Ctx Venture A")

    res = client.get(
        f"/platform/workspaces/{workspace_id}/session-context",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["workspaceId"] == workspace_id
    assert body["role"] == "founder"
    assert body["asOf"].endswith("Z")
    # Server không nhận runtimeMode/presence từ request — workspace chưa đăng
    # ký runtime node nào ⇒ mặc định trung thực LOCAL_ONLY/OFFLINE.
    assert body["runtimeMode"] == "LOCAL_ONLY"
    assert body["presenceStatus"] == "OFFLINE"
    assert body["lastHeartbeatAt"] is None
    assert "workspace.session.read" in body["capabilities"]
    # Review fix (2026-09-02, Task 3 review "Needs fixes") — cosa chưa đọc
    # được cột runtime_mode canonical bên services/company, nên runtimeMode ở
    # endpoint này luôn là suy đoán (inferred) từ node presence, có thể SAI
    # so với cấu hình thật (không chỉ stale) — client không được coi nó như
    # sự thật đã xác minh tuyệt đối cho tới khi có adapter đọc cấu hình thật.
    assert body["runtimeModeSource"] == "inferred"


def test_session_context_denies_a_member_of_another_workspace(real_cosa_service) -> None:
    client = httpx.Client(base_url=real_cosa_service.base_url, timeout=10.0)
    _, workspace_a = _register(client, f"session-ctx-b-owner-{time.time()}@example.com", "Session Ctx Venture B-owner")
    token_outsider, _ = _register(client, f"session-ctx-b-outsider-{time.time()}@example.com", "Session Ctx Venture B-outsider")

    res = client.get(
        f"/platform/workspaces/{workspace_a}/session-context",
        headers={"Authorization": f"Bearer {token_outsider}"},
    )
    assert res.status_code == 403, res.text
    assert res.json()["code"] == "permission_denied"
