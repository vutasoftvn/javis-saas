import asyncio
import os
from dotenv import load_dotenv

# Nạp file .env từ thư mục gốc dự án trước khi import router
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from fastapi import FastAPI, Response
import uvicorn
from sqlalchemy import text

from app.modules.iam import router as auth
from app.modules.vault import router as vault
from app.modules.vault import sync_router as sync
from app.modules.vault import brains_router as brains
from app.modules.vault import knowledge_router
from app.modules.chat import router as chat
from app.modules.chat import ai_api as ai
from app.modules.tasks import router as tasks
from app.modules.tasks import agents_router as agents
from app.modules.workflows import router as workflows
from app.modules.strategy import router as strategy
from app.modules.strategy import okrs_router as okrs
from app.modules.strategy import execution_router as execution
from app.modules.strategy import portfolio_router as portfolios
from app.modules.strategy import next_action_router as next_actions
from app.modules.strategy import living_pestel_router as living_pestel


from app.modules.integrations import router as connectors

from app.modules.integrations import connectors_zalo_router as connectors_zalo
from app.modules.integrations import google_router as connectors_google
from app.modules.integrations import email_approval_router as email_approvals
from app.modules.integrations import channels_router as channels
from app.modules.integrations import plugins_router as plugins
from app.modules.platform import router as admin
from app.modules.platform import domain_router as domain
from app.modules.platform import events_router
from app.modules.marketing import router as marketing
from app.modules.outcomes.router import router as outcomes_router
from app.modules.devices.router import router as devices_router
from app.modules.organization.router import router as organization_router

from app.db.session import engine
from app.integrations.s3_client import get_s3_client, ensure_bucket_exists
from app.services.channels.channel_worker import channel_worker_loop

app = FastAPI(title="Javis Brain API")

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(vault.router, prefix="/api/v1/vault", tags=["vault"])
app.include_router(knowledge_router.router, prefix="/api/v1/vault", tags=["vault-knowledge"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(strategy.router, prefix="/api/v1/strategy", tags=["strategy"])
app.include_router(portfolios.router, prefix="/api/v1/strategy", tags=["portfolios"])
app.include_router(next_actions.router, prefix="/api/v1/strategy", tags=["next-actions"])
app.include_router(living_pestel.router, prefix="/api/v1/strategy", tags=["living-pestel"])


app.include_router(marketing.router, prefix="/api/v1/marketing", tags=["marketing"])

app.include_router(okrs.router, prefix="/api/v1/okrs", tags=["okrs"])
app.include_router(execution.router, prefix="/api/v1/execution", tags=["execution"])
app.include_router(workflows.router, prefix="/api/v1/workflows", tags=["workflows"])
app.include_router(outcomes_router, prefix="/api/v1", tags=["outcomes"])
app.include_router(devices_router, prefix="/api/v1", tags=["devices"])
app.include_router(organization_router, prefix="/api/v1", tags=["organization"])
app.include_router(events_router.router, prefix="/api/v1/events", tags=["events"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["ai"])
app.include_router(plugins.router, prefix="/api/v1/plugins", tags=["plugins"])
app.include_router(channels.router, prefix="/api/v1/channels", tags=["channels"])
app.include_router(sync.router, prefix="/api/v1/sync", tags=["sync"])
app.include_router(brains.router, prefix="/api/v1/brains", tags=["brains"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(connectors.router, prefix="/api/v1/connectors", tags=["connectors"])
app.include_router(connectors_zalo.router, prefix="/api/v1/connectors", tags=["connectors-zalo"])
app.include_router(connectors_google.router, prefix="/api/v1/connectors", tags=["connectors-google"])
app.include_router(email_approvals.router, prefix="/api/v1/connectors", tags=["email-approvals"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(domain.router, prefix="/api/v1/domain", tags=["domain"])

@app.on_event("startup")
async def on_startup():
    try:
        ensure_bucket_exists()
    except Exception as exc:
        print(f"[MinIO Warning] {exc}")
    try:
        from app.db.base import Base
        Base.metadata.create_all(bind=engine)
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE key_results ADD COLUMN IF NOT EXISTS title VARCHAR(255);"))
            conn.execute(text("ALTER TABLE marketing_contexts ADD COLUMN IF NOT EXISTS market JSONB;"))
            conn.execute(text("ALTER TABLE marketing_contexts ADD COLUMN IF NOT EXISTS category VARCHAR(255);"))
            conn.execute(text("ALTER TABLE marketing_contexts ADD COLUMN IF NOT EXISTS customer_research JSONB;"))
            conn.execute(text("ALTER TABLE marketing_contexts ADD COLUMN IF NOT EXISTS product_marketing JSONB;"))
            conn.execute(text("ALTER TABLE marketing_contexts ADD COLUMN IF NOT EXISTS offer_architecture JSONB;"))
            conn.execute(text("ALTER TABLE marketing_contexts ADD COLUMN IF NOT EXISTS marketing_plan_12w JSONB;"))
            conn.execute(text("ALTER TABLE marketing_contexts ADD COLUMN IF NOT EXISTS proofs JSONB;"))
            conn.execute(text("ALTER TABLE marketing_contexts ADD COLUMN IF NOT EXISTS channels JSONB;"))
    except Exception as exc:
        print(f"[DB Migration Warning] {exc}")

        
    asyncio.create_task(channel_worker_loop())

@app.get("/live")
def liveness_probe():
    return {"status": "alive"}

@app.get("/ready")
def readiness_probe(response: Response):
    checks = {"database": "unknown", "storage": "unknown"}
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

    if not healthy:
        response.status_code = 503
    return {"status": "ready" if healthy else "not_ready", "checks": checks}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
