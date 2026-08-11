"""Luồng OAuth2 thật với Google - thay cho "kết nối" giả trước đây (chỉ lưu chuỗi email
người dùng gõ vào rồi gán status='connected', không có credential nào).

Refresh token là thứ duy nhất cần giữ lâu dài; access token sống 1 giờ nên xin lại mỗi
lần cần thay vì lưu. Token luôn được mã hoá theo workspace bằng secrets_service trước khi
chạm tới DB.
"""

import hashlib
import hmac
import json
import logging
import os
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"

# gmail.compose gộp cả tạo nháp lẫn gửi. Không xin gmail.modify/full: đọc + soạn là đủ cho
# mọi thứ sản phẩm hứa, còn xoá/sửa nhãn thì không tính năng nào cần.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/userinfo.email",
]

# state sống ngắn: nó chỉ cần tồn tại đủ để người dùng bấm xong màn hình đồng ý của Google.
STATE_TTL_SECONDS = 600


class GoogleOAuthError(RuntimeError):
    """Lỗi nói được cho người dùng, khác với lỗi lập trình."""


def client_id() -> str:
    return os.environ.get("GOOGLE_CLIENT_ID", "").strip()


def client_secret() -> str:
    return os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()


def redirect_uri() -> str:
    return os.environ.get(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/v1/connectors/google/oauth/callback",
    ).strip()


def is_configured() -> bool:
    return bool(client_id() and client_secret())


def _state_key() -> bytes:
    # Dùng chung JWT_SECRET: state chỉ cần chống giả mạo trong vài phút, không đáng để
    # thêm một secret nữa phải xoay vòng.
    return os.environ.get("JWT_SECRET", "supersecret-dev-key").encode("utf-8")


def sign_state(workspace_id: int, user_id: int) -> str:
    """Buộc lượt OAuth vào đúng workspace đã mở nó.

    Google gọi ngược lại /callback KHÔNG kèm session người dùng, nên workspace_id phải đi
    theo state. Ký để không ai tự chế state trỏ vào workspace của người khác rồi gắn hòm
    thư mình vào đó (hoặc ngược lại, cướp kết nối của workspace khác).
    """
    payload = {
        "workspace_id": str(workspace_id),
        "user_id": str(user_id),
        "exp": int(time.time()) + STATE_TTL_SECONDS,
    }
    raw = urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii").rstrip("=")
    signature = hmac.new(_state_key(), raw.encode("ascii"), hashlib.sha256).hexdigest()[:32]
    return f"{raw}.{signature}"


def verify_state(state: str) -> dict:
    try:
        raw, signature = state.split(".", 1)
    except ValueError:
        raise GoogleOAuthError("State không hợp lệ")

    expected = hmac.new(_state_key(), raw.encode("ascii"), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(signature, expected):
        raise GoogleOAuthError("State không hợp lệ")

    padding = "=" * (-len(raw) % 4)
    payload = json.loads(urlsafe_b64decode(raw + padding))
    if payload.get("exp", 0) < time.time():
        raise GoogleOAuthError("Liên kết kết nối đã hết hạn, hãy bấm kết nối lại")
    return payload


def build_authorize_url(state: str, login_hint: str | None = None) -> str:
    if not is_configured():
        raise GoogleOAuthError(
            "Máy chủ chưa có GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET nên chưa mở được "
            "cửa sổ đăng nhập Google."
        )

    params = {
        "client_id": client_id(),
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        # offline + consent: không có refresh_token thì kết nối chết sau đúng 1 giờ. Google
        # chỉ phát refresh_token ở lần đồng ý ĐẦU TIÊN, nên phải ép prompt=consent để lần
        # kết nối lại (vd. sau khi xoá connector) vẫn nhận được token mới.
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    if login_hint:
        params["login_hint"] = login_hint
    return f"{AUTH_ENDPOINT}?{urlencode(params)}"


async def exchange_code(code: str, transport: httpx.AsyncBaseTransport | None = None) -> dict:
    """Đổi authorization code lấy token. Trả về dict có refresh_token + access_token."""
    async with httpx.AsyncClient(transport=transport, timeout=30.0) as client:
        response = await client.post(
            TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": client_id(),
                "client_secret": client_secret(),
                "redirect_uri": redirect_uri(),
                "grant_type": "authorization_code",
            },
        )
    if response.status_code != 200:
        logger.warning("Google từ chối đổi code: %s %s", response.status_code, response.text[:300])
        raise GoogleOAuthError("Google từ chối cấp token cho mã đăng nhập này")

    tokens = response.json()
    if not tokens.get("refresh_token"):
        # Xảy ra khi user đã đồng ý trước đó và Google không phát lại refresh token. Không
        # có nó thì kết nối chỉ sống 1 giờ, thà báo hỏng ngay còn hơn hỏng lúc đang dùng.
        raise GoogleOAuthError(
            "Google không trả refresh token. Hãy vào myaccount.google.com/permissions, gỡ "
            "quyền của ứng dụng này rồi kết nối lại."
        )
    return tokens


async def fetch_email(access_token: str, transport: httpx.AsyncBaseTransport | None = None) -> str:
    """Địa chỉ thật của hòm thư vừa cấp quyền - không tin email người dùng tự gõ."""
    async with httpx.AsyncClient(transport=transport, timeout=30.0) as client:
        response = await client.get(
            USERINFO_ENDPOINT, headers={"Authorization": f"Bearer {access_token}"}
        )
    if response.status_code != 200:
        return ""
    return response.json().get("email", "")


async def refresh_access_token(
    refresh_token: str, transport: httpx.AsyncBaseTransport | None = None
) -> str:
    async with httpx.AsyncClient(transport=transport, timeout=30.0) as client:
        response = await client.post(
            TOKEN_ENDPOINT,
            data={
                "refresh_token": refresh_token,
                "client_id": client_id(),
                "client_secret": client_secret(),
                "grant_type": "refresh_token",
            },
        )
    if response.status_code != 200:
        logger.warning("Làm mới access token thất bại: %s", response.status_code)
        raise GoogleOAuthError(
            "Kết nối Gmail đã hết hiệu lực (có thể bạn đã thu hồi quyền). Hãy kết nối lại."
        )
    return response.json().get("access_token", "")
