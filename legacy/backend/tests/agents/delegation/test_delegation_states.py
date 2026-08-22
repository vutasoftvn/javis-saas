import pytest

from core import feature_flags


def test_terminal_delegation_state_cannot_reopen():
    """A stale worker must not reopen a completed provider side effect."""
    from workforce.agents.delegation.states import transition_delegation

    with pytest.raises(ValueError, match="terminal"):
        transition_delegation("succeeded", "queued")


def test_step_completion_is_terminal_but_same_state_is_idempotent():
    """Duplicate completion is safe, while retry must create a new attempt."""
    from workforce.agents.delegation.states import transition_step

    assert transition_step("completed", "completed") == "completed"
    with pytest.raises(ValueError, match="terminal"):
        transition_step("completed", "running")


def test_phase_c_feature_flags_are_declared_but_not_tool_seeded():
    """A missing workspace opt-in must leave every Phase C execution path off."""
    expected = {
        "agent_delegation",
        "agent_delegation_chief_of_staff",
        "agent_delegation_device_executors",
        "agent_delegation_n8n",
        "agent_delegation_sandbox",
    }
    actual = {
        getattr(feature_flags, "FLAG_AGENT_DELEGATION", None),
        getattr(feature_flags, "FLAG_AGENT_DELEGATION_CHIEF_OF_STAFF", None),
        getattr(feature_flags, "FLAG_AGENT_DELEGATION_DEVICE_EXECUTORS", None),
        getattr(feature_flags, "FLAG_AGENT_DELEGATION_N8N", None),
        getattr(feature_flags, "FLAG_AGENT_DELEGATION_SANDBOX", None),
    }
    assert actual == expected
    assert expected.isdisjoint(feature_flags.TOOL_FLAG_DEFAULTS)
