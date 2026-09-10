"""COSA Automation MVP (Task 10) — tenant isolation + authorization negatives.

Workspace B cannot read, configure, invoke, cancel, approve or project
workspace A's Automation chain; a non-founder member cannot publish or suspend.
"""

from __future__ import annotations

import pytest

from tests.e2e.seed import identity

pytestmark = pytest.mark.cross_plane


def _configure(company, token, ws, *, key="operating.weekly-review"):
    r = company.post(
        "/operations/automation/definitions/x/configuration",
        json={
            "automationKey": key,
            "configuration": {"projectId": "p1"},
            "triggerContract": {"kind": "manual"},
        },
        token=token,
        workspace_id=ws,
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]


def test_foreign_workspace_cannot_touch_another_workspaces_automation(
    real_cosa_stack, disposable_cluster
) -> None:
    a = identity.seed_workspace(real_cosa_stack, disposable_cluster)
    b = identity.seed_workspace(real_cosa_stack, disposable_cluster)
    company = real_cosa_stack.company

    definition_id = _configure(company, a.owner_token, a.workspace_id)
    r = company.post(
        f"/operations/automation/definitions/{definition_id}/revisions",
        json={}, token=a.owner_token, workspace_id=a.workspace_id,
    )
    assert r.status_code == 200

    r = company.post(
        f"/operations/automation/definitions/{definition_id}/invocations",
        json={"command": {"triggerKind": "manual", "clientRequestId": "x"}},
        token=a.owner_token, workspace_id=a.workspace_id,
    )
    invocation_id = r.json()["data"]["id"]

    # B, targeting A's workspace with B's token -> fail-closed everywhere.
    for method, path in [
        ("get", "/operations/automation/definitions"),
        ("get", f"/operations/automation/definitions/{definition_id}"),
        ("get", f"/operations/automation/invocations/{invocation_id}"),
        ("get", f"/operations/automation/invocations/{invocation_id}/inspector"),
    ]:
        resp = getattr(company, method)(path, token=b.owner_token, workspace_id=a.workspace_id)
        assert resp.status_code in (401, 403, 404), f"{method} {path} -> {resp.status_code}"

    for path in [
        f"/operations/automation/definitions/{definition_id}/configuration",
        f"/operations/automation/definitions/{definition_id}/revisions",
        f"/operations/automation/definitions/{definition_id}/suspension",
        f"/operations/automation/invocations/{invocation_id}/cancellation",
    ]:
        resp = company.post(path, json={}, token=b.owner_token, workspace_id=a.workspace_id)
        assert resp.status_code in (400, 401, 403, 404), f"POST {path} -> {resp.status_code}"


def test_non_founder_member_cannot_publish_or_suspend(
    real_cosa_stack, disposable_cluster
) -> None:
    seeded = identity.seed_workspace(real_cosa_stack, disposable_cluster, with_member=True)
    company = real_cosa_stack.company
    ws = seeded.workspace_id

    definition_id = _configure(company, seeded.owner_token, ws)

    r = company.post(
        f"/operations/automation/definitions/{definition_id}/revisions",
        json={}, token=seeded.member_token, workspace_id=ws,
    )
    assert r.status_code in (401, 403), r.text

    # Owner publishes, then member cannot suspend.
    r = company.post(
        f"/operations/automation/definitions/{definition_id}/revisions",
        json={}, token=seeded.owner_token, workspace_id=ws,
    )
    assert r.status_code == 200
    r = company.post(
        f"/operations/automation/definitions/{definition_id}/suspension",
        json={}, token=seeded.member_token, workspace_id=ws,
    )
    assert r.status_code in (401, 403)
