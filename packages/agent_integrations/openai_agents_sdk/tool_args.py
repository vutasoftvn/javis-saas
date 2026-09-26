"""Xử lý đầu vào tool ở biên kernel: (1) lỗi đầu vào (HTTP 400/404/409/422,
JSON args hỏng, ToolInputError) trả về cho model như kết quả tool để nó tự sửa
và gọi lại — không làm cả run thất bại; (2) lỗi runtime có kiểu
(AgentRuntimeError: denied, waiting_approval, ...), 401/403, 5xx và ValueError
nội bộ vẫn phải ném ra như cũ."""

from __future__ import annotations

import json
from typing import Any

from agent.contracts.errors import AgentRuntimeError

__all__ = ["ToolInputError", "apply_run_scope", "input_error_payload", "tool_input_error_result"]

# Chỉ các mã "đầu vào sai" — 401/403 (quyền) và 429/5xx không phải lỗi model tự sửa được.
_INPUT_ERROR_STATUSES = frozenset({400, 404, 409, 422})


class ToolInputError(ValueError):
    """Đầu vào tool do model sinh ra không hợp lệ (vd. project_id lệch scope)."""


def input_error_payload(detail: str) -> dict[str, Any]:
    return {"error": detail, "hint": "Fix the arguments and call the tool again."}


def tool_input_error_result(exc: BaseException | None) -> dict[str, Any] | None:
    if exc is None or isinstance(exc, AgentRuntimeError):
        return None
    status = getattr(exc, "status_code", None)
    if isinstance(exc, (ToolInputError, json.JSONDecodeError)) or (
        isinstance(status, int) and status in _INPUT_ERROR_STATUSES
    ):
        detail = getattr(exc, "detail", None) or str(exc)
        return input_error_payload(str(detail))
    return None


def apply_run_scope(
    args: dict[str, Any], input_schema: dict[str, Any] | None, context: dict[str, Any]
) -> dict[str, Any]:
    """Tự điền `project_id` từ scope của run (đã verify ở backend) để model
    không phải chép/bịa ID; ID khác project của run bị chặn (không đọc chéo
    project)."""
    scoped = context.get("project_id")
    props = (input_schema or {}).get("properties") or {}
    if not scoped or "project_id" not in props:
        return args
    given = args.get("project_id")
    if given in (None, ""):
        return {**args, "project_id": scoped}
    if str(given) != str(scoped):
        raise ToolInputError("project_id không khớp project của phiên hiện tại")
    return args
