"""Boot 4 vùng kiến trúc THẬT bằng subprocess cho E2E Tầng 1 (không Docker).

Mở rộng pattern `tests/e2e/conftest.py::real_company_service` sang cả 4 plane,
tất cả trỏ vào một `DisposableCluster` duy nhất:

    company (Encore/TS)  →  cosa (Encore/TS)  →  apps/cosa API (uvicorn)  →  worker

Mỗi bước health-gated trước khi spawn bước kế: nếu company chưa xanh thì cosa
chưa boot, v.v. — thứ tự này khớp chiều phụ thuộc runtime (cosa gọi company,
apps/cosa gọi cả hai, worker poll scheduler của cosa).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field

from tests.e2e.stack._process import (
    ManagedProc,
    pick_free_port,
    spawn,
    terminate_all,
    wait_until_ready,
)
from tests.e2e.stack.disposable_postgres import DisposableCluster

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
_PYTHON = os.environ.get("PYTHON", os.path.join(_REPO_ROOT, ".venv", "bin", "python"))

# Secrets dev từ `.env.e2e` — non-strict env (`APP_ENV=development`) chấp nhận
# các giá trị này; `validate_service_identity` chỉ siết ở staging/production.
_SECRETS = {
    "PLATFORM_JWT_SECRET": "cosa-super-secret-platform-jwt-key-change-in-prod",
    "WORKER_SERVICE_JWT_SECRET": "cosa-worker-service-jwt-key-change-in-prod-min32chars",
    "JWT_SECRET": "cosa-dev-jwt-secret-do-not-use-in-prod",
}

# Encore compile cả 2 service TS ở lần chạy đầu -> boot có thể mất 60-180s;
# đó KHÔNG phải treo. Cho health-wait timeout rộng tay.
_ENCORE_READY_TIMEOUT_S = 240.0
_PY_READY_TIMEOUT_S = 180.0


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


def _asyncpg_url(url: str) -> str:
    """apps/cosa mở agent DB bằng driver `postgresql+asyncpg`; `DisposableCluster`
    phát app URL ở scheme `postgresql://` trần kèm `?sslmode=disable`.

    Hai việc phải làm: (1) đổi scheme sang `postgresql+asyncpg`, (2) bỏ RIÊNG
    param `sslmode` khỏi query (giữ nguyên các param khác) — asyncpg nhận param
    `ssl`, không hiểu `sslmode` và sẽ raise
    `connect() got an unexpected keyword argument 'sslmode'`."""
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    parts = urlsplit(url)
    scheme = parts.scheme
    for prefix in ("postgresql+asyncpg", "postgresql", "postgres"):
        if scheme == prefix:
            scheme = "postgresql+asyncpg"
            break
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "sslmode"]
    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(kept), parts.fragment))


def _mint_worker_token(run_id: str) -> str:
    result = subprocess.run(
        ["node", "scripts/mint-worker-service-token.mjs", f"e2e-{run_id}"],
        cwd=_REPO_ROOT,
        env={**os.environ, "WORKER_SERVICE_JWT_SECRET": _SECRETS["WORKER_SERVICE_JWT_SECRET"]},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(f"mint worker token failed: {result.stdout}\n{result.stderr}")
    return result.stdout.strip()


def _clean_env(**overrides: str) -> dict[str, str]:
    """Build env con từ bản sao sạch của `os.environ` rồi áp override tường minh.

    Ép `APP_ENV`/`ENVIRONMENT=development` để không bao giờ rơi vào nhánh strict
    hoặc nhánh `APP_ENV=test` (worker raise nếu `test` + `DEEPSEEK_API_KEY`)."""
    env = dict(os.environ)
    env["APP_ENV"] = "development"
    env["ENVIRONMENT"] = "development"
    env.update(_SECRETS)
    env.update(overrides)
    return env


def boot_subprocess_stack(cluster: DisposableCluster) -> StackHandles:
    encore = _require_encore()
    p_company, p_cosa, p_api, p_worker = (pick_free_port() for _ in range(4))
    company_url = f"http://127.0.0.1:{p_company}"
    cosa_url = f"http://127.0.0.1:{p_cosa}"
    api_url = f"http://127.0.0.1:{p_api}"
    worker_health_url = f"http://127.0.0.1:{p_worker}/live"  # worker health chỉ có /live + /ready
    worker_token = _mint_worker_token(cluster.run_id)
    procs: list[ManagedProc] = []

    try:
        # 1) company — Encore/TS. Chỉ cần DB workspace + seed endpoint E2E-only.
        company = spawn(
            "company",
            [encore, "run", f"--port={p_company}"],
            cwd=os.path.join(_REPO_ROOT, "services", "company"),
            env=_clean_env(
                WORKSPACE_DATABASE_URL=cluster.workspace_app_url,
                E2E_TEST_SEED_ENABLED="1",
                COSA_CONTROL_PLANE_URL=cosa_url,
                PLATFORM_API_BASE_URL=cosa_url,
            ),
        )
        procs.append(company)
        wait_until_ready(
            "company", f"{company_url}/healthz", company, timeout_s=_ENCORE_READY_TIMEOUT_S
        )

        # 2) cosa — Encore/TS. DB cosa + trỏ ngược về company cho callback.
        cosa = spawn(
            "cosa",
            [encore, "run", f"--port={p_cosa}"],
            cwd=os.path.join(_REPO_ROOT, "services", "cosa"),
            env=_clean_env(
                COSA_DATABASE_URL=cluster.cosa_app_url,
                COMPANY_SERVICE_URL=company_url,
            ),
        )
        procs.append(cosa)
        wait_until_ready("cosa", f"{cosa_url}/healthz", cosa, timeout_s=_ENCORE_READY_TIMEOUT_S)

        # Env chung cho 2 process Python — agent DB phải ở scheme asyncpg.
        common_py = dict(
            AGENT_DATABASE_URL=_asyncpg_url(cluster.agent_app_url),
            COSA_DATABASE_URL=cluster.cosa_app_url,
            COMPANY_SERVICE_URL=company_url,
            COSA_CONTROL_PLANE_URL=cosa_url,
            COSA_PLATFORM_CONTROL_PLANE_URL=cosa_url,
            COSA_EXECUTION_PLANE_URL=cosa_url,
            COSA_MODEL_PROVIDER="fake",
            COSA_WORKER_SERVICE_TOKEN=worker_token,
            # Khớp `pythonpath = [".", "packages", "apps"]` trong pyproject.toml —
            # `agent`, `agent_testkit` nằm dưới `packages/`, `apps.cosa` dưới root.
            PYTHONPATH=os.pathsep.join(
                (
                    _REPO_ROOT,
                    os.path.join(_REPO_ROOT, "packages"),
                    os.path.join(_REPO_ROOT, "apps"),
                )
            ),
        )

        # 3) apps/cosa API — uvicorn import `apps.cosa.api.main:app`.
        # Lifespan fail ASGI startup nếu thiếu DEEPSEEK_API_KEY, nên set cả key
        # giả LẪN COSA_MODEL_PROVIDER=fake (key giả không bao giờ được gọi thật).
        api = spawn(
            "apps_cosa_api",
            [
                _PYTHON,
                "-m",
                "uvicorn",
                "apps.cosa.api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(p_api),
            ],
            cwd=_REPO_ROOT,
            env=_clean_env(**common_py, DEEPSEEK_API_KEY="fake-deepseek-key-for-e2e"),
        )
        procs.append(api)
        wait_until_ready("apps_cosa_api", f"{api_url}/healthz", api, timeout_s=_PY_READY_TIMEOUT_S)

        # 4) worker — `python -m apps.cosa.worker.main`. Worker CHỈ dùng
        # FakeSDKModel khi DEEPSEEK_API_KEY UNSET (không đọc COSA_MODEL_PROVIDER),
        # nên phải pop key khỏi env con dù parent shell có set.
        worker_env = _clean_env(
            **common_py,
            COSA_WORKER_ID=f"e2e-{cluster.run_id}",
            COSA_WORKER_HEALTH_PORT=str(p_worker),
            COSA_WORKER_HEALTH_HOST="127.0.0.1",
        )
        worker_env.pop("DEEPSEEK_API_KEY", None)
        worker = spawn(
            "apps_cosa_worker",
            [_PYTHON, "-m", "apps.cosa.worker.main"],
            cwd=_REPO_ROOT,
            env=worker_env,
        )
        procs.append(worker)
        wait_until_ready(
            "apps_cosa_worker", worker_health_url, worker, timeout_s=_PY_READY_TIMEOUT_S
        )

        return StackHandles(company_url, cosa_url, api_url, worker_health_url, procs)
    except Exception:
        terminate_all(procs)
        raise


def teardown_subprocess_stack(handles: StackHandles) -> None:
    terminate_all(handles.procs)
