import logging
import time
from datetime import datetime
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models import AIRun, Brain, ChatMessage, ChatSession, MCPConnection
from app.modules.chat import gmail_tools
from app.modules.chat.ai_router import AIRouter, ChatTurn
from app.modules.chat.chat_stream_bus import ChatEventPublisher, NullChatEventPublisher
from app.modules.chat.model_registry import DEFAULT_MODEL, DEFAULT_PROVIDER, get_model
from app.modules.integrations.google_connection_service import (
    CONNECTOR_TYPE as GOOGLE_CONNECTOR_TYPE,
    has_usable_google_connection,
)

logger = logging.getLogger(__name__)

# Cố định tiếng Việt cho mọi phản hồi - trước đây không gửi system prompt nào nên
# model tự chọn ngôn ngữ (có lúc trả lời song ngữ Việt/Anh không cần thiết). Chưa cần
# cấu hình theo workspace/brain, làm khi có yêu cầu đa ngôn ngữ thực tế.
SYSTEM_PROMPT_VI = (
    "Luôn trả lời bằng tiếng Việt, trừ khi người dùng yêu cầu rõ ràng dùng ngôn ngữ "
    "khác. Không cần dịch lại câu trả lời sang tiếng Anh."
)

# Token đi tới client qua NOTIFY ngay khi provider trả về; ghi DB chỉ để bền hoá nên gom
# lại theo nhịp này. Trước đây mỗi token tốn 2 commit (content + notify) - với ~50 token/s
# là ~100 lần fsync/giây trên một cột TEXT càng lúc càng dài, đủ để bóp nghẹt tốc độ stream.
CONTENT_COMMIT_INTERVAL_SECONDS = 0.75

# /cancel chạy ở process API khác nên chỉ phát hiện được bằng cách đọc lại DB. Đọc mỗi
# token là thêm một round-trip DB cho mỗi token; 0.4s vẫn phản hồi tức thì với người dùng.
CANCEL_CHECK_INTERVAL_SECONDS = 0.4

# Số vòng model được phép gọi tool trước khi buộc phải chốt câu trả lời. Đọc hòm thư thực
# tế cần 1-2 vòng (list, đôi khi get thêm 1 thư); để rộng hơn chỉ mở đường cho vòng lặp
# gọi tool vô tận, mà mỗi vòng là một lần gửi lại toàn bộ hội thoại đang phình to.
MAX_TOOL_ROUNDS = 4


GENERIC_FAILURE_MESSAGE = "Không thể tạo phản hồi AI lúc này."


def _failure_message(error_code: str | None, provider: str, model: str) -> str:
    """Thiếu khoá là lỗi cấu hình người dùng sửa được, khác hẳn provider đang chập chờn -
    câu trả lời phải chỉ đúng model nào hỏng thay vì một câu chung chung."""
    if error_code == "provider_not_configured":
        return (
            f"Model {model} ({provider}) chưa được cấu hình API key trên máy chủ. "
            "Hãy chọn model khác trong danh sách, hoặc bổ sung khoá cho provider này rồi "
            "tạo đoạn chat mới."
        )
    return GENERIC_FAILURE_MESSAGE


def _is_cancelled(db: Session, message_id) -> bool:
    """Re-query trực tiếp cột status thay vì đọc từ object ORM đang giữ trong bộ nhớ -
    endpoint /cancel chạy ở process API khác với worker này nên object đang giữ có thể
    đã cũ."""
    status = (
        db.query(ChatMessage.status).filter(ChatMessage.id == message_id).scalar()
    )
    return status == "cancelled"


def _brain_has_chunks(db: Session, brain_id) -> bool:
    """Brain chưa có tài liệu nào thì bỏ qua hẳn bước retrieval.

    ``search_chunks`` luôn gọi API embedding cho câu hỏi trước khi truy vấn - với brain
    rỗng thì đó là một round-trip mạng nằm chắn ngay trước token đầu tiên mà chắc chắn
    không trả về kết quả nào.
    """
    try:
        return bool(db.execute(
            text(
                "SELECT 1 FROM document_chunks dc "
                "JOIN vault_revisions vr ON dc.revision_id = vr.id "
                "JOIN vault_documents vd ON vr.document_id = vd.id "
                "WHERE vd.brain_id = :brain_id AND vd.status = 'active' LIMIT 1"
            ),
            {"brain_id": str(brain_id)},
        ).scalar())
    except Exception:
        # Không chặn lượt trả lời chỉ vì câu kiểm tra phụ này hỏng.
        return True


async def _retrieve_context(db: Session, brain_id, query: str) -> list:
    if not _brain_has_chunks(db, brain_id):
        return []
    try:
        from app.modules.vault.retrieval_service import search_chunks

        return await search_chunks(db, brain_id, query)
    except Exception:
        logger.warning("Retrieval thất bại, trả lời không kèm ngữ cảnh", exc_info=True)
        return []


def _get_active_connectors_prompt(db: Session, workspace_id) -> str:
    """Nói với model những gì nó THỰC SỰ làm được, không hơn.

    Bản trước dặn model "hãy trích xuất và hiển thị 3 email cụ thể" trong khi không hề đưa
    cho nó tool nào - model ngoan thì từ chối, model chiều lòng người thì bịa ra thư giả.
    Giờ khả năng đọc thư đến từ TOOL (gmail_tools), còn prompt chỉ mô tả bối cảnh.
    """
    try:
        connectors = db.query(MCPConnection).filter(
            MCPConnection.workspace_id == workspace_id
        ).all()
        if not connectors:
            return ""

        info = ["\n\n[KẾT NỐI ĐANG BẬT TRONG WORKSPACE]"]
        gmail_ready = has_usable_google_connection(db, workspace_id)
        for c in connectors:
            config = c.config_jsonb or {}
            if config.get("type") == GOOGLE_CONNECTOR_TYPE:
                if gmail_ready:
                    info.append(
                        f"- Gmail {config.get('email', '')}: dùng tool gmail_list_messages / "
                        "gmail_get_message để đọc thư thật. Tuyệt đối không bịa nội dung thư; "
                        "chưa gọi tool thì chưa biết gì về hòm thư. Khi soạn thư, dùng "
                        "gmail_prepare_email - thư chỉ là bản nháp chờ người dùng bấm duyệt, "
                        "bạn không có cách nào tự gửi thư đi."
                    )
                else:
                    info.append(
                        f"- {c.name}: đã tạo nhưng CHƯA đăng nhập Google nên không đọc được "
                        "thư. Nếu người dùng hỏi về email, hãy bảo họ vào mục Kết nối bấm "
                        "'Đăng nhập Google' để cấp quyền."
                    )
            elif "zalo" in c.name.lower():
                info.append(f"- {c.name}: đã kết nối Zalo (chưa có tool đọc/gửi trong chat).")
        return "\n".join(info)
    except Exception:
        return ""


def _tools_for(db: Session, workspace_id, provider: str, model: str) -> list:
    """Chỉ đính tool khi vừa có kết nối dùng được VỪA có model biết gọi tool.

    Gửi tools cho model không hỗ trợ thì provider trả 400 và hỏng cả lượt chat - thà không
    có tool và trả lời thành thật là chưa đọc được thư.
    """
    if not has_usable_google_connection(db, workspace_id):
        return []
    entry = get_model(provider, model)
    if entry and not entry.supports_tools:
        logger.info("Model %s/%s không hỗ trợ tool nên bỏ qua tool Gmail", provider, model)
        return []
    return gmail_tools.TOOL_SPECS


async def _execute_turn(
    db: Session,
    router: AIRouter,
    publisher: ChatEventPublisher,
    user_message_id,
) -> None:
    """Chạy trọn một lượt hỏi-đáp. Nạp lại mọi thứ theo id vì Session ở đây có thể là
    session riêng của lượt này (chế độ chạy song song), không phải session đã claim."""
    user_message = db.query(ChatMessage).filter(ChatMessage.id == user_message_id).first()
    if not user_message:
        return

    session = db.query(ChatSession).filter(ChatSession.id == user_message.session_id).first()
    if not session:
        user_message.status = "error"
        db.commit()
        return

    brain = db.query(Brain).filter(Brain.id == session.brain_id).first()
    if not brain:
        user_message.status = "error"
        db.commit()
        return

    provider_name = session.provider or DEFAULT_PROVIDER
    model_name = session.model or DEFAULT_MODEL

    assistant = ChatMessage(
        session_id=session.id,
        role="assistant",
        content="",
        status="streaming",
        client_message_id=str(uuid.uuid4()),
    )
    run = AIRun(
        workspace_id=brain.workspace_id,
        chat_session_id=session.id,
        chat_message_id=user_message.id,
        provider=provider_name,
        model=model_name,
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(assistant)
    db.add(run)
    db.commit()

    # Báo ngay id của bong bóng trả lời để client dựng khung "đang soạn" trước cả token
    # đầu tiên, thay vì đợi retrieval + provider xong mới thấy gì.
    publisher.status(session.id, assistant.id, "streaming", 0)

    content = ""
    try:
        citations = await _retrieve_context(db, brain.id, user_message.content)
        assistant.citations = citations

        context = ""
        if citations:
            context = "\n\nRelevant Context:\n" + "\n---\n".join([c['text'] for c in citations])

        connectors_prompt = _get_active_connectors_prompt(db, brain.workspace_id)
        system_content = SYSTEM_PROMPT_VI + connectors_prompt

        chat_turns = [
            ChatTurn(role="system", content=system_content),
            ChatTurn(role="user", content=user_message.content + context),
        ]

        cancelled = False
        last_commit = time.monotonic()
        last_cancel_check = 0.0
        tools = _tools_for(db, brain.workspace_id, provider_name, model_name)

        failed_event = None
        answered = False
        input_tokens = 0
        output_tokens = 0

        # Vòng lặp tool: model xin gọi tool -> ta chạy -> trả kết quả -> model nói tiếp.
        # Có trần vòng vì model hoàn toàn có thể xin gọi tool mãi không dừng, và mỗi vòng
        # là một lần trả tiền cho cả hội thoại đang dài dần.
        for round_index in range(MAX_TOOL_ROUNDS + 1):
            pending_calls = []
            round_content = ""

            async for event in router.stream_chat(
                chat_turns, provider_name, model_name, tools=tools or None
            ):
                now = time.monotonic()
                if now - last_cancel_check >= CANCEL_CHECK_INTERVAL_SECONDS:
                    last_cancel_check = now
                    if _is_cancelled(db, assistant.id):
                        cancelled = True
                        break

                if event.kind == "delta":
                    # Đẩy đi trước, ghi DB sau: client thấy token ngay, DB chỉ cần bắt kịp
                    # trước khi lượt này kết thúc.
                    publisher.delta(session.id, assistant.id, len(content), event.content)
                    content += event.content
                    round_content += event.content
                    if now - last_commit >= CONTENT_COMMIT_INTERVAL_SECONDS:
                        assistant.content = content
                        db.commit()
                        last_commit = now
                elif event.kind == "tool_call":
                    pending_calls.append(event.tool_call)
                elif event.kind == "completed":
                    input_tokens += event.input_tokens or 0
                    output_tokens += event.output_tokens or 0
                elif event.kind == "failed":
                    failed_event = event
                    break

            if cancelled or failed_event:
                break

            if not pending_calls:
                answered = True
                break

            if round_index >= MAX_TOOL_ROUNDS:
                # Hết lượt mà model vẫn đòi gọi tool: dừng hẳn thay vì gọi vô hạn.
                content += (
                    "\n\nTôi đã tra cứu nhiều lần nhưng chưa khép lại được yêu cầu này. "
                    "Bạn thử hỏi cụ thể hơn giúp tôi nhé."
                )
                answered = True
                break

            # Phát lại nguyên văn lượt xin gọi tool rồi tới kết quả: provider đối chiếu
            # tool_call_id giữa hai lượt, thiếu một vế là nó từ chối cả hội thoại.
            chat_turns.append(
                ChatTurn(
                    role="assistant",
                    content=round_content,
                    tool_calls=tuple(pending_calls),
                )
            )
            for call in pending_calls:
                logger.info("Chat gọi tool %s", call.name)
                result = await gmail_tools.execute_tool(
                    db, brain.workspace_id, session.id, call.name, call.arguments
                )
                chat_turns.append(
                    ChatTurn(role="tool", content=result, tool_call_id=call.id)
                )

        if failed_event is not None:
            assistant.content = _failure_message(
                failed_event.error_code, provider_name, model_name
            )
            assistant.status = "error"
            user_message.status = "error"
            run.status = "failed"
            run.error_code = failed_event.error_code
            run.finished_at = datetime.utcnow()
            db.commit()
            publisher.status(session.id, assistant.id, "error", len(assistant.content))
        elif answered:
            assistant.content = content
            assistant.status = "delivered"
            user_message.status = "processed"
            run.status = "completed"
            run.input_tokens = input_tokens or None
            run.output_tokens = output_tokens or None
            run.finished_at = datetime.utcnow()
            session.last_message_at = datetime.utcnow()
            db.commit()
            publisher.status(session.id, assistant.id, "delivered", len(content))

        if cancelled:
            # Giữ lại phần đã sinh được thay vì vứt đi - người dùng bấm dừng chứ không
            # phải muốn xoá.
            assistant.content = content
            run.status = "cancelled"
            run.finished_at = datetime.utcnow()
            user_message.status = "processed"
            db.commit()
            publisher.status(session.id, assistant.id, "cancelled", len(content))
    except Exception:
        logger.exception("Lượt chat thất bại")
        db.rollback()
        assistant.content = GENERIC_FAILURE_MESSAGE
        assistant.status = "error"
        user_message.status = "error"
        run.status = "failed"
        run.error_code = "provider_unavailable"
        run.finished_at = datetime.utcnow()
        db.commit()
        publisher.status(session.id, assistant.id, "error", len(assistant.content))


def claim_pending_messages(db: Session, limit: int) -> list:
    """Giành lấy tối đa ``limit`` message user đang chờ và trả về id của chúng.

    Đổi status sang "processing" rồi commit NGAY, trước khi chạy bất cứ lượt nào: vòng
    lặp worker giờ quay lại tìm việc liên tục chứ không ngủ giữa các vòng, nên nếu chưa
    commit thì nó sẽ nhặt lại đúng message đang xử lý dở.
    """
    if limit <= 0:
        return []

    pending = (
        db.query(ChatMessage)
        .filter(ChatMessage.role == "user", ChatMessage.status == "sent")
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
        .all()
    )
    if not pending:
        return []

    pending_ids = [message.id for message in pending]
    for message in pending:
        message.status = "processing"
    db.commit()
    return pending_ids


async def run_turn(
    session_factory,
    router: AIRouter,
    publisher: ChatEventPublisher,
    message_id,
) -> None:
    """Chạy một lượt trên Session riêng của nó, không bao giờ ném ra ngoài.

    Worker chạy hàm này như một task độc lập, nên một lượt hỏng không được phép kéo theo
    vòng lặp chat.
    """
    db = session_factory()
    try:
        await _execute_turn(db, router, publisher, message_id)
    except Exception:
        logger.exception("Lượt chat thoát bất thường")
    finally:
        db.close()


async def process_pending_chat_messages(
    db: Session,
    router: AIRouter,
    publisher: ChatEventPublisher | None = None,
    max_concurrency: int = 4,
) -> int:
    """Nhận và chạy tuần tự các message đang chờ trên cùng ``db``.

    Dùng cho test và script offline. Worker thật KHÔNG dùng hàm này: nó chờ cả mẻ chạy
    xong mới quay lại tìm việc, nên message đến giữa chừng phải đợi cả mẻ trước đó -
    xem ``claim_pending_messages`` + ``run_turn`` trong worker_main.
    """
    publisher = publisher or NullChatEventPublisher()

    pending_ids = claim_pending_messages(db, max_concurrency)
    for message_id in pending_ids:
        await _execute_turn(db, router, publisher, message_id)
    return len(pending_ids)
