from __future__ import annotations

import pytest

from agent.workflows.engine import WorkflowEngine
from agent.workflows.models import WorkflowStatus
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
async def test_workflow_resumes_from_checkpoint_without_rerunning_completed_steps():
    step1_call_count = 0
    step2_call_count = 0

    async def step1_non_idempotent_charge(args):
        nonlocal step1_call_count
        step1_call_count += 1
        return {"charge_id": "chg_999", "amount": 100}

    async def step2_fulfill_order(args):
        nonlocal step2_call_count
        step2_call_count += 1
        return {"order_status": "fulfilled"}

    registry = MockToolRegistry()
    registry.register(MockToolSpec(name="payment.charge", handler=step1_non_idempotent_charge))
    registry.register(MockToolSpec(name="order.fulfill", handler=step2_fulfill_order))

    engine = WorkflowEngine(tool_registry=registry)

    spec = WorkflowSpec(
        id="test.resume",
        steps=[
            WorkflowStepSpec(id="charge_step", type=StepType.TOOL_CALL, tool="payment.charge"),
            WorkflowStepSpec(
                id="fulfill_step",
                type=StepType.TOOL_CALL,
                tool="order.fulfill",
                depends_on=["charge_step"],
            ),
        ],
    )

    # 1. Simulate process running step 1 and creating a checkpoint
    workflow = await engine.execute_spec(spec, initial_state={"workspace_id": "ws1"})
    assert workflow.status == WorkflowStatus.COMPLETED
    assert step1_call_count == 1
    assert step2_call_count == 1
    assert "charge_step" in workflow.completed_steps
    assert "charge_step" in workflow.checkpoints

    # 2. Simulate resuming a workflow that was interrupted after step 1:
    interrupted_workflow = workflow.model_copy(deep=True)
    interrupted_workflow.status = WorkflowStatus.RUNNING
    interrupted_workflow.completed_steps = ["charge_step"]
    del interrupted_workflow.state["fulfill_step"]

    # Resume execution with the existing workflow instance
    resumed_workflow = await engine.execute_spec(spec, initial_state={}, workflow=interrupted_workflow)

    assert resumed_workflow.status == WorkflowStatus.COMPLETED
    assert resumed_workflow.state["fulfill_step"] == {"order_status": "fulfilled"}
    assert step1_call_count == 1, "Non-idempotent step 1 was re-executed on resume!"
    assert step2_call_count == 2
