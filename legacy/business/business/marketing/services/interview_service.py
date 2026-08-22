import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from business.marketing.models_validation import (
    CustomerInterview,
    MarketingAttribution,
    Assumption,
    Evidence,
    EvidenceSourceType,
    EvidenceStrength,
)
from business.marketing.schemas.validation_schemas import EvidenceCreate
from business.marketing.services.assumption_service import AssumptionService


class InterviewService:
    """
    Customer Interview & CRM Evidence Management (§33 - §35, §58 - §59 trong E3.md).
    """

    @classmethod
    def extract_interview_from_transcript(
        cls,
        transcript_text: str,
        customer_name: Optional[str] = None,
        segment: Optional[str] = "ICP Target",
    ) -> Dict[str, Any]:
        """
        AI trích xuất tín hiệu khách hàng (Pains, Alternatives, Objections, Willingness-to-pay, Quotes)
        từ nội dung phỏng vấn thô (§35).
        """
        lines = [l.strip() for l in transcript_text.split("\n") if l.strip()]
        
        pains: List[str] = []
        alternatives: List[str] = []
        objections: List[str] = []
        quotes: List[str] = []
        willingness_to_pay: Optional[str] = None

        for line in lines:
            lower = line.lower()
            # Quotes extraction with regex first
            quote_match = re.search(r'["“]([^"”]+)["”]', line)
            if quote_match:
                quotes.append(quote_match.group(1).strip())

            # Pains
            if any(w in lower for w in ("khó khăn", "nỗi đau", "mất thời gian", "phức tạp", "tốn công", "vấn đề lớn", "phân tán")):
                pains.append(line.lstrip("-*•0123456789. "))
            
            # Alternatives
            if any(w in lower for w in ("đang dùng", "hiện tại dùng", "notion", "excel", "chatgpt", "thuê ngoài", "freelancer")):
                alternatives.append(line.lstrip("-*•0123456789. "))
            
            # Objections
            if any(w in lower for w in ("ngại", "lo ngại", "sợ", "chưa tin", "bảo mật", "khó dùng", "không có thời gian học")):
                objections.append(line.lstrip("-*•0123456789. "))
            
            # Willingness to pay
            if any(w in lower for w in ("giá", "sẵn sàng trả", "chi phí", "ngân sách", "500k", "1 triệu", "100$", "trả phí")):
                willingness_to_pay = line.lstrip("-*•0123456789. ")

        if not pains and lines:
            pains.append(lines[0])
        if not quotes and lines:
            quotes.append(lines[-1])

        return {
            "customer_name": customer_name or "Khách hàng ẩn danh",
            "segment": segment,
            "interview_date": datetime.utcnow().isoformat(),
            "pains": pains[:5],
            "alternatives": alternatives[:5],
            "objections": objections[:5],
            "willingness_to_pay": willingness_to_pay,
            "notable_quotes": quotes[:5],
        }

    @classmethod
    def record_interview_and_generate_evidence(
        cls,
        db: Session,
        workspace_id: int,
        brain_id: int,
        project_id: Optional[int],
        contact_id: Optional[int],
        customer_name: Optional[str],
        segment: str,
        pains: List[str],
        alternatives: List[str],
        objections: List[str],
        willingness_to_pay: Optional[str],
        notable_quotes: List[str],
        notes: Optional[str] = None,
    ) -> Tuple[CustomerInterview, List[Evidence]]:
        """
        Lưu Interview có cấu trúc và tự động sinh Evidence hỗ trợ các Assumption hiện có (§35, §101).
        """
        # 1. Tạo CustomerInterview
        interview = CustomerInterview(
            workspace_id=workspace_id,
            brain_id=brain_id,
            project_id=project_id,
            contact_id=contact_id,
            customer_name=customer_name,
            segment=segment,
            pains=pains,
            alternatives=alternatives,
            objections=objections,
            willingness_to_pay=willingness_to_pay,
            notable_quotes=notable_quotes,
            notes=notes,
        )
        db.add(interview)
        db.flush()

        generated_evidence: List[Evidence] = []
        generated_ev_ids: List[str] = []

        # 2. Tìm các assumptions liên quan để gắn evidence
        assumptions = db.query(Assumption).filter(Assumption.workspace_id == workspace_id).all()

        # Tạo evidence từ pain points
        for pain in pains:
            matching_asms = [
                str(a.id) for a in assumptions 
                if a.category in ("customer", "problem")
            ]
            if matching_asms:
                ev_data = EvidenceCreate(
                    statement=f"Khách hàng {customer_name or 'phỏng vấn'} ({segment}) xác nhận nỗi đau: '{pain}'",
                    source_type=EvidenceSourceType.CUSTOMER_INTERVIEW,
                    source_id=str(interview.id),
                    project_id=project_id,
                    supports_assumption_ids=matching_asms[:2],
                    strength=EvidenceStrength.STRONG,
                    meta_data={"quotes": notable_quotes},
                )
                ev, _ = AssumptionService.create_evidence(db=db, workspace_id=workspace_id, brain_id=brain_id, data=ev_data)
                generated_evidence.append(ev)
                generated_ev_ids.append(str(ev.id))

        # Tạo evidence từ willingness to pay nếu có
        if willingness_to_pay:
            pricing_asms = [
                str(a.id) for a in assumptions 
                if a.category in ("pricing", "offer")
            ]
            if pricing_asms:
                ev_data = EvidenceCreate(
                    statement=f"Khách hàng {customer_name or 'phỏng vấn'} phản hồi về mức giá/ngân sách: '{willingness_to_pay}'",
                    source_type=EvidenceSourceType.CUSTOMER_INTERVIEW,
                    source_id=str(interview.id),
                    project_id=project_id,
                    supports_assumption_ids=pricing_asms[:2],
                    strength=EvidenceStrength.MEDIUM,
                )
                ev, _ = AssumptionService.create_evidence(db=db, workspace_id=workspace_id, brain_id=brain_id, data=ev_data)
                generated_evidence.append(ev)
                generated_ev_ids.append(str(ev.id))

        interview.evidence_ids = generated_ev_ids
        db.flush()
        return interview, generated_evidence

    @classmethod
    def record_attribution(
        cls,
        db: Session,
        workspace_id: int,
        contact_id: Optional[int] = None,
        lead_id: Optional[int] = None,
        campaign_id: Optional[int] = None,
        experiment_id: Optional[int] = None,
        variant_id: Optional[str] = None,
        utm_source: Optional[str] = None,
        utm_medium: Optional[str] = None,
        utm_campaign: Optional[str] = None,
        utm_content: Optional[str] = None,
        utm_term: Optional[str] = None,
    ) -> MarketingAttribution:
        """
        Ghi nhận nguồn gốc Marketing Attribution cho Lead/Contact (§58, §59).
        """
        attr = MarketingAttribution(
            workspace_id=workspace_id,
            contact_id=contact_id,
            lead_id=lead_id,
            campaign_id=campaign_id,
            experiment_id=experiment_id,
            variant_id=variant_id,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
            utm_content=utm_content,
            utm_term=utm_term,
        )
        db.add(attr)
        db.flush()
        return attr
