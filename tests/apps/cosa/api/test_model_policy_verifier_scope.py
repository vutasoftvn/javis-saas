"""Model-policy REST nhận scope nội bộ `verifier` (thẩm phán độc lập) mà KHÔNG
biến nó thành profile công khai."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from tests.apps.cosa.api.test_model_policy_routes import (  # noqa: F401
    mock_company_client,
    setup_env,
)


def test_resolve_agent_spec_id_accepts_verifier():
    from apps.cosa.api.model_policy_routes import _resolve_agent_spec_id

    assert _resolve_agent_spec_id("verifier") == "cosa.agents.verifier"


def test_unknown_profile_still_404():
    from apps.cosa.api.model_policy_routes import _resolve_agent_spec_id

    with pytest.raises(HTTPException) as exc_info:
        _resolve_agent_spec_id("ghost-profile")
    assert exc_info.value.status_code == 404


def test_verifier_is_still_not_a_public_profile():
    from apps.cosa.agents.agent_profile_specs import AGENT_PROFILE_SPECS

    assert "verifier" not in AGENT_PROFILE_SPECS


def test_put_then_get_policy_for_verifier_roundtrips(setup_env):  # noqa: F811
    client = setup_env["client"]
    created = client.post(
        "/agent/settings/model-providers",
        json={"provider_type": "openai_api", "profile_id": "judge-model", "api_key": "k"},
    )
    assert created.status_code == 201

    put = client.put(
        "/agent/settings/model-policies/verifier",
        json={"primary_profile_id": "judge-model", "fallback_profile_ids": []},
    )
    assert put.status_code == 200

    got = client.get("/agent/settings/model-policies/verifier")
    assert got.status_code == 200
    data = got.json()["data"]
    assert data["scope_key"] == "cosa.agents.verifier"
    assert data["resolved_profile_id"] == "judge-model"
    assert data["is_system_default"] is False
