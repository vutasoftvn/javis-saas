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
