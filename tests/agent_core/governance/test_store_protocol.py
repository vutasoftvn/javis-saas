from __future__ import annotations

from agent_core.governance.store import GovernanceStateStore


def test_governance_state_store_protocol_declares_the_expected_methods():
    expected = {
        "save_manifest_entry",
        "load_manifest",
        "save_governance_state",
        "load_governance_state",
        "save_evidence",
        "list_evidence",
    }

    assert expected.issubset(set(dir(GovernanceStateStore)))
