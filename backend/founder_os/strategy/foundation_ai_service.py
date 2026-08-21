import json
import logging
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from db.models import Brain
from workforce.chat.worker_prompt import run_worker_prompt

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = (
    "Bạn là chuyên gia tư vấn chiến lược doanh nghiệp. Dựa trên tên và mô tả công ty dưới "
    "đây, hãy đề xuất 1 Vision, 1 Mission và đúng 3 Core Values theo khung Strategic Canvas "
    "1-1-3. Vision và Mission phải dài 20-500 ký tự, súc tích và truyền cảm hứng. Mỗi Core "
    "Value cần có title (ngắn gọn), description (giải thích ý nghĩa), và decision_rule (một "
    "quy tắc cụ thể, kiểm tra được, dùng khi ra quyết định thực tế). Trả lời DUY NHẤT một "
    "khối JSON hợp lệ theo đúng cấu trúc sau, không kèm lời chào hay giải thích nào khác:\n"
    '{{"vision": "...", "mission": "...", "values": ['
    '{{"slot_no": 1, "title": "...", "description": "...", "decision_rule": "..."}}, '
    '{{"slot_no": 2, "title": "...", "description": "...", "decision_rule": "..."}}, '
    '{{"slot_no": 3, "title": "...", "description": "...", "decision_rule": "..."}}]}}\n\n'
    "Tên công ty: {name}\n"
    "Mô tả: {description}"
)


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.warning("generate_ai_foundation: AI response not valid JSON: %s", text[:500])
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI trả về nội dung không hợp lệ, hãy nhập Vision/Mission/Core Values thủ công",
        ) from exc


async def generate_foundation_suggestion(
    db: Session, workspace_id: int, canvas_name: str, canvas_description: Optional[str]
) -> dict:
    """Gợi ý Vision/Mission/3 Core Values bằng AI.

    Model chạy ở agent-worker, không phải ở brain-api (xem chat/worker_prompt.py). Chỉ
    trả gợi ý để người dùng xem lại và tự bấm Lưu, không tự ghi vào Foundation.
    """
    brain = db.query(Brain).filter(Brain.workspace_id == workspace_id).first()
    if brain is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Workspace chưa khởi tạo Brain, không thể sinh gợi ý bằng AI",
        )

    prompt = _PROMPT_TEMPLATE.format(
        name=canvas_name, description=canvas_description or "Không có mô tả"
    )
    result = await run_worker_prompt(
        db,
        brain_id=brain.id,
        prompt=prompt,
        title="AI Foundation Suggestion",
        manual_hint="hãy nhập Vision/Mission/Core Values thủ công",
    )
    parsed = _extract_json(result.text)

    vision = parsed.get("vision")
    mission = parsed.get("mission")
    values = parsed.get("values")
    if not vision or not mission or not isinstance(values, list) or len(values) != 3:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI trả về thiếu Vision/Mission/3 Core Values, hãy nhập thủ công",
        )
    return {
        "vision": vision,
        "mission": mission,
        "values": [
            {
                "slot_no": v.get("slot_no"),
                "title": v.get("title", ""),
                "description": v.get("description", ""),
                "decision_rule": v.get("decision_rule", ""),
            }
            for v in values
        ],
    }
