"""JWT helpers riêng cho Central Control Plane (PlatformUser).

Dùng chung JWT_SECRET/JWT_ALGORITHM/create_access_token với Local Business DB
(`core.security`) nhưng gắn claim `aud="control_plane"` bắt buộc, để 1 token
Local `User` không thể được chấp nhận bởi dependency control-plane và ngược
lại - PyJWT tự chặn cả 2 chiều khi audience được truyền vào decode() (đã
verify thực nghiệm: token có "aud" nhưng decode() không truyền audience ->
InvalidAudienceError; token không có "aud" nhưng decode() truyền audience ->
MissingRequiredClaimError).
"""
import jwt

import core.security as core_security

CONTROL_PLANE_AUDIENCE = "control_plane"


def create_platform_access_token(data: dict) -> str:
    payload = {**data, "aud": CONTROL_PLANE_AUDIENCE}
    return core_security.create_access_token(payload)


def decode_platform_access_token(token: str) -> dict:
    # Đọc core_security.JWT_SECRET/JWT_ALGORITHM động (không import trực tiếp
    # tên biến) để test có thể monkeypatch core.security.JWT_SECRET và cả 2
    # bên (encode ở core.security, decode ở đây) luôn cùng 1 giá trị.
    return jwt.decode(
        token,
        core_security.JWT_SECRET,
        algorithms=[core_security.JWT_ALGORITHM],
        audience=CONTROL_PLANE_AUDIENCE,
    )
