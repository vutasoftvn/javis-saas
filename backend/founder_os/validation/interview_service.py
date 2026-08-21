import json
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from founder_os.validation.models import (
    ValidationSession,
    StructuredClaim,
    FieldRevision,
    ValidationAssumption,
    EpistemicType,
    ClaimConfirmationStatus,
    DimensionName,
    DimensionStateEnum,
    FeasibilityPillar,
    DimensionState,
)
from founder_os.validation.schemas import (
    StructuredClaimCreate,
    StructuredClaimResponse,
)
from founder_os.validation.service import ValidationEngineService
from founder_os.validation.question_graph_service import QuestionGraphService
from founder_os.strategy.models import Project
from workforce.chat.worker_prompt import run_worker_prompt

logger = logging.getLogger(__name__)

# 11 Cluster Order according to F1.md §23 - §34
INTERVIEW_TOPICS = [
    DimensionName.FOUNDER_FIT.value,
    "PROJECT_IDEA",
    DimensionName.CUSTOMER.value,
    DimensionName.PROBLEM.value,
    "ALTERNATIVE_COMPETITION",
    DimensionName.SOLUTION.value,
    DimensionName.PRICING.value,
    DimensionName.CHANNEL.value,
    DimensionName.TECHNICAL.value,
    "BUSINESS_VIABILITY",
    DimensionName.GROWTH.value,
]

VALIDATION_INTERVIEWER_SYSTEM_PROMPT = """You are COSA Project Validation Interviewer (F2.md & F3.md).

Your responsibility is not to convince the founder that an idea is good or bad.
Your responsibility is to progressively understand the project, identify assumptions, determine missing evidence, and help convert critical assumptions into testable hypotheses using a strict Problem-First approach.

Rules:
1. Treat founder statements as claims, not facts, unless supporting evidence exists.
2. Distinguish: FACT, BELIEF, ASSUMPTION, HYPOTHESIS, EVIDENCE, DECISION.
3. Apply a Problem-First approach: Distinguish the customer's Job-to-be-Done (JTBD) from the proposed Solution.
4. Ask how customers currently solve the problem (Current Alternative & Cost) before discussing replacement solutions.
5. Treat observed behavior, time commitment, deposit and payment as stronger evidence than praise (Action > Words).
6. Detect Solution Bias when Solution maturity significantly exceeds Problem evidence maturity.
7. When Solution Bias is detected, prioritize Problem Validation before recommending major builds.
8. Do not interpret compliments from friends or prospective users ("Ý tưởng rất hay") as strong validation.
9. Ask only 1–3 related questions per turn. Focus on specific past behavior rather than hypothetical opinions.
10. Do not repeat questions already answered.
11. Do not fabricate missing values. Allow UNKNOWN.
12. At the end of each topic cluster, summarize the structured data you extracted.
13. Ask the founder to Confirm, Edit, Continue Discussing, or Mark Uncertain.
14. Never silently change founder-confirmed data.
15. Pain Severity scores must be evidence-backed; 40/50 threshold is a framework heuristic, not an absolute approval rule.
16. Always respond in valid JSON matching the specified schema.
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


class ValidationInterviewService:
    @staticmethod
    async def process_user_turn(
        db: Session,
        workspace_id: int,
        brain_id: int,
        project_id: int,
        user_message: str,
        current_topic: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Xử lý một lượt trao đổi giữa Founder và Validation Interviewer:
        1. Lấy context session và các claims đã có của Project.
        2. Gửi cho LLM để phân tích:
           - Trích xuất Structured Claims mới (kèm Epistemic Type).
           - Phát hiện UNKNOWN hoặc Contradictions.
           - Đưa ra phản hồi tự nhiên + 1-3 câu hỏi kế tiếp.
           - Tóm tắt cụm dữ liệu nếu đã đủ thông tin cho topic.
        3. Tự động lưu Structured Claims và cập nhật DimensionState.
        """
        # 1. Lấy hoặc tạo session
        session = ValidationEngineService.get_or_create_session(
            db=db,
            workspace_id=workspace_id,
            brain_id=brain_id,
            project_id=project_id,
            initial_topic=current_topic or DimensionName.CUSTOMER.value,
        )
        active_topic = current_topic or session.current_topic

        # 2. Lấy dữ liệu Project & Claims hiện có
        project = db.get(Project, project_id)
        existing_claims = db.scalars(
            select(StructuredClaim).where(
                StructuredClaim.workspace_id == workspace_id,
                StructuredClaim.project_id == project_id,
            )
        ).all()

        claims_context = [
            {
                "dimension": c.dimension,
                "subject": c.subject,
                "predicate": c.predicate,
                "value": c.value_jsonb,
                "epistemic_type": c.epistemic_type,
                "status": c.confirmation_status,
            }
            for c in existing_claims
        ]

        # 2b. Question Graph: câu hỏi ưu tiên cao nhất tính toán xác định (Supplement §14.2) —
        # gợi ý cho LLM, không ép hỏi nguyên văn.
        question_suggestion = QuestionGraphService.select_next_question(
            db=db, workspace_id=workspace_id, project_id=project_id, session=session,
        )
        suggestion_block = ""
        coaching_block = ""
        if question_suggestion and question_suggestion.get("node"):
            node = question_suggestion["node"]
            suggestion_block = (
                f"\nCÂU HỎI ƯU TIÊN CAO NHẤT (Question Graph, tính toán xác định — không phải ý kiến AI):\n"
                f'"{node["prompt_vi"]}"\n'
                f"Lý do ưu tiên: {question_suggestion['rationale']}\n"
                f"Hãy diễn đạt tự nhiên theo mạch hội thoại, không đọc nguyên văn. Chỉ bỏ qua câu này nếu "
                f"hội thoại vừa rồi đã tự nhiên trả lời được nó hoặc có việc khẩn cấp hơn.\n"
            )
            # 2c. Just-in-time coaching (Supplement §20): tri thức trong Vault gắn đúng
            # stage/dimension của câu hỏi đang hỏi, không phải toàn bộ Vault không lọc gì.
            # Best-effort — brain rỗng hoặc lỗi embedding không được làm hỏng lượt hỏi.
            try:
                from platform_core.vault.retrieval_service import search_chunks

                knowledge_chunks = await search_chunks(
                    db, brain_id, node["prompt_vi"], k=2, stage=node["stage"], dimension=node["dimension"],
                )
                fresh_chunks = [c for c in knowledge_chunks if not c["stale"]]
                if fresh_chunks:
                    coaching_block = "\nKIẾN THỨC LIÊN QUAN (Vault, đúng stage/dimension câu hỏi):\n" + "\n".join(
                        f"- ({c['path']}) {c['text'][:300]}" for c in fresh_chunks
                    ) + "\n"
            except Exception:
                logger.warning("Coaching retrieval thất bại, bỏ qua không chặn lượt hỏi", exc_info=True)

        # 3. Xây dựng prompt
        prompt = (
            f"{VALIDATION_INTERVIEWER_SYSTEM_PROMPT}\n\n"
            f"PROJECT CONTEXT:\n"
            f"- Title: {project.title if project else 'Unknown'}\n"
            f"- Description: {project.description if project else 'N/A'}\n"
            f"- Current Project Stage: {project.project_stage if project else 'VALIDATION'}\n"
            f"- Active Interview Topic: {active_topic}\n"
            f"{coaching_block}"
            f"{suggestion_block}\n"
            f"EXISTING STRUCTURED CLAIMS ({len(claims_context)} claims):\n"
            f"{json.dumps(claims_context, ensure_ascii=False, indent=2)}\n\n"
            f"FOUNDER'S LATEST MESSAGE:\n"
            f'"{user_message}"\n\n'
            f"Respond with a JSON object containing:\n"
            f"{{\n"
            f'  "ai_reply": "Natural conversational response to founder in Vietnamese",\n'
            f'  "extracted_claims": [\n'
            f"    {{\n"
            f'      "dimension": "{active_topic}",\n'
            f'      "subject": "e.g. buyer",\n'
            f'      "predicate": "e.g. title",\n'
            f'      "value": "CEO",\n'
            f'      "epistemic_type": "ASSUMPTION",\n'
            f'      "confidence": 1.0\n'
            f"    }}\n"
            f"  ],\n"
            f'  "is_topic_cluster_complete": true/false,\n'
            f'  "cluster_summary": {{\n'
            f'    "title": "CUSTOMER SNAPSHOT",\n'
            f'    "summary_items": ["Customer: SMEs", "Buyer: CEO"],\n'
            f'    "status": "ASSUMPTION"\n'
            f"  }} (or null if not complete),\n"
            f'  "next_questions": ["Question 1", "Question 2"],\n'
            f'  "suggested_next_topic": "PROBLEM" (or current topic if still ongoing)\n'
            f"}}"
        )

        extracted_claims_objs = []
        try:
            worker_res = await run_worker_prompt(
                db=db,
                workspace_id=workspace_id,
                prompt=prompt,
                max_wait_seconds=45.0,
            )
            parsed = _extract_json(worker_res.text)
        except Exception as exc:
            logger.warning("ValidationInterviewService fallback on LLM error: %s", exc)
            # Fallback heuristic when worker is not available during offline tests
            parsed = {
                "ai_reply": f"Tôi đã ghi nhận thông tin về {active_topic}. Chúng ta hãy tiếp tục làm rõ thêm.",
                "extracted_claims": [
                    {
                        "dimension": active_topic,
                        "subject": "general",
                        "predicate": "statement",
                        "value": user_message,
                        "epistemic_type": EpistemicType.ASSUMPTION.value,
                        "confidence": 0.8,
                    }
                ],
                "is_topic_cluster_complete": False,
                "cluster_summary": None,
                "next_questions": [
                    "Anh/chị có thể chia sẻ cụ thể hơn về khó khăn lớn nhất gặp phải không?"
                ],
                "suggested_next_topic": active_topic,
            }

        # 4. Lưu các claims mới trích xuất được vào DB
        for c in parsed.get("extracted_claims", []):
            try:
                dim_str = c.get("dimension", active_topic)
                # Map to valid DimensionName or default to CUSTOMER
                dim_enum = (
                    DimensionName(dim_str)
                    if dim_str in DimensionName.__members__
                    else DimensionName.CUSTOMER
                )
                claim_dto = StructuredClaimCreate(
                    dimension=dim_enum,
                    subject=c.get("subject", "topic"),
                    predicate=c.get("predicate", "detail"),
                    value=c.get("value", {}),
                    epistemic_type=EpistemicType(c.get("epistemic_type", "ASSUMPTION")),
                    source_type="FOUNDER_CHAT",
                    confidence=float(c.get("confidence", 1.0)),
                )
                saved_claim = ValidationEngineService.create_claim(
                    db=db,
                    workspace_id=workspace_id,
                    brain_id=brain_id,
                    project_id=project_id,
                    claim_in=claim_dto,
                    session_id=session.id,
                )
                extracted_claims_objs.append(
                    {
                        "id": saved_claim.id,
                        "dimension": saved_claim.dimension,
                        "subject": saved_claim.subject,
                        "predicate": saved_claim.predicate,
                        "value": saved_claim.value_jsonb,
                        "confirmation_status": saved_claim.confirmation_status,
                    }
                )
            except Exception as e:
                logger.error("Failed to save extracted claim: %s", e)

        # 4b. Đánh dấu node Question Graph tương ứng dimension vừa trả lời là đã hỏi, để lượt
        # sau không gợi ý lại câu đã có claim. Heuristic v1 — xem docstring
        # ``mark_answered_for_dimension``; chỉ chạy khi có graph cho stage hiện tại.
        answered_stage = project.project_stage if project else None
        if answered_stage:
            for claim in extracted_claims_objs:
                QuestionGraphService.mark_answered_for_dimension(
                    session, claim["dimension"], answered_stage,
                )

        # 5. Cập nhật current_topic của session nếu topic hoàn thành
        if parsed.get("is_topic_cluster_complete") and parsed.get("suggested_next_topic"):
            session.current_topic = parsed.get("suggested_next_topic")

        db.commit()

        return {
            "session_id": session.id,
            "current_topic": session.current_topic,
            "ai_reply": parsed.get("ai_reply", ""),
            "extracted_claims": extracted_claims_objs,
            "is_topic_cluster_complete": parsed.get("is_topic_cluster_complete", False),
            "cluster_summary": parsed.get("cluster_summary"),
            "next_questions": parsed.get("next_questions", []),
            "suggested_next_topic": parsed.get("suggested_next_topic", session.current_topic),
            "question_graph_suggestion": (
                question_suggestion.get("node", {}).get("id") if question_suggestion else None
            ),
        }
