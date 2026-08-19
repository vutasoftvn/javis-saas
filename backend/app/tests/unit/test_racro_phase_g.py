import pytest
from app.business.marketing.services.racro_governance_service import (
    RACROGovernanceService,
    MarketingUsageAggregateSync,
)


def test_sanitize_and_build_aggregate_payload():
    payload = RACROGovernanceService.sanitize_and_build_aggregate_payload(
        company_id="comp_123",
        project_id="proj_456",
        research_runs=10,
        campaigns_created=4,
        leads_count=50,
        qualified_leads_count=15,
        customers_count=6,
        capability_usage={"market_intelligence": 10, "speed_to_lead": 50},
        project_stage="Validation",
    )

    assert isinstance(payload, MarketingUsageAggregateSync)
    assert payload.company_id == "comp_123"
    assert payload.leads_count == 50
    assert payload.qualified_leads_count == 15
    assert payload.project_stage == "Validation"


def test_pii_sanitization_guard_blocks_pii():
    """Kiểm tra Guard chặn đứng các trường PII gửi lên Control Plane."""
    with pytest.raises(ValueError, match="Vi phạm ranh giới dữ liệu"):
        RACROGovernanceService.sanitize_and_build_aggregate_payload(
            company_id="comp_123",
            project_id="proj_456",
            research_runs=1,
            campaigns_created=1,
            leads_count=1,
            qualified_leads_count=1,
            customers_count=1,
            capability_usage={},
            project_stage="Validation",
            extra_data={"email": "customer@example.com"},  # PII bị cấm
        )


def test_company_override_precedence():
    """Kiểm tra quy tắc: Company Override > Factory Default."""
    factory = "Bạn là trợ lý marketing chuyên nghiệp của COSA."
    company = "Bạn là chuyên gia tư vấn bất động sản cao cấp của VinLand."

    # Khi có company override -> lấy company
    effective1 = RACROGovernanceService.resolve_effective_prompt(
        factory_prompt=factory,
        company_override=company,
    )
    assert effective1 == company

    # Khi không có company override -> lấy factory
    effective2 = RACROGovernanceService.resolve_effective_prompt(
        factory_prompt=factory,
        company_override="",
    )
    assert effective2 == factory


def test_admin_permission_enforcement():
    """Kiểm tra bảo vệ System Prompts và Specs chỉ dành cho Admin."""
    # Admin được phép
    assert RACROGovernanceService.check_permission("admin", "edit_core_prompt") is True
    assert RACROGovernanceService.check_permission("owner", "reset_factory_pack") is True

    # Member / Viewer bị từ chối
    assert RACROGovernanceService.check_permission("member", "edit_core_prompt") is False
    assert RACROGovernanceService.check_permission("viewer", "reset_factory_pack") is False
    assert RACROGovernanceService.check_permission("user", "modify_security_connectors") is False
