from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.agent_platform.routing.deterministic import Intent, deterministic_intent


class IntentDecision(BaseModel):
    intent: Intent
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reason: str = Field(default="")
    entities: Dict[str, Any] = Field(default_factory=dict)
    target_agent_key: str = Field(default="general")


class IntentRouter:
    """COSA Intent Router: Điều phối tin nhắn vào Lane A (Realtime Chat) hoặc Lane B (ADK Workflow)."""

    @staticmethod
    async def route_message(message: str) -> IntentDecision:
        # 1. Deterministic Check trước tiên
        det_intent = deterministic_intent(message)
        if det_intent is not None:
            return IntentDecision(
                intent=det_intent,
                confidence=1.0,
                reason="Deterministic match for greetings/social chat.",
                target_agent_key="general"
            )

        # 2. Rule-based heuristic phân loại nhanh
        normalized = message.lower()

        if any(w in normalized for w in ["doanh số", "bán hàng", "lead", "khách hàng", "crm", "pipeline", "chốt đơn"]):
            return IntentDecision(
                intent=Intent.SALES,
                confidence=0.9,
                reason="Matched sales keywords.",
                target_agent_key="sales"
            )

        if any(w in normalized for w in ["tài chính", "dòng tiền", "chi phí", "ngân sách", "lợi nhuận", "báo cáo tài chính", "thu chi"]):
            return IntentDecision(
                intent=Intent.FINANCE,
                confidence=0.9,
                reason="Matched finance keywords.",
                target_agent_key="finance"
            )

        if any(w in normalized for w in ["marketing", "chiến dịch", "quảng cáo", "bài viết", "content", "facebook", "tiktok"]):
            return IntentDecision(
                intent=Intent.MARKETING,
                confidence=0.9,
                reason="Matched marketing keywords.",
                target_agent_key="marketing"
            )

        if any(w in normalized for w in ["phát triển", "viết code", "lập trình", "bug", "lỗi code", "pull request", "github", "sandbox"]):
            return IntentDecision(
                intent=Intent.DEVELOPER,
                confidence=0.9,
                reason="Matched developer keywords.",
                target_agent_key="developer"
            )

        if any(w in normalized for w in ["chiến lược", "okr", "mục tiêu", "định hướng", "tổng hợp công ty", "toàn diện"]):
            return IntentDecision(
                intent=Intent.OKR_MANAGEMENT,
                confidence=0.85,
                reason="Matched strategic/founder keywords.",
                target_agent_key="founder"
            )

        if any(w in normalized for w in ["dự án", "project", "tiến độ"]):
            return IntentDecision(
                intent=Intent.PROJECT_QUERY,
                confidence=0.85,
                reason="Matched project query keywords.",
                target_agent_key="founder"
            )

        if any(w in normalized for w in ["tìm kiếm google", "google search", "tìm trên google", "tìm kiếm internet", "tra cứu trên mạng", "search web", "tìm thông tin trên mạng", "tra cứu web", "search google", "tin tức mới nhất", "tra cứu internet"]):
            return IntentDecision(
                intent=Intent.RESEARCH,
                confidence=0.95,
                reason="Matched search/research keywords.",
                target_agent_key="google_search"
            )

        # Default fallback về GENERAL_CHAT an toàn
        return IntentDecision(
            intent=Intent.GENERAL_CHAT,
            confidence=0.7,
            reason="Fallback to general conversation.",
            target_agent_key="general"
        )
