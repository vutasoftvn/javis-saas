import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from platform_core.control_plane.models import PlatformUser, CompanyMembership
from platform_core.control_plane.authz import (
    COMPANY_ROLE_LEVELS,
    PLATFORM_STAFF_ROLE_LEVELS,
    authorize_company,
    authorize_platform_staff,
)


def _membership(role_id: str) -> CompanyMembership:
    m = MagicMock(spec=CompanyMembership)
    m.role_id = role_id
    return m


def test_founder_can_manage_company():
    authorize_company(_membership("founder"), "company.manage")


def test_user_cannot_manage_company():
    with pytest.raises(HTTPException) as exc:
        authorize_company(_membership("user"), "company.manage")
    assert exc.value.status_code == 403


def test_co_founder_can_manage_company():
    authorize_company(_membership("co-founder"), "company.manage")


def test_no_membership_raises_403():
    with pytest.raises(HTTPException) as exc:
        authorize_company(None, "company.manage")
    assert exc.value.status_code == 403


def test_unknown_role_defaults_to_lowest_level():
    with pytest.raises(HTTPException):
        authorize_company(_membership("some_unknown_role"), "company.manage")


def test_authorize_platform_staff_allows_admin():
    user = MagicMock(spec=PlatformUser)
    user.platform_role_id = "admin"
    authorize_platform_staff(user, "platform.manage")


def test_authorize_platform_staff_allows_superadmin():
    user = MagicMock(spec=PlatformUser)
    user.platform_role_id = "superadmin"
    authorize_platform_staff(user, "platform.manage")


def test_authorize_platform_staff_rejects_support():
    user = MagicMock(spec=PlatformUser)
    user.platform_role_id = "support"
    with pytest.raises(HTTPException) as exc:
        authorize_platform_staff(user, "platform.manage")
    assert exc.value.status_code == 403


def test_authorize_platform_staff_rejects_no_role():
    user = MagicMock(spec=PlatformUser)
    user.platform_role_id = None
    with pytest.raises(HTTPException) as exc:
        authorize_platform_staff(user, "platform.manage")
    assert exc.value.status_code == 403


def test_authorize_platform_staff_rejects_none_user():
    with pytest.raises(HTTPException) as exc:
        authorize_platform_staff(None, "platform.manage")
    assert exc.value.status_code == 403


def test_company_founder_has_no_platform_staff_role_by_default():
    """1 founder cua company khong tu nhien co quyen quan tri nen tang -
    2 truc quyen doc lap (COMPANY_ROLE_LEVELS vs PLATFORM_STAFF_ROLE_LEVELS)."""
    assert "founder" not in PLATFORM_STAFF_ROLE_LEVELS
    assert "superadmin" not in COMPANY_ROLE_LEVELS
