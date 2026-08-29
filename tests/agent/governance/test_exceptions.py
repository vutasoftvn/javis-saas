from __future__ import annotations

from agent.governance.exceptions import GovernanceStoreConfigurationError


def test_governance_store_configuration_error_is_an_exception():
    error = GovernanceStoreConfigurationError("missing db_session_factory")

    assert isinstance(error, Exception)
    assert str(error) == "missing db_session_factory"
