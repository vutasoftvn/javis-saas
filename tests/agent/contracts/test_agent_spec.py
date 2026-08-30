from __future__ import annotations

import pytest
from agent.contracts.spec import AgentSpec
from pydantic import ValidationError


def test_agent_spec_requires_explicit_model_input_capability_ref() -> None:
    with pytest.raises(ValidationError):
        AgentSpec(id="test.agent.direct-input")


def test_agent_spec_keeps_model_input_scope_separate_from_executable_tools() -> None:
    spec = AgentSpec(
        id="test.agent.direct-input",
        capability_refs=["operations.task.list"],
        model_input_capability_ref="model.input.direct-user-message",
    )

    assert spec.model_input_capability_ref == "model.input.direct-user-message"
    assert spec.capability_refs == ["operations.task.list"]
