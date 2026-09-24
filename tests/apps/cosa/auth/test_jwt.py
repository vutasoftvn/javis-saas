from __future__ import annotations

import time

import jwt
import pytest

from apps.cosa.auth.jwt import InvalidPlatformTokenError, verify_local_session_token

# Local session token do services/company ký (JWT_SECRET, HS256, KHÔNG audience). Danh tính gốc do
# backend/core quản lý; AgentOS chỉ chấp nhận local session.
SECRET = "cosa-dev-jwt-secret-do-not-use-in-prod"


def _make_token(*, sub="42", secret=SECRET, exp_delta=3600, extra=None):
    payload = {"sub": sub, "exp": int(time.time()) + exp_delta}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, secret, algorithm="HS256")


def test_valid_token_returns_sub():
    assert verify_local_session_token(_make_token(sub="123")) == "123"


def test_wrong_secret_rejected():
    with pytest.raises(InvalidPlatformTokenError):
        verify_local_session_token(_make_token(secret="wrong-secret"))


def test_expired_token_rejected():
    with pytest.raises(InvalidPlatformTokenError):
        verify_local_session_token(_make_token(exp_delta=-10))


def test_token_with_audience_rejected():
    """Token mang audience (vd delegation của luồng khác) không phải local session."""
    with pytest.raises(InvalidPlatformTokenError):
        verify_local_session_token(_make_token(extra={"aud": "cosa"}))


def test_missing_sub_rejected():
    token = jwt.encode({"exp": int(time.time()) + 3600}, SECRET, algorithm="HS256")
    with pytest.raises(InvalidPlatformTokenError):
        verify_local_session_token(token)


def test_garbage_token_rejected():
    with pytest.raises(InvalidPlatformTokenError):
        verify_local_session_token("not-a-real-jwt")
