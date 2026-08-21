"""Auth router cho Central Control Plane (PlatformUser) - mirror
`platform_core.auth.router` (Local Business DB) nhưng dùng JWT audience
riêng (`platform_core.control_plane.security`) để không lẫn với token Local."""
import re

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import or_
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional

from db.session import get_db
from core.security import verify_password, get_password_hash
from platform_core.control_plane.models import Company, CompanyMembership, PlatformUser, Profile
from platform_core.control_plane.security import create_platform_access_token
from platform_core.control_plane.deps import get_current_platform_user

router = APIRouter(prefix="/auth", tags=["Platform Auth"])

# +84912345678 hoặc 0912345678 - 9 tới 15 chữ số, tối đa 1 dấu + ở đầu.
PHONE_RE = re.compile(r"^\+?\d{9,15}$")


def _normalize_phone(v: str) -> str:
    v = v.strip().replace(" ", "").replace("-", "")
    if not PHONE_RE.match(v):
        raise ValueError("Số điện thoại không hợp lệ")
    return v


class Token(BaseModel):
    access_token: str
    token_type: str
    company_id: Optional[str] = None


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    join_company_id: Optional[int] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Mật khẩu phải có ít nhất 6 ký tự")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return _normalize_phone(v)

    @model_validator(mode="after")
    def validate_company_choice(self) -> "RegisterRequest":
        if bool(self.company_name) == bool(self.join_company_id):
            raise ValueError(
                "Phải chọn đúng 1 trong 2: tạo company mới (company_name) "
                "hoặc tham gia company có sẵn (join_company_id)"
            )
        return self


class UpdateMeRequest(BaseModel):
    phone: Optional[str] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return _normalize_phone(v)


@router.post("/register", response_model=Token)
def register_platform_user(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(PlatformUser).filter(PlatformUser.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email đã được đăng ký",
        )
    if payload.phone:
        existing_phone = db.query(PlatformUser).filter(PlatformUser.phone == payload.phone).first()
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Số điện thoại đã được đăng ký",
            )

    company: Optional[Company] = None
    if payload.join_company_id is not None:
        company = db.query(Company).filter(Company.id == payload.join_company_id).first()
        if company is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company không tồn tại",
            )

    user = PlatformUser(
        email=payload.email,
        phone=payload.phone,
        hashed_password=get_password_hash(payload.password),
    )
    db.add(user)
    db.flush()

    db.add(Profile(user_id=user.id, full_name=payload.full_name))

    if payload.company_name:
        company = Company(name=payload.company_name, slug=_slugify(payload.company_name, user.id), created_by=user.id)
        db.add(company)
        db.flush()
        role_id = "founder"
    else:
        role_id = "user"

    db.add(CompanyMembership(company_id=company.id, user_id=user.id, role_id=role_id))
    db.commit()

    access_token = create_platform_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer", "company_id": str(company.id)}


def _slugify(name: str, user_id: int) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-") or "company"
    return f"{base}-{user_id}"


@router.post("/sessions", response_model=Token)
def login_platform_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    identifier = form_data.username.strip()
    normalized_phone = identifier.replace(" ", "").replace("-", "")
    user = db.query(PlatformUser).filter(
        or_(
            PlatformUser.email == identifier,
            PlatformUser.phone == identifier,
            PlatformUser.phone == normalized_phone,
        )
    ).first()
    if not user or not user.hashed_password or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_platform_access_token({"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me/companies")
def list_my_companies(
    current_user: PlatformUser = Depends(get_current_platform_user), db: Session = Depends(get_db)
):
    """Danh sach company ma platform user hien tai la thanh vien - dung de
    app hien man 'Chon cong ty' luc dang nhap khi 1 tai khoan thuoc >1
    company (khong bat nguoi dung go company_id thu cong)."""
    memberships = db.query(CompanyMembership).filter(CompanyMembership.user_id == current_user.id).all()
    if not memberships:
        return []

    company_ids = [m.company_id for m in memberships]
    companies = {c.id: c for c in db.query(Company).filter(Company.id.in_(company_ids)).all()}

    return [
        {
            "company_id": str(m.company_id),
            "name": companies[m.company_id].name if m.company_id in companies else None,
            "role_id": m.role_id,
        }
        for m in memberships
    ]


@router.get("/me")
def read_platform_user_me(
    current_user: PlatformUser = Depends(get_current_platform_user), db: Session = Depends(get_db)
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "phone": current_user.phone,
        "full_name": profile.full_name if profile else None,
        "avatar_url": profile.avatar_url if profile else None,
        "is_platform_admin": current_user.is_platform_admin,
        "platform_role_id": current_user.platform_role_id,
    }


@router.patch("/me")
def update_platform_user_me(
    payload: UpdateMeRequest,
    current_user: PlatformUser = Depends(get_current_platform_user),
    db: Session = Depends(get_db),
):
    if payload.phone is not None:
        existing_phone = (
            db.query(PlatformUser)
            .filter(PlatformUser.phone == payload.phone, PlatformUser.id != current_user.id)
            .first()
        )
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Số điện thoại đã được đăng ký",
            )
        current_user.phone = payload.phone

    if payload.full_name is not None or payload.avatar_url is not None:
        profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
        if profile is None:
            profile = Profile(user_id=current_user.id)
            db.add(profile)
        if payload.full_name is not None:
            profile.full_name = payload.full_name
        if payload.avatar_url is not None:
            profile.avatar_url = payload.avatar_url

    db.commit()
    return read_platform_user_me(current_user=current_user, db=db)
