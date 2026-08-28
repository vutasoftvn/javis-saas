"""HMAC-SHA256 giữa local relay (`services/company`) và AgentOS intake.
Secret dùng chung qua `COSA_LOCAL_SERVICE_SECRET`. Đây là ranh giới tin cậy
cho `/agent/internal/events` (không public browser access).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os

__all__ = ["LocalServiceAuth"]


class LocalServiceAuth:
    def __init__(self, secret: str | None = None) -> None:
        self._secret = (secret or os.environ.get("COSA_LOCAL_SERVICE_SECRET", "")).encode("utf-8")

    def sign(self, raw_body: dict) -> str:
        return hmac.new(self._secret, json.dumps(raw_body).encode("utf-8"), hashlib.sha256).hexdigest()

    def verify(self, signature: str, raw_body: dict) -> bool:
        if not signature or not self._secret:
            return False
        return hmac.compare_digest(signature, self.sign(raw_body))
