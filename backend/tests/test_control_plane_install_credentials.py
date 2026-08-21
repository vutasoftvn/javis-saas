from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from platform_core.control_plane.models import InstallCredential
from platform_core.control_plane.install_credentials import (
    hash_install_token,
    enroll_install_credential,
    resolve_install_credential,
)
from platform_core.control_plane.deps import get_current_install


def test_hash_install_token_is_deterministic_sha256():
    assert hash_install_token("abc") == hash_install_token("abc")
    assert hash_install_token("abc") != hash_install_token("xyz")
    assert len(hash_install_token("abc")) == 64


def test_enroll_install_credential_returns_raw_token_once():
    db = MagicMock()
    credential, raw_token = enroll_install_credential(db, company_id=123)
    assert isinstance(raw_token, str) and len(raw_token) > 20
    assert db.add.called
    assert db.commit.called
    # the stored hash must never equal the raw token itself
    added_credential = db.add.call_args_list[0].args[0]
    assert added_credential.token_hash == hash_install_token(raw_token)


def test_resolve_install_credential_valid():
    db = MagicMock()
    cred = MagicMock(spec=InstallCredential)
    cred.is_revoked = False
    cred.expires_at = datetime.utcnow() + timedelta(days=1)
    db.query.return_value.filter.return_value.first.return_value = cred

    result = resolve_install_credential(db, "raw-token")
    assert result is cred


def test_resolve_install_credential_revoked_returns_none():
    db = MagicMock()
    cred = MagicMock(spec=InstallCredential)
    cred.is_revoked = True
    cred.expires_at = datetime.utcnow() + timedelta(days=1)
    db.query.return_value.filter.return_value.first.return_value = cred

    assert resolve_install_credential(db, "raw-token") is None


def test_resolve_install_credential_expired_returns_none():
    db = MagicMock()
    cred = MagicMock(spec=InstallCredential)
    cred.is_revoked = False
    cred.expires_at = datetime.utcnow() - timedelta(days=1)
    db.query.return_value.filter.return_value.first.return_value = cred

    assert resolve_install_credential(db, "raw-token") is None


def test_resolve_install_credential_not_found_returns_none():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    assert resolve_install_credential(db, "raw-token") is None


def test_get_current_install_rejects_missing_header():
    db = MagicMock()
    with pytest.raises(HTTPException) as exc:
        get_current_install(authorization="", db=db)
    assert exc.value.status_code == 401


def test_get_current_install_rejects_non_bearer_header():
    db = MagicMock()
    with pytest.raises(HTTPException) as exc:
        get_current_install(authorization="Token abc", db=db)
    assert exc.value.status_code == 401


def test_get_current_install_rejects_unresolvable_token():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        get_current_install(authorization="Bearer bad-token", db=db)
    assert exc.value.status_code == 401


def test_get_current_install_accepts_valid_token():
    db = MagicMock()
    cred = MagicMock(spec=InstallCredential)
    cred.is_revoked = False
    cred.expires_at = datetime.utcnow() + timedelta(days=1)
    db.query.return_value.filter.return_value.first.return_value = cred

    result = get_current_install(authorization="Bearer good-token", db=db)
    assert result is cred
