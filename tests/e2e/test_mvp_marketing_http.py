"""E2E HTTP tests for MVP Marketing Contracts and Provenance.
Ensures truth-only contracts and workspace isolation without mock transports.
"""

from __future__ import annotations

import time
import httpx
import pytest


def test_marketing_contracts_live(real_company_service):
    """Test marketing context, objectives, campaigns, experiments and tenant isolation."""
    base_url = real_company_service.base_url
    client = httpx.Client(base_url=base_url, timeout=10.0)

    # 1. Create Workspace A session
    email_a = f"test-mkt-a-{time.time()}@example.com"
    reg_a = client.post(
        "/identity/test-session",
        json={"email": email_a, "displayName": "Marketing Founder A"},
    )
    if reg_a.status_code != 200:
        pytest.skip(f"Identity test session creation failed ({reg_a.status_code}): {reg_a.text}")

    data_a = reg_a.json()
    token_a = data_a["accessToken"]
    ws_a = str(data_a["workspaceId"])
    headers_a = {
        "Authorization": f"Bearer {token_a}",
        "X-Workspace-Id": ws_a,
    }

    # 2. Create Workspace B session
    email_b = f"test-mkt-b-{time.time()}@example.com"
    reg_b = client.post(
        "/identity/test-session",
        json={"email": email_b, "displayName": "Marketing Founder B"},
    )
    if reg_b.status_code != 200:
        pytest.skip(f"Identity test session creation failed ({reg_b.status_code}): {reg_b.text}")

    data_b = reg_b.json()
    token_b = data_b["accessToken"]
    ws_b = str(data_b["workspaceId"])
    headers_b = {
        "Authorization": f"Bearer {token_b}",
        "X-Workspace-Id": ws_b,
    }

    # ─── Marketing Context ───
    # Initial get
    ctx_res = client.get("/commercial/marketing-context", headers=headers_a)
    assert ctx_res.status_code == 200

    # Update context
    put_ctx = client.put(
        "/commercial/marketing-context",
        headers=headers_a,
        json={
            "category": "Autonomous Marketing System",
            "positioningStatement": "Zero-hallucination agentic growth engine",
        },
    )
    assert put_ctx.status_code == 200
    assert put_ctx.json()["data"]["productMarketing"]["category"] == "Autonomous Marketing System"

    # ─── Objectives ───
    # List objectives (empty)
    list_obj_empty = client.get("/commercial/marketing/objectives", headers=headers_a)
    assert list_obj_empty.status_code == 200
    assert list_obj_empty.json()["meta"]["dataState"] == "empty"
    assert list_obj_empty.json()["data"] == []

    # Create objective
    create_obj = client.post(
        "/commercial/marketing/objectives",
        headers=headers_a,
        json={
            "title": "Scale Qualified Inbound Leads",
            "targetMetric": "inbound_leads",
            "targetValue": 250.0,
        },
    )
    assert create_obj.status_code == 200
    obj_data = create_obj.json()["data"]
    assert obj_data["title"] == "Scale Qualified Inbound Leads"
    assert obj_data["currentValue"] is None

    # ─── Campaigns ───
    create_camp = client.post(
        "/commercial/marketing/campaigns",
        headers=headers_a,
        json={
            "name": "Q4 Global Growth Campaign",
            "budget": 25000000.0,
            "funnelStage": "discover",
        },
    )
    assert create_camp.status_code == 200
    camp_data = create_camp.json()["data"]
    camp_id = camp_data["id"]
    assert camp_data["name"] == "Q4 Global Growth Campaign"
    assert camp_data["budget"] == 25000000.0

    # List campaigns in Workspace A
    list_camp_a = client.get("/commercial/marketing/campaigns", headers=headers_a)
    assert list_camp_a.status_code == 200
    assert len(list_camp_a.json()["data"]) == 1

    # ─── Experiments ───
    create_exp = client.post(
        "/commercial/marketing/experiments",
        headers=headers_a,
        json={
            "campaignId": camp_id,
            "name": "Interactive Demo vs Video Demo",
            "hypothesis": "Interactive demo boosts trial starts by 15%",
            "baselineValue": 8.0,
            "targetValue": 9.2,
        },
    )
    assert create_exp.status_code == 200
    exp_data = create_exp.json()["data"]
    assert exp_data["name"] == "Interactive Demo vs Video Demo"

    # ─── Observed Metrics ───
    obs_res = client.get("/commercial/marketing/metrics/observed", headers=headers_a)
    assert obs_res.status_code == 200
    assert obs_res.json()["meta"]["sources"][0]["kind"] == "external_connector"

    # ─── Tenant Isolation Assertions ───
    # Workspace B sees no campaigns
    list_camp_b = client.get("/commercial/marketing/campaigns", headers=headers_b)
    assert list_camp_b.status_code == 200
    assert list_camp_b.json()["data"] == []

    # Workspace B sees no objectives
    list_obj_b = client.get("/commercial/marketing/objectives", headers=headers_b)
    assert list_obj_b.status_code == 200
    assert list_obj_b.json()["data"] == []

    # Workspace B cannot access Workspace A's headers
    cross_res = client.get("/commercial/marketing/campaigns", headers={"Authorization": f"Bearer {token_b}", "X-Workspace-Id": ws_a})
    assert cross_res.status_code in {401, 403}
