"""HMAC-SHA256 giữa local relay (`services/company`) và AgentOS intake.
Secret dùng chung qua `COSA_LOCAL_SERVICE_SECRET`. Đây là ranh giới tin cậy
cho `/agent/internal/events` (không public browser access).

Ký/verify trên đúng chuỗi bytes của request body (`raw_body: bytes`) — không
re-serialize dict — để chữ ký khớp byte-exact với payload mà relay đã gửi,
tránh sai lệch do khác biệt separator/ordering/unicode giữa hai lần json.dumps.
"""

from __future__ import annotations

import hashlib
import hmac
import os

__all__ = ["LocalServiceAuth"]


class LocalServiceAuth:
    def __init__(self, secret: str | None = None) -> None:
        self._secret = (secret or os.environ.get("COSA_LOCAL_SERVICE_SECRET", "")).encode("utf-8")

    def sign(self, raw_body: bytes) -> str:
        return hmac.new(self._secret, raw_body, hashlib.sha256).hexdigest()

    def verify(self, signature: str, raw_body: bytes) -> bool:
        if not signature or not self._secret:
            return False
        return hmac.compare_digest(signature, self.sign(raw_body))
