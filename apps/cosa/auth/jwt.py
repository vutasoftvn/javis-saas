from __future__ import annotations

import os
import time
import uuid

import jwt

__all__ = [
    "InvalidPlatformTokenError",
    "MissingPlatformIdentityError",
    "mint_company_delegation",
    "mint_control_plane_delegation",
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

# Task 3 (AI compliance hardening) — secret RIÊNG cho delegation có cấu trúc
# (scoped) COSA -> Company (mint_company_delegation / verifyCosaDelegation ở
# services/company/shared/auth/cosa-delegation.service.ts). KHÔNG tái dùng
# PLATFORM_JWT_SECRET (đối xứng với services/cosa, chiều ký khác — services/cosa
# ký, apps/cosa verify) hay JWT_SECRET (đối xứng với services/company local
# session, cũng sai chiều — services/company ký, apps/cosa verify). Chiều cần
# ở đây là apps/cosa KÝ, services/company VERIFY — chưa từng có secret nào
# đi đúng chiều này trước Task 3, nên dùng biến env mới, đơn mục đích.
_COMPANY_DELEGATION_DEV_DEFAULT_SECRET = "cosa-company-delegation-dev-secret-change-in-prod"
_COMPANY_DELEGATION_MAX_TTL_SECONDS = 600

# B5 fix (2026-09-04) — secret RIÊNG cho delegation có cấu trúc (scoped) chiều
# apps/cosa -> services/cosa (verify tại services/cosa/services/token.service.ts
# ::verifyControlDelegationToken). Trước bug này, verifyWorkspaceMembership phía
# services/cosa forward nguyên Authorization header (PLATFORM_JWT_SECRET, hoặc
# JWT_SECRET local session) sang services/company để re-verify — nhưng
# services/company chỉ hiểu JWT_SECRET local-session, nên mọi token platform
# hợp lệ đều fail ở đó (khác secret) => 403 permission_denied vô điều kiện.
# Cùng pattern với _COMPANY_DELEGATION_DEV_DEFAULT_SECRET (apps/cosa KÝ,
# services/cosa VERIFY) nhưng KHÁC mục đích: mint_company_delegation phục vụ
# apps/cosa -> services/company; secret này phục vụ apps/cosa -> services/cosa
# — không dùng lẫn giữa 2 chiều.
_CONTROL_DELEGATION_DEV_DEFAULT_SECRET = "cosa-control-delegation-dev-secret-change-in-prod"
_CONTROL_DELEGATION_MAX_TTL_SECONDS = 600


class MissingPlatformIdentityError(Exception):
    """Principal hiện tại (thường là local_session chưa từng sync qua
    platform) không có platform_user_id thật — không thể mint control-plane
    delegation. Call site PHẢI coi đây là DENY, không silently fallback sang
    local id (2 ID space khác nhau, verify phía services/cosa sẽ reject hoặc
    tệ hơn là match nhầm sang user khác nếu ID trùng ngẫu nhiên)."""


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


def _get_company_delegation_secret() -> str:
    env_name = os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "development")).lower()
    secret = os.environ.get("COSA_COMPANY_DELEGATION_SECRET")
    if env_name in ("production", "staging", "prod") and (
        not secret or secret == _COMPANY_DELEGATION_DEV_DEFAULT_SECRET or len(secret) < 32
    ):
        raise RuntimeError(
            f"COSA_COMPANY_DELEGATION_SECRET must be explicitly set with >= 32 characters and not use default key in {env_name} environment"
        )
    return secret or _COMPANY_DELEGATION_DEV_DEFAULT_SECRET


def _get_control_delegation_secret() -> str:
    env_name = os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "development")).lower()
    secret = os.environ.get("COSA_CONTROL_DELEGATION_SECRET")
    if env_name in ("production", "staging", "prod") and (
        not secret or secret == _CONTROL_DELEGATION_DEV_DEFAULT_SECRET or len(secret) < 32
    ):
        raise RuntimeError(
            f"COSA_CONTROL_DELEGATION_SECRET must be explicitly set with >= 32 characters and not use default key in {env_name} environment"
        )
    return secret or _CONTROL_DELEGATION_DEV_DEFAULT_SECRET


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


def mint_company_delegation(
    *,
    sub: str,
    workspace_id: str,
    run_id: str,
    capability_ids: list[str],
    ttl_seconds: int = _COMPANY_DELEGATION_MAX_TTL_SECONDS,
) -> str:
    """Mint delegation JWT CÓ CẤU TRÚC (scoped) để apps/cosa gọi sang
    services/company thay mặt đúng 1 workspace + 1 run + đúng tập capability
    đã khai báo — verify bằng verifyCosaDelegation (services/company/shared/
    auth/cosa-delegation.service.ts).

    Khác hẳn mint_delegation_token/mint_local_delegation_token ở trên (chỉ
    re-sign lại {sub, aud?, exp} để giảm rủi ro lộ bearer token dài hạn khi
    lưu vào durable queue) — hàm này KHÔNG mang theo bearer token gốc của
    user, KHÔNG có quyền rộng hơn những gì được khai báo tường minh:
    - `sub`: Company identity user/member ID đã xác thực cục bộ (KHÔNG phải
      platform_user_id thô — caller phải tự resolve trước khi gọi hàm này).
    - `workspace_id`/`run_id`: đã được verify (workspace cross-check, run đã
      tạo) trước khi mint — hàm này KHÔNG tự resolve/verify lại.
    - `capability_ids`: đúng tập capability caller khai báo cần dùng, không
      hơn — verify phía Company reject nếu capability được dùng không nằm
      trong danh sách này.

    TTL tối đa CỨNG 600 giây (§ giảm cửa sổ rủi ro nếu payload này bị lộ) —
    truyền ttl_seconds lớn hơn KHÔNG kéo dài thời hạn thật, giá trị bị cắt về
    600. Durable task payload không bao giờ chứa bearer token gốc của user.
    """
    secret = _get_company_delegation_secret()
    ttl = min(ttl_seconds, _COMPANY_DELEGATION_MAX_TTL_SECONDS)
    payload = {
        "iss": "cosa",
        "aud": "company",
        "sub": sub,
        "principal_id": f"user:{sub}",
        "workspace_id": workspace_id,
        "run_id": run_id,
        "capability_ids": list(capability_ids),
        "jti": str(uuid.uuid4()),
        "exp": int(time.time()) + ttl,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def mint_control_plane_delegation(
    *,
    sub: str,
    workspace_id: str,
    role: str,
    ttl_seconds: int = _CONTROL_DELEGATION_MAX_TTL_SECONDS,
) -> str:
    """Mint delegation JWT CÓ CẤU TRÚC (scoped) để apps/cosa gọi các endpoint
    control-plane (services/cosa) đòi hỏi vừa qua platform gateway vừa chứng
    minh workspace membership trong 1 lần gọi — verify bằng
    verifyControlDelegationToken (services/cosa/services/token.service.ts).

    B5 fix — trước hàm này, endpoint như `GET /platform/auth/me/agent-policy-
    snapshot` và `/cosa/schedules*` verify membership bằng cách forward
    Authorization header sang services/company, nhưng services/company chỉ
    hiểu local-session token (JWT_SECRET) — token platform hợp lệ (aud=cosa,
    PLATFORM_JWT_SECRET) luôn fail ở đó vì khác secret, dẫn tới 403
    permission_denied VÔ ĐIỀU KIỆN bất kể workspace nào (bug B5).

    - `sub` PHẢI là platform_user_id THẬT (không phải local company user id —
      caller dùng `AuthenticatedIdentity.mint_control_plane_delegation()`,
      hàm đó tự raise `MissingPlatformIdentityError` nếu thiếu, không tự ý
      dùng local id thay thế).
    - `workspace_id`/`role` LUÔN lấy từ identity đã cross-check thật (không
      nhận làm tham số tự do từ request) — xem lời gọi trong
      `AuthenticatedIdentity.mint_control_plane_delegation()`.

    TTL tối đa CỨNG 600 giây, cùng lý do giảm cửa sổ rủi ro với
    mint_company_delegation."""
    secret = _get_control_delegation_secret()
    ttl = min(ttl_seconds, _CONTROL_DELEGATION_MAX_TTL_SECONDS)
    payload = {
        "iss": "cosa_apps",
        "aud": "cosa_control",
        "sub": sub,
        # snake_case — cùng convention với mint_company_delegation (JWT claim
        # do Python mint luôn snake_case, TS verify destructure nguyên văn
        # field này, KHÔNG map sang camelCase — xem cosa-delegation.service.ts
        # phía services/company làm y hệt cho workspace_id/run_id/capability_ids).
        "workspace_id": workspace_id,
        "role": role,
        "jti": str(uuid.uuid4()),
        "exp": int(time.time()) + ttl,
    }
    return jwt.encode(payload, secret, algorithm="HS256")
