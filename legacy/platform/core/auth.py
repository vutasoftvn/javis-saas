from typing import TYPE_CHECKING
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import jwt

from core.security import decode_access_token, JWT_SECRET, JWT_ALGORITHM
from db.session import get_db
from platform_core.auth.models import User, WorkspaceMember

if TYPE_CHECKING:
    from integrations.devices.models import Device

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/sessions")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    if user.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return user

def get_current_workspace_member(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == current_user.id
    ).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this workspace"
        )
    return member


def get_current_device(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
) -> "Device":
    """Xác thực một Local Worker Plane node bằng enrollment token của nó (§113's
    two-plane split) - KHÔNG dùng JWT của user. Endpoint nào chỉ dành cho
    worker gọi (heartbeat, claim job, submit results) phải dùng dependency
    này thay vì get_current_workspace_member, nếu không thì bất kỳ user nào
    đăng nhập cũng giả được làm một worker/device.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or revoked device credential",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not authorization or not authorization.startswith("Bearer "):
        raise credentials_exception

    raw_token = authorization[len("Bearer "):].strip()
    if not raw_token:
        raise credentials_exception

    from integrations.devices.service import resolve_device_from_token
    device = resolve_device_from_token(db, raw_token)
    if not device:
        raise credentials_exception
    return device
