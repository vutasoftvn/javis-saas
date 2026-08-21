from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from platform_core.control_plane.models import PlatformUser
from platform_core.sync.router import enroll_install_credential_route, EnrollInstallCredentialRequest


def _admin() -> PlatformUser:
    u = MagicMock(spec=PlatformUser)
    u.is_platform_admin = True
    return u


def _non_admin() -> PlatformUser:
    u = MagicMock(spec=PlatformUser)
    u.is_platform_admin = False
    return u


def test_enroll_rejects_non_admin():
    db = MagicMock()
    payload = EnrollInstallCredentialRequest(company_id="123")
    with pytest.raises(HTTPException) as exc:
        enroll_install_credential_route(payload=payload, db=db, current_user=_non_admin())
    assert exc.value.status_code == 403


def test_enroll_returns_raw_token_for_admin():
    db = MagicMock()
    payload = EnrollInstallCredentialRequest(company_id="123")
    result = enroll_install_credential_route(payload=payload, db=db, current_user=_admin())
    assert "token" in result
    assert isinstance(result["token"], str) and len(result["token"]) > 20
