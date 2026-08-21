import logging
import time
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from workforce.agents.orchestrator.command import CommandCategory, OrchestratorRequest
from workforce.agents.orchestrator.service import WorkOrchestratorService
from db.models import AIRun, Brain, ChatMessage, ChatSession, MCPConnection
from workforce.chat import company_tools, conversation_gate, gmail_tools
from workforce.chat.ai_router import AIRouter, ChatTurn
from workforce.chat.chat_stream_bus import ChatEventPublisher, NullChatEventPublisher
from workforce.chat.conversation_gate import GateDecision, GateIntent
from workforce.chat.model_registry import DEFAULT_MODEL, DEFAULT_PROVIDER, get_model
from workforce.chat.models import ONESHOT_PURPOSE
from platform_core.license.intent_classifier import WorkIntentClassifier
from integrations.channels.google.google_connection_service import (
    CONNECTOR_TYPE as GOOGLE_CONNECTOR_TYPE,
    has_usable_google_connection,
)
from founder_os.strategy.models import Project
from founder_os.strategy.services.stage_resolver_service import StageResolverService
from founder_os.strategy.services.stage_gate_service import StageGateService
from founder_os.strategy.next_best_action_service import NextBestActionService
from workforce.ai.prompt_registry import PromptRegistry
from core.feature_flags import FLAG_CONVERSATION_GATE_V13_2, is_enabled
from core.snowflake import generate_snowflake_id
from integrations.llm_providers._openai_compatible import cleanse_text_content

logger = logging.getLogger(__name__)

# Luật chống bịa. Model được huấn luyện để luôn có câu trả lời, nên hỏi "OKR của tôi thế
# nào" mà không có dữ liệu thì nó dựng ra một bộ OKR nghe rất hợp lý - người dùng không có
# cách nào phân biệt với số thật. Nói thẳng ranh giới: chưa gọi tool là chưa biết gì.
GROUNDING_PROMPT = (
    "\n\n[DỮ LIỆU CÔNG TY]\n"
    "Bạn có tool đọc & lưu dữ liệu THẬT của workspace này: dự án, OKR, task, blocker, việc cần "
    "duyệt, tài chính, chu kỳ và Knowledge Vault. Quy tắc bắt buộc:\n"
    "- Mọi con số, tên dự án, tên OKR, trạng thái công việc chỉ được lấy từ kết quả tool. "
    "Chưa gọi tool thì bạn CHƯA BIẾT GÌ về workspace này.\n"
    "- Tuyệt đối không suy đoán, không lấy ví dụ minh hoạ thay cho dữ liệu thật, không "
    "dựng ra dự án hay chỉ số 'cho dễ hình dung'.\n"
    "- Tool trả về rỗng thì nói thẳng là workspace chưa có dữ liệu đó, và gợi ý người dùng "
    "tạo. Đó là câu trả lời đúng, không phải thất bại.\n"
    "- Người dùng hỏi về dự án, OKR hay công việc: gọi tool tra cứu danh sách trước để "
    "lấy thông tin và id chính xác, rồi mới xem chi tiết. Tuyệt đối không tự đoán id.\n"
    "- Khi người dùng hỏi về tiến độ, trạng thái dự án, dự án đang ở giai đoạn nào: "
    "gọi tool list_projects để lấy ID dự án, sau đó gọi tool get_project_roadmap để đọc trạng thái Live "
    "từ cơ sở dữ liệu (xem giai đoạn nào ACTIVE, giai đoạn nào chỉ mới CONFIRMED chưa kích hoạt, giai đoạn nào COMPLETED). "
    "Tuyệt đối không tự suy diễn trạng thái từ tài liệu văn bản RAG tĩnh.\n"
    "- Khi người dùng chất vấn, nghi ngờ, hỏi lại tính chính xác ('bạn kiểm tra dữ liệu hay bịa đó?', 'kiểm tra lại chưa', 'thật không?'): "
    "BẮT BUỘC phải gọi tool kiểm tra trực tiếp vào cơ sở dữ liệu để đối soát lại dữ liệu live thật trước khi trả lời, "
    "không được chỉ dựa vào lịch sử chat hay văn bản tham khảo tĩnh để khẳng định bừa.\n"
    "- Định dạng tài liệu tri thức & kế hoạch theo chuẩn Obsidian Markdown (.md) với YAML Frontmatter "
    "và liên kết hai chiều [[wikilinks]] (vd: [[projects/mid/roadmap]], [[strategy/12wy/2026-Q3_12wy]]).\n"
    "- Khi người dùng yêu cầu 'lưu vào data', 'lưu vào vault', 'xác nhận lộ trình' hoặc 'lưu kế hoạch này':\n"
    "  + Nếu là lộ trình/giai đoạn dự án: gọi ngay tool project_save_and_confirm_roadmap kèm các giai đoạn (stages) "
    "để lưu và xác nhận trực tiếp vào cơ sở dữ liệu.\n"
    "  + Nếu là tài liệu tri thức, kế hoạch 12WY, đặc tả hoặc báo cáo: gọi tool vault_save_document để lưu tài liệu "
    "Markdown (.md) chuẩn Obsidian vào Knowledge Vault ('projects/{code}/roadmaps/YYYY-MM-DD_{title}.md' hoặc 'strategy/12wy/YYYY-WW_{title}.md').\n"
    "  + Sau khi gọi tool thành công, thông báo rõ ràng dữ liệu đã được lưu thành công vào hệ thống.\n"
    "- Với các hành động khác cần phê duyệt cấp cao, hãy dùng chat_propose_action để tạo đề xuất. Tuyệt đối không tự nhận là đã lưu nếu chưa gọi tool thành công.\n"
    "- Tool và tên hàm là chi tiết triển khai nội bộ: đừng nhắc tên hàm trong câu trả lời. Chỉ nói kết quả bạn tìm được hoặc đã lưu, bằng ngôn ngữ tự nhiên."
)

# Khi model đang dùng không gọi được tool (xem model_registry.supports_tools) thì nó không
# có đường nào chạm tới dữ liệu. Im lặng để nó tự xoay là đúng công thức tạo ra câu trả lời
# bịa nghe rất thuyết phục.
NO_TOOLS_PROMPT = (
    "\n\n[KHÔNG CÓ QUYỀN TRUY CẬP DỮ LIỆU]\n"
    "Trong phiên này bạn KHÔNG đọc được dữ liệu thật của workspace (dự án, OKR, task, tài "
    "chính). Nếu người dùng hỏi về những thứ đó, hãy nói thẳng là bạn chưa truy cập được "
    "và khuyên họ chọn model khác có hỗ trợ gọi tool trong danh sách model. Tuyệt đối "
    "không đoán hay bịa dữ liệu để lấp chỗ trống."
)

# Dành cho GateIntent.AMBIGUOUS và DOMAIN_JOB-không-có-dispatcher (STRATEGIC/COMPANY_WORK/
# APPROVAL ngoài CYCLE_CHANGE - xem conversation_gate.py). Hai nhánh này không đủ tin cậy để
# cấp tool đọc dữ liệu, nhưng KHÔNG được đối xử như hội thoại phiếm (CONVERSATION_PROMPT
# không có luật chống bịa): câu như "giai đoạn 1 và 2 đã triển khai xong, cập nhật giai đoạn
# 3..." từng lọt qua CONVERSATION_PROMPT và model tự nhận "đã cập nhật thành công" dù chưa
# gọi tool nào. Namespace "chat" luôn được gate mở ở đây nên model có đúng 1 tool:
# chat_propose_action.
UNGROUNDED_ACTION_PROMPT = (
    "\n\n[CHƯA XÁC ĐỊNH RÕ Ý ĐỊNH - KHÔNG CÓ TOOL ĐỌC DỮ LIỆU]\n"
    "Hệ thống chưa phân loại chắc chắn đây là hội thoại thông thường hay một yêu cầu công "
    "việc cụ thể. Bạn KHÔNG có tool đọc dữ liệu thật của workspace trong lượt này (không "
    "biết tên dự án, giai đoạn hay trạng thái thật nào). Quy tắc bắt buộc:\n"
    "- TUYỆT ĐỐI không tự nhận là đã thực hiện, cập nhật, hoàn tất hay xác nhận bất kỳ thay "
    "đổi dữ liệu nào - bạn không có khả năng đó và chưa xác minh được gì.\n"
    "- Nếu người dùng đang báo cáo tiến độ thực tế hoặc nhờ ghi nhận/thay đổi điều gì đó (vd. "
    "'giai đoạn X đã xong', 'cập nhật lộ trình'), hãy gọi chat_propose_action để tạo đề xuất "
    "chờ họ duyệt, rồi nói rõ: bạn đã ghi nhận thành một đề xuất trong mục 'Cần bạn xử lý', "
    "KHÔNG PHẢI là đã áp dụng thay đổi.\n"
    "- Nếu thực sự chỉ là câu hỏi hoặc trò chuyện thông thường, trả lời ngắn gọn, thân thiện, "
    "không cần dùng tool."
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
# Nâng từ 4 lên 6 khi chat có thêm tool dữ liệu công ty: câu hỏi kiểu "dự án Alpha tới đâu"
# tốn 2 vòng chỉ để tra tên -> id, chưa tính vòng đọc thêm OKR/task liên quan.
MAX_TOOL_ROUNDS = 6

# Trước đây mỗi lượt chỉ gửi lên model đúng 1 tin nhắn hiện tại - hỏi "phân tích roadmap dự
# án Alpha" xong yêu cầu "sửa giai đoạn đó vì đã triển khai rồi" (không nhắc lại tên dự án)
# là model coi như chưa từng có cuộc trò chuyện trước đó. Nạp lại các lượt gần nhất để model
# thấy được mạch hội thoại; giới hạn vì mỗi lượt sau đó phải trả tiền lại cho toàn bộ lịch sử
# này, cộng dồn theo phiên chat càng dài.
MAX_HISTORY_MESSAGES = 20


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


def _load_recent_history(db: Session, session_id, before_message_id) -> list:
    """Các lượt user/assistant đã hoàn tất gần nhất của session, trước tin nhắn hiện tại,
    theo thứ tự thời gian tăng dần - đúng thứ tự cần để phát lại thành ChatTurn cho model.

    Bỏ qua lượt lỗi/huỷ/đang stream: đó không phải nội dung một cuộc hội thoại bình thường,
    phát lại chỉ làm model bối rối. Snowflake ID tăng đơn điệu theo thời gian nên so sánh id
    tương đương so sánh created_at mà không cần thêm điều kiện range.
    """
    rows = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.session_id == session_id,
            ChatMessage.id < before_message_id,
            ChatMessage.role.in_(("user", "assistant")),
            ChatMessage.status.in_(("processed", "delivered")),
        )
        .order_by(ChatMessage.created_at.desc())
        .all()
    )
    return list(reversed(rows[:MAX_HISTORY_MESSAGES]))


async def _retrieve_context(db: Session, brain_id, query: str) -> list:
    if not _brain_has_chunks(db, brain_id):
        return []
    try:
        from platform_core.vault.retrieval_service import search_chunks

        return await search_chunks(db, brain_id, query)
    except Exception:
        logger.warning("Retrieval thất bại, trả lời không kèm ngữ cảnh", exc_info=True)
        # search_chunks chạy raw SQL trên chính Session của lượt chat: một câu lỗi để
        # transaction Postgres ở trạng thái aborted, mọi query sau đó trên cùng Session
        # (kể cả không liên quan gì tới retrieval) sẽ ăn theo lỗi InFailedSqlTransaction
        # nếu không rollback ở đây.
        db.rollback()
        return []


def _build_stage_context_prompt_block(db: Session, workspace_id: int, user_id: Optional[int]) -> str:
    """P1.2 (mục 21 tài liệu COSA Stage-Aware, Phase 5 Master Plan): khối
    [PROJECT & STAGE OPERATING CONTEXT] chỉ được chèn khi intent = STAGE_AWARE_CONSULTATION,
    không ép vào mọi lượt chat (AC-13)."""
    stage_context = StageResolverService(db, workspace_id).resolve_context(project_id=None)

    readiness_score: Optional[float] = None
    if stage_context.project_id:
        history = StageGateService.get_audit_history(db, workspace_id, stage_context.project_id)
        if history:
            readiness_score = round(history[0].readiness_score * 100)

    next_actions_text = "Chưa có dữ liệu Next Best Action."
    try:
        top_actions = NextBestActionService(db, workspace_id, user_id or 0).get_top_next_actions(limit=3)
        if top_actions:
            next_actions_text = "; ".join(a["title"] for a in top_actions)
    except Exception:
        logger.warning("Không lấy được Next Best Actions cho Stage context prompt", exc_info=True)

    policy = stage_context.policy
    constraints_text = (
        ", ".join(stage_context.critical_constraints) if stage_context.critical_constraints else "Chưa xác định"
    )

    return (
        "\n\n[PROJECT & STAGE OPERATING CONTEXT]\n"
        f"Project: {stage_context.project_title or 'Chưa xác định'} | Stage: {policy.stage_name_vi} ({policy.code})\n"
        f"Primary Goal: {stage_context.stage_goal or policy.primary_goal}\n"
        f"Critical Constraints / Blockers: {constraints_text}\n"
        f"Readiness Score: {readiness_score if readiness_score is not None else 'N/A'}%\n"
        f"Policy Guidance: Focus on {', '.join(policy.recommended_methods)}. Deemphasize {', '.join(policy.deemphasized_tools)}.\n"
        f"Top 3 Next Actions: {next_actions_text}"
    )


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


def _tools_for(
    db: Session,
    workspace_id,
    provider: str,
    model: str,
    user_id,
    allowed_namespaces: Optional[Any] = None,
) -> list:
    """Bộ tool cho một lượt chat: dữ liệu công ty LUÔN có, Gmail chỉ khi đã nối được.

    Gửi tools cho model không hỗ trợ thì provider trả 400 và hỏng cả lượt chat - đó là lý
    do duy nhất danh sách này được phép rỗng.

    Trước đây hàm này thoát sớm khi chưa nối Gmail, nên workspace không dùng Gmail thì
    model không có một tool nào: hỏi dự án hay OKR là nó chỉ còn cách tự nghĩ ra câu trả
    lời. Tool công ty không phụ thuộc kết nối ngoài nào cả.
    """
    entry = get_model(provider, model)
    if entry and not entry.supports_tools:
        logger.info("Model %s/%s không gọi được tool nên lượt này không có tool", provider, model)
        return []

    tools = company_tools.tool_specs(
        db, workspace_id, user_id, allowed_namespaces=allowed_namespaces
    )
    if (allowed_namespaces is None or "gmail" in allowed_namespaces or "tasks" in allowed_namespaces) and has_usable_google_connection(db, workspace_id):
        tools = tools + gmail_tools.TOOL_SPECS
    return tools


async def _run_tool(db: Session, workspace_id, session, call) -> str:
    """Định tuyến một lần gọi tool về đúng nơi thực thi."""
    if call.name in gmail_tools.TOOL_NAMES:
        return await gmail_tools.execute_tool(
            db, workspace_id, session.id, call.name, call.arguments
        )
    return await company_tools.execute_tool(
        db, workspace_id, session.id, session.user_id, call.name, call.arguments
    )


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

    assistant_id = generate_snowflake_id()
    run_id = generate_snowflake_id()
    session_id = session.id
    user_msg_id = user_message.id
    workspace_id = brain.workspace_id

    assistant = ChatMessage(
        id=assistant_id,
        session_id=session_id,
        role="assistant",
        content="",
        status="streaming",
        client_message_id=str(generate_snowflake_id()),
    )
    run = AIRun(
        id=run_id,
        workspace_id=workspace_id,
        chat_session_id=session_id,
        chat_message_id=user_msg_id,
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
    publisher.status(session_id, assistant_id, "streaming", 0)

    one_shot = session.purpose == ONESHOT_PURPOSE

    gate_decision: Optional[GateDecision] = None
    # Feature flag gate: nếu không bật hoặc chưa cấu hình thì vẫn có thể chạy gate an toàn
    gate_enabled = is_enabled(db, FLAG_CONVERSATION_GATE_V13_2, workspace_id) if workspace_id else True
    if not one_shot:
        # Resolve Gate Decision cho lượt chat
        gate_decision = conversation_gate.resolve(user_message.content)
        if _dispatch_cycle_change_command(
            db, publisher, workspace_id, session, user_message, assistant, run, gate_decision=gate_decision
        ):
            return

    content = ""
    try:
        # Lượt one-shot mang sẵn toàn bộ dữ liệu trong prompt: thêm đoạn RAG vào chỉ làm
        # loãng yêu cầu định dạng, còn citations thì không ai đọc vì session bị xoá ngay
        # sau khi lấy kết quả.
        # Với non-one-shot: chỉ retrieve context khi gate xác định cần thông tin dự án/ngữ cảnh.
        should_retrieve = not one_shot
        if gate_decision is not None and not gate_decision.needs_project:
            should_retrieve = False

        citations = await _retrieve_context(db, brain.id, user_message.content) if should_retrieve else []
        if citations:
            db.query(ChatMessage).filter(ChatMessage.id == assistant_id).update({
                "citations": citations,
            })
            db.commit()

        context = ""
        if citations:
            context = "\n\nRelevant Context:\n" + "\n---\n".join([c['text'] for c in citations])

        cancelled = False
        last_commit = time.monotonic()
        last_cancel_check = 0.0
        if one_shot:
            tools = []
            system_content = PromptRegistry.get_instance().render_effective(
                db, workspace_id, "cosa", "chat_structured_oneshot", None
            )
        else:
            allowed_namespaces = gate_decision.allowed_namespaces if gate_decision is not None else None
            tools = _tools_for(
                db, workspace_id, provider_name, model_name, session.user_id,
                allowed_namespaces=allowed_namespaces,
            )

            connectors_prompt = _get_active_connectors_prompt(db, workspace_id)
            # Luật chống bịa phải khớp với thứ model thật sự cầm trong tay. AMBIGUOUS/
            # DOMAIN_JOB đi trước "if tools": cả hai chỉ có đúng chat_propose_action (không
            # tool đọc dữ liệu nào), nên GROUNDING_PROMPT (nói "bạn có tool đọc dữ liệu THẬT")
            # sẽ sai với thực tế chúng cầm trong tay - phải dùng prompt riêng.
            prompt_registry = PromptRegistry.get_instance()
            if gate_decision and gate_decision.intent in (GateIntent.AMBIGUOUS, GateIntent.DOMAIN_JOB):
                try:
                    prompt_addon = "\n\n" + prompt_registry.render_effective(
                        db, workspace_id, "cosa", "ungrounded_action", None
                    )
                except Exception:
                    prompt_addon = UNGROUNDED_ACTION_PROMPT
            elif tools:
                try:
                    prompt_addon = "\n\n" + prompt_registry.render_effective(
                        db, workspace_id, "cosa", "grounding", None
                    )
                except Exception:
                    prompt_addon = GROUNDING_PROMPT
            elif gate_decision and gate_decision.intent in (
                GateIntent.SOCIAL_CHAT, GateIntent.GENERAL_QUESTION
            ):
                prompt_addon = "\n\n" + prompt_registry.render_effective(
                    db, workspace_id, "cosa", "chat_conversation", None
                )
            else:
                try:
                    prompt_addon = "\n\n" + prompt_registry.render_effective(
                        db, workspace_id, "cosa", "no_tools", None
                    )
                except Exception:
                    prompt_addon = NO_TOOLS_PROMPT

            system_content = (
                prompt_registry.render_effective(
                    db, workspace_id, "cosa", "chat_language", None
                )
                + prompt_addon
                + connectors_prompt
            )

            # P1.2: chỉ nạp Stage context khi intent đã được conversation_gate xác định rõ
            # là tư vấn chiến lược/next-action (AC-13/AC-14/AC-15) - không ép vào mọi câu chat.
            if gate_decision and gate_decision.intent == GateIntent.STAGE_AWARE_CONSULTATION:
                try:
                    system_content += _build_stage_context_prompt_block(db, workspace_id, session.user_id)
                except Exception:
                    logger.warning("Không dựng được Stage context prompt block", exc_info=True)

        history_turns = []
        if not one_shot:
            history_turns = [
                ChatTurn(role=m.role, content=m.content)
                for m in _load_recent_history(db, session_id, user_msg_id)
            ]

        chat_turns = [
            ChatTurn(role="system", content=system_content),
            *history_turns,
            ChatTurn(role="user", content=user_message.content + context),
        ]

        failed_event = None
        answered = False
        input_tokens = 0
        output_tokens = 0
        executed_proposals = []

        # Vòng lặp tool: model xin gọi tool -> ta chạy -> trả kết quả -> model nói tiếp.
        # Có trần vòng vì model hoàn toàn có thể xin gọi tool mãi không dừng, và mỗi vòng
        # là một lần trả tiền cho cả hội thoại đang dài dần.
        for round_index in range(MAX_TOOL_ROUNDS + 1):
            pending_calls = []
            round_content = ""

            async for event in router.stream_chat(
                chat_turns, provider_name, model_name, tools=tools or None,
                workspace_id=workspace_id,
            ):
                now = time.monotonic()
                if now - last_cancel_check >= CANCEL_CHECK_INTERVAL_SECONDS:
                    last_cancel_check = now
                    if _is_cancelled(db, assistant_id):
                        cancelled = True
                        break

                if event.kind == "delta":
                    # Đẩy đi trước, ghi DB sau: client thấy token ngay, DB chỉ cần bắt kịp
                    # trước khi lượt này kết thúc.
                    publisher.delta(session_id, assistant_id, len(content), event.content)
                    content += event.content
                    round_content += event.content
                    if now - last_commit >= CONTENT_COMMIT_INTERVAL_SECONDS:
                        db.query(ChatMessage).filter(ChatMessage.id == assistant_id).update({
                            "content": content,
                        })
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

            # Nếu model gọi tool trong lượt này, dọn sạch content đã tích luỹ trong lượt
            # để không làm rò rỉ JSON thô hay cú pháp gọi tool vào bong bóng chat của người dùng.
            if pending_calls:
                content = ""
                round_content = ""
                db.query(ChatMessage).filter(ChatMessage.id == assistant_id).update({
                    "content": "",
                })
                db.commit()

            # Phát lại nguyên văn lượt xin gọi tool rồi tới kết quả: provider đối chiếu
            # tool_call_id giữa hai lượt, thiếu một vế là nó từ chối cả hội thoại.
            chat_turns.append(
                ChatTurn(
                    role="assistant",
                    content="",
                    tool_calls=tuple(pending_calls),
                )
            )
            for call in pending_calls:
                logger.info("Chat gọi tool %s", call.name)
                result = await _run_tool(db, workspace_id, session, call)
                if call.name in ("chat_propose_action", "propose_action"):
                    try:
                        res_json = json.loads(result)
                        if isinstance(res_json, dict) and res_json.get("ok"):
                            executed_proposals.append({
                                "id": str(res_json.get("proposal_id")),
                                "requested_action": res_json.get("requested_action") or "",
                                "reason": res_json.get("reason") or "",
                                "priority": res_json.get("priority", "P1"),
                                "status": res_json.get("status", "OPEN"),
                            })
                    except Exception:
                        pass
                chat_turns.append(
                    ChatTurn(role="tool", content=result, tool_call_id=call.id)
                )

        if failed_event is not None:
            err_msg = _failure_message(
                failed_event.error_code, provider_name, model_name
            )
            assistant.content = err_msg
            assistant.status = "error"
            user_message.status = "error"
            try:
                run.status = "failed"
                run.error_code = failed_event.error_code
                run.finished_at = datetime.utcnow()
            except Exception:
                pass
            try:
                db.commit()
            except Exception:
                db.rollback()
                db.query(ChatMessage).filter(ChatMessage.id == assistant_id).update({
                    "content": err_msg,
                    "status": "error",
                })
                db.query(ChatMessage).filter(ChatMessage.id == user_msg_id).update({
                    "status": "error",
                })
                db.commit()
            publisher.status(session_id, assistant_id, "error", len(err_msg))
        elif answered:
            final_content = cleanse_text_content(content)
            assistant.content = final_content
            assistant.status = "delivered"
            if executed_proposals:
                current_citations = assistant.citations if isinstance(assistant.citations, dict) else {}
                current_citations["proposals"] = executed_proposals
                assistant.citations = current_citations
            user_message.status = "processed"
            try:
                run.status = "completed"
                run.input_tokens = input_tokens or None
                run.output_tokens = output_tokens or None
                run.finished_at = datetime.utcnow()
            except Exception:
                pass
            session.last_message_at = datetime.utcnow()

            try:
                db.commit()
            except Exception:
                db.rollback()
                db.query(ChatMessage).filter(ChatMessage.id == assistant_id).update({
                    "content": final_content,
                    "status": "delivered",
                })
                db.query(ChatMessage).filter(ChatMessage.id == user_msg_id).update({
                    "status": "processed",
                })
                db.commit()
            publisher.status(session_id, assistant_id, "delivered", len(final_content))

        if cancelled:
            # Giữ lại phần đã sinh được thay vì vứt đi - người dùng bấm dừng chứ không
            # phải muốn xoá.
            assistant.content = content
            assistant.status = "cancelled"
            user_message.status = "processed"
            try:
                run.status = "cancelled"
                run.finished_at = datetime.utcnow()
            except Exception:
                pass
            try:
                db.commit()
            except Exception:
                db.rollback()
                db.query(ChatMessage).filter(ChatMessage.id == assistant_id).update({
                    "content": content,
                    "status": "cancelled",
                })
                db.query(ChatMessage).filter(ChatMessage.id == user_msg_id).update({
                    "status": "processed",
                })
                db.commit()
            publisher.status(session_id, assistant_id, "cancelled", len(content))
    except Exception:
        logger.exception("Lượt chat thất bại")
        try:
            db.rollback()
            assistant.content = GENERIC_FAILURE_MESSAGE
            assistant.status = "error"
            user_message.status = "error"
            try:
                run.status = "failed"
                run.error_code = "provider_unavailable"
                run.finished_at = datetime.utcnow()
            except Exception:
                pass
            db.commit()
            publisher.status(session_id, assistant_id, "error", len(GENERIC_FAILURE_MESSAGE))
        except Exception:
            try:
                db.rollback()
                db.query(ChatMessage).filter(ChatMessage.id == assistant_id).update({
                    "content": GENERIC_FAILURE_MESSAGE,
                    "status": "error",
                })
                db.query(ChatMessage).filter(ChatMessage.id == user_msg_id).update({
                    "status": "error",
                })
                db.commit()
                publisher.status(session_id, assistant_id, "error", len(GENERIC_FAILURE_MESSAGE))
            except Exception:
                logger.exception("Lỗi khi ghi nhận trạng thái thất bại cho lượt chat")


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


def _dispatch_cycle_change_command(
    db: Session,
    publisher: ChatEventPublisher,
    workspace_id: int,
    session: ChatSession,
    user_message: ChatMessage,
    assistant: ChatMessage,
    run: AIRun,
    gate_decision: Optional[GateDecision] = None,
) -> bool:
    """Rẻ, không tốn AI call: phân loại bằng regex trước khi vào vòng lặp AI+tool. Khớp
    CYCLE_CHANGE thì đi thẳng qua Shared Work Orchestrator (dùng đúng prompt chuyên biệt
    có sẵn cho roadmap/OKR ở agents/proposals) thay vì để general chat model tự bịa JSON.
    Trả về True nếu đã xử lý xong lượt này (caller phải return ngay), False nếu phải đi
    tiếp vào vòng lặp hội thoại thông thường."""
    if gate_decision is not None and gate_decision.raw_classification:
        classification = gate_decision.raw_classification
    else:
        classification = WorkIntentClassifier.classify(user_message.content)

    if classification.get("intent") != "CYCLE_CHANGE":
        return False

    project_hint = classification.get("project_hint")
    if not project_hint:
        # Câu này không tự nhắc tên dự án (vd. "giai đoạn đó tôi đã triển khai rồi") - dò
        # lại lịch sử hội thoại cùng phiên, mới nhất trước, tìm lượt user gần nhất có nhắc
        # tên dự án. Không tra thì sẽ hiểu nhầm thành yêu cầu dựng "Dự án mới".
        for message in reversed(_load_recent_history(db, session.id, user_message.id)):
            if message.role != "user":
                continue
            project_hint = WorkIntentClassifier.extract_project_hint(message.content)
            if project_hint:
                break

    existing_project = None
    if project_hint:
        existing_project = (
            db.query(Project)
            .filter(Project.workspace_id == workspace_id, Project.title.ilike(f"%{project_hint}%"))
            .order_by(Project.created_at.desc())
            .first()
        )

    request = OrchestratorRequest(
        category=CommandCategory.PLAN_CYCLE_COMMAND,
        action="activate_cycle",
        payload={
            "title": project_hint or "Dự án mới",
            "desired_week_count": classification["duration_weeks"],
            "existing_project_id": str(existing_project.id) if existing_project else None,
        },
    )
    response = WorkOrchestratorService.handle_command(
        db=db, workspace_id=workspace_id, user_id=session.user_id, request=request,
    )

    delivered = response.status != "rejected"
    assistant.content = response.message
    assistant.status = "delivered" if delivered else "error"
    user_message.status = "processed" if delivered else "error"
    run.status = "completed" if delivered else "failed"
    run.finished_at = datetime.utcnow()
    db.commit()
    publisher.status(session.id, assistant.id, assistant.status, len(assistant.content))
    return True
