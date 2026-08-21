import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from db.base_class import Base
from db.session import get_db
from core.snowflake import generate_snowflake_id
from core.rate_limiter import InMemoryRateLimiter, public_rate_limiter
from platform_core.auth.models import Workspace, User, WorkspaceMember
from business.marketing.models import MarketingCampaign, MarketingExperiment
from business.marketing.form_models import FormDefinition, FormSubmission, WebEvent
from business.marketing.services.analytics_engine import AnalyticsEngine
from platform_core.core.models import WorkspaceDomain, NavigationGroup, NavigationItem
from platform_core.core.deployment_models import Deployment
from business.sales.models import Contact, SalesLead, SalesActivity
from integrations.channels.models import EmailApproval, WorkspaceSecret
from integrations.channels.email.providers.resend_provider import ResendEmailProvider, build_resend_client
from integrations.channels.plugins.deployment_providers.hostinger_provider import HostingerDeploymentProvider, build_hostinger_provider
from workforce.agents.domains.sales.action import SalesActionCapability
from workforce.agents.execution.coding_agent_provider import ClaudeCodeLandingProvider
from core.tool_registry import get_registered_tools


from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

@compiles(TSVECTOR, "sqlite")
def compile_tsvector_sqlite(type_, compiler, **kw):
    return "TEXT"

if Vector is not None:
    @compiles(Vector, "sqlite")
    def compile_vector_sqlite(type_, compiler, **kw):
        return "TEXT"

# Setup test SQLite DB
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    public_rate_limiter.reset()
    yield
    app.dependency_overrides.pop(get_db, None)


def create_test_workspace(db):
    user = User(
        id=generate_snowflake_id(),
        email="test_founder@cosa.ai",
        password_hash="hash",
        display_name="Test Founder",
    )
    workspace = Workspace(
        id=generate_snowflake_id(),
        name="COSA Growth Test",
    )
    member = WorkspaceMember(
        id=generate_snowflake_id(),
        workspace_id=workspace.id,
        user_id=user.id,
        role="admin",
    )
    db.add_all([user, workspace, member])
    db.commit()
    return workspace, user, member


# ==========================================
# Phase 0 Tests: Sales Outreach Logging to SalesActivity
# ==========================================

@pytest.mark.asyncio
async def test_sales_outreach_creates_sales_activity():
    db = TestingSessionLocal()
    ws, user, _ = create_test_workspace(db)

    lead = SalesLead(
        workspace_id=ws.id,
        name="Outreach Target",
        stage="NEW",
    )
    db.add(lead)
    db.commit()

    drafts = [
        {
            "lead_id": lead.id,
            "recipient_email": "target@client.com",
            "recipient_name": "Target Client",
            "subject": "Intro COSA",
            "message": "Hello from COSA",
        }
    ]

    with patch("workforce.agents.domains.sales.action.dispatch_outbound_action", new_callable=AsyncMock) as mock_dispatch:
        mock_dispatch.return_value = {"success": True, "status": "sent", "delivered": True}
        result = await SalesActionCapability.dispatch_outreach(
            db=db,
            workspace_id=ws.id,
            drafts=drafts,
            channel="email",
            is_approved=True,
        )

        assert result["status"] == "success"
        assert result["dispatched_count"] == 1

        # Check SalesActivity was created
        activity = (
            db.query(SalesActivity)
            .filter(SalesActivity.workspace_id == ws.id, SalesActivity.entity_id == lead.id)
            .first()
        )
        assert activity is not None
        assert activity.activity_type == "EMAIL"
        assert "target@client.com" in activity.summary
    db.close()


# ==========================================
# Phase 1 Tests: Public Form Submissions & Web Events Ingestion
# ==========================================

def test_public_form_submission_creates_lead_contact_and_utm():
    db = TestingSessionLocal()
    ws, _, _ = create_test_workspace(db)

    campaign = MarketingCampaign(
        id=generate_snowflake_id(),
        workspace_id=ws.id,
        brain_id=1,
        name="Spring Growth 2026",
    )
    experiment = MarketingExperiment(
        id=generate_snowflake_id(),
        workspace_id=ws.id,
        brain_id=1,
        campaign_id=campaign.id,
        hypothesis="Modular landing increases conversion",
        metric="cvr",
        variant_a="Hero A",
        variant_b="Hero B",
    )
    form_def = FormDefinition(
        id=generate_snowflake_id(),
        workspace_id=ws.id,
        form_key="modular-signup",
        name="Signup Form",
        campaign_id=campaign.id,
        experiment_id=experiment.id,
        is_active=True,
    )
    db.add_all([campaign, experiment, form_def])
    db.commit()

    payload = {
        "name": "Nguyen Van A",
        "email": "nguyen.a@startup.vn",
        "company": "Startup VN",
        "phone": "+84901234567",
        "message": "Interested in COSA platform",
        "utm_source": "facebook",
        "utm_medium": "cpc",
        "utm_campaign": "spring_2026",
        "utm_content": "hero_banner",
        "visitor_id": "vis_12345",
        "variant": "variant_b",
    }

    res = client.post("/api/v1/public/forms/modular-signup/submissions", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["success"] is True
    assert "submission_id" in data

    # Verify CRM Contact
    contact = db.query(Contact).filter(Contact.email == "nguyen.a@startup.vn").first()
    assert contact is not None
    assert contact.name == "Nguyen Van A"

    # Verify CRM SalesLead with UTM & Experiment link
    lead = db.query(SalesLead).filter(SalesLead.contact_id == contact.id).first()
    assert lead is not None
    assert lead.company == "Startup VN"
    assert lead.utm_source == "facebook"
    assert lead.utm_campaign == "spring_2026"
    assert lead.source_campaign_id == campaign.id
    assert lead.source_experiment_id == experiment.id

    # Verify FormSubmission record
    sub = db.query(FormSubmission).filter(FormSubmission.form_key == "modular-signup").first()
    assert sub is not None
    assert sub.status == "processed"
    assert sub.lead_id == lead.id
    assert sub.contact_id == contact.id
    db.close()


def test_public_form_rate_limiter():
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    assert limiter.is_allowed("test-ip:form1")[0] is True
    assert limiter.is_allowed("test-ip:form1")[0] is True
    assert limiter.is_allowed("test-ip:form1")[0] is False


def test_web_events_ingestion_and_cvr_evaluation():
    db = TestingSessionLocal()
    ws, _, _ = create_test_workspace(db)

    experiment = MarketingExperiment(
        id=generate_snowflake_id(),
        workspace_id=ws.id,
        brain_id=1,
        hypothesis="Landing test",
        metric="cvr",
        variant_a="Control",
        variant_b="Challenger",
    )
    db.add(experiment)
    db.commit()

    # Ingest web events batch
    batch_payload = {
        "events": [
            # Variant A: 40 views, 4 conversions (10% CVR)
            *[
                {
                    "workspace_id": ws.id,
                    "experiment_id": experiment.id,
                    "variant": "variant_a",
                    "visitor_id": f"usr_a_{i}",
                    "event_type": "page_view",
                }
                for i in range(40)
            ],
            *[
                {
                    "workspace_id": ws.id,
                    "experiment_id": experiment.id,
                    "variant": "variant_a",
                    "visitor_id": f"usr_a_{i}",
                    "event_type": "form_submitted",
                }
                for i in range(4)
            ],
            # Variant B: 40 views, 12 conversions (30% CVR)
            *[
                {
                    "workspace_id": ws.id,
                    "experiment_id": experiment.id,
                    "variant": "variant_b",
                    "visitor_id": f"usr_b_{i}",
                    "event_type": "page_view",
                }
                for i in range(40)
            ],
            *[
                {
                    "workspace_id": ws.id,
                    "experiment_id": experiment.id,
                    "variant": "variant_b",
                    "visitor_id": f"usr_b_{i}",
                    "event_type": "form_submitted",
                }
                for i in range(12)
            ],
        ]
    }

    res = client.post("/api/v1/public/events", json=batch_payload)
    assert res.status_code == 202
    assert res.json()["ingested_count"] == 96

    # Test AnalyticsEngine evaluation directly from events
    eval_result = AnalyticsEngine.evaluate_experiment_from_events(
        db=db,
        workspace_id=ws.id,
        experiment_id=experiment.id,
        conversion_event_type="form_submitted",
    )
    assert eval_result["variant_a_views"] == 40
    assert eval_result["variant_a_conversions"] == 4
    assert eval_result["variant_b_views"] == 40
    assert eval_result["variant_b_conversions"] == 12
    assert eval_result["baseline_cvr"] == 10.0
    assert eval_result["variant_cvr"] == 30.0
    assert eval_result["decision"] in ["WIN", "INCONCLUSIVE", "LOSE"]
    assert eval_result["uplift_pct"] == 200.0
    db.close()


# ==========================================
# Phase 2 Tests: Site/Domain Registry & Navigation Manifest
# ==========================================

def test_public_navigation_manifest_endpoint():
    db = TestingSessionLocal()
    ws, _, _ = create_test_workspace(db)

    domain = WorkspaceDomain(
        id=generate_snowflake_id(),
        workspace_id=ws.id,
        domain="cosa.vn",
        subdomain="landing",
        site_type="landing",
        environment="production",
        status="active",
    )
    nav_group = NavigationGroup(
        id=generate_snowflake_id(),
        workspace_id=ws.id,
        site_key="cosa.vn",
        name="Main Header Menu",
        is_active=True,
    )
    item1 = NavigationItem(
        id=generate_snowflake_id(),
        group_id=nav_group.id,
        title="Features",
        path="/#features",
        sort_order=1,
        is_visible=True,
    )
    item2 = NavigationItem(
        id=generate_snowflake_id(),
        group_id=nav_group.id,
        title="Pricing",
        path="/#pricing",
        sort_order=2,
        is_visible=True,
    )
    db.add_all([domain, nav_group, item1, item2])
    db.commit()

    res = client.get("/api/v1/public/sites/cosa.vn/navigation")
    assert res.status_code == 200
    assert "public, max-age=60" in res.headers.get("cache-control", "")
    data = res.json()
    assert data["site_key"] == "cosa.vn"
    assert data["group_name"] == "Main Header Menu"
    assert len(data["items"]) == 2
    assert data["items"][0]["title"] == "Features"
    assert data["items"][1]["title"] == "Pricing"
    db.close()


# ==========================================
# Phase 3 Tests: EmailProvider + Resend Adapter & Webhook
# ==========================================

@pytest.mark.asyncio
async def test_resend_email_provider_dispatch():
    provider = ResendEmailProvider(api_key="re_test_123456789")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "resend_msg_999"}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        result = await provider.send_email(
            to_email="customer@domain.com",
            subject="Welcome to COSA",
            body_html="<h1>Welcome</h1>",
        )
        assert result["success"] is True
        assert result["id"] == "resend_msg_999"


def test_resend_webhook_records_sales_activity():
    db = TestingSessionLocal()
    ws, _, _ = create_test_workspace(db)

    contact = Contact(
        id=generate_snowflake_id(),
        workspace_id=ws.id,
        name="Lead Contact",
        email="lead.client@cosa.ai",
    )
    db.add(contact)
    db.commit()

    webhook_payload = {
        "type": "email.delivered",
        "data": {
            "id": "email_evt_101",
            "to": ["lead.client@cosa.ai"],
            "subject": "Proposal Discussion",
        },
    }

    res = client.post("/api/v1/integrations/webhooks/resend", json=webhook_payload)
    assert res.status_code == 200
    assert res.json()["received"] is True

    # Check that SalesActivity was logged
    activity = (
        db.query(SalesActivity)
        .filter(SalesActivity.workspace_id == ws.id, SalesActivity.entity_id == contact.id)
        .first()
    )
    assert activity is not None
    assert activity.activity_type == "EMAIL"
    assert activity.outcome == "DELIVERED"
    db.close()


# ==========================================
# Phase 4 Tests: Coding Agent Landing Generator Tool
# ==========================================

def test_generate_landing_project_tool_registration():
    db = TestingSessionLocal()
    ws, user, _ = create_test_workspace(db)

    tool_def = get_registered_tools().get("execution.generate_landing_project")
    assert tool_def is not None
    assert tool_def.risk_level == "high"

    spec = {
        "project_name": "cosa-finance-landing",
        "form_key": "finance-early-access",
        "site_key": "finance.cosa.ai",
        "hypothesis": "SMBs need real-time cash flow intelligence",
        "offer": {"plan": "Starter", "price": "499k/mo"},
    }

    provider = ClaudeCodeLandingProvider()
    job = provider.generate_landing_project_job(
        db=db,
        workspace_id=ws.id,
        user_id=user.id,
        landing_spec=spec,
    )
    assert job is not None
    assert job.metadata_jsonb["task_type"] == "generate_landing_project"
    assert job.metadata_jsonb["project_name"] == "cosa-finance-landing"
    assert "spec.md" in job.metadata_jsonb["input_files"]
    db.close()


# ==========================================
# Phase 5 Tests: DeploymentProvider & Hostinger Adapter
# ==========================================

@pytest.mark.asyncio
async def test_hostinger_deployment_provider():
    provider = HostingerDeploymentProvider(api_token="hostinger_token_123")

    mock_deploy_res = MagicMock()
    mock_deploy_res.status_code = 200
    mock_deploy_res.content = b'{"status":"deployed","project":"cosa-landing"}'
    mock_deploy_res.json.return_value = {"status": "deployed", "project": "cosa-landing"}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_deploy_res):
        res = await provider.deploy_compose_project(
            vps_id="vps_hostinger_01",
            project_name="cosa-landing",
            compose_content="version: '3.8'\nservices:\n  web:\n    image: cosa-landing:latest",
        )
        assert res["status"] == "deployed"


def test_deployment_model_lifecycle():
    db = TestingSessionLocal()
    ws, _, _ = create_test_workspace(db)

    deployment = Deployment(
        id=generate_snowflake_id(),
        workspace_id=ws.id,
        provider="hostinger",
        vps_id="vps_001",
        project_name="landing-page-v1",
        compose_yaml="version: '3.8'",
        status="running",
        url="https://landing.cosa.vn",
        metadata_jsonb={"docker_network": "bridge"},
    )
    db.add(deployment)
    db.commit()

    saved = db.query(Deployment).filter(Deployment.id == deployment.id).first()
    assert saved is not None
    assert saved.status == "running"
    assert saved.provider == "hostinger"
    assert saved.url == "https://landing.cosa.vn"
    db.close()
