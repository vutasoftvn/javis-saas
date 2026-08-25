from __future__ import annotations

import os

import jwt

__all__ = ["InvalidPlatformTokenError", "verify_platform_token"]

# Cùng default insecure dev secret với services/cosa/services/token.service.ts
# (PLATFORM_JWT_SECRET) — giữ đối xứng để token do COSA control plane phát
# hành verify được ở cả 2 phía trong local dev không cần cấu hình thêm.
# Production PHẢI set PLATFORM_JWT_SECRET thật qua env — đây là dev fallback,
# không phải một "an toàn vì đã có default" giả định.
_DEV_DEFAULT_SECRET = "cosa-super-secret-platform-jwt-key-change-in-prod"


class InvalidPlatformTokenError(Exception):
    """Token thiếu, sai chữ ký, hết hạn, hoặc sai audience."""


def verify_platform_token(token: str) -> str:
    """Verify JWT platform token (HS256, aud="cosa") phát hành bởi
    services/cosa/services/token.service.ts::signPlatformToken(). Trả về
    platform_user_id (claim `sub`) nếu hợp lệ, raise InvalidPlatformTokenError
    nếu không — không có đường fallback nào trả về identity mặc định.
    """
    secret = os.environ.get("PLATFORM_JWT_SECRET", _DEV_DEFAULT_SECRET)
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], audience="cosa")
    except jwt.InvalidTokenError as exc:
        raise InvalidPlatformTokenError(str(exc)) from exc

    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise InvalidPlatformTokenError("token thiếu claim 'sub' hợp lệ")
    return sub
