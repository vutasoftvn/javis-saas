"""Tool Gmail cho vòng lặp chat.

KHÔNG CÓ TOOL GỬI THƯ, và đó là chủ ý. Model chỉ soạn được bản nháp kèm một dòng chờ
duyệt; thư chỉ rời hòm thư khi người dùng bấm duyệt qua endpoint có xác thực. Nội dung
email đến là chữ của người lạ - model đọc nó hoàn toàn có thể bị dụ "gửi giúp thư này cho
X". Chặn bằng cấu trúc (không có tool) thì lời dụ đó không có gì để bấu víu, khác hẳn với
chặn bằng câu dặn trong system prompt.
"""

import json
import logging

from sqlalchemy.orm import Session

from db.models import EmailApproval
from integrations.channels.email.gmail_client import GmailError
from integrations.channels.google.google_connection_service import (
    GoogleNotConnected,
    build_gmail_client,
)

logger = logging.getLogger(__name__)

# Mỗi thư là một lần messages.get riêng, và cả 3-5 thư đều bị nhét vào prompt vòng sau.
MAX_MESSAGES_PER_CALL = 10

TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "gmail_list_messages",
            "description": (
                "Đọc danh sách email trong hòm thư Gmail đã kết nối của người dùng, kèm nội "
                "dung từng thư. Dùng khi người dùng hỏi về email/hộp thư/hòm thư của họ, ví "
                "dụ 'tóm tắt 3 email mới nhất', 'có thư nào từ sếp không'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Câu truy vấn theo cú pháp tìm kiếm Gmail, ví dụ 'in:inbox', "
                            "'from:sep@example.com', 'is:unread newer_than:7d'. Để trống "
                            "nghĩa là thư mới nhất trong Inbox."
                        ),
                    },
                    "max_results": {
                        "type": "integer",
                        "description": f"Số thư cần lấy, 1..{MAX_MESSAGES_PER_CALL}. Mặc định 5.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_get_message",
            "description": (
                "Đọc trọn vẹn một email theo id lấy được từ gmail_list_messages. Dùng khi cần "
                "chi tiết hơn phần nội dung đã tóm lược."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message_id": {"type": "string", "description": "id của thư"},
                },
                "required": ["message_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_prepare_email",
            "description": (
                "Soạn một email và lưu thành BẢN NHÁP trong Gmail, đồng thời tạo yêu cầu chờ "
                "người dùng duyệt. Thư KHÔNG được gửi đi cho tới khi người dùng tự bấm nút "
                "duyệt trong ứng dụng - hãy nói rõ điều đó cho họ. Dùng khi người dùng nhờ "
                "viết/trả lời/gửi email."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Địa chỉ người nhận"},
                    "subject": {"type": "string", "description": "Tiêu đề thư"},
                    "body": {"type": "string", "description": "Nội dung thư, viết sẵn hoàn chỉnh"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
]

TOOL_NAMES = {spec["function"]["name"] for spec in TOOL_SPECS}


async def _list_messages(db: Session, workspace_id, args: dict) -> dict:
    raw_max = args.get("max_results") or 5
    try:
        max_results = int(raw_max)
    except (TypeError, ValueError):
        max_results = 5
    max_results = max(1, min(MAX_MESSAGES_PER_CALL, max_results))

    client = await build_gmail_client(db, workspace_id)
    messages = await client.list_messages(
        query=str(args.get("query") or ""), max_results=max_results
    )
    return {
        "count": len(messages),
        "messages": [message.as_prompt_dict() for message in messages],
    }


async def _get_message(db: Session, workspace_id, args: dict) -> dict:
    message_id = str(args.get("message_id") or "").strip()
    if not message_id:
        return {"error": "Thiếu message_id"}
    client = await build_gmail_client(db, workspace_id)
    return (await client.get_message(message_id)).as_prompt_dict()


async def _prepare_email(db: Session, workspace_id, session_id, args: dict) -> dict:
    to = str(args.get("to") or "").strip()
    subject = str(args.get("subject") or "").strip()
    body = str(args.get("body") or "").strip()
    if not to or not body:
        return {"error": "Cần ít nhất người nhận và nội dung thư"}

    client = await build_gmail_client(db, workspace_id)
    draft = await client.create_draft(to=to, subject=subject, body=body)

    approval = EmailApproval(
        workspace_id=workspace_id,
        chat_session_id=session_id,
        draft_id=draft.get("id"),
        to_email=to,
        subject=subject,
        body=body,
        status="pending",
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)

    return {
        "status": "cho_duyet",
        "approval_id": str(approval.id),
        "draft_id": approval.draft_id,
        "message": (
            "Đã lưu bản nháp trong Gmail và tạo yêu cầu chờ duyệt. Thư CHƯA được gửi. "
            "Hãy báo người dùng xem lại rồi bấm duyệt để gửi."
        ),
    }


async def execute_tool(db: Session, workspace_id, session_id, name: str, arguments: str) -> str:
    """Chạy một tool và luôn trả về CHUỖI để nhét lại vào hội thoại.

    Không bao giờ ném ra ngoài: lỗi tool phải quay lại làm dữ liệu cho model (để nó nói lại
    cho người dùng), chứ không được giết cả lượt trả lời.
    """
    try:
        args = json.loads(arguments or "{}")
        if not isinstance(args, dict):
            args = {}
    except json.JSONDecodeError:
        return json.dumps({"error": "Tham số tool không phải JSON hợp lệ"}, ensure_ascii=False)

    try:
        if name == "gmail_list_messages":
            result = await _list_messages(db, workspace_id, args)
        elif name == "gmail_get_message":
            result = await _get_message(db, workspace_id, args)
        elif name == "gmail_prepare_email":
            result = await _prepare_email(db, workspace_id, session_id, args)
        else:
            result = {"error": f"Tool không tồn tại: {name}"}
    except GoogleNotConnected as exc:
        result = {"error": str(exc)}
    except GmailError as exc:
        result = {"error": str(exc)}
    except Exception:
        logger.exception("Tool %s thất bại", name)
        result = {"error": "Gọi Gmail thất bại, thử lại sau."}

    return json.dumps(result, ensure_ascii=False)
