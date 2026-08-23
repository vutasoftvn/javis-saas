from __future__ import annotations

import pytest

from agentos.tools.registry import ToolRegistry, ToolSpec
from agentos.workflows.engine import WorkflowEngine
from agentos.workflows.models import StepStatus, WorkflowStatus
from agentos.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec


@pytest.mark.asyncio
async def test_workflow_step_on_failure_triggers_compensation():
    compensation_called = []

    async def step_fetch(args):
        return {"items": ["item1"]}

    async def step_failing_action(args):
        raise RuntimeError("Network timeout connecting to external API")

    async def step_compensate_handler(args):
        compensation_called.append(True)
        return {"compensated": True, "fallback_logged": True}

    registry = ToolRegistry()
    registry.register(ToolSpec(name="fetch.data", description="d", handler=step_fetch))
    registry.register(ToolSpec(name="dangerous.action", description="d", handler=step_failing_action))
    registry.register(ToolSpec(name="compensate.fallback", description="d", handler=step_compensate_handler))

    engine = WorkflowEngine(tool_registry=registry)

    spec = WorkflowSpec(
        id="test.compensation",
        steps=[
            WorkflowStepSpec(id="step_fetch", type=StepType.TOOL_CALL, tool="fetch.data"),
            WorkflowStepSpec(
                id="step_action",
                type=StepType.TOOL_CALL,
                tool="dangerous.action",
                depends_on=["step_fetch"],
                on_failure="step_compensate",
            ),
            WorkflowStepSpec(
                id="step_compensate",
                type=StepType.TOOL_CALL,
                tool="compensate.fallback",
            ),
        ],
    )

    workflow = await engine.execute_spec(spec, initial_state={"workspace_id": "ws1"})

    assert workflow.status == WorkflowStatus.FAILED
    assert workflow.failed_step_name == "step_action"
    assert len(compensation_called) == 1
    assert workflow.state["_compensated_step"] == "step_action"
    assert workflow.state["step_compensate"] == {"compensated": True, "fallback_logged": True}
    assert workflow.step_outcomes["step_compensate"].status == StepStatus.COMPLETED
