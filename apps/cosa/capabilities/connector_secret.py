"""Resolve `secret_ref` của grant connector workspace thành credential thật (plan hub đợt 2 B3).

Mẫu giống `services/company/commercial/services/customer-engagement/channel-secret.ts`:
- `set_custom_connector_secret_resolver(fn)` — test (hoặc vault thật sau này) tiêm resolver;
  resolver trả `None` thì rơi xuống bước env.
- Mặc định cho dev: env `COSA_CONNECTOR_SECRET_<REF đã chuẩn hoá>`. Chuẩn hoá: bỏ tiền tố
  namespace `secret://cosa-connectors/` (services/cosa `validateSecretRef` bắt buộc tiền tố
  này), mọi ký tự ngoài `[A-Za-z0-9]` thành `_`, viết hoa. Ví dụ
  `secret://cosa-connectors/ws-42/email-read` → `COSA_CONNECTOR_SECRET_WS_42_EMAIL_READ`.
- Không resolve được → `ConnectorSecretUnresolvableError`; message KHÔNG chứa secret_ref/tên env.

GAP (chưa làm, không bịa): chưa có vault thật cho namespace `secret://cosa-connectors/` và chưa
có OAuth flow Google/Gmail trong repo (dù `.env.example` có `GOOGLE_CLIENT_ID/SECRET/REDIRECT_URI`),
nên chưa có refresh token/tự làm mới access token. Production cần tiêm resolver vault thật.
"""

from __future__ import annotations

import inspect
import os
import re
from collections.abc import Awaitable, Callable

__all__ = [
    "SECRET_REF_NAMESPACE",
    "ConnectorSecretUnresolvableError",
    "connector_secret_env_name",
    "resolve_connector_secret",
    "set_custom_connector_secret_resolver",
]

SECRET_REF_NAMESPACE = "secret://cosa-connectors/"
_ENV_PREFIX = "COSA_CONNECTOR_SECRET_"

ConnectorSecretResolver = Callable[[str], str | Awaitable[str | None] | None]

_custom_resolver: ConnectorSecretResolver | None = None


class ConnectorSecretUnresolvableError(RuntimeError):
    code = "connector_secret_unresolvable"

    def __init__(self, connector_key: str | None = None) -> None:
        target = f"connector {connector_key}" if connector_key else "connector"
        super().__init__(
            f"{self.code}: không đọc được credential của {target} "
            "(chưa cấu hình kho secret cho grant này)"
        )


def set_custom_connector_secret_resolver(resolver: ConnectorSecretResolver | None) -> None:
    global _custom_resolver
    _custom_resolver = resolver


def connector_secret_env_name(secret_ref: str) -> str:
    ref = secret_ref.removeprefix(SECRET_REF_NAMESPACE)
    return _ENV_PREFIX + re.sub(r"[^A-Za-z0-9]", "_", ref).upper()


async def resolve_connector_secret(secret_ref: str, *, connector_key: str | None = None) -> str:
    if not secret_ref:
        raise ConnectorSecretUnresolvableError(connector_key)
    if _custom_resolver is not None:
        value = _custom_resolver(secret_ref)
        if inspect.isawaitable(value):
            value = await value
        if value:
            return str(value)
    env_value = os.environ.get(connector_secret_env_name(secret_ref), "")
    if env_value:
        return env_value
    raise ConnectorSecretUnresolvableError(connector_key)
