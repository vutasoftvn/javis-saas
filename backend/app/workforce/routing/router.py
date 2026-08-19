from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.workforce.routing.deterministic import Intent, deterministic_intent


class IntentDecision(BaseModel):
    intent: Intent
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reason: str = Field(default="")
    entities: Dict[str, Any] = Field(default_factory=dict)
    target_agent_key: str = Field(default="general")


class IntentRouter:
    """COSA Intent Router: Điều phối tin nhắn vào Co-Founder Engine hoặc Domain Agents theo F4 Spec."""

    @staticmethod
    async def route_message(message: str) -> IntentDecision:
        # 1. Deterministic Check trước tiên cho câu chào / cảm ơn
        det_intent = deterministic_intent(message)
        if det_intent is not None:
            return IntentDecision(
                intent=det_intent,
                confidence=1.0,
                reason="Deterministic match for greetings/social chat.",
                target_agent_key="cosa"
            )

        # 2. Rule-based heuristic phân loại
        normalized = message.lower().strip()

        # A. Founder Review / Focus / Top 3 / Pulse Queries
        if any(w in normalized for w in [
            "hôm nay tôi nên làm gì", "hôm nay làm gì", "tôi nên làm gì", "tập trung vào gì",
            "ưu tiên gì", "ưu tiên hôm nay", "ưu tiên tuần này", "top 3", "tình hình công ty",
            "báo cáo tổng thể", "pulse", "nhịp tim công ty", "review tuần", "công việc hôm nay"
        ]):
            return IntentDecision(
                intent=Intent.FOUNDER_REVIEW,
                confidence=0.95,
                reason="Matched founder review / priority / daily focus intent.",
                target_agent_key="cosa"
            )

        # B. Founder Decision Queries (Strategic Tradeoffs / Cross-domain Decisions)
        if any(w in normalized for w in [
            "có nên ", "quyết định ", "nên chọn phương án", "tăng ngân sách",
            "có nên mở rộng", "có nên chi", "có nên đầu tư", "đánh giá quyết định"
        ]):
            return IntentDecision(
                intent=Intent.FOUNDER_DECISION,
                confidence=0.9,
                reason="Matched strategic business decision intent.",
                target_agent_key="cosa"
            )

        # C. Founder Command (Mission Shaping & Multi-Agent Dispatch)
        if any(w in normalized for w in [
            "tìm cho tôi", "tìm 20 khách hàng", "trong 30 ngày", "tạo mission",
            "mục tiêu tháng", "mục tiêu tuần", "phát động chiến dịch", "triển khai dự án"
        ]):
            return IntentDecision(
                intent=Intent.FOUNDER_COMMAND,
                confidence=0.9,
                reason="Matched high-level founder command / mission shaping intent.",
                target_agent_key="cosa"
            )

        # D. Founder Reflection (Strategic thoughts & hypotheses)
        if any(w in normalized for w in [
            "tôi đang băn khoăn", "tôi nghĩ rằng", "tầm nhìn", "định hướng tương lai",
            "giả định của tôi", "ý kiến của bạn thế nào"
        ]):
            return IntentDecision(
                intent=Intent.FOUNDER_REFLECTION,
                confidence=0.85,
                reason="Matched founder strategic reflection intent.",
                target_agent_key="cosa"
            )

        # E. Core Domain 1: Sales
        if any(w in normalized for w in ["doanh số", "bán hàng", "lead", "crm", "pipeline", "chốt đơn", "outbound", "outreach"]):
            return IntentDecision(
                intent=Intent.SALES,
                confidence=0.9,
                reason="Matched sales domain keywords.",
                target_agent_key="sales"
            )

        # F. Core Domain 2: Finance
        if any(w in normalized for w in ["tài chính", "dòng tiền", "chi phí", "ngân sách", "lợi nhuận", "báo cáo tài chính", "thu chi", "runway", "cashflow", "sổ cái"]):
            return IntentDecision(
                intent=Intent.FINANCE,
                confidence=0.9,
                reason="Matched finance domain keywords.",
                target_agent_key="finance"
            )

        # G. Core Domain 3: Marketing
        if any(w in normalized for w in ["marketing", "chiến dịch", "quảng cáo", "bài viết", "content", "facebook", "tiktok", "seo", "landing page", "icp", "positioning"]):
            return IntentDecision(
                intent=Intent.MARKETING,
                confidence=0.9,
                reason="Matched marketing domain keywords.",
                target_agent_key="marketing"
            )

        # H. Core Domain 4: Engineering & Tech / Build
        if any(w in normalized for w in ["phát triển", "viết code", "lập trình", "bug", "lỗi code", "pull request", "github", "sandbox", "kiến trúc phần mềm", "deploy"]):
            return IntentDecision(
                intent=Intent.DEVELOPER,
                confidence=0.9,
                reason="Matched engineering / build domain keywords.",
                target_agent_key="developer"
            )

        # I. Core Domain 5: Legal & Compliance
        if any(w in normalized for w in ["hợp đồng", "pháp lý", "điều khoản", "tuân thủ", "luật", "chính sách hỗ trợ", "nghĩa vụ pháp lý", "rủi ro pháp lý"]):
            return IntentDecision(
                intent=Intent.LEGAL,
                confidence=0.9,
                reason="Matched legal domain keywords.",
                target_agent_key="legal"
            )

        # J. Web Research & Search
        if any(w in normalized for w in ["tìm kiếm google", "google search", "tìm trên google", "tìm kiếm internet", "tra cứu trên mạng", "search web", "tìm thông tin trên mạng", "tra cứu web", "search google", "tin tức mới nhất", "tra cứu internet"]):
            return IntentDecision(
                intent=Intent.RESEARCH,
                confidence=0.95,
                reason="Matched search/research keywords.",
                target_agent_key="google_search"
            )

        # Default fallback về GENERAL_CHAT với COSA Co-Founder
        return IntentDecision(
            intent=Intent.GENERAL_CHAT,
            confidence=0.7,
            reason="Fallback to Co-Founder general conversation.",
            target_agent_key="cosa"
        )

