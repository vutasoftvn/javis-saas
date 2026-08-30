from __future__ import annotations

import time

import jwt as pyjwt
import pytest

from apps.cosa.auth.jwt import mint_company_delegation, mint_delegation_token, verify_platform_token

SECRET = "cosa-super-secret-platform-jwt-key-change-in-prod"
COMPANY_DELEGATION_SECRET = "cosa-company-delegation-dev-secret-change-in-prod"


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


# ---------------------------------------------------------------------------
# mint_company_delegation — scoped COSA -> Company delegation (Task 3).
#
# Khác hẳn mint_delegation_token/mint_local_delegation_token ở trên (chỉ
# re-sign {sub, aud?, exp} để giảm rủi ro lộ bearer token dài hạn khi lưu
# queue) — mint_company_delegation phát hành claim CÓ CẤU TRÚC
# (iss=cosa, aud=company, workspace_id, run_id, capability_ids, jti) để
# services/company verify đúng phạm vi trước khi cho phép side effect.
# ---------------------------------------------------------------------------


def _decode_company_claims(token: str) -> dict:
    return pyjwt.decode(
        token,
        COMPANY_DELEGATION_SECRET,
        algorithms=["HS256"],
        audience="company",
        issuer="cosa",
    )


def test_mint_company_delegation_has_expected_shape():
    token = mint_company_delegation(
        sub="member-1",
        workspace_id="w1",
        run_id="r1",
        capability_ids=["finance.read"],
    )
    claims = _decode_company_claims(token)
    assert claims["iss"] == "cosa"
    assert claims["aud"] == "company"
    assert claims["sub"] == "member-1"
    assert claims["workspace_id"] == "w1"
    assert claims["run_id"] == "r1"
    assert claims["capability_ids"] == ["finance.read"]
    assert claims["principal_id"] == "user:member-1"
    assert claims["jti"]
    now = int(time.time())
    assert claims["exp"] - now <= 600
    assert claims["exp"] - now > 0


def test_mint_company_delegation_default_ttl_is_capped_at_600s():
    token = mint_company_delegation(
        sub="member-1",
        workspace_id="w1",
        run_id="r1",
        capability_ids=["finance.read"],
        ttl_seconds=99999,
    )
    claims = _decode_company_claims(token)
    now = int(time.time())
    assert claims["exp"] - now <= 600


def test_mint_company_delegation_generates_unique_jti_each_call():
    token1 = mint_company_delegation(
        sub="member-1", workspace_id="w1", run_id="r1", capability_ids=["finance.read"]
    )
    token2 = mint_company_delegation(
        sub="member-1", workspace_id="w1", run_id="r1", capability_ids=["finance.read"]
    )
    assert _decode_company_claims(token1)["jti"] != _decode_company_claims(token2)["jti"]


def test_mint_company_delegation_rejects_wrong_audience_or_issuer():
    token = mint_company_delegation(
        sub="member-1", workspace_id="w1", run_id="r1", capability_ids=["finance.read"]
    )
    with pytest.raises(Exception):
        pyjwt.decode(
            token,
            COMPANY_DELEGATION_SECRET,
            algorithms=["HS256"],
            audience="cosa",
            issuer="cosa",
        )
    with pytest.raises(Exception):
        pyjwt.decode(
            token,
            COMPANY_DELEGATION_SECRET,
            algorithms=["HS256"],
            audience="company",
            issuer="company",
        )
