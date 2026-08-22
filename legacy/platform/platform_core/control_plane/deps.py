"""FastAPI auth dependencies cho Central Control Plane - mirror
`core.auth.get_current_user` nhưng nhắm PlatformUser + JWT audience
`control_plane` riêng (xem `platform_core.control_plane.security`)."""
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import jwt

from platform_core.control_plane.session import get_control_plane_db
from platform_core.control_plane.models import InstallCredential, PlatformUser
from platform_core.control_plane.install_credentials import resolve_install_credential
from platform_core.control_plane.security import decode_platform_access_token

oauth2_scheme_platform = OAuth2PasswordBearer(tokenUrl="api/v1/platform/auth/sessions")


def get_current_platform_user(
    token: str = Depends(oauth2_scheme_platform), db: Session = Depends(get_control_plane_db)
) -> PlatformUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_platform_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(PlatformUser).filter(PlatformUser.id == user_id).first()
    if user is None:
        raise credentials_exception
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive platform user")
    return user


def get_current_install(
    authorization: str = Header(...), db: Session = Depends(get_control_plane_db)
) -> InstallCredential:
    """Xác thực kênh sync máy-với-máy giữa 1 Local install và Central Control
    Plane bằng InstallCredential của nó - KHÔNG dùng PlatformUser JWT (không
    có người đăng nhập ở kênh này), mirror `core.auth.get_current_device`."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or revoked install credential",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not authorization or not authorization.startswith("Bearer "):
        raise credentials_exception

    raw_token = authorization[len("Bearer "):].strip()
    if not raw_token:
        raise credentials_exception

    credential = resolve_install_credential(db, raw_token)
    if not credential:
        raise credentials_exception
    return credential
