"""Unit tests for Public Intake Gateway, Marketing App Generator, and Zero Lock-in Export (Phase 4)."""
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"

from business.marketing.form_models import FormDefinition, FormSubmission
from business.sales.models import SalesLead, Contact
from platform_core.sync.models import PlatformInbox
from business.marketing.public_intake_service import PublicIntakeService
from business.marketing.app_generator_service import (
    AppGeneratorService,
    RouteModuleConfig,
)
from platform_core.sync.entitlement_crypto import EntitlementSigner
from platform_core.sync.entitlement_manager import EntitlementManager
from platform_core.sync.schemas import EntitlementFeatures, EntitlementLimits


@pytest.fixture
def db_session():
    """In-memory SQLite database session for unit testing."""
    engine = create_engine("sqlite:///:memory:")
    engine = engine.execution_options(schema_translate_map={"agent_runtime": None, "integrations": None, "finance": None, "sales": None, "marketing": None, "legal": None, "validation": None, "strategy": None, "operating": None, "knowledge": None, "policy_funding": None, "core": None, "runtime_ops": None})
    Contact.__table__.create(bind=engine, checkfirst=True)
    FormDefinition.__table__.create(bind=engine, checkfirst=True)
    FormSubmission.__table__.create(bind=engine, checkfirst=True)
    SalesLead.__table__.create(bind=engine, checkfirst=True)
    PlatformInbox.__table__.create(bind=engine, checkfirst=True)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_public_intake_ip_hashing():
    """Verify privacy-preserving IP hashing."""
    ip1 = "192.168.1.100"
    ip2 = "192.168.1.101"

    hash1 = PublicIntakeService.hash_ip(ip1)
    hash1_repeat = PublicIntakeService.hash_ip(ip1)
    hash2 = PublicIntakeService.hash_ip(ip2)

    assert hash1 == hash1_repeat
    assert hash1 != hash2
    assert PublicIntakeService.hash_ip(None) is None


def test_public_intake_submission_and_lead_creation(db_session):
    """Verify public form submission creates FormSubmission, SalesLead, and queues into PlatformInbox."""
    company_id = str(uuid.uuid4())
    payload = {
        "name": "Tran Van B",
        "email": "b.tran@techcorp.vn",
        "phone": "0912345678",
        "company": "TechCorp",
        "message": "Interested in enterprise AI agent deployment",
        "utm_source": "google_ads",
        "utm_campaign": "q3_startup_boost",
    }

    submission, inbox_entry = PublicIntakeService.ingest_submission(
        db=db_session,
        company_id=company_id,
        form_slug="enterprise-contact",
        payload=payload,
        client_ip="115.79.20.15",
        source_domain="techcorp.cosa.vn",
    )

    # 1. Verify FormSubmission
    assert submission.form_key == "enterprise-contact"
    assert submission.payload_jsonb["name"] == "Tran Van B"
    assert submission.payload_jsonb["email"] == "b.tran@techcorp.vn"
    assert submission.utm_source == "google_ads"

    # 2. Verify auto-generated Contact and SalesLead in CRM
    contact = db_session.query(Contact).filter(Contact.email == "b.tran@techcorp.vn").first()
    assert contact is not None
    assert contact.name == "Tran Van B"
    assert contact.phone == "0912345678"

    lead = db_session.query(SalesLead).filter(SalesLead.contact_id == contact.id).first()
    assert lead is not None
    assert lead.name == "Tran Van B"
    assert lead.company == "TechCorp"
    assert lead.source == "google_ads"

    # 3. Verify PlatformInbox event
    assert inbox_entry.event_type == "form.submission_received"
    assert inbox_entry.company_id == company_id
    assert inbox_entry.payload["email"] == "b.tran@techcorp.vn"
    assert inbox_entry.payload["ip_hash"] is not None


def test_app_generator_manifest_and_entitlement(monkeypatch):
    """Verify marketing app manifest generation and custom domain entitlement logic."""
    monkeypatch.setenv("COSA_PLATFORM_SIGNING_SECRET", "test-only-hmac-secret-not-a-production-default")
    company_id = str(uuid.uuid4())

    # Case 1: Free tier requesting custom domain -> Fallback to cosa subdomain
    free_manifest = AppGeneratorService.generate_app_manifest(
        company_id=company_id,
        name="Startup X",
        slug="startup-x",
        custom_domain="www.startup-x.vn",
    )
    assert free_manifest.default_subdomain == "startup-x.cosa.vn"
    assert free_manifest.custom_domain is None # stripped due to lack of entitlement

    # Case 2: Upgrade company to Pro with custom_domain = True
    pro_snapshot = EntitlementSigner.sign_snapshot(
        company_id=company_id,
        plan="pro",
        limits=EntitlementLimits(max_projects=10),
        features=EntitlementFeatures(custom_domain=True),
        signing_secret="test-only-hmac-secret-not-a-production-default",
    )
    EntitlementManager.save_snapshot(pro_snapshot)

    pro_manifest = AppGeneratorService.generate_app_manifest(
        company_id=company_id,
        name="Startup X",
        slug="startup-x",
        custom_domain="www.startup-x.vn",
    )
    assert pro_manifest.custom_domain == "www.startup-x.vn"
    assert len(pro_manifest.routes) == 2
    assert pro_manifest.routes[0].path == "/"
    assert pro_manifest.routes[1].path == "/survey"


def test_app_generator_export_package():
    """Verify zero lock-in export package structure."""
    manifest = AppGeneratorService.generate_app_manifest(
        company_id=str(uuid.uuid4()),
        name="AI Co",
        slug="ai-co",
    )

    package = AppGeneratorService.get_export_package_structure(manifest)
    assert "cosa.manifest.yaml" in package["files"]
    assert "package.json" in package["files"]
    assert "src/app/page.tsx" in package["files"]
    assert "src/components/sections/HeroSection.tsx" in package["files"]
    assert package["manifest_yaml"] is not None
