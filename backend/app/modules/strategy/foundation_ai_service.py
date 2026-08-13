import asyncio
import json
import logging
import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import AIRun, Brain, ChatMessage, ChatSession
from app.modules.chat.chat_stream_bus import notify_user_message_submitted
from app.modules.chat.model_registry import DEFAULT_PROVIDER, DEFAULT_MODEL

logger = logging.getLogger(__name__)

# DeepSeek/OpenRouter cho một câu trả lời JSON ngắn thường mất vài giây; 30s đủ dư mà
# vẫn còn "cảm giác" là một cú bấm nút chờ trực tiếp, không cần polling/SSE phía Flutter.
_POLL_INTERVAL_SECONDS = 1.0
_MAX_WAIT_SECONDS = 30.0

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


async def _wait_for_reply(db: Session, session_id: int, after_message_id: int) -> Optional[ChatMessage]:
    elapsed = 0.0
    while elapsed < _MAX_WAIT_SECONDS:
        db.rollback()  # kết thúc transaction đang mở để lần query kế tiếp đọc dữ liệu mới nhất
        reply = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.session_id == session_id,
                ChatMessage.role == "assistant",
                ChatMessage.id > after_message_id,
                ChatMessage.status.in_(["delivered", "error"]),
            )
            .order_by(ChatMessage.created_at.asc())
            .first()
        )
        if reply is not None:
            return reply
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)
        elapsed += _POLL_INTERVAL_SECONDS
    return None


async def generate_foundation_suggestion(
    db: Session, workspace_id: int, canvas_name: str, canvas_description: Optional[str]
) -> dict:
    """Gợi ý Vision/Mission/3 Core Values bằng AI.

    brain-api không giữ API key thật của provider (chỉ agent-worker có - xem
    DEPLOYMENT.md, docker-compose.yml: agent-worker nhận OPENROUTER_API_KEY/...,
    brain-api chỉ nhận cờ PROVIDER_CONFIGURED_*). Vì vậy không gọi provider trực tiếp ở
    đây được - phải tạo một chat session "ẩn", gửi 1 message rồi NOTIFY để agent-worker xử
    lý như một job chat bình thường, sau đó poll bảng chat_messages tới khi có phản hồi.
    Chỉ trả gợi ý để người dùng xem lại và tự bấm Lưu, không tự ghi vào Foundation.
    """
    brain = db.query(Brain).filter(Brain.workspace_id == workspace_id).first()
    if brain is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Workspace chưa khởi tạo Brain, không thể sinh gợi ý bằng AI",
        )

    session = ChatSession(
        brain_id=brain.id,
        title="AI Foundation Suggestion",
        provider=DEFAULT_PROVIDER,
        model=DEFAULT_MODEL,
    )
    db.add(session)
    db.flush()

    prompt = _PROMPT_TEMPLATE.format(
        name=canvas_name, description=canvas_description or "Không có mô tả"
    )
    user_message = ChatMessage(
        session_id=session.id,
        role="user",
        content=prompt,
        client_message_id=str(uuid.uuid4()),
        status="sent",
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    notify_user_message_submitted(db, session.id)

    try:
        assistant_message = await _wait_for_reply(db, session.id, user_message.id)
        if assistant_message is None:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="AI phản hồi quá lâu, hãy nhập Vision/Mission/Core Values thủ công",
            )
        if assistant_message.status == "error":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI provider lỗi, hãy nhập Vision/Mission/Core Values thủ công",
            )
        parsed = _extract_json(assistant_message.content)
    finally:
        # Session này chỉ để lấy 1 gợi ý, không phải hội thoại người dùng cần giữ lại.
        # ai_runs.chat_message_id tham chiếu chat_messages nên phải xoá trước, nếu không
        # xoá chat_messages sẽ vi phạm FK (agent-worker luôn ghi 1 AIRun cho lượt trả lời).
        db.rollback()
        db.query(AIRun).filter(AIRun.chat_session_id == session.id).delete(synchronize_session=False)
        db.query(ChatMessage).filter(ChatMessage.session_id == session.id).delete(synchronize_session=False)
        db.query(ChatSession).filter(ChatSession.id == session.id).delete(synchronize_session=False)
        db.commit()

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
