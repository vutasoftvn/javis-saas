from __future__ import annotations

import pytest

from agent.workflows.engine import WorkflowEngine
from agent.workflows.models import StepStatus, WorkflowStatus
from agent.workflows.schema import StepType, WorkflowSpec, WorkflowStepSpec


class MockToolSpec:
    def __init__(self, name: str, handler):
        self.name = name
        self._handler = handler

    async def execute(self, **kwargs):
        return await self._handler(kwargs)


class MockToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, tool):
        self._tools[tool.name] = tool

    def get(self, name: str):
        return self._tools.get(name)


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

    registry = MockToolRegistry()
    registry.register(MockToolSpec(name="fetch.data", handler=step_fetch))
    registry.register(MockToolSpec(name="dangerous.action", handler=step_failing_action))
    registry.register(MockToolSpec(name="compensate.fallback", handler=step_compensate_handler))

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
