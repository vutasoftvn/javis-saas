from __future__ import annotations

from apps.cosa.capabilities.access_matrix import MATRIX

EXPECTED_REGISTERED = {
    "business.read",
    "startup_os.goal.create",
    "startup_os.project.triage",
    "operations.task.advance",
    "okr.objective.list",
    "okr.key_result.create",
    "okr.key_result.checkin",
    "strategy.evidence.create",
    "strategy.pilot.create_draft",
    "strategy.pilot.get",
    "legal.obligation.create_draft",
    "venture.profile.propose_update",
}


def test_all_expected_capabilities_are_registered(registered_capability_ids: set[str]) -> None:
    assert EXPECTED_REGISTERED <= registered_capability_ids
    assert EXPECTED_REGISTERED <= set(MATRIX)
