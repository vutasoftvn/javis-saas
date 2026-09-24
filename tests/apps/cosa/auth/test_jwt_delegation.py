from __future__ import annotations

import time

import jwt as pyjwt
import pytest

from apps.cosa.auth.jwt import (
    mint_company_delegation,
    mint_control_plane_delegation,
)

COMPANY_DELEGATION_SECRET = "cosa-company-delegation-dev-secret-change-in-prod"
CONTROL_DELEGATION_SECRET = "cosa-control-delegation-dev-secret-change-in-prod"


# ---------------------------------------------------------------------------
# mint_company_delegation — scoped COSA -> Company delegation (Task 3).
#
# Khác hẳn mint_local_delegation_token (chỉ
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


def _decode_control_delegation_claims(token: str) -> dict:
    return pyjwt.decode(
        token,
        CONTROL_DELEGATION_SECRET,
        algorithms=["HS256"],
        audience="cosa_control",
        issuer="cosa_apps",
    )


def test_mint_control_plane_delegation_has_expected_shape():
    """B5 fix — mint_control_plane_delegation() mint token có cấu trúc mà
    services/cosa/services/token.service.ts::verifyControlDelegationToken
    verify trực tiếp, KHÔNG round-trip sang services/company (khác bug đã
    khiến verifyWorkspaceMembership luôn fail 403 với token platform hợp lệ)."""
    token = mint_control_plane_delegation(sub="platform_user_1", workspace_id="ws_1", role="founder")
    claims = _decode_control_delegation_claims(token)
    assert claims["iss"] == "cosa_apps"
    assert claims["aud"] == "cosa_control"
    assert claims["sub"] == "platform_user_1"
    assert claims["workspace_id"] == "ws_1"
    assert claims["role"] == "founder"
    assert claims["jti"]
    now = int(time.time())
    assert claims["exp"] - now <= 600
    assert claims["exp"] - now > 0


def test_mint_control_plane_delegation_default_ttl_is_capped_at_600s():
    token = mint_control_plane_delegation(
        sub="platform_user_1", workspace_id="ws_1", role="founder", ttl_seconds=99999
    )
    claims = _decode_control_delegation_claims(token)
    now = int(time.time())
    assert claims["exp"] - now <= 600


def test_mint_control_plane_delegation_generates_unique_jti_each_call():
    token1 = mint_control_plane_delegation(sub="platform_user_1", workspace_id="ws_1", role="founder")
    token2 = mint_control_plane_delegation(sub="platform_user_1", workspace_id="ws_1", role="founder")
    assert (
        _decode_control_delegation_claims(token1)["jti"]
        != _decode_control_delegation_claims(token2)["jti"]
    )


def test_mint_control_plane_delegation_rejects_wrong_audience_or_issuer():
    token = mint_control_plane_delegation(sub="platform_user_1", workspace_id="ws_1", role="founder")
    with pytest.raises(Exception):
        pyjwt.decode(
            token,
            CONTROL_DELEGATION_SECRET,
            algorithms=["HS256"],
            audience="cosa",
            issuer="cosa_apps",
        )
    with pytest.raises(Exception):
        pyjwt.decode(
            token,
            CONTROL_DELEGATION_SECRET,
            algorithms=["HS256"],
            audience="cosa_control",
            issuer="cosa",
        )


def test_mint_control_plane_delegation_uses_different_secret_than_company_delegation():
    """Đảm bảo 2 chiều delegation (apps/cosa->company vs apps/cosa->cosa)
    không lẫn secret — 1 token mint cho chiều này không verify được ở chiều kia."""
    control_token = mint_control_plane_delegation(sub="platform_user_1", workspace_id="ws_1", role="founder")
    with pytest.raises(Exception):
        pyjwt.decode(
            control_token,
            COMPANY_DELEGATION_SECRET,
            algorithms=["HS256"],
            audience="cosa_control",
            issuer="cosa_apps",
        )
