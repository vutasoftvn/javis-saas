from __future__ import annotations

import os
import time

import jwt

__all__ = [
    "InvalidPlatformTokenError",
    "mint_delegation_token",
    "mint_local_delegation_token",
    "verify_local_session_token",
    "verify_platform_token",
]

# Cùng default insecure dev secret với services/cosa/services/token.service.ts
# (PLATFORM_JWT_SECRET) — giữ đối xứng để token do COSA control plane phát
# hành verify được ở cả 2 phía trong local dev không cần cấu hình thêm.
# Production PHẢI set PLATFORM_JWT_SECRET thật qua env — đây là dev fallback,
# không phải một "an toàn vì đã có default" giả định.
_DEV_DEFAULT_SECRET = "cosa-super-secret-platform-jwt-key-change-in-prod"
# M1 §1 — local session token do services/company/identity/token.service.ts ký
# (JWT_SECRET, HS256, KHÔNG audience). AgentOS chạy local business ⇒ chấp nhận
# token này cho luồng business; giữ đối xứng secret với token.service.ts.
_LOCAL_SESSION_DEV_DEFAULT_SECRET = "cosa-dev-jwt-secret-do-not-use-in-prod"


def _get_jwt_secret() -> str:
    env_name = os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "development")).lower()
    secret = os.environ.get("PLATFORM_JWT_SECRET")
    if env_name in ("production", "staging", "prod") and (
        not secret or secret == _DEV_DEFAULT_SECRET or len(secret) < 32
    ):
        raise RuntimeError(
            f"PLATFORM_JWT_SECRET must be explicitly set with >= 32 characters and not use default key in {env_name} environment"
        )
    return secret or _DEV_DEFAULT_SECRET


def _get_local_session_secret() -> str:
    env_name = os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "development")).lower()
    secret = os.environ.get("JWT_SECRET")
    if env_name in ("production", "staging", "prod") and (
        not secret or secret == _LOCAL_SESSION_DEV_DEFAULT_SECRET or len(secret) < 32
    ):
        raise RuntimeError(
            f"JWT_SECRET must be explicitly set with >= 32 characters and not use default key in {env_name} environment"
        )
    return secret or _LOCAL_SESSION_DEV_DEFAULT_SECRET


class InvalidPlatformTokenError(Exception):
    """Token thiếu, sai chữ ký, hết hạn, hoặc sai audience."""


def verify_platform_token(token: str) -> str:
    """Verify JWT platform token (HS256, aud="cosa") phát hành bởi
    services/cosa/services/token.service.ts::signPlatformToken(). Trả về
    platform_user_id (claim `sub`) nếu hợp lệ, raise InvalidPlatformTokenError
    nếu không — không có đường fallback nào trả về identity mặc định.
    """
    secret = _get_jwt_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], audience="cosa")
    except jwt.InvalidTokenError as exc:
        raise InvalidPlatformTokenError(str(exc)) from exc

    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise InvalidPlatformTokenError("token thiếu claim 'sub' hợp lệ")
    return sub


def verify_local_session_token(token: str) -> str:
    """Verify local session JWT (HS256, KHÔNG audience) do
    services/company/identity/token.service.ts::signAccessToken() phát hành.
    Trả về local user id (claim `sub`). Raise InvalidPlatformTokenError nếu sai.
    """
    secret = _get_local_session_secret()
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.InvalidTokenError as exc:
        raise InvalidPlatformTokenError(str(exc)) from exc
    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise InvalidPlatformTokenError("token thiếu claim 'sub' hợp lệ")
    return sub


def mint_local_delegation_token(user_id: str, *, ttl_seconds: int = 600) -> str:
    """Như mint_delegation_token nhưng shape local session (JWT_SECRET, KHÔNG
    audience) — dùng khi identity gốc đến từ local session token, để lệnh
    forward xuống services/company verify được."""
    secret = _get_local_session_secret()
    payload = {"sub": user_id, "exp": int(time.time()) + ttl_seconds}
    return jwt.encode(payload, secret, algorithm="HS256")


def mint_delegation_token(platform_user_id: str, *, ttl_seconds: int = 600) -> str:
    """Mint 1 JWT ngắn hạn cùng shape với token do
    services/cosa/services/token.service.ts::signPlatformToken() phát hành
    ({sub, aud: "cosa"}, cùng PLATFORM_JWT_SECRET đối xứng) — dùng để thay
    thế bearer token dài hạn (7 ngày) của user thật khi cần lưu credential
    vào durable queue (`scheduled_tasks.input_payload`). TTL mặc định 10
    phút — đủ cho worker xử lý task trong thời gian hợp lý, nhưng giảm mạnh
    cửa sổ rủi ro nếu payload này bị lộ ở rest trong Postgres (COSA_
    PRODUCTION_RUNTIME_CLOSURE_ADJUSTMENT_2026-08-25.md §6.2).

    KHÔNG mint token với TTL dài — nếu cần task chạy lâu hơn TTL, worker
    phải re-resolve authorization mới, không phải mint token sống lâu hơn.
    """
    secret = _get_jwt_secret()
    payload = {
        "sub": platform_user_id,
        "aud": "cosa",
        "exp": int(time.time()) + ttl_seconds,
    }
    return jwt.encode(payload, secret, algorithm="HS256")
