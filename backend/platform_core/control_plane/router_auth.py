"""Auth router cho Central Control Plane (PlatformUser) - mirror
`platform_core.auth.router` (Local Business DB) nhưng dùng JWT audience
riêng (`platform_core.control_plane.security`) để không lẫn với token Local."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from typing import Optional

from db.session import get_db
from core.security import verify_password, get_password_hash
from platform_core.control_plane.models import PlatformUser
from platform_core.control_plane.security import create_platform_access_token
from platform_core.control_plane.deps import get_current_platform_user

router = APIRouter(prefix="/auth", tags=["Platform Auth"])


class Token(BaseModel):
    access_token: str
    token_type: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Mật khẩu phải có ít nhất 6 ký tự")
        return v


@router.post("/register", response_model=Token)
def register_platform_user(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(PlatformUser).filter(PlatformUser.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email đã được đăng ký",
        )

    user = PlatformUser(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_platform_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/sessions", response_model=Token)
def login_platform_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(PlatformUser).filter(PlatformUser.email == form_data.username).first()
    if not user or not user.hashed_password or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_platform_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
def read_platform_user_me(current_user: PlatformUser = Depends(get_current_platform_user)):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_platform_admin": current_user.is_platform_admin,
    }
