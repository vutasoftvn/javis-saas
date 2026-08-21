"""Test cho POST /api/v1/auth/sync-from-platform - diem vao chinh cua app moi
(control_plane la nguon su that, local user duoc tao/dong bo tu do thay vi
tu form dang ky local)."""
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from core.snowflake import generate_snowflake_id
from db.models import User, Workspace, WorkspaceMember
from platform_core.control_plane.models import Company, CompanyMembership, PlatformUser, Profile
from platform_core.control_plane.security import create_platform_access_token
from platform_core.auth.router import sync_from_platform, SyncFromPlatformRequest


@pytest.fixture(autouse=True)
def secure_jwt_secret(monkeypatch):
    monkeypatch.setattr(
        "core.security.JWT_SECRET",
        "test-jwt-secret-that-is-long-enough-for-hs256-123456",
    )


def _query_side_effect(model_to_result: dict):
    def side_effect(model):
        q = MagicMock()
        q.filter.return_value.first.return_value = model_to_result.get(model)
        return q

    return side_effect


def test_sync_creates_new_local_user_and_workspace_for_founder():
    platform_user_id = generate_snowflake_id()
    company_id = generate_snowflake_id()
    token = create_platform_access_token({"sub": str(platform_user_id)})

    platform_user = MagicMock(spec=PlatformUser)
    platform_user.id = platform_user_id
    platform_user.email = "founder@cosa.dev"
    platform_user.phone = None

    membership = MagicMock(spec=CompanyMembership)
    membership.user_id = platform_user_id
    membership.company_id = company_id
    membership.role_id = "founder"

    company = MagicMock(spec=Company)
    company.id = company_id
    company.name = "Acme Inc"

    db = MagicMock()
    db.query.side_effect = _query_side_effect(
        {
            PlatformUser: platform_user,
            CompanyMembership: membership,
            Company: company,
            Profile: None,
            User: None,  # no existing local user by platform_user_id nor email
            Workspace: None,  # no existing local workspace for this company yet
            WorkspaceMember: None,
        }
    )

    created = []
    db.add.side_effect = lambda obj: created.append(obj)

    payload = SyncFromPlatformRequest(platform_access_token=token, company_id=str(company_id))
    res = sync_from_platform(payload=payload, db=db)

    assert "access_token" in res
    assert res["token_type"] == "bearer"

    new_users = [o for o in created if isinstance(o, User)]
    assert len(new_users) == 1
    assert new_users[0].email == "founder@cosa.dev"
    assert new_users[0].platform_user_id == str(platform_user_id)
    assert new_users[0].role == "founder"

    new_workspaces = [o for o in created if isinstance(o, Workspace)]
    assert len(new_workspaces) == 1
    assert new_workspaces[0].name == "Acme Inc"
    assert new_workspaces[0].platform_company_id == str(company_id)

    new_memberships = [o for o in created if isinstance(o, WorkspaceMember)]
    assert len(new_memberships) == 1
    assert new_memberships[0].role == "admin"  # first member of a brand-new workspace


def test_sync_reuses_existing_local_user_matched_by_platform_user_id():
    platform_user_id = generate_snowflake_id()
    company_id = generate_snowflake_id()
    token = create_platform_access_token({"sub": str(platform_user_id)})

    platform_user = MagicMock(spec=PlatformUser)
    platform_user.id = platform_user_id
    platform_user.email = "member@cosa.dev"
    platform_user.phone = None

    membership = MagicMock(spec=CompanyMembership)
    membership.role_id = "user"

    company = MagicMock(spec=Company)
    company.id = company_id
    company.name = "Acme Inc"

    existing_local_user = MagicMock(spec=User)
    existing_local_user.id = generate_snowflake_id()
    existing_local_user.platform_user_id = str(platform_user_id)

    existing_workspace = MagicMock(spec=Workspace)
    existing_workspace.id = generate_snowflake_id()
    existing_workspace.platform_company_id = str(company_id)

    db = MagicMock()
    db.query.side_effect = _query_side_effect(
        {
            PlatformUser: platform_user,
            CompanyMembership: membership,
            Company: company,
            User: existing_local_user,
            Workspace: existing_workspace,
            WorkspaceMember: MagicMock(spec=WorkspaceMember),  # already a member
        }
    )

    created = []
    db.add.side_effect = lambda obj: created.append(obj)

    payload = SyncFromPlatformRequest(platform_access_token=token, company_id=str(company_id))
    res = sync_from_platform(payload=payload, db=db)

    assert "access_token" in res
    # No new User/Workspace/WorkspaceMember rows - reused existing ones.
    assert not any(isinstance(o, User) for o in created)
    assert not any(isinstance(o, Workspace) for o in created)
    assert not any(isinstance(o, WorkspaceMember) for o in created)
    assert existing_local_user.role == "user"


def test_sync_rejects_when_not_a_member_of_company():
    platform_user_id = generate_snowflake_id()
    company_id = generate_snowflake_id()
    token = create_platform_access_token({"sub": str(platform_user_id)})

    platform_user = MagicMock(spec=PlatformUser)
    platform_user.id = platform_user_id

    db = MagicMock()
    db.query.side_effect = _query_side_effect({PlatformUser: platform_user, CompanyMembership: None})

    payload = SyncFromPlatformRequest(platform_access_token=token, company_id=str(company_id))
    with pytest.raises(HTTPException) as exc:
        sync_from_platform(payload=payload, db=db)
    assert exc.value.status_code == 403


def test_sync_rejects_invalid_platform_token():
    db = MagicMock()
    payload = SyncFromPlatformRequest(platform_access_token="not-a-real-token", company_id="123")
    with pytest.raises(HTTPException) as exc:
        sync_from_platform(payload=payload, db=db)
    assert exc.value.status_code == 401


def test_sync_rejects_invalid_company_id_format():
    platform_user_id = generate_snowflake_id()
    token = create_platform_access_token({"sub": str(platform_user_id)})

    platform_user = MagicMock(spec=PlatformUser)
    platform_user.id = platform_user_id

    db = MagicMock()
    db.query.side_effect = _query_side_effect({PlatformUser: platform_user})

    payload = SyncFromPlatformRequest(platform_access_token=token, company_id="not-a-number")
    with pytest.raises(HTTPException) as exc:
        sync_from_platform(payload=payload, db=db)
    assert exc.value.status_code == 422
