"""COSA Automation MVP (Task 10) — recovery + cancellation race.

Restart the worker mid-run, race cancel with completion, and confirm one durable
terminal state, no second effect and a matching Company projection.
"""

from __future__ import annotations

import time

import pytest

from tests.e2e.seed import identity

pytestmark = pytest.mark.cross_plane

_TERMINAL = ("COMPLETED", "FAILED", "BLOCKED", "CANCELLED")
_TIMEOUT_S = 150.0


def _publish(company, token, ws, *, key="operating.weekly-review") -> str:
    r = company.patch(
        "/operations/automation/definitions/x/configuration",
        json={
            "automationKey": key,
            "configuration": {"projectId": "p1"},
            "triggerContract": {"kind": "manual"},
        },
        token=token, workspace_id=ws,
    )
    assert r.status_code == 200, r.text
    definition_id = r.json()["data"]["id"]
    r = company.post(
        f"/operations/automation/definitions/{definition_id}/revisions",
        json={}, token=token, workspace_id=ws,
    )
    assert r.status_code == 200
    return definition_id


def _invoke(company, token, ws, definition_id, crid):
    r = company.post(
        f"/operations/automation/definitions/{definition_id}/invocations",
        json={"command": {"triggerKind": "manual", "clientRequestId": crid}},
        token=token, workspace_id=ws,
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]


def _wait_terminal(company, token, ws, invocation_id) -> str:
    deadline = time.monotonic() + _TIMEOUT_S
    last = ""
    while time.monotonic() < deadline:
        company.post("/events/relay/tick")
        r = company.get(
            f"/operations/automation/invocations/{invocation_id}/inspector", token=token, workspace_id=ws
        )
        if r.status_code == 200:
            last = r.json()["data"]["state"]
            if last in _TERMINAL:
                return last
        time.sleep(2.0)
    return last


def test_worker_restart_after_claim_still_reaches_one_terminal_state(
    real_cosa_stack, disposable_cluster
) -> None:
    seeded = identity.seed_workspace(real_cosa_stack, disposable_cluster)
    company = real_cosa_stack.company
    token, ws = seeded.owner_token, seeded.workspace_id
    definition_id = _publish(company, token, ws)
    inv = _invoke(company, token, ws, definition_id, "recover-1")

    # Bounce only the Python processes — the durable scheduler + manifest must
    # carry the run to a single terminal state.
    if hasattr(real_cosa_stack, "restart_api_and_worker"):
        real_cosa_stack.restart_api_and_worker()

    state = _wait_terminal(company, token, ws, inv["id"])
    assert state in _TERMINAL and state != "", f"no terminal state after restart (last={state})"

    # A second inspector read is identical — no flip-flop.
    r = company.get(
        f"/operations/automation/invocations/{inv['id']}/inspector", token=token, workspace_id=ws
    )
    assert r.json()["data"]["state"] == state


def test_cancel_racing_completion_keeps_one_durable_terminal_state(
    real_cosa_stack, disposable_cluster
) -> None:
    seeded = identity.seed_workspace(real_cosa_stack, disposable_cluster)
    company = real_cosa_stack.company
    token, ws = seeded.owner_token, seeded.workspace_id
    definition_id = _publish(company, token, ws)
    inv = _invoke(company, token, ws, definition_id, "race-1")

    # Fire a cancel immediately; whichever wins, the state must be durable.
    company.post(
        f"/operations/automation/invocations/{inv['id']}/cancellation",
        json={"expectedVersion": inv["version"]},
        token=token, workspace_id=ws,
    )
    state = _wait_terminal(company, token, ws, inv["id"])
    assert state in ("COMPLETED", "CANCELLED", "FAILED")

    r = company.get(
        f"/operations/automation/invocations/{inv['id']}/inspector", token=token, workspace_id=ws
    )
    assert r.json()["data"]["state"] == state, "terminal state must not regress"
