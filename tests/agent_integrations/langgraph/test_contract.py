"""Contract and smoke tests for LangGraph workflow runtime adapter.

Gated by skipif when langgraph is not installed.
"""

from __future__ import annotations

import importlib.util

import pytest

if importlib.util.find_spec("langgraph") is None:
    pytest.skip(
        "langgraph is not installed — skipping LangGraph contract tests", allow_module_level=True
    )

from agent.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec
from agent_integrations.langgraph.workflow_runtime import (
    _merge_results,
    compile_deterministic_workflow,
)


def test_langgraph_merge_results_reducer():
    """_merge_results correctly unions dictionaries."""
    left = {"step_1": {"a": 1}, "common": "left"}
    right = {"step_2": {"b": 2}, "common": "right"}
    merged = _merge_results(left, right)
    assert merged["step_1"] == {"a": 1}
    assert merged["step_2"] == {"b": 2}
    assert merged["common"] == "right"


def test_compile_deterministic_workflow():
    """compile_deterministic_workflow builds StateGraph from WorkflowSpec."""
    spec = WorkflowSpec(
        id="test_dag",
        name="Test DAG",
        version="1.0.0",
        steps=[
            WorkflowStepSpec(id="step_a", name="Step A", type=StepType.DETERMINISTIC),
            WorkflowStepSpec(
                id="step_b", name="Step B", type=StepType.DETERMINISTIC, depends_on=["step_a"]
            ),
        ],
    )
    registry = {
        "step_a": lambda results: {"val": 10},
        "step_b": lambda results: {"val": results["step_a"]["val"] * 2},
    }

    graph = compile_deterministic_workflow(spec, registry)
    assert graph is not None
