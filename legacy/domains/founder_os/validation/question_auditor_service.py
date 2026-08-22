import json
import logging
from typing import Dict, Any, List

from founder_os.validation.models import QuestionTypeEnum
from founder_os.validation.schemas import QuestionAuditResponse
from workforce.chat.worker_prompt import run_worker_prompt

logger = logging.getLogger(__name__)

QUESTION_AUDITOR_PROMPT = """You are COSA Interview Question Auditor (F3.md §35).

Your responsibility is to analyze a proposed customer discovery interview question and classify it strictly as one of:
- PAST_BEHAVIOR (Questions about specific past events, real actions, or history)
- CURRENT_BEHAVIOR (Questions about current workflow, tools, or habits)
- OPINION (Questions asking what they think or feel in general)
- HYPOTHETICAL_FUTURE (Questions asking "Would you...", "If you had...", etc.)
- LEADING (Questions that nudge the interviewee towards a positive answer)
- SOLUTION_PITCH (Questions describing or pitching a feature/product)
- COST_DISCOVERY (Questions about money, time, or resources spent)
- ALTERNATIVE_DISCOVERY (Questions about current workarounds, tools, or doing nothing)

If the question is LEADING, SOLUTION_PITCH, OPINION, or HYPOTHETICAL_FUTURE:
1. Flag it as biased/leading (is_biased_or_leading = true).
2. Generate 2-3 high-quality neutral replacement questions focusing on PAST_BEHAVIOR, CURRENT_BEHAVIOR, COST, or ALTERNATIVE.
3. Provide a constructive warning message and clear reasoning.

Return ONLY a valid JSON object matching this schema:
{
  "classification": "LEADING | SOLUTION_PITCH | OPINION | HYPOTHETICAL_FUTURE | PAST_BEHAVIOR | CURRENT_BEHAVIOR | COST_DISCOVERY | ALTERNATIVE_DISCOVERY",
  "is_biased_or_leading": true/false,
  "warning_message": "Warning text if biased",
  "suggested_rewrites": ["Rewrite 1", "Rewrite 2"],
  "reasoning": "Explanation of why this question is biased or good"
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


class QuestionAuditorService:
    @staticmethod
    async def audit_question(question: str, research_objective: str = "") -> QuestionAuditResponse:
        user_prompt = f"Proposed Question: \"{question}\"\n"
        if research_objective:
            user_prompt += f"Research Objective: {research_objective}\n"

        try:
            raw_response = await run_worker_prompt(
                system_prompt=QUESTION_AUDITOR_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2,
            )
            parsed = _extract_json(raw_response)
            return QuestionAuditResponse(
                original_question=question,
                classification=parsed.get("classification", QuestionTypeEnum.OPINION.value),
                is_biased_or_leading=parsed.get("is_biased_or_leading", False),
                warning_message=parsed.get("warning_message"),
                suggested_rewrites=parsed.get("suggested_rewrites", []),
                reasoning=parsed.get("reasoning"),
            )
        except Exception as e:
            logger.warning(f"Failed to run LLM question audit: {e}. Falling back to rule-based analysis.")
            
            # Rule-based fallback
            lower_q = question.lower()
            if any(w in lower_q for w in ["nếu có", "nếu chúng tôi", "bạn có thấy tốt không", "bạn có mua không", "would you", "if there was"]):
                return QuestionAuditResponse(
                    original_question=question,
                    classification=QuestionTypeEnum.LEADING.value,
                    is_biased_or_leading=True,
                    warning_message="Leading / Solution Pitch: Hỏi về tương lai giả định hoặc dẫn dắt khách hàng khen ngợi.",
                    suggested_rewrites=[
                        "Lần gần nhất anh/chị gặp tình huống này là khi nào?",
                        "Hiện anh/chị đang giải quyết việc đó bằng công cụ hoặc quy trình nào?",
                        "Lần gần nhất anh/chị đã mất bao nhiêu thời gian hoặc chi phí cho việc xử lý nó?"
                    ],
                    reasoning="Câu hỏi giả định tương lai không phản ánh hành vi chi trả hay nhu cầu thực tế."
                )
            
            return QuestionAuditResponse(
                original_question=question,
                classification=QuestionTypeEnum.PAST_BEHAVIOR.value,
                is_biased_or_leading=False,
                warning_message=None,
                suggested_rewrites=[],
                reasoning="Câu hỏi tập trung vào khám phá thực tế."
            )
