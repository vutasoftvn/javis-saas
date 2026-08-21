"""
COSA RACRO Convert & Attract Service.
Hiện thực hóa các Capabilities:
1. Content & Creative (Targeted Content generation tied to Demand Signal & ICP)
2. Lead Intake & Qualification Scoring (Fit + Intent + Budget = 0-100)
3. Speed-to-Lead Automation (Instant response & channel dispatch)
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from business.marketing.schemas.racro_contracts import MarketingSignal
from business.marketing.adapters.channel_adapter import MultiChannelDispatcher, DispatchResult
from business.sales.models import SalesLead, Contact


class RACROConvertService:
    def __init__(self, dispatcher: Optional[MultiChannelDispatcher] = None):
        self.dispatcher = dispatcher or MultiChannelDispatcher()

    def generate_targeted_content(
        self,
        demand_signal: MarketingSignal,
        icp: Dict[str, Any],
        offer_type: str = "demo",
        channel: str = "social_post",
    ) -> Dict[str, Any]:
        """Sản xuất nội dung thu hút có nguồn gốc từ Demand Signal và ICP (§4.2 Spec)."""
        target_role = icp.get("role", "Founder / Giám đốc điều hành")
        target_industry = icp.get("industry", "Doanh nghiệp SME")

        title = f"Giải pháp tối ưu cho {target_role} ngành {target_industry}"
        body = (
            f"Dựa trên xu hướng '{demand_signal.title}': {demand_signal.summary}\n\n"
            f"Chúng tôi mang đến giải pháp {offer_type.upper()} giúp tự động hóa và tăng trưởng doanh thu vượt bậc."
        )

        return {
            "title": title,
            "content": body,
            "channel": channel,
            "signal_id": demand_signal.id,
            "target_icp": icp,
            "offer_type": offer_type,
            "created_at": datetime.utcnow().isoformat(),
        }

    def score_lead(self, payload: Dict[str, Any]) -> Tuple[float, float, str]:
        """Chấm điểm tiềm năng Lead (Fit + Intent + Budget) trên thang điểm 100 (§5.3 Spec)."""
        fit_score = 0.0
        intent_score = 0.0

        company = payload.get("company")
        title = payload.get("title") or payload.get("role")
        message = payload.get("message") or payload.get("need") or ""
        budget_signal = payload.get("budget_signal")

        # 1. Fit Score (Max 50đ): Có công ty, có chức danh quản lý
        if company:
            fit_score += 25.0
        if title and any(r in str(title).lower() for r in ["ceo", "founder", "giám đốc", "trưởng phòng", "manager", "head"]):
            fit_score += 25.0
        elif title:
            fit_score += 15.0

        # 2. Intent Score (Max 50đ): Nhu cầu cụ thể, độ dài thông điệp, budget
        if len(message.strip()) > 20:
            intent_score += 25.0
        elif len(message.strip()) > 5:
            intent_score += 15.0

        if budget_signal:
            intent_score += 25.0
        elif payload.get("utm_campaign"):
            intent_score += 10.0

        total_score = min(100.0, fit_score + intent_score)

        if total_score >= 70.0:
            status = "QUALIFIED"
        elif total_score >= 40.0:
            status = "NURTURING"
        else:
            status = "DISQUALIFIED"

        return fit_score, intent_score, status

    async def execute_speed_to_lead(
        self,
        lead: SalesLead,
        contact: Optional[Contact],
        payload: Dict[str, Any],
        db: Session,
    ) -> DispatchResult:
        """Tự động chấm điểm và gửi phản hồi Speed-to-Lead tức thì (§5.2 Spec)."""
        fit_score, intent_score, qualification_status = self.score_lead(payload)

        lead.fit_score = fit_score
        lead.intent_score = intent_score
        lead.qualification_status = qualification_status
        lead.next_action_at = datetime.utcnow() + timedelta(hours=2)
        lead.next_action_type = "SALES_FOLLOWUP" if qualification_status == "QUALIFIED" else "AUTO_NURTURE"

        db.flush()

        # Gửi tin nhắn phản hồi tự động
        recipient = (contact.email or contact.phone or lead.name) if contact else lead.name
        reply_message = (
            f"Chào {contact.name if contact else lead.name}, cảm ơn bạn đã quan tâm đến giải pháp của COSA! "
            f"Đội ngũ chuyên gia đã tiếp nhận yêu cầu và sẽ liên hệ hỗ trợ bạn trong ít phút."
        )

        dispatch_res = await self.dispatcher.send_message(
            recipient=recipient,
            message=reply_message,
            meta={"channel": "email" if contact and contact.email else "sms", "lead_id": lead.id},
        )
        return dispatch_res
