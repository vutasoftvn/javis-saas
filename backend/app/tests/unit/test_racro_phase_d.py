import pytest
from unittest.mock import MagicMock
from app.business.marketing.services.racro_convert_service import RACROConvertService
from app.business.marketing.schemas.racro_contracts import MarketingSignal
from app.business.sales.models import SalesLead, Contact


def test_generate_targeted_content():
    service = RACROConvertService()
    sig = MarketingSignal(
        id="sig_content_01",
        workspace_id=1,
        source_type="search",
        title="Tăng trưởng tìm kiếm phần mềm CRM",
        summary="Nhu cầu quản trị lead tăng 50%",
        confidence=0.9,
    )
    icp = {"role": "Giám đốc Kinh doanh", "industry": "Bất động sản"}

    content = service.generate_targeted_content(
        demand_signal=sig,
        icp=icp,
        offer_type="demo",
        channel="facebook_post",
    )

    assert content["signal_id"] == "sig_content_01"
    assert "Giám đốc Kinh doanh" in content["title"]
    assert "Bất động sản" in content["title"]
    assert "DEMO" in content["content"]


def test_score_lead_qualification():
    service = RACROConvertService()

    # 1. High-tier Lead (CEO + Full Need + Budget) -> QUALIFIED (>= 70đ)
    payload_high = {
        "company": "Tập đoàn VinaTech",
        "title": "CEO",
        "message": "Chúng tôi cần triển khai hệ thống quản trị lead cho 50 nhân viên kinh doanh ngay trong tháng này.",
        "budget_signal": "50-100tr",
    }
    fit1, intent1, status1 = service.score_lead(payload_high)
    assert status1 == "QUALIFIED"
    assert (fit1 + intent1) >= 70.0

    # 2. Mid-tier Lead -> NURTURING (40-69đ)
    payload_mid = {
        "company": "Công ty ABC",
        "title": "Chuyên viên",
        "message": "Muốn tìm hiểu giải pháp",
    }
    fit2, intent2, status2 = service.score_lead(payload_mid)
    assert status2 == "NURTURING"

    # 3. Low-tier Lead -> DISQUALIFIED (< 40đ)
    payload_low = {
        "company": "",
        "title": "",
        "message": "alo",
    }
    fit3, intent3, status3 = service.score_lead(payload_low)
    assert status3 == "DISQUALIFIED"


@pytest.mark.asyncio
async def test_execute_speed_to_lead():
    service = RACROConvertService()
    mock_db = MagicMock()

    lead = SalesLead(
        id=1001,
        workspace_id=1,
        name="Nguyễn Văn A",
        company="MivaCorp",
        stage="NEW",
    )
    contact = Contact(
        id=2001,
        workspace_id=1,
        name="Nguyễn Văn A",
        email="vana@mivacorp.com",
    )
    payload = {
        "company": "MivaCorp",
        "title": "Founder",
        "message": "Cần tư vấn triển khai phần mềm cho doanh nghiệp",
    }

    result = await service.execute_speed_to_lead(
        lead=lead,
        contact=contact,
        payload=payload,
        db=mock_db,
    )

    assert result.success is True
    assert result.recipient == "vana@mivacorp.com"
    assert lead.qualification_status == "QUALIFIED"
    assert lead.fit_score == 50.0
    assert lead.next_action_type == "SALES_FOLLOWUP"
    assert mock_db.flush.called
