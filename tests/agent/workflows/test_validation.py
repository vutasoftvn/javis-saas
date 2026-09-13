from __future__ import annotations

import pytest

from agent.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec
from agent.workflows.validation import (
    UnsupportedWorkflowStepError,
    WorkflowPublishValidator,
    WorkflowValidationContext,
)


def test_publish_validator_passes_valid_v1_spec():
    spec = WorkflowSpec(
        id="wf_valid_v1",
        name="Valid V1 Flow",
        version="1.0.0",
        steps=[
            WorkflowStepSpec(
                id="step_tool",
                type=StepType.TOOL_CALL,
                tool="read_data",
            ),
            WorkflowStepSpec(
                id="step_agent",
                type=StepType.AGENT,
                project_agent_deployment_id="dep_valid_123",
                depends_on=["step_tool"],
            ),
            WorkflowStepSpec(
                id="step_gate",
                type=StepType.APPROVAL_GATE,
                action="publish_data",
                subject_key="data_id",
                depends_on=["step_agent"],
            ),
        ],
    )

    ctx = WorkflowValidationContext(
        workspace_id="ws-1",
        project_id="proj-1",
        active_deployments={"dep_valid_123": {"status": "ACTIVE"}},
        active_capabilities={"read_data", "write_data"},
        registered_executors={StepType.AGENT, StepType.TOOL_CALL, StepType.APPROVAL_GATE},
    )

    result = WorkflowPublishValidator.validate(spec, ctx)
    assert result.is_valid is True
    assert len(result.errors) == 0


def test_publish_validator_rejects_step_without_registered_executor():
    spec = WorkflowSpec(
        id="wf_agent_no_exec",
        name="Agent Without Registered Executor Flow",
        version="1.0.0",
        steps=[
            WorkflowStepSpec(
                id="step_agent",
                type=StepType.AGENT,
                project_agent_deployment_id="dep_valid_123",
            ),
        ],
    )
    # Default context does not register AGENT executor
    ctx = WorkflowValidationContext(
        workspace_id="ws-1",
        active_deployments={"dep_valid_123": {"status": "ACTIVE"}},
    )
    result = WorkflowPublishValidator.validate(spec, ctx)
    assert result.is_valid is False
    assert any("has no registered executor in execution plane" in e for e in result.errors)


def test_publish_validator_rejects_inactive_agent_deployment():
    spec = WorkflowSpec(
        id="wf_inactive_agent",
        name="Inactive Agent Flow",
        version="1.0.0",
        steps=[
            WorkflowStepSpec(
                id="step_agent",
                type=StepType.AGENT,
                project_agent_deployment_id="dep_unknown_404",
            ),
        ],
    )

    ctx = WorkflowValidationContext(
        workspace_id="ws-1",
        active_deployments={"dep_other": {"status": "ACTIVE"}},
        registered_executors={StepType.AGENT},
    )

    result = WorkflowPublishValidator.validate(spec, ctx)
    assert result.is_valid is False
    assert any("dep_unknown_404" in e for e in result.errors)


def test_publish_validator_rejects_non_allowlisted_capability():
    spec = WorkflowSpec(
        id="wf_bad_cap",
        name="Bad Cap Flow",
        version="1.0.0",
        steps=[
            WorkflowStepSpec(
                id="step_tool",
                type=StepType.TOOL_CALL,
                tool="unapproved_network_call",
            ),
        ],
    )

    ctx = WorkflowValidationContext(
        workspace_id="ws-1",
        active_capabilities={"read_db"},
    )

    result = WorkflowPublishValidator.validate(spec, ctx)
    assert result.is_valid is False
    assert any("unapproved_network_call" in e for e in result.errors)


def test_publish_validator_rejects_malformed_approval_gate():
    spec = WorkflowSpec(
        id="wf_bad_gate",
        name="Bad Gate Flow",
        version="1.0.0",
        steps=[
            WorkflowStepSpec(
                id="step_gate",
                type=StepType.APPROVAL_GATE,
                # missing action and subject_key
            ),
        ],
    )

    result = WorkflowPublishValidator.validate(spec)
    assert result.is_valid is False
    assert any("missing action" in e for e in result.errors)
    assert any("missing subject_key" in e for e in result.errors)
