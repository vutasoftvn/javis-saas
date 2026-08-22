import pytest

from workforce.agents.runtime.adapters.mock import MockRuntime
from workforce.agents.runtime.errors import AgentRuntimeError
from workforce.agents.runtime.manager import AgentRuntimeManager


def test_explicit_unknown_runtime_never_falls_back_to_mock():
    """A typo in a governed assignment must not execute a different runtime."""
    manager = AgentRuntimeManager()
    manager.register(MockRuntime())

    with pytest.raises(AgentRuntimeError) as error:
        manager.get_runtime("missing", allow_default=False)

    assert error.value.code == "AGENT_RUNTIME_UNAVAILABLE"


def test_delegation_provider_manager_rejects_unknown_provider():
    """Unknown delegation routing is a terminal configuration error."""
    from workforce.agents.delegation.manager import (
        DelegationProviderManager,
        DelegationProviderUnknown,
    )

    manager = DelegationProviderManager()
    with pytest.raises(DelegationProviderUnknown, match="missing"):
        manager.get("missing")
