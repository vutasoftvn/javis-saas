import os
from contextlib import asynccontextmanager
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


from app.modules.integrations import router as connectors

from app.modules.integrations import connectors_zalo_router as connectors_zalo
from app.modules.integrations import google_router as connectors_google
from app.modules.integrations import email_approval_router as email_approvals
from app.modules.integrations import channels_router as channels
from app.modules.integrations import plugins_router as plugins
from app.modules.integrations import outbox_router
from app.modules.integrations import public_channel_router
from app.modules.platform import router as admin
from app.modules.platform import feature_flags_router
from app.modules.platform import prompts_router
from app.modules.platform import domain_router as domain
from app.modules.platform import events_router
from app.modules.platform import founder_hub_router
from app.modules.platform import missions_router
from app.modules.marketing import router as marketing
from app.modules.marketing.public_router import router as public_router
from app.modules.integrations.email_webhook_router import router as email_webhooks_router
from app.modules.outcomes.router import router as outcomes_router
from app.modules.devices.router import router as devices_router
from app.modules.organization.router import router as organization_router
from app.modules.realtime import router as realtime
from app.modules.agent_memory import router as agent_memory
from app.modules.learning import router as learning
from app.modules.skills import router as skills_router
from app.modules.tech_radar import router as tech_radar_router
from app.modules.legal import router as legal
from app.modules.sales import router as sales
from app.modules.sales import revenue_router
from app.modules.sales import public_lead_router
from app.modules.tech import router as tech
from app.modules.finance import router as finance
from app.modules.finance import tt58_router
from app.modules.policy_funding.routers import project_funding_router
from app.modules.policy_funding.routers import policy_catalog_router
from app.modules.policy_funding.routers import admin_policy_router
from app.modules.policy_funding.routers import application_router
from app.modules.ai_team import router as ai_team
from app.modules.company_runtime.router import router as company_runtime
from app.agents.gateway import agents_gateway_router
from app.agents.execution.manager import execution_provider_manager
from app.modules.reports.router import router as reports_router
from app.agents.ai_programs_router import router as ai_programs_router
from app.agents.runtime.manager import agent_runtime_manager

from app.automations.router import router as automations_router
from app.automations.runtime.manager import automation_runtime_manager

from app.core.events import cross_process_event_listener
from app.core.cors import configured_allowed_origins
from app.core.migration_health import get_migration_health
from app.core.worker_health import get_worker_health
from app.db.session import engine
from app.integrations.s3_client import get_s3_client, ensure_bucket_exists

@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        from app.core.telemetry import configure_telemetry
        configure_telemetry()
    except Exception as exc:
        print(f"[Telemetry Warning] OpenTelemetry không khởi động được: {exc}")
    try:
        ensure_bucket_exists()
    except Exception as exc:
        print(f"[MinIO Warning] {exc}")
    try:
        await cross_process_event_listener.start()
    except Exception as exc:
        print(f"[Events Warning] cross-process listener không khởi động được: {exc}")
    try:
        await agent_runtime_manager.start()
    except Exception as exc:
        print(f"[AgentRuntime Warning] agent runtime manager không khởi động được: {exc}")
    try:
        await execution_provider_manager.start()
    except Exception as exc:
        print(f"[ExecutionProvider Warning] execution provider manager không khởi động được: {exc}")
    try:
        await automation_runtime_manager.start()
    except Exception as exc:
        print(f"[AutomationRuntime Warning] automation runtime manager không khởi động được: {exc}")

    yield

    await automation_runtime_manager.stop()
    await execution_provider_manager.stop()
    await agent_runtime_manager.stop()
    await cross_process_event_listener.stop()


app = FastAPI(title="COSA Brain API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_allowed_origins(),
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(agents_gateway_router)
app.include_router(ai_programs_router, prefix="/api/v1/internal/ai", tags=["ai-programs"])
app.include_router(reports_router, tags=["reports"])
app.include_router(automations_router, prefix="/api/v1/automations", tags=["automations"])
app.include_router(vault.router, prefix="/api/v1/vault", tags=["vault"])
app.include_router(knowledge_router.router, prefix="/api/v1/vault", tags=["vault-knowledge"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(strategy.router, prefix="/api/v1/strategy", tags=["strategy"])
app.include_router(portfolios.router, prefix="/api/v1/strategy", tags=["portfolios"])
app.include_router(next_actions.router, prefix="/api/v1/strategy", tags=["next-actions"])


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
app.include_router(legal.router, prefix="/api/v1/legal", tags=["legal"])
app.include_router(sales.router, prefix="/api/v1/sales", tags=["sales"])
app.include_router(tech.router, prefix="/api/v1/tech", tags=["tech"])
app.include_router(finance.router, prefix="/api/v1/finance", tags=["finance"])
app.include_router(project_funding_router.router, prefix="/api/v1", tags=["policy-funding-projects"])
app.include_router(policy_catalog_router.router, prefix="/api/v1", tags=["policy-programs"])
app.include_router(admin_policy_router.router, prefix="/api/v1", tags=["admin-policy"])
app.include_router(application_router.router, prefix="/api/v1", tags=["policy-applications"])
app.include_router(ai_team.router, prefix="/api/v1/functions", tags=["ai-team"])
app.include_router(company_runtime, prefix="/api/v1/company-runtime", tags=["company-runtime"])
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
app.include_router(founder_hub_router.router, prefix="/api/v1", tags=["founder-hub"])
app.include_router(missions_router.router, prefix="/api/v1", tags=["missions"])
app.include_router(revenue_router.router, prefix="/api/v1", tags=["revenue-engine"])
app.include_router(public_lead_router.router, prefix="/api/v1", tags=["public-leads"])
app.include_router(outbox_router.router, prefix="/api/v1", tags=["outbox-gateway"])
app.include_router(public_channel_router.router, prefix="/api/v1", tags=["public-channels"])
app.include_router(tt58_router.router, prefix="/api/v1", tags=["finance-tt58"])
app.include_router(skills_router.router)
app.include_router(tech_radar_router.router)
app.include_router(feature_flags_router.router, prefix="/api/v1/platform", tags=["platform"])
app.include_router(prompts_router.router, prefix="/api/v1/platform/prompts", tags=["platform-prompts"])
app.include_router(domain.router, prefix="/api/v1/domain", tags=["domain"])
app.include_router(public_router, prefix="/api/v1")
app.include_router(email_webhooks_router, prefix="/api/v1")

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
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
