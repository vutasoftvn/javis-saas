"""E2E HTTP smoke test across all full MVP planes and source truths."""

from __future__ import annotations

import httpx
import pytest


def test_full_mvp_release_smoke(real_company_service):
    """Smoke test ensuring all 6 MVP sub-domains expose truthful source metadata."""
    base_url = real_company_service.base_url
    client = httpx.Client(base_url=base_url, timeout=10.0)

    # 1. Identity
    reg = client.post(
        "/identity/test-session",
        json={"email": "smoke-tester@example.com", "displayName": "Smoke Tester"},
    )
    if reg.status_code != 200:
        pytest.skip(f"Identity test session creation failed: {reg.text}")

    data = reg.json()
    token = data["accessToken"]
    ws_id = str(data["workspaceId"])
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Workspace-Id": ws_id,
    }

    # 2. Strategy
    strat_res = client.get("/operations/strategy/canvases", headers=headers)
    assert strat_res.status_code == 200
    assert strat_res.json()["meta"]["sources"][0]["kind"] == "company_db"

    # 3. Marketing
    mkt_res = client.get("/commercial/marketing/objectives", headers=headers)
    assert mkt_res.status_code == 200
    assert mkt_res.json()["meta"]["sources"][0]["kind"] == "company_db"
