import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from platform_core.control_plane.models import PlatformUser, CompanyMembership
from platform_core.control_plane.authz import (
    PLATFORM_PERMISSION_LEVELS,
    authorize_platform,
    require_platform_admin,
)


def _membership(role: str) -> CompanyMembership:
    m = MagicMock(spec=CompanyMembership)
    m.platform_role = role
    return m


def test_owner_can_manage_company():
    authorize_platform(_membership("owner"), "company.manage")


def test_member_cannot_manage_company():
    with pytest.raises(HTTPException) as exc:
        authorize_platform(_membership("member"), "company.manage")
    assert exc.value.status_code == 403


def test_admin_can_manage_company():
    authorize_platform(_membership("admin"), "company.manage")


def test_no_membership_raises_403():
    with pytest.raises(HTTPException) as exc:
        authorize_platform(None, "company.manage")
    assert exc.value.status_code == 403


def test_unknown_role_defaults_to_lowest_level():
    with pytest.raises(HTTPException):
        authorize_platform(_membership("some_unknown_role"), "company.manage")


def test_require_platform_admin_allows_admin_flag():
    user = MagicMock(spec=PlatformUser)
    user.is_platform_admin = True
    require_platform_admin(user)


def test_require_platform_admin_rejects_non_admin():
    user = MagicMock(spec=PlatformUser)
    user.is_platform_admin = False
    with pytest.raises(HTTPException) as exc:
        require_platform_admin(user)
    assert exc.value.status_code == 403
