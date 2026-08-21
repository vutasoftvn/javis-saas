"""Chạy MỘT prompt qua agent-worker rồi trả về nguyên văn câu trả lời.

brain-api cố tình không giữ khoá provider: docker-compose chỉ truyền cho nó các cờ
``PROVIDER_CONFIGURED_*`` chứ không truyền khoá nào (DEPLOYMENT.md: "``env | grep
API_KEY`` trong container phải ra rỗng"), agent-worker mới là process có khoá thật. Vì
vậy mọi nút "AI đề xuất ..." nằm trong request handler đều phải nhờ worker gọi model hộ:
tạo một chat session ẩn, gửi 1 message, NOTIFY, rồi poll ``chat_messages`` tới khi có
phản hồi.

Gọi provider thẳng từ brain-api chỉ "chạy được" khi có khoá lọt vào container bằng đường
khác - và đó chính là cách nút "AI đề xuất roadmap" từng đâm vào một khoá OpenAI đã hết
quota rồi báo cho founder "AI đang bị giới hạn tốc độ, thử lại sau ít phút", một lời
khuyên không bao giờ đúng vì 429 đó là hết hạn mức chứ không phải nghẽn tạm thời.

Session ẩn mang ``purpose = ONESHOT_PURPOSE`` nên worker chạy nó ở chế độ một-lần: không
RAG, không tool, không system prompt hội thoại - xem chat_execution_service.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from db.models import AIRun, ChatMessage, ChatSession
from workforce.chat.chat_stream_bus import notify_user_message_submitted
from workforce.chat.model_registry import DEFAULT_MODEL, DEFAULT_PROVIDER
from workforce.chat.models import ONESHOT_PURPOSE

logger = logging.getLogger(__name__)

# Một câu trả lời JSON ngắn thường mất vài giây. 60s là trần cho trường hợp worker đang
# bận hàng đợi, vẫn còn nằm trong "cảm giác một cú bấm nút chờ trực tiếp" nên phía Flutter
# không cần polling/SSE riêng.
_POLL_INTERVAL_SECONDS = 1.0
DEFAULT_MAX_WAIT_SECONDS = 60.0


@dataclass(frozen=True)
class WorkerPromptResult:
    """Kết quả thật của lượt chạy, không phải cấu hình mong muốn: ``provider``/``model`` là
    cặp worker đã dùng, để ModelRunAudit ghi đúng thứ đã tiêu tiền."""

    text: str
    provider: str
    model: str
    latency_ms: int


def _provider_error_detail(error_code: Optional[str], manual_hint: str) -> str:
    """Lỗi provider phải nói đúng thứ founder sửa được.

    Gộp mọi thất bại thành "thử lại sau ít phút" là cách giấu mất hai nguyên nhân thường
    gặp nhất và không bao giờ tự hết: worker chưa có khoá, và tài khoản provider hết hạn
    mức/credit (HTTP 429 ``insufficient_quota`` trả về y hệt một lần rate limit thật).
    """
    if error_code == "provider_not_configured":
        return (
            "agent-worker chưa có khoá API cho model đang chọn nên không gọi được AI. "
            f"Bổ sung khoá provider cho worker rồi thử lại, hoặc {manual_hint}"
        )
    if error_code == "provider_http_429":
        return (
            "AI provider từ chối với HTTP 429 - tài khoản hết hạn mức/credit, hoặc đang bị "
            "chặn tốc độ. Kiểm tra billing của provider đang dùng, đổi sang model khác, "
            f"hoặc {manual_hint}"
        )
    if error_code == "provider_http_401" or error_code == "provider_http_403":
        return (
            "AI provider từ chối khoá API (HTTP 401/403). Kiểm tra lại khoá của worker, "
            f"hoặc {manual_hint}"
        )
    if error_code and error_code.startswith("provider_http_5"):
        return f"AI provider đang gặp sự cố, thử lại sau ít phút hoặc {manual_hint}"
    return f"AI provider gặp lỗi ({error_code or 'không rõ'}), {manual_hint}"


async def _wait_for_reply(
    db: Session, session_id, after_message_id, max_wait_seconds: float
) -> Optional[ChatMessage]:
    elapsed = 0.0
    while elapsed < max_wait_seconds:
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


async def run_worker_prompt(
    db: Session,
    *,
    brain_id,
    prompt: str,
    title: str,
    manual_hint: str,
    max_wait_seconds: float = DEFAULT_MAX_WAIT_SECONDS,
) -> WorkerPromptResult:
    """Nhờ agent-worker chạy ``prompt`` và trả về câu trả lời thô.

    ``manual_hint`` là lối thoát thủ công của chính tính năng gọi tới (ví dụ "hãy nhập MVP
    roadmap thủ công") - nó được ghép vào mọi thông báo lỗi để founder biết làm gì tiếp
    thay vì chỉ biết là hỏng.
    """
    session = ChatSession(
        brain_id=brain_id,
        title=title,
        provider=DEFAULT_PROVIDER,
        model=DEFAULT_MODEL,
        purpose=ONESHOT_PURPOSE,
    )
    db.add(session)
    db.flush()

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

    started_at = datetime.utcnow()
    try:
        assistant_message = await _wait_for_reply(
            db, session.id, user_message.id, max_wait_seconds
        )
        if assistant_message is None:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"AI phản hồi quá lâu, {manual_hint}",
            )
        if assistant_message.status == "error":
            # Lý do thật nằm ở AIRun.error_code; nội dung message chỉ là câu xin lỗi dành
            # cho khung chat, không đủ để founder biết phải sửa gì.
            run = (
                db.query(AIRun)
                .filter(AIRun.chat_session_id == session.id)
                .order_by(AIRun.id.desc())
                .first()
            )
            error_code = run.error_code if run is not None else None
            logger.warning("run_worker_prompt(%s) thất bại: %s", title, error_code)
            # Thiếu khoá là lỗi cấu hình phía ta (503), provider trả lỗi là lỗi của
            # upstream (502) - hai thứ này người vận hành xử lý khác nhau.
            raise HTTPException(
                status_code=(
                    status.HTTP_503_SERVICE_UNAVAILABLE
                    if error_code == "provider_not_configured"
                    else status.HTTP_502_BAD_GATEWAY
                ),
                detail=_provider_error_detail(error_code, manual_hint),
            )
        text = assistant_message.content or ""
        provider_used = session.provider
        model_used = session.model
    finally:
        # Session này chỉ để lấy 1 kết quả, không phải hội thoại người dùng cần giữ lại.
        # ai_runs.chat_message_id tham chiếu chat_messages nên phải xoá trước, nếu không
        # xoá chat_messages sẽ vi phạm FK (agent-worker luôn ghi 1 AIRun cho lượt trả lời).
        db.rollback()
        db.query(AIRun).filter(AIRun.chat_session_id == session.id).delete(synchronize_session=False)
        db.query(ChatMessage).filter(ChatMessage.session_id == session.id).delete(synchronize_session=False)
        db.query(ChatSession).filter(ChatSession.id == session.id).delete(synchronize_session=False)
        db.commit()

    return WorkerPromptResult(
        text=text,
        provider=provider_used,
        model=model_used,
        latency_ms=int((datetime.utcnow() - started_at).total_seconds() * 1000),
    )


def run_worker_prompt_sync(
    db: Session,
    *,
    brain_id,
    prompt: str,
    title: str,
    manual_hint: str,
    max_wait_seconds: float = DEFAULT_MAX_WAIT_SECONDS,
) -> WorkerPromptResult:
    """Bản gọi từ service đồng bộ (endpoint ``def``, chạy trong threadpool của FastAPI).

    Không dùng được từ endpoint ``async def`` - ở đó phải ``await run_worker_prompt``.
    """
    return asyncio.run(
        run_worker_prompt(
            db,
            brain_id=brain_id,
            prompt=prompt,
            title=title,
            manual_hint=manual_hint,
            max_wait_seconds=max_wait_seconds,
        )
    )
