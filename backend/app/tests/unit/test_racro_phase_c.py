import pytest
from unittest.mock import MagicMock
from app.business.marketing.services.racro_research_service import RACROResearchService
from app.business.marketing.schemas.racro_contracts import MarketingSignal
from app.founder_os.strategy.models import EvidenceItem


@pytest.mark.asyncio
async def test_analyze_market_intelligence():
    service = RACROResearchService()
    signals = await service.analyze_market_intelligence(
        workspace_id=1,
        topic="SaaS B2B AI Co-Founder",
        industry="Technology",
    )
    assert len(signals) > 0
    sig = signals[0]
    assert sig.workspace_id == 1
    assert "SaaS B2B AI Co-Founder" in sig.title
    assert sig.source_type == "market_report"
    assert sig.confidence > 0.0
    assert sig.related_segment == "Technology"


@pytest.mark.asyncio
async def test_analyze_competitor_intelligence():
    service = RACROResearchService()
    signals = await service.analyze_competitor_intelligence(
        workspace_id=1,
        competitor_name="CompetitorX",
        competitor_url="https://competitorx.com",
    )
    assert len(signals) > 0
    sig = signals[0]
    assert sig.workspace_id == 1
    assert "CompetitorX" in sig.title
    assert sig.source_type == "competitor"
    assert sig.confidence == 0.85
    assert sig.source_url == "https://competitorx.com"


@pytest.mark.asyncio
async def test_detect_demand_signals():
    service = RACROResearchService()
    signals = await service.detect_demand_signals(
        workspace_id=1,
        keywords=["phần mềm quản trị doanh nghiệp", "crm tự động hóa"],
    )
    assert len(signals) == 2
    for sig in signals:
        assert sig.source_type == "search"
        assert sig.confidence == 0.9
        assert sig.related_segment == "In-market Buyers"


def test_promote_signal_to_evidence_bridge():
    """Kiểm tra cầu nối chuyển đổi MarketingSignal sang EvidenceItem khi Founder duyệt."""
    service = RACROResearchService()
    
    mock_signal = MarketingSignal(
        id="sig_test_999",
        workspace_id=10,
        project_id=100,
        source_type="market_report",
        source_url="https://report.example.com",
        title="Báo cáo nhu cầu thị trường Q3",
        summary="Thị trường tăng trưởng 30% hàng năm",
        confidence=0.88,
        related_segment="SME",
        related_hypothesis="Khách hàng SME sẵn sàng chi trả cho tự động hóa",
    )

    mock_db = MagicMock()

    evidence = service.promote_signal_to_evidence(
        signal=mock_signal,
        user_id=1,
        db=mock_db,
    )

    assert mock_db.add.called
    assert mock_db.flush.called
    assert isinstance(evidence, EvidenceItem)
    assert evidence.workspace_id == 10
    assert evidence.title == mock_signal.title
    assert evidence.summary == mock_signal.summary
    assert evidence.reliability == "high"  # confidence 0.88 >= 0.8 -> high
    assert evidence.tags["signal_id"] == "sig_test_999"
    assert evidence.tags["related_hypothesis"] == "Khách hàng SME sẵn sàng chi trả cho tự động hóa"
    assert mock_signal.evidence_id == evidence.id
