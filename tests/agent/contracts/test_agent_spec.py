from __future__ import annotations

import pytest
from agent.contracts.spec import AgentSpec
from pydantic import ValidationError


def test_agent_spec_defaults_model_input_capability_ref_to_none() -> None:
    spec = AgentSpec(id="test.agent.direct-input")
    assert spec.model_input_capability_ref is None


def test_agent_spec_keeps_model_input_scope_separate_from_executable_tools() -> None:
    spec = AgentSpec(
        id="test.agent.direct-input",
        capability_refs=["operations.task.list"],
        model_input_capability_ref="model.input.direct-user-message",
    )

    assert spec.model_input_capability_ref == "model.input.direct-user-message"
    assert spec.capability_refs == ["operations.task.list"]


def test_agent_spec_rejects_model_input_scope_as_an_executable_tool() -> None:
    with pytest.raises(ValidationError, match="model_input_capability_ref"):
        AgentSpec(
            id="test.agent.overlapping-input-scope",
            capability_refs=[
                "operations.task.list",
                "model.input.direct-user-message",
            ],
            model_input_capability_ref="model.input.direct-user-message",
        )
