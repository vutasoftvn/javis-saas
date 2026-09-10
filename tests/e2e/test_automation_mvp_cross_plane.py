"""COSA Automation MVP (Task 10) — golden cross-plane path.

Real Company outbox -> signed apps/cosa intake -> services/cosa scheduler/lease
-> agent worker -> pinned manifest -> signed Company outcome projection. No
in-memory repository substitute, no mock transport, no skip.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from tests.e2e.seed import identity

pytestmark = pytest.mark.cross_plane

_DEFINITION_ID_PLACEHOLDER = "x"
_TERMINAL_TIMEOUT_S = 150.0
_POLL_STEP_S = 2.0


def _configure_and_publish(company, token: str, workspace_id: str, *, key: str) -> str:
    r = company.post(
        f"/operations/automation/definitions/{_DEFINITION_ID_PLACEHOLDER}/configuration",
        json={
            "automationKey": key,
            "configuration": {"projectId": "p1"},
            "triggerContract": {"kind": "manual"},
        },
        token=token,
        workspace_id=workspace_id,
    )
    assert r.status_code == 200, r.text
    definition_id = r.json()["data"]["id"]

    r = company.post(
        f"/operations/automation/definitions/{definition_id}/revisions",
        json={},
        token=token,
        workspace_id=workspace_id,
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["lifecycleState"] == "PUBLISHED"
    return definition_id


def _invoke(company, token, workspace_id, definition_id, client_request_id) -> dict[str, Any]:
    r = company.post(
        f"/operations/automation/definitions/{definition_id}/invocations",
        json={"command": {"triggerKind": "manual", "clientRequestId": client_request_id}},
        token=token,
        workspace_id=workspace_id,
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]


def test_configure_publish_invoke_twice_yields_one_run_and_completes(
    real_cosa_stack, disposable_cluster
) -> None:
    seeded = identity.seed_workspace(real_cosa_stack, disposable_cluster)
    company = real_cosa_stack.company
    token = seeded.owner_token
    ws = seeded.workspace_id

    definition_id = _configure_and_publish(company, token, ws, key="operating.weekly-review")

    first = _invoke(company, token, ws, definition_id, "run-once")
    second = _invoke(company, token, ws, definition_id, "run-once")
    assert first["id"] == second["id"], "same client request id must return the original invocation"
    assert second["deduplicated"] is True

    invocation_id = first["id"]

    deadline = time.monotonic() + _TERMINAL_TIMEOUT_S
    state = None
    while time.monotonic() < deadline:
        r = company.get(
            f"/operations/automation/invocations/{invocation_id}/inspector",
            token=token,
            workspace_id=ws,
        )
        if r.status_code == 200:
            state = r.json()["data"]["state"]
            if state in ("COMPLETED", "FAILED", "BLOCKED", "CANCELLED"):
                break
        time.sleep(_POLL_STEP_S)

    assert state == "COMPLETED", f"automation run did not complete cross-plane (last state={state})"

    r = company.get(
        f"/operations/automation/invocations/{invocation_id}/inspector",
        token=token,
        workspace_id=ws,
    )
    data = r.json()["data"]
    assert data["revisionHash"], "inspector must project the pinned revision hash"
    assert "source_refs" in data["evidenceRefs"] or "digest_markdown" in data["evidenceRefs"]


def test_commercial_outbound_draft_cannot_deliver_externally(
    real_cosa_stack, disposable_cluster
) -> None:
    seeded = identity.seed_workspace(real_cosa_stack, disposable_cluster)
    company = real_cosa_stack.company
    token, ws = seeded.owner_token, seeded.workspace_id

    definition_id = _configure_and_publish(company, token, ws, key="commercial.outbound-draft")
    inv = _invoke(company, token, ws, definition_id, "draft-1")

    deadline = time.monotonic() + _TERMINAL_TIMEOUT_S
    data: dict[str, Any] = {}
    while time.monotonic() < deadline:
        r = company.get(
            f"/operations/automation/invocations/{inv['id']}/inspector", token=token, workspace_id=ws
        )
        if r.status_code == 200 and r.json()["data"]["state"] in (
            "COMPLETED", "FAILED", "BLOCKED", "CANCELLED",
        ):
            data = r.json()["data"]
            break
        time.sleep(_POLL_STEP_S)

    assert data.get("state") == "COMPLETED"
    # The draft artifact is evidence; nothing is delivered.
    for ref in data.get("evidenceRefs", []):
        assert "send" not in ref and "deliver" not in ref and "email" not in ref
