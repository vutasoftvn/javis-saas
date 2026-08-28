"""Unit tests for COSA workflow specifications (apps/cosa/workflows/specs.py).

Asserts:
- COSA_PAYOUT_APPROVAL_WORKFLOW_SPEC loads and passes strict DAG validation.
- Workflow steps sequence correctly: prepare_payout -> approval_gate -> execute_payout -> notify_failure.
- Malformed workflow definitions are rejected (cycles, dangling dependencies, duplicate IDs).
"""

from __future__ import annotations

import pytest
from agent_core.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec
from pydantic import ValidationError

from apps.cosa.workflows.specs import COSA_PAYOUT_APPROVAL_WORKFLOW_SPEC


def test_cosa_payout_approval_workflow_spec_validity():
    """COSA_PAYOUT_APPROVAL_WORKFLOW_SPEC is a well-formed DAG with approval and compensation."""
    spec = COSA_PAYOUT_APPROVAL_WORKFLOW_SPEC

    assert spec.id == "cosa.workflows.payout_approval"
    assert spec.version == "1.0.0"
    assert len(spec.steps) == 4

    step_map = {s.id: s for s in spec.steps}
    assert "prepare_payout" in step_map
    assert "approval_gate" in step_map
    assert "execute_payout" in step_map
    assert "notify_failure" in step_map

    # Step types
    assert step_map["prepare_payout"].type == StepType.DETERMINISTIC
    assert step_map["approval_gate"].type == StepType.APPROVAL_GATE
    assert step_map["execute_payout"].type == StepType.TOOL_CALL
    assert step_map["notify_failure"].type == StepType.COMPENSATING

    # Dependencies & tool target
    assert step_map["approval_gate"].depends_on == ["prepare_payout"]
    assert step_map["execute_payout"].depends_on == ["approval_gate"]
    assert step_map["execute_payout"].tool == "finance.payout.execute"
    assert step_map["execute_payout"].on_failure == "notify_failure"


def test_reject_invalid_payout_workflow_missing_dependency():
    """WorkflowSpec rejects steps referencing non-existent depends_on."""
    with pytest.raises(ValidationError, match="depends_on unknown step"):
        WorkflowSpec(
            id="cosa.workflows.invalid_dep",
            steps=[
                WorkflowStepSpec(
                    id="execute_payout",
                    type=StepType.TOOL_CALL,
                    tool="finance.payout.execute",
                    depends_on=["non_existent_gate"],
                )
            ],
        )


def test_reject_invalid_payout_workflow_cycle():
    """WorkflowSpec rejects cyclic step dependencies."""
    with pytest.raises(ValidationError, match="dependency cycle"):
        WorkflowSpec(
            id="cosa.workflows.cyclic",
            steps=[
                WorkflowStepSpec(
                    id="prepare_payout",
                    type=StepType.DETERMINISTIC,
                    depends_on=["execute_payout"],
                ),
                WorkflowStepSpec(
                    id="execute_payout",
                    type=StepType.TOOL_CALL,
                    tool="finance.payout.execute",
                    depends_on=["prepare_payout"],
                ),
            ],
        )


def test_reject_duplicate_step_ids():
    """WorkflowSpec rejects duplicate step identifiers."""
    with pytest.raises(ValidationError, match="duplicate step id"):
        WorkflowSpec(
            id="cosa.workflows.duplicate_steps",
            steps=[
                WorkflowStepSpec(id="step_a", type=StepType.DETERMINISTIC),
                WorkflowStepSpec(id="step_a", type=StepType.DETERMINISTIC),
            ],
        )
