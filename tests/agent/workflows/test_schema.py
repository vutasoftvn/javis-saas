from __future__ import annotations

import pytest

from agent.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec


def agent_step_without_deployment() -> dict:
    return {
        "id": "wf_agent_test",
        "name": "Agent Flow",
        "version": "1.0.0",
        "steps": [
            {
                "id": "step_agent_1",
                "name": "Run Agent",
                "type": "agent",
                "inputs": {"prompt": "analyze data"},
            }
        ],
    }


def test_agent_step_requires_project_agent_deployment_pin():
    with pytest.raises(ValueError, match="project_agent_deployment_id"):
        WorkflowSpec.model_validate(agent_step_without_deployment())


def test_agent_step_succeeds_with_project_agent_deployment_pin():
    data = agent_step_without_deployment()
    data["steps"][0]["project_agent_deployment_id"] = "proj_dep_12345"
    spec = WorkflowSpec.model_validate(data)
    assert spec.steps[0].project_agent_deployment_id == "proj_dep_12345"


def test_spec_hash_and_pinned_identity():
    spec = WorkflowSpec(
        id="wf_pin_test",
        name="Pin Test",
        version="1.2.0",
        steps=[
            WorkflowStepSpec(
                id="step-1",
                type=StepType.DETERMINISTIC,
            )
        ],
    ).with_hash()

    assert spec.definition_hash is not None
    assert len(spec.definition_hash) == 64

    pinned = spec.to_pinned_identity()
    assert pinned.spec_kind == "workflow"
    assert pinned.spec_id == "wf_pin_test"
    assert pinned.spec_version == "1.2.0"
    assert pinned.definition_hash == spec.definition_hash
