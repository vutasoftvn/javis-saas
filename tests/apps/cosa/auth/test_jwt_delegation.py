from __future__ import annotations

import time

import jwt as pyjwt
import pytest

from apps.cosa.auth.jwt import mint_delegation_token, verify_platform_token

SECRET = "cosa-super-secret-platform-jwt-key-change-in-prod"


def test_mint_delegation_token_verifies_via_verify_platform_token():
    """Token tự mint phải verify được qua chính hàm verify_platform_token()
    hiện có — chứng minh tương thích với services/cosa
    token.service.ts::verifyPlatformToken() (cùng secret/aud/thuật toán)."""
    token = mint_delegation_token("99")
    assert verify_platform_token(token) == "99"


def test_mint_delegation_token_has_short_ttl_by_default():
    token = mint_delegation_token("99")
    payload = pyjwt.decode(token, SECRET, algorithms=["HS256"], audience="cosa")
    now = int(time.time())
    assert payload["exp"] - now <= 600
    assert payload["exp"] - now > 0


def test_mint_delegation_token_respects_custom_ttl():
    token = mint_delegation_token("99", ttl_seconds=30)
    payload = pyjwt.decode(token, SECRET, algorithms=["HS256"], audience="cosa")
    now = int(time.time())
    assert payload["exp"] - now <= 30


def test_mint_delegation_token_expired_fails_verification():
    token = mint_delegation_token("99", ttl_seconds=-1)
    with pytest.raises(Exception):
        verify_platform_token(token)
