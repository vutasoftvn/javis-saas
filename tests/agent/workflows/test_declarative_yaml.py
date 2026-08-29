from __future__ import annotations

from pathlib import Path
import pytest

from agent.workflows.loader import WorkflowDefinitionLoadError, load_workflow_spec
from agent.workflows.schema import StepType, WorkflowSpec


def test_load_strategy_gate_evaluation_flow_yaml():
    yaml_path = Path("packages/agent/workflows/definitions/strategy_gate_evaluation_flow.yaml")
    spec = load_workflow_spec(yaml_path)

    assert isinstance(spec, WorkflowSpec)
    assert spec.id == "strategy.gate-evaluation-flow"
    assert spec.name == "Strategy Gate Evaluation Flow"
    assert len(spec.steps) == 4

    step_fetch = spec.get_step("fetch_evidence")
    assert step_fetch is not None
    assert step_fetch.type == StepType.TOOL_CALL
    assert step_fetch.tool == "strategy.evidence.list"
    assert step_fetch.depends_on == []

    step_eval = spec.get_step("evaluate_gate")
    assert step_eval is not None
    assert step_eval.depends_on == ["fetch_evidence"]
    assert step_eval.tool == "strategy.gate_evaluation.create"

    step_notify = spec.get_step("notify_founder")
    assert step_notify is not None
    assert step_notify.depends_on == ["evaluate_gate"]
    assert step_notify.on_failure == "compensate_notify"

    step_comp = spec.get_step("compensate_notify")
    assert step_comp is not None
    assert step_comp.tool == "notification.retry_or_log"


def test_load_from_yaml_string():
    content = """
id: custom.flow
steps:
  - id: step_1
    type: tool_call
    tool: test.echo
"""
    spec = load_workflow_spec(content)
    assert spec.id == "custom.flow"
    assert len(spec.steps) == 1
    assert spec.steps[0].id == "step_1"


def test_load_invalid_yaml_raises_error():
    with pytest.raises(WorkflowDefinitionLoadError):
        load_workflow_spec("non_existent_file.yaml")

    with pytest.raises(WorkflowDefinitionLoadError):
        load_workflow_spec("- just a list, not a dict")
