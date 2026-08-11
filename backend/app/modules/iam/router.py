import re

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from typing import Optional

from app.db.session import get_db
from app.db.models import User, Workspace, WorkspaceMember, Brain
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.auth import get_current_user

router = APIRouter()

# +84912345678 hoặc 0912345678 - 9 tới 15 chữ số, tối đa 1 dấu + ở đầu.
PHONE_RE = re.compile(r"^\+?\d{9,15}$")

class Token(BaseModel):
    access_token: str
    token_type: str

class RegisterRequest(BaseModel):
    phone: str
    password: str
    display_name: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip().replace(" ", "").replace("-", "")
        if not PHONE_RE.match(v):
            raise ValueError("Số điện thoại không hợp lệ")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Mật khẩu phải có ít nhất 6 ký tự")
        return v

@router.post("/register", response_model=Token)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.phone == payload.phone).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Số điện thoại đã được đăng ký",
        )

    user = User(
        phone=payload.phone,
        password_hash=get_password_hash(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    db.flush()

    # MVP cá nhân: mỗi user mới tự có 1 workspace/brain mặc định, đúng quy ước
    # đã dùng ở GET /me (xem chú thích bên dưới) để Flutter có workspace_id/brain_id ngay.
    workspace = Workspace(name=f"Workspace của {payload.display_name or payload.phone}")
    db.add(workspace)
    db.flush()

    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="admin"))
    db.add(Brain(workspace_id=workspace.id, name="Brain mặc định"))
    db.commit()

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/sessions", response_model=Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    identifier = form_data.username.strip()
    user = db.query(User).filter(
        or_(User.phone == identifier, User.email == identifier)
    ).first()
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me")
def read_users_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    membership = db.query(WorkspaceMember).filter(WorkspaceMember.user_id == current_user.id).first()
    brains = []
    default_brain_id = None
    if membership:
        brains_list = db.query(Brain).filter(Brain.workspace_id == membership.workspace_id, Brain.archived_at.is_(None)).all()
        brains = [{"id": str(b.id), "name": b.name, "slug": b.slug} for b in brains_list]
        if brains_list:
            default_brain_id = str(brains_list[0].id)

    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "phone": current_user.phone,
        "display_name": current_user.display_name,
        "workspace_id": str(membership.workspace_id) if membership else None,
        "role": membership.role if membership else None,
        "brain_id": default_brain_id,
        "default_brain_id": default_brain_id,
        "brains": brains,
    }
