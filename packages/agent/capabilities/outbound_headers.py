from __future__ import annotations

import contextvars
from typing import Any

__all__ = ["get_outbound_headers", "reset_outbound_headers", "set_outbound_headers"]

# Kênh trung lập (không phụ thuộc apps/cosa) để kernel truyền các header xác
# thực (Authorization, X-Workspace-Id, X-COSA-Run-Id, X-COSA-Capability-Id)
# xuống HTTP client của Company (`apps.cosa.capabilities.client.CompanyServiceClient`)
# TRONG PHẠM VI đúng 1 tool call — không phải qua tham số hàm capability
# handler (tránh phải sửa chữ ký mọi handler) và cũng không phải qua field
# argument do model sinh ra (Task 5 §Step 4: "Company capability handlers
# build these values from InvocationContext, never tool arguments").
#
# Vì sao đặt ở packages/agent (không phải apps/cosa hay agent_integrations):
# packages/agent_integrations/openai_agents_sdk/kernel.py (nơi set giá trị)
# và apps/cosa/capabilities/client.py (nơi đọc giá trị) không được phép phụ
# thuộc chéo lẫn nhau theo 4 vùng kiến trúc ở CLAUDE.md — packages/agent là
# lớp trung lập duy nhất cả hai cùng import được.
_outbound_headers: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "cosa_outbound_headers", default=None
)


def set_outbound_headers(headers: dict[str, str]) -> contextvars.Token:
    """Set header ambient cho đúng 1 tool call đang chạy trong context hiện tại.
    Trả về Token để caller bắt buộc `reset_outbound_headers()` trong finally —
    không reset sẽ làm header của 1 tool call "rò" sang các câu gọi HTTP khác
    chạy đồng thời trong cùng task/coroutine con cháu."""
    return _outbound_headers.set(dict(headers))


def reset_outbound_headers(token: contextvars.Token) -> None:
    _outbound_headers.reset(token)


def get_outbound_headers() -> dict[str, str]:
    """Đọc header ambient hiện tại — rỗng nếu không có tool call nào đang set
    (vd. gọi Company ngoài luồng capability, hoặc test không set)."""
    return dict(_outbound_headers.get() or {})
