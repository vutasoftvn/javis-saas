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
from app.modules.platform import feature_flags_router
from app.modules.platform import domain_router as domain
from app.modules.platform import events_router
from app.modules.marketing import router as marketing
from app.modules.outcomes.router import router as outcomes_router
from app.modules.devices.router import router as devices_router
from app.modules.organization.router import router as organization_router
from app.modules.realtime import router as realtime
from app.modules.agent_memory import router as agent_memory
from app.modules.learning import router as learning

from app.core.events import cross_process_event_listener
from app.db.session import engine
from app.integrations.s3_client import get_s3_client, ensure_bucket_exists

app = FastAPI(title="COSA Brain API")

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
app.include_router(realtime.router, prefix="/api/v1/realtime", tags=["realtime"])
app.include_router(agent_memory.router, prefix="/api/v1/memory", tags=["agent-memory"])
app.include_router(learning.router, prefix="/api/v1/learning", tags=["learning"])
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
app.include_router(feature_flags_router.router, prefix="/api/v1/platform", tags=["platform"])
app.include_router(domain.router, prefix="/api/v1/domain", tags=["domain"])

@app.on_event("startup")
async def on_startup():
    try:
        ensure_bucket_exists()
    except Exception as exc:
        print(f"[MinIO Warning] {exc}")
    try:
        await cross_process_event_listener.start()
    except Exception as exc:
        print(f"[Events Warning] cross-process listener không khởi động được: {exc}")


@app.on_event("shutdown")
async def on_shutdown():
    await cross_process_event_listener.stop()

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
