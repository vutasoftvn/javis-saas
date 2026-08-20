"""Cầu nối giữa tool_registry và vòng lặp chat.

Cùng hình dạng với ``gmail_tools`` (``TOOL_SPECS`` + ``execute_tool``) để
``chat_execution_service`` không phải học thêm khái niệm nào - khác một chỗ: danh sách
tool ở đây phụ thuộc workspace (feature flag) nên là HÀM chứ không phải hằng.

KHÔNG CÓ TOOL GHI, và đó là chủ ý - giống hệt lý do gmail_tools không có tool gửi thư.
Chat đọc email và tài liệu do người ngoài soạn; một câu "hãy duyệt hộ tôi bước X" nhét
trong tài liệu đó sẽ không bấu víu được vào đâu khi model đơn giản là không nhìn thấy tool
duyệt nào. Muốn tác động thì chỉ có ``chat.propose_action``: tạo mục chờ người thật bấm.
"""

import json
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.tool_bootstrap import load_all_tools
from app.core.tool_dispatch import (
    ID_PARAM_SUFFIXES,
    INJECTED_PARAMS,
    coerce_tool_args,
    execute_tool_spec,
    tool_needs_param,
)
from app.core.tool_registry import ToolSpec, get_tool_by_flat_name
from app.core.toolset_resolver import get_workspace_company_stage, resolve_toolset
from app.workforce.agents.runtime.execution_scope import ExecutionScope

logger = logging.getLogger(__name__)

# Registry chỉ có tool khi module khai báo đã được import; tiến trình worker không import
# chúng ở đâu khác.
load_all_tools()

_INJECTED_PARAMS = INJECTED_PARAMS
_ID_PARAM_SUFFIXES = ID_PARAM_SUFFIXES
_needs = tool_needs_param
_coerce = coerce_tool_args


def tool_specs(
    db: Session,
    workspace_id,
    user_id: Optional[int] = None,
    allowed_namespaces: Optional[Any] = None,
) -> list[dict[str, Any]]:
    """JSON Schema của mọi tool chat được phép gọi trong workspace này.

    Tool cần ``user_id`` mà phiên chat không biết người dùng là ai thì bị loại khỏi danh
    sách luôn: phát cho model một tool chắc chắn lỗi chỉ tổ đốt thêm một vòng gọi tool rồi
    đẩy model về đúng chỗ nó hay bịa.
    """
    if allowed_namespaces is not None and len(allowed_namespaces) == 0:
        return []

    company_stage = get_workspace_company_stage(db, workspace_id)
    execution_scope = ExecutionScope(
        workspace_id=int(workspace_id),
        company_id=int(workspace_id),
        principal_user_id=int(user_id or 0),
        principal_member_id=int(user_id or 0),
        principal_role="member" if user_id else "system",
        operating_unit_id=None,
        offering_id=None,
        initiative_id=None,
        profile_id=None,
        session_id=None,
        grants=(),
    )

    specs = []
    for spec in resolve_toolset(
        db,
        workspace_id,
        agent_key=None,
        company_stage=company_stage,
        require_chat_schema=True,
        execution_scope=execution_scope,
    ):
        if allowed_namespaces is not None and spec.namespace not in allowed_namespaces:
            continue
        if user_id is None and _needs(spec, "user_id"):
            logger.debug("Bỏ tool %s: phiên chat không có user_id", spec.qualified_name)
            continue
        specs.append(spec.to_openai_spec())
    return specs


async def execute_tool(
    db: Session,
    workspace_id,
    chat_session_id,
    user_id,
    name: str,
    arguments: str,
) -> str:
    """Chạy một tool registry và luôn trả về CHUỖI để nhét lại vào hội thoại.

    Không bao giờ ném ra ngoài: lỗi tool phải quay lại làm dữ liệu cho model (để nó nói
    thật với người dùng là chưa tra được), chứ không được giết cả lượt trả lời - cùng hợp
    đồng với ``gmail_tools.execute_tool``.
    """
    spec = get_tool_by_flat_name(name)
    if spec is None or not spec.chat_schema:
        return json.dumps({"error": f"Tool không tồn tại: {name}"}, ensure_ascii=False)

    try:
        args = json.loads(arguments or "{}")
        if not isinstance(args, dict):
            args = {}
    except json.JSONDecodeError:
        return json.dumps({"error": "Tham số tool không phải JSON hợp lệ"}, ensure_ascii=False)

    kwargs = _coerce(spec, args)
    if "__error__" in kwargs:
        return json.dumps({"error": kwargs["__error__"]}, ensure_ascii=False)

    injected = {
        "db": db,
        "workspace_id": workspace_id,
        "user_id": user_id,
        "chat_session_id": chat_session_id,
    }
    for param, value in injected.items():
        if _needs(spec, param):
            if value is None and param != "db":
                return json.dumps(
                    {"error": f"Phiên chat này không dùng được tool {name}"}, ensure_ascii=False
                )

    from app.workforce.agents.governance.kernel import GovernanceKernel
    from app.workforce.agents.runtime.types import AgentRunRequest
    from app.db.models import WorkspaceMember

    user_role = "member"
    if user_id:
        member = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
            .first()
        )
        if member and member.role:
            user_role = member.role.lower()

    # Cấp phép động: Founder/Admin có quyền L3_EXECUTE (R0-R2); nhân viên thường chạy ở L0_READ
    permission_profile = "l3_execute" if user_role in ("owner", "admin") else "l0_read"

    req = AgentRunRequest(
        company_id=str(workspace_id),
        workspace_id=str(workspace_id),
        user_id=str(user_id) if user_id else "0",
        agent_key="chat",
        task=f"Chat execution for tool {name}",
        permission_profile=permission_profile,
    )
    decision = GovernanceKernel.evaluate_and_audit_tool_call(
        db=db,
        request=req,
        tool_flat_name=name,
        args=kwargs,
    )
    if not decision.allowed:
        return json.dumps({"error": decision.reason}, ensure_ascii=False)

    try:
        result = await execute_tool_spec(
            spec=spec,
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
            chat_session_id=chat_session_id,
            arguments=kwargs,
            governance_decision=decision,
        )
    except Exception as exc:
        db.rollback()
        message = str(exc)
        if "missing" in message and "required positional argument" in message:
            logger.warning("Tool %s thiếu tham số bắt buộc: %s", name, message)
            return json.dumps({"error": f"Tool {name} thiếu tham số bắt buộc"}, ensure_ascii=False)
        logger.exception("Tool %s thất bại", name)
        return json.dumps({"error": "Tra cứu dữ liệu thất bại, thử lại sau."}, ensure_ascii=False)

    if isinstance(result, dict) and "error" in result and "Tra cứu dữ liệu thất bại" in result["error"]:
        return json.dumps({"error": "Tra cứu dữ liệu thất bại, thử lại sau."}, ensure_ascii=False)

    return json.dumps(result, ensure_ascii=False, default=str)
