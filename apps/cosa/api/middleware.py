"""Middleware phòng thủ bề mặt tấn công cơ bản cho apps/cosa/api (Part 2C.4).

`MaxBodySizeMiddleware` — chặn request có `Content-Length` vượt ngưỡng với
HTTP 413, ngay ở lớp ứng dụng. Đây là lớp phòng thủ chiều sâu, KHÔNG thay
cho giới hạn cứng ở edge proxy: request `Transfer-Encoding: chunked` không
kèm `Content-Length` sẽ lọt qua middleware này — Caddy `request_body
max_size` (deploy/central_vps/Caddyfile) mới là giới hạn cứng chặn cả
trường hợp đó.

`RateLimitMiddleware` + `SlidingWindowLimiter` (review 2026-09-27, G-4) —
trước đây docstring này ghi rate limit "đặt ở Caddy" nhưng Caddyfile không có
(image `caddy:2-alpine` chuẩn không kèm plugin rate-limit). Giới hạn đặt ở app:
theo IP cho mọi request, và chặt hơn cho tạo run (`conversation_routes`).
Giới hạn là PER-PROCESS (bộ nhớ trong) — đủ chặn lạm dụng trên 1 replica; khi
chạy nhiều replica cần store chung (Redis/DB) để đếm chính xác.
"""

from __future__ import annotations

import math
import os
import threading
import time
from collections import deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

__all__ = [
    "MaxBodySizeMiddleware",
    "RateLimitMiddleware",
    "SlidingWindowLimiter",
    "resolve_max_request_bytes",
    "resolve_rate_limit",
]

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


def resolve_rate_limit(env_name: str, default: int) -> int:
    """Số request tối đa mỗi 60s; 0 = tắt. Giá trị sai -> lỗi khởi động (không
    âm thầm thành "không giới hạn")."""
    raw = os.environ.get(env_name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{env_name} không phải số nguyên hợp lệ: {raw!r}") from exc
    if value < 0:
        raise RuntimeError(f"{env_name} phải >= 0")
    return value


class SlidingWindowLimiter:
    """Cửa sổ trượt theo khoá (IP, workspace+principal…). Thread-safe, O(k)."""

    def __init__(self, limit: int, window_sec: float = 60.0, clock=time.monotonic) -> None:
        self.limit = limit
        self.window_sec = window_sec
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str) -> float | None:
        """Ghi 1 lượt; trả None nếu cho phép, hoặc số giây phải chờ nếu vượt."""
        if self.limit <= 0:
            return None
        now = self._clock()
        with self._lock:
            q = self._hits.setdefault(key, deque())
            cutoff = now - self.window_sec
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= self.limit:
                return max(q[0] + self.window_sec - now, 0.0)
            q.append(now)
            if len(self._hits) > 50_000:  # chặn phình bộ nhớ khi bị quét IP
                for k in [k for k, v in self._hits.items() if not v or v[-1] <= cutoff]:
                    self._hits.pop(k, None)
            return None


def too_many_requests(retry_after: float, detail: str = "rate limit exceeded") -> JSONResponse:
    return JSONResponse(
        {"detail": detail, "code": "RATE_LIMITED"},
        status_code=429,
        headers={"Retry-After": str(max(1, math.ceil(retry_after)))},
    )


_EXEMPT_PATHS = ("/healthz", "/live", "/ready", "/metrics")


def _client_ip(request: Request) -> str:
    # Caddy (edge duy nhất) đặt X-Forwarded-For; chỉ tin khi được bật tường minh.
    if os.environ.get("COSA_TRUST_FORWARDED_FOR", "").lower() in ("1", "true", "yes"):
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Giới hạn theo IP (`COSA_RATE_LIMIT_PER_MINUTE`, mặc định 600, 0 = tắt)."""

    def __init__(self, app, limiter: SlidingWindowLimiter | None = None) -> None:
        super().__init__(app)
        self._limiter = limiter or SlidingWindowLimiter(
            resolve_rate_limit("COSA_RATE_LIMIT_PER_MINUTE", 600)
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method != "OPTIONS" and not request.url.path.startswith(_EXEMPT_PATHS):
            wait = self._limiter.hit(f"ip:{_client_ip(request)}")
            if wait is not None:
                return too_many_requests(wait)
        return await call_next(request)
