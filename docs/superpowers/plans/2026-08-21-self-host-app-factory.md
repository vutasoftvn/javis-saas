# Founder Self-Host Full Stack + Central Control-Plane App Factory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Triển khai Quyết định 3 của `docs/architecture/COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md` — cho phép founder tự host toàn bộ COSA stack trên VPS riêng (bổ sung, không thay desktop-first), đồng thời vá lỗ hổng đã verify: `deploy/central_vps` hiện chạy cùng 1 image monolith với `brain-api` local, chưa từng thu hẹp về đúng control-plane.

**Architecture:** Xây 1 app factory thật — `backend/app/bootstrap/create_app.py::create_app(role)` — import router **có điều kiện theo `role`** (không phải chỉ mount có điều kiện), vì `app/main.py` hiện tại `import` cả 5 domain router ở top-level trước khi gọi `include_router`. Hai entrypoint mỏng `backend/app/full_main.py` / `backend/app/central_main.py` gọi `create_app("full"|"central_control_plane")`; `backend/app/main.py` trở thành alias tương thích ngược trỏ về `full_main` để không phá `uvicorn app.main:app` hiện có. `deploy/central_vps/docker-compose.yaml` chuyển sang chạy `central_main:app` với `APP_ROLE=central_control_plane`. `deploy/self_host/` là bộ compose/Caddyfile/README mới, tái dùng service definitions của root `docker-compose.yml`, chạy `full_main:app`, chỉ `brain-api` lộ ra ngoài qua Caddy/TLS.

**Tech Stack:** FastAPI, Uvicorn, Docker Compose, Caddy 2, pytest + pytest-asyncio + `fastapi.testclient.TestClient`, PyYAML (test-side compose-contract assertions, đã có sẵn trong `backend/app/tests/test_compose_contract.py`).

## Global Constraints

- Default `APP_ROLE` (khi không set) phải giữ nguyên hành vi hiện tại (`full`, đủ 5 domain) — không được regress cho local/dev hiện có (`uvicorn app.main:app`, `docker compose up brain-api`).
- Không bao giờ publish port ra ngoài (`ports:` trong compose) cho `postgres`, `minio`, `agent-worker` ở bất kỳ file compose nào plan này đụng vào.
- `desktop_worker` (bất kỳ tên service nào trỏ tới `desktop_worker/main.py`) không được xuất hiện trong `deploy/self_host/docker-compose.yaml` dưới bất kỳ hình thức nào — nó có lỗ hổng đã biết (`subprocess(..., shell=True)` không sandbox, chỉ an toàn khi bind loopback trên máy dev).
- Nguyên tắc single-authority (không active-active): Personal Mode (desktop hoặc self-host 1 founder) — Postgres local/self-host là authority cho dữ liệu business; central control-plane chỉ là control plane cho licensing/entitlement, không mở rộng thành sync 2 chiều dữ liệu business. Team Mode là 1 hành động "Promote to Team Workspace" tường minh, ngoài phạm vi plan này — không tự động, không ngầm định.
- Self-host vẫn single-tenant mỗi deployment, giống desktop — `markdown/Structure.md:286`: "Không thiết kế multi-tenant SaaS vào local application."
- Không đụng vào: ADK Co-founder Orchestrator, thiết kế lược đồ Central DB (`infra/supabase/migrations/`, `deploy/central_vps/init_central_postgres.sql`), hợp nhất định danh Workforce/Agent — đây là 3 subsystem đang được plan song song bởi agent khác.
- Root `docker-compose.yml` không nằm trong phạm vi sửa của Quyết định 3 (chỉ `deploy/central_vps/docker-compose.yaml` được liệt kê) — `backend/app/main.py` phải tiếp tục hoạt động làm entrypoint tương thích ngược thay vì yêu cầu đổi root compose.
- `PlatformOutbox/PlatformInbox/LocalEntitlementSnapshot` schema, cơ chế HMAC/signature của `EntitlementManager`, cơ chế outbox/backoff/idempotent ACK của `PlatformSyncWorker` — không đổi (Quyết định 2, "Không đổi").

---

## Bối cảnh đã verify trước khi viết task (không lặp lại nghiên cứu này khi thực thi)

- `backend/app/main.py` hiện `import` `app.founder_os.router`, `app.business.router`, `app.workforce.router`, `app.integrations.router`, `app.platform.router` (dòng 76-87) **trước** mọi lệnh `include_router` — đúng như phát hiện phụ của Quyết định 3.
- `app.platform.router` (aggregator) tự nó `import` **toàn bộ** sub-domain của platform (`auth`, `vault`, `license` tức company-runtime, `core`/admin, `organization`, `tech_radar`, `policy_funding`, `sync`) ở top-level. Nghĩa là nếu `create_app("central_control_plane")` lỡ `import app.platform.router` (thay vì import thẳng `app.platform.sync.router`), toàn bộ vấn đề mà Quyết định 3 muốn sửa sẽ tái diễn — chỉ lùi xuống 1 tầng package thay vì biến mất. Do đó role `central_control_plane` phải import thẳng `app.platform.sync.router`, **không được** đi qua `app.platform.router`.
- `app.platform.sync.router` (module thực sự nói giao thức central: `PlatformOutbox`/`PlatformInbox`/`EntitlementManager`, có gate `COSA_RUNTIME_PLANE=control` cho endpoint `/entitlement/sign`) mounted qua aggregator ở prefix `/api/v1/platform` (chính `sync/router.py` tự có `prefix="/sync"` nội bộ nên full path cuối là `/api/v1/platform/sync/...`) — đã verify khớp với `deploy/central_vps/README.md` (đang document `/api/v1/platform/sync/status` làm healthcheck URL production thật).
- **Phát hiện thêm (ngoài mô tả gốc của Quyết định 3, cần vá kèm trong Task 4):** `deploy/central_vps/docker-compose.yaml` hiện KHÔNG set `command:` cho `central_api`, nên nó kế thừa `CMD` mặc định của `backend/Dockerfile.api`: `alembic upgrade head 2>/dev/null || true; uvicorn app.main:app --host 0.0.0.0 --port 8000` — tức là production central_api hôm nay **âm thầm chạy toàn bộ Alembic migration của schema local/company** nhắm vào `central_postgres` (`cosa_central` database, vốn được khởi tạo bằng `init_central_postgres.sql` raw SQL, không phải Alembic) mỗi lần container khởi động, lỗi bị nuốt bởi `2>/dev/null || true`. Task 4 phải override `command:` để không còn chạy alembic ở container này nữa.
- **Phát hiện thêm thứ hai:** `deploy/central_vps/docker-compose.yaml` hiện cũng KHÔNG set `COSA_RUNTIME_PLANE=control`. `app/platform/sync/router.py` đọc biến này 1 lần lúc import module (mặc định `"company"` nếu unset) để quyết định có đăng ký route `/entitlement/sign` hay không (route ký entitlement — chính là lý do tồn tại của central control-plane). Nghĩa là: dù central_api hiện đang mount toàn bộ router (kể cả `platform.sync.router` qua aggregator), endpoint `/entitlement/sign` **chưa từng được đăng ký trên production** vì thiếu biến này. Task 4 phải set `COSA_RUNTIME_PLANE=control` để central role thực sự phục vụ được đúng chức năng của nó.
- `backend/app/tests/conftest.py` có fixture `client` dùng chung cho **toàn bộ** test suite hiện có, xây từ `from app.main import app`. Bất kỳ refactor nào ở `app/main.py` phải giữ `app.main.app` là cùng 1 FastAPI instance object hợp lệ, nếu không toàn bộ suite hiện có sẽ vỡ.
- `backend/app/tests/test_compose_contract.py` đã có sẵn pattern "đọc compose/README bằng `yaml.safe_load`/text rồi assert" — dùng đúng pattern này, không tự chế cách test mới (§14 CLAUDE.md — tái dùng, không trùng kiến trúc).
- `desktop_worker/main.py`: FastAPI app riêng, bind `127.0.0.1:8765`, endpoint `/execute-task` chạy `subprocess.run(req.command, shell=True, ...)` không sandbox, comment tự nhận "Chỉ lắng nghe trên 127.0.0.1 (Loopback only)". Không có lý do hợp lệ nào để đưa vào self-host — xác nhận đúng như mô tả trong Quyết định 3.
- `markdown/Structure.md:286` — nguyên văn: "Không thiết kế multi-tenant SaaS vào local application."

---

### Task 1: `resolve_app_role()` — parse `APP_ROLE` với default an toàn

**Files:**
- Create: `backend/app/bootstrap/__init__.py`
- Create: `backend/app/bootstrap/create_app.py`
- Test: `backend/app/tests/test_app_factory.py`

**Interfaces:**
- Produces: `resolve_app_role(environment: dict[str, str] | None = None) -> str`, hằng số `FULL_ROLE = "full"`, `CENTRAL_CONTROL_PLANE_ROLE = "central_control_plane"` — Task 2+ và các entrypoint ở Task 3 dùng lại đúng 3 tên này.

- [ ] **Step 1: Viết test cho `resolve_app_role`**

Tạo `backend/app/tests/test_app_factory.py`:

```python
"""Tests cho COSA app factory (Quyết định 3 - self-host + central control-plane
role split). Xem docs/architecture/COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md,
Quyết định 3.
"""
import pytest


def test_resolve_app_role_defaults_to_full_when_unset():
    from app.bootstrap.create_app import resolve_app_role, FULL_ROLE

    assert resolve_app_role({}) == FULL_ROLE


def test_resolve_app_role_defaults_to_full_when_blank():
    from app.bootstrap.create_app import resolve_app_role, FULL_ROLE

    assert resolve_app_role({"APP_ROLE": "   "}) == FULL_ROLE


def test_resolve_app_role_accepts_central_control_plane():
    from app.bootstrap.create_app import resolve_app_role, CENTRAL_CONTROL_PLANE_ROLE

    assert resolve_app_role({"APP_ROLE": "central_control_plane"}) == CENTRAL_CONTROL_PLANE_ROLE
    assert resolve_app_role({"APP_ROLE": " Central_Control_Plane "}) == CENTRAL_CONTROL_PLANE_ROLE


def test_resolve_app_role_rejects_unknown_value():
    from app.bootstrap.create_app import resolve_app_role

    with pytest.raises(ValueError, match="Unknown APP_ROLE"):
        resolve_app_role({"APP_ROLE": "central"})
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && python -m pytest app/tests/test_app_factory.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.bootstrap'`

- [ ] **Step 3: Implement `resolve_app_role`**

Tạo `backend/app/bootstrap/__init__.py` (rỗng):

```python
```

Tạo `backend/app/bootstrap/create_app.py`:

```python
"""COSA FastAPI application factory (Quyết định 3 - self-host + central
control-plane role split).

`create_app(role)` build 1 FastAPI app mà việc IMPORT router phụ thuộc điều
kiện vào `role`, không chỉ việc `include_router()` - import
`app.founder_os.router` (v.v.) có chi phí thật (kéo theo toàn bộ dependency
tầng service/tool của domain đó) ngay cả khi router object không được mount,
nên 1 role không cần domain nào thì tuyệt đối không được import domain đó.
"""
import os

FULL_ROLE = "full"
CENTRAL_CONTROL_PLANE_ROLE = "central_control_plane"
_VALID_ROLES = (FULL_ROLE, CENTRAL_CONTROL_PLANE_ROLE)


def resolve_app_role(environment: "os._Environ[str] | dict | None" = None) -> str:
    """Resolve APP_ROLE từ environment. Mặc định "full" khi unset/rỗng - giữ
    đúng hành vi hiện tại (trước Quyết định 3), không được tự ý thu hẹp phạm
    vi. Giá trị không hợp lệ (vd gõ nhầm "central") phải raise ngay thay vì
    âm thầm fallback về "full" - fallback êm sẽ khiến 1 deployment central
    gõ sai APP_ROLE lại mount lại nguyên con monolith mà Quyết định 3 đang
    vá, chỉ khác là không còn ai biết để verify nữa.
    """
    environment = environment if environment is not None else os.environ
    raw = environment.get("APP_ROLE")
    if raw is None or raw.strip() == "":
        return FULL_ROLE
    role = raw.strip().lower()
    if role not in _VALID_ROLES:
        raise ValueError(
            f"Unknown APP_ROLE={raw!r}; must be unset (defaults to {FULL_ROLE!r}) "
            f"or one of {_VALID_ROLES!r}."
        )
    return role
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `cd backend && python -m pytest app/tests/test_app_factory.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/bootstrap/__init__.py backend/app/bootstrap/create_app.py backend/app/tests/test_app_factory.py
git commit -m "feat(bootstrap): add resolve_app_role() for APP_ROLE parsing"
```

---

### Task 2: `create_app(role)` — import router có điều kiện + lifespan có điều kiện + `/ready` theo role

Đây là task lõi của Quyết định 3: build đầy đủ `create_app()`, bao gồm mount router theo role, lifespan theo role (4 startup hook hiện tại của `main.py` chỉ có ý nghĩa với role `full`), và health probe `/live` + `/ready` (role `central_control_plane` không có MinIO/Vault/local Alembic-managed schema/agent-worker nên `/ready` chỉ còn check `database`).

**Files:**
- Modify: `backend/app/bootstrap/create_app.py`
- Modify: `backend/app/tests/test_app_factory.py`

**Interfaces:**
- Consumes: `FULL_ROLE`, `CENTRAL_CONTROL_PLANE_ROLE`, `resolve_app_role()` (Task 1).
- Produces: `create_app(role: str | None = None) -> fastapi.FastAPI` — Task 3 (`full_main.py`/`central_main.py`/`main.py`) gọi hàm này với `role="full"` / `role="central_control_plane"`.

- [ ] **Step 1: Viết test subprocess-based chứng minh import có điều kiện (role `full`)**

Append vào `backend/app/tests/test_app_factory.py`:

```python
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]  # app/tests -> app -> backend


def _run_role_probe(role: str, forbidden_prefixes: tuple, required_modules: tuple) -> None:
    """Spawn 1 process `python` mới, build create_app(role), rồi kiểm tra
    những module `app.*` nào đã lọt vào sys.modules. Bắt buộc chạy ở process
    riêng - 1 module đã bị import ở bất kỳ đâu trong cùng phiên pytest sẽ ở
    lại sys.modules cho tới hết process đó, khiến check "X có bị import
    không" trong cùng process pass/fail tuỳ thứ tự chạy test chứ không phải
    tuỳ hành vi thật của create_app().
    """
    script = (
        "import sys\n"
        "from app.bootstrap.create_app import create_app\n"
        f"create_app({role!r})\n"
        f"required = {list(required_modules)!r}\n"
        f"forbidden_prefixes = {list(forbidden_prefixes)!r}\n"
        "missing = [m for m in required if m not in sys.modules]\n"
        "leaked = [m for m in sys.modules if any(m.startswith(p) for p in forbidden_prefixes)]\n"
        "assert not missing, f'expected imported, missing: {missing}'\n"
        "assert not leaked, f'unexpectedly imported: {leaked}'\n"
        "print('PROBE_OK')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(BACKEND_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    assert "PROBE_OK" in result.stdout


def test_full_role_imports_every_domain_router_module():
    _run_role_probe(
        role="full",
        forbidden_prefixes=(),
        required_modules=(
            "app.founder_os.router",
            "app.business.router",
            "app.workforce.router",
            "app.integrations.router",
            "app.platform.router",
            "app.workforce.agents.capabilities.router",
            "app.workforce.agents.delegation.router",
        ),
    )


def test_central_control_plane_role_only_imports_platform_sync_router():
    _run_role_probe(
        role="central_control_plane",
        forbidden_prefixes=(
            "app.founder_os",
            "app.business",
            "app.workforce",
            "app.integrations",
            "app.platform.router",
        ),
        required_modules=("app.platform.sync.router",),
    )
```

- [ ] **Step 2: Viết test route-prefix theo role (in-process, không cần subprocess)**

Append tiếp:

```python
def _route_paths(app) -> list:
    return [getattr(route, "path", "") for route in app.routes]


def test_full_role_mounts_all_five_domain_prefixes():
    from app.bootstrap.create_app import create_app

    app = create_app("full")
    paths = _route_paths(app)

    assert any(p.startswith("/api/v1/auth") for p in paths)
    assert any(p.startswith("/api/v1/vault") for p in paths)
    assert any(p.startswith("/api/v1/company-runtime") for p in paths)
    assert any(p.startswith("/api/v1/organization") for p in paths)
    assert any(p.startswith("/api/v1/capabilities") for p in paths)
    assert any(p.startswith("/api/v1/agents/delegations") for p in paths)
    assert any(p.startswith("/api/v1/platform/sync") for p in paths)


def test_central_control_plane_role_mounts_only_platform_sync():
    from app.bootstrap.create_app import create_app

    app = create_app("central_control_plane")
    paths = _route_paths(app)

    assert any(p.startswith("/api/v1/platform/sync") for p in paths)
    assert not any(p.startswith("/api/v1/auth") for p in paths)
    assert not any(p.startswith("/api/v1/vault") for p in paths)
    assert not any(p.startswith("/api/v1/company-runtime") for p in paths)
    assert not any(p.startswith("/api/v1/organization") for p in paths)
    assert not any(p.startswith("/api/v1/capabilities") for p in paths)
    assert not any(p.startswith("/api/v1/agents/delegations") for p in paths)
```

- [ ] **Step 3: Viết test lifespan theo role**

Append tiếp:

```python
def test_full_role_lifespan_runs_all_four_startup_hooks(monkeypatch):
    from unittest.mock import MagicMock
    from fastapi.testclient import TestClient

    ensure_bucket = MagicMock()
    load_snapshots = MagicMock()
    seed_registry = MagicMock()
    register_listeners = MagicMock()

    monkeypatch.setattr("app.integrations.storage.s3_client.ensure_bucket_exists", ensure_bucket)
    monkeypatch.setattr(
        "app.platform.sync.entitlement_manager.load_all_current_snapshots_into_cache", load_snapshots
    )
    monkeypatch.setattr(
        "app.founder_os.strategy.services.capability_registry_seed_service."
        "seed_canonical_capability_registry",
        seed_registry,
    )
    monkeypatch.setattr(
        "app.workforce.agents.orchestration.mission_control_bus.register_default_listeners",
        register_listeners,
    )

    from app.bootstrap.create_app import create_app

    app = create_app("full")
    with TestClient(app):
        pass

    ensure_bucket.assert_called_once()
    load_snapshots.assert_called_once()
    seed_registry.assert_called_once()
    register_listeners.assert_called_once()


def test_central_control_plane_lifespan_is_a_noop(monkeypatch):
    from unittest.mock import MagicMock
    from fastapi.testclient import TestClient

    ensure_bucket = MagicMock()
    monkeypatch.setattr("app.integrations.storage.s3_client.ensure_bucket_exists", ensure_bucket)

    from app.bootstrap.create_app import create_app

    app = create_app("central_control_plane")
    with TestClient(app):
        pass

    ensure_bucket.assert_not_called()
```

- [ ] **Step 4: Viết test `/ready` theo role**

Append tiếp:

```python
def test_full_role_ready_probe_reports_four_checks():
    from fastapi.testclient import TestClient
    from app.bootstrap.create_app import create_app

    app = create_app("full")
    response = TestClient(app).get("/ready")

    assert set(response.json()["checks"].keys()) == {"database", "storage", "migrations", "worker"}


def test_central_control_plane_ready_probe_only_checks_database():
    from fastapi.testclient import TestClient
    from app.bootstrap.create_app import create_app

    app = create_app("central_control_plane")
    response = TestClient(app).get("/ready")

    assert set(response.json()["checks"].keys()) == {"database"}
```

- [ ] **Step 5: Chạy toàn bộ file test, xác nhận các test mới FAIL**

Run: `cd backend && python -m pytest app/tests/test_app_factory.py -v`
Expected: 4 test cũ (Task 1) PASS, các test mới FAIL — `create_app` chưa tồn tại (chỉ có `resolve_app_role`).

- [ ] **Step 6: Implement `create_app()` đầy đủ**

Thay thế toàn bộ nội dung `backend/app/bootstrap/create_app.py`:

```python
"""COSA FastAPI application factory (Quyết định 3 - self-host + central
control-plane role split).

`create_app(role)` build 1 FastAPI app mà việc IMPORT router phụ thuộc điều
kiện vào `role`, không chỉ việc `include_router()` - import
`app.founder_os.router` (v.v.) có chi phí thật (kéo theo toàn bộ dependency
tầng service/tool của domain đó) ngay cả khi router object không được mount,
nên 1 role không cần domain nào thì tuyệt đối không được import domain đó.

Roles:
- "full" (mặc định): đủ 5 domain (founder_os/business/workforce/integrations/
  platform) - local dev, backend desktop, self-host VPS.
- "central_control_plane": chỉ bề mặt platform sync/entitlement
  (`app.platform.sync.router`) - VPS trung tâm do COSA vận hành, chỉ ký
  entitlement snapshot và nhận PlatformOutbox event. Không bao giờ import
  founder_os/business/workforce/integrations, và KHÔNG import qua
  `app.platform.router` (aggregator) - module đó tự import toàn bộ sub-domain
  của platform (auth/vault/license/organization/tech_radar/policy_funding) ở
  top-level, nên import nó sẽ tái diễn đúng vấn đề Quyết định 3 đang vá, chỉ
  lùi xuống 1 tầng package.
"""
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dotenv import load_dotenv
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

logger = logging.getLogger(__name__)

FULL_ROLE = "full"
CENTRAL_CONTROL_PLANE_ROLE = "central_control_plane"
_VALID_ROLES = (FULL_ROLE, CENTRAL_CONTROL_PLANE_ROLE)


def resolve_app_role(environment: "os._Environ[str] | dict | None" = None) -> str:
    """Resolve APP_ROLE từ environment. Mặc định "full" khi unset/rỗng - giữ
    đúng hành vi hiện tại (trước Quyết định 3), không được tự ý thu hẹp phạm
    vi. Giá trị không hợp lệ (vd gõ nhầm "central") phải raise ngay thay vì
    âm thầm fallback về "full" - fallback êm sẽ khiến 1 deployment central
    gõ sai APP_ROLE lại mount lại nguyên con monolith mà Quyết định 3 đang
    vá, chỉ khác là không còn ai biết để verify nữa.
    """
    environment = environment if environment is not None else os.environ
    raw = environment.get("APP_ROLE")
    if raw is None or raw.strip() == "":
        return FULL_ROLE
    role = raw.strip().lower()
    if role not in _VALID_ROLES:
        raise ValueError(
            f"Unknown APP_ROLE={raw!r}; must be unset (defaults to {FULL_ROLE!r}) "
            f"or one of {_VALID_ROLES!r}."
        )
    return role


def _mount_full_routers(app: FastAPI) -> None:
    """Role "full": import + mount đúng y hệt `app/main.py` trước Quyết định 3
    (5 domain master router + 2 sub-router của workforce.agents)."""
    from app.founder_os.router import router as founder_os_router
    from app.business.router import router as business_router
    from app.workforce.router import router as workforce_router
    from app.integrations.router import router as integrations_router
    from app.platform.router import router as platform_router
    from app.workforce.agents.capabilities.router import router as capabilities_router
    from app.workforce.agents.delegation.router import router as delegation_router

    app.include_router(founder_os_router)
    app.include_router(business_router)
    app.include_router(workforce_router)
    app.include_router(integrations_router)
    app.include_router(platform_router)
    app.include_router(capabilities_router, prefix="/api/v1/capabilities", tags=["capabilities"])
    app.include_router(
        delegation_router,
        prefix="/api/v1/agents/delegations",
        tags=["agents-delegations"],
    )


def _mount_central_control_plane_routers(app: FastAPI) -> None:
    """Role "central_control_plane": chỉ bề mặt platform sync/entitlement.
    Import thẳng `app.platform.sync.router`, KHÔNG đi qua
    `app.platform.router` aggregator - mount ở đúng prefix aggregator vẫn
    dùng (`/api/v1/platform`) để URL contract (`/api/v1/platform/sync/...`)
    không đổi giữa role "full" và role "central_control_plane"."""
    from app.platform.sync import router as platform_sync_router

    app.include_router(platform_sync_router.router, prefix="/api/v1/platform", tags=["platform-sync"])


def _build_lifespan(role: str, *, engine, session_factory):
    if role == FULL_ROLE:
        @asynccontextmanager
        async def full_lifespan(app: FastAPI) -> AsyncIterator[None]:
            from app.integrations.storage.s3_client import ensure_bucket_exists
            from app.platform.sync.entitlement_manager import load_all_current_snapshots_into_cache
            from app.workforce.agents.orchestration.mission_control_bus import register_default_listeners
            from app.founder_os.strategy.services.capability_registry_seed_service import (
                seed_canonical_capability_registry,
            )

            # Object storage là dependency bắt buộc cho Vault revisions. Provision
            # bucket đã cấu hình lúc startup để lần ghi đầu tiên không fail chỉ vì
            # 1 môi trường MinIO/S3 rỗng vừa được bootstrap.
            try:
                ensure_bucket_exists()
            except Exception:
                logger.exception("Failed to ensure object-storage bucket on startup")

            # Startup: nạp lại entitlement snapshot đã persist (G2 P0.3 / G3 §9.3) -
            # thiếu bước này, mỗi lần restart process sẽ âm thầm rơi về Free tier
            # mặc định cho mọi company dù license vẫn còn hiệu lực, vì cache của
            # EntitlementManager vốn chỉ ở process-memory.
            try:
                db = session_factory()
                try:
                    load_all_current_snapshots_into_cache(db)
                finally:
                    db.close()
            except Exception:
                logger.exception("Failed to load persisted entitlement snapshots on startup")

            # G3 Phase 1B: seed Capability Registry (capability_definitions) từ
            # CAPABILITY_CATALOG + business pack YAML mỗi lần startup - idempotent
            # upsert.
            try:
                db = session_factory()
                try:
                    seed_canonical_capability_registry(db)
                finally:
                    db.close()
            except Exception:
                logger.exception("Failed to seed canonical capability registry on startup")

            # G1/G3 §10.6: gắn listener process-wide của mission_control_bus.
            try:
                register_default_listeners()
            except Exception:
                logger.exception("Failed to register mission_control_bus default listeners on startup")

            yield

        return full_lifespan

    @asynccontextmanager
    async def central_control_plane_lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Role "central_control_plane" không sở hữu state runtime nào của role
        # "full" (không MinIO/Vault bucket, không cache entitlement để nạp -
        # central là bên KÝ snapshot chứ không phải bên tiêu thụ; không Founder
        # OS capability registry; không Workforce mission_control_bus). Không có
        # gì cần provision lúc startup.
        yield

    return central_control_plane_lifespan


def _mount_health_probes(app: FastAPI, *, role: str, engine) -> None:
    @app.get("/live")
    def liveness_probe():
        return {"status": "alive"}

    @app.get("/ready")
    def readiness_probe(response: Response):
        checks: dict = {"database": "unknown"}
        healthy = True

        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as exc:
            checks["database"] = f"error: {exc.__class__.__name__}"
            healthy = False

        if role == FULL_ROLE:
            from app.core.migration_health import get_migration_health
            from app.core.worker_health import get_worker_health
            from app.integrations.storage.s3_client import get_s3_client

            checks["storage"] = "unknown"
            try:
                get_s3_client().list_buckets()
                checks["storage"] = "ok"
            except Exception as exc:
                checks["storage"] = f"error: {exc.__class__.__name__}"
                healthy = False

            migrations_healthy, migration_status = get_migration_health(engine)
            checks["migrations"] = migration_status
            if not migrations_healthy:
                healthy = False

            worker_healthy, worker_status = get_worker_health(engine)
            checks["worker"] = worker_status
            if not worker_healthy:
                healthy = False

        if not healthy:
            response.status_code = 503
        return {"status": "ready" if healthy else "not_ready", "checks": checks}


def create_app(role: str | None = None) -> FastAPI:
    # Nạp file .env từ thư mục gốc dự án trước khi import bất kỳ router nào -
    # bootstrap/ nằm sâu hơn 1 cấp so với app/main.py cũ nên cần thêm 1 "..".
    load_dotenv()
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"))

    from app.core.runtime_config import validate_runtime_configuration, resolve_cors_origins
    validate_runtime_configuration()

    resolved_role = resolve_app_role() if role is None else role
    if resolved_role not in _VALID_ROLES:
        raise ValueError(f"Unknown role={resolved_role!r}; must be one of {_VALID_ROLES!r}.")

    from app.db.session import engine, SessionLocal

    lifespan = _build_lifespan(resolved_role, engine=engine, session_factory=SessionLocal)

    enable_docs = os.getenv("ENABLE_DOCS", "false").strip().lower() in ("true", "1", "yes")
    is_prod = (
        os.getenv("ENVIRONMENT", "").strip().lower() == "production"
        or os.getenv("APP_ENV", "").strip().lower() in ("production", "prod")
    )
    docs_enabled = enable_docs and not is_prod

    app = FastAPI(
        title="COSA OS API",
        description="Hệ điều hành Doanh nghiệp Tự trị (Autonomous Enterprise Operating System) - Kiến trúc 5 Domain",
        version="2.0.0",
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
        lifespan=lifespan,
    )

    origins = resolve_cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if resolved_role == FULL_ROLE:
        _mount_full_routers(app)
    else:
        _mount_central_control_plane_routers(app)

    _mount_health_probes(app, role=resolved_role, engine=engine)

    return app
```

- [ ] **Step 7: Chạy toàn bộ file test, xác nhận PASS**

Run: `cd backend && python -m pytest app/tests/test_app_factory.py -v`
Expected: tất cả pass (4 từ Task 1 + 8 mới = 12 passed)

- [ ] **Step 8: Commit**

```bash
git add backend/app/bootstrap/create_app.py backend/app/tests/test_app_factory.py
git commit -m "feat(bootstrap): implement create_app(role) with conditional router imports"
```

---

### Task 3: Entrypoint mỏng `full_main.py` / `central_main.py` + `main.py` alias tương thích ngược

**Files:**
- Create: `backend/app/full_main.py`
- Create: `backend/app/central_main.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/tests/test_app_factory.py`

**Interfaces:**
- Consumes: `create_app`, `FULL_ROLE`, `CENTRAL_CONTROL_PLANE_ROLE` (Task 2), fixture `client` có sẵn ở `backend/app/tests/conftest.py` (`from app.main import app`).
- Produces: `app.full_main.app`, `app.central_main.app`, `app.main.app` (alias của `app.full_main.app`) - lệnh deploy dùng `uvicorn app.full_main:app` (mặc định/local/self-host) hoặc `uvicorn app.central_main:app` (central VPS); `uvicorn app.main:app` tiếp tục hoạt động nguyên trạng.

- [ ] **Step 1: Viết test cho 2 entrypoint mới + tính tương thích ngược của `main.py`**

Append vào `backend/app/tests/test_app_factory.py`:

```python
def test_full_main_app_has_full_role_route_surface():
    from app.full_main import app as full_app

    paths = _route_paths(full_app)
    assert any(p.startswith("/api/v1/auth") for p in paths)
    assert any(p.startswith("/api/v1/capabilities") for p in paths)


def test_central_main_app_has_central_role_route_surface():
    from app.central_main import app as central_app

    paths = _route_paths(central_app)
    assert any(p.startswith("/api/v1/platform/sync") for p in paths)
    assert not any(p.startswith("/api/v1/auth") for p in paths)


def test_main_module_is_a_backward_compatible_alias_for_full_main():
    from app.main import app as main_app
    from app.full_main import app as full_app

    assert main_app is full_app


def test_main_module_client_fixture_still_serves_live_probe(client):
    response = client.get("/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && python -m pytest app/tests/test_app_factory.py -v`
Expected: 4 test mới FAIL — `app.full_main`/`app.central_main` chưa tồn tại; `app.main` vẫn là bản `main.py` cũ (import trực tiếp, chưa alias) nên `test_main_module_is_a_backward_compatible_alias_for_full_main` FAIL vì `app.full_main` chưa tồn tại để import.

- [ ] **Step 3: Tạo `backend/app/full_main.py`**

```python
"""Entrypoint role "full" - đủ 5 domain (founder_os/business/workforce/
integrations/platform). Dùng cho local dev, backend desktop, self-host VPS.

    uvicorn app.full_main:app --host 0.0.0.0 --port 8000
"""
import os

import uvicorn

from app.bootstrap.create_app import FULL_ROLE, create_app

app = create_app(FULL_ROLE)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.full_main:app", host="0.0.0.0", port=port, reload=True)
```

- [ ] **Step 4: Tạo `backend/app/central_main.py`**

```python
"""Entrypoint role "central_control_plane" (Quyết định 3) - chỉ bề mặt
platform sync/entitlement (`app.platform.sync.router`). Không bao giờ import
founder_os/business/workforce/integrations, hay `app.platform.router`
aggregator.

    uvicorn app.central_main:app --host 0.0.0.0 --port 8000
"""
import os

import uvicorn

from app.bootstrap.create_app import CENTRAL_CONTROL_PLANE_ROLE, create_app

app = create_app(CENTRAL_CONTROL_PLANE_ROLE)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.central_main:app", host="0.0.0.0", port=port)
```

- [ ] **Step 5: Thay `backend/app/main.py` bằng alias tương thích ngược**

Ghi đè toàn bộ nội dung `backend/app/main.py`:

```python
"""Alias tương thích ngược cho `app.full_main` (refactor app-factory, Quyết
định 3). Tooling/docs/`docker-compose.yml` hiện có đang tham chiếu
`uvicorn app.main:app` - file này giữ nguyên điều đó hoạt động, import lại
đúng 1 FastAPI instance mà `app.full_main` đã build qua
`create_app("full")` thay vì build lại 1 bản trùng."""
from app.full_main import app

__all__ = ["app"]

if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
```

- [ ] **Step 6: Chạy toàn bộ file test, xác nhận PASS**

Run: `cd backend && python -m pytest app/tests/test_app_factory.py -v`
Expected: tất cả pass (12 từ Task 1+2 + 4 mới = 16 passed)

- [ ] **Step 7: Chạy lại toàn bộ test suite hiện có để xác nhận không regress**

Run: `cd backend && python -m pytest app/tests -x -q`
Expected: PASS toàn bộ (không có test nào vỡ vì fixture `client`/`app.main.app` đổi identity — `main_app is full_app` đã tự chứng minh identity giữ nguyên qua 1 assert riêng ở Step 1, và mọi fixture khác trong suite chỉ dùng `client`/`app` giống hệt trước).

- [ ] **Step 8: Commit**

```bash
git add backend/app/full_main.py backend/app/central_main.py backend/app/main.py backend/app/tests/test_app_factory.py
git commit -m "feat(bootstrap): add full_main/central_main entrypoints, main.py becomes compat alias"
```

---

### Task 4: `deploy/central_vps/docker-compose.yaml` — chuyển sang role `central_control_plane` thật

**Files:**
- Modify: `deploy/central_vps/docker-compose.yaml`
- Modify: `backend/app/tests/test_compose_contract.py`

**Interfaces:**
- Consumes: `app.central_main:app` (Task 3).
- Produces: service `central_api` chạy đúng role thu hẹp, không còn tự ý chạy Alembic local vào DB central.

- [ ] **Step 1: Viết compose-contract test**

Append vào `backend/app/tests/test_compose_contract.py`:

```python
def test_central_vps_scopes_central_api_to_control_plane_role():
    compose = yaml.safe_load((REPO_ROOT / "deploy/central_vps/docker-compose.yaml").read_text())
    central_api = compose["services"]["central_api"]

    assert "APP_ROLE=central_control_plane" in central_api["environment"]
    assert "COSA_RUNTIME_PLANE=control" in central_api["environment"]
    assert central_api["command"] == "uvicorn app.central_main:app --host 0.0.0.0 --port 8000"


def test_central_vps_does_not_run_local_alembic_migrations():
    compose = yaml.safe_load((REPO_ROOT / "deploy/central_vps/docker-compose.yaml").read_text())
    central_api = compose["services"]["central_api"]

    assert "alembic" not in central_api.get("command", "")
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && python -m pytest app/tests/test_compose_contract.py -k central_vps -v`
Expected: FAIL — `central_api` hiện chưa có `command`, environment thiếu `APP_ROLE`/`COSA_RUNTIME_PLANE`.

- [ ] **Step 3: Sửa `deploy/central_vps/docker-compose.yaml`**

Thay khối `central_api` (giữ nguyên `caddy`/`central_postgres`/`volumes` phía dưới, không đổi):

```yaml
  central_api:
    build:
      context: ../../backend
      dockerfile: Dockerfile.api
    restart: always
    # APP_ROLE=central_control_plane (Quyết định 3): backend/app/central_main.py
    # chỉ import app.platform.sync.router (ký entitlement + nhận
    # PlatformOutbox/Inbox) - không bao giờ founder_os/business/workforce/
    # integrations, và không đi qua app.platform.router aggregator
    # (auth/vault/organization/tech_radar/...).
    #
    # `command` PHẢI override CMD mặc định của Dockerfile.api - CMD mặc định
    # chạy `alembic upgrade head` vô điều kiện, sẽ áp toàn bộ Alembic
    # migration của schema local/company vào chính database central này.
    # Schema của database này do init_central_postgres.sql quản lý (mount
    # vào docker-entrypoint-initdb.d bên dưới), không phải Alembic -
    # central_api không bao giờ được chạy alembic nhắm vào nó.
    #
    # COSA_RUNTIME_PLANE=control mở endpoint /entitlement/sign (xem
    # backend/app/platform/sync/router.py) - thiếu biến này, mặc định
    # "company", central_api sẽ không có route ký entitlement dù đã mount
    # đúng router.
    command: uvicorn app.central_main:app --host 0.0.0.0 --port 8000
    environment:
      - APP_ROLE=central_control_plane
      - COSA_RUNTIME_PLANE=control
      - DATABASE_URL=postgresql://${POSTGRES_USER:-cosa_central_admin}:${POSTGRES_PASSWORD:-SecureCentralPass2026}@central_postgres:5432/${POSTGRES_DB:-cosa_central}
      - COSA_PLATFORM_SIGNING_SECRET=${COSA_PLATFORM_SIGNING_SECRET:-cosa_platform_master_signing_key_2026_production}
      - ENVIRONMENT=production
      - PYTHONUNBUFFERED=1
    depends_on:
      central_postgres:
        condition: service_healthy
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `cd backend && python -m pytest app/tests/test_compose_contract.py -v`
Expected: tất cả pass (bao gồm các test compose-contract cũ, chưa bị đụng vào)

- [ ] **Step 5: Commit**

```bash
git add deploy/central_vps/docker-compose.yaml backend/app/tests/test_compose_contract.py
git commit -m "fix(central-vps): scope central_api to central_control_plane role, stop running local alembic"
```

---

### Task 5: `deploy/self_host/docker-compose.yaml` — stack tự host mới

**Files:**
- Create: `deploy/self_host/docker-compose.yaml`
- Modify: `backend/app/tests/test_compose_contract.py`

**Interfaces:**
- Consumes: `app.full_main:app` (Task 3), `backend/Dockerfile.api`, `backend/Dockerfile.worker`, `services/realtime_agent/Dockerfile` (đã tồn tại, không đổi).
- Produces: service `brain-api` là điểm vào duy nhất qua `caddy` (Task 6 dùng lại tên service `brain-api:8000`).

- [ ] **Step 1: Viết compose-contract test**

Append vào `backend/app/tests/test_compose_contract.py`:

```python
SELF_HOST_COMPOSE = "deploy/self_host/docker-compose.yaml"


def test_self_host_compose_defines_expected_services():
    compose = yaml.safe_load((REPO_ROOT / SELF_HOST_COMPOSE).read_text())
    assert set(compose["services"].keys()) == {
        "caddy", "postgres", "minio", "migrate", "brain-api", "agent-worker", "realtime-agent",
    }


def test_self_host_compose_never_publishes_postgres_minio_or_worker_ports():
    compose = yaml.safe_load((REPO_ROOT / SELF_HOST_COMPOSE).read_text())
    services = compose["services"]

    assert "ports" not in services["postgres"]
    assert "ports" not in services["minio"]
    assert "ports" not in services["agent-worker"]


def test_self_host_compose_only_exposes_caddy_publicly():
    compose = yaml.safe_load((REPO_ROOT / SELF_HOST_COMPOSE).read_text())
    caddy_ports = compose["services"]["caddy"]["ports"]

    assert "80:80" in caddy_ports
    assert "443:443" in caddy_ports
    assert "ports" not in compose["services"]["brain-api"]


def test_self_host_compose_runs_brain_api_as_full_role():
    compose = yaml.safe_load((REPO_ROOT / SELF_HOST_COMPOSE).read_text())
    brain_api = compose["services"]["brain-api"]

    assert "APP_ROLE=full" in brain_api["environment"]
    assert brain_api["command"] == "uvicorn app.full_main:app --host 0.0.0.0 --port 8000"


def test_self_host_compose_never_includes_desktop_worker():
    raw_text = (REPO_ROOT / SELF_HOST_COMPOSE).read_text()
    assert "desktop_worker" not in raw_text

    compose = yaml.safe_load(raw_text)
    assert "desktop_worker" not in compose["services"]
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && python -m pytest app/tests/test_compose_contract.py -k self_host -v`
Expected: FAIL — `deploy/self_host/docker-compose.yaml` chưa tồn tại (`FileNotFoundError`).

- [ ] **Step 3: Tạo `deploy/self_host/docker-compose.yaml`**

```yaml
services:
  # ─────────────────────────────────────────────────────────────
  # Reverse proxy - service DUY NHẤT lộ ra internet. TLS Let's Encrypt
  # tự động, phỏng theo deploy/central_vps/Caddyfile.
  # ─────────────────────────────────────────────────────────────
  caddy:
    image: caddy:2-alpine
    container_name: cosa_self_host_caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    environment:
      - SELF_HOST_DOMAIN=${SELF_HOST_DOMAIN:-app.example.com}
      - ACME_EMAIL=${ACME_EMAIL:-admin@example.com}
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - brain-api

  # ─────────────────────────────────────────────────────────────
  # Postgres - authority cho dữ liệu business của deployment self-host
  # này (Personal Mode single-authority). Chỉ mạng nội bộ Docker - không
  # có `ports:`, không bao giờ public.
  # ─────────────────────────────────────────────────────────────
  postgres:
    image: pgvector/pgvector:pg16
    container_name: cosa_self_host_postgres
    environment:
      - POSTGRES_USER=${POSTGRES_USER:-javis}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set in .env}
      - POSTGRES_DB=${POSTGRES_DB:-javis}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-javis}"]
      interval: 5s
      timeout: 5s
      retries: 10
    restart: unless-stopped

  # ─────────────────────────────────────────────────────────────
  # MinIO - object storage cho Vault. Chỉ mạng nội bộ Docker.
  # ─────────────────────────────────────────────────────────────
  minio:
    image: minio/minio:latest
    container_name: cosa_self_host_minio
    environment:
      - MINIO_ROOT_USER=${MINIO_ACCESS_KEY:-minioadmin}
      - MINIO_ROOT_PASSWORD=${MINIO_SECRET_KEY:?MINIO_SECRET_KEY must be set in .env}
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 5s
      timeout: 5s
      retries: 10
    restart: unless-stopped

  migrate:
    build:
      context: ../../backend
      dockerfile: Dockerfile.api
    command: alembic upgrade head
    environment:
      - DATABASE_URL=${DATABASE_URL:-postgresql://javis:javis@postgres:5432/javis}
    depends_on:
      postgres:
        condition: service_healthy
    restart: "no"

  # ─────────────────────────────────────────────────────────────
  # brain-api - service duy nhất caddy trỏ vào. APP_ROLE=full: self-host
  # là 1 bản cài full-stack single-tenant, cùng phạm vi domain với
  # desktop (markdown/Structure.md:286 - "không multi-tenant SaaS vào
  # local app"), KHÔNG phải role central_control_plane.
  # ─────────────────────────────────────────────────────────────
  brain-api:
    build:
      context: ../../backend
      dockerfile: Dockerfile.api
    container_name: cosa_self_host_brain_api
    command: uvicorn app.full_main:app --host 0.0.0.0 --port 8000
    environment:
      - APP_ROLE=full
      - APP_ENV=${APP_ENV:-production}
      - DATABASE_URL=${DATABASE_URL:-postgresql://javis:javis@postgres:5432/javis}
      - MINIO_ENDPOINT=http://minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-minioadmin}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY:?MINIO_SECRET_KEY must be set in .env}
      - JWT_SECRET=${JWT_SECRET:?JWT_SECRET must be set in .env}
      - MASTER_SECRET_KEY=${MASTER_SECRET_KEY:?MASTER_SECRET_KEY must be set in .env}
      - COSA_ALLOWED_ORIGINS=${COSA_ALLOWED_ORIGINS:?COSA_ALLOWED_ORIGINS must be set in .env}
      - CHAT_DEFAULT_PROVIDER=${CHAT_DEFAULT_PROVIDER:-deepseek}
      - CHAT_DEFAULT_MODEL=${CHAT_DEFAULT_MODEL:-deepseek-chat}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:-}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
      - GEMINI_API_KEY=${GEMINI_API_KEY:-}
      - LIVEKIT_URL=${LIVEKIT_URL:-}
      - LIVEKIT_API_KEY=${LIVEKIT_API_KEY:-}
      - LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET:-}
    depends_on:
      postgres:
        condition: service_healthy
      minio:
        condition: service_healthy
      migrate:
        condition: service_completed_successfully
    restart: unless-stopped

  # ─────────────────────────────────────────────────────────────
  # agent-worker - chỉ mạng nội bộ Docker, không có `ports:` (giống hệt
  # root docker-compose.yml - cũng không public ở đó).
  # ─────────────────────────────────────────────────────────────
  agent-worker:
    build:
      context: ../../backend
      dockerfile: Dockerfile.worker
    container_name: cosa_self_host_agent_worker
    environment:
      - APP_ENV=${APP_ENV:-production}
      - JAVIS_STATE_DIR=/var/lib/javis-connectors
      - DATABASE_URL=${DATABASE_URL:-postgresql://javis:javis@postgres:5432/javis}
      - MINIO_ENDPOINT=http://minio:9000
      - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY:-minioadmin}
      - MINIO_SECRET_KEY=${MINIO_SECRET_KEY:?MINIO_SECRET_KEY must be set in .env}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:-}
      - DEEPSEEK_BASE_URL=${DEEPSEEK_BASE_URL:-https://api.deepseek.com}
      - DEEPSEEK_DEFAULT_MODEL=${DEEPSEEK_DEFAULT_MODEL:-deepseek-chat}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-}
      - OPENROUTER_BASE_URL=${OPENROUTER_BASE_URL:-https://openrouter.ai/api/v1}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
      - GEMINI_API_KEY=${GEMINI_API_KEY:-}
      - CHAT_DEFAULT_PROVIDER=${CHAT_DEFAULT_PROVIDER:-deepseek}
      - CHAT_DEFAULT_MODEL=${CHAT_DEFAULT_MODEL:-deepseek-chat}
      - MASTER_SECRET_KEY=${MASTER_SECRET_KEY:?MASTER_SECRET_KEY must be set in .env}
      - COSA_EXECUTION_PROVIDER=${COSA_EXECUTION_PROVIDER:-mock}
    depends_on:
      postgres:
        condition: service_healthy
      minio:
        condition: service_healthy
      brain-api:
        condition: service_started
      migrate:
        condition: service_completed_successfully
    volumes:
      - connector_state:/var/lib/javis-connectors
    restart: unless-stopped

  # ─────────────────────────────────────────────────────────────
  # realtime-agent - worker giọng nói/video. Self-host được truy cập từ
  # xa (mobile/web qua internet, không phải desktop loopback), nên đăng
  # ký với 1 LIVEKIT_URL bên ngoài (LiveKit Cloud hoặc LiveKit server tự
  # vận hành riêng) thay vì tự bundle 1 LiveKit server trên chính VPS
  # này - tự host WebRTC/TURN nằm ngoài phạm vi quyết định này. Để
  # trống LIVEKIT_URL trong .env để tắt hẳn service này (profile
  # "realtime", không chạy mặc định).
  # ─────────────────────────────────────────────────────────────
  realtime-agent:
    build:
      context: ../../services/realtime_agent
      dockerfile: Dockerfile
    container_name: cosa_self_host_realtime_agent
    environment:
      - DATABASE_URL=${DATABASE_URL:-postgresql://javis:javis@postgres:5432/javis}
      - LIVEKIT_URL=${LIVEKIT_URL:-}
      - LIVEKIT_API_KEY=${LIVEKIT_API_KEY:-}
      - LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET:-}
      - LIVEKIT_FORCE_CLOUD=true
      - GEMINI_API_KEY=${GEMINI_API_KEY:-}
      - GOOGLE_API_KEY=${GEMINI_API_KEY:-}
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    profiles: ["realtime"]

volumes:
  postgres_data:
  minio_data:
  connector_state:
  caddy_data:
  caddy_config:
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `cd backend && python -m pytest app/tests/test_compose_contract.py -v`
Expected: tất cả pass

- [ ] **Step 5: Commit**

```bash
git add deploy/self_host/docker-compose.yaml backend/app/tests/test_compose_contract.py
git commit -m "feat(self-host): add docker-compose.yaml for founder self-host deployment"
```

---

### Task 6: `deploy/self_host/Caddyfile`

**Files:**
- Create: `deploy/self_host/Caddyfile`
- Modify: `backend/app/tests/test_compose_contract.py`

**Interfaces:**
- Consumes: service `brain-api` (Task 5, cổng nội bộ `8000`).

- [ ] **Step 1: Viết test**

Append vào `backend/app/tests/test_compose_contract.py`:

```python
def test_self_host_caddyfile_proxies_only_brain_api():
    caddyfile = (REPO_ROOT / "deploy/self_host/Caddyfile").read_text()

    assert "reverse_proxy brain-api:8000" in caddyfile
    assert "SELF_HOST_DOMAIN" in caddyfile
    assert "central_api" not in caddyfile
    assert "central_postgres" not in caddyfile
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && python -m pytest app/tests/test_compose_contract.py -k self_host_caddyfile -v`
Expected: FAIL — file chưa tồn tại.

- [ ] **Step 3: Tạo `deploy/self_host/Caddyfile`**

```text
# ============================================================================
# CADDYFILE - SELF-HOST REVERSE PROXY & AUTOMATIC SSL
# Phỏng theo deploy/central_vps/Caddyfile - 1 domain -> brain-api:8000.
# ============================================================================

{
    email {$ACME_EMAIL:admin@example.com}
    admin off
}

{$SELF_HOST_DOMAIN:app.example.com} {
    reverse_proxy brain-api:8000 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
}
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `cd backend && python -m pytest app/tests/test_compose_contract.py -v`
Expected: tất cả pass

- [ ] **Step 5: Commit**

```bash
git add deploy/self_host/Caddyfile backend/app/tests/test_compose_contract.py
git commit -m "feat(self-host): add Caddyfile for TLS reverse proxy to brain-api"
```

---

### Task 7: `deploy/self_host/.env.example`

**Files:**
- Create: `deploy/self_host/.env.example`
- Modify: `backend/app/tests/test_compose_contract.py`

**Interfaces:**
- Consumes: tên biến môi trường đã dùng ở `deploy/self_host/docker-compose.yaml` (Task 5) và `deploy/self_host/Caddyfile` (Task 6).

- [ ] **Step 1: Viết test**

Append vào `backend/app/tests/test_compose_contract.py`:

```python
def test_self_host_env_example_documents_required_vars():
    env_example = (REPO_ROOT / "deploy/self_host/.env.example").read_text()

    for var in (
        "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB",
        "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY",
        "JWT_SECRET", "MASTER_SECRET_KEY", "COSA_ALLOWED_ORIGINS",
        "SELF_HOST_DOMAIN", "DEEPSEEK_API_KEY",
        "LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET",
    ):
        assert var in env_example

    assert "APP_ROLE=central_control_plane" not in env_example
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && python -m pytest app/tests/test_compose_contract.py -k self_host_env_example -v`
Expected: FAIL — file chưa tồn tại.

- [ ] **Step 3: Tạo `deploy/self_host/.env.example`**

```bash
# ============================================================================
# COSA SELF-HOST FULL STACK - VPS ENVIRONMENT VARIABLES
# File này nằm CÙNG thư mục với docker-compose.yaml (deploy/self_host/.env) -
# docker compose CHỈ đọc .env ở đây, KHÔNG đọc backend/.env bên trong
# container (không service nào trong docker-compose.yaml khai báo
# `env_file: ../../backend/.env`).
# ============================================================================

# --- Domain & TLS (Caddy tự cấp Let's Encrypt) ---
SELF_HOST_DOMAIN=app.example.com
ACME_EMAIL=admin@example.com

# --- PostgreSQL (authority cho dữ liệu business - Personal Mode single-authority) ---
POSTGRES_USER=javis
POSTGRES_PASSWORD=ChangeThisToAStrongPassword2026!
POSTGRES_DB=javis
DATABASE_URL=postgresql://javis:ChangeThisToAStrongPassword2026!@postgres:5432/javis

# --- MinIO (object storage cho Vault) ---
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=ChangeThisToAStrongSecret2026!

# --- Auth / Vault master secrets (bắt buộc, tối thiểu 32 ký tự, KHÔNG dùng giá trị dev mặc định) ---
JWT_SECRET=change-this-to-a-random-secret-at-least-32-chars
MASTER_SECRET_KEY=change-this-to-a-random-secret-at-least-32-chars

# --- CORS allowlist (bắt buộc khi APP_ENV=production, không được để wildcard) ---
COSA_ALLOWED_ORIGINS=https://app.example.com

# --- AI Provider keys (điền provider bạn dùng) ---
CHAT_DEFAULT_PROVIDER=deepseek
CHAT_DEFAULT_MODEL=deepseek-chat
DEEPSEEK_API_KEY=
OPENROUTER_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=

# --- Realtime voice/video (tuỳ chọn - để trống để tắt "docker compose --profile realtime up -d") ---
LIVEKIT_URL=
LIVEKIT_API_KEY=
LIVEKIT_API_SECRET=
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `cd backend && python -m pytest app/tests/test_compose_contract.py -v`
Expected: tất cả pass

- [ ] **Step 5: Commit**

```bash
git add deploy/self_host/.env.example backend/app/tests/test_compose_contract.py
git commit -m "feat(self-host): add .env.example template"
```

---

### Task 8: `deploy/self_host/README.md`

**Files:**
- Create: `deploy/self_host/README.md`
- Modify: `backend/app/tests/test_compose_contract.py`

**Interfaces:**
- Consumes: nội dung từ Task 5-7 (`docker-compose.yaml`, `Caddyfile`, `.env.example`).

- [ ] **Step 1: Viết test**

Append vào `backend/app/tests/test_compose_contract.py`:

```python
def test_self_host_readme_documents_env_file_gotcha_and_desktop_worker_exclusion():
    readme = (REPO_ROOT / "deploy/self_host/README.md").read_text()

    assert "backend/.env" in readme
    assert "docker compose" in readme or "docker-compose" in readme
    assert "desktop_worker" in readme
    assert "subprocess" in readme.lower() or "shell=true" in readme.lower()
    assert "cp .env.example .env" in readme
```

- [ ] **Step 2: Chạy test, xác nhận FAIL**

Run: `cd backend && python -m pytest app/tests/test_compose_contract.py -k self_host_readme -v`
Expected: FAIL — file chưa tồn tại.

- [ ] **Step 3: Tạo `deploy/self_host/README.md`**

```markdown
# Hướng Dẫn Tự Host COSA Full Stack Trên VPS Riêng

Hướng dẫn founder tự triển khai **toàn bộ COSA** (không chỉ control-plane) lên
VPS riêng của mình, dùng chính `backend/app/full_main.py` (role `full` - đủ 5
domain: founder_os/business/workforce/integrations/platform) - cùng 1 code
chạy trên desktop (Flutter), chỉ khác cách deploy.

Đây là **lựa chọn triển khai bổ sung**, không thay thế desktop-first. Xem
`docs/architecture/COSA_ADK_ORCHESTRATOR_UUID7_PROPOSAL.md`, Quyết định 3.

---

## 1. Kiến trúc

```text
deploy/self_host/
├── docker-compose.yaml   # caddy, postgres, minio, migrate, brain-api, agent-worker, realtime-agent
├── Caddyfile             # Reverse proxy + TLS Let's Encrypt tự động, 1 domain -> brain-api:8000
├── .env.example          # Template biến môi trường
└── README.md
```

Chỉ **`caddy`** (cổng 80/443) lộ ra internet. `brain-api` chỉ nghe trên mạng
nội bộ Docker (không có `ports:`), Caddy là reverse proxy TLS duy nhất phía
trước nó. `postgres`, `minio`, `agent-worker` **không** có `ports:` publish ra
host - chỉ giao tiếp qua mạng nội bộ Docker giữa các service trong cùng
compose file này, không public.

**KHÔNG bao gồm `desktop_worker`** (`desktop_worker/main.py`): đây là 1 plane
chạy `subprocess(..., shell=True)` không sandbox, chỉ an toàn khi bind
loopback (`127.0.0.1`) trên máy dev cục bộ. Chạy nó trên VPS - hoặc lộ nó ra
ngoài dưới bất kỳ hình thức nào - sẽ biến VPS thành remote-code-execution công
khai. Không có ca sử dụng hợp lệ nào cho self-host; service này cố tình không
xuất hiện trong `docker-compose.yaml` ở đây.

## 2. Nguyên tắc single-authority (Personal Mode)

Self-host 1 founder = **Personal Mode**: Postgres tự host ở đây là
**authority duy nhất** cho dữ liệu business (Task/CRM/Finance/...). Central
control-plane (do COSA vận hành) chỉ đóng vai trò licensing/entitlement -
**không** đồng bộ 2 chiều dữ liệu business với self-host của bạn. Nếu sau này
cần nhiều Human Employee cộng tác (Team Mode), đó là 1 hành động "Promote to
Team Workspace" tường minh riêng - self-host mặc định không tự động làm việc
này.

Self-host vẫn **single-tenant mỗi deployment** - 1 lần cài đặt = 1 công ty,
giống desktop (`markdown/Structure.md:286`: "Không thiết kế multi-tenant SaaS
vào local application.").

## 3. Cài đặt (1 lệnh sau khi cấu hình)

```bash
# 1. SSH vào VPS, clone repo
ssh root@<IP_VPS>
git clone https://github.com/<your-fork>/javis-saas.git /opt/cosa
cd /opt/cosa/deploy/self_host

# 2. Tạo file cấu hình môi trường
cp .env.example .env
# Chỉnh sửa .env: SELF_HOST_DOMAIN, POSTGRES_PASSWORD, MINIO_SECRET_KEY,
# JWT_SECRET, MASTER_SECRET_KEY, COSA_ALLOWED_ORIGINS, DEEPSEEK_API_KEY, ...

# 3. Trỏ DNS domain của bạn (bản ghi A) về IP VPS này TRƯỚC khi chạy -
#    Caddy cần domain resolve được để tự cấp SSL Let's Encrypt.

# 4. Khởi chạy toàn bộ stack
docker compose up -d --build
```

Voice/realtime (LiveKit) là **tuỳ chọn** - mặc định service `realtime-agent`
nằm trong Docker Compose profile `realtime`, không chạy nếu bạn không cấu
hình `LIVEKIT_URL`/`LIVEKIT_API_KEY`/`LIVEKIT_API_SECRET` trong `.env`. Muốn
bật:

```bash
docker compose --profile realtime up -d
```

## 4. Cảnh báo quan trọng đã biết: `.env` gốc, không phải `backend/.env`

`docker compose` chỉ đọc file `.env` nằm **cùng thư mục với file
`docker-compose.yaml`** (tức `deploy/self_host/.env` ở đây) để substitute các
biến `${VAR}` trong chính file compose. Nó **KHÔNG** đọc `backend/.env` bên
trong container - nếu bạn chỉnh `backend/.env` mong đổi cấu hình, container
`brain-api`/`agent-worker` sẽ **không** thấy giá trị đó, dẫn tới lỗi kiểu
"invalid API key" giả (biến trông như đã set nhưng thực chất container vẫn
dùng giá trị mặc định/rỗng). Luôn set biến trong `deploy/self_host/.env`,
không phải `backend/.env`.

## 5. Kiểm tra sau khi deploy

```bash
curl https://<SELF_HOST_DOMAIN>/live
curl https://<SELF_HOST_DOMAIN>/ready
```

`/ready` trả về `checks: {database, storage, migrations, worker}` - cả 4 phải
`"ok"` khi stack chạy đúng (role `full` giữ nguyên đủ 4 check, khác với role
`central_control_plane` chỉ check `database`).
```

- [ ] **Step 4: Chạy test, xác nhận PASS**

Run: `cd backend && python -m pytest app/tests/test_compose_contract.py -v`
Expected: tất cả pass

- [ ] **Step 5: Chạy toàn bộ test suite backend 1 lần cuối**

Run: `cd backend && python -m pytest app/tests -q`
Expected: PASS toàn bộ, không regress bất kỳ test nào có trước plan này.

- [ ] **Step 6: Commit**

```bash
git add deploy/self_host/README.md backend/app/tests/test_compose_contract.py
git commit -m "docs(self-host): add setup README with .env gotcha and desktop_worker exclusion notes"
```

---

## Self-Review

**1. Spec coverage** — đối chiếu từng mục của Quyết định 3:
- App factory thật (`create_app(role)`, import có điều kiện, không chỉ mount có điều kiện) → Task 2.
- 2 entrypoint mỏng `full_main.py`/`central_main.py` → Task 3.
- Sửa `deploy/central_vps/docker-compose.yaml` (`APP_ROLE=central_control_plane`, đổi lệnh chạy) → Task 4 (kèm 2 phát hiện phụ: thiếu `command` override nên đang chạy alembic local vào DB central; thiếu `COSA_RUNTIME_PLANE=control` nên endpoint ký entitlement chưa từng đăng ký).
- `deploy/self_host/docker-compose.yaml` (chỉ `brain-api` lộ ra ngoài, `postgres`/`minio`/`agent-worker` nội bộ) → Task 5.
- `deploy/self_host/Caddyfile` (phỏng theo central_vps) → Task 6.
- `deploy/self_host/.env.example` → Task 7.
- `deploy/self_host/README.md` (1 lệnh, cảnh báo `.env` gốc) → Task 8.
- Nguyên tắc single-authority (Personal Mode/Team Mode, không active-active) → ghi trong Global Constraints + README (Task 8, mục 2) làm design constraint tường minh, không thêm code sync 2 chiều nào.
- `desktop_worker` không bao giờ vào self-host → Global Constraints + test riêng ở Task 5 (`test_self_host_compose_never_includes_desktop_worker`) + giải thích trong README (Task 8).
- Single-tenant per deployment (`markdown/Structure.md:286`) → trích dẫn trong Global Constraints + README.
- Phasing 1 (compose + Caddyfile + README, verify tay trên VPS thật) → Task 5+6+8 tạo đủ file; verify tay trên VPS thật là bước vận hành ngoài phạm vi "viết code" của plan này, đã nêu rõ ở README mục 3.
- Phasing 2 (APP_ROLE split áp cho cả central_vps) → Task 2+4.
- Phasing 3 (script tự động hoá setup, tuỳ chọn) → cố tình KHÔNG đưa vào plan này vì đề bài đánh dấu "tuỳ chọn" và `docker compose up -d --build` ở Task 8 đã là "1 lệnh" như yêu cầu — không cần thêm script.

**2. Placeholder scan** — không còn "TBD"/"tương tự Task N"/"thêm xử lý lỗi phù hợp"; mọi step code đều là nội dung thật, đầy đủ, có thể chạy được nguyên trạng.

**3. Type/tên nhất quán** — `FULL_ROLE`/`CENTRAL_CONTROL_PLANE_ROLE`/`resolve_app_role`/`create_app` dùng đúng 1 tên xuyên suốt Task 1→3; `APP_ROLE=full`/`APP_ROLE=central_control_plane` khớp giữa code Python và compose; prefix mount `/api/v1/platform` cho `platform.sync.router` khớp giữa `_mount_full_routers` (qua aggregator) và `_mount_central_control_plane_routers` (mount thẳng) nên URL client không đổi giữa 2 role; tên service `brain-api:8000` khớp giữa `docker-compose.yaml` (Task 5) và `Caddyfile` (Task 6).

## Rủi ro/khoảng hở đã phát hiện, nằm ngoài phạm vi Quyết định 3 (không sửa trong plan này)

- **Lược đồ Central DB chưa khớp router**: bảng `platform_outbox`/`platform_inbox`/`local_entitlement_snapshots` (dùng bởi `app.platform.sync.router`, router mà role `central_control_plane` mount) **không tồn tại** trong `deploy/central_vps/init_central_postgres.sql` hiện tại (chỉ có `platform_users`/`companies`/`licenses`/... - lược đồ registry, không phải lược đồ sync). Ngược lại, `app.platform.auth.router` dùng `app.db.models.User/Workspace` (lược đồ local/company) chứ không dùng `platform_users` central - nên dù có mount, nó cũng không chạy đúng trên DB central. Đây thuộc phạm vi "central DB schema" - 1 trong 3 subsystem đang được agent khác plan song song; plan này chỉ đảm bảo role `central_control_plane` KHÔNG import những gì không cần, không tự ý mở rộng sang sửa lược đồ DB.
- **`validate_runtime_configuration()` không role-aware**: nếu tương lai `deploy/central_vps` set đúng `APP_ENV=production` (hiện đang chỉ set `ENVIRONMENT=production`, khiến hàm này luôn no-op vì nó chỉ đọc `APP_ENV`), `central_api` sẽ crash lúc startup vì thiếu `JWT_SECRET`/`MASTER_SECRET_KEY` - 2 secret vốn chỉ có ý nghĩa cho role `full` (JWT auth, Vault master key). Đây là bug tiềm ẩn có sẵn từ trước, không bị plan này làm nặng thêm hay nhẹ đi (compose central vẫn set `ENVIRONMENT=production` như cũ) - nêu ở đây để người review biết, không mở task sửa vì `app/core/runtime_config.py` không nằm trong danh sách file của Quyết định 3.
