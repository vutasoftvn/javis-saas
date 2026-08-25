from __future__ import annotations

import time

import jwt
import pytest

from apps.cosa.auth.jwt import InvalidPlatformTokenError, verify_platform_token

SECRET = "cosa-super-secret-platform-jwt-key-change-in-prod"


def _make_token(*, sub="42", aud="cosa", secret=SECRET, exp_delta=3600, extra=None):
    payload = {"sub": sub, "aud": aud, "exp": int(time.time()) + exp_delta}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, secret, algorithm="HS256")


def test_valid_token_returns_sub():
    token = _make_token(sub="123")
    assert verify_platform_token(token) == "123"


def test_wrong_secret_rejected():
    token = _make_token(secret="wrong-secret")
    with pytest.raises(InvalidPlatformTokenError):
        verify_platform_token(token)


def test_expired_token_rejected():
    token = _make_token(exp_delta=-10)
    with pytest.raises(InvalidPlatformTokenError):
        verify_platform_token(token)


def test_wrong_audience_rejected():
    token = _make_token(aud="control_plane")
    with pytest.raises(InvalidPlatformTokenError):
        verify_platform_token(token)


def test_missing_sub_rejected():
    token = jwt.encode({"aud": "cosa", "exp": int(time.time()) + 3600}, SECRET, algorithm="HS256")
    with pytest.raises(InvalidPlatformTokenError):
        verify_platform_token(token)


def test_garbage_token_rejected():
    with pytest.raises(InvalidPlatformTokenError):
        verify_platform_token("not-a-real-jwt")
