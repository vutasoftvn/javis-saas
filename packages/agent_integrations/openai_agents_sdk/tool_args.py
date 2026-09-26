"""Xử lý đầu vào tool ở biên kernel: (1) lỗi validate đầu vào (4xx/ValueError)
trả về cho model như kết quả tool để nó tự sửa và gọi lại — không làm cả run
thất bại; (2) lỗi runtime có kiểu (AgentRuntimeError: denied, waiting_approval,
...) và 5xx vẫn phải ném ra như cũ."""

from __future__ import annotations

from typing import Any

from agent.contracts.errors import AgentRuntimeError

__all__ = ["tool_input_error_result"]


def tool_input_error_result(exc: Exception) -> dict[str, Any] | None:
    if isinstance(exc, AgentRuntimeError):
        return None
    status = getattr(exc, "status_code", None)
    if isinstance(exc, ValueError) or (isinstance(status, int) and 400 <= status < 500):
        detail = getattr(exc, "detail", None) or str(exc)
        return {
            "error": str(detail),
            "hint": "Fix the arguments and call the tool again.",
        }
    return None
