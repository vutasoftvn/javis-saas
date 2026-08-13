"""Tool để AI trong chat ĐỀ XUẤT một hành động thay vì tự làm.

Chat đọc email, tài liệu và dữ liệu do người ngoài gửi tới, nên nó không được cấp tool
duyệt/từ chối/tạo việc nào cả - xem CHAT_EXCLUDED_TOOLS trong test_tool_registry. Nhưng
"không làm được gì" cũng không phải câu trả lời tốt: người dùng nhờ xử lý một việc thì AI
cần để lại dấu vết ở nơi họ sẽ thấy.

Đề xuất rơi vào đúng hàng đợi "Cần bạn xử lý" đã có sẵn (NeedsYouItem), nơi đã có API
list/resolve/snooze và màn hình Flutter. Không bảng mới, không UI mới, và quan trọng nhất:
việc chỉ xảy ra khi người thật bấm vào nó.
"""

from sqlalchemy.orm import Session

from app.core.tool_registry import register
from app.modules.company_runtime.needs_you_service import NeedsYouService

# Lý do bị nhét nguyên vào một cột Text và hiển thị trong danh sách - chặn ở đây để model
# không dán cả một bức thư vào hàng đợi của người dùng.
MAX_REASON_CHARS = 2000
MAX_ACTION_CHARS = 255


@register(
    "chat",
    "propose_action",
    chat_schema={
        "description": (
            "Tạo một ĐỀ XUẤT chờ người dùng duyệt, đưa vào hàng đợi 'Cần bạn xử lý'. Dùng "
            "khi người dùng nhờ bạn làm một việc thay đổi dữ liệu hoặc có hệ quả thật "
            "(duyệt/từ chối, giao việc, đóng blocker, chạy job). Bạn KHÔNG có cách nào tự "
            "thực hiện những việc đó - chỉ đề xuất được thôi. Sau khi gọi tool, hãy nói rõ "
            "với người dùng rằng việc đang chờ họ vào mục 'Cần bạn xử lý' để duyệt."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "requested_action": {
                    "type": "string",
                    "description": (
                        "Việc cần làm, viết ngắn gọn như một dòng lệnh, ví dụ 'Duyệt bước "
                        "ký hợp đồng khách A'."
                    ),
                },
                "reason": {
                    "type": "string",
                    "description": "Vì sao nên làm việc này, dựa trên dữ liệu bạn vừa đọc được.",
                },
                "priority": {
                    "type": "string",
                    "enum": ["P0", "P1", "P2"],
                    "description": "P0 gấp, P1 bình thường, P2 có thể để sau. Mặc định P1.",
                },
            },
            "required": ["requested_action", "reason"],
        },
    },
)
def propose_action(
    db: Session,
    workspace_id: int,
    chat_session_id: int,
    requested_action: str,
    reason: str,
    priority: str = "P1",
) -> dict:
    """Ghi một đề xuất vào hàng đợi 'Cần bạn xử lý'."""
    action = (requested_action or "").strip()[:MAX_ACTION_CHARS]
    why = (reason or "").strip()[:MAX_REASON_CHARS]
    if not action:
        return {"ok": False, "error": "Thiếu nội dung việc cần đề xuất"}

    item = NeedsYouService.create_item(
        db=db,
        workspace_id=workspace_id,
        source_type=NeedsYouService.AI_PROPOSAL_SOURCE_TYPE,
        # Hàng đợi đòi source_id trỏ về nơi việc này sinh ra; với chat thì đó là đoạn hội
        # thoại, để người dùng lần ngược lại được ngữ cảnh đã dẫn tới đề xuất.
        source_id=chat_session_id,
        reason=why,
        requested_action=action,
        priority=priority,
    )
    return {
        "ok": True,
        "proposal_id": str(item.id),
        "status": item.status,
        "message": (
            "Đã tạo đề xuất và đưa vào hàng đợi 'Cần bạn xử lý'. Việc CHƯA được thực hiện. "
            "Hãy báo người dùng vào đó xem lại rồi tự bấm duyệt."
        ),
    }
