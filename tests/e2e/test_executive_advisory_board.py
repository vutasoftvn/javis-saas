"""E2E Executive Advisory Board: lifecycle, cancellation và operations roles trên stack 4 plane thật.

Office role là Workspace-scoped, Project chỉ deploy Workspace Agent; frame pin cả Project deployment
lẫn advisor overlay (spec 2026-09-20-governed-advisor-overlay-and-truthful-hub-design.md).
"""

from __future__ import annotations

import httpx
import pytest

from apps.cosa.agents.catalog import CATALOG_BY_PROFILE
from tests.e2e.advisor_board import Board, _bare_board, advance_to
from tests.e2e.seed import identity

pytestmark = pytest.mark.cross_plane


def _foreign_headers(stack, cluster) -> dict[str, str]:
    other = identity.seed_workspace(stack, cluster)
    return {"Authorization": f"Bearer {other.owner_token}", "X-Workspace-Id": other.workspace_id}


def test_executive_board_full_lifecycle(advisor_stack, advisor_cluster):
    board = Board(advisor_stack, advisor_cluster)
    delib_id, framed = board.frame("Should we deploy $500k into enterprise sales or PLG automation?")
    assert framed["state"] == "ANALYSIS_QUEUED"
    frame_version = framed["activeFrameVersion"]

    # Worker kiểm authority: pin trả về gồm cả Project deployment và overlay.
    auth = board.authority(delib_id, "cfo")
    assert auth.status_code == 200, auth.text
    pin = auth.json()["rolePin"]
    assert pin["roleKey"] == "cfo"
    assert pin["deployment"]["projectAgentDeploymentId"] == board.deployment_id
    assert pin["overlay"]["overlaySpecId"] == "cosa.executive.cfo"

    cb = board.completed_callback(
        delib_id, "cfo", frame_version=frame_version, conclusion="Allocate 70% to PLG automation."
    )
    assert cb.status_code == 200, cb.text
    assert cb.json()["status"] == "COMPLETED"
    assert cb.json()["state"] == "AWAITING_FOUNDER"

    retry = board.completed_callback(
        delib_id, "cfo", frame_version=frame_version, conclusion="Allocate 70% to PLG automation."
    )
    assert retry.status_code == 200, retry.text
    assert retry.json()["id"] == cb.json()["id"]

    details = board.deliberation(delib_id)
    assert details["state"] == "AWAITING_FOUNDER"
    assert len(details["analyses"]) == 1

    decision = board.call(
        "post",
        f"/operations/projects/{board.project_id}/deliberations/{delib_id}/decision",
        json={"decisionType": "APPROVE", "notes": "Approved PLG first approach."},
    )
    assert decision.status_code == 200, decision.text
    assert board.deliberation(delib_id)["state"] == "DECIDED"

    foreign = httpx.get(
        f"{board.company.base_url}/operations/projects/{board.project_id}/deliberations/{delib_id}",
        headers=_foreign_headers(advisor_stack, advisor_cluster),
        timeout=20.0,
    )
    assert foreign.status_code in (403, 404)


def test_executive_board_cancellation_and_rejection(advisor_stack, advisor_cluster):
    board = Board(advisor_stack, advisor_cluster)
    delib_id, framed = board.frame("Test question?")

    cancel = board.call(
        "post",
        f"/operations/projects/{board.project_id}/deliberations/{delib_id}/cancel",
        json={"reason": "Board pivot"},
    )
    assert cancel.status_code == 200, cancel.text

    late = board.completed_callback(delib_id, "cfo", frame_version=framed["activeFrameVersion"])
    assert late.status_code in (400, 412), "Cancelled deliberation must reject callbacks"
    assert board.deliberation(delib_id).get("analyses") in (None, [])


def test_operations_roles_lifecycle_dual_frame_and_isolation(advisor_stack, advisor_cluster):
    """chief_of_staff + coo dùng chung profile operations:
    1. Chưa có profile -> office UNAVAILABLE.  2. Profile active -> AVAILABLE_NOT_ACTIVATED.
    3. Kích hoạt office cả hai.  4. Deploy + stage P2 -> frame 2 role, pin đúng spec operations
    và overlay skill.  5. Callback 2 role -> AWAITING_FOUNDER, 2 analyses.  6. Cross-workspace bị chặn."""
    board = _bare_board(advisor_stack, advisor_cluster, "operations")
    roles = board.roles()
    for key in ("chief_of_staff", "coo"):
        assert roles[key]["officeState"] == "UNAVAILABLE"
        assert roles[key]["disabledReason"] == "UNDERLYING_PROFILE_UNAVAILABLE"
        early = board.call(
            "post",
            f"/operations/workspaces/{board.ws}/executive-roles/{key}/activate",
            json={"expectedVersion": 1},
        )
        assert early.status_code in (400, 412), early.text

    board.activate_profile()
    roles = board.roles()
    assert roles["chief_of_staff"]["officeState"] == "AVAILABLE_NOT_ACTIVATED"
    assert roles["coo"]["officeState"] == "AVAILABLE_NOT_ACTIVATED"

    for key in ("chief_of_staff", "coo"):
        assert board.activate_role(key).json()["state"] == "ACTIVE"
    board.deploy()
    board.seed_compliance()
    advance_to(board, "P2_SOLUTION_VALIDATION")

    delib_id = board.draft("Q4 Operating Model Review")
    framed = board.frame_raw(
        delib_id,
        "How should we restructure operations to scale cross-functional delivery in Q4?",
        ["chief_of_staff", "coo"],
    )
    assert framed.status_code == 200, framed.text
    assert framed.json()["state"] == "ANALYSIS_QUEUED"

    ops_spec = CATALOG_BY_PROFILE["operations"].agent_spec
    for key, skill in (("chief_of_staff", "executive.chief-of-staff"), ("coo", "executive.coo-advisor")):
        auth = board.authority(delib_id, key)
        assert auth.status_code == 200, auth.text
        pin = auth.json()["rolePin"]
        assert pin["deployment"]["specId"] == ops_spec.id
        assert pin["deployment"]["specHash"] == ops_spec.compute_hash()
        assert skill in [s["skillId"] for s in pin["overlay"]["skillPins"]]

    first = board.completed_callback(delib_id, "chief_of_staff", conclusion="Weekly cadence.")
    assert first.status_code == 200, first.text
    assert first.json()["state"] == "ANALYZING"
    second = board.completed_callback(delib_id, "coo", conclusion="Automate fulfilment.")
    assert second.status_code == 200, second.text
    assert second.json()["state"] == "AWAITING_FOUNDER"

    details = board.deliberation(delib_id)
    assert {a["roleKey"] for a in details["analyses"]} == {"chief_of_staff", "coo"}

    foreign = httpx.get(
        f"{board.company.base_url}/operations/projects/{board.project_id}/deliberations/{delib_id}",
        headers=_foreign_headers(advisor_stack, advisor_cluster),
        timeout=20.0,
    )
    assert foreign.status_code in (403, 404)
