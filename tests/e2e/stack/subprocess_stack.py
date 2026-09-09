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
    # HMAC dùng chung cho local outbox relay (`services/company` ký) ↔ apps/cosa
    # intake (`/agent/internal/events` verify). Cả hai phía mặc định về
    # `"dev-secret"` khi biến này trống ở APP_ENV=development, nhưng set tường
    # minh (>= 32 ký tự) để relay POST được chấp nhận không phụ thuộc default.
    "COSA_LOCAL_SERVICE_SECRET": "cosa-local-service-hmac-secret-change-in-prod-32b",
    # Scoped cross-plane delegation (ADR-COSA-DELEGATION-002). Cả apps/cosa (ký)
    # và services/cosa / services/company (verify) đều fallback về đúng các dev
    # default này khi biến trống, nhưng pin tường minh để token B5
    # (`aud=cosa_control`, dùng cho agent-policy-snapshot) ký==verify không phụ
    # thuộc shell env của người chạy test. Đây là bug class B5 gốc:
    # forward nhầm token nên policy_snapshot_unavailable.
    "COSA_CONTROL_DELEGATION_SECRET": "cosa-control-delegation-dev-secret-change-in-prod",
    "COSA_COMPANY_DELEGATION_SECRET": "cosa-company-delegation-dev-secret-change-in-prod",
}

# Export công khai cho test signer (vd. `_sign_worker_token` trong
# test_lease_mutual_exclusion_real.py / test_crash_recovery_subprocess.py) — các
# test này PHẢI ký JWT bằng đúng secret cố định mà process isolated ở đây được
# boot bằng, KHÔNG được đọc `os.environ` (ambient fallback là chính bug class mà
# các test này được viết ra để chống). Đừng đổi giá trị này mà không đổi
# `_SECRETS["WORKER_SERVICE_JWT_SECRET"]` ở trên — hai bên phải luôn khớp nhau.
WORKER_SERVICE_JWT_SECRET = _SECRETS["WORKER_SERVICE_JWT_SECRET"]

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


def asyncpg_test_url(url: str) -> str:
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


def _spawn_api_and_worker(
    cluster: DisposableCluster,
    *,
    company_url: str,
    cosa_url: str,
    api_url: str,
    p_api: int,
    worker_health_url: str,
    p_worker: int,
    worker_token: str,
    extra_py_env: dict[str, str] | None = None,
) -> tuple[ManagedProc, ManagedProc]:
    """Tách riêng phần spawn 2 process Python (api + worker) để dùng chung
    giữa `boot_subprocess_stack()` (boot lần đầu) và `restart_api_and_worker()`
    (Task 13, plan local-first-enterprise-knowledge — chứng minh durability
    thật qua restart process, không phải instance thứ hai trong cùng process,
    xem CLAUDE.md rule 6). `extra_py_env` merge THÊM vào `common_py` — dùng
    cho `KNOWLEDGE_INGESTION_ENABLED`/`COSA_WORKSPACE_STORAGE_ROOT` khi test
    cần bật knowledge ingestion, mặc định `None` giữ hành vi cũ nguyên vẹn."""
    common_py = dict(
        AGENT_DATABASE_URL=asyncpg_test_url(cluster.agent_app_url),
        COSA_DATABASE_URL=cluster.cosa_app_url,
        COMPANY_SERVICE_URL=company_url,
        COSA_CONTROL_PLANE_URL=cosa_url,
        COSA_PLATFORM_CONTROL_PLANE_URL=cosa_url,
        COSA_EXECUTION_PLANE_URL=cosa_url,
        COSA_MODEL_PROVIDER="fake",
        COSA_WORKER_SERVICE_TOKEN=worker_token,
        PYTHONPATH=os.pathsep.join(
            (
                _REPO_ROOT,
                os.path.join(_REPO_ROOT, "packages"),
                os.path.join(_REPO_ROOT, "apps"),
            )
        ),
        **(extra_py_env or {}),
    )

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
    wait_until_ready("apps_cosa_api", f"{api_url}/healthz", api, timeout_s=_PY_READY_TIMEOUT_S)

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
    wait_until_ready("apps_cosa_worker", worker_health_url, worker, timeout_s=_PY_READY_TIMEOUT_S)

    return api, worker


def restart_api_and_worker(
    handles: StackHandles,
    cluster: DisposableCluster,
    *,
    extra_py_env: dict[str, str] | None = None,
) -> StackHandles:
    """Task 13 — kill THẬT rồi respawn `apps_cosa_api`/`apps_cosa_worker` trên
    CÙNG port (company/cosa Encore giữ nguyên, không restart — chỉ 2 process
    Python là mục tiêu chứng minh durability của Workspace Runtime Node).
    Postgres/local storage không đổi qua lần restart này — nếu 1 upload/
    document sống sót thì đó là bằng chứng thật (không phải state giữ trong
    RAM của process cũ)."""
    from urllib.parse import urlsplit

    p_api = urlsplit(handles.apps_cosa_url).port
    p_worker = urlsplit(handles.worker_health_url).port
    if p_api is None or p_worker is None:
        raise RuntimeError(
            f"không parse được port từ {handles.apps_cosa_url!r}/{handles.worker_health_url!r}"
        )

    keep: list[ManagedProc] = []
    restart_targets: list[ManagedProc] = []
    for proc in handles.procs:
        if proc.name in ("apps_cosa_api", "apps_cosa_worker"):
            restart_targets.append(proc)
        else:
            keep.append(proc)
    terminate_all(restart_targets)

    worker_token = _mint_worker_token(cluster.run_id)
    api, worker = _spawn_api_and_worker(
        cluster,
        company_url=handles.company_url,
        cosa_url=handles.cosa_url,
        api_url=handles.apps_cosa_url,
        p_api=p_api,
        worker_health_url=handles.worker_health_url,
        p_worker=p_worker,
        worker_token=worker_token,
        extra_py_env=extra_py_env,
    )

    return StackHandles(
        handles.company_url,
        handles.cosa_url,
        handles.apps_cosa_url,
        handles.worker_health_url,
        [*keep, api, worker],
    )


def boot_subprocess_stack(
    cluster: DisposableCluster, *, extra_py_env: dict[str, str] | None = None
) -> StackHandles:
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
                # Đích relay outbox → apps/cosa intake. Mặc định code là
                # `http://127.0.0.1:8000`, sai khi stack dùng cổng động.
                COSA_AGENTOS_INTAKE_URL=api_url,
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

        # 3+4) apps/cosa API (uvicorn) + worker — factored ra
        # `_spawn_api_and_worker()` để `restart_api_and_worker()` (Task 13)
        # dùng chung logic, không lặp lại.
        api, worker = _spawn_api_and_worker(
            cluster,
            company_url=company_url,
            cosa_url=cosa_url,
            api_url=api_url,
            p_api=p_api,
            worker_health_url=worker_health_url,
            p_worker=p_worker,
            worker_token=worker_token,
            extra_py_env=extra_py_env,
        )
        procs.append(api)
        procs.append(worker)

        return StackHandles(company_url, cosa_url, api_url, worker_health_url, procs)
    except Exception:
        terminate_all(procs)
        raise


def boot_cosa_only(cluster: DisposableCluster) -> tuple[str, ManagedProc]:
    """Boot MỘT MÌNH `services/cosa` (Encore) trỏ vào DB disposable của
    `cluster`, trên cổng vừa reserve bằng `pick_free_port()` (không bao giờ
    cổng cố định — tránh đụng một `services/cosa` khác đang chạy sẵn ở máy
    dev). Dùng cho test chỉ cần lease/scheduled-tasks endpoint của Control
    Plane (vd. `tests/apps/cosa/worker/test_lease_mutual_exclusion_real.py`),
    không cần boot đủ 4 vùng kiến trúc như `boot_subprocess_stack()`.

    Caller chịu trách nhiệm `terminate_all([proc])` ở teardown — hàm này chỉ
    spawn, không tự dọn khi thành công (khi `wait_until_ready` raise thì có
    dọn trước khi propagate, tránh rò rỉ tiến trình con)."""
    encore = _require_encore()
    port = pick_free_port()
    cosa_url = f"http://127.0.0.1:{port}"
    proc = spawn(
        "cosa",
        [encore, "run", f"--port={port}"],
        cwd=os.path.join(_REPO_ROOT, "services", "cosa"),
        env=_clean_env(COSA_DATABASE_URL=cluster.cosa_app_url),
    )
    try:
        wait_until_ready("cosa", f"{cosa_url}/healthz", proc, timeout_s=_ENCORE_READY_TIMEOUT_S)
    except Exception:
        terminate_all([proc])
        raise
    return cosa_url, proc


def teardown_subprocess_stack(handles: StackHandles) -> None:
    terminate_all(handles.procs)
