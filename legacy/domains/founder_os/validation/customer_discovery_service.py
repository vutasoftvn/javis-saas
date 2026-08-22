import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, and_

from founder_os.validation.models import (
    CustomerContact,
    CustomerInterviewSession,
    VerbatimQuote,
    CustomerRoleEnum,
    BuyingSignalLevelEnum,
)
from founder_os.validation.schemas import (
    CustomerContactCreate,
    CustomerContactResponse,
    InterviewSessionCreate,
    InterviewSessionResponse,
    VerbatimQuoteCreate,
    VerbatimQuoteResponse,
    InterviewScriptResponse,
)
from workforce.chat.worker_prompt import run_worker_prompt

logger = logging.getLogger(__name__)

QUOTE_EXTRACTOR_PROMPT = """You are COSA Customer Evidence Analyst (F3.md §36).

Analyze the provided customer interview notes or transcript.
Extract key verbatim statements, tag them, and assign buying signal levels.

Rules:
1. Preserve the raw quote exactly as stated (do not sanitize or make up quotes).
2. For each quote, provide an analytical interpretation and identify the actor as "AI".
3. Assign applicable tags from: ["TIME", "COST", "EMOTION", "BEHAVIOR", "ALTERNATIVE", "WTP", "ROOT_CAUSE", "CONSEQUENCE"].
4. Classify buying signal if present:
   - LEVEL_1_INTEREST (Curiosity, asking questions)
   - LEVEL_2_PAIN (Complaining about current problems, high frustration)
   - LEVEL_3_WTP (Already paying for workarounds or stating budget spent)
   - LEVEL_4_ACTION (Requesting demo, trial, immediate follow-up)
   - LEVEL_5_STRONG_PROOF (Offering deposit, introducing to budget decider)

Return ONLY valid JSON matching this schema:
{
  "quotes": [
    {
      "raw_quote": "Exact text stated by customer",
      "interpretation": "Structured interpretation of pain or behavior",
      "tags": ["TIME", "BEHAVIOR"],
      "buying_signal_level": "LEVEL_2_PAIN"
    }
  ],
  "session_summary": "Concise summary of customer context and main findings",
  "referral_notes": "Any mentioned colleagues or other contacts to talk to"
}
"""

SCRIPT_BUILDER_PROMPT = """You are COSA Interview Script Builder (F3.md §4, §5).

Generate a 5-step customer discovery interview script based on the project context.
Crucial Rule: DO NOT include a "Pitch Solution" step. The interview is for discovery and understanding only.

Steps required:
1. Warm-up & Psychological Safety (Mở đầu / tạo an toàn)
2. Workflow & Context (Bối cảnh làm việc)
3. Problem & Friction Deep Dive (Khám phá vấn đề thực tế trong quá khứ)
4. Current Alternatives & Real Cost (Cách giải quyết hiện tại & Chi phí đã mất)
5. Wrap-up & Referral Request (Giới thiệu người tương tự)

Return ONLY valid JSON matching this schema:
{
  "script_title": "Customer Discovery Interview Guide",
  "target_segment": "Target audience description",
  "steps": [
    {
      "step_number": 1,
      "title": "Mở đầu / Tạo an toàn",
      "objective": "Thiết lập mối quan hệ và sự thoải mái",
      "questions": ["Câu hỏi 1", "Câu hỏi 2"]
    }
  ],
  "counter_bias_tips": [
    "Không giải thích hoặc pitch sản phẩm trong buổi này",
    "Nếu khách hỏi sản phẩm làm gì, nói rõ: 'Hôm nay em chỉ muốn lắng nghe quy trình thực tế của anh/chị'",
    "Ưu tiên hỏi: 'Lần gần nhất xảy ra là khi nào?' thay vì 'Anh/chị có thích...?'"
  ]
}
"""

def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return json.loads(cleaned[start_idx : end_idx + 1])
        raise


class CustomerDiscoveryService:
    @staticmethod
    def create_contact(
        db: Session, workspace_id: int, project_id: int, data: CustomerContactCreate
    ) -> CustomerContact:
        contact = CustomerContact(
            workspace_id=workspace_id,
            project_id=project_id,
            name=data.name,
            role=data.role,
            segment=data.segment,
            company=data.company,
            contact_info=data.contact_info,
            notes=data.notes,
        )
        db.add(contact)
        db.commit()
        db.refresh(contact)
        return contact

    @staticmethod
    def list_contacts(
        db: Session, workspace_id: int, project_id: int
    ) -> List[CustomerContact]:
        stmt = (
            select(CustomerContact)
            .where(
                and_(
                    CustomerContact.workspace_id == workspace_id,
                    CustomerContact.project_id == project_id,
                )
            )
            .order_by(desc(CustomerContact.created_at))
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def create_interview_session(
        db: Session, workspace_id: int, project_id: int, data: InterviewSessionCreate
    ) -> CustomerInterviewSession:
        session = CustomerInterviewSession(
            workspace_id=workspace_id,
            project_id=project_id,
            contact_id=data.contact_id,
            role=data.role,
            segment=data.segment,
            interview_date=data.interview_date or datetime.utcnow(),
            duration_minutes=data.duration_minutes,
            raw_notes=data.raw_notes,
            transcript=data.transcript,
            session_summary=data.session_summary,
            referral_notes=data.referral_notes,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def list_interview_sessions(
        db: Session, workspace_id: int, project_id: int
    ) -> List[Dict[str, Any]]:
        stmt = (
            select(CustomerInterviewSession)
            .where(
                and_(
                    CustomerInterviewSession.workspace_id == workspace_id,
                    CustomerInterviewSession.project_id == project_id,
                )
            )
            .order_by(desc(CustomerInterviewSession.interview_date))
        )
        sessions = list(db.scalars(stmt).all())
        results = []
        for s in sessions:
            quotes_count_stmt = select(VerbatimQuote).where(VerbatimQuote.session_id == s.id)
            quotes_count = len(list(db.scalars(quotes_count_stmt).all()))
            results.append({
                "id": s.id,
                "project_id": s.project_id,
                "contact_id": s.contact_id,
                "role": s.role,
                "segment": s.segment,
                "interview_date": s.interview_date,
                "duration_minutes": s.duration_minutes,
                "raw_notes": s.raw_notes,
                "transcript": s.transcript,
                "session_summary": s.session_summary,
                "referral_notes": s.referral_notes,
                "quotes_count": quotes_count,
                "created_at": s.created_at,
            })
        return results

    @staticmethod
    def add_verbatim_quote(
        db: Session, workspace_id: int, project_id: int, session_id: int, data: VerbatimQuoteCreate
    ) -> VerbatimQuote:
        quote = VerbatimQuote(
            workspace_id=workspace_id,
            project_id=project_id,
            session_id=session_id,
            raw_quote=data.raw_quote,
            interpretation=data.interpretation,
            interpretation_actor=data.interpretation_actor or "AI",
            tags_jsonb=data.tags or [],
            buying_signal_level=data.buying_signal_level,
            linked_assumption_id=data.linked_assumption_id,
        )
        db.add(quote)
        db.commit()
        db.refresh(quote)
        return quote

    @staticmethod
    def list_quotes_by_project(
        db: Session, workspace_id: int, project_id: int
    ) -> List[VerbatimQuote]:
        stmt = (
            select(VerbatimQuote)
            .where(
                and_(
                    VerbatimQuote.workspace_id == workspace_id,
                    VerbatimQuote.project_id == project_id,
                )
            )
            .order_by(desc(VerbatimQuote.created_at))
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    async def analyze_and_extract_quotes(
        db: Session, workspace_id: int, project_id: int, session_id: int
    ) -> Dict[str, Any]:
        """
        AI bóc tách Verbatim Quotes và gắn thẻ từ transcript hoặc raw notes của session.
        """
        session = db.scalar(
            select(CustomerInterviewSession).where(
                and_(
                    CustomerInterviewSession.id == session_id,
                    CustomerInterviewSession.workspace_id == workspace_id,
                )
            )
        )
        if not session:
            raise ValueError(f"Session {session_id} not found")

        content_to_analyze = session.transcript or session.raw_notes or ""
        if not content_to_analyze.strip():
            return {"quotes_extracted": 0, "quotes": []}

        user_prompt = f"Role: {session.role}\nSegment: {session.segment or 'N/A'}\nContent:\n{content_to_analyze}"

        try:
            raw_res = await run_worker_prompt(
                system_prompt=QUOTE_EXTRACTOR_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2,
            )
            parsed = _extract_json(raw_res)
            
            created_quotes = []
            for q_data in parsed.get("quotes", []):
                vq = VerbatimQuote(
                    workspace_id=workspace_id,
                    project_id=project_id,
                    session_id=session_id,
                    raw_quote=q_data["raw_quote"],
                    interpretation=q_data.get("interpretation"),
                    interpretation_actor="AI",
                    tags_jsonb=q_data.get("tags", []),
                    buying_signal_level=q_data.get("buying_signal_level"),
                )
                db.add(vq)
                created_quotes.append(vq)

            if parsed.get("session_summary") and not session.session_summary:
                session.session_summary = parsed.get("session_summary")
            if parsed.get("referral_notes") and not session.referral_notes:
                session.referral_notes = parsed.get("referral_notes")

            db.commit()
            return {
                "quotes_extracted": len(created_quotes),
                "summary": session.session_summary,
                "referral": session.referral_notes,
            }
        except Exception as e:
            logger.error(f"Error extracting quotes from session {session_id}: {e}")
            raise

    @staticmethod
    async def generate_interview_script(
        project_context: str, target_segment: str = "Target Customers"
    ) -> InterviewScriptResponse:
        user_prompt = f"Project Context: {project_context}\nTarget Segment: {target_segment}"
        try:
            raw_res = await run_worker_prompt(
                system_prompt=SCRIPT_BUILDER_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3,
            )
            parsed = _extract_json(raw_res)
            return InterviewScriptResponse(
                script_title=parsed.get("script_title", "Customer Discovery Script"),
                target_segment=parsed.get("target_segment", target_segment),
                steps=parsed.get("steps", []),
                counter_bias_tips=parsed.get("counter_bias_tips", []),
            )
        except Exception as e:
            logger.warning(f"Error generating script via LLM: {e}. Returning template.")
            return InterviewScriptResponse(
                script_title="Customer Discovery Interview Guide (Default)",
                target_segment=target_segment,
                steps=[
                    {
                        "step_number": 1,
                        "title": "Mở đầu / Tạo an toàn",
                        "objective": "Tạo sự thoải mái và làm rõ mục đích lắng nghe",
                        "questions": [
                            "Cảm ơn anh/chị đã dành thời gian. Hôm nay em muốn tìm hiểu thực tế quy trình làm việc hàng ngày của anh/chị.",
                            "Một ngày làm việc điển hình của anh/chị diễn ra như thế nào?"
                        ]
                    },
                    {
                        "step_number": 2,
                        "title": "Bối cảnh & Trách nhiệm",
                        "objective": "Xác định ai làm gì và ai chịu ảnh hưởng",
                        "questions": [
                            "Trong quy trình này anh/chị chịu trách nhiệm chính ở phần nào?",
                            "Những ai khác cùng tham gia vào bước này?"
                        ]
                    },
                    {
                        "step_number": 3,
                        "title": "Khám phá vấn đề trong quá khứ",
                        "objective": "Khai thác hành vi thực tế đã diễn ra",
                        "questions": [
                            "Lần gần nhất xảy ra sự cố hoặc tắc nghẽn ở khâu này là khi nào?",
                            "Khi đó anh/chị đã xử lý như thế nào và bước nào mất nhiều thời gian nhất?",
                            "Hậu quả thực tế về thời gian hoặc tiền bạc là gì?"
                        ]
                    },
                    {
                        "step_number": 4,
                        "title": "Giải pháp thay thế & Chi phí",
                        "objective": "Hiểu công cụ hiện tại và mức độ sẵn sàng chi trả",
                        "questions": [
                            "Hiện anh/chị đang dùng công cụ hoặc cách thủ công nào để giải quyết việc này?",
                            "Điều gì ở cách làm hiện tại làm anh/chị khó chịu nhất?",
                            "Anh/chị đã từng chi tiền hoặc nguồn lực nào để xử lý việc này chưa?"
                        ]
                    },
                    {
                        "step_number": 5,
                        "title": "Kết thúc & Giới thiệu",
                        "objective": "Mở rộng mạng lưới đối tượng phỏng vấn",
                        "questions": [
                            "Anh/chị có biết ai khác trong ngành cũng đang gặp tình huống tương tự mà em có thể trao đổi không?"
                        ]
                    }
                ],
                counter_bias_tips=[
                    "Tuyệt đối không giải thích tính năng sản phẩm",
                    "Luôn đào sâu hành vi trong quá khứ (Action > Words)",
                    "Lắng nghe 80%, nói 20%"
                ]
            )
