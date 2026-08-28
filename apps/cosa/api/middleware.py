"""Middleware phòng thủ bề mặt tấn công cơ bản cho apps/cosa/api (Part 2C.4).

`MaxBodySizeMiddleware` — chặn request có `Content-Length` vượt ngưỡng với
HTTP 413, ngay ở lớp ứng dụng. Đây là lớp phòng thủ chiều sâu, KHÔNG thay
cho giới hạn cứng ở edge proxy: request `Transfer-Encoding: chunked` không
kèm `Content-Length` sẽ lọt qua middleware này — Caddy `request_body
max_size` (deploy/central_vps/Caddyfile) mới là giới hạn cứng chặn cả
trường hợp đó.

Rate limiting theo IP/principal cũng đặt ở edge proxy (Caddy), không nhúng
vào app — xem ADR-DEPLOY-001 và Caddyfile.
"""

from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

__all__ = ["MaxBodySizeMiddleware", "resolve_max_request_bytes"]

_DEFAULT_MAX_REQUEST_BYTES = 10 * 1024 * 1024  # 10 MiB


def resolve_max_request_bytes() -> int:
    raw = os.environ.get("COSA_MAX_REQUEST_BYTES")
    if not raw:
        return _DEFAULT_MAX_REQUEST_BYTES
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"COSA_MAX_REQUEST_BYTES không phải số nguyên hợp lệ: {raw!r}") from exc
    if value <= 0:
        raise RuntimeError("COSA_MAX_REQUEST_BYTES phải > 0")
    return value


class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """Từ chối request có body vượt `max_bytes` với HTTP 413."""

    def __init__(self, app, max_bytes: int | None = None) -> None:
        super().__init__(app)
        self._max_bytes = max_bytes if max_bytes is not None else resolve_max_request_bytes()

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                return JSONResponse({"detail": "invalid Content-Length header"}, status_code=400)
            if declared > self._max_bytes:
                return JSONResponse(
                    {"detail": f"request body exceeds limit of {self._max_bytes} bytes"},
                    status_code=413,
                )
        return await call_next(request)
