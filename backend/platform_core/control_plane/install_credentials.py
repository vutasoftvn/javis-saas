"""Enroll/resolve InstallCredential - mirror
`integrations.devices.service.hash_device_token`/`enroll_device` (Local)
nhưng cho kênh sync máy-với-máy giữa Local install và Central Control Plane."""
from datetime import datetime, timedelta
import hashlib
import secrets
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from platform_core.control_plane.models import InstallCredential


def hash_install_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def enroll_install_credential(
    db: Session, company_id: int, validity_days: int = 365
) -> Tuple[InstallCredential, str]:
    """Tạo credential mới cho 1 company, trả về (credential, raw_token).

    raw_token chỉ tồn tại trong bộ nhớ ở lần gọi này - DB chỉ lưu hash của nó."""
    raw_token = f"cosa_install_{secrets.token_urlsafe(32)}"
    credential = InstallCredential(
        company_id=company_id,
        token_hash=hash_install_token(raw_token),
        is_revoked=False,
        expires_at=datetime.utcnow() + timedelta(days=validity_days),
        created_at=datetime.utcnow(),
    )
    db.add(credential)
    db.commit()
    return credential, raw_token


def resolve_install_credential(db: Session, raw_token: str) -> Optional[InstallCredential]:
    """Trả về credential hợp lệ (chưa revoke, chưa hết hạn) hoặc None."""
    credential = (
        db.query(InstallCredential)
        .filter(InstallCredential.token_hash == hash_install_token(raw_token))
        .first()
    )
    if credential is None:
        return None
    if credential.is_revoked:
        return None
    if credential.expires_at is not None and credential.expires_at < datetime.utcnow():
        return None
    return credential
