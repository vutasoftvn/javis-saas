from __future__ import annotations

import contextvars

from agent.capabilities.grants import ConnectorGrant

__all__ = [
    "get_current_connector_grant",
    "reset_current_connector_grant",
    "set_current_connector_grant",
]

# Grant connector mà CapabilityGateway vừa re-verify ở Bước 8.5 cho ĐÚNG 1 tool call đang chạy
# (plan hub vận hành đợt 2 B3). Handler cần credential theo workspace (vd. `email.digest.read`
# đọc `metadata["secret_ref"]`) lấy grant ở đây thay vì tự gọi control-plane assert lần hai:
# - dùng đúng grant đã kiểm (không có khe TOCTOU giữa hai lần assert, không lệch `action`);
# - không thêm field vào context/payload của handler (context có thể được persist/log).
# Cùng mẫu `outbound_headers.py`: gateway set trước khi gọi handler và reset trong finally,
# nên grant không rò sang tool call khác. Không có connector requirement / không có resolver
# ⇒ None, handler cần grant phải fail-closed.
_current_grant: contextvars.ContextVar[ConnectorGrant | None] = contextvars.ContextVar(
    "cosa_current_connector_grant", default=None
)


def set_current_connector_grant(grant: ConnectorGrant | None) -> contextvars.Token:
    return _current_grant.set(grant)


def reset_current_connector_grant(token: contextvars.Token) -> None:
    _current_grant.reset(token)


def get_current_connector_grant() -> ConnectorGrant | None:
    return _current_grant.get()
