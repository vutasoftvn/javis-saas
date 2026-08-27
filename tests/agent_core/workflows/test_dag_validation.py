from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent_core.workflows.engine import WorkflowEngine
from agent_core.workflows.models import WorkflowStatus
from agent_core.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec


def test_rejects_duplicate_step_ids():
    with pytest.raises(ValidationError, match="duplicate step id"):
        WorkflowSpec(
            id="test.dup",
            steps=[
                WorkflowStepSpec(id="a", type=StepType.DETERMINISTIC),
                WorkflowStepSpec(id="a", type=StepType.DETERMINISTIC),
            ],
        )


def test_rejects_dangling_depends_on():
    with pytest.raises(ValidationError, match="depends_on unknown step"):
        WorkflowSpec(
            id="test.dangling",
            steps=[
                WorkflowStepSpec(id="a", type=StepType.DETERMINISTIC, depends_on=["does_not_exist"]),
            ],
        )


def test_rejects_dangling_on_failure_target():
    with pytest.raises(ValidationError, match="on_failure targets unknown step"):
        WorkflowSpec(
            id="test.dangling_on_failure",
            steps=[
                WorkflowStepSpec(id="a", type=StepType.DETERMINISTIC, on_failure="does_not_exist"),
            ],
        )


def test_rejects_dangling_compensate_with_target():
    with pytest.raises(ValidationError, match="compensate_with targets unknown step"):
        WorkflowSpec(
            id="test.dangling_compensate_with",
            steps=[
                WorkflowStepSpec(id="a", type=StepType.DETERMINISTIC, compensate_with="does_not_exist"),
            ],
        )


def test_rejects_direct_cycle():
    with pytest.raises(ValidationError, match="dependency cycle"):
        WorkflowSpec(
            id="test.cycle",
            steps=[
                WorkflowStepSpec(id="a", type=StepType.DETERMINISTIC, depends_on=["b"]),
                WorkflowStepSpec(id="b", type=StepType.DETERMINISTIC, depends_on=["a"]),
            ],
        )


def test_rejects_self_cycle():
    with pytest.raises(ValidationError, match="dependency cycle"):
        WorkflowSpec(
            id="test.self_cycle",
            steps=[
                WorkflowStepSpec(id="a", type=StepType.DETERMINISTIC, depends_on=["a"]),
            ],
        )


def test_rejects_forward_step_depending_on_compensation_target():
    with pytest.raises(ValidationError, match="never runs as a forward step"):
        WorkflowSpec(
            id="test.compensation_as_forward_dep",
            steps=[
                WorkflowStepSpec(id="a", type=StepType.DETERMINISTIC, on_failure="rollback_a"),
                WorkflowStepSpec(id="rollback_a", type=StepType.DETERMINISTIC),
                WorkflowStepSpec(id="b", type=StepType.DETERMINISTIC, depends_on=["rollback_a"]),
            ],
        )


def test_valid_parallel_dag_with_approval_and_compensation_still_passes():
    # Không raise — DAG hợp lệ: b, c chạy song song sau a; d chờ cả hai;
    # a có compensation riêng không bị ai depends_on.
    spec = WorkflowSpec(
        id="test.valid_dag",
        steps=[
            WorkflowStepSpec(id="a", type=StepType.DETERMINISTIC, on_failure="rollback_a"),
            WorkflowStepSpec(id="rollback_a", type=StepType.DETERMINISTIC),
            WorkflowStepSpec(id="b", type=StepType.DETERMINISTIC, depends_on=["a"]),
            WorkflowStepSpec(id="c", type=StepType.DETERMINISTIC, depends_on=["a"]),
            WorkflowStepSpec(id="d", type=StepType.APPROVAL_GATE, depends_on=["b", "c"]),
        ],
    )
    assert spec.get_step("d") is not None


@pytest.mark.asyncio
async def test_engine_fails_safe_when_spec_bypasses_validation_with_dangling_dependency():
    # Xây spec hợp lệ trước, rồi mutate depends_on sau khi validation đã chạy
    # để mô phỏng spec "lọt" qua validation (vd construct thủ công / bypass).
    spec = WorkflowSpec(
        id="test.bypassed_dangling",
        steps=[
            WorkflowStepSpec(id="a", type=StepType.DETERMINISTIC),
        ],
    )
    spec.steps[0].depends_on = ["ghost_step"]

    engine = WorkflowEngine()
    workflow = await engine.execute_spec(spec, initial_state={})

    assert workflow.status == WorkflowStatus.FAILED
    assert workflow.completed_steps == []
    assert "stuck" in (workflow.error or "")
