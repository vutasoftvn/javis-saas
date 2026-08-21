"""
COSA RACRO Retain Service.
Hiện thực hóa 3 Capabilities của Khối RETAIN:
1. Follow-Up & Playbooks (Chăm sóc theo trạng thái CRM)
2. Reputation & Review-to-Proof Loop (Đánh giá tốt -> Evidence / Testimonial)
3. Referral Engine (Vòng lặp giới thiệu khách hàng mới)
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from founder_os.strategy.models import EvidenceItem
from business.sales.models import SalesLead, Contact
from core.snowflake import generate_snowflake_id


class RACRORetainService:
    @staticmethod
    def generate_followup_playbook(
        stage: str,
        customer_name: str,
        channel: str = "email",
    ) -> Dict[str, Any]:
        """Tạo thông điệp chăm sóc khách hàng tuân thủ quy tắc và không spam (§6.1 Spec)."""
        stage_norm = stage.upper()
        
        if stage_norm in ["NEW", "NURTURING"]:
            subject = f"Tài liệu hữu ích dành riêng cho {customer_name}"
            body = f"Chào {customer_name}, COSA gửi bạn bộ tài liệu và cẩm nang tối ưu quy trình kinh doanh..."
            delay_days = 3
        elif stage_norm in ["WON", "CUSTOMER"]:
            subject = f"Khảo sát trải nghiệm giải pháp COSA của {customer_name}"
            body = f"Chào {customer_name}, cảm ơn bạn đã đồng hành. Hãy cho COSA biết cảm nhận của bạn để nâng cao dịch vụ nhé..."
            delay_days = 7
        elif stage_norm == "INACTIVE":
            subject = f"Món quà đặc biệt chào đón {customer_name} quay trở lại"
            body = f"Chào {customer_name}, COSA vừa ra mắt các tính năng mới cùng ưu đãi đặc quyền dành cho bạn..."
            delay_days = 30
        elif stage_norm == "RENEWAL_DUE":
            subject = f"Thông báo gia hạn gói dịch vụ COSA cho {customer_name}"
            body = f"Chào {customer_name}, gói dịch vụ của bạn sắp đến hạn gia hạn. Vui lòng kiểm tra quyền lợi..."
            delay_days = 14
        else:
            subject = f"Chăm sóc khách hàng - COSA"
            body = f"Chào {customer_name}, COSA luôn sẵn sàng hỗ trợ bạn bất cứ lúc nào."
            delay_days = 5

        return {
            "stage": stage_norm,
            "channel": channel,
            "subject": subject,
            "body": body,
            "scheduled_after_days": delay_days,
            "created_at": datetime.utcnow().isoformat(),
        }

    @staticmethod
    def process_customer_review(
        workspace_id: int,
        contact_id: int,
        rating: int,  # 1 - 5 sao
        review_text: str,
        customer_name: str,
        db: Session,
        user_id: int = 1,
    ) -> Tuple[Optional[EvidenceItem], Dict[str, Any]]:
        """Review-to-Proof Loop: Đánh giá >= 4 sao trở thành Evidence / Social Proof; Đánh giá <= 3 sao kích hoạt Service Recovery (§6.2 Spec)."""
        if rating >= 4:
            # Tạo EvidenceItem phục vụ làm bằng chứng tiếp thị (Social Proof)
            evidence = EvidenceItem(
                id=generate_snowflake_id(),
                workspace_id=workspace_id,
                title=f"Đánh giá {rating} sao từ khách hàng {customer_name}",
                summary=review_text,
                source_type="customer_interview",
                reliability="high" if rating == 5 else "medium",
                tags={
                    "social_proof": True,
                    "rating": rating,
                    "contact_id": contact_id,
                    "customer_name": customer_name,
                    "usage": "landing_page_testimonial",
                },
                created_by=user_id,
            )
            db.add(evidence)
            db.flush()
            return evidence, {
                "action": "PROMOTED_TO_EVIDENCE",
                "evidence_id": evidence.id,
                "message": "Đánh giá xuất sắc đã được lưu vào kho Bằng chứng tiếp thị (Social Proof).",
            }
        else:
            # Rating thấp: Kích hoạt cảnh báo hỗ trợ khách hàng khẩn cấp
            return None, {
                "action": "SERVICE_RECOVERY_ALERT",
                "requires_human_attention": True,
                "rating": rating,
                "contact_id": contact_id,
                "customer_name": customer_name,
                "feedback": review_text,
                "message": "Cảnh báo: Khách hàng có phản hồi chưa hài lòng. Cần Founder/CS liên hệ hỗ trợ ngay.",
            }

    @staticmethod
    def create_referral_lead(
        workspace_id: int,
        referrer_contact_id: int,
        referred_name: str,
        referred_email: Optional[str] = None,
        referred_phone: Optional[str] = None,
        company_name: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Tuple[Contact, SalesLead]:
        """Tạo Lead mới từ chương trình Referral, gắn định danh nguồn người giới thiệu (§6.3 Spec)."""
        now = datetime.utcnow()

        contact = Contact(
            workspace_id=workspace_id,
            name=referred_name,
            email=referred_email,
            phone=referred_phone,
            source="referral",
            created_at=now,
        )
        if db:
            db.add(contact)
            db.flush()

        lead = SalesLead(
            workspace_id=workspace_id,
            contact_id=contact.id if contact else None,
            name=referred_name,
            company=company_name,
            source="referral",
            stage="NEW",
            fit_score=35.0,  # Lead giới thiệu có điểm tin cậy ban đầu cao
            intent_score=35.0,
            qualification_status="QUALIFIED",
            next_action_type="REFERRAL_OUTREACH",
            next_action_at=now + timedelta(hours=4),
            created_at=now,
        )
        if db:
            db.add(lead)
            db.flush()

        return contact, lead
