import pytest
from datetime import datetime
from business.marketing.racro_registry import RACROMove
from business.marketing.schemas.racro_contracts import (
    MarketingSignal,
    MarketingMission,
    RACROIntentDecision,
    AttributionChainEvent,
)
from workforce.routing.racro_router import RACROMarketingRouter


def test_no_intent_no_tool_invariant():
    """Kiểm tra Invariant: Câu chào/hội thoại cơ bản KHÔNG được phép kích hoạt Tool (is_tool_allowed = False)."""
    greeting_queries = [
        "chào",
        "chào bạn",
        "xin chào COSA",
        "hello",
        "hello em",
        "cảm ơn",
        "thank you",
        "hôm nay trời đẹp nhỉ",
    ]
    for query in greeting_queries:
        decision = RACROMarketingRouter.route_query(query)
        assert decision.is_tool_allowed is False, f"Query '{query}' đã vi phạm quy tắc NO INTENT = NO TOOL!"
        assert decision.move is None
        assert decision.domain == "general"


def test_research_routing():
    """Kiểm tra định tuyến chính xác khối RESEARCH."""
    # Competitor Intelligence
    res1 = RACROMarketingRouter.route_query("nghiên cứu đối thủ của mID")
    assert res1.domain == "marketing"
    assert res1.move == RACROMove.RESEARCH
    assert res1.capability_id == "competitor_intelligence"
    assert res1.is_tool_allowed is True

    # Market Intelligence
    res2 = RACROMarketingRouter.route_query("nghiên cứu thị trường và tìm kiếm khách hàng mục tiêu")
    assert res2.domain == "marketing"
    assert res2.move == RACROMove.RESEARCH
    assert res2.capability_id == "market_intelligence"
    assert res2.is_tool_allowed is True

    # Demand Intelligence
    res3 = RACROMarketingRouter.route_query("kiểm tra xu hướng tìm kiếm và tín hiệu nhu cầu")
    assert res3.domain == "marketing"
    assert res3.move == RACROMove.RESEARCH
    assert res3.capability_id == "demand_intelligence"
    assert res3.is_tool_allowed is True


def test_attract_routing():
    """Kiểm tra định tuyến chính xác khối ATTRACT."""
    # Content & Creative
    res1 = RACROMarketingRouter.route_query("tạo bài viết và viết content cho tuần tới")
    assert res1.domain == "marketing"
    assert res1.move == RACROMove.ATTRACT
    assert res1.capability_id == "content_creative"
    assert res1.is_tool_allowed is True

    # Search & Discovery
    res2 = RACROMarketingRouter.route_query("tối ưu local seo và google business")
    assert res2.domain == "marketing"
    assert res2.move == RACROMove.ATTRACT
    assert res2.capability_id == "search_discovery"
    assert res2.is_tool_allowed is True


def test_convert_routing():
    """Kiểm tra định tuyến chính xác khối CONVERT & Speed-to-Lead."""
    # Speed to Lead (Route to Sales Domain with Convert Move)
    res1 = RACROMarketingRouter.route_query("kiểm tra xem có lead mới nào chưa phản hồi không")
    assert res1.domain == "sales"
    assert res1.move == RACROMove.CONVERT
    assert res1.capability_id == "speed_to_lead"
    assert res1.is_tool_allowed is True

    # Campaign & Offer
    res2 = RACROMarketingRouter.route_query("tạo chiến dịch thu lead cho sản phẩm mới")
    assert res2.domain == "marketing"
    assert res2.move == RACROMove.CONVERT
    assert res2.capability_id == "campaign_offer"
    assert res2.is_tool_allowed is True


def test_retain_routing():
    """Kiểm tra định tuyến chính xác khối RETAIN."""
    # Follow-Up
    res1 = RACROMarketingRouter.route_query("chăm sóc lại khách cũ tháng trước")
    assert res1.domain == "sales"
    assert res1.move == RACROMove.RETAIN
    assert res1.capability_id == "follow_up"
    assert res1.is_tool_allowed is True

    # Reputation & Reviews
    res2 = RACROMarketingRouter.route_query("thu thập feedback và quản lý review khách hàng")
    assert res2.domain == "marketing"
    assert res2.move == RACROMove.RETAIN
    assert res2.capability_id == "reputation"
    assert res2.is_tool_allowed is True


def test_orchestrate_routing():
    """Kiểm tra định tuyến chính xác khối ORCHESTRATE."""
    res = RACROMarketingRouter.route_query("marketing hôm nay có gì cần tôi chú ý?")
    assert res.domain == "marketing"
    assert res.move == RACROMove.ORCHESTRATE
    assert res.capability_id == "founder_brief"
    assert res.is_tool_allowed is True


def test_racro_data_contracts():
    """Kiểm tra tính toàn vẹn của Pydantic Contracts."""
    # MarketingSignal
    sig = MarketingSignal(
        id="sig_12345",
        workspace_id=1,
        source_type="search",
        title="Tăng trưởng tìm kiếm từ khóa X",
        summary="Volume tăng 45% trong tuần qua",
        confidence=0.85,
    )
    assert sig.id == "sig_12345"
    assert sig.confidence == 0.85
    assert sig.evidence_id is None

    # MarketingMission
    mission = MarketingMission(
        mission_id="msn_999",
        workspace_id=1,
        move=RACROMove.RESEARCH,
        capability_id="competitor_intelligence",
        intent="Nghiên cứu đối thủ",
        goal="Lập bảng so sánh 3 đối thủ chính",
    )
    assert mission.move == RACROMove.RESEARCH
    assert mission.approval_required is False

    # AttributionChainEvent
    attr = AttributionChainEvent(
        event_id="attr_001",
        workspace_id=1,
        campaign_id=10,
        lead_id=100,
        revenue_amount=5000000.0,
        event_type="sale_closed",
    )
    assert attr.revenue_amount == 5000000.0
    assert attr.event_type == "sale_closed"
