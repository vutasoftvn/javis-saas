from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.workforce.ai.prompt_registry import PromptRegistry


class SalesCommunicationCapability:
    """Capability for composing personalized multi-channel outreach drafts (Email, Zalo, Telegram)."""

    @classmethod
    def generate_outreach_drafts(
        cls,
        qualified_prospects: List[Dict[str, Any]],
        tone: str = "consultative_expert",
        sender_name: str = "COSA Founder",
        db: Optional[Session] = None,
        workspace_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        prompt_registry = PromptRegistry.get_instance()
        prompt_template = None
        if db is not None and workspace_id is not None:
            try:
                rendered_prompt = prompt_registry.render_effective(
                    db=db,
                    workspace_id=workspace_id,
                    domain="sales",
                    name="outreach",
                    variables={"company_name": "COSA OS"},
                )
            except Exception:
                rendered_prompt = None
        else:
            template_obj = prompt_registry.get("sales", "outreach")
            rendered_prompt = template_obj.content if template_obj else None

        drafts = []
        for p in qualified_prospects:
            recipient_name = p.get("name", "Quý đối tác")
            company_name = p.get("company", "quý công ty")
            industry = p.get("industry", "kinh doanh")
            pain_point = p.get("pain_point", "tối ưu quy trình vận hành và tăng trưởng")
            
            subject = f"Giải pháp tối ưu hóa vận hành & Agentic AI cho {company_name}"
            body_email = (
                f"Kính gửi {recipient_name},\n\n"
                f"Tôi là {sender_name} từ COSA OS. Chúng tôi nhận thấy {company_name} đang phát triển mạnh mẽ "
                f"trong lĩnh vực {industry}.\n\n"
                f"COSA đã giúp các One Person Company và Founder tự động hóa tới 80% quy trình vận hành và sales "
                f"thông qua hệ thống Agentic AI có kiểm soát.\n\n"
                f"Chúng tôi rất mong có cơ hội trao đổi ngắn 15 phút để demo cách COSA có thể áp dụng trực tiếp cho {company_name}.\n\n"
                f"Trân trọng,\n{sender_name}"
            )
            
            body_zalo = (
                f"Chào anh/chị {recipient_name} ({company_name}), em là {sender_name} bên COSA OS. "
                f"Em xin phép gửi anh/chị bản giới thiệu tóm tắt về hệ thống Agentic Founder OS giúp tối ưu quy trình kinh doanh. "
                f"Nếu thuận tiện, em xin phép đặt lịch hẹn trao đổi ngắn 15 phút với anh/chị trong tuần này nhé!"
            )

            drafts.append({
                "recipient_name": recipient_name,
                "recipient_email": p.get("email"),
                "company": company_name,
                "email_draft": {
                    "subject": subject,
                    "body": body_email,
                },
                "zalo_draft": {
                    "message": body_zalo,
                },
                "ready_for_approval": True,
            })

        return {
            "status": "success",
            "drafts_count": len(drafts),
            "drafts": drafts,
            "summary": f"Generated {len(drafts)} personalized outreach draft packages for Founder review.",
        }
