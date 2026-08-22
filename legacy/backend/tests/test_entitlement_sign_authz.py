"""`/sync/entitlement/sign` được mount khi COSA_RUNTIME_PLANE=control (xem
test_entitlement_plane_gating.py) nhưng trước đây không kiểm tra danh tính
người/máy gọi - bất kỳ ai gọi tới cũng ký được entitlement cho bất kỳ
company nào. Test này khoá lại: chỉ PlatformUser có platform staff role
(superadmin/admin, qua platform_role_id) mới gọi được."""
import importlib
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from platform_core.control_plane.models import PlatformUser


@pytest.fixture
def control_plane_sync_router(monkeypatch):
    monkeypatch.setenv("COSA_RUNTIME_PLANE", "control")
    import platform_core.sync.router as sync_router_module
    importlib.reload(sync_router_module)
    yield sync_router_module
    monkeypatch.delenv("COSA_RUNTIME_PLANE", raising=False)
    importlib.reload(sync_router_module)


def _admin_user() -> PlatformUser:
    u = MagicMock(spec=PlatformUser)
    u.platform_role_id = "admin"
    return u


def _non_admin_user() -> PlatformUser:
    u = MagicMock(spec=PlatformUser)
    u.platform_role_id = None
    return u


def test_sign_rejects_non_admin_platform_user(control_plane_sync_router):
    payload = control_plane_sync_router.IssueSnapshotRequest(company_id="123")
    with pytest.raises(HTTPException) as exc:
        control_plane_sync_router.sign_company_entitlement(
            payload=payload, current_user=_non_admin_user()
        )
    assert exc.value.status_code == 403


def test_sign_allows_platform_admin(control_plane_sync_router, monkeypatch):
    import base64
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption

    private_key = Ed25519PrivateKey.generate()
    private_b64 = base64.urlsafe_b64encode(
        private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    ).decode("utf-8")
    monkeypatch.setenv("COSA_ENTITLEMENT_PRIVATE_KEY_B64", private_b64)
    monkeypatch.setenv("COSA_ENTITLEMENT_KEY_ID", "test-key")

    payload = control_plane_sync_router.IssueSnapshotRequest(company_id="123")
    result = control_plane_sync_router.sign_company_entitlement(
        payload=payload, current_user=_admin_user()
    )
    assert result.company_id == "123"
