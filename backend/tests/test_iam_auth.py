from core.snowflake import generate_snowflake_id
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError

from db.models import User, Workspace, WorkspaceMember, Brain
from core.security import get_password_hash
from platform_core.auth.router import (
    register,
    login_for_access_token,
    read_users_me,
    update_users_me,
    RegisterRequest,
    UpdateMeRequest,
)


@pytest.fixture(autouse=True)
def secure_jwt_secret(monkeypatch):
    """Keep token tests independent of a developer's local JWT secret."""
    monkeypatch.setattr(
        "core.security.JWT_SECRET",
        "test-jwt-secret-that-is-long-enough-for-hs256-123456",
    )


def test_register_success():
    db = MagicMock()
    # No existing user
    db.query.return_value.filter.return_value.first.return_value = None

    req = RegisterRequest(
        email="founder@javis.ai",
        password="secretpassword123",
        display_name="Nguyen Van A",
    )

    res = register(payload=req, db=db)
    assert "access_token" in res
    assert res["token_type"] == "bearer"
    assert db.add.call_count >= 3  # User, Workspace, WorkspaceMember, Brain
    assert db.commit.called


def test_register_duplicate_email():
    db = MagicMock()
    existing_user = MagicMock(spec=User)
    db.query.return_value.filter.return_value.first.return_value = existing_user

    req = RegisterRequest(
        email="founder@javis.ai",
        password="secretpassword123",
        display_name="Nguyen Van A",
    )

    with pytest.raises(HTTPException) as exc:
        register(payload=req, db=db)
    assert exc.value.status_code == 409
    assert "đã được đăng ký" in exc.value.detail


def test_register_validation_invalid_email():
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="not-an-email",
            password="secretpassword123",
            display_name="Nguyen Van A",
        )


def test_register_validation_short_password():
    with pytest.raises(ValidationError):
        RegisterRequest(
            email="founder@javis.ai",
            password="123",  # Less than 6 characters
            display_name="Nguyen Van A",
        )


def test_update_me_sets_phone():
    db = MagicMock()
    mock_user = MagicMock(spec=User)
    mock_user.id = generate_snowflake_id()
    mock_user.email = "founder@javis.ai"
    mock_user.phone = None
    mock_user.display_name = "Nguyen Van A"

    # 1st call: phone duplicate check (in update_users_me) -> None.
    # 2nd call: WorkspaceMember lookup (in read_users_me) -> None.
    db.query.return_value.filter.return_value.first.side_effect = [None, None]
    db.query.return_value.filter.return_value.all.return_value = []

    req = UpdateMeRequest(phone="0912345678")
    res = update_users_me(payload=req, current_user=mock_user, db=db)

    assert mock_user.phone == "0912345678"
    assert db.commit.called
    assert res["phone"] == "0912345678"


def test_update_me_rejects_duplicate_phone():
    db = MagicMock()
    other_user = MagicMock(spec=User)
    db.query.return_value.filter.return_value.first.return_value = other_user
    mock_user = MagicMock(spec=User)
    mock_user.id = generate_snowflake_id()

    req = UpdateMeRequest(phone="0912345678")
    with pytest.raises(HTTPException) as exc:
        update_users_me(payload=req, current_user=mock_user, db=db)
    assert exc.value.status_code == 409


def test_update_me_validation_invalid_phone():
    with pytest.raises(ValidationError):
        UpdateMeRequest(phone="123")


def test_login_success():
    db = MagicMock()
    user_id = generate_snowflake_id()
    mock_user = MagicMock(spec=User)
    mock_user.id = user_id
    mock_user.phone = "0912345678"
    mock_user.password_hash = get_password_hash("mypassword")

    db.query.return_value.filter.return_value.first.return_value = mock_user

    form_data = OAuth2PasswordRequestForm(
        grant_type="password",
        username="0912345678",
        password="mypassword",
        scope="",
        client_id=None,
        client_secret=None,
    )

    res = login_for_access_token(form_data=form_data, db=db)
    assert "access_token" in res
    assert res["token_type"] == "bearer"


def test_login_wrong_password():
    db = MagicMock()
    mock_user = MagicMock(spec=User)
    mock_user.id = generate_snowflake_id()
    mock_user.phone = "0912345678"
    mock_user.password_hash = get_password_hash("correctpassword")

    db.query.return_value.filter.return_value.first.return_value = mock_user

    form_data = OAuth2PasswordRequestForm(
        grant_type="password",
        username="0912345678",
        password="wrongpassword",
        scope="",
        client_id=None,
        client_secret=None,
    )

    with pytest.raises(HTTPException) as exc:
        login_for_access_token(form_data=form_data, db=db)
    assert exc.value.status_code == 401


def test_read_users_me_success():
    db = MagicMock()
    user_id = generate_snowflake_id()
    ws_id = generate_snowflake_id()
    brain_id = generate_snowflake_id()

    mock_user = MagicMock(spec=User)
    mock_user.id = user_id
    mock_user.email = "test@javis.ai"
    mock_user.phone = "0912345678"
    mock_user.display_name = "Founder AI"

    mock_member = MagicMock(spec=WorkspaceMember)
    mock_member.workspace_id = ws_id
    mock_member.user_id = user_id
    mock_member.role = "admin"

    mock_brain = MagicMock(spec=Brain)
    mock_brain.id = brain_id
    mock_brain.name = "Brain mặc định"
    mock_brain.slug = "brain-mac-dinh"

    db.query.return_value.filter.return_value.first.return_value = mock_member
    db.query.return_value.filter.return_value.all.return_value = [mock_brain]

    res = read_users_me(current_user=mock_user, db=db)
    assert res["id"] == str(user_id)
    assert res["email"] == "test@javis.ai"
    assert res["phone"] == "0912345678"
    assert res["display_name"] == "Founder AI"
    assert res["workspace_id"] == str(ws_id)
    assert res["role"] == "admin"
    assert res["brain_id"] == str(brain_id)
