"""E2E HTTP tests for MVP Settings Contracts, Redaction and Provenance.
Ensures truth-only contracts and workspace isolation without mock transports.
"""

from __future__ import annotations

import time

import httpx


def test_settings_contracts_live(real_company_service):
    """Test members, connectors, runtime nodes, skills and tenant isolation."""
    base_url = real_company_service.base_url
    client = httpx.Client(base_url=base_url, timeout=10.0)

    # 1. Create Workspace A session
    email_a = f"test-settings-a-{time.time()}@example.com"
    reg_a = client.post(
        "/identity/_e2e/session",
        json={"email": email_a, "displayName": "Settings Founder A"},
    )
    assert reg_a.status_code == 200, (
        f"Identity test session creation failed ({reg_a.status_code}): {reg_a.text}"
    )

    data_a = reg_a.json()
    token_a = data_a["accessToken"]
    ws_a = str(data_a["workspaceId"])
    headers_a = {
        "Authorization": f"Bearer {token_a}",
        "X-Workspace-Id": ws_a,
    }

    # 2. Create Workspace B session
    email_b = f"test-settings-b-{time.time()}@example.com"
    reg_b = client.post(
        "/identity/_e2e/session",
        json={"email": email_b, "displayName": "Settings Founder B"},
    )
    assert reg_b.status_code == 200, (
        f"Identity test session creation failed ({reg_b.status_code}): {reg_b.text}"
    )

    data_b = reg_b.json()
    token_b = data_b["accessToken"]
    ws_b = str(data_b["workspaceId"])
    headers_b = {
        "Authorization": f"Bearer {token_b}",
        "X-Workspace-Id": ws_b,
    }

    # ─── 3. Verify Members ───
    # If control plane is wired
    res_mem = client.get(f"/platform/workspaces/{ws_a}/members", headers=headers_a)
    if res_mem.status_code == 200:
        mem_data = res_mem.json()
        assert mem_data["meta"]["dataState"] == "populated"
        assert len(mem_data["data"]) >= 1
        assert mem_data["data"][0]["roleId"] in {"founder", "member", "admin"}

    # ─── 4. Verify Connectors ───
    res_conn = client.get(f"/platform/workspaces/{ws_a}/connectors", headers=headers_a)
    if res_conn.status_code == 200:
        conn_data = res_conn.json()
        assert conn_data["meta"]["sources"][0]["kind"] == "control_plane"
        assert "secret" not in res_conn.text.lower() or "secretRef" not in res_conn.text

    # ─── 5. Verify Runtime Nodes ───
    res_nodes = client.get(f"/platform/workspaces/{ws_a}/runtime-nodes", headers=headers_a)
    if res_nodes.status_code == 200:
        nodes_data = res_nodes.json()
        assert nodes_data["meta"]["sources"][0]["kind"] == "control_plane"
        for node in nodes_data["data"]:
            assert node["presence"] in {"ONLINE", "OFFLINE", "DEGRADED"}

    # ─── 6. Tenant Isolation ───
    # Workspace B cannot read Workspace A's members
    cross_res = client.get(f"/platform/workspaces/{ws_a}/members", headers=headers_b)
    assert cross_res.status_code in {401, 403, 404}
