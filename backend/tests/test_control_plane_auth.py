import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError

from core.snowflake import generate_snowflake_id
from core.security import get_password_hash, create_access_token
from platform_core.control_plane.models import Company, CompanyMembership, PlatformUser
from platform_core.control_plane.security import (
    create_platform_access_token,
    decode_platform_access_token,
)
from platform_core.control_plane.deps import get_current_platform_user
from platform_core.control_plane.router_auth import (
    register_platform_user,
    login_platform_user,
    RegisterRequest,
)


@pytest.fixture(autouse=True)
def secure_jwt_secret(monkeypatch):
    monkeypatch.setattr(
        "core.security.JWT_SECRET",
        "test-jwt-secret-that-is-long-enough-for-hs256-123456",
    )


def test_register_with_new_company_creates_founder():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    created = []
    db.add.side_effect = lambda obj: created.append(obj)

    req = RegisterRequest(
        email="founder@cosa.dev", password="secretpassword123", company_name="Acme Inc"
    )
    res = register_platform_user(payload=req, db=db)

    assert "access_token" in res
    assert res["token_type"] == "bearer"
    assert db.commit.called

    memberships = [obj for obj in created if isinstance(obj, CompanyMembership)]
    assert len(memberships) == 1
    assert memberships[0].role_id == "founder"
    assert any(isinstance(obj, Company) for obj in created)


def test_register_joining_existing_company_gets_user_role():
    db = MagicMock()
    existing_company = MagicMock(spec=Company)
    existing_company.id = 999

    def query_side_effect(model):
        q = MagicMock()
        if model is Company:
            q.filter.return_value.first.return_value = existing_company
        else:
            q.filter.return_value.first.return_value = None
        return q

    db.query.side_effect = query_side_effect

    created = []
    db.add.side_effect = lambda obj: created.append(obj)

    req = RegisterRequest(
        email="member@cosa.dev", password="secretpassword123", join_company_id=999
    )
    res = register_platform_user(payload=req, db=db)

    assert "access_token" in res
    memberships = [obj for obj in created if isinstance(obj, CompanyMembership)]
    assert len(memberships) == 1
    assert memberships[0].role_id == "user"
    assert memberships[0].company_id == 999


def test_register_requires_company_choice():
    with pytest.raises(ValidationError):
        RegisterRequest(email="founder@cosa.dev", password="secretpassword123")


def test_register_rejects_both_company_choices():
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="founder@cosa.dev",
            password="secretpassword123",
            company_name="Acme",
            join_company_id=1,
        )


def test_register_duplicate_email():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = MagicMock(spec=PlatformUser)

    req = RegisterRequest(
        email="founder@cosa.dev", password="secretpassword123", company_name="Acme Inc"
    )
    with pytest.raises(HTTPException) as exc:
        register_platform_user(payload=req, db=db)
    assert exc.value.status_code == 409


def test_register_validation_short_password():
    with pytest.raises(ValidationError):
        RegisterRequest(email="founder@cosa.dev", password="123", company_name="Acme")


def test_login_success_by_email():
    db = MagicMock()
    user_id = generate_snowflake_id()
    mock_user = MagicMock(spec=PlatformUser)
    mock_user.id = user_id
    mock_user.email = "founder@cosa.dev"
    mock_user.phone = None
    mock_user.hashed_password = get_password_hash("mypassword")

    db.query.return_value.filter.return_value.first.return_value = mock_user

    form_data = OAuth2PasswordRequestForm(
        grant_type="password",
        username="founder@cosa.dev",
        password="mypassword",
        scope="",
        client_id=None,
        client_secret=None,
    )

    res = login_platform_user(form_data=form_data, db=db)
    assert "access_token" in res
    assert res["token_type"] == "bearer"


def test_login_success_by_phone():
    db = MagicMock()
    user_id = generate_snowflake_id()
    mock_user = MagicMock(spec=PlatformUser)
    mock_user.id = user_id
    mock_user.email = "founder@cosa.dev"
    mock_user.phone = "0912345678"
    mock_user.hashed_password = get_password_hash("mypassword")

    db.query.return_value.filter.return_value.first.return_value = mock_user

    form_data = OAuth2PasswordRequestForm(
        grant_type="password",
        username="0912345678",
        password="mypassword",
        scope="",
        client_id=None,
        client_secret=None,
    )

    res = login_platform_user(form_data=form_data, db=db)
    assert "access_token" in res


def test_login_wrong_password():
    db = MagicMock()
    mock_user = MagicMock(spec=PlatformUser)
    mock_user.id = generate_snowflake_id()
    mock_user.email = "founder@cosa.dev"
    mock_user.phone = None
    mock_user.hashed_password = get_password_hash("correctpassword")

    db.query.return_value.filter.return_value.first.return_value = mock_user

    form_data = OAuth2PasswordRequestForm(
        grant_type="password",
        username="founder@cosa.dev",
        password="wrongpassword",
        scope="",
        client_id=None,
        client_secret=None,
    )

    with pytest.raises(HTTPException) as exc:
        login_platform_user(form_data=form_data, db=db)
    assert exc.value.status_code == 401


def test_platform_token_roundtrip():
    token = create_platform_access_token({"sub": "123"})
    payload = decode_platform_access_token(token)
    assert payload["sub"] == "123"
    assert payload["aud"] == "control_plane"


def test_local_token_rejected_by_platform_decode():
    local_token = create_access_token({"sub": "123"})
    with pytest.raises(Exception):
        decode_platform_access_token(local_token)


def test_get_current_platform_user_rejects_local_token():
    db = MagicMock()
    local_token = create_access_token({"sub": "123"})
    with pytest.raises(HTTPException) as exc:
        get_current_platform_user(token=local_token, db=db)
    assert exc.value.status_code == 401


def test_get_current_platform_user_accepts_platform_token():
    db = MagicMock()
    user_id = generate_snowflake_id()
    mock_user = MagicMock(spec=PlatformUser)
    mock_user.id = user_id
    mock_user.status = "active"
    db.query.return_value.filter.return_value.first.return_value = mock_user

    token = create_platform_access_token({"sub": str(user_id)})
    result = get_current_platform_user(token=token, db=db)
    assert result is mock_user
