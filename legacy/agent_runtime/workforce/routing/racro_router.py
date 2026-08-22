"""
COSA RACRO Specialist Router & Intent Guard.
Triển khai logic định tuyến Intent đa tầng và đảm bảo invariant NO INTENT = NO TOOL.
"""

from typing import Optional
from business.marketing.racro_registry import RACROMove
from business.marketing.schemas.racro_contracts import RACROIntentDecision
from workforce.routing.deterministic import deterministic_intent


class RACROMarketingRouter:
    """Specialist Router chuyên biệt cho miền Marketing & Sales theo kiến trúc RACRO."""

    @staticmethod
    def route_query(message: str) -> RACROIntentDecision:
        if not message or not message.strip():
            return RACROIntentDecision(
                domain="general",
                move=None,
                capability_id=None,
                skill_name=None,
                confidence=1.0,
                is_tool_allowed=False,
                reason="Empty message - NO INTENT = NO TOOL"
            )

        # 1. Deterministic Intent Guard (Bắt các câu chào, cảm ơn)
        det = deterministic_intent(message)
        if det is not None:
            return RACROIntentDecision(
                domain="general",
                move=None,
                capability_id=None,
                skill_name=None,
                confidence=1.0,
                is_tool_allowed=False,
                reason="Social greeting detected - NO INTENT = NO TOOL invariant preserved."
            )

        norm = message.lower().strip()

        # 2. Khối 1: RESEARCH (Market, Competitor, Demand)
        if any(w in norm for w in ["đối thủ", "nghiên cứu đối thủ", "competitor", "giá đối thủ"]):
            return RACROIntentDecision(
                domain="marketing",
                move=RACROMove.RESEARCH,
                capability_id="competitor_intelligence",
                skill_name="competitor_intelligence",
                confidence=0.95,
                is_tool_allowed=True,
                reason="Matched competitor research intent."
            )

        if any(w in norm for w in ["thị trường", "market research", "nghiên cứu thị trường", "khách hàng mục tiêu", "icp", "phân khúc"]):
            return RACROIntentDecision(
                domain="marketing",
                move=RACROMove.RESEARCH,
                capability_id="market_intelligence",
                skill_name="market_intelligence",
                confidence=0.9,
                is_tool_allowed=True,
                reason="Matched market intelligence intent."
            )

        if any(w in norm for w in ["nhu cầu", "xu hướng tìm kiếm", "search volume", "trends", "tín hiệu nhu cầu", "demand"]):
            return RACROIntentDecision(
                domain="marketing",
                move=RACROMove.RESEARCH,
                capability_id="demand_intelligence",
                skill_name="demand_intelligence",
                confidence=0.9,
                is_tool_allowed=True,
                reason="Matched demand intelligence intent."
            )

        # 3. Khối 2: ATTRACT (Search & Discovery, Content & Creative, Distribution)
        if any(w in norm for w in ["tạo bài viết", "viết content", "brief video", "content pillar", "ý tưởng nội dung", "copywriting", "viết bài"]):
            return RACROIntentDecision(
                domain="marketing",
                move=RACROMove.ATTRACT,
                capability_id="content_creative",
                skill_name="content_creative",
                confidence=0.9,
                is_tool_allowed=True,
                reason="Matched content creative intent."
            )

        if any(w in norm for w in ["seo", "local seo", "google business", "tối ưu tìm kiếm", "map"]):
            return RACROIntentDecision(
                domain="marketing",
                move=RACROMove.ATTRACT,
                capability_id="search_discovery",
                skill_name="search_discovery",
                confidence=0.9,
                is_tool_allowed=True,
                reason="Matched search and discovery intent."
            )

        # 4. Khối 3: CONVERT (Campaign, Speed-to-Lead, Qualification)
        if any(w in norm for w in ["lead chưa", "lead mới", "chưa phản hồi", "speed to lead", "phản hồi lead", "chưa rep"]):
            return RACROIntentDecision(
                domain="sales",
                move=RACROMove.CONVERT,
                capability_id="speed_to_lead",
                skill_name="speed_to_lead_check",
                confidence=0.95,
                is_tool_allowed=True,
                reason="Matched speed-to-lead check intent."
            )

        if any(w in norm for w in ["tạo chiến dịch", "thu lead", "landing page", "chạy ads", "offer", "ưu đãi", "campaign"]):
            return RACROIntentDecision(
                domain="marketing",
                move=RACROMove.CONVERT,
                capability_id="campaign_offer",
                skill_name="campaign_offer",
                confidence=0.9,
                is_tool_allowed=True,
                reason="Matched campaign offer generation intent."
            )

        # 5. Khối 4: RETAIN (Follow-up, Review/Reputation, Referral)
        if any(w in norm for w in ["chăm sóc lại", "khách cũ", "reactivation", "follow up", "tái kích hoạt", "nhắc lịch"]):
            return RACROIntentDecision(
                domain="sales",
                move=RACROMove.RETAIN,
                capability_id="follow_up",
                skill_name="follow_up",
                confidence=0.9,
                is_tool_allowed=True,
                reason="Matched customer follow-up / retain intent."
            )

        if any(w in norm for w in ["đánh giá", "review", "feedback", "testimonial", "uy tín"]):
            return RACROIntentDecision(
                domain="marketing",
                move=RACROMove.RETAIN,
                capability_id="reputation",
                skill_name="reputation",
                confidence=0.85,
                is_tool_allowed=True,
                reason="Matched reputation and review management intent."
            )

        # 6. Khối 5: ORCHESTRATE (Marketing Pulse, Attribution, Brief)
        if any(w in norm for w in ["marketing hôm nay", "marketing pulse", "tổng kết marketing", "báo cáo marketing", "roi marketing", "hiệu quả marketing"]):
            return RACROIntentDecision(
                domain="marketing",
                move=RACROMove.ORCHESTRATE,
                capability_id="founder_brief",
                skill_name="founder_brief",
                confidence=0.95,
                is_tool_allowed=True,
                reason="Matched marketing orchestration / daily brief intent."
            )

        # Fallback về General Chat
        return RACROIntentDecision(
            domain="general",
            move=None,
            capability_id=None,
            skill_name=None,
            confidence=0.7,
            is_tool_allowed=False,
            reason="Unrecognized domain intent - fallback to General Conversation."
        )
