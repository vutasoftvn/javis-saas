import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from business.packs.loader import BusinessPackLoader
from business.packs.resolver import BusinessPackResolver
from business.packs.legal_resolver import LegalKnowledgeResolver
from business.packs.service import BusinessPackService
from business.packs.models import BusinessAssetOverrideModel, LegalAnnotationRecord
from business.packs.schemas import TemplateBundle, CapabilityDefinition, SOPDefinition


def test_business_pack_loader_discovers_all_packs():
    loader = BusinessPackLoader()
    pack_ids = loader.list_factory_pack_ids()

    assert "governance" in pack_ids
    assert "operations" in pack_ids
    assert "sales" in pack_ids
    assert "reporting" in pack_ids
    assert "finance" in pack_ids
    assert "marketing" in pack_ids
    assert "customer" in pack_ids
    assert "product-tech" in pack_ids
    assert "people" in pack_ids
    assert "training" in pack_ids
    assert "growth" in pack_ids
    assert len(pack_ids) == 11


def test_finance_and_marketing_pack_contents():
    loader = BusinessPackLoader()
    # Finance
    fin_caps = loader.list_capabilities("finance")
    fin_cap_ids = [c.id for c in fin_caps]
    assert "finance.cashflow_forecast" in fin_cap_ids
    assert "finance.break_even_analysis" in fin_cap_ids
    fin_tpl = loader.get_template_bundle("finance", "cashflow-forecast")
    assert fin_tpl is not None
    assert "{{opening_cash}}" in fin_tpl.body_markdown

    # Marketing
    mkt_caps = loader.list_capabilities("marketing")
    mkt_cap_ids = [c.id for c in mkt_caps]
    assert "marketing.content_strategy" in mkt_cap_ids
    assert "marketing.paid_ads_sop" in mkt_cap_ids
    mkt_tpl = loader.get_template_bundle("marketing", "campaign-brief")
    assert mkt_tpl is not None


def test_customer_and_product_tech_pack_contents():
    loader = BusinessPackLoader()
    # Customer
    cust_caps = loader.list_capabilities("customer")
    cust_cap_ids = [c.id for c in cust_caps]
    assert "customer.complaint_handling" in cust_cap_ids
    cust_sop = loader.get_sop("customer", "complaint-handling-sop")
    assert cust_sop is not None

    # Product Tech
    tech_caps = loader.list_capabilities("product-tech")
    tech_cap_ids = [c.id for c in tech_caps]
    assert "product_tech.product_roadmap" in tech_cap_ids
    assert "product_tech.it_security_policy" in tech_cap_ids
    tech_tpl = loader.get_template_bundle("product-tech", "product-brief")
    assert tech_tpl is not None


def test_optional_packs_people_training_growth():
    loader = BusinessPackLoader()
    # People
    assert "people.job_description" in [c.id for c in loader.list_capabilities("people")]
    # Training
    assert "training.training_plan" in [c.id for c in loader.list_capabilities("training")]
    # Growth
    assert "growth.cap_table" in [c.id for c in loader.list_capabilities("growth")]
    growth_tpl = loader.get_template_bundle("growth", "pitch-deck")
    assert growth_tpl is not None


def test_governance_pack_contents():
    loader = BusinessPackLoader()
    manifest = loader.load_pack_manifest("governance")
    assert manifest is not None
    assert manifest.id == "governance"
    assert manifest.version == "1.0.0"

    caps = loader.list_capabilities("governance")
    cap_ids = [c.id for c in caps]
    assert "governance.create_nda" in cap_ids
    assert "governance.compliance_checklist" in cap_ids
    assert "governance.company_profile" in cap_ids
    assert "governance.raci_matrix" in cap_ids

    # Template
    nda_tpl = loader.get_template_bundle("governance", "nda-vn")
    assert nda_tpl is not None
    assert nda_tpl.metadata.id == "nda-vn"
    assert "{{party_a}}" in nda_tpl.body_markdown

    # SOP
    sop = loader.get_sop("governance", "create-legal-document")
    assert sop is not None
    assert sop.id == "governance.create_legal_document"

    # Legal source
    legal_sources = loader.list_legal_sources("governance")
    assert len(legal_sources) >= 1
    assert legal_sources[0].id == "vn-law-doanh-nghiep-2020"
    assert legal_sources[0].status == "current"


def test_operations_pack_contents():
    loader = BusinessPackLoader()
    caps = loader.list_capabilities("operations")
    cap_ids = [c.id for c in caps]
    assert "operations.create_sop" in cap_ids
    assert "operations.incident_handling" in cap_ids

    tpl = loader.get_template_bundle("operations", "sop-standard")
    assert tpl is not None
    assert "{{sop_title}}" in tpl.body_markdown


def test_sales_pack_contents():
    loader = BusinessPackLoader()
    caps = loader.list_capabilities("sales")
    cap_ids = [c.id for c in caps]
    assert "sales.sales_process_design" in cap_ids
    assert "sales.quotation_drafting" in cap_ids

    sop = loader.get_sop("sales", "sales-standard-process")
    assert sop is not None
    assert "qualify" in sop.stages


def test_reporting_pack_contents():
    loader = BusinessPackLoader()
    caps = loader.list_capabilities("reporting")
    cap_ids = [c.id for c in caps]
    assert "reporting.generate_weekly_report" in cap_ids

    tpl = loader.get_template_bundle("reporting", "weekly-report")
    assert tpl is not None
    assert "{{kpi_table}}" in tpl.body_markdown


@pytest.mark.asyncio
async def test_resolver_company_override_priority():
    loader = BusinessPackLoader()
    resolver = BusinessPackResolver(loader)

    mock_db = AsyncMock()

    # Case 1: No override -> returns factory default
    mock_result_none = MagicMock()
    mock_result_none.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result_none

    bundle = await resolver.resolve_template(mock_db, workspace_id=1, pack_id="governance", template_id="nda-vn")
    assert bundle is not None
    assert bundle.is_override is False
    assert "# THỎA THUẬN BẢO MẬT THÔNG TIN (NDA)" in bundle.body_markdown

    # Case 2: Company Override exists -> returns overridden content
    mock_override = BusinessAssetOverrideModel(
        workspace_id=1,
        asset_id="governance.templates.nda-vn",
        asset_type="template",
        pack_id="governance",
        version="2.0.0",
        content_override_jsonb={"metadata": {"name": "NDA Công ty ABC Tùy chỉnh"}},
        body_override_markdown="# THỎA THUẬN BẢO MẬT RIÊNG CỦA CÔNG TY ABC",
        is_active=True,
    )
    mock_result_override = MagicMock()
    mock_result_override.scalars.return_value.first.return_value = mock_override
    mock_db.execute.return_value = mock_result_override

    overridden_bundle = await resolver.resolve_template(mock_db, workspace_id=1, pack_id="governance", template_id="nda-vn")
    assert overridden_bundle is not None
    assert overridden_bundle.is_override is True
    assert overridden_bundle.override_version == "2.0.0"
    assert overridden_bundle.metadata.name == "NDA Công ty ABC Tùy chỉnh"
    assert "THỎA THUẬN BẢO MẬT RIÊNG CỦA CÔNG TY ABC" in overridden_bundle.body_markdown


@pytest.mark.asyncio
async def test_legal_knowledge_resolver_and_annotations():
    loader = BusinessPackLoader()
    legal_resolver = LegalKnowledgeResolver(loader)

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result

    sources = await legal_resolver.resolve_legal_sources_for_capability(
        db=mock_db,
        workspace_id=100,
        pack_id="governance",
        jurisdiction="VN",
    )

    assert len(sources) >= 1
    assert sources[0]["source_id"] == "vn-law-doanh-nghiep-2020"
    assert sources[0]["status"] == "current"
    assert sources[0]["is_unverified"] is False
    assert sources[0]["company_applicability"] == "applicable"


@pytest.mark.asyncio
async def test_business_pack_service_list_and_details():
    service = BusinessPackService()
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    packs = await service.list_available_packs(mock_db, workspace_id=1)
    assert len(packs) == 11
    pack_map = {p["id"]: p for p in packs}
    assert pack_map["governance"]["capabilities_count"] >= 4
    assert pack_map["operations"]["capabilities_count"] >= 4
    assert pack_map["sales"]["capabilities_count"] >= 3
    assert pack_map["reporting"]["capabilities_count"] >= 3
    assert pack_map["finance"]["capabilities_count"] >= 4
    assert pack_map["marketing"]["capabilities_count"] >= 5
    assert pack_map["customer"]["capabilities_count"] >= 4
    assert pack_map["product-tech"]["capabilities_count"] >= 4

    details = await service.get_pack_details(mock_db, workspace_id=1, pack_id="governance")
    assert details is not None
    assert len(details["capabilities"]) >= 4
    assert len(details["templates"]) >= 2
    assert len(details["sops"]) >= 2
    assert len(details["legal_sources"]) >= 1


@pytest.mark.asyncio
async def test_update_engine_check_and_conflict_detection():
    from business.packs.update_engine import PackUpdateEngine
    engine = PackUpdateEngine()

    mock_db = AsyncMock()
    # Mock existing override for nda-vn template
    mock_override = BusinessAssetOverrideModel(
        workspace_id=1,
        asset_id="governance.templates.nda-vn",
        asset_type="template",
        pack_id="governance",
        version="1.0.0",
        is_active=True,
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_override]
    mock_db.execute.return_value = mock_result

    # Incoming update manifest
    update_manifest = {
        "package": "governance",
        "version": "1.2.0",
        "release_notes": "Cập nhật điều khoản bảo mật dữ liệu.",
        "breaking": False,
        "files": [
            {
                "path": "templates/nda-vn/template.yaml",
                "change": "modified"
            }
        ]
    }

    check_res = await engine.check_for_updates(
        db=mock_db,
        workspace_id=1,
        pack_id="governance",
        update_manifest=update_manifest,
    )

    assert check_res["update_available"] is True
    assert check_res["latest_version"] == "1.2.0"
    assert check_res["conflicts_count"] == 1
    assert check_res["conflicts"][0]["asset_id"] == "governance.templates.nda-vn"
    assert check_res["conflicts"][0]["requires_admin_review"] is True


@pytest.mark.asyncio
async def test_update_engine_diff_and_resolutions():
    from business.packs.update_engine import PackUpdateEngine
    engine = PackUpdateEngine()

    # 1. Test Diff Generator
    diff = engine.generate_diff("Version A\nLine 1", "Version B\nLine 1")
    assert "-Version A" in diff
    assert "+Version B" in diff

    mock_db = AsyncMock()
    mock_override = BusinessAssetOverrideModel(
        workspace_id=1,
        asset_id="governance.templates.nda-vn",
        asset_type="template",
        pack_id="governance",
        version="1.0.0",
        is_active=True,
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_override
    mock_db.execute.return_value = mock_result

    # 2. Test KEEP_COMPANY
    keep_res = await engine.apply_resolution(
        db=mock_db,
        workspace_id=1,
        asset_id="governance.templates.nda-vn",
        resolution="KEEP_COMPANY"
    )
    assert keep_res["status"] == "success"
    assert keep_res["resolution"] == "KEEP_COMPANY"

    # 3. Test ACCEPT_FACTORY / RESET_FACTORY
    reset_res = await engine.apply_resolution(
        db=mock_db,
        workspace_id=1,
        asset_id="governance.templates.nda-vn",
        resolution="RESET_FACTORY"
    )
    assert reset_res["status"] == "success"
    assert reset_res["resolution"] == "RESET_FACTORY"
    mock_db.delete.assert_called_once_with(mock_override)

    # 4. Test MERGE
    merge_res = await engine.apply_resolution(
        db=mock_db,
        workspace_id=1,
        asset_id="governance.templates.nda-vn",
        resolution="MERGE",
        merged_body="# MERGED CONTENT",
        user_id=99
    )
    assert merge_res["status"] == "success"
    assert merge_res["resolution"] == "MERGE"
    assert mock_override.body_override_markdown == "# MERGED CONTENT"


def test_marketing_pack_marketingskills_suite():
    loader = BusinessPackLoader()

    # 1. Manifest
    manifest = loader.load_pack_manifest("marketing")
    assert manifest is not None
    assert "coreyhaines31/marketingskills" in manifest.source.references

    # 2. Skills
    skills = loader.list_skills("marketing")
    skill_ids = [s.id for s in skills]
    assert "product-marketing" in skill_ids
    assert "page-cro" in skill_ids
    assert "ai-seo" in skill_ids
    assert "copywriting" in skill_ids
    assert "emails" in skill_ids
    assert "pricing-pages" in skill_ids

    pm_skill = loader.get_skill("marketing", "product-marketing")
    assert pm_skill is not None
    assert "Single Source of Truth" in pm_skill.body_markdown

    # 3. Capabilities
    caps = loader.list_capabilities("marketing")
    cap_ids = [c.id for c in caps]
    assert "marketing.product_marketing_foundation" in cap_ids
    assert "marketing.landing_page_cro_audit" in cap_ids
    assert "marketing.ai_seo_geo_strategy" in cap_ids
    assert "marketing.copywriting_generator" in cap_ids
    assert "marketing.email_lifecycle_drip" in cap_ids
    assert "marketing.pricing_page_optimization" in cap_ids

    # 4. SOPs
    cro_sop = loader.get_sop("marketing", "landing-page-cro-audit-sop")
    assert cro_sop is not None
    step_ids = [s.get("id") if isinstance(s, dict) else getattr(s, "id", None) for s in cro_sop.steps]
    assert "analyze_above_the_fold" in step_ids

    # 5. Templates
    dna_tpl = loader.get_template_bundle("marketing", "product-marketing-dna")
    assert dna_tpl is not None
    assert "{{unique_value_proposition}}" in dna_tpl.body_markdown

    pricing_tpl = loader.get_template_bundle("marketing", "saas-pricing-matrix")
    assert pricing_tpl is not None
    assert "{{starter_tier_details}}" in pricing_tpl.body_markdown



