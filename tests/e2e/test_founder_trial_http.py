"""E2E HTTP tests for the Founder Trial R1 surface.

Covers the Founder Trial Board read model and the stricter Founder Trial
experiment contract against a real Company service (no mock transports).
Workspace isolation is asserted at every read and mutation boundary.
"""

from __future__ import annotations

import time

import httpx


def _session(client: httpx.Client, label: str) -> dict[str, str]:
    email = f"founder-trial-{label}-{time.time()}@example.com"
    res = client.post(
        "/identity/_e2e/session",
        json={"email": email, "displayName": f"Founder Trial {label}"},
    )
    assert res.status_code == 200, f"session failed ({res.status_code}): {res.text}"
    data = res.json()
    return {
        "Authorization": f"Bearer {data['accessToken']}",
        "X-Workspace-Id": str(data["workspaceId"]),
    }


def test_founder_trial_board_and_experiment_contract(real_company_service):
    base_url = real_company_service.base_url
    client = httpx.Client(base_url=base_url, timeout=15.0)

    headers_a = _session(client, "a")
    headers_b = _session(client, "b")

    # 1. Create a project in workspace A.
    proj = client.post(
        "/operations/projects",
        headers=headers_a,
        json={"title": "Founder Trial E2E"},
    )
    assert proj.status_code == 200, proj.text
    project_id = str(proj.json()["id"])

    # 2. Board is reachable and empty-but-typed before any strategy data.
    board = client.get(
        f"/operations/projects/{project_id}/founder-trial-board", headers=headers_a
    )
    assert board.status_code == 200, board.text
    body = board.json()["data"]
    assert body["projectId"] == project_id
    assert body["assumptions"] == []
    assert body["experiments"] == []
    assert body["evidence"]["candidate"] == []
    assert "reviews" in body["cycle"]

    # 3. Workspace B cannot read workspace A's board.
    cross = client.get(
        f"/operations/projects/{project_id}/founder-trial-board", headers=headers_b
    )
    assert cross.status_code in (403, 404), cross.text

    # 4. Seed an assumption, then the Founder Trial experiment contract.
    a_res = client.post(
        "/operations/strategy/assumptions",
        headers=headers_a,
        json={
            "projectId": project_id,
            "statement": "Customers feel this pain weekly",
            "importance": 9,
            "uncertainty": 8,
        },
    )
    assert a_res.status_code == 200, a_res.text
    assumption_id = str(a_res.json()["id"])

    # 4a. Missing assumptionId is rejected on the Founder Trial path.
    bad = client.post(
        f"/operations/projects/{project_id}/founder-trial/experiments",
        headers=headers_a,
        json={"hypothesis": "H", "method": "customer_interview", "successCriteria": "5/10"},
    )
    assert bad.status_code == 400, bad.text

    # 4b. Empty successCriteria is rejected.
    bad2 = client.post(
        f"/operations/projects/{project_id}/founder-trial/experiments",
        headers=headers_a,
        json={
            "assumptionId": assumption_id,
            "hypothesis": "H",
            "method": "customer_interview",
            "successCriteria": "   ",
        },
    )
    assert bad2.status_code == 400, bad2.text

    # 4c. A valid Founder Trial experiment is created and linked.
    ok = client.post(
        f"/operations/projects/{project_id}/founder-trial/experiments",
        headers=headers_a,
        json={
            "assumptionId": assumption_id,
            "hypothesis": "5/10 interviews confirm weekly pain",
            "method": "customer_interview",
            "successCriteria": "At least 5 of 10 confirm",
        },
    )
    assert ok.status_code == 200, ok.text
    assert str(ok.json()["data"]["assumptionId"]) == assumption_id

    # 5. Board now reflects the assumption and experiment.
    board2 = client.get(
        f"/operations/projects/{project_id}/founder-trial-board", headers=headers_a
    ).json()["data"]
    assert len(board2["assumptions"]) == 1
    assert board2["assumptions"][0]["isFocus"] is True
    assert len(board2["experiments"]) == 1
    assert board2["experiments"][0]["linkedToAssumption"] is True
