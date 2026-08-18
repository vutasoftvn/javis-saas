import os
from dotenv import load_dotenv

# Nạp file .env từ thư mục gốc dự án trước khi import router
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from app.core.runtime_config import validate_runtime_configuration
validate_runtime_configuration()

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from sqlalchemy import text

# Database Engine & S3 Storage
from app.db.session import engine
from app.core.migration_health import get_migration_health
from app.core.worker_health import get_worker_health
from app.integrations.storage.s3_client import get_s3_client


# --- Import 5 Domain Master Routers ---
from app.founder_os.router import router as founder_os_router
from app.business.router import router as business_router
from app.workforce.router import router as workforce_router
from app.integrations.router import router as integrations_router
from app.platform.router import router as platform_router


app = FastAPI(
    title="COSA OS API",
    description="Hệ điều hành Doanh nghiệp Tự trị (Autonomous Enterprise Operating System) - Kiến trúc 5 Domain",
    version="2.0.0"
)

# Cấu hình CORS
origins = ["*"]
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


# =====================================================================
# SYSTEM HEALTH & LIVENESS PROBES
# =====================================================================

@app.get("/live")
def liveness_probe():
    return {"status": "alive", "architecture": "5-Domain Clean Architecture"}


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
