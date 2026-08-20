import logging
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Nạp file .env từ thư mục gốc dự án trước khi import router
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from app.core.runtime_config import validate_runtime_configuration, resolve_cors_origins
validate_runtime_configuration()

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from sqlalchemy import text

# Database Engine & S3 Storage
from app.db.session import engine, SessionLocal
from app.core.migration_health import get_migration_health
from app.core.worker_health import get_worker_health
from app.integrations.storage.s3_client import ensure_bucket_exists, get_s3_client
from app.platform.sync.entitlement_manager import load_all_current_snapshots_into_cache
from app.workforce.agents.orchestration.mission_control_bus import register_default_listeners
from app.founder_os.strategy.services.capability_registry_seed_service import seed_canonical_capability_registry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: "FastAPI"):
    # Object storage is a required dependency for Vault revisions.  Provision
    # the configured bucket at startup so a first write cannot fail merely
    # because an empty MinIO/S3 environment has just been bootstrapped.
    try:
        ensure_bucket_exists()
    except Exception:
        logger.exception("Failed to ensure object-storage bucket on startup")

    # Startup: reload persisted entitlement snapshots (G2 P0.3 / G3 §9.3) —
    # without this, every process restart would silently fall back every
    # company to the Free tier default even with a still-valid persisted
    # license, since EntitlementManager's cache is otherwise process-memory-only.
    try:
        db = SessionLocal()
        try:
            load_all_current_snapshots_into_cache(db)
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to load persisted entitlement snapshots on startup")

    # G3 Phase 1B: seed the canonical Capability Registry (capability_definitions)
    # from CAPABILITY_CATALOG + business pack YAML on every startup — idempotent
    # upsert, so CapabilityGateway/the /catalog endpoint always have DB rows to
    # read instead of falling back to the static dict on a cold DB.
    try:
        db = SessionLocal()
        try:
            seed_canonical_capability_registry(db)
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to seed canonical capability registry on startup")

    # G1/G3 §10.6: attach the process-wide mission_control_bus listener(s) —
    # de-risks the Learning Review Worker's trigger point ahead of Phase 1E.
    try:
        register_default_listeners()
    except Exception:
        logger.exception("Failed to register mission_control_bus default listeners on startup")

    yield


# --- Import 5 Domain Master Routers ---
from app.founder_os.router import router as founder_os_router
from app.business.router import router as business_router
from app.workforce.router import router as workforce_router
from app.integrations.router import router as integrations_router
from app.platform.router import router as platform_router

# G3 §9.6b: mounted directly (not through the still-unaudited, unmounted
# `workforce.agents.gateway.router` package that bundles 8 sub-routers) — see
# that package's module docstring for why the other 7 stay unmounted for now.
from app.workforce.agents.capabilities.router import router as capabilities_router
from app.workforce.agents.delegation.router import router as delegation_router


# Cấu hình Swagger / OpenAPI Documentation (Mặc định tắt trên Production / hoặc khi không bật ENABLE_DOCS)
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

# Cấu hình CORS — allowlist từ COSA_ALLOWED_ORIGINS, không cho wildcard ngoài development (G2 P0.10)
origins = resolve_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================================
# ĐĂNG KÝ 5 KHỐI DOMAIN CHÍNH (5-DOMAIN MASTER ROUTERS)
# =====================================================================

# 1. Founder OS Domain (Identity, Strategy, OKRs, Tactics Tuần 1..N, Tasks, Outcomes)

app.include_router(founder_os_router)

# 2. Business Domain (Sales, Marketing, Finance TT58 VN, Legal VN, Learning)
app.include_router(business_router)

# 3. AI Workforce Domain (Chat, AI Engine, Agents, Skills, Governance, Memory, Multi-agent)
app.include_router(workforce_router)

# 4. Integrations Domain (Channels Omnichannel, Realtime Voice/Video, Workflows, Devices)
app.include_router(integrations_router)

# 5. Platform Domain (Auth, Vault, License, Core/Admin, Organization, Policy Funding, Tech)
app.include_router(platform_router)

# Capabilities Registry (fast win, G3 §4/§9.6b) — /check, /grants, /catalog live;
# /execute stays behind COSA_ENABLE_CAPABILITY_EXECUTE until Phase 1B.
app.include_router(capabilities_router, prefix="/api/v1/capabilities", tags=["capabilities"])
app.include_router(
    delegation_router,
    prefix="/api/v1/agents/delegations",
    tags=["agents-delegations"],
)


# =====================================================================
# SYSTEM HEALTH & LIVENESS PROBES
# =====================================================================

@app.get("/live")
def liveness_probe():
    return {"status": "alive"}


@app.get("/ready")
def readiness_probe(response: Response):
    checks = {"database": "unknown", "storage": "unknown", "migrations": "unknown", "worker": "unknown"}
    healthy = True

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc.__class__.__name__}"
        healthy = False

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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
