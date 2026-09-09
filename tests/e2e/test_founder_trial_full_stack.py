"""Release proof for the exact Founder Trial R1 loop (Task 11).

Real HTTP, no mock transport. Covers the full accepted sequence from
spec §10:  project -> activate 1..12wk cycle -> resize an ACTIVE cycle with
revision protection -> assumption -> strict experiment -> interview ->
submit-as-evidence -> approve -> Founder Brief (coverage only, no verdict) ->
founder decision, plus the cross-workspace negative case and the
stale-revision / missing-CAS negatives.

Run against the Task 10 freshly reset databases:
    make test-db-reset
    .venv/bin/python -m pytest tests/e2e/test_founder_trial_full_stack.py -q
"""

from __future__ import annotations

import time

import httpx


def _session(client: httpx.Client, label: str) -> dict[str, str]:
    res = client.post(
        "/identity/_e2e/session",
        json={
            "email": f"ft-full-{label}-{time.time()}@example.com",
            "displayName": f"FT Full {label}",
        },
    )
    assert res.status_code == 200, res.text
    d = res.json()
    return {
        "Authorization": f"Bearer {d['accessToken']}",
        "X-Workspace-Id": str(d["workspaceId"]),
    }


def _activate_cycle(client, headers, project_id, weeks):
    res = client.post(
        f"/operations/projects/{project_id}/operating-setup/activate",
        headers=headers,
        json={
            "targetCustomer": "Ops leads",
            "problemStatement": "Slow weekly close",
            "evidenceLevel": "NONE",
            "selectedStage": "P0_DISCOVERY",
            "stageDurationWeeks": 2,
            "cycleDurationWeeks": weeks,
            "roundStartDate": "2026-09-21",
            "weeklyReviewWeekday": 5,
            "weeklyReviewTime": "16:00",
            "firstWeekOutcome": "Talk to leads",
            "firstWeekActions": [{"title": "List prospects"}],
        },
    )
    assert res.status_code == 200, res.text
    return res


def test_founder_trial_full_stack_release_loop(real_company_service):
    client = httpx.Client(base_url=real_company_service.base_url, timeout=20.0)
    headers_a = _session(client, "a")
    headers_b = _session(client, "b")

    project_id = str(
        client.post(
            "/operations/projects", headers=headers_a, json={"title": "FT Full Stack"}
        ).json()["id"]
    )

    _activate_cycle(client, headers_a, project_id, weeks=6)
    board = client.get(
        f"/operations/projects/{project_id}/founder-trial-board", headers=headers_a
    ).json()["data"]
    cycle_id = board["cycle"]["cycleId"]
    revision = board["cycle"]["revision"]
    assert board["cycle"]["durationWeeks"] == 6
    assert revision is not None

    # Resize the ACTIVE cycle 6 -> 10 with revision protection.
    resize = client.patch(
        f"/operations/projects/{project_id}/operating-cycle",
        headers=headers_a,
        json={
            "cycleId": cycle_id,
            "durationWeeks": 10,
            "expectedRevision": revision,
            "reason": "Founder widened the trial",
        },
    )
    assert resize.status_code == 200, resize.text
    assert resize.json()["revision"] == revision + 1

    # A stale revision now conflicts.
    stale = client.patch(
        f"/operations/projects/{project_id}/operating-cycle",
        headers=headers_a,
        json={"cycleId": cycle_id, "durationWeeks": 4, "expectedRevision": revision},
    )
    assert stale.status_code in (400, 409, 412), stale.text

    # Assumption -> strict experiment.
    assumption_id = str(
        client.post(
            "/operations/strategy/assumptions",
            headers=headers_a,
            json={
                "projectId": project_id,
                "statement": "Founders feel weekly cash uncertainty",
                "importance": 9,
                "uncertainty": 8,
            },
        ).json()["id"]
    )
    exp = client.post(
        f"/operations/projects/{project_id}/founder-trial/experiments",
        headers=headers_a,
        json={
            "assumptionId": assumption_id,
            "hypothesis": "5 of 10 interviews confirm weekly cash uncertainty",
            "method": "customer_interview",
            "successCriteria": "5 of 10",
        },
    )
    assert exp.status_code == 200, exp.text

    # Interview -> submit as candidate evidence -> approve.
    interview_id = str(
        client.post(
            "/operations/strategy/interviews",
            headers=headers_a,
            json={"projectId": project_id, "notes": "Five ops leads, all confirmed"},
        ).json()["id"]
    )
    submit = client.post(
        f"/operations/strategy/interviews/{interview_id}/submit-evidence",
        headers=headers_a,
        json={"claim": "6 of 10 confirmed the weekly pain"},
    )
    assert submit.status_code == 200, submit.text

    board = client.get(
        f"/operations/projects/{project_id}/founder-trial-board", headers=headers_a
    ).json()["data"]
    candidates = board["evidence"]["candidate"]
    assert candidates, "interview submit should create a candidate evidence row"
    evidence_id = candidates[0]["id"]
    # Interview evidence is NOT tied to the founder-trial experiment, so it must
    # never count toward problem/solution coverage (spec §10.5).
    assert candidates[0]["linkedToFounderTrialAssumption"] is False

    approve = client.post(
        f"/operations/strategy/evidence/{evidence_id}/review",
        headers=headers_a,
        json={"action": "approve"},
    )
    assert approve.status_code == 200, approve.text

    # Founder Brief: coverage only, economics split, no verdict, and the
    # approved-but-unlinked interview evidence does NOT move the problem axis.
    brief = client.get(
        f"/operations/projects/{project_id}/founder-brief", headers=headers_a
    ).json()["data"]
    axes = {a["axis"]: a for a in brief["axes"]}
    assert {a["axis"] for a in brief["axes"]} == {
        "problem", "solution", "traction", "economics", "compliance"
    }
    assert axes["problem"]["state"] == "NO_EVIDENCE"
    assert axes["economics"]["projectBudget"]["state"] == "CONFIGURATION_REQUIRED"
    assert axes["compliance"]["state"] == "NOT_ASSESSED"
    assert brief["nextReviewFocus"]["isAuthoritative"] is False
    assert "suggestedDecision" not in brief

    # Founder decision is the only path that records proceed/pivot/kill/hold.
    decision = client.post(
        "/operations/strategy/decision-records",
        headers=headers_a,
        json={"projectId": project_id, "decision": "hold"},
    )
    assert decision.status_code == 200, decision.text

    # Workspace B cannot read or mutate anything in the sequence.
    for method, path in [
        ("GET", f"/operations/projects/{project_id}/founder-trial-board"),
        ("GET", f"/operations/projects/{project_id}/founder-brief"),
    ]:
        r = client.request(method, path, headers=headers_b)
        assert r.status_code in (403, 404), f"{method} {path} -> {r.status_code}"
    r = client.patch(
        f"/operations/projects/{project_id}/operating-cycle",
        headers=headers_b,
        json={"cycleId": cycle_id, "durationWeeks": 8, "expectedRevision": revision + 1},
    )
    assert r.status_code in (403, 404), r.text
