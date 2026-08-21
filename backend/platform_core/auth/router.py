import re

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator
from typing import Optional

from db.session import get_db
from db.models import User, Workspace, WorkspaceMember, Brain
from core.security import verify_password, get_password_hash, create_access_token
from core.auth import get_current_user
from platform_core.control_plane.models import Company, CompanyMembership, PlatformUser, Profile
from platform_core.control_plane.security import decode_platform_access_token

router = APIRouter()

# +84912345678 hoặc 0912345678 - 9 tới 15 chữ số, tối đa 1 dấu + ở đầu.
PHONE_RE = re.compile(r"^\+?\d{9,15}$")

class Token(BaseModel):
    access_token: str
    token_type: str

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("Email không hợp lệ")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Mật khẩu phải có ít nhất 6 ký tự")
        return v


class UpdateMeRequest(BaseModel):
    phone: Optional[str] = None
    display_name: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().replace(" ", "").replace("-", "")
        if not PHONE_RE.match(v):
            raise ValueError("Số điện thoại không hợp lệ")
        return v


@router.post("/register", response_model=Token)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email đã được đăng ký",
        )

    user = User(
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    db.flush()

    # MVP cá nhân: mỗi user mới tự có 1 workspace/brain mặc định, đúng quy ước
    # đã dùng ở GET /me (xem chú thích bên dưới) để Flutter có workspace_id/brain_id ngay.
    workspace = Workspace(name=f"Workspace của {payload.display_name or payload.email}")
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
    normalized_phone = identifier.replace(" ", "").replace("-", "")
    user = db.query(User).filter(
        or_(
            User.phone == identifier,
            User.phone == normalized_phone,
            User.email == identifier,
        )
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


@router.patch("/me")
def update_users_me(
    payload: UpdateMeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bo sung/cap nhat ho so sau khi da dang ky bang email+password - truoc
    het la so dien thoai (khong bat buoc luc dang ky nua, xem RegisterRequest)."""
    if payload.phone is not None:
        existing_phone = (
            db.query(User).filter(User.phone == payload.phone, User.id != current_user.id).first()
        )
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Số điện thoại đã được đăng ký",
            )
        current_user.phone = payload.phone

    if payload.display_name is not None:
        current_user.display_name = payload.display_name

    db.commit()
    return read_users_me(current_user=current_user, db=db)


class SyncFromPlatformRequest(BaseModel):
    platform_access_token: str
    company_id: str


@router.post("/sync-from-platform", response_model=Token)
def sync_from_platform(payload: SyncFromPlatformRequest, db: Session = Depends(get_db)):
    """Diem vao chinh cua app: control_plane la nguon su that cho danh tinh
    (bat buoc dang nhap/dang ky online tren control_plane truoc). Endpoint
    nay nhan platform_access_token (da co tu /platform/auth/register hoac
    /platform/auth/sessions) + company_id nguoi dung da chon, roi:
      1. Tim hoac tao core.users tuong ung (khop theo platform_user_id, roi
         toi email) - KHONG con yeu cau da dang nhap local truoc (khac
         link_platform_account cu, endpoint nay thay the hoan toan).
      2. Tim hoac tao core.workspaces cho company_id do (workspace moi thi
         rong, tai su dung du lieu cu neu may nay da tung sync company do
         truoc day - dung nguyen tac OPC: 1 workspace local = 1 company).
      3. Dong bo role tu company_roles.role_id xuong core.users.role.
      4. Phat local JWT (dung nhu /auth/sessions) de app dung tiep cho moi
         API local khac.
    KHONG dong bo nen tu dong (CLAUDE.md §10 Local First) - chi chay khi app
    chu dong goi voi 1 platform token + company_id da chon tuong minh."""
    try:
        decoded = decode_platform_access_token(payload.platform_access_token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid platform access token")

    platform_user_id = decoded.get("sub")
    if not platform_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid platform access token")

    platform_user = db.query(PlatformUser).filter(PlatformUser.id == platform_user_id).first()
    if platform_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Platform user không tồn tại")

    try:
        company_id = int(payload.company_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="company_id không hợp lệ")

    membership = (
        db.query(CompanyMembership)
        .filter(
            CompanyMembership.user_id == platform_user.id,
            CompanyMembership.company_id == company_id,
        )
        .first()
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Bạn không phải thành viên của company này"
        )

    company = db.query(Company).filter(Company.id == company_id).first()
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company không tồn tại")

    # 1. Tim hoac tao local user tuong ung voi platform_user nay.
    local_user = (
        db.query(User).filter(User.platform_user_id == str(platform_user.id)).first()
    )
    if local_user is None and platform_user.email:
        local_user = db.query(User).filter(User.email == platform_user.email).first()

    if local_user is None:
        profile = db.query(Profile).filter(Profile.user_id == platform_user.id).first()
        local_user = User(
            email=platform_user.email,
            phone=platform_user.phone,
            platform_user_id=str(platform_user.id),
            display_name=profile.full_name if profile else None,
        )
        db.add(local_user)
        db.flush()
    else:
        local_user.platform_user_id = str(platform_user.id)

    local_user.role = membership.role_id

    # 2. Tim hoac tao workspace local rong cho company nay (OPC - 1 workspace
    # local = 1 company; workspace da tung sync truoc day thi giu nguyen du
    # lieu, khong tao lai).
    workspace = (
        db.query(Workspace).filter(Workspace.platform_company_id == str(company.id)).first()
    )
    is_new_workspace = workspace is None
    if workspace is None:
        workspace = Workspace(name=company.name, platform_company_id=str(company.id))
        db.add(workspace)
        db.flush()
        db.add(Brain(workspace_id=workspace.id, name="Brain mặc định"))

    workspace_membership = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.workspace_id == workspace.id, WorkspaceMember.user_id == local_user.id)
        .first()
    )
    if workspace_membership is None:
        db.add(
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=local_user.id,
                role="admin" if is_new_workspace else "member",
            )
        )

    db.commit()

    access_token = create_access_token(data={"sub": str(local_user.id)})
    return {"access_token": access_token, "token_type": "bearer"}
